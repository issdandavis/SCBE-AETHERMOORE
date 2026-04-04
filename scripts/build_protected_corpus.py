#!/usr/bin/env python3
"""Build a protected corpus for synthetic training prep.

The builder ingests JSONL training records and plain-text note sources, applies
regex-backed sensitive string detection, and replaces findings via a vault
adapter expected from ``src.security.privacy_token_vault``.

The pipeline is intentionally bounded: it keeps a novelty-aware cycle guard so
repeated non-productive passes exit early while still allowing new source
shapes, categories, or semantic neighborhoods to continue up to the cap.
"""

from __future__ import annotations

import argparse
import importlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_VAULT_MODULE = "src.security.privacy_token_vault"
DEFAULT_MAX_CYCLES = 10
TEXT_NOTE_EXTENSIONS = {".md", ".markdown", ".txt"}
JSONL_EXTENSIONS = {".jsonl"}


@dataclass(frozen=True)
class PatternRule:
    kind: str
    regex: re.Pattern[str]


@dataclass
class LoopBudget:
    max_cycles: int = DEFAULT_MAX_CYCLES
    cycles_run: int = 0
    productive_cycles: int = 0
    last_delta: int = 0
    exit_reason: str = "not_started"
    seen_identifier_kinds: set[str] = field(default_factory=set)
    seen_shapes: set[str] = field(default_factory=set)
    seen_source_buckets: set[str] = field(default_factory=set)


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
    PatternRule(
        "api_key", re.compile(r"(?i)\b(?:sk|rk|pk|ghp|gho|ghu|ghs|ghr|hf|xox[baprs])[_-]?[A-Za-z0-9_\-]{10,}\b")
    ),
    PatternRule(
        "api_key",
        re.compile(
            r"(?i)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|secret|session[_-]?token)\s*[:=]\s*[A-Za-z0-9._\-+/=]{12,}"
        ),
    ),
]
SENSITIVE_RULES = [
    BEARER_RULE,
    API_KEY_RULES[0],
    API_KEY_RULES[1],
    CC_RULE,
    SSN_RULE,
    ACCOUNT_RULE,
    EMAIL_RULE,
    PHONE_RULE,
    URL_RULE,
    IP_RULE,
]


def _safe_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except Exception:
        return str(path.resolve())


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


def _shape_signature(record: Any) -> str:
    if isinstance(record, dict):
        keys = ",".join(sorted(str(key) for key in record.keys())[:12])
        return f"dict:{keys}"
    if isinstance(record, list):
        return f"list:{len(record)}"
    return type(record).__name__


def _title_from_text(text: str, fallback: str) -> str:
    for line in text.splitlines():
        candidate = line.strip().lstrip("#").strip()
        if candidate:
            return candidate[:120]
    return fallback


def _load_vault_adapter(module_name: str, vault_dir: str | None) -> Any:
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise RuntimeError(
            f"Vault module '{module_name}' is unavailable. Expected src.security.privacy_token_vault to provide a vault adapter."
        ) from exc

    candidates: list[Callable[..., Any]] = []
    for attr in ("create_vault", "get_vault", "build_vault"):
        candidate = getattr(module, attr, None)
        if callable(candidate):
            candidates.append(candidate)
    for attr in ("PrivacyTokenVault", "TokenVault"):
        candidate = getattr(module, attr, None)
        if candidate is not None:
            candidates.append(candidate)

    for candidate in candidates:
        try:
            if vault_dir is None:
                vault = candidate()
            else:
                vault = candidate(vault_dir=vault_dir)
        except TypeError:
            try:
                vault = candidate(vault_dir) if vault_dir is not None else candidate()
            except TypeError:
                continue
        if vault is not None:
            return _VaultAdapter(vault)

    raise RuntimeError(
        f"Vault module '{module_name}' does not expose a usable adapter. Expected create_vault()/get_vault()/build_vault() "
        "or a PrivacyTokenVault/TokenVault class with a protect-like method."
    )


class _VaultAdapter:
    def __init__(self, backend: Any):
        self.backend = backend

    def protect(self, value: str, kind: str, source_file: str) -> str:
        for method_name in ("protect", "tokenize", "seal", "encode"):
            method = getattr(self.backend, method_name, None)
            if callable(method):
                try:
                    return str(method(value, kind=kind, source_file=source_file))
                except TypeError:
                    try:
                        return str(method(value, kind))
                    except TypeError:
                        return str(method(value))
        put_method = getattr(self.backend, "put", None)
        if callable(put_method):
            metadata = {"source_file": source_file} if source_file else None
            try:
                entry = put_method(value, kind=kind, metadata=metadata)
            except TypeError:
                entry = put_method(value, kind=kind)
            alias = getattr(entry, "alias", None) or str(entry)
            return f"<<{(kind or 'value').upper()}:{'~'.join(alias)}>>"
        raise RuntimeError(
            "privacy_token_vault adapter must expose protect/tokenize/seal/encode so strings can be replaced deterministically."
        )


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


