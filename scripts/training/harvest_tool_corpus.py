#!/usr/bin/env python3
"""Build the verified TOOL-USE corpus: run the local 1.5B through the ReAct tool loop over real MBPP
problems and keep ONLY trajectories whose final answer passes HELD-BACK tests AND that actually called
a tool. The kept transcripts (system + real-problem turns, few-shot demo stripped) are SFT records that
teach the call->use->answer ORCHESTRATION loop -- the learnable, non-saturated skill, after plain
final-code SFT measured ~0 lift on a likely-pretrained benchmark.

This is a thin runner around python.helm.tool_trajectory: it mirrors harvest_tool_traces' keep
condition (verified AND used_tool) but writes each kept record the moment it is found, so a long run
preserves partial progress and emits a live log. Output goes to training/sft_records/ (gitignored).

    # default: 200 MBPP problems through qwen2.5-coder:1.5b on local ollama
    python scripts/training/harvest_tool_corpus.py
    python scripts/training/harvest_tool_corpus.py --problems 50 --model qwen2.5-coder:3b

Needs ollama serving the model (SCBE_LLM_BASE / SCBE_LLM_KEY override the endpoint). $0; CPU/GPU local.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from python.helm.public_bench import pull_mbpp  # noqa: E402
from python.helm.tool_trajectory import ollama_ask, solve_with_tools  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="harvest verified tool-use trajectories from MBPP")
    ap.add_argument("--problems", type=int, default=200, help="how many usable MBPP problems to attempt")
    ap.add_argument("--model", default="qwen2.5-coder:1.5b", help="ollama model tag")
    ap.add_argument("--public-k", type=int, default=1, help="tests shown to the model; the rest are held back")
    ap.add_argument("--max-steps", type=int, default=5, help="max tool-dialogue turns per problem")
    ap.add_argument(
        "--prompt-mode",
        choices=["confirm", "repair-biased"],
        default="confirm",
        help="confirm keeps the original prompt; repair-biased asks for quick test -> feedback -> repair loops",
    )
    ap.add_argument(
        "--out",
        default=str(REPO / "training" / "sft_records" / "tool_trajectory_mbpp.jsonl"),
        help="output corpus path (gitignored)",
    )
    ap.add_argument("--require-tool-use", action="store_true", default=True)
    args = ap.parse_args(argv)

    # MBPP problems need >=2 tests so there is at least one HELD-BACK test after showing public_k.
    pool = [p for p in pull_mbpp() if len(p.get("test_list", [])) > args.public_k]
    problems = pool[: args.problems]
    print("MBPP usable (>%d tests): %d; attempting %d" % (args.public_k, len(pool), len(problems)), flush=True)

    ask = ollama_ask(args.model)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    attempted = with_tool_use = kept = 0
    t0 = time.time()
    with out_path.open("w", encoding="utf-8") as fh:
        for i, p in enumerate(problems, 1):
            attempted += 1
            try:
                tr = solve_with_tools(
                    p,
                    ask,
                    max_steps=args.max_steps,
                    public_k=args.public_k,
                    prompt_mode=args.prompt_mode,
                )
            except Exception as exc:  # one bad problem must not abort a long run
                print("  [%d/%d] task %s ERROR %s" % (i, len(problems), p.get("task_id"), exc), flush=True)
                continue
            if tr["used_tool"]:
                with_tool_use += 1
            # keep condition mirrors harvest_tool_traces: verified on held-back AND actually used a tool
            if tr["verified"] and (tr["used_tool"] or not args.require_tool_use):
                rec = {
                    "messages": tr["messages"],
                    "meta": {
                        "verified": True,
                        "task_id": p.get("task_id"),
                        "tool_calls": tr["tool_calls"],
                        "tools_used": tr["tools_used"],
                        "prompt_mode": args.prompt_mode,
                        "source": "tool_trajectory",
                    },
                }
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
                fh.flush()
                kept += 1
            if i % 10 == 0 or i == len(problems):
                rate = kept / attempted if attempted else 0.0
                print(
                    "  [%d/%d] kept=%d with_tool_use=%d verified_rate=%.2f (%.0fs)"
                    % (i, len(problems), kept, with_tool_use, rate, time.time() - t0),
                    flush=True,
                )

    print("=" * 64, flush=True)
    print("TOOL-USE CORPUS BUILT", flush=True)
    print("  attempted       : %d" % attempted, flush=True)
    print("  with_tool_use   : %d  (model actually called a tool)" % with_tool_use, flush=True)
    print("  kept (verified) : %d  (held-back tests passed AND used a tool)" % kept, flush=True)
    print("  out             : %s" % out_path, flush=True)

    # freeze: content-hash the corpus so drift before/after training is detectable (same as VTC)
    try:
        from python.helm.freeze_dataset import sha256_file

        if kept:
            print("  sha256          : %s" % sha256_file(out_path), flush=True)
    except Exception as exc:
        print("  (freeze-hash skipped: %s)" % exc, flush=True)
    print("=" * 64, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
