"""Streaming six-view token catalog with prime topology and goal surfing.

Canonical source bytes and word spans remain the identity.  BPE IDs, 5W/color,
speech-function candidates, atomic state, prime lanes, and source provenance are
typed views of that identity.  The module builds an external SQLite lookup and
never writes model weights.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from html import escape
import json
import math
from pathlib import Path
import re
import sqlite3
from typing import Any, Iterable, Iterator, Mapping, Sequence

from python.scbe.atomic_tokenization import map_token_to_atomic_state
from python.scbe.chemistry_sieve_spectrum import primes_through
from python.scbe.function_lexicon import FunctionLexicon

SCHEMA = "scbe.prime-token-catalog.v1"
SEARCH_SCHEMA = "scbe.prime-token-goal-search.v1"
PROBABILITY_SCHEMA = "scbe.prime-token-probability.v1"
ALGORITHM_REVISION = "six-view-topology-v3"
LEXICAL_FIRST_REVISION = "six-view-lexical-first-v1"
LEXICAL_BAND_REVISION = "six-view-lexical-band-v1"
DEFAULT_TOKENIZER = Path(
    r"C:\dev\clay_home\tokenizers\clay_open_core_bpe_v1\tokenizer.json"
)
DEFAULT_TOKENIZER_SHA256 = (
    "6c14a5cd26188678f920273cff49483f535e340caa98e3a7eb4d3285286c37c6"
)
WORD_RE = re.compile(r"[^\W_]+(?:['’-][^\W_]+)*", re.UNICODE)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
MAX_RELATIONSHIPS_PER_OCCURRENCE = 12
VIEW_NAMES = ("lexical", "five_w", "speech", "atomic", "prime", "source")
VIEW_WEIGHTS = {
    "lexical": 2.0,
    "five_w": 1.0,
    "speech": 0.5,
    "atomic": 0.5,
    "prime": 0.75,
    "source": 0.75,
}
ROLE_ORDER = ("who", "what", "when", "where", "why", "unknown")
ROLE_PRIMES = {"who": 2, "what": 3, "when": 5, "where": 7, "why": 11, "unknown": 13}
ROLE_COLORS = {
    "who": "#2563EB",
    "what": "#16A34A",
    "when": "#F59E0B",
    "where": "#7C3AED",
    "why": "#DC2626",
    "unknown": "#64748B",
}
COLOR_MAPPING_ID = sha256(
    json.dumps(ROLE_COLORS, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()
WHEN_WORDS = {
    "after",
    "already",
    "before",
    "during",
    "eventually",
    "later",
    "meanwhile",
    "next",
    "now",
    "recently",
    "since",
    "soon",
    "then",
    "today",
    "tomorrow",
    "until",
    "when",
    "whenever",
    "yesterday",
}
WHERE_WORDS = {
    "above",
    "across",
    "at",
    "behind",
    "below",
    "beside",
    "between",
    "inside",
    "near",
    "outside",
    "over",
    "through",
    "under",
    "where",
    "within",
}
WHY_WORDS = {
    "because",
    "consequently",
    "due",
    "hence",
    "reason",
    "so",
    "therefore",
    "why",
}
WHO_WORDS = {
    "he",
    "her",
    "hers",
    "him",
    "his",
    "i",
    "me",
    "mine",
    "our",
    "ours",
    "she",
    "their",
    "theirs",
    "them",
    "they",
    "we",
    "who",
    "whom",
    "whose",
    "you",
    "your",
    "yours",
}
CODE_SUFFIXES = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".go",
    ".java",
    ".js",
    ".jsx",
    ".mjs",
    ".py",
    ".rs",
    ".ts",
    ".tsx",
}


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def stable_id(namespace: str, *parts: object) -> str:
    payload = "\x1f".join([namespace, *(str(part) for part in parts)])
    return sha256(payload.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_word(surface: str) -> str:
    return surface.casefold().replace("’", "'")


def infer_source_kind(path: Path) -> str:
    lower = str(path).casefold()
    if path.suffix.casefold() in CODE_SUFFIXES:
        return "code"
    if any(
        marker in lower
        for marker in ("conversation", "transcript", "session", "chat", "dialog")
    ):
        return "conversation"
    if any(
        marker in lower
        for marker in ("paper", "academic", "arxiv", "research", "citation")
    ):
        return "academic"
    if path.suffix.casefold() in {".md", ".rst"}:
        return "documentation"
    if path.suffix.casefold() in {".jsonl", ".ndjson"}:
        return "records"
    return "local_text"


@dataclass(frozen=True, slots=True)
class InputRecord:
    text: str
    source_uri: str
    source_kind: str
    source_id_hint: str = ""
    license_name: str = "unknown"


class FrozenTokenizerView:
    """Pinned BPE view. It never replaces the canonical UTF-8 byte identity."""

    def __init__(
        self,
        path: Path = DEFAULT_TOKENIZER,
        expected_sha256: str = DEFAULT_TOKENIZER_SHA256,
    ):
        self.path = Path(path).resolve()
        if not self.path.is_file():
            raise FileNotFoundError(f"frozen tokenizer not found: {self.path}")
        self.sha256 = sha256_file(self.path)
        if self.sha256 != expected_sha256.casefold():
            raise ValueError(
                f"tokenizer hash mismatch: expected {expected_sha256}, found {self.sha256}"
            )
        try:
            from tokenizers import Tokenizer
        except (
            ImportError
        ) as exc:  # pragma: no cover - dependency is present in the supported environment
            raise RuntimeError(
                "the pinned tokenizer requires the tokenizers package"
            ) from exc
        self.tokenizer = Tokenizer.from_file(str(self.path))
        self.vocab_size = int(self.tokenizer.get_vocab_size())

    def encode(self, text: str) -> tuple[list[int], list[tuple[int, int]]]:
        encoded = self.tokenizer.encode(text, add_special_tokens=False)
        return [int(value) for value in encoded.ids], [
            (int(a), int(b)) for a, b in encoded.offsets
        ]


class PrimeOracle:
    """Amortized prime lookup backed by Loom's Eratosthenes implementation."""

    def __init__(self) -> None:
        self.limit = 1
        self.primes: tuple[int, ...] = ()
        self.prime_set: set[int] = set()

    def _grow(self, value: int) -> None:
        if value <= self.limit:
            return
        limit = max(1024, self.limit)
        while limit < value:
            limit *= 2
        self.primes = primes_through(limit)
        self.prime_set = set(self.primes)
        self.limit = limit

    def describe(self, value: int) -> dict[str, Any]:
        number = int(value)
        if number < 2:
            return {"kind": "edge", "prime": False, "factors": []}
        self._grow(number)
        if number in self.prime_set:
            return {"kind": "prime", "prime": True, "factors": [number]}
        rest = number
        factors: list[int] = []
        for prime in self.primes:
            if prime * prime > rest:
                break
            while rest % prime == 0:
                factors.append(prime)
                rest //= prime
        if rest > 1:
            factors.append(rest)
        return {"kind": "composite", "prime": False, "factors": factors}


