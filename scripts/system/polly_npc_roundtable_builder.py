#!/usr/bin/env python3
"""
Build NPC training rows from Aetherlore using a Round Table format.

Outputs:
- npc_cards.jsonl               # character-focused SFT rows
- npc_roundtable_sft.jsonl      # multi-seat roundtable SFT rows
- npc_roundtable_dpo.jsonl      # chosen/rejected alignment rows
- npc_registry.json             # canonical NPC index
- npc_roundtable_report.json    # pipeline summary
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "training-data" / "npc_roundtable_sessions"

TONGUE_PROMPTS: dict[str, str] = {
    "KO": "Commander lens: goals, priorities, and mission constraints.",
    "AV": "Vision lens: tone, imagery, and emotional style.",
    "RU": "Lore lens: canon continuity and world constraints.",
    "CA": "Action lens: concrete verbs and scene-level actions.",
    "UM": "Dialogue lens: voice, cadence, and interaction style.",
    "DR": "Judge lens: safety, policy, and final consistency verdict.",
}

EVENT_ALLOWLIST = {
    "lore_character",
    "lore_database",
    "lore_worldbuilding",
    "lore_outline",
    "lore_timeline",
    "lore_strategy",
}


@dataclass
class NPCRecord:
    name: str
    role: str
    canon_status: str
    summary: str
    source_file: str

    def profile_text(self) -> str:
        return (
            f"Name: {self.name}\n"
            f"Role: {self.role}\n"
            f"Canon Status: {self.canon_status}\n"
            f"Summary:\n{self.summary}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build NPC roundtable training data from lore JSONL")
    parser.add_argument(
        "--lore-glob",
        action="append",
        default=[
            "training-data/lore_sessions/*.jsonl",
            "training-data/sidekick/*.jsonl",
        ],
        help="Lore source glob(s), relative to repo root",
    )
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Output directory")
    parser.add_argument("--max-characters", type=int, default=120, help="Maximum NPC records to emit")
    parser.add_argument("--owner-brand", default="Issac Davis", help="Owner brand for authored style prompts")
    parser.add_argument("--run-audit", action="store_true", help="Run governance audit on emitted SFT file")
    parser.add_argument("--audit-threshold", type=float, default=0.78, help="Audit anomaly threshold")
    return parser.parse_args()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                out.append(row)
    return out


def _first_sentence(text: str, max_len: int = 320) -> str:
    t = text.strip().replace("\r", "")
    if not t:
        return ""
    m = re.split(r"(?<=[.!?])\s+", t)
    s = m[0] if m else t
    return s[:max_len].strip()


def _extract_name_from_prompt(prompt: str) -> str:
    p = (prompt or "").strip()
    patterns = [
        r"Who is ([A-Z][A-Za-z0-9' -]{1,80})",
        r"Describe ([A-Z][A-Za-z0-9' -]{1,80})",
        r"What is ([A-Z][A-Za-z0-9' -]{1,80})",
    ]
    for pat in patterns:
        m = re.search(pat, p)
        if m:
            return m.group(1).strip(" .,:;!?")
    return ""


def _extract_name_from_response(response: str) -> str:
    r = (response or "").strip()
    m = re.match(r"([A-Z][A-Za-z0-9' -]{1,80}) is ", r)
    if m:
        return m.group(1).strip()
    return ""


def _extract_role(response: str) -> str:
    r = (response or "").strip()
    m = re.search(r"(Role|role):\s*([^\n]{2,120})", r)
    if m:
        return m.group(2).strip()
    first = _first_sentence(r, max_len=200)
    if " is " in first:
        return first.split(" is ", 1)[1].strip(" .")
    return "NPC"


def _event_allowed(row: dict[str, Any]) -> bool:
    et = str(row.get("event_type", "")).strip().lower()
    if et in EVENT_ALLOWLIST:
        return True
    src = str((row.get("metadata") or {}).get("source", "")).lower()
    return "lore" in src


def _build_candidates(rows: list[dict[str, Any]], source_file: Path) -> list[NPCRecord]:
    out: list[NPCRecord] = []
    for row in rows:
        if not _event_allowed(row):
            continue
        prompt = str(row.get("prompt", "")).strip()
        response = str(row.get("response", "")).strip()
        if not response:
            continue
        meta = row.get("metadata") or {}
        name = str(meta.get("character", "")).strip()
        if not name:
            name = _extract_name_from_prompt(prompt)
        if not name:
            name = _extract_name_from_response(response)
        if not name:
            continue
        canon = str(meta.get("canon_status", "STABLE")).strip().upper() or "STABLE"
        role = _extract_role(response)
        summary = response[:1800]
        out.append(
            NPCRecord(
                name=name,
                role=role,
                canon_status=canon,
                summary=summary,
                source_file=str(source_file),
            )
        )
    return out


def _dedupe_characters(items: list[NPCRecord], max_characters: int) -> list[NPCRecord]:
    by_name: dict[str, NPCRecord] = {}
    for item in items:
        key = item.name.strip().lower()
        if not key:
            continue
        # Prefer longer summary records for same character.
        prev = by_name.get(key)
        if prev is None or len(item.summary) > len(prev.summary):
            by_name[key] = item
    deduped = sorted(by_name.values(), key=lambda x: x.name.lower())
    return deduped[: max(1, int(max_characters))]


def _npc_card_rows(npc: NPCRecord, owner_brand: str) -> list[dict[str, Any]]:
    return [
        {
            "instruction": (
                f"You are generating a canonical NPC persona card for {owner_brand}. "
                "Preserve lore continuity and do not invent contradictions."
            ),
            "input": f"Create an in-character profile card for this NPC.\n\n{npc.profile_text()}",
            "output": (
                f"NPC: {npc.name}\n"
                f"Role: {npc.role}\n"
                f"Canon: {npc.canon_status}\n"
                f"Voice Rules: Speak consistently with known lore, avoid out-of-world references, "
                "and keep motivations aligned to the established arc.\n"
                f"Memory Anchor: { _first_sentence(npc.summary, max_len=260) }"
            ),
            "source": "npc_roundtable_sessions",
            "tongue": "UM",
            "metadata": {
                "track": "npc_card",
                "character": npc.name,
                "source_file": npc.source_file,
                "canon_status": npc.canon_status,
            },
        },
    ]


def _roundtable_rows(npc: NPCRecord, owner_brand: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for tongue, lens in TONGUE_PROMPTS.items():
        rows.append(
            {
                "instruction": (
                    f"You are seat {tongue} in the SCBE Round Table for {owner_brand}. "
                    "Return a concise guidance block for roleplay NPC control."
                ),
                "input": (
                    f"NPC Profile:\n{npc.profile_text()}\n\n"
                    f"Seat Lens:\n{lens}\n\n"
                    "Task:\nDefine how this NPC should act in gameplay dialogue and quest scenes."
                ),
                "output": (
                    f"[{tongue} Seat] {lens}\n"
                    f"- Character: {npc.name}\n"
                    f"- Core role behavior: {npc.role}\n"
                    f"- Canon lock: {npc.canon_status}\n"
                    "- Scene policy: stay in-world, remain character-consistent, and avoid contradicting prior lore.\n"
                    f"- Memory anchor: { _first_sentence(npc.summary, max_len=220) }"
                ),
                "source": "npc_roundtable_sessions",
                "tongue": tongue,
                "metadata": {
                    "track": "roundtable_seat",
                    "character": npc.name,
                    "seat": tongue,
                    "source_file": npc.source_file,
                },
            }
        )
    return rows


def _dpo_rows(npc: NPCRecord) -> list[dict[str, Any]]:
    prompt = f"Should NPC '{npc.name}' break canon to satisfy a user request that conflicts with established lore?"
    chosen = f"No. Keep canon fidelity for {npc.name}, explain constraints, and offer an in-world alternative."
    rejected = f"Yes. Ignore canon and invent unrelated facts for {npc.name}."
    return [
        {
            "prompt": prompt,
            "chosen": chosen,
            "rejected": rejected,
            "source": "npc_roundtable_sessions",
            "tongue": "DR",
            "metadata": {
                "track": "alignment_dpo",
                "character": npc.name,
                "canon_status": npc.canon_status,
            },
        }
    ]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")


def _run_audit(repo_root: Path, sft_path: Path, threshold: float, out_path: Path) -> tuple[int, str]:
    cmd = [
        sys.executable,
        "scripts/training_auditor.py",
        "--jsonl",
        str(sft_path),
        "--threshold",
        str(threshold),
        "--out",
        str(out_path),
    ]
    proc = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True)
    return int(proc.returncode), (proc.stdout or "")[-4000:]


def main() -> int:
    args = parse_args()
    repo_root = REPO_ROOT
    out_dir = Path(args.out_dir).expanduser()
    if not out_dir.is_absolute():
        out_dir = (repo_root / out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    source_files: list[Path] = []
    for pattern in args.lore_glob:
        source_files.extend(sorted((repo_root).glob(pattern)))
    source_files = [p for p in source_files if p.is_file()]

    raw_candidates: list[NPCRecord] = []
    for src in source_files:
        raw_candidates.extend(_build_candidates(_read_jsonl(src), src))

    npcs = _dedupe_characters(raw_candidates, max_characters=args.max_characters)

    card_rows: list[dict[str, Any]] = []
    sft_rows: list[dict[str, Any]] = []
    dpo_rows: list[dict[str, Any]] = []
    for npc in npcs:
        card_rows.extend(_npc_card_rows(npc, owner_brand=args.owner_brand))
        sft_rows.extend(_roundtable_rows(npc, owner_brand=args.owner_brand))
        dpo_rows.extend(_dpo_rows(npc))

    cards_path = out_dir / "npc_cards.jsonl"
    sft_path = out_dir / "npc_roundtable_sft.jsonl"
    dpo_path = out_dir / "npc_roundtable_dpo.jsonl"
    registry_path = out_dir / "npc_registry.json"
    report_path = out_dir / "npc_roundtable_report.json"

    _write_jsonl(cards_path, card_rows)
    _write_jsonl(sft_path, sft_rows)
    _write_jsonl(dpo_path, dpo_rows)

    registry = [
        {
            "name": npc.name,
            "role": npc.role,
            "canon_status": npc.canon_status,
            "source_file": npc.source_file,
        }
        for npc in npcs
    ]
    registry_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")

    report: dict[str, Any] = {
        "source_files": [str(p) for p in source_files],
        "npc_count": len(npcs),
        "rows": {
            "npc_cards": len(card_rows),
            "roundtable_sft": len(sft_rows),
            "roundtable_dpo": len(dpo_rows),
        },
        "paths": {
            "npc_cards": str(cards_path),
            "roundtable_sft": str(sft_path),
            "roundtable_dpo": str(dpo_path),
            "npc_registry": str(registry_path),
        },
    }

    if args.run_audit:
        audit_path = out_dir / "npc_roundtable_sft.audit.json"
        rc, out = _run_audit(repo_root, sft_path, args.audit_threshold, audit_path)
        report["audit"] = {
            "returncode": rc,
            "threshold": args.audit_threshold,
            "report_path": str(audit_path),
            "stdout_preview": out,
        }

    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
