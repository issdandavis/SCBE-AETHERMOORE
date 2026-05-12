"""SCBE Code-Diffusion Bake-Off (v1).

Runs the v6h coding-verification gate (12 prompts, lowercase-substring
scoring) against TWO generators in parallel:

  * an autoregressive baseline (default: Qwen2.5-Coder-7B-Instruct)
  * a diffusion candidate (default: apple/DiffuCoder-7B-Instruct)

The point is *not* to pick a winner overall. The point is to find
problem SHAPES where diffusion lifts AR-stuck prompts, so we can route
those shapes to a diffusion oracle as a second-opinion lane.

Run modes:
  --dry-run       record stub responses; useful for testing the harness
                  itself without touching a GPU.
  --baseline-only run only the AR baseline (cheap sanity check).
  --diffusion-only run only the diffusion candidate.

Output:
  artifacts/eval/diffusion_bakeoff_<contract_id>_<timestamp>.json
  docs/research/CODE_DIFFUSION_BAKEOFF_<date>.md (when --emit-report)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
DEFAULT_CONTRACT = REPO_ROOT / "config" / "eval" / "coding_diffusion_bakeoff_v1.json"
DEFAULT_BASELINE = "Qwen/Qwen2.5-Coder-7B-Instruct"
DEFAULT_DIFFUSION = "apple/DiffuCoder-7B-Instruct"
DEFAULT_SCHRODINGER = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "eval"


@dataclass
class GateVerdict:
    id: str
    shape: str
    ok: bool
    missing_required: list[str]
    triggered_forbidden: list[str]
    response_chars: int


@dataclass
class GeneratorReport:
    label: str
    model_id: str
    n_total: int
    n_pass: int
    pass_rate: float
    by_prompt: list[GateVerdict] = field(default_factory=list)


def gate_score(prompt: dict, response: str) -> GateVerdict:
    """Identical to the v6h `_gate_score` rule (canonical scorer)."""
    body_lower = (response or "").lower()
    missing_required = [str(t) for t in (prompt.get("required") or []) if str(t).lower() not in body_lower]

    def contains_forbidden(term: str) -> bool:
        needle = str(term).strip().lower()
        if not needle:
            return False
        if re.fullmatch(r"[a-z0-9_ -]+", needle):
            pattern_body = r"\s+".join(re.escape(part) for part in needle.split())
            pattern = r"(?<![a-z0-9_])" + pattern_body + r"(?![a-z0-9_])"
            return re.search(pattern, body_lower) is not None
        return needle in body_lower

    triggered_forbidden = [str(t) for t in (prompt.get("forbidden") or []) if contains_forbidden(t)]
    return GateVerdict(
        id=str(prompt.get("id", "")),
        shape=str(prompt.get("shape", "unknown")),
        ok=(not missing_required) and (not triggered_forbidden),
        missing_required=missing_required,
        triggered_forbidden=triggered_forbidden,
        response_chars=len(response or ""),
    )


def load_contract(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------


def _stub_response(prompt: dict, label: str) -> str:
    """A deliberately *partial* dry-run response.

    It satisfies SOME required tokens (the function-name-shaped ones) and
    avoids forbidden tokens, so dry-run pass-rate is non-zero but not
    100%. That gives the harness a meaningful signal during smoke tests.
    """
    required = [str(t) for t in (prompt.get("required") or [])]
    # Take the first half of required tokens; leave the rest missing.
    half = required[: max(1, len(required) // 2)]
    body_chunks = [
        f"# stub response from generator '{label}'",
        "# emitted by --dry-run; not a real model output",
    ]
    body_chunks.extend(half)
    return "\n".join(body_chunks)


def make_dry_run_generator(label: str) -> Callable[[dict], str]:
    def _gen(prompt: dict) -> str:
        return _stub_response(prompt, label)

    return _gen


def make_schrodinger_generator_local(
    model_id: str = DEFAULT_SCHRODINGER, max_new_tokens: int = 320
) -> Callable[[dict], str]:
    """Lazy-loaded Schrödinger code-wave generator (logit-space evolution)."""
    from scripts.eval.schrodinger_codewave_generator import (  # noqa: WPS433
        make_schrodinger_generator,
    )

    return make_schrodinger_generator(model_id=model_id, max_new_tokens=max_new_tokens)


def make_ar_generator(model_id: str, max_new_tokens: int = 320) -> Callable[[dict], str]:
    """Lazy-loaded HF causal-LM generator.

    Imports torch + transformers only when called, so dry-run + tests
    don't pay the import cost.
    """

    state: dict = {}

    def _ensure_loaded() -> None:
        if state:
            return
        import torch  # noqa: WPS433 (lazy by design)
        from transformers import AutoModelForCausalLM, AutoTokenizer

        tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        if tok.pad_token_id is None:
            tok.pad_token_id = tok.eos_token_id
        dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=dtype,
            trust_remote_code=True,
        )
        model.eval()
        if torch.cuda.is_available():
            model = model.to("cuda")
        state["torch"] = torch
        state["tok"] = tok
        state["model"] = model

    def _gen(prompt: dict) -> str:
        _ensure_loaded()
        torch = state["torch"]
        tok = state["tok"]
        model = state["model"]
        text = (prompt.get("prompt") or "").strip()
        messages = [{"role": "user", "content": text}]
        try:
            enc = tok.apply_chat_template(messages, return_tensors="pt", add_generation_prompt=True)
        except Exception:
            enc = tok(text, return_tensors="pt").input_ids
        # Newer transformers may return a BatchEncoding here; unwrap to a tensor.
        if hasattr(enc, "input_ids") and not hasattr(enc, "shape"):
            enc = enc.input_ids
        if torch.cuda.is_available():
            enc = enc.to("cuda")
        with torch.inference_mode():
            out = model.generate(
                enc,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                temperature=1.0,
                pad_token_id=tok.pad_token_id,
            )
        new_tokens = out[0, enc.shape[1] :]
        return tok.decode(new_tokens, skip_special_tokens=True)

    return _gen


def make_diffusion_generator(model_id: str, max_new_tokens: int = 320, num_steps: int = 64) -> Callable[[dict], str]:
    """Lazy-loaded diffusion-LM generator.

    DiffuCoder-style models expose `generate(...)` with `num_inference_steps`.
    If the model doesn't ship that signature, we fall back to a plain
    `generate` call so the bake-off still produces a comparable output.
    """

    state: dict = {}

    def _ensure_loaded() -> None:
        if state:
            return
        import torch
        from transformers import AutoModel, AutoTokenizer

        tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        if tok.pad_token_id is None:
            tok.pad_token_id = tok.eos_token_id
        dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
        model = AutoModel.from_pretrained(model_id, torch_dtype=dtype, trust_remote_code=True)
        model.eval()
        if torch.cuda.is_available():
            model = model.to("cuda")
        state["torch"] = torch
        state["tok"] = tok
        state["model"] = model

    def _gen(prompt: dict) -> str:
        _ensure_loaded()
        torch = state["torch"]
        tok = state["tok"]
        model = state["model"]
        text = (prompt.get("prompt") or "").strip()
        messages = [{"role": "user", "content": text}]
        try:
            enc = tok.apply_chat_template(messages, return_tensors="pt", add_generation_prompt=True)
        except Exception:
            enc = tok(text, return_tensors="pt").input_ids
        if torch.cuda.is_available():
            enc = enc.to("cuda")
        gen_kwargs: dict[str, Any] = {
            "max_new_tokens": max_new_tokens,
            "pad_token_id": tok.pad_token_id,
        }
        # DiffuCoder-style hyperparameters; `generate` ignores unknown kwargs
        # on stricter models, in which case we retry without them.
        attempt_kwargs = dict(gen_kwargs, num_inference_steps=num_steps, do_sample=False)
        with torch.inference_mode():
            try:
                out = model.generate(enc, **attempt_kwargs)
            except TypeError:
                out = model.generate(enc, **gen_kwargs)
        new_tokens = out[0, enc.shape[1] :] if out.dim() > 1 else out
        return tok.decode(new_tokens, skip_special_tokens=True)

    return _gen


# ---------------------------------------------------------------------------
# Bake-off + triangulation
# ---------------------------------------------------------------------------


def run_generator(
    label: str,
    model_id: str,
    prompts: list[dict],
    generator: Callable[[dict], str],
) -> tuple[GeneratorReport, list[dict]]:
    raw_responses: list[dict] = []
    verdicts: list[GateVerdict] = []
    for p in prompts:
        response = generator(p)
        verdict = gate_score(p, response)
        raw_responses.append({"id": p.get("id"), "label": label, "response": response})
        verdicts.append(verdict)
    n_pass = sum(1 for v in verdicts if v.ok)
    return (
        GeneratorReport(
            label=label,
            model_id=model_id,
            n_total=len(prompts),
            n_pass=n_pass,
            pass_rate=(n_pass / len(prompts)) if prompts else 0.0,
            by_prompt=verdicts,
        ),
        raw_responses,
    )


def triangulate(reports: list[GeneratorReport]) -> dict:
    """Per-shape pass counts + per-prompt who-won-who-lost matrix."""
    if not reports:
        return {}
    labels = [r.label for r in reports]
    by_shape: dict[str, dict[str, dict[str, int]]] = {}
    by_prompt: list[dict] = []
    # Index verdicts by prompt id per generator.
    indexed = {r.label: {v.id: v for v in r.by_prompt} for r in reports}
    prompt_ids = [v.id for v in reports[0].by_prompt]
    for pid in prompt_ids:
        verdicts = {lab: indexed[lab].get(pid) for lab in labels}
        shape = next(
            (v.shape for v in verdicts.values() if v is not None and v.shape),
            "unknown",
        )
        bucket = by_shape.setdefault(shape, {lab: {"pass": 0, "fail": 0} for lab in labels})
        for lab in labels:
            v = verdicts[lab]
            key = "pass" if (v is not None and v.ok) else "fail"
            bucket[lab][key] += 1
        winners = [lab for lab in labels if verdicts[lab] is not None and verdicts[lab].ok]
        losers = [lab for lab in labels if verdicts[lab] is not None and not verdicts[lab].ok]
        verdict_class: str
        if not winners:
            verdict_class = "all_fail"
        elif not losers:
            verdict_class = "all_pass"
        else:
            verdict_class = "split"
        by_prompt.append(
            {
                "id": pid,
                "shape": shape,
                "verdicts": {lab: (verdicts[lab].ok if verdicts[lab] else None) for lab in labels},
                "verdict_class": verdict_class,
                "winners": winners,
                "losers": losers,
            }
        )
    # Per-shape deltas: diffusion_pass - ar_pass per shape (when both labels present).
    deltas: dict[str, dict[str, int]] = {}
    if "ar" in labels and "diffusion" in labels:
        for shape, counts in by_shape.items():
            deltas[shape] = {
                "ar_pass": counts["ar"]["pass"],
                "diffusion_pass": counts["diffusion"]["pass"],
                "delta": counts["diffusion"]["pass"] - counts["ar"]["pass"],
            }
    return {"by_shape": by_shape, "by_prompt": by_prompt, "shape_delta": deltas}


def run_bakeoff(
    contract: dict,
    generators: list[tuple[str, str, Callable[[dict], str]]],
) -> tuple[dict, list[dict]]:
    prompts = list(contract.get("prompts") or [])
    reports: list[GeneratorReport] = []
    raw_responses_all: list[dict] = []
    for label, model_id, gen in generators:
        report, raws = run_generator(label, model_id, prompts, gen)
        reports.append(report)
        raw_responses_all.extend(raws)
    triangulation = triangulate(reports)
    return (
        {
            "schema_version": "scbe_diffusion_bakeoff_report_v1",
            "contract_id": contract.get("contract_id"),
            "source_contract": contract.get("source_contract"),
            "n_prompts": len(prompts),
            "generators": [
                {
                    "label": r.label,
                    "model_id": r.model_id,
                    "n_pass": r.n_pass,
                    "n_total": r.n_total,
                    "pass_rate": r.pass_rate,
                    "by_prompt": [asdict(v) for v in r.by_prompt],
                }
                for r in reports
            ],
            "triangulation": triangulation,
        },
        raw_responses_all,
    )


def emit_markdown_report(report: dict, out_path: Path) -> None:
    lines: list[str] = []
    lines.append(f"# Code-Diffusion Bake-Off — {report.get('contract_id')}")
    lines.append("")
    lines.append("## Generator pass-rates")
    lines.append("")
    lines.append("| Generator | Model | Pass | Rate |")
    lines.append("|---|---|---|---|")
    for g in report.get("generators") or []:
        lines.append(f"| {g['label']} | `{g['model_id']}` | {g['n_pass']}/{g['n_total']} | {g['pass_rate']:.3f} |")
    lines.append("")
    tri = report.get("triangulation") or {}
    if tri.get("shape_delta"):
        lines.append("## Per-shape delta (diffusion - AR)")
        lines.append("")
        lines.append("| Shape | AR pass | Diffusion pass | Delta |")
        lines.append("|---|---|---|---|")
        for shape, row in sorted(tri["shape_delta"].items(), key=lambda kv: -kv[1]["delta"]):
            lines.append(f"| {shape} | {row['ar_pass']} | {row['diffusion_pass']} | {row['delta']:+d} |")
        lines.append("")
    if tri.get("by_prompt"):
        lines.append("## Per-prompt verdict-class")
        lines.append("")
        lines.append("| Prompt | Shape | Class | Winners |")
        lines.append("|---|---|---|---|")
        for row in tri["by_prompt"]:
            winners = ", ".join(row.get("winners") or []) or "—"
            lines.append(f"| {row['id']} | {row['shape']} | {row['verdict_class']} | {winners} |")
        lines.append("")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="SCBE Code-Diffusion Bake-Off")
    p.add_argument("--contract", default=str(DEFAULT_CONTRACT), help="Path to bake-off contract JSON.")
    p.add_argument("--baseline-model", default=DEFAULT_BASELINE, help="HF model id for the AR baseline.")
    p.add_argument("--diffusion-model", default=DEFAULT_DIFFUSION, help="HF model id for the diffusion candidate.")
    p.add_argument(
        "--schrodinger-model",
        default=DEFAULT_SCHRODINGER,
        help="HF model id for the Schrödinger code-wave generator (logit-space evolution).",
    )
    p.add_argument("--max-new-tokens", type=int, default=320)
    p.add_argument("--diffusion-steps", type=int, default=64)
    p.add_argument("--dry-run", action="store_true", help="Use stub generators; do not load models.")
    p.add_argument("--baseline-only", action="store_true")
    p.add_argument("--diffusion-only", action="store_true")
    p.add_argument(
        "--schrodinger-only",
        action="store_true",
        help="Run only the Schrödinger code-wave generator (skip AR + diffusion).",
    )
    p.add_argument(
        "--with-schrodinger",
        action="store_true",
        help="Add the Schrödinger generator alongside whichever others run.",
    )
    p.add_argument("--emit-report", action="store_true", help="Also emit the markdown report.")
    p.add_argument("--out-dir", default=str(ARTIFACT_DIR))
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    contract_path = Path(args.contract)
    contract = load_contract(contract_path)

    generators: list[tuple[str, str, Callable[[dict], str]]] = []
    if args.schrodinger_only:
        use_baseline = False
        use_diffusion = False
        use_schrodinger = True
    else:
        use_baseline = not args.diffusion_only
        use_diffusion = not args.baseline_only
        use_schrodinger = bool(args.with_schrodinger)

    if args.dry_run:
        if use_baseline:
            generators.append(("ar", "dry-run::ar", make_dry_run_generator("ar")))
        if use_diffusion:
            generators.append(("diffusion", "dry-run::diffusion", make_dry_run_generator("diffusion")))
        if use_schrodinger:
            generators.append(("schrodinger", "dry-run::schrodinger", make_dry_run_generator("schrodinger")))
    else:
        if use_baseline:
            generators.append(("ar", args.baseline_model, make_ar_generator(args.baseline_model, args.max_new_tokens)))
        if use_diffusion:
            generators.append(
                (
                    "diffusion",
                    args.diffusion_model,
                    make_diffusion_generator(args.diffusion_model, args.max_new_tokens, args.diffusion_steps),
                )
            )
        if use_schrodinger:
            generators.append(
                (
                    "schrodinger",
                    args.schrodinger_model,
                    make_schrodinger_generator_local(args.schrodinger_model, args.max_new_tokens),
                )
            )

    if not generators:
        print("ERROR: no generators selected", file=sys.stderr)
        return 2

    report, raws = run_bakeoff(contract, generators)
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / f"diffusion_bakeoff_{contract.get('contract_id')}_{timestamp}.json"
    raws_path = out_dir / f"diffusion_bakeoff_{contract.get('contract_id')}_{timestamp}.responses.jsonl"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    with raws_path.open("w", encoding="utf-8") as fh:
        for row in raws:
            fh.write(json.dumps(row) + "\n")

    if args.emit_report:
        date = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
        md_path = REPO_ROOT / "docs" / "research" / f"CODE_DIFFUSION_BAKEOFF_{date}.md"
        emit_markdown_report(report, md_path)
        print(f"wrote {md_path}")

    print(f"wrote {json_path}")
    print(f"wrote {raws_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
