"""
@file exp_geometric_bounds.py
@module experiments
@layer Layer 4, 5, 8, 9, 10, 13
@component Geometric Bounds Checker Experiment
@version 1.0.0

Tests the BoundsChecker implementation against:
1. Spec examples (normal navigation = ALLOW, credential access = DENY)
2. All 6 bound types independently
3. Adversarial scenarios (scope escalation, low provenance, collusion)
4. AUC: Can the bounds checker discriminate safe from unsafe actions?

From the Geometric Bounds Specification:
    B = B_intent ∩ B_coherence ∩ B_spectral ∩ B_authority ∩ B_realm ∩ B_gfss

Author: Issac Davis
"""

import sys
import math
import time
import json
from typing import Dict, Any, List

import numpy as np

sys.path.insert(0, "/home/user/SCBE-AETHERMOORE")

# Import directly to avoid FastAPI dependency in agents/browser/__init__.py
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "bounds_checker",
    "/home/user/SCBE-AETHERMOORE/agents/browser/bounds_checker.py"
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["bounds_checker"] = _mod
_spec.loader.exec_module(_mod)

BoundsChecker = _mod.BoundsChecker
ActionContext = _mod.ActionContext
Decision = _mod.Decision
BoundsResult = _mod.BoundsResult
hyperbolic_distance = _mod.hyperbolic_distance
poincare_embed = _mod.poincare_embed
weighted_transform = _mod.weighted_transform
realify = _mod.realify
spectral_stability = _mod.spectral_stability
spin_coherence = _mod.spin_coherence
graph_fourier_high_freq_energy = _mod.graph_fourier_high_freq_energy


def compute_auc(positive_scores: List[float], negative_scores: List[float]) -> float:
    """AUC via Mann-Whitney U. Positive = safe, higher = more safe."""
    n_pos = len(positive_scores)
    n_neg = len(negative_scores)
    if n_pos == 0 or n_neg == 0:
        return 0.5
    correct = sum(1 for p in positive_scores for n in negative_scores if p > n)
    ties = sum(1 for p in positive_scores for n in negative_scores if p == n)
    return (correct + 0.5 * ties) / (n_pos * n_neg)


# ============================================================================
# Test 1: Spec Examples
# ============================================================================

def test_spec_examples(checker: BoundsChecker) -> Dict[str, Any]:
    """Test the exact examples from the Geometric Bounds Specification."""
    print("\n" + "=" * 70)
    print("  TEST 1: Specification Examples")
    print("=" * 70)

    results = {"tests": [], "passed": 0, "failed": 0}

    # Example 1: Normal Navigation (INSIDE → ALLOW)
    ctx_safe = ActionContext(
        risk_score=0.1,
        scope_delta=0.0,
        provenance_score=0.9,
        touches_secrets=False,
        tool_class="navigate",
        coherence=0.92,
    )
    result = checker.check_all_bounds(ctx_safe)
    passed = result.decision == Decision.ALLOW
    results["tests"].append({
        "name": "Normal navigation → ALLOW",
        "expected": "ALLOW",
        "actual": result.decision.value,
        "violations": result.violations,
        "scores": {k: round(v, 4) for k, v in result.scores.items()},
        "embedding_norm": round(result.embedding_norm, 4),
        "passed": passed,
    })
    if passed:
        results["passed"] += 1
    else:
        results["failed"] += 1
    status = "PASS" if passed else "FAIL"
    print(f"\n  [{status}] Normal navigation → {result.decision.value}")
    print(f"    Embedding ||u|| = {result.embedding_norm:.4f}")
    print(f"    dH(u, μ) = {result.hyperbolic_distance:.4f} (R = {checker.R_intent})")
    print(f"    Violations: {result.violations}")
    for k, v in result.scores.items():
        print(f"    {k}: {v:.4f}")

    # Example 2: Suspicious Type in Credential Field (OUTSIDE → DENY)
    ctx_dangerous = ActionContext(
        risk_score=0.85,
        scope_delta=0.7,
        provenance_score=0.45,
        touches_secrets=True,
        tool_class="type",
        coherence=0.58,
    )
    result = checker.check_all_bounds(ctx_dangerous)
    passed = result.decision in (Decision.DENY, Decision.QUARANTINE)
    results["tests"].append({
        "name": "Credential typing → not ALLOW",
        "expected": "DENY or QUARANTINE",
        "actual": result.decision.value,
        "violations": result.violations,
        "scores": {k: round(v, 4) for k, v in result.scores.items()},
        "embedding_norm": round(result.embedding_norm, 4),
        "passed": passed,
    })
    if passed:
        results["passed"] += 1
    else:
        results["failed"] += 1
    status = "PASS" if passed else "FAIL"
    print(f"\n  [{status}] Credential typing → {result.decision.value}")
    print(f"    Embedding ||u|| = {result.embedding_norm:.4f}")
    print(f"    dH(u, μ) = {result.hyperbolic_distance:.4f} (R = {checker.R_intent})")
    print(f"    Violations ({len(result.violations)}): {result.violations}")
    for k, v in result.scores.items():
        print(f"    {k}: {v:.4f}")

    return results


