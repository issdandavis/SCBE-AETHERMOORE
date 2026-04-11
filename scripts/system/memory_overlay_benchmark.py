"""Memory Overlay Benchmark
===========================

Minimal local benchmark for the MemPalace + SCBE overlay thesis:

1. Keep a verbatim memory substrate.
2. Retrieve with a cheap lexical baseline.
3. Rerank with deterministic SCBE sidecars.

This does not try to prove a grand theory. It measures whether an SCBE rerank
layer adds useful retrieval signal over a strong verbatim-first baseline on a
hand-labeled eval set.

Usage:
  python scripts/system/memory_overlay_benchmark.py
  python scripts/system/memory_overlay_benchmark.py --top-k 5
  python scripts/system/memory_overlay_benchmark.py --corpus-root notes/System\\ Library/Indexes --corpus-root docs/01-architecture
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from python.scbe.atomic_tokenization import TONGUES, map_token_to_atomic_state
from python.scbe.rhombic_bridge import rhombic_fusion, rhombic_score
from src.crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER

DEFAULT_CORPUS_ROOTS = (
    REPO_ROOT / "notes" / "System Library" / "Indexes",
    REPO_ROOT / "docs" / "01-architecture",
    REPO_ROOT / "python" / "scbe",
)
DEFAULT_EVAL_PATH = REPO_ROOT / "training-data" / "evals" / "memory_overlay_seed.jsonl"
ARTIFACT_DIR = REPO_ROOT / "artifacts" / "system_audit" / "memory_overlay_benchmark"
TEXT_EXTENSIONS = {".md", ".py", ".txt", ".jsonl"}
WORD_RE = re.compile(r"[A-Za-z0-9_']+")
SEMANTIC_CLASSES = (
    "INERT_WITNESS",
    "ACTION",
    "ENTITY",
    "NEGATION",
    "MODIFIER",
    "RELATION",
    "TEMPORAL",
)


@dataclass(frozen=True, slots=True)
class MemoryChunk:
    chunk_id: str
    path: str
    source: str
    chunk_index: int
    text: str


@dataclass(frozen=True, slots=True)
class ChunkFeatures:
    chunk: MemoryChunk
    token_counts: Dict[str, int]
    atomic_signature_counts: Dict[str, int]
    sacred_token_counts: Dict[str, int]
    filename_tokens: Dict[str, int]
    path_tokens: Dict[str, int]
    title_tokens: Dict[str, int]
    semantic_vector: List[float]
    tongue_vector: List[float]
    trust_mean: float


@dataclass(frozen=True, slots=True)
class RetrievalHit:
    path: str
    score: float
    best_chunk_id: str


@dataclass(frozen=True, slots=True)
class EvalItem:
    eval_id: str
    query: str
    expected_paths: List[str]
    eval_type: str
    notes: str


def _normalize_path(path: str | Path) -> str:
    resolved = Path(path)
    try:
        resolved = resolved.resolve()
    except OSError:
        resolved = Path(path)
    return resolved.as_posix().lower()


def _display_source(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _tokenize(text: str) -> List[str]:
    return [token.lower() for token in WORD_RE.findall(text)]


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    left_arr = np.asarray(left, dtype=float)
    right_arr = np.asarray(right, dtype=float)
    left_norm = float(np.linalg.norm(left_arr))
    right_norm = float(np.linalg.norm(right_arr))
    if left_norm <= 1e-12 or right_norm <= 1e-12:
        return 0.0
    return float(np.dot(left_arr, right_arr) / (left_norm * right_norm))


def _counter_cosine(left: Dict[str, int], right: Dict[str, int]) -> float:
    if not left or not right:
        return 0.0
    numerator = 0.0
    left_norm = 0.0
    right_norm = 0.0
    for term in set(left) | set(right):
        lval = float(left.get(term, 0))
        rval = float(right.get(term, 0))
        numerator += lval * rval
        left_norm += lval * lval
        right_norm += rval * rval
    if left_norm <= 1e-12 or right_norm <= 1e-12:
        return 0.0
    return numerator / math.sqrt(left_norm * right_norm)


def _iter_text_chunks(text: str, chunk_chars: int, overlap_chars: int) -> Iterable[tuple[int, str]]:
    text = text.strip()
    if not text:
        return
    if len(text) <= chunk_chars:
        yield 0, text
        return

    start = 0
    index = 0
    step = max(1, chunk_chars - overlap_chars)
    while start < len(text):
        end = min(len(text), start + chunk_chars)
        yield index, text[start:end]
        if end >= len(text):
            break
        start += step
        index += 1


def _extract_jsonl_text(line: str) -> str:
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return ""

    text_parts: List[str] = []
    for key in ("instruction", "prompt", "input", "question", "response", "output", "answer", "text", "content"):
        value = obj.get(key)
        if isinstance(value, str):
            text_parts.append(value)
    metadata = obj.get("metadata")
    if isinstance(metadata, str):
        text_parts.append(metadata)
    return "\n".join(part for part in text_parts if part)


def _extract_title_tokens(chunk: MemoryChunk) -> Counter[str]:
    for line in chunk.text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            if heading:
                return Counter(_tokenize(heading))
    stem = Path(chunk.source).stem
    return Counter(_tokenize(stem))


def _path_feature_counts(chunk: MemoryChunk) -> tuple[Counter[str], Counter[str]]:
    source_path = Path(chunk.source.replace("/", "\\"))
    filename_tokens = Counter(_tokenize(source_path.stem))
    path_tokens: Counter[str] = Counter()
    for part in source_path.parts:
        path_tokens.update(_tokenize(part))
    return filename_tokens, path_tokens


def load_corpus(
    roots: Sequence[Path],
    *,
    chunk_chars: int,
    overlap_chars: int,
) -> List[MemoryChunk]:
    chunks: List[MemoryChunk] = []
    seen_paths: set[str] = set()

    for root in roots:
        if not root.exists():
            continue
        if root.is_file():
            candidates = [root]
        else:
            candidates = [path for path in root.rglob("*") if path.is_file() and path.suffix.lower() in TEXT_EXTENSIONS]

        for path in candidates:
            normalized_path = _normalize_path(path)
            if normalized_path in seen_paths:
                continue
            seen_paths.add(normalized_path)

            if path.suffix.lower() == ".jsonl":
                try:
                    with path.open("r", encoding="utf-8", errors="replace") as handle:
                        for line_index, line in enumerate(handle):
                            text = _extract_jsonl_text(line)
                            if not text.strip():
                                continue
                            chunks.append(
                                MemoryChunk(
                                    chunk_id=f"{normalized_path}::record-{line_index}",
                                    path=normalized_path,
                                    source=_display_source(path),
                                    chunk_index=line_index,
                                    text=text,
                                )
                            )
                except OSError:
                    continue
                continue

            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

            for chunk_index, chunk_text in _iter_text_chunks(text, chunk_chars, overlap_chars):
                chunks.append(
                    MemoryChunk(
                        chunk_id=f"{normalized_path}::chunk-{chunk_index}",
                        path=normalized_path,
                        source=_display_source(path),
                        chunk_index=chunk_index,
                        text=chunk_text,
                    )
                )

    return chunks


def _build_scbe_sidecar(text: str) -> tuple[Counter[str], np.ndarray, np.ndarray, float]:
    semantic_counts: Counter[str] = Counter()
    tongue_accumulator = np.zeros(len(TONGUES), dtype=float)
    trust_values: List[float] = []

    for token in _tokenize(text):
        state = map_token_to_atomic_state(token, context_class="memory")
        semantic_counts[state.semantic_class] += 1
        tongue_accumulator += np.asarray(state.tau.as_tuple(), dtype=float)
        trust_values.append(float(state.trust_baseline))

    semantic_vector = np.array([float(semantic_counts[name]) for name in SEMANTIC_CLASSES], dtype=float)
    if trust_values:
        trust_mean = float(sum(trust_values) / len(trust_values))
    else:
        trust_mean = 0.0
    return semantic_counts, semantic_vector, tongue_accumulator, trust_mean


def _quantized_state_signature(token: str) -> str:
    state = map_token_to_atomic_state(token, context_class="memory")
    resilience = int(round(state.resilience * 10))
    adaptivity = int(round(state.adaptivity * 10))
    trust = int(round(state.trust_baseline * 10))
    dual = "x" if state.dual_state is None else str(state.dual_state)
    tau = ",".join(str(v) for v in state.tau.as_tuple())
    return (
        f"{state.semantic_class}|tau:{tau}|neg:{int(state.negative_state)}|dual:{dual}"
        f"|band:{state.band_flag}|res:{resilience}|ada:{adaptivity}|trust:{trust}"
    )


def _sacred_token_counts(text: str) -> Counter[str]:
    payload = text.encode("utf-8", errors="replace")
    counts: Counter[str] = Counter()
    for tongue in ("ko", "av", "ru", "ca", "um", "dr"):
        for token in SACRED_TONGUE_TOKENIZER.encode_bytes(tongue, payload):
            counts[f"{tongue}:{token}"] += 1
    return counts


def build_features(chunks: Sequence[MemoryChunk]) -> List[ChunkFeatures]:
    features: List[ChunkFeatures] = []
    for chunk in chunks:
        tokens = _tokenize(chunk.text)
        token_counts = Counter(tokens)
        atomic_signature_counts = Counter(_quantized_state_signature(token) for token in tokens)
        sacred_token_counts = _sacred_token_counts(chunk.text)
        filename_tokens, path_tokens = _path_feature_counts(chunk)
        title_tokens = _extract_title_tokens(chunk)
        _, semantic_vector, tongue_vector, trust_mean = _build_scbe_sidecar(chunk.text)
        features.append(
            ChunkFeatures(
                chunk=chunk,
                token_counts=dict(token_counts),
                atomic_signature_counts=dict(atomic_signature_counts),
                sacred_token_counts=dict(sacred_token_counts),
                filename_tokens=dict(filename_tokens),
                path_tokens=dict(path_tokens),
                title_tokens=dict(title_tokens),
                semantic_vector=semantic_vector.tolist(),
                tongue_vector=tongue_vector.tolist(),
                trust_mean=trust_mean,
            )
        )
    return features


def compute_idf(features: Sequence[ChunkFeatures]) -> Dict[str, float]:
    doc_freq: Counter[str] = Counter()
    total_docs = max(1, len(features))
    for feature in features:
        doc_freq.update(feature.token_counts.keys())
    return {term: math.log((1.0 + total_docs) / (1.0 + freq)) + 1.0 for term, freq in doc_freq.items()}


def _tfidf_score(query_counts: Dict[str, int], doc_counts: Dict[str, int], idf: Dict[str, float]) -> float:
    if not query_counts or not doc_counts:
        return 0.0
    terms = set(query_counts) | set(doc_counts)
    numerator = 0.0
    left_norm = 0.0
    right_norm = 0.0
    for term in terms:
        weight = idf.get(term, 1.0)
        q = float(query_counts.get(term, 0)) * weight
        d = float(doc_counts.get(term, 0)) * weight
        numerator += q * d
        left_norm += q * q
        right_norm += d * d
    if left_norm <= 1e-12 or right_norm <= 1e-12:
        return 0.0
    return numerator / math.sqrt(left_norm * right_norm)


def _keyword_overlap_fraction(query_counts: Dict[str, int], doc_counts: Dict[str, int]) -> float:
    if not query_counts or not doc_counts:
        return 0.0
    query_terms = set(query_counts)
    if not query_terms:
        return 0.0
    return float(len(query_terms & set(doc_counts)) / len(query_terms))


def _phrase_bonus(query_text: str, doc_text: str) -> float:
    normalized_query = " ".join(_tokenize(query_text))
    normalized_doc = " ".join(_tokenize(doc_text))
    if not normalized_query or not normalized_doc:
        return 0.0
    if normalized_query in normalized_doc:
        return 1.0

    query_terms = normalized_query.split()
    if len(query_terms) < 2:
        return 0.0

    longest = 0
    for width in range(min(6, len(query_terms)), 1, -1):
        for start in range(0, len(query_terms) - width + 1):
            phrase = " ".join(query_terms[start : start + width])
            if phrase in normalized_doc:
                longest = max(longest, width)
                break
        if longest:
            break
    if longest <= 0:
        return 0.0
    return float(longest / len(query_terms))


def _mempalace_style_score(query: ChunkFeatures, doc: ChunkFeatures, baseline_score: float) -> float:
    keyword_overlap = _keyword_overlap_fraction(query.token_counts, doc.token_counts)
    title_overlap = _counter_cosine(query.token_counts, doc.title_tokens)
    filename_overlap = _counter_cosine(query.token_counts, doc.filename_tokens)
    path_overlap = _counter_cosine(query.token_counts, doc.path_tokens)
    phrase_bonus = _phrase_bonus(query.chunk.text, doc.chunk.text)
    return (
        baseline_score
        + (0.30 * keyword_overlap)
        + (0.20 * title_overlap)
        + (0.15 * filename_overlap)
        + (0.10 * path_overlap)
        + (0.10 * phrase_bonus)
    )


def _overlay_score(query: ChunkFeatures, doc: ChunkFeatures, baseline_score: float) -> float:
    mempalace_score = _mempalace_style_score(query, doc, baseline_score)
    semantic_cos = _cosine(query.semantic_vector, doc.semantic_vector)
    tongue_cos = _cosine(query.tongue_vector, doc.tongue_vector)
    atomic_cos = _counter_cosine(query.atomic_signature_counts, doc.atomic_signature_counts)
    sacred_cos = _counter_cosine(query.sacred_token_counts, doc.sacred_token_counts)

    query_feature = np.asarray(query.semantic_vector + query.tongue_vector, dtype=float)
    doc_feature = np.asarray(doc.semantic_vector + doc.tongue_vector, dtype=float)
    bridge_feature = np.abs(query_feature - doc_feature)
    governance_feature = 0.5 * (query_feature + doc_feature)
    rhombic = rhombic_score(
        rhombic_fusion(
            x=query_feature,
            audio=doc_feature,
            vision=bridge_feature,
            governance=governance_feature,
        )
    )

    trust_bonus = min(query.trust_mean, doc.trust_mean)
    return (
        mempalace_score
        + (0.18 * semantic_cos)
        + (0.12 * tongue_cos)
        + (0.20 * atomic_cos)
        + (0.20 * sacred_cos)
        + (0.20 * rhombic)
        + (0.05 * trust_bonus)
    )


def rank_paths(
    query_text: str,
    corpus: Sequence[ChunkFeatures],
    idf: Dict[str, float],
    *,
    top_k: int,
    mode: str,
) -> List[RetrievalHit]:
    query_chunk = MemoryChunk(
        chunk_id="__query__",
        path="__query__",
        source="query",
        chunk_index=0,
        text=query_text,
    )
    query_features = build_features([query_chunk])[0]

    best_by_path: Dict[str, RetrievalHit] = {}
    for doc in corpus:
        baseline = _tfidf_score(query_features.token_counts, doc.token_counts, idf)
        if mode == "baseline":
            score = baseline
        elif mode == "mempalace_style":
            score = _mempalace_style_score(query_features, doc, baseline)
        elif mode == "overlay":
            score = _overlay_score(query_features, doc, baseline)
        else:
            raise ValueError(f"Unknown ranking mode: {mode}")
        current = best_by_path.get(doc.chunk.path)
        if current is None or score > current.score:
            best_by_path[doc.chunk.path] = RetrievalHit(
                path=doc.chunk.path,
                score=score,
                best_chunk_id=doc.chunk.chunk_id,
            )

    hits = sorted(best_by_path.values(), key=lambda hit: hit.score, reverse=True)
    return hits[:top_k]


def load_eval_items(path: Path) -> List[EvalItem]:
    items: List[EvalItem] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            query = obj.get("query") or obj.get("instruction")
            expected_paths_raw = obj.get("expected_paths")
            if expected_paths_raw is None:
                expected_path = obj.get("expected_path")
                expected_paths_raw = [expected_path] if expected_path else []
            if not query or not expected_paths_raw:
                continue
            expected_paths = [
                _normalize_path(REPO_ROOT / expected_path)
                for expected_path in expected_paths_raw
                if isinstance(expected_path, str) and expected_path.strip()
            ]
            if not expected_paths:
                continue
            items.append(
                EvalItem(
                    eval_id=str(obj.get("id", f"eval-{len(items)+1:03d}")),
                    query=query,
                    expected_paths=expected_paths,
                    eval_type=str(obj.get("type", "generic")),
                    notes=str(obj.get("notes", "")),
                )
            )
    return items


def _mrr(rank: int | None) -> float:
    if rank is None or rank <= 0:
        return 0.0
    return 1.0 / float(rank)


def evaluate(
    eval_items: Sequence[EvalItem],
    corpus: Sequence[ChunkFeatures],
    idf: Dict[str, float],
    *,
    top_k: int,
) -> Dict[str, object]:
    modes = ("baseline", "mempalace_style", "overlay")
    rows: List[Dict[str, object]] = []
    summary: Dict[str, Dict[str, float]] = {
        mode: {"hits": 0.0, "mrr_sum": 0.0, "queries": 0.0} for mode in modes
    }

    for item in eval_items:
        row: Dict[str, object] = {
            "id": item.eval_id,
            "query": item.query,
            "expected_paths": item.expected_paths,
            "type": item.eval_type,
            "notes": item.notes,
        }

        for mode in modes:
            hits = rank_paths(item.query, corpus, idf, top_k=top_k, mode=mode)
            hit_paths = [hit.path for hit in hits]
            candidate_ranks = [hit_paths.index(path) + 1 for path in item.expected_paths if path in hit_paths]
            rank = min(candidate_ranks) if candidate_ranks else None
            row[f"{mode}_hits"] = [asdict(hit) for hit in hits]
            row[f"{mode}_rank"] = rank
            row[f"{mode}_hit_at_k"] = rank is not None

            summary[mode]["queries"] += 1.0
            summary[mode]["hits"] += 1.0 if rank is not None else 0.0
            summary[mode]["mrr_sum"] += _mrr(rank)

        rows.append(row)

    metrics = {}
    for mode in modes:
        queries = max(1.0, summary[mode]["queries"])
        metrics[mode] = {
            "queries": int(summary[mode]["queries"]),
            "recall_at_k": round(summary[mode]["hits"] / queries, 4),
            "mrr": round(summary[mode]["mrr_sum"] / queries, 4),
        }
    return {"metrics": metrics, "rows": rows}


def write_artifact(payload: Dict[str, object]) -> Path:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = ARTIFACT_DIR / f"memory_overlay_benchmark_{stamp}.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark verbatim memory retrieval with an SCBE rerank overlay.")
    parser.add_argument(
        "--corpus-root",
        action="append",
        default=[],
        help="File or directory to include in the corpus. Can be provided multiple times.",
    )
    parser.add_argument(
        "--eval-path",
        default=str(DEFAULT_EVAL_PATH),
        help="JSONL file of hand-labeled query -> expected_path pairs.",
    )
    parser.add_argument("--top-k", type=int, default=5, help="Top-k path-level hits to score.")
    parser.add_argument("--chunk-chars", type=int, default=2200, help="Characters per file chunk.")
    parser.add_argument("--overlap-chars", type=int, default=250, help="Chunk overlap in characters.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    corpus_roots = [Path(root) for root in args.corpus_root] if args.corpus_root else list(DEFAULT_CORPUS_ROOTS)
    eval_path = Path(args.eval_path)

    corpus = build_features(load_corpus(corpus_roots, chunk_chars=args.chunk_chars, overlap_chars=args.overlap_chars))
    if not corpus:
        raise SystemExit("No corpus documents loaded. Provide valid --corpus-root paths.")

    eval_items = load_eval_items(eval_path)
    if not eval_items:
        raise SystemExit(f"No eval items loaded from {eval_path}")

    idf = compute_idf(corpus)
    results = evaluate(eval_items, corpus, idf, top_k=args.top_k)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "corpus_roots": [str(path) for path in corpus_roots],
        "eval_path": str(eval_path),
        "corpus_chunks": len(corpus),
        "unique_paths": len({feature.chunk.path for feature in corpus}),
        "top_k": args.top_k,
        **results,
    }
    artifact_path = write_artifact(payload)

    print("Memory overlay benchmark complete")
    print(f"Corpus chunks: {payload['corpus_chunks']} | unique paths: {payload['unique_paths']}")
    for mode, metrics in payload["metrics"].items():
        print(f"{mode}: recall@{args.top_k}={metrics['recall_at_k']:.4f} mrr={metrics['mrr']:.4f}")
    print(f"Artifact: {artifact_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
