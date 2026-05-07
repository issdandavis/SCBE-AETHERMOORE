# /// script
# dependencies = [
#   "torch>=2.5",
#   "transformers>=4.46",
#   "accelerate>=0.34",
#   "peft>=0.12",
#   "datasets>=2.20",
#   "huggingface_hub",
# ]
# ///
"""HF Jobs entry point: v8-pre Phase 3a-2 retrieval-pivot A/B training run.

Phase 3a (the original A/B run) showed bridge-arm produced equally correct
code with different surface form; the contract measured lexical scaffolding-
marker adherence, not code quality. Phase 3a-2 fixes the measurement: the
contract now demands the model USE a project-specific helper without
redefining it. The bridge memory at eval time is populated with helper
bindings; the LoRA-only arm has no equivalent context.

Trains TWO arms on the COMBINED corpus:

  Arm A (LoRA only):     Qwen2.5-Coder-7B-Instruct + standard LoRA
  Arm B (LoRA + bridge): same + MAHSSAttentionBridge attached to layer 18

Training corpus: mahss_phase3a_corpus.jsonl (41 v6g-style direct-generation
rows) PLUS mahss_retrieval_pivot_corpus.jsonl (24 retrieval-style rows
where the prompt names a helper the bridge memory has bound). The
retrieval rows teach the bridge to attend to memory when the prompt
references a known helper name.

Held-out: the 6 helpers in the eval contract (harmonic_wall, phi_weight,
poincare_distance, tongue_encode, breath_phase, realm_transition) DO
NOT appear in either training corpus. The bridge must transfer the
GENERAL retrieval mechanism to unseen helper names.

After training, both arms evaluate on coding_retrieval_pivot_eval_v1.
Bridge memory at eval is built from the contract's bridge_memory_spec
(role = helper_name, filler = canonical signature summary).

Output: JSON receipt pushed to issdandavis/scbe-eval-results.

Falsifiable prediction: Arm B raw pass rate exceeds Arm A by at least
2/6 prompts on the retrieval-pivot contract. If yes, the bridge does
provide retrieval capability that LoRA alone cannot. If no, retrieval
via this integration does not work at 7B-LoRA scale and the next move
is from-zero or a different routing mechanism.
"""

from __future__ import annotations

import base64
import ast
import hashlib
import json
import math
import os
import sys
from datetime import datetime, timezone

