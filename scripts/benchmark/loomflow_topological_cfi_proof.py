#!/usr/bin/env python3
"""Build a deterministic reduction-to-practice packet for topological CFI.

This packet proves a deliberately narrow technical statement. It does not
opine on patent validity, novelty, infringement, or the contents of a filed
specification that has not been exported from Patent Center.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from python.scbe.loomflow import (  # noqa: E402
    EXAMPLES,
    parse,
    trace_execution,
    verify,
    verify_trace_integrity,
)

OUT = ROOT / "docs" / "legal" / "patent-workbench" / "claim-evidence"
JSON_OUT = OUT / "topological_linearization_cfi_proof.json"
MD_OUT = OUT / "topological_linearization_cfi_proof.md"
NEUROGOLF_RECORD = Path(r"C:\dev\neurogolf\reports\arc_record_player\receipt.json")
NEUROGOLF_COLOR = Path(r"C:\dev\neurogolf\cleanroom\color_chroma_frontier_20260711\verification_receipt.json")
NEUROGOLF_MATERIAL = Path(r"C:\dev\neurogolf\reports\material_flow_arc_receipt.json")


def sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def run_json(command: Sequence[str]) -> dict[str, Any]:
    try:
        result = subprocess.run(
            list(command),
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=True,
        )
        value = json.loads(result.stdout)
        return value if isinstance(value, dict) else {}
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return {}


def github_evidence() -> dict[str, Any]:
    if shutil.which("gh") is None:
        return {"live_query": False}
    pull = run_json(
        [
            "gh",
            "pr",
            "view",
            "2406",
            "--json",
            "number,title,state,mergedAt,mergeCommit,url",
        ]
    )
    run = run_json(
        [
            "gh",
            "run",
            "view",
            "27793695962",
            "--json",
            "databaseId,conclusion,status,url,headSha,workflowName,jobs",
        ]
    )
    c_agreement = False
    try:
        log = subprocess.run(
            ["gh", "run", "view", "27793695962", "--job", "82248573328", "--log"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
            check=True,
        ).stdout
        c_agreement = all(
            marker in log
            for marker in (
                "c            AGREE        value=15.0",
                "c            AGREE        value=120.0",
            )
        )
    except (OSError, subprocess.SubprocessError):
        pass
    return {
        "live_query": bool(pull and run),
        "pull_request": pull,
        "rosetta_run": run,
        "c_agreement_in_job_log": c_agreement,
    }


def mutation_audit(reference: list[int], instruction_count: int) -> dict[str, Any]:
    attacks: list[tuple[str, list[int]]] = []
    for phase, expected in enumerate(reference):
        for replacement in range(instruction_count):
            if replacement == expected:
                continue
            mutated = list(reference)
            mutated[phase] = replacement
            attacks.append(("pc_substitution", mutated))
    for phase in range(len(reference)):
        attacks.append(("state_deletion", reference[:phase] + reference[phase + 1 :]))
        attacks.append(("state_insertion", reference[:phase] + [reference[0]] + reference[phase:]))
    for phase in range(max(0, len(reference) - 1)):
        mutated = list(reference)
        mutated[phase], mutated[phase + 1] = mutated[phase + 1], mutated[phase]
        if mutated != reference:
            attacks.append(("adjacent_reorder", mutated))
    attacks.append(("post_completion_replay", list(reference) + [reference[0]]))

    by_kind: dict[str, dict[str, int]] = {}
    detected = 0
    for kind, observed in attacks:
        row = by_kind.setdefault(kind, {"attacks": 0, "detected": 0})
        row["attacks"] += 1
        if not verify_trace_integrity(reference, observed)["valid"]:
            detected += 1
            row["detected"] += 1
    return {
        "attack_count": len(attacks),
        "detected_count": detected,
        "detection_rate": detected / len(attacks) if attacks else 0.0,
        "by_kind": by_kind,
        "corpus_scope": "deterministic single-trajectory PC mutations, not a real-world ROP corpus",
    }


def source_hashes() -> dict[str, str | None]:
    paths = [
        ROOT / "python" / "scbe" / "loomflow.py",
        ROOT / "tests" / "test_loomflow.py",
        ROOT / "python" / "scbe" / "material_flow.py",
        ROOT / "tests" / "test_material_flow.py",
        ROOT / "packages" / "kernel" / "src" / "topologicalLinearization.ts",
        ROOT / "tests" / "harmonic" / "topologicalLinearization.test.ts",
        ROOT / "bin" / "scbe-patent.cjs",
        NEUROGOLF_RECORD,
        NEUROGOLF_COLOR,
        Path(r"C:\dev\neurogolf\arc_material_flow.py"),
        NEUROGOLF_MATERIAL,
    ]
    return {str(path): sha256(path) for path in paths}


def build_packet() -> dict[str, Any]:
    examples: dict[str, Any] = {}
    for name, source in EXAMPLES.items():
        program = parse(source)
        trace = trace_execution(program)
        local_faces = verify(program)
        examples[name] = {
            "reference_output": local_faces["reference"],
            "local_face_results": local_faces["results"],
            "local_verified_faces": local_faces["verified"],
            "trace": trace,
            "mutation_audit": mutation_audit(trace["pc_trace"], trace["base_instruction_count"]),
        }

    record = load_json(NEUROGOLF_RECORD)
    color = load_json(NEUROGOLF_COLOR)
    material = load_json(NEUROGOLF_MATERIAL)
    packet = {
        "schema": "scbe.patent-evidence.topological-linearization-cfi.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "application_reference": {
            "provisional": "63/961,403",
            "title": (
                "System and Method for Hyperbolic Geometry-Based Authorization "
                "with Topological Control-Flow Integrity"
            ),
            "filed_specification_export_present": False,
            "boundary": (
                "The workbench records the application metadata, but the official filed "
                "specification and claims are not present in the local evidence drop."
            ),
        },
        "technical_statement_tested": (
            "A control-flow graph or authorized execution trace can be linearized in a "
            "lifted state space by adding a monotonically increasing phase/program-counter "
            "coordinate; repeated base states become unique lifted states, every projected "
            "transition remains authorized by the base topology, and deviations from the "
            "receipted lifted path are detected."
        ),
        "constructive_chain": [
            "Loomflow parses branch, loop, and variable instructions into a finite PC-indexed IR.",
            "Each target face executes the IR through a universal dispatch loop keyed by PC.",
            "The reference interpreter records the actual PC walk.",
            "Phase paired with PC makes loop revisits unique lifted states.",
            "Every adjacent projected PC pair is checked against a static authorized CFG edge.",
            "Trace CFI rejects substitutions, deletions, insertions, reorders, and replay.",
            "Independent target execution compares Python, JavaScript, Rust, and CI C results.",
        ],
        "examples": examples,
        "typescript_constructive_graph_proof": {
            "test": "tests/harmonic/topologicalLinearization.test.ts",
            "statement": (
                "A non-Hamiltonian star base graph has no base Hamiltonian path; a DFS "
                "covering walk lifted by phase yields a unique-state Hamiltonian path "
                "without inventing a base edge."
            ),
        },
        "github_ci": github_evidence(),
        "neurogolf_multimodal_reduction_to_practice": {
            "record_receipt_present": bool(record),
            "ordered_task_count": record.get("task_count"),
            "layers": record.get("layers"),
            "audio_phase_roundtrip": record.get("audio_intent"),
            "color_verification_present": bool(color),
            "color_candidates_all_passed": color.get("all_passed"),
            "color_candidate_count": color.get("candidate_count"),
            "material_flow_receipt_present": bool(material),
            "material_flow_audits": material.get("audits"),
            "role": (
                "A separate application demo: ordered binary geometry, categorical color, "
                "local texture, and verification state are rendered as a surface/audio record."
            ),
        },
        "source_sha256": source_hashes(),
        "support_state": "tested reduction to practice for the stated construction",
        "not_proven": [
            "Patent validity, novelty, non-obviousness, scope, or infringement.",
            "Support in the exact filed claims until the official Patent Center export is supplied.",
            "The broad statement that arbitrary graphs themselves become Hamiltonian.",
            "A 99% real-world ROP detection rate; only the disclosed synthetic mutation corpus is measured here.",
            "Directed whole-CFG coverage where mutually exclusive branches cannot occur in one execution trace.",
        ],
    }
    return packet


def markdown(packet: dict[str, Any]) -> str:
    rows = []
    for name, evidence in packet["examples"].items():
        audit = evidence["mutation_audit"]
        trace = evidence["trace"]
        rows.append(
            f"| `{name}` | {evidence['reference_output']} | "
            f"{', '.join(evidence['local_verified_faces'])} | "
            f"{len(trace['pc_trace'])} | {audit['detected_count']}/{audit['attack_count']} |"
        )
    ci = packet["github_ci"]
    pr_url = ci.get("pull_request", {}).get("url", "https://github.com/issdandavis/SCBE-AETHERMOORE/pull/2406")
    run_url = ci.get("rosetta_run", {}).get(
        "url", "https://github.com/issdandavis/SCBE-AETHERMOORE/actions/runs/27793695962"
    )
    limitations = "\n".join(f"- {item}" for item in packet["not_proven"])
    chain = "\n".join(f"{index}. {item}" for index, item in enumerate(packet["constructive_chain"], 1))
    mutation_scope = (
        "The mutation corpus covers PC substitutions, state deletion/insertion, "
        "adjacent reorder, and replay. It is not labeled as a real-world ROP benchmark."
    )
    filing_boundary = (
        "The local workbench identifies provisional `63/961,403` and the matching "
        "title, but the official filed specification/claim export is still absent "
        "from `docs/legal/patent-workbench/uploads/`. Exact claim-element support "
        "therefore remains pending that export."
    )
    return f"""# Topological Linearization / CFI Evidence Packet

