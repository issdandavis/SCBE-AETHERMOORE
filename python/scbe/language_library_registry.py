"""Language library registry for SCBE coding faces.

This is the practical version of "Lis Biblioteca de Infinity": every language,
conlang, notation, binary lane, or book can be registered, but each face must
state its proof level honestly.

Levels:
  0 concept      idea/notation only
  1 book         grammar/reference/manual exists
  2 emitter      system can emit source/text in that face
  3 parser       system can lift/read that face into IR
  4 interpreter  controlled runtime can execute it
  5 compiler     real toolchain can compile/build it
  6 verified     ran against tests and produced a receipt
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Iterable


LEVELS = {
    0: "concept",
    1: "book",
    2: "emitter",
    3: "parser",
    4: "interpreter",
    5: "compiler",
    6: "verified",
}


@dataclass(frozen=True)
class LanguageFace:
    id: str
    name: str
    family: str
    level: int
    code_paths: list[str] = field(default_factory=list)
    reference_paths: list[str] = field(default_factory=list)
    receipt_paths: list[str] = field(default_factory=list)
    notes: str = ""

    @property
    def level_name(self) -> str:
        return LEVELS.get(self.level, "unknown")

    def claim(self) -> str:
        if self.level >= 6:
            return f"{self.name}: verified by execution receipt"
        if self.level == 5:
            return f"{self.name}: compiler/toolchain lane exists"
        if self.level == 4:
            return f"{self.name}: interpreter/runtime lane exists"
        if self.level == 3:
            return f"{self.name}: parser/lift-to-IR lane exists"
        if self.level == 2:
            return f"{self.name}: emitter/source face exists"
        if self.level == 1:
            return f"{self.name}: book/reference face exists"
        return f"{self.name}: concept face only"

    def to_dict(self) -> dict:
        data = asdict(self)
        data["level_name"] = self.level_name
        data["safe_claim"] = self.claim()
        return data


DEFAULT_FACES: tuple[LanguageFace, ...] = (
    LanguageFace(
        id="python",
        name="Python",
        family="general-purpose",
        level=6,
        code_paths=["src/code_prism/emitter.py", "python/scbe/tongue_isa.py"],
        reference_paths=["scripts/mountain_map/pipeline_map.md"],
        notes="Primary executable and verifier-friendly face.",
    ),
    LanguageFace(
        id="stib",
        name="Sacred Tongue Instruction Binary",
        family="binary-ir",
        level=3,
        code_paths=["python/scbe/tongue_isa_binary.py", "agents/agent_bus.py"],
        notes="Canonical executable opcode/program binary lane; not arbitrary text.",
    ),
    LanguageFace(
        id="ca-compiler-lane",
        name="CA Opcode Compiler Lane",
        family="compiler",
        level=6,
        code_paths=[
            "python/scbe/tongue_isa.py",
            "python/scbe/tongue_isa_binary.py",
            "src/code_prism/emitter.py",
            "scripts/system/run_scbe_compiler_lane.py",
        ],
        receipt_paths=["artifacts/ai_brain/compiler_lane_receipt.json"],
        notes="Verified narrow lane: CA opcodes -> STIB -> Code Prism Python source -> executed receipt.",
    ),
    LanguageFace(
        id="code-prism",
        name="Code Prism / LatticeOp",
        family="shared-ir",
        level=3,
        code_paths=["src/code_prism/emitter.py", "src/cli/cross_build_ir.py"],
        notes="Shared IR and emitter lane for cross-build/code faces.",
    ),
    LanguageFace(
        id="utf-transfer",
        name="UTF Transfer",
        family="text-transference",
        level=2,
        code_paths=["python/scbe/transference_gate.py"],
        reference_paths=["docs/specs/UTF_PYTHON_TRANSFER_GATE_2026-06-27.md"],
        notes="Raw UTF/BOM text to Python-safe UTF-8/no-BOM text/source with receipt hashes.",
    ),
    LanguageFace(
        id="sacred-tongues",
        name="Six Sacred Tongues",
        family="conlang",
        level=2,
        code_paths=["python/scbe/rosetta.py", "src/symphonic_cipher/scbe_aethermoore/rosetta/seed_data.py"],
        notes="Conlang and concept-emission lane; specific opcode subsets route through STIB/CA.",
    ),
    LanguageFace(
        id="conlang-macros",
        name="Conlang Macro Binding",
        family="conlang-runtime",
        level=6,
        code_paths=[
            "C:/dev/train-orchestrator/training/conlang_macros.py",
            "python/scbe/instrument.py",
            "python/scbe/tongue_isa.py",
            "python/scbe/ca_opcode_table.py",
        ],
        receipt_paths=[
            "C:/dev/train-orchestrator/artifacts/runs/conlang-macros.run.txt",
            "artifacts/ai_brain/gate_reports/conlang_macros/claim_gate_summary.json",
        ],
        notes=(
            "Verified narrow lane: real Cassisivadan CA words bind to verified CA opcode macros, "
            "phase grammar rejects illegal/unsealed/unknown sentences, and Python/Rust execution is "
            "reported honestly. Emitted-to-8 faces is not claimed as executed-on-8."
        ),
    ),
    LanguageFace(
        id="haskell",
        name="Haskell",
        family="general-purpose",
        level=2,
        code_paths=["python/scbe/tongue_isa.py", "scripts/system/mixed_expression_lane.py"],
        reference_paths=["scripts/mountain_map/pipeline_map.md"],
        notes="Emitter/reference face unless local toolchain receipt is attached.",
    ),
    LanguageFace(
        id="rust",
        name="Rust",
        family="general-purpose",
        level=2,
        code_paths=["python/scbe/tongue_isa.py"],
        reference_paths=["scripts/mountain_map/pipeline_map.md"],
        notes="Emitter/reference face unless local toolchain receipt is attached.",
    ),
    LanguageFace(
        id="music-binary",
        name="Music/Binary Mapping",
        family="notation",
        level=1,
        reference_paths=["docs/research/CODE_CONLANGS_OPEN_QUESTIONS_2026-06-27.md"],
        notes="Book/reference lane for binary-to-musical coding ideas.",
    ),
)


def faces() -> list[LanguageFace]:
    return list(DEFAULT_FACES)


def by_id(face_id: str) -> LanguageFace | None:
    key = face_id.strip().lower()
    for face in DEFAULT_FACES:
        if face.id == key:
            return face
    return None


def manifest(items: Iterable[LanguageFace] | None = None) -> dict:
    rows = [face.to_dict() for face in (items or DEFAULT_FACES)]
    return {
        "schema": "scbe.language_library_registry.v1",
        "rule": "No fake code: claim only the highest proven level for each face.",
        "levels": LEVELS,
        "faces": rows,
    }


if __name__ == "__main__":
    import json

    print(json.dumps(manifest(), indent=2, sort_keys=True))
