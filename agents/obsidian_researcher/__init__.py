"""Obsidian Note-Taker Agent with Cross-Reference Intelligence.

Ingests research from multiple sources (arXiv, Reddit, web, user notes)
and produces cross-referenced Obsidian vault pages using CDDM morphisms,
keyword matching, semantic search, and citation linking.
"""

from .source_adapter import SourceType, IngestionResult, SourceAdapter
from .cross_reference_engine import CrossReferenceEngine, WikiLink, LinkType
from .note_renderer import NoteRenderer
from .vault_manager import VaultManager
from .coverage_map import CoverageMap, ConceptCoverage
from .podcast_generator import PodcastGenerator, PodcastScript, PodcastSegment
from .knowledge_graph import KnowledgeGraph, GraphNode, GraphEdge
from .byproduct_logger import ByproductLogger

__all__ = [
    "SourceType", "IngestionResult", "SourceAdapter",
    "CrossReferenceEngine", "WikiLink", "LinkType",
    "NoteRenderer", "VaultManager",
    "CoverageMap", "ConceptCoverage",
    "PodcastGenerator", "PodcastScript", "PodcastSegment",
    "KnowledgeGraph", "GraphNode", "GraphEdge",
    "ByproductLogger",
]
