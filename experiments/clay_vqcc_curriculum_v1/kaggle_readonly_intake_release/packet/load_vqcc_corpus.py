"""Fail-closed streaming sampler for Clay's private VQCC research corpus v2.

The loader intentionally keeps only the requested per-lane reservoirs in memory.
It verifies the pinned manifest and every consumed training shard before returning
any sample.  The command-line interface does not expose authority overrides.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


DATASET_ID = "issacizrealdavis/clay-vqcc-research-corpus"
DATASET_VERSION = 2
EXPECTED_SCHEMA = "clay.vqcc-research-corpus.v1"
EXPECTED_MANIFEST_SHA256 = "e4a9e7e9911fd8cdd8f858595a57b047402eb32a51571a54db580f4be87597c5"
EXPECTED_COUNTS = {"train": 621_731, "holdout": 48, "ordinary": 48, "retention": 48}
SAFE_NAME = re.compile(r"[A-Za-z0-9_.-]+\Z")
SHA256 = re.compile(r"[0-9a-f]{64}\Z")
RECORD_ID = re.compile(
    r"(?:"
    r"[0-9a-f]{64}"
    r"|(?:train|holdout|ordinary|retention)-[0-9]{3}-[0-9a-f]{8,64}"
    r"|(?:notebook|owned-analysis|experimental-method):[0-9a-f]{64}"
    r")\Z"
)
CAMPAIGN_OWNED_LANES = {"owned.experimental_method", "owned.public_notebook_observation"}
CAMPAIGN_ROLES = {"train", "holdout"}
SPECIAL_TOKEN_OVERHEAD = 3  # sequence start, prompt/target separator, sequence end


class CorpusIntegrityError(ValueError):
    """Raised when corpus identity, structure, or content differs from the pin."""


@dataclass(frozen=True)
class SampleConfig:
    """All bounds that determine a training sample."""

    lane_caps: Mapping[str, int]
    seed: int = 0
    max_chars_per_record: int = 4_096
    max_tokens_per_record: int = 1_024
    total_token_budget: int = 100_000
    campaign_role: str = "train"

    def validate(self) -> None:
        if not self.lane_caps:
            raise ValueError("At least one lane cap is required")
        for lane, cap in self.lane_caps.items():
            if not isinstance(lane, str) or not lane.strip() or type(cap) is not int or cap < 0:
                raise ValueError("Lane caps must map nonempty strings to nonnegative integers")
        if not any(self.lane_caps.values()):
            raise ValueError("At least one lane cap must be positive")
        for name, value in (
            ("max_chars_per_record", self.max_chars_per_record),
            ("max_tokens_per_record", self.max_tokens_per_record),
            ("total_token_budget", self.total_token_budget),
        ):
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        if type(self.seed) is not int:
            raise ValueError("seed must be an integer")
        if self.campaign_role not in CAMPAIGN_ROLES:
            raise ValueError(f"campaign_role must be one of {sorted(CAMPAIGN_ROLES)}")


@dataclass(frozen=True)
class SampleResult:
    """Bounded selected rows and their immutable receipt."""

    rows: tuple[dict[str, Any], ...]
    receipt: dict[str, Any]


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _file_sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _training_payload(row: Mapping[str, Any]) -> str:
    text = row.get("text", "")
    if isinstance(text, str) and text.strip():
        return text
    question, answer = row.get("question", ""), row.get("answer", "")
    if isinstance(question, str) and question.strip() and isinstance(answer, str) and answer.strip():
        return f"{question}\n{answer}"
    raise CorpusIntegrityError("Training row has neither text nor a question/answer pair")


def _token_proxy(payload: str) -> int:
    """Upper-bound Clay's byte/character input plus its three separators."""

    return len(payload.encode("utf-8")) + SPECIAL_TOKEN_OVERHEAD


