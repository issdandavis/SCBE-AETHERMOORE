#!/usr/bin/env python3
"""
Build and query a local RAG index from normalized JSONL records.

Outputs (default):
  data/perplexity/rag_index/index.npz
  data/perplexity/rag_index/documents.jsonl
  data/perplexity/rag_index/manifest.json
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np


DEFAULT_INPUT_TAGGED = Path("data/perplexity/normalized/perplexity_tagged.jsonl")
DEFAULT_INPUT_NORMALIZED = Path("data/perplexity/normalized/perplexity_normalized.jsonl")
DEFAULT_OUTPUT_DIR = Path("data/perplexity/rag_index")
DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_DIMENSION = 384
DEFAULT_HASH_SALT = "scbe-rag-v1"
DEFAULT_TEXT_FIELDS = ("text", "content", "source_text", "title")
DEFAULT_ID_FIELDS = ("id", "thread_id", "cubeId")


@dataclass
class IndexRecord:
    doc_id: str
    text: str
    payload: dict[str, Any]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_input_jsonl() -> Path:
    if DEFAULT_INPUT_TAGGED.exists():
        return DEFAULT_INPUT_TAGGED
    return DEFAULT_INPUT_NORMALIZED


def parse_csv_fields(raw: str, fallback: tuple[str, ...]) -> tuple[str, ...]:
    values = [x.strip() for x in str(raw or "").split(",") if x.strip()]
    return tuple(values) if values else fallback


def clean_text(text: Any) -> str:
    if text is None:
        raw = ""
    else:
        raw = str(text)
    return re.sub(r"\s+", " ", raw).strip()


def tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_']+", text.lower())


def row_normalize(vectors: np.ndarray) -> np.ndarray:
    if vectors.size == 0:
        return vectors
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms = np.where(norms > 0.0, norms, 1.0)
    return vectors / norms


def hashed_embedding(text: str, dimension: int, salt: str) -> np.ndarray:
    tokens = tokenize(text)
    if not tokens:
        tokens = [clean_text(text) or "<empty>"]

    vector = np.zeros((dimension,), dtype=np.float32)
    for tok in tokens:
        digest = hashlib.sha256(f"{salt}|{tok}".encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "little") % dimension
        sign = -1.0 if (digest[4] & 1) else 1.0
        mag = 1.0 + (digest[5] / 255.0)
        vector[idx] += sign * mag

    norm = float(np.linalg.norm(vector))
    if norm > 0.0:
        vector /= norm
    return vector


def embed_hash_texts(texts: Iterable[str], dimension: int, salt: str) -> np.ndarray:
    rows = [hashed_embedding(text, dimension=dimension, salt=salt) for text in texts]
    if not rows:
        return np.zeros((0, dimension), dtype=np.float32)
    return np.vstack(rows).astype(np.float32)


def try_sentence_transformers_encode(
    texts: list[str],
    model_name: str,
    batch_size: int,
) -> np.ndarray:
    try:
        st_mod = importlib.import_module("sentence_transformers")
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            "sentence-transformers is not installed. "
            "Install with: pip install sentence-transformers"
        ) from exc

    model = st_mod.SentenceTransformer(model_name)
    vectors = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    vectors = np.asarray(vectors, dtype=np.float32)
    return row_normalize(vectors)


def embed_texts(
    *,
    texts: list[str],
    backend: str,
    model_name: str,
    dimension: int,
    batch_size: int,
    hash_salt: str,
) -> tuple[np.ndarray, str]:
    if backend in ("auto", "sentence-transformers"):
        try:
            vectors = try_sentence_transformers_encode(
                texts=texts,
                model_name=model_name,
                batch_size=batch_size,
            )
            return vectors.astype(np.float32), "sentence-transformers"
        except Exception:
            if backend == "sentence-transformers":
                raise

    vectors = embed_hash_texts(texts, dimension=dimension, salt=hash_salt)
    return vectors.astype(np.float32), "hash"


def pick_text(payload: dict[str, Any], text_fields: tuple[str, ...]) -> str:
    for field in text_fields:
        if field in payload:
            text = clean_text(payload.get(field))
            if text:
                return text
    return ""


def pick_id(payload: dict[str, Any], *, line_no: int, id_fields: tuple[str, ...]) -> str:
    for field in id_fields:
        value = payload.get(field)
        if value is not None:
            value_s = clean_text(value)
            if value_s:
                if field == "thread_id" and "turn_index" in payload:
                    turn = clean_text(payload.get("turn_index"))
                    if turn:
                        return f"{value_s}:{turn}"
                return value_s

    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]  # noqa: S324
    return f"line-{line_no}-{digest}"


def load_index_records(
    *,
    input_jsonl: Path,
    text_fields: tuple[str, ...],
    id_fields: tuple[str, ...],
    min_text_chars: int,
    max_records: int,
) -> tuple[list[IndexRecord], dict[str, int]]:
    if not input_jsonl.exists():
        raise FileNotFoundError(f"Input JSONL not found: {input_jsonl}")

    records: list[IndexRecord] = []
    seen_ids: set[str] = set()
    stats = {
        "rows_seen": 0,
        "rows_kept": 0,
        "rows_invalid_json": 0,
        "rows_missing_text": 0,
    }

    with input_jsonl.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            stats["rows_seen"] += 1

            try:
                payload = json.loads(line)
            except Exception:  # noqa: BLE001
                stats["rows_invalid_json"] += 1
                continue
            if not isinstance(payload, dict):
                stats["rows_invalid_json"] += 1
                continue

            text = pick_text(payload, text_fields=text_fields)
            if len(text) < min_text_chars:
                stats["rows_missing_text"] += 1
                continue

            doc_id = pick_id(payload, line_no=line_no, id_fields=id_fields)
            if doc_id in seen_ids:
                suffix = hashlib.sha1(f"{line_no}|{doc_id}".encode("utf-8")).hexdigest()[:8]  # noqa: S324
                doc_id = f"{doc_id}#{suffix}"
            seen_ids.add(doc_id)

            records.append(IndexRecord(doc_id=doc_id, text=text, payload=payload))
            stats["rows_kept"] += 1

            if max_records > 0 and len(records) >= max_records:
                break

    return records, stats


def write_index_files(
    *,
    output_dir: Path,
    records: list[IndexRecord],
    vectors: np.ndarray,
    input_jsonl: Path,
    embedding_backend: str,
    model_name: str,
    hash_salt: str,
    text_fields: tuple[str, ...],
    id_fields: tuple[str, ...],
    min_text_chars: int,
    max_records: int,
    load_stats: dict[str, int],
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    index_path = output_dir / "index.npz"
    docs_path = output_dir / "documents.jsonl"
    manifest_path = output_dir / "manifest.json"

    ids = np.array([r.doc_id for r in records])
    np.savez_compressed(index_path, vectors=vectors.astype(np.float32), ids=ids)

    with docs_path.open("w", encoding="utf-8", newline="\n") as f:
        for rec in records:
            f.write(
                json.dumps(
                    {"id": rec.doc_id, "text": rec.text, "payload": rec.payload},
                    ensure_ascii=False,
                )
                + "\n"
            )

    summary = {
        "generated_at": utc_now(),
        "input_jsonl": str(input_jsonl),
        "output_dir": str(output_dir),
        "record_count": int(len(records)),
        "dimension": int(vectors.shape[1]) if vectors.ndim == 2 and vectors.size else 0,
        "embedding_backend": embedding_backend,
        "model_name": model_name if embedding_backend == "sentence-transformers" else None,
        "hash_salt": hash_salt if embedding_backend == "hash" else None,
        "text_fields": list(text_fields),
        "id_fields": list(id_fields),
        "min_text_chars": int(min_text_chars),
        "max_records": int(max_records),
        "load_stats": load_stats,
        "files": {
            "index": str(index_path),
            "documents": str(docs_path),
            "manifest": str(manifest_path),
        },
    }
    manifest_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def build_rag_index(
    *,
    input_jsonl: Path,
    output_dir: Path,
    text_fields: tuple[str, ...],
    id_fields: tuple[str, ...],
    min_text_chars: int,
    max_records: int,
    backend: str,
    model_name: str,
    dimension: int,
    batch_size: int,
    hash_salt: str,
) -> dict[str, Any]:
    records, load_stats = load_index_records(
        input_jsonl=input_jsonl,
        text_fields=text_fields,
        id_fields=id_fields,
        min_text_chars=min_text_chars,
        max_records=max_records,
    )
    if not records:
        raise RuntimeError("No records eligible for indexing.")

    texts = [r.text for r in records]
    vectors, backend_used = embed_texts(
        texts=texts,
        backend=backend,
        model_name=model_name,
        dimension=dimension,
        batch_size=batch_size,
        hash_salt=hash_salt,
    )
    vectors = row_normalize(vectors.astype(np.float32))

    return write_index_files(
        output_dir=output_dir,
        records=records,
        vectors=vectors,
        input_jsonl=input_jsonl,
        embedding_backend=backend_used,
        model_name=model_name,
        hash_salt=hash_salt,
        text_fields=text_fields,
        id_fields=id_fields,
        min_text_chars=min_text_chars,
        max_records=max_records,
        load_stats=load_stats,
    )


def load_saved_index(index_dir: Path) -> tuple[np.ndarray, list[str], dict[str, Any], dict[str, dict[str, Any]]]:
    index_path = index_dir / "index.npz"
    docs_path = index_dir / "documents.jsonl"
    manifest_path = index_dir / "manifest.json"
    if not index_path.exists():
        raise FileNotFoundError(f"Missing index file: {index_path}")
    if not docs_path.exists():
        raise FileNotFoundError(f"Missing documents file: {docs_path}")
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest file: {manifest_path}")

    blob = np.load(index_path)
    vectors = np.asarray(blob["vectors"], dtype=np.float32)
    ids = [str(x) for x in blob["ids"].tolist()]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    docs: dict[str, dict[str, Any]] = {}
    with docs_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:  # noqa: BLE001
                continue
            row_id = clean_text(row.get("id"))
            if row_id:
                docs[row_id] = row

    return vectors, ids, manifest, docs


def query_rag_index(
    *,
    index_dir: Path,
    query: str,
    top_k: int,
) -> list[dict[str, Any]]:
    vectors, ids, manifest, docs = load_saved_index(index_dir=index_dir)
    if vectors.size == 0 or not ids:
        return []
    if top_k <= 0:
        return []

    backend = str(manifest.get("embedding_backend") or "hash")
    model_name = str(manifest.get("model_name") or DEFAULT_MODEL_NAME)
    dimension = int(manifest.get("dimension") or DEFAULT_DIMENSION)
    hash_salt = str(manifest.get("hash_salt") or DEFAULT_HASH_SALT)

    query_vecs, _ = embed_texts(
        texts=[query],
        backend=backend,
        model_name=model_name,
        dimension=dimension,
        batch_size=1,
        hash_salt=hash_salt,
    )
    query_vec = row_normalize(query_vecs)[0]

    scores = vectors @ query_vec
    k = min(top_k, len(ids))
    top_idx = np.argpartition(-scores, k - 1)[:k]
    ranked = sorted(top_idx.tolist(), key=lambda i: float(scores[i]), reverse=True)

    results: list[dict[str, Any]] = []
    for i in ranked:
        doc_id = ids[i]
        row = docs.get(doc_id, {"id": doc_id, "text": "", "payload": {}})
        results.append(
            {
                "id": doc_id,
                "score": float(scores[i]),
                "text": row.get("text", ""),
                "payload": row.get("payload", {}),
            }
        )
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build/query a local RAG index from JSONL records."
    )
    parser.add_argument("--input-jsonl", default=str(default_input_jsonl()))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--text-fields", default=",".join(DEFAULT_TEXT_FIELDS))
    parser.add_argument("--id-fields", default=",".join(DEFAULT_ID_FIELDS))
    parser.add_argument("--min-text-chars", type=int, default=8)
    parser.add_argument("--max-records", type=int, default=0)
    parser.add_argument(
        "--backend",
        choices=("auto", "hash", "sentence-transformers"),
        default="auto",
    )
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--dimension", type=int, default=DEFAULT_DIMENSION)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--hash-salt", default=DEFAULT_HASH_SALT)
    parser.add_argument("--query", default="")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--query-only", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    text_fields = parse_csv_fields(args.text_fields, DEFAULT_TEXT_FIELDS)
    id_fields = parse_csv_fields(args.id_fields, DEFAULT_ID_FIELDS)
    output_dir = Path(args.output_dir)

    try:
        if not args.query_only:
            summary = build_rag_index(
                input_jsonl=Path(args.input_jsonl),
                output_dir=output_dir,
                text_fields=text_fields,
                id_fields=id_fields,
                min_text_chars=int(args.min_text_chars),
                max_records=int(args.max_records),
                backend=str(args.backend),
                model_name=str(args.model_name),
                dimension=int(args.dimension),
                batch_size=int(args.batch_size),
                hash_salt=str(args.hash_salt),
            )
            print(json.dumps(summary, indent=2))

        if args.query:
            results = query_rag_index(
                index_dir=output_dir,
                query=str(args.query),
                top_k=int(args.top_k),
            )
            print(json.dumps({"query": args.query, "results": results}, indent=2))
    except Exception as exc:  # noqa: BLE001
        print(f"[build_rag_index] ERROR: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