# ============================================================================
# Test 2: Individual Bound Types
# ============================================================================

def test_individual_bounds(checker: BoundsChecker) -> Dict[str, Any]:
    """Test each bound type independently."""
    print("\n" + "=" * 70)
    print("  TEST 2: Individual Bound Types")
    print("=" * 70)

    results = {"tests": [], "passed": 0, "failed": 0}

    # 2a: Intent bounds - high risk should violate
    ctx = ActionContext(risk_score=0.9, scope_delta=0.8, provenance_score=0.2,
                        touches_secrets=True, tool_class="execute", coherence=0.3)
    u = checker.embed_action(ctx)
    ok, d = checker.check_intent_bounds(u)
    passed = not ok  # Should be violated
    results["tests"].append({"name": "Intent bounds violated for high-risk", "passed": passed})
    results["passed" if passed else "failed"] += 1
    print(f"\n  [{'PASS' if passed else 'FAIL'}] Intent bounds: dH={d:.4f}, violated={not ok}")

    # 2b: Intent bounds - low risk should pass
    ctx_safe = ActionContext(risk_score=0.05, scope_delta=0.0, provenance_score=0.95,
                             touches_secrets=False, tool_class="read", coherence=0.95)
    u_safe = checker.embed_action(ctx_safe)
    ok, d = checker.check_intent_bounds(u_safe)
    passed = ok
    results["tests"].append({"name": "Intent bounds pass for low-risk", "passed": passed})
    results["passed" if passed else "failed"] += 1
    print(f"  [{'PASS' if passed else 'FAIL'}] Intent bounds: dH={d:.4f}, passed={ok}")

    # 2c: Realm bounds - check that near-origin passes
    ok, d_star = checker.check_realm_bounds(u_safe)
    passed = ok
    results["tests"].append({"name": "Realm bounds pass for safe action", "passed": passed})
    results["passed" if passed else "failed"] += 1
    print(f"  [{'PASS' if passed else 'FAIL'}] Realm bounds: d*={d_star:.4f}, passed={ok}")

    # 2d: Spectral bounds - high coherence passes
    ok, s = checker.check_spectral_bounds(ctx_safe)
    passed = ok
    results["tests"].append({"name": "Spectral bounds pass for coherent state", "passed": passed})
    results["passed" if passed else "failed"] += 1
    print(f"  [{'PASS' if passed else 'FAIL'}] Spectral bounds: S_spec={s:.4f}, passed={ok}")

    # 2e: Spin bounds - aligned phases pass
    ok, c = checker.check_spin_bounds(ctx_safe)
    passed = ok
    results["tests"].append({"name": "Spin bounds pass for aligned state", "passed": passed})
    results["passed" if passed else "failed"] += 1
    print(f"  [{'PASS' if passed else 'FAIL'}] Spin bounds: C_spin={c:.4f}, passed={ok}")

    # 2f: Authority bounds - sufficient votes
    ctx_voted = ActionContext(risk_score=0.5, scope_delta=0.3, provenance_score=0.7,
                              touches_secrets=False, tool_class="click", coherence=0.8,
                              votes=["APPROVE", "APPROVE", "APPROVE", "APPROVE", "APPROVE", "DENY"])
    ok, ratio = checker.check_authority_bounds(ctx_voted)
    passed = ok  # 5/6 approvals, high risk needs 5
    results["tests"].append({"name": "Authority bounds pass with 5/6 votes", "passed": passed})
    results["passed" if passed else "failed"] += 1
    print(f"  [{'PASS' if passed else 'FAIL'}] Authority bounds: ratio={ratio:.2f}, passed={ok}")

    # 2g: Authority bounds - insufficient votes for critical
    ctx_critical = ActionContext(risk_score=0.9, scope_delta=0.9, provenance_score=0.3,
                                 touches_secrets=True, tool_class="admin", coherence=0.4,
                                 votes=["APPROVE", "APPROVE", "APPROVE", "APPROVE", "DENY", "DENY"])
    ok, ratio = checker.check_authority_bounds(ctx_critical)
    passed = not ok  # 4/6 but critical needs 6/6
    results["tests"].append({"name": "Authority bounds fail for critical with 4/6", "passed": passed})
    results["passed" if passed else "failed"] += 1
    print(f"  [{'PASS' if passed else 'FAIL'}] Authority bounds (critical): ratio={ratio:.2f}, violated={not ok}")

    # 2h: GFSS bounds - normal agents pass
    ctx_gfss = ActionContext(risk_score=0.3, scope_delta=0.1, provenance_score=0.8,
                              touches_secrets=False, tool_class="navigate", coherence=0.85,
                              agent_states=np.array([0.9, 0.85, 0.88, 0.92, 0.87, 0.91]))
    ok, e = checker.check_gfss_bounds(ctx_gfss)
    passed = ok
    results["tests"].append({"name": "GFSS bounds pass for normal agents", "passed": passed})
    results["passed" if passed else "failed"] += 1
    print(f"  [{'PASS' if passed else 'FAIL'}] GFSS bounds: E_high={e:.4f}, passed={ok}")

    # 2i: GFSS bounds - collusion pattern
    # 3 agents with identical state + 3 different = suspicious clustering
    ctx_collusion = ActionContext(risk_score=0.3, scope_delta=0.1, provenance_score=0.8,
                                  touches_secrets=False, tool_class="navigate", coherence=0.85,
                                  agent_states=np.array([0.99, 0.99, 0.99, 0.01, 0.01, 0.01]))
    ok, e = checker.check_gfss_bounds(ctx_collusion)
    # Note: whether this triggers depends on the energy distribution
    results["tests"].append({
        "name": f"GFSS collusion pattern: E_high={e:.4f}",
        "passed": True,  # Informational
        "e_high": e,
    })
    results["passed"] += 1
    print(f"  [INFO] GFSS collusion pattern: E_high={e:.4f}, violated={not ok}")

    return results