Generated: {packet['created_at']}

## Evidence conclusion

**Support state:** {packet['support_state']}.

The tested construction is:

> {packet['technical_statement_tested']}

This is technical evidence, not a conclusion about patent validity or legal scope.

## Constructive chain

{chain}

## Executed examples

| Program | Reference | Locally agreeing faces | Lifted states | Synthetic mutations detected |
|---|---:|---|---:|---:|
{chr(10).join(rows)}

{mutation_scope}

## Independent provenance

- Loomflow merge: [PR #2406]({pr_url})
- Rosetta execution: [GitHub Actions run 27793695962]({run_url})
- C agreed on both `15.0` and `120.0` in the queried job log: `{ci.get('c_agreement_in_job_log')}`
- TypeScript non-Hamiltonian-star construction: `tests/harmonic/topologicalLinearization.test.ts`
- NeuroGolf 400-task surface/audio receipt: `C:\\dev\\neurogolf\\reports\\arc_record_player\\receipt.json`

## Filing-source boundary

{filing_boundary}

## Not proven

{limitations}
"""


def main() -> int:
    packet = build_packet()
    OUT.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps(packet, indent=2), encoding="utf-8")
    MD_OUT.write_text(markdown(packet), encoding="utf-8")
    audits = [row["mutation_audit"] for row in packet["examples"].values()]
    total = sum(row["attack_count"] for row in audits)
    detected = sum(row["detected_count"] for row in audits)
    print(f"TOPOLOGICAL CFI PROOF: {detected}/{total} synthetic mutations detected; " f"packet={JSON_OUT}")
    return 0 if total and total == detected else 1


if __name__ == "__main__":
    raise SystemExit(main())
