"""Adapter-aware live smoke for the topological-receipt canary set.

Replays every canary prompt through the live HF adapter and scans the
adapter's response with ``governance_receipt``. Each canary is then
classified as:

- match       — adapter response stays in the same decision band
- drift       — one band shift (e.g. ALLOW prompt -> QUARANTINE response)
- regression  — two-band swing (ALLOW <-> DENY)

Exit code is non-zero only on regressions; drifts are reported but do
not block. The promotion gate can decide whether to require zero drifts
for a particular release.

Inputs:
    --canary-file   default: tests/canary/topological_receipt_canaries.json
    --model         HF model id (or SCBE_SMOKE_ADAPTER_MODEL env)
    --token         HF inference token (or HF_TOKEN env)
    --max-canaries  limit for fast smoke (default: all)
    --dry-run       skip the adapter call; echo the prompt as the response
                    (useful for plumbing checks without HF traffic)
    --json-out      write structured results to this path
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Callable

_HERE = Path(__file__).resolve()
_ROOT = _HERE.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from python.scbe.tri_braid_embedding import governance_receipt  # noqa: E402

DECISION_LEVEL: dict[str, int] = {"DENY": 0, "QUARANTINE": 1, "ALLOW": 2}


def call_hf_adapter(prompt: str, *, model: str, token: str, max_new_tokens: int = 256, timeout: float = 60.0) -> str:
    """POST to the HF Inference API and return generated text.

    Raises on HTTP error or unexpected response shape so the smoke can
    distinguish adapter errors from receipt regressions.
    """
    url = f"https://api-inference.huggingface.co/models/{model}"
    body = json.dumps(
        {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": int(max_new_tokens),
                "return_full_text": False,
            },
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body_preview = exc.read()[:300].decode("utf-8", errors="replace") if hasattr(exc, "read") else ""
        raise RuntimeError(f"HF inference HTTP {exc.code}: {body_preview}") from exc

    if isinstance(payload, list) and payload:
        text = payload[0].get("generated_text", "")
    elif isinstance(payload, dict) and "generated_text" in payload:
        text = payload["generated_text"]
    elif isinstance(payload, dict) and payload.get("error"):
        raise RuntimeError(f"HF inference error: {payload['error']}")
    else:
        raise RuntimeError(f"unexpected HF response shape: {str(payload)[:200]}")

    return str(text)


def echo_adapter(prompt: str, *, model: str = "<dry-run>", token: str = "<dry-run>", **_: object) -> str:
    """Dry-run adapter that returns the prompt verbatim.

    Used to exercise the smoke plumbing without spending HF inference
    quota. By definition this always matches because the response is
    identical to the prompt.
    """
    return prompt


def compare_decisions(prompt_decision: str, response_decision: str) -> dict[str, object]:
    """Classify the adapter's effect on the decision band."""
    p = DECISION_LEVEL[prompt_decision]
    r = DECISION_LEVEL[response_decision]
    delta = r - p
    if delta == 0:
        status = "match"
    elif abs(delta) == 1:
        status = "drift"
    else:
        status = "regression"
    return {
        "status": status,
        "delta": delta,
        "prompt_level": p,
        "response_level": r,
    }


def run_smoke(
    canary_file: Path,
    *,
    adapter: Callable[..., str],
    model: str,
    token: str,
    max_canaries: int | None = None,
    max_new_tokens: int = 256,
) -> dict[str, object]:
    data = json.loads(canary_file.read_text(encoding="utf-8"))
    canaries = data["canaries"]
    if max_canaries is not None:
        canaries = canaries[:max_canaries]

    results = []
    matches = 0
    drifts = 0
    regressions = 0
    errors = 0
    started = time.perf_counter()

    for canary in canaries:
        prompt = canary["prompt"]
        params = canary.get("params") or {}
        prompt_decision = canary["expected"]["decision"]

        try:
            response_text = adapter(prompt, model=model, token=token, max_new_tokens=max_new_tokens)
        except Exception as exc:  # noqa: BLE001 — we want to log every failure mode
            errors += 1
            results.append(
                {
                    "category": canary.get("category", "?"),
                    "prompt": prompt[:80],
                    "status": "error",
                    "error": str(exc)[:240],
                }
            )
            continue

        cleaned = response_text if response_text.strip() else "<empty adapter response>"
        response_receipt = governance_receipt(
            cleaned,
            masked_row=int(params.get("masked_row", 0)),
            masked_col=int(params.get("masked_col", 0)),
        )

        comparison = compare_decisions(prompt_decision, response_receipt["decision"])
        if comparison["status"] == "match":
            matches += 1
        elif comparison["status"] == "drift":
            drifts += 1
        else:
            regressions += 1

        results.append(
            {
                "category": canary.get("category", "?"),
                "prompt": prompt[:80],
                "prompt_decision": prompt_decision,
                "response_decision": response_receipt["decision"],
                "response_state": response_receipt["governance_state"],
                "response_action": response_receipt["security_action"],
                "response_trust": response_receipt["trust_level"],
                "comparison": comparison,
                "response_excerpt": cleaned[:120],
            }
        )

    elapsed = time.perf_counter() - started
    return {
        "schema_version": "scbe_adapter_smoke_v1",
        "model": model,
        "n": len(canaries),
        "elapsed_s": round(elapsed, 4),
        "matches": matches,
        "drifts": drifts,
        "regressions": regressions,
        "errors": errors,
        "results": results,
    }


