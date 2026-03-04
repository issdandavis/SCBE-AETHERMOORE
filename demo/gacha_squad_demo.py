#!/usr/bin/env python3
"""
Gacha Isekai Squad Demo — Full Integration
============================================

Demonstrates the complete gacha isekai pipeline:
    1. Tower floor embedding (L4)
    2. Squad formation & gacha pulls
    3. Gravitational alignment
    4. Math-monster combat (L11)
    5. Digimon-style evolution (L7)
    6. Life-sim career progression
    7. HF training loop (L9/L12/L14)
    8. Poly-AI nodal network contributions

Run:
    python demo/gacha_squad_demo.py

Requires: numpy, torch
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np

from src.m4mesh.canonical_state import embed_gacha_floor, compute_squad_ds_squared, MONSTER_BUG_MAP
from src.gacha_isekai.squad import GachaSquad, TernaryAlignment
from src.gacha_isekai.combat import GachaSquadCombat, DebugAction, MathMonster
from src.gacha_isekai.evolution import EvolutionSimulator, EvolutionState, Career, ArcStage
from src.gacha_isekai.training import HFTrainingLoop
from src.gacha_isekai.nodal import PolyAINodalNetwork, CulturalArtifact


def section(title: str) -> None:
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def demo_floor_embedding():
    """L4: Embed gacha tower floors as 21D canonical states."""
    section("LAYER 4: Gacha Floor Embedding (Poincare Ball)")

    for floor in [1, 5, 10, 25, 50]:
        for bug_type, bug_name in list(MONSTER_BUG_MAP.items())[:2]:
            bug = {"a": 1.0 + floor * 0.1, "b": -0.5, "c": 0.3, "type": bug_type}
            state = embed_gacha_floor(floor, bug, seed=floor * 42)
            norm = float(state[:6].norm())
            harmonic = float(state[20])
            print(f"  Floor {floor:3d} | {bug_type:25s} | ||u||={norm:.4f} | H(d)={harmonic:.2f}")

    print("\n  -> Higher floors drift toward Poincare boundary")
    print("  -> Edge-case bugs (near boundary) have exponential harmonic cost")


def demo_squad_formation():
    """Squad formation with gacha pulls and gravitational alignment."""
    section("GACHA SQUAD: Formation & Pulls")

    squad = GachaSquad(leader_name="Marcus_Chen_Jr", level=10)
    print(f"  Leader: {squad.leader_name}")
    print(f"  Position: {squad.leader_position}")
    print(f"  Capacity: {squad._current_capacity()}\n")

    # Gacha pulls
    print("  --- Gacha Pulls ---")
    for i in range(6):
        member = squad.gacha_pull(seed=i * 137)
        squad.add_member(member)
        d = float(np.linalg.norm(member.position - squad.leader_position))
        print(f"  Pull {i+1}: {member.name} ({member.rarity} star, d={d:.3f}, loyalty={member.loyalty:.2f})")

    # Gravitational alignment
    print("\n  --- Gravitational Alignment (3 steps) ---")
    for step in range(3):
        squad.apply_gravitational_step()
        avg_dist = np.mean([
            np.linalg.norm(m.position - squad.leader_position)
            for m in squad.members
        ])
        avg_loyalty = np.mean([m.loyalty for m in squad.members])
        print(f"  Step {step+1}: avg_dist={avg_dist:.4f}, avg_loyalty={avg_loyalty:.3f}")

    print("\n  -> Squad naturally converges toward leader via phi^(-d^2)")

    # Formation
    print("\n  --- Formation ---")
    for tongue, members in squad.get_formation().items():
        print(f"  {tongue}: {', '.join(members)}")

    return squad


def demo_combat(squad: GachaSquad):
    """L11: Squad combat against math-monsters."""
    section("LAYER 11: Squad Combat (Math-Monster Debugging)")

    combat = GachaSquadCombat()

    # Create monsters for floors 1, 5, 10 (boss)
    floors = [
        (1, "null_pointer", False),
        (5, "race_condition", False),
        (10, "cross_boundary_exploit", True),
    ]

    for floor, bug_type, is_boss in floors:
        monster = combat.create_monster(floor, bug_type, is_boss)
        print(f"\n  {'BOSS ' if is_boss else ''}Floor {floor}: {monster.name}")
        print(f"  HP={monster.hp}, ATK={monster.attack}")
        print(f"  Quadratic: {monster.a:.1f}x^2 + {monster.b:.1f}x + {monster.c:.1f}")
        print(f"  Discriminant: {monster.discriminant():.2f}")

        # Squad positions for path validation
        squad_positions = [m.position for m in squad.members[:3]]

        # Choose best debug action for this bug type
        action_map = {
            "null_pointer": DebugAction.ASSERT_STATE,
            "race_condition": DebugAction.LOCK_THREAD,
            "cross_boundary_exploit": DebugAction.SANITIZE_INPUT,
        }
        action = action_map.get(bug_type, DebugAction.RECOMPILE)

        # Combat rounds until victory or 5 rounds
        for rnd in range(5):
            bonus = squad.members[0].combat_bonus if squad.members else 1.0
            result = combat.execute_combat_round(squad_positions, monster, action, bonus)
            print(f"    Round {rnd+1}: {action.value} -> {result.damage_dealt} dmg "
                  f"(eff={result.effectiveness:.1f}, math={'Y' if result.math_solved else 'N'})")
            if result.victory:
                print(f"    VICTORY! Monster defeated.")
                # Shadow Army: recruit defeated enemy
                recruit = squad.recruit_defeated(
                    np.random.rand(3) * 0.5,
                    bug_type.split("_")[0].upper()[:2],
                )
                if recruit:
                    print(f"    Shadow recruit: {recruit.name} ({recruit.rarity} star)")
                break

    return combat


def demo_evolution():
    """L7: Digimon-style evolution and life-sim careers."""
    section("LAYER 7: Evolution & Careers")

    sim = EvolutionSimulator()
    evo = EvolutionState(name="Izack_Companion")

    # Simulate a series of actions
    print("  --- Action History ---")
    actions = [
        (True, 0.1, "Assert boundary check"),
        (True, 0.2, "Sanitize user input"),
        (False, 0.8, "Deployed untested patch"),
        (True, 0.1, "Rollback to stable"),
        (True, 0.15, "Lock shared resource"),
        (True, 0.1, "Verify thread safety"),
        (True, 0.05, "Clean code refactor"),
        (True, 0.1, "Add integration test"),
    ]

    for is_safe, risk, desc in actions:
        sim.record_action(evo, is_safe, risk)
        print(f"  {'SAFE' if is_safe else 'RISK'} | risk={risk:.2f} | {desc}")

    print(f"\n  Safe ratio: {evo.safe_ratio:.2f}")
    print(f"  Evolution pressure: {evo.evolution_pressure:.2f}")
    print(f"  Ready to evolve: {evo.is_ready_to_evolve}")

    # Force evolution pressure for demo
    evo.evolution_pressure = 15.0
    result = sim.evolve(evo)
    print(f"\n  Evolution result: {result['result']}")
    if result["result"] == "EVOLVED":
        print(f"  New stage: {result['new_stage']}")
        print(f"  Branch: {result['branch']}")
        print(f"  rho_e: {result['rho_e']:.3f}")

    # Career
    print("\n  --- Career Progression ---")
    for career in [Career.SEAL_ENGINEER, Career.ROGUE_HUNTER, Career.HARMONIC_AUDITOR]:
        career_result = sim.simulate_career(evo, career)
        print(f"  {career.value}: {career_result['result']} (rho_e={career_result['rho_e']:.3f})")

    return evo


def demo_training_loop():
    """L9/L12/L14: HF training pipeline with governance gating."""
    section("LAYERS 9/12/14: HF Training Loop")

    loop = HFTrainingLoop(batch_size=5)  # Small batch for demo

    # Simulate game events
    events = [
        {"choice": "Explore the abandoned tower", "outcome": "Found a Glitchling nest on floor 3", "arc_stage": "youth"},
        {"choice": "Train with Polly at the academy", "outcome": "Learned Wingscroll Blast technique", "arc_stage": "youth"},
        {"choice": "Investigate the Void Seed whispers", "outcome": "Discovered corrupted echo in the Root Network", "arc_stage": "teen"},
        {"choice": "Defend the village from Drift Maw", "outcome": "Squad combat victory, recruited shadow ally", "arc_stage": "teen"},
        {"choice": "Decode father's harmonic message", "outcome": "Partial decode: 'You must grow before the outer realms accept you'", "arc_stage": "teen"},
        {"choice": "Challenge the Hollow Tongue boss", "outcome": "Boss fight: cross-boundary exploit with complex roots", "arc_stage": "adult"},
        {"choice": "Enter the Timeless Observatory", "outcome": "Time dilation zone: 1 hour inside = 1 day outside", "arc_stage": "adult"},
    ]

    result = loop.run_loop(events)
    print(f"  Events collected: {result['events_collected']}")
    print(f"  Events approved:  {result['events_approved']}")
    print(f"  Events rejected:  {result['events_rejected']}")
    print(f"  Pending pairs:    {result['pending_pairs']}")
    if result["export_path"]:
        print(f"  Exported batch:   {result['export_path']}")
    else:
        print(f"  (Batch not yet full — need {loop.batch_size} pairs)")

    stats = loop.get_stats()
    print(f"\n  Pipeline stats: {stats}")

    return loop


def demo_nodal_network():
    """L6/L11/L12/L14: Poly-AI cultural nodal network."""
    section("POLY-AI NODAL NETWORK")

    network = PolyAINodalNetwork()

    # Add cultural artifacts from various game events
    artifacts = [
        CulturalArtifact(
            artifact_id="math_001",
            artifact_type="math_solution",
            content="Solved quadratic 1.5x^2 - 3x + 0.6 via discriminant method",
            contributor="Izack",
            tongue="CA",
            embedding=np.array([0.1, 0.2, 0.3, 0.1, 0.1, 0.1]),
        ),
        CulturalArtifact(
            artifact_id="dungeon_001",
            artifact_type="dungeon",
            content="Tower Floor 5: Race condition maze with phantom forks",
            contributor="Polly",
            tongue="KO",
            embedding=np.array([0.2, 0.1, 0.3, 0.2, 0.1, 0.2]),
        ),
        CulturalArtifact(
            artifact_id="career_001",
            artifact_type="career",
            content="Seal Engineer: Cryptographic key rotation mini-game unlocked",
            contributor="Clay",
            tongue="RU",
            embedding=np.array([0.15, 0.15, 0.25, 0.15, 0.2, 0.15]),
        ),
        CulturalArtifact(
            artifact_id="cinematic_001",
            artifact_type="cinematic",
            content="Father's first harmonic message decoded during Void Seed incursion",
            contributor="Kael",
            tongue="UM",
            embedding=np.array([0.1, 0.3, 0.2, 0.1, 0.3, 0.1]),
        ),
        CulturalArtifact(
            artifact_id="evolution_001",
            artifact_type="evolution",
            content="Izack's companion evolved to Teen stage via Architect branch",
            contributor="Izack",
            tongue="CA",
            embedding=np.array([0.12, 0.22, 0.28, 0.12, 0.12, 0.12]),
        ),
    ]

    print("  --- Adding Artifacts ---")
    for art in artifacts:
        # Connect to previous artifacts where applicable
        connected = [a.artifact_id for a in artifacts if a.artifact_id != art.artifact_id and a.tongue == art.tongue]
        success = network.add_artifact(
            art,
            connected_ids=connected[:2],
            leader_alignment=(1, 1),
            contributor_alignment=(1, 0),
        )
        status = "ADDED" if success else "REJECTED"
        print(f"  {status}: {art.artifact_id} ({art.artifact_type}, {art.tongue})")

    # Stats
    stats = network.get_stats()
    print(f"\n  --- Network Stats ---")
    print(f"  Total artifacts: {stats.total_artifacts}")
    print(f"  Total edges:     {stats.total_edges}")
    print(f"  Rejected:        {stats.rejected_count}")
    print(f"  Avg rho_e:       {stats.avg_rho_e:.3f}")

    print(f"\n  By tongue: {dict(stats.artifacts_by_tongue)}")
    print(f"  By type:   {dict(stats.artifacts_by_type)}")

    # Autonomous queue
    queue = network.drain_autonomous_queue()
    print(f"\n  Autonomous 24/7 queue: {len(queue)} artifacts ready for agent replay")

    return network


def main():
    print("=" * 70)
    print("  GACHA ISEKAI — SCBE-AETHERMOORE Integration Demo")
    print("  'Stuck in a Gacha Game' meets AI Safety Governance")
    print("=" * 70)

    # 1. Floor embedding
    demo_floor_embedding()

    # 2. Squad formation
    squad = demo_squad_formation()

    # 3. Combat
    combat = demo_combat(squad)

    # 4. Evolution
    evo = demo_evolution()

    # 5. Training loop
    loop = demo_training_loop()

    # 6. Nodal network
    network = demo_nodal_network()

    # Summary
    section("INTEGRATION SUMMARY")
    print(f"  Squad size:       {len(squad.members)}")
    print(f"  Combat rounds:    {len(combat.combat_log)}")
    print(f"  Evolution stage:  {evo.arc_stage.value}")
    print(f"  Training batches: {loop.total_batches_exported}")
    print(f"  Nodal artifacts:  {network.get_stats().total_artifacts}")
    print()
    print("  Layer mapping:")
    print("    L4  - Floor embedding (Poincare ball)")
    print("    L6  - Squad alignment (HYDRA coordination)")
    print("    L7  - Evolution & careers (phase modulation)")
    print("    L9  - Validation & sanitization (auth envelope)")
    print("    L11 - Squad combat path integrity (PHDM)")
    print("    L12 - Training rho_e gating (entropic defense)")
    print("    L14 - PQC signing (topological CFI)")
    print()
    print("  Next: python scripts/hf_training_loop.py --batch 100 --autonomous True")
    print("=" * 70)


if __name__ == "__main__":
    main()
