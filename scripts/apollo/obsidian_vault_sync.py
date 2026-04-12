"""Obsidian Vault Sync — Read vault, build nodal network, export for training.

Reads all .md files from the Avalon Files vault, extracts wiki-links
to build a knowledge graph, syncs to cloud (Dropbox/OneDrive), and
exports the connected graph as SFT training data.

Usage:
    python scripts/apollo/obsidian_vault_sync.py scan           # Inventory vault
    python scripts/apollo/obsidian_vault_sync.py graph          # Build link graph
    python scripts/apollo/obsidian_vault_sync.py connect        # Add missing links
    python scripts/apollo/obsidian_vault_sync.py export-sft     # Generate training data
    python scripts/apollo/obsidian_vault_sync.py sync-cloud     # Copy to Dropbox/OneDrive
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_VAULT_PATH = ROOT / "notes" if (ROOT / "notes").exists() else Path(r"C:\Users\issda\Documents\Avalon Files")
VAULT_PATH = Path(os.environ.get("OBSIDIAN_VAULT", str(DEFAULT_VAULT_PATH)))
CLOUD_TARGETS = [
    Path(r"C:\Users\issda\Dropbox\Obsidian-Sync"),
    Path(r"C:\Users\issda\OneDrive\Obsidian-Sync"),
]
GRAPH_OUTPUT = ROOT / "artifacts" / "apollo" / "obsidian_graph.json"
SFT_OUTPUT = ROOT / "training-data" / "apollo" / "obsidian_vault_sft.jsonl"

# Wiki-link pattern: [[Target]] or [[Target|Display]]
WIKI_LINK = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]")
# Heading pattern
HEADING = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
# Tag pattern
TAG = re.compile(r"#([a-zA-Z][a-zA-Z0-9_/-]+)")
TOKEN_SPLIT = re.compile(r"[^a-z0-9]+")

PHI = 1.6180339887498949
TONGUE_ORDER = ("KO", "AV", "RU", "CA", "UM", "DR")
TONGUE_FULL_NAMES = {
    "KO": "Kor'aelin",
    "AV": "Avali",
    "RU": "Runethic",
    "CA": "Cassisivadan",
    "UM": "Umbroth",
    "DR": "Draumric",
}
TONGUE_SECTORS_DEGREES = {
    "KO": 0.0,
    "AV": 60.0,
    "RU": 120.0,
    "CA": 180.0,
    "UM": 240.0,
    "DR": 300.0,
}
TONGUE_SECTORS_RADIANS = {
    tongue: math.radians(degrees) for tongue, degrees in TONGUE_SECTORS_DEGREES.items()
}
TONGUE_PHI_WEIGHTS = {
    "KO": 1.0,
    "AV": PHI ** 1,
    "RU": PHI ** 2,
    "CA": PHI ** 3,
    "UM": PHI ** 4,
    "DR": PHI ** 5,
}
TONGUE_KEYWORDS = {
    "KO": ["intent", "purpose", "goal", "governance", "route", "session", "flow", "agent"],
    "AV": ["context", "metadata", "environment", "condition", "state", "config", "index", "schema"],
    "RU": ["binding", "relation", "connect", "link", "dependency", "edge", "graph", "couple"],
    "CA": ["implement", "compute", "code", "algorithm", "function", "execute", "runtime", "calculate"],
    "UM": ["security", "veil", "hidden", "risk", "threat", "encrypt", "protect", "guard", "attack"],
    "DR": ["structure", "architecture", "layer", "pipeline", "topology", "framework", "system", "operations"],
}
SUBJECT_KEYWORDS = {
    "agents": ["agent", "swarm", "assistant", "handoff", "crosstalk", "relay"],
    "architecture": ["architecture", "system", "framework", "layer", "topology", "structure"],
    "automation": ["automation", "workflow", "orchestration", "job", "pipeline", "scheduler"],
    "browser": ["browser", "playwright", "chrome", "web", "page", "navigation"],
    "cryptography": ["cryptography", "crypto", "cipher", "nonce", "encrypt", "decrypt", "signature", "authentication"],
    "documentation": ["documentation", "doc", "manual", "guide", "tutorial", "readme", "spec"],
    "governance": ["governance", "policy", "gate", "allow", "deny", "quarantine", "compliance"],
    "lore": ["lore", "story", "world", "character", "narrative", "webtoon", "manhwa"],
    "mathematics": ["math", "mathematics", "vector", "tensor", "geometry", "hyperbolic", "proof", "metric"],
    "mobile": ["android", "mobile", "phone", "tablet", "emulator", "kindle", "ios"],
    "monetization": ["stripe", "shopify", "checkout", "payment", "revenue", "sales", "product"],
    "research": ["research", "paper", "arxiv", "benchmark", "experiment", "dataset", "evaluation"],
    "security": ["security", "risk", "threat", "attack", "secret", "redact", "guard"],
    "storage": ["storage", "vault", "database", "cache", "bucket", "drive", "s3", "dropbox"],
    "training": ["training", "fine tune", "finetune", "sft", "jsonl", "corpus", "checkpoint", "eval"],
}
TASK_KEYWORDS = {
    "audit": ["audit", "review", "inspect", "triage", "assess"],
    "build": ["build", "create", "make", "implement", "assemble"],
    "capture": ["capture", "collect", "gather", "ingest", "extract"],
    "deploy": ["deploy", "ship", "release", "launch", "publish"],
    "document": ["document", "write", "explain", "describe", "summarize"],
    "repair": ["repair", "fix", "recover", "stabilize", "heal"],
    "route": ["route", "dispatch", "handoff", "bridge", "relay"],
    "sync": ["sync", "mirror", "copy", "backup", "promote"],
    "test": ["test", "verify", "validate", "check", "prove"],
    "train": ["train", "fine tune", "finetune", "evaluate", "score", "benchmark"],
}
RELATION_KEYWORDS = {
    "bridge": ["bridge", "handoff", "relay", "route", "cross talk", "crosstalk"],
    "dependency": ["depend", "requires", "upstream", "downstream", "prerequisite"],
    "evidence": ["evidence", "proof", "artifact", "report", "trace"],
    "feedback": ["feedback", "review", "score", "critique", "improve"],
    "governs": ["govern", "policy", "gate", "permit", "block"],
    "implements": ["implement", "executes", "runs", "powers"],
    "linked": ["link", "linked", "reference", "connect", "associate"],
    "maps": ["map", "index", "catalog", "taxonomy"],
    "mirrors": ["mirror", "replica", "copy", "sync"],
    "sequence": ["first", "next", "then", "before", "after"],
}
GENERIC_LABEL_STOPWORDS = {
    "the", "and", "for", "with", "from", "into", "root", "notes", "system", "library", "repo", "repository",
    "files", "docs", "doc", "data", "general", "misc", "miscellaneous", "master", "index",
}
MAX_CANDIDATE_BUCKET_SIZE = 200
SEMANTIC_EDGE_MIN_GRAVITY = 0.2
NULL_PATH_LIMIT = 64


@dataclass
class VaultNote:
    path: str
    name: str
    folder: str
    size: int
    headings: List[str]
    tags: List[str]
    outgoing_links: List[str]
    incoming_links: List[str] = field(default_factory=list)
    content_hash: str = ""
    word_count: int = 0
    tongue: str = ""  # classified Sacred Tongue
    tongue_profile: Dict[str, float] = field(default_factory=dict)
    primary_weight_phi: float = 0.0
    semantic_mass_phi: float = 0.0
    tongue_sector_degrees: float = 0.0
    tongue_sector_radians: float = 0.0
    subjects: List[str] = field(default_factory=list)
    tasks: List[str] = field(default_factory=list)
    relations: List[str] = field(default_factory=list)


def _normalize_text(value: str) -> str:
    return " ".join(TOKEN_SPLIT.split(value.lower())).strip()


def _compile_signal_sources(
    name: str,
    folder: str,
    headings: Iterable[str],
    tags: Iterable[str],
    content: str,
) -> List[Tuple[str, float]]:
    return [
        (_normalize_text(name.replace("_", " ").replace("-", " ")), 2.5),
        (_normalize_text(folder.replace("\\", " ").replace("/", " ")), 1.8),
        (_normalize_text(" ".join(tags)), 1.6),
        (_normalize_text(" ".join(headings)), 1.4),
        (_normalize_text(content[:6000]), 1.0),
    ]


def _keyword_hits(text: str, keywords: Iterable[str]) -> int:
    return sum(1 for keyword in keywords if keyword in text)


def _extract_label_matches(signal_text: str, label_keywords: Dict[str, List[str]]) -> List[str]:
    labels = []
    for label, keywords in label_keywords.items():
        if _keyword_hits(signal_text, keywords):
            labels.append(label)
    return sorted(labels)


def compute_tongue_profile(
    name: str,
    folder: str,
    headings: Iterable[str],
    tags: Iterable[str],
    content: str,
    primary_tongue: str,
) -> Dict[str, float]:
    raw_scores = {tongue: 0.0 for tongue in TONGUE_ORDER}
    max_phi_weight = max(TONGUE_PHI_WEIGHTS.values())
    for signal_text, source_weight in _compile_signal_sources(name, folder, headings, tags, content):
        if not signal_text:
            continue
        for tongue, keywords in TONGUE_KEYWORDS.items():
            raw_scores[tongue] += _keyword_hits(signal_text, keywords) * source_weight * TONGUE_PHI_WEIGHTS[tongue]

    raw_scores[primary_tongue] += max_phi_weight
    total = sum(raw_scores.values())
    if total <= 0:
        return {tongue: round(1.0 / len(TONGUE_ORDER), 6) for tongue in TONGUE_ORDER}
    return {tongue: round(raw_scores[tongue] / total, 6) for tongue in TONGUE_ORDER}


def compute_semantic_mass(tongue_profile: Dict[str, float]) -> float:
    return round(sum(tongue_profile[tongue] * TONGUE_PHI_WEIGHTS[tongue] for tongue in TONGUE_ORDER), 6)


def extract_semantic_labels(
    name: str,
    folder: str,
    headings: Iterable[str],
    tags: Iterable[str],
    content: str,
) -> Tuple[List[str], List[str], List[str]]:
    signal_text = _normalize_text(" ".join([
        name.replace("_", " ").replace("-", " "),
        folder.replace("\\", " ").replace("/", " "),
        " ".join(tags),
        " ".join(headings),
        content[:4000],
    ]))
    subject_labels = _extract_label_matches(signal_text, SUBJECT_KEYWORDS)
    tasks = _extract_label_matches(signal_text, TASK_KEYWORDS)
    relations = _extract_label_matches(signal_text, RELATION_KEYWORDS)
    high_signal_tokens = []
    token_counter = Counter(token for token in signal_text.split() if len(token) >= 4 and token not in GENERIC_LABEL_STOPWORDS)
    for token, _count in token_counter.most_common(8):
        if token not in subject_labels:
            high_signal_tokens.append(token)

    subjects = sorted(set(subject_labels + high_signal_tokens))
    return subjects, tasks, relations


def compute_overlap_score(values_a: Iterable[str], values_b: Iterable[str]) -> float:
    set_a = set(values_a)
    set_b = set(values_b)
    if not set_a and not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def compute_shared_tongue_weight(profile_a: Dict[str, float], profile_b: Dict[str, float]) -> float:
    return round(
        sum(min(profile_a[tongue], profile_b[tongue]) * TONGUE_PHI_WEIGHTS[tongue] for tongue in TONGUE_ORDER),
        6,
    )


def compute_sector_alignment(primary_tongue_a: str, primary_tongue_b: str) -> float:
    angle_a = TONGUE_SECTORS_RADIANS[primary_tongue_a]
    angle_b = TONGUE_SECTORS_RADIANS[primary_tongue_b]
    return round((1.0 + math.cos(angle_a - angle_b)) / 2.0, 6)


def compute_semantic_gravity(
    note_a: VaultNote,
    note_b: VaultNote,
    explicit_link: bool = False,
) -> Dict[str, object]:
    subject_overlap = compute_overlap_score(note_a.subjects, note_b.subjects)
    task_overlap = compute_overlap_score(note_a.tasks, note_b.tasks)
    relation_overlap = compute_overlap_score(note_a.relations, note_b.relations)
    semantic_overlap = (0.45 * subject_overlap) + (0.30 * task_overlap) + (0.25 * relation_overlap)
    shared_tongue_weight = compute_shared_tongue_weight(note_a.tongue_profile, note_b.tongue_profile)
    sector_alignment = compute_sector_alignment(note_a.tongue, note_b.tongue)
    max_weight = max(TONGUE_PHI_WEIGHTS.values())
    explicit_bonus = 0.25 if explicit_link else 0.0
    gravity = round(
        (semantic_overlap + explicit_bonus)
        * (1.0 + (shared_tongue_weight / max_weight))
        * (0.5 + (0.5 * sector_alignment)),
        6,
    )
    return {
        "subject_overlap": round(subject_overlap, 6),
        "task_overlap": round(task_overlap, 6),
        "relation_overlap": round(relation_overlap, 6),
        "semantic_overlap": round(semantic_overlap, 6),
        "shared_tongue_weight_phi": shared_tongue_weight,
        "sector_alignment": sector_alignment,
        "semantic_gravity": gravity,
        "shared_subjects": sorted(set(note_a.subjects) & set(note_b.subjects)),
        "shared_tasks": sorted(set(note_a.tasks) & set(note_b.tasks)),
        "shared_relations": sorted(set(note_a.relations) & set(note_b.relations)),
    }


def _pair_key(name_a: str, name_b: str) -> Tuple[str, str]:
    return tuple(sorted((name_a, name_b)))


def classify_tongue(name: str, folder: str, content: str) -> str:
    """Classify note by Sacred Tongue based on folder and content."""
    folder_lower = folder.lower()
    name_lower = name.lower()
    content_lower = content[:500].lower()

    if any(k in folder_lower for k in ["architecture", "system", "ops"]):
        return "DR"
    if any(k in folder_lower for k in ["writing", "story", "lore"]):
        return "RU"
    if any(k in folder_lower for k in ["tongue", "language"]):
        return "AV"
    if any(k in folder_lower for k in ["agent", "cross talk", "session"]):
        return "KO"
    if any(k in folder_lower for k in ["security", "patent", "crypto"]):
        return "UM"
    if any(k in folder_lower for k in ["reference", "research", "cddm"]):
        return "CA"
    if any(k in name_lower for k in ["security", "patent", "vault"]):
        return "UM"
    if any(k in name_lower for k in ["agent", "cross talk", "handoff"]):
        return "KO"
    if any(k in content_lower for k in ["governance", "gate", "allow", "deny"]):
        return "KO"
    return "AV"  # default: metadata/context


def scan_vault() -> List[VaultNote]:
    """Scan all markdown files in the vault."""
    notes = []
    for md_file in VAULT_PATH.rglob("*.md"):
        if ".obsidian" in str(md_file):
            continue
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        rel_path = str(md_file.relative_to(VAULT_PATH))
        name = md_file.stem
        folder = str(md_file.parent.relative_to(VAULT_PATH)) if md_file.parent != VAULT_PATH else ""

        headings = [m.group(2) for m in HEADING.finditer(content)]
        tags = list(set(TAG.findall(content)))
        links = list(set(WIKI_LINK.findall(content)))
        words = len(content.split())
        content_hash = hashlib.blake2s(content.encode()[:4096], digest_size=8).hexdigest()
        tongue = classify_tongue(name, folder, content)
        tongue_profile = compute_tongue_profile(name, folder, headings, tags, content, tongue)
        subjects, tasks, relations = extract_semantic_labels(name, folder, headings, tags, content)

        notes.append(VaultNote(
            path=rel_path,
            name=name,
            folder=folder,
            size=len(content),
            headings=headings[:10],
            tags=tags,
            outgoing_links=links,
            word_count=words,
            content_hash=content_hash,
            tongue=tongue,
            tongue_profile=tongue_profile,
            primary_weight_phi=round(TONGUE_PHI_WEIGHTS[tongue], 6),
            semantic_mass_phi=compute_semantic_mass(tongue_profile),
            tongue_sector_degrees=TONGUE_SECTORS_DEGREES[tongue],
            tongue_sector_radians=round(TONGUE_SECTORS_RADIANS[tongue], 6),
            subjects=subjects,
            tasks=tasks,
            relations=relations,
        ))

    # Build incoming links
    name_map = {n.name: n for n in notes}
    for note in notes:
        for link_target in note.outgoing_links:
            target = name_map.get(link_target)
            if target:
                target.incoming_links.append(note.name)

    for note in notes:
        if note.outgoing_links or note.incoming_links:
            note.relations = sorted(set(note.relations) | {"linked"})
        if note.outgoing_links and note.incoming_links:
            note.relations = sorted(set(note.relations) | {"bridge"})

    return notes


def build_graph(notes: List[VaultNote]) -> Dict:
    """Build a knowledge graph from vault notes."""
    name_map = {note.name: note for note in notes}
    explicit_target_pairs = set()
    explicit_connected = set()
    nodes = []

    for note in notes:
        nodes.append({
            "id": note.name,
            "path": note.path,
            "folder": note.folder,
            "tongue": note.tongue,
            "tongue_full_name": TONGUE_FULL_NAMES[note.tongue],
            "tongue_profile": note.tongue_profile,
            "primary_weight_phi": note.primary_weight_phi,
            "semantic_mass_phi": note.semantic_mass_phi,
            "tongue_sector_degrees": note.tongue_sector_degrees,
            "tongue_sector_radians": note.tongue_sector_radians,
            "subjects": note.subjects,
            "tasks": note.tasks,
            "relations": note.relations,
            "words": note.word_count,
            "headings": len(note.headings),
            "tags": note.tags,
            "outgoing": len(note.outgoing_links),
            "incoming": len(note.incoming_links),
        })

        for target in note.outgoing_links:
            explicit_connected.add(note.name)
            explicit_connected.add(target)
            if target in name_map:
                explicit_target_pairs.add(_pair_key(note.name, target))

    subject_index = defaultdict(list)
    task_index = defaultdict(list)
    relation_index = defaultdict(list)
    for note in notes:
        for subject in note.subjects:
            subject_index[subject].append(note.name)
        for task in note.tasks:
            task_index[task].append(note.name)
        for relation in note.relations:
            relation_index[relation].append(note.name)

    candidate_pairs: Set[Tuple[str, str]] = set(explicit_target_pairs)
    for index in (subject_index, task_index, relation_index):
        for names in index.values():
            unique_names = sorted(set(names))
            if len(unique_names) < 2 or len(unique_names) > MAX_CANDIDATE_BUCKET_SIZE:
                continue
            for pair in combinations(unique_names, 2):
                candidate_pairs.add(pair)

    pair_metrics: Dict[Tuple[str, str], Dict[str, object]] = {}
    for source_name, target_name in candidate_pairs:
        metrics = compute_semantic_gravity(
            name_map[source_name],
            name_map[target_name],
            explicit_link=(source_name, target_name) in explicit_target_pairs,
        )
        if metrics["semantic_gravity"] >= SEMANTIC_EDGE_MIN_GRAVITY or (source_name, target_name) in explicit_target_pairs:
            pair_metrics[(source_name, target_name)] = metrics

    edges = []
    total_edge_graph = defaultdict(list)
    for note in notes:
        for target in note.outgoing_links:
            edge = {
                "source": note.name,
                "target": target,
                "edge_kind": "explicit_link",
                "directionality": "directed",
                "explicit_link": True,
                "target_exists": target in name_map,
            }
            if target in name_map:
                metrics = pair_metrics.get(_pair_key(note.name, target)) or compute_semantic_gravity(note, name_map[target], explicit_link=True)
                edge.update(metrics)
                total_edge_graph[note.name].append(metrics["semantic_gravity"])
                total_edge_graph[target].append(metrics["semantic_gravity"])
            else:
                edge.update({
                    "subject_overlap": 0.0,
                    "task_overlap": 0.0,
                    "relation_overlap": 0.0,
                    "semantic_overlap": 0.0,
                    "shared_tongue_weight_phi": 0.0,
                    "sector_alignment": 0.0,
                    "semantic_gravity": 0.0,
                    "shared_subjects": [],
                    "shared_tasks": [],
                    "shared_relations": [],
                })
            edges.append(edge)

    explicit_edge_keys = {(edge["source"], edge["target"]) for edge in edges}
    for (source_name, target_name), metrics in sorted(pair_metrics.items()):
        if (source_name, target_name) in explicit_edge_keys or (target_name, source_name) in explicit_edge_keys:
            continue
        semantic_edge = {
            "source": source_name,
            "target": target_name,
            "edge_kind": "semantic_overlap",
            "directionality": "bidirectional",
            "explicit_link": False,
            "target_exists": True,
        }
        semantic_edge.update(metrics)
        edges.append(semantic_edge)
        total_edge_graph[source_name].append(metrics["semantic_gravity"])
        total_edge_graph[target_name].append(metrics["semantic_gravity"])

    max_gravity = max((edge["semantic_gravity"] for edge in edges), default=0.0)
    max_degree = max((len(values) for values in total_edge_graph.values()), default=0)
    node_null_scores = {}
    for note in notes:
        incident = total_edge_graph.get(note.name, [])
        avg_gravity = (sum(incident) / len(incident)) if incident else 0.0
        gravity_norm = (avg_gravity / max_gravity) if max_gravity else 0.0
        degree_norm = (len(incident) / max_degree) if max_degree else 0.0
        node_null_scores[note.name] = round(degree_norm * (1.0 - gravity_norm), 6)

    for node in nodes:
        node["null_space_score"] = node_null_scores.get(node["id"], 0.0)
        node["gravity_degree"] = len(total_edge_graph.get(node["id"], []))
        node["average_incident_gravity"] = round(
            (sum(total_edge_graph.get(node["id"], [])) / len(total_edge_graph.get(node["id"], [])))
            if total_edge_graph.get(node["id"])
            else 0.0,
            6,
        )

    null_space_paths = []
    if max_gravity and max_degree:
        for edge in edges:
            if edge["semantic_gravity"] <= 0:
                continue
            source_pressure = len(total_edge_graph.get(edge["source"], [])) / max_degree if max_degree else 0.0
            target_pressure = len(total_edge_graph.get(edge["target"], [])) / max_degree if max_degree else 0.0
            gravity_norm = edge["semantic_gravity"] / max_gravity
            null_flux = round(((source_pressure + target_pressure) / 2.0) * (1.0 - gravity_norm), 6)
            if null_flux <= 0:
                continue
            null_space_paths.append({
                "source": edge["source"],
                "target": edge["target"],
                "edge_kind": edge["edge_kind"],
                "semantic_gravity": edge["semantic_gravity"],
                "null_space_flux": null_flux,
                "source_null_space_score": node_null_scores.get(edge["source"], 0.0),
                "target_null_space_score": node_null_scores.get(edge["target"], 0.0),
            })
        null_space_paths.sort(key=lambda item: item["null_space_flux"], reverse=True)
        null_space_paths = null_space_paths[:NULL_PATH_LIMIT]

    # Find disconnected notes based on explicit links only for backwards compatibility.
    orphans = [n["id"] for n in nodes if n["id"] not in explicit_connected]
    semantic_connected = set()
    for edge in edges:
        semantic_connected.add(edge["source"])
        semantic_connected.add(edge["target"])
    semantic_orphans = [n["id"] for n in nodes if n["id"] not in semantic_connected]

    # Find clusters
    by_folder = defaultdict(list)
    by_tongue = defaultdict(list)
    for n in nodes:
        by_folder[n["folder"]].append(n["id"])
        by_tongue[n["tongue"]].append(n["id"])

    return {
        "nodes": nodes,
        "edges": edges,
        "null_space_paths": null_space_paths,
        "tongue_weights_phi": {tongue: round(weight, 6) for tongue, weight in TONGUE_PHI_WEIGHTS.items()},
        "tongue_sectors": {
            tongue: {
                "degrees": TONGUE_SECTORS_DEGREES[tongue],
                "radians": round(TONGUE_SECTORS_RADIANS[tongue], 6),
                "full_name": TONGUE_FULL_NAMES[tongue],
            }
            for tongue in TONGUE_ORDER
        },
        "stats": {
            "total_notes": len(nodes),
            "total_links": sum(1 for edge in edges if edge["edge_kind"] == "explicit_link"),
            "semantic_links": sum(1 for edge in edges if edge["edge_kind"] == "semantic_overlap"),
            "total_edges_enriched": len(edges),
            "orphan_notes": orphans,
            "orphan_count": len(orphans),
            "semantic_orphan_notes": semantic_orphans,
            "semantic_orphan_count": len(semantic_orphans),
            "max_semantic_gravity": round(max_gravity, 6),
            "mean_null_space_score": round(sum(node_null_scores.values()) / len(node_null_scores), 6) if node_null_scores else 0.0,
            "folders": dict(by_folder),
            "tongues": {t: len(v) for t, v in by_tongue.items()},
        },
    }


def suggest_connections(notes: List[VaultNote]) -> List[Dict]:
    """Suggest missing wiki-links based on name mentions in content."""
    suggestions = []
    name_set = {n.name for n in notes}

    for note in notes:
        try:
            content = (VAULT_PATH / note.path).read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        existing_links = set(note.outgoing_links)
        for other_name in name_set:
            if other_name == note.name or other_name in existing_links:
                continue
            if len(other_name) < 4:
                continue
            # Check if the other note's name appears in this note's content
            if other_name.lower() in content.lower():
                suggestions.append({
                    "source": note.name,
                    "target": other_name,
                    "reason": f"'{other_name}' mentioned in content but not linked",
                })

    return suggestions


def add_connections(suggestions: List[Dict], dry_run: bool = True) -> int:
    """Add wiki-links to notes based on suggestions."""
    added = 0
    by_source = defaultdict(list)
    for s in suggestions:
        by_source[s["source"]].append(s)

    auto_start = "<!-- scbe-auto-links:start -->"
    auto_end = "<!-- scbe-auto-links:end -->"
    auto_block_re = re.compile(
        r"(?s)\n##\s+Auto links\s*\n\s*<!--\s*scbe-auto-links:start\s*-->\n.*?<!--\s*scbe-auto-links:end\s*-->\n?",
        re.IGNORECASE,
    )

    for note_name, suggs in by_source.items():
        # Find the file
        matches = list(VAULT_PATH.rglob(f"{note_name}.md"))
        if not matches:
            continue
        filepath = matches[0]

        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        before_links = set(WIKI_LINK.findall(content))
        modified = content
        append_targets: Set[str] = set()

        for s in suggs:
            target = s["target"]
            if target in before_links:
                continue

            # Replace first plain-text mention with wiki-link (case-insensitive)
            pattern = re.compile(re.escape(target), re.IGNORECASE)
            match = pattern.search(modified)
            if match:
                original = match.group()
                # Don't replace if already inside a wiki-link
                start = match.start()
                before = modified[max(0, start - 2):start]
                if "[[" not in before:
                    modified = modified[:start] + f"[[{target}|{original}]]" + modified[match.end():]
                    continue

            # Fallback: if we can't inline-link, append an idempotent auto-links block.
            append_targets.add(target)

        if append_targets:
            # Remove any existing auto-links block so we can rewrite deterministically.
            base = auto_block_re.sub("\n", modified).rstrip()

            links_lines = "\n".join(f"- [[{t}]]" for t in sorted(append_targets))
            auto_block = (
                "\n\n## Auto links\n"
                f"{auto_start}\n"
                f"{links_lines}\n"
                f"{auto_end}\n"
            )
            modified = base + auto_block

        if modified != content and not dry_run:
            filepath.write_text(modified, encoding="utf-8")

        after_links = set(WIKI_LINK.findall(modified))
        added += len(after_links - before_links)

    return added


def export_sft(notes: List[VaultNote]) -> int:
    """Export vault as SFT training pairs."""
    pairs = []

    for note in notes:
        try:
            content = (VAULT_PATH / note.path).read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        if note.word_count < 30:
            continue

        # Pair 1: What is this note about?
        snippet = content[:600].replace("\n", " ").strip()
        pairs.append({
            "instruction": f"What is the Obsidian note '{note.name}' about in the SCBE knowledge vault?",
            "response": f"'{note.name}' is in the {note.folder or 'root'} folder (tongue: {note.tongue}). "
                        f"It has {note.word_count} words and covers: {snippet[:400]}",
            "source": "obsidian_vault",
            "category": f"vault_{note.tongue.lower()}",
            "tongue": note.tongue,
        })

        # Pair 2: How does this note connect to others?
        if note.outgoing_links or note.incoming_links:
            links_desc = ""
            if note.outgoing_links:
                links_desc += f"Links to: {', '.join(note.outgoing_links[:5])}. "
            if note.incoming_links:
                links_desc += f"Referenced by: {', '.join(note.incoming_links[:5])}."
            pairs.append({
                "instruction": f"How does '{note.name}' connect to other notes in the SCBE vault?",
                "response": links_desc,
                "source": "obsidian_vault",
                "category": "vault_graph",
                "tongue": note.tongue,
            })

    SFT_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(SFT_OUTPUT, "w", encoding="utf-8") as f:
        for p in pairs:
            json.dump(p, f, ensure_ascii=False)
            f.write("\n")

    return len(pairs)


def sync_to_cloud():
    """Copy vault to cloud sync folders."""
    synced = []
    for target in CLOUD_TARGETS:
        target.mkdir(parents=True, exist_ok=True)
        # Use robocopy on Windows for efficient sync
        import subprocess
        _result = subprocess.run(
            ["robocopy", str(VAULT_PATH), str(target), "/MIR", "/XD", ".obsidian", "/NFL", "/NDL", "/NJH", "/NJS"],
            capture_output=True, text=True
        )
        synced.append(str(target))
    return synced


def main():
    parser = argparse.ArgumentParser(description="Obsidian Vault Sync")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("scan", help="Inventory vault notes")
    sub.add_parser("graph", help="Build knowledge graph")

    c = sub.add_parser("connect", help="Suggest + add missing wiki-links")
    c.add_argument("--apply", action="store_true", help="Actually modify files (default: dry run)")

    sub.add_parser("export-sft", help="Export as SFT training data")
    sub.add_parser("sync-cloud", help="Sync to Dropbox/OneDrive")
    sub.add_parser("full", help="Scan + graph + connect + export + sync")

    args = parser.parse_args()

    if args.command in ("scan", "full"):
        notes = scan_vault()
        print(f"OBSIDIAN VAULT SCAN: {len(notes)} notes")
        print(f"  Total words: {sum(n.word_count for n in notes):,}")

        by_tongue = defaultdict(int)
        for n in notes:
            by_tongue[n.tongue] += 1
        print(f"  By tongue:")
        for t, c in sorted(by_tongue.items()):
            print(f"    {t}: {c}")

        by_folder = defaultdict(int)
        for n in notes:
            by_folder[n.folder or "(root)"] += 1
        print(f"  By folder:")
        for f, c in sorted(by_folder.items(), key=lambda x: x[1], reverse=True):
            print(f"    {f}: {c}")

    if args.command in ("graph", "full"):
        notes = scan_vault()
        graph = build_graph(notes)
        GRAPH_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        with open(GRAPH_OUTPUT, "w", encoding="utf-8") as f:
            json.dump(graph, f, indent=2, ensure_ascii=False)
        s = graph["stats"]
        print(f"\nKNOWLEDGE GRAPH:")
        print(f"  Nodes: {s['total_notes']} | Edges: {s['total_links']}")
        print(f"  Orphans (no links): {s['orphan_count']}")
        if s["orphan_notes"]:
            for o in s["orphan_notes"][:10]:
                print(f"    - {o}")
        print(f"  Graph: {GRAPH_OUTPUT}")

    if args.command in ("connect", "full"):
        notes = scan_vault()
        suggestions = suggest_connections(notes)
        apply = getattr(args, "apply", False) or args.command == "full"
        print(f"\nCONNECTION SUGGESTIONS: {len(suggestions)}")
        for s in suggestions[:20]:
            print(f"  {s['source']} -> [[{s['target']}]]  ({s['reason'][:50]})")
        if apply and suggestions:
            added = add_connections(suggestions, dry_run=False)
            print(f"\n  Applied {added} new wiki-links")
        elif suggestions:
            print(f"\n  Dry run. Use --apply to add links.")

    if args.command in ("export-sft", "full"):
        notes = scan_vault()
        count = export_sft(notes)
        print(f"\nSFT EXPORT: {count} training pairs -> {SFT_OUTPUT}")

    if args.command in ("sync-cloud", "full"):
        synced = sync_to_cloud()
        print(f"\nCLOUD SYNC:")
        for s in synced:
            print(f"  -> {s}")

    if not args.command:
        parser.print_help()


if __name__ == "__main__":
    main()
