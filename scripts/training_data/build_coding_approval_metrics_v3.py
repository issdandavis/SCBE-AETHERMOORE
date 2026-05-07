#!/usr/bin/env python3
"""Build the compact coding-approval-metrics v3 SFT pack.

This round teaches the agent fleet to preserve option value instead of
collapsing every path into pass/fail. It uses only existing local artifacts:
Markdown task-flow cards, executable packet traces, and positive gate residues.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = REPO_ROOT / "training-data" / "sft"
DEFAULT_KAGGLE_DIR = REPO_ROOT / "artifacts" / "kaggle_datasets" / "scbe-coding-agent-stage6-repair-v7"
FLOW_MANIFEST = REPO_ROOT / "notes" / "agentic_task_flows" / "manifest.json"
PACKET_TRACES = REPO_ROOT / "training-data" / "agentic_coding" / "packet_traces.jsonl"
RESIDUES = (
    REPO_ROOT
    / "artifacts"
    / "training_digestion"
    / "stage5-command-harmony-signal-repair-69f6a61c"
    / "training_residues.jsonl"
)

FALLBACK_RESIDUES = [
    {
        "prompt_id": "fallback_seed_hold_open_path",
        "contract_id": "coding_approval_metrics_v3_fallback",
        "token_chain": ["approval", "evidence", "incubate"],
        "loss_latest": 0.0,
    },
    {
        "prompt_id": "fallback_seed_long_return",
        "contract_id": "coding_approval_metrics_v3_fallback",
        "token_chain": ["long_return", "reuse", "compact"],
        "loss_latest": 0.0,
    },
]

TRAIN_NAME = "coding_approval_metrics_v3_train.sft.jsonl"
EVAL_NAME = "coding_approval_metrics_v3_eval.sft.jsonl"
MANIFEST_NAME = "coding_approval_metrics_v3_manifest.json"

SACRED_TONGUE_NAMES = {
    "KO": "Kor'aelin",
    "AV": "Avali",
    "RU": "Runethic",
    "CA": "Cassisivadan",
    "UM": "Umbroth",
    "DR": "Draumric",
}

SYSTEM = (
    "You are an SCBE-AETHERMOORE agentic coding approval instructor. "
    "Use non-binary verdicts: PROMOTE, HOLD, INCUBATE, TRANSFORM, ESCALATE, DENY, or ARCHIVE. "
    "Preserve long-return design paths when they have plausible future value, but require concrete evidence before "
    "promotion. Mention the full Sacred Tongue names when route context matters: Kor'aelin, Avali, Runethic, "
    "Cassisivadan, Umbroth, and Draumric."
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            rows.append(json.loads(stripped))
    return rows


def _record(*, source: str, scenario: str, user: str, assistant: str, meta: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "metadata": {
            "track": "coding_approval_metrics_v3",
            "source": source,
            "scenario": scenario,
            **meta,
        },
    }
    payload["id"] = f"coding_approval_metrics_v3_{source}_{_sha(json.dumps(payload, sort_keys=True))}"
    return payload


def build_task_flow_records(limit: int = 72) -> list[dict[str, Any]]:
    manifest = json.loads(FLOW_MANIFEST.read_text(encoding="utf-8"))
    cards = sorted(manifest.get("cards", []), key=lambda item: (item.get("script_tongue", ""), item.get("script_path", "")))
    records: list[dict[str, Any]] = []
    for card in cards[:limit]:
        tongue = card.get("script_tongue", "")
        tongue_name = card.get("script_tongue_name") or SACRED_TONGUE_NAMES.get(tongue, tongue)
        card_tongue_name = card.get("card_tongue_name") or "Draumric"
        user = (
            "Evaluate this agentic task-flow card before execution.\n\n"
            f"title: {card.get('title')}\n"
            f"script_path: {card.get('script_path')}\n"
            f"command: {card.get('command')}\n"
            f"purpose: {card.get('purpose')}\n"
            f"card_route: {card.get('card_tongue')} / {card_tongue_name} Markdown\n"
            f"script_route: {tongue} / {tongue_name} / {card.get('script_language')}\n"
            f"route_reason: {card.get('route_reason')}\n\n"
            "Return a verdict, evidence requirement, next safe action, and whether this is fast, medium, or long return."
        )
        assistant = (
            "verdict=HOLD\n"
            "return_horizon=medium\n"
            f"route={card.get('card_tongue')}:{card_tongue_name}->"
            f"{tongue}:{tongue_name}\n"
            "evidence_required=read the Markdown card, confirm the script still exists, and run the narrowest dry-run or "
            "targeted test before promotion\n"
            f"next_safe_action=inspect {card.get('card_path')} before executing `{card.get('command')}`\n"
            "reason=The card is useful routeable structure, but execution should wait for current-file verification."
        )
        records.append(
            _record(
                source="markdown_task_flow",
                scenario="route_card_approval",
                user=user,
                assistant=assistant,
                meta={
                    "script_path": card.get("script_path"),
                    "card_path": card.get("card_path"),
                    "script_tongue": tongue,
                    "script_tongue_name": tongue_name,
                    "card_tongue_name": card_tongue_name,
                },
            )
        )
    return records


def build_packet_trace_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for row in _read_jsonl(PACKET_TRACES):
        meta = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
        tongue = str(meta.get("tongue") or "")
        tongue_name = SACRED_TONGUE_NAMES.get(tongue, tongue or "unknown")
        user = (
            "Approve this executable packet-trace training example.\n\n"
            f"instruction: {row.get('instruction')}\n"
            f"packet_fingerprint: {meta.get('packet_fingerprint')}\n"
            f"phase: {meta.get('phase')}\n"
            f"node_id: {meta.get('node_id')}\n"
            f"route: {tongue} / {tongue_name}\n\n"
            "Return the approval verdict and the exact artifact-preservation rule."
        )
        assistant = (
            "verdict=PROMOTE\n"
            "return_horizon=fast\n"
            f"route={tongue}:{tongue_name}\n"
            "evidence_required=packet fingerprint must round-trip and response JSON must remain byte-deterministic\n"
            "next_safe_action=keep this row in executable-trace SFT and score it with score_packet_trace_sft before promotion\n"
            "artifact_rule=preserve instruction, metadata.packet_fingerprint, and compact JSON response; do not replace it "
            "with prose."
        )
        records.append(
            _record(
                source="packet_trace",
                scenario=str(row.get("category") or "agentic_packet_trace"),
                user=user,
                assistant=assistant,
                meta={
                    "trace_id": row.get("id"),
                    "packet_fingerprint": meta.get("packet_fingerprint"),
                    "tongue": tongue,
                    "tongue_name": tongue_name,
                },
            )
        )
    return records


def build_residue_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    rows = _read_jsonl(RESIDUES) or FALLBACK_RESIDUES
    for row in rows:
        chain = row.get("token_chain") if isinstance(row.get("token_chain"), list) else []
        user = (
            "Digest this post-gate training residue.\n\n"
            f"prompt_id: {row.get('prompt_id')}\n"
            f"contract_id: {row.get('contract_id')}\n"
            f"token_chain: {' | '.join(str(item) for item in chain)}\n"
            f"loss_latest: {row.get('loss_latest')}\n\n"
            "Return how the fleet should reuse this residue without bloating context."
        )
        assistant = (
            "verdict=INCUBATE\n"
            "return_horizon=long\n"
            "evidence_required=reuse only the compact token chain and contract id; discard full conversational clutter\n"
            "next_safe_action=store as a small skill seed or gate reminder when the same command family appears again\n"
            "reason=This is positive residue from a passed gate. It should bias future routing lightly without becoming a "
            "large prompt replay."
        )
        records.append(
            _record(
                source="training_residue",
                scenario="post_gate_digest",
                user=user,
                assistant=assistant,
                meta={
                    "prompt_id": row.get("prompt_id"),
                    "contract_id": row.get("contract_id"),
                    "token_chain_len": len(chain),
                },
            )
        )
    return records


def split_records(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    train: list[dict[str, Any]] = []
    eval_rows: list[dict[str, Any]] = []
    for idx, record in enumerate(records):
        record = dict(record)
        record["metadata"] = dict(record["metadata"])
        split = "eval" if idx % 5 == 0 else "train"
        record["metadata"]["split"] = split
        if split == "eval":
            eval_rows.append(record)
        else:
            train.append(record)
    return train, eval_rows


def write_outputs(out_dir: Path, *, copy_kaggle: bool = False, kaggle_dir: Path = DEFAULT_KAGGLE_DIR) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    records = build_task_flow_records() + build_packet_trace_records() + build_residue_records()
    train, eval_rows = split_records(records)

    train_path = out_dir / TRAIN_NAME
    eval_path = out_dir / EVAL_NAME
    manifest_path = out_dir / MANIFEST_NAME
    train_path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in train) + "\n", encoding="utf-8")
    eval_path.write_text("\n".join(json.dumps(row, sort_keys=True) for row in eval_rows) + "\n", encoding="utf-8")

    source_counts: dict[str, int] = {}
    verdict_counts: dict[str, int] = {}
    for row in records:
        source = str(row["metadata"].get("source"))
        source_counts[source] = source_counts.get(source, 0) + 1
        content = row["messages"][-1]["content"]
        verdict = content.split("\n", 1)[0].replace("verdict=", "").strip()
        verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1

    manifest = {
        "schema_version": "scbe_coding_approval_metrics_v3_manifest",
        "track": "coding_approval_metrics_v3",
        "train_file": TRAIN_NAME,
        "eval_file": EVAL_NAME,
        "train_count": len(train),
        "eval_count": len(eval_rows),
        "total_count": len(records),
        "source_counts": source_counts,
        "verdict_counts": verdict_counts,
        "sacred_tongue_names": SACRED_TONGUE_NAMES,
        "source_paths": {
            "flow_manifest": str(FLOW_MANIFEST.relative_to(REPO_ROOT)),
            "packet_traces": str(PACKET_TRACES.relative_to(REPO_ROOT)),
            "residues": str(RESIDUES.relative_to(REPO_ROOT)),
        },
        "sha256": {
            TRAIN_NAME: hashlib.sha256(train_path.read_bytes()).hexdigest(),
            EVAL_NAME: hashlib.sha256(eval_path.read_bytes()).hexdigest(),
        },
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if copy_kaggle:
        kaggle_dir.mkdir(parents=True, exist_ok=True)
        for path in (train_path, eval_path, manifest_path):
            (kaggle_dir / path.name).write_bytes(path.read_bytes())

    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--copy-kaggle", action="store_true")
    parser.add_argument("--kaggle-dir", type=Path, default=DEFAULT_KAGGLE_DIR)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    manifest = write_outputs(args.out_dir, copy_kaggle=args.copy_kaggle, kaggle_dir=args.kaggle_dir)
    if args.json:
        print(json.dumps(manifest, indent=2, sort_keys=True))
    else:
        print(
            f"wrote {manifest['train_count']} train / {manifest['eval_count']} eval rows "
            f"to {args.out_dir}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
