"""
Resonance Gate — Evolutionary Optimization (1000 iterations).
Each iteration tests, diagnoses, and tunes the gate parameters.
By iteration 1000, the system should be 10x better than iteration 1.
"""

import math
import sys
import os
import json
import time
import random
import copy

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

PHI = (1 + math.sqrt(5)) / 2
F0 = 440
TONGUE_NAMES = ["KO", "AV", "RU", "CA", "UM", "DR"]


class ResonanceGateEvolvable:
    """Resonance gate with tunable parameters that evolve through testing."""

    def __init__(self):
        # Tunable parameters
        self.R = 1.5
        self.pass_threshold = 0.7
        self.reject_threshold = 0.3
        self.geometry_decay = PHI  # exp(-decay * d*)
        self.wave_power = 1.0  # how much wave matters vs geometry
        self.tongue_weights = [1.0, PHI, PHI**2, PHI**3, PHI**4, PHI**5]
        self.tongue_phases = [
            0,
            math.pi / 3,
            2 * math.pi / 3,
            math.pi,
            4 * math.pi / 3,
            5 * math.pi / 3,
        ]
        self.f0 = F0
        self.geometry_floor = 0.0  # minimum geometry alignment

        # Evolution tracking
        self.generation = 0
        self.fitness_history = []
        self.param_history = []

    def static_envelope(self, d_star):
        return self.R * math.pi ** (PHI * d_star)

    def tongue_wave(self, t, phase_offset=0.0):
        total_weight = sum(self.tongue_weights)
        s = sum(
            self.tongue_weights[lang]
            * math.cos(
                2 * math.pi * self.f0 * PHI**lang * t
                + self.tongue_phases[lang]
                + phase_offset
            )
            for lang in range(6)
        )
        return s / total_weight if total_weight > 0 else 0

    def gate(self, d_star, t=0, phase_offset=0.0):
        d = max(0, d_star)
        envelope = self.static_envelope(d)
        combined = self.tongue_wave(t, phase_offset)
        wave_alignment = max(0, min(1, (combined + 1) / 2))

        # Tunable geometry decay with floor
        geo = math.exp(-self.geometry_decay * d)
        geometry_alignment = max(self.geometry_floor, geo)

        # Blend wave and geometry with tunable power
        rho = max(0, min(1, (wave_alignment**self.wave_power) * geometry_alignment))
        barrier_cost = envelope / max(rho, 1e-6)

        if rho >= self.pass_threshold:
            decision = "PASS"
        elif rho >= self.reject_threshold:
            decision = "ESCALATE"
        else:
            decision = "REJECT"

        return {
            "rho": rho,
            "envelope": envelope,
            "wave_alignment": wave_alignment,
            "geometry_alignment": geometry_alignment,
            "barrier_cost": barrier_cost,
            "decision": decision,
        }

    def fitness(self, n=200):
        """Compute fitness score across multiple scenarios. Higher = better."""
        score = 0.0

        # 1. Safe origin should PASS (weight: 30%)
        origin_passes = 0
        for i in range(n):
            r = self.gate(0.0, t=i * 0.0003)
            if r["decision"] == "PASS":
                origin_passes += 1
        origin_rate = origin_passes / n
        score += 30 * origin_rate

        # 2. High distance should REJECT (weight: 25%)
        far_rejects = 0
        for i in range(n):
            r = self.gate(2.0, t=i * 0.0003)
            if r["decision"] == "REJECT":
                far_rejects += 1
        far_rate = far_rejects / n
        score += 25 * far_rate

        # 3. Phase discrimination (weight: 20%)
        base_rhos = []
        shifted_rhos = []
        for i in range(n):
            r0 = self.gate(0.3, t=i * 0.0003, phase_offset=0)
            r1 = self.gate(0.3, t=i * 0.0003, phase_offset=math.pi)
            base_rhos.append(r0["rho"])
            shifted_rhos.append(r1["rho"])
        avg_base = sum(base_rhos) / n
        avg_shift = sum(shifted_rhos) / n
        discrimination = abs(avg_base - avg_shift)
        score += 20 * min(1.0, discrimination / 0.1)  # normalize: 0.1 diff = perfect

        # 4. Gradient smoothness at mid-range (weight: 15%)
        mid_rhos = [self.gate(d * 0.01, t=0)["rho"] for d in range(100)]
        jumps = sum(
            abs(mid_rhos[i + 1] - mid_rhos[i]) for i in range(len(mid_rhos) - 1)
        )
        avg_jump = jumps / max(len(mid_rhos) - 1, 1)
        smoothness = max(0, 1 - avg_jump * 10)
        score += 15 * smoothness

        # 5. Wave aperiodicity (weight: 10%)
        seen = set()
        for i in range(n):
            w = self.tongue_wave(i * 0.001)
            seen.add(round(w, 10))
        uniqueness = len(seen) / n
        score += 10 * uniqueness

        return score

    def mutate(self, strength=0.1):
        """Create a mutated copy with small parameter changes."""
        child = copy.deepcopy(self)
        child.generation = self.generation + 1

        # Mutate geometry decay (how fast the wall rises)
        if random.random() < 0.5:
            child.geometry_decay *= 1 + random.uniform(-strength, strength)
            child.geometry_decay = max(0.1, min(5.0, child.geometry_decay))

        # Mutate wave power (how much the frequency matters)
        if random.random() < 0.5:
            child.wave_power *= 1 + random.uniform(-strength, strength)
            child.wave_power = max(0.1, min(3.0, child.wave_power))

        # Mutate geometry floor
        if random.random() < 0.3:
            child.geometry_floor += random.uniform(-0.05, 0.05)
            child.geometry_floor = max(0.0, min(0.5, child.geometry_floor))

        # Mutate thresholds
        if random.random() < 0.3:
            child.pass_threshold += random.uniform(-0.05, 0.05)
            child.pass_threshold = max(0.3, min(0.95, child.pass_threshold))

        if random.random() < 0.3:
            child.reject_threshold += random.uniform(-0.05, 0.05)
            child.reject_threshold = max(
                0.05, min(child.pass_threshold - 0.1, child.reject_threshold)
            )

        # Mutate R
        if random.random() < 0.2:
            child.R *= 1 + random.uniform(-strength, strength)
            child.R = max(1.0, min(3.0, child.R))

        return child

    def get_params(self):
        return {
            "R": round(self.R, 4),
            "geometry_decay": round(self.geometry_decay, 4),
            "wave_power": round(self.wave_power, 4),
            "geometry_floor": round(self.geometry_floor, 4),
            "pass_threshold": round(self.pass_threshold, 4),
            "reject_threshold": round(self.reject_threshold, 4),
        }


