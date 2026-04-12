from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

from src.ca_lexicon import TONGUE_NAMES
from src.mempalace.rooms import Room

TONGUE_TO_SPHERE_DIR: Dict[str, str] = {
    "KO": "KO-Command",
    "AV": "AV-Transport",
    "RU": "RU-Entropy",
    "CA": "CA-Compute",
    "UM": "UM-Security",
    "DR": "DR-Structure",
}

BAND_TO_PRIMARY_TONGUE: Dict[str, str] = {
    "ARITHMETIC": "CA",
    "LOGIC": "CA",
    "COMPARISON": "CA",
    "AGGREGATION": "CA",
}

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_TAG_RE = re.compile(r"(?:^|\s)#([A-Za-z][\w-]{1,63})")
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+)(?:\|[^\]]*)?\]\]")


@dataclass
class NoteRecord:
    """One indexed vault note."""

    path: Path
    size: int
    sha256: str
    tags: Tuple[str, ...] = ()
    wikilinks: Tuple[str, ...] = ()
    tongues: Tuple[str, ...] = ()

    @property
    def stem(self) -> str:
        return self.path.stem


@dataclass
class VaultIndex:
    """Indexer for the Obsidian vault. Never deletes; finds duplicates by hash."""

    root: Path
    include_suffixes: Tuple[str, ...] = (".md",)
    exclude_dirs: Tuple[str, ...] = (".obsidian", ".trash", "_quarantine")
    records: Dict[Path, NoteRecord] = field(default_factory=dict)
    by_hash: Dict[str, List[Path]] = field(default_factory=dict)
    by_tongue: Dict[str, List[Path]] = field(default_factory=dict)

    def scan(self, hash_content: bool = True) -> "VaultIndex":
        if not self.root.exists():
            return self
        for path in self._walk():
            rec = self._record(path, hash_content=hash_content)
            self.records[path] = rec
            self.by_hash.setdefault(rec.sha256, []).append(path)
            for tongue in rec.tongues:
                self.by_tongue.setdefault(tongue, []).append(path)
        return self

    def _walk(self) -> Iterable[Path]:
        excluded = set(self.exclude_dirs)
        for path in self.root.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in self.include_suffixes:
                continue
            if any(part in excluded for part in path.parts):
                continue
            yield path

    def _record(self, path: Path, hash_content: bool) -> NoteRecord:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            text = ""
        size = len(text.encode("utf-8"))
        sha = self._sha256(text) if hash_content else ""
        tags = self._extract_tags(text)
        links = self._extract_wikilinks(text)
        tongues = self._detect_tongues(path, text)
        return NoteRecord(
            path=path,
            size=size,
            sha256=sha,
            tags=tuple(tags),
            wikilinks=tuple(links),
            tongues=tuple(tongues),
        )

    @staticmethod
    def _sha256(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _extract_tags(text: str) -> List[str]:
        seen: Set[str] = set()
        out: List[str] = []
        fm = _FRONTMATTER_RE.match(text)
        if fm:
            for line in fm.group(1).splitlines():
                stripped = line.strip()
                if stripped.startswith("- "):
                    tag = stripped[2:].strip().strip("\"'")
                    if tag and tag not in seen:
                        seen.add(tag)
                        out.append(tag)
                elif stripped.lower().startswith("tags:"):
                    rest = stripped[5:].strip()
                    if rest.startswith("[") and rest.endswith("]"):
                        for token in rest[1:-1].split(","):
                            tag = token.strip().strip("\"'")
                            if tag and tag not in seen:
                                seen.add(tag)
                                out.append(tag)
        for match in _TAG_RE.finditer(text):
            tag = match.group(1)
            if tag not in seen:
                seen.add(tag)
                out.append(tag)
        return out

    @staticmethod
    def _extract_wikilinks(text: str) -> List[str]:
        seen: Set[str] = set()
        out: List[str] = []
        for match in _WIKILINK_RE.finditer(text):
            target = match.group(1).strip()
            if target and target not in seen:
                seen.add(target)
                out.append(target)
        return out

    @staticmethod
    def _detect_tongues(path: Path, text: str) -> List[str]:
        """Tongues active in a note = path-derived + content-derived."""
        tongues: List[str] = []
        parts = {part.upper() for part in path.parts}
        for tongue, sphere_dir in TONGUE_TO_SPHERE_DIR.items():
            if sphere_dir.upper() in parts:
                tongues.append(tongue)
        upper = text.upper()
        for tongue in TONGUE_NAMES:
            sphere = TONGUE_TO_SPHERE_DIR[tongue].upper()
            if tongue not in tongues and sphere in upper:
                tongues.append(tongue)
        return tongues

    def find_duplicates(self) -> Dict[str, List[Path]]:
        return {h: paths for h, paths in self.by_hash.items() if len(paths) > 1}

    def duplicate_count(self) -> int:
        return sum(len(paths) - 1 for paths in self.by_hash.values() if len(paths) > 1)

    def save(self, path: Path) -> Path:
        """Serialize the index to a JSON cache file. Read-only on the vault."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "root": str(self.root),
            "include_suffixes": list(self.include_suffixes),
            "exclude_dirs": list(self.exclude_dirs),
            "records": [
                {
                    "path": str(rec.path),
                    "size": rec.size,
                    "sha256": rec.sha256,
                    "tags": list(rec.tags),
                    "wikilinks": list(rec.wikilinks),
                    "tongues": list(rec.tongues),
                }
                for rec in self.records.values()
            ],
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    @classmethod
    def load(cls, path: Path) -> "VaultIndex":
        """Rebuild an index from a JSON cache. Does not re-read the vault."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        idx = cls(
            root=Path(data["root"]),
            include_suffixes=tuple(data.get("include_suffixes", (".md",))),
            exclude_dirs=tuple(data.get("exclude_dirs", (".obsidian", ".trash", "_quarantine"))),
        )
        for raw in data.get("records", []):
            p = Path(raw["path"])
            rec = NoteRecord(
                path=p,
                size=int(raw["size"]),
                sha256=raw["sha256"],
                tags=tuple(raw.get("tags", ())),
                wikilinks=tuple(raw.get("wikilinks", ())),
                tongues=tuple(raw.get("tongues", ())),
            )
            idx.records[p] = rec
            idx.by_hash.setdefault(rec.sha256, []).append(p)
            for tongue in rec.tongues:
                idx.by_tongue.setdefault(tongue, []).append(p)
        return idx


