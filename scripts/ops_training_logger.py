#!/usr/bin/env python3
"""Operations Training Logger — Every action generates training data.

Logs what was done, why, how, the access path, time taken, outcome,
and how it could be done better. Produces SFT training pairs for
an AI that learns to do operations work.

Usage:
    from scripts.ops_training_logger import OpsLogger
    logger = OpsLogger()
    logger.log_action(
        action="fix_security_alert",
        what="Updated lodash to fix Code Injection CVE",
        why="GitHub Dependabot flagged high-severity vulnerability",
        how="npm update lodash",
        access_path="GitHub notifications → Dependabot alerts → npm update",
        time_taken_seconds=15,
        outcome="success",
        could_be_better="Auto-merge dependabot PRs for patch versions"
    )
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = REPO_ROOT / "training-data" / "sft" / "ops_actions_sft.jsonl"


class OpsLogger:
    """Log every operations action as a training pair."""

    def __init__(self, log_file: Path = LOG_FILE):
        self.log_file = log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def log_action(
        self,
        action: str,
        what: str,
        why: str,
        how: str,
        access_path: str = "",
        time_taken_seconds: float = 0,
        optimal_time_seconds: float = 0,
        outcome: str = "success",
        could_be_better: str = "",
        category: str = "operations",
        tongue: str = "DR",
    ) -> dict:
        """Log an action and generate an SFT training pair."""

        timestamp = datetime.now(timezone.utc).isoformat()

        instruction = f"How do you {action.replace('_', ' ')} in SCBE-AETHERMOORE?"

        output_parts = [
            f"Action: {what}",
            f"Why: {why}",
            f"How: {how}",
        ]
        if access_path:
            output_parts.append(f"Access path: {access_path}")
        if time_taken_seconds > 0:
            output_parts.append(f"Time taken: {time_taken_seconds:.0f}s")
        if optimal_time_seconds > 0:
            output_parts.append(f"Optimal time: {optimal_time_seconds:.0f}s")
        output_parts.append(f"Outcome: {outcome}")
        if could_be_better:
            output_parts.append(f"Improvement: {could_be_better}")

        record = {
            "instruction": instruction,
            "output": ". ".join(output_parts),
            "source": "ops_training_logger",
            "tongue": tongue,
            "category": category,
            "timestamp": timestamp,
            "action": action,
            "outcome": outcome,
            "time_taken": time_taken_seconds,
        }

        with open(self.log_file, "a", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(record, ensure_ascii=True) + "\n")

        return record

    def log_security_fix(
        self,
        package: str,
        severity: str,
        fix_command: str,
        time_taken: float = 0,
    ) -> dict:
        return self.log_action(
            action="fix_security_vulnerability",
            what=f"Fixed {severity}-severity vulnerability in {package}",
            why=f"GitHub Dependabot / security scanner flagged {package}",
            how=fix_command,
            access_path="GitHub notifications → Security alerts → terminal fix",
            time_taken_seconds=time_taken,
            category="security",
            tongue="UM",
        )

    def log_cleanup(
        self,
        target: str,
        size_freed: str = "",
        method: str = "",
    ) -> dict:
        return self.log_action(
            action="cleanup_repository",
            what=f"Cleaned {target}" + (f" ({size_freed} freed)" if size_freed else ""),
            why="Repository hygiene and disk management",
            how=method,
            category="maintenance",
            tongue="DR",
        )

    def log_github_action(
        self,
        action_type: str,
        target: str,
        details: str = "",
    ) -> dict:
        return self.log_action(
            action=f"github_{action_type}",
            what=f"{action_type}: {target}",
            why=details or f"GitHub {action_type} operation",
            how=f"gh CLI or GitHub API",
            access_path="GitHub → gh CLI → API",
            category="github_ops",
            tongue="CA",
        )


if __name__ == "__main__":
    logger = OpsLogger()

    # Log tonight's security fixes as examples
    logger.log_security_fix("lodash", "high", "npm update lodash", 5)
    logger.log_security_fix("@xmldom/xmldom", "high", "npm update @xmldom/xmldom", 5)
    logger.log_security_fix("Pygments", "low", "pip install --upgrade Pygments", 10)

    logger.log_cleanup("__pycache__ in demo repo", "14 files", "git rm -r --cached + .gitignore")
    logger.log_cleanup("81 API keys in training data", "81 secrets scrubbed", "python scripts/check_secrets.py + regex replace")
    logger.log_cleanup("25 GB disk space", "25 GB freed", "rm driver backups + push to cloud + clear caches")

    logger.log_github_action("archive", "23 stale repos", "Superseded by SCBE-AETHERMOORE")
    logger.log_github_action("close_pr", "3 stale PRs", "#905, #900, #899 — superseded by main branch work")
    logger.log_github_action("fix_ci", "ci-auto-fix.yml", "Added branches: [main] filter to prevent phantom failures")

    print(f"Logged {sum(1 for _ in open(LOG_FILE))} ops training pairs")
