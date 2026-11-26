"""Deterministic one-command-to-workflow curriculum for Clay's bounded tools.

The curriculum is intentionally finite and side-effect free. It teaches the
canonical command grammar first, then ordered pairs and short workflows. Tool
execution is a separate sandbox concern; these records only supervise routing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from clay_bijective_router import (
    DEFAULT_HOLDOUT,
    DEFAULT_TRAIN,
    HANDLERS,
    ToolCall,
    compact_tools_payload,
    format_tool_call,
    load_rows,
    parse_tool_call,
    verify_tool_call,
)


SCHEMA = "clay.tool-sequence-curriculum.v1"
HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = HERE / "clay_tool_sequence_curriculum.jsonl"
DEFAULT_REPORT = HERE / "clay_tool_sequence_curriculum_report.json"
DEFAULT_MCP_SLASH_REGISTRY = HERE / "clay_mcp_slash_registry.json"

PROMPT_PREFIXES = (
    "",
    "Clay, ",
    "Route this request: ",
    "Use the bounded tool grammar: ",
)

WORKFLOW_PREFIXES = (
    "",
    "Clay, ",
    "In order, ",
    "Follow this sequence: ",
    "Route each step: ",
    "Use the exact tool order: ",
)

HOLDOUT_SINGLE_SPECS: dict[str, tuple[tuple[str, str], ...]] = {
    "tools": (
        ("Show the complete Clay tool list.", "tools ::"),
        ("Which bounded handlers are available?", "tools ::"),
        ("Inventory the tools before acting.", "tools ::"),
    ),
    "sieve": (
        ("List primes through 173.", "sieve :: 173"),
        ("Run the prime sieve with upper bound 211.", "sieve :: 211"),
        ("Find every prime no greater than 257.", "sieve :: 257"),
    ),
    "web": (
        (
            "Research finite mathematics requirements.",
            "web :: finite mathematics requirements",
        ),
        (
            "Open https://example.com/reference",
            "web :: fetch https://example.com/reference",
        ),
        ("Look up deterministic tool routing.", "web :: deterministic tool routing"),
    ),
    "remember": (
        ("Resume the saved Clay state.", "remember :: resume"),
        ("Recall the tool gateway notes.", "remember :: recall tool gateway"),
        (
            "Save a note that the fixed fallback stays frozen.",
            "remember :: note fixed fallback stays frozen",
        ),
    ),
    "read": (
        ("Read clay_tools.py.", "read :: clay_tools.py"),
        (
            "Find HANDLERS in clay_bijective_router.py.",
            "read :: clay_bijective_router.py --find HANDLERS",
        ),
        ("Inspect clay_cli.py for solve.", "read :: clay_cli.py --find solve"),
    ),
    "solve": (
        ("Solve binding_compose.json.", "solve :: binding_compose.json"),
        (
            "Run the task in clay_apollonian_pairs.jsonl.",
            "solve :: clay_apollonian_pairs.jsonl",
        ),
        ("Solve browser_policy_sft.jsonl.", "solve :: browser_policy_sft.jsonl"),
    ),
    "accuplacer": (
        ("Show the placement study plan.", "accuplacer :: plan"),
        ("Give one quantitative reasoning question.", "accuplacer :: question qas"),
        ("Report placement practice status.", "accuplacer :: status"),
    ),
    "email": (
        ("Check the safe mailbox status.", "email :: mailbox-status"),
        ("Show the email style hints.", "email :: style-hints"),
        (
            "Build a cleanup plan for inbox.json.",
            "email :: cleanup-plan inbox.json --out cleanup.json",
        ),
    ),
    "localapi": (
        ("List local API surfaces.", "localapi :: list"),
        ("Check the local Ollama process list.", "localapi :: ollama ps"),
        (
            "Read the loopback health endpoint.",
            "localapi :: get http://127.0.0.1:8000/health",
        ),
    ),
    "ferro": (
        ("Form a governed ferro ring.", "ferro :: ring"),
        ("Place one spike at the center.", "ferro :: spike center"),
        ("Render the AI ferro glyph.", "ferro :: spell AI"),
    ),
}

TRAIN_WORKFLOWS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "research_note",
        "Research opcode routing and preserve a concise note.",
        ("web :: opcode routing", "remember :: note opcode routing research"),
    ),
    (
        "inspect_solve",
        "Inspect the solver entry point, then solve a local task.",
        ("read :: clay_cli.py --find solve", "solve :: binding_compose.json"),
    ),
    (
        "placement_ladder",
        "Check placement status, inspect the plan, then ask an arithmetic question.",
        (
            "accuplacer :: status",
            "accuplacer :: plan",
            "accuplacer :: question arithmetic",
        ),
    ),
    (
        "local_health",
        "Inventory local APIs and then check Ollama tags and processes.",
        (
            "localapi :: list",
            "localapi :: ollama tags",
            "localapi :: ollama ps",
        ),
    ),
    (
        "mail_review",
        "Inspect safe mailbox metadata before deriving style hints.",
        (
            "email :: mailbox-status",
            "email :: training-status",
            "email :: style-hints",
        ),
    ),
    (
        "ferro_shapes",
        "Render a ring, center spike, and twin spikes in that order.",
        ("ferro :: ring", "ferro :: spike center", "ferro :: two spikes"),
    ),
    (
        "inventory_read",
        "List the tools and inspect their implementation.",
        ("tools ::", "read :: clay_tools.py"),
    ),
    (
        "prime_note",
        "Sieve through 97 and preserve the result context.",
        ("sieve :: 97", "remember :: note primes through 97"),
    ),
)

HOLDOUT_WORKFLOWS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "research_recall",
        "Look up triadic routing, then recall the saved gateway context.",
        ("web :: triadic routing", "remember :: recall gateway context"),
    ),
    (
        "inspect_then_solve",
        "Read the bounded router before solving the composition fixture.",
        (
            "read :: clay_bijective_router.py --find payload_is_valid",
            "solve :: binding_compose.json",
        ),
    ),
    (
        "placement_sequence",
        "Start placement practice, get the plan, then request an advanced question.",
        (
            "accuplacer :: start",
            "accuplacer :: plan",
            "accuplacer :: question advanced",
        ),
    ),
    (
        "local_sequence",
        "Inventory local services, check Ollama version, then read loopback health.",
        (
            "localapi :: list",
            "localapi :: ollama version",
            "localapi :: get http://localhost:8000/health",
        ),
    ),
    (
        "ferro_sequence",
        "Draw a circle, a bar, and the HK glyph in order.",
        ("ferro :: circle", "ferro :: bar", "ferro :: spell HK"),
    ),
)


@dataclass(frozen=True)
class SequenceRecord:
    record_id: str
    split: str
    stage: int
    request: str
    calls: tuple[str, ...]
    source: str

    @property
    def prompt(self) -> str:
        # Reuse markers already present in Clay's retained tokenizer instead of
        # spending the 128-token context on a new verbose envelope.
        if self.source == "registered_mcp_and_slash_envelopes":
            return f"[STOP] {self.request}\ntape="
        return f"[STOP] request={self.request}\ntarget_tool_tape="

    @property
    def answer(self) -> str:
        calls = "\n".join(self.calls)
        return f"\n[TAPE]\n{calls}\n[/TAPE]\n[/STOP]"

    @property
    def text(self) -> str:
        return self.prompt + self.answer

    def to_json(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "calls": list(self.calls),
            "prompt": self.prompt,
            "answer": self.answer,
            "text": self.text,
        }


def _digest(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8")).hexdigest()


def _canonical(line: str) -> str:
    call = parse_tool_call(line)
    canonical = format_tool_call(call)
    verification = verify_tool_call(canonical)
    if not verification["valid"]:
        raise ValueError(f"invalid curriculum call {line!r}: {verification}")
    return canonical


def _balanced_singles(
    path: Path,
    *,
    per_tool: int,
) -> list[SequenceRecord]:
    grouped: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for request, target in load_rows(path):
        canonical = _canonical(target)
        grouped[parse_tool_call(canonical).tool].append((request, canonical))
    missing = sorted(set(HANDLERS) - set(grouped))
    if missing:
        raise ValueError(f"single-call source is missing tools: {missing}")

    records: list[SequenceRecord] = []
    for tool in HANDLERS:
        rows = sorted(grouped[tool], key=lambda row: _digest(*row))
        for index in range(per_tool):
            request, target = rows[index % len(rows)]
            cycle = index // len(rows)
            prefix = PROMPT_PREFIXES[cycle % len(PROMPT_PREFIXES)]
            suffix = "" if cycle < len(PROMPT_PREFIXES) else f" [practice {cycle + 1}]"
            routed_request = f"{prefix}{request}{suffix}"
            records.append(
                SequenceRecord(
                    record_id=f"train:single:{tool}:{index:03d}",
                    split="train",
                    stage=1,
                    request=routed_request,
                    calls=(target,),
                    source="balanced_existing_tool_rows",
                )
            )
    return records


def _evaluation_singles() -> list[SequenceRecord]:
    records = []
    for tool in HANDLERS:
        specs = HOLDOUT_SINGLE_SPECS[tool]
        for index, (request, target) in enumerate(specs):
            split = "validation" if index < 2 else "test"
            records.append(
                SequenceRecord(
                    record_id=f"{split}:single:{tool}:{index:03d}",
                    split=split,
                    stage=1,
                    request=request,
                    calls=(_canonical(target),),
                    source=f"curated_disjoint_tool_{split}",
                )
            )
    return records


def _workflow_records(
    specs: Sequence[tuple[str, str, tuple[str, ...]]],
    *,
    split: str,
    variants: int = 1,
) -> list[SequenceRecord]:
    records = []
    for name, request, calls in specs:
        canonical = tuple(_canonical(call) for call in calls)
        for variant in range(variants):
            prefix = WORKFLOW_PREFIXES[variant % len(WORKFLOW_PREFIXES)]
            records.append(
                SequenceRecord(
                    record_id=f"{split}:workflow:{name}:{variant:02d}",
                    split=split,
                    stage=min(4, len(canonical)),
                    request=f"{prefix}{request}",
                    calls=canonical,
                    source="curated_ordered_workflow",
                )
            )
    return records


def _mcp_slash_records(registry_path: Path) -> list[SequenceRecord]:
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    if registry.get("schema") != "clay.mcp-slash-registry.v1":
        raise ValueError(f"unsupported MCP/slash registry: {registry_path}")
    specs = registry.get("records")
    if not isinstance(specs, list) or not specs:
        raise ValueError("MCP/slash registry has no records")

    records: list[SequenceRecord] = []
    registry_calls: dict[str, set[str]] = defaultdict(set)
    for spec in specs:
        split = spec.get("split")
        if split not in {"train", "validation", "test"}:
            raise ValueError(f"invalid MCP/slash split: {split!r}")
        calls = []
        for line in spec.get("calls", ()):
            canonical = _canonical(str(line))
            call = parse_tool_call(canonical)
            if call.tool != "tools" or not call.payload:
                raise ValueError("MCP/slash registry calls must use tools payloads")
            compact = format_tool_call(
                ToolCall("tools", compact_tools_payload(call.payload))
            )
            calls.append(_canonical(compact))
        calls = tuple(calls)
        stage = int(spec.get("stage", 0))
        if not calls or len(calls) > 3 or stage != len(calls):
            raise ValueError(
                f"MCP/slash record {spec.get('id')!r} must have 1-3 calls "
                "and stage must equal call count"
            )
        variants = int(spec.get("variants", 1))
        if variants != 1 and split != "train":
            raise ValueError("only training MCP/slash records may have variants")
        if not 1 <= variants <= len(PROMPT_PREFIXES) + 2:
            raise ValueError("MCP/slash variants must be in [1, 6]")
        record_name = str(spec.get("id", "")).strip()
        request = str(spec.get("request", "")).strip()
        if not record_name or not request:
            raise ValueError("MCP/slash records require id and request")
        registry_calls[split].update(calls)
        for variant in range(variants):
            prefix = (
                PROMPT_PREFIXES[variant % len(PROMPT_PREFIXES)]
                if split == "train"
                else ""
            )
            suffix = (
                f" [route practice {variant + 1}]"
                if variant >= len(PROMPT_PREFIXES)
                else ""
            )
            records.append(
                SequenceRecord(
                    record_id=(
                        f"{split}:mcp-slash:{record_name}:{variant:02d}"
                    ),
                    split=split,
                    stage=stage,
                    request=f"{prefix}{request}{suffix}",
                    calls=calls,
                    source="registered_mcp_and_slash_envelopes",
                )
            )

    for left, right in (("train", "validation"), ("train", "test"), ("validation", "test")):
        overlap = registry_calls[left] & registry_calls[right]
        if overlap:
            raise ValueError(
                f"MCP/slash target leakage between {left} and {right}: "
                f"{sorted(overlap)}"
            )
    return records


def build_curriculum(
    train_path: Path = DEFAULT_TRAIN,
    *,
    singles_per_tool: int = 192,
    mcp_slash_registry: Path = DEFAULT_MCP_SLASH_REGISTRY,
) -> list[SequenceRecord]:
    if singles_per_tool < 1:
        raise ValueError("singles_per_tool must be positive")
    records = _balanced_singles(train_path, per_tool=singles_per_tool)
    records.extend(_workflow_records(TRAIN_WORKFLOWS, split="train", variants=6))
    records.extend(_evaluation_singles())
    records.extend(_workflow_records(HOLDOUT_WORKFLOWS[:3], split="validation"))
    records.extend(_workflow_records(HOLDOUT_WORKFLOWS[3:], split="test"))
    records.extend(_mcp_slash_records(mcp_slash_registry))
    ids = [record.record_id for record in records]
    if len(ids) != len(set(ids)):
        raise ValueError("curriculum record IDs are not unique")
    return records


CALL_PATTERN = re.compile(r"\[CALL\](.*?)\[/CALL\]", re.DOTALL)
TAPE_PATTERN = re.compile(r"\[TAPE\](.*?)\[/TAPE\]", re.DOTALL)


def parse_call_tape(text: str) -> list[str]:
    legacy = [match.strip() for match in CALL_PATTERN.findall(text)]
    if legacy:
        return legacy
    tape = TAPE_PATTERN.search(text)
    if not tape:
        return []
    return [line.strip() for line in tape.group(1).splitlines() if line.strip()]


def _multiplier(combo: int) -> int:
    if combo >= 30:
        return 4
    if combo >= 20:
        return 3
    if combo >= 10:
        return 2
    return 1


def score_predictions(
    records: Sequence[SequenceRecord],
    predictions: dict[str, str],
) -> dict[str, Any]:
    exact_calls = tool_hits = payload_hits = valid_calls = 0
    expected_total = predicted_total = exact_sequences = 0
    score = combo = max_combo = 0
    rows = []
    for record in sorted(records, key=lambda item: item.record_id):
        expected = list(record.calls)
        predicted = parse_call_tape(predictions.get(record.record_id, ""))
        expected_total += len(expected)
        predicted_total += len(predicted)
        sequence_exact = predicted == expected
        exact_sequences += int(sequence_exact)
        position_rows = []
        for index in range(max(len(expected), len(predicted))):
            expected_line = expected[index] if index < len(expected) else None
            predicted_line = predicted[index] if index < len(predicted) else None
            exact = expected_line is not None and predicted_line == expected_line
            expected_call = parse_tool_call(expected_line) if expected_line else None
            predicted_call = None
            valid = False
            if predicted_line is not None:
                verification = verify_tool_call(predicted_line)
                valid = bool(verification["valid"])
                if valid:
                    predicted_call = parse_tool_call(verification["canonical"])
                    valid_calls += 1
            tool_hit = bool(
                expected_call
                and predicted_call
                and expected_call.tool == predicted_call.tool
            )
            payload_hit = bool(
                tool_hit and expected_call.payload == predicted_call.payload
            )
            exact_calls += int(exact)
            tool_hits += int(tool_hit)
            payload_hits += int(payload_hit)
            if exact:
                combo += 1
                max_combo = max(max_combo, combo)
                score += 100 * _multiplier(combo)
            else:
                combo = 0
            position_rows.append(
                {
                    "index": index,
                    "expected": expected_line,
                    "predicted": predicted_line,
                    "valid": valid,
                    "tool_hit": tool_hit,
                    "payload_hit": payload_hit,
                    "exact": exact,
                }
            )
        rows.append(
            {
                "record_id": record.record_id,
                "stage": record.stage,
                "sequence_exact": sequence_exact,
                "positions": position_rows,
            }
        )
    sequence_count = len(records)
    accuracy = exact_calls / expected_total if expected_total else 0.0
    stars = (
        5
        if accuracy >= 0.95
        else 4
        if accuracy >= 0.85
        else 3
        if accuracy >= 0.70
        else 2
        if accuracy >= 0.50
        else 1
    )
    return {
        "schema": "clay.tool-sequence-score.v1",
        "records": sequence_count,
        "expected_calls": expected_total,
        "predicted_calls": predicted_total,
        "exact_call_accuracy": accuracy,
        "tool_position_accuracy": tool_hits / expected_total if expected_total else 0.0,
        "payload_position_accuracy": payload_hits / expected_total
        if expected_total
        else 0.0,
        "valid_predicted_rate": valid_calls / predicted_total
        if predicted_total
        else 0.0,
        "sequence_exact_rate": exact_sequences / sequence_count
        if sequence_count
        else 0.0,
        "guitar_score": score,
        "max_combo": max_combo,
        "stars": stars,
        "details": rows,
    }


def cross_section_slot(value: int) -> int | None:
    """Map nonzero bytes to 255 active phase slots; zero is fixed fallback."""
    if not 0 <= value <= 255:
        raise ValueError("byte value must be in [0, 255]")
    return None if value == 0 else value - 1


def cross_section_phase(value: int) -> float:
    slot = cross_section_slot(value)
    return 0.0 if slot is None else math.tau * slot / 255.0


def triadic_neighbors(value: int) -> tuple[int, int, int]:
    """Return left-edge, anchored-node, right-edge values on the 255 ring."""
    if value == 0:
        return (0, 0, 0)
    cross_section_slot(value)
    left = 255 if value == 1 else value - 1
    right = 1 if value == 255 else value + 1
    return left, value, right


def silent_face(data: bytes) -> dict[str, Any]:
    recovered = bytes(data)
    slots = [cross_section_slot(value) for value in data]
    return {
        "encoding": "nonzero-byte-cross-section-255",
        "bytes_hex": data.hex(),
        "sha256": hashlib.sha256(data).hexdigest(),
        "active_slots": [slot for slot in slots if slot is not None],
        "fallback_zero_count": sum(slot is None for slot in slots),
        "round_trip": recovered == data,
    }


def droid_route(
    line: str, *, mode: str = "and", mood: str = "neutral"
) -> dict[str, Any]:
    """Seal one canonical call through silent and/or audible Droid faces."""
    canonical = _canonical(line)
    data = canonical.encode("utf-8")
    silent = silent_face(data)
    audible: dict[str, Any] | None = None
    if mode in {"audible", "and", "or"}:
        import droid_voice  # noqa: F401 - installs the existing C:\dev codec path
        import astromech

        signal = astromech.encode(data, mood)
        recovered = astromech.decode(signal)
        audible = {
            "codec": "astromech-fsk",
            "mood": mood,
            "sample_rate": int(astromech.SR),
            "samples": int(len(signal)),
            "round_trip": recovered == data,
            "decoded_sha256": hashlib.sha256(recovered).hexdigest(),
        }
    if mode == "silent":
        accepted = silent["round_trip"]
    elif mode == "audible":
        accepted = bool(audible and audible["round_trip"])
    elif mode == "and":
        accepted = bool(silent["round_trip"] and audible and audible["round_trip"])
    elif mode == "or":
        accepted = bool(silent["round_trip"] or (audible and audible["round_trip"]))
    else:
        raise ValueError("mode must be silent, audible, and, or or")
    return {
        "schema": "clay.droid-tool-route.v1",
        "canonical": canonical,
        "mode": mode,
        "silent": silent,
        "audible": audible,
        "accepted": accepted,
    }


def droid_cross255_smoke(
    *,
    moods: Sequence[str] = ("neutral",),
) -> dict[str, Any]:
    """Round-trip every active cross-section byte through both route faces."""
    payload = bytes(range(1, 256))
    silent = silent_face(payload)
    import droid_voice  # noqa: F401 - installs the existing C:\dev codec path
    import astromech

    audible = []
    for mood in moods:
        signal = astromech.encode(payload, mood)
        recovered = astromech.decode(signal)
        audible.append(
            {
                "mood": mood,
                "samples": int(len(signal)),
                "sample_rate": int(astromech.SR),
                "round_trip": recovered == payload,
                "decoded_sha256": hashlib.sha256(recovered).hexdigest(),
            }
        )
    return {
        "schema": "clay.droid-cross255-smoke.v1",
        "active_slots": 255,
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "silent_round_trip": silent["round_trip"],
        "audible": audible,
        "and_accepted": bool(
            silent["round_trip"] and all(row["round_trip"] for row in audible)
        ),
        "or_accepted": bool(
            silent["round_trip"] or any(row["round_trip"] for row in audible)
        ),
    }


def bounded_grammar_inventory(
    paths: Iterable[Path],
    records: Sequence[SequenceRecord] = (),
) -> list[str]:
    """Enumerate the finite observed corpus, not infinite free-text slot values."""
    lines = set()
    for path in paths:
        if path.suffix.lower() != ".jsonl":
            continue
        for _request, target in load_rows(path):
            lines.add(_canonical(target))
    for specs in HOLDOUT_SINGLE_SPECS.values():
        lines.update(_canonical(target) for _request, target in specs)
    for specs in (TRAIN_WORKFLOWS, HOLDOUT_WORKFLOWS):
        for _name, _request, calls in specs:
            lines.update(_canonical(call) for call in calls)
    for record in records:
        lines.update(_canonical(call) for call in record.calls)
    return sorted(lines)


def write_curriculum(
    records: Sequence[SequenceRecord],
    *,
    output: Path,
    report_path: Path,
    source_paths: Sequence[Path],
) -> dict[str, Any]:
    output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(record.to_json(), ensure_ascii=True, sort_keys=True)
        for record in records
    ]
    payload = ("\n".join(lines) + "\n").encode("utf-8")
    output.write_bytes(payload)
    counts: dict[str, int] = defaultdict(int)
    tools: dict[str, int] = defaultdict(int)
    for record in records:
        counts[f"{record.split}:stage_{record.stage}"] += 1
        for line in record.calls:
            tools[parse_tool_call(line).tool] += 1
    inventory = bounded_grammar_inventory(source_paths, records)
    report = {
        "schema": SCHEMA,
        "deterministic": True,
        "records": len(records),
        "counts": dict(sorted(counts.items())),
        "tool_mentions": dict(sorted(tools.items())),
        "observed_canonical_inventory": len(inventory),
        "inventory_boundary": (
            "exhaustive over observed canonical calls and finite enum branches; "
            "free-text, URL, integer, and filename slots are intentionally unbounded"
        ),
        "output": str(output),
        "output_sha256": hashlib.sha256(payload).hexdigest(),
        "sources": [
            {
                "path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in source_paths
        ],
    }
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", type=Path, default=DEFAULT_TRAIN)
    parser.add_argument("--holdout", type=Path, default=DEFAULT_HOLDOUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--singles-per-tool", type=int, default=192)
    parser.add_argument("--droid-smoke", action="store_true")
    parser.add_argument("--droid-cross255", action="store_true")
    args = parser.parse_args()
    records = build_curriculum(args.train, singles_per_tool=args.singles_per_tool)
    report = write_curriculum(
        records,
        output=args.output,
        report_path=args.report,
        source_paths=(args.train, args.holdout, DEFAULT_MCP_SLASH_REGISTRY),
    )
    if args.droid_smoke:
        representatives = [HOLDOUT_SINGLE_SPECS[tool][0][1] for tool in HANDLERS]
        receipts = [droid_route(line, mode="and") for line in representatives]
        report["droid_representatives"] = {
            "calls": len(receipts),
            "accepted": sum(int(row["accepted"]) for row in receipts),
            "all_tools": sorted(
                parse_tool_call(row["canonical"]).tool for row in receipts
            ),
        }
    if args.droid_cross255:
        report["droid_cross255"] = droid_cross255_smoke()
    if args.droid_smoke or args.droid_cross255:
        args.report.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
