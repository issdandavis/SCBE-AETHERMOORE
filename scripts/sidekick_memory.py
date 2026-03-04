#!/usr/bin/env python3
"""
Sidekick memory and SFT bootstrap utility.

This keeps an append-only memory log that "grows" over time and can be
converted into prompt/response JSONL for cloud training.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIR = REPO_ROOT / "training-data" / "sidekick"
DEFAULT_MEMORY = DEFAULT_DIR / "sidekick_memory.jsonl"
DEFAULT_SFT = DEFAULT_DIR / "sidekick_sft.jsonl"


def utc_now_iso() -> str:
    return dt.datetime.now(dt.UTC).isoformat()


def ensure_layout(base_dir: Path) -> None:
    base_dir.mkdir(parents=True, exist_ok=True)
    for p in (base_dir / "sidekick_memory.jsonl", base_dir / "sidekick_sft.jsonl"):
        if not p.exists():
            p.write_text("", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]], append: bool = True) -> int:
    mode = "a" if append else "w"
    count = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open(mode, encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def normalize_tags(raw_tags: str) -> List[str]:
    tags: List[str] = []
    for piece in raw_tags.split(","):
        tag = piece.strip().lower()
        if not tag:
            continue
        tag = re.sub(r"[^a-z0-9_.-]+", "-", tag)
        if tag:
            tags.append(tag)
    return sorted(set(tags))


def create_memory_event(args: argparse.Namespace) -> Dict[str, Any]:
    return {
        "event_id": f"mem_{uuid.uuid4().hex[:12]}",
        "timestamp_utc": utc_now_iso(),
        "source": args.source,
        "task": args.task.strip(),
        "context": args.context.strip(),
        "action": args.action.strip(),
        "outcome": args.outcome.strip(),
        "artifacts": [x.strip() for x in args.artifacts.split(",") if x.strip()],
        "tags": normalize_tags(args.tags),
        "score": args.score,
    }


def memory_to_sft_rows(events: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for e in events:
        task = str(e.get("task", "")).strip()
        action = str(e.get("action", "")).strip()
        outcome = str(e.get("outcome", "")).strip()
        if not task or not action:
            continue
        context = str(e.get("context", "")).strip()
        tags = e.get("tags", [])
        artifacts = e.get("artifacts", [])
        prompt = (
            f"[SIDEKICK_TASK]\n"
            f"Task: {task}\n"
            f"Context: {context or '(none)'}\n"
            f"Tags: {', '.join(tags) if tags else '(none)'}\n"
            f"Artifacts: {', '.join(artifacts) if artifacts else '(none)'}\n"
            f"What should the sidekick do?"
        )
        response = (
            f"Action plan: {action}\n"
            f"Expected outcome: {outcome or '(not specified)'}"
        )
        rows.append(
            {
                "id": f"sft_{e.get('event_id', uuid.uuid4().hex[:8])}",
                "prompt": prompt,
                "response": response,
                "event_type": "sidekick_memory",
                "metadata": {
                    "source": e.get("source", "manual"),
                    "event_id": e.get("event_id", ""),
                    "timestamp_utc": e.get("timestamp_utc", ""),
                    "tags": tags,
                    "score": e.get("score"),
                },
                "timestamp": dt.datetime.now(dt.UTC).timestamp(),
            }
        )
    return rows


def token_set(text: str) -> set[str]:
    toks = re.findall(r"[a-z0-9]{2,}", text.lower())
    return set(toks)


def suggest(events: List[Dict[str, Any]], query: str, top_k: int) -> List[Dict[str, Any]]:
    q = token_set(query)
    if not q:
        return []
    ranked: List[tuple[float, Dict[str, Any]]] = []
    for e in events:
        blob = " ".join(
            [
                str(e.get("task", "")),
                str(e.get("context", "")),
                str(e.get("action", "")),
                str(e.get("outcome", "")),
                " ".join(e.get("tags", [])),
            ]
        )
        t = token_set(blob)
        if not t:
            continue
        overlap = len(q & t)
        if overlap == 0:
            continue
        score = overlap / max(1, len(q))
        ranked.append((score, e))
    ranked.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in ranked[: max(1, top_k)]]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Sidekick memory + SFT utility")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Create sidekick memory files")
    p_init.add_argument("--dir", default=str(DEFAULT_DIR))

    p_log = sub.add_parser("log", help="Append one memory event")
    p_log.add_argument("--memory", default=str(DEFAULT_MEMORY))
    p_log.add_argument("--source", default="manual")
    p_log.add_argument("--task", required=True)
    p_log.add_argument("--context", default="")
    p_log.add_argument("--action", required=True)
    p_log.add_argument("--outcome", default="")
    p_log.add_argument("--artifacts", default="")
    p_log.add_argument("--tags", default="")
    p_log.add_argument("--score", type=float, default=None)
    p_log.add_argument(
        "--also-sft",
        action="store_true",
        help="Also append one converted SFT row to sidekick_sft.jsonl",
    )

    p_build = sub.add_parser("build-sft", help="Rebuild SFT rows from memory")
    p_build.add_argument("--memory", default=str(DEFAULT_MEMORY))
    p_build.add_argument("--out", default=str(DEFAULT_SFT))

    p_stats = sub.add_parser("stats", help="Show memory and SFT counts")
    p_stats.add_argument("--memory", default=str(DEFAULT_MEMORY))
    p_stats.add_argument("--sft", default=str(DEFAULT_SFT))

    p_suggest = sub.add_parser("suggest", help="Get top memory matches for a query")
    p_suggest.add_argument("--memory", default=str(DEFAULT_MEMORY))
    p_suggest.add_argument("--query", required=True)
    p_suggest.add_argument("--top-k", type=int, default=5)

    return p.parse_args()


def main() -> int:
    args = parse_args()

    if args.cmd == "init":
        ensure_layout(Path(args.dir).expanduser().resolve())
        print(f"Initialized: {Path(args.dir).expanduser().resolve()}")
        return 0

    if args.cmd == "log":
        memory_path = Path(args.memory).expanduser().resolve()
        ensure_layout(memory_path.parent)
        event = create_memory_event(args)
        write_jsonl(memory_path, [event], append=True)
        print(f"Appended memory event: {event['event_id']}")
        print(f"Memory file: {memory_path}")
        if args.also_sft:
            sft_path = memory_path.parent / "sidekick_sft.jsonl"
            rows = memory_to_sft_rows([event])
            write_jsonl(sft_path, rows, append=True)
            print(f"Appended SFT row: {len(rows)} -> {sft_path}")
        return 0

    if args.cmd == "build-sft":
        memory_path = Path(args.memory).expanduser().resolve()
        out_path = Path(args.out).expanduser().resolve()
        events = read_jsonl(memory_path)
        rows = memory_to_sft_rows(events)
        write_jsonl(out_path, rows, append=False)
        print(f"Memory events: {len(events)}")
        print(f"SFT rows written: {len(rows)}")
        print(f"Output: {out_path}")
        return 0

    if args.cmd == "stats":
        memory_path = Path(args.memory).expanduser().resolve()
        sft_path = Path(args.sft).expanduser().resolve()
        memory_events = read_jsonl(memory_path)
        sft_rows = read_jsonl(sft_path)
        print(
            json.dumps(
                {
                    "memory_file": str(memory_path),
                    "memory_events": len(memory_events),
                    "sft_file": str(sft_path),
                    "sft_rows": len(sft_rows),
                },
                indent=2,
            )
        )
        return 0

    if args.cmd == "suggest":
        memory_path = Path(args.memory).expanduser().resolve()
        events = read_jsonl(memory_path)
        hits = suggest(events, args.query, args.top_k)
        if not hits:
            print("No matches.")
            return 0
        for i, hit in enumerate(hits, start=1):
            print(f"{i}. [{hit.get('event_id', '')}] {hit.get('task', '')}")
            print(f"   action: {hit.get('action', '')}")
            print(f"   outcome: {hit.get('outcome', '')}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
