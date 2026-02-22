from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

from .emitter import emit_from_ir
from .matrix import InteroperabilityMatrix, load_interoperability_matrix
from .parser import parse_source_to_ir
from .validator import ValidationIssue, validate_generated_code


@dataclass
class TranslationArtifact:
    source_language: str
    target_language: str
    code: str
    valid: bool
    issues: List[ValidationIssue] = field(default_factory=list)
    metadata: Dict[str, object] = field(default_factory=dict)


class CodePrismBuilder:
    def __init__(self, matrix_path: Path | None = None) -> None:
        self.matrix: InteroperabilityMatrix = load_interoperability_matrix(matrix_path)

    def translate(
        self,
        source_code: str,
        source_language: str,
        target_languages: List[str],
        module_name: str = "prism_module",
        tongue_combo: str = "KO+CA",
    ) -> Dict[str, TranslationArtifact]:
        source = source_language.lower()
        ir = parse_source_to_ir(source_code, source_language=source, module_name=module_name)
        artifacts: Dict[str, TranslationArtifact] = {}

        for target in target_languages:
            target_lang = target.lower()
            if not self.matrix.can_translate(source, target_lang):
                artifacts[target_lang] = TranslationArtifact(
                    source_language=source,
                    target_language=target_lang,
                    code="",
                    valid=False,
                    issues=[ValidationIssue(code="unsupported_route", message=f"{source} -> {target_lang} not allowed by matrix.")],
                    metadata={"tongue_combo": tongue_combo, "route_allowed": False},
                )
                continue

            emitted = emit_from_ir(ir, target_lang)
            issues = validate_generated_code(emitted, target_lang)
            artifacts[target_lang] = TranslationArtifact(
                source_language=source,
                target_language=target_lang,
                code=emitted,
                valid=len(issues) == 0,
                issues=issues,
                metadata={
                    "tongue_combo": tongue_combo,
                    "route_allowed": True,
                    "matrix_version": self.matrix.version,
                    "function_count": len(ir.functions),
                },
            )

        return artifacts

