from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "system-audit"


def run_gh(args: list[str]) -> Any:
    completed = subprocess.run(
        ["gh"] + args,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if completed.returncode != 0:
        # gh pr checks exits non-zero when checks are failing/pending;
        # still try to parse its stdout, fall back to empty list.
        if completed.stdout and completed.stdout.strip():
            try:
                return json.loads(completed.stdout)
            except json.JSONDecodeError:
                pass
        return []
    return json.loads(completed.stdout or "[]")


def classify_pr(pr: dict[str, Any], checks: list[dict[str, Any]]) -> tuple[str, str]:
    label_names = {label["name"] for label in pr.get("labels", [])}
    failing = [check for check in checks if check.get("bucket") == "fail"]
    pending = [check for check in checks if check.get("bucket") in {"pending", "skipping"}]

    if pr.get("isDraft"):
        return "hold", "draft"
    if "needs-rebase" in label_names:
        return "blocked", "needs-rebase"
    if failing:
        return "blocked", f"{len(failing)} failing checks"
    if pending:
        return "wait", f"{len(pending)} pending checks"
    return "merge-ready", "all visible checks green"


def build_triage(open_prs: list[dict[str, Any]], checks_by_pr: dict[int, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    cards = []
    for pr in open_prs:
        checks = checks_by_pr.get(pr["number"], [])
        status, reason = classify_pr(pr, checks)
        cards.append(
            {
                "number": pr["number"],
                "title": pr["title"],
                "headRefName": pr["headRefName"],
                "url": pr["url"],
                "labels": [label["name"] for label in pr.get("labels", [])],
                "status": status,
                "reason": reason,
                "check_counts": {
                    "pass": sum(1 for check in checks if check.get("bucket") == "pass"),
                    "fail": sum(1 for check in checks if check.get("bucket") == "fail"),
                    "pending": sum(1 for check in checks if check.get("bucket") in {"pending", "skipping"}),
                },
            }
        )
    order = {"merge-ready": 0, "wait": 1, "blocked": 2, "hold": 3}
    return sorted(cards, key=lambda item: (order.get(item["status"], 9), item["number"]))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rank open PRs by merge readiness.")
    parser.add_argument("--prs-json", help="Offline PR list JSON file")
    parser.add_argument("--checks-json", help="Offline checks JSON file keyed by PR number")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def load_inputs(args: argparse.Namespace) -> tuple[list[dict[str, Any]], dict[int, list[dict[str, Any]]]]:
    if args.prs_json:
        prs = json.loads(Path(args.prs_json).read_text(encoding="utf-8"))
    else:
        prs = run_gh(
            ["pr", "list", "--state", "open", "--limit", "30", "--json", "number,title,headRefName,isDraft,labels,url"]
        )

    if args.checks_json:
        raw_checks = json.loads(Path(args.checks_json).read_text(encoding="utf-8"))
        checks_by_pr = {int(key): value for key, value in raw_checks.items()}
    else:
        checks_by_pr: dict[int, list[dict[str, Any]]] = {}
        for pr in prs:
            checks_by_pr[pr["number"]] = run_gh(["pr", "checks", str(pr["number"]), "--json", "bucket,name"])
    return prs, checks_by_pr


def main() -> int:
    args = parse_args()
    prs, checks_by_pr = load_inputs(args)
    triage = build_triage(prs, checks_by_pr)

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = ARTIFACT_DIR / "pr_merge_triage.json"
    output_path.write_text(json.dumps(triage, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(triage, indent=2))
    else:
        print(f"wrote={output_path}")
        for card in triage:
            print(
                f"#{card['number']} {card['status']} "
                f"fail={card['check_counts']['fail']} pending={card['check_counts']['pending']} "
                f"{card['headRefName']} :: {card['title']}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
