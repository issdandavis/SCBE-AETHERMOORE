from __future__ import annotations

import json

from src.neurogolf.arc_io import load_arc_task
from src.neurogolf.token_braid import (
    BRAID_TONGUES,
    FAMILY_PQC_PACKETS,
    TritVoxel,
    box_threat_topology,
    explain_task_braid,
    family_trit_voxel,
    family_token_braid_signatures,
    free_axes,
    invariant_null_axes,
    null_space_report,
    rank_families_by_token_braid,
    rank_families_by_token_braid_null_space,
    task_packet,
    task_tokens,
    task_triad,
    task_trit_voxel,
    tongue_null_axes,
    wormhole_axes,
)
from src.neurogolf.pqc_braid_thread import (
    ThreatVerdict,
    detect_threat,
    pqc_alignment,
    pqc_packet_fingerprint,
    pqc_thread_score,
)


def _write_task(tmp_path, name: str, payload: dict) -> object:
    task_path = tmp_path / f"{name}.json"
    task_path.write_text(json.dumps(payload), encoding="utf-8")
    return load_arc_task(task_path)


def test_family_braid_signatures_cover_all_braid_tongues():
    signatures = family_token_braid_signatures()
    identity = signatures["identity"]
    assert tuple(identity) == BRAID_TONGUES
    assert all(len(sig.tokens) == 6 for sig in identity.values())


def test_task_packet_tokens_and_triad_have_fixed_width(tmp_path):
    task = _write_task(
        tmp_path,
        "identity",
        {
            "train": [{"input": [[1, 2], [3, 4]], "output": [[1, 2], [3, 4]]}],
            "test": [{"input": [[1, 2], [3, 4]]}],
        },
    )

    packet = task_packet(task)
    tokens = task_tokens(task, "CA")
    triad = task_triad(task)

    assert len(packet) == 6
    assert len(tokens) == 6
    assert len(triad) == 6
    assert set(triad).issubset({-1, 0, 1})


def test_trit_voxel_splits_all_three_bands(tmp_path):
    task = _write_task(
        tmp_path,
        "voxel_probe",
        {
            "train": [{"input": [[1]], "output": [[1]]}],
            "test": [{"input": [[1]]}],
        },
    )

    voxel = TritVoxel.from_triad((-1, 0, 1, -1, 1, 0))
    assert voxel.neg_band == frozenset({0, 3})
    assert voxel.zero_band == frozenset({1, 5})
    assert voxel.pos_band == frozenset({2, 4})

    task_voxel = task_trit_voxel(task)
    assert isinstance(task_voxel, TritVoxel)
    assert task_voxel.neg_band | task_voxel.zero_band | task_voxel.pos_band == frozenset(range(6))


def test_family_trit_voxel_matches_signature_triad():
    voxel = family_trit_voxel("color_remap")
    assert isinstance(voxel, TritVoxel)
    assert voxel.neg_band | voxel.zero_band | voxel.pos_band == frozenset(range(6))


def test_tile_self_task_ranks_tile_self_first_in_braid(tmp_path):
    task = _write_task(
        tmp_path,
        "tile_self",
        {
            "train": [
                {
                    "input": [[1, 0], [0, 1]],
                    "output": [
                        [1, 0, 0, 0],
                        [0, 1, 0, 0],
                        [0, 0, 1, 0],
                        [0, 0, 0, 1],
                    ],
                }
            ],
            "test": [{"input": [[1, 0], [0, 1]]}],
        },
    )

    braid = rank_families_by_token_braid(task)
    assert braid[0] == "tile_self"


def test_color_remap_task_keeps_color_family_near_top(tmp_path):
    task = _write_task(
        tmp_path,
        "color_remap",
        {
            "train": [
                {"input": [[1, 2], [2, 1]], "output": [[3, 4], [4, 3]]},
                {"input": [[2, 1]], "output": [[4, 3]]},
            ],
            "test": [{"input": [[1, 2]]}],
        },
    )

    braid = rank_families_by_token_braid(task)
    assert "color_remap" in braid[:5]


def test_trit_voxel_alignment_keeps_color_family_ahead_of_motion_family(tmp_path):
    task = _write_task(
        tmp_path,
        "color_remap_voxel",
        {
            "train": [
                {"input": [[1, 2], [2, 1]], "output": [[3, 4], [4, 3]]},
                {"input": [[2, 1]], "output": [[4, 3]]},
            ],
            "test": [{"input": [[1, 2]]}],
        },
    )

    braid = rank_families_by_token_braid(task)
    assert braid.index("color_remap") < braid.index("shift")