def _validated_manifest(
    root: Path,
    *,
    expected_manifest_sha256: str = EXPECTED_MANIFEST_SHA256,
    expected_counts: Mapping[str, int] = EXPECTED_COUNTS,
) -> tuple[dict[str, Any], str]:
    root = root.resolve()
    path = root / "CORPUS_MANIFEST.json"
    if not path.is_file():
        raise FileNotFoundError(f"Pinned corpus manifest missing: {path}")
    raw = path.read_bytes()
    actual_sha256 = _sha256_bytes(raw)
    if actual_sha256 != expected_manifest_sha256:
        raise CorpusIntegrityError(
            f"Corpus manifest hash differs: expected {expected_manifest_sha256}, got {actual_sha256}"
        )
    try:
        manifest = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CorpusIntegrityError("Corpus manifest is not valid UTF-8 JSON") from exc
    if manifest.get("schema") != EXPECTED_SCHEMA:
        raise CorpusIntegrityError(f"Corpus schema differs: {manifest.get('schema')!r}")
    counts = manifest.get("counts")
    if not isinstance(counts, dict) or {name: counts.get(name) for name in expected_counts} != dict(expected_counts):
        raise CorpusIntegrityError(f"Corpus counts differ: {counts!r}")
    if any(manifest.get(name) != 0 for name in ("submission_archive_members", "official_competition_mounts", "model_checkpoints")):
        raise CorpusIntegrityError("Competition inputs, submissions, or model checkpoints entered the corpus")
    files = manifest.get("files")
    lanes = manifest.get("lanes")
    if not isinstance(files, dict) or not files or not isinstance(lanes, dict) or not lanes:
        raise CorpusIntegrityError("Manifest files or lanes are missing")
    for name, spec in files.items():
        if not isinstance(name, str) or not SAFE_NAME.fullmatch(name) or Path(name).name != name:
            raise CorpusIntegrityError(f"Unsafe manifest filename: {name!r}")
        if not isinstance(spec, dict):
            raise CorpusIntegrityError(f"Invalid file specification: {name}")
        size, digest = spec.get("bytes"), spec.get("sha256")
        if type(size) is not int or size < 0 or not isinstance(digest, str) or not SHA256.fullmatch(digest):
            raise CorpusIntegrityError(f"Invalid size or hash for {name}")
    return manifest, actual_sha256


def _validate_row(row: Any, *, file_name: str, line_number: int) -> tuple[str, str, str]:
    if not isinstance(row, dict):
        raise CorpusIntegrityError(f"Non-object row in {file_name}:{line_number}")
    if row.get("split") != "train":
        raise CorpusIntegrityError(f"Non-training row in {file_name}:{line_number}")
    record_id, lane, group = row.get("record_id"), row.get("lane"), row.get("split_group")
    if not isinstance(record_id, str) or not RECORD_ID.fullmatch(record_id):
        raise CorpusIntegrityError(f"Invalid record_id in {file_name}:{line_number}")
    if not isinstance(lane, str) or not lane.strip() or not isinstance(group, str) or not group.strip():
        raise CorpusIntegrityError(f"Missing lane or split_group in {file_name}:{line_number}")
    return record_id, lane, group


def _is_campaign_row(row: Mapping[str, Any]) -> bool:
    lane = str(row.get("lane", ""))
    return lane.startswith("public.") or lane in CAMPAIGN_OWNED_LANES


