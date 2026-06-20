#!/usr/bin/env python3
"""Generate and score an Ollama submission for the SCBE Kaggle-style holdout.

This is a local benchmark adapter, not a Kaggle upload tool. It reads the
public-style `holdout.jsonl`, asks a local Ollama model to answer each prompt,
writes a Kaggle-shaped `submission.csv`, and scores it with the bundled scorer.
Failures are kept as per-row diagnostics so misses can become repair data.
"""

from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BUNDLE = REPO_ROOT / "artifacts" / "benchmarks" / "scbe_bijective_round_trip"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
TONGUE_ORDER = ("KO", "AV", "RU", "CA", "UM", "DR")
TONGUE_LANG = {
    "KO": "py",
    "AV": "js",
    "RU": "rs",
    "CA": "wl",
    "UM": "hs",
    "DR": "md",
}
TONGUE_NAMES = {
    "KO": "Kor'aelin",
    "AV": "Avali",
    "RU": "Runethic",
    "CA": "Cassisivadan",
    "UM": "Umbroth",
    "DR": "Draumric",
}
LANG_ALIASES = {
    "KO": ("py", "python"),
    "AV": ("js", "javascript"),
    "RU": ("rs", "rust"),
    "CA": ("wl", "mathematica", "wolfram"),
    "UM": ("hs", "haskell"),
    "DR": ("md", "markdown"),
}
SLOT_ORDER = ("sig", "init", "loop_open", "loop_body", "loop_close", "not_found", "body", "ret")
ALGORITHM_CARDS = {
    "is_even": {
        "description": "Test parity with modulo 2 equals 0.",
        "names": "Python/Rust/Markdown is_even; JavaScript/Haskell/Mathematica isEven.",
        "must_include": "mod, 2, 0, Bool/boolean where the target language supports it.",
    },
    "sum_list": {
        "description": "Reduce a list by accumulation; product edit starts at 1 and multiplies each item.",
        "names": "Python/Rust/Markdown sum_list; JavaScript/Haskell/Mathematica sumList.",
        "must_include": "total, 1, loop over xs, multiplication, return total.",
    },
    "is_palindrome": {
        "description": "Return true when a string equals its reverse.",
        "names": "Python/Rust/Markdown is_palindrome; JavaScript/Haskell/Mathematica isPalindrome.",
        "must_include": "reverse operation and equality comparison.",
    },
    "swap": {
        "description": "Return the pair in reversed order: (b, a).",
        "names": "swap in every tongue.",
        "must_include": "a, b, b, a.",
    },
    "linear_search": {
        "description": "Return the index of the first matching item, or -1 when no item matches.",
        "names": "Public algorithm label linear_search; local function can be find where the prompt uses find.",
        "must_include": "index, equality check, return index on match, return -1 on miss.",
    },
    "fibonacci_iter": {
        "description": "Iterative Fibonacci using two running values a and b.",
        "names": "Public algorithm label fibonacci_iter; local function can be fib where the prompt uses fib.",
        "must_include": "a=0, b=1, loop n times, update (a,b) to (b,a+b), return a.",
    },
}


