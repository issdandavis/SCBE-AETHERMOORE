"""
language_library_registry.py

Central registry for verified language faces / lanes in SCBE-AETHERMOORE.

Each entry records:
- level (verification tier)
- verified status
- explicit honesty caveats separating provenance (emits-to) from runtime (executed-on)

This file enforces the standing rule: caveats live in source, not just run logs.

conlang_macros entry (added 2026-06-27):
- level=6 verified
- caveat: emitted-to-8 faces is not claimed as executed-on-8
- binds-to: ca core / ca_word_for_opcode in instrument.py
- emits-to: 8 faces (provenance)
- executed-on: narrow set (python, rust where run)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

@dataclass(frozen=True)
class LanguageFace:
    name: str
    level: int
    verified: bool
    binds_to: str
    emits_to: int
    executed_on: List[str]
    caveat: str
    artifact_hash: str = ""

REGISTRY: Dict[str, LanguageFace] = {}

def register_face(face: LanguageFace) -> None:
    REGISTRY[face.name] = face

# --- Verified faces -------------------------------------------------------

register_face(LanguageFace(
    name="conlang_macros",
    level=6,
    verified=True,
    binds_to="ca_opcode core (instrument.py ca_word_for_opcode)",
    emits_to=8,
    executed_on=["python", "rust"],  # narrow; only where actually run and checked
    caveat="emitted-to-8 faces is not claimed as executed-on-8. Provenance breadth separate from runtime claim. BOM/UTF handled via transference_gate adapter.",
    artifact_hash="5117a81c6dc6bf2f6594862e728fd9b149a9835a1938172ac22fb8cf51e1efb1",
))

# Add other faces (python, ca, etc.) here following the same pattern.
# Example skeleton for a standard face:
# register_face(LanguageFace(
#     name="python",
#     level=9,
#     verified=True,
#     binds_to="...",
#     emits_to=8,
#     executed_on=["python"],
#     caveat="...",
# ))

def get_face(name: str) -> LanguageFace:
    return REGISTRY[name]

def list_verified_faces() -> List[str]:
    return [name for name, f in REGISTRY.items() if f.verified]

if __name__ == "__main__":
    print("Verified language faces:")
    for name in list_verified_faces():
        f = get_face(name)
        print(f"  {name}: level={f.level}, emits_to={f.emits_to}, executed_on={f.executed_on}")
        print(f"    caveat: {f.caveat}")