def iter_sections(
    stream: Iterable[str], max_chars: int = 8192
) -> Iterator[tuple[int, int, str]]:
    """Yield bounded paragraph-like sections while retaining exact character offsets."""
    if max_chars < 256:
        raise ValueError("max_chars must be at least 256")
    pieces: list[str] = []
    start = 0
    cursor = 0
    length = 0

    def flush() -> tuple[int, int, str] | None:
        nonlocal pieces, length
        if not pieces:
            return None
        text = "".join(pieces)
        row = (start, start + len(text), text)
        pieces = []
        length = 0
        return row

    for raw in stream:
        line = str(raw)
        if pieces and length + len(line) > max_chars:
            row = flush()
            if row is not None:
                yield row
            start = cursor
        while len(line) > max_chars:
            chunk = line[:max_chars]
            line = line[max_chars:]
            if pieces:
                row = flush()
                if row is not None:
                    yield row
            yield cursor, cursor + len(chunk), chunk
            cursor += len(chunk)
            start = cursor
        if not pieces:
            start = cursor
        pieces.append(line)
        length += len(line)
        cursor += len(line)
        if not line.strip():
            row = flush()
            if row is not None:
                yield row
            start = cursor
    row = flush()
    if row is not None:
        yield row


def _atomic_payload(surface: str) -> tuple[dict[str, Any], list[tuple[str, str]]]:
    state = map_token_to_atomic_state(surface, language="en")
    payload = {
        "semantic_class": state.semantic_class,
        "resolved": bool(state.semantic_resolved),
        "source": state.semantic_source,
        "lexical_domains": list(state.lexical_domains),
        "element": state.element.symbol,
        "tau": state.tau.as_dict(),
    }
    features = [
        ("atomic", f"semantic:{state.semantic_class}"),
        ("atomic", f"resolved:{int(state.semantic_resolved)}"),
        ("atomic", f"element:{state.element.symbol}"),
    ]
    features.extend(
        ("atomic", f"tau:{tongue}:{value}")
        for tongue, value in state.tau.as_dict().items()
    )
    return payload, features


def _speech_payload(
    lexicon: FunctionLexicon, surface: str
) -> tuple[list[dict[str, Any]], list[tuple[str, str]]]:
    candidates = lexicon.lookup(surface)[:16]
    compact = [
        {
            "id": row["id"],
            "kind": row["kind"],
            "family": row["family"],
            "upos": row["upos"],
        }
        for row in candidates
    ]
    features: list[tuple[str, str]] = []
    for row in compact:
        features.extend(
            (
                ("speech", f"primitive:{row['id']}"),
                ("speech", f"kind:{row['kind']}"),
                ("speech", f"family:{row['family']}"),
                ("speech", f"upos:{row['upos']}"),
            )
        )
    if not compact:
        features.append(("speech", "candidate:ABSENT"))
    return compact, features


def _five_w(words: Sequence[dict[str, Any]]) -> dict[str, Any]:
    scores = Counter({role: 0.0 for role in ROLE_ORDER})
    evidence: dict[str, list[str]] = {role: [] for role in ROLE_ORDER}
    for word in words:
        normalized = word["normalized"]
        surface = word["surface"]
        atomic = word["atomic"]
        speech = word["speech"]

        def mark(role: str, amount: float = 1.0) -> None:
            scores[role] += amount
            if surface not in evidence[role] and len(evidence[role]) < 12:
                evidence[role].append(surface)

        upos = {row["upos"] for row in speech}
        families = {row["family"] for row in speech}
        if (
            normalized in WHO_WORDS
            or "PRON" in upos
            or (surface[:1].isupper() and surface[1:].islower())
        ):
            mark("who", 1.25)
        if atomic["semantic_class"] in {"ACTION", "ENTITY", "MODIFIER"} or upos & {
            "NOUN",
            "VERB",
            "ADJ",
            "ADV",
        }:
            mark(
                "what",
                (
                    0.65
                    if speech and all(row["kind"] == "function" for row in speech)
                    else 1.0
                ),
            )
        if normalized in WHEN_WORDS or atomic["semantic_class"] == "TEMPORAL":
            mark("when", 1.5)
        if normalized in WHERE_WORDS or (
            "preposition" in families and normalized not in WHEN_WORDS
        ):
            mark("where", 1.1)
        if normalized in WHY_WORDS or normalized in {"cause", "causes", "caused"}:
            mark("why", 1.6)
    nonzero = [role for role in ROLE_ORDER[:-1] if scores[role] > 0]
    primary = (
        max(
            nonzero,
            key=lambda role: (
                scores[role] / max(1, len(evidence[role])),
                scores[role],
                -ROLE_ORDER.index(role),
            ),
        )
        if nonzero
        else "unknown"
    )
    total = sum(scores[role] for role in ROLE_ORDER[:-1])
    normalized_scores = {
        role: (scores[role] / total if total else (1.0 if role == "unknown" else 0.0))
        for role in ROLE_ORDER
    }
    return {
        "scores": normalized_scores,
        "raw_scores": {role: scores[role] for role in ROLE_ORDER},
        "evidence": evidence,
        "primary": primary,
        "color": ROLE_COLORS[primary],
        "mapping_id": COLOR_MAPPING_ID,
    }


