"""Crosswalk gate for the research-claim registry: every verified claim must back its repo_action with
real on-disk evidence or an explicit backlog fence -- no green-by-fiat. Imports the real crosswalk and
runs it over the real registry, then proves the gate actually FAILS on a broken/missing evidence pointer.
"""

import copy
import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "eval" / "claim_evidence_crosswalk.py"
REGISTRY_PATH = REPO_ROOT / "config" / "eval" / "aether_research_claim_registry.v1.json"


def load_module():
    spec = importlib.util.spec_from_file_location("_claim_crosswalk_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_registry():
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def test_real_registry_crosswalk_passes():
    mod = load_module()
    ok, rows, problems = mod.check(load_registry(), REPO_ROOT)
    assert ok, "unbacked verified claims: %r" % problems
    assert len(rows) == 7  # the 7 verified claims that carry a repo_action


def test_latent_fusion_is_backlog_not_falsely_green():
    # the registry's own action says coverage cannot be claimed until a regression test exists -> backlog
    mod = load_module()
    rows = {r["claim_id"]: r for r in mod.crosswalk(load_registry(), REPO_ROOT)}
    assert rows["latent_fusion_jailbreak"]["evidence_status"] == "backlog"


def test_terminal_bench_evidence_path_resolves_on_disk():
    mod = load_module()
    rows = {r["claim_id"]: r for r in mod.crosswalk(load_registry(), REPO_ROOT)}
    tb = rows["terminal_bench_2_hard_cli_tasks"]
    assert tb["evidence_status"] == "resolved" and tb["ok"] is True


def test_crosswalk_fails_on_a_bogus_evidence_path():
    mod = load_module()
    reg = copy.deepcopy(load_registry())
    for c in reg["claims"]:
        if c["claim_id"] == "terminal_bench_2_hard_cli_tasks":
            c["evidence"] = {"kind": "script", "path": "scripts/benchmark/DOES_NOT_EXIST.py"}
    ok, rows, problems = mod.check(reg, REPO_ROOT)
    assert ok is False
    assert any(
        p["claim_id"] == "terminal_bench_2_hard_cli_tasks" and p["evidence_status"] == "broken_path" for p in problems
    )


def test_crosswalk_fails_on_missing_evidence_field():
    mod = load_module()
    reg = copy.deepcopy(load_registry())
    for c in reg["claims"]:
        if c["claim_id"] == "latent_fusion_jailbreak":
            c.pop("evidence", None)
    ok, _, problems = mod.check(reg, REPO_ROOT)
    assert ok is False and any(p["claim_id"] == "latent_fusion_jailbreak" for p in problems)
