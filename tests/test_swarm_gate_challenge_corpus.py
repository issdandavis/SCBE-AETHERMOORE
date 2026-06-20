"""Precision/recall test for the OpenClaw assurance gate against a labeled challenge corpus.

The whole continual-assurance pitch rests on a gate (quality_flags + applicability_score in
scripts/system/openclaw_swarm.py) whose precision/recall was never measured. This makes it measurable:
it imports the REAL gate (no reimplementation), runs it over config/eval/swarm_gate_challenge_corpus.v1.json,
and asserts the gate BLOCKS every malicious case (recall == 1.0) and FLAGS no valid case
(block-decision precision == 1.0). Promotion requires score >= 90 AND zero flags, so any flag blocks.
Offline: no Ollama, no network, no git worktree.
"""

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "scripts" / "system" / "openclaw_swarm.py"
CORPUS_PATH = REPO_ROOT / "config" / "eval" / "swarm_gate_challenge_corpus.v1.json"
PROMOTION_THRESHOLD = 90


def load_module():
    spec = importlib.util.spec_from_file_location("_openclaw_swarm_gate_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_corpus():
    data = json.loads(CORPUS_PATH.read_text(encoding="utf-8"))
    assert data["schema"] == "swarm_gate_challenge_corpus_v1"
    return data["cases"]


def _run_gate(module, case):
    flags = module.quality_flags(
        case["text"],
        tuple(case["scopes"]),
        require_paths=case.get("require_paths", True),
        check_paths=case.get("check_paths", True),
    )
    score = module.applicability_score(flags)
    promotable = score >= PROMOTION_THRESHOLD and not flags  # the gate's own promotion rule
    return flags, score, promotable


def test_corpus_is_balanced_and_nontrivial():
    cases = load_corpus()
    mal = [c for c in cases if c["label"] == "malicious"]
    val = [c for c in cases if c["label"] == "valid"]
    assert len(mal) >= 5 and len(val) >= 5, "need a real both-sided corpus, not a one-sided one"
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids)), "case ids must be unique"


def test_every_malicious_case_is_blocked():
    module = load_module()
    for case in (c for c in load_corpus() if c["label"] == "malicious"):
        flags, score, promotable = _run_gate(module, case)
        assert flags, "%s: a malicious case must raise >=1 quality flag" % case["id"]
        assert not promotable, "%s: a malicious case must NOT be promotable" % case["id"]
        assert score < PROMOTION_THRESHOLD, "%s: malicious score %d should be < %d" % (
            case["id"],
            score,
            PROMOTION_THRESHOLD,
        )
        for expected in case.get("expect_flags_include", []):
            assert any(f.split(":", 1)[0] == expected for f in flags), "%s: expected flag %r, got %r" % (
                case["id"],
                expected,
                flags,
            )


def test_no_valid_case_is_flagged():
    module = load_module()
    for case in (c for c in load_corpus() if c["label"] == "valid"):
        flags, score, promotable = _run_gate(module, case)
        assert flags == [], "%s: a valid case must raise zero flags, got %r" % (case["id"], flags)
        assert promotable and score >= PROMOTION_THRESHOLD, "%s: a valid case must be promotable" % case["id"]


def test_gate_precision_and_recall_are_perfect_on_the_corpus():
    module = load_module()
    cases = load_corpus()
    malicious = [c for c in cases if c["label"] == "malicious"]
    blocked_malicious = [c for c in malicious if _run_gate(module, c)[0]]  # raised >=1 flag
    flagged_valid = [c for c in cases if c["label"] == "valid" and _run_gate(module, c)[0]]
    recall = len(blocked_malicious) / len(malicious)
    precision = len(blocked_malicious) / (len(blocked_malicious) + len(flagged_valid))
    assert recall == 1.0, "malicious recall must be 1.0, got %.3f" % recall
    assert precision == 1.0, "block-decision precision must be 1.0 (a valid case was flagged)"
