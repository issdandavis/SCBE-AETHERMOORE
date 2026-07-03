#!/usr/bin/env python
"""Convert a real coder corpus into SCBE multi-view training rows.

Corpus choice: CodeSearchNet.

Why this corpus:
  - function-level code records
  - paired natural-language documentation
  - multiple programming languages
  - small enough to stream samples locally

Outputs:
  artifacts/coder_corpus_labyrinth/corpus_multiview.jsonl
  artifacts/coder_corpus_labyrinth/labyrinth_graph.json
  artifacts/coder_corpus_labyrinth/research_brief.md
  artifacts/coder_corpus_labyrinth/receipt.json

The "labyrinth" is not a Pac-Man clone. It is a goal graph:
doc -> signature -> operations -> SCBE tokens -> binary -> verifier gate.
Each record gets a path through that graph, so curriculum/training can target
where a model fails instead of treating code as one flat string.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from collections import Counter, defaultdict
from itertools import islice
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
OUT_ROOT = ROOT / "artifacts" / "coder_corpus_labyrinth"

SOURCES = [
    {
        "name": "CodeSearchNet paper",
        "url": "https://arxiv.org/abs/1909.09436",
        "claim": "Function-level code corpus with natural-language documentation across Go, Java, JavaScript, PHP, Python, and Ruby.",
    },
    {
        "name": "CodeSearchNet GitHub",
        "url": "https://github.com/github/CodeSearchNet",
        "claim": "Open dataset and benchmark for semantic code search.",
    },
    {
        "name": "The Stack v2 dataset card",
        "url": "https://huggingface.co/datasets/bigcode/the-stack-v2",
        "claim": "Large code-pretraining corpus with billions of files across hundreds of languages.",
    },
    {
        "name": "StarCoder2 / The Stack v2 paper",
        "url": "https://arxiv.org/abs/2402.19173",
        "claim": "Modern coder model corpus stack combines Software Heritage code, GitHub pull requests, Kaggle notebooks, and documentation.",
    },
]

LANE_WORDS = {
    "KO": "kor-vael",
    "AV": "av-sai",
    "RU": "ru-thar",
    "CA": "ca-forge",
    "DR": "draum-sel",
}

OP_WORD = {
    "function": "bip'fn",
    "return": "bip'out",
    "branch": "fork'ra",
    "loop": "wheel'a",
    "call": "call'an",
    "math": "bip'a",
    "compare": "mira'voth",
    "index": "slot'a",
    "assign": "bind'a",
    "import": "gate'in",
    "exception": "guard'a",
    "class": "house'a",
    "io": "mouth'a",
}

NODE_ORDER = [
    "doc_intent",
    "language_id",
    "signature_shape",
    "operation_bag",
    "binary_view",
    "scbe_phase_tokens",
    "verifier_gate",
    "training_row",
]

CODESEARCHNET_LANGUAGES = ("go", "java", "javascript", "php", "python", "ruby")


def load_codesearchnet(language: str, limit: int) -> list[dict[str, Any]]:
    from datasets import load_dataset

    stream = load_dataset("code_search_net", language, split="train", streaming=True)
    rows = []
    for raw in islice(stream, limit):
        rows.append(raw)
    return rows


def normalize_record(raw: dict[str, Any]) -> dict[str, str]:
    code = raw.get("whole_func_string") or raw.get("func_code_string") or ""
    doc = raw.get("func_documentation_string") or ""
    return {
        "language": str(raw.get("language") or "unknown"),
        "repository": str(raw.get("repository_name") or ""),
        "path": str(raw.get("func_path_in_repository") or ""),
        "name": str(raw.get("func_name") or ""),
        "doc": clean_text(doc),
        "code": code,
        "url": str(raw.get("func_code_url") or ""),
    }


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def infer_ops(code: str, language: str) -> list[str]:
    lower = code.lower()
    ops = []
    if re.search(r"\b(def|function|func|fn)\b", lower):
        ops.append("function")
    if re.search(r"\bclass\b", lower):
        ops.append("class")
    if re.search(r"\breturn\b", lower):
        ops.append("return")
    if re.search(r"\b(if|else|elif|switch|case)\b", lower):
        ops.append("branch")
    if re.search(r"\b(for|while|foreach|map|filter|reduce)\b", lower):
        ops.append("loop")
    if re.search(r"\b(import|from|require|include|using)\b", lower):
        ops.append("import")
    if re.search(r"\b(try|except|catch|finally|raise|throw)\b", lower):
        ops.append("exception")
    if re.search(r"[-+*/%]|math\.|numpy|np\.", lower):
        ops.append("math")
    if re.search(r"==|!=|<=|>=|<|>| and | or |&&|\|\|", lower):
        ops.append("compare")
    if re.search(r"\[[^\]]+\]", code):
        ops.append("index")
    if re.search(r"(^|[^=!<>])=([^=]|$)", code):
        ops.append("assign")
    if re.search(r"\w+\s*\(", code):
        ops.append("call")
    if re.search(r"\b(print|read|write|open|input|stdout|stdin|file)\b", lower):
        ops.append("io")
    if not ops:
        ops.append("function" if language == "python" else "call")
    return sorted(dict.fromkeys(ops))


def binary_view(code: str, max_bytes: int = 256) -> dict[str, Any]:
    data = code.encode("utf-8", errors="replace")[:max_bytes]
    return {
        "encoding": "utf8",
        "byte_len_sampled": len(data),
        "sha256": hashlib.sha256(code.encode("utf-8", errors="replace")).hexdigest(),
        "hex_prefix": data[:64].hex(),
        "bit_prefix": "".join(f"{byte:08b}" for byte in data[:32]),
    }


def scbe_tokens(record: dict[str, str], ops: list[str], digest: str) -> list[str]:
    lang = safe_atom(record["language"])
    name = safe_atom(record["name"] or "anonymous")
    doc_words = [safe_atom(w) for w in re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", record["doc"])[:8]]
    ca_words = [OP_WORD.get(op, "ca-forge") for op in ops]
    return [
        "KO",
        LANE_WORDS["KO"],
        *doc_words,
        "AV",
        LANE_WORDS["AV"],
        f"lang:{lang}",
        f"name:{name}",
        "RU",
        LANE_WORDS["RU"],
        f"source:{digest[:12]}",
        *sum((["CA", word] for word in ca_words), []),
        "DR",
        LANE_WORDS["DR"],
        f"seal:{digest[:16]}",
    ]


def safe_atom(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_'-]+", "_", str(value).strip().lower())
    return value[:48] or "x"


def verify_record(record: dict[str, str], ops: list[str]) -> dict[str, Any]:
    if record["language"] == "python":
        try:
            ast.parse(record["code"])
            syntax_ok = True
            syntax_error = None
        except SyntaxError as exc:
            syntax_ok = False
            syntax_error = f"{exc.__class__.__name__}: {exc.msg}"
    else:
        # Non-Python syntax verification is intentionally weak until a runner is wired.
        opens = record["code"].count("{") + record["code"].count("(") + record["code"].count("[")
        closes = record["code"].count("}") + record["code"].count(")") + record["code"].count("]")
        syntax_ok = abs(opens - closes) <= 3
        syntax_error = None if syntax_ok else "brace/paren balance failed"
    return {
        "syntax_ok": syntax_ok,
        "syntax_error": syntax_error,
        "has_doc": bool(record["doc"]),
        "has_name": bool(record["name"]),
        "ops_count": len(ops),
        "path_ok": syntax_ok and bool(ops),
    }


def make_multiview(raw: dict[str, Any], idx: int) -> dict[str, Any]:
    record = normalize_record(raw)
    ops = infer_ops(record["code"], record["language"])
    bview = binary_view(record["code"])
    tokens = scbe_tokens(record, ops, bview["sha256"])
    verifier = verify_record(record, ops)
    path = [
        {"node": "doc_intent", "value": record["doc"][:220]},
        {"node": "language_id", "value": record["language"]},
        {"node": "signature_shape", "value": record["name"]},
        {"node": "operation_bag", "value": ops},
        {"node": "binary_view", "value": bview["sha256"][:16]},
        {"node": "scbe_phase_tokens", "value": tokens[:18]},
        {"node": "verifier_gate", "value": verifier},
        {"node": "training_row", "value": "emit"},
    ]
    return {
        "id": f"codesearchnet:{record['language']}:{idx}:{bview['sha256'][:12]}",
        "source": {
            "dataset": "code_search_net",
            "language": record["language"],
            "repository": record["repository"],
            "path": record["path"],
            "url": record["url"],
        },
        "views": {
            "natural_language": {
                "doc": record["doc"],
                "name": record["name"],
            },
            "code": {
                "language": record["language"],
                "text": record["code"],
            },
            "ops": ops,
            "binary": bview,
            "scbe_tokens": tokens,
            "labyrinth_path": path,
        },
        "verifier": verifier,
        "training_targets": {
            "doc_to_code": record["code"],
            "doc_to_ops": ops,
            "code_to_doc": record["doc"],
            "code_to_scbe_tokens": " ".join(tokens),
            "code_to_binary_prefix": bview["bit_prefix"],
            "path_to_goal": [step["node"] for step in path],
        },
    }


def build_labyrinth(rows: list[dict[str, Any]]) -> dict[str, Any]:
    node_counts = Counter()
    edge_counts = Counter()
    op_counts = Counter()
    language_counts = Counter()
    verifier_counts = Counter()
    for row in rows:
        nodes = [step["node"] for step in row["views"]["labyrinth_path"]]
        for node in nodes:
            node_counts[node] += 1
        for a, b in zip(nodes, nodes[1:]):
            edge_counts[(a, b)] += 1
        for op in row["views"]["ops"]:
            op_counts[op] += 1
        language_counts[row["source"]["language"]] += 1
        verifier_counts["syntax_ok" if row["verifier"]["syntax_ok"] else "syntax_failed"] += 1
    return {
        "description": "Goal graph for navigating coder-corpus rows through SCBE training views.",
        "nodes": [{"id": node, "count": node_counts[node]} for node in NODE_ORDER],
        "edges": [{"from": a, "to": b, "count": count} for (a, b), count in edge_counts.items()],
        "operation_counts": dict(op_counts.most_common()),
        "language_counts": dict(language_counts.most_common()),
        "verifier_counts": dict(verifier_counts.most_common()),
        "recommended_curriculum": [
            "doc_intent -> language_id",
            "language_id -> signature_shape",
            "signature_shape -> operation_bag",
            "operation_bag -> scbe_phase_tokens",
            "scbe_phase_tokens -> binary_view",
            "binary_view -> verifier_gate",
            "verifier_gate -> training_row",
        ],
    }


def write_research_brief(path: Path, limit: int, language: str) -> None:
    lines = [
        "# Coder Corpus Stack Brief",
        "",
        "A modern general coder corpus is usually layered, not just one pile of files:",
        "",
        "1. Raw source files across many languages.",
        "2. Function/method-level slices with signatures and local context.",
        "3. Natural-language documentation, comments, issues, pull requests, notebooks, and Q&A.",
        "4. Deduplication, license/PII filtering, quality filtering, and language balancing.",
        "5. Evaluation and verifier sets separate from training.",
        "",
        "For this first SCBE converter, CodeSearchNet is the practical starting point because it already pairs functions with natural-language documentation.",
        f"This run streamed `{limit}` `{language}` records from Hugging Face `code_search_net`.",
        "",
        "## Sources",
        "",
    ]
    for source in SOURCES:
        lines.append(f"- [{source['name']}]({source['url']}): {source['claim']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", default="python")
    parser.add_argument("--all", action="store_true", help="run all CodeSearchNet language configs")
    parser.add_argument("--limit", type=int, default=80)
    args = parser.parse_args()

    if args.all:
        receipts = []
        for language in CODESEARCHNET_LANGUAGES:
            receipts.append(run_language(language, args.limit))
        combined = {
            "ok": all(item["ok"] for item in receipts),
            "kind": "coder_corpus_labyrinth_all_codesearchnet",
            "languages": list(CODESEARCHNET_LANGUAGES),
            "limit_per_language": args.limit,
            "total_rows": sum(item["rows"] for item in receipts),
            "total_path_ok_rows": sum(item["path_ok_rows"] for item in receipts),
            "runs": receipts,
        }
        combined["path_ok_rate"] = round(combined["total_path_ok_rows"] / max(1, combined["total_rows"]), 4)
        OUT_ROOT.mkdir(parents=True, exist_ok=True)
        combined_path = OUT_ROOT / f"all_codesearchnet_{args.limit}_manifest.json"
        combined_path.write_text(json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8")
        print("CODER_CORPUS_LABYRINTH_ALL_DONE")
        print(f"languages: {', '.join(CODESEARCHNET_LANGUAGES)}")
        print(f"rows: {combined['total_rows']} path_ok: {combined['total_path_ok_rows']}/{combined['total_rows']} ({combined['path_ok_rate']})")
        print(f"manifest: {combined_path}")
        return 0 if combined["ok"] else 1

    receipt = run_language(args.language, args.limit)
    print("CODER_CORPUS_LABYRINTH_DONE")
    print(f"dataset: code_search_net language: {args.language} rows: {receipt['rows']}")
    print(f"path_ok: {receipt['path_ok_rows']}/{receipt['rows']} ({receipt['path_ok_rate']})")
    print("top_ops:", dict(list(receipt["operation_counts"].items())[:10]))
    print(f"receipt: {receipt['artifacts']['receipt']}")
    return 0 if receipt["ok"] else 1


def run_language(language: str, limit: int) -> dict[str, Any]:
    out_dir = OUT_ROOT / f"{safe_atom(language)}_{limit}"
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_rows = load_codesearchnet(language, limit)
    rows = [make_multiview(raw, idx) for idx, raw in enumerate(raw_rows)]
    graph = build_labyrinth(rows)

    corpus_path = out_dir / "corpus_multiview.jsonl"
    with corpus_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    graph_path = out_dir / "labyrinth_graph.json"
    graph_path.write_text(json.dumps(graph, indent=2, ensure_ascii=False), encoding="utf-8")

    brief_path = out_dir / "research_brief.md"
    write_research_brief(brief_path, limit, language)

    ok_rows = sum(1 for row in rows if row["verifier"]["path_ok"])
    receipt_path = out_dir / "receipt.json"
    receipt = {
        "ok": True,
        "kind": "coder_corpus_labyrinth",
        "dataset": "code_search_net",
        "language": language,
        "limit": limit,
        "rows": len(rows),
        "path_ok_rows": ok_rows,
        "path_ok_rate": round(ok_rows / max(1, len(rows)), 4),
        "operation_counts": graph["operation_counts"],
        "language_counts": graph["language_counts"],
        "verifier_counts": graph["verifier_counts"],
        "artifacts": {
            "corpus_multiview": str(corpus_path),
            "labyrinth_graph": str(graph_path),
            "research_brief": str(brief_path),
            "receipt": str(receipt_path),
        },
        "sources": SOURCES,
    }
    receipt["artifacts"]["receipt"] = str(receipt_path)
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
    return receipt


if __name__ == "__main__":
    raise SystemExit(main())
