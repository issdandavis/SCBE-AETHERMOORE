from __future__ import annotations

import glob
import hashlib
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from hydra.color_dimension import TONGUE_WAVELENGTHS, TONGUE_WEIGHTS
from hydra.octree_sphere_grid import HyperbolicLattice25D

_WORD_RE = re.compile(r"[A-Za-z0-9_']+")
_URL_RE = re.compile(r"https?://", flags=re.IGNORECASE)
_TAG_SANITIZE_RE = re.compile(r"[^a-z0-9._:-]+")


@dataclass(frozen=True)
class NoteRecord:
    note_id: str
    text: str
    tags: Tuple[str, ...] = ()
    source: str = "local"
    authority: str = "public"
    tongue: str = "KO"
    phase_rad: Optional[float] = None


def _clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _slug_tag(value: str) -> str:
    cleaned = _TAG_SANITIZE_RE.sub("-", (value or "").strip().lower())
    cleaned = cleaned.strip("-")
    return cleaned[:64]


def _hash_unit(seed: str) -> float:
    digest = hashlib.blake2s(seed.encode("utf-8"), digest_size=8).digest()
    raw = int.from_bytes(digest, "big", signed=False)
    return raw / float((1 << 64) - 1)


def load_notes_from_glob(
    pattern: str,
    max_notes: int = 100,
    source: str = "repo",
    authority: str = "public",
) -> List[NoteRecord]:
    paths = sorted(glob.glob(pattern, recursive=True))
    notes: List[NoteRecord] = []
    for p in paths:
        if len(notes) >= max(0, max_notes):
            break
        path = Path(p)
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix not in {".md", ".txt", ".rst"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        note_id = str(path.as_posix())
        notes.append(
            NoteRecord(
                note_id=note_id,
                text=text,
                tags=("imported", suffix.lstrip("."), "repo-note"),
                source=source,
                authority=authority,
                tongue="KO",
            )
        )
    return notes


def text_metrics(text: str) -> Dict[str, Any]:
    chars = len(text)
    words = _WORD_RE.findall(text)
    word_count = len(words)
    unique_word_count = len({w.lower() for w in words})
    lines = text.count("\n") + (1 if text else 0)
    digits = sum(ch.isdigit() for ch in text)
    uppercase = sum(ch.isupper() for ch in text)
    punctuation = sum(ch in ".,;:!?-_/\\()[]{}<>@#$%^&*+=" for ch in text)
    url_hits = len(_URL_RE.findall(text))

    unique_ratio = (unique_word_count / word_count) if word_count else 0.0
    digit_ratio = (digits / chars) if chars else 0.0
    uppercase_ratio = (uppercase / chars) if chars else 0.0
    punctuation_ratio = (punctuation / chars) if chars else 0.0

    return {
        "char_count": chars,
        "line_count": lines,
        "word_count": word_count,
        "unique_word_count": unique_word_count,
        "unique_ratio": unique_ratio,
        "digit_ratio": digit_ratio,
        "uppercase_ratio": uppercase_ratio,
        "punctuation_ratio": punctuation_ratio,
        "url_count": url_hits,
        "has_url": url_hits > 0,
    }


def metric_tags(
    metrics: Dict[str, Any],
    *,
    base_tags: Sequence[str],
    source: str,
    authority: str,
    tongue: str,
) -> List[str]:
    tags = {
        "lattice25d",
        f"source:{_slug_tag(source) or 'local'}",
        f"authority:{_slug_tag(authority) or 'public'}",
        f"tongue:{_slug_tag(tongue) or 'ko'}",
    }

    char_count = int(metrics.get("char_count", 0))
    word_count = int(metrics.get("word_count", 0))
    unique_ratio = float(metrics.get("unique_ratio", 0.0))

    if char_count < 240:
        tags.add("length:tiny")
    elif char_count < 1200:
        tags.add("length:short")
    elif char_count < 5000:
        tags.add("length:medium")
    else:
        tags.add("length:long")

    if word_count < 40:
        tags.add("density:light")
    elif word_count < 220:
        tags.add("density:normal")
    else:
        tags.add("density:dense")

    if unique_ratio >= 0.8:
        tags.add("lexical:high-diversity")
    elif unique_ratio >= 0.55:
        tags.add("lexical:balanced")
    else:
        tags.add("lexical:repetitive")

    if metrics.get("has_url"):
        tags.add("contains:url")
    if float(metrics.get("digit_ratio", 0.0)) > 0.05:
        tags.add("contains:numeric")
    if float(metrics.get("uppercase_ratio", 0.0)) > 0.15:
        tags.add("style:loud")

    for raw in base_tags:
        slug = _slug_tag(raw)
        if slug:
            tags.add(f"tag:{slug}")

    return sorted(tags)


def intent_from_metrics(metrics: Dict[str, Any]) -> List[float]:
    word_norm = _clip(float(metrics.get("word_count", 0)) / 600.0, 0.0, 1.0)
    unique_ratio = _clip(float(metrics.get("unique_ratio", 0.0)), 0.0, 1.0)
    punctuation_ratio = _clip(float(metrics.get("punctuation_ratio", 0.0)), 0.0, 1.0)
    uppercase_ratio = _clip(float(metrics.get("uppercase_ratio", 0.0)), 0.0, 1.0)
    has_url = 1.0 if metrics.get("has_url") else 0.0

    governance = _clip(
        0.2 + 0.45 * uppercase_ratio + 0.35 * punctuation_ratio + 0.15 * has_url,
        0.0,
        1.0,
    )
    research = _clip(
        0.2 + 0.4 * unique_ratio + 0.25 * word_norm + 0.25 * has_url,
        0.0,
        1.0,
    )
    cohesion = _clip(1.0 - abs(governance - research), 0.0, 1.0)
    return [governance, research, cohesion]


def _select_tongue(preferred: str, index: int, seed: str) -> str:
    if preferred in TONGUE_WEIGHTS:
        return preferred
    tongues = list(TONGUE_WEIGHTS.keys())
    if not tongues:
        return "KO"
    offset = int(_hash_unit(seed) * 1_000_000)
    return tongues[(index + offset) % len(tongues)]


def _position_for_note(note_id: str, radius: float, phase_rad: Optional[float]) -> Tuple[float, float, float]:
    angle = 2.0 * math.pi * _hash_unit(f"{note_id}|angle")
    radial = 0.05 + _clip(radius, 0.05, 0.95) * _hash_unit(f"{note_id}|radius")
    x = math.cos(angle) * radial
    y = math.sin(angle) * radial
    if phase_rad is None:
        phase = 2.0 * math.pi * _hash_unit(f"{note_id}|phase")
    else:
        phase = phase_rad
    return x, y, phase


def build_lattice25d_payload(
    notes: Sequence[NoteRecord],
    *,
    cell_size: float = 0.4,
    max_depth: int = 6,
    phase_weight: float = 0.35,
    radius: float = 0.72,
    query_intent: Optional[List[float]] = None,
    query_x: float = 0.1,
    query_y: float = 0.1,
    query_phase: float = 0.0,
    query_top_k: int = 5,
) -> Dict[str, Any]:
    if not notes:
        raise ValueError("at least one note is required")

    lattice = HyperbolicLattice25D(
        cell_size=cell_size,
        max_depth=max_depth,
        phase_weight=phase_weight,
    )

    inserted: List[Dict[str, Any]] = []
    for idx, note in enumerate(notes):
        note_id = note.note_id or f"note-{idx}"
        text = note.text or ""
        metrics = text_metrics(text)
        tongue = _select_tongue(note.tongue, idx, note_id)
        tags = metric_tags(
            metrics,
            base_tags=list(note.tags),
            source=note.source,
            authority=note.authority,
            tongue=tongue,
        )
        intent = intent_from_metrics(metrics)
        x, y, phase = _position_for_note(note_id, radius=radius, phase_rad=note.phase_rad)

        bundle = lattice.insert_bundle(
            x=x,
            y=y,
            phase_rad=phase,
            tongue=tongue,
            authority=note.authority or "public",
            intent_vector=intent,
            intent_label=(note_id[:48] if note_id else f"note-{idx}"),
            payload={
                "note_id": note_id,
                "source": note.source,
                "tags": tags,
                "metrics": metrics,
                "snippet": text[:220],
            },
            wavelength_nm=float(TONGUE_WAVELENGTHS.get(tongue, 550.0)),
        )

        inserted.append(
            {
                "note_id": note_id,
                "bundle_id": bundle.bundle_id,
                "tongue": bundle.tongue,
                "authority": bundle.authority,
                "phase_rad": bundle.phase_rad,
                "position": [bundle.x, bundle.y],
                "intent_vector": [float(v) for v in bundle.intent_vector],
                "metric_tags": tags,
                "metrics": metrics,
            }
        )

    nearest = lattice.query_nearest(
        x=query_x,
        y=query_y,
        phase_rad=query_phase,
        intent_vector=query_intent or [0.9, 0.1, 0.1],
        tongue="DR",
        top_k=max(1, query_top_k),
    )

    overlap = sorted(
        (
            {
                "cell": [cell[0], cell[1]],
                "count": len(items),
                "bundle_ids": [b.bundle_id for b in items],
            }
            for cell, items in lattice.overlapping_cells().items()
        ),
        key=lambda row: row["count"],
        reverse=True,
    )

    return {
        "dimensions": ["x", "y", "phase", "tongue", "authority", "intent"],
        "ingested_count": len(inserted),
        "stats": lattice.stats(),
        "overlap_cells": overlap,
        "lace_edge_count": len(lattice.lace_edges()),
        "query": {
            "x": query_x,
            "y": query_y,
            "phase_rad": query_phase,
            "intent_vector": query_intent or [0.9, 0.1, 0.1],
            "top_k": max(1, query_top_k),
        },
        "nearest": [
            {
                "bundle_id": b.bundle_id,
                "note_label": b.intent_label,
                "tongue": b.tongue,
                "authority": b.authority,
                "phase_rad": b.phase_rad,
                "distance": dist,
                "tags": list((b.payload or {}).get("tags", [])),
            }
            for b, dist in nearest
        ],
        "notes": inserted,
    }


def sample_notes(count: int = 12) -> List[NoteRecord]:
    templates = [
        "Swarm navigation checkpoint with decimal drift residual below threshold.",
        "Council review notes with multi-model vote deltas and risk tags.",
        "Research summary with arXiv citations and geometric routing constraints.",
        "Deployment lane notes for n8n callback integrity and queue throughput.",
    ]
    tongues = list(TONGUE_WEIGHTS.keys()) or ["KO"]
    out: List[NoteRecord] = []
    for idx in range(max(1, count)):
        text = f"{templates[idx % len(templates)]} Item {idx}."
        out.append(
            NoteRecord(
                note_id=f"sample-{idx}",
                text=text,
                tags=("sample", f"lane-{idx % 4}"),
                source="sample",
                authority=["public", "internal", "sealed"][idx % 3],
                tongue=tongues[idx % len(tongues)],
                phase_rad=((idx * 0.73) % (2.0 * math.pi)),
            )
        )
    return out

