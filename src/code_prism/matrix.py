from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set


DEFAULT_MATRIX_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "code_prism" / "interoperability_matrix.json"
)


@dataclass(frozen=True)
class InteroperabilityMatrix:
    version: str
    languages: Set[str]
    transpilers: Dict[str, Set[str]]
    conlang_routes: Dict[str, List[str]]
    safe_subset: Dict[str, List[str]]

    def can_translate(self, source_language: str, target_language: str) -> bool:
        src = source_language.lower()
        dst = target_language.lower()
        return dst in self.transpilers.get(src, set())


def _normalize_transpilers(raw: Dict[str, List[str]]) -> Dict[str, Set[str]]:
    normalized: Dict[str, Set[str]] = {}
    for source, targets in raw.items():
        normalized[source.lower()] = {target.lower() for target in targets}
    return normalized


def load_interoperability_matrix(path: Path | None = None) -> InteroperabilityMatrix:
    matrix_path = path or DEFAULT_MATRIX_PATH
    payload = json.loads(matrix_path.read_text(encoding="utf-8"))
    return InteroperabilityMatrix(
        version=str(payload.get("version", "0.1.0")),
        languages={lang.lower() for lang in payload.get("languages", [])},
        transpilers=_normalize_transpilers(payload.get("transpilers", {})),
        conlang_routes=payload.get("conlang_routes", {}),
        safe_subset=payload.get("safe_subset", {}),
    )

