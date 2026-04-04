"""Obsidian Inflow — Collect knowledge from all ponds and push INTO Obsidian.

Complements obsidian_vault_sync.py (which pushes OUT). This script pulls
from GitLab repos, GitHub commits, HuggingFace, training JSONL, the lore
bible, and ChatGPT exports, then creates/updates Obsidian notes with
YAML frontmatter, wiki-links, and correct subfolder placement.

Usage:
    python scripts/apollo/obsidian_inflow.py --source gitlab --dry-run
    python scripts/apollo/obsidian_inflow.py --source all
    python scripts/apollo/obsidian_inflow.py --source lore-bible
    python scripts/apollo/obsidian_inflow.py --source github
    python scripts/apollo/obsidian_inflow.py --source huggingface
    python scripts/apollo/obsidian_inflow.py --source training
    python scripts/apollo/obsidian_inflow.py --source chatgpt
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import zipfile
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent.parent

VAULT_PATH = Path(
    os.environ.get(
        "OBSIDIAN_VAULT",
        r"C:\Users\issda\Documents\Avalon Files\SCBE Research",
    )
)

GITLAB_REPOS: List[Path] = [
    Path("/tmp/Avalon"),
    Path("/tmp/Aethromoor"),
]

LORE_BIBLE = ROOT / "artifacts" / "book" / "LORE_BIBLE_COMPLETE.md"

TRAINING_DATA_DIR = ROOT / "training-data"

CHATGPT_ZIP = Path(
    r"C:\Users\issda\OneDrive\Books\Avalon_Reference_Pack"
    r"\chatgpt_data_export_20250608.zip"
)

REPORT_PATH = ROOT / "artifacts" / "apollo" / "obsidian_inflow_report.json"

# Vault subfolder mapping
FOLDER_MAP = {
    "character": "People",
    "person": "People",
    "npc": "People",
    "location": "Architecture",
    "place": "Architecture",
    "geography": "Architecture",
    "faction": "Theories",
    "theory": "Theories",
    "magic": "Theories",
    "tongue": "Tongues",
    "language": "Tongues",
    "model": "Products",
    "dataset": "Products",
    "concept": "Ideas",
    "idea": "Ideas",
    "session": "Research Results",
    "research": "Research Results",
    "ops": "Ops",
    "agent": "Agent Ops",
    "infrastructure": "Infrastructure",
    "growth": "Growth Log",
    "writing": "Writing",
    "reference": "References",
    "architecture": "Architecture",
    "product": "Products",
    "cddm": "CDDM",
}

# Characters and locations we know from the lore bible — used for wiki-linking
KNOWN_ENTITIES: Set[str] = set()

NOW = datetime.datetime.now(datetime.timezone.utc)
TODAY = NOW.strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
@dataclass
class InflowNote:
    """A note to be written into the vault."""

    title: str
    folder: str  # Vault subfolder name
    body: str
    note_type: str  # character, location, concept, session, model, dataset, etc.
    source: str  # gitlab, github, huggingface, training, lore-bible, chatgpt
    tags: List[str] = field(default_factory=list)
    links: List[str] = field(default_factory=list)
    date: str = ""

    def __post_init__(self):
        if not self.date:
            self.date = TODAY

    def filename(self) -> str:
        """Safe filename for this note."""
        safe = re.sub(r'[<>:"/\\|?*]', "", self.title)
        safe = safe.strip(". ")
        if not safe:
            safe = "Untitled"
        return safe + ".md"

    def frontmatter(self) -> str:
        tags_str = "\n".join(f"  - {t}" for t in self.tags) if self.tags else "  - inflow"
        return (
            "---\n"
            f"title: \"{self.title}\"\n"
            f"type: {self.note_type}\n"
            f"source: {self.source}\n"
            f"date: {self.date}\n"
            f"tags:\n{tags_str}\n"
            "---\n"
        )

    def render(self) -> str:
        """Render the full note content with frontmatter and wiki-links."""
        content = self.frontmatter() + "\n" + self.body

        # Inject wiki-links for known entities mentioned in the body
        for entity in self.links:
            if entity in content and f"[[{entity}]]" not in content:
                # Replace first plain-text mention (not already linked)
                pattern = re.compile(re.escape(entity))
                match = pattern.search(content)
                if match:
                    start = match.start()
                    before = content[max(0, start - 2) : start]
                    if "[[" not in before:
                        content = (
                            content[:start]
                            + f"[[{entity}]]"
                            + content[match.end() :]
                        )

        # Add related notes section if there are links
        if self.links:
            content += "\n\n## Related Notes\n"
            for link in sorted(set(self.links)):
                content += f"- [[{link}]]\n"

        return content


def sanitize_title(raw: str) -> str:
    """Clean up a title string."""
    title = raw.strip().strip("#").strip()
    title = re.sub(r"\s+", " ", title)
    title = re.sub(r'[<>:"/\\|?*]', "", title)
    return title[:120]


def resolve_folder(note_type: str, fallback: str = "Ideas") -> str:
    """Map a note type to a vault subfolder."""
    return FOLDER_MAP.get(note_type.lower(), fallback)


def note_exists(folder: str, filename: str) -> bool:
    """Check if a note already exists in the vault."""
    target = VAULT_PATH / folder / filename
    return target.exists()


def write_note(note: InflowNote, dry_run: bool = False) -> Tuple[bool, str]:
    """Write a note to the vault. Returns (created, path)."""
    folder_path = VAULT_PATH / note.folder
    filepath = folder_path / note.filename()

    if filepath.exists():
        return False, str(filepath)

    if dry_run:
        return True, str(filepath)

    folder_path.mkdir(parents=True, exist_ok=True)
    filepath.write_text(note.render(), encoding="utf-8")
    return True, str(filepath)


def find_wiki_links(text: str, known: Set[str]) -> List[str]:
    """Find entities from the known set that appear in the text."""
    links = []
    text_lower = text.lower()
    for entity in known:
        if len(entity) >= 4 and entity.lower() in text_lower:
            links.append(entity)
    return links


# ---------------------------------------------------------------------------
# Source: GitLab Repos (/tmp/Avalon, /tmp/Aethromoor)
# ---------------------------------------------------------------------------
def inflow_gitlab() -> List[InflowNote]:
    """Extract characters, locations, and plot points from GitLab repos."""
    notes: List[InflowNote] = []

    for repo_path in GITLAB_REPOS:
        if not repo_path.exists():
            print(f"  SKIP: {repo_path} not found")
            continue

        repo_name = repo_path.name
        print(f"  Scanning {repo_name}...")

        # Scan lore/ and writing_drafts/ directories for narrative content
        lore_dirs = [
            repo_path / "lore",
            repo_path / "writing_drafts",
            repo_path / "docs",
        ]

        for lore_dir in lore_dirs:
            if not lore_dir.exists():
                continue

            for md_file in lore_dir.rglob("*.md"):
                try:
                    content = md_file.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue

                if len(content) < 100:
                    continue

                title = sanitize_title(md_file.stem)
                if not title:
                    continue

                # Classify note type from content and filename
                note_type = _classify_gitlab_content(title, content)
                folder = resolve_folder(note_type)

                links = find_wiki_links(content, KNOWN_ENTITIES)

                notes.append(
                    InflowNote(
                        title=f"{title} ({repo_name})",
                        folder=folder,
                        body=f"# {title}\n\nSource: `{repo_name}/{md_file.relative_to(repo_path)}`\n\n{content[:3000]}",
                        note_type=note_type,
                        source="gitlab",
                        tags=[repo_name.lower(), note_type, "inflow"],
                        links=links,
                    )
                )

        # Scan for ChoiceScript game content
        cs_dir = repo_path / "choicescript_game"
        if cs_dir.exists():
            for scene_file in cs_dir.glob("*.txt"):
                try:
                    content = scene_file.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue
                if len(content) < 200:
                    continue

                title = sanitize_title(scene_file.stem)
                # Extract character names from *goto and *label lines
                chars = set(
                    re.findall(r"(?:^|\s)([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)", content[:2000])
                )
                links = [c for c in chars if len(c) > 3]

                notes.append(
                    InflowNote(
                        title=f"Scene - {title} ({repo_name})",
                        folder="Writing",
                        body=f"# Scene: {title}\n\nSource: `{repo_name}/choicescript_game/{scene_file.name}`\n\nCharacters mentioned: {', '.join(sorted(links)[:15])}\n\n```\n{content[:2000]}\n```",
                        note_type="writing",
                        source="gitlab",
                        tags=[repo_name.lower(), "choicescript", "scene", "inflow"],
                        links=links[:10],
                    )
                )

        # Extract character names from key reference files
        for ref_file in [
            "GAME_DEVELOPMENT_MASTER_REFERENCE.md",
            "COMPLETE_MATERIALS_SUMMARY.md",
            "AETHERMOOR_CHRONICLES.md",
            "README.md",
        ]:
            path = repo_path / ref_file
            if path.exists():
                try:
                    content = path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue

                # Extract character names (capitalized multi-word patterns)
                char_matches = re.findall(
                    r"\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,}){0,2})\b", content
                )
                for name in set(char_matches):
                    if len(name) > 4:
                        KNOWN_ENTITIES.add(name)

    print(f"  GitLab: {len(notes)} notes extracted")
    return notes


def _classify_gitlab_content(title: str, content: str) -> str:
    """Classify GitLab content into a note type."""
    t = title.lower()
    c = content[:500].lower()

    if any(k in t for k in ["character", "npc", "cast", "person"]):
        return "character"
    if any(k in t for k in ["location", "map", "region", "realm", "place"]):
        return "location"
    if any(k in t for k in ["lore", "history", "chronicle"]):
        return "writing"
    if any(k in t for k in ["game", "mechanic", "system"]):
        return "concept"
    if any(k in c for k in ["character", "personality", "appearance", "backstory"]):
        return "character"
    if any(k in c for k in ["located", "geography", "terrain", "realm"]):
        return "location"
    return "reference"


# ---------------------------------------------------------------------------
# Source: GitHub Commits (recent)
# ---------------------------------------------------------------------------
def inflow_github() -> List[InflowNote]:
    """Summarize recent GitHub commits into Session Log notes."""
    notes: List[InflowNote] = []

    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "--since=7 days ago", "-50"],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        commits = result.stdout.strip().split("\n") if result.stdout.strip() else []
    except Exception:
        print("  SKIP: git not available")
        return notes

    if not commits:
        print("  GitHub: no recent commits")
        return notes

    # Group commits by date
    try:
        result_full = subprocess.run(
            [
                "git",
                "log",
                "--format=%H|%ai|%s",
                "--since=7 days ago",
                "-50",
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        lines = result_full.stdout.strip().split("\n") if result_full.stdout.strip() else []
    except Exception:
        lines = []

    by_date: Dict[str, List[str]] = defaultdict(list)
    for line in lines:
        if "|" not in line:
            continue
        parts = line.split("|", 2)
        if len(parts) < 3:
            continue
        commit_hash, date_str, message = parts
        day = date_str[:10]
        by_date[day].append(f"- `{commit_hash[:8]}` {message}")

    for day, commit_lines in sorted(by_date.items()):
        title = f"Session Log {day}"
        body = f"# Session Log: {day}\n\n"
        body += f"**{len(commit_lines)} commits** to SCBE-AETHERMOORE\n\n"
        body += "## Commits\n\n"
        body += "\n".join(commit_lines)

        # Classify the session
        all_msgs = " ".join(commit_lines).lower()
        tags = ["github", "session-log", "inflow"]
        if "feat" in all_msgs:
            tags.append("feature")
        if "fix" in all_msgs:
            tags.append("bugfix")
        if "docs" in all_msgs:
            tags.append("docs")
        if "test" in all_msgs:
            tags.append("testing")

        links = find_wiki_links(all_msgs, KNOWN_ENTITIES)

        notes.append(
            InflowNote(
                title=title,
                folder="Growth Log",
                body=body,
                note_type="session",
                source="github",
                tags=tags,
                links=links,
                date=day,
            )
        )

    print(f"  GitHub: {len(notes)} session log notes")
    return notes


# ---------------------------------------------------------------------------
# Source: HuggingFace (models + datasets)
# ---------------------------------------------------------------------------
def inflow_huggingface() -> List[InflowNote]:
    """Create Model and Dataset notes from HuggingFace repos."""
    notes: List[InflowNote] = []

    # Known HF repos (from MEMORY.md)
    hf_models = [
        ("issdandavis/phdm-21d-embedding", "model"),
        ("issdandavis/spiralverse-ai-federated-v1", "model"),
    ]
    hf_datasets = [
        ("issdandavis/scbe-aethermoore-training-data", "dataset"),
    ]

    # Try to list repos via huggingface_hub if available
    try:
        from huggingface_hub import HfApi

        api = HfApi()
        for model in api.list_models(author="issdandavis"):
            repo_id = model.modelId
            if repo_id not in [m[0] for m in hf_models]:
                hf_models.append((repo_id, "model"))

        for ds in api.list_datasets(author="issdandavis"):
            repo_id = ds.id
            if repo_id not in [d[0] for d in hf_datasets]:
                hf_datasets.append((repo_id, "dataset"))
    except ImportError:
        print("  Note: huggingface_hub not installed, using known repos only")
    except Exception as e:
        print(f"  HF API error (using known repos): {e}")

    for repo_id, repo_type in hf_models + hf_datasets:
        name = repo_id.split("/")[-1]
        title = f"HF {repo_type.title()} - {name}"

        body = f"# {title}\n\n"
        body += f"**Repository**: [{repo_id}](https://huggingface.co/{repo_id})\n"
        body += f"**Type**: {repo_type}\n"
        body += f"**Author**: issdandavis\n\n"

        # Try to fetch model card / dataset card
        try:
            from huggingface_hub import HfApi

            api = HfApi()
            if repo_type == "model":
                info = api.model_info(repo_id)
                if hasattr(info, "card_data") and info.card_data:
                    body += f"## Model Card\n\n"
                    if hasattr(info.card_data, "tags") and info.card_data.tags:
                        body += f"**Tags**: {', '.join(info.card_data.tags)}\n\n"
            else:
                info = api.dataset_info(repo_id)
                if hasattr(info, "card_data") and info.card_data:
                    body += f"## Dataset Card\n\n"
                    if hasattr(info.card_data, "tags") and info.card_data.tags:
                        body += f"**Tags**: {', '.join(info.card_data.tags)}\n\n"

            if hasattr(info, "last_modified") and info.last_modified:
                body += f"**Last Modified**: {info.last_modified}\n"
            if hasattr(info, "downloads") and info.downloads:
                body += f"**Downloads**: {info.downloads}\n"
        except Exception:
            body += "*Could not fetch full metadata. Install huggingface_hub for details.*\n"

        tags = ["huggingface", repo_type, "inflow"]
        links = find_wiki_links(body, KNOWN_ENTITIES)

        notes.append(
            InflowNote(
                title=title,
                folder="Products",
                body=body,
                note_type=repo_type,
                source="huggingface",
                tags=tags,
                links=links,
            )
        )

    print(f"  HuggingFace: {len(notes)} notes ({len(hf_models)} models, {len(hf_datasets)} datasets)")
    return notes


# ---------------------------------------------------------------------------
# Source: Training Data JSONL
# ---------------------------------------------------------------------------
def inflow_training() -> List[InflowNote]:
    """Extract unique concepts from training JSONL files into Concept notes."""
    notes: List[InflowNote] = []
    seen_concepts: Set[str] = set()

    if not TRAINING_DATA_DIR.exists():
        print("  SKIP: training-data/ not found")
        return notes

    jsonl_files = list(TRAINING_DATA_DIR.rglob("*.jsonl"))
    print(f"  Scanning {len(jsonl_files)} JSONL files...")

    # Extract category/topic concepts from instruction fields
    concept_sources: Dict[str, List[str]] = defaultdict(list)

    for jsonl_file in jsonl_files:
        try:
            content = jsonl_file.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        rel_path = str(jsonl_file.relative_to(ROOT))

        for line in content.strip().split("\n")[:200]:  # Cap per file
            try:
                record = json.loads(line)
            except (json.JSONDecodeError, ValueError):
                continue

            # Look for category, topic, or concept fields
            category = record.get("category", "")
            tongue = record.get("tongue", "")
            instruction = record.get("instruction", "")

            if category and len(category) > 3:
                key = sanitize_title(category)
                if key and key not in seen_concepts:
                    seen_concepts.add(key)
                    concept_sources[key].append(rel_path)

            # Extract concept from instruction
            if instruction:
                # Look for quoted terms
                quoted = re.findall(r"'([^']{4,40})'", instruction)
                for q in quoted:
                    q_clean = sanitize_title(q)
                    if q_clean and q_clean not in seen_concepts and len(q_clean) > 4:
                        seen_concepts.add(q_clean)
                        concept_sources[q_clean].append(rel_path)

    # Create concept notes (limit to most interesting ones)
    priority_concepts = sorted(
        concept_sources.items(), key=lambda x: len(x[1]), reverse=True
    )[:80]

    for concept, sources in priority_concepts:
        title = f"Concept - {concept}"
        body = f"# {concept}\n\n"
        body += f"Extracted from {len(sources)} training data file(s).\n\n"
        body += "## Sources\n\n"
        for s in sorted(set(sources))[:10]:
            body += f"- `{s}`\n"

        links = find_wiki_links(concept, KNOWN_ENTITIES)

        notes.append(
            InflowNote(
                title=title,
                folder="Ideas",
                body=body,
                note_type="concept",
                source="training",
                tags=["training-data", "concept", "inflow"],
                links=links,
            )
        )

    print(f"  Training: {len(notes)} concept notes from {len(seen_concepts)} unique concepts")
    return notes


# ---------------------------------------------------------------------------
# Source: Lore Bible
# ---------------------------------------------------------------------------
def inflow_lore_bible() -> List[InflowNote]:
    """Split the lore bible into individual notes per character, location, faction."""
    notes: List[InflowNote] = []

    if not LORE_BIBLE.exists():
        print(f"  SKIP: {LORE_BIBLE} not found")
        return notes

    content = LORE_BIBLE.read_text(encoding="utf-8", errors="replace")
    lines = content.split("\n")

    # Phase 1: Extract all named characters (### headers in PART 2, PART 3, PART 4, PART 5)
    current_section = ""
    current_h3 = ""
    current_body_lines: List[str] = []
    all_character_names: Set[str] = set()

    for line in lines:
        if line.startswith("## PART"):
            # Save previous entry
            if current_h3 and current_body_lines:
                _save_lore_entry(
                    notes, current_section, current_h3, current_body_lines
                )
            current_section = line.strip("# ").strip()
            current_h3 = ""
            current_body_lines = []
            continue

        if line.startswith("### "):
            # Save previous entry
            if current_h3 and current_body_lines:
                _save_lore_entry(
                    notes, current_section, current_h3, current_body_lines
                )
            current_h3 = line.strip("# ").strip()
            current_body_lines = []
            continue

        if line.startswith("**") and " -- " in line:
            # Character entry like **Marcus Chen** -- description
            if current_h3 and current_body_lines:
                # Don't save the h3 section, save individual entries
                pass

            char_match = re.match(r"\*\*(.+?)\*\*\s*--\s*(.*)", line)
            if char_match:
                char_name = char_match.group(1).strip()
                char_desc = char_match.group(2).strip()
                all_character_names.add(char_name)

                # Collect the full character description (may span multiple lines)
                char_body_lines = [line]
                continue

        current_body_lines.append(line)

    # Save last entry
    if current_h3 and current_body_lines:
        _save_lore_entry(notes, current_section, current_h3, current_body_lines)

    # Phase 2: Parse character entries more carefully
    # Re-parse focusing on bold-name entries
    char_notes = _extract_character_entries(content)
    notes.extend(char_notes)

    # Phase 3: Extract location entries from PART 6
    location_notes = _extract_location_entries(content)
    notes.extend(location_notes)

    # Phase 4: Extract magic system entries from PART 7
    magic_notes = _extract_magic_entries(content)
    notes.extend(magic_notes)

    # Update global known entities
    for note in notes:
        # Extract the core name from the title
        name = note.title.replace("(Lore)", "").strip()
        if len(name) > 3:
            KNOWN_ENTITIES.add(name)

    # Now add wiki-links
    for note in notes:
        note.links = find_wiki_links(note.body, KNOWN_ENTITIES)

    print(f"  Lore Bible: {len(notes)} notes extracted")
    return notes


def _save_lore_entry(
    notes: List[InflowNote],
    section: str,
    heading: str,
    body_lines: List[str],
) -> None:
    """Save a lore section as a note."""
    body = "\n".join(body_lines).strip()
    if not body or len(body) < 50:
        return

    title = sanitize_title(heading)
    if not title:
        return

    # Determine type and folder from section
    section_lower = section.lower()
    if "character" in section_lower or "thorne" in section_lower or "polly" in section_lower or "kael" in section_lower:
        note_type = "character"
        folder = "People"
    elif "geography" in section_lower or "world" in section_lower:
        note_type = "location"
        folder = "Architecture"
    elif "magic" in section_lower:
        note_type = "theory"
        folder = "Theories"
    elif "timeline" in section_lower:
        note_type = "writing"
        folder = "Writing"
    elif "ame" in section_lower:
        note_type = "character"
        folder = "People"
    else:
        note_type = "reference"
        folder = "References"

    notes.append(
        InflowNote(
            title=f"{title} (Lore)",
            folder=folder,
            body=f"# {title}\n\nSource: Lore Bible ({section})\n\n{body[:4000]}",
            note_type=note_type,
            source="lore-bible",
            tags=["lore-bible", note_type, "inflow"],
        )
    )


def _extract_character_entries(content: str) -> List[InflowNote]:
    """Extract individual character entries from bold-dash patterns."""
    notes: List[InflowNote] = []
    seen: Set[str] = set()

    # Match patterns like **Name** -- description (possibly multi-line until next ** or ###)
    pattern = re.compile(
        r"\*\*(.+?)\*\*\s*--\s*(.*?)(?=\n\*\*|\n###|\n## |\Z)",
        re.DOTALL,
    )

    for match in pattern.finditer(content):
        name = match.group(1).strip()
        desc = match.group(2).strip()

        if name in seen or len(name) < 2 or len(desc) < 20:
            continue
        seen.add(name)
        KNOWN_ENTITIES.add(name)

        # Clean up the name for title
        title = sanitize_title(name)
        if not title:
            continue

        body = f"# {title}\n\nSource: Lore Bible\n\n{desc[:3000]}"

        notes.append(
            InflowNote(
                title=title,
                folder="People",
                body=body,
                note_type="character",
                source="lore-bible",
                tags=["lore-bible", "character", "inflow"],
            )
        )

    return notes


def _extract_location_entries(content: str) -> List[InflowNote]:
    """Extract location entries from PART 6."""
    notes: List[InflowNote] = []

    # Find PART 6 section
    part6_match = re.search(
        r"## PART 6: WORLD GEOGRAPHY\s*\n(.*?)(?=\n## PART|\Z)", content, re.DOTALL
    )
    if not part6_match:
        return notes

    part6 = part6_match.group(1)

    # Extract bold entries
    pattern = re.compile(
        r"\*\*(.+?)\*\*\s*[-:–]\s*(.*?)(?=\n\*\*|\n###|\n## |\Z)",
        re.DOTALL,
    )

    seen: Set[str] = set()
    for match in pattern.finditer(part6):
        name = match.group(1).strip()
        desc = match.group(2).strip()

        if name in seen or len(name) < 3 or len(desc) < 20:
            continue
        seen.add(name)
        KNOWN_ENTITIES.add(name)

        title = sanitize_title(name)
        if not title:
            continue

        body = f"# {title}\n\nSource: Lore Bible (World Geography)\n\n{desc[:3000]}"
        links = find_wiki_links(desc, KNOWN_ENTITIES)

        notes.append(
            InflowNote(
                title=title,
                folder="Architecture",
                body=body,
                note_type="location",
                source="lore-bible",
                tags=["lore-bible", "location", "geography", "inflow"],
                links=links,
            )
        )

    return notes


def _extract_magic_entries(content: str) -> List[InflowNote]:
    """Extract magic system entries from PART 7."""
    notes: List[InflowNote] = []

    part7_match = re.search(
        r"## PART 7: MAGIC SYSTEM\s*\n(.*?)(?=\n## PART|\Z)", content, re.DOTALL
    )
    if not part7_match:
        return notes

    part7 = part7_match.group(1)

    # Extract h3 sections
    sections = re.split(r"\n### ", part7)
    for section in sections[1:]:  # Skip pre-header content
        lines = section.split("\n", 1)
        heading = lines[0].strip()
        body_text = lines[1].strip() if len(lines) > 1 else ""

        if not heading or len(body_text) < 50:
            continue

        title = sanitize_title(heading)
        links = find_wiki_links(body_text, KNOWN_ENTITIES)

        notes.append(
            InflowNote(
                title=f"{title} (Magic System)",
                folder="Theories",
                body=f"# {title}\n\nSource: Lore Bible (Magic System)\n\n{body_text[:3000]}",
                note_type="theory",
                source="lore-bible",
                tags=["lore-bible", "magic", "theory", "inflow"],
                links=links,
            )
        )

    return notes


# ---------------------------------------------------------------------------
# Source: ChatGPT Exports
# ---------------------------------------------------------------------------
def inflow_chatgpt() -> List[InflowNote]:
    """Extract conversation summaries from ChatGPT export zip."""
    notes: List[InflowNote] = []

    if not CHATGPT_ZIP.exists():
        print(f"  SKIP: {CHATGPT_ZIP} not found")
        return notes

    try:
        with zipfile.ZipFile(str(CHATGPT_ZIP), "r") as zf:
            # Look for conversations.json inside the zip
            json_files = [
                n for n in zf.namelist() if n.endswith("conversations.json")
            ]
            if not json_files:
                print("  SKIP: No conversations.json in zip")
                return notes

            with zf.open(json_files[0]) as f:
                conversations = json.loads(f.read().decode("utf-8", errors="replace"))
    except Exception as e:
        print(f"  SKIP: Could not read ChatGPT export: {e}")
        return notes

    print(f"  Found {len(conversations)} ChatGPT conversations")

    # Filter for relevant conversations (SCBE, Avalon, Spiralverse, lore, etc.)
    keywords = [
        "scbe",
        "avalon",
        "spiralverse",
        "aethermoore",
        "izack",
        "polly",
        "sacred tongue",
        "six tongue",
        "geoseed",
        "governance",
        "hyperbolic",
        "poincare",
        "security",
        "training",
        "ai safety",
        "kael",
        "senna",
        "marcus",
    ]

    for conv in conversations:
        title_raw = conv.get("title", "Untitled")
        create_time = conv.get("create_time")

        if create_time:
            date_str = datetime.datetime.fromtimestamp(
                create_time, tz=datetime.timezone.utc
            ).strftime("%Y-%m-%d")
        else:
            date_str = TODAY

        # Check if this conversation is relevant
        title_lower = title_raw.lower()
        mapping = conv.get("mapping", {})

        # Build a preview of the conversation
        messages: List[str] = []
        for _node_id, node in mapping.items():
            msg = node.get("message")
            if not msg:
                continue
            content_obj = msg.get("content", {})
            parts = content_obj.get("parts", [])
            role = msg.get("author", {}).get("role", "")

            for part in parts:
                if isinstance(part, str) and len(part) > 20:
                    messages.append(f"**{role}**: {part[:300]}")

        full_text = " ".join(messages).lower()

        # Check relevance
        is_relevant = any(kw in title_lower or kw in full_text[:2000] for kw in keywords)
        if not is_relevant:
            continue

        title = sanitize_title(title_raw)
        if not title:
            continue

        body = f"# Research Session: {title}\n\n"
        body += f"**Date**: {date_str}\n"
        body += f"**Source**: ChatGPT Export\n"
        body += f"**Messages**: {len(messages)}\n\n"
        body += "## Conversation Preview\n\n"
        body += "\n\n".join(messages[:20])  # First 20 message snippets

        links = find_wiki_links(full_text[:3000], KNOWN_ENTITIES)

        tags = ["chatgpt", "research-session", "inflow"]
        # Auto-tag by topic
        if "lore" in full_text[:1000] or "character" in full_text[:1000]:
            tags.append("lore")
        if "code" in full_text[:1000] or "python" in full_text[:1000]:
            tags.append("code")
        if "security" in full_text[:1000] or "governance" in full_text[:1000]:
            tags.append("security")

        notes.append(
            InflowNote(
                title=f"Research Session - {title}",
                folder="Research Results",
                body=body[:5000],
                note_type="research",
                source="chatgpt",
                tags=tags,
                links=links,
                date=date_str,
            )
        )

    print(f"  ChatGPT: {len(notes)} relevant research session notes")
    return notes


# ---------------------------------------------------------------------------
# Main Orchestrator
# ---------------------------------------------------------------------------
SOURCE_HANDLERS = {
    "gitlab": inflow_gitlab,
    "github": inflow_github,
    "huggingface": inflow_huggingface,
    "training": inflow_training,
    "lore-bible": inflow_lore_bible,
    "chatgpt": inflow_chatgpt,
}


def run_inflow(sources: List[str], dry_run: bool = False) -> Dict[str, Any]:
    """Run the inflow pipeline for the specified sources."""
    report: Dict[str, Any] = {
        "timestamp": NOW.isoformat(),
        "vault_path": str(VAULT_PATH),
        "dry_run": dry_run,
        "sources": {},
        "totals": {"created": 0, "skipped": 0, "errors": 0},
    }

    # Pre-seed known entities from lore bible (even if not processing it)
    if LORE_BIBLE.exists():
        try:
            lore_text = LORE_BIBLE.read_text(encoding="utf-8", errors="replace")
            # Extract bold names
            for m in re.finditer(r"\*\*(.+?)\*\*", lore_text):
                name = m.group(1).strip()
                if 3 < len(name) < 60 and not name.startswith("http"):
                    KNOWN_ENTITIES.add(name)
        except Exception:
            pass

    all_notes: List[InflowNote] = []

    for source in sources:
        handler = SOURCE_HANDLERS.get(source)
        if not handler:
            print(f"  Unknown source: {source}")
            continue

        print(f"\n--- Source: {source} ---")
        try:
            source_notes = handler()
            all_notes.extend(source_notes)
            report["sources"][source] = {
                "notes_generated": len(source_notes),
                "status": "ok",
            }
        except Exception as e:
            print(f"  ERROR in {source}: {e}")
            report["sources"][source] = {
                "notes_generated": 0,
                "status": f"error: {e}",
            }
            report["totals"]["errors"] += 1

    # Write notes to vault
    print(f"\n--- Writing {len(all_notes)} notes to vault ---")
    created = 0
    skipped = 0

    for note in all_notes:
        was_created, path = write_note(note, dry_run=dry_run)
        if was_created:
            created += 1
            action = "WOULD CREATE" if dry_run else "CREATED"
            print(f"  {action}: {note.folder}/{note.filename()}")
        else:
            skipped += 1

    report["totals"]["created"] = created
    report["totals"]["skipped"] = skipped
    report["totals"]["total_notes"] = len(all_notes)

    # Save report
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Obsidian Inflow — push knowledge INTO the Obsidian vault"
    )
    parser.add_argument(
        "--source",
        choices=list(SOURCE_HANDLERS.keys()) + ["all"],
        default="all",
        help="Which source to pull from (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be created without writing files",
    )
    parser.add_argument(
        "--vault",
        type=str,
        default=None,
        help="Override vault path",
    )

    args = parser.parse_args()

    global VAULT_PATH
    if args.vault:
        VAULT_PATH = Path(args.vault)

    print(f"OBSIDIAN INFLOW")
    print(f"  Vault: {VAULT_PATH}")
    print(f"  Dry run: {args.dry_run}")

    if not VAULT_PATH.exists():
        print(f"  ERROR: Vault path does not exist: {VAULT_PATH}")
        print(f"  Set OBSIDIAN_VAULT env var or use --vault flag")
        sys.exit(1)

    if args.source == "all":
        sources = list(SOURCE_HANDLERS.keys())
    else:
        sources = [args.source]

    report = run_inflow(sources, dry_run=args.dry_run)

    print(f"\n=== INFLOW SUMMARY ===")
    print(f"  Total notes:  {report['totals']['total_notes']}")
    print(f"  Created:      {report['totals']['created']}")
    print(f"  Skipped:      {report['totals']['skipped']} (already exist)")
    print(f"  Errors:       {report['totals']['errors']}")
    print(f"  Report:       {REPORT_PATH}")


if __name__ == "__main__":
    main()