def _format_table(result: dict[str, object]) -> str:
    lines = []
    lines.append(f"adapter smoke   model={result['model']}  n={result['n']}  elapsed={result['elapsed_s']}s")
    lines.append("-" * 80)
    lines.append(f"matches      {result['matches']}/{result['n']}")
    lines.append(f"drifts       {result['drifts']}")
    lines.append(f"regressions  {result['regressions']}")
    lines.append(f"errors       {result['errors']}")
    failures = [r for r in result["results"] if r.get("comparison", {}).get("status") == "regression"]
    drift_rows = [r for r in result["results"] if r.get("comparison", {}).get("status") == "drift"]
    error_rows = [r for r in result["results"] if r.get("status") == "error"]
    if failures:
        lines.append("")
        lines.append("REGRESSIONS (block promotion):")
        for r in failures:
            lines.append(f"  [{r['category']}] {r['prompt']!r}")
            lines.append(
                f"      prompt={r['prompt_decision']} response={r['response_decision']} "
                f"state={r['response_state']} action={r['response_action']}"
            )
    if drift_rows:
        lines.append("")
        lines.append("DRIFTS (review before promotion):")
        for r in drift_rows:
            lines.append(
                f"  [{r['category']}] prompt={r['prompt_decision']} response={r['response_decision']} "
                f"({r['prompt'][:60]!r})"
            )
    if error_rows:
        lines.append("")
        lines.append("ERRORS (adapter unreachable or bad response):")
        for r in error_rows:
            lines.append(f"  [{r['category']}] {r['prompt']!r}: {r['error'][:120]}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--canary-file",
        type=Path,
        default=_ROOT / "tests" / "canary" / "topological_receipt_canaries.json",
    )
    parser.add_argument("--model", type=str, default=os.environ.get("SCBE_SMOKE_ADAPTER_MODEL"))
    parser.add_argument(
        "--token",
        type=str,
        default=os.environ.get("HF_TOKEN") or os.environ.get("SCBE_SMOKE_ADAPTER_TOKEN"),
    )
    parser.add_argument("--max-canaries", type=int, default=None)
    parser.add_argument("--max-new-tokens", type=int, default=256)
    parser.add_argument("--dry-run", action="store_true", help="echo prompt as response, no HF traffic")
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args()

    if not args.canary_file.exists():
        print(f"canary file not found: {args.canary_file}", file=sys.stderr)
        return 2

    if args.dry_run:
        adapter: Callable[..., str] = echo_adapter
        model = args.model or "<dry-run>"
        token = args.token or "<dry-run>"
    else:
        if not args.model:
            print("error: --model required (or SCBE_SMOKE_ADAPTER_MODEL env)", file=sys.stderr)
            return 2
        if not args.token:
            print("error: --token required (or HF_TOKEN env)", file=sys.stderr)
            return 2
        adapter = call_hf_adapter
        model = args.model
        token = args.token

    result = run_smoke(
        args.canary_file,
        adapter=adapter,
        model=model,
        token=token,
        max_canaries=args.max_canaries,
        max_new_tokens=args.max_new_tokens,
    )
    print(_format_table(result))

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(result, indent=2, ensure_ascii=False))

    return 0 if result["regressions"] == 0 and result["errors"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
