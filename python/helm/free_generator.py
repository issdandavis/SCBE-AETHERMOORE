"""A free, stdlib-only code generator for the verify loop -- backed by ANY
OpenAI-compatible endpoint: Ollama (local, $0 forever), Groq, Gemini, etc.

No `openai` package needed (uses urllib). Default target = local Ollama. Override via env:
  SCBE_LLM_BASE   (default http://localhost:11434/v1)   # Ollama; Groq: https://api.groq.com/openai/v1
  SCBE_LLM_KEY    (default "ollama")                     # any string for Ollama; real key for cloud
  SCBE_LLM_MODEL  (default qwen2.5-coder:7b)             # Groq e.g. llama-3.3-70b-versatile

The model only PROPOSES; public_bench / score_solutions DECIDES (runs the code, checks the
hidden tests, flags overfit). So a free/weaker model is safe -- nothing reaches the user unless
it actually ran and passed tests it never saw. On any failure this emits a stub that FAILS
verification rather than returning confident-but-wrong code.

    from python.helm.free_generator import make_generator
    from python.helm.public_bench import run_public_bench
    run_public_bench(problems, generator=make_generator(), public_k=1)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Sequence

DEFAULT_BASE = "http://localhost:11434/v1"  # Ollama's OpenAI-compatible endpoint
DEFAULT_MODEL = "qwen2.5-coder:7b"


def _chat(messages, *, base: str, key: str, model: str, timeout: int = 120) -> str:
    """POST to an OpenAI-compatible /chat/completions endpoint; return the message text."""
    body = json.dumps({"model": model, "messages": messages, "temperature": 0}).encode("utf-8")
    req = urllib.request.Request(
        base.rstrip("/") + "/chat/completions",
        data=body,
        headers={"content-type": "application/json", "authorization": f"Bearer {key}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310 - user-configured LLM endpoint
        data = json.loads(r.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]


def strip_to_code(text: str) -> str:
    """Pull the code out of a model reply. Robust to: fenced ```python blocks (takes the LARGEST), a
    truncated/unclosed fence, bare code with no fences, and leading prose before the first code line.

    The naive version (return-whole-text when no closing fence) silently fed prose/markdown into the
    verifier, so good solutions failed to parse -- which crushed the repair-loop + harvest solve rates.
    This is the same extraction the lift notebook uses; fixing it here lifts every caller at once."""
    blocks = re.findall(r"```(?:python)?\s*(.*?)```", text or "", re.S)
    if blocks:
        return max(blocks, key=len).strip()
    body = re.sub(r"^\s*```(?:python)?\s*", "", (text or "").strip())  # drop a dangling open fence
    lines = body.splitlines()
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith(("def ", "import ", "from ", "class ", "@")):
            return "\n".join(lines[i:]).strip()
    return body.strip()


def make_generator(
    base: Optional[str] = None,
    key: Optional[str] = None,
    model: Optional[str] = None,
    public_k: int = 1,
) -> Callable[[Dict[str, Any]], str]:
    """Build a generator(problem) -> source backed by a free OpenAI-compatible model."""
    base = base or os.environ.get("SCBE_LLM_BASE", DEFAULT_BASE)
    key = key or os.environ.get("SCBE_LLM_KEY", "ollama")
    model = model or os.environ.get("SCBE_LLM_MODEL", DEFAULT_MODEL)

    def generator(problem: Dict[str, Any]) -> str:
        public = "\n".join(list(problem.get("test_list", []))[:public_k])
        prompt = (
            (problem.get("prompt") or problem.get("text") or "").strip()
            + "\n\nWrite a complete Python solution. It must make this example pass:\n"
            + public
            + "\nReturn ONLY the code."
        )
        try:
            return strip_to_code(_chat([{"role": "user", "content": prompt}], base=base, key=key, model=model))
        except Exception as exc:  # fail closed: emit code that FAILS the tests, never confident-wrong code
            return f"# generation failed ({type(exc).__name__}: {exc})\ndef _failed(*a, **k):\n    return None\n"

    generator.__name__ = "free_llm(%s)" % model
    return generator


