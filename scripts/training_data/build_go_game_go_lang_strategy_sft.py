#!/usr/bin/env python3
"""Build Go-game plus Go-language strategy SFT rows for agentic coding."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER

DEFAULT_OUT_DIR = REPO_ROOT / "training-data" / "sft"
DEFAULT_KAGGLE_DIR = REPO_ROOT / "artifacts" / "kaggle_datasets" / "scbe-coding-agent-stage6-repair-v7"
TRAIN_NAME = "go_game_go_lang_agentic_strategy_v1_train.sft.jsonl"
EVAL_NAME = "go_game_go_lang_agentic_strategy_v1_eval.sft.jsonl"
MANIFEST_NAME = "go_game_go_lang_agentic_strategy_v1_manifest.json"

SYSTEM = (
    "You are an SCBE-AETHERMOORE agentic coding strategist. Use Go the board game and Go the programming "
    "language as training analogies only when they improve task decisions. Keep outputs practical and testable."
)

CONCEPTS = [
    {
        "concept": "liberty",
        "coding_behavior": "available safe next actions before a task group is blocked",
        "go_language": "small explicit interface with one clear caller",
        "difficulty_band": "easy",
        "move": "defend",
    },
    {
        "concept": "atari",
        "coding_behavior": "one failing gate away from a blocked state",
        "go_language": "return errors immediately and expose the exact failing condition",
        "difficulty_band": "easy",
        "move": "defend",
    },
    {
        "concept": "ko",
        "coding_behavior": "retry loop or repeated patch cycle that needs a different move",
        "go_language": "make loop exits explicit and test the repeated-state guard",
        "difficulty_band": "medium",
        "move": "tenuki_or_reframe",
    },
    {
        "concept": "sente",
        "coding_behavior": "action that forces the next necessary response while preserving initiative",
        "go_language": "write the narrow failing test first so implementation has a forced target",
        "difficulty_band": "medium",
        "move": "attack_with_test",
    },
    {
        "concept": "gote",
        "coding_behavior": "locally useful move that gives up initiative or delays the gate",
        "go_language": "avoid broad refactors when a small function patch unlocks the test",
        "difficulty_band": "medium",
        "move": "defer",
    },
    {
        "concept": "territory",
        "coding_behavior": "owned module or file boundary",
        "go_language": "package boundary with exported surface kept small",
        "difficulty_band": "easy",
        "move": "hold_boundary",
    },
    {
        "concept": "influence",
        "coding_behavior": "indirect future leverage from a small architectural move",
        "go_language": "interface or table-driven test that makes later cases cheaper",
        "difficulty_band": "hard",
        "move": "build_shape",
    },
    {
        "concept": "sacrifice",
        "coding_behavior": "drop a noisy path to keep the main workflow alive",
        "go_language": "delete or quarantine an experiment after preserving its useful receipt",
        "difficulty_band": "hard",
        "move": "sacrifice",
    },
    {
        "concept": "life_and_death",
        "coding_behavior": "whether the workflow survives tests, gates, and rollback constraints",
        "go_language": "integration test plus error boundary decides viability",
        "difficulty_band": "hard",
        "move": "read_deep",
    },
]

TONGUE_SPEAKERS = [
    {
        "code": "ko",
        "short": "KO",
        "full": "Kor'aelin",
        "role": "intent and opening direction",
    },
    {
        "code": "av",
        "short": "AV",
        "full": "Avali",
        "role": "context and board reading",
    },
    {
        "code": "ru",
        "short": "RU",
        "full": "Runethic",
        "role": "binding and threat response",
    },
    {
        "code": "ca",
        "short": "CA",
        "full": "Cassisivadan",
        "role": "calculation and liberty count",
    },
    {
        "code": "um",
        "short": "UM",
        "full": "Umbroth",
        "role": "hidden risk and sacrifice logic",
    },
    {
        "code": "dr",
        "short": "DR",
        "full": "Draumric",
        "role": "structure and final attestation",
    },
]

GO_DIALOGUE_TURNS = [
    {
        "turn": 1,
        "player": "black",
        "move": "D4",
        "concept": "corner_claim",
        "strategy": "take stable corner influence before fighting",
        "team_message": "Black opens with a corner anchor. The team should preserve future liberties before local fights.",
    },
    {
        "turn": 2,
        "player": "white",
        "move": "Q16",
        "concept": "opposite_corner",
        "strategy": "answer with balance instead of chasing",
        "team_message": "White mirrors across the board. Translation must keep the board coordinate exact across tongues.",
    },
    {
        "turn": 3,
        "player": "black",
        "move": "C16",
        "concept": "extension",
        "strategy": "build shape while keeping a route back to safety",
        "team_message": "Black extends on the upper side. The move is not an attack yet; it stores future influence.",
    },
    {
        "turn": 4,
        "player": "white",
        "move": "Q4",
        "concept": "framework_balance",
        "strategy": "avoid overconcentration by taking the open quadrant",
        "team_message": "White claims the last big corner. The group strategy remains whole-board, not local greed.",
    },
    {
        "turn": 5,
        "player": "black",
        "move": "K10",
        "concept": "center_probe",
        "strategy": "test center influence after corners are stable",
        "team_message": "Black probes the center. The team should ask whether this creates sente or merely noise.",
    },
    {
        "turn": 6,
        "player": "white",
        "move": "pass",
        "concept": "stand_and_audit",
        "strategy": "pause when the board needs verification more than another move",
        "team_message": "White passes to force audit. A pass is still a semantic move and must round-trip bijectively.",
    },
]


def _sha(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _stable_payload_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _transport_packet(payload: dict[str, Any], tongue_code: str) -> dict[str, Any]:
    source_bytes = _stable_payload_bytes(payload)
    tokens = SACRED_TONGUE_TOKENIZER.encode_bytes(tongue_code, source_bytes)
    decoded = SACRED_TONGUE_TOKENIZER.decode_tokens(tongue_code, tokens)
    return {
        "tongue_code": tongue_code,
        "token_count": len(tokens),
        "token_sha256": hashlib.sha256(" ".join(tokens).encode("utf-8")).hexdigest(),
        "source_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "first_12_tokens": tokens[:12],
        "roundtrip_ok": decoded == source_bytes,
    }


def _record(concept: dict[str, str], idx: int) -> dict[str, Any]:
    user = (
        "Map this Go-game concept into an agentic coding move and a Go-language habit.\n\n"
        f"concept: {concept['concept']}\n"
        f"repo situation: {concept['coding_behavior']}\n"
        "Return the move, why it applies, and the next testable action."
    )
    assistant = (
        f"move={concept['move']}\n"
        f"go_game_concept={concept['concept']}\n"
        f"coding_behavior={concept['coding_behavior']}\n"
        f"go_language_habit={concept['go_language']}\n"
        "next_testable_action=write or run the narrowest check that proves the group still has liberties before "
        "expanding the task"
    )
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "metadata": {
            "track": "go_game_go_lang_agentic_strategy_v1",
            "concept": concept["concept"],
            "move": concept["move"],
            "difficulty_band": concept["difficulty_band"],
            "language": "Go",
            "strategy_source": "go_board_game_and_go_language_bridge",
            "curriculum_order": idx,
        },
    }
    payload["id"] = f"go_game_go_lang_agentic_strategy_v1_{concept['concept']}_{_sha(payload)[:12]}"
    return payload


def _go_dialogue_record(turn: dict[str, Any], idx: int) -> dict[str, Any]:
    speaker = TONGUE_SPEAKERS[(turn["turn"] - 1) % len(TONGUE_SPEAKERS)]
    semantic_payload = {
        "game": "go",
        "board_size": 19,
        "turn": turn["turn"],
        "player": turn["player"],
        "move": turn["move"],
        "concept": turn["concept"],
        "strategy": turn["strategy"],
        "team_message": turn["team_message"],
    }
    transport = _transport_packet(semantic_payload, speaker["code"])
    user = (
        "Play one turn of Go through the bijective Sacred Tongues transport layer.\n\n"
        f"Speaker language: {speaker['full']} ({speaker['short']})\n"
        f"Role: {speaker['role']}\n"
        f"Semantic payload JSON: {json.dumps(semantic_payload, sort_keys=True)}\n\n"
        "Return the exact move, the strategic reason, and the transport verification."
    )
    assistant = (
        f"speaker={speaker['full']} ({speaker['short']})\n"
        f"player={turn['player']}\n"
        f"move={turn['move']}\n"
        f"go_concept={turn['concept']}\n"
        f"strategy={turn['strategy']}\n"
        f"teamwork_note={turn['team_message']}\n"
        "translation_boundary=semantic Go move stays invariant while the speaking tongue changes\n"
        f"transport_roundtrip_ok={str(transport['roundtrip_ok']).lower()}\n"
        f"transport_token_count={transport['token_count']}\n"
        f"transport_token_sha256={transport['token_sha256']}"
    )
    payload = {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
        "metadata": {
            "track": "go_game_go_lang_agentic_strategy_v1",
            "concept": turn["concept"],
            "move": turn["move"],
            "difficulty_band": "medium" if turn["move"] != "pass" else "hard",
            "language": "Go",
            "speaker_tongue": speaker["short"],
            "speaker_tongue_full": speaker["full"],
            "strategy_source": "go_board_game_cross_tongue_bijective_dialogue",
            "curriculum_order": idx,
            "semantic_payload_sha256": transport["source_sha256"],
            "transport_token_sha256": transport["token_sha256"],
            "transport_roundtrip_ok": transport["roundtrip_ok"],
        },
        "semantic_payload": semantic_payload,
        "bijective_transport": transport,
    }
    payload["id"] = f"go_game_go_lang_agentic_strategy_v1_cross_tongue_turn_{turn['turn']}_{_sha(payload)[:12]}"
    return payload


def build_records() -> list[dict[str, Any]]:
    records = [_record(concept, idx) for idx, concept in enumerate(CONCEPTS)]
    board_user = (
        "A coding fleet has three groups: research bridge has citations but no eval, operator bus has tests but "
        "weak handoff, and governance has one failing boundary check. Choose the next Go-style move."
    )
    board_assistant = (
        "move=defend\n"
        "reason=governance is in atari because one boundary check can block promotion; research and operator lanes "
        "still have liberties\n"
        "next_testable_action=fix or rerun the governance boundary check before expanding research or bus features\n"
        "go_language_habit=return the exact failing error and keep the patch scoped to the boundary function"
    )
    board = {
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": board_user},
            {"role": "assistant", "content": board_assistant},
        ],
        "metadata": {
            "track": "go_game_go_lang_agentic_strategy_v1",
            "concept": "board_state",
            "move": "defend",
            "difficulty_band": "hard",
            "language": "Go",
            "strategy_source": "agentic_board_state_eval",
            "curriculum_order": len(records),
        },
    }
    board["id"] = f"go_game_go_lang_agentic_strategy_v1_board_state_{_sha(board)[:12]}"
    records.append(board)
    records.extend(_go_dialogue_record(turn, len(records) + idx) for idx, turn in enumerate(GO_DIALOGUE_TURNS))
    return records


def split_records(records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    train: list[dict[str, Any]] = []
    eval_rows: list[dict[str, Any]] = []
    for idx, row in enumerate(records):
        item = dict(row)
        item["metadata"] = dict(row["metadata"])
        split = "eval" if idx in {2, 9} else "train"
        item["metadata"]["split"] = split
        (eval_rows if split == "eval" else train).append(item)
    return train, eval_rows


def write_outputs(
    out_dir: Path = DEFAULT_OUT_DIR, *, copy_kaggle: bool = False, kaggle_dir: Path = DEFAULT_KAGGLE_DIR
) -> dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    records = build_records()
    train, eval_rows = split_records(records)
    train_path = out_dir / TRAIN_NAME
    eval_path = out_dir / EVAL_NAME
    manifest_path = out_dir / MANIFEST_NAME

    for path, rows in ((train_path, train), (eval_path, eval_rows)):
        path.write_text(
            "\n".join(json.dumps(row, sort_keys=True, ensure_ascii=True) for row in rows) + "\n", encoding="utf-8"
        )

    difficulty_counts: dict[str, int] = {}
    for row in records:
        band = str(row["metadata"]["difficulty_band"])
        difficulty_counts[band] = difficulty_counts.get(band, 0) + 1

    manifest = {
        "schema_version": "go_game_go_lang_agentic_strategy_v1_manifest",
        "train_file": str(train_path.relative_to(REPO_ROOT)),
        "eval_file": str(eval_path.relative_to(REPO_ROOT)),
        "train_records": len(train),
        "eval_records": len(eval_rows),
        "difficulty_counts": difficulty_counts,
        "cross_tongue_dialogue_records": sum(
            1
            for row in records
            if row["metadata"]["strategy_source"] == "go_board_game_cross_tongue_bijective_dialogue"
        ),
        "bijective_transport_gate": {
            "all_dialogue_roundtrips_ok": all(
                row.get("metadata", {}).get("transport_roundtrip_ok", True) for row in records
            ),
            "speaker_tongues_full": [speaker["full"] for speaker in TONGUE_SPEAKERS],
        },
        "math_boosters": {
            "curriculum_difficulty_scheduling": "easy -> medium -> hard strategy rows",
            "multi_granularity_preference": "concept, move, language habit, and next action are separately inspectable",
            "geometric_mean_reward_stabilization": "reserved for later mechanical reward loops; not applied to SFT labels",
        },
        "sha256": _sha(records),
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=True), encoding="utf-8")

    copied: list[str] = []
    if copy_kaggle:
        kaggle_dir.mkdir(parents=True, exist_ok=True)
        for path in (train_path, eval_path, manifest_path):
            target = kaggle_dir / path.name
            shutil.copy2(path, target)
            copied.append(str(target.relative_to(REPO_ROOT)))

    return {
        "ok": True,
        "train_records": len(train),
        "eval_records": len(eval_rows),
        "train_path": str(train_path),
        "eval_path": str(eval_path),
        "manifest_path": str(manifest_path),
        "copied_to_kaggle": copied,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--copy-kaggle", action="store_true")
    parser.add_argument("--kaggle-dir", type=Path, default=DEFAULT_KAGGLE_DIR)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = write_outputs(args.out_dir, copy_kaggle=args.copy_kaggle, kaggle_dir=args.kaggle_dir)
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=True))
    else:
        print(
            "go game/go language strategy SFT: "
            f"train={result['train_records']} eval={result['eval_records']} path={result['train_path']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
