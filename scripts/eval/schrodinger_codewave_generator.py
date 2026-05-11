"""Schrödinger code-wave generator (split-operator method).

The third oracle for the code-diffusion bake-off. SCBE-native: per AR
step, treat the LM's logits as a quantum wavefunction over the vocab,
evolve K Trotter-Strang steps under a contract-shaped potential

    V(t) = -log P_base(t) - alpha * required_indicator(t)
                          + beta  * forbidden_indicator(t)

with kinetic term T_kin = (1/2m) * p^2 (FFT-diagonal on token-id index).
The kinetic operator lets amplitude flow between vocab positions; the
potential pulls amplitude toward the contract.

By default we evolve in IMAGINARY TIME (Wick rotation tau -> i*tau).
Real-time Schrödinger evolution is unitary and preserves |psi|^2 in a
way that doesn't converge to a "best" token — it oscillates. Imaginary-
time evolution is the standard numerical-QM technique for projecting
onto the ground state of H = T + V, i.e. the deepest contract well.
The wave still "propagates"; it just relaxes into the contract basin
instead of bouncing off its walls.

Configurable: set `imaginary_time = False` to recover unitary real-time
evolution as a research lever (interesting but typically worse at the
gate).

This is NOT a diffusion LM. It is a logit-space wave-propagation
post-processor that runs on top of any AR model. The mod replaces the
"diffusion" oracle in the bake-off when DiffuCoder is unavailable
(local 6GB GPU, no HF Jobs credits).

Mathematical sketch (imaginary time):
    Strang splitting per step:
        psi <- exp(-tau*V/2) * psi
        psi <- IFFT[ exp(-tau*k^2 / (2m)) * FFT[psi] ]
        psi <- exp(-tau*V/2) * psi
        psi <- psi / ||psi||                      # renormalize
    After K steps: sample from |psi|^2 (or argmax) -> token id.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np


@dataclass
class SchrodingerConfig:
    """Default settings tuned to PERTURB rather than DOMINATE base logits.

    Earlier defaults (alpha=6, beta=12) were too strong when required
    phrases tokenize into many BPE pieces — every piece got the bonus,
    creating attractors that caused repetition collapse on small models.
    Defaults are now mild; bump for stronger contract enforcement.
    """

    alpha_required: float = 1.5     # required-token bonus depth (lowers V)
    beta_forbidden: float = 4.0     # forbidden-token wall height (raises V)
    inverse_mass: float = 0.3       # 1/m in T_kin = p^2 / (2m)
    tau: float = 0.25               # time-step size
    n_steps: int = 8                # Trotter steps per token decision
    sample: bool = False            # False = argmax; True = sample from |psi|^2
    imaginary_time: bool = True     # True = ground-state projection (default);
                                    # False = unitary real-time (research lever)
    active_top_k: int = 256         # Restrict wave evolution to top-K base
                                    # logit tokens + any required-marker tokens.
                                    # Drops FFT cost from O(V log V) to
                                    # O(K log K). Set 0 to disable subsetting
                                    # (full-vocab evolution; expensive).


def _build_indicator_masks(
    vocab: list[str],
    required: list[str],
    forbidden: list[str],
) -> tuple[np.ndarray, np.ndarray]:
    """Token-level required/forbidden indicators.

    A token is "required-flavored" if its lowercased text is a substring
    of any required phrase OR contains any required phrase. A token is
    "forbidden-flavored" if its lowercased text contains a forbidden
    phrase as a word-boundary regex match (matching v6h scoring).
    """
    req = [str(r).lower().strip() for r in (required or []) if str(r).strip()]
    forb = [str(f).lower().strip() for f in (forbidden or []) if str(f).strip()]
    n = len(vocab)
    req_mask = np.zeros(n, dtype=np.float32)
    forb_mask = np.zeros(n, dtype=np.float32)

    forb_patterns: list[re.Pattern] = []
    for f in forb:
        if re.fullmatch(r"[a-z0-9_ -]+", f):
            body = r"\s+".join(re.escape(part) for part in f.split())
            forb_patterns.append(re.compile(r"(?<![a-z0-9_])" + body + r"(?![a-z0-9_])"))
        else:
            forb_patterns.append(re.compile(re.escape(f)))

    for i, raw_tok in enumerate(vocab):
        tok = (raw_tok or "").lower().strip()
        if not tok:
            continue
        # Required: token is part of OR contains a required phrase
        for r in req:
            if not r:
                continue
            if r in tok or tok in r:
                req_mask[i] += 1.0
                break
        # Forbidden: token text directly matches a forbidden pattern
        for pat in forb_patterns:
            if pat.search(tok):
                forb_mask[i] += 1.0
                break
    return req_mask, forb_mask


def _evolve_wavefunction(
    psi: np.ndarray,
    V: np.ndarray,
    cfg: SchrodingerConfig,
    k_grid: np.ndarray,
) -> np.ndarray:
    """K Trotter-Strang steps of split-operator Schrödinger evolution.

    Real-time when cfg.imaginary_time is False (unitary, exp(-i*tau*...));
    imaginary-time when True (ground-state projection, exp(-tau*...)
    plus per-step renormalization).
    """
    factor = 1.0 if cfg.imaginary_time else 1j
    # half-V step exponent
    half_V = np.exp(-factor * cfg.tau * V / 2.0)
    # kinetic step exponent (diagonal in momentum basis)
    kin = np.exp(-factor * cfg.tau * (k_grid ** 2) * cfg.inverse_mass / 2.0)
    for _ in range(int(cfg.n_steps)):
        psi = half_V * psi
        psi = np.fft.ifft(kin * np.fft.fft(psi))
        psi = half_V * psi
        if cfg.imaginary_time:
            norm = np.linalg.norm(psi)
            if norm > 0:
                psi = psi / norm
    return psi


def _select_active_subset(
    base_logits: np.ndarray, req_mask: np.ndarray, top_k: int
) -> np.ndarray:
    """Indices of (top-K base-logit tokens) ∪ (required-marker tokens).

    The wave-evolution restriction set: large enough that the model's
    actual candidates are present, plus any required-marker tokens so
    the alpha bonus has somewhere to pull amplitude into.
    """
    n = base_logits.shape[0]
    if top_k <= 0 or top_k >= n:
        return np.arange(n, dtype=np.int64)
    k = min(int(top_k), n)
    # Top-k by base logit (np.argpartition is O(V); cheap relative to FFT).
    top_idx = np.argpartition(-base_logits, k - 1)[:k]
    req_idx = np.nonzero(req_mask > 0)[0]
    union = np.unique(np.concatenate([top_idx, req_idx]))
    return union.astype(np.int64)


def schrodinger_step_logits(
    base_logits: np.ndarray,
    req_mask: np.ndarray,
    forb_mask: np.ndarray,
    cfg: SchrodingerConfig,
    rng: np.random.Generator | None = None,
) -> int:
    """Pick one token id per AR step via Schrödinger evolution.

    1. select active subset (top-K base + required tokens)
    2. psi_0 = sqrt(softmax(logits[active]))
    3. V = -log p_base - alpha*req_mask + beta*forb_mask  (over active)
    4. evolve K Strang steps with FFT-diagonal kinetic term
    5. argmax (or sample) of |psi|^2 -> return ORIGINAL token id
    """
    active = _select_active_subset(base_logits, req_mask, cfg.active_top_k)

    sub_logits = base_logits[active]
    sub_req = req_mask[active].astype(np.float64)
    sub_forb = forb_mask[active].astype(np.float64)

    shifted = sub_logits - np.max(sub_logits)
    p_base = np.exp(shifted)
    p_base = p_base / np.maximum(p_base.sum(), 1e-30)
    psi = np.sqrt(p_base + 1e-30).astype(np.complex128)

    log_p = np.log(p_base + 1e-30).astype(np.float64)
    V = -log_p - cfg.alpha_required * sub_req + cfg.beta_forbidden * sub_forb

    n_sub = sub_logits.shape[0]
    k_grid = np.fft.fftfreq(n_sub) * (2.0 * np.pi)
    psi = _evolve_wavefunction(psi, V, cfg, k_grid)

    prob = np.abs(psi) ** 2
    total = prob.sum()
    if not np.isfinite(total) or total <= 0:
        return int(active[int(np.argmax(p_base))])
    prob = prob / total

    if cfg.sample:
        rng = rng or np.random.default_rng()
        chosen_in_subset = int(rng.choice(n_sub, p=prob))
    else:
        chosen_in_subset = int(np.argmax(prob))
    return int(active[chosen_in_subset])


class SchrodingerLogitsProcessor:
    """HF-compatible LogitsProcessor that applies Schrödinger evolution.

    Plugs into `model.generate(...)` so the standard HF generation loop
    handles KV caching for us. Per generation step, we receive the
    next-token logits, evolve the wavefunction K Trotter steps under
    the contract potential, and return log|psi|^2 as the new logits.
    """

    def __init__(
        self,
        req_mask: np.ndarray,
        forb_mask: np.ndarray,
        cfg: SchrodingerConfig,
    ) -> None:
        self.req_mask = req_mask
        self.forb_mask = forb_mask
        self.cfg = cfg

    def __call__(self, input_ids, scores):
        import torch

        # scores: (batch, vocab) float; assume batch=1 in the bake-off.
        np_scores = scores[0].detach().to("cpu", dtype=torch.float32).numpy()
        if np_scores.shape[0] != self.req_mask.shape[0]:
            if np_scores.shape[0] > self.req_mask.shape[0]:
                pad = np_scores.shape[0] - self.req_mask.shape[0]
                self.req_mask = np.concatenate([self.req_mask, np.zeros(pad, dtype=self.req_mask.dtype)])
                self.forb_mask = np.concatenate([self.forb_mask, np.zeros(pad, dtype=self.forb_mask.dtype)])
            else:
                self.req_mask = self.req_mask[: np_scores.shape[0]]
                self.forb_mask = self.forb_mask[: np_scores.shape[0]]

        # Restrict the wave evolution to an active subset to keep CPU/RAM
        # sane on a 152k-vocab model. Inactive tokens keep their original
        # logits (so the rest of the generation pipeline still sees them).
        active = _select_active_subset(np_scores, self.req_mask, self.cfg.active_top_k)
        sub_logits = np_scores[active]
        sub_req = self.req_mask[active].astype(np.float64)
        sub_forb = self.forb_mask[active].astype(np.float64)

        shifted = sub_logits - np.max(sub_logits)
        p_base = np.exp(shifted)
        p_base = p_base / np.maximum(p_base.sum(), 1e-30)
        psi = np.sqrt(p_base + 1e-30).astype(np.complex128)
        log_p = np.log(p_base + 1e-30).astype(np.float64)
        V = -log_p - self.cfg.alpha_required * sub_req + self.cfg.beta_forbidden * sub_forb

        n_sub = sub_logits.shape[0]
        k_grid = np.fft.fftfreq(n_sub) * (2.0 * np.pi)
        psi = _evolve_wavefunction(psi, V, self.cfg, k_grid)
        prob = np.abs(psi) ** 2
        total = prob.sum()
        if not np.isfinite(total) or total <= 0:
            return scores
        prob = prob / total
        sub_new_logits = np.log(prob + 1e-30)

        # Splice the evolved logits back into the full-vocab scores tensor.
        # Inactive token IDs keep their original (very-negative) logits,
        # so they remain effectively un-pickable by argmax / softmax.
        new_logits_np = np_scores.copy()
        new_logits_np[active] = sub_new_logits
        out = torch.from_numpy(new_logits_np).to(scores.dtype).to(scores.device)
        return out.unsqueeze(0)


class SchrodingerCodeWaveGenerator:
    """Wraps an HF causal-LM with Schrödinger logit-space evolution.

    Uses `model.generate(...)` + a `LogitsProcessor` so KV caching is
    handled by HF (~50-100x faster than naive per-token full forward).
    """

    def __init__(
        self,
        model_id: str = "Qwen/Qwen2.5-Coder-1.5B-Instruct",
        max_new_tokens: int = 320,
        cfg: SchrodingerConfig | None = None,
        device: str | None = None,
    ) -> None:
        self.model_id = model_id
        self.max_new_tokens = max_new_tokens
        self.cfg = cfg or SchrodingerConfig()
        self._device_pref = device
        self._tok = None
        self._model = None
        self._vocab_strings: list[str] | None = None

    def _ensure_loaded(self) -> None:
        if self._model is not None:
            return
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        tok = AutoTokenizer.from_pretrained(self.model_id, trust_remote_code=True)
        if tok.pad_token_id is None:
            tok.pad_token_id = tok.eos_token_id
        if self._device_pref:
            device = self._device_pref
        else:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        dtype = torch.float16 if device == "cuda" else torch.float32
        model = AutoModelForCausalLM.from_pretrained(
            self.model_id, torch_dtype=dtype, trust_remote_code=True
        )
        model.eval()
        model = model.to(device)
        self._tok = tok
        self._model = model
        self._device = device
        # Materialize vocab strings once for indicator masks.
        n = tok.vocab_size
        strings: list[str] = []
        for i in range(n):
            try:
                s = tok.decode([i], skip_special_tokens=False)
            except Exception:
                s = ""
            strings.append(s or "")
        self._vocab_strings = strings

    def generate(self, prompt: dict) -> str:
        self._ensure_loaded()
        import torch
        from transformers import LogitsProcessorList

        text = (prompt.get("prompt") or "").strip()
        try:
            input_ids = self._tok.apply_chat_template(
                [{"role": "user", "content": text}],
                return_tensors="pt",
                add_generation_prompt=True,
            )
        except Exception:
            input_ids = self._tok(text, return_tensors="pt").input_ids
        if hasattr(input_ids, "input_ids") and not hasattr(input_ids, "shape"):
            input_ids = input_ids.input_ids
        input_ids = input_ids.to(self._device)

        assert self._vocab_strings is not None
        req_mask, forb_mask = _build_indicator_masks(
            self._vocab_strings,
            list(prompt.get("required") or []),
            list(prompt.get("forbidden") or []),
        )
        processor = SchrodingerLogitsProcessor(req_mask, forb_mask, self.cfg)
        processors = LogitsProcessorList([processor])

        with torch.inference_mode():
            out = self._model.generate(
                input_ids,
                max_new_tokens=self.max_new_tokens,
                do_sample=False,
                pad_token_id=self._tok.pad_token_id,
                logits_processor=processors,
            )
        new_tokens = out[0, input_ids.shape[1]:]
        return self._tok.decode(new_tokens, skip_special_tokens=True)


def make_schrodinger_generator(
    model_id: str = "Qwen/Qwen2.5-Coder-1.5B-Instruct",
    max_new_tokens: int = 320,
    cfg: SchrodingerConfig | None = None,
) -> Callable[[dict], str]:
    """Bake-off-compatible factory matching make_ar_generator signature."""
    gen = SchrodingerCodeWaveGenerator(model_id=model_id, max_new_tokens=max_new_tokens, cfg=cfg)

    def _call(prompt: dict) -> str:
        return gen.generate(prompt)

    return _call


__all__ = [
    "SchrodingerConfig",
    "SchrodingerCodeWaveGenerator",
    "make_schrodinger_generator",
    "schrodinger_step_logits",
]
