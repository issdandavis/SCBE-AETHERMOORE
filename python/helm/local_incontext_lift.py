"""local_incontext_lift: a REAL, $0, browser-free measurement of whether the pitfall corpus helps.

The GPU LoRA fine-tune lives in Colab. But the core hypothesis -- "does exposure to the execution-verified
pitfall->fix traces make the model avoid those pitfalls on NEW problems?" -- can be tested locally, today,
with no GPU and no browser, by delivering the data IN CONTEXT instead of in the weights:

    base      = the model, plain prompt
    in-context = the SAME model, prompt prepended with better_corpus pitfall->fix demos

Both are graded by EXECUTION on python.helm.pitfall_eval's held-out headroom problems (a pitfall-maker
fails, a pitfall-avoider passes), via code_lift.measure_code_lift -> the delta is a genuine, falsifiable
number: held-out problems the data-conditioned model solves that the base could not.

HONEST SCOPE: in-context delivery is a PROXY for the LoRA fine-tune, not the same thing -- it shows whether
the data CARRIES the signal, which is the necessary precondition for the fine-tune to work. The weight-level
number is still the Colab run. This is the part that needs no GPU and can be run by anyone.

    python -m python.helm.local_incontext_lift --model Qwen/Qwen2.5-Coder-0.5B-Instruct
"""

from __future__ import annotations

import argparse
import re
from typing import Any, Dict, List

from . import public_bench as pb  # noqa: F401  (kept: import-time sanity that the bench is available)
from .better_corpus import PITFALLS
from .code_lift import measure_code_lift, render
from .pitfall_eval import EVAL, eval_problems

# one pitfall->fix demo per pitfall CLASS that appears in the eval, so the in-context arm sees the class
# (a DIFFERENT instance) before being asked the held-out problem -- generalization, not teaching-to-the-test.
_DEMO_FOR_CLASS = {
    "off_by_one": "off_by_one_range",
    "mutable_default": "mutable_default_arg",
    "int_vs_float": "integer_vs_float_division",
    "modify_while_iter": "modify_list_while_iterating",
    "dict_keyerror": "dict_keyerror_vs_get",
    "empty_index": "empty_string_index",
    "float_equality": "float_equality",
    "shallow_copy": "shallow_copy_nested",
    "stack_invariant": "balanced_parens_no_underflow_check",
    "dp_vs_greedy": "coin_change_max_greedy_fails",
}


def _code_of(text: str) -> str:
    """Extract a python function from a chat completion: prefer a fenced block, else from the first 'def'."""
    m = re.search(r"```(?:python)?\s*(.+?)```", text, re.DOTALL)
    body = m.group(1) if m else text
    i = body.find("def ")
    return (body[i:] if i >= 0 else body).strip()


def _demos() -> str:
    by_name = {p["name"]: p for p in PITFALLS}
    classes = {it["cls"] for it in EVAL}
    blocks: List[str] = []
    for cls in sorted(classes):
        p = by_name.get(_DEMO_FOR_CLASS.get(cls, ""))
        if not p:
            continue
        blocks.append(
            "# Common bug:\n%s\n# Corrected:\n%s" % (p["buggy"], p["fix"])
        )
    head = (
        "Here are common Python bugs and their corrections. Study how each WRONG version fails and learn "
        "to write the corrected form:\n\n"
    )
    return head + "\n\n".join(blocks) + "\n\n"


def make_hf_generators(model_id: str, max_new_tokens: int = 256):
    """Load `model_id` once and return (base_gen, context_gen): identical model + decoding, the only
    difference is whether the prompt is prefixed with the pitfall->fix demos."""
    import torch  # noqa: F401  (transformers needs it; surfaced here if missing)
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForCausalLM.from_pretrained(model_id, torch_dtype="auto")
    model.eval()
    demos = _demos()

    def _ask(user: str) -> str:
        msgs = [{"role": "user", "content": user}]
        text = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
        ids = tok(text, return_tensors="pt").to(model.device)
        out = model.generate(**ids, max_new_tokens=max_new_tokens, do_sample=False, pad_token_id=tok.eos_token_id)
        gen = tok.decode(out[0][ids["input_ids"].shape[1] :], skip_special_tokens=True)
        return _code_of(gen)

    def _prompt(problem: Dict[str, Any]) -> str:
        tests = list(problem.get("test_list", []))
        spec = ("\nIt must pass:\n" + tests[0]) if tests else ""
        return problem["text"] + spec + "\nReturn ONLY the Python function, in a ```python block."

    def base_gen(problem: Dict[str, Any]) -> str:
        return _ask(_prompt(problem))

    def context_gen(problem: Dict[str, Any]) -> str:
        return _ask(demos + _prompt(problem))

    return base_gen, context_gen


def run(model_id: str, public_k: int = 1, max_new_tokens: int = 256) -> Dict[str, Any]:
    probs = eval_problems()
    base_gen, context_gen = make_hf_generators(model_id, max_new_tokens=max_new_tokens)
    return measure_code_lift(base_gen, context_gen, probs, public_k=public_k)


def main(argv: List[str] = None) -> int:
    ap = argparse.ArgumentParser(prog="scbe-local-incontext-lift", description="local $0 in-context pitfall-data lift")
    ap.add_argument("--model", default="Qwen/Qwen2.5-Coder-0.5B-Instruct")
    ap.add_argument("--public-k", type=int, default=1)
    ap.add_argument("--max-new-tokens", type=int, default=256)
    a = ap.parse_args(list(argv) if argv is not None else None)
    print("model: %s   eval: pitfall_eval headroom set   grade: execution (hidden tests)" % a.model)
    rep = run(a.model, public_k=a.public_k, max_new_tokens=a.max_new_tokens)
    print()
    print(render(rep).replace("held-out MBPP", "held-out pitfall_eval"))
    print()
    print("  [in-context proxy for the LoRA fine-tune: data delivered via prompt, not weights]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