class _AssignmentCursor:
    """Lockstep, constant-memory join against the split builder's row sidecar."""

    def __init__(self, path: Path, expected_sha256: str) -> None:
        if not SHA256.fullmatch(expected_sha256):
            raise ValueError("Expected assignment SHA-256 must be 64 lowercase hexadecimal characters")
        if not path.is_file():
            raise FileNotFoundError(f"Campaign row-assignment sidecar missing: {path}")
        self.path = path
        self.expected_sha256 = expected_sha256
        self.stream = path.open("rb")
        self.digest = hashlib.sha256()
        self.line_number = 0
        self.previous_record_id: str | None = None
        self.role_counts: Counter[str] = Counter()

    def _next_assignment(self) -> dict[str, Any] | None:
        raw = self.stream.readline()
        if not raw:
            return None
        self.line_number += 1
        self.digest.update(raw)
        try:
            assignment = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise CorpusIntegrityError(
                f"Invalid campaign assignment JSON in {self.path.name}:{self.line_number}"
            ) from exc
        if not isinstance(assignment, dict):
            raise CorpusIntegrityError(f"Non-object campaign assignment in {self.path.name}:{self.line_number}")
        record_id = assignment.get("record_id")
        role = assignment.get("split")
        lane = assignment.get("lane")
        family = assignment.get("family")
        if not isinstance(record_id, str) or not RECORD_ID.fullmatch(record_id):
            raise CorpusIntegrityError(f"Invalid assignment record_id in {self.path.name}:{self.line_number}")
        if record_id == self.previous_record_id:
            raise CorpusIntegrityError(f"Duplicate campaign assignment for {record_id}")
        if role not in CAMPAIGN_ROLES:
            raise CorpusIntegrityError(f"Invalid campaign role in {self.path.name}:{self.line_number}")
        if not isinstance(lane, str) or not lane or not isinstance(family, str) or not family:
            raise CorpusIntegrityError(f"Assignment lacks lane or family in {self.path.name}:{self.line_number}")
        self.previous_record_id = record_id
        self.role_counts[role] += 1
        return assignment

    def match(self, *, record_id: str, lane: str) -> dict[str, Any]:
        assignment = self._next_assignment()
        if assignment is None:
            raise CorpusIntegrityError(f"Campaign assignment missing for corpus row {record_id}")
        assigned_id = str(assignment["record_id"])
        if assigned_id != record_id:
            raise CorpusIntegrityError(
                "Campaign assignments are missing, extra, duplicated, or out of corpus order: "
                f"expected {record_id}, got {assigned_id}"
            )
        if assignment["lane"] != lane:
            raise CorpusIntegrityError(f"Campaign assignment lane differs for {record_id}")
        return assignment

    def finish(self) -> None:
        extra = self._next_assignment()
        if extra is not None:
            raise CorpusIntegrityError(f"Campaign assignment has no matching corpus row: {extra['record_id']}")
        actual_sha256 = self.digest.hexdigest()
        if actual_sha256 != self.expected_sha256:
            raise CorpusIntegrityError(
                f"Campaign assignment hash differs: expected {self.expected_sha256}, got {actual_sha256}"
            )

    def close(self) -> None:
        self.stream.close()


def _lane_rng(seed: int, lane: str) -> random.Random:
    material = hashlib.sha256(f"clay-vqcc-reservoir-v1\0{seed}\0{lane}".encode()).digest()
    return random.Random(int.from_bytes(material, "big"))


def _budget_priority(seed: int, record_id: str) -> bytes:
    return hashlib.sha256(f"clay-vqcc-budget-v1\0{seed}\0{record_id}".encode()).digest()


