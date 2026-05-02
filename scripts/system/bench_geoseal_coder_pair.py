"""Side-by-side benchmark: scbe-geoseal-coder:q8 vs qwen2.5-coder:0.5b.

Hits the GeoSeal harness bridge (default 127.0.0.1:8766) so both candidates
go through the same OpenAI-compat path the Console uses. Two tracks:

  * coding   - generate a small Python function and exec-check it against
               canned inputs.
  * routing  - emit a JSON object selecting one of the six Sacred Tongues
               (KO, AV, RU, CA, UM, DR) for a described task.

Reports per-prompt pass/fail, latency, and an aggregate scorecard.
Writes JSON results to artifacts/bench/geoseal_coder_pair_<ts>.json.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.coding_spine.deterministic_tongue_router import route_prompt

ARTIFACT_DIR = REPO_ROOT / "artifacts" / "bench"

CHAMP = "scbe-geoseal-coder:q8"
CHALLENGER = "qwen2.5-coder:0.5b"

CODING_PROMPTS = [
    {
        "id": "add",
        "prompt": "Write a Python function `add(a, b)` that returns a + b. Output only a fenced ```python code block.",
        "fn": "add",
        "cases": [((1, 2), 3), ((-4, 4), 0), ((10, 7), 17)],
    },
    {
        "id": "reverse_string",
        "prompt": "Write a Python function `reverse_string(s)` that returns the reverse of s. Output only a fenced ```python code block.",
        "fn": "reverse_string",
        "cases": [(("abc",), "cba"), (("",), ""), (("racecar",), "racecar")],
    },
    {
        "id": "is_even",
        "prompt": "Write a Python function `is_even(n)` returning True if n is even else False. Output only a fenced ```python code block.",
        "fn": "is_even",
        "cases": [((0,), True), ((3,), False), ((-2,), True)],
    },
    {
        "id": "max_of_list",
        "prompt": "Write a Python function `max_of_list(xs)` returning the max of a non-empty list. Output only a fenced ```python code block.",
        "fn": "max_of_list",
        "cases": [(([1, 2, 3],), 3), (([-5, -1, -10],), -1), (([7],), 7)],
    },
    {
        "id": "count_vowels",
        "prompt": "Write a Python function `count_vowels(s)` that returns the number of vowels (aeiouAEIOU) in s. Output only a fenced ```python code block.",
        "fn": "count_vowels",
        "cases": [(("hello",), 2), (("BCD",), 0), (("AaEeIi",), 6)],
    },
    {
        "id": "fizzbuzz_one",
        "prompt": (
            "Write a Python function `fizzbuzz_one(n)` returning 'FizzBuzz' if n%15==0, "
            "'Fizz' if n%3==0, 'Buzz' if n%5==0, else str(n). Output only a fenced ```python code block."
        ),
        "fn": "fizzbuzz_one",
        "cases": [((15,), "FizzBuzz"), ((9,), "Fizz"), ((10,), "Buzz"), ((7,), "7")],
    },
]

# Sacred Tongues -> canonical coding-language map in docs/TONGUE_CODING_LANGUAGE_MAP.md
ROUTING_PROMPTS = [
    {
        "id": "py_dict",
        "prompt": (
            "Task: implement a Python helper that loads a JSON dict from disk. "
            "Choose the best Sacred Tongue (KO=Python, AV=TypeScript, RU=Rust, CA=C, UM=Julia, DR=Haskell). "
            'Reply with ONLY a JSON object: {"tongue": "<CODE>", "lang": "<language>"}. No prose.'
        ),
        "expect": "KO",
    },
    {
        "id": "js_dom",
        "prompt": (
            "Task: write a browser snippet that toggles a DOM class on click. "
            "Choose the best Sacred Tongue (KO=Python, AV=TypeScript, RU=Rust, CA=C, UM=Julia, DR=Haskell). "
            'Reply with ONLY a JSON object: {"tongue": "<CODE>", "lang": "<language>"}. No prose.'
        ),
        "expect": "AV",
    },
    {
        "id": "rust_safety",
        "prompt": (
            "Task: implement a memory-safe ring buffer with zero-cost abstractions. "
            "Choose the best Sacred Tongue (KO=Python, AV=TypeScript, RU=Rust, CA=C, UM=Julia, DR=Haskell). "
            'Reply with ONLY a JSON object: {"tongue": "<CODE>", "lang": "<language>"}. No prose.'
        ),
        "expect": "RU",
    },
    {
        "id": "c_symbolic",
        "prompt": (
            "Task: write a C function for a symbolic polynomial evaluator. "
            "Choose the best Sacred Tongue (KO=Python, AV=TypeScript, RU=Rust, CA=C, UM=Julia, DR=Haskell). "
            'Reply with ONLY a JSON object: {"tongue": "<CODE>", "lang": "<language>"}. No prose.'
        ),
        "expect": "CA",
    },
    {
        "id": "julia_spectral",
        "prompt": (
            "Task: build a Julia spectral anomaly detector using DataFrames. "
            "Choose the best Sacred Tongue (KO=Python, AV=TypeScript, RU=Rust, CA=C, UM=Julia, DR=Haskell). "
            'Reply with ONLY a JSON object: {"tongue": "<CODE>", "lang": "<language>"}. No prose.'
        ),
        "expect": "UM",
    },
    {
        "id": "haskell_monad",
        "prompt": (
            "Task: implement a pure-functional Maybe monad bind operator. "
            "Choose the best Sacred Tongue (KO=Python, AV=TypeScript, RU=Rust, CA=C, UM=Julia, DR=Haskell). "
            'Reply with ONLY a JSON object: {"tongue": "<CODE>", "lang": "<language>"}. No prose.'
        ),
        "expect": "DR",
    },
]


def call_pair(
    client: httpx.Client,
    bridge: str,
    prompt: str,
    models: list[str],
    max_tokens: int,
    system: str | None = None,
) -> dict:
    payload = {"prompt": prompt, "models": models, "temperature": 0.0, "max_tokens": max_tokens}
    if system is not None:
        payload["system"] = system
    r = client.post(f"{bridge}/harness/pair", json=payload, timeout=90.0)
    r.raise_for_status()
    return r.json()


CODE_FENCE = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_python(text: str) -> str | None:
    m = CODE_FENCE.search(text or "")
    if m:
        return m.group(1).strip()
    if text and "def " in text:
        return text.strip()
    return None


def exec_and_check(code: str, fn_name: str, cases: list[tuple]) -> tuple[bool, str]:
    if not code:
        return False, "no_code"
    runner = (
        code
        + "\n\nimport json,sys\n"
        + f"_results=[]\n_cases={cases!r}\n"
        + f"for args,expected in _cases:\n"
        + f"    try: _results.append({fn_name}(*args)==expected)\n"
        + f"    except Exception as e: _results.append(False)\n"
        + "print(json.dumps(_results))\n"
    )
    try:
        proc = subprocess.run(
            [sys.executable, "-c", runner],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        return False, "timeout"
    if proc.returncode != 0:
        return False, f"exec_err: {proc.stderr.strip()[:200]}"
    try:
        results = json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return False, f"no_json: {proc.stdout[:200]}"
    return all(results), f"cases={results}"


TONGUE_RX = re.compile(r'"tongue"\s*:\s*"([A-Z]{2})"')


def score_routing(text: str, expected: str) -> tuple[bool, str]:
    if not text:
        return False, "empty"
    m = TONGUE_RX.search(text)
    if m:
        return m.group(1) == expected, f"got={m.group(1)} expected={expected}"
    upper = text.upper()
    for code in ("KO", "AV", "RU", "CA", "UM", "DR"):
        if code in upper:
            return code == expected, f"loose={code} expected={expected}"
    return False, "no_code_in_text"


NEUTRAL_ROUTING_SYSTEM = (
    "You are a routing classifier. Reply ONLY with the requested JSON object and nothing else. "
    "No prose, no commentary, no code fences."
)


def run_track(client: httpx.Client, bridge: str, track: str, prompts: list, models: list[str]) -> list[dict]:
    rows = []
    for p in prompts:
        max_tok = 256 if track == "coding" else 64
        system = NEUTRAL_ROUTING_SYSTEM if track == "routing" else None
        t0 = time.perf_counter()
        try:
            res = call_pair(client, bridge, p["prompt"], models, max_tok, system=system)
        except httpx.HTTPError as exc:
            rows.append({"track": track, "id": p["id"], "error": f"http: {type(exc).__name__}: {exc}"})
            continue
        wall_ms = int((time.perf_counter() - t0) * 1000)
        a, b = res["a"], res["b"]

        if track == "coding":
            ok_a, det_a = exec_and_check(extract_python(a.get("text", "")) or "", p["fn"], p["cases"])
            ok_b, det_b = exec_and_check(extract_python(b.get("text", "")) or "", p["fn"], p["cases"])
        else:
            ok_a, det_a = score_routing(a.get("text", ""), p["expect"])
            ok_b, det_b = score_routing(b.get("text", ""), p["expect"])
            route = route_prompt(p["prompt"])
            ok_route = route.tongue == p["expect"]
            det_route = f"got={route.tongue} expected={p['expect']} source={route.source} reason={route.reason}"

        rows.append({
            "track": track,
            "id": p["id"],
            "wall_ms": wall_ms,
            "a_model": a.get("model"),
            "a_ok": ok_a,
            "a_detail": det_a,
            "a_text": (a.get("text") or "")[:400],
            "a_latency_ms": a.get("latency_ms"),
            "b_model": b.get("model"),
            "b_ok": ok_b,
            "b_detail": det_b,
            "b_text": (b.get("text") or "")[:400],
            "b_latency_ms": b.get("latency_ms"),
            **(
                {
                    "deterministic_route_ok": ok_route,
                    "deterministic_route_detail": det_route,
                    "deterministic_route": route.as_json(),
                }
                if track == "routing"
                else {}
            ),
        })
        flag_a = "PASS" if ok_a else "FAIL"
        flag_b = "PASS" if ok_b else "FAIL"
        route_flag = ""
        if track == "routing":
            route_flag = f" route={'PASS' if ok_route else 'FAIL'}"
        print(f"  [{track}/{p['id']}] champ={flag_a} chal={flag_b}{route_flag}  wall={wall_ms}ms")
    return rows


def summarize(rows: list[dict]) -> dict:
    summary = {}
    for track in {r["track"] for r in rows if "track" in r}:
        sub = [r for r in rows if r.get("track") == track]
        a_pass = sum(1 for r in sub if r.get("a_ok"))
        b_pass = sum(1 for r in sub if r.get("b_ok"))
        summary[track] = {
            "n": len(sub),
            "champ_pass": a_pass,
            "challenger_pass": b_pass,
            "champ_acc": round(a_pass / len(sub), 3) if sub else 0.0,
            "challenger_acc": round(b_pass / len(sub), 3) if sub else 0.0,
            "champ_avg_latency_ms": int(sum(r.get("a_latency_ms") or 0 for r in sub) / max(1, len(sub))),
            "challenger_avg_latency_ms": int(sum(r.get("b_latency_ms") or 0 for r in sub) / max(1, len(sub))),
        }
        if track == "routing":
            route_pass = sum(1 for r in sub if r.get("deterministic_route_ok"))
            summary[track]["deterministic_route_pass"] = route_pass
            summary[track]["deterministic_route_acc"] = round(route_pass / len(sub), 3) if sub else 0.0
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bridge", default="http://127.0.0.1:8766")
    parser.add_argument("--champ", default=CHAMP)
    parser.add_argument("--challenger", default=CHALLENGER)
    parser.add_argument("--track", choices=("all", "coding", "routing"), default="all")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    models = [args.champ, args.challenger]
    rows: list[dict] = []
    print(f"bench: champ={args.champ}  challenger={args.challenger}  bridge={args.bridge}")

    with httpx.Client() as client:
        if args.track in ("all", "coding"):
            print("-- coding track --")
            rows.extend(run_track(client, args.bridge, "coding", CODING_PROMPTS, models))
        if args.track in ("all", "routing"):
            print("-- routing track --")
            rows.extend(run_track(client, args.bridge, "routing", ROUTING_PROMPTS, models))

    summary = summarize(rows)
    out = args.out or ARTIFACT_DIR / f"geoseal_coder_pair_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "ts": datetime.now(timezone.utc).isoformat(),
                "bridge": args.bridge,
                "champ": args.champ,
                "challenger": args.challenger,
                "summary": summary,
                "rows": rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print()
    print("== SUMMARY ==")
    for track, s in summary.items():
        line = (
            f"  {track:8s}  champ {s['champ_pass']}/{s['n']} ({s['champ_acc']*100:.1f}%, "
            f"{s['champ_avg_latency_ms']}ms)   challenger {s['challenger_pass']}/{s['n']} "
            f"({s['challenger_acc']*100:.1f}%, {s['challenger_avg_latency_ms']}ms)"
        )
        if track == "routing":
            line += (
                f"   deterministic {s['deterministic_route_pass']}/{s['n']} "
                f"({s['deterministic_route_acc']*100:.1f}%)"
            )
        print(line)
    print(f"results -> {out}")


if __name__ == "__main__":
    main()
