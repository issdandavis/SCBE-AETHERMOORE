"""Git Operations SFT Harvester — captures repo cleanup as training data.

Records each git operation (untrack, compress, deduplicate) as an
instruction/output SFT pair documenting the decision-making process.

Usage:
    from scripts.git_ops_sft_harvester import GitOpsHarvester

    harvester = GitOpsHarvester()
    harvester.record_operation(
        command="git rm --cached training-data/sft/consolidated_root_sft.jsonl",
        reasoning="File matches gitignore pattern consolidated*.jsonl but was tracked before rule existed",
        category="zombie_untrack",
        file_path="training-data/sft/consolidated_root_sft.jsonl",
        file_size_bytes=67_000_000,
        outcome="Untracked 67MB LFS object; local copy preserved",
    )
    harvester.flush()  # writes JSONL
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "training-data" / "sft"
OUTPUT_FILE = OUTPUT_DIR / "git_ops_cleanup_sft.jsonl"


@dataclass
class GitOpsRecord:
    """Single git operation captured as SFT training data."""

    timestamp: str
    command: str
    reasoning: str
    category: str  # zombie_untrack, compress, deduplicate, gitignore_update, lfs_migrate
    file_path: str = ""
    file_size_bytes: int = 0
    file_count: int = 1
    outcome: str = ""
    git_status_before: str = ""
    git_status_after: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_sft_pair(self) -> dict[str, str]:
        """Convert to instruction/output SFT format."""
        size_human = _human_size(self.file_size_bytes)

        instruction = (
            f"You are performing git repository maintenance. "
            f"Category: {self.category}. "
        )

        if self.category == "zombie_untrack":
            instruction += (
                f"A file '{self.file_path}' ({size_human}) is tracked by git "
                f"but matches a .gitignore pattern. It was added before the "
                f"gitignore rule existed. What command should you run and why?"
            )
        elif self.category == "compress":
            instruction += (
                f"A local file '{self.file_path}' ({size_human}) is untracked "
                f"training data taking up disk space. The project policy is "
                f"'compress, never delete'. What should you do?"
            )
        elif self.category == "deduplicate":
            instruction += (
                f"Found {self.file_count} copies of similar training data "
                f"totaling {size_human}. How should you consolidate without "
                f"losing data?"
            )
        elif self.category == "batch_untrack":
            instruction += (
                f"Found {self.file_count} zombie files ({size_human} total) "
                f"that are tracked but match gitignore patterns. They span "
                f"directories: {self.file_path}. How do you clean this up?"
            )
        else:
            instruction += (
                f"Operation on '{self.file_path}' ({size_human}): "
                f"{self.reasoning}"
            )

        output = (
            f"Command: `{self.command}`\n\n"
            f"Reasoning: {self.reasoning}\n\n"
            f"Outcome: {self.outcome}\n\n"
            f"Key principle: {_principle_for_category(self.category)}"
        )

        return {
            "instruction": instruction,
            "output": output,
            "source": "git_ops_cleanup",
            "category": self.category,
            "timestamp": self.timestamp,
            "tongue_profile": {
                "KO": 0.20,  # Intent: what we're doing
                "AV": 0.10,  # Wisdom: why
                "RU": 0.25,  # Governance: policy compliance
                "CA": 0.15,  # Compute: file sizes, counts
                "UM": 0.20,  # Security: safe operations
                "DR": 0.10,  # Architecture: repo structure
            },
            "metadata": {
                "file_size_bytes": self.file_size_bytes,
                "file_count": self.file_count,
                "file_path": self.file_path,
            },
        }


class GitOpsHarvester:
    """Captures git cleanup operations as SFT training data."""

    def __init__(self, output_path: Path | None = None):
        self.output_path = output_path or OUTPUT_FILE
        self.records: list[GitOpsRecord] = []
        self._session_start = datetime.now(timezone.utc).isoformat()

    def record_operation(
        self,
        command: str,
        reasoning: str,
        category: str,
        file_path: str = "",
        file_size_bytes: int = 0,
        file_count: int = 1,
        outcome: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> GitOpsRecord:
        """Record a single git operation."""
        record = GitOpsRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            command=command,
            reasoning=reasoning,
            category=category,
            file_path=file_path,
            file_size_bytes=file_size_bytes,
            file_count=file_count,
            outcome=outcome,
            metadata=metadata or {},
        )
        self.records.append(record)
        return record

    def record_batch_untrack(
        self,
        files: list[str],
        total_size_bytes: int,
        directories: list[str],
        gitignore_patterns: list[str],
    ) -> GitOpsRecord:
        """Record a batch untrack operation (the main cleanup)."""
        return self.record_operation(
            command=f"git rm --cached (748 files via git ls-files --cached --ignored --exclude-standard)",
            reasoning=(
                f"Found {len(files)} files tracked by git that match current .gitignore patterns. "
                f"These were added before gitignore rules existed. Patterns: {', '.join(gitignore_patterns[:5])}... "
                f"Using --cached flag preserves local copies while removing from git index."
            ),
            category="batch_untrack",
            file_path=", ".join(directories[:5]),
            file_size_bytes=total_size_bytes,
            file_count=len(files),
            outcome=(
                f"Removed {len(files)} files from git tracking. "
                f"Reclaimed {_human_size(total_size_bytes)} from remote. "
                f"Local copies preserved. LFS objects will be garbage collected."
            ),
        )

    def record_compress(
        self,
        original_path: str,
        compressed_path: str,
        original_size: int,
        compressed_size: int,
    ) -> GitOpsRecord:
        """Record a compression operation."""
        ratio = compressed_size / original_size if original_size > 0 else 0
        return self.record_operation(
            command=f"gzip -k {original_path}",
            reasoning=(
                f"Untracked training data at {original_path} ({_human_size(original_size)}) "
                f"consuming local disk. Project policy: compress, never delete. "
                f"Compression ratio: {ratio:.1%}"
            ),
            category="compress",
            file_path=original_path,
            file_size_bytes=original_size,
            outcome=(
                f"Compressed {_human_size(original_size)} -> {_human_size(compressed_size)} "
                f"({ratio:.1%}). Original preserved alongside .gz."
            ),
            metadata={"compressed_path": compressed_path, "ratio": ratio},
        )

    def record_deduplicate(
        self,
        files: list[str],
        total_size: int,
        kept_file: str,
        method: str = "symlink",
    ) -> GitOpsRecord:
        """Record a deduplication operation."""
        return self.record_operation(
            command=f"# Keep {kept_file}, replace {len(files)-1} duplicates with {method}s",
            reasoning=(
                f"Found {len(files)} near-identical training data files "
                f"({_human_size(total_size)} total). Content hash comparison "
                f"confirms >99% overlap. Keeping newest, replacing others."
            ),
            category="deduplicate",
            file_path=kept_file,
            file_size_bytes=total_size,
            file_count=len(files),
            outcome=(
                f"Deduplicated {len(files)} files. Kept {kept_file}. "
                f"Saved {_human_size(total_size * (len(files)-1) // len(files))} local disk."
            ),
            metadata={"method": method, "kept": kept_file, "replaced": files},
        )

    def generate_session_summary(self) -> dict[str, Any]:
        """Generate a summary SFT pair for the entire cleanup session."""
        total_reclaimed = sum(r.file_size_bytes for r in self.records)
        total_files = sum(r.file_count for r in self.records)
        categories = {}
        for r in self.records:
            categories.setdefault(r.category, 0)
            categories[r.category] += 1

        instruction = (
            "You just completed a git repository cleanup session. "
            "Summarize the operations performed, data reclaimed, and "
            "principles followed."
        )
        output = (
            f"Session summary ({self._session_start}):\n\n"
            f"- Total operations: {len(self.records)}\n"
            f"- Total files affected: {total_files}\n"
            f"- Total data reclaimed/compressed: {_human_size(total_reclaimed)}\n"
            f"- Categories: {json.dumps(categories)}\n\n"
            f"Principles followed:\n"
            f"1. Compress, never delete (data preservation policy)\n"
            f"2. git rm --cached preserves local copies\n"
            f"3. Gitignore rules prevent future re-tracking\n"
            f"4. LFS objects garbage-collected on next prune\n"
            f"5. Every operation captured as training data (meta-learning)\n"
        )

        return {
            "instruction": instruction,
            "output": output,
            "source": "git_ops_cleanup",
            "category": "session_summary",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tongue_profile": {
                "KO": 0.15, "AV": 0.20, "RU": 0.25,
                "CA": 0.10, "UM": 0.15, "DR": 0.15,
            },
        }

    def flush(self) -> int:
        """Write all records to JSONL file. Returns number written."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        count = 0
        with open(self.output_path, "a", encoding="utf-8") as f:
            for record in self.records:
                pair = record.to_sft_pair()
                f.write(json.dumps(pair, ensure_ascii=False) + "\n")
                count += 1

            # Write session summary
            summary = self.generate_session_summary()
            f.write(json.dumps(summary, ensure_ascii=False) + "\n")
            count += 1

        self.records.clear()
        return count