def link_rooms_to_notes(
    palace: Dict[int, Room],
    index: VaultIndex,
    sphere_subdir: str = "sphere-grid",
) -> Dict[int, List[Path]]:
    """Attach vault notes to rooms via tongue corridors and band-primary tongue.

    For each room:
      1. Walk room.entry.trit; every tongue with non-zero trit contributes its sphere-grid notes.
      2. The band's primary tongue (defaults to CA) always contributes.
      3. Results are deduplicated.
    """
    if not index.root.exists():
        return {rid: [] for rid in palace}

    sphere_root = index.root / sphere_subdir
    tongue_to_paths: Dict[str, List[Path]] = {}
    if sphere_root.exists():
        for tongue, dirname in TONGUE_TO_SPHERE_DIR.items():
            tdir = sphere_root / dirname
            if not tdir.exists():
                continue
            notes: List[Path] = []
            for path in tdir.rglob("*.md"):
                if path.is_file():
                    notes.append(path)
            tongue_to_paths[tongue] = notes

    out: Dict[int, List[Path]] = {}
    for rid, room in palace.items():
        selected: List[Path] = []
        seen: Set[Path] = set()
        for t_idx, t_name in enumerate(TONGUE_NAMES):
            if room.entry.trit[t_idx] != 0:
                for path in tongue_to_paths.get(t_name, []):
                    if path not in seen:
                        seen.add(path)
                        selected.append(path)
        primary = BAND_TO_PRIMARY_TONGUE.get(room.wing, "CA")
        for path in tongue_to_paths.get(primary, []):
            if path not in seen:
                seen.add(path)
                selected.append(path)
        out[rid] = selected
    return out


