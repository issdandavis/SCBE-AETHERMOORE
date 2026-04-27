from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AcceleratorTaskPacket:
    task_id: str
    workload: str
    matmul_fraction: float = 0.0
    nonlinear_op_fraction: float = 0.0
    precision_required_bits: int = 16
    input_is_optical_signal: bool = False
    branching_density: float = 0.0
    memory_access_density: float = 0.0
    latency_budget_ms: float = 100.0
    energy_budget_j: float = 1.0
    fallback: str = "gpu"

    def normalized(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "workload": self.workload,
            "matmul_fraction": _clamp01(self.matmul_fraction),
            "nonlinear_op_fraction": _clamp01(self.nonlinear_op_fraction),
            "precision_required_bits": max(1, int(self.precision_required_bits)),
            "input_is_optical_signal": bool(self.input_is_optical_signal),
            "branching_density": _clamp01(self.branching_density),
            "memory_access_density": _clamp01(self.memory_access_density),
            "latency_budget_ms": max(0.001, float(self.latency_budget_ms)),
            "energy_budget_j": max(0.001, float(self.energy_budget_j)),
            "fallback": self.fallback or "gpu",
        }


@dataclass(frozen=True)
class AcceleratorProviderProfile:
    provider_id: str = "photonic_npu_simulator_v1"
    precision_native_bits: int = 16
    matmul_throughput_score: float = 0.88
    nonlinear_supported_score: float = 0.92
    optical_input_native: bool = False
    branching_supported_score: float = 0.12
    memory_access_score: float = 0.22
    energy_efficiency_score: float = 0.82
    latency_score: float = 0.65

    def normalized(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "precision_native_bits": max(1, int(self.precision_native_bits)),
            "matmul_throughput_score": _clamp01(self.matmul_throughput_score),
            "nonlinear_supported_score": _clamp01(self.nonlinear_supported_score),
            "optical_input_native": bool(self.optical_input_native),
            "branching_supported_score": _clamp01(self.branching_supported_score),
            "memory_access_score": _clamp01(self.memory_access_score),
            "energy_efficiency_score": _clamp01(self.energy_efficiency_score),
            "latency_score": _clamp01(self.latency_score),
        }


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _route_id(task: dict[str, Any], provider: dict[str, Any]) -> str:
    payload = "|".join(f"{key}={task[key]}" for key in sorted(task))
    payload += "|" + "|".join(f"{key}={provider[key]}" for key in sorted(provider))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def accelerator_fit_score(
    packet: AcceleratorTaskPacket,
    provider: AcceleratorProviderProfile | None = None,
) -> dict[str, Any]:
    task = packet.normalized()
    profile = (provider or AcceleratorProviderProfile()).normalized()
    precision_gap = max(0, task["precision_required_bits"] - profile["precision_native_bits"])
    precision_score = max(0.0, 1.0 - precision_gap / 32.0)
    optical_score = 1.0 if task["input_is_optical_signal"] and profile["optical_input_native"] else 0.55
    if not task["input_is_optical_signal"]:
        optical_score = 0.65
    positive = (
        task["matmul_fraction"] * profile["matmul_throughput_score"] * 0.26
        + task["nonlinear_op_fraction"] * profile["nonlinear_supported_score"] * 0.26
        + precision_score * 0.14
        + optical_score * 0.10
        + profile["energy_efficiency_score"] * 0.14
        + profile["latency_score"] * 0.10
    )
    penalties = (
        task["branching_density"] * (1.0 - profile["branching_supported_score"]) * 0.30
        + task["memory_access_density"] * (1.0 - profile["memory_access_score"]) * 0.24
    )
    score = _clamp01(positive - penalties)
    return {
        "score": round(score, 6),
        "provider": profile,
        "task": task,
        "components": {
            "precision_score": round(precision_score, 6),
            "optical_score": round(optical_score, 6),
            "positive": round(positive, 6),
            "penalties": round(penalties, 6),
        },
        "fit_class": "strong" if score >= 0.70 else "partial" if score >= 0.45 else "poor",
    }