def _schema(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=NORMAL;
        PRAGMA foreign_keys=ON;
        CREATE TABLE sources (
          source_id TEXT PRIMARY KEY, source_uri TEXT NOT NULL, source_kind TEXT NOT NULL,
          license_name TEXT NOT NULL, content_sha256 TEXT NOT NULL, byte_count INTEGER NOT NULL
        );
        CREATE TABLE sections (
          section_id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(source_id),
          ordinal INTEGER NOT NULL, start_char INTEGER NOT NULL, end_char INTEGER NOT NULL,
          text_sha256 TEXT NOT NULL, text_preview TEXT NOT NULL, primary_role TEXT NOT NULL,
          color TEXT NOT NULL, five_w_json TEXT NOT NULL, bpe_ids_json TEXT NOT NULL
        );
        CREATE TABLE tokens (
          token_id TEXT PRIMARY KEY, normalized TEXT NOT NULL UNIQUE, utf8_hex TEXT NOT NULL,
          atomic_json TEXT NOT NULL, speech_json TEXT NOT NULL, is_function INTEGER NOT NULL
        );
        CREATE TABLE occurrences (
          occurrence_id TEXT PRIMARY KEY, token_id TEXT NOT NULL REFERENCES tokens(token_id),
          source_id TEXT NOT NULL REFERENCES sources(source_id),
          section_id TEXT NOT NULL REFERENCES sections(section_id), global_ordinal INTEGER NOT NULL UNIQUE,
          section_ordinal INTEGER NOT NULL, start_char INTEGER NOT NULL, end_char INTEGER NOT NULL,
          surface TEXT NOT NULL, bpe_ids_json TEXT NOT NULL, prime_kind TEXT NOT NULL,
          prime_factors_json TEXT NOT NULL, route_prime INTEGER NOT NULL, route_residue INTEGER NOT NULL,
          range_bucket INTEGER NOT NULL
        );
        CREATE TABLE section_features (
          section_id TEXT NOT NULL REFERENCES sections(section_id), view_name TEXT NOT NULL,
          feature_key TEXT NOT NULL, feature_value REAL NOT NULL,
          PRIMARY KEY(section_id, view_name, feature_key)
        );
        CREATE TABLE relation_members (
          relation_type TEXT NOT NULL, relation_key TEXT NOT NULL,
          token_id TEXT NOT NULL REFERENCES tokens(token_id),
          PRIMARY KEY(relation_type, relation_key, token_id)
        );
        CREATE TABLE feature_catalog (
          view_name TEXT NOT NULL, feature_key TEXT NOT NULL, section_frequency INTEGER NOT NULL,
          PRIMARY KEY(view_name, feature_key)
        );
        CREATE TABLE token_rank (
          token_id TEXT PRIMARY KEY REFERENCES tokens(token_id), frequency INTEGER NOT NULL,
          document_frequency INTEGER NOT NULL, source_kind_count INTEGER NOT NULL,
          role_count INTEGER NOT NULL, resolved_rate REAL NOT NULL, function_rate REAL NOT NULL,
          baseline_score REAL NOT NULL, secondary_score REAL NOT NULL,
          baseline_rank INTEGER NOT NULL, secondary_rank INTEGER NOT NULL
        );
        """)


class PrimeTokenCatalogBuilder:
    def __init__(
        self,
        output_dir: str | Path,
        *,
        tokenizer_path: str | Path = DEFAULT_TOKENIZER,
        tokenizer_sha256: str = DEFAULT_TOKENIZER_SHA256,
        section_chars: int = 8192,
        range_size: int = 4096,
    ) -> None:
        self.output_dir = Path(output_dir).resolve()
        if self.output_dir.exists() and any(self.output_dir.iterdir()):
            raise FileExistsError(f"output directory is not empty: {self.output_dir}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.section_chars = int(section_chars)
        self.range_size = int(range_size)
        if self.range_size < 128:
            raise ValueError("range_size must be at least 128")
        self.tokenizer = FrozenTokenizerView(Path(tokenizer_path), tokenizer_sha256)
        self.lexicon = FunctionLexicon()
        self.primes = PrimeOracle()
        self.db_path = self.output_dir / "catalog.sqlite3"
        self.connection = sqlite3.connect(self.db_path)
        _schema(self.connection)
        self.sections_out = (self.output_dir / "sections.jsonl").open(
            "x", encoding="utf-8", newline="\n"
        )
        self.tokens_out = (self.output_dir / "tokens.jsonl").open(
            "x", encoding="utf-8", newline="\n"
        )
        self.occurrences_out = (self.output_dir / "occurrences.jsonl").open(
            "x", encoding="utf-8", newline="\n"
        )
        self.preview_rows: list[dict[str, Any]] = []
        self.source_count = 0
        self.section_count = 0
        self.occurrence_count = 0
        self.relationship_count = 0
        self._closed = False

    def _write_jsonl(self, handle, value: Mapping[str, Any]) -> None:
        handle.write(canonical_json(value).decode("utf-8") + "\n")

    def _source_row(self, record: InputRecord) -> tuple[str, str, int]:
        raw = record.text.encode("utf-8")
        content_hash = sha256(raw).hexdigest()
        source_id = stable_id(
            "source", record.source_id_hint or record.source_uri, content_hash
        )
        self.connection.execute(
            "INSERT INTO sources VALUES (?, ?, ?, ?, ?, ?)",
            (
                source_id,
                record.source_uri,
                record.source_kind,
                record.license_name,
                content_hash,
                len(raw),
            ),
        )
        self.source_count += 1
        return source_id, content_hash, len(raw)

    def ingest_record(self, record: InputRecord) -> None:
        if not isinstance(record.text, str) or not record.text:
            raise ValueError("source text must be a nonempty string")
        source_id, _content_hash, _byte_count = self._source_row(record)
        self._ingest_sections(
            source_id,
            record.source_kind,
            iter_sections(record.text.splitlines(keepends=True), self.section_chars),
        )
        self.connection.commit()

    def ingest_file(
        self,
        path: str | Path,
        *,
        source_kind: str = "auto",
        license_name: str = "unknown",
    ) -> None:
        source_path = Path(path).resolve()
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
        if source_path.suffix.casefold() in {".jsonl", ".ndjson"}:
            self._ingest_jsonl(
                source_path, source_kind=source_kind, license_name=license_name
            )
            return
        kind = infer_source_kind(source_path) if source_kind == "auto" else source_kind
        content_hash = sha256_file(source_path)
        source_id = stable_id("source", str(source_path), content_hash)
        byte_count = source_path.stat().st_size
        self.connection.execute(
            "INSERT INTO sources VALUES (?, ?, ?, ?, ?, ?)",
            (source_id, str(source_path), kind, license_name, content_hash, byte_count),
        )
        self.source_count += 1
        with source_path.open(
            "r", encoding="utf-8", errors="replace", newline=""
        ) as handle:
            self._ingest_sections(
                source_id, kind, iter_sections(handle, self.section_chars)
            )
        self.connection.commit()

    def _ingest_jsonl(self, path: Path, *, source_kind: str, license_name: str) -> None:
        with path.open("r", encoding="utf-8", errors="strict") as handle:
            for line_no, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                row = json.loads(line)
                if not isinstance(row, dict) or not isinstance(row.get("text"), str):
                    raise ValueError(f"{path}:{line_no}: JSONL row needs a text string")
                kind = str(
                    row.get("source_kind")
                    or (
                        infer_source_kind(path)
                        if source_kind == "auto"
                        else source_kind
                    )
                )
                uri = str(row.get("source_uri") or f"{path}#L{line_no}")
                license_value = str(row.get("license") or license_name)
                self.ingest_record(
                    InputRecord(
                        text=row["text"],
                        source_uri=uri,
                        source_kind=kind,
                        source_id_hint=str(row.get("source_id") or uri),
                        license_name=license_value,
                    )
                )

    def ingest_paths(
        self,
        paths: Sequence[str | Path],
        *,
        source_kind: str = "auto",
        license_name: str = "unknown",
    ) -> None:
        files: list[Path] = []
        for raw in paths:
            path = Path(raw).resolve()
            if path.is_dir():
                files.extend(
                    candidate
                    for candidate in path.rglob("*")
                    if candidate.is_file()
                    and candidate.suffix.casefold()
                    in {
                        ".c",
                        ".cpp",
                        ".go",
                        ".java",
                        ".js",
                        ".jsonl",
                        ".md",
                        ".py",
                        ".rs",
                        ".rst",
                        ".txt",
                        ".ts",
                    }
                )
            elif path.is_file():
                files.append(path)
            else:
                raise FileNotFoundError(path)
        for path in sorted(set(files), key=lambda item: str(item).casefold()):
            self.ingest_file(path, source_kind=source_kind, license_name=license_name)

    def _ingest_sections(
        self,
        source_id: str,
        source_kind: str,
        sections: Iterable[tuple[int, int, str]],
    ) -> None:
        section_ordinal = 0
        for start_char, end_char, text in sections:
            if not text.strip():
                continue
            section_ordinal += 1
            self._ingest_section(
                source_id, source_kind, section_ordinal, start_char, end_char, text
            )
            if self.section_count % 128 == 0:
                self.connection.commit()

    def _ingest_section(
        self,
        source_id: str,
        source_kind: str,
        section_ordinal: int,
        start_char: int,
        end_char: int,
        text: str,
    ) -> None:
        text_hash = sha256(text.encode("utf-8")).hexdigest()
        section_id = stable_id("section", source_id, section_ordinal, text_hash)
        bpe_ids, bpe_offsets = self.tokenizer.encode(text)
        words: list[dict[str, Any]] = []
        for match in WORD_RE.finditer(text):
            surface = match.group(0)
            atomic, atomic_features = _atomic_payload(surface)
            speech, speech_features = _speech_payload(self.lexicon, surface)
            overlapping = [
                token_id
                for token_id, (left, right) in zip(bpe_ids, bpe_offsets, strict=True)
                if right > match.start() and left < match.end()
            ]
            words.append(
                {
                    "surface": surface,
                    "normalized": normalize_word(surface),
                    "start": match.start(),
                    "end": match.end(),
                    "bpe_ids": overlapping,
                    "atomic": atomic,
                    "atomic_features": atomic_features,
                    "speech": speech,
                    "speech_features": speech_features,
                }
            )
        if not words:
            return
        five_w = _five_w(words)
        primary_role = five_w["primary"]
        self.connection.execute(
            "INSERT INTO sections VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                section_id,
                source_id,
                section_ordinal,
                start_char,
                end_char,
                text_hash,
                text[:500],
                primary_role,
                five_w["color"],
                canonical_json(five_w).decode("utf-8"),
                canonical_json(bpe_ids).decode("utf-8"),
            ),
        )
        section_features: Counter[tuple[str, str]] = Counter()
        section_features[("five_w", f"role:{primary_role}")] += 1
        section_features[("five_w", f"color:{five_w['color']}")] += 1
        section_features[("source", f"kind:{source_kind}")] += 1
        section_features[("source", f"source:{source_id}")] += 1
        route_prime = ROLE_PRIMES[primary_role]
        for word_ordinal, word in enumerate(words, 1):
            self.occurrence_count += 1
            global_ordinal = self.occurrence_count
            prime = self.primes.describe(global_ordinal)
            token_id = stable_id("word", word["normalized"])
            occurrence_id = stable_id(
                "occurrence",
                section_id,
                word_ordinal,
                word["start"],
                word["end"],
                word["surface"],
            )
            utf8_hex = word["normalized"].encode("utf-8").hex()
            is_function = bool(word["speech"]) and all(
                row["kind"] == "function" for row in word["speech"]
            )
            inserted_token = self.connection.execute(
                "INSERT OR IGNORE INTO tokens VALUES (?, ?, ?, ?, ?, ?)",
                (
                    token_id,
                    word["normalized"],
                    utf8_hex,
                    canonical_json(word["atomic"]).decode("utf-8"),
                    canonical_json(word["speech"]).decode("utf-8"),
                    int(is_function),
                ),
            )
            if inserted_token.rowcount:
                self._write_jsonl(
                    self.tokens_out,
                    {
                        "schema": SCHEMA,
                        "token_id": token_id,
                        "normalized": word["normalized"],
                        "utf8_hex": utf8_hex,
                        "atomic": word["atomic"],
                        "speech_candidates": word["speech"],
                    },
                )
            range_bucket = (global_ordinal - 1) // self.range_size
            self.connection.execute(
                "INSERT INTO occurrences VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    occurrence_id,
                    token_id,
                    source_id,
                    section_id,
                    global_ordinal,
                    word_ordinal,
                    word["start"],
                    word["end"],
                    word["surface"],
                    canonical_json(word["bpe_ids"]).decode("utf-8"),
                    prime["kind"],
                    canonical_json(prime["factors"]).decode("utf-8"),
                    route_prime,
                    global_ordinal % route_prime,
                    range_bucket,
                ),
            )
            features: list[tuple[str, str]] = [
                ("lexical", f"word:{word['normalized']}"),
                ("five_w", f"role:{primary_role}"),
                ("five_w", f"color:{five_w['color']}"),
                ("prime", f"kind:{prime['kind']}"),
                (
                    "prime",
                    f"route:{route_prime}:residue:{global_ordinal % route_prime}",
                ),
                ("prime", f"range:{range_bucket}"),
                ("source", f"kind:{source_kind}"),
                ("source", f"source:{source_id}"),
            ]
            features.extend(
                ("lexical", f"bpe:{token_id_value}")
                for token_id_value in word["bpe_ids"][:16]
            )
            features.extend(word["atomic_features"])
            features.extend(word["speech_features"])
            features.extend(
                ("prime", f"factor:{factor}")
                for factor in sorted(set(prime["factors"]))
            )
            for view_name, feature_key in dict.fromkeys(features):
                section_features[(view_name, feature_key)] += 1
            relationship_features = [
                ("lexical", f"word:{word['normalized']}"),
                ("five_w", f"role:{primary_role}"),
                ("atomic", f"semantic:{word['atomic']['semantic_class']}"),
                ("prime", f"kind:{prime['kind']}"),
                (
                    "prime",
                    f"route:{route_prime}:residue:{global_ordinal % route_prime}",
                ),
                ("source", f"kind:{source_kind}"),
            ]
            if word["speech"]:
                relationship_features.extend(
                    [
                        ("speech", f"primitive:{word['speech'][0]['id']}"),
                        ("speech", f"upos:{word['speech'][0]['upos']}"),
                    ]
                )
            if prime["factors"]:
                relationship_features.append(("prime", f"factor:{prime['factors'][0]}"))
            unique_relationships = list(dict.fromkeys(relationship_features))[
                :MAX_RELATIONSHIPS_PER_OCCURRENCE
            ]
            for view_name, feature_key in unique_relationships:
                inserted = self.connection.execute(
                    "INSERT OR IGNORE INTO relation_members VALUES (?, ?, ?)",
                    (view_name, feature_key, token_id),
                )
                self.relationship_count += max(0, inserted.rowcount)
            occurrence_row = {
                "schema": SCHEMA,
                "occurrence_id": occurrence_id,
                "token_id": token_id,
                "source_id": source_id,
                "section_id": section_id,
                "surface": word["surface"],
                "normalized": word["normalized"],
                "utf8_hex": word["surface"].encode("utf-8").hex(),
                "global_ordinal": global_ordinal,
                "bpe_ids": word["bpe_ids"],
                "five_w_role": primary_role,
                "color": five_w["color"],
                "token_analysis_ref": token_id,
                "prime": {
                    **prime,
                    "route_prime": route_prime,
                    "residue": global_ordinal % route_prime,
                    "range_bucket": range_bucket,
                },
            }
            self._write_jsonl(self.occurrences_out, occurrence_row)
        for (view_name, feature_key), count in section_features.items():
            self.connection.execute(
                "INSERT INTO section_features VALUES (?, ?, ?, ?)",
                (section_id, view_name, feature_key, 1.0 + math.log(count)),
            )
        section_row = {
            "schema": SCHEMA,
            "section_id": section_id,
            "source_id": source_id,
            "ordinal": section_ordinal,
            "sha256": text_hash,
            "five_w": five_w,
            "bpe_ids": bpe_ids,
            "word_count": len(words),
        }
        self._write_jsonl(self.sections_out, section_row)
        if len(self.preview_rows) < 500:
            self.preview_rows.append({**section_row, "preview": text[:500]})
        self.section_count += 1

    def _finalize_feature_catalog(self) -> None:
        self.connection.execute("DELETE FROM feature_catalog")
        self.connection.execute("""
            INSERT INTO feature_catalog(view_name, feature_key, section_frequency)
            SELECT view_name, feature_key, COUNT(*) FROM section_features GROUP BY view_name, feature_key
            """)
        self.connection.executescript("""
            CREATE INDEX idx_occurrence_section ON occurrences(section_id);
            CREATE INDEX idx_occurrence_token ON occurrences(token_id);
            CREATE INDEX idx_feature_lookup ON section_features(view_name, feature_key);
            CREATE INDEX idx_relation_lookup ON relation_members(relation_type, relation_key);
            """)

    def _finalize_ranks(self) -> None:
        self.connection.execute("DELETE FROM token_rank")
        rows = self.connection.execute("""
            SELECT o.token_id, COUNT(*) AS frequency, COUNT(DISTINCT o.source_id) AS document_frequency,
                   COUNT(DISTINCT s.source_kind) AS source_kind_count,
                   COUNT(DISTINCT sec.primary_role) AS role_count,
                   AVG(CAST(json_extract(t.atomic_json, '$.resolved') AS REAL)) AS resolved_rate,
                   AVG(CASE WHEN t.speech_json != '[]' THEN 1.0 ELSE 0.0 END) AS function_rate
            FROM occurrences o JOIN tokens t ON t.token_id=o.token_id
            JOIN sources s ON s.source_id=o.source_id
            JOIN sections sec ON sec.section_id=o.section_id GROUP BY o.token_id
            """).fetchall()
        scored: list[dict[str, Any]] = []
        for (
            token_id,
            frequency,
            documents,
            source_kinds,
            roles,
            resolved_rate,
            function_rate,
        ) in rows:
            baseline = math.log1p(frequency)
            secondary = (
                baseline
                + 0.75 * math.log1p(documents)
                + 0.35 * source_kinds
                + 0.20 * roles
                + 0.25 * float(resolved_rate or 0.0)
                + 0.15 * float(function_rate or 0.0)
            )
            scored.append(
                {
                    "token_id": token_id,
                    "frequency": frequency,
                    "documents": documents,
                    "source_kinds": source_kinds,
                    "roles": roles,
                    "resolved_rate": float(resolved_rate or 0.0),
                    "function_rate": float(function_rate or 0.0),
                    "baseline": baseline,
                    "secondary": secondary,
                }
            )
        baseline_order = {
            row["token_id"]: rank
            for rank, row in enumerate(
                sorted(scored, key=lambda x: (-x["baseline"], x["token_id"])), 1
            )
        }
        secondary_order = {
            row["token_id"]: rank
            for rank, row in enumerate(
                sorted(scored, key=lambda x: (-x["secondary"], x["token_id"])), 1
            )
        }
        self.connection.executemany(
            "INSERT INTO token_rank VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    row["token_id"],
                    row["frequency"],
                    row["documents"],
                    row["source_kinds"],
                    row["roles"],
                    row["resolved_rate"],
                    row["function_rate"],
                    row["baseline"],
                    row["secondary"],
                    baseline_order[row["token_id"]],
                    secondary_order[row["token_id"]],
                )
                for row in scored
            ],
        )

    def _write_html(self) -> Path:
        path = self.output_dir / "sections.html"
        cards = []
        for row in self.preview_rows:
            role = row["five_w"]["primary"]
            color = row["five_w"]["color"]
            cards.append(
                f'<article style="border-left:8px solid {color};padding:12px;margin:10px;background:#f8fafc">'
                f"<b>{escape(role.upper())}</b> · {escape(row['section_id'][:12])}"
                f"<pre style=\"white-space:pre-wrap\">{escape(row['preview'])}</pre></article>"
            )
        path.write_text(
            "<!doctype html><meta charset=utf-8><title>Prime Token Catalog</title>"
            "<h1>Prime Token Catalog — bounded preview</h1>" + "".join(cards),
            encoding="utf-8",
        )
        return path

    def finalize(self) -> dict[str, Any]:
        if self._closed:
            raise RuntimeError("catalog builder is already closed")
        self._finalize_feature_catalog()
        self._finalize_ranks()
        self.connection.commit()
        self.sections_out.close()
        self.tokens_out.close()
        self.occurrences_out.close()
        html_path = self._write_html()
        self.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        self.connection.close()
        self._closed = True
        outputs = [
            self.db_path,
            self.output_dir / "sections.jsonl",
            self.output_dir / "tokens.jsonl",
            self.output_dir / "occurrences.jsonl",
            html_path,
        ]
        manifest = {
            "schema": SCHEMA,
            "status": "MECHANICS_ONLY_NO_PROMOTION",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "algorithm_revision": ALGORITHM_REVISION,
            "views": list(VIEW_NAMES),
            "source_count": self.source_count,
            "section_count": self.section_count,
            "occurrence_count": self.occurrence_count,
            "relationship_memberships": self.relationship_count,
            "relationship_cap_per_occurrence": MAX_RELATIONSHIPS_PER_OCCURRENCE,
            "tokenizer": {
                "path": str(self.tokenizer.path),
                "sha256": self.tokenizer.sha256,
                "vocab_size": self.tokenizer.vocab_size,
                "role": "typed_bpe_view_not_active_byte_model_identity",
            },
            "canonical_identity": "utf8_bytes_and_source_word_span",
            "color_mapping_id": COLOR_MAPPING_ID,
            "function_registry_sha256": self.lexicon.registry_hash,
            "sieve": "clay_sieve.sieve_of_eratosthenes",
            "outputs": [
                {
                    "path": str(path),
                    "bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
                for path in outputs
            ],
            "boundary": (
                "Deterministic retrieval metadata only. Six views of one occurrence are correlated. "
                "No model weight, serving pointer, or promotion state changed."
            ),
        }
        manifest_path = self.output_dir / "MANIFEST.json"
        manifest_path.write_bytes(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True).encode(
                "utf-8"
            )
        )
        return manifest


def _query_features(
    goal: str, lexicon: FunctionLexicon
) -> tuple[dict[str, set[str]], dict[str, Any]]:
    words: list[dict[str, Any]] = []
    features: dict[str, set[str]] = {view: set() for view in VIEW_NAMES}
    for match in WORD_RE.finditer(goal):
        surface = match.group(0)
        normalized = normalize_word(surface)
        atomic, atomic_features = _atomic_payload(surface)
        speech, speech_features = _speech_payload(lexicon, surface)
        words.append(
            {
                "surface": surface,
                "normalized": normalized,
                "atomic": atomic,
                "speech": speech,
            }
        )
        features["lexical"].add(f"word:{normalized}")
        for view, key in atomic_features + speech_features:
            features[view].add(key)
    five_w = _five_w(words)
    features["five_w"].add(f"role:{five_w['primary']}")
    features["five_w"].add(f"color:{five_w['color']}")
    oracle = PrimeOracle()
    route_prime = ROLE_PRIMES[five_w["primary"]]
    for ordinal in range(1, len(words) + 1):
        prime = oracle.describe(ordinal)
        features["prime"].add(f"kind:{prime['kind']}")
        features["prime"].add(f"route:{route_prime}:residue:{ordinal % route_prime}")
        features["prime"].update(f"factor:{factor}" for factor in prime["factors"][:2])
    return features, {"words": words, "five_w": five_w}


def _softmax(values: Mapping[str, float]) -> dict[str, float]:
    if not values:
        return {}
    peak = max(values.values())
    exp = {
        key: math.exp(max(-60.0, min(60.0, value - peak)))
        for key, value in values.items()
    }
    total = sum(exp.values()) or 1.0
    return {key: value / total for key, value in exp.items()}


def search_goal(
    database: str | Path,
    goal: str,
    *,
    limit: int = 20,
    topology_steps: int = 2,
    damping: float = 0.35,
    ablate_views: Sequence[str] = (),
    control: str = "aligned",
    control_seed: int = 0,
    source_kinds: Sequence[str] = (),
) -> dict[str, Any]:
    """Search ideas/evidence, then use grammar only as returned constraints.

    ``control='shuffled'`` rotates all non-lexical memberships one section while
    preserving feature counts. It is a size-matched binding control.
    """
    if not goal.strip():
        raise ValueError("goal must be nonempty")
    if control not in {"aligned", "shuffled"}:
        raise ValueError("control must be aligned or shuffled")
    ablated = set(ablate_views)
    if ablated - set(VIEW_NAMES):
        raise ValueError("unknown ablation view")
    catalog_path = Path(database).resolve()
    catalog_hash = sha256_file(catalog_path)
    search_id = stable_id(
        "search",
        catalog_hash,
        goal,
        control,
        control_seed,
        sorted(ablated),
        sorted(
            source_kind.strip() for source_kind in source_kinds if source_kind.strip()
        ),
        topology_steps,
        damping,
        ALGORITHM_REVISION,
    )
    connection = sqlite3.connect(catalog_path)
    connection.row_factory = sqlite3.Row
    lexicon = FunctionLexicon()
    query, query_analysis = _query_features(goal, lexicon)
    query["source"].update(
        f"kind:{source_kind.strip()}"
        for source_kind in source_kinds
        if source_kind.strip()
    )
    section_ids = [
        row[0]
        for row in connection.execute(
            "SELECT section_id FROM sections ORDER BY section_id"
        )
    ]
    if len(section_ids) > 1:
        offset = 1
        if control_seed:
            offset = 1 + int(
                stable_id("control-offset", control_seed, ALGORITHM_REVISION), 16
            ) % (len(section_ids) - 1)
        rotate = {
            section_id: section_ids[(index + offset) % len(section_ids)]
            for index, section_id in enumerate(section_ids)
        }
    else:
        offset = 0
        rotate = {}
    scores: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    evidence: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for view_name in VIEW_NAMES:
        if view_name in ablated or not query[view_name]:
            continue
        placeholders = ",".join("?" for _ in query[view_name])
        params = [view_name, *sorted(query[view_name])]
        rows = connection.execute(
            f"""
            SELECT sf.section_id, sf.feature_key, sf.feature_value, fc.section_frequency
            FROM section_features sf JOIN feature_catalog fc
              ON fc.view_name=sf.view_name AND fc.feature_key=sf.feature_key
            WHERE sf.view_name=? AND sf.feature_key IN ({placeholders})
            """,
            params,
        )
        for row in rows:
            target = row["section_id"]
            if control == "shuffled" and view_name != "lexical":
                target = rotate[target]
            idf = 1.0 + math.log(
                (len(section_ids) + 1) / (int(row["section_frequency"]) + 1)
            )
            scores[target][view_name] += float(row["feature_value"]) * idf
            evidence[target][view_name].append(row["feature_key"])
    maxima = {
        view_name: max(
            (view_scores.get(view_name, 0.0) for view_scores in scores.values()),
            default=0.0,
        )
        for view_name in VIEW_NAMES
    }
    base: dict[str, float] = {}
    for section_id, view_scores in scores.items():
        weighted = []
        for view_name, value in view_scores.items():
            if view_name in ablated or maxima[view_name] <= 0:
                continue
            weighted.append(
                (
                    VIEW_WEIGHTS[view_name],
                    min(1.0, max(0.0, value / maxima[view_name])),
                )
            )
        total_weight = sum(weight for weight, _value in weighted) or 1.0
        base[section_id] = (
            sum(weight * value for weight, value in weighted) / total_weight
        )
    if base and topology_steps > 0:
        frontier = sorted(base, key=base.get, reverse=True)[: max(100, limit * 10)]
        placeholders = ",".join("?" for _ in frontier)
        rows = connection.execute(
            f"SELECT section_id, view_name, feature_key FROM section_features WHERE section_id IN ({placeholders})",
            frontier,
        ).fetchall()
        groups: dict[tuple[str, str], list[str]] = defaultdict(list)
        for row in rows:
            if row["view_name"] not in ablated:
                groups[(row["view_name"], row["feature_key"])].append(row["section_id"])
        current = dict(base)
        center = sum(current.values()) / len(current)
        for _ in range(topology_steps):
            deltas: dict[str, list[float]] = defaultdict(list)
            for members in groups.values():
                active = [member for member in members if member in current]
                if len(active) < 2:
                    continue
                group_mean = sum(current[member] for member in active) / len(active)
                for member in active:
                    deltas[member].append(group_mean - center)
            current = {
                section_id: (1.0 - damping) * base[section_id]
                + damping
                * (score + (sum(deltas[section_id]) / max(1, len(deltas[section_id]))))
                for section_id, score in current.items()
            }
        final_scores = current
    else:
        final_scores = base
    probabilities = _softmax(final_scores)
    ranked = sorted(
        final_scores, key=lambda section_id: (-final_scores[section_id], section_id)
    )[:limit]
    results: list[dict[str, Any]] = []
    for section_id in ranked:
        section = connection.execute(
            """
            SELECT sec.*, src.source_kind, src.source_uri FROM sections sec
            JOIN sources src ON src.source_id=sec.source_id WHERE sec.section_id=?
            """,
            (section_id,),
        ).fetchone()
        occurrence_rows = connection.execute(
            """
            SELECT o.surface, t.is_function, t.speech_json, t.normalized, tr.secondary_rank
            FROM occurrences o JOIN tokens t ON t.token_id=o.token_id
            LEFT JOIN token_rank tr ON tr.token_id=o.token_id
            WHERE o.section_id=? ORDER BY o.section_ordinal LIMIT 80
            """,
            (section_id,),
        ).fetchall()
        content_tokens = []
        grammar_constraints = []
        for row in occurrence_rows:
            speech = json.loads(row["speech_json"])
            if row["is_function"]:
                grammar_constraints.append(
                    {
                        "surface": row["surface"],
                        "candidates": speech,
                        "role": "constraint_not_idea_evidence",
                    }
                )
            else:
                content_tokens.append(
                    {
                        "surface": row["surface"],
                        "normalized": row["normalized"],
                        "catalog_rank": row["secondary_rank"],
                    }
                )
        results.append(
            {
                "section_id": section_id,
                "score": final_scores[section_id],
                "probability": probabilities[section_id],
                "source_kind": section["source_kind"],
                "source_uri": section["source_uri"],
                "primary_role": section["primary_role"],
                "color": section["color"],
                "preview": section["text_preview"],
                "view_scores": dict(scores[section_id]),
                "evidence_path": {
                    view: sorted(set(keys))
                    for view, keys in evidence[section_id].items()
                },
                "content_tokens": content_tokens[:24],
                "grammar_constraints": grammar_constraints[:24],
            }
        )
    connection.close()
    return {
        "schema": SEARCH_SCHEMA,
        "algorithm_revision": ALGORITHM_REVISION,
        "search_id": search_id,
        "catalog_sha256": catalog_hash,
        "goal": goal,
        "control": control,
        "control_seed": control_seed,
        "control_offset": offset if control == "shuffled" else 0,
        "ablated_views": sorted(ablated),
        "query_analysis": query_analysis,
        "query_view_status": {
            view_name: ("PRESENT" if query[view_name] else "ABSENT")
            for view_name in VIEW_NAMES
        },
        "views": list(VIEW_NAMES),
        "view_weights": dict(VIEW_WEIGHTS),
        "topology": {
            "steps": topology_steps,
            "damping": damping,
            "rise_fall": "competitive_centered_propagation",
        },
        "results": results,
        "boundary": "Grammar is returned as a constraint layer; content ideas and evidence drive retrieval.",
    }


def search_lexical_first(
    database: str | Path,
    goal: str,
    *,
    limit: int = 20,
    topology_steps: int = 2,
    damping: float = 0.35,
    control: str = "aligned",
    control_seed: int = 0,
    source_kinds: Sequence[str] = (),
) -> dict[str, Any]:
    """Keep lexical retrieval authoritative and use other views only for ties.

    The ranking is lexicographic, not a weighted scalar: the lexical-only score
    is the primary key and the full six-view score is the secondary key. A
    candidate with any higher lexical score can never be displaced by auxiliary
    evidence. Full-field ranking therefore acts only on exact lexical ties or
    the all-zero lexical fallback set.
    """
    if limit < 1:
        raise ValueError("limit must be positive")
    catalog_path = Path(database).resolve()
    connection = sqlite3.connect(catalog_path)
    try:
        section_count = int(
            connection.execute("SELECT COUNT(*) FROM sections").fetchone()[0]
        )
    finally:
        connection.close()
    candidate_limit = max(limit, section_count)
    lexical = search_goal(
        catalog_path,
        goal,
        limit=candidate_limit,
        topology_steps=topology_steps,
        damping=damping,
        ablate_views=[view for view in VIEW_NAMES if view != "lexical"],
        control="aligned",
        source_kinds=source_kinds,
    )
    auxiliary = search_goal(
        catalog_path,
        goal,
        limit=candidate_limit,
        topology_steps=topology_steps,
        damping=damping,
        control=control,
        control_seed=control_seed,
        source_kinds=source_kinds,
    )
    lexical_by_section = {row["section_id"]: row for row in lexical["results"]}
    auxiliary_by_section = {row["section_id"]: row for row in auxiliary["results"]}
    section_ids = set(lexical_by_section) | set(auxiliary_by_section)
    ranked = sorted(
        section_ids,
        key=lambda section_id: (
            -float(lexical_by_section.get(section_id, {}).get("score", 0.0)),
            -float(auxiliary_by_section.get(section_id, {}).get("score", 0.0)),
            section_id,
        ),
    )
    results = []
    for section_id in ranked[:limit]:
        lexical_row = lexical_by_section.get(section_id)
        auxiliary_row = auxiliary_by_section.get(section_id)
        row = dict(auxiliary_row or lexical_row or {})
        lexical_score = float((lexical_row or {}).get("score", 0.0))
        auxiliary_score = float((auxiliary_row or {}).get("score", 0.0))
        row["score"] = lexical_score
        row["probability"] = None
        row["cascade_scores"] = {
            "lexical_primary": lexical_score,
            "auxiliary_tiebreak": auxiliary_score,
        }
        results.append(row)
    search_id = stable_id(
        "lexical-first-search",
        lexical["search_id"],
        auxiliary["search_id"],
        LEXICAL_FIRST_REVISION,
    )
    return {
        "schema": SEARCH_SCHEMA,
        "algorithm_revision": LEXICAL_FIRST_REVISION,
        "search_id": search_id,
        "catalog_sha256": lexical["catalog_sha256"],
        "goal": goal,
        "control": control,
        "control_seed": control_seed,
        "control_offset": auxiliary["control_offset"],
        "query_analysis": auxiliary["query_analysis"],
        "query_view_status": auxiliary["query_view_status"],
        "views": list(VIEW_NAMES),
        "ranking_rule": [
            "lexical_only_score_descending",
            "full_six_view_score_descending_on_exact_lexical_ties",
            "section_id_ascending",
        ],
        "child_search_ids": {
            "lexical": lexical["search_id"],
            "auxiliary": auxiliary["search_id"],
        },
        "results": results,
        "boundary": (
            "Auxiliary views can only break an exact lexical-score tie or order lexical-zero fallbacks; "
            "they cannot displace stronger lexical evidence."
        ),
    }


def search_lexical_banded(
    database: str | Path,
    goal: str,
    *,
    lexical_band_width: float,
    limit: int = 20,
    topology_steps: int = 2,
    damping: float = 0.35,
    control: str = "aligned",
    control_seed: int = 0,
    source_kinds: Sequence[str] = (),
) -> dict[str, Any]:
    """Use auxiliary evidence only within anchored lexical-score bands.

    Bands are contiguous in descending lexical order and anchored to their
    strongest lexical score. This prevents pairwise-near candidates from
    chaining across a wider lexical interval. Width zero is exactly the
    lexical-first ranking rule.
    """
    if limit < 1:
        raise ValueError("limit must be positive")
    if not 0.0 <= lexical_band_width <= 1.0:
        raise ValueError("lexical_band_width must be between 0 and 1")
    catalog_path = Path(database).resolve()
    connection = sqlite3.connect(catalog_path)
    try:
        section_count = int(
            connection.execute("SELECT COUNT(*) FROM sections").fetchone()[0]
        )
    finally:
        connection.close()
    candidate_limit = max(limit, section_count)
    lexical = search_goal(
        catalog_path,
        goal,
        limit=candidate_limit,
        topology_steps=topology_steps,
        damping=damping,
        ablate_views=[view for view in VIEW_NAMES if view != "lexical"],
        control="aligned",
        source_kinds=source_kinds,
    )
    auxiliary = search_goal(
        catalog_path,
        goal,
        limit=candidate_limit,
        topology_steps=topology_steps,
        damping=damping,
        control=control,
        control_seed=control_seed,
        source_kinds=source_kinds,
    )
    lexical_by_section = {row["section_id"]: row for row in lexical["results"]}
    auxiliary_by_section = {row["section_id"]: row for row in auxiliary["results"]}
    section_ids = set(lexical_by_section) | set(auxiliary_by_section)

    def lexical_score(section_id: str) -> float:
        return float(lexical_by_section.get(section_id, {}).get("score", 0.0))

    def auxiliary_score(section_id: str) -> float:
        return float(auxiliary_by_section.get(section_id, {}).get("score", 0.0))

    lexical_order = sorted(section_ids, key=lambda item: (-lexical_score(item), item))
    bands: list[tuple[float, list[str]]] = []
    for section_id in lexical_order:
        score = lexical_score(section_id)
        if not bands or bands[-1][0] - score > lexical_band_width:
            bands.append((score, [section_id]))
        else:
            bands[-1][1].append(section_id)

    ranked: list[tuple[str, int, float]] = []
    for band_index, (anchor_score, members) in enumerate(bands):
        ordered_members = sorted(
            members,
            key=lambda item: (-auxiliary_score(item), item),
        )
        ranked.extend(
            (section_id, band_index, anchor_score) for section_id in ordered_members
        )

    results = []
    for section_id, band_index, anchor_score in ranked[:limit]:
        lexical_row = lexical_by_section.get(section_id)
        auxiliary_row = auxiliary_by_section.get(section_id)
        row = dict(auxiliary_row or lexical_row or {})
        primary_score = lexical_score(section_id)
        secondary_score = auxiliary_score(section_id)
        row["score"] = primary_score
        row["probability"] = None
        row["cascade_scores"] = {
            "lexical_primary": primary_score,
            "auxiliary_within_band": secondary_score,
            "lexical_band_width": lexical_band_width,
            "lexical_band_index": band_index,
            "lexical_band_anchor": anchor_score,
        }
        results.append(row)
    search_id = stable_id(
        "lexical-band-search",
        lexical["search_id"],
        auxiliary["search_id"],
        lexical_band_width,
        LEXICAL_BAND_REVISION,
    )
    return {
        "schema": SEARCH_SCHEMA,
        "algorithm_revision": LEXICAL_BAND_REVISION,
        "search_id": search_id,
        "catalog_sha256": lexical["catalog_sha256"],
        "goal": goal,
        "control": control,
        "control_seed": control_seed,
        "control_offset": auxiliary["control_offset"],
        "query_analysis": auxiliary["query_analysis"],
        "query_view_status": auxiliary["query_view_status"],
        "views": list(VIEW_NAMES),
        "lexical_band_width": lexical_band_width,
        "ranking_rule": [
            "lexical_score_band_descending",
            "full_six_view_score_descending_inside_anchored_band",
            "section_id_ascending",
        ],
        "child_search_ids": {
            "lexical": lexical["search_id"],
            "auxiliary": auxiliary["search_id"],
        },
        "results": results,
        "boundary": (
            "Auxiliary views reorder only candidates inside a fixed anchored lexical-score band; "
            "the emitted score remains lexical and no probability or neural weight is changed."
        ),
    }


def _probability_schema(connection: sqlite3.Connection) -> None:
    connection.executescript("""
        PRAGMA journal_mode=WAL;
        PRAGMA synchronous=FULL;
        CREATE TABLE IF NOT EXISTS goals (
          goal_id TEXT PRIMARY KEY, goal_text TEXT NOT NULL, created_at_utc TEXT NOT NULL,
          model_anchor_sha256 TEXT NOT NULL, catalog_sha256 TEXT NOT NULL,
          algorithm_revision TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS token_probability_current (
          goal_id TEXT NOT NULL REFERENCES goals(goal_id), token_id TEXT NOT NULL,
          probability REAL NOT NULL, updated_at_utc TEXT NOT NULL,
          PRIMARY KEY(goal_id, token_id)
        );
        CREATE TABLE IF NOT EXISTS probability_events (
          event_id TEXT PRIMARY KEY, goal_id TEXT NOT NULL REFERENCES goals(goal_id),
          token_id TEXT NOT NULL, old_probability REAL NOT NULL,
          new_probability REAL NOT NULL, delta REAL NOT NULL,
          model_anchor_sha256 TEXT NOT NULL, catalog_sha256 TEXT NOT NULL,
          evidence_json TEXT NOT NULL, created_at_utc TEXT NOT NULL,
          algorithm_revision TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_probability_goal ON probability_events(goal_id);
        """)


def update_probability_lookup(
    database: str | Path,
    search_receipt: Mapping[str, Any],
    *,
    model_anchor_sha256: str,
    token_limit: int = 256,
    probability_database: str | Path | None = None,
) -> dict[str, Any]:
    """Append probabilities to a sidecar anchored to catalog and weights."""
    anchor = model_anchor_sha256.casefold()
    if not SHA256_RE.fullmatch(anchor):
        raise ValueError("model_anchor_sha256 must be a 64-character lowercase SHA-256")
    if search_receipt.get("schema") != SEARCH_SCHEMA:
        raise ValueError("unknown search receipt")
    catalog_path = Path(database).resolve()
    lookup_path = (
        Path(probability_database).resolve()
        if probability_database is not None
        else catalog_path.with_name("probability_lookup.sqlite3")
    )
    if lookup_path == catalog_path:
        raise ValueError("probability sidecar must not overwrite the immutable catalog")
    lookup_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_hash = sha256_file(catalog_path)
    goal = str(search_receipt.get("goal") or "")
    goal_id = stable_id("goal", goal, anchor, catalog_hash, ALGORITHM_REVISION)
    now = datetime.now(timezone.utc).isoformat()
    catalog = sqlite3.connect(catalog_path)
    lookup = sqlite3.connect(lookup_path)
    _probability_schema(lookup)
    lookup.execute(
        "INSERT OR IGNORE INTO goals VALUES (?, ?, ?, ?, ?, ?)",
        (goal_id, goal, now, anchor, catalog_hash, ALGORITHM_REVISION),
    )
    token_scores: Counter[str] = Counter()
    token_evidence: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in search_receipt.get("results", []):
        section_weight = float(result["probability"])
        rows = catalog.execute(
            """
            SELECT DISTINCT o.token_id, t.is_function, t.normalized, tr.secondary_score
            FROM occurrences o JOIN tokens t ON t.token_id=o.token_id
            LEFT JOIN token_rank tr ON tr.token_id=o.token_id WHERE o.section_id=?
            """,
            (result["section_id"],),
        ).fetchall()
        for token_id, is_function, normalized, secondary_score in rows:
            grammar_discount = 0.25 if is_function else 1.0
            score = (
                section_weight
                * grammar_discount
                * (1.0 + math.log1p(float(secondary_score or 0.0)))
            )
            token_scores[token_id] += score
            if len(token_evidence[token_id]) < 8:
                token_evidence[token_id].append(
                    {
                        "section_id": result["section_id"],
                        "token": normalized,
                        "section_probability": section_weight,
                        "grammar_discount": grammar_discount,
                    }
                )
    top = dict(token_scores.most_common(token_limit))
    probabilities = _softmax(top)
    events = []
    for token_id, probability in probabilities.items():
        old_row = lookup.execute(
            "SELECT probability FROM token_probability_current WHERE goal_id=? AND token_id=?",
            (goal_id, token_id),
        ).fetchone()
        old = float(old_row[0]) if old_row else 0.0
        evidence_json = canonical_json(token_evidence[token_id]).decode("utf-8")
        event_id = stable_id(
            "probability-event", goal_id, token_id, now, probability, evidence_json
        )
        lookup.execute(
            "INSERT INTO probability_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                event_id,
                goal_id,
                token_id,
                old,
                probability,
                probability - old,
                anchor,
                catalog_hash,
                evidence_json,
                now,
                ALGORITHM_REVISION,
            ),
        )
        lookup.execute(
            """
            INSERT INTO token_probability_current VALUES (?, ?, ?, ?)
            ON CONFLICT(goal_id, token_id) DO UPDATE SET
              probability=excluded.probability,
              updated_at_utc=excluded.updated_at_utc
            """,
            (goal_id, token_id, probability, now),
        )
        events.append(
            {
                "event_id": event_id,
                "token_id": token_id,
                "old_probability": old,
                "new_probability": probability,
                "delta": probability - old,
            }
        )
    lookup.commit()
    lookup.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    lookup.close()
    catalog.close()
    return {
        "schema": PROBABILITY_SCHEMA,
        "goal_id": goal_id,
        "model_anchor_sha256": anchor,
        "catalog_sha256": catalog_hash,
        "probability_database": str(lookup_path),
        "algorithm_revision": ALGORITHM_REVISION,
        "events": events,
        "probability_sum": sum(probabilities.values()),
        "boundary": "External lookup update only; no neural tensor or serving pointer was changed.",
    }
