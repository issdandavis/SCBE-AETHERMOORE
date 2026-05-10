from scripts.research.aether_lattice_sim import (
    aggregate_reports,
    build_route_table,
    run_simulation,
    run_trials,
    tesseract_address,
)


def test_lattice_contains_faults_better_than_flat_queue():
    report = run_simulation(operations=100, fault_rate=0.05, seed=42, octree_depth=3)

    assert report.flat.faulty_agent_events > 0
    assert report.flat.public_corruptions > report.lattice.public_corruptions
    assert report.actor_isolation.public_corruptions > report.lattice.public_corruptions
    assert report.actor_supervisor.public_corruptions == report.lattice.public_corruptions
    assert report.lattice.max_containment_radius <= 1
    assert report.crypto_profile["name"] == "star-fortress-v1"
    assert report.crypto_profile["sacred_egg_mapping"]["yolk"].startswith("CORE")
    assert report.comparison["claim_supported"] is True


def test_lattice_outputs_star_fortress_receipts():
    report = run_simulation(operations=24, fault_rate=0.25, seed=12, octree_depth=3)

    receipts = report.lattice.sample_boundary_receipts
    assert receipts
    assert any(receipt["fail_to_noise"] for receipt in receipts)
    assert any(receipt["active_ring"] == "outer-lattice" for receipt in receipts)
    assert all(receipt["sacred_egg"]["yolk_emitted"] is False for receipt in receipts)
    assert report.crypto_profile["triadic_fallback_order"] == [
        "outer-lattice",
        "middle-hash",
        "inner-dev-fallback",
    ]


def test_lattice_trace_cost_is_log_like_not_linear():
    report = run_simulation(operations=128, fault_rate=0.1, seed=7, octree_depth=4)

    assert report.flat.mean_trace_cost == 64.5
    assert report.lattice.mean_trace_cost <= 5.0
    assert report.lattice.mean_trace_cost < report.actor_supervisor.mean_trace_cost
    assert report.comparison["trace_cost_reduction_percent"] > 90
    assert report.comparison["trace_cost_reduction_vs_actor_supervisor_percent"] > 0


def test_lattice_spore_cache_reuses_repair_routes():
    report = run_simulation(operations=128, fault_rate=0.1, seed=7, octree_depth=4)

    assert report.lattice.spore_count > 0
    assert report.lattice.dynamic_cache_hits > 0
    assert report.lattice.tabulated_route_count == 128
    assert report.lattice.tabulation_hits == 128
    assert report.lattice.centerline_roundabout_hits == 128
    assert report.lattice.mean_trace_cost < 5.0


def test_tesseract_route_table_is_deterministic_and_projected_to_octree():
    first = build_route_table(operations=16, depth=3)
    second = build_route_table(operations=16, depth=3)
    address = tesseract_address(op_id=7, depth=3)

    assert first == second
    assert first[7] == address
    assert len(address.octree_path.split(".")) == 3
    assert 0 <= address.roundabout_lane < 8
    assert address.route_key.endswith(f"|r{address.roundabout_lane}")
    assert address.centerline_distance > 0


def test_no_fault_run_still_routes_without_public_corruption():
    report = run_simulation(operations=32, fault_rate=0.0, seed=9, octree_depth=2)

    assert report.flat.public_corruptions == 0
    assert report.lattice.public_corruptions == 0
    assert report.lattice.throughput == 1.0


def test_trial_sweep_reports_supported_claims():
    reports = run_trials(operations=64, fault_rate=0.05, seed=100, octree_depth=3, trials=5)
    aggregate = aggregate_reports(reports)

    assert aggregate["trials"] == 5
    assert aggregate["claim_supported_trials"] == 5
    assert aggregate["actor_supervisor_mean_public_corruptions"] == 0
    assert aggregate["lattice_mean_public_corruptions"] <= aggregate["flat_mean_public_corruptions"]
    assert aggregate["mean_trace_cost_reduction_vs_actor_supervisor_percent"] > 0
    assert aggregate["lattice_mean_dynamic_cache_hits"] >= 0
    assert aggregate["lattice_mean_tabulated_route_count"] == 64
    assert aggregate["lattice_mean_tabulation_hits"] == 64
