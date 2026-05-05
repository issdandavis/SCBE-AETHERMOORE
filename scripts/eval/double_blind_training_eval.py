#!/usr/bin/env python3
"""Double-blind training evaluation with commit-reveal receipts.

This tool scores precomputed candidate responses without exposing candidate
identity to the scoring stage. It is intentionally model-free: collect outputs
from Hugging Face, Kaggle, Colab, local models, or API lanes first, then pass
them here as one JSON payload.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "artifacts" / "eval" / "double_blind_training_eval_latest.json"
SCHEMA_VERSION = "scbe_double_blind_training_eval_v1"
INPUT_SCHEMA_VERSION = "scbe_double_blind_eval_input_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _canonical_json(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _safe_id(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "").strip())
    return re.sub(r"-+", "-", safe).strip("-.") or "candidate"


_WORD_LIKE = re.compile(r"[a-z0-9_ -]+")


def _contains_token(body_lower: str, token: str) -> bool:
    return str(token).lower() in body_lower


def _contains_forbidden(body_lower: str, term: str) -> bool:
    """Forbidden-token check that respects word boundaries for word-like terms.

    Mirrors the dispatcher's inline gate semantics
    (scripts/system/dispatch_coding_agent_hf_job.py:_gate_score) so the
    standalone gate runner and the on-runner gate agree on what counts as
    a forbidden hit. Without this, "PASS" as a forbidden token would
    false-positive on words like "PASSAGE" or "compass" — fine for
    bare-substring contracts but wrong for the chemistry contract where
    forbidden tokens are meaningful tokens, not stems.
    """
    needle = str(term).strip().lower()
    if not needle:
        return False
    if _WORD_LIKE.fullmatch(needle):
        pattern_body = r"\s+".join(re.escape(part) for part in needle.split())
        pattern = r"(?<![a-z0-9_])" + pattern_body + r"(?![a-z0-9_])"
        return re.search(pattern, body_lower) is not None
    return needle in body_lower


def score_response(prompt: dict[str, Any], response: str) -> dict[str, Any]:
    """Score one response using deterministic required/forbidden checks.

    Required tokens use loose substring match (model may embed them
    anywhere). Forbidden tokens use word-boundary match for word-like
    terms (so "PASS" doesn't false-positive on "PASSAGE" or "compass").
    """

    body = response or ""
    body_lower = body.lower()
    missing_required = [
        str(token) for token in prompt.get("required", []) or [] if not _contains_token(body_lower, token)
    ]
    triggered_forbidden = [
        str(token) for token in prompt.get("forbidden", []) or [] if _contains_forbidden(body_lower, token)
    ]
    ok = (not missing_required) and (not triggered_forbidden)
    return {
        "ok": ok,
        "missing_required": missing_required,
        "triggered_forbidden": triggered_forbidden,
        "required_count": len(prompt.get("required", []) or []),
        "forbidden_count": len(prompt.get("forbidden", []) or []),
    }


def _load_prompts(contract: dict[str, Any]) -> list[dict[str, Any]]:
    prompts = contract.get("prompts") or []
    if not isinstance(prompts, list) or not prompts:
        raise ValueError("contract.prompts must be a non-empty list")
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for prompt in prompts:
        prompt_id = str(prompt.get("id") or "").strip()
        if not prompt_id:
            raise ValueError("each prompt must have an id")
        if prompt_id in seen:
            raise ValueError(f"duplicate prompt id: {prompt_id}")
        seen.add(prompt_id)
        normalized.append(
            {
                "id": prompt_id,
                "prompt": str(prompt.get("prompt", "")),
                "required": [str(token) for token in prompt.get("required", []) or []],
                "forbidden": [str(token) for token in prompt.get("forbidden", []) or []],
            }
        )
    return normalized


def _load_candidates(payload: dict[str, Any], prompt_ids: set[str]) -> list[dict[str, Any]]:
    candidates = payload.get("candidates") or []
    if not isinstance(candidates, list) or not candidates:
        raise ValueError("candidates must be a non-empty list")
    seen: set[str] = set()
    normalized: list[dict[str, Any]] = []
    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id") or "").strip()
        if not candidate_id:
            raise ValueError("each candidate must have a candidate_id")
        if candidate_id in seen:
            raise ValueError(f"duplicate candidate id: {candidate_id}")
        seen.add(candidate_id)
        responses = candidate.get("responses") or {}
        if not isinstance(responses, dict):
            raise ValueError(f"candidate {candidate_id} responses must be an object")
        missing = sorted(prompt_ids - set(map(str, responses)))
        if missing:
            raise ValueError(f"candidate {candidate_id} missing responses for prompts: {', '.join(missing)}")
        normalized.append(
            {
                "candidate_id": candidate_id,
                "metadata": candidate.get("metadata", {}),
                "responses": {prompt_id: str(responses[prompt_id]) for prompt_id in prompt_ids},
            }
        )
    return normalized


def _derive_seed(payload: dict[str, Any], contract: dict[str, Any], candidates: list[dict[str, Any]]) -> str:
    explicit = str(payload.get("seed") or "").strip()
    if explicit:
        return explicit
    seed_payload = {
        "contract": contract,
        "candidate_ids": sorted(candidate["candidate_id"] for candidate in candidates),
    }
    return _sha256(seed_payload)[:24]


def _build_blind_deck(
    *,
    prompts: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    seed: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    deck: list[dict[str, Any]] = []
    prompt_by_id = {prompt["id"]: prompt for prompt in prompts}
    for candidate in candidates:
        for prompt_id, response in candidate["responses"].items():
            deck.append(
                {
                    "candidate_id": candidate["candidate_id"],
                    "prompt_id": prompt_id,
                    "prompt": prompt_by_id[prompt_id],
                    "response": response,
                }
            )

    rng = random.Random(seed)
    rng.shuffle(deck)
    blinded: list[dict[str, Any]] = []
    mapping: list[dict[str, Any]] = []
    for index, row in enumerate(deck, 1):
        blind_digest = hashlib.sha256(f"{seed}|{index}|{row['prompt_id']}".encode("utf-8")).hexdigest()[:8]
        blind_id = f"seat_{index:04d}_{blind_digest}"
        blinded.append(
            {
                "blind_id": blind_id,
                "prompt_id": row["prompt_id"],
                "prompt": row["prompt"]["prompt"],
                "response": row["response"],
            }
        )
        mapping.append(
            {
                "blind_id": blind_id,
                "candidate_id": row["candidate_id"],
                "prompt_id": row["prompt_id"],
            }
        )
    return blinded, mapping


def _aggregate_by_candidate(
    *,
    scored_rows: list[dict[str, Any]],
    mapping: list[dict[str, Any]],
    thresholds: dict[str, Any],
) -> list[dict[str, Any]]:
    row_by_blind = {row["blind_id"]: row for row in scored_rows}
    by_candidate: dict[str, list[dict[str, Any]]] = {}
    for reveal in mapping:
        by_candidate.setdefault(reveal["candidate_id"], []).append(row_by_blind[reveal["blind_id"]])

    minimum_pass_rate = float(thresholds.get("minimum_pass_rate", 1.0))
    must_pass = {str(prompt_id) for prompt_id in thresholds.get("must_pass", []) or []}
    aggregates: list[dict[str, Any]] = []
    for candidate_id, rows in sorted(by_candidate.items()):
        n_total = len(rows)
        n_pass = sum(1 for row in rows if row["score"]["ok"])
        must_pass_results = {row["prompt_id"]: row["score"]["ok"] for row in rows if row["prompt_id"] in must_pass}
        must_pass_all_ok = all(must_pass_results.values()) if must_pass else True
        pass_rate = (n_pass / n_total) if n_total else 0.0
        overall_pass = pass_rate >= minimum_pass_rate and must_pass_all_ok
        aggregates.append(
            {
                "candidate_id": candidate_id,
                "n_total": n_total,
                "n_pass": n_pass,
                "pass_rate": round(pass_rate, 6),
                "minimum_pass_rate": minimum_pass_rate,
                "must_pass_results": must_pass_results,
                "must_pass_all_ok": must_pass_all_ok,
                "overall_pass": overall_pass,
            }
        )
    return aggregates


def build_double_blind_round(payload: dict[str, Any]) -> dict[str, Any]:
    """Build, score, and reveal a deterministic double-blind training round."""

    if payload.get("schema_version") not in {None, INPUT_SCHEMA_VERSION}:
        raise ValueError(f"unsupported schema_version: {payload.get('schema_version')}")
    contract = payload.get("contract") or {}
    prompts = _load_prompts(contract)
    prompt_by_id = {prompt["id"]: prompt for prompt in prompts}
    candidates = _load_candidates(payload, set(prompt_by_id))
    seed = _derive_seed(payload, contract, candidates)
    blind_rows, mapping = _build_blind_deck(prompts=prompts, candidates=candidates, seed=seed)

    mapping_commit_payload = {
        "seed": seed,
        "mapping": mapping,
    }
    mapping_commit_sha256 = _sha256(mapping_commit_payload)

    scored_rows: list[dict[str, Any]] = []
    for row in blind_rows:
        score = score_response(prompt_by_id[row["prompt_id"]], row["response"])
        scored_rows.append({**row, "score": score})

    thresholds = contract.get("thresholds") or {}
    candidate_results = _aggregate_by_candidate(scored_rows=scored_rows, mapping=mapping, thresholds=thresholds)
    reveal_sha256 = _sha256(mapping_commit_payload)
    commit_verified = reveal_sha256 == mapping_commit_sha256
    winners = sorted(
        candidate_results,
        key=lambda item: (item["overall_pass"], item["pass_rate"], item["n_pass"], item["candidate_id"]),
        reverse=True,
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": _utc_now(),
        "contract_id": contract.get("contract_id", "unnamed_contract"),
        "claim_boundary": (
            "Scores are deterministic checks over precomputed outputs. Candidate identity is hidden during scoring, "
            "then revealed through a commit-reveal mapping receipt."
        ),
        "seed": seed,
        "mapping_commit_sha256": mapping_commit_sha256,
        "score_stage_blind": True,
        "blind_row_count": len(scored_rows),
        "candidate_count": len(candidates),
        "blind_rows": scored_rows,
        "reveal": {
            "mapping": mapping,
            "mapping_reveal_sha256": reveal_sha256,
            "commit_verified": commit_verified,
            "candidate_metadata": {
                candidate["candidate_id"]: candidate.get("metadata", {}) for candidate in candidates
            },
        },
        "candidate_results": candidate_results,
        "winner_order": [candidate["candidate_id"] for candidate in winners],
    }


def write_report(report: dict[str, Any], out_path: Path = DEFAULT_OUT) -> Path:
    out_path = out_path if out_path.is_absolute() else (REPO_ROOT / out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=True) + "\n", encoding="utf-8")
    return out_path


def load_payload(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="JSON file containing contract and candidate outputs")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="report output path")
    parser.add_argument("--json", action="store_true", help="print full JSON report")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    report = build_double_blind_round(load_payload(args.input))
    out_path = write_report(report, args.out)
    if args.json:
        print(json.dumps({**report, "artifact_path": str(out_path)}, indent=2, sort_keys=True, ensure_ascii=True))
    else:
        passed = sum(1 for row in report["candidate_results"] if row["overall_pass"])
        print(
            f"double-blind training eval: candidates={report['candidate_count']} "
            f"blind_rows={report['blind_row_count']} passed={passed} wrote={out_path}"
        )
    return 0 if any(row["overall_pass"] for row in report["candidate_results"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
