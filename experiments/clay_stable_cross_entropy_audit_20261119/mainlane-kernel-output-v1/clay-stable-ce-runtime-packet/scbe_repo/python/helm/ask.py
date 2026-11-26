"""ask: summon an AI in the terminal -- the AI-using-AI primitive, logged.

Send a prompt to a local model (Ollama by default, any OpenAI-compatible endpoint) and get TEXT
back. `ask` is the SUMMON layer: it returns the model's text; it does not execute it. That is not a
chain on the AI -- summoning and acting are different jobs. Acting on any of that text is the
SEPARATE gated-shell layer (the PowerShell fork), where the bounds are about SAFETY not chains:
they loosen for ordinary ops and hold the line only on destructive / drive-scope moves. So
"an AI in the terminal" = get its advice here, act through the gated shell there.

Every call writes an audit receipt (prompt digest + preview, response tail) to
artifacts/aetherdesk_receipts/ -- the same place AetherDesk logs its runs -- so AI-using-AI is
auditable. On a dead endpoint it returns ok=False with the error, never a fabricated answer.

    python -m python.helm.ask "in one sentence, what is a Poincare ball?"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Sequence

from . import free_generator as fg

ROOT = Path(__file__).resolve().parents[2]
RECEIPTS_DIR = ROOT / "artifacts" / "aetherdesk_receipts"
_RESPONSE_TAIL = 4000


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ask(
    prompt: str, model: Optional[str] = None, base: Optional[str] = None, key: Optional[str] = None, timeout: int = 120
) -> Dict[str, Any]:
    """Summon the model; return its TEXT (never executed here). ok=False on any endpoint failure."""
    base = base or os.environ.get("SCBE_LLM_BASE", fg.DEFAULT_BASE)
    key = key or os.environ.get("SCBE_LLM_KEY", "ollama")
    model = model or os.environ.get("SCBE_LLM_MODEL", fg.DEFAULT_MODEL)
    started = _now()
    try:
        text = fg._chat([{"role": "user", "content": prompt}], base=base, key=key, model=model, timeout=timeout)
        return {
            "ok": True,
            "model": model,
            "response": text,
            "error": None,
            "started_at": started,
            "finished_at": _now(),
        }
    except Exception as exc:  # honest: a dead endpoint yields no answer, never a guess
        return {
            "ok": False,
            "model": model,
            "response": "",
            "error": "%s: %s" % (type(exc).__name__, exc),
            "started_at": started,
            "finished_at": _now(),
        }


def log_ask(result: Dict[str, Any], prompt: str) -> Path:
    """Write an audit receipt for one AI summon (prompt hashed + previewed, response tail)."""
    RECEIPTS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    receipt = {
        "schema": "aetherdesk_ask_receipt_v1",
        "task_id": "%s_ask" % stamp,
        "model": result["model"],
        "prompt_digest": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "prompt_preview": prompt[:200],
        "response_tail": (result["response"] or "")[-_RESPONSE_TAIL:],
        "ok": result["ok"],
        "error": result["error"],
        "started_at": result["started_at"],
        "finished_at": result["finished_at"],
        "note": "advisory text only -- not executed; acting goes through the safety-gated shell",
    }
    path = RECEIPTS_DIR / (receipt["task_id"] + ".json")
    path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return path


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="scbe-ask", description="summon an AI in the terminal (logged; text only)")
    ap.add_argument("prompt", help="the prompt to send to the local model")
    ap.add_argument("--model", help="override the model (default: env SCBE_LLM_MODEL or free_generator default)")
    a = ap.parse_args(list(argv) if argv is not None else None)
    result = ask(a.prompt, model=a.model)
    path = log_ask(result, a.prompt)
    if not result["ok"]:
        print(
            "ask failed (%s) -- no answer returned, not a guess. receipt: %s" % (result["error"], path.name),
            file=sys.stderr,
        )
        return 1
    print(result["response"])
    print("\n[advisory text only -- not executed; receipt: %s]" % path.name, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
