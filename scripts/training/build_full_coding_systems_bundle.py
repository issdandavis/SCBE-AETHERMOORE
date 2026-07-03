#!/usr/bin/env python
"""Build a full SCBE coding-systems training bundle.

Inputs:
  - artifacts/coder_corpus_labyrinth/*/corpus_multiview.jsonl
  - artifacts/rosetta_seed/dataset.jsonl
  - curated markdown/docs from scoped repo roots

Outputs:
  - artifacts/full_coding_systems_bundle/training_bundle.jsonl
  - artifacts/full_coding_systems_bundle/manual_parameter_bank.json
  - artifacts/full_coding_systems_bundle/labyrinth_curriculum.json
  - artifacts/full_coding_systems_bundle/receipt.json

This is not a fine-tune runner. It is the data/parameter-seed layer that makes a
fine-tune sane: one concept preserved across code, English, binary, SCBE tokens,
verification gates, and curated lore/creation notes.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import re
import zipfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
CODER_ROOT = ROOT / "artifacts" / "coder_corpus_labyrinth"
ROSETTA_DATASET = ROOT / "artifacts" / "rosetta_seed" / "dataset.jsonl"
LANGUAGE_ATLAS_ROWS = ROOT / "artifacts" / "language_systems_atlas" / "language_systems_training_rows.jsonl"
COORDINATION_GRAPH_ROWS = ROOT / "artifacts" / "language_systems_atlas" / "code_coordination_graph_training_rows.jsonl"
RECOVERED_ROOT = Path("D:/Recovery/_RECOVERED")
OUT_DIR = ROOT / "artifacts" / "full_coding_systems_bundle"

DOC_ROOTS = [
    ROOT / "docs" / "books",
    ROOT / "docs" / "research",
    ROOT / "docs" / "specs",
    ROOT / "docs" / "map-room",
    ROOT / "docs" / "system",
    ROOT / "docs" / "superpowers",
]

SECRET_PATTERNS = [
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{12,})"),
    re.compile(r"hf_[A-Za-z0-9]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
]

BINARY_MODES = ("utf8", "bytes", "hex", "bits", "nibbles", "base64", "byte_hist", "sha256")


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def scrub(text: str) -> str:
    out = str(text or "")
    for pattern in SECRET_PATTERNS:
        out = pattern.sub(lambda m: f"{m.group(1)}=<REDACTED>", out)
    return out


def stable_id(*parts: str) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(str(part).encode("utf-8", errors="replace"))
        h.update(b"\x00")
    return h.hexdigest()[:24]


def binary_views(text: str, max_bytes: int = 512) -> dict[str, Any]:
    data = scrub(text).encode("utf-8", errors="replace")
    sample = data[:max_bytes]
    hist = Counter(sample)
    total = max(1, len(sample))
    entropy = -sum((count / total) * math.log2(count / total) for count in hist.values())
    return {
        "utf8": sample.decode("utf-8", errors="replace"),
        "bytes": list(sample[:96]),
        "hex": sample[:192].hex(),
        "bits": "".join(f"{byte:08b}" for byte in sample[:64]),
        "nibbles": " ".join(f"{byte >> 4:x} {byte & 0x0f:x}" for byte in sample[:64]),
        "base64": base64.b64encode(sample[:192]).decode("ascii"),
        "base64url": base64.urlsafe_b64encode(sample[:192]).decode("ascii"),
        "ascii85": base64.a85encode(sample[:192]).decode("ascii", errors="replace"),
        "byte_hist": {str(k): hist[k] for k in sorted(hist)[:128]},
        "sha256": hashlib.sha256(data).hexdigest(),
        "sample_bytes": len(sample),
        "full_bytes": len(data),
        "entropy": round(entropy, 4),
    }


def add_row(rows: list[dict[str, Any]], *, lane: str, task: str, source: dict[str, Any], prompt: str, response: str, views: dict[str, Any] | None = None) -> None:
    prompt = scrub(prompt)
    response = scrub(response)
    row_id = stable_id(lane, task, source.get("id", ""), prompt, response)
    rows.append(
        {
            "id": row_id,
            "lane": lane,
            "task": task,
            "prompt": prompt,
            "response": response,
            "views": views or {},
            "metadata": {
                "source": source,
                "validated": bool(source.get("validated", False)),
                "binary_modes": list(BINARY_MODES),
            },
        }
    )


def load_coder_rows(limit_per_language: int | None = None) -> list[dict[str, Any]]:
    files = sorted(CODER_ROOT.glob("*_*/corpus_multiview.jsonl"))
    selected = []
    per_lang_counts: dict[str, int] = defaultdict(int)
    for file in files:
        for row in iter_jsonl(file):
            language = row.get("source", {}).get("language", "unknown")
            if limit_per_language is not None and per_lang_counts[language] >= limit_per_language:
                continue
            per_lang_counts[language] += 1
            selected.append(row)
    return selected


def expand_coder_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        source = {
            "id": row["id"],
            "kind": "coder_corpus",
            "dataset": row["source"].get("dataset"),
            "language": row["source"].get("language"),
            "url": row["source"].get("url"),
            "validated": row.get("verifier", {}).get("path_ok", False),
        }
        doc = row["views"]["natural_language"].get("doc", "")
        name = row["views"]["natural_language"].get("name", "")
        code = row["views"]["code"].get("text", "")
        language = row["views"]["code"].get("language", "unknown")
        ops = row["views"].get("ops", [])
        scbe = " ".join(row["views"].get("scbe_tokens", []))
        bviews = binary_views(code)
        path_nodes = [step["node"] for step in row["views"].get("labyrinth_path", [])]
        verifier = row.get("verifier", {})

        add_row(
            out,
            lane="coding",
            task="doc_to_code",
            source=source,
            prompt=f"Language: {language}\nFunction name: {name}\nDoc: {doc}\nWrite the function.",
            response=code,
            views={"ops": ops, "scbe_tokens": scbe, "binary": bviews},
        )
        add_row(
            out,
            lane="coding",
            task="code_to_ops",
            source=source,
            prompt=f"Language: {language}\nCode:\n{code}\nInfer the operation bag.",
            response=json.dumps(ops, ensure_ascii=False),
            views={"binary": bviews},
        )
        add_row(
            out,
            lane="coding",
            task="code_to_scbe_tokens",
            source=source,
            prompt=f"Convert this {language} code into SCBE phase tokens:\n{code}",
            response=scbe,
            views={"ops": ops, "binary": bviews},
        )
        add_row(
            out,
            lane="binary",
            task="code_to_binary_views",
            source=source,
            prompt=f"Encode this {language} function into binary views:\n{code}",
            response=json.dumps({k: bviews[k] for k in BINARY_MODES}, ensure_ascii=False),
            views={"entropy": bviews["entropy"], "sample_bytes": bviews["sample_bytes"]},
        )
        add_row(
            out,
            lane="labyrinth",
            task="path_to_goal",
            source=source,
            prompt=f"Given doc/code/ops, choose the path through the coding labyrinth.\nDoc: {doc}\nOps: {ops}",
            response=" -> ".join(path_nodes),
            views={"path_nodes": path_nodes, "verifier": verifier},
        )
        add_row(
            out,
            lane="governance",
            task="predict_verifier_gate",
            source=source,
            prompt=f"Check whether this corpus row is usable for training.\nLanguage: {language}\nOps: {ops}\nCode hash: {bviews['sha256']}",
            response=json.dumps(verifier, ensure_ascii=False),
            views={"path_nodes": path_nodes},
        )
    return out


def expand_rosetta_rows(limit: int | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not ROSETTA_DATASET.exists():
        return out
    for idx, rec in enumerate(iter_jsonl(ROSETTA_DATASET)):
        if limit is not None and idx >= limit:
            break
        text = rec.get("text", "")
        code = rec.get("code", "")
        source = {
            "id": f"rosetta:{idx}",
            "kind": "rosetta_seed",
            "validated": bool(rec.get("valid", 0)),
        }
        add_row(
            out,
            lane="rosetta",
            task="conlang_to_program",
            source=source,
            prompt=f"Decode this SCBE conlang sentence into executable meaning:\n{text}",
            response=json.dumps({"program": rec.get("program"), "result": rec.get("result"), "code": code}, ensure_ascii=False),
            views={"binary": binary_views(code), "tokens": rec.get("tokens", [])},
        )
    return out


def expand_language_atlas_rows(limit: int | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not LANGUAGE_ATLAS_ROWS.exists():
        return out
    for idx, rec in enumerate(iter_jsonl(LANGUAGE_ATLAS_ROWS)):
        if limit is not None and idx >= limit:
            break
        source = {
            "id": rec.get("id", f"language_atlas:{idx}"),
            "kind": "language_systems_atlas",
            "validated": bool(rec.get("metadata", {}).get("validated")),
            "manual_url": rec.get("metadata", {}).get("manual_url"),
        }
        add_row(
            out,
            lane=rec.get("lane", "language_primary"),
            task=rec.get("task", "language_mapping"),
            source=source,
            prompt=rec.get("prompt", ""),
            response=rec.get("response", ""),
            views=rec.get("views", {}),
        )
    return out


def expand_coordination_graph_rows(limit: int | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not COORDINATION_GRAPH_ROWS.exists():
        return out
    for idx, rec in enumerate(iter_jsonl(COORDINATION_GRAPH_ROWS)):
        if limit is not None and idx >= limit:
            break
        source = {
            "id": rec.get("id", f"coordination_graph:{idx}"),
            "kind": "code_coordination_graph",
            "validated": bool(rec.get("metadata", {}).get("validated")),
            "graph_artifact": rec.get("metadata", {}).get("graph_artifact"),
        }
        add_row(
            out,
            lane=rec.get("lane", "coordination_graph"),
            task=rec.get("task", "code_payload_to_binary_harmonic_views"),
            source=source,
            prompt=rec.get("prompt", ""),
            response=rec.get("response", ""),
            views=rec.get("views", {}),
        )
    return out


def expand_binary_drills() -> list[dict[str, Any]]:
    snippets = [
        "print('hello')",
        "def f(a,b): return a + b",
        "console.log('hello')",
        "function add(a,b){return a+b;}",
        "fn add(a: i32, b: i32) -> i32 { a + b }",
        "SELECT * FROM users WHERE id = 1;",
        "KO kor-vael AV A_2 AV B_3 RU ru-thar CA bip'a DR draum-sel",
        "+++[>++<-]>",
        "{\"hello\":\"world\"}",
        "name: scbe\nlane: binary\n",
    ]
    out: list[dict[str, Any]] = []
    for idx, snippet in enumerate(snippets):
        bviews = binary_views(snippet)
        source = {"id": f"binary_drill:{idx}", "kind": "binary_drill", "validated": True}
        add_row(
            out,
            lane="binary",
            task="code_to_binary_views",
            source=source,
            prompt=f"Encode {snippet} into binary views.",
            response=json.dumps({k: bviews[k] for k in ("utf8", "bytes", "hex", "bits", "nibbles", "base64", "base64url", "ascii85", "byte_hist", "sha256")}, ensure_ascii=False),
            views={"binary": bviews},
        )
    return out


def expand_scbe_token_drills() -> list[dict[str, Any]]:
    examples = [
        ("python", "def f(a,b): return a + b", "KO kor-vael AV av-sai lang:python RU ru-thar CA bip'fn CA bip'a CA bip'out DR draum-sel"),
        ("python", "def f(a,b): return a * b", "KO kor-vael AV av-sai lang:python RU ru-thar CA bip'fn CA bip'i CA bip'out DR draum-sel"),
        ("javascript", "function add(a,b){return a+b;}", "KO kor-vael AV av-sai lang:javascript RU ru-thar CA bip'fn CA bip'a CA bip'out DR draum-sel"),
        ("rust", "fn add(a: i32, b: i32) -> i32 { a + b }", "KO kor-vael AV av-sai lang:rust RU ru-thar CA bip'fn CA bip'a CA bip'out DR draum-sel"),
        ("python", "for x in xs:\n    if x > 0:\n        total += x", "KO kor-vael AV av-sai lang:python RU ru-thar CA wheel'a CA fork'ra CA mira'voth CA bip'a DR draum-sel"),
        ("sql", "SELECT * FROM users WHERE id = 1;", "KO kor-vael AV av-sai lang:sql RU ru-thar CA slot'a CA mira'voth CA call'an DR draum-sel"),
        ("json", "{\"hello\":\"world\"}", "KO kor-vael AV av-sai lang:json RU ru-thar CA bind'a CA slot'a DR draum-sel"),
        ("brainfuck", "+++[>++<-]>", "KO kor-vael AV av-sai lang:brainfuck RU ru-thar CA bip'a CA wheel'a CA slot'a DR draum-sel"),
    ]
    out: list[dict[str, Any]] = []
    for idx, (language, code, tokens) in enumerate(examples):
        source = {"id": f"scbe_token_drill:{idx}", "kind": "scbe_token_drill", "validated": True}
        add_row(
            out,
            lane="coding",
            task="code_to_scbe_tokens",
            source=source,
            prompt=f"Convert this {language} code into SCBE phase tokens: {code}",
            response=tokens,
            views={"binary": binary_views(code), "scbe_tokens": tokens.split()},
        )
    return out


def iter_markdown_files(max_files: int) -> list[Path]:
    files: list[Path] = []
    for root in DOC_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if len(files) >= max_files:
                return files
            if path.is_dir():
                if path.name in {".git", "node_modules", "__pycache__", "artifacts"}:
                    continue
                continue
            if path.suffix.lower() in {".md", ".txt"} and path.stat().st_size <= 300_000:
                files.append(path)
    return files


def classify_doc(path: Path, text: str) -> str:
    lowered = f"{path} {text[:1000]}".lower()
    if "world bible" in lowered or "canon" in lowered or "lore" in lowered:
        return "world_bible"
    if "creation note" in lowered or "design note" in lowered or "behind" in lowered:
        return "creation_notes"
    if "spec" in lowered or "protocol" in lowered or "architecture" in lowered:
        return "system_spec"
    return "curated_lore"


def expand_docs(max_files: int, max_chars: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in iter_markdown_files(max_files):
        text = scrub(path.read_text(encoding="utf-8", errors="replace"))[:max_chars]
        if len(text.strip()) < 200:
            continue
        lane = classify_doc(path, text)
        rel = str(path.relative_to(ROOT))
        source = {"id": f"doc:{rel}", "kind": lane, "path": rel, "validated": False}
        title = next((line.strip("# ").strip() for line in text.splitlines() if line.strip().startswith("#")), path.stem)
        add_row(
            out,
            lane=lane,
            task="doc_to_summary",
            source=source,
            prompt=f"Summarize this {lane} source while preserving creation/system notes.\nPath: {rel}\n\n{text[:4000]}",
            response=f"Title: {title}\nSource lane: {lane}\nKeep as curated context, not execution proof.",
            views={"binary": binary_views(text), "title": title},
        )
    return out


def read_docx_text(path: Path, max_chars: int) -> str:
    try:
        with zipfile.ZipFile(path) as zf:
            xml = zf.read("word/document.xml").decode("utf-8", errors="replace")
    except Exception:
        return ""
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<[^>]+>", " ", xml)
    xml = re.sub(r"\s+", " ", xml)
    return scrub(xml)[:max_chars].strip()


def read_any_recovered_text(path: Path, max_chars: int) -> str:
    if path.suffix.lower() == ".docx":
        return read_docx_text(path, max_chars)
    if path.suffix.lower() in {".txt", ".md", ".json", ".csv", ".xml"}:
        return scrub(path.read_text(encoding="utf-8", errors="replace"))[:max_chars]
    return ""


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
      for chunk in iter(lambda: f.read(1024 * 1024), b""):
          h.update(chunk)
    return h.hexdigest()


def expand_recovered_docs(max_files: int, max_chars: int) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not RECOVERED_ROOT.exists():
        return out
    files = [p for p in RECOVERED_ROOT.rglob("*") if p.is_file()]
    files = sorted(files, key=lambda p: str(p).lower())[:max_files]
    for path in files:
        rel = str(path.relative_to(RECOVERED_ROOT))
        folder = path.parent.name
        digest = file_sha256(path)
        text = read_any_recovered_text(path, max_chars)
        lane = {
            "books": "recovered_world_bible",
            "patents": "recovered_patent",
            "scbe-docs": "recovered_scbe_doc",
            "other-docs": "recovered_other_doc",
        }.get(folder, "recovered_doc")
        source = {
            "id": f"recovered:{rel}",
            "kind": lane,
            "path": str(path),
            "relative_path": rel,
            "sha256": digest,
            "bytes": path.stat().st_size,
            "validated": bool(text),
        }
        prompt_text = text[:4000] if text else f"Recovered file {rel}; text extraction unavailable for extension {path.suffix}."
        response_text = (
            f"Recovered source: {rel}\n"
            f"Lane: {lane}\n"
            f"SHA-256: {digest}\n"
            f"Use as source-grounded context; do not treat as execution proof."
        )
        add_row(
            out,
            lane=lane,
            task="recovered_source_summary",
            source=source,
            prompt=f"Summarize recovered source material without losing provenance.\n\n{prompt_text}",
            response=response_text,
            views={"binary": binary_views(text or rel), "sha256": digest, "folder": folder},
        )
    return out


def build_parameter_bank(rows: list[dict[str, Any]]) -> dict[str, Any]:
    tokens = Counter()
    lanes = Counter()
    tasks = Counter()
    binary_modes = Counter()
    for row in rows:
        lanes[row["lane"]] += 1
        tasks[row["task"]] += 1
        for mode in row["metadata"].get("binary_modes", []):
            binary_modes[mode] += 1
        text = f"{row['prompt']} {row['response']}"
        for token in re.findall(r"[A-Za-z0-9_:'-]{2,}", text):
            tokens[token[:80]] += 1
    manual_vectors = []
    for idx, (token, count) in enumerate(tokens.most_common(512)):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        vector = [round(((byte / 255.0) * 2.0) - 1.0, 6) for byte in digest[:16]]
        manual_vectors.append({"token": token, "count": count, "seed_vector_16": vector, "slot": idx})
    return {
        "kind": "manual_parameter_bank",
        "honest_scope": "Deterministic seed vectors/vocabulary slots for initialization or feature expansion; not learned capability by itself.",
        "lanes": dict(lanes.most_common()),
        "tasks": dict(tasks.most_common()),
        "binary_modes": dict(binary_modes.most_common()),
        "manual_vectors": manual_vectors,
    }


def build_curriculum(rows: list[dict[str, Any]]) -> dict[str, Any]:
    stages = [
        {"stage": 1, "name": "binary literacy", "tasks": ["code_to_binary_views"], "gate": "loss + exact decode sample"},
        {"stage": 2, "name": "operation recognition", "tasks": ["code_to_ops"], "gate": "operation F1"},
        {"stage": 3, "name": "SCBE token bridge", "tasks": ["code_to_scbe_tokens", "conlang_to_program"], "gate": "phase grammar validity"},
        {"stage": 4, "name": "doc/code alignment", "tasks": ["doc_to_code"], "gate": "syntax/verifier pass"},
        {"stage": 5, "name": "labyrinth planning", "tasks": ["path_to_goal", "predict_verifier_gate"], "gate": "path/gate accuracy"},
        {"stage": 6, "name": "curated system/lore context", "tasks": ["doc_to_summary"], "gate": "source citation and no execution overclaim"},
    ]
    counts_by_task = Counter(row["task"] for row in rows)
    for stage in stages:
        stage["available_rows"] = sum(counts_by_task[task] for task in stage["tasks"])
    return {"kind": "labyrinth_curriculum", "stages": stages}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-per-language", type=int, default=40)
    parser.add_argument("--rosetta-limit", type=int, default=2500)
    parser.add_argument("--language-atlas-limit", type=int, default=500)
    parser.add_argument("--coordination-graph-limit", type=int, default=1000)
    parser.add_argument("--doc-files", type=int, default=80)
    parser.add_argument("--doc-chars", type=int, default=12000)
    parser.add_argument("--recovered-files", type=int, default=100)
    parser.add_argument("--recovered-chars", type=int, default=12000)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    coder_source = load_coder_rows(args.limit_per_language)
    rows = []
    rows.extend(expand_coder_rows(coder_source))
    rows.extend(expand_rosetta_rows(args.rosetta_limit))
    rows.extend(expand_language_atlas_rows(args.language_atlas_limit))
    rows.extend(expand_coordination_graph_rows(args.coordination_graph_limit))
    rows.extend(expand_binary_drills())
    rows.extend(expand_scbe_token_drills())
    rows.extend(expand_docs(args.doc_files, args.doc_chars))
    rows.extend(expand_recovered_docs(args.recovered_files, args.recovered_chars))

    bundle_path = OUT_DIR / "training_bundle.jsonl"
    with bundle_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    parameter_bank = build_parameter_bank(rows)
    parameter_path = OUT_DIR / "manual_parameter_bank.json"
    parameter_path.write_text(json.dumps(parameter_bank, indent=2, ensure_ascii=False), encoding="utf-8")

    curriculum = build_curriculum(rows)
    curriculum_path = OUT_DIR / "labyrinth_curriculum.json"
    curriculum_path.write_text(json.dumps(curriculum, indent=2, ensure_ascii=False), encoding="utf-8")

    lane_counts = Counter(row["lane"] for row in rows)
    task_counts = Counter(row["task"] for row in rows)
    receipt = {
        "ok": True,
        "kind": "full_coding_systems_training_bundle",
        "honest_scope": "Data expansion and deterministic parameter seeds; does not claim model improvement until trained and validated.",
        "counts": {
            "rows": len(rows),
            "coder_source_rows": len(coder_source),
            "lanes": dict(lane_counts.most_common()),
            "tasks": dict(task_counts.most_common()),
            "manual_parameter_vectors": len(parameter_bank["manual_vectors"]),
        },
        "artifacts": {
            "training_bundle": str(bundle_path),
            "manual_parameter_bank": str(parameter_path),
            "labyrinth_curriculum": str(curriculum_path),
        },
    }
    receipt_path = OUT_DIR / "receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")

    print("FULL_CODING_SYSTEMS_BUNDLE_DONE")
    print(f"rows: {len(rows)}")
    print(f"lanes: {dict(lane_counts.most_common())}")
    print(f"tasks: {dict(task_counts.most_common())}")
    print(f"manual parameter seed vectors: {len(parameter_bank['manual_vectors'])}")
    print(f"receipt: {receipt_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