def _diagnose(code: str, asserts: Sequence[str], imports: Sequence[str], timeout: int = 15) -> List[str]:
    """Run each failing assert and report GOT-vs-EXPECTED (or the raised exception) -- the signal a
    bare 'AssertionError()' lacks. Brace-safe (built by line-join, not str.format)."""
    runner = "\n".join(
        list(imports)
        + [
            code,
            "import json as _j",
            "_A = " + repr(list(asserts)),
            "_O = []",
            "for _a in _A:",
            "    try:",
            "        exec(_a, globals()); continue",
            "    except Exception as _e:",
            "        _err = repr(_e)",
            "    _b = _a[7:].strip() if _a.strip().startswith('assert ') else _a",
            "    if ' == ' in _b:",
            "        _l, _r = _b.split(' == ', 1)",
            "        try:",
            "            _g = repr(eval(_l))",
            "        except Exception as _e2:",
            "            _g = '<raised ' + repr(_e2) + '>'",
            "        try:",
            "            _x = repr(eval(_r))",
            "        except Exception:",
            "            _x = _r",
            "        _O.append(_a + '  ->  got ' + _g + ', expected ' + _x)",
            "    else:",
            "        _O.append(_a + '  ->  ' + _err)",
            "print(_j.dumps(_O))",
        ]
    )
    try:
        proc = subprocess.run([sys.executable, "-c", runner], capture_output=True, text=True, timeout=timeout)
        if proc.returncode == 0 and proc.stdout.strip():
            return json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception:
        pass
    return list(asserts)


def _norm_code(code: str) -> str:
    """Normalize code for stuck-detection: drop blank/comment-only lines and collapse whitespace, so
    cosmetic edits don't hide that the model is regenerating the SAME approach (its stuck prior)."""
    out = []
    for line in (code or "").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        out.append(" ".join(s.split()))
    return "\n".join(out)


def make_repair_generator(
    base: Optional[str] = None,
    key: Optional[str] = None,
    model: Optional[str] = None,
    public_k: int = 1,
    rounds: int = 3,
) -> Callable[[Dict[str, Any]], str]:
    """Execution-feedback repair -- the CODE-ladder analog of routing reasoning through execution.

    The model writes code; we RUN it against the PUBLIC example(s) only and, on failure, feed the code
    plus a got-vs-expected diagnosis back and let it fix, up to `rounds` times. Hidden tests stay held
    out (the model never sees them), so any gain is honest lift, not leakage.

    STUCK-PRIOR DETECTOR: plain "fix it" retries hit the same reflex (e.g. the memorized fizzbuzz keeps
    coming back). When the model REGENERATES an approach it already tried, that is its stuck prior --
    so the next round escalates from "fix this" to "you are stuck, solve it a STRUCTURALLY DIFFERENT
    way", which attacks the prior-override wall instead of bouncing off it."""
    base = base or os.environ.get("SCBE_LLM_BASE", DEFAULT_BASE)
    key = key or os.environ.get("SCBE_LLM_KEY", "ollama")
    model = model or os.environ.get("SCBE_LLM_MODEL", DEFAULT_MODEL)
    first = make_generator(base=base, key=key, model=model, public_k=public_k)

    def generator(problem: Dict[str, Any]) -> str:
        from . import public_bench as pb  # lazy import avoids any cycle

        head = (problem.get("prompt") or problem.get("text") or "").strip()
        public = list(problem.get("test_list", []))[:public_k]
        imports = list(problem.get("test_imports", []))
        code = first(problem)
        seen = {_norm_code(code)}  # approaches already tried
        stuck = False
        for _ in range(rounds):
            res = pb._verify(code, public, [], imports)  # PUBLIC only; hidden never shown
            if res.get("public_passed"):
                break
            feedback = "\n".join(str(d) for d in _diagnose(code, public, imports))[:700]
            if stuck:
                # the model keeps regenerating the same failing approach -> force a different one
                prompt = (
                    head
                    + "\n\nYou are STUCK: you keep producing essentially the same solution and it keeps failing the"
                    + " SAME check. Do NOT reuse your previous approach or structure. Solve it a DIFFERENT way --"
                    + " handle every condition explicitly and in the right order (including combined/overlapping"
                    + " cases), and make sure the failing input below is handled.\n\nFailing check (got vs expected):\n"
                    + feedback
                    + "\nReturn ONLY new Python code, structured differently."
                )
            else:
                prompt = (
                    head
                    + "\n\nYour previous code:\n"
                    + code
                    + "\n\nIt FAILED these checks (showing got vs expected):\n"
                    + feedback
                    + "\nFix the function so every check passes. Return ONLY corrected Python code."
                )
            try:
                code = strip_to_code(_chat([{"role": "user", "content": prompt}], base=base, key=key, model=model))
            except Exception:
                break
            n = _norm_code(code)
            stuck = n in seen  # regenerated an approach already tried -> escalate next round
            seen.add(n)
        return code

    generator.__name__ = "repair_llm(%s,r=%d)" % (model, rounds)
    return generator