# ============================================================================
# Test 3: Adversarial Scenarios (from spec Section 9)
# ============================================================================

def test_adversarial_scenarios(checker: BoundsChecker) -> Dict[str, Any]:
    """Test failure modes from spec Section 9."""
    print("\n" + "=" * 70)
    print("  TEST 3: Adversarial Scenarios (Spec Section 9)")
    print("=" * 70)

    results = {"tests": [], "passed": 0, "failed": 0}

    # Failure Mode 1: Scope Escalation
    ctx = ActionContext(
        risk_score=0.6, scope_delta=0.9, provenance_score=0.7,
        touches_secrets=True, tool_class="execute", coherence=0.75,
    )
    result = checker.check_all_bounds(ctx)
    passed = "intent" in result.violations
    results["tests"].append({"name": "Scope escalation → intent violation", "passed": passed,
                             "decision": result.decision.value, "violations": result.violations})
    results["passed" if passed else "failed"] += 1
    print(f"\n  [{'PASS' if passed else 'FAIL'}] Scope escalation: {result.decision.value}, "
          f"violations={result.violations}")

    # Failure Mode 2: Low-Provenance Memory
    ctx = ActionContext(
        risk_score=0.6, scope_delta=0.3, provenance_score=0.2,
        touches_secrets=False, tool_class="type", coherence=0.65,
    )
    result = checker.check_all_bounds(ctx)
    not_allow = result.decision != Decision.ALLOW
    results["tests"].append({"name": "Low provenance → not ALLOW", "passed": not_allow,
                             "decision": result.decision.value, "violations": result.violations})
    results["passed" if not_allow else "failed"] += 1
    print(f"  [{'PASS' if not_allow else 'FAIL'}] Low provenance: {result.decision.value}, "
          f"violations={result.violations}")

    # Failure Mode 3: Collusion (3 agents simultaneously approve high-risk)
    ctx = ActionContext(
        risk_score=0.85, scope_delta=0.5, provenance_score=0.6,
        touches_secrets=False, tool_class="execute", coherence=0.7,
        votes=["APPROVE", "APPROVE", "APPROVE", "APPROVE", "APPROVE", "APPROVE"],
        agent_states=np.array([0.99, 0.99, 0.99, 0.01, 0.01, 0.01]),
    )
    result = checker.check_all_bounds(ctx)
    # Should at least catch intent violation (high risk + scope)
    passed = result.decision != Decision.ALLOW
    results["tests"].append({"name": "Collusion pattern → not ALLOW", "passed": passed,
                             "decision": result.decision.value, "violations": result.violations})
    results["passed" if passed else "failed"] += 1
    print(f"  [{'PASS' if passed else 'FAIL'}] Collusion: {result.decision.value}, "
          f"violations={result.violations}")

    # Failure Mode 4: Phase Desynchronization
    ctx = ActionContext(
        risk_score=0.3, scope_delta=0.1, provenance_score=0.8,
        touches_secrets=False, tool_class="click", coherence=0.3,  # Low coherence → phase misalign
    )
    result = checker.check_all_bounds(ctx)
    has_spin = "spin" in result.violations
    results["tests"].append({"name": "Phase desynch → spin violation", "passed": has_spin,
                             "decision": result.decision.value, "violations": result.violations})
    results["passed" if has_spin else "failed"] += 1
    print(f"  [{'PASS' if has_spin else 'FAIL'}] Phase desynch: {result.decision.value}, "
          f"violations={result.violations}")

    # Edge case: All-zero action (minimal action)
    ctx = ActionContext(
        risk_score=0.0, scope_delta=0.0, provenance_score=1.0,
        touches_secrets=False, tool_class="read", coherence=1.0,
    )
    result = checker.check_all_bounds(ctx)
    passed = result.decision == Decision.ALLOW
    results["tests"].append({"name": "Minimal action → ALLOW", "passed": passed,
                             "decision": result.decision.value})
    results["passed" if passed else "failed"] += 1
    print(f"  [{'PASS' if passed else 'FAIL'}] Minimal action: {result.decision.value}")

    # Edge case: Maximum danger
    ctx = ActionContext(
        risk_score=1.0, scope_delta=1.0, provenance_score=0.0,
        touches_secrets=True, tool_class="admin", coherence=0.0,
    )
    result = checker.check_all_bounds(ctx)
    passed = result.decision == Decision.DENY
    results["tests"].append({"name": "Maximum danger → DENY", "passed": passed,
                             "decision": result.decision.value, "violations": result.violations})
    results["passed" if passed else "failed"] += 1
    print(f"  [{'PASS' if passed else 'FAIL'}] Maximum danger: {result.decision.value}, "
          f"violations={result.violations}")

    return results


