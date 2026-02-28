"""Governed Code Search -- SemanticMesh integration for tongue-classified retrieval.

Uses the SemanticMesh MCP's property graph for code search.
Every search query goes through tongue classification to find
code in the right linguistic register.

@layer Layer 3, Layer 9
@component AetherIDE.CodeSearch
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from src.mcp_server.semantic_mesh import SemanticMeshServer
    _HAS_MESH = True
except ImportError:
    _HAS_MESH = False

TONGUE_NAMES = ["KO", "AV", "RU", "CA", "UM", "DR"]


class GovernedCodeSearch:
    """Search code using tongue-classified semantic mesh."""

    def __init__(self) -> None:
        self._mesh: Optional[Any] = None
        self._search_count = 0
        if _HAS_MESH:
            try:
                self._mesh = SemanticMeshServer()
            except Exception:
                self._mesh = None

    def search(self, query: str, tongue_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search the mesh for code matching the query.

        If tongue_filter is provided, restrict results to that tongue.
        Otherwise, auto-classify the query's tongue.
        """
        self._search_count += 1

        if self._mesh is not None and hasattr(self._mesh, "handle_query"):
            try:
                params = {"query": query, "top_k": 10}
                if tongue_filter:
                    params["tongue"] = tongue_filter
                result = self._mesh.handle_query(params)
                if isinstance(result, list):
                    return result
                return [result] if result else []
            except Exception:
                pass

        # Fallback: return empty results
        return []

    def classify(self, text: str) -> str:
        """Classify text into a Sacred Tongue register."""
        text_lower = text.lower()
        scores = {
            "KO": sum(1 for kw in ["if", "while", "for", "switch", "control"] if kw in text_lower),
            "AV": sum(1 for kw in ["import", "return", "send", "fetch", "transport"] if kw in text_lower),
            "RU": sum(1 for kw in ["assert", "validate", "check", "rule", "constraint"] if kw in text_lower),
            "CA": sum(1 for kw in ["compute", "calculate", "sum", "process", "transform"] if kw in text_lower),
            "UM": sum(1 for kw in ["private", "hidden", "encrypt", "secret", "internal"] if kw in text_lower),
            "DR": sum(1 for kw in ["class", "struct", "model", "schema", "define"] if kw in text_lower),
        }
        return max(scores, key=scores.get)  # type: ignore[arg-type]

    @property
    def available(self) -> bool:
        return self._mesh is not None

    @property
    def search_count(self) -> int:
        return self._search_count