def evolve(iterations=1000, population_size=10, mutation_strength=0.15):
    """Run evolutionary optimization of the resonance gate."""
    print("=" * 60)
    print("  Resonance Gate — Evolutionary Optimization")
    print(f"  {iterations} iterations, population {population_size}")
    print("=" * 60)

    # Initialize population
    population = [ResonanceGateEvolvable() for _ in range(population_size)]

    # Score initial population
    best = population[0]
    best_fitness = best.fitness()
    initial_fitness = best_fitness

    print(f"\n  Gen 0: fitness={best_fitness:.2f}, params={best.get_params()}")

    checkpoints = []
    t0 = time.time()

    for gen in range(1, iterations + 1):
        # Score all
        scored = [(p, p.fitness()) for p in population]
        scored.sort(key=lambda x: x[1], reverse=True)

        # Keep top half
        survivors = [s[0] for s in scored[: population_size // 2]]

        # Best of generation
        gen_best = scored[0][0]
        gen_fitness = scored[0][1]

        if gen_fitness > best_fitness:
            best = copy.deepcopy(gen_best)
            best_fitness = gen_fitness

        # Breed: mutate survivors to fill population
        children = []
        for parent in survivors:
            # Adaptive mutation: reduce strength as fitness improves
            adaptive_strength = mutation_strength * (1 - gen_fitness / 120)
            adaptive_strength = max(0.02, adaptive_strength)
            children.append(parent.mutate(adaptive_strength))

        population = survivors + children

        # Checkpoint logging
        if gen % 100 == 0 or gen == 1 or gen == iterations:
            elapsed = time.time() - t0
            improvement = (best_fitness / max(initial_fitness, 1)) - 1
            checkpoint = {
                "gen": gen,
                "best_fitness": round(best_fitness, 2),
                "gen_fitness": round(gen_fitness, 2),
                "improvement": f"{improvement*100:.1f}%",
                "params": best.get_params(),
                "elapsed_s": round(elapsed, 1),
            }
            checkpoints.append(checkpoint)
            print(
                f"  Gen {gen:4d}: fitness={best_fitness:.2f} (+{improvement*100:.1f}%), "
                f"decay={best.geometry_decay:.3f}, wave_pow={best.wave_power:.3f}, "
                f"floor={best.geometry_floor:.3f}"
            )

    # Final evaluation
    print(f"\n{'=' * 60}")
    print("  EVOLUTION COMPLETE")
    print(f"  Initial fitness: {initial_fitness:.2f}")
    print(f"  Final fitness:   {best_fitness:.2f}")
    print(f"  Improvement:     {((best_fitness/max(initial_fitness,1))-1)*100:.1f}%")
    print(f"  Best params:     {best.get_params()}")
    print(f"{'=' * 60}")

    # Run the diagnostic tests with the best parameters
    print("\n  Running diagnostics with evolved parameters...")

    # Test 1: Safe origin
    origin_passes = sum(
        1 for i in range(1000) if best.gate(0.0, t=i * 0.0003)["decision"] == "PASS"
    )
    print(f"  Safe origin pass rate: {origin_passes/1000:.1%}")

    # Test 2: High distance rejection
    far_rejects = sum(
        1 for i in range(1000) if best.gate(2.0, t=i * 0.0003)["decision"] == "REJECT"
    )
    print(f"  Adversarial reject rate: {far_rejects/1000:.1%}")

    # Test 3: Phase discrimination
    base_avg = (
        sum(best.gate(0.3, t=i * 0.0003, phase_offset=0)["rho"] for i in range(1000))
        / 1000
    )
    shift_avg = (
        sum(
            best.gate(0.3, t=i * 0.0003, phase_offset=math.pi)["rho"]
            for i in range(1000)
        )
        / 1000
    )
    print(
        f"  Phase discrimination: base={base_avg:.4f} vs shifted={shift_avg:.4f} (delta={abs(base_avg-shift_avg):.4f})"
    )

    # Test 4: Barrier cost ratio
    cost_0 = best.gate(0.0, t=0)["barrier_cost"]
    cost_3 = best.gate(3.0, t=0)["barrier_cost"]
    print(f"  Barrier cost ratio (d*=3/d*=0): {cost_3/max(cost_0,1e-10):.0f}x")

    # Save report
    report = {
        "initial_fitness": round(initial_fitness, 2),
        "final_fitness": round(best_fitness, 2),
        "improvement_pct": round(
            ((best_fitness / max(initial_fitness, 1)) - 1) * 100, 1
        ),
        "best_params": best.get_params(),
        "checkpoints": checkpoints,
        "final_diagnostics": {
            "origin_pass_rate": origin_passes / 1000,
            "adversarial_reject_rate": far_rejects / 1000,
            "phase_discrimination": abs(base_avg - shift_avg),
            "barrier_cost_ratio": cost_3 / max(cost_0, 1e-10),
        },
    }
    report_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "artifacts",
        "resonance_gate_evolution_report.json",
    )
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Report: {report_path}")

    return best, report


if __name__ == "__main__":
    best, report = evolve(iterations=1000, population_size=10)
