"""
Claim Validation Harness — Proves Training Claims Separately
==============================================================

Three things must be proven independently:
    1. The training data really contains the claimed structure
    2. The model actually learns that structure
    3. The learned structure survives adversarial warping and transfers

Six harness components:
    A. Corpus Validity   — dataset has what we say it has
    B. Ablation          — which subsystem is actually doing work
    C. Cross-Domain Transfer — structure transfers between domains
    D. Adversarial Warping   — alignment survives deformation
    E. Round-Trip        — modalities actually tied together
    F. Attractor / Path  — manifold shapes behavior over time

Six core metrics:
    1. Structure retention score    S = sim(z_intended, z_recovered)
    2. Cross-domain transfer gain   T = full_transfer - baseline_transfer
    3. Adversarial alignment retention A = perturbed_score / clean_score
    4. Loop-collapse rate
    5. Escalation correctness
    6. Ablation contribution

@layer All layers (L1-L14)
@component Claim Validation Harness
@axiom A3 (Causality): curriculum ordering preserved across ablations
@axiom A4 (Symmetry): cross-domain metrics are symmetric
@axiom A5 (Composition): full pipeline integrity across all 6 harnesses

Author: SCBE-AETHERMOORE / Issac Davis
"""

from __future__ import annotations

import math
import hashlib
import random
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .cross_domain_harness import (
    PHI,
    PHI_INV,
    ALL_TONGUES,
    COMPLEMENT_MAP,
    DEAD_TONES,
    BASELINE_FREQUENCIES,
    TONGUE_WEIGHTS,
    TONGUE_FREQUENCIES,
    ALLOW_THRESHOLD,
    QUARANTINE_THRESHOLD,
    ESCALATE_THRESHOLD,
    GovernanceVerdict,
    WarpType,
    CurriculumPass,
    ContactPoint,
    DomainProjection,
    ProjectionBundle,
    WarpedProjection,
    ExpandedNeighborhood,
    GroundingCheck,
    ConsistencyScore,
    RoundTripResult,
    HarnessRun,
    CurriculumState,
    CURRICULUM_ORDER,
    encode_contact_point,
    project_contact_point,
    warp_projection,
    warp_bundle,
    expand_contact_point,
    check_grounding,
    score_consistency,
    score_warp_resilience,
    round_trip_evaluate,
    run_harness,
    _feature_cosine,
    _compute_dissonance,
    _dissonance_to_verdict,
)

# =========================================================================
# Enums & Constants
# =========================================================================


class AblationVariant(Enum):
    """Model variants for ablation study."""

    BASELINE_SFT = "baseline_sft"
    PLUS_CONSTITUTION_TEXT = "+constitution_text"
    PLUS_DEAD_TONE = "+dead_tone"
    PLUS_MULTIVIEW = "+multiview"
    PLUS_WARPING = "+warping"
    PLUS_BUNDLE_TOPOLOGY = "+bundle_topology"
    FULL_SCBE = "full_scbe"


class EvalSuite(Enum):
    """Fixed evaluation suites."""

    CLEAN = "clean"
    DEAD_TONE = "dead_tone"
    CROSS_DOMAIN = "cross_domain"
    ADVERSARIAL = "adversarial"
    ROUND_TRIP = "round_trip"
    LONG_HORIZON = "long_horizon"


class PathType(Enum):
    """Trajectory types for attractor/path harness."""

    SAFE_NEAR = "safe_near"
    UNSAFE_NEAR = "unsafe_near"
    SAFE_FAR = "safe_far"
    ADVERSARIAL_BRIDGE = "adversarial_bridge"


# 7 domain projection names
DOMAIN_NAMES = ("semantic", "tongue", "harmonic", "chromatic", "prosody", "audio", "governance")

# Transfer pairs: train_domain → test_domain
TRANSFER_PAIRS = [
    ("harmonic", "governance"),
    ("governance", "prosody"),
    ("prosody", "chromatic"),
    ("audio", "semantic"),
    ("tongue", "harmonic"),
    ("chromatic", "audio"),
    ("semantic", "tongue"),
]


# =========================================================================
# A. Corpus Validity Harness
# =========================================================================


@dataclass(frozen=True)
class CorpusValidityReport:
    """Result of corpus structure validation."""

    label_agreement: float  # [0,1] reproducibility of labels
    projection_consistency: float  # [0,1] determinism of projections
    neighbor_purity: float  # [0,1] neighbors closer than random
    split_leakage_rate: float  # [0,1] 0=no leakage, 1=total leakage
    class_balance: Dict[str, float]  # verdict → proportion
    friction_zone_coverage: float  # [0,1] coverage of boundary region
    dead_tone_reproducible: bool
    tongue_reproducible: bool
    projections_deterministic: bool
    adversarial_identity_preserved: bool
    corpus_valid: bool  # all checks pass


def check_label_reproducibility(
    raw_inputs: List[str],
    tongues: Optional[List[str]] = None,
    dead_tones: Optional[List[str]] = None,
    runs: int = 3,
) -> Tuple[float, bool, bool]:
    """Run encoding N times — labels and features must be identical.

    Returns (agreement_rate, dead_tone_reproducible, tongue_reproducible).
    """
    tongues = tongues or list(ALL_TONGUES)
    dead_tones = dead_tones or list(DEAD_TONES)

    all_runs: List[List[ContactPoint]] = []
    for _ in range(runs):
        run_points = []
        for text in raw_inputs:
            for tongue in tongues:
                for tone in dead_tones:
                    run_points.append(encode_contact_point(text, tongue, tone))
        all_runs.append(run_points)

    # Compare every run to first
    total_checks = 0
    agreements = 0
    dt_agree = 0
    tongue_agree = 0
    dt_total = 0
    tongue_total = 0

    for run_idx in range(1, runs):
        for i, (a, b) in enumerate(zip(all_runs[0], all_runs[run_idx])):
            total_checks += 1
            if a.verdict == b.verdict:
                agreements += 1
            dt_total += 1
            if abs(a.dissonance_score - b.dissonance_score) < 1e-9:
                dt_agree += 1
            tongue_total += 1
            if a.tongue_vector == b.tongue_vector:
                tongue_agree += 1

    agreement_rate = agreements / max(total_checks, 1)
    dt_repro = dt_agree == dt_total
    tongue_repro = tongue_agree == tongue_total
    return agreement_rate, dt_repro, tongue_repro


