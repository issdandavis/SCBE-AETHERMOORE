#!/usr/bin/env python3
"""mason_model_benchmark — does the mason let a FREE model punch above its weight?

The thesis (the whole reason the mason exists): a small/free model, streamed from the
web, should produce real working code by SELECTING + CHISELING pre-verified procedural
stones and reading verifier feedback move-by-move — instead of writing the whole program
blind. This benchmark measures that head-to-head, on the same targets, against the same
ground truth (real execution of each schematic's integration request).

Two conditions, identical PASS bar (the schematic's integration request runs green):

  FREESTYLE  the model is handed the spec (every slot's acceptance + the integration) and
             must emit ONE complete module. One shot. This is "write the program."

  MASON      for each slot in order the model is shown the resident's request and a MENU of
             candidate stones (the real one, the hollow stub, and a foreign stone from
             another pack). It returns {stone, fills}. The stone is chiseled and verified
             IN PLACE by real execution. A crack feeds the failure back and it re-picks
             (bounded retries, Reflexion-style); exhausting retries ESCALATES (counted, and
             the correct stone is placed so the build can continue — the big-model rung).

No model ever decides pass/fail — exit-0 of the acceptance subprocess is the only authority
(the load-bearing rule from docs/MASON_GAME_BOARD_DESIGN.md). The model only chooses and
chisels; the board catches it. Reported per cell: integration pass, plus for MASON the
slot-level first-try hits, total re-rolls, and escalations — the cost of the help.

Run:
  python scripts/eval/mason_model_benchmark.py --models gpt-oss-120b --trials 3
  python scripts/eval/mason_model_benchmark.py --models gpt-oss-120b zai-glm-4.7 --json out.json
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) scbe-mason-bench/1.0"
_CEREBRAS = "https://api.cerebras.ai/v1/chat/completions"


def _load_mason():
    spec = importlib.util.spec_from_file_location("mason", ROOT / "scripts" / "tools" / "mason.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["mason"] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


M = _load_mason()


# ─────────────────────────────────────────────────────────────────────────────
# Model call (Cerebras, OpenAI-compatible, stdlib only). Retries on rate limit.
# ─────────────────────────────────────────────────────────────────────────────
def call_model(model: str, messages: list[dict], *, max_tokens: int = 2048, temperature: float = 0.0) -> str:
    key = os.environ.get("CEREBRAS_API_KEY")
    if not key:
        raise RuntimeError("CEREBRAS_API_KEY not set")
    body = json.dumps(
        {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    ).encode()
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json", "User-Agent": _UA}
    last = ""
    for attempt in range(5):
        req = urllib.request.Request(_CEREBRAS, data=body, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.load(r)
            return d["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode()[:200]}"
            if e.code in (429, 503, 500, 502):
                time.sleep(2 * (attempt + 1))
                continue
            raise RuntimeError(last)
        except Exception as e:  # transient network
            last = f"{type(e).__name__}: {e}"
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"model call failed after retries: {last}")


def _extract_code(text: str) -> str:
    """Pull a python module out of a model reply (fenced or raw)."""
    fences = re.findall(r"```(?:python|py)?\s*\n(.*?)```", text, re.S)
    if fences:
        return max(fences, key=len).strip("\n")
    return text.strip("\n")


def _extract_json(text: str) -> dict | None:
    fences = re.findall(r"```(?:json)?\s*\n(.*?)```", text, re.S)
    for blob in sorted(fences, key=len, reverse=True):
        try:
            return json.loads(blob)
        except Exception:
            pass
    # last resort: first balanced {...}
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Spec rendering
# ─────────────────────────────────────────────────────────────────────────────
def _slot_specs(schematic) -> str:
    lines = []
    for i, slot in enumerate(schematic.slots, 1):
        lines.append(f"--- slot {i}: {slot.name} ---")
        lines.append("It must satisfy this check (runs with the earlier slots' code already defined):")
        lines.append(slot.acceptance)
        lines.append("")
    return "\n".join(lines)


def freestyle_prompt(schematic) -> list[dict]:
    spec = _slot_specs(schematic)
    user = (
        "Write ONE complete, self-contained Python module (standard library only, no I/O, "
        "deterministic) that makes ALL of the following checks pass. Define every class/"
        "function the checks reference at module top level. Do not include the checks "
        "themselves or any __main__ block — just the implementation.\n\n"
        f"{spec}\n"
        "Finally, this end-to-end scenario must also pass:\n"
        f"{schematic.integration}\n\n"
        "Return only the module inside a ```python code block."
    )
    return [
        {"role": "system", "content": "You are a precise Python engineer. Output only working code."},
        {"role": "user", "content": user},
    ]


def _candidate_menu(slot, pieces: dict, stubs: dict, foreign: dict) -> list[dict]:
    """The stones offered for a slot: the real one, its stub, and a foreign stone."""
    menu = []
    real = pieces[slot.piece]
    menu.append({"id": real.name, "shape": real.shape, "holes": list(real.holes), "_piece": real, "_correct": True})
    if slot.piece in stubs:
        st = stubs[slot.piece]
        menu.append({"id": st.name, "shape": st.shape, "holes": list(st.holes), "_piece": st, "_correct": False})
    if foreign:
        fid = sorted(foreign)[0]
        fp = foreign[fid]
        menu.append({"id": fp.name, "shape": fp.shape, "holes": list(fp.holes), "_piece": fp, "_correct": False})
    return menu


def mason_slot_prompt(slot, menu, placed_names: list[str], crack: str | None) -> list[dict]:
    catalog = "\n".join(
        f"  - stone '{c['id']}'  (shape: {c['shape']}; chisel holes: {c['holes'] or 'none'})" for c in menu
    )
    placed = ", ".join(placed_names) or "(none yet)"
    feedback = ""
    if crack:
        feedback = (
            "\nYour previous pick was CAPTURED by the verifier (it did not satisfy the request):\n"
            f"    {crack}\n"
            "Pick a different stone or fix the chisel values.\n"
        )
    user = (
        f"You are setting the next stone into slot '{slot.name}'. Stones already placed: {placed}.\n\n"
        "The resident's request (this exact code must run green once your stone is set):\n"
        f"{slot.acceptance}\n\n"
        "Available stones for this slot:\n"
        f"{catalog}\n"
        f"{feedback}\n"
        "Choose the stone whose behavior satisfies the request and provide the chisel-hole values "
        "(infer them from the request). Reply with ONLY a JSON object:\n"
        '  {"stone": "<stone id>", "fills": {"<HOLE>": <value>, ...}}\n'
        "Use {} for fills if the stone has no holes. Hole values are substituted verbatim, so give "
        "a Python literal (e.g. a number, a string of operator chars, or a dict like "
        '{"+": 1, "-": 1}).'
    )
    return [
        {"role": "system", "content": "You select and chisel pre-made code stones. Output only JSON."},
        {"role": "user", "content": user},
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Runners
# ─────────────────────────────────────────────────────────────────────────────
def run_freestyle(model: str, name: str, schematic, temperature: float) -> dict:
    try:
        reply = call_model(model, freestyle_prompt(schematic), max_tokens=3000, temperature=temperature)
    except Exception as e:
        return {"condition": "freestyle", "target": name, "passed": False, "error": str(e)[:200]}
    code = _extract_code(reply)
    ok, detail = M._verify(code, schematic.integration)
    return {
        "condition": "freestyle",
        "target": name,
        "passed": bool(ok),
        "detail": "" if ok else detail[:200],
        "code_chars": len(code),
    }


def run_mason(model: str, name: str, schematic, pieces, stubs, foreign, temperature: float, max_tries: int = 3) -> dict:
    placed_code: list[str] = []
    placed_names: list[str] = []
    slot_log = []
    rerolls = 0
    escalations = 0
    first_try_hits = 0

    for slot in schematic.slots:
        menu = _candidate_menu(slot, pieces, stubs, foreign)
        by_id = {c["id"]: c for c in menu}
        crack = None
        set_ok = False
        tries = 0
        used_escalation = False
        chosen = None
        for attempt in range(max_tries):
            tries += 1
            try:
                reply = call_model(
                    model, mason_slot_prompt(slot, menu, placed_names, crack), max_tokens=600, temperature=temperature
                )
            except Exception as e:
                crack = f"model error: {str(e)[:120]}"
                continue
            choice = _extract_json(reply) or {}
            cand = by_id.get(str(choice.get("stone", "")).strip())
            if cand is None:
                crack = f"no such stone {choice.get('stone')!r}; choose one of {list(by_id)}"
                continue
            fills = choice.get("fills", {}) or {}
            chosen = {"stone": cand["id"], "fills": fills}
            try:
                chiseled = cand["_piece"].chisel(
                    {k: fills[k] for k in cand["_piece"].holes} if cand["_piece"].holes else {}
                )
            except Exception as e:
                crack = f"chisel failed: {str(e)[:120]}"
                continue
            candidate_code = "\n\n".join(placed_code + [chiseled])
            ok, detail = M._verify(candidate_code, slot.acceptance)
            if ok:
                placed_code.append(chiseled)
                placed_names.append(slot.name)
                set_ok = True
                if attempt == 0 and cand["_correct"]:
                    first_try_hits += 1
                break
            crack = detail or "request failed"
            rerolls += 1
        if not set_ok:
            # escalate: the big-model rung places the known-correct stone so the build continues
            escalations += 1
            used_escalation = True
            correct = pieces[slot.piece]
            chiseled = correct.chisel(dict(slot.fills))
            placed_code.append(chiseled)
            placed_names.append(slot.name)
        slot_log.append({"slot": slot.name, "tries": tries, "escalated": used_escalation, "chosen": chosen})

    assembled = "\n\n".join(placed_code)
    ok, detail = M._verify(assembled, schematic.integration)
    return {
        "condition": "mason",
        "target": name,
        "passed": bool(ok),
        "integration_detail": "" if ok else detail[:200],
        "slots": len(schematic.slots),
        "first_try_hits": first_try_hits,
        "rerolls": rerolls,
        "escalations": escalations,
        "self_sufficient": escalations == 0,  # finished with zero big-model help
        "slot_log": slot_log,
    }


def _foreign_for(name: str) -> dict:
    """Distractor stones drawn from OTHER packs (wrong shape for this slot)."""
    foreign = {}
    for other, (_sc, pcs, _st) in M.REGISTRY.items():
        if other == name:
            continue
        for pid, piece in pcs.items():
            foreign.setdefault(piece.name, piece)
    return foreign


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="mason_model_benchmark")
    ap.add_argument("--models", nargs="+", default=["gpt-oss-120b"])
    ap.add_argument("--targets", nargs="+", default=sorted(M.REGISTRY))
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--temperature", type=float, default=0.2)
    ap.add_argument("--json", default=None, help="write full report JSON to this path")
    ap.add_argument("--conditions", nargs="+", default=["freestyle", "mason"], choices=["freestyle", "mason"])
    args = ap.parse_args(argv)

    cells = []
    for model in args.models:
        for target in args.targets:
            schematic, pieces, stubs = M.REGISTRY[target]
            foreign = _foreign_for(target)
            for trial in range(args.trials):
                for cond in args.conditions:
                    t0 = time.time()
                    if cond == "freestyle":
                        rec = run_freestyle(model, target, schematic, args.temperature)
                    else:
                        rec = run_mason(model, target, schematic, pieces, stubs, foreign, args.temperature)
                    rec.update({"model": model, "trial": trial, "seconds": round(time.time() - t0, 1)})
                    cells.append(rec)
                    mark = "PASS" if rec.get("passed") else "fail"
                    extra = ""
                    if cond == "mason" and "rerolls" in rec:
                        extra = (
                            f"  rerolls={rec['rerolls']} esc={rec['escalations']}"
                            f" firsttry={rec['first_try_hits']}/{rec['slots']}"
                        )
                    print(
                        f"  [{model}] {target:14s} {cond:9s} t{trial}: {mark}{extra}  ({rec['seconds']}s)", flush=True
                    )

    # aggregate
    summary = {}
    for model in args.models:
        for cond in args.conditions:
            rows = [c for c in cells if c["model"] == model and c["condition"] == cond]
            passed = sum(1 for c in rows if c.get("passed"))
            agg = {"pass": passed, "total": len(rows), "rate": round(passed / len(rows), 3) if rows else 0.0}
            if cond == "mason":
                msl = [c for c in rows if "rerolls" in c]
                if msl:
                    agg["self_sufficient"] = sum(1 for c in msl if c.get("self_sufficient"))
                    agg["total_rerolls"] = sum(c["rerolls"] for c in msl)
                    agg["total_escalations"] = sum(c["escalations"] for c in msl)
            summary[f"{model}/{cond}"] = agg

    report = {
        "schema_version": "mason_model_benchmark_v1",
        "models": args.models,
        "targets": args.targets,
        "trials": args.trials,
        "temperature": args.temperature,
        "summary": summary,
        "cells": cells,
    }

    print("\n=== summary ===")
    for key, agg in summary.items():
        line = f"  {key:32s} pass {agg['pass']}/{agg['total']} ({agg['rate']:.0%})"
        if "self_sufficient" in agg:
            line += (
                f"  self-sufficient={agg['self_sufficient']}"
                f"  rerolls={agg['total_rerolls']}  escalations={agg['total_escalations']}"
            )
        print(line)

    out = Path(args.json) if args.json else ROOT / "artifacts" / "mason" / "benchmark_report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nreport: {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
