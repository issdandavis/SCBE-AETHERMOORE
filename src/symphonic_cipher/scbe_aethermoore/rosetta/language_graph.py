"""Language Graph — Weighted relationship graph between language systems.

Models relationships between languages (shared script, cognate vocab,
shared grammar, TAM parallels, concept bridges, constructed-from links)
as a weighted graph with shortest-path and similarity queries.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional
import heapq


@dataclass
class LanguageEdge:
    """A weighted, typed edge between two languages."""

    lang_a: str
    lang_b: str
    rel_type: str
    strength: float     # 0.0 (weak) to 1.0 (strong)
    notes: str = ""


class LanguageGraph:
    """Weighted graph of language relationships for translation chain planning."""

    RELATIONSHIP_TYPES = [
        "shared_script",      # ZH↔JA (kanji/hanzi)
        "cognate_vocab",      # JA↔KO (sino-readings), ES↔PT (Romance)
        "shared_grammar",     # JA↔KO (SOV, agglutinative)
        "tam_parallel",       # ZH↔JA (aspect-heavy)
        "concept_bridge",     # Sacred Tongue ↔ natural via NSM primes
        "constructed_from",   # Esperanto ← Romance+Germanic+Slavic
    ]

    def __init__(self) -> None:
        self._edges: list[LanguageEdge] = []
        self._adjacency: dict[str, list[tuple[str, float, str]]] = defaultdict(list)
        self._nodes: set[str] = set()
        self._load_default_edges()

    def _load_default_edges(self) -> None:
        """Seed the graph with known language relationships."""
        default_edges = [
            # CJK shared script
            ("ZH", "JA", "shared_script", 0.8, "Kanji/Hanzi shared logographic characters"),
            ("ZH", "KO", "shared_script", 0.5, "Hanja usage declining but Sino-Korean readings remain"),
            ("JA", "KO", "shared_script", 0.3, "Both borrowed from Chinese; Katakana/Hangul diverged"),

            # Cognate vocabulary (Sino-Xenic)
            ("ZH", "JA", "cognate_vocab", 0.7, "~60% JA vocab is Sino-Japanese"),
            ("ZH", "KO", "cognate_vocab", 0.6, "~60% KO vocab is Sino-Korean"),
            ("JA", "KO", "cognate_vocab", 0.5, "Shared Sino-readings, divergent native vocab"),

            # Shared grammar
            ("JA", "KO", "shared_grammar", 0.9, "SOV order, agglutinative, honorific systems"),
            ("JA", "TOKIPONA", "shared_grammar", 0.2, "Toki Pona is SVO but particles similar"),

            # TAM parallels
            ("ZH", "TOKIPONA", "tam_parallel", 0.7, "Both tenseless, aspect-via-context"),
            ("ZH", "LOJBAN", "tam_parallel", 0.5, "Both treat tense as optional"),
            ("JA", "KO", "tam_parallel", 0.6, "Both aspect-prominent with tense morphology"),
            ("EN", "ESPERANTO", "tam_parallel", 0.7, "Both tense-prominent, 3-way distinction"),

            # Sacred Tongue bridges (via NSM primes)
            ("EN", "KO_ST", "concept_bridge", 0.4, "NSM prime mapping via Rosetta"),
            ("EN", "AV_ST", "concept_bridge", 0.4, "NSM prime mapping via Rosetta"),
            ("EN", "RU_ST", "concept_bridge", 0.4, "NSM prime mapping via Rosetta"),
            ("EN", "CA_ST", "concept_bridge", 0.4, "NSM prime mapping via Rosetta"),
            ("EN", "UM_ST", "concept_bridge", 0.4, "NSM prime mapping via Rosetta"),
            ("EN", "DR_ST", "concept_bridge", 0.4, "NSM prime mapping via Rosetta"),

            # Sacred Tongue inter-bridges
            ("KO_ST", "AV_ST", "concept_bridge", 0.6, "Both Sacred Tongues, shared token grammar"),
            ("AV_ST", "RU_ST", "concept_bridge", 0.6, "Sacred Tongue family"),
            ("RU_ST", "CA_ST", "concept_bridge", 0.6, "Sacred Tongue family"),
            ("CA_ST", "UM_ST", "concept_bridge", 0.6, "Sacred Tongue family"),
            ("UM_ST", "DR_ST", "concept_bridge", 0.6, "Sacred Tongue family"),

            # Conlang construction sources
            ("EN", "ESPERANTO", "constructed_from", 0.5, "Romance+Germanic+Slavic base"),
            ("EN", "TOKIPONA", "constructed_from", 0.3, "Some English-derived roots"),
            ("EN", "LOJBAN", "constructed_from", 0.2, "Lojban vocab from 6 source languages"),
        ]

        for la, lb, rt, strength, notes in default_edges:
            self.add_edge(la, lb, rt, strength, notes)

    def add_edge(
        self,
        lang_a: str,
        lang_b: str,
        rel_type: str,
        strength: float,
        notes: str = "",
    ) -> None:
        """Add a weighted edge between two languages."""
        edge = LanguageEdge(lang_a, lang_b, rel_type, strength, notes)
        self._edges.append(edge)
        self._nodes.add(lang_a)
        self._nodes.add(lang_b)

        # Cost = inverse of strength (stronger connection = lower cost)
        cost = 1.0 - strength + 0.01  # +0.01 to avoid zero cost
        self._adjacency[lang_a].append((lang_b, cost, rel_type))
        self._adjacency[lang_b].append((lang_a, cost, rel_type))

    def get_edges(self, lang: str) -> list[LanguageEdge]:
        """Get all edges connected to a language."""
        return [e for e in self._edges if e.lang_a == lang or e.lang_b == lang]

    def get_edge(self, lang_a: str, lang_b: str) -> list[LanguageEdge]:
        """Get edges between two specific languages."""
        return [
            e for e in self._edges
            if (e.lang_a == lang_a and e.lang_b == lang_b) or
               (e.lang_a == lang_b and e.lang_b == lang_a)
        ]

    def shortest_path(self, src_lang: str, dst_lang: str) -> list[str]:
        """Find shortest translation chain between two languages (Dijkstra).

        Returns list of language codes forming the path, or empty if no path.
        """
        if src_lang not in self._nodes or dst_lang not in self._nodes:
            return []
        if src_lang == dst_lang:
            return [src_lang]

        # Dijkstra's algorithm
        dist: dict[str, float] = {n: float("inf") for n in self._nodes}
        prev: dict[str, Optional[str]] = {n: None for n in self._nodes}
        dist[src_lang] = 0.0
        heap = [(0.0, src_lang)]

        while heap:
            d, u = heapq.heappop(heap)
            if d > dist[u]:
                continue
            if u == dst_lang:
                break
            for v, cost, _ in self._adjacency[u]:
                new_dist = d + cost
                if new_dist < dist[v]:
                    dist[v] = new_dist
                    prev[v] = u
                    heapq.heappush(heap, (new_dist, v))

        # Reconstruct path
        if dist[dst_lang] == float("inf"):
            return []
        path = []
        node: Optional[str] = dst_lang
        while node is not None:
            path.append(node)
            node = prev[node]
        return list(reversed(path))

    def similarity(self, lang_a: str, lang_b: str) -> float:
        """Compute weighted similarity between two languages.

        Sum of all edge strengths connecting them directly.
        Returns 0.0 if no direct connection.
        """
        edges = self.get_edge(lang_a, lang_b)
        if not edges:
            return 0.0
        return sum(e.strength for e in edges) / len(edges)

    def all_languages(self) -> list[str]:
        """List all language codes in the graph."""
        return sorted(self._nodes)

    def related_languages(self, lang: str, min_strength: float = 0.3) -> list[tuple[str, float]]:
        """Find languages related to the given one, sorted by strength."""
        edges = self.get_edges(lang)
        related: dict[str, float] = {}
        for e in edges:
            other = e.lang_b if e.lang_a == lang else e.lang_a
            current = related.get(other, 0.0)
            related[other] = max(current, e.strength)

        filtered = [(l, s) for l, s in related.items() if s >= min_strength]
        return sorted(filtered, key=lambda x: x[1], reverse=True)