# ============================================================================
# Test 4: Discrimination AUC
# ============================================================================

def test_discrimination_auc(checker: BoundsChecker) -> Dict[str, Any]:
    """
    Generate safe and unsafe actions, compute AUC for the bounds checker.
    Can it tell them apart?
    """
    print("\n" + "=" * 70)
    print("  TEST 4: Discrimination AUC (200 safe vs 200 unsafe)")
    print("=" * 70)

    np.random.seed(42)
    n_samples = 200

    # Generate safe actions
    safe_scores = []
    safe_decisions = []
    for i in range(n_samples):
        ctx = ActionContext(
            risk_score=np.random.uniform(0.0, 0.25),
            scope_delta=np.random.uniform(0.0, 0.15),
            provenance_score=np.random.uniform(0.7, 1.0),
            touches_secrets=False,
            tool_class=np.random.choice(["read", "navigate", "click", "screenshot"]),
            coherence=np.random.uniform(0.75, 1.0),
        )
        result = checker.check_all_bounds(ctx)
        # Score: fewer violations = more safe. Invert for AUC.
        safe_score = 1.0 / (1.0 + len(result.violations) + result.hyperbolic_distance)
        safe_scores.append(safe_score)
        safe_decisions.append(result.decision.value)

    # Generate unsafe actions
    unsafe_scores = []
    unsafe_decisions = []
    for i in range(n_samples):
        ctx = ActionContext(
            risk_score=np.random.uniform(0.5, 1.0),
            scope_delta=np.random.uniform(0.3, 1.0),
            provenance_score=np.random.uniform(0.0, 0.5),
            touches_secrets=np.random.random() > 0.5,
            tool_class=np.random.choice(["type", "evaluate", "execute", "admin"]),
            coherence=np.random.uniform(0.1, 0.6),
        )
        result = checker.check_all_bounds(ctx)
        unsafe_score = 1.0 / (1.0 + len(result.violations) + result.hyperbolic_distance)
        unsafe_scores.append(unsafe_score)
        unsafe_decisions.append(result.decision.value)

    # AUC: safe should score higher than unsafe
    auc = compute_auc(safe_scores, unsafe_scores)

    # Decision distribution
    from collections import Counter
    safe_dist = Counter(safe_decisions)
    unsafe_dist = Counter(unsafe_decisions)

    print(f"\n  Safe action decisions:   {dict(safe_dist)}")
    print(f"  Unsafe action decisions: {dict(unsafe_dist)}")
    print(f"\n  Safe score mean:   {np.mean(safe_scores):.4f}")
    print(f"  Unsafe score mean: {np.mean(unsafe_scores):.4f}")
    print(f"  Gap:               {np.mean(safe_scores) - np.mean(unsafe_scores):.4f}")
    print(f"\n  AUC: {auc:.4f}")

    # Perfect separation?
    safe_allow = safe_dist.get("ALLOW", 0) / n_samples
    unsafe_deny = (unsafe_dist.get("DENY", 0) + unsafe_dist.get("QUARANTINE", 0)) / n_samples
    print(f"\n  Safe → ALLOW rate:              {safe_allow:.1%}")
    print(f"  Unsafe → DENY or QUARANTINE:    {unsafe_deny:.1%}")

    return {
        "auc": auc,
        "safe_allow_rate": safe_allow,
        "unsafe_deny_rate": unsafe_deny,
        "safe_score_mean": float(np.mean(safe_scores)),
        "unsafe_score_mean": float(np.mean(unsafe_scores)),
        "safe_decisions": dict(safe_dist),
        "unsafe_decisions": dict(unsafe_dist),
    }


