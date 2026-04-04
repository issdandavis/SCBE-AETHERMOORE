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
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set

ROOT = Path(__file__).resolve().parent.parent.parent
VAULT_PATH = Path(os.environ.get("OBSIDIAN_VAULT", r"C:\Users\issda\Documents\Avalon Files"))
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
        ))

    # Build incoming links
    name_map = {n.name: n for n in notes}
    for note in notes:
        for link_target in note.outgoing_links:
            target = name_map.get(link_target)
            if target:
                target.incoming_links.append(note.name)

    return notes


def build_graph(notes: List[VaultNote]) -> Dict:
    """Build a knowledge graph from vault notes."""
    nodes = []
    edges = []

    for note in notes:
        nodes.append({
            "id": note.name,
            "folder": note.folder,
            "tongue": note.tongue,
            "words": note.word_count,
            "headings": len(note.headings),
            "tags": note.tags,
            "outgoing": len(note.outgoing_links),
            "incoming": len(note.incoming_links),
        })

        for target in note.outgoing_links:
            edges.append({"source": note.name, "target": target})

    # Find disconnected notes (no links in or out)
    connected = set()
    for e in edges:
        connected.add(e["source"])
        connected.add(e["target"])
    orphans = [n["id"] for n in nodes if n["id"] not in connected]

    # Find clusters
    by_folder = defaultdict(list)
    by_tongue = defaultdict(list)
    for n in nodes:
        by_folder[n["folder"]].append(n["id"])
        by_tongue[n["tongue"]].append(n["id"])

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": {
            "total_notes": len(nodes),
            "total_links": len(edges),
            "orphan_notes": orphans,
            "orphan_count": len(orphans),
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
