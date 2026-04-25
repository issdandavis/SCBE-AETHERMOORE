from src.tokenizer.accelerator_routing import (
    AcceleratorProviderProfile,
    AcceleratorTaskPacket,
    accelerator_fit_score,
    route_accelerator_task,
    simulate_photonic_accelerator,
)


def test_photonic_simulator_routes_nonlinear_low_precision_workload() -> None:
    packet = AcceleratorTaskPacket(
        task_id="image_learning_patch",
        workload="nonlinear_inference",
        matmul_fraction=0.72,
        nonlinear_op_fraction=0.82,
        precision_required_bits=16,
        branching_density=0.05,
        memory_access_density=0.10,
        latency_budget_ms=80,
        energy_budget_j=1.0,
    )

    route = route_accelerator_task(packet)

    assert route["decision"] == "PHOTONIC_NPU"
    assert route["simulation"]["fit"]["fit_class"] == "strong"
    assert route["simulation"]["predicted_energy_j"] < packet.energy_budget_j
    assert route["audit"]["hardware_claim"] == "simulated"


def test_branchy_memory_heavy_workload_falls_back_to_gpu() -> None:
    packet = AcceleratorTaskPacket(
        task_id="symbolic_planner",
        workload="branchy_planning",
        matmul_fraction=0.10,
        nonlinear_op_fraction=0.08,
        precision_required_bits=32,
        branching_density=0.88,
        memory_access_density=0.80,
        latency_budget_ms=50,
        energy_budget_j=0.8,
        fallback="gpu",
    )

    route = route_accelerator_task(packet)

    assert route["decision"] in {"GPU", "HOLD"}
    assert "branching_density_high" in route["simulation"]["failure_modes"]
    assert route["simulation"]["fit"]["fit_class"] == "poor"


def test_optical_input_provider_profile_improves_fit_for_signal_frontend() -> None:
    packet = AcceleratorTaskPacket(
        task_id="lidar_phase_filter",
        workload="optical_preprocess",
        matmul_fraction=0.35,
        nonlinear_op_fraction=0.55,
        precision_required_bits=12,
        input_is_optical_signal=True,
        branching_density=0.02,
        memory_access_density=0.08,
    )
    normal = accelerator_fit_score(packet)
    optical = accelerator_fit_score(packet, AcceleratorProviderProfile(optical_input_native=True))

    assert optical["score"] > normal["score"]


def test_simulation_reports_precision_mismatch_for_high_precision_task() -> None:
    packet = AcceleratorTaskPacket(
        task_id="high_precision_solver",
        workload="scientific_solver",
        matmul_fraction=0.80,
        nonlinear_op_fraction=0.60,
        precision_required_bits=64,
        branching_density=0.02,
        memory_access_density=0.05,
    )

    sim = simulate_photonic_accelerator(packet)

    assert "precision_mismatch" in sim["failure_modes"]
    assert sim["predicted_precision_loss"] > 0