def _load_jsonl_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                records.append(
                    {
                        "source_kind": "jsonl_malformed",
                        "source_file": _safe_relative(path),
                        "line_number": line_no,
                        "content": line,
                    }
                )
                continue
            if not isinstance(record, dict):
                record = {"value": record}
            record.setdefault("source_kind", "jsonl")
            record.setdefault("source_file", _safe_relative(path))
            record.setdefault("line_number", line_no)
            records.append(record)
    return records


def _load_note_record(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return {
        "source_kind": "note",
        "source_file": _safe_relative(path),
        "source_extension": path.suffix.lower(),
        "title": _title_from_text(text, path.stem),
        "content": text,
    }


def _load_source_records(inputs: Iterable[str | Path]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    records: list[dict[str, Any]] = []
    extension_counts: Counter[str] = Counter()
    for path in _iter_input_files(inputs):
        extension_counts[path.suffix.lower() or "<none>"] += 1
        if path.suffix.lower() in JSONL_EXTENSIONS:
            records.extend(_load_jsonl_records(path))
        else:
            records.append(_load_note_record(path))
    return records, dict(extension_counts)


def _protect_text(
    text: str, vault: _VaultAdapter, source_file: str, counts: Counter[str], unique_values: dict[str, set[str]]
) -> tuple[str, int]:
    replacement_total = 0
    protected = text
    for rule in SENSITIVE_RULES:
        if rule.kind == "credit_card":

            def repl_cc(match: re.Match[str]) -> str:
                nonlocal replacement_total
                raw = match.group(0)
                compact = re.sub(r"\D", "", raw)
                if not _luhn_check(compact):
                    return raw
                counts[rule.kind] += 1
                unique_values[rule.kind].add(raw)
                replacement_total += 1
                return vault.protect(raw, kind=rule.kind, source_file=source_file)

            protected, _ = rule.regex.subn(repl_cc, protected)
            continue

        def repl(match: re.Match[str]) -> str:
            nonlocal replacement_total
            raw = match.group(0)
            if rule.kind == "ip":
                octets = raw.split(".")
                if len(octets) != 4 or any(not part.isdigit() or int(part) > 255 for part in octets):
                    return raw
            counts[rule.kind] += 1
            unique_values[rule.kind].add(raw)
            replacement_total += 1
            return vault.protect(raw, kind=rule.kind, source_file=source_file)

        protected, _ = rule.regex.subn(repl, protected)
    return protected, replacement_total


def _protect_value(
    value: Any,
    vault: _VaultAdapter,
    source_file: str,
    counts: Counter[str],
    unique_values: dict[str, set[str]],
) -> tuple[Any, int]:
    if isinstance(value, str):
        return _protect_text(value, vault, source_file, counts, unique_values)
    if isinstance(value, list):
        protected_items: list[Any] = []
        total = 0
        for item in value:
            protected_item, item_total = _protect_value(item, vault, source_file, counts, unique_values)
            protected_items.append(protected_item)
            total += item_total
        return protected_items, total
    if isinstance(value, dict):
        protected_map: dict[str, Any] = {}
        total = 0
        for key, item in value.items():
            protected_item, item_total = _protect_value(item, vault, source_file, counts, unique_values)
            protected_map[key] = protected_item
            total += item_total
        return protected_map, total
    return value, 0


def _process_cycle(
    records: list[dict[str, Any]],
    vault: _VaultAdapter,
    state: LoopBudget,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    protected_records: list[dict[str, Any]] = []
    identifier_counts: Counter[str] = Counter()
    source_file_counts: Counter[str] = Counter()
    unique_values: dict[str, set[str]] = defaultdict(set)
    shape_hits: set[str] = set()
    source_buckets: set[str] = set()
    total_replacements = 0

    for record in records:
        source_file = str(record.get("source_file", "<unknown>"))
        source_kind = str(record.get("source_kind", "unknown"))
        shape_hits.add(_shape_signature(record))
        source_buckets.add(f"{source_kind}:{Path(source_file).suffix.lower()}")
        protected, replacements = _protect_value(record, vault, source_file, identifier_counts, unique_values)
        if isinstance(protected, dict):
            protected.setdefault("protection", {})
            protected["protection"].update(
                {
                    "source_file": source_file,
                    "source_kind": source_kind,
                    "protected_by": "build_protected_corpus.py",
                }
            )
        protected_records.append(
            protected if isinstance(protected, dict) else {"value": protected, "source_file": source_file}
        )
        source_file_counts[source_file] += 1
        total_replacements += replacements

    delta = 0
    fresh_kinds = set(identifier_counts) - state.seen_identifier_kinds
    fresh_shapes = shape_hits - state.seen_shapes
    fresh_sources = source_buckets - state.seen_source_buckets
    delta += len(fresh_kinds) * 3
    delta += len(fresh_shapes) * 2
    delta += len(fresh_sources)
    state.seen_identifier_kinds.update(identifier_counts)
    state.seen_shapes.update(shape_hits)
    state.seen_source_buckets.update(source_buckets)

    cycle_report = {
        "identifier_counts": dict(identifier_counts),
        "source_file_counts": dict(source_file_counts),
        "unique_value_counts": {kind: len(values) for kind, values in unique_values.items()},
        "total_replacements": total_replacements,
        "useful_delta": delta,
    }
    return protected_records, cycle_report


def build_protected_corpus(
    inputs: Iterable[str | Path],
    output_path: Path,
    manifest_path: Path,
    vault_module: str = DEFAULT_VAULT_MODULE,
    vault_dir: str | None = None,
    max_cycles: int = DEFAULT_MAX_CYCLES,
) -> dict[str, Any]:
    input_list = list(inputs)
    source_records, extension_counts = _load_source_records(input_list)
    vault = _load_vault_adapter(vault_module, vault_dir)

    loop_budget = LoopBudget(max_cycles=max_cycles)
    protected_records = source_records
    aggregate_identifier_counts: Counter[str] = Counter()
    aggregate_source_file_counts: dict[str, int] = {}
    aggregate_unique_value_counts: Counter[str] = Counter()
    aggregate_replacements = 0
    cycle_report = {
        "identifier_counts": {},
        "source_file_counts": {},
        "unique_value_counts": {},
        "total_replacements": 0,
        "useful_delta": 0,
    }
    cycle_reports: list[dict[str, Any]] = []

    if not source_records:
        exit_reason = "empty_input"
    else:
        while loop_budget.cycles_run < loop_budget.max_cycles:
            protected_records, cycle_report = _process_cycle(protected_records, vault, loop_budget)
            loop_budget.cycles_run += 1
            loop_budget.last_delta = int(cycle_report["useful_delta"])
            aggregate_identifier_counts.update(cycle_report["identifier_counts"])
            aggregate_replacements += int(cycle_report["total_replacements"])
            for source_file, count in cycle_report["source_file_counts"].items():
                aggregate_source_file_counts[source_file] = max(count, aggregate_source_file_counts.get(source_file, 0))
            for kind, count in cycle_report["unique_value_counts"].items():
                aggregate_unique_value_counts[kind] = max(count, aggregate_unique_value_counts.get(kind, 0))
            cycle_reports.append(
                {
                    "cycle": loop_budget.cycles_run,
                    "total_replacements": cycle_report["total_replacements"],
                    "useful_delta": cycle_report["useful_delta"],
                    "identifier_counts": cycle_report["identifier_counts"],
                }
            )
            if cycle_report["total_replacements"] > 0:
                loop_budget.productive_cycles += 1
            if cycle_report["total_replacements"] == 0:
                exit_reason = "no_sensitive_matches" if loop_budget.productive_cycles == 0 else "completed"
                break
            if cycle_report["useful_delta"] == 0:
                exit_reason = "stagnant_delta" if loop_budget.productive_cycles == 0 else "completed"
                break
        else:
            exit_reason = "max_cycles_reached"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for record in protected_records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    manifest = {
        "status": "ok",
        "exit_reason": exit_reason,
        "loop_budget": {
            "max_cycles": loop_budget.max_cycles,
            "cycles_run": loop_budget.cycles_run,
            "productive_cycles": loop_budget.productive_cycles,
            "last_delta": loop_budget.last_delta,
            "seen_identifier_kinds": sorted(loop_budget.seen_identifier_kinds),
            "seen_shapes": sorted(loop_budget.seen_shapes),
            "seen_source_buckets": sorted(loop_budget.seen_source_buckets),
        },
        "cycle_reports": cycle_reports,
        "input_files": len(_iter_input_files(input_list)),
        "records_processed": len(source_records),
        "records_written": len(protected_records),
        "total_replacements": aggregate_replacements,
        "identifier_counts": dict(aggregate_identifier_counts),
        "unique_value_counts": dict(aggregate_unique_value_counts),
        "source_file_counts": aggregate_source_file_counts,
        "input_extensions": extension_counts,
        "vault_module": vault_module,
        "output_path": str(output_path),
    }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    return manifest


def _default_output_for(inputs: list[str]) -> Path:
    first = Path(inputs[0]) if inputs else REPO_ROOT / "training-data"
    stem = first.stem if first.is_file() else "training-data"
    return REPO_ROOT / "training-data" / f"protected_{stem}.jsonl"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build a protected corpus from training-style sources and notes.")
    parser.add_argument("--input", nargs="*", default=["training-data"], help="Input files, directories, or globs.")
    parser.add_argument("--output", default="", help="Protected JSONL output path.")
    parser.add_argument("--manifest", default="", help="Manifest JSON output path.")
    parser.add_argument("--vault-module", default=DEFAULT_VAULT_MODULE, help="Vault module to import.")
    parser.add_argument("--vault-dir", default=None, help="Optional vault directory or token store path.")
    parser.add_argument(
        "--max-cycles", type=int, default=DEFAULT_MAX_CYCLES, help="Maximum novelty cycles before exit."
    )
    args = parser.parse_args(argv)

    output_path = Path(args.output) if args.output else _default_output_for(args.input)
    manifest_path = Path(args.manifest) if args.manifest else output_path.with_suffix(".manifest.json")
    report = build_protected_corpus(
        args.input,
        output_path=output_path,
        manifest_path=manifest_path,
        vault_module=args.vault_module,
        vault_dir=args.vault_dir,
        max_cycles=args.max_cycles,
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
