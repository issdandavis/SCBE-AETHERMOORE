#!/usr/bin/env python3
"""Audit a protected corpus for surviving sensitive strings and extractiveness."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
JSONL_EXTENSIONS = {".jsonl"}
TEXT_NOTE_EXTENSIONS = {".md", ".markdown", ".txt"}
DEFAULT_TANGENTIAL_PASSES = 10


@dataclass(frozen=True)
class PatternRule:
    kind: str
    regex: re.Pattern[str]


EMAIL_RULE = PatternRule("email", re.compile(r"(?<![\w@])[\w.+-]+@[\w-]+(?:\.[\w-]+)+"))
PHONE_RULE = PatternRule("phone", re.compile(r"(?<!\d)(?:\+?1[\s.-]*)?(?:\(?\d{3}\)?[\s.-]*)\d{3}[\s.-]*\d{4}(?!\d)"))
URL_RULE = PatternRule("url", re.compile(r"(?i)\bhttps?://[^\s<>'\"]+"))
IP_RULE = PatternRule("ip", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"))
SSN_RULE = PatternRule("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b"))
CC_RULE = PatternRule("credit_card", re.compile(r"\b(?:\d[ -]*?){13,19}\b"))
BEARER_RULE = PatternRule("bearer_header", re.compile(r"(?i)\bAuthorization\s*:\s*Bearer\s+[A-Za-z0-9._\-+=/]{8,}\b"))
ACCOUNT_RULE = PatternRule(
    "account_id",
    re.compile(
        r"(?i)\b(?:account|acct|customer|user|session|record|identifier|id)\s*(?:id|number|no\.?|#)?\s*[:=]\s*[A-Za-z0-9][A-Za-z0-9_\-./]{5,}"
    ),
)
API_KEY_RULES = [
    PatternRule("api_key", re.compile(r"(?i)\b(?:sk|rk|pk|ghp|gho|ghu|ghs|ghr|hf|xox[baprs])[_-]?[A-Za-z0-9_\-]{10,}\b")),
    PatternRule(
        "api_key",
        re.compile(
            r"(?i)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|secret|session[_-]?token)\s*[:=]\s*[A-Za-z0-9._\-+/=]{12,}"
        ),
    ),
]
SENSITIVE_RULES = [BEARER_RULE, API_KEY_RULES[0], API_KEY_RULES[1], CC_RULE, SSN_RULE, ACCOUNT_RULE, EMAIL_RULE, PHONE_RULE, URL_RULE, IP_RULE]


def _safe_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except Exception:
        return str(path.resolve())


def _iter_input_files(inputs: Iterable[str | Path]) -> list[Path]:
    files: list[Path] = []
    seen: set[str] = set()
    for item in inputs:
        raw = Path(item)
        if any(ch in str(raw) for ch in "*?[]"):
            matches = [Path(path) for path in sorted(Path().glob(str(raw)))]
        elif raw.is_dir():
            matches = [p for p in sorted(raw.rglob("*")) if p.is_file()]
        elif raw.is_file():
            matches = [raw]
        else:
            matches = []
        for path in matches:
            if path.suffix.lower() not in JSONL_EXTENSIONS and path.suffix.lower() not in TEXT_NOTE_EXTENSIONS:
                continue
            resolved = str(path.resolve())
            if resolved in seen:
                continue
            seen.add(resolved)
            files.append(path)
    return files


def _read_jsonl_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                records.append({"source_file": _safe_relative(path), "line_number": line_no, "content": line})
                continue
            if not isinstance(record, dict):
                record = {"value": record}
            record.setdefault("source_file", _safe_relative(path))
            record.setdefault("line_number", line_no)
            records.append(record)
    return records


def _read_note_record(path: Path) -> dict[str, Any]:
    return {
        "source_file": _safe_relative(path),
        "source_kind": "note",
        "title": path.stem,
        "content": path.read_text(encoding="utf-8", errors="replace"),
    }


def _load_records(inputs: Iterable[str | Path]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in _iter_input_files(inputs):
        if path.suffix.lower() in JSONL_EXTENSIONS:
            records.extend(_read_jsonl_records(path))
        else:
            records.append(_read_note_record(path))
    return records


def _flatten_strings(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        parts = []
        for item in value.values():
            flattened = _flatten_strings(item)
            if flattened:
                parts.append(flattened)
        return "\n".join(parts)
    if isinstance(value, list):
        parts = []
        for item in value:
            flattened = _flatten_strings(item)
            if flattened:
                parts.append(flattened)
        return "\n".join(parts)
    return ""


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _luhn_check(candidate: str) -> bool:
    digits = [int(ch) for ch in candidate if ch.isdigit()]
    if len(digits) < 13:
        return False
    checksum = 0
    parity = len(digits) % 2
    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def _scan_sensitive(text: str) -> tuple[Counter[str], dict[str, list[str]]]:
    counts: Counter[str] = Counter()
    examples: dict[str, list[str]] = defaultdict(list)
    for rule in SENSITIVE_RULES:
        for match in rule.regex.finditer(text):
            raw = match.group(0)
            if rule.kind == "credit_card" and not _luhn_check(re.sub(r"\D", "", raw)):
                continue
            if rule.kind == "ip":
                octets = raw.split(".")
                if len(octets) != 4 or any(not part.isdigit() or int(part) > 255 for part in octets):
                    continue
            counts[rule.kind] += 1
            if len(examples[rule.kind]) < 3 and raw not in examples[rule.kind]:
                examples[rule.kind].append(raw)
    return counts, dict(examples)


def _tokenize(text: str) -> list[str]:
    return re.findall(r"\b[\w$./-]+\b", text.lower())


def _ngram_set(tokens: list[str], n: int = 4) -> set[tuple[str, ...]]:
    if len(tokens) < n:
        return set()
    return {tuple(tokens[idx : idx + n]) for idx in range(len(tokens) - n + 1)}


def _measure_overlap(protected_texts: list[str], source_texts: list[str]) -> dict[str, Any]:
    source_ngrams: set[tuple[str, ...]] = set()
    for text in source_texts:
        source_ngrams.update(_ngram_set(_tokenize(text)))

    ratios: list[float] = []
    best_examples: list[dict[str, Any]] = []
    for text in protected_texts:
        protected_ngrams = _ngram_set(_tokenize(text))
        if not protected_ngrams:
            ratios.append(0.0)
            continue
        overlap = protected_ngrams & source_ngrams
        ratio = len(overlap) / len(protected_ngrams)
        ratios.append(ratio)
        if ratio > 0:
            best_examples.append({"ratio": round(ratio, 4), "excerpt": text[:220]})

    return {
        "mean_ratio": round(sum(ratios) / len(ratios), 4) if ratios else 0.0,
        "max_ratio": round(max(ratios), 4) if ratios else 0.0,
        "rows_above_threshold": sum(1 for ratio in ratios if ratio >= 0.65),
        "examples": best_examples[:5],
    }


def _scan_pass(name: str, protected_texts: list[str], source_texts: list[str]) -> dict[str, Any]:
    if name == "exact_sensitive":
        sensitive_counts: Counter[str] = Counter()
        sensitive_examples: dict[str, list[str]] = defaultdict(list)
        for text in protected_texts:
            counts, examples = _scan_sensitive(text)
            sensitive_counts.update(counts)
            for kind, items in examples.items():
                for item in items:
                    if item not in sensitive_examples[kind]:
                        sensitive_examples[kind].append(item)
        return {
            "name": name,
            "sensitive_counts": dict(sensitive_counts),
            "sensitive_examples": dict(sensitive_examples),
            "signals": sorted(f"sensitive:{kind}" for kind in sensitive_counts),
        }
    if name == "normalized_sensitive":
        sensitive_counts: Counter[str] = Counter()
        for text in protected_texts:
            counts, _ = _scan_sensitive(_collapse_whitespace(text))
            sensitive_counts.update(counts)
        return {
            "name": name,
            "sensitive_counts": dict(sensitive_counts),
            "sensitive_examples": {},
            "signals": sorted(f"normalized_sensitive:{kind}" for kind in sensitive_counts),
        }
    if name == "extractive_overlap":
        overlap = _measure_overlap(protected_texts, source_texts) if source_texts else {
            "mean_ratio": 0.0,
            "max_ratio": 0.0,
            "rows_above_threshold": 0,
            "examples": [],
        }
        signals: list[str] = []
        if overlap["max_ratio"] >= 0.75:
            signals.append("overlap:max_ratio")
        if overlap["rows_above_threshold"] > 0:
            signals.append("overlap:rows_above_threshold")
        return {
            "name": name,
            "overlap": overlap,
            "signals": signals,
        }
    raise ValueError(f"unknown scan pass: {name}")


def audit_protected_corpus(
    protected_inputs: Iterable[str | Path],
    source_inputs: Iterable[str | Path] | None,
    out_path: Path,
    max_tangential_passes: int = DEFAULT_TANGENTIAL_PASSES,
) -> dict[str, Any]:
    protected_records = _load_records(protected_inputs)
    source_records = _load_records(source_inputs or [])

    protected_texts = [_flatten_strings(record) for record in protected_records]
    source_texts = [_flatten_strings(record) for record in source_records]

    pass_order = ["exact_sensitive", "normalized_sensitive", "extractive_overlap"]
    seen_signals: set[str] = set()
    pass_reports: list[dict[str, Any]] = []
    sensitive_counts: dict[str, int] = {}
    sensitive_examples: dict[str, list[str]] = {}
    overlap = {
        "mean_ratio": 0.0,
        "max_ratio": 0.0,
        "rows_above_threshold": 0,
        "examples": [],
    }
    exit_reason = "empty_scan"

    for pass_name in pass_order[:max_tangential_passes]:
        pass_report = _scan_pass(pass_name, protected_texts, source_texts)
        new_signals = [signal for signal in pass_report.get("signals", []) if signal not in seen_signals]
        seen_signals.update(pass_report.get("signals", []))
        pass_report["new_signals"] = new_signals
        pass_reports.append(pass_report)
        if pass_name == "exact_sensitive":
            sensitive_counts = dict(pass_report.get("sensitive_counts", {}))
            sensitive_examples = dict(pass_report.get("sensitive_examples", {}))
        elif pass_name == "extractive_overlap":
            overlap = dict(pass_report.get("overlap", overlap))
            if not new_signals:
                exit_reason = "no_new_signal"
                break
        elif pass_name != pass_order[0] and not new_signals and not source_texts:
            exit_reason = "no_new_signal"
            break
    else:
        exit_reason = "scan_complete"

    status = "PASS"
    if sensitive_counts or overlap["max_ratio"] >= 0.75:
        status = "QUARANTINE"
        if exit_reason == "scan_complete":
            exit_reason = "sensitive_match"

    report = {
        "status": status,
        "loop_budget": {
            "max_tangential_passes": max_tangential_passes,
            "tangential_passes_run": len(pass_reports),
            "exit_reason": exit_reason,
        },
        "pass_reports": pass_reports,
        "protected_files": len({str(record.get("source_file", "<unknown>")) for record in protected_records}),
        "source_files": len({str(record.get("source_file", "<unknown>")) for record in source_records}),
        "protected_rows": len(protected_records),
        "source_rows": len(source_records),
        "surviving_sensitive_counts": dict(sensitive_counts),
        "surviving_sensitive_examples": dict(sensitive_examples),
        "overlap": overlap,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit a protected corpus for leakage and extractiveness.")
    parser.add_argument("--protected", nargs="+", required=True, help="Protected JSONL files, dirs, or globs.")
    parser.add_argument("--source", nargs="*", default=[], help="Optional source JSONL or note files for overlap checks.")
    parser.add_argument("--out", required=True, help="Report JSON output path.")
    parser.add_argument("--max-source-rows", type=int, default=1000, help="Reserved extension point for future bounded scanning.")
    parser.add_argument(
        "--max-tangential-passes",
        type=int,
        default=DEFAULT_TANGENTIAL_PASSES,
        help="Maximum audit scan passes before the tangential loop exits.",
    )
    args = parser.parse_args(argv)

    report = audit_protected_corpus(
        args.protected,
        args.source,
        Path(args.out),
        max_tangential_passes=args.max_tangential_passes,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
