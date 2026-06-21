"""vtc_loop: one command for the VTC training-data + eval loop (validate -> augment -> score).

Ties the toolchain together so the training lane is one step, not five:
  PREP   validate a retry corpus (retry_corpus_validate); if it is teacher-bailout-heavy, rebalance it with
         execution-verified self-repair traces (self_repair_corpus) toward a target self-repair ratio.
  EVAL   score a staged retry-loop run (staged_retry_score) and, against a baseline run, report the
         per-category delta (newly_repaired / regressed) -- the fair-baseline LIFT, not a raw score.

    python -m python.helm.vtc_loop prep --corpus retry.jsonl --pool vtc_fixture.jsonl --out balanced.jsonl
    python -m python.helm.vtc_loop eval --run staged.jsonl --baseline prev.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import retry_corpus_validate as rcv
from . import self_repair_corpus as src
from . import staged_retry_score as srs


def prepare(
    corpus: Sequence[Dict[str, Any]], pool: Sequence[Dict[str, Any]], target: float = 0.4
) -> Tuple[List[Dict], Dict]:
    """Validate the corpus; if it teaches teacher-dependence, rebalance with verified self-repair traces.
    Returns (corpus_out, report). corpus_out == corpus when no rebalancing was needed."""
    before = rcv.validate(corpus)
    if not before["teacher_dependence_warning"]:
        return list(corpus), {"validation": before, "augmented": False, "aug": None}
    verified_pool = src.verified_pool_from_vtc(pool)
    new, aug = src.augment(corpus, verified_pool, target)
    return new, {"validation": before, "augmented": True, "aug": aug, "after": rcv.validate(new)}


def evaluate(run: Sequence[Dict[str, Any]], baseline: Optional[Sequence[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Score a staged run; add the per-category delta vs a baseline when one is given."""
    return {"score": srs.score(run), "delta": srs.delta(baseline, run) if baseline is not None else None}


def _load(path: str) -> List[Dict]:
    return [json.loads(ln) for ln in Path(path).read_text(encoding="utf-8").splitlines() if ln.strip()]


def _write(path: str, records: Sequence[Dict]) -> None:
    Path(path).write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")


def _cmd_prep(a: argparse.Namespace) -> int:
    corpus_out, report = prepare(_load(a.corpus), _load(a.pool), a.target)
    print(rcv.render(report["validation"]))
    if report["augmented"]:
        aug = report["aug"]
        print(
            "\n  REBALANCED with verified self-repair: %.3f -> %.3f (added %d of %d; %s)"
            % (
                aug["before_self_ratio"],
                aug["after_self_ratio"],
                aug["added"],
                aug["pool_available"],
                "target reached" if aug["reached_target"] else "POOL EXHAUSTED",
            )
        )
    else:
        print("\n  no rebalancing needed (corpus is not teacher-dependence-heavy).")
    if a.out:
        _write(a.out, corpus_out)
        print("  wrote %d records -> %s" % (len(corpus_out), a.out))
    return 0


def _cmd_eval(a: argparse.Namespace) -> int:
    run = _load(a.run)
    res = evaluate(run, _load(a.baseline) if a.baseline else None)
    print(srs.render(res["score"], res["delta"]))
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="VTC training-data + eval pipeline (prep | eval)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prep", help="validate + (if needed) rebalance a retry corpus")
    p.add_argument("--corpus", required=True)
    p.add_argument("--pool", required=True, help="verified-solution corpus to synth self-repair traces from")
    p.add_argument("--out", default=None)
    p.add_argument("--target", type=float, default=0.4)
    p.set_defaults(func=_cmd_prep)
    e = sub.add_parser("eval", help="score a staged retry-loop run (+ baseline delta)")
    e.add_argument("--run", required=True)
    e.add_argument("--baseline", default=None)
    e.set_defaults(func=_cmd_eval)
    a = ap.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
