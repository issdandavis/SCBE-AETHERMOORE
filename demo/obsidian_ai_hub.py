"""Obsidian AI Workspace Hub -- Shared coordination for multi-AI workflows.

A shared coordination system where all AIs (Claude, Gemini, Codex, Copilot)
can read/write tasks and share context through the user's Obsidian vault.

Usage:
    python obsidian_ai_hub.py post --title "Task name" --context "Details" --posted-by claude
    python obsidian_ai_hub.py inbox
    python obsidian_ai_hub.py active
    python obsidian_ai_hub.py claim --task-id <id> --agent <name>
    python obsidian_ai_hub.py complete --task-id <id> --result "What was done"
    python obsidian_ai_hub.py context [--key <key> --value <value>]
    python obsidian_ai_hub.py status --agent <name> [--set-status <status>] [--working-on <task>]
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


DEFAULT_VAULT = Path(r"C:\Users\issda\OneDrive\Dropbox\Izack Realmforge")


class ObsidianAIHub:
    """Shared coordination hub backed by Obsidian markdown files."""

    def __init__(self, vault_path: Path) -> None:
        self.workspace = vault_path / "AI Workspace"
        self.workspace.mkdir(parents=True, exist_ok=True)
        (self.workspace / "agents").mkdir(parents=True, exist_ok=True)

        # Ensure core files exist
        for fname, header in [
            ("_inbox.md", "# AI Workspace -- Inbox\n\nTasks posted here by any AI agent. Claim by moving to active tasks.\n\n---\n"),
            ("_active_tasks.md", "# AI Workspace -- Active Tasks\n\nTasks currently being worked on by AI agents.\n\n---\n"),
            ("_completed.md", "# AI Workspace -- Completed\n\nArchive of completed tasks.\n\n---\n"),
        ]:
            p = self.workspace / fname
            if not p.exists():
                p.write_text(header, encoding="utf-8")

        ctx = self.workspace / "_context.md"
        if not ctx.exists():
            ctx.write_text(
                "# Shared Context\n\n## Current Focus\n\n\n## Recent Decisions\n\n\n## Key Paths\n\n\n## Blocking Issues\n\n",
                encoding="utf-8",
            )

    # ------------------------------------------------------------------
    # Task lifecycle
    # ------------------------------------------------------------------

    def post_task(
        self,
        title: str,
        context: str,
        priority: str = "medium",
        posted_by: str = "claude",
        suggested_agent: str = "any",
    ) -> str:
        """Append a new task to _inbox.md and return its task ID."""
        task_id = f"task-{int(time.time() * 1000)}"
        now = datetime.now(timezone.utc).isoformat()

        block = (
            f"\n## Task: {title}\n"
            f"- **ID**: {task_id}\n"
            f"- **Posted by**: {posted_by}\n"
            f"- **Priority**: {priority}\n"
            f"- **Suggested agent**: {suggested_agent}\n"
            f"- **Posted at**: {now}\n"
            f"- **Context**: {context}\n\n"
        )

        inbox = self.workspace / "_inbox.md"
        with inbox.open("a", encoding="utf-8") as f:
            f.write(block)

        return task_id

    def claim_task(self, task_id: str, agent_name: str) -> bool:
        """Move a task from _inbox.md to _active_tasks.md, tagging the claiming agent."""
        inbox = self.workspace / "_inbox.md"
        text = inbox.read_text(encoding="utf-8")

        # Find the task block by ID
        task_block, remaining = self._extract_task_block(text, task_id)
        if task_block is None:
            return False

        # Write back inbox without the claimed task
        inbox.write_text(remaining, encoding="utf-8")

        # Add claim metadata
        now = datetime.now(timezone.utc).isoformat()
        task_block += f"- **Claimed by**: {agent_name}\n- **Claimed at**: {now}\n\n"

        active = self.workspace / "_active_tasks.md"
        with active.open("a", encoding="utf-8") as f:
            f.write(task_block)

        return True

    def complete_task(self, task_id: str, result: str) -> bool:
        """Move a task from _active_tasks.md to _completed.md with the result."""
        active = self.workspace / "_active_tasks.md"
        text = active.read_text(encoding="utf-8")

        task_block, remaining = self._extract_task_block(text, task_id)
        if task_block is None:
            return False

        active.write_text(remaining, encoding="utf-8")

        now = datetime.now(timezone.utc).isoformat()
        task_block += f"- **Completed at**: {now}\n- **Result**: {result}\n\n"

        completed = self.workspace / "_completed.md"
        with completed.open("a", encoding="utf-8") as f:
            f.write(task_block)

        return True

    # ------------------------------------------------------------------
    # Shared context
    # ------------------------------------------------------------------

    def update_context(self, key: str, value: str) -> None:
        """Update or add a key-value section in _context.md."""
        ctx_path = self.workspace / "_context.md"
        text = ctx_path.read_text(encoding="utf-8")

        section_header = f"## {key}"
        pattern = re.compile(
            rf"(## {re.escape(key)}\n)(.*?)(?=\n## |\Z)",
            re.DOTALL,
        )
        match = pattern.search(text)
        if match:
            text = text[: match.start()] + f"{section_header}\n{value}\n" + text[match.end():]
        else:
            text = text.rstrip() + f"\n\n{section_header}\n{value}\n"

        ctx_path.write_text(text, encoding="utf-8")

    def read_context(self) -> Dict[str, str]:
        """Parse _context.md into a dict of section-name -> content."""
        ctx_path = self.workspace / "_context.md"
        if not ctx_path.exists():
            return {}

        text = ctx_path.read_text(encoding="utf-8")
        result: Dict[str, str] = {}
        sections = re.split(r"\n## ", text)
        for section in sections[1:]:  # skip preamble
            lines = section.split("\n", 1)
            heading = lines[0].strip()
            body = lines[1].strip() if len(lines) > 1 else ""
            result[heading] = body
        return result

    # ------------------------------------------------------------------
    # Agent status
    # ------------------------------------------------------------------

    def update_agent_status(self, agent_name: str, status_dict: Dict[str, str]) -> None:
        """Write / update agents/{agent_name}.md with the supplied status fields."""
        agent_file = self.workspace / "agents" / f"{agent_name}.md"

        # Merge with existing data if available
        existing = self.get_agent_status(agent_name)
        existing.update(status_dict)

        # Always update last-active timestamp
        existing.setdefault("Last active", datetime.now(timezone.utc).isoformat())
        if "Last active" not in status_dict:
            existing["Last active"] = datetime.now(timezone.utc).isoformat()

        lines = [f"# Agent: {agent_name}\n"]
        for k, v in existing.items():
            lines.append(f"- **{k}**: {v}")
        lines.append("")

        agent_file.write_text("\n".join(lines), encoding="utf-8")

    def get_agent_status(self, agent_name: str) -> Dict[str, str]:
        """Read and parse agents/{agent_name}.md into a dict."""
        agent_file = self.workspace / "agents" / f"{agent_name}.md"
        if not agent_file.exists():
            return {}

        text = agent_file.read_text(encoding="utf-8")
        result: Dict[str, str] = {}
        for m in re.finditer(r"- \*\*(.+?)\*\*:\s*(.+)", text):
            result[m.group(1)] = m.group(2).strip()
        return result

    # ------------------------------------------------------------------
    # Query helpers
    # ------------------------------------------------------------------

    def get_inbox(self) -> List[Dict[str, str]]:
        """Parse _inbox.md and return a list of task dicts."""
        return self._parse_tasks(self.workspace / "_inbox.md")

    def get_active_tasks(self) -> List[Dict[str, str]]:
        """Parse _active_tasks.md and return a list of task dicts."""
        return self._parse_tasks(self.workspace / "_active_tasks.md")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_tasks(path: Path) -> List[Dict[str, str]]:
        """Parse a task markdown file into a list of dicts."""
        if not path.exists():
            return []
        text = path.read_text(encoding="utf-8")
        tasks: List[Dict[str, str]] = []
        blocks = re.split(r"\n## Task: ", text)
        for block in blocks[1:]:
            lines = block.strip().split("\n")
            task: Dict[str, str] = {"title": lines[0].strip()}
            for line in lines[1:]:
                m = re.match(r"- \*\*(.+?)\*\*:\s*(.+)", line)
                if m:
                    task[m.group(1)] = m.group(2).strip()
            tasks.append(task)
        return tasks

    @staticmethod
    def _extract_task_block(text: str, task_id: str) -> tuple[Optional[str], str]:
        """Extract a task block by ID from markdown text.

        Returns (task_block_str, remaining_text).  If not found returns (None, original_text).
        """
        # Split on task headers while keeping them
        parts = re.split(r"(\n## Task: )", text)
        # parts alternates: [preamble, sep, block, sep, block, ...]

        found_idx: Optional[int] = None
        task_block: Optional[str] = None

        i = 1
        while i < len(parts):
            sep = parts[i]
            block = parts[i + 1] if i + 1 < len(parts) else ""
            if task_id in block:
                found_idx = i
                task_block = sep + block
                break
            i += 2

        if found_idx is None:
            return None, text

        remaining_parts = parts[:found_idx] + parts[found_idx + 2:]
        remaining = "".join(remaining_parts)
        return task_block, remaining


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def _print_tasks(tasks: List[Dict[str, str]], label: str) -> None:
    if not tasks:
        print(f"No {label} tasks.")
        return
    for t in tasks:
        priority = t.get("Priority", "?")
        agent = t.get("Suggested agent", t.get("Claimed by", "?"))
        posted = t.get("Posted by", "?")
        print(f"  [{priority.upper()}] {t.get('title', '?')}  (ID: {t.get('ID', '?')}, by: {posted}, agent: {agent})")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Obsidian AI Workspace Hub -- multi-AI task coordination",
    )
    parser.add_argument(
        "--vault",
        type=Path,
        default=DEFAULT_VAULT,
        help="Path to Obsidian vault root",
    )
    sub = parser.add_subparsers(dest="command")

    # post
    p_post = sub.add_parser("post", help="Post a new task to the inbox")
    p_post.add_argument("--title", required=True)
    p_post.add_argument("--context", required=True)
    p_post.add_argument("--priority", default="medium", choices=["low", "medium", "high", "critical"])
    p_post.add_argument("--posted-by", default="claude")
    p_post.add_argument("--suggested-agent", default="any")

    # inbox
    sub.add_parser("inbox", help="List inbox tasks")

    # active
    sub.add_parser("active", help="List active tasks")

    # claim
    p_claim = sub.add_parser("claim", help="Claim a task from the inbox")
    p_claim.add_argument("--task-id", required=True)
    p_claim.add_argument("--agent", required=True)

    # complete
    p_complete = sub.add_parser("complete", help="Mark an active task as completed")
    p_complete.add_argument("--task-id", required=True)
    p_complete.add_argument("--result", required=True)

    # context
    p_ctx = sub.add_parser("context", help="Read or update shared context")
    p_ctx.add_argument("--key", default=None)
    p_ctx.add_argument("--value", default=None)

    # status
    p_status = sub.add_parser("status", help="Read or update agent status")
    p_status.add_argument("--agent", required=True)
    p_status.add_argument("--set-status", default=None)
    p_status.add_argument("--working-on", default=None)

    args = parser.parse_args()
    hub = ObsidianAIHub(args.vault)

    if args.command == "post":
        tid = hub.post_task(
            title=args.title,
            context=args.context,
            priority=args.priority,
            posted_by=args.posted_by,
            suggested_agent=args.suggested_agent,
        )
        print(f"Posted task: {tid}")

    elif args.command == "inbox":
        _print_tasks(hub.get_inbox(), "inbox")

    elif args.command == "active":
        _print_tasks(hub.get_active_tasks(), "active")

    elif args.command == "claim":
        ok = hub.claim_task(args.task_id, args.agent)
        print(f"Claimed: {ok}")

    elif args.command == "complete":
        ok = hub.complete_task(args.task_id, args.result)
        print(f"Completed: {ok}")

    elif args.command == "context":
        if args.key and args.value:
            hub.update_context(args.key, args.value)
            print(f"Updated context: {args.key}")
        else:
            ctx = hub.read_context()
            if not ctx:
                print("No shared context yet.")
            else:
                for k, v in ctx.items():
                    print(f"## {k}\n{v}\n")

    elif args.command == "status":
        if args.set_status or args.working_on:
            updates: Dict[str, str] = {}
            if args.set_status:
                updates["Status"] = args.set_status
            if args.working_on:
                updates["Working on"] = args.working_on
            hub.update_agent_status(args.agent, updates)
            print(f"Updated status for {args.agent}")
        else:
            st = hub.get_agent_status(args.agent)
            if not st:
                print(f"No status found for agent: {args.agent}")
            else:
                for k, v in st.items():
                    print(f"  {k}: {v}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
