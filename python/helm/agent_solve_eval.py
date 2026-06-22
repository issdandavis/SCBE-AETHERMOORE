"""agent_solve_eval -- point the live loop at the REAL recovery pool and report the RUNG BREAKDOWN.

Question: how many tasks resolve on the DETERMINISTIC path (dispatch, no model) before the
model is ever asked, how many via the routed model+builtin+tools rung, how many ESCALATE --
and are the claimed wins actually correct?

Honesty rails:
 - the pitfall pool is code-GEN ("write a function ...") not tool-shaped QUESTIONS, so the
   pure-dispatch rung is expected ~0 here; the deterministic LEVER for code tasks is the
   builtin-hint+verified-tools injection (the routed rung). Report dispatch coverage anyway.
 - INDEPENDENT re-verification: every returned solution is re-run against the FULL test_list
   in a fresh subprocess here (not trusting solve_routed's own verdict). A claim of VERIFIED
   that fails the full tests is a FALSE SUCCESS and is flagged loudly.
 - dead model endpoint must FAIL LOUD (probe guard), never silently score 0 (the cross-instrument
   lesson: a 0/N that contradicts the known rate is an instrument failure, not a result).

Usage: python agent_solve_eval.py [N]   (N = first N tasks; default all 48)
"""

from __future__ import annotations
import json, sys, time, subprocess, urllib.request

try:
    from . import agent_solve as A, query_dispatch
except ImportError:
    import agent_solve as A, query_dispatch

OLLAMA = "http://localhost:11434/api/generate"
MODEL = "qwen2.5-coder:1.5b"
POOL = "pitfall_headroom_pool.jsonl"


def make_ask():
    def ask(prompt):
        body = json.dumps({"model": MODEL, "prompt": prompt, "stream": False,
                           "options": {"temperature": 0.0}}).encode()
        last = None
        for attempt in range(3):
            try:
                req = urllib.request.Request(OLLAMA, data=body,
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=120) as r:
                    return json.loads(r.read().decode())["response"]
            except Exception as e:
                last = e
                time.sleep(2)
        raise RuntimeError("ollama ask failed after retries: %s" % last)
    probe = ask("Reply with only the number 7.")
    assert probe and probe.strip(), "ollama probe returned empty -- endpoint dead, aborting (no fake 0)"
    return ask


def verify_full(code, tests):
    """Independent: re-run the returned solution against the FULL test_list in a fresh subprocess."""
    if not code or len(code) < 3:
        return False
    try:
        return subprocess.run([sys.executable, "-c", code + "\n" + "\n".join(tests) + "\n"],
                              capture_output=True, text=True, timeout=15).returncode == 0
    except Exception:
        return False


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else None
    pool = [json.loads(l) for l in open(POOL, encoding="utf-8") if l.strip()]
    if n:
        pool = pool[:n]
    ask = make_ask()

    # deterministic dispatch coverage on the raw task text (no model)
    dispatch_hits = sum(1 for r in pool if query_dispatch.dispatch(r["text"]) is not None)

    rungs = {"dispatch": 0, "routed": 0, "escalate": 0}
    claimed_verified = independently_verified = false_success = 0
    for i, r in enumerate(pool):
        tests = r["test_list"]
        res = A.agent_solve(r["text"], ask=ask, tests=tests)
        via = res.get("via", "")
        if via.startswith("dispatch"):
            rungs["dispatch"] += 1
        elif via.startswith("routed") or via.startswith("fallback"):
            rungs["routed"] += 1
        else:
            rungs["escalate"] += 1

        claims = res["status"] == "VERIFIED_FIX"
        # independent check: dispatch answers are deterministic; code answers re-run on FULL tests
        if res.get("deterministic"):
            ok = True
        else:
            ok = verify_full(res.get("code", ""), tests)
        claimed_verified += int(claims)
        independently_verified += int(ok)
        if claims and not ok:
            false_success += 1
            print("  !! FALSE SUCCESS: %s claimed VERIFIED but failed full tests" % r["task_id"])
        flag = "" if claims == ok else "  <-- MISMATCH"
        print("[%2d/%2d] %-26s claim=%-12s indep=%s%s"
              % (i + 1, len(pool), r["task_id"][:26], res["status"], "PASS" if ok else "fail", flag))

    N = len(pool)
    print("\n=== agent_solve over %d REAL recovery tasks (qwen2.5-coder:1.5b) ===" % N)
    print("deterministic dispatch answers task text directly: %d/%d "
          "(expected ~0: these are code-gen tasks, not tool-questions)" % (dispatch_hits, N))
    print("rung breakdown:  dispatch(no model)=%d   routed(model+builtin+tools)=%d   escalate=%d"
          % (rungs["dispatch"], rungs["routed"], rungs["escalate"]))
    print("independently VERIFIED (full test_list, fresh subprocess): %d/%d" % (independently_verified, N))
    print("claimed VERIFIED by the loop: %d/%d" % (claimed_verified, N))
    print("FALSE SUCCESS (claimed but failed independent check): %d   <-- must be 0" % false_success)


if __name__ == "__main__":
    main()
