"""Run the Biblical Null-Space probe suite against a live model.

Usage:
    python scripts/run_biblical_null_space_eval.py
    python scripts/run_biblical_null_space_eval.py --provider gemini
    python scripts/run_biblical_null_space_eval.py --provider openai --model gpt-4o-mini
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# Load env
env_path = Path(__file__).resolve().parent.parent / "config" / "connector_oauth" / ".env.connector.oauth"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            v = v.strip().strip("\"'")
            if k.strip() not in os.environ:
                os.environ[k.strip()] = v

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from tests.test_biblical_null_space import PROBES, score_response, run_null_space_analysis


def call_gemini(prompt: str, model: str = "gemini-2.5-flash") -> str:
    """Call Google Gemini API via google-genai SDK."""
    from google import genai

    api_key = os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))
    client = genai.Client(api_key=api_key)
    r = client.models.generate_content(
        model=model,
        contents=prompt,
        config={"temperature": 0.3, "max_output_tokens": 500},
    )
    return r.text


def call_openai(prompt: str, model: str = "gpt-4o-mini") -> str:
    """Call OpenAI API."""
    import urllib.request

    api_key = os.environ.get("OPENAI_API_KEY", "")
    url = "https://api.openai.com/v1/chat/completions"

    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 500,
    }).encode()

    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    })
    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read().decode())
    return data["choices"][0]["message"]["content"]


def call_xai(prompt: str, model: str = "grok-3-mini-fast") -> str:
    """Call xAI/Grok API (OpenAI-compatible)."""
    import urllib.request

    api_key = os.environ.get("XAI_API_KEY", "")
    base_url = os.environ.get("XAI_BASE_URL", "https://api.x.ai/v1")
    url = f"{base_url}/chat/completions"

    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 500,
    }).encode()

    req = urllib.request.Request(url, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    })
    resp = urllib.request.urlopen(req, timeout=30)
    data = json.loads(resp.read().decode())
    return data["choices"][0]["message"]["content"]


PROVIDERS = {
    "gemini": call_gemini,
    "openai": call_openai,
    "xai": call_xai,
}


def main():
    parser = argparse.ArgumentParser(description="Run Biblical Null-Space eval")
    parser.add_argument("--provider", default="gemini", choices=list(PROVIDERS.keys()))
    parser.add_argument("--model", default=None, help="Override model name")
    parser.add_argument("--output", default=None, help="Output JSON path")
    args = parser.parse_args()

    defaults = {"gemini": "gemini-2.5-flash", "openai": "gpt-4o-mini", "xai": "grok-3-mini-fast"}
    model = args.model or defaults[args.provider]
    call_fn = PROVIDERS[args.provider]

    print(f"Running 20 Biblical Null-Space probes against {args.provider}/{model}...")
    print(f"{'='*70}")

    scores = []
    for i, probe in enumerate(PROBES):
        try:
            response = call_fn(probe.prompt, model)
            result = score_response(probe, response)
            result["response_preview"] = response[:200]
            scores.append(result)

            symbol = {0: "NULL", 1: "WEAK", 2: "GOOD", 3: "FULL"}[result["score"]]
            print(f"  [{probe.id:5s}] {probe.tongue} {probe.pattern:20s} -> {symbol} ({result['score']}/3)  ideal={result['ideal_count']} anti={result['anti_count']}")

            time.sleep(0.5)  # rate limit
        except Exception as e:
            print(f"  [{probe.id:5s}] ERROR: {e}")
            scores.append({
                "probe_id": probe.id, "tongue": probe.tongue,
                "pattern": probe.pattern, "score": 0,
                "ideal_hits": [], "anti_hits": [],
                "ideal_count": 0, "anti_count": 0,
                "error": str(e),
            })

    print(f"\n{'='*70}")
    analysis = run_null_space_analysis(scores)

    print(f"\nTotal: {analysis['total_score']}/{analysis['max_score']} ({analysis['percentage']}%)")
    print(f"\nTongue means (0-3 scale):")
    for tongue, mean in sorted(analysis["tongue_means"].items()):
        bar = "#" * int(mean * 10)
        null_marker = " <-- NULL-SPACE" if mean < 1.0 else ""
        print(f"  {tongue}: {mean:.2f} [{bar:30s}]{null_marker}")

    print(f"\nPattern means:")
    for pattern, mean in sorted(analysis["pattern_means"].items()):
        bar = "#" * int(mean * 10)
        null_marker = " <-- NULL" if mean < 1.0 else ""
        print(f"  {pattern:20s}: {mean:.2f} [{bar:30s}]{null_marker}")

    if analysis["null_tongues"]:
        print(f"\nNULL-SPACE DETECTED in tongues: {', '.join(analysis['null_tongues'])}")
    else:
        print(f"\nNo null-space detected — all tongues above threshold")

    if analysis["null_patterns"]:
        print(f"NULL-SPACE DETECTED in patterns: {', '.join(analysis['null_patterns'])}")

    # Save results
    out_path = args.output or f"artifacts/biblical_null_space_{args.provider}_{model.replace('/', '_')}.json"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump({
            "provider": args.provider,
            "model": model,
            "timestamp": time.time(),
            "analysis": analysis,
            "scores": scores,
        }, f, indent=2)
    print(f"\nResults saved to: {out_path}")


if __name__ == "__main__":
    main()
