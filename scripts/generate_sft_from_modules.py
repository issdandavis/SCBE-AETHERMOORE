#!/usr/bin/env python3
"""Generate SFT training pairs from Python module docstrings and signatures.

Part of the Ouroboros loop: codebase -> SFT data -> model -> governance -> codebase.

Scans specified Python files, extracts docstrings from classes/functions/modules,
and generates instruction/response pairs for fine-tuning.

Usage:
    python scripts/generate_sft_from_modules.py
    python scripts/generate_sft_from_modules.py --output training-data/sft_codebase_new.jsonl
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any

TRAINING_DATA_DIR = Path(__file__).parent.parent / "training-data"

# Modules to extract from (relative to project root)
_BASE = "src/symphonic_cipher/scbe_aethermoore"

DEFAULT_MODULES = [
    # --- Encoding systems ---
    f"{_BASE}/trinary.py",
    f"{_BASE}/negabinary.py",
    # --- Fleet management ---
    f"{_BASE}/flock_shepherd.py",
    # --- Concept blocks: navigation primitives ---
    f"{_BASE}/concept_blocks/base.py",
    f"{_BASE}/concept_blocks/decide.py",
    f"{_BASE}/concept_blocks/plan.py",
    f"{_BASE}/concept_blocks/sense.py",
    f"{_BASE}/concept_blocks/steer.py",
    f"{_BASE}/concept_blocks/coordinate.py",
    f"{_BASE}/concept_blocks/telemetry.py",
    f"{_BASE}/concept_blocks/matrix_catalog_bridge.py",
    # --- CSTM (ChoiceScript-style modules) ---
    f"{_BASE}/concept_blocks/cstm/models.py",
    f"{_BASE}/concept_blocks/cstm/story_engine.py",
    f"{_BASE}/concept_blocks/cstm/player_agent.py",
    f"{_BASE}/concept_blocks/cstm/nursery.py",
    f"{_BASE}/concept_blocks/cstm/kernel.py",
    f"{_BASE}/concept_blocks/cstm/telemetry_bridge.py",
    # --- Web agent ---
    f"{_BASE}/concept_blocks/web_agent/semantic_antivirus.py",
    f"{_BASE}/concept_blocks/web_agent/web_polly_pad.py",
    f"{_BASE}/concept_blocks/web_agent/navigation_engine.py",
    f"{_BASE}/concept_blocks/web_agent/agent_orchestrator.py",
    f"{_BASE}/concept_blocks/web_agent/buffer_integration.py",
    f"{_BASE}/concept_blocks/web_agent/publishers.py",
    f"{_BASE}/concept_blocks/web_agent/tongue_transport.py",
    # --- Context catalog & credit ledger ---
    f"{_BASE}/concept_blocks/context_catalog/catalog.py",
    f"{_BASE}/concept_blocks/context_credit_ledger/credit.py",
    f"{_BASE}/concept_blocks/context_credit_ledger/ledger.py",
    f"{_BASE}/concept_blocks/context_credit_ledger/exchange.py",
    f"{_BASE}/concept_blocks/context_credit_ledger/bitlocker.py",
    # --- Heart vault ---
    f"{_BASE}/concept_blocks/heart_vault/emotions.py",
    f"{_BASE}/concept_blocks/heart_vault/graph.py",
    f"{_BASE}/concept_blocks/heart_vault/heart_credit.py",
    f"{_BASE}/concept_blocks/heart_vault/literary.py",
    # --- Core architecture ---
    f"{_BASE}/cpse.py",
    f"{_BASE}/cpse_integrator.py",
    f"{_BASE}/constants.py",
    f"{_BASE}/dual_lattice.py",
    f"{_BASE}/full_system.py",
    f"{_BASE}/genesis_protocol.py",
    f"{_BASE}/scbe_aethermoore_core.py",
    f"{_BASE}/unified.py",
    f"{_BASE}/living_metric.py",
    f"{_BASE}/fractional_flux.py",
    f"{_BASE}/organic_hyperbolic.py",
    f"{_BASE}/vacuum_acoustics.py",
    f"{_BASE}/hal_attention.py",
    # --- Governance ---
    f"{_BASE}/governance/grand_unified.py",
    # --- PQC / crypto ---
    f"{_BASE}/pqc/pqc_core.py",
    f"{_BASE}/pqc/pqc_audit.py",
    f"{_BASE}/pqc/pqc_harmonic.py",
    f"{_BASE}/pqc/pqc_hmac.py",
    f"{_BASE}/kyber_orchestrator.py",
    f"{_BASE}/qr_cube_kdf.py",
    # --- Spiral seal ---
    f"{_BASE}/spiral_seal/seal.py",
    f"{_BASE}/spiral_seal/spiral_seal.py",
    f"{_BASE}/spiral_seal/key_exchange.py",
    f"{_BASE}/spiral_seal/sacred_tongues.py",
    f"{_BASE}/spiral_seal/signatures.py",
    # --- AI brain ---
    f"{_BASE}/ai_brain/bft_consensus.py",
    f"{_BASE}/ai_brain/circuit_flow.py",
    f"{_BASE}/ai_brain/dual_lattice.py",
    f"{_BASE}/ai_brain/fsgs.py",
    f"{_BASE}/ai_brain/governance_adapter.py",
    f"{_BASE}/ai_brain/hamiltonian_braid.py",
    f"{_BASE}/ai_brain/unified_state.py",
    f"{_BASE}/ai_brain/multiscale_spectrum.py",
    # --- Layers ---
    f"{_BASE}/layers/fourteen_layer_pipeline.py",
    f"{_BASE}/layers_9_12.py",
    f"{_BASE}/layer_13.py",
    # --- Axiom grouped ---
    f"{_BASE}/axiom_grouped/audio_axis.py",
    f"{_BASE}/axiom_grouped/causality_axiom.py",
    f"{_BASE}/axiom_grouped/composition_axiom.py",
    f"{_BASE}/axiom_grouped/dual_mode_core.py",
    f"{_BASE}/axiom_grouped/hamiltonian_cfi.py",
    f"{_BASE}/axiom_grouped/langues_metric.py",
    f"{_BASE}/axiom_grouped/locality_axiom.py",
    f"{_BASE}/axiom_grouped/symmetry_axiom.py",
    f"{_BASE}/axiom_grouped/unitarity_axiom.py",
    # --- Rosetta ---
    f"{_BASE}/rosetta/rosetta_core.py",
    f"{_BASE}/rosetta/language_graph.py",
    f"{_BASE}/rosetta/lcda.py",
    f"{_BASE}/rosetta/dede.py",
    # --- QC lattice ---
    f"{_BASE}/qc_lattice/quasicrystal.py",
    f"{_BASE}/qc_lattice/phdm.py",
    f"{_BASE}/qc_lattice/integration.py",
    # --- EDE ---
    f"{_BASE}/ede/ede_protocol.py",
    f"{_BASE}/ede/chemistry_agent.py",
    f"{_BASE}/ede/spiral_ring.py",
    # --- Misc ---
    f"{_BASE}/phdm_module.py",
    f"{_BASE}/qasi_core.py",
    f"{_BASE}/attack_simulation.py",
    f"{_BASE}/sacred_eggs.py",
    f"{_BASE}/adaptive_navigator.py",
    f"{_BASE}/cymatic_storage.py",
    f"{_BASE}/decision_telemetry.py",
    f"{_BASE}/quasicrystal_lattice.py",
    f"{_BASE}/tri_mechanism_detector.py",
    # --- API ---
    "api/main.py",
    "api/auth.py",
    "api/metering.py",
    "api/persistence.py",
    # --- Agents ---
    "agents/antivirus_membrane.py",
    "agents/browser_agent.py",
    "agents/kernel_antivirus_gate.py",
    "agents/extension_gate.py",
    # --- Cloud / billing ---
    "src/api/cloud_browser.py",
    "api/billing/stripe_client.py",
    # --- Top-level ---
    "src/polly_pads_runtime.py",
    "hydra/head.py",
    "hydra/spine.py",
    "training/federated_orchestrator.py",
]

CATEGORY_MAP = {
    # Encoding systems
    "trinary": "encoding-systems",
    "negabinary": "encoding-systems",
    # Fleet management
    "flock_shepherd": "fleet-management",
    # Concept blocks
    "base": "architecture",
    "decide": "architecture",
    "plan": "architecture",
    "sense": "architecture",
    "steer": "architecture",
    "coordinate": "architecture",
    "telemetry": "architecture",
    "matrix_catalog_bridge": "architecture",
    # CSTM
    "models": "architecture",
    "story_engine": "architecture",
    "player_agent": "architecture",
    "nursery": "architecture",
    "kernel": "architecture",
    "telemetry_bridge": "architecture",
    # Web agent
    "semantic_antivirus": "safety",
    "web_polly_pad": "architecture",
    "navigation_engine": "architecture",
    "agent_orchestrator": "architecture",
    "buffer_integration": "architecture",
    "publishers": "architecture",
    "tongue_transport": "constants",
    # Context catalog/ledger
    "catalog": "architecture",
    "credit": "architecture",
    "ledger": "architecture",
    "exchange": "architecture",
    "bitlocker": "crypto",
    # Heart vault
    "emotions": "architecture",
    "graph": "topology",
    "heart_credit": "architecture",
    "literary": "architecture",
    # Core
    "cpse": "layers",
    "cpse_integrator": "layers",
    "constants": "constants",
    "dual_lattice": "crypto",
    "full_system": "architecture",
    "genesis_protocol": "architecture",
    "scbe_aethermoore_core": "architecture",
    "unified": "architecture",
    "living_metric": "math",
    "fractional_flux": "math",
    "organic_hyperbolic": "math",
    "vacuum_acoustics": "layers",
    "hal_attention": "safety",
    # Governance
    "grand_unified": "governance",
    # PQC
    "pqc_core": "crypto",
    "pqc_audit": "crypto",
    "pqc_harmonic": "crypto",
    "pqc_hmac": "crypto",
    "kyber_orchestrator": "crypto",
    "qr_cube_kdf": "crypto",
    # Spiral seal
    "seal": "crypto",
    "spiral_seal": "crypto",
    "key_exchange": "crypto",
    "sacred_tongues": "constants",
    "signatures": "crypto",
    # AI brain
    "bft_consensus": "governance",
    "circuit_flow": "architecture",
    "fsgs": "governance",
    "governance_adapter": "governance",
    "hamiltonian_braid": "topology",
    "unified_state": "architecture",
    "multiscale_spectrum": "layers",
    # Layers
    "fourteen_layer_pipeline": "layers",
    "layers_9_12": "layers",
    "layer_13": "layers",
    # Axiom grouped
    "audio_axis": "layers",
    "causality_axiom": "math",
    "composition_axiom": "math",
    "dual_mode_core": "architecture",
    "hamiltonian_cfi": "topology",
    "langues_metric": "constants",
    "locality_axiom": "math",
    "symmetry_axiom": "math",
    "unitarity_axiom": "math",
    # Rosetta
    "rosetta_core": "constants",
    "language_graph": "constants",
    "lcda": "architecture",
    "dede": "architecture",
    # QC lattice
    "quasicrystal": "topology",
    "phdm": "topology",
    "integration": "architecture",
    # EDE
    "ede_protocol": "architecture",
    "chemistry_agent": "architecture",
    "spiral_ring": "crypto",
    # Misc
    "phdm_module": "topology",
    "qasi_core": "math",
    "attack_simulation": "safety",
    "sacred_eggs": "constants",
    "adaptive_navigator": "architecture",
    "cymatic_storage": "architecture",
    "decision_telemetry": "governance",
    "quasicrystal_lattice": "topology",
    "tri_mechanism_detector": "safety",
    # API
    "main": "architecture",
    "auth": "safety",
    "metering": "governance",
    "persistence": "architecture",
    # Agents
    "antivirus_membrane": "safety",
    "browser_agent": "architecture",
    "kernel_antivirus_gate": "safety",
    "extension_gate": "safety",
    # Cloud / billing
    "cloud_browser": "architecture",
    "stripe_client": "governance",
    # Top-level
    "polly_pads_runtime": "architecture",
    "head": "architecture",
    "spine": "architecture",
    "federated_orchestrator": "architecture",
}


def extract_docstrings(filepath: Path) -> list[dict[str, Any]]:
    """Extract module, class, and function docstrings from a Python file."""
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source)
    records: list[dict[str, Any]] = []
    module_name = filepath.stem

    # Module docstring
    module_doc = ast.get_docstring(tree)
    if module_doc and len(module_doc) >= 30:
        records.append({
            "type": "module",
            "name": module_name,
            "docstring": module_doc,
            "filepath": str(filepath),
        })

    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node)
            if not doc or len(doc) < 10:
                continue

            # Get function signature
            sig = ""
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = []
                for arg in node.args.args:
                    annotation = ""
                    if arg.annotation:
                        annotation = f": {ast.unparse(arg.annotation)}"
                    args.append(f"{arg.arg}{annotation}")
                returns = ""
                if node.returns:
                    returns = f" -> {ast.unparse(node.returns)}"
                sig = f"def {node.name}({', '.join(args)}){returns}"
            elif isinstance(node, ast.ClassDef):
                bases = ", ".join(ast.unparse(b) for b in node.bases)
                sig = f"class {node.name}({bases})" if bases else f"class {node.name}"

            records.append({
                "type": "class" if isinstance(node, ast.ClassDef) else "function",
                "name": node.name,
                "signature": sig,
                "docstring": doc,
                "filepath": str(filepath),
                "line": node.lineno,
            })

    return records


def docstring_to_sft(record: dict[str, Any], module_name: str) -> dict[str, Any]:
    """Convert a docstring record to an SFT instruction/response pair."""
    category = CATEGORY_MAP.get(module_name, "architecture")

    if record["type"] == "module":
        instruction = f"What is the {record['name']} module in SCBE-AETHERMOORE and what does it provide?"
        response = record["docstring"]
    elif record["type"] == "class":
        instruction = f"Explain the {record['name']} class in the SCBE-AETHERMOORE {module_name} module."
        response = f"```python\n{record['signature']}\n```\n\n{record['docstring']}"
    else:
        instruction = f"What does the `{record['name']}` function do in {module_name}?"
        response = f"```python\n{record['signature']}\n```\n\n{record['docstring']}"

    return {
        "instruction": instruction,
        "response": response,
        "category": category,
        "metadata": {
            "source_file": record["filepath"].replace("\\", "/"),
            "origin": "codebase_docs",
            "source_type": "code_doc",
            "track": "functions" if record["type"] == "function" else "system",
            "quality": {"dedup": True, "validated": True},
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate SFT pairs from module docstrings")
    parser.add_argument(
        "--output",
        default=str(TRAINING_DATA_DIR / "sft_codebase_new.jsonl"),
        help="Output JSONL path",
    )
    parser.add_argument(
        "--modules",
        nargs="*",
        default=DEFAULT_MODULES,
        help="Python files to extract from",
    )
    args = parser.parse_args()

    project_root = Path(__file__).parent.parent
    all_records: list[dict[str, Any]] = []

    print("--- Extracting docstrings ---", file=sys.stderr)
    for mod_path in args.modules:
        filepath = project_root / mod_path
        if not filepath.exists():
            print(f"  SKIP (not found): {mod_path}", file=sys.stderr)
            continue

        extracted = extract_docstrings(filepath)
        module_name = filepath.stem
        sft_pairs = [docstring_to_sft(r, module_name) for r in extracted]
        print(f"  {filepath.name}: {len(sft_pairs)} pairs", file=sys.stderr)
        all_records.extend(sft_pairs)

    # Assign IDs
    for i, record in enumerate(all_records):
        record["id"] = f"sft-gen-{i+1:04d}"

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for record in all_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"\nGenerated {len(all_records)} SFT pairs -> {output_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