def room_tongue_profile(room: Room) -> Dict[str, int]:
    """Return {tongue_name: trit} for every active tongue of a room."""
    return {
        name: room.entry.trit[i]
        for i, name in enumerate(TONGUE_NAMES)
        if room.entry.trit[i] != 0
    }


def vault_stats(index: VaultIndex) -> Dict[str, object]:
    """Summary stats for lattice visualization. Read-only."""
    tag_counts: Dict[str, int] = {}
    for rec in index.records.values():
        for tag in rec.tags:
            tag_counts[tag] = tag_counts.get(tag, 0) + 1
    tongue_counts = {t: len(paths) for t, paths in index.by_tongue.items()}
    dup_clusters = index.find_duplicates()
    largest_clusters = sorted(
        ((h, paths) for h, paths in dup_clusters.items()),
        key=lambda kv: len(kv[1]),
        reverse=True,
    )[:10]
    top_tags = sorted(tag_counts.items(), key=lambda kv: kv[1], reverse=True)[:25]
    total_size = sum(rec.size for rec in index.records.values())
    return {
        "note_count": len(index.records),
        "unique_hashes": len(index.by_hash),
        "duplicate_clusters": len(dup_clusters),
        "duplicate_extra_copies": index.duplicate_count(),
        "total_bytes": total_size,
        "tongue_counts": tongue_counts,
        "top_tags": top_tags,
        "largest_clusters": [(h, len(paths)) for h, paths in largest_clusters],
    }


def dedup_report(index: VaultIndex, output_path: Path) -> Path:
    """Write a human-readable dedup report. Never deletes. Read-only on the vault."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dups = index.find_duplicates()
    lines: List[str] = []
    lines.append("# Vault Duplicate Report")
    lines.append("")
    lines.append(f"- Scanned root: `{index.root}`")
    lines.append(f"- Notes indexed: {len(index.records)}")
    lines.append(f"- Unique content hashes: {len(index.by_hash)}")
    lines.append(f"- Duplicate clusters: {len(dups)}")
    lines.append(f"- Extra copies (beyond one canonical per cluster): {index.duplicate_count()}")
    lines.append("")
    lines.append("> **Never-delete rule.** This report lists duplicates by SHA-256 content hash.")
    lines.append("> Nothing is removed. Review clusters manually or quarantine via a reversible move.")
    lines.append("")
    sorted_clusters = sorted(dups.items(), key=lambda kv: len(kv[1]), reverse=True)
    for h, paths in sorted_clusters[:200]:
        lines.append(f"## cluster `{h[:12]}` — {len(paths)} copies")
        for p in paths:
            try:
                rel = p.relative_to(index.root)
            except ValueError:
                rel = p
            lines.append(f"- `{rel}`")
        lines.append("")
    if len(sorted_clusters) > 200:
        lines.append(f"_({len(sorted_clusters) - 200} additional clusters omitted for brevity.)_")
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path


def stats_report(index: VaultIndex, output_path: Path) -> Path:
    """Write a lattice-stats markdown summary. Read-only."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    stats = vault_stats(index)
    lines: List[str] = []
    lines.append("# Vault Lattice Stats")
    lines.append("")
    lines.append(f"- Root: `{index.root}`")
    lines.append(f"- Notes: {stats['note_count']}")
    lines.append(f"- Unique content hashes: {stats['unique_hashes']}")
    lines.append(f"- Duplicate clusters: {stats['duplicate_clusters']}")
    lines.append(f"- Extra duplicate copies: {stats['duplicate_extra_copies']}")
    lines.append(f"- Total bytes: {stats['total_bytes']}")
    lines.append("")
    lines.append("## Tongue distribution")
    lines.append("")
    for tongue, count in sorted(stats["tongue_counts"].items(), key=lambda kv: kv[1], reverse=True):
        lines.append(f"- {tongue}: {count}")
    lines.append("")
    lines.append("## Top tags")
    lines.append("")
    for tag, count in stats["top_tags"]:
        lines.append(f"- `{tag}`: {count}")
    lines.append("")
    lines.append("## Largest duplicate clusters")
    lines.append("")
    for h, n in stats["largest_clusters"]:
        lines.append(f"- `{h[:12]}`: {n} copies")
    lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
