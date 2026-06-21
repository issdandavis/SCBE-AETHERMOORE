"""miniwob_bench: run the SCBE AI browser against the MiniWoB++ (Farama) benchmark, scored by WOB_REWARD.

A TRUSTED third-party benchmark (Farama Foundation's standard web-interaction suite, 100+ self-hosted
synthetic tasks with exact rewards), driven by OUR Playwright stack and scored by MiniWoB's own reward
globals -- not a homemade metric.

Pieces:
  * serve()         -- start a static http server over miniwob's html dir (tasks load their own JS).
  * observe()       -- the agent's view of a task: the #query instruction + our element feed.
  * RulePolicy      -- a no-LLM baseline (parse the instruction, act).
  * LLMPolicy       -- a real model (default ollama qwen2.5-coder:3b) reads the observation and picks the
                       action -- the policy the stack is meant to carry.
  * run_task()      -- a step loop (observe -> policy.act -> our Move -> check WOB_DONE), up to max_steps.
  * run_bench()     -- runs a task list x seeds for a policy; returns per-task + overall solve rate.

    from python.scbe.ai_browser import AIBrowser
    from python.scbe.miniwob_bench import serve, run_bench, RulePolicy, LLMPolicy
    srv = serve(8099)
    with AIBrowser(headless=True) as br:
        rep = run_bench(br, ["click-test", "enter-text"], RulePolicy(), seeds=5)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional

from .ai_browser import AIBrowser, Move

BASE_URL = "http://localhost:%d/miniwob/%s.html"


def html_root() -> str:
    import miniwob

    return os.path.join(os.path.dirname(miniwob.__file__), "html")


def serve(port: int = 8099):
    """Start a static server over MiniWoB's html dir (so each task's relative JS/CSS resolves)."""
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port)],
        cwd=html_root(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc


def observe(br: AIBrowser, page) -> Dict[str, Any]:
    """The agent's view of the task: the #query instruction + the bounded element feed (with the current
    value of each text input, so a deterministic layer can tell when a field is already filled)."""
    q = page.evaluate("() => { const e = document.querySelector('#query'); return e ? e.innerText.trim() : ''; }")
    feed = br.read(page)
    els = []
    for e in feed["elements"]:
        item = {
            "ref": e["ref"],
            "tag": e["tag"],
            "name": (e.get("name") or "")[:40],
            "editable": bool(e.get("editable")),
        }
        if item["editable"]:
            try:
                item["value"] = page.eval_on_selector("[data-aibref='%s']" % e["ref"], "el => el.value || ''")
            except Exception:
                item["value"] = ""
        els.append(item)
    return {"instruction": q, "elements": els}


class RulePolicy:
    """No-LLM baseline: parse the instruction, pick one move."""

    name = "rule"

    def act(self, obs: Dict[str, Any]) -> Optional[Move]:
        q = obs["instruction"]
        ql = q.lower()
        els = obs["elements"]
        quoted = re.findall(r'"([^"]+)"', q)

        def find(target, tags=None):
            for e in els:
                if (tags is None or e["tag"] in tags) and target and target.lower() in e["name"].lower():
                    return e
            return None

        if ("enter" in ql or "type" in ql) and quoted:
            inp = next((e for e in els if e["editable"]), None)
            if inp:
                return Move("type", ref=inp["ref"], value=quoted[0])
        if "focus" in ql:
            inp = next((e for e in els if e["editable"] or e["tag"] == "input"), None)
            if inp:
                return Move("click", ref=inp["ref"])
        target = quoted[0] if quoted else (q.split()[-1].strip(".") if q.split() else "")
        el = find(target) or next((e for e in els if e["tag"] in ("button", "a")), None)
        return Move("click", ref=el["ref"]) if el else None


class LLMPolicy:
    """A real model reads the observation and chooses one action. Defaults to local ollama qwen-coder."""

    def __init__(self, model: str = "qwen2.5-coder:3b", base: Optional[str] = None):
        self.model = model
        self.base = base or os.environ.get("SCBE_LLM_BASE", "http://localhost:11434/v1")
        self.name = "llm:" + model

    def act(self, obs: Dict[str, Any]) -> Optional[Move]:
        from python.helm.free_generator import _chat

        listing = "\n".join(
            "  %s %s %r%s" % (e["ref"], e["tag"], e["name"], " [text input]" if e["editable"] else "")
            for e in obs["elements"]
        )
        prompt = (
            "You drive a web page to satisfy an instruction. Pick exactly ONE next action.\n\n"
            'Instruction: "%s"\n\nInteractive elements (ref tag name):\n%s\n\n'
            "Reply with ONLY one JSON object, no prose. One of:\n"
            '{"action":"click","ref":"rN"}  to click an element\n'
            '{"action":"type","ref":"rN","value":"text"}  to type into a text input\n'
            '{"action":"submit"}  to press Enter\n' % (obs["instruction"], listing or "  (none)")
        )
        try:
            resp = _chat([{"role": "user", "content": prompt}], base=self.base, key="ollama", model=self.model)
        except Exception:
            return None
        return _parse_action(resp, obs)


class HybridPolicy:
    """qwen-where-it's-reliable + a DETERMINISTIC substitution for the transitions it fumbles. The LLM
    recognizes targets and types; the 'focus the input' and 'submit once filled' transitions -- which a
    small model botches -- are issued deterministically instead. (Issac's 'lateral transition of
    submission': keep the model on what it nails, substitute the transition steps.)"""

    def __init__(self, llm: "LLMPolicy"):
        self.llm = llm
        self.name = "hybrid(" + llm.name + ")"

    def act(self, obs: Dict[str, Any]) -> Optional[Move]:
        ql = obs["instruction"].lower()
        # transition 1: 'focus the input' is deterministic -- the small model fumbles it, so just do it.
        if "focus" in ql and not any((e.get("value") or "") for e in obs["elements"] if e["editable"]):
            inp = next((e for e in obs["elements"] if e["editable"]), None)
            if inp:
                return Move("click", ref=inp["ref"])
        # transition 2: submit once a field is filled (the 'lateral transition of submission').
        needs_submit = ("submit" in ql) or ("press enter" in ql) or ("and press" in ql)
        filled = any((e.get("value") or "") for e in obs["elements"] if e["editable"])
        if needs_submit and filled:
            btn = next(
                (
                    e
                    for e in obs["elements"]
                    if e["tag"] == "button" and any(w in e["name"].lower() for w in ("submit", "ok", "done", "go"))
                ),
                None,
            )
            return Move("click", ref=btn["ref"]) if btn else Move("submit")
        return self.llm.act(obs)


def _parse_action(text: str, obs: Dict[str, Any]) -> Optional[Move]:
    m = re.search(r"\{[^{}]*\}", text or "", re.DOTALL)
    if not m:
        return None
    try:
        a = json.loads(m.group(0))
    except Exception:
        return None
    kind = str(a.get("action", "")).lower()
    refs = {e["ref"] for e in obs["elements"]}
    if kind == "submit":
        return Move("submit")
    ref = a.get("ref")
    if ref not in refs:
        return None
    if kind == "type":
        return Move("type", ref=ref, value=str(a.get("value", "")))
    if kind == "click":
        return Move("click", ref=ref)
    return None


def run_task(br: AIBrowser, url: str, policy, max_steps: int = 4) -> float:
    """Run one episode: START the task, then step observe->act until WOB_DONE or the step budget. Returns
    the final WOB_REWARD_GLOBAL (>0 = solved)."""
    page = br.open(url)
    page.wait_for_timeout(450)
    try:
        page.click("#sync-task-cover", timeout=4000)  # START the episode (genProblem runs)
    except Exception:
        pass
    page.wait_for_timeout(350)
    for _ in range(max_steps):
        if page.evaluate("() => window.WOB_DONE_GLOBAL"):
            break
        mv = policy.act(observe(br, page))
        if mv is None:
            break
        try:
            br.act(page, mv)
        except Exception:
            break
        page.wait_for_timeout(300)
    page.wait_for_timeout(250)
    r = page.evaluate("() => window.WOB_REWARD_GLOBAL")
    return float(r) if r is not None else 0.0


def run_bench(br: AIBrowser, tasks: List[str], policy, seeds: int = 5, port: int = 8099) -> Dict[str, Any]:
    results = {}
    solved = total = 0
    for task in tasks:
        ok = 0
        for _ in range(seeds):
            try:
                r = run_task(br, BASE_URL % (port, task), policy)
            except Exception:
                r = 0.0
            ok += 1 if r > 0 else 0
        results[task] = (ok, seeds)
        solved += ok
        total += seeds
    return {
        "policy": getattr(policy, "name", "?"),
        "solved": solved,
        "total": total,
        "rate": round(solved / total, 3) if total else 0.0,
        "per_task": results,
    }