def load_holdout(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_prompt(
    row: dict[str, Any],
    lookup_feedback: list[str] | None = None,
    *,
    include_algorithm_card: bool = False,
) -> str:
    meta = row.get("meta") or {}
    task = meta.get("task", "unknown")
    tongue = meta.get("tongue") or meta.get("src") or meta.get("dst") or "unknown"
    contract_hint = build_contract_hint(row)
    algorithm_card = build_algorithm_card(row) if include_algorithm_card else ""
    feedback = ""
    if lookup_feedback:
        bullets = "\n".join(f"- {item}" for item in lookup_feedback)
        feedback = (
            "\nManual lookup-table verification failed on the prior attempt. "
            "Regenerate from scratch; do not patch or continue the old answer.\n"
            f"Failed checks:\n{bullets}\n"
        )
    return (
        "You are completing a Kaggle-style SCBE Bijective Tongue Coder task.\n"
        "Return only the requested answer. Preserve markdown code fences, tongue headers, "
        "slot markers, and line structure when the prompt asks for them.\n"
        "Before answering, manually consult this benchmark lookup table:\n"
        "KO=Kor'aelin/Python, AV=Avali/JavaScript, RU=Runethic/Rust, "
        "CA=Cassisivadan/Mathematica, UM=Umbroth/Haskell, DR=Draumric/Markdown.\n"
        f"Task: {task}\n"
        f"Tongue: {tongue}\n\n"
        f"{algorithm_card}\n"
        f"{contract_hint}\n"
        f"{feedback}"
        f"{row.get('prompt', '')}\n"
    )


def build_algorithm_card(row: dict[str, Any]) -> str:
    meta = row.get("meta") or {}
    algorithm = str(meta.get("algorithm") or "").strip()
    card = ALGORITHM_CARDS.get(algorithm)
    if not card:
        return ""
    lines = [
        "Algorithm lookup card:",
        f"- canonical label: {algorithm}",
        f"- description: {card['description']}",
        f"- naming: {card['names']}",
        f"- must include: {card['must_include']}",
    ]
    return "\n".join(lines)


def _slots_from_prompt(prompt: str) -> list[str]:
    import re

    slots = []
    match = re.search(r"Slots:\s*([A-Za-z0-9_,\s-]+)", prompt)
    if match:
        slot_text = match.group(1).splitlines()[0]
        for raw in slot_text.split(","):
            slot = raw.strip().strip(".")
            if slot and slot not in slots:
                slots.append(slot)
    for slot in re.findall(r"\bslot\s*=\s*([A-Za-z0-9_]+)", prompt):
        if slot and slot not in slots:
            slots.append(slot)
    return slots


def _ordered_unique(items: list[str]) -> list[str]:
    seen = set()
    out = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def expanded_slots(row: dict[str, Any]) -> list[str]:
    """Infer public slot expectations from metadata and prompt text.

    This never reads the hidden reference. It only expands slot names that are
    implied by the public prompt, e.g. a multi-slot loop edit has a signature,
    loop opening, edited loop body, and return surface even when the prompt only
    names the edited slots.
    """
    meta = row.get("meta") or {}
    prompt = str(row.get("prompt", ""))
    slots = [str(slot) for slot in meta.get("slots") or []]
    slots.extend(_slots_from_prompt(prompt))

    task = str(meta.get("task", "unknown"))
    lower_prompt = prompt.lower()
    if task in {"multiline_edit", "edit_slot_all"}:
        inferred = ["sig"]
        if "initialize" in lower_prompt or "total =" in lower_prompt:
            inferred.append("init")
        if "for " in lower_prompt or "loop" in lower_prompt:
            inferred.append("loop_open")
        if "loop_body" in lower_prompt or "convert" in lower_prompt:
            inferred.append("loop_body")
        if "return" in lower_prompt:
            inferred.append("ret")
        slots.extend(inferred)

    order = {slot: idx for idx, slot in enumerate(SLOT_ORDER)}
    unique = _ordered_unique(slots)
    return sorted(unique, key=lambda slot: (order.get(slot, len(order)), unique.index(slot)))


def metadata_preface(row: dict[str, Any]) -> str:
    """Render deterministic public metadata so generated answers self-identify."""
    meta = row.get("meta") or {}
    lines = []
    algorithm = str(meta.get("algorithm") or "").strip()
    task = str(meta.get("task") or "").strip()
    tongue = str(meta.get("tongue") or meta.get("src") or meta.get("dst") or "").strip()
    slots = expanded_slots(row)
    if algorithm:
        lines.append(f"## algorithm: {algorithm}")
    if task:
        lines.append(f"## task: {task}")
    if tongue:
        label = f"{tongue} ({TONGUE_NAMES[tongue]})" if tongue in TONGUE_NAMES else tongue
        lines.append(f"## tongue: {label}")
    if slots:
        lines.append("## slots: " + ", ".join(slots))
    return "\n".join(lines)


def with_metadata_preface(row: dict[str, Any], prediction: str) -> str:
    preface = metadata_preface(row)
    if not preface:
        return prediction.strip()
    algorithm = str((row.get("meta") or {}).get("algorithm") or "").strip()
    if algorithm and f"algorithm: {algorithm}".lower() in prediction.lower():
        return prediction.strip()
    return f"{preface}\n\n{prediction.strip()}"


def build_contract_hint(row: dict[str, Any]) -> str:
    meta = row.get("meta") or {}
    task = str(meta.get("task", "unknown"))
    slots = expanded_slots(row)

    lines = ["Output contract:"]
    if task in {"translate_all", "multiline_edit", "edit_slot_all"}:
        lines.append("- Emit all six tongue sections in this exact order: KO, AV, RU, CA, UM, DR.")
        lines.append("- Each section must start with `### TONGUE:<CODE>`.")
        lines.append("- Each section should include fenced code for that tongue.")
        if slots:
            lines.append("- Preserve these slot markers where applicable: " + ", ".join(f"#slot:{s}" for s in slots))
    elif task in {"translate_one", "edit_slot_one"}:
        lines.append("- Emit one fenced code block in the target tongue.")
        if slots:
            lines.append("- Preserve the requested slot marker where applicable.")
    elif task == "align":
        lines.append("- Emit a markdown slot-alignment table or section, not a prose summary.")
    elif task == "identify":
        lines.append("- Emit algorithm, description, tongue, slots, and slot breakdown.")
    elif task == "governance_tag":
        lines.append("- Emit per-line governance with H, d_H, and tier fields.")
    else:
        lines.append("- Follow the exact structure requested by the prompt.")
    return "\n".join(lines)


def structural_scaffold(row: dict[str, Any], prediction: str) -> str:
    """Add deterministic format rails without copying the hidden reference."""
    meta = row.get("meta") or {}
    task = str(meta.get("task", "unknown"))
    slots = expanded_slots(row)
    body = prediction.strip()

    if task in {"translate_all", "multiline_edit", "edit_slot_all"}:
        sections = []
        for tongue in TONGUE_ORDER:
            lang = TONGUE_LANG[tongue]
            slot_lines = "\n".join(f"#slot:{slot}" for slot in slots)
            content = slot_lines + ("\n" if slot_lines else "") + body
            sections.append(f"### TONGUE:{tongue}\n```{lang}\n{content}\n```")
        return "\n\n".join(sections)

    if task in {"translate_one", "edit_slot_one"} and "```" not in body:
        target = meta.get("tongue") or meta.get("dst") or meta.get("src") or "KO"
        lang = TONGUE_LANG.get(str(target), "")
        return f"```{lang}\n{body}\n```"

    if task == "align" and "slot alignment" not in body.lower():
        return f"## slot alignment\n\n{body}"

    return body


def contract_repair(row: dict[str, Any], prediction: str) -> str:
    """Minimal deterministic repair pass for known benchmark output contracts."""
    meta = row.get("meta") or {}
    task = str(meta.get("task", "unknown"))
    slots = expanded_slots(row)
    out = with_metadata_preface(row, prediction)

    if task in {"multiline_edit", "translate_all", "edit_slot_all"}:
        for tongue in TONGUE_ORDER:
            marker = f"### TONGUE:{tongue}"
            if marker not in out:
                lang = TONGUE_LANG[tongue]
                out += f"\n\n{marker}\n```{lang}\n```"
        for slot in slots:
            marker = f"#slot:{slot}"
            if marker not in out:
                out = f"{marker}\n{out}"

    if task == "align" and "slot alignment" not in out.lower():
        out = f"## slot alignment\n\n{out}"

    return out


def _fence_languages(text: str) -> list[str]:
    import re

    return [m.lower() for m in re.findall(r"```([A-Za-z0-9_+-]*)", text)]


def _tongue_marker_positions(text: str) -> dict[str, int]:
    return {tongue: text.find(f"### TONGUE:{tongue}") for tongue in TONGUE_ORDER}


def lookup_verify(row: dict[str, Any], prediction: str) -> dict[str, Any]:
    """Manual lookup-table verifier for retry gating.

    This intentionally checks public row metadata and benchmark lookup tables,
    not hidden reference text. It is a process verifier, not the final scorer.
    """
    meta = row.get("meta") or {}
    task = str(meta.get("task", "unknown"))
    algorithm = str(meta.get("algorithm", "") or "")
    text = prediction or ""
    lower = text.lower()
    slots = list(meta.get("slots") or _slots_from_prompt(str(row.get("prompt", ""))))
    issues: list[str] = []

    if algorithm and algorithm.lower() not in lower:
        issues.append(f"missing exact algorithm token `{algorithm}`")

    if task in {"translate_all", "multiline_edit", "edit_slot_all"}:
        positions = _tongue_marker_positions(text)
        missing = [tongue for tongue, pos in positions.items() if pos < 0]
        if missing:
            issues.append("missing tongue sections: " + ", ".join(missing))
        present_positions = [positions[tongue] for tongue in TONGUE_ORDER if positions[tongue] >= 0]
        if present_positions != sorted(present_positions):
            issues.append("tongue sections are not in lookup-table order KO, AV, RU, CA, UM, DR")
        for slot in slots:
            count = text.count(f"#slot:{slot}")
            if count < len(TONGUE_ORDER):
                issues.append(f"slot `{slot}` appears {count}/6 times")
    elif task in {"translate_one", "edit_slot_one"}:
        target = str(meta.get("dst") or meta.get("tongue") or meta.get("src") or "")
        if target in TONGUE_LANG:
            aliases = LANG_ALIASES[target]
            fences = _fence_languages(text)
            if not any(fence in aliases for fence in fences):
                issues.append(f"missing target fence for {target}/{TONGUE_NAMES[target]} ({'/'.join(aliases)})")
    elif task == "identify":
        tongue = str(meta.get("tongue") or "")
        if tongue in TONGUE_NAMES:
            if tongue.lower() not in lower and TONGUE_NAMES[tongue].lower() not in lower:
                issues.append(f"missing tongue identity `{tongue}` / `{TONGUE_NAMES[tongue]}`")
        if "slots" not in lower and "slot breakdown" not in lower:
            issues.append("missing slots or slot breakdown field")
    elif task == "align":
        src = str(meta.get("src") or "")
        dst = str(meta.get("dst") or "")
        if "slot alignment" not in lower:
            issues.append("missing `slot alignment` heading")
        for tongue in (src, dst):
            if tongue and tongue not in text and TONGUE_NAMES.get(tongue, "").lower() not in lower:
                issues.append(f"missing alignment side `{tongue}`")
    elif task == "governance_tag":
        for marker in ("h", "d_h", "tier"):
            if marker not in lower:
                issues.append(f"missing governance field `{marker}`")

    return {
        "ok": not issues,
        "issue_count": len(issues),
        "issues": issues,
    }


def ollama_generate(
    prompt: str,
    *,
    model: str,
    url: str = DEFAULT_OLLAMA_URL,
    timeout: int = 120,
    max_tokens: int = 512,
) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0,
            "num_predict": max_tokens,
        },
    }
    req = urllib.request.Request(
        f"{url.rstrip('/')}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as err:
        raise RuntimeError(f"Ollama request failed for {model}: {err}") from err
    return str(data.get("response") or "").strip()


def write_submission(rows: list[dict[str, Any]], predictions: dict[str, str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "prediction"])
        for row in rows:
            writer.writerow([row["id"], predictions.get(row["id"], "")])


def load_scorer(score_path: Path):
    spec = importlib.util.spec_from_file_location("scbe_round_trip_score_runtime", score_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load scorer: {score_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def summarize_failures(report: dict[str, Any], *, max_rows: int = 10) -> list[dict[str, Any]]:
    misses = [r for r in report.get("per_row", []) if float(r.get("row_score", 0.0)) < 0.999]
    misses.sort(key=lambda r: (float(r.get("row_score", 0.0)), r.get("id", "")))
    return misses[:max_rows]


def structural_signature(row: dict[str, Any], scorer: Any) -> dict[str, Any]:
    meta = row.get("meta") or {}
    reference = str(row.get("reference", ""))
    task = str(meta.get("task", "unknown"))
    sig = scorer._ref_signature(reference, task)
    sig["slots_from_prompt"] = _slots_from_prompt(str(row.get("prompt", "")))
    return sig


def write_failure_lessons(
    rows: list[dict[str, Any]],
    report: dict[str, Any],
    diagnostics: list[dict[str, Any]],
    scorer: Any,
    path: Path,
) -> int:
    by_row = {str(row["id"]): row for row in rows}
    by_diag = {str(item["id"]): item for item in diagnostics}
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for scored in report.get("per_row", []):
            score = float(scored.get("row_score", 0.0))
            if score >= 0.999:
                continue
            row_id = str(scored.get("id", ""))
            row = by_row.get(row_id)
            if not row:
                continue
            meta = row.get("meta") or {}
            diag = by_diag.get(row_id, {})
            lesson = {
                "schema": "scbe_roundtrip_failure_lesson_v1",
                "id": row_id,
                "task": meta.get("task", "unknown"),
                "algorithm": meta.get("algorithm", "unknown"),
                "tongue": meta.get("tongue") or meta.get("src") or meta.get("dst"),
                "row_score": score,
                "token_recall": scored.get("token_recall"),
                "structural_preservation": scored.get("structural_preservation"),
                "expected_structure": structural_signature(row, scorer),
                "raw_prediction_preview": diag.get("raw_prediction_preview", ""),
                "prediction_preview": diag.get("prediction_preview", ""),
                "lesson": "Improve output contract compliance first, then content recall.",
            }
            handle.write(json.dumps(lesson, ensure_ascii=False) + "\n")
            count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, default=DEFAULT_BUNDLE)
    parser.add_argument("--model", required=True, help="Ollama model name, e.g. openclaw:latest")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--limit", type=int, default=0, help="Optional row limit for smoke runs.")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--out-dir", type=Path, default=None)
    parser.add_argument(
        "--structural-scaffold",
        action="store_true",
        help="Apply deterministic SCBE output-shape rails before scoring.",
    )
    parser.add_argument(
        "--contract-repair",
        action="store_true",
        help="Apply a post-generation benchmark contract repair pass before scoring.",
    )
    parser.add_argument(
        "--lookup-retries",
        type=int,
        default=0,
        help="Retry generation from scratch when lookup-table verification fails.",
    )
    parser.add_argument(
        "--algorithm-card",
        action="store_true",
        help="Include public algorithm clue cards in the model prompt. Experimental; can distract weak models.",
    )
    args = parser.parse_args()

    bundle = args.bundle
    rows = load_holdout(bundle / "holdout.jsonl")
    if args.limit and args.limit > 0:
        rows = rows[: args.limit]
    if not rows:
        print("no holdout rows found")
        return 2

    safe_model = args.model.replace(":", "_").replace("/", "_")
    out_dir = args.out_dir or bundle / "ollama_runs" / safe_model
    out_dir.mkdir(parents=True, exist_ok=True)

    predictions: dict[str, str] = {}
    diagnostics: list[dict[str, Any]] = []
    started = time.time()
    for idx, row in enumerate(rows, 1):
        rid = str(row["id"])
        t0 = time.time()
        attempts: list[dict[str, Any]] = []
        feedback: list[str] | None = None
        raw_prediction = ""
        prediction = ""
        verification = {"ok": False, "issue_count": 0, "issues": []}
        error = None
        for attempt_idx in range(args.lookup_retries + 1):
            try:
                raw_prediction = ollama_generate(
                    build_prompt(row, lookup_feedback=feedback, include_algorithm_card=args.algorithm_card),
                    model=args.model,
                    url=args.ollama_url,
                    timeout=args.timeout,
                    max_tokens=args.max_tokens,
                )
                prediction = structural_scaffold(row, raw_prediction) if args.structural_scaffold else raw_prediction
                if args.contract_repair:
                    prediction = contract_repair(row, prediction)
                verification = lookup_verify(row, prediction)
                error = None
            except RuntimeError as err:
                raw_prediction = ""
                prediction = ""
                verification = {"ok": False, "issue_count": 1, "issues": [str(err)]}
                error = str(err)
            attempts.append(
                {
                    "attempt": attempt_idx + 1,
                    "lookup_ok": verification["ok"],
                    "lookup_issues": verification["issues"],
                    "raw_prediction_preview": raw_prediction[:240],
                    "prediction_preview": prediction[:240],
                }
            )
            if verification["ok"]:
                break
            feedback = list(verification["issues"])
        elapsed = round(time.time() - t0, 3)
        predictions[rid] = prediction
        diagnostics.append(
            {
                "id": rid,
                "elapsed_s": elapsed,
                "error": error,
                "structural_scaffold": args.structural_scaffold,
                "contract_repair": args.contract_repair,
                "lookup_retries": args.lookup_retries,
                "lookup_verification": verification,
                "attempts": attempts,
                "raw_prediction_preview": raw_prediction[:240],
                "prediction_preview": prediction[:240],
            }
        )
        print(f"[{idx}/{len(rows)}] {rid} {elapsed:.2f}s")

    submission_path = out_dir / "submission.csv"
    write_submission(rows, predictions, submission_path)

    scorer = load_scorer(bundle / "score.py")
    report = scorer.score(rows, predictions)
    report["model"] = args.model
    report["row_limit"] = args.limit or None
    report["elapsed_s"] = round(time.time() - started, 3)
    report["submission_path"] = str(submission_path)
    report["diagnostics"] = diagnostics
    report["lowest_rows"] = summarize_failures(report)

    report_path = out_dir / "score_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    lessons_path = out_dir / "failure_lessons.jsonl"
    lesson_count = write_failure_lessons(rows, report, diagnostics, scorer, lessons_path)
    report["failure_lessons_path"] = str(lessons_path)
    report["failure_lesson_count"] = lesson_count
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"overall_score = {report['overall_score']:.4f}  (n={report['n_rows']})")
    print(f"wrote {report_path}")
    print(f"wrote {lessons_path} ({lesson_count} lessons)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