def sample_corpus(
    root: str | Path,
    config: SampleConfig,
    *,
    assignments_path: str | Path,
    expected_assignments_sha256: str,
    expected_manifest_sha256: str = EXPECTED_MANIFEST_SHA256,
    expected_counts: Mapping[str, int] = EXPECTED_COUNTS,
) -> SampleResult:
    """Stream and verify all train shards, retaining only bounded lane reservoirs.

    Authority overrides exist only for hermetic tests.  The CLI always uses the
    production constants above.
    """

    config.validate()
    corpus_root = Path(root).resolve()
    manifest, manifest_sha256 = _validated_manifest(
        corpus_root,
        expected_manifest_sha256=expected_manifest_sha256,
        expected_counts=expected_counts,
    )
    declared_lanes = manifest["lanes"]
    unknown_lanes = sorted(set(config.lane_caps) - set(declared_lanes))
    if unknown_lanes:
        raise ValueError(f"Requested lanes are absent from the pinned manifest: {unknown_lanes}")

    train_specs = [
        (name, spec)
        for name, spec in sorted(manifest["files"].items())
        if name.startswith("train-") and name.endswith(".jsonl")
    ]
    if not train_specs:
        raise CorpusIntegrityError("Pinned manifest declares no train JSONL shards")

    wanted = {lane: cap for lane, cap in config.lane_caps.items() if cap}
    reservoirs: dict[str, list[tuple[dict[str, Any], int]]] = {lane: [] for lane in wanted}
    seen_eligible = dict.fromkeys(wanted, 0)
    rngs = {lane: _lane_rng(config.seed, lane) for lane in wanted}
    scanned_by_lane: Counter[str] = Counter()
    eligible_by_lane: Counter[str] = Counter()
    excluded_chars: Counter[str] = Counter()
    excluded_tokens: Counter[str] = Counter()
    scanned_rows = 0
    assignments = _AssignmentCursor(Path(assignments_path).resolve(), expected_assignments_sha256)
    try:
        for file_name, spec in train_specs:
            path = corpus_root / file_name
            if not path.is_file():
                raise FileNotFoundError(f"Pinned training shard missing: {path}")
            if path.stat().st_size != spec["bytes"]:
                raise CorpusIntegrityError(f"Training shard size differs: {file_name}")
            digest = hashlib.sha256()
            line_count = 0
            with path.open("rb") as stream:
                for line_count, raw_line in enumerate(stream, 1):
                    digest.update(raw_line)
                    try:
                        row = json.loads(raw_line)
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        raise CorpusIntegrityError(f"Invalid JSON row in {file_name}:{line_count}") from exc
                    record_id, lane, _group = _validate_row(row, file_name=file_name, line_number=line_count)
                    scanned_rows += 1
                    scanned_by_lane[lane] += 1
                    if not _is_campaign_row(row):
                        continue
                    assignment = assignments.match(record_id=record_id, lane=lane)
                    if assignment["split"] != config.campaign_role or lane not in wanted:
                        continue
                    payload = _training_payload(row)
                    if len(payload) > config.max_chars_per_record:
                        excluded_chars[lane] += 1
                        continue
                    token_proxy = _token_proxy(payload)
                    if token_proxy > config.max_tokens_per_record:
                        excluded_tokens[lane] += 1
                        continue
                    eligible_by_lane[lane] += 1
                    seen_eligible[lane] += 1
                    picked = reservoirs[lane]
                    cap = wanted[lane]
                    candidate = (row, token_proxy)
                    if len(picked) < cap:
                        picked.append(candidate)
                    else:
                        slot = rngs[lane].randrange(seen_eligible[lane])
                        if slot < cap:
                            picked[slot] = candidate
            if digest.hexdigest() != spec["sha256"]:
                raise CorpusIntegrityError(f"Training shard hash differs: {file_name}")
            if line_count == 0:
                raise CorpusIntegrityError(f"Training shard is empty: {file_name}")
        assignments.finish()
        assignment_role_counts = dict(sorted(assignments.role_counts.items()))
    finally:
        assignments.close()

    if scanned_rows != expected_counts["train"]:
        raise CorpusIntegrityError(
            f"Training row count differs: expected {expected_counts['train']}, got {scanned_rows}"
        )
    empty_lanes = sorted(lane for lane in wanted if not seen_eligible[lane])
    if empty_lanes:
        raise ValueError(f"No eligible training rows for requested lanes: {empty_lanes}")

    # Reserve the shortest deterministic candidate in every requested lane first.
    # This prevents the global budget order from silently erasing a lane.
    required: list[tuple[dict[str, Any], int]] = []
    remaining: list[tuple[dict[str, Any], int]] = []
    for lane in sorted(reservoirs):
        ordered = sorted(
            reservoirs[lane],
            key=lambda item: (item[1], _budget_priority(config.seed, item[0]["record_id"])),
        )
        required.append(ordered[0])
        remaining.extend(ordered[1:])
    required_tokens = sum(tokens for _row, tokens in required)
    if required_tokens > config.total_token_budget:
        raise ValueError(
            "Total token budget cannot retain one row per requested positive lane: "
            f"need at least {required_tokens}, have {config.total_token_budget}"
        )
    remaining.sort(key=lambda item: _budget_priority(config.seed, item[0]["record_id"]))
    selected: list[tuple[dict[str, Any], int]] = list(required)
    selected_tokens = required_tokens
    dropped_by_budget: Counter[str] = Counter()
    for row, tokens in remaining:
        if selected_tokens + tokens <= config.total_token_budget:
            selected.append((row, tokens))
            selected_tokens += tokens
        else:
            dropped_by_budget[row["lane"]] += 1
    selected.sort(key=lambda item: _budget_priority(config.seed, item[0]["record_id"]))

    rows = tuple(row for row, _tokens in selected)
    record_ids = [row["record_id"] for row in rows]
    if len(record_ids) != len(set(record_ids)):
        raise CorpusIntegrityError("Selected sample contains repeated record IDs")
    rows_bytes = b"".join(_canonical_json(row) + b"\n" for row in rows)
    selected_by_lane = Counter(row["lane"] for row in rows)
    receipt = {
        "schema": "clay.vqcc-stream-sample.v1",
        "dataset": {"id": DATASET_ID, "version": DATASET_VERSION, "manifest_sha256": manifest_sha256},
        "campaign_assignments": {
            "file": Path(assignments_path).name,
            "sha256": expected_assignments_sha256,
            "roles": assignment_role_counts,
            "selected_role": config.campaign_role,
        },
        "config": {
            "lane_caps": dict(sorted(config.lane_caps.items())),
            "seed": config.seed,
            "max_chars_per_record": config.max_chars_per_record,
            "max_tokens_per_record": config.max_tokens_per_record,
            "total_token_budget": config.total_token_budget,
            "token_proxy": f"utf8_bytes_plus_{SPECIAL_TOKEN_OVERHEAD}_special_tokens",
            "campaign_role": config.campaign_role,
        },
        "scan": {
            "train_shards": len(train_specs),
            "train_rows": scanned_rows,
            "scanned_by_lane": dict(sorted(scanned_by_lane.items())),
            "eligible_by_lane": dict(sorted(eligible_by_lane.items())),
            "excluded_by_character_cap": dict(sorted(excluded_chars.items())),
            "excluded_by_token_cap": dict(sorted(excluded_tokens.items())),
        },
        "selection": {
            "rows": len(rows),
            "token_proxy_total": selected_tokens,
            "selected_by_lane": dict(sorted(selected_by_lane.items())),
            "dropped_by_total_token_budget": dict(sorted(dropped_by_budget.items())),
            "record_ids": record_ids,
            "record_ids_sha256": _sha256_bytes(("\n".join(record_ids) + "\n").encode()),
            "sample_sha256": _sha256_bytes(rows_bytes),
            "sample_bytes": len(rows_bytes),
        },
    }
    return SampleResult(rows=rows, receipt=receipt)