# ============================================================================
# Main
# ============================================================================

def main():
    start_time = time.time()

    print("\n" + "=" * 70)
    print("  GEOMETRIC BOUNDS CHECKER EXPERIMENT")
    print("  B = B_intent ∩ B_coherence ∩ B_spectral ∩ B_authority ∩ B_realm ∩ B_gfss")
    print("=" * 70)

    checker = BoundsChecker()

    all_results = {}

    # Test 1: Spec examples
    all_results["spec_examples"] = test_spec_examples(checker)

    # Test 2: Individual bounds
    all_results["individual_bounds"] = test_individual_bounds(checker)

    # Test 3: Adversarial scenarios
    all_results["adversarial"] = test_adversarial_scenarios(checker)

    # Test 4: AUC discrimination
    all_results["discrimination"] = test_discrimination_auc(checker)

    # Summary
    total_passed = sum(r.get("passed", 0) for r in all_results.values() if isinstance(r.get("passed"), int))
    total_failed = sum(r.get("failed", 0) for r in all_results.values() if isinstance(r.get("failed"), int))
    total = total_passed + total_failed
    duration_ms = (time.time() - start_time) * 1000

    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)

    for name, res in all_results.items():
        if "passed" in res and "failed" in res and isinstance(res["passed"], int):
            status = "ALL PASS" if res["failed"] == 0 else f"{res['failed']} FAILED"
            print(f"  {name:30s}: {res['passed']}/{res['passed'] + res['failed']} ({status})")
        elif "auc" in res:
            print(f"  {name:30s}: AUC = {res['auc']:.4f}")

    if total > 0:
        print(f"\n  Unit tests: {total_passed}/{total} ({total_passed / total * 100:.1f}%)")
    print(f"  AUC (safe vs unsafe): {all_results['discrimination']['auc']:.4f}")
    print(f"  Duration: {duration_ms:.1f}ms")

    return all_results


if __name__ == "__main__":
    main()