def test_explain_task_braid_returns_usable_payload(tmp_path):
    task = _write_task(
        tmp_path,
        "shift_color",
        {
            "train": [
                {
                    "input": [[1, 0, 0], [0, 2, 0], [0, 0, 0]],
                    "output": [[0, 0, 0], [5, 0, 0], [0, 6, 0]],
                }
            ],
            "test": [{"input": [[1, 0, 0], [0, 2, 0], [0, 0, 0]]}],
        },
    )

    payload = explain_task_braid(task)
    assert set(payload["axes"]) == {"shape", "motion", "color", "scope", "topology", "composition"}
    assert len(payload["packet"]) == 6
    assert len(payload["triad"]) == 6
    assert len(payload["tokens"]) == 6


# ---------------------------------------------------------------------------
# Null-space tests
# ---------------------------------------------------------------------------


def test_tongue_null_axes_returns_six_tongue_sets(tmp_path):
    """Every tongue code should be present; each value is a frozenset of ints."""
    task = _write_task(
        tmp_path,
        "identity",
        {
            "train": [{"input": [[1, 0], [0, 1]], "output": [[1, 0], [0, 1]]}],
            "test": [{"input": [[1, 0], [0, 1]]}],
        },
    )
    result = tongue_null_axes(task)
    assert set(result) == {"ko", "av", "ru", "ca", "um", "dr"}
    for null_set in result.values():
        assert isinstance(null_set, frozenset)
        assert all(0 <= i < 6 for i in null_set)


def test_invariant_null_axes_subset_of_each_tongue(tmp_path):
    """Invariant null must be ⊆ every per-tongue null set."""
    task = _write_task(
        tmp_path,
        "color_remap_null",
        {
            "train": [
                {"input": [[1, 2], [2, 1]], "output": [[3, 4], [4, 3]]},
            ],
            "test": [{"input": [[1, 2]]}],
        },
    )
    per_tongue = tongue_null_axes(task)
    inv_null = invariant_null_axes(task)
    for null_set in per_tongue.values():
        assert inv_null <= null_set, "invariant null must be a subset of every tongue's null"


def test_free_axes_complement_of_invariant_null(tmp_path):
    """free_axes ∪ invariant_null == {0,1,2,3,4,5}."""
    task = _write_task(
        tmp_path,
        "tile_free",
        {
            "train": [
                {
                    "input": [[1, 0], [0, 1]],
                    "output": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
                }
            ],
            "test": [{"input": [[1, 0], [0, 1]]}],
        },
    )
    fa = set(free_axes(task))
    inv_null = invariant_null_axes(task)
    assert fa | inv_null == set(range(6))
    assert fa & inv_null == set()


def test_wormhole_axes_subset_of_coarse_null(tmp_path):
    """Wormhole axes must be null in KO/AV/RU (coarse tongues)."""
    task = _write_task(
        tmp_path,
        "wormhole_check",
        {
            "train": [
                {"input": [[1, 2, 3], [0, 0, 0]], "output": [[3, 2, 1], [0, 0, 0]]},
            ],
            "test": [{"input": [[1, 2, 3], [0, 0, 0]]}],
        },
    )
    per_tongue = tongue_null_axes(task)
    worm = wormhole_axes(task)
    coarse_null = per_tongue["ko"] & per_tongue["av"] & per_tongue["ru"]
    assert worm <= coarse_null, "wormhole axes must be null in all coarse tongues"


def test_dr_sees_more_than_ko(tmp_path):
    """Draumric (phi=11.09) should have fewer or equal null axes than Kor'aelin (phi=1.0)
    because higher sensitivity means fewer axes fall below the threshold."""
    task = _write_task(
        tmp_path,
        "sensitivity_check",
        {
            "train": [
                {"input": [[1, 2], [3, 4]], "output": [[2, 1], [4, 3]]},
            ],
            "test": [{"input": [[1, 2], [3, 4]]}],
        },
    )
    per_tongue = tongue_null_axes(task)
    # DR is more sensitive → should detect at most as many null axes as KO
    assert len(per_tongue["dr"]) <= len(per_tongue["ko"])