def write_sample(result: SampleResult, rows_path: str | Path, receipt_path: str | Path) -> None:
    """Write a sample exactly once; existing targets are never overwritten."""

    rows_path, receipt_path = Path(rows_path), Path(receipt_path)
    if rows_path.resolve() == receipt_path.resolve():
        raise ValueError("Rows and receipt paths must differ")
    existing = [str(path) for path in (rows_path, receipt_path) if path.exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite immutable output: {existing}")
    rows_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    rows_bytes = b"".join(_canonical_json(row) + b"\n" for row in result.rows)
    if _sha256_bytes(rows_bytes) != result.receipt["selection"]["sample_sha256"]:
        raise CorpusIntegrityError("In-memory rows differ from the sealed sample hash")
    with rows_path.open("xb") as stream:
        stream.write(rows_bytes)
    try:
        with receipt_path.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(result.receipt, stream, ensure_ascii=False, indent=2, sort_keys=True)
            stream.write("\n")
    except BaseException:
        rows_path.unlink(missing_ok=True)
        raise


def _parse_lane_cap(raw: str) -> tuple[str, int]:
    if "=" not in raw:
        raise argparse.ArgumentTypeError("lane cap must have the form LANE=COUNT")
    lane, count = raw.rsplit("=", 1)
    try:
        value = int(count)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("lane cap count must be an integer") from exc
    if not lane or value < 0:
        raise argparse.ArgumentTypeError("lane cap needs a nonempty lane and nonnegative count")
    return lane, value


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus_root", type=Path)
    parser.add_argument("--lane-cap", action="append", required=True, type=_parse_lane_cap, metavar="LANE=COUNT")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-chars-per-record", type=int, default=4_096)
    parser.add_argument("--max-tokens-per-record", type=int, default=1_024)
    parser.add_argument("--total-token-budget", type=int, default=100_000)
    parser.add_argument("--assignments", type=Path, required=True)
    parser.add_argument("--assignments-sha256", required=True)
    parser.add_argument("--campaign-role", choices=sorted(CAMPAIGN_ROLES), default="train")
    parser.add_argument("--rows-output", type=Path, required=True)
    parser.add_argument("--receipt-output", type=Path, required=True)
    args = parser.parse_args(argv)
    lane_caps = dict(args.lane_cap)
    if len(lane_caps) != len(args.lane_cap):
        parser.error("each lane may be specified only once")
    result = sample_corpus(
        args.corpus_root,
        SampleConfig(
            lane_caps=lane_caps,
            seed=args.seed,
            max_chars_per_record=args.max_chars_per_record,
            max_tokens_per_record=args.max_tokens_per_record,
            total_token_budget=args.total_token_budget,
            campaign_role=args.campaign_role,
        ),
        assignments_path=args.assignments,
        expected_assignments_sha256=args.assignments_sha256,
    )
    write_sample(result, args.rows_output, args.receipt_output)
    print(json.dumps(result.receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
