#!/usr/bin/env python3
"""Build the SCBE coding-system registry consumed by the swarm router.

The registry intentionally points at existing code, docs, and Obsidian-imported
notes. It is not a new architecture layer; it is a machine-readable map of the
coding systems already present in this workspace.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = REPO_ROOT / "docs" / "research" / "SCBE_CODING_SYSTEM_REGISTRY_2026-05-10.json"


@dataclass(frozen=True)
class CodingSystem:
    system_id: str
    name: str
    purpose: str
    best_for: list[str]
    benchmark_role: str
    primary_paths: list[str]
    obsidian_or_note_paths: list[str]
    commands: list[str]
    expected_outputs: list[str]
    registry_status: str = "active"


SYSTEMS = (
    CodingSystem(
        system_id="stisa_atomic_tokenizer",
        name="STISA Atomic Tokenizer Surface",
        purpose="Map code tokens into atomic/STISA feature rows, binary groups, and transport-aligned token metadata.",
        best_for=["precision builds", "semantic feature rows", "cross-system code packets", "evidence traces"],
        benchmark_role="atomic_surface",
        primary_paths=[
            "src/tokenizer/code_weight_packets.py",
            "src/geoseal_cli.py",
            "scripts/build_coding_system_full_sft.py",
            "scripts/benchmark/build_representation_kaleidoscope.py",
            "scripts/benchmark/coding_system_industry_benchmark.py",
        ],
        obsidian_or_note_paths=["notes/theory/atomic-tokenizer-chemistry-unified.md"],
        commands=[
            "python scripts/benchmark/build_representation_kaleidoscope.py",
            "python scripts/benchmark/coding_system_industry_benchmark.py",
        ],
        expected_outputs=["stisa_field_names", "atomic_tokenizer_rows", "source_sha256", "token_sha256"],
    ),
    CodingSystem(
        system_id="ss1_sacred_tongue_transport",
        name="SS1 Sacred Tongue Transport",
        purpose="Bijective byte/token transport over KO/AV/RU/CA/UM/DR for exact round-trip proofs.",
        best_for=["cross-language transport", "build bijection", "payload verification", "tokenizer identity"],
        benchmark_role="transport_surface",
        primary_paths=[
            "src/crypto/sacred_tongue_payload_bijection.py",
            "scripts/system/sacred_tongue_build_bijection.py",
            "src/symphonic_cipher/scbe_aethermoore/spiral_seal/sacred_tongues.py",
        ],
        obsidian_or_note_paths=[
            "notes/System Library/Tokenizer Vault/Transport Tokenizer - SS1 and Sacred Tongues.md",
            "exports/obsidian/notion_mcp_ingest_2026-02-24/SS1_Tokenizer_Protocol.md",
        ],
        commands=["npm run agent:prove-build-bijection"],
        expected_outputs=["SS1 round-trip proof", "tongue token stream", "byte-equal verification"],
    ),
    CodingSystem(
        system_id="geoseal_agent_task",
        name="GeoSeal Agent Task Runner",
        purpose="Wrap coding tasks in signed canonical packets with SS1 proof and routeable receipts.",
        best_for=["auditable coding tasks", "handoff receipts", "safe agent execution", "precision task packets"],
        benchmark_role="packet_surface",
        primary_paths=[
            "src/geoseal_cli.py",
            "scripts/agents/run_agent_task.py",
            "tests/test_agent_task_run_and_external_eval.py",
        ],
        obsidian_or_note_paths=[],
        commands=["npm run agent:task"],
        expected_outputs=["canonical task JSON", "SS1 proof", "task receipt", "route decision"],
    ),
    CodingSystem(
        system_id="cross_language_lookup",
        name="Cross-Language Lookup",
        purpose="Map equivalent coding concepts across Python, TypeScript, Rust, C, Java, and other language lenses.",
        best_for=["cross-language coding", "translation checks", "polyglot docs", "language-agnostic examples"],
        benchmark_role="cross_language_surface",
        primary_paths=[
            "scripts/system/build_cross_language_lookup.py",
            "tests/test_cross_language_lookup.py",
            "tests/test_geoseal_cross_language_lookup_bridge.py",
        ],
        obsidian_or_note_paths=[],
        commands=["npm run benchmark:cross-language-lookup"],
        expected_outputs=["concept lookup table", "language lens rows", "consistency checks"],
    ),
    CodingSystem(
        system_id="code_slice_geometry",
        name="Code Slice Geometry",
        purpose="Represent code slices as geometry for route choice, task decomposition, and focus-path selection.",
        best_for=["geometric routing", "focus-path selection", "multi-lane task decomposition"],
        benchmark_role="geometry_surface",
        primary_paths=["scripts/system/code_slice_geometry.py", "tests/test_code_slice_geometry.py"],
        obsidian_or_note_paths=[],
        commands=["npm run agent:code-slice-geometry"],
        expected_outputs=["slice geometry", "route hints", "focus paths"],
    ),
    CodingSystem(
        system_id="aetherpp_lowering",
        name="Aether++ Parser and Lowering",
        purpose="Parse and lower Aether++ syntax into executable or analyzable code surfaces.",
        best_for=["structured code generation", "compiler-style lowering", "precision syntax checks"],
        benchmark_role="compiler_surface",
        primary_paths=["scripts/aetherpp/cli.py", "tests/test_aetherpp_parser.py", "tests/test_aetherpp_lowering.py"],
        obsidian_or_note_paths=[],
        commands=["npm run agent:aetherpp"],
        expected_outputs=["parsed AST", "lowered code", "syntax diagnostics"],
    ),
    CodingSystem(
        system_id="functional_coding_agent_benchmark",
        name="Functional Coding Agent Benchmark",
        purpose="Grade candidate coding-agent answers against executable task checks.",
        best_for=["daily coding quality", "held-out task scoring", "patch regression checks"],
        benchmark_role="grading_surface",
        primary_paths=[
            "scripts/eval/functional_coding_agent_benchmark.py",
            "scripts/eval/compare_functional_benchmark_reports.py",
            "scripts/eval/gate_functional_benchmark.py",
        ],
        obsidian_or_note_paths=[],
        commands=[
            "npm run benchmark:coding-agents",
            "npm run benchmark:coding-agents:compare",
            "npm run benchmark:coding-agents:gate",
        ],
        expected_outputs=["functional score", "comparison report", "gate pass/fail"],
    ),
    CodingSystem(
        system_id="agent_bus",
        name="SCBE Agent Bus",
        purpose="Route tasks through local and package-level agent bus surfaces with receipts and role separation.",
        best_for=["multi-agent task routing", "operator control", "headless agent work", "daily tool use"],
        benchmark_role="orchestration_surface",
        primary_paths=[
            "agents/agent_bus.py",
            "agents/agent_bus_cli.py",
            "packages/agent-bus/README.md",
            "packages/agent-bus-py/README.md",
        ],
        obsidian_or_note_paths=["docs/archive/agent_bus_notes.md"],
        commands=["python agents/agent_bus_cli.py --help"],
        expected_outputs=["task route", "consensus record", "agent receipt"],
    ),
    CodingSystem(
        system_id="swarm_router",
        name="SCBE Swarm Router",
        purpose="Run local/cloud coding lanes, block low-quality outputs, and produce benchmark/consensus artifacts.",
        best_for=["headless coding swarms", "free-first model routing", "benchmark-improvement loops"],
        benchmark_role="swarm_surface",
        primary_paths=[
            "scripts/system/openclaw_swarm.py",
            "scripts/system/scbe_swarm_router.py",
            "scripts/benchmark/openclaw_swarm_benchmark.py",
        ],
        obsidian_or_note_paths=[],
        commands=[
            "python scripts/benchmark/openclaw_swarm_benchmark.py --mode semantic",
            "python scripts/benchmark/openclaw_swarm_benchmark.py --mode loop",
            "python scripts/benchmark/openclaw_swarm_benchmark.py --mode public-parallel",
        ],
        expected_outputs=["semantic_task_variables", "weakness_loop", "geometric_consensus", "information_ray_trace"],
    ),
    CodingSystem(
        system_id="trust_self_tune_loop",
        name="Fibonacci Trust Ladder + Turing Self-Tune Loop",
        purpose="Convert accepted/rejected agent turns into trust-weighted SFT/DPO feedback "
        "for later model improvement.",
        best_for=["self-tuning", "DPO pair weighting", "trust decay", "benchmark rerun closure"],
        benchmark_role="feedback_surface",
        primary_paths=[
            "python/scbe/history_reducer.py",
            "tests/governance/test_history_reducer.py",
            "scripts/benchmark/openclaw_swarm_benchmark.py",
        ],
        obsidian_or_note_paths=[
            "notes/theory/fibonacci-trust-ladder.md",
            "notes/theory/turing-self-tuning.md",
            "notes/theory/turing-test-research-synthesis.md",
        ],
        commands=[
            "pytest tests/governance/test_history_reducer.py -q",
            "python scripts/benchmark/openclaw_swarm_benchmark.py --mode loop",
        ],
        expected_outputs=[
            "trust_ladder_report",
            "betrayal_count",
            "trust_factor",
            "chosen/rejected DPO weighting cue",
        ],
    ),
    CodingSystem(
        system_id="public_agentic_eval",
        name="Public Agentic Evaluation Adapter",
        purpose="Bridge local SCBE agent runs toward public-style CLI and SWE-bench/Terminal-Bench comparisons.",
        best_for=["outside benchmark comparison", "cost/speed tracking", "public readiness evidence"],
        benchmark_role="public_adapter_surface",
        primary_paths=[
            "scripts/benchmark/public_agentic_cli_suite.py",
            "scripts/benchmark/external_agentic_eval_driver.py",
            "config/eval/public_agentic_cli_suite.v1.json",
            "config/eval/public_agentic_benchmark_sources.v1.json",
        ],
        obsidian_or_note_paths=["docs/benchmarks/PUBLIC_AGENTIC_CLI_BENCHMARK_PLAN.md"],
        commands=["npm run benchmark:agentic:external"],
        expected_outputs=["adapter readiness", "cost/speed fields", "public-style task results"],
    ),
    CodingSystem(
        system_id="sacred_eggs",
        name="Sacred Eggs / Kernel Concepts",
        purpose="Reference kernel-like conceptual primitives and reusable system objects for coding-system design.",
        best_for=["architecture grounding", "system object analogies", "training context"],
        benchmark_role="concept_surface",
        primary_paths=["packages/kernel/src/sacredEggs.ts", "tests/test_sacred_egg_registry.py"],
        obsidian_or_note_paths=[
            "notes/round-table/2026-03-17-sacred-egg-model-genesis.md",
            "training-data/research_bridge_smoke/avalon-bridge-20260318T091500Z/sources/obsidian/"
            "b6d29f9c26_2026-03-17-sacred-egg-model-genesis.md",
        ],
        commands=["python scripts/sacred_egg_benchmark.py"],
        expected_outputs=["egg registry", "concept mapping", "benchmark notes"],
    ),
)


def _exists(rel_path: str) -> bool:
    return (REPO_ROOT / rel_path).exists()


def build_registry() -> dict[str, Any]:
    systems: list[dict[str, Any]] = []
    for system in SYSTEMS:
        payload = asdict(system)
        all_paths = [*system.primary_paths, *system.obsidian_or_note_paths]
        payload["path_status"] = {path: _exists(path) for path in all_paths}
        payload["coverage"] = {
            "paths_total": len(all_paths),
            "paths_present": sum(1 for path in all_paths if _exists(path)),
        }
        systems.append(payload)
    return {
        "schema": "scbe_coding_system_registry_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "scripts/system/build_coding_system_registry.py",
        "claim_boundary": "Registry of existing local coding systems and notes; not a public benchmark score.",
        "systems": systems,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build SCBE coding-system registry.")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    output = Path(args.output)
    payload = build_registry()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(output), "systems": len(payload["systems"])}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