def test_null_space_report_has_required_keys(tmp_path):
    """null_space_report must return all expected keys."""
    task = _write_task(
        tmp_path,
        "report_check",
        {
            "train": [{"input": [[1, 0], [0, 1]], "output": [[1, 0], [0, 1]]}],
            "test": [{"input": [[1, 0], [0, 1]]}],
        },
    )
    report = null_space_report(task)
    assert "topology" in report
    assert "per_tongue_null" in report
    assert "invariant_null_axes" in report
    assert "wormhole_axes" in report
    assert "free_axes" in report
    assert set(report["per_tongue_null"]) == {"ko", "av", "ru", "ca", "um", "dr"}


def test_cross_tongue_null_space_thresholds_are_respected(tmp_path, monkeypatch):
    task = _write_task(
        tmp_path,
        "threshold_probe",
        {
            "train": [{"input": [[1]], "output": [[1]]}],
            "test": [{"input": [[1]]}],
        },
    )
    monkeypatch.setattr(
        "src.neurogolf.token_braid.task_topology",
        lambda _task: [0.02, 0.0, 0.12, 0.03, 0.2, 0.0],
    )

    per_tongue = tongue_null_axes(task)
    assert per_tongue["ko"] == frozenset({0, 1, 3, 5})
    assert per_tongue["ru"] == frozenset({0, 1, 3, 5})
    assert per_tongue["ca"] == frozenset({0, 1, 5})
    assert invariant_null_axes(task) == frozenset({1, 5})
    assert wormhole_axes(task) == frozenset({0, 3})
    assert free_axes(task) == (0, 2, 3, 4)


def test_null_space_report_names_axes_cleanly(tmp_path, monkeypatch):
    task = _write_task(
        tmp_path,
        "named_report",
        {
            "train": [{"input": [[1]], "output": [[1]]}],
            "test": [{"input": [[1]]}],
        },
    )
    monkeypatch.setattr(
        "src.neurogolf.token_braid.task_topology",
        lambda _task: [0.02, 0.0, 0.12, 0.03, 0.2, 0.0],
    )

    report = null_space_report(task)
    # invariant_null and wormhole are lists of axis names (consistent with free_axes)
    assert report["invariant_null_axes"] == ["motion", "composition"]
    assert report["wormhole_axes"] == ["shape", "scope"]
    assert report["free_axes"] == ["shape", "color", "scope", "topology"]


def test_null_space_rerank_penalizes_dead_axis_families(tmp_path, monkeypatch):
    """Null reranker must actually invert order when a family's topology mass
    sits inside the invariant-null subspace of the task.

    Setup:
      - rotate_180 topology: motion=1.0, topology_axis=0.8  (heavy in motion/idx=1)
      - color_remap topology: color=1.0, scope=0.1          (zero in motion/idx=1)
      - task topology: motion=0.0, composition=0.0 → invariant_null = {1, 5}
      - rotate_180 null_mass = mean(1.0, 0.0) = 0.5  → penalty = 0.20*0.5 = 0.10
      - color_remap null_mass = mean(0.0, 0.0) = 0.0  → penalty = 0.0
      - base scores: rotate_180=0.8 > color_remap=0.7  → base_order[0] = rotate_180
      - adjusted:    rotate_180=0.70, color_remap≈0.705 → null_order[0] = color_remap
    """
    task = _write_task(
        tmp_path,
        "rerank_probe",
        {
            "train": [{"input": [[1]], "output": [[1]]}],
            "test": [{"input": [[1]]}],
        },
    )
    # rotate_180 leads plain braid by 0.1
    monkeypatch.setattr(
        "src.neurogolf.token_braid._token_braid_scores",
        lambda _task, _tongues=BRAID_TONGUES: [("rotate_180", 0.8), ("color_remap", 0.7)],
    )
    # motion (idx=1) and composition (idx=5) are zero → invariant_null = {1,5}
    monkeypatch.setattr(
        "src.neurogolf.token_braid.task_topology",
        lambda _task: [0.02, 0.0, 0.12, 0.03, 0.2, 0.0],
    )

    base_order = rank_families_by_token_braid(task)
    null_order = rank_families_by_token_braid_null_space(task)
    # plain braid: rotate_180 wins (0.8 vs 0.7)
    assert base_order[:2] == ["rotate_180", "color_remap"]
    # null reranker: rotate_180 penalised 0.10 for motion mass → color_remap wins
    assert null_order[:2] == ["color_remap", "rotate_180"]


# ---------------------------------------------------------------------------
# Thread 3: PQC braid thread tests
# ---------------------------------------------------------------------------