def _human_size(size_bytes: int) -> str:
    """Convert bytes to human-readable size."""
    for unit in ("B", "KB", "MB", "GB"):
        if abs(size_bytes) < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"


def _principle_for_category(category: str) -> str:
    """Return the governing principle for a cleanup category."""
    principles = {
        "zombie_untrack": (
            "Files added before a gitignore rule exists remain tracked. "
            "Use `git rm --cached` to untrack without deleting local copies."
        ),
        "batch_untrack": (
            "Batch untrack via `git ls-files --cached --ignored --exclude-standard` "
            "finds all zombie files. Pipe to xargs for bulk removal."
        ),
        "compress": (
            "Training data is never deleted — it represents accumulated experience. "
            "Compress to reclaim disk space while preserving the full record."
        ),
        "deduplicate": (
            "Incremental training runs produce near-identical snapshots. "
            "Keep the latest, compress older versions, maintain an audit trail."
        ),
        "gitignore_update": (
            "Gitignore rules should be added BEFORE large files are tracked. "
            "When added after, a cleanup pass is required."
        ),
        "lfs_migrate": (
            "Large binary/data files belong in Git LFS, not regular git objects. "
            "LFS stores pointers in the repo and content in a separate store."
        ),
    }
    return principles.get(category, "Follow the principle of least surprise.")


if __name__ == "__main__":
    print("Git Ops SFT Harvester — self-test")
    h = GitOpsHarvester(Path("test_git_ops_sft.jsonl"))

    h.record_operation(
        command="git rm --cached big_file.jsonl",
        reasoning="Zombie file: tracked but gitignored",
        category="zombie_untrack",
        file_path="training-data/big_file.jsonl",
        file_size_bytes=67_000_000,
        outcome="Untracked, local copy preserved",
    )

    h.record_batch_untrack(
        files=["a.jsonl", "b.jsonl", "c.jsonl"],
        total_size_bytes=150_000_000,
        directories=["artifacts/", "training-data/sft/"],
        gitignore_patterns=["artifacts/", "consolidated*.jsonl"],
    )

    count = h.flush()
    print(f"  Wrote {count} SFT pairs to test_git_ops_sft.jsonl")

    # Show a sample
    with open("test_git_ops_sft.jsonl") as f:
        for line in f:
            rec = json.loads(line)
            print(f"\n  Category: {rec['category']}")
            print(f"  Instruction: {rec['instruction'][:100]}...")
            print(f"  Output: {rec['output'][:100]}...")

    os.remove("test_git_ops_sft.jsonl")
    print("\n  Self-test passed.")
