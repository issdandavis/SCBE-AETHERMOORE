#!/usr/bin/env python3
"""Benchmark HyperSphereIndex against full-scan cosine baseline."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import random
import statistics
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.storage.hypersphere_index import HyperSphereIndex


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _norm(v: list[float]) -> float:
    return _dot(v, v) ** 0.5


def _normalize(v: list[float]) -> list[float]:
    n = _norm(v)
    if n == 0.0:
        return [0.0 for _ in v]
    return [x / n for x in v]


def _cosine(a: list[float], b: list[float]) -> float:
    denom = _norm(a) * _norm(b)
    if denom == 0.0:
        return 0.0
    return _dot(a, b) / denom


@dataclass
class Doc:
    doc_id: str
    vector: list[float]
    topic: int


def _random_ball_vector(rng: random.Random, dims: int, radius: float) -> list[float]:
    direction = [rng.gauss(0.0, 1.0) for _ in range(dims)]
    direction = _normalize(direction)
    scaled_radius = rng.random() * radius
    return [x * scaled_radius for x in direction]


def build_dataset(
    *, rng: random.Random, doc_count: int, dims: int, topic_count: int
) -> tuple[list[Doc], list[list[float]]]:
    centers = [_random_ball_vector(rng, dims, 0.7) for _ in range(topic_count)]
    docs: list[Doc] = []
    for i in range(doc_count):
        topic = rng.randrange(topic_count)
        center = centers[topic]
        noise = [rng.gauss(0.0, 0.08) for _ in range(dims)]
        vector = [center[d] + noise[d] for d in range(dims)]
        docs.append(Doc(doc_id=f"doc-{i}", vector=vector, topic=topic))
    return docs, centers


def make_queries(*, rng: random.Random, centers: list[list[float]], query_count: int) -> list[tuple[list[float], int]]:
    queries: list[tuple[list[float], int]] = []
    for _ in range(query_count):
        topic = rng.randrange(len(centers))
        center = centers[topic]
        noise = [rng.gauss(0.0, 0.07) for _ in range(len(center))]
        query = [center[d] + noise[d] for d in range(len(center))]
        queries.append((query, topic))
    return queries


def baseline_search(query: list[float], docs: list[Doc], top_k: int) -> list[Doc]:
    scored = [(_cosine(query, doc.vector), doc) for doc in docs]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [doc for _, doc in scored[:top_k]]


def evaluate_hits(hits_topic: list[int], expected_topic: int) -> float:
    if not hits_topic:
        return 0.0
    return sum(1 for topic in hits_topic if topic == expected_topic) / len(hits_topic)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark HyperSphereIndex vs cosine full scan.")
    parser.add_argument("--docs", type=int, default=5000)
    parser.add_argument("--queries", type=int, default=300)
    parser.add_argument("--topics", type=int, default=12)
    parser.add_argument("--dims", type=int, default=6)
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--layer-window", type=int, default=1)
    parser.add_argument("--candidate-cap", type=int, default=1800)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rng = random.Random(args.seed)
    docs, centers = build_dataset(rng=rng, doc_count=args.docs, dims=args.dims, topic_count=args.topics)
    queries = make_queries(rng=rng, centers=centers, query_count=args.queries)

    index = HyperSphereIndex(dimensions=args.dims, layer_count=8, max_radius=0.95)
    topic_by_id: dict[str, int] = {}
    for doc in docs:
        index.add(doc_id=doc.doc_id, text=doc.doc_id, vector=doc.vector, metadata={"topic": doc.topic})
        topic_by_id[doc.doc_id] = doc.topic

    hyper_latencies_ms: list[float] = []
    baseline_latencies_ms: list[float] = []
    hyper_precisions: list[float] = []
    baseline_precisions: list[float] = []

    for query, expected_topic in queries:
        t0 = time.perf_counter()
        hyper_hits = index.search(
            query_vector=query,
            top_k=args.top_k,
            layer_window=args.layer_window,
            candidate_cap=args.candidate_cap,
        )
        hyper_latencies_ms.append((time.perf_counter() - t0) * 1000.0)

        t1 = time.perf_counter()
        baseline_hits = baseline_search(query, docs, args.top_k)
        baseline_latencies_ms.append((time.perf_counter() - t1) * 1000.0)

        hyper_topics = [topic_by_id[hit.doc_id] for hit in hyper_hits]
        baseline_topics = [doc.topic for doc in baseline_hits]
        hyper_precisions.append(evaluate_hits(hyper_topics, expected_topic))
        baseline_precisions.append(evaluate_hits(baseline_topics, expected_topic))

    result = {
        "schema_version": "scbe_hypersphere_benchmark_v1",
        "config": {
            "docs": args.docs,
            "queries": args.queries,
            "topics": args.topics,
            "dims": args.dims,
            "top_k": args.top_k,
            "layer_window": args.layer_window,
            "candidate_cap": args.candidate_cap,
            "seed": args.seed,
        },
        "index": {
            "size": index.size,
            "layer_sizes": index.layer_sizes(),
        },
        "metrics": {
            "hypersphere_precision_at_k": round(statistics.mean(hyper_precisions), 6),
            "baseline_precision_at_k": round(statistics.mean(baseline_precisions), 6),
            "hypersphere_p95_ms": round(statistics.quantiles(hyper_latencies_ms, n=20)[18], 4),
            "baseline_p95_ms": round(statistics.quantiles(baseline_latencies_ms, n=20)[18], 4),
            "hypersphere_mean_ms": round(statistics.mean(hyper_latencies_ms), 4),
            "baseline_mean_ms": round(statistics.mean(baseline_latencies_ms), 4),
        },
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
