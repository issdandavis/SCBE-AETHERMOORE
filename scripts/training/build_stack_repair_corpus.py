"""Build the first SCBE stack-agent SFT corpus.

This is not a generic MBPP corpus. It teaches the stack-agent loop:

    task -> attempted action -> execution feedback -> repair -> receipt

The load-bearing records come from execution-verified pitfall pairs already in
`python.helm.better_corpus` and `python.helm.pitfall_eval`. Optional stack-smoke
records teach how to run bounded repo checks without pretending they are model
capability evals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from python.helm import better_corpus, pitfall_eval, public_bench

SYSTEM = """You are an SCBE stack coding agent.
Use this action grammar:
PLAN: identify the repo surface and invariant.
CALL run_code or CALL run_command with the smallest bounded check.
TOOL feedback is evidence, not decoration.
REPAIR only what the evidence supports.
ANSWER with the final artifact and a receipt.
Never claim success without an execution check."""


def _json_line(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=True, sort_keys=True)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _first_failure(source: str, tests: Sequence[str]) -> str:
    check = public_bench._verify(source, [], tests, [])
    failures = list(check.get("hidden_failures", [])) or list(check.get("public_failures", []))
    if not failures:
        return "FAIL: expected failure, but no failure text was emitted"
    return "FAIL: " + str(failures[0])[:900]


def _passes(source: str, tests: Sequence[str]) -> bool:
    return bool(public_bench._verify(source, [], tests, [])["hidden_passed"])


def _repair_record(
    *,
    source: str,
    task_id: str,
    pitfall_class: str,
    prompt: str,
    buggy: str,
    fix: str,
    tests: Sequence[str],
) -> Optional[Dict[str, Any]]:
    buggy_passes = _passes(buggy, tests)
    fix_passes = _passes(fix, tests)
    if buggy_passes or not fix_passes:
        return None
    failure = _first_failure(buggy, tests)
    public_test = list(tests)[0] if tests else ""
    messages = [
        {"role": "system", "content": SYSTEM},
        {
            "role": "user",
            "content": (
                "STACK TASK: repair this coding task using the SCBE action grammar.\n"
                f"Surface: python execution verifier\nPitfall class: {pitfall_class}\n\n"
                f"Problem:\n{prompt}\n\nVisible check:\n{public_test}"
            ),
        },
        {
            "role": "assistant",
            "content": (
                "PLAN: try the direct implementation, then run the bounded Python tests.\n"
                "CALL run_code\n```python\n" + buggy + "\n```"
            ),
        },
        {"role": "user", "content": "TOOL run_code: " + failure},
        {
            "role": "assistant",
            "content": (
                "REPAIR: the execution feedback exposes the pitfall; replace the faulty pattern.\n"
                "CALL run_code\n```python\n" + fix + "\n```"
            ),
        },
        {"role": "user", "content": "TOOL run_code: PASS"},
        {
            "role": "assistant",
            "content": "ANSWER:\n```python\n"
            + fix
            + "\n```\nRECEIPT: verified=PASS; source="
            + source
            + "; task_id="
            + task_id,
        },
    ]
    return {
        "messages": messages,
        "meta": {
            "task_id": task_id,
            "category": "pitfall_repair",
            "source": source,
            "pitfall_class": pitfall_class,
            "verified": True,
            "buggy_fails": True,
            "fix_passes": True,
            "tests": list(tests),
            "buggy": buggy,
            "fix": fix,
        },
    }


def pitfall_records(limit: Optional[int] = None) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for spec in better_corpus.PITFALLS:
        rec = _repair_record(
            source="python.helm.better_corpus",
            task_id="better_" + spec["name"],
            pitfall_class=spec["name"],
            prompt=spec["prompt"],
            buggy=spec["buggy"],
            fix=spec["fix"],
            tests=spec["tests"],
        )
        if rec:
            records.append(rec)
    for spec in pitfall_eval.EVAL:
        rec = _repair_record(
            source="python.helm.pitfall_eval",
            task_id="pitfalleval_" + spec["name"],
            pitfall_class=spec["cls"],
            prompt=spec["prompt"],
            buggy=spec["naive"],
            fix=spec["ref"],
            tests=spec["tests"],
        )
        if rec:
            records.append(rec)
    return records[:limit] if limit is not None else records


def _run_command(command: Sequence[str], cwd: Path, timeout: int = 45) -> Dict[str, Any]:
    proc = subprocess.run(command, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
    out = (proc.stdout + proc.stderr).strip()
    return {"returncode": proc.returncode, "output": out[-1200:]}


def stack_smoke_records(repo: Path) -> List[Dict[str, Any]]:
    specs = [
        {
            "task_id": "stack_pycompile_code_lift",
            "surface": "python compiler",
            "command": [sys.executable, "-m", "py_compile", "python/helm/code_lift.py"],
            "why": "prove the code-lift evaluator imports as valid Python before training notebooks depend on it",
        },
        {
            "task_id": "stack_pitfall_eval_smoke",
            "surface": "pitfall held-out eval",
            "command": [sys.executable, "-m", "python.helm.pitfall_eval"],
            "why": "prove the held-out pitfall eval still discriminates before using it as a lift ruler",
        },
    ]
    records: List[Dict[str, Any]] = []
    for spec in specs:
        result = _run_command(spec["command"], repo)
        passed = result["returncode"] == 0
        command_text = " ".join(spec["command"])
        messages = [
            {"role": "system", "content": SYSTEM},
            {
                "role": "user",
                "content": (
                    "STACK TASK: run a bounded repo check.\n"
                    f"Surface: {spec['surface']}\nReason: {spec['why']}\n"
                    f"Command: {command_text}"
                ),
            },
            {
                "role": "assistant",
                "content": (
                    "PLAN: use the narrowest command that verifies this surface.\n"
                    "CALL run_command\n```powershell\n" + command_text + "\n```"
                ),
            },
            {
                "role": "user",
                "content": ("TOOL run_command: PASS\n" if passed else "TOOL run_command: FAIL\n") + result["output"],
            },
            {
                "role": "assistant",
                "content": (
                    "ANSWER: "
                    + (
                        "the bounded stack check passed."
                        if passed
                        else "the bounded stack check failed; do not train on it as proof."
                    )
                    + "\nRECEIPT: verified="
                    + ("PASS" if passed else "FAIL")
                    + "; task_id="
                    + spec["task_id"]
                ),
            },
        ]
        records.append(
            {
                "messages": messages,
                "meta": {
                    "task_id": spec["task_id"],
                    "category": "stack_smoke",
                    "source": "scripts.training.build_stack_repair_corpus",
                    "verified": passed,
                    "command": list(spec["command"]),
                    "returncode": result["returncode"],
                },
            }
        )
    return records


def build_records(repo: Path, limit_pitfalls: Optional[int], include_smoke: bool) -> List[Dict[str, Any]]:
    records = pitfall_records(limit=limit_pitfalls)
    if include_smoke:
        records.extend(stack_smoke_records(repo))
    return records


def write_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for rec in records:
            f.write(_json_line(rec) + "\n")
            count += 1
    return count


def write_manifest(path: Path, out: Path, records: Sequence[Dict[str, Any]], repo: Path) -> Dict[str, Any]:
    categories: Dict[str, int] = {}
    for rec in records:
        cat = rec.get("meta", {}).get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
    try:
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(repo), text=True).strip()
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=str(repo), text=True).strip()
    except Exception:
        head = "unknown"
        branch = "unknown"
    manifest = {
        "schema": "scbe.stack_agent_corpus.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "repo": str(repo),
        "git_head": head,
        "git_branch": branch,
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "records": len(records),
        "categories": categories,
        "verified_records": sum(1 for r in records if r.get("meta", {}).get("verified") is True),
        "output": str(out),
        "sha256": _sha256(out),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")
    return manifest


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Build the SCBE stack-agent repair corpus")
    ap.add_argument("--out", default="training/sft_records/stack_agent_seed.jsonl")
    ap.add_argument("--manifest", default=None)
    ap.add_argument("--limit-pitfalls", type=int, default=None)
    ap.add_argument("--include-smoke", action="store_true", help="also execute and include bounded stack smoke checks")
    args = ap.parse_args(list(argv) if argv is not None else None)

    repo = Path.cwd()
    out = Path(args.out)
    manifest_path = Path(args.manifest) if args.manifest else out.with_suffix(out.suffix + ".manifest.json")
    records = build_records(repo, args.limit_pitfalls, args.include_smoke)
    if not records:
        raise SystemExit("no records built")
    write_jsonl(out, records)
    manifest = write_manifest(manifest_path, out, records, repo)
    print(
        "STACK_AGENT_CORPUS records=%d verified=%d sha256=%s out=%s"
        % (manifest["records"], manifest["verified_records"], manifest["sha256"], out)
    )
    print("manifest=%s" % manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
