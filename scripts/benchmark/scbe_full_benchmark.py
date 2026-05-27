#!/usr/bin/env python3
"""
SCBE-AETHERMOORE Full System Benchmark
Runs five benchmark layers and compares against published external baselines.

Usage:
    python scripts/benchmark/scbe_full_benchmark.py [--json] [--skip-live]

Layers:
  1. Governance accuracy   — 14-layer SCBE pipeline on 560-case synthetic test set
  2. CLI capability        — 11-criteria comparison vs codex/claude/gemini/aider
  3. Squad latency         — Live provider probe (cerebras + groq) [skipped with --skip-live]
  4. Knowledge accuracy    — 10 factual questions via squad providers [skipped with --skip-live]
  5. Test suite health     — TypeScript vitest pass rate
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

# ── External published baselines ──────────────────────────────────────────────

EXTERNAL_BASELINES = {
    "safety_classifiers": [
        {"name": "WildGuard",       "score": 0.877, "metric": "balanced_accuracy", "source": "arxiv:2406.18495"},
        {"name": "LlamaGuard-3",    "score": 0.825, "metric": "balanced_accuracy", "source": "Meta AI, 2024"},
        {"name": "GPT-4-based",     "score": 0.860, "metric": "balanced_accuracy", "source": "OpenAI safety eval, 2024"},
        {"name": "ShieldLM",        "score": 0.803, "metric": "balanced_accuracy", "source": "arxiv:2402.09571"},
    ],
    "llm_quality_mmlu": [
        {"name": "llama-3.3-70b",   "score": 0.832, "metric": "5-shot MMLU",       "source": "Meta AI blog 2024"},
        {"name": "gpt-4o-mini",     "score": 0.820, "metric": "5-shot MMLU",       "source": "OpenAI evals 2024"},
        {"name": "gpt-4o",          "score": 0.887, "metric": "5-shot MMLU",       "source": "OpenAI evals 2024"},
        {"name": "claude-3.5-sonnet","score": 0.889, "metric": "5-shot MMLU",      "source": "Anthropic evals 2024"},
    ],
    "cli_capability": [
        {"name": "claude-code",     "score": 1.0,   "metric": "11/11 criteria",    "source": "docs.claude.com"},
        {"name": "gemini-cli",      "score": 0.909, "metric": "10/11 criteria",    "source": "geminicli.com/docs"},
        {"name": "codex-cli",       "score": 0.818, "metric": "9/11 criteria",     "source": "help.openai.com"},
        {"name": "aider",           "score": 0.727, "metric": "8/11 criteria",     "source": "aider.chat/docs"},
    ],
    "latency_p50_ms": [
        {"name": "cerebras llama",  "score": 920,   "metric": "p50 TTFT ms",       "source": "artificialanalysis.ai 2025"},
        {"name": "groq llama",      "score": 2659,  "metric": "p50 TTFT ms",       "source": "artificialanalysis.ai 2025"},
        {"name": "openai gpt-4o-mini", "score": 1500, "metric": "p50 TTFT ms",    "source": "artificialanalysis.ai 2025"},
    ],
}

# ── Knowledge accuracy questions (MMLU-style, public-domain) ──────────────────

KNOWLEDGE_QUESTIONS = [
    {"q": "What is the speed of light in a vacuum (approximate)?",
     "choices": {"A": "3×10^8 m/s", "B": "3×10^6 m/s", "C": "3×10^10 m/s", "D": "1×10^6 m/s"},
     "answer": "A", "category": "physics"},
    {"q": "What is the derivative of x³ with respect to x?",
     "choices": {"A": "3x", "B": "x²", "C": "3x²", "D": "x³"},
     "answer": "C", "category": "calculus"},
    {"q": "In what year did World War II end?",
     "choices": {"A": "1943", "B": "1944", "C": "1945", "D": "1946"},
     "answer": "C", "category": "history"},
    {"q": "What does CPU stand for?",
     "choices": {"A": "Central Processing Unit", "B": "Computer Processing Unit",
                 "C": "Central Program Unit", "D": "Core Processing Unit"},
     "answer": "A", "category": "cs"},
    {"q": "What is the chemical formula for water?",
     "choices": {"A": "CO2", "B": "H2O2", "C": "NaCl", "D": "H2O"},
     "answer": "D", "category": "chemistry"},
    {"q": "What is the capital of France?",
     "choices": {"A": "Berlin", "B": "Madrid", "C": "Paris", "D": "Rome"},
     "answer": "C", "category": "geography"},
    {"q": "How many chromosomes does a typical human have?",
     "choices": {"A": "23", "B": "46", "C": "44", "D": "48"},
     "answer": "B", "category": "biology"},
    {"q": "What is √144?",
     "choices": {"A": "12", "B": "14", "C": "11", "D": "13"},
     "answer": "A", "category": "math"},
    {"q": "What does HTTP stand for?",
     "choices": {"A": "HyperText Transfer Protocol", "B": "High Transfer Text Protocol",
                 "C": "HyperText Transport Protocol", "D": "High Text Transfer Protocol"},
     "answer": "A", "category": "cs"},
    {"q": "What is the largest planet in the solar system?",
     "choices": {"A": "Saturn", "B": "Neptune", "C": "Uranus", "D": "Jupiter"},
     "answer": "D", "category": "astronomy"},
]


# ── Layer 1: Governance ───────────────────────────────────────────────────────

def run_governance_benchmark() -> dict[str, Any]:
    """Run the standalone governance benchmark via subprocess."""
    script = REPO_ROOT / "benchmarks" / "scbe_benchmark_standalone.py"
    results_dir = REPO_ROOT / "benchmarks" / "results"

    t0 = time.time()
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    elapsed = time.time() - t0

    # Try to find the most recent result JSON
    result_files = sorted(results_dir.glob("scbe_benchmark_local_*.json"), reverse=True)
    if result_files:
        data = json.loads(result_files[0].read_text())
        acc = data["results"]["overall_accuracy"]
        f1 = data["results"]["f1_score"]
        fpr = data["results"]["false_positive_rate"]
        n = data["dataset"]["total_cases"]
        harmonic_sep = data["harmonic_wall"]["cost_separation"]

        # Live pattern-filter recall measurement (Petri-173 corpus)
        petri_recall = _measure_petri_recall()

        return {
            "ok": True,
            "cases": n,
            "accuracy": acc,
            "f1": f1,
            "false_positive_rate": fpr,
            "harmonic_cost_separation": harmonic_sep,
            "note": "Synthetic test set — regex-based; honest blind-holdout rate is 34.5% (published)",
            "blind_detection_rate": 0.345,
            "hybrid_detection_rate": 0.545,
            "petri_pattern_filter_recall": petri_recall["recall"],
            "petri_seeds_caught": petri_recall["hit"],
            "petri_seeds_total": petri_recall["total"],
            "petri_tongue_only": petri_recall.get("tongue_only", 0),
            "petri_regex_only": petri_recall.get("regex_only", 0),
            "elapsed_s": elapsed,
        }
    return {"ok": False, "error": "no result file found", "elapsed_s": elapsed}


def _measure_petri_recall() -> dict[str, Any]:
    """Run the Petri-173 corpus through the full governance pre-filter stack.

    Measures combined recall: Petri regex filter + Sacred Tongue KO coverage gate.
    The tongue gate catches non-Latin-script adversarial inputs (CJK, Devanagari,
    Arabic, etc.) that the English regex filter cannot reach.

    Returns a dict with: recall (float), hit (int), total (int), corpus_available (bool),
    plus per-layer breakdown (regex_only, tongue_only, both).
    """
    seeds_dir = REPO_ROOT / "external" / "benchmarks" / "petri-seeds"
    if not seeds_dir.exists() or not any(seeds_dir.glob("*.md")):
        return {"recall": None, "hit": 0, "total": 0, "corpus_available": False}

    try:
        from src.cli.petri_pattern_filter import is_meta_ai_auditor_phrasing, is_non_latin_script_input
        total, hit, regex_only, tongue_only, both_hit = 0, 0, 0, 0, 0
        for f in sorted(seeds_dir.glob("*.md")):
            body = f.read_text(encoding="utf-8")
            if body.startswith("---"):
                parts = body.split("---", 2)
                body = parts[2].strip() if len(parts) >= 3 else body
            total += 1
            r_hit = is_meta_ai_auditor_phrasing(body)[0]
            t_hit = is_non_latin_script_input(body)[0]
            if r_hit or t_hit:
                hit += 1
                if r_hit and t_hit:
                    both_hit += 1
                elif r_hit:
                    regex_only += 1
                else:
                    tongue_only += 1
        recall = hit / total if total else 0.0
        return {
            "recall": recall,
            "hit": hit,
            "total": total,
            "corpus_available": True,
            "regex_only": regex_only,
            "tongue_only": tongue_only,
            "both": both_hit,
        }
    except Exception as exc:
        return {"recall": None, "hit": 0, "total": 0, "corpus_available": False, "error": str(exc)}


# ── Layer 2: CLI capability ───────────────────────────────────────────────────

def run_cli_benchmark() -> dict[str, Any]:
    script = REPO_ROOT / "scripts" / "benchmark" / "cli_competitive_benchmark.py"
    t0 = time.time()
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    elapsed = time.time() - t0

    if proc.returncode == 0:
        try:
            # stdout: {"ok": true, "json": path, "markdown": path, "ranking": [...]}
            summary = json.loads(proc.stdout)
            ranking = summary.get("ranking", [])
            full_data: dict[str, Any] = {}
            if summary.get("json"):
                try:
                    full_data = json.loads(Path(summary["json"]).read_text())
                except Exception:
                    pass
            scbe_row = next((r for r in ranking if r["name"] == "scbe-geoseal"), ranking[0] if ranking else {})
            return {
                "ok": True,
                "scbe_score": scbe_row,
                "ranking": ranking,
                "gaps": full_data.get("scbe", {}).get("gaps", []),
                "elapsed_s": elapsed,
            }
        except Exception as exc:
            return {"ok": False, "error": str(exc), "raw": proc.stdout[:500], "elapsed_s": elapsed}
    return {"ok": False, "error": proc.stderr[:500], "elapsed_s": elapsed}


# ── Layer 3: Squad latency probe ─────────────────────────────────────────────

def _openai_chat_request(base_url: str, api_key: str, model: str, prompt: str, timeout: int = 30, max_tokens: int = 500) -> tuple[str, float]:
    """Fire a single chat completion request and return (response_text, latency_ms).
    max_tokens=500 required for reasoning models (zai-glm-4.7, gpt-oss-*) to complete chain-of-thought.
    """
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "python-httpx/0.27.0",
        },
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ms = (time.time() - t0) * 1000
            text = resp.read().decode()
            data = json.loads(text)
            msg = data["choices"][0]["message"]
            # Reasoning models (zai-glm-4.7, gpt-oss-120b) emit content after the reasoning chain
            content = msg.get("content") or ""
            return content.strip(), ms
    except Exception as exc:
        ms = (time.time() - t0) * 1000
        return f"ERROR: {exc}", ms


def run_squad_latency_benchmark() -> dict[str, Any]:
    """Probe cerebras and groq with 3 pings each, report p50 latency."""
    providers = []

    cerebras_key = os.environ.get("CEREBRAS_API_KEY", "")
    groq_key = os.environ.get("GROQ_API_KEY", "")
    ping_prompt = "Reply with just: OK"

    for name, base_url, api_key, model in [
        # zai-glm-4.7 is a reasoning model available on this account; llama not provisioned
        ("cerebras", "https://api.cerebras.ai/v1",       cerebras_key, "zai-glm-4.7"),
        ("groq",     "https://api.groq.com/openai/v1",   groq_key,     "llama-3.3-70b-versatile"),
    ]:
        if not api_key:
            providers.append({"provider": name, "ok": False, "error": "no api key", "latencies_ms": []})
            continue

        latencies = []
        errors = []
        for _ in range(3):
            resp, ms = _openai_chat_request(base_url, api_key, model, ping_prompt, timeout=30, max_tokens=200)
            if resp.startswith("ERROR:"):
                errors.append(resp)
            else:
                latencies.append(round(ms, 1))
            time.sleep(0.3)

        if latencies:
            latencies_sorted = sorted(latencies)
            p50 = latencies_sorted[len(latencies_sorted) // 2]
            providers.append({
                "provider": name,
                "model": model,
                "ok": True,
                "latencies_ms": latencies,
                "p50_ms": p50,
                "errors": errors,
            })
        else:
            providers.append({"provider": name, "model": model, "ok": False, "error": errors[0] if errors else "unknown", "latencies_ms": []})

    return {"providers": providers}


# ── Layer 4: Knowledge accuracy ───────────────────────────────────────────────

def _extract_answer_letter(response: str) -> str | None:
    """Extract A/B/C/D from a model response."""
    # Look for explicit "Answer: X" or "(X)" or standalone letter at start
    patterns = [
        r"\bthe\s+answer\s+is\s+\(?([A-D])\)?",
        r"^([A-D])[.):]\s",
        r"answer[:\s]+\(?([A-D])\)?",
        r"\b([A-D])\)\s",
        r"^\(?([A-D])\)?[\s.:,]",
        r"\s\(([A-D])\)\s",
    ]
    for pat in patterns:
        m = re.search(pat, response, re.IGNORECASE | re.MULTILINE)
        if m:
            return m.group(1).upper()
    # Last resort: first standalone letter in first 50 chars
    m = re.search(r'\b([A-D])\b', response[:80], re.IGNORECASE)
    return m.group(1).upper() if m else None


def run_knowledge_benchmark(skip_live: bool = False) -> dict[str, Any]:
    if skip_live:
        return {"ok": False, "skipped": True, "reason": "--skip-live"}

    providers_tested = []

    for name, base_url, api_key, model in [
        ("cerebras", "https://api.cerebras.ai/v1",       os.environ.get("CEREBRAS_API_KEY", ""), "zai-glm-4.7"),
        ("groq",     "https://api.groq.com/openai/v1",   os.environ.get("GROQ_API_KEY", ""),     "llama-3.3-70b-versatile"),
    ]:
        if not api_key:
            providers_tested.append({"provider": name, "ok": False, "error": "no api key"})
            continue

        correct = 0
        results = []
        for q in KNOWLEDGE_QUESTIONS:
            choices_str = " | ".join(f"({k}) {v}" for k, v in q["choices"].items())
            prompt = f"Multiple choice. Reply with ONLY the letter of the correct answer (A, B, C, or D).\n\nQuestion: {q['q']}\n{choices_str}"
            resp, ms = _openai_chat_request(base_url, api_key, model, prompt, timeout=45, max_tokens=600)
            predicted = _extract_answer_letter(resp)
            hit = predicted == q["answer"] if predicted else False
            if hit:
                correct += 1
            results.append({
                "category": q["category"],
                "correct": hit,
                "predicted": predicted,
                "expected": q["answer"],
                "latency_ms": round(ms, 1),
            })
            time.sleep(0.2)

        accuracy = correct / len(KNOWLEDGE_QUESTIONS)
        providers_tested.append({
            "provider": name,
            "model": model,
            "ok": True,
            "correct": correct,
            "total": len(KNOWLEDGE_QUESTIONS),
            "accuracy": round(accuracy, 3),
            "results": results,
        })

    return {"ok": True, "providers": providers_tested}


# ── Layer 5: Test suite health ────────────────────────────────────────────────

def run_test_suite_benchmark() -> dict[str, Any]:
    """Run vitest via npm test, parse summary line."""
    t0 = time.time()
    proc = subprocess.run(
        ["npm", "test", "--", "--run"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=180,
        env={**os.environ, "CI": "true", "FORCE_COLOR": "0"},
        shell=True,
    )
    elapsed = time.time() - t0
    combined = proc.stdout + proc.stderr

    passed_m = re.search(r'(\d+)\s+passed', combined)
    failed_m = re.search(r'(\d+)\s+failed', combined)
    p = int(passed_m.group(1)) if passed_m else 0
    f = int(failed_m.group(1)) if failed_m else 0
    total = p + f
    return {
        "ok": f == 0 and p > 0,
        "total": total,
        "passed": p,
        "failed": f,
        "pass_rate": round(p / total, 3) if total else 0,
        "elapsed_s": round(elapsed, 1),
        "returncode": proc.returncode,
    }


# ── Composite score ───────────────────────────────────────────────────────────

WEIGHTS = {
    "governance": 0.35,
    "cli":        0.20,
    "latency":    0.15,
    "knowledge":  0.20,
    "tests":      0.10,
}


def _latency_score(providers: list[dict]) -> float:
    """Lower latency → higher score. Normalise against 5000ms ceiling."""
    CEILING = 5000
    ok = [p for p in providers if p.get("ok") and p.get("p50_ms")]
    if not ok:
        return 0.5  # unknown
    best_p50 = min(p["p50_ms"] for p in ok)
    return max(0.0, min(1.0, 1.0 - best_p50 / CEILING))


def compute_composite(gov, cli, latency, knowledge, tests) -> dict[str, Any]:
    # Use live Petri recall if available; fall back to published blind-holdout.
    petri_recall = gov.get("petri_pattern_filter_recall")
    if petri_recall is not None:
        gov_score = petri_recall * 0.5 + gov.get("accuracy", 0) * 0.5 if gov.get("ok") else 0
    else:
        gov_score = gov.get("blind_detection_rate", 0) * 0.4 + gov.get("accuracy", 0) * 0.6 if gov.get("ok") else 0
    cli_score = cli["scbe_score"]["score"] if cli.get("ok") else 0
    lat_score = _latency_score(latency.get("providers", []))
    know_score = 0.0
    know_providers = [p for p in knowledge.get("providers", []) if p.get("ok")]
    if know_providers:
        know_score = sum(p["accuracy"] for p in know_providers) / len(know_providers)
    elif knowledge.get("skipped"):
        know_score = None
    test_score = tests.get("pass_rate", 0) if tests.get("ok") is not None else 0

    parts = {
        "governance": (gov_score,  WEIGHTS["governance"]),
        "cli":        (cli_score,  WEIGHTS["cli"]),
        "latency":    (lat_score,  WEIGHTS["latency"]),
        "knowledge":  (know_score, WEIGHTS["knowledge"]),
        "tests":      (test_score, WEIGHTS["tests"]),
    }
    effective_weight = sum(w for s, w in parts.values() if s is not None)
    total = sum(s * w for s, w in parts.values() if s is not None)
    composite = round(total / effective_weight, 3) if effective_weight else 0

    return {
        "composite": composite,
        "grade": _grade(composite),
        "parts": {k: {"score": round(s, 3) if s is not None else None, "weight": w} for k, (s, w) in parts.items()},
        "effective_weight": round(effective_weight, 3),
    }


def _grade(score: float) -> str:
    if score >= 0.90: return "A"
    if score >= 0.80: return "B"
    if score >= 0.70: return "C"
    if score >= 0.60: return "D"
    return "F"


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--skip-live", action="store_true", help="Skip live provider calls")
    args = parser.parse_args()

    print("SCBE-AETHERMOORE Full System Benchmark", flush=True)
    print("=" * 50, flush=True)

    print("\n[1/5] Governance accuracy...", flush=True)
    gov = run_governance_benchmark()
    petri_r = gov.get("petri_pattern_filter_recall")
    if petri_r is not None:
        tongue_only = gov.get("petri_tongue_only", 0)
        tongue_tag = f" +{tongue_only}✦KO" if tongue_only > 0 else ""
        petri_str = (
            f"  |  Petri(regex+KO): {petri_r:.1%} "
            f"({gov.get('petri_seeds_caught',0)}/{gov.get('petri_seeds_total',0)}{tongue_tag})"
        )
    else:
        petri_str = "  |  Petri: corpus not present"
    print(f"      synthetic: {gov.get('accuracy', 'N/A'):.1%}  |  blind-holdout: {gov.get('blind_detection_rate', 'N/A'):.1%}  |  hybrid: {gov.get('hybrid_detection_rate', 'N/A'):.1%}{petri_str}")

    print("\n[2/5] CLI capability...", flush=True)
    cli = run_cli_benchmark()
    if cli.get("ok"):
        top = cli["ranking"][0]
        scbe_row = next((r for r in cli["ranking"] if r["name"] == "scbe-geoseal"), None)
        scbe_pos = cli["ranking"].index(scbe_row) + 1 if scbe_row else "?"
        print(f"      scbe: {scbe_row['score']:.1%} ({scbe_row['passed']}/{scbe_row['total']}) — rank {scbe_pos}/{len(cli['ranking'])}")

    print("\n[3/5] Squad latency probe...", flush=True)
    if args.skip_live:
        latency = {"providers": []}
        print("      skipped (--skip-live)")
    else:
        latency = run_squad_latency_benchmark()
        for p in latency["providers"]:
            if p.get("ok"):
                print(f"      {p['provider']:12s}  p50={p['p50_ms']:.0f}ms  ({p['latencies_ms']})")
            else:
                print(f"      {p['provider']:12s}  {p.get('error', 'failed')}")

    print("\n[4/5] Knowledge accuracy (10 MMLU-style Q)...", flush=True)
    knowledge = run_knowledge_benchmark(skip_live=args.skip_live)
    if knowledge.get("skipped"):
        print("      skipped (--skip-live)")
    elif knowledge.get("ok"):
        for p in knowledge.get("providers", []):
            if p.get("ok"):
                print(f"      {p['provider']:12s}  {p['correct']}/{p['total']}  ({p['accuracy']:.0%})")
            else:
                print(f"      {p['provider']:12s}  {p.get('error', 'failed')}")

    print("\n[5/5] TypeScript test suite...", flush=True)
    tests = run_test_suite_benchmark()
    print(f"      {tests.get('passed', '?')}/{tests.get('total', '?')} passed  ({tests.get('pass_rate', 0):.1%})  [{tests.get('elapsed_s', '?')}s]")

    score = compute_composite(gov, cli, latency, knowledge, tests)

    report = {
        "schema_version": "scbe_full_benchmark_v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "platform": sys.platform,
        "skip_live": args.skip_live,
        "layers": {
            "governance": gov,
            "cli": cli,
            "latency": latency,
            "knowledge": knowledge,
            "tests": tests,
        },
        "score": score,
        "external_baselines": EXTERNAL_BASELINES,
    }

    # Save artifact
    out_dir = REPO_ROOT / "artifacts" / "benchmarks"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"scbe_full_benchmark_{stamp}.json"
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    # Print summary
    print("\n" + "=" * 50)
    print("COMPOSITE SCORE")
    print("=" * 50)
    for layer, part in score["parts"].items():
        s = part["score"]
        w = part["weight"]
        bar = ("█" * int((s or 0) * 20)).ljust(20) if s is not None else "─" * 20
        label = f"{s:.1%}" if s is not None else "skipped"
        print(f"  {layer:<12s} {bar}  {label}  (w={w:.0%})")
    print(f"\n  COMPOSITE     {'█' * int(score['composite'] * 20)}  {score['composite']:.1%}  grade={score['grade']}")

    print("\nExternal comparisons:")
    if gov.get("blind_detection_rate"):
        print("  Safety classifiers (balanced accuracy on blind holdout):")
        for b in EXTERNAL_BASELINES["safety_classifiers"]:
            marker = "← SCBE hybrid" if abs(b["score"] - gov.get("hybrid_detection_rate", 0)) < 0.02 else ""
            print(f"    {b['name']:20s}  {b['score']:.1%}  {marker}")
        print(f"    {'SCBE hybrid':20s}  {gov.get('hybrid_detection_rate', 0):.1%}  ← SCBE")
        print(f"    {'SCBE blind-only':20s}  {gov.get('blind_detection_rate', 0):.1%}")
    if knowledge.get("ok"):
        best_know = max((p["accuracy"] for p in knowledge.get("providers", []) if p.get("ok")), default=None)
        if best_know is not None:
            print("  LLM knowledge (MMLU-style 10Q):")
            for b in EXTERNAL_BASELINES["llm_quality_mmlu"]:
                print(f"    {b['name']:20s}  {b['score']:.1%}")
            print(f"    {'SCBE squad best':20s}  {best_know:.1%}  ← SCBE")

    print(f"\nArtifact: {out_path}")

    if args.json:
        print(json.dumps(report, indent=2))

    return 0 if score["composite"] >= 0.5 else 1


if __name__ == "__main__":
    raise SystemExit(main())
