#!/usr/bin/env python3
"""Long-form compound decomposition/recomposition benchmark.

This benchmark tests the product layer of the SCBE chemistry CLI idea:

1. Parse a natural-language compound task.
2. Load a real molecular graph with RDKit.
3. Decompose it into formula, atom counts, descriptors, fragments, and a
   dimensional-analysis sample path.
4. Pass through a "mud step" where graph topology is dropped and only conserved
   field cards remain.
5. Recompose by searching a candidate field and selecting the known solution.

The benchmark deliberately records atom-only ambiguity. If the system can only
count atoms, it should fail or remain ambiguous for isomers. The value is in the
multi-lattice field: atom bag + descriptor field + fragment cards + receipts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.reaction_state import (
    ReactionEndpoint,
    ReactionRecalculation,
    build_reaction_state_packet,
)

OUT_DIR = (
    REPO_ROOT / "artifacts" / "benchmarks" / "compound_decomposition_recomposition"
)
AVOGADRO = 6.02214076e23


@dataclass(frozen=True)
class CompoundCase:
    case_id: str
    prompt: str
    name: str
    smiles: str
    sample_grams: float
    expected_formula: str
    required_smarts: tuple[str, ...]


@dataclass(frozen=True)
class Candidate:
    name: str
    smiles: str


CASES: tuple[CompoundCase, ...] = (
    CompoundCase(
        case_id="ethanol_from_atom_mud",
        prompt="Decompose 46.069 grams of ethanol, drop to atomic mud at step 5, then recompose the known alcohol.",
        name="ethanol",
        smiles="CCO",
        sample_grams=46.069,
        expected_formula="C2H6O",
        required_smarts=("[OX2H]",),
    ),
    CompoundCase(
        case_id="aspirin_from_functional_cards",
        prompt="Decompose aspirin into atom counts and functional cards, then recover it after the mud step.",
        name="aspirin",
        smiles="CC(=O)Oc1ccccc1C(=O)O",
        sample_grams=180.158,
        expected_formula="C9H8O4",
        required_smarts=("CC(=O)O", "c1ccccc1", "C(=O)O"),
    ),
    CompoundCase(
        case_id="caffeine_from_heterocycle_cards",
        prompt="Track caffeine through atomic decomposition and recompose using heterocycle and carbonyl cards.",
        name="caffeine",
        smiles="Cn1cnc2c1c(=O)n(C)c(=O)n2C",
        sample_grams=194.19,
        expected_formula="C8H10N4O2",
        required_smarts=("[#6](=O)[#7]", "[n]c[n]"),
    ),
)


CANDIDATES: tuple[Candidate, ...] = (
    Candidate("ethanol", "CCO"),
    Candidate("dimethyl ether", "COC"),
    Candidate("propan-1-ol", "CCCO"),
    Candidate("propan-2-ol", "CC(C)O"),
    Candidate("aspirin", "CC(=O)Oc1ccccc1C(=O)O"),
    Candidate("salicylic acid", "O=C(O)c1ccccc1O"),
    Candidate("methyl salicylate", "COC(=O)c1ccccc1O"),
    Candidate("acetaminophen", "CC(=O)Nc1ccc(O)cc1"),
    Candidate("caffeine", "Cn1cnc2c1c(=O)n(C)c(=O)n2C"),
    Candidate("theobromine", "CN1C=NC2=C1C(=O)NC(=O)N2C"),
    Candidate("theophylline", "Cn1c(=O)c2[nH]cnc2n(C)c1=O"),
)


def utc_now() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def git_commit() -> str:
    import subprocess

    proc = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return proc.stdout.strip() if proc.returncode == 0 else "unknown"


def require_rdkit():
    try:
        from rdkit import Chem
        from rdkit.Chem import Descriptors, Lipinski, rdMolDescriptors
    except Exception as exc:  # pragma: no cover - environment specific
        raise RuntimeError(f"RDKit is required for this benchmark: {exc!r}") from exc
    return Chem, Descriptors, Lipinski, rdMolDescriptors


def mol_from_smiles(smiles: str):
    Chem, _, _, _ = require_rdkit()
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        raise ValueError(f"invalid SMILES: {smiles}")
    return mol


def canonical_smiles(smiles: str) -> str:
    Chem, _, _, _ = require_rdkit()
    return Chem.MolToSmiles(mol_from_smiles(smiles), canonical=True)


def formula_atom_counts(formula: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for element, count in re.findall(r"([A-Z][a-z]?)(\d*)", formula):
        counts[element] = counts.get(element, 0) + int(count or "1")
    return counts


def descriptor_cards(smiles: str) -> dict[str, Any]:
    Chem, Descriptors, Lipinski, rdMolDescriptors = require_rdkit()
    mol = mol_from_smiles(smiles)
    carbonyl = Chem.MolFromSmarts("[CX3]=[OX1]")
    hydroxyl = Chem.MolFromSmarts("[OX2H]")
    return {
        "canonical_smiles": Chem.MolToSmiles(mol, canonical=True),
        "formula": rdMolDescriptors.CalcMolFormula(mol),
        "exact_mw": round(float(Descriptors.ExactMolWt(mol)), 6),
        "mol_wt": round(float(Descriptors.MolWt(mol)), 6),
        "hbd": int(Lipinski.NumHDonors(mol)),
        "hba": int(Lipinski.NumHAcceptors(mol)),
        "tpsa": round(float(rdMolDescriptors.CalcTPSA(mol)), 6),
        "ring_count": int(rdMolDescriptors.CalcNumRings(mol)),
        "aromatic_ring_count": int(rdMolDescriptors.CalcNumAromaticRings(mol)),
        "carbonyl_count": len(mol.GetSubstructMatches(carbonyl)),
        "hydroxyl_count": len(mol.GetSubstructMatches(hydroxyl)),
    }


def required_fragment_hits(
    smiles: str, smarts_list: tuple[str, ...]
) -> dict[str, bool]:
    Chem, _, _, _ = require_rdkit()
    mol = mol_from_smiles(smiles)
    hits = {}
    for smarts in smarts_list:
        pattern = Chem.MolFromSmarts(smarts)
        hits[smarts] = bool(pattern is not None and mol.HasSubstructMatch(pattern))
    return hits


def dimensional_path(
    sample_grams: float, mol_wt: float, atom_counts: dict[str, int]
) -> dict[str, Any]:
    moles = sample_grams / mol_wt
    molecules = moles * AVOGADRO
    return {
        "sample_grams": sample_grams,
        "molar_mass_g_per_mol": mol_wt,
        "moles": moles,
        "molecules": molecules,
        "atom_totals": {
            element: molecules * count for element, count in atom_counts.items()
        },
    }


def candidate_score(
    candidate: Candidate, mud: dict[str, Any], required_smarts: tuple[str, ...]
) -> dict[str, Any]:
    desc = descriptor_cards(candidate.smiles)
    fragment_hits = required_fragment_hits(candidate.smiles, required_smarts)
    formula_match = desc["formula"] == mud["atom_bag"]["formula"]
    descriptor_keys = (
        "hbd",
        "hba",
        "ring_count",
        "aromatic_ring_count",
        "carbonyl_count",
        "hydroxyl_count",
    )
    descriptor_matches = sum(
        1 for key in descriptor_keys if desc[key] == mud["descriptor_cards"][key]
    )
    fragment_matches = sum(1 for ok in fragment_hits.values() if ok)
    exact_mw_delta = abs(
        float(desc["exact_mw"]) - float(mud["descriptor_cards"]["exact_mw"])
    )
    score = 0
    score += 100 if formula_match else 0
    score += descriptor_matches * 10
    score += fragment_matches * 25
    score -= min(20, exact_mw_delta)
    return {
        "name": candidate.name,
        "smiles": candidate.smiles,
        "canonical_smiles": desc["canonical_smiles"],
        "formula": desc["formula"],
        "score": round(float(score), 6),
        "formula_match": formula_match,
        "descriptor_matches": descriptor_matches,
        "fragment_hits": fragment_hits,
        "exact_mw_delta": round(float(exact_mw_delta), 8),
    }


def run_case(case: CompoundCase) -> dict[str, Any]:
    t0 = time.perf_counter()
    desc = descriptor_cards(case.smiles)
    atom_counts = formula_atom_counts(desc["formula"])
    expected_canonical = canonical_smiles(case.smiles)
    dim = dimensional_path(case.sample_grams, desc["mol_wt"], atom_counts)

    steps = [
        {
            "step": 1,
            "name": "intent_parse",
            "output": {"prompt": case.prompt, "compound": case.name},
        },
        {
            "step": 2,
            "name": "graph_load",
            "output": {"smiles": case.smiles, "canonical_smiles": expected_canonical},
        },
        {
            "step": 3,
            "name": "formula_decomposition",
            "output": {"formula": desc["formula"], "atom_counts": atom_counts},
        },
        {"step": 4, "name": "dimensional_analysis", "output": dim},
        {
            "step": 5,
            "name": "atomic_mud",
            "output": {
                "topology_retained": False,
                "atom_bag": {"formula": desc["formula"], "atom_counts": atom_counts},
                "lost_information": [
                    "bond_order",
                    "connectivity",
                    "stereochemistry",
                    "conformation",
                ],
            },
        },
    ]

    mud = {
        "atom_bag": steps[-1]["output"]["atom_bag"],
        "descriptor_cards": desc,
        "required_smarts": case.required_smarts,
    }
    atom_only_candidates = [
        candidate.name
        for candidate in CANDIDATES
        if descriptor_cards(candidate.smiles)["formula"] == desc["formula"]
    ]
    scored = [
        candidate_score(candidate, mud, case.required_smarts)
        for candidate in CANDIDATES
    ]
    scored.sort(key=lambda item: item["score"], reverse=True)
    selected = scored[0]
    ok = (
        selected["canonical_smiles"] == expected_canonical
        and desc["formula"] == case.expected_formula
    )

    steps.append(
        {
            "step": 6,
            "name": "recomposition_search",
            "output": {
                "atom_only_candidates": atom_only_candidates,
                "atom_only_ambiguous": len(atom_only_candidates) != 1,
                "selected": selected,
                "top_candidates": scored[:5],
            },
        }
    )
    steps.append(
        {
            "step": 7,
            "name": "known_solution_check",
            "output": {
                "expected_name": case.name,
                "expected_formula": case.expected_formula,
                "expected_canonical_smiles": expected_canonical,
                "selected_canonical_smiles": selected["canonical_smiles"],
                "ok": ok,
            },
        }
    )
    packet = build_reaction_state_packet(
        domain="chem",
        step=7,
        bounded_operation="decompose_atom_mud_recompose",
        source=ReactionEndpoint(
            identity=case.name,
            representation="smiles",
            language="chem",
            tongue="KO",
            payload_sha256=sha256_text(case.smiles),
            metadata={"smiles": case.smiles, "formula": desc["formula"]},
        ),
        target=ReactionEndpoint(
            identity=selected["name"],
            representation="canonical_smiles",
            language="chem",
            tongue="DR",
            payload_sha256=sha256_text(selected["canonical_smiles"]),
            metadata={
                "canonical_smiles": selected["canonical_smiles"],
                "formula": selected["formula"],
            },
        ),
        semantic_engravings=[
            "formula and atom counts preserved through mud step",
            "descriptor and fragment cards used for recomposition",
            f"selected candidate score={selected['score']}",
        ],
        loss_notes=[
            "topology dropped at atomic mud step",
            "bond order, connectivity, stereochemistry, and conformation not retained in atom bag",
        ],
        recalculation=ReactionRecalculation(
            scientific_checks_ok=ok,
            unit_checks_ok=math.isfinite(dim["moles"])
            and math.isfinite(dim["molecules"]),
            identity_ok=selected["canonical_smiles"] == expected_canonical,
            extra={
                "formula_ok": desc["formula"] == case.expected_formula,
                "atom_only_ambiguous": len(atom_only_candidates) != 1,
                "fragment_hits": selected["fragment_hits"],
            },
        ),
        identity_preserved=ok,
        recovery_evidence=[
            "descriptor cards",
            "fragment SMARTS cards",
            "canonical SMILES recalculation",
            "known solution check",
        ],
        claim_boundary=[
            "computational chemistry benchmark",
            "not wet-lab synthesis",
            "not biological efficacy proof",
            "not medical advice",
        ],
    )

    return {
        "case_id": case.case_id,
        "ok": ok,
        "duration_ms": int((time.perf_counter() - t0) * 1000),
        "mud_step": 5,
        "claim": "Long-form compound decomposition can recover a known solution after topology loss only by carrying multi-lattice evidence cards.",
        "steps": steps,
        "receipt": {
            "input_sha256": sha256_text(json.dumps(asdict(case), sort_keys=True)),
            "selected_sha256": sha256_text(json.dumps(selected, sort_keys=True)),
            "engine": "rdkit",
            "safety_decision": "ALLOW_COMPUTATIONAL_ONLY",
            "claim_boundary": "computational chemistry benchmark; not wet-lab synthesis, efficacy proof, or medical advice",
        },
        "reaction_state_packet": packet.to_dict(),
    }


def build_report(out_dir: Path) -> dict[str, Any]:
    try:
        require_rdkit()
        rdkit_available = True
        rdkit_error = None
    except RuntimeError as exc:
        rdkit_available = False
        rdkit_error = str(exc)

    cases = [run_case(case) for case in CASES] if rdkit_available else []
    passed = sum(1 for case in cases if case["ok"])
    report = {
        "schema_version": "scbe_compound_decomposition_recomposition_v1",
        "generated_at_utc": utc_now(),
        "commit": git_commit(),
        "claim_boundary": [
            "Computational compound decomposition/recomposition benchmark using RDKit.",
            "Tests atom-bag ambiguity plus descriptor/fragment recomposition.",
            "Not wet-lab synthesis, biological efficacy proof, dosing guidance, or medical advice.",
        ],
        "summary": {
            "decision": "PASS" if rdkit_available and passed == len(CASES) else "HOLD",
            "rdkit_available": rdkit_available,
            "case_count": len(CASES),
            "passed": passed,
            "pass_rate": passed / len(CASES) if CASES else 0.0,
            "mud_step": 5,
            "rdkit_error": rdkit_error,
        },
        "field_model": {
            "cards": [
                "atom_bag",
                "dimensional_analysis",
                "descriptor_cards",
                "fragment_cards",
                "candidate_scores",
            ],
            "lesson": "Atom counts alone do not preserve chemical topology; recomposition needs extra conserved fields.",
        },
        "cases": cases,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    payload = json.dumps(report, indent=2)
    (out_dir / f"compound_decomposition_recomposition_{stamp}.json").write_text(
        payload, encoding="utf-8"
    )
    (out_dir / "latest_report.json").write_text(payload, encoding="utf-8")
    write_markdown(report, out_dir / f"compound_decomposition_recomposition_{stamp}.md")
    write_markdown(report, out_dir / "LATEST.md")
    return report


def write_markdown(report: dict[str, Any], path: Path) -> None:
    summary = report["summary"]
    lines = [
        "# SCBE Compound Decomposition/Recomposition Benchmark",
        "",
        f"- Generated: `{report['generated_at_utc']}`",
        f"- Commit: `{report['commit']}`",
        f"- Decision: `{summary['decision']}`",
        f"- Passed: `{summary['passed']}/{summary['case_count']}`",
        "",
        "## Cases",
        "",
        "| Case | OK | Mud Step | Atom-Only Ambiguous | Selected |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for case in report["cases"]:
        recomposition = next(
            step for step in case["steps"] if step["name"] == "recomposition_search"
        )
        selected = recomposition["output"]["selected"]["name"]
        ambiguous = recomposition["output"]["atom_only_ambiguous"]
        lines.append(
            f"| {case['case_id']} | {case['ok']} | {case['mud_step']} | {ambiguous} | {selected} |"
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "This is a computational chemistry benchmark. It does not provide wet-lab synthesis steps, biological efficacy proof, dosing guidance, or medical advice.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    args = parser.parse_args()
    report = build_report(Path(args.out_dir))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        summary = report["summary"]
        print(
            "compound decomposition/recomposition: "
            f"decision={summary['decision']} passed={summary['passed']}/{summary['case_count']} "
            f"rdkit={summary['rdkit_available']}"
        )
        print(f"report={Path(args.out_dir) / 'LATEST.md'}")
    return 0 if report["summary"]["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