# --- Embedded contract: coding_retrieval_pivot_eval_v2 (signatures hidden, opaque names) ---
EMBEDDED_CONTRACT_JSON = '{"contract_id":"coding_retrieval_pivot_eval_v2","prompts":[{"id":"retrieval_v2_xR_compute","prompt":"Implement `safety(d, p)` using the SCBE helper `xR_compute`. The helper computes a Layer 12 safety score. Do not redefine the helper.","required":["xR_compute(","safety","return","d","p"],"forbidden":["def xR_compute"],"canonical_call_hint":"xR_compute(d, p)  # 2-arg helper"},{"id":"retrieval_v2_vR_resolve","prompt":"Implement `place(x, y)` using the SCBE helper `vR_resolve`. The helper computes a hyperbolic embedding distance. Do not redefine the helper.","required":["vR_resolve(","place","return","x","y"],"forbidden":["def vR_resolve"],"canonical_call_hint":"vR_resolve(x, y)  # 2-arg helper"},{"id":"retrieval_v2_kT_route","prompt":"Implement `pick(token, lang)` using the SCBE helper `kT_route`. The helper routes a token to a Sacred Tongues lane. Do not redefine the helper.","required":["kT_route(","pick","return","token","lang"],"forbidden":["def kT_route"],"canonical_call_hint":"kT_route(token, lang)  # 2-arg helper"},{"id":"retrieval_v2_mF_unbind","prompt":"Implement `lookup(memory, role)` using the SCBE helper `mF_unbind`. The helper unbinds a filler from an HRR memory bundle. Do not redefine the helper.","required":["mF_unbind(","lookup","return","memory","role"],"forbidden":["def mF_unbind"],"canonical_call_hint":"mF_unbind(memory, role)  # 2-arg helper"},{"id":"retrieval_v2_sB_emit","prompt":"Implement `cast(t)` using the SCBE helper `sB_emit`. The helper emits a Layer 6 breathing-cycle phase value. Do not redefine the helper.","required":["sB_emit(","cast","return","t"],"forbidden":["def sB_emit"],"canonical_call_hint":"sB_emit(t)  # 1-arg helper"},{"id":"retrieval_v2_qH_consensus","prompt":"Implement `decide(votes)` using the SCBE helper `qH_consensus`. The helper computes a Layer 13 swarm consensus over agent votes. Do not redefine the helper.","required":["qH_consensus(","decide","return","votes"],"forbidden":["def qH_consensus"],"canonical_call_hint":"qH_consensus(votes)  # 1-arg helper"}],"bridge_memory_spec":{"description":"MAHSS bridge memory at eval is populated with role=opaque_name, filler=canonical signature + semantics summary. Without the bridge, Arm A has only the prompt\'s brief description and must guess the helper\'s argument arity.","bindings":[{"role":"xR_compute","filler":"(d_h: float, pd: float) -> float; Layer 12 safety score; returns 1/(1 + d_h + 2*pd)"},{"role":"vR_resolve","filler":"(u, v) -> float; Layer 5 Poincare hyperbolic distance"},{"role":"kT_route","filler":"(token: str, tongue_code: str) -> int; routes a token to a Sacred Tongues lane"},{"role":"mF_unbind","filler":"(memory: list[float], role: list[float]) -> list[float]; HRR circular-correlation unbind"},{"role":"sB_emit","filler":"(t: float) -> float; Layer 6 breath_phase emission"},{"role":"qH_consensus","filler":"(votes: list[str]) -> str; Layer 13 swarm BFT consensus"}]}}'


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _wilson(passed: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total <= 0:
        return (0.0, 0.0)
    p = passed / total
    z2 = z * z
    denom = 1.0 + z2 / total
    centre = (p + z2 / (2.0 * total)) / denom
    halfwidth = (z * math.sqrt((p * (1.0 - p) / total) + z2 / (4.0 * total * total))) / denom
    return (max(0.0, centre - halfwidth), min(1.0, centre + halfwidth))


def _canonical_call_parts(canonical_call_hint: str | None) -> tuple[str, list[str]] | None:
    if not canonical_call_hint:
        return None
    expr = canonical_call_hint.split("#", 1)[0].strip()
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        return None
    call = tree.body
    if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
        return None
    args = [arg.id for arg in call.args if isinstance(arg, ast.Name)]
    if len(args) != len(call.args):
        return None
    return call.func.id, args


def _has_canonical_call(response: str, canonical_call_hint: str | None) -> bool:
    parts = _canonical_call_parts(canonical_call_hint)
    if parts is None:
        return True
    helper_name, expected_args = parts
    try:
        tree = ast.parse(response)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
            continue
        if node.func.id != helper_name:
            continue
        arg_names = [arg.id for arg in node.args if isinstance(arg, ast.Name)]
        if arg_names == expected_args and len(arg_names) == len(node.args):
            return True
    return False


def score(
    response: str,
    required: list[str],
    forbidden: list[str],
    canonical_call_hint: str | None = None,
) -> tuple[bool, list[str], list[str]]:
    rl = response.lower()
    missing = [r for r in required if r.lower() not in rl]
    triggered = [f for f in forbidden if f.lower() in rl]
    if not _has_canonical_call(response, canonical_call_hint):
        missing.append(f"canonical_call:{canonical_call_hint}")
    return (not missing and not triggered, missing, triggered)


# --- Embedded MAHSS bridge primitives (single-file deployment) ---

import torch
import torch.nn as nn
import torch.nn.functional as F


def circular_correlation_torch(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    # torch.fft.fft does not support bf16/fp16; promote to fp32 for the FFT,
    # then cast back so the bridge stays compatible with bf16 base models.
    orig_dtype = a.dtype
    a32 = a.to(torch.float32)
    b32 = b.to(torch.float32)
    A = torch.fft.fft(a32, dim=-1)
    B = torch.fft.fft(b32, dim=-1)
    out = torch.fft.ifft(torch.conj(A) * B, dim=-1).real
    return out.to(orig_dtype)


def circular_convolution_torch(a: torch.Tensor, b: torch.Tensor) -> torch.Tensor:
    orig_dtype = a.dtype
    a32 = a.to(torch.float32)
    b32 = b.to(torch.float32)
    A = torch.fft.fft(a32, dim=-1)
    B = torch.fft.fft(b32, dim=-1)
    out = torch.fft.ifft(A * B, dim=-1).real
    return out.to(orig_dtype)


def deterministic_role_vector(name: str, dim: int) -> torch.Tensor:
    """Build a stable role/filler vector from an identifier string."""

    chunks: list[float] = []
    counter = 0
    while len(chunks) < dim:
        digest = hashlib.sha256(f"mahss-role:{name}:{counter}".encode("utf-8")).digest()
        chunks.extend((byte / 127.5) - 1.0 for byte in digest)
        counter += 1
    v = torch.tensor(chunks[:dim], dtype=torch.float32)
    return v / v.norm()


class MAHSSAttentionBridge(nn.Module):
    def __init__(self, hidden_dim: int, memory_dim: int, rank: int = 32, gate_init_bias: float = -2.0) -> None:
        super().__init__()
        d, k, r = hidden_dim, memory_dim, rank
        self.W_q_a = nn.Parameter(torch.empty(d, r))
        self.W_q_b = nn.Parameter(torch.empty(r, k))
        self.W_v_a = nn.Parameter(torch.empty(k, r))
        self.W_v_b = nn.Parameter(torch.empty(r, d))
        self.W_g = nn.Parameter(torch.empty(d, d))
        self.b_g = nn.Parameter(torch.empty(d))
        nn.init.kaiming_uniform_(self.W_q_a, a=math.sqrt(5))
        nn.init.zeros_(self.W_q_b)
        nn.init.kaiming_uniform_(self.W_v_a, a=math.sqrt(5))
        nn.init.zeros_(self.W_v_b)
        nn.init.kaiming_uniform_(self.W_g, a=math.sqrt(5))
        nn.init.constant_(self.b_g, gate_init_bias)

    def forward(self, hidden, memory, vocab):
        q = (hidden @ self.W_q_a) @ self.W_q_b
        if memory.shape != q.shape:
            memory = memory.expand_as(q)
        u = circular_correlation_torch(q, memory)
        u_norm = u / (u.norm(dim=-1, keepdim=True) + 1e-9)
        v_norm = vocab / (vocab.norm(dim=-1, keepdim=True) + 1e-9)
        scores = torch.einsum("...k,...vk->...v", u_norm, v_norm)
        attn = F.softmax(scores, dim=-1)
        attended = torch.einsum("...v,...vk->...k", attn, vocab)
        delta = (attended @ self.W_v_a) @ self.W_v_b
        gate = torch.sigmoid(hidden @ self.W_g + self.b_g)
        return hidden + gate * delta, attn


class MahssMemoryRegistry:
    def __init__(self) -> None:
        self.memory = None
        self.vocab = None

    def set_per_batch(self, memory, vocab):
        self.memory = memory
        self.vocab = vocab

    def clear(self):
        self.memory = None
        self.vocab = None


def schema_to_memory_and_vocab(schema: dict, dim: int, device, dtype) -> tuple[torch.Tensor, torch.Tensor]:
    """Build (memory, vocab) tensors for one schema."""

    bindings = []
    fillers_seen: list[tuple[str, str]] = []
    for role, fillers in schema.items():
        for filler in fillers:
            r_vec = deterministic_role_vector(f"role::{role}", dim)
            f_vec = deterministic_role_vector(f"filler::{role}::{filler}", dim)
            bindings.append((r_vec, f_vec))
            fillers_seen.append((role, filler))
    if not bindings:
        # Fallback: zero memory + single zero vocab entry
        memory = torch.zeros(dim, dtype=dtype, device=device)
        vocab = torch.zeros(1, dim, dtype=dtype, device=device)
        return memory, vocab
    memory = torch.zeros(dim, dtype=torch.float32)
    for r, f in bindings:
        memory = memory + circular_convolution_torch(r, f)
    vocab = torch.stack([f for _r, f in bindings])
    return memory.to(device=device, dtype=dtype), vocab.to(device=device, dtype=dtype)


def main() -> int:
    print(f"[{_utc_stamp()}] v8-pre Phase 3a-3 retrieval-v2 A/B starting")

    from peft import LoraConfig, TaskType, get_peft_model
    from transformers import AutoModelForCausalLM, AutoTokenizer

    base_model = os.environ.get("SCBE_BASE_MODEL", "Qwen/Qwen2.5-Coder-7B-Instruct")
    bridge_layer = int(os.environ.get("SCBE_BRIDGE_LAYER", "18"))
    bridge_dim = int(os.environ.get("SCBE_BRIDGE_DIM", "1024"))
    bridge_rank = int(os.environ.get("SCBE_BRIDGE_RANK", "32"))
    n_train_steps = int(os.environ.get("SCBE_N_STEPS", "150"))
    batch_size = int(os.environ.get("SCBE_BATCH", "2"))
    lr = float(os.environ.get("SCBE_LR", "2e-4"))
    max_new_tokens = int(os.environ.get("SCBE_MAX_NEW_TOKENS", "256"))
    result_repo = os.environ.get("SCBE_RESULT_REPO", "issdandavis/scbe-eval-results")
    corpus_repo = os.environ.get("SCBE_TRAIN_DATA_REPO", "issdandavis/scbe-aethermoore-training-data")

    contract = json.loads(EMBEDDED_CONTRACT_JSON)
    prompts = contract["prompts"]

    # Load BOTH corpora: direct-generation (41 rows) + retrieval-pivot (24 rows)
    print(f"  loading corpora from {corpus_repo} ...")
    try:
        from huggingface_hub import hf_hub_download

        corpus = []
        for fname in ("mahss_phase3a_corpus.jsonl", "mahss_retrieval_pivot_corpus.jsonl"):
            p = hf_hub_download(corpus_repo, fname, repo_type="dataset")
            with open(p, "r", encoding="utf-8") as f:
                rows = [json.loads(line) for line in f if line.strip()]
            print(f"    {fname}: {len(rows)} rows")
            corpus.extend(rows)
        print(f"    combined: {len(corpus)} rows")
    except Exception as e:
        print(f"    corpus dataset fetch failed: {e}")
        print(f"    aborting -- both corpora must be uploaded to {corpus_repo} before this job runs")
        return 2

    print(f"  base_model:    {base_model}")
    print(f"  bridge layer:  {bridge_layer}, dim={bridge_dim}, rank={bridge_rank}")
    print(f"  train steps:   {n_train_steps}, batch={batch_size}, lr={lr}")

    tokenizer = AutoTokenizer.from_pretrained(base_model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # ------------------------------------------------------------------
    # Train one arm
    # ------------------------------------------------------------------

    def train_arm(arm_label: str, attach_bridge: bool) -> dict:
        print(f"\n=== Arm: {arm_label} (bridge={attach_bridge}) ===")
        print("  loading base model...")
        model = AutoModelForCausalLM.from_pretrained(
            base_model, torch_dtype=torch.bfloat16, device_map="auto", low_cpu_mem_usage=True,
        )
        # Add LoRA
        lora_cfg = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=16,
            lora_alpha=32,
            lora_dropout=0.05,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        )
        model = get_peft_model(model, lora_cfg)
        model.print_trainable_parameters()

        # Attach bridge if requested
        registry = MahssMemoryRegistry()
        bridge = None
        attachment_handle = None
        if attach_bridge:
            print("  attaching MAHSS bridge...")
            bridge = MAHSSAttentionBridge(
                hidden_dim=model.config.hidden_size,
                memory_dim=bridge_dim,
                rank=bridge_rank,
            )
            first_param = next(model.parameters())
            bridge = bridge.to(device=first_param.device, dtype=first_param.dtype)
            for p in bridge.parameters():
                p.requires_grad_(True)

            def hook(_module, _inputs, output):
                if registry.memory is None:
                    return output
                if isinstance(output, tuple):
                    h = output[0]
                    rest = output[1:]
                else:
                    h = output
                    rest = None
                B, T, _d = h.shape
                m_bt = registry.memory.unsqueeze(1).expand(B, T, registry.memory.shape[-1]).to(dtype=h.dtype, device=h.device)
                v_btvk = registry.vocab.unsqueeze(1).expand(B, T, registry.vocab.shape[1], registry.vocab.shape[-1]).to(dtype=h.dtype, device=h.device)
                h_new, _ = bridge(h, m_bt, v_btvk)
                if rest is None:
                    return h_new
                return (h_new,) + rest

            # Locate decoder layers (Qwen2 uses model.model.layers via PEFT wrapper)
            target_layer = model.base_model.model.model.layers[bridge_layer]
            attachment_handle = target_layer.register_forward_hook(hook)
            n_bridge_params = sum(p.numel() for p in bridge.parameters())
            print(f"  bridge params: {n_bridge_params:,}")

        # Build optimizer over LoRA + bridge params
        train_params = list(filter(lambda p: p.requires_grad, model.parameters()))
        if bridge is not None:
            train_params.extend(bridge.parameters())
        opt = torch.optim.AdamW(train_params, lr=lr)

        # Training loop
        model.train()
        if bridge is not None:
            bridge.train()
        device = next(model.parameters()).device
        dtype = next(model.parameters()).dtype

        rng = torch.Generator().manual_seed(0)
        for step in range(n_train_steps):
            # Sample a mini-batch
            idxs = torch.randperm(len(corpus), generator=rng)[:batch_size].tolist()
            batch = [corpus[i] for i in idxs]
            # Tokenize (full prompt + completion as one sequence; loss on full)
            texts = []
            schemas = []
            for row in batch:
                text = row["prompt"] + "\n\n" + row["completion"]
                texts.append(text)
                schemas.append(row["schema"])
            tokens = tokenizer(texts, return_tensors="pt", padding=True, truncation=True, max_length=512)
            tokens = {k: v.to(device) for k, v in tokens.items()}
            labels = tokens["input_ids"].clone()
            labels[labels == tokenizer.pad_token_id] = -100

            # Set bridge memory if applicable
            if attach_bridge:
                memories = []
                vocabs = []
                for s in schemas:
                    m, v = schema_to_memory_and_vocab(s, bridge_dim, device, dtype)
                    memories.append(m)
                    vocabs.append(v)
                # Pad vocabs to same length for stacking
                max_v = max(v.shape[0] for v in vocabs)
                padded = []
                for v in vocabs:
                    if v.shape[0] < max_v:
                        pad = torch.zeros(max_v - v.shape[0], v.shape[1], device=v.device, dtype=v.dtype)
                        v = torch.cat([v, pad], dim=0)
                    padded.append(v)
                memory_batch = torch.stack(memories)
                vocab_batch = torch.stack(padded)
                registry.set_per_batch(memory_batch, vocab_batch)

            opt.zero_grad()
            out = model(**tokens, labels=labels)
            loss = out.loss
            loss.backward()
            opt.step()
            registry.clear()
            if step % 25 == 0 or step == n_train_steps - 1:
                print(f"    step {step:>4}/{n_train_steps}  loss={loss.item():.4f}")

        # Eval on contract
        print(f"\n  evaluating on contract...")
        model.eval()
        if bridge is not None:
            bridge.eval()
        results = []
        n_pass = 0

        # Pre-compute schemas for eval prompts: extract helper names referenced
        # in the prompt text and build a (role=helper_name, filler=signature)
        # bundle from the contract's bridge_memory_spec.bindings.
        # Schema shape matches the training corpus: {helper_name: [filler_summary]}
        # so the bridge sees the same binding pattern at eval as it did during training.
        helper_fillers: dict[str, str] = {}
        for binding in contract.get("bridge_memory_spec", {}).get("bindings", []):
            helper_fillers[binding["role"]] = binding["filler"]
        for entry in prompts:
            text = entry["prompt"]
            mentioned = [name for name in helper_fillers if name in text]
            schema: dict = {name: [helper_fillers[name]] for name in mentioned}

            messages = [{"role": "user", "content": text}]
            chat_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = tokenizer(chat_text, return_tensors="pt").to(device)

            if attach_bridge and schema:
                m, v = schema_to_memory_and_vocab(schema, bridge_dim, device, dtype)
                registry.set_per_batch(m.unsqueeze(0), v.unsqueeze(0))

            with torch.no_grad():
                out_ids = model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    do_sample=False,
                    temperature=0.0,
                    pad_token_id=tokenizer.eos_token_id,
                )
            response = tokenizer.decode(out_ids[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
            registry.clear()

            ok, missing, triggered = score(
                response,
                entry["required"],
                entry["forbidden"],
                entry.get("canonical_call_hint"),
            )
            results.append({
                "id": entry["id"],
                "ok": ok,
                "missing": missing,
                "triggered": triggered,
                "response_head": response[:400],
            })
            if ok:
                n_pass += 1
            print(f"    [{arm_label}] {entry['id']:<42} ok={ok}  missing={len(missing)}  triggered={len(triggered)}")

        if attachment_handle is not None:
            attachment_handle.remove()
        # Free GPU memory
        del model
        if bridge is not None:
            del bridge
        torch.cuda.empty_cache()

        ci = _wilson(n_pass, len(prompts))
        return {
            "arm": arm_label,
            "n_pass": n_pass,
            "n_total": len(prompts),
            "pass_rate": n_pass / len(prompts),
            "wilson_95_ci": [round(ci[0], 6), round(ci[1], 6)],
            "results": results,
        }

    arm_a = train_arm("lora_only", attach_bridge=False)
    arm_b = train_arm("lora_plus_bridge", attach_bridge=True)

    delta = arm_b["pass_rate"] - arm_a["pass_rate"]

    receipt = {
        "schema": "scbe_mahss_v8_pre_phase3a_3_retrieval_v2_v1",
        "generated_utc": _utc_stamp(),
        "base_model": base_model,
        "contract_id": contract["contract_id"],
        "n_prompts": len(prompts),
        "bridge_config": {
            "layer": bridge_layer,
            "memory_dim": bridge_dim,
            "rank": bridge_rank,
        },
        "training": {
            "n_steps": n_train_steps,
            "batch_size": batch_size,
            "lr": lr,
            "corpus_size": len(corpus),
        },
        "arm_a_lora_only": arm_a,
        "arm_b_lora_plus_bridge": arm_b,
        "lift_b_minus_a": round(delta, 4),
    }

    print()
    print("=" * 78)
    print(f"== Phase 3a-3 retrieval-v2 RESULT ==")
    print(f"  Arm A (LoRA only):     {arm_a['n_pass']:>2}/{arm_a['n_total']:<2}  ({arm_a['pass_rate']:.1%})  CI95 {arm_a['wilson_95_ci']}")
    print(f"  Arm B (LoRA+bridge):   {arm_b['n_pass']:>2}/{arm_b['n_total']:<2}  ({arm_b['pass_rate']:.1%})  CI95 {arm_b['wilson_95_ci']}")
    print(f"  Lift (B-A):            {delta:+.4f}  ({delta*12:+.0f}/12)")
    print("=" * 78)

    try:
        from huggingface_hub import HfApi

        api = HfApi()
        receipt_filename = f"v8_pre_phase3a_3_retrieval_v2_receipt_{_utc_stamp()}.json"
        local = f"/tmp/{receipt_filename}"
        with open(local, "w", encoding="utf-8") as f:
            json.dump(receipt, f, indent=2)
        api.upload_file(
            path_or_fileobj=local,
            path_in_repo=receipt_filename,
            repo_id=result_repo,
            repo_type="dataset",
        )
        print(f"  receipt pushed: {result_repo}/{receipt_filename}")
    except Exception as e:
        print(f"  (push failed: {e}; receipt JSON below)")
        print(json.dumps(receipt, indent=2))

    return 0


if __name__ == "__main__":
    sys.exit(main())