def test_pqc_fingerprint_is_deterministic():
    """Same packet always produces the same fingerprint."""
    packet = bytes([10, 200, 50, 180, 75, 130])
    fp1 = pqc_packet_fingerprint(packet)
    fp2 = pqc_packet_fingerprint(packet)
    assert fp1 == fp2
    assert len(fp1) == 8


def test_pqc_alignment_identical_is_one():
    """Identical fingerprints score 1.0."""
    fp = pqc_packet_fingerprint(bytes([1, 2, 3, 4, 5, 6]))
    assert pqc_alignment(fp, fp) == 1.0


def test_pqc_alignment_different_packets_below_one():
    """Different topology packets produce different fingerprints."""
    fp_a = pqc_packet_fingerprint(bytes([255, 0, 255, 0, 255, 0]))
    fp_b = pqc_packet_fingerprint(bytes([0, 255, 0, 255, 0, 255]))
    assert pqc_alignment(fp_a, fp_b) < 1.0


def test_pqc_thread_score_self_is_one():
    """A packet scored against itself is 1.0."""
    packet = bytes([100, 50, 200, 10, 150, 80])
    assert pqc_thread_score(packet, packet) == 1.0


def test_family_pqc_packets_covers_all_families():
    """FAMILY_PQC_PACKETS has an entry for every known family."""
    from src.neurogolf.family_lattice import FAMILY_TOPOLOGIES

    assert set(FAMILY_PQC_PACKETS) == set(FAMILY_TOPOLOGIES)
    for fam, pkt in FAMILY_PQC_PACKETS.items():
        assert isinstance(pkt, bytes), f"{fam} packet is not bytes"
        assert len(pkt) > 0, f"{fam} packet is empty"


def test_box_threat_topology_genuine_allows(tmp_path):
    """A normal color-remap task routes to ALLOW."""
    task = _write_task(
        tmp_path,
        "genuine_color",
        {
            "train": [{"input": [[1, 2], [2, 1]], "output": [[3, 4], [4, 3]]}],
            "test": [{"input": [[1, 2]]}],
        },
    )
    verdict = box_threat_topology(task)
    assert isinstance(verdict, ThreatVerdict)
    assert verdict.action == "ALLOW"
    assert 0.0 <= verdict.impostor_confidence <= 1.0
    assert 0.0 <= verdict.pqc_score <= 1.0


def test_detect_threat_impostor_triggers_deny():
    """High Thread 1+2 score + low Thread 3 → DENY at default thresholds.

    A zero-filled packet vs any real family packet produces pqc_score ≈ 0.5
    (random bit-agreement), which is below the default deny_threshold=0.65.
    Combined with a high fake TG score this must fire DENY, not ALLOW.
    """
    task_pkt = bytes(6)  # all zeros — maximally divergent from any real family
    best_family = "color_remap"
    family_pkt = FAMILY_PQC_PACKETS[best_family]

    # Confirm the alignment is below the deny threshold (0.55)
    # Zero-packet empirically scores ≈0.34 vs any real family packet.
    actual_pqc = pqc_alignment(
        pqc_packet_fingerprint(task_pkt),
        pqc_packet_fingerprint(family_pkt),
    )
    assert actual_pqc < 0.55, (
        f"Expected pqc_score < 0.55 (deny threshold), got {actual_pqc:.4f}. "
        "If fingerprint distribution changed, recalibrate deny_threshold."
    )

    # High Thread 1+2 + random Thread 3 → DENY at default thresholds
    fake_tg_scores = [(best_family, 0.85)]
    verdict = detect_threat(task_pkt, fake_tg_scores, {best_family: family_pkt})
    assert verdict.action == "DENY", (
        f"Expected DENY, got {verdict.action} (pqc_score={verdict.pqc_score:.4f})"
    )
    assert verdict.impostor_confidence > 0.0


def test_three_thread_structure_in_braid_scores(tmp_path):
    """All three threads contribute: changing topology changes the final score."""
    task_a = _write_task(
        tmp_path,
        "t3_a",
        {
            "train": [{"input": [[1, 2]], "output": [[3, 4]]}],
            "test": [{"input": [[1, 2]]}],
        },
    )
    task_b = _write_task(
        tmp_path,
        "t3_b",
        {
            "train": [
                {
                    "input": [[1, 0], [0, 1]],
                    "output": [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]],
                }
            ],
            "test": [{"input": [[1, 0], [0, 1]]}],
        },
    )
    rank_a = rank_families_by_token_braid(task_a)
    rank_b = rank_families_by_token_braid(task_b)
    # Different topologies should produce different top families
    assert rank_a[0] != rank_b[0]