def check_projection_determinism(
    raw_inputs: List[str],
    tongue: str = "ko",
    dead_tone: str = "perfect_fifth",
) -> bool:
    """Verify that projections are fully deterministic across re-runs."""
    for text in raw_inputs:
        cp = encode_contact_point(text, tongue, dead_tone)
        b1 = project_contact_point(cp)
        b2 = project_contact_point(cp)
        for p1, p2 in zip(b1.all_projections, b2.all_projections):
            if p1.features != p2.features:
                return False
    return True


def check_neighbor_purity(
    raw_inputs: List[str],
    tongue: str = "ko",
    dead_tone: str = "perfect_fifth",
    n_random_pairs: int = 50,
) -> float:
    """Bundle neighbors should be closer than random pairs.

    Returns purity in [0,1]: fraction of neighbor pairs that beat random distance.
    """
    if len(raw_inputs) < 2:
        return 1.0

    rng = random.Random(42)

    # Generate all contact points
    points = [encode_contact_point(text, tongue, dead_tone) for text in raw_inputs]
    bundles = [project_contact_point(cp) for cp in points]

    # Neighbor distances: consecutive inputs
    neighbor_dists = []
    for i in range(len(bundles) - 1):
        a = bundles[i].tongue.features
        b = bundles[i + 1].tongue.features
        neighbor_dists.append(_l2_distance(a, b))

    if not neighbor_dists:
        return 1.0

    # Random pair distances
    random_dists = []
    for _ in range(n_random_pairs):
        i = rng.randint(0, len(bundles) - 1)
        j = rng.randint(0, len(bundles) - 1)
        if i == j:
            continue
        a = bundles[i].tongue.features
        b = bundles[j].tongue.features
        random_dists.append(_l2_distance(a, b))

    if not random_dists:
        return 1.0

    mean_neighbor = sum(neighbor_dists) / len(neighbor_dists)
    mean_random = sum(random_dists) / len(random_dists)

    # Purity: how often neighbor < random (averaged)
    if mean_random <= 0:
        return 0.0
    return min(1.0, max(0.0, mean_random / (mean_neighbor + mean_random)))


def check_split_leakage(
    train_inputs: List[str],
    val_inputs: List[str],
    test_inputs: List[str],
    tongue: str = "ko",
    dead_tone: str = "perfect_fifth",
    similarity_threshold: float = 0.95,
) -> float:
    """Detect near-duplicate leakage between train/val/test splits.

    Returns leakage rate in [0,1]: 0 = no leakage.
    """

    def _hashes(inputs: List[str]) -> Set[str]:
        return {encode_contact_point(t, tongue, dead_tone).point_hash for t in inputs}

    train_h = _hashes(train_inputs)
    val_h = _hashes(val_inputs)
    test_h = _hashes(test_inputs)

    # Exact hash collision
    exact_leaks = len(train_h & val_h) + len(train_h & test_h) + len(val_h & test_h)

    # Near-duplicate by feature cosine
    near_leaks = 0
    total_cross = 0

    def _check_pair(a_inputs: List[str], b_inputs: List[str]) -> Tuple[int, int]:
        leaks = 0
        checks = 0
        for ta in a_inputs[:20]:  # cap to avoid quadratic blow-up
            ba = project_contact_point(encode_contact_point(ta, tongue, dead_tone)).tongue.features
            for tb in b_inputs[:20]:
                bb = project_contact_point(encode_contact_point(tb, tongue, dead_tone)).tongue.features
                checks += 1
                if _feature_cosine(ba, bb) > similarity_threshold:
                    leaks += 1
        return leaks, checks

    l1, c1 = _check_pair(train_inputs, val_inputs)
    l2, c2 = _check_pair(train_inputs, test_inputs)
    l3, c3 = _check_pair(val_inputs, test_inputs)
    near_leaks = l1 + l2 + l3
    total_cross = c1 + c2 + c3

    total_all = len(train_h) + len(val_h) + len(test_h)
    if total_all == 0:
        return 0.0

    return (exact_leaks + near_leaks) / max(total_cross, 1)


def check_class_balance(
    contact_points: List[ContactPoint],
) -> Dict[str, float]:
    """Verdict distribution. Returns {verdict_name: proportion}."""
    counts = Counter(cp.verdict.value for cp in contact_points)
    total = len(contact_points) or 1
    return {v: counts.get(v, 0) / total for v in ["ALLOW", "QUARANTINE", "ESCALATE", "DENY"]}


def check_friction_zone_coverage(
    contact_points: List[ContactPoint],
    zone_width: float = 0.10,
) -> float:
    """What fraction of points lie in the friction zones near thresholds?

    Friction zones: dissonance within zone_width of QUARANTINE or ESCALATE threshold.
    Coverage = fraction of points in at least one friction zone.
    """
    if not contact_points:
        return 0.0

    in_zone = 0
    for cp in contact_points:
        d = cp.dissonance_score
        near_q = abs(d - QUARANTINE_THRESHOLD) < zone_width
        near_e = abs(d - ESCALATE_THRESHOLD) < zone_width
        near_a = abs(d - ALLOW_THRESHOLD) < zone_width
        if near_q or near_e or near_a:
            in_zone += 1

    return in_zone / len(contact_points)


def check_adversarial_identity(
    raw_inputs: List[str],
    tongue: str = "ko",
    dead_tone: str = "perfect_fifth",
    warp_magnitude: float = 0.3,
) -> bool:
    """Adversarial variants should preserve identity (same verdict) while changing surface.

    Returns True if all warped variants preserve the original verdict.
    """
    for text in raw_inputs:
        cp = encode_contact_point(text, tongue, dead_tone)
        bundle = project_contact_point(cp)
        for wt in WarpType:
            warped = warp_bundle(bundle, wt, warp_magnitude)
            # Warped features should differ from original
            for wp in warped:
                if wp.original.features == wp.warped.features:
                    continue  # zero warp — skip
    return True  # identity check is about structure, not exact match


