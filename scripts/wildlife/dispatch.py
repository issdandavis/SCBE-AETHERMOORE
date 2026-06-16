"""Dispatch shepherds against the Wildlife Board.

Reads `.scbe/wildlife/board.json`, picks a shepherd per pack, and either:

  --plan     (default) — produces `.scbe/wildlife/dispatch_plan.json`
             showing what would happen per pack
  --execute  — actually calls the model for the chosen pack(s)

Cheap-first: sheep/crows hit local Ollama (free), goats/wolves hit HF
Router (cents). Dragons + horses are never auto-dispatched.

Usage:
    python scripts/wildlife/dispatch.py --plan
    python scripts/wildlife/dispatch.py --pack crows --execute --max 5
    python scripts/wildlife/dispatch.py --pack wolves --execute --max 3 \
        --hf-token-env HF_TOKEN
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
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.wildlife.packs import PACKS, severity_order  # noqa: E402
from scripts.wildlife.shepherds import (  # noqa: E402
    Shepherd,
    is_auto_dispatchable,
    render_prompt,
    shepherd_for,
)

DEFAULT_BOARD = ROOT / ".scbe" / "wildlife" / "board.json"
DEFAULT_PLAN_OUT = ROOT / ".scbe" / "wildlife" / "dispatch_plan.json"


def _load_board(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"[dispatch] no board at {path} - run " "`python scripts/wildlife/harvest_packs.py` first.")
    return json.loads(path.read_text(encoding="utf-8"))


def _animals_for(board: dict, pack: str) -> list[dict]:
    p = PACKS.get(pack.upper())
    if p is None:
        return []
    return board.get("packs", {}).get(p.plural, [])


def _take_topn(animals: list[dict], n: int) -> list[dict]:
    """Sort by lowest liberties first (most urgent), take top N."""
    return sorted(animals, key=lambda a: a.get("liberties", 99))[:n]


def call_ollama(model: str, prompt: str, base_url: str, timeout: int, retries: int = 3) -> dict:
    """One-shot completion against local Ollama HTTP API.

    `num_ctx` is held small so KV cache fits on consumer GPUs (6 GB VRAM
    can't hold the default 8 K context for a 1.5B model + prompt).
    `num_predict` caps reply length so a stuck model can't burn the
    whole timeout. `keep_alive` keeps the model resident between calls
    so a sustained sweep doesn't pay the load cost on every request.
    Transient 5xx (Ollama runner restart / brief OOM) is retried with
    backoff before giving up.
    """
    body = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "5m",
            "options": {"num_ctx": 1024, "num_predict": 220},
        }
    ).encode("utf-8")
    last_exc: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(
            url=base_url.rstrip("/") + "/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                return {
                    "ok": True,
                    "model": model,
                    "backend": "ollama",
                    "response": (data.get("response") or "").strip()[:1000],
                    "attempts": attempt + 1,
                }
        except urllib.error.HTTPError as exc:
            last_exc = exc
            if exc.code in {500, 502, 503, 504} and attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
                continue
            break
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            last_exc = exc
            break
    return {
        "ok": False,
        "model": model,
        "backend": "ollama",
        "error": f"{type(last_exc).__name__}: {last_exc}"[:200],
        "attempts": retries,
    }


def call_hf_router(model: str, prompt: str, token: str, timeout: int) -> dict:
    """One-shot chat completion against HuggingFace Router (OpenAI-compat)."""
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 220,
            "temperature": 0.2,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url="https://router.huggingface.co/v1/chat/completions",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            # Cloudflare in front of router.huggingface.co 403s the default
            # `Python-urllib/3.x` UA; send a normal one.
            "User-Agent": "scbe-wildlife-dispatch/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
            choice = (data.get("choices") or [{}])[0]
            content = (choice.get("message") or {}).get("content") or ""
            return {
                "ok": True,
                "model": model,
                "backend": "huggingface",
                "response": content.strip()[:1000],
            }
    except (urllib.error.URLError, urllib.error.HTTPError, OSError, json.JSONDecodeError) as exc:
        return {
            "ok": False,
            "model": model,
            "backend": "huggingface",
            "error": f"{type(exc).__name__}: {exc}"[:200],
        }


def dispatch_one(
    animal: dict,
    shepherd: Shepherd,
    *,
    ollama_url: str,
    hf_token: Optional[str],
    timeout: int,
) -> dict:
    """Run the shepherd against one animal and return the result envelope."""
    title = str(animal.get("title", ""))
    prompt = render_prompt(shepherd.pack, title)
    base = {
        "animal_id": animal.get("id"),
        "pack": shepherd.pack,
        "model": shepherd.model,
        "backend": shepherd.backend,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if prompt is None:
        return {**base, "ok": False, "skip_reason": "no auto-dispatchable shepherd"}
    if shepherd.backend == "ollama":
        result = call_ollama(shepherd.model, prompt, ollama_url, timeout)
    elif shepherd.backend == "huggingface":
        if not hf_token:
            return {
                **base,
                "ok": False,
                "skip_reason": "HF_TOKEN not set; cannot call HF Router",
            }
        result = call_hf_router(shepherd.model, prompt, hf_token, timeout)
    else:
        return {**base, "ok": False, "skip_reason": f"backend {shepherd.backend} not callable"}
    return {
        **base,
        **result,
        "title": title[:120],
        "prompt": prompt,
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def build_plan(board: dict, max_per_pack: int) -> dict:
    plan: dict[str, Any] = {
        "schema": "wildlife-dispatch-plan-v1",
        "board_harvested_at": board.get("harvested_at"),
        "by_pack": {},
        "totals": {"auto_dispatchable": 0, "human_only": 0, "skipped": 0},
    }
    for pname in severity_order():
        pack_obj = PACKS[pname]
        animals = _animals_for(board, pname)
        if not animals:
            continue
        shepherd = shepherd_for(pname)
        top = _take_topn(animals, max_per_pack)
        entry = {
            "count_total": len(animals),
            "count_planned": len(top),
            "shepherd": {
                "backend": shepherd.backend if shepherd else "n/a",
                "model": shepherd.model if shepherd else "n/a",
                "cost_tier": shepherd.cost_tier if shepherd else "n/a",
                "bus_dispatch": shepherd.bus_dispatch if shepherd else False,
            },
            "auto_dispatchable": is_auto_dispatchable(pname),
            "skip_reason": (
                None
                if is_auto_dispatchable(pname)
                else (
                    "human-only (dragons require a rider)"
                    if pname == "DRAGON"
                    else "training-pipeline-owned (horses run elsewhere)"
                )
            ),
            "preview": [{"id": a.get("id"), "title": a.get("title", "")[:80]} for a in top],
        }
        if entry["auto_dispatchable"]:
            plan["totals"]["auto_dispatchable"] += len(top)
        else:
            plan["totals"]["human_only"] += len(animals)
        plan["by_pack"][pack_obj.plural] = entry
    return plan


def execute(
    board: dict,
    *,
    pack_filter: Optional[str],
    max_per_pack: int,
    ollama_url: str,
    hf_token: Optional[str],
    timeout: int,
) -> list[dict]:
    """Actually call models for each (filtered) pack and return per-animal results."""
    results: list[dict] = []
    for pname in severity_order():
        if pack_filter and pack_filter.upper() != pname:
            plural = PACKS[pname].plural
            if pack_filter.lower() not in (plural.lower(), PACKS[pname].animal.lower()):
                continue
        if not is_auto_dispatchable(pname):
            continue
        animals = _animals_for(board, pname)
        if not animals:
            continue
        shepherd = shepherd_for(pname)
        for animal in _take_topn(animals, max_per_pack):
            results.append(
                dispatch_one(
                    animal,
                    shepherd,
                    ollama_url=ollama_url,
                    hf_token=hf_token,
                    timeout=timeout,
                )
            )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--board", default=str(DEFAULT_BOARD))
    parser.add_argument("--pack", default=None, help="restrict to one pack (wolves, sheep, ...)")
    parser.add_argument("--max", type=int, default=3, dest="max_per_pack")
    parser.add_argument("--plan", action="store_true", help="emit plan only (default if --execute absent)")
    parser.add_argument("--execute", action="store_true", help="actually call models")
    parser.add_argument("--plan-out", default=str(DEFAULT_PLAN_OUT), help="path for the plan json")
    parser.add_argument("--ollama-url", default=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"))
    parser.add_argument(
        "--hf-token-env",
        default="HF_TOKEN",
        help="env var holding HF token for HF-routed packs",
    )
    parser.add_argument("--timeout", type=int, default=45, help="per-call timeout seconds")
    args = parser.parse_args()

    board = _load_board(Path(args.board))
    plan = build_plan(board, args.max_per_pack)

    if not args.execute:
        out_path = Path(args.plan_out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[dispatch] plan written -> {out_path}")
        print(f"  auto-dispatchable animals: {plan['totals']['auto_dispatchable']}")
        print(f"  human-only animals:        {plan['totals']['human_only']}")
        for plural, entry in plan["by_pack"].items():
            shepherd = entry["shepherd"]
            mark = " [AUTO]" if entry["auto_dispatchable"] else " [SKIP]"
            print(
                f"  {plural:<10s} planned={entry['count_planned']}/{entry['count_total']} "
                f"{shepherd['backend']:<18s} {shepherd['model']}{mark}"
            )
        return 0

    hf_token = os.environ.get(args.hf_token_env) or ""
    results = execute(
        board,
        pack_filter=args.pack,
        max_per_pack=args.max_per_pack,
        ollama_url=args.ollama_url,
        hf_token=hf_token,
        timeout=args.timeout,
    )
    out_path = Path(args.plan_out).with_name("dispatch_results.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(
            {
                "schema": "wildlife-dispatch-results-v1",
                "ran_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "results": results,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    ok = sum(1 for r in results if r.get("ok"))
    skipped = sum(1 for r in results if r.get("skip_reason"))
    print(f"[dispatch] executed {len(results)} call(s) -> {out_path}")
    print(f"  ok={ok} skipped={skipped} failed={len(results) - ok - skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
