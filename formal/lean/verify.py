"""Build the contracts, audit theorem axioms, and require false fixtures to fail."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent
ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}


def run(args, *, expected_success=True, timeout=300):
    env = {**os.environ, "LEAN_NUM_THREADS": "2"}
    result = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", timeout=timeout)
    if (result.returncode == 0) != expected_success:
        raise RuntimeError(f"Unexpected command status: {args}\n{result.stdout}\n{result.stderr}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "validation.json")
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Refusing to overwrite a validation receipt")
    source_files = sorted((ROOT / "SCBE").glob("*.lean"))
    theorems = []
    for source in source_files:
        text = source.read_text(encoding="utf-8")
        if re.search(r"\b(sorry|admit|native_decide)\b|^\s*axiom\s", text, re.MULTILINE):
            raise RuntimeError(f"Unapproved proof shortcut in {source.name}")
        namespace = re.search(r"^namespace (\S+)", text, re.MULTILINE).group(1)
        theorems.extend(namespace + "." + name for name in re.findall(r"^theorem (\w+)", text, re.MULTILINE))
    if not theorems:
        raise RuntimeError("No theorems discovered")
    run(["lake", "build"])
    scratch = ROOT / ".lake" / "contract-audit"
    scratch.mkdir(parents=True, exist_ok=True)
    axiom_file = scratch / "Axioms.lean"
    axiom_file.write_text(
        "import SCBE\n" + "\n".join("#print axioms " + name for name in theorems) + "\n", encoding="utf-8"
    )
    output = run(["lake", "env", "lean", str(axiom_file)]).stdout
    entries = re.findall(r"'([^']+)' depends on axioms:\s*\[([^\]]*)\]", output)
    audits = {name: [a.strip() for a in axioms.split(",") if a.strip()] for name, axioms in entries}
    for name in re.findall(r"'([^']+)' does not depend on any axioms", output):
        audits[name] = []
    if set(audits) != set(theorems):
        raise RuntimeError(f"Incomplete axiom report:\n{output}")
    for name, axioms in audits.items():
        if not set(axioms) <= ALLOWED_AXIOMS:
            raise RuntimeError(f"Unapproved axiom dependency for {name}: {axioms}")
    false_fixtures = {
        "reverse_edge": ("SCBE.Routing", "example : SCBE.permits SCBE.forwardChain 1 0 = true := by decide"),
        "weaken_refusal": ("SCBE.Composition", "example : SCBE.combine .deny .allow = .allow := by decide"),
        "exclude_valid_center": ("SCBE.Geometry", "example : SCBE.safetyScore 0 0 < 1 := by simp [SCBE.safetyScore]"),
        "double_owned_seam": (
            "SCBE.NestedRegions",
            "example : SCBE.inCell ⟨0, 1, by decide⟩ 1 := by norm_num [SCBE.inCell, SCBE.cellUpper]",
        ),
        "rebase_grants_membership": (
            "SCBE.NestedRegions",
            "example : SCBE.inCell ⟨0, 1, by decide⟩ "
            "(SCBE.globalCoord ⟨0, 1, by decide⟩ (SCBE.localCoord ⟨0, 1, by decide⟩ 2)) "
            ":= by norm_num [SCBE.inCell, SCBE.cellUpper, SCBE.globalCoord, SCBE.localCoord]",
        ),
        "quarantine_executes_unscoped": (
            "SCBE.RestrictedExecution",
            "example : SCBE.dispatchAllowed SCBE.forwardChain 0 1 .quarantine false "
            "⟨true, true, true, true⟩ = true := by decide",
        ),
        "quarantine_silently_promotes": (
            "SCBE.RestrictedExecution",
            "example : (SCBE.checkedCall SCBE.forwardChain 0 1 .quarantine true "
            "⟨true, true, true, true⟩ (fun _ => (6 : Nat))).1 = .allow := by decide",
        ),
    }
    # Compile the actual negations first. An import/syntax failure in a fixture
    # must not masquerade as rejection of a mathematically false statement.
    for name, (module, statement) in false_fixtures.items():
        proposition = statement.removeprefix("example : ").split(" := by ", 1)[0]
        proof = statement.split(" := by ", 1)[1]
        path = scratch / (name + "_counterexample.lean")
        path.write_text(f"import {module}\nexample : ¬ ({proposition}) := by {proof}\n", encoding="utf-8")
        run(["lake", "env", "lean", str(path)], timeout=60)
    rejected = []
    for name, (module, statement) in false_fixtures.items():
        path = scratch / (name + ".lean")
        path.write_text("import " + module + "\n" + statement + "\n", encoding="utf-8")
        result = run(["lake", "env", "lean", str(path)], expected_success=False, timeout=60)
        if "error:" not in result.stdout + result.stderr:
            raise RuntimeError("Fixture failed without a Lean error")
        rejected.append(name)
    pinned = [ROOT / "SCBE.lean", ROOT / "lean-toolchain", ROOT / "lakefile.toml", ROOT / "lake-manifest.json"]
    result = {
        "schema": "scbe-lean-proof-check/v1",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "lean": run(["lake", "env", "lean", "--version"]).stdout.strip(),
        "passed": True,
        "theorem_count": len(theorems),
        "axioms": audits,
        "rejected_false_fixtures": rejected,
        "proved_fixture_negations": list(false_fixtures),
        "sha256": {
            str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in source_files + pinned + [Path(__file__).resolve()]
        },
        "scope": "Exact formal definitions; implementation correspondence is audited separately",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("Lean build passed.")
    print(f"Checked {len(theorems)} theorems; audited all axioms; rejected {len(rejected)} false fixtures.")
    print(args.output)


if __name__ == "__main__":
    main()