def simulate_photonic_accelerator(
    packet: AcceleratorTaskPacket,
    provider: AcceleratorProviderProfile | None = None,
) -> dict[str, Any]:
    fit = accelerator_fit_score(packet, provider)
    task = fit["task"]
    profile = fit["provider"]
    score = float(fit["score"])
    compute_intensity = 0.5 + task["matmul_fraction"] + task["nonlinear_op_fraction"]
    branch_penalty = 1.0 + task["branching_density"] * 2.5
    memory_penalty = 1.0 + task["memory_access_density"] * 1.8
    precision_loss = max(0.0, (task["precision_required_bits"] - profile["precision_native_bits"]) / 64.0)
    precision_loss += task["branching_density"] * 0.04 + task["memory_access_density"] * 0.03
    predicted_latency_ms = max(0.1, task["latency_budget_ms"] * (0.22 + (1.0 - score) * 1.1) * branch_penalty)
    predicted_energy_j = max(
        0.0001, task["energy_budget_j"] * (0.12 + (1.0 - score) * 0.55) * memory_penalty / compute_intensity
    )
    failure_modes: list[str] = []
    if task["precision_required_bits"] > profile["precision_native_bits"] + 8:
        failure_modes.append("precision_mismatch")
    if task["branching_density"] > 0.35:
        failure_modes.append("branching_density_high")
    if task["memory_access_density"] > 0.45:
        failure_modes.append("memory_access_high")
    if predicted_latency_ms > task["latency_budget_ms"]:
        failure_modes.append("latency_budget_exceeded")
    if predicted_energy_j > task["energy_budget_j"]:
        failure_modes.append("energy_budget_exceeded")
    return {
        "schema_version": "photonic_accelerator_simulation_v1",
        "route_id": _route_id(task, profile),
        "provider_id": profile["provider_id"],
        "fit": fit,
        "predicted_latency_ms": round(predicted_latency_ms, 6),
        "predicted_energy_j": round(predicted_energy_j, 6),
        "predicted_precision_loss": round(min(1.0, precision_loss), 6),
        "failure_modes": failure_modes,
    }


def route_accelerator_task(
    packet: AcceleratorTaskPacket,
    provider: AcceleratorProviderProfile | None = None,
) -> dict[str, Any]:
    sim = simulate_photonic_accelerator(packet, provider)
    task = sim["fit"]["task"]
    score = float(sim["fit"]["score"])
    failure_modes = set(sim["failure_modes"])
    if score >= 0.70 and not failure_modes:
        decision = "PHOTONIC_NPU"
    elif score >= 0.55 and failure_modes <= {"precision_mismatch"}:
        decision = "PHOTONIC_NPU_WITH_VERIFY"
    elif "energy_budget_exceeded" in failure_modes or "latency_budget_exceeded" in failure_modes:
        decision = "HOLD"
    else:
        decision = str(task["fallback"]).upper()
    return {
        "schema_version": "accelerator_route_decision_v1",
        "decision": decision,
        "fallback": task["fallback"],
        "simulation": sim,
        "audit": {
            "provider_neutral": True,
            "hardware_claim": "simulated",
            "reason": _decision_reason(decision, score, sorted(failure_modes)),
        },
    }


def _decision_reason(decision: str, score: float, failure_modes: list[str]) -> str:
    if decision == "PHOTONIC_NPU":
        return f"fit_score={score:.3f}; no simulated failure modes"
    if decision == "PHOTONIC_NPU_WITH_VERIFY":
        target = ",".join(failure_modes) if failure_modes else "partial_fit"
        return f"fit_score={score:.3f}; requires verification for {target}"
    if decision == "HOLD":
        return f"fit_score={score:.3f}; budget failure {','.join(failure_modes)}"
    return f"fit_score={score:.3f}; fallback due to {','.join(failure_modes) or 'low_fit'}"