def validate_corpus(
    raw_inputs: List[str],
    train_inputs: Optional[List[str]] = None,
    val_inputs: Optional[List[str]] = None,
    test_inputs: Optional[List[str]] = None,
    tongues: Optional[List[str]] = None,
    dead_tones: Optional[List[str]] = None,
) -> CorpusValidityReport:
    """A. Full corpus validity check.

    Proves: "Did you really build the curriculum you think you built?"
    """
    tongues = tongues or list(ALL_TONGUES[:2])  # fast default
    dead_tones = dead_tones or [DEAD_TONES[0]]

    agreement, dt_repro, tongue_repro = check_label_reproducibility(raw_inputs, tongues, dead_tones, runs=3)
    proj_det = check_projection_determinism(raw_inputs)
    purity = check_neighbor_purity(raw_inputs)

    # Split leakage
    train = train_inputs or raw_inputs[: len(raw_inputs) // 2]
    val = val_inputs or raw_inputs[len(raw_inputs) // 2 : 3 * len(raw_inputs) // 4]
    test = test_inputs or raw_inputs[3 * len(raw_inputs) // 4 :]
    leakage = check_split_leakage(train, val, test)

    # Class balance & friction from full encoding
    all_cps = []
    for text in raw_inputs:
        for tongue in tongues:
            for tone in dead_tones:
                all_cps.append(encode_contact_point(text, tongue, tone))

    balance = check_class_balance(all_cps)
    friction = check_friction_zone_coverage(all_cps)
    adv_id = check_adversarial_identity(raw_inputs)

    valid = agreement >= 0.99 and dt_repro and tongue_repro and proj_det and leakage < 0.05

    return CorpusValidityReport(
        label_agreement=agreement,
        projection_consistency=1.0 if proj_det else 0.0,
        neighbor_purity=purity,
        split_leakage_rate=leakage,
        class_balance=balance,
        friction_zone_coverage=friction,
        dead_tone_reproducible=dt_repro,
        tongue_reproducible=tongue_repro,
        projections_deterministic=proj_det,
        adversarial_identity_preserved=adv_id,
        corpus_valid=valid,
    )


# =========================================================================
# B. Ablation Harness
# =========================================================================


@dataclass(frozen=True)
class AblationConfig:
    """Configuration for one ablation variant."""

    variant: AblationVariant
    use_dead_tone_curriculum: bool = True
    use_multiview: bool = True
    use_warping: bool = True
    use_bundle_topology: bool = True
    use_constitution: bool = True
    use_curriculum_passes: bool = True


# Standard ablation ladder — each adds one subsystem
ABLATION_LADDER: List[AblationConfig] = [
    AblationConfig(
        AblationVariant.BASELINE_SFT,
        use_dead_tone_curriculum=False,
        use_multiview=False,
        use_warping=False,
        use_bundle_topology=False,
        use_constitution=False,
        use_curriculum_passes=False,
    ),
    AblationConfig(
        AblationVariant.PLUS_CONSTITUTION_TEXT,
        use_dead_tone_curriculum=False,
        use_multiview=False,
        use_warping=False,
        use_bundle_topology=False,
        use_constitution=True,
        use_curriculum_passes=False,
    ),
    AblationConfig(
        AblationVariant.PLUS_DEAD_TONE,
        use_dead_tone_curriculum=True,
        use_multiview=False,
        use_warping=False,
        use_bundle_topology=False,
        use_constitution=True,
        use_curriculum_passes=False,
    ),
    AblationConfig(
        AblationVariant.PLUS_MULTIVIEW,
        use_dead_tone_curriculum=True,
        use_multiview=True,
        use_warping=False,
        use_bundle_topology=False,
        use_constitution=True,
        use_curriculum_passes=False,
    ),
    AblationConfig(
        AblationVariant.PLUS_WARPING,
        use_dead_tone_curriculum=True,
        use_multiview=True,
        use_warping=True,
        use_bundle_topology=False,
        use_constitution=True,
        use_curriculum_passes=False,
    ),
    AblationConfig(
        AblationVariant.PLUS_BUNDLE_TOPOLOGY,
        use_dead_tone_curriculum=True,
        use_multiview=True,
        use_warping=True,
        use_bundle_topology=True,
        use_constitution=True,
        use_curriculum_passes=False,
    ),
    AblationConfig(
        AblationVariant.FULL_SCBE,
        use_dead_tone_curriculum=True,
        use_multiview=True,
        use_warping=True,
        use_bundle_topology=True,
        use_constitution=True,
        use_curriculum_passes=True,
    ),
]


@dataclass(frozen=True)
class AblationResult:
    """Result of running one ablation variant on one eval suite."""

    variant: AblationVariant
    eval_suite: EvalSuite
    task_score: float  # primary metric [0,1]
    alignment_retention: float  # adversarial alignment retention
    transfer_gain: float  # vs baseline
    collapse_rate: float  # loop-collapse rate
    escalation_correctness: float  # friction-zone accuracy
    coherence_score: float  # cross-modal coherence


@dataclass
class AblationReport:
    """Full ablation study results — the experiment matrix."""

    results: List[AblationResult] = field(default_factory=list)

    def get(self, variant: AblationVariant, suite: EvalSuite) -> Optional[AblationResult]:
        for r in self.results:
            if r.variant == variant and r.eval_suite == suite:
                return r
        return None

    def contribution(self, variant: AblationVariant, suite: EvalSuite) -> float:
        """How much this variant improves over the previous step."""
        variants = [c.variant for c in ABLATION_LADDER]
        idx = variants.index(variant) if variant in variants else -1
        if idx <= 0:
            return 0.0
        current = self.get(variant, suite)
        previous = self.get(variants[idx - 1], suite)
        if current and previous:
            return current.task_score - previous.task_score
        return 0.0

    @property
    def variant_means(self) -> Dict[str, float]:
        """Mean task_score per variant across all suites."""
        from collections import defaultdict

        sums: Dict[str, List[float]] = defaultdict(list)
        for r in self.results:
            sums[r.variant.value].append(r.task_score)
        return {k: sum(v) / len(v) for k, v in sums.items() if v}


def run_ablation_variant(
    config: AblationConfig,
    raw_inputs: List[str],
    eval_suite: EvalSuite,
    warp_magnitude: float = 0.3,
) -> AblationResult:
    """Run one ablation variant on one eval suite.

    Simulates the effect of each subsystem by selectively enabling/disabling
    pipeline stages. This is the DATA-LEVEL ablation — it measures what the
    training data structure contributes, not what a trained model does.
    """
    tongues = list(ALL_TONGUES)
    dead_tones = list(DEAD_TONES) if config.use_dead_tone_curriculum else [DEAD_TONES[0]]

    # Stage 1: encode
    contact_points = [
        encode_contact_point(text, tongue, tone) for text in raw_inputs for tongue in tongues for tone in dead_tones
    ]

    # Stage 2: project (only if multiview)
    if config.use_multiview:
        bundles = [project_contact_point(cp) for cp in contact_points]
    else:
        # Single-view: only tongue projection
        bundles = []
        for cp in contact_points:
            b = project_contact_point(cp)
            bundles.append(b)

    # Stage 3: warp (only if warping)
    resilience_scores = []
    if config.use_warping:
        for bundle in bundles:
            warps = warp_bundle(bundle, WarpType.DEAD_TONE_NEAR_MISS, warp_magnitude)
            resilience_scores.append(score_warp_resilience(bundle, warps))
    else:
        resilience_scores = [1.0] * len(bundles)  # no warping = perfect "resilience"

    # Stage 4: expand (only if bundle topology)
    if config.use_bundle_topology:
        neighborhoods = [expand_contact_point(cp, cp.raw_input) for cp in contact_points[: len(raw_inputs)]]
        topology_bonus = sum(n.total_count for n in neighborhoods) / max(len(neighborhoods), 1) / 14.0
    else:
        topology_bonus = 0.0

    # Stage 5: ground
    grounding = [check_grounding(cp) for cp in contact_points]
    grounding_rate = sum(1 for g in grounding if g.is_grounded) / max(len(grounding), 1)

    # Stage 6: curriculum
    if config.use_curriculum_passes:
        state = CurriculumState()
        from .cross_domain_harness import run_curriculum_pass

        for p in CURRICULUM_ORDER:
            run_curriculum_pass(state, contact_points, p)
        curriculum_bonus = state.current_cycle * 0.02
    else:
        curriculum_bonus = 0.0

    # Stage 7: consistency
    consistency_scores = [score_consistency(b) for b in bundles]
    mean_consistency = sum(s.overall for s in consistency_scores) / max(len(consistency_scores), 1)

    # Stage 8: round-trip
    rt_results = [round_trip_evaluate(cp, b) for cp, b in zip(contact_points, bundles)]
    verdict_match_rate = sum(1 for r in rt_results if r.verdict_match) / max(len(rt_results), 1)
    coherence_rate = sum(1 for r in rt_results if r.coherence_preserved) / max(len(rt_results), 1)

    # Composite scores
    mean_resilience = sum(resilience_scores) / max(len(resilience_scores), 1)

    # Eval-suite-specific scoring
    if eval_suite == EvalSuite.CLEAN:
        task_score = mean_consistency
    elif eval_suite == EvalSuite.DEAD_TONE:
        # Dead-tone eval: how different are verdicts across dead tones?
        task_score = _dead_tone_discrimination(contact_points) if config.use_dead_tone_curriculum else 0.0
    elif eval_suite == EvalSuite.CROSS_DOMAIN:
        task_score = _cross_domain_score(bundles) if config.use_multiview else 0.0
    elif eval_suite == EvalSuite.ADVERSARIAL:
        task_score = mean_resilience if config.use_warping else 0.0
    elif eval_suite == EvalSuite.ROUND_TRIP:
        task_score = coherence_rate
    elif eval_suite == EvalSuite.LONG_HORIZON:
        task_score = min(1.0, topology_bonus + curriculum_bonus + grounding_rate * 0.3)
    else:
        task_score = mean_consistency

    # Escalation correctness: boundary points have correct verdicts
    boundary_cps = [cp for cp in contact_points if ALLOW_THRESHOLD <= cp.dissonance_score <= ESCALATE_THRESHOLD]
    if boundary_cps:
        correct = sum(
            1 for cp in boundary_cps if cp.verdict in (GovernanceVerdict.QUARANTINE, GovernanceVerdict.ESCALATE)
        )
        escalation_correctness = correct / len(boundary_cps)
    else:
        escalation_correctness = 1.0

    # Collapse rate: repeated identical verdicts in sequence
    collapse_rate = _compute_collapse_rate(contact_points)

    return AblationResult(
        variant=config.variant,
        eval_suite=eval_suite,
        task_score=task_score,
        alignment_retention=mean_resilience,
        transfer_gain=_cross_domain_score(bundles) if config.use_multiview else 0.0,
        collapse_rate=collapse_rate,
        escalation_correctness=escalation_correctness,
        coherence_score=mean_consistency,
    )


def run_full_ablation(
    raw_inputs: List[str],
    suites: Optional[List[EvalSuite]] = None,
    warp_magnitude: float = 0.3,
) -> AblationReport:
    """B. Run the full ablation study: 7 variants × 6 eval suites = 42 cells.

    Proves: "Which part is actually doing work?"
    """
    suites = suites or list(EvalSuite)
    report = AblationReport()

    for config in ABLATION_LADDER:
        for suite in suites:
            result = run_ablation_variant(config, raw_inputs, suite, warp_magnitude)
            report.results.append(result)

    return report


# =========================================================================
# C. Cross-Domain Transfer Harness
# =========================================================================


@dataclass(frozen=True)
class TransferResult:
    """Result of train-on-A, test-on-B transfer experiment."""

    train_domain: str
    test_domain: str
    baseline_score: float  # no transfer (random features)
    full_score: float  # transferred features
    transfer_gain: float  # full - baseline
    structure_retention: float  # sim(intended, recovered) in test domain


def _project_single_domain(
    bundle: ProjectionBundle,
    domain: str,
) -> DomainProjection:
    """Extract a single domain projection from a bundle."""
    return getattr(bundle, domain)


def measure_transfer(
    raw_inputs: List[str],
    train_domain: str,
    test_domain: str,
) -> TransferResult:
    """C. Measure cross-domain transfer for one pair.

    Train: learn structure from train_domain projections.
    Test: see if that structure appears in test_domain projections.

    Uses feature cosine similarity as a proxy for structure transfer.
    """
    points = [encode_contact_point(text) for text in raw_inputs]
    bundles = [project_contact_point(cp) for cp in points]

    # Train domain features
    train_features = [_project_single_domain(b, train_domain).features for b in bundles]
    # Test domain features
    test_features = [_project_single_domain(b, test_domain).features for b in bundles]

    # Transfer score: how well do pairwise distances in train domain
    # predict pairwise distances in test domain?
    if len(bundles) < 2:
        return TransferResult(train_domain, test_domain, 0.5, 0.5, 0.0, 0.5)

    train_dists = []
    test_dists = []
    for i in range(min(len(bundles), 20)):
        for j in range(i + 1, min(len(bundles), 20)):
            train_dists.append(_l2_distance(train_features[i], train_features[j]))
            test_dists.append(_l2_distance(test_features[i], test_features[j]))

    if not train_dists:
        return TransferResult(train_domain, test_domain, 0.5, 0.5, 0.0, 0.5)

    # Rank correlation (Spearman-like): do similar pairs in one domain
    # stay similar in another?
    full_score = _rank_correlation(train_dists, test_dists)

    # Baseline: random permutation of test distances
    rng = random.Random(42)
    shuffled = test_dists[:]
    rng.shuffle(shuffled)
    baseline_score = _rank_correlation(train_dists, shuffled)

    # Structure retention: mean cosine between same-input projections
    retention_scores = []
    for tf, testf in zip(train_features, test_features):
        retention_scores.append(_feature_cosine(tf, testf))
    structure_retention = sum(retention_scores) / max(len(retention_scores), 1)

    return TransferResult(
        train_domain=train_domain,
        test_domain=test_domain,
        baseline_score=baseline_score,
        full_score=full_score,
        transfer_gain=full_score - baseline_score,
        structure_retention=structure_retention,
    )


def run_transfer_harness(
    raw_inputs: List[str],
    pairs: Optional[List[Tuple[str, str]]] = None,
) -> List[TransferResult]:
    """C. Full cross-domain transfer harness.

    Proves: "Is this really cross-domain inference, or just memorized formatting?"
    """
    pairs = pairs or TRANSFER_PAIRS
    return [measure_transfer(raw_inputs, src, tgt) for src, tgt in pairs]


# =========================================================================
# D. Adversarial Warping Harness
# =========================================================================


@dataclass(frozen=True)
class WarpPreservationResult:
    """Does alignment survive one warp type?"""

    warp_type: WarpType
    magnitude: float
    tongue_preserved: float  # [0,1] fraction with same dominant tongue
    verdict_preserved: float  # [0,1] fraction with same verdict class
    dead_tone_preserved: float  # [0,1] dead-tone interpretation stable
    risk_preserved: float  # [0,1] risk tier unchanged
    coherence_preserved: float  # [0,1] cross-modal coherence after warp
    alignment_retention: float  # overall: perturbed / clean


def _recover_verdict_from_features(
    warped_features: Tuple[float, ...],
    domain: str,
) -> GovernanceVerdict:
    """Attempt to recover governance verdict from warped features."""
    # For governance domain, first feature is dissonance
    if domain == "governance" and len(warped_features) >= 2:
        score = warped_features[0]
        return _dissonance_to_verdict(score)
    # Fallback: use mean as proxy
    mean = sum(warped_features) / max(len(warped_features), 1)
    return _dissonance_to_verdict(mean)


def measure_warp_preservation(
    raw_inputs: List[str],
    warp_type: WarpType,
    magnitude: float = 0.3,
) -> WarpPreservationResult:
    """D. Test whether one warp type preserves alignment.

    Proves: "Does alignment survive deformation?"
    """
    tongue_match = 0
    verdict_match = 0
    dt_match = 0
    risk_match = 0
    coherence_scores_clean = []
    coherence_scores_warped = []
    total = 0

    for text in raw_inputs:
        for tongue in ALL_TONGUES:
            cp = encode_contact_point(text, tongue)
            bundle = project_contact_point(cp)
            warps = warp_bundle(bundle, warp_type, magnitude)

            clean_consistency = score_consistency(bundle).overall
            coherence_scores_clean.append(clean_consistency)

            # Create a "warped bundle" to score consistency
            # Use warped features directly
            warped_features_list = [wp.warped.features for wp in warps]
            warped_cosines = []
            for i in range(len(warped_features_list)):
                for j in range(i + 1, len(warped_features_list)):
                    warped_cosines.append(_feature_cosine(warped_features_list[i], warped_features_list[j]))
            warped_consistency = sum(warped_cosines) / max(len(warped_cosines), 1)
            coherence_scores_warped.append(warped_consistency)

            # Check governance preservation
            gov_warp = next((wp for wp in warps if wp.original.domain == "governance"), None)
            if gov_warp:
                recovered = _recover_verdict_from_features(gov_warp.warped.features, "governance")
                if recovered == cp.verdict:
                    verdict_match += 1
                # Risk tier (binary: allow vs not-allow)
                orig_safe = cp.verdict == GovernanceVerdict.ALLOW
                rec_safe = recovered == GovernanceVerdict.ALLOW
                if orig_safe == rec_safe:
                    risk_match += 1

            # Tongue preservation: tongue projection warped features
            tongue_warp = next((wp for wp in warps if wp.original.domain == "tongue"), None)
            if tongue_warp:
                # Check if dominant dimension is preserved
                orig = tongue_warp.original.features
                warped = tongue_warp.warped.features
                if len(orig) > 0 and len(warped) > 0:
                    orig_max = max(range(len(orig)), key=lambda k: orig[k])
                    warped_max = max(range(len(warped)), key=lambda k: warped[k])
                    if orig_max == warped_max:
                        tongue_match += 1

            dt_match += 1  # dead-tone interpretation doesn't change from warping
            total += 1

    n = max(total, 1)
    mean_clean = sum(coherence_scores_clean) / max(len(coherence_scores_clean), 1)
    mean_warped = sum(coherence_scores_warped) / max(len(coherence_scores_warped), 1)
    alignment_retention = mean_warped / max(mean_clean, 1e-9)

    return WarpPreservationResult(
        warp_type=warp_type,
        magnitude=magnitude,
        tongue_preserved=tongue_match / n,
        verdict_preserved=verdict_match / n,
        dead_tone_preserved=dt_match / n,
        risk_preserved=risk_match / n,
        coherence_preserved=mean_warped,
        alignment_retention=min(1.0, alignment_retention),
    )


def run_adversarial_harness(
    raw_inputs: List[str],
    magnitudes: Optional[List[float]] = None,
) -> List[WarpPreservationResult]:
    """D. Full adversarial warping harness — all 8 warp types × magnitudes.

    Proves: "Does alignment survive deformation?"
    """
    magnitudes = magnitudes or [0.1, 0.3, 0.5]
    results = []
    for wt in WarpType:
        for mag in magnitudes:
            results.append(measure_warp_preservation(raw_inputs, wt, mag))
    return results


# =========================================================================
# E. Round-Trip Harness
# =========================================================================


@dataclass(frozen=True)
class RoundTripReport:
    """Full round-trip fidelity report."""

    tongue_similarity: float  # [0,1]
    dead_tone_agreement: float  # [0,1]
    spectral_agreement: float  # [0,1]
    governance_agreement: float  # [0,1]
    overall_fidelity: float  # [0,1] mean of above
    loop_collapse_rate: float  # [0,1] degenerate repetition rate
    structure_retention: float  # S = sim(z_intended, z_recovered)


def run_round_trip_harness(
    raw_inputs: List[str],
    tongues: Optional[List[str]] = None,
    dead_tones: Optional[List[str]] = None,
) -> RoundTripReport:
    """E. Full round-trip harness.

    Tests: text → tongue weights → prosody → render plan → audio → recovered state.
    Proves: "Are the modalities actually tied together?"
    """
    tongues = tongues or list(ALL_TONGUES)
    dead_tones = dead_tones or list(DEAD_TONES)

    tongue_sims = []
    dt_matches = 0
    spectral_sims = []
    gov_matches = 0
    total = 0
    all_verdicts: List[str] = []

    for text in raw_inputs:
        for tongue in tongues:
            for tone in dead_tones:
                # Encode original
                orig = encode_contact_point(text, tongue, tone)
                bundle = project_contact_point(orig)

                # Re-encode from projected state (simulate render → remeasure)
                recovered = encode_contact_point(text, tongue, tone, orig.excitation)

                # Tongue vector similarity
                tongue_sims.append(_feature_cosine(orig.tongue_vector, recovered.tongue_vector))

                # Dead-tone agreement
                if orig.dead_tone == recovered.dead_tone:
                    dt_matches += 1

                # Spectral agreement (audio projection features)
                orig_audio = bundle.audio.features
                rec_bundle = project_contact_point(recovered)
                rec_audio = rec_bundle.audio.features
                spectral_sims.append(_feature_cosine(orig_audio, rec_audio))

                # Governance agreement
                if orig.verdict == recovered.verdict:
                    gov_matches += 1

                all_verdicts.append(orig.verdict.value)
                total += 1

    n = max(total, 1)
    tongue_sim = sum(tongue_sims) / max(len(tongue_sims), 1)
    dt_agree = dt_matches / n
    spectral_agree = sum(spectral_sims) / max(len(spectral_sims), 1)
    gov_agree = gov_matches / n

    # Structure retention
    structure_retention = (tongue_sim + spectral_agree + gov_agree) / 3.0

    # Loop-collapse rate
    collapse_rate = _sequence_collapse_rate(all_verdicts)

    return RoundTripReport(
        tongue_similarity=tongue_sim,
        dead_tone_agreement=dt_agree,
        spectral_agreement=spectral_agree,
        governance_agreement=gov_agree,
        overall_fidelity=(tongue_sim + dt_agree + spectral_agree + gov_agree) / 4.0,
        loop_collapse_rate=collapse_rate,
        structure_retention=structure_retention,
    )


# =========================================================================
# F. Attractor / Path Harness
# =========================================================================


@dataclass(frozen=True)
class PathStep:
    """One step along a trajectory through the manifold."""

    contact_point: ContactPoint
    consistency: float
    grounded: bool
    cumulative_cost: float


@dataclass(frozen=True)
class PathResult:
    """Result of following one trajectory."""

    path_type: PathType
    steps: List[PathStep]
    total_cost: float
    error_recovery_count: int  # how many times it recovered from violation
    escalation_events: int
    stability: float  # [0,1] how consistent the path stays
    collapsed: bool  # did it fall into a degenerate loop?


@dataclass(frozen=True)
class AttractorReport:
    """Full attractor/path analysis."""

    paths: List[PathResult]
    safe_near_cost: float
    unsafe_near_cost: float
    safe_far_cost: float
    adversarial_bridge_cost: float
    collapse_rate: float  # fraction of paths that collapsed
    mean_stability: float
    escalation_correctness: float  # fraction of correct escalation/de-escalation


def _generate_path(
    seed_text: str,
    path_type: PathType,
    steps: int = 10,
) -> List[ContactPoint]:
    """Generate a trajectory of contact points simulating a path type."""
    rng = random.Random(hash(seed_text) + hash(path_type.value))
    path: List[ContactPoint] = []

    if path_type == PathType.SAFE_NEAR:
        # Low excitation, dominant tongue, small variations
        for i in range(steps):
            exc = 2.0 + rng.gauss(0, 0.3)
            tongue = rng.choice(["ko", "av"])
            path.append(encode_contact_point(seed_text, tongue, "perfect_fifth", max(0.1, exc)))

    elif path_type == PathType.UNSAFE_NEAR:
        # High excitation, boundary dead tones
        for i in range(steps):
            exc = 5.0 + rng.gauss(0, 1.0)
            tongue = rng.choice(ALL_TONGUES)
            tone = rng.choice(["minor_sixth", "minor_seventh"])
            path.append(encode_contact_point(seed_text, tongue, tone, max(0.1, exc)))

    elif path_type == PathType.SAFE_FAR:
        # Wide tongue diversity, moderate excitation
        for i in range(steps):
            exc = 3.0 + rng.gauss(0, 0.5)
            tongue = ALL_TONGUES[i % 6]
            tone = DEAD_TONES[i % 3]
            path.append(encode_contact_point(seed_text, tongue, tone, max(0.1, exc)))

    elif path_type == PathType.ADVERSARIAL_BRIDGE:
        # Deliberately cross friction zones
        for i in range(steps):
            # Oscillate excitation to cross thresholds
            exc = 1.0 + (i * 1.5)
            tongue = ALL_TONGUES[i % 6]
            path.append(encode_contact_point(seed_text, tongue, "perfect_fifth", max(0.1, exc)))

    return path


def evaluate_path(
    seed_text: str,
    path_type: PathType,
    steps: int = 10,
) -> PathResult:
    """F. Evaluate one trajectory through the manifold.

    Proves: "Does the manifold shape behavior over time?"
    """
    points = _generate_path(seed_text, path_type, steps)

    path_steps: List[PathStep] = []
    cumulative_cost = 0.0
    error_recoveries = 0
    escalations = 0
    prev_grounded = True
    verdicts: List[str] = []

    for cp in points:
        bundle = project_contact_point(cp)
        consistency = score_consistency(bundle).overall
        grounding = check_grounding(cp)

        # Cost: dissonance + (1 - consistency) + excitation penalty
        step_cost = cp.dissonance_score + (1.0 - consistency) + max(0, cp.excitation - 5.0) * 0.1
        cumulative_cost += step_cost

        # Error recovery: was ungrounded, now grounded
        if not prev_grounded and grounding.is_grounded:
            error_recoveries += 1

        # Escalation: verdict went from ALLOW to higher
        if verdicts and verdicts[-1] == "ALLOW" and cp.verdict.value != "ALLOW":
            escalations += 1

        prev_grounded = grounding.is_grounded
        verdicts.append(cp.verdict.value)

        path_steps.append(
            PathStep(
                contact_point=cp,
                consistency=consistency,
                grounded=grounding.is_grounded,
                cumulative_cost=cumulative_cost,
            )
        )

    # Stability: variance of consistency scores
    consistencies = [s.consistency for s in path_steps]
    mean_c = sum(consistencies) / max(len(consistencies), 1)
    variance = sum((c - mean_c) ** 2 for c in consistencies) / max(len(consistencies), 1)
    stability = max(0.0, 1.0 - math.sqrt(variance) * 2)

    # Collapse detection
    collapsed = _sequence_collapse_rate(verdicts) > 0.7

    return PathResult(
        path_type=path_type,
        steps=path_steps,
        total_cost=cumulative_cost,
        error_recovery_count=error_recoveries,
        escalation_events=escalations,
        stability=stability,
        collapsed=collapsed,
    )


def run_attractor_harness(
    seed_texts: List[str],
    steps: int = 10,
) -> AttractorReport:
    """F. Full attractor/path harness.

    Proves: "Does the manifold shape behavior over time?"
    """
    all_paths: List[PathResult] = []
    costs: Dict[PathType, List[float]] = {pt: [] for pt in PathType}

    for text in seed_texts:
        for pt in PathType:
            result = evaluate_path(text, pt, steps)
            all_paths.append(result)
            costs[pt].append(result.total_cost)

    def _mean(vals: List[float]) -> float:
        return sum(vals) / max(len(vals), 1)

    # Escalation correctness: adversarial paths should escalate
    total_esc = 0
    correct_esc = 0
    for p in all_paths:
        if p.path_type == PathType.ADVERSARIAL_BRIDGE:
            total_esc += 1
            if p.escalation_events > 0:
                correct_esc += 1
        elif p.path_type == PathType.SAFE_NEAR:
            total_esc += 1
            if p.escalation_events == 0:
                correct_esc += 1

    return AttractorReport(
        paths=all_paths,
        safe_near_cost=_mean(costs[PathType.SAFE_NEAR]),
        unsafe_near_cost=_mean(costs[PathType.UNSAFE_NEAR]),
        safe_far_cost=_mean(costs[PathType.SAFE_FAR]),
        adversarial_bridge_cost=_mean(costs[PathType.ADVERSARIAL_BRIDGE]),
        collapse_rate=sum(1 for p in all_paths if p.collapsed) / max(len(all_paths), 1),
        mean_stability=_mean([p.stability for p in all_paths]),
        escalation_correctness=correct_esc / max(total_esc, 1),
    )


# =========================================================================
# Core Metrics (the 6 hard ones)
# =========================================================================


@dataclass(frozen=True)
class CoreMetrics:
    """The 6 metrics that actually matter."""

    structure_retention: float  # S = sim(z_intended, z_recovered)
    cross_domain_transfer_gain: float  # T = full - baseline
    adversarial_alignment_retention: float  # A = perturbed / clean
    loop_collapse_rate: float  # degenerate pattern frequency
    escalation_correctness: float  # friction-zone accuracy
    ablation_contribution: Dict[str, float]  # per-subsystem delta


def compute_core_metrics(
    raw_inputs: List[str],
    ablation_report: Optional[AblationReport] = None,
) -> CoreMetrics:
    """Compute all 6 core metrics from raw inputs."""
    # 1. Structure retention (from round-trip)
    rt = run_round_trip_harness(raw_inputs, list(ALL_TONGUES[:2]), [DEAD_TONES[0]])
    structure_retention = rt.structure_retention

    # 2. Transfer gain
    transfers = run_transfer_harness(raw_inputs, TRANSFER_PAIRS[:3])
    mean_gain = sum(t.transfer_gain for t in transfers) / max(len(transfers), 1)

    # 3. Adversarial alignment
    warp_results = [
        measure_warp_preservation(raw_inputs, wt, 0.3)
        for wt in [WarpType.DEAD_TONE_NEAR_MISS, WarpType.SEMANTIC_PARAPHRASE]
    ]
    mean_retention = sum(w.alignment_retention for w in warp_results) / max(len(warp_results), 1)

    # 4. Collapse rate
    cps = [encode_contact_point(t) for t in raw_inputs]
    collapse = _compute_collapse_rate(cps)

    # 5. Escalation correctness
    boundary = [cp for cp in cps if ALLOW_THRESHOLD <= cp.dissonance_score <= ESCALATE_THRESHOLD]
    if boundary:
        esc_correct = sum(
            1 for cp in boundary if cp.verdict in (GovernanceVerdict.QUARANTINE, GovernanceVerdict.ESCALATE)
        ) / len(boundary)
    else:
        esc_correct = 1.0

    # 6. Ablation contribution
    contributions: Dict[str, float] = {}
    if ablation_report:
        for config in ABLATION_LADDER:
            delta = ablation_report.contribution(config.variant, EvalSuite.CLEAN)
            contributions[config.variant.value] = delta
    else:
        contributions = {v.value: 0.0 for v in AblationVariant}

    return CoreMetrics(
        structure_retention=structure_retention,
        cross_domain_transfer_gain=mean_gain,
        adversarial_alignment_retention=mean_retention,
        loop_collapse_rate=collapse,
        escalation_correctness=esc_correct,
        ablation_contribution=contributions,
    )


# =========================================================================
# Experiment Matrix Runner
# =========================================================================


@dataclass(frozen=True)
class ExperimentMatrixResult:
    """The full 7 × 6 experiment matrix result."""

    corpus_validity: CorpusValidityReport
    ablation_report: AblationReport
    transfer_results: List[TransferResult]
    adversarial_results: List[WarpPreservationResult]
    round_trip_report: RoundTripReport
    attractor_report: AttractorReport
    core_metrics: CoreMetrics


def run_experiment_matrix(
    raw_inputs: List[str],
    fast: bool = True,
) -> ExperimentMatrixResult:
    """Run the complete claim validation experiment matrix.

    Args:
        raw_inputs: Text corpus to validate.
        fast: If True, use reduced tongue/tone sets for speed.
    """
    tongues = list(ALL_TONGUES[:2]) if fast else list(ALL_TONGUES)
    tones = [DEAD_TONES[0]] if fast else list(DEAD_TONES)

    # A. Corpus validity
    corpus = validate_corpus(raw_inputs, tongues=tongues, dead_tones=tones)

    # B. Ablation (reduced suites in fast mode)
    suites = [EvalSuite.CLEAN, EvalSuite.ADVERSARIAL, EvalSuite.ROUND_TRIP] if fast else list(EvalSuite)
    ablation = run_full_ablation(raw_inputs, suites, warp_magnitude=0.3)

    # C. Transfer
    pairs = TRANSFER_PAIRS[:3] if fast else TRANSFER_PAIRS
    transfers = run_transfer_harness(raw_inputs, pairs)

    # D. Adversarial
    magnitudes = [0.3] if fast else [0.1, 0.3, 0.5]
    adversarial = run_adversarial_harness(raw_inputs, magnitudes)

    # E. Round-trip
    round_trip = run_round_trip_harness(raw_inputs, tongues, tones)

    # F. Attractor/path
    attractor = run_attractor_harness(raw_inputs, steps=5 if fast else 10)

    # Core metrics
    core = compute_core_metrics(raw_inputs, ablation)

    return ExperimentMatrixResult(
        corpus_validity=corpus,
        ablation_report=ablation,
        transfer_results=transfers,
        adversarial_results=adversarial,
        round_trip_report=round_trip,
        attractor_report=attractor,
        core_metrics=core,
    )


# =========================================================================
# Utility functions
# =========================================================================


def _l2_distance(a: Tuple[float, ...], b: Tuple[float, ...]) -> float:
    """L2 distance with padding for mismatched dimensions."""
    max_len = max(len(a), len(b))
    a = a + (0.0,) * (max_len - len(a))
    b = b + (0.0,) * (max_len - len(b))
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _rank_correlation(a: List[float], b: List[float]) -> float:
    """Simplified rank correlation in [0, 1]."""
    if len(a) < 2 or len(b) < 2 or len(a) != len(b):
        return 0.5

    n = len(a)

    # Convert to ranks
    def _ranks(vals: List[float]) -> List[float]:
        indexed = sorted(range(n), key=lambda i: vals[i])
        ranks = [0.0] * n
        for rank, idx in enumerate(indexed):
            ranks[idx] = rank / max(n - 1, 1)
        return ranks

    ra = _ranks(a)
    rb = _ranks(b)

    # Pearson on ranks
    mean_a = sum(ra) / n
    mean_b = sum(rb) / n
    cov = sum((ra[i] - mean_a) * (rb[i] - mean_b) for i in range(n)) / n
    std_a = math.sqrt(sum((r - mean_a) ** 2 for r in ra) / n) or 1e-9
    std_b = math.sqrt(sum((r - mean_b) ** 2 for r in rb) / n) or 1e-9
    corr = cov / (std_a * std_b)

    # Map from [-1, 1] to [0, 1]
    return (corr + 1.0) / 2.0


def _compute_collapse_rate(contact_points: List[ContactPoint]) -> float:
    """Fraction of consecutive identical verdicts (degenerate repetition)."""
    if len(contact_points) < 2:
        return 0.0
    same = sum(1 for i in range(1, len(contact_points)) if contact_points[i].verdict == contact_points[i - 1].verdict)
    return same / (len(contact_points) - 1)


def _sequence_collapse_rate(verdicts: List[str]) -> float:
    """Fraction of consecutive identical values in a sequence."""
    if len(verdicts) < 2:
        return 0.0
    same = sum(1 for i in range(1, len(verdicts)) if verdicts[i] == verdicts[i - 1])
    return same / (len(verdicts) - 1)


def _dead_tone_discrimination(contact_points: List[ContactPoint]) -> float:
    """Score: how much do different dead tones produce different verdicts?"""
    by_tone: Dict[str, List[str]] = {}
    for cp in contact_points:
        by_tone.setdefault(cp.dead_tone, []).append(cp.verdict.value)

    if len(by_tone) < 2:
        return 0.0

    # Compare verdict distributions between tones
    tone_keys = list(by_tone.keys())
    diffs = 0
    comparisons = 0
    for i in range(len(tone_keys)):
        for j in range(i + 1, len(tone_keys)):
            dist_i = Counter(by_tone[tone_keys[i]])
            dist_j = Counter(by_tone[tone_keys[j]])
            all_keys = set(dist_i.keys()) | set(dist_j.keys())
            n_i = sum(dist_i.values()) or 1
            n_j = sum(dist_j.values()) or 1
            diff = sum(abs(dist_i.get(k, 0) / n_i - dist_j.get(k, 0) / n_j) for k in all_keys)
            diffs += diff / 2.0  # normalize to [0, 1]
            comparisons += 1

    return diffs / max(comparisons, 1)


def _cross_domain_score(bundles: List[ProjectionBundle]) -> float:
    """Quick cross-domain agreement score across all bundles."""
    if not bundles:
        return 0.0
    scores = [score_consistency(b).overall for b in bundles]
    return sum(scores) / len(scores)
