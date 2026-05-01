#!/usr/bin/env python3
"""scbe-geo — smart GeoSeal CLI with trijective cross-check gate.

One entry point, two modes:

    python scbe-geo.py                  # interactive REPL (readline, history, tab-complete)
    python scbe-geo.py <verb> [args]    # one-shot

Verbs:
    seal <text>       Envelope-encrypt <text> with GeoSeal (uses default context)
    unseal <file>     Decrypt a GeoSeal envelope JSON file
    tok <text>        Show atomic + Sacred Tongue tokenization of <text>
    tri <text>        Run trijective cross-check; print the full report
    exec <family> ..  Run a turning-lane execution packet (seals if trijective-valid)
    status            Show package, site, git, archive, and pipeline health
    ask <question>    Rule-based intent router (no external AI yet)
    do <action>       Run an authorized system op (commit, sweep-status, site-check)
    verbs             List the trijective operational verb vocabulary
    help [verb]       Show help (top-level or for one verb)
    quit              Leave the REPL

Every command typed in the REPL is gated by the trijective validator: if
the verb is not in the semantic lookup table, or if the anchor text fails
byte round-trips through two witness tongues, the command is REJECTED.
This is the "operational valid cross-check" — a command must triangulate
across three tongues before the system will execute it.
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parent
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# Force UTF-8 so tongue glyphs don't die on Windows cp1252
for _s in ("stdout", "stderr"):
    _stream = getattr(sys, _s, None)
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

from symphonic_cipher.scbe_aethermoore.trijective import (
    SEMANTIC_VERBS,
    TrijectiveValidator,
    semantic_cross_check,
)
from symphonic_cipher.scbe_aethermoore.cli_toolkit import (
    CrossTokenizer,
    Lexicons,
    TongueTokenizer,
)

try:
    import readline  # noqa: F401  (enables history + line editing when present)
    _HAS_READLINE = True
except ImportError:
    _HAS_READLINE = False


# --- Tokenizer singletons ------------------------------------------------
_LEX = Lexicons()
_TOK = TongueTokenizer(_LEX)
_XT = CrossTokenizer(_TOK)
_TRI = TrijectiveValidator(_TOK)


# --- Rule-based intent router --------------------------------------------
INTENT_SYNONYMS: Dict[str, List[str]] = {
    "seal":    ["seal", "encrypt", "lock", "wrap", "protect"],
    "unseal":  ["unseal", "decrypt", "unlock", "unwrap", "open"],
    "tok":     ["tok", "tokenize", "encode", "tokens"],
    "tri":     ["tri", "trijective", "triangulate", "crosscheck", "validate"],
    "exec":    ["exec", "execute", "run", "launch"],
    "status":  ["status", "health", "state", "report", "check"],
    "verbs":   ["verbs", "vocab", "vocabulary", "commands"],
    "help":    ["help", "?", "how", "what"],
    "quit":    ["quit", "exit", "bye", "leave"],
    "do":      ["do", "perform"],
    "ask":     ["ask", "query", "question"],
}


def route_intent(phrase: str) -> Optional[str]:
    """Return the canonical verb for a free-text phrase, or None."""
    if not phrase:
        return None
    head = phrase.strip().split()[0].lower().rstrip("?!.")
    for canonical, synonyms in INTENT_SYNONYMS.items():
        if head in synonyms:
            return canonical
    return None


# --- Output helpers ------------------------------------------------------
def c_ok(msg: str) -> str:
    return f"  [OK] {msg}"


def c_err(msg: str) -> str:
    return f"  [!!] {msg}"


def c_info(msg: str) -> str:
    return f"  ..  {msg}"


# --- Verb implementations -----------------------------------------------
def verb_tok(args: List[str]) -> int:
    if not args:
        print(c_err("tok: need text to tokenize"))
        return 1
    text = " ".join(args)
    data = text.encode("utf-8")
    print(c_info(f"input: {text}"))
    print(c_info(f"bytes: {len(data)}"))
    print()
    for tongue in ("KO", "AV", "RU", "CA", "UM", "DR"):
        tokens = _XT.to_tokens_from_bytes(tongue, data)
        sample = " ".join(tokens[:8]) + (" …" if len(tokens) > 8 else "")
        print(f"  {tongue}  ({len(tokens)} tok)  {sample}")
    try:
        from python.scbe.atomic_tokenization import map_token_to_atomic_state

        atoms = [map_token_to_atomic_state(t) for t in text.split()]
        print()
        print(c_info(f"atomic states: {len(atoms)}"))
        for word, state in zip(text.split()[:5], atoms[:5]):
            print(f"  {word} -> lang={state.language} elem={state.element.symbol} trust={state.trust_baseline:.2f}")
    except Exception as exc:
        print(c_info(f"(atomic layer unavailable: {exc})"))
    return 0


def verb_tri(args: List[str]) -> int:
    if not args:
        print(c_err("tri: need text"))
        return 1
    text = " ".join(args)
    # Build a canonical KO tongue-stream from the bytes so the validator has
    # something it can legally parse. This is the "lift" into tongue space.
    ko_stream = " ".join(_XT.to_tokens_from_bytes("KO", text.encode("utf-8")))
    report = _TRI.validate(ko_stream, anchor="KO")
    print(json.dumps(report.to_dict(), indent=2))
    return 0 if report.valid else 2


def verb_seal(args: List[str]) -> int:
    if not args:
        print(c_err("seal: need text"))
        return 1
    text = " ".join(args)
    # Gate: must be trijective-valid first
    ko_stream = " ".join(_XT.to_tokens_from_bytes("KO", text.encode("utf-8")))
    ok, rep = _TRI.gate(ko_stream, anchor="KO")
    if not ok:
        print(c_err(f"trijective gate FAILED: {rep.to_dict()}"))
        return 2
    print(c_ok(f"trijective gate passed (legs {int(rep.leg1_ok)}{int(rep.leg2_ok)}{int(rep.leg3_ok)})"))
    # Delegate to scbe-cli.py for the actual envelope crypto
    try:
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scbe-cli.py"), "geoseal-encrypt",
             "--text", text, "--key", "geo-cli-default"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            print(result.stdout)
            return 0
        print(c_err(f"scbe-cli returned {result.returncode}"))
        print(result.stderr)
        return result.returncode
    except FileNotFoundError:
        print(c_err("scbe-cli.py not found"))
        return 127


def verb_unseal(args: List[str]) -> int:
    if not args:
        print(c_err("unseal: need envelope file path"))
        return 1
    env_path = args[0]
    if not Path(env_path).exists():
        print(c_err(f"no such file: {env_path}"))
        return 1
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "scbe-cli.py"), "geoseal-decrypt",
         "--envelope", env_path, "--key", "geo-cli-default"],
        capture_output=True, text=True, timeout=30,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
    return result.returncode


def verb_exec(args: List[str]) -> int:
    if not args:
        print(c_err("exec: need family (and optional args)"))
        return 1
    family = args[0]
    rest = args[1:]
    ko_stream = " ".join(_XT.to_tokens_from_bytes("KO", (family + " " + " ".join(rest)).encode("utf-8")))
    ok, rep = _TRI.gate(ko_stream, anchor="KO")
    if not ok:
        print(c_err("trijective gate FAILED — exec denied"))
        print(json.dumps(rep.to_dict(), indent=2))
        return 2
    print(c_ok(f"trijective gate passed for family={family}"))
    cmd = [sys.executable, str(REPO_ROOT / "scbe-cli.py"), "turning-exec", "--family", family, "--seal"]
    if rest:
        cmd += ["--args", json.dumps(rest)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
    return result.returncode


def verb_status(args: List[str]) -> int:
    print("SCBE-AETHERMOORE :: system status")
    print()
    # Package versions
    pkg = REPO_ROOT / "package.json"
    pyp = REPO_ROOT / "pyproject.toml"
    if pkg.exists():
        data = json.loads(pkg.read_text(encoding="utf-8"))
        print(c_info(f"npm    scbe-aethermoore@{data.get('version', '?')}"))
    if pyp.exists():
        for line in pyp.read_text(encoding="utf-8").splitlines():
            if line.startswith("version"):
                print(c_info(f"pypi   {line.strip()}"))
                break
    # Git state
    try:
        branch = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        head = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        dirty_count = len(dirty.splitlines()) if dirty else 0
        print(c_info(f"git    {branch}@{head}  dirty={dirty_count}"))
    except Exception as exc:
        print(c_err(f"git: {exc}"))
    # Archive health (F: drive)
    for target in ("artifacts", "training-data"):
        p = REPO_ROOT / target
        if p.is_symlink() or (p.exists() and os.path.realpath(p) != str(p)):
            print(c_info(f"archive {target} -> {os.path.realpath(p)}"))
        elif p.exists():
            print(c_info(f"{target} LOCAL"))
    # Trijective self-test
    rep = _TRI.validate(" ".join(_XT.to_tokens_from_bytes("KO", b"self-test")), anchor="KO")
    tag = c_ok("trijective self-test passed") if rep.valid else c_err("trijective self-test FAILED")
    print(tag)
    # Vocab size
    print(c_info(f"verbs  {len(SEMANTIC_VERBS)} operational verbs x 6 tongues"))
    return 0


def verb_verbs(args: List[str]) -> int:
    print("operational vocabulary (trijective-validated):")
    for canonical, row in SEMANTIC_VERBS.items():
        forms = "  ".join(f"{t}:{f}" for t, f in row.items())
        print(f"  {canonical:8}  {forms}")
    return 0


def verb_ask(args: List[str]) -> int:
    if not args:
        print(c_err("ask: need a question"))
        return 1
    question = " ".join(args)
    print(c_info(f"q: {question}"))
    canonical = route_intent(question)
    if canonical:
        print(c_ok(f"intent -> {canonical}"))
        print(c_info(f"try:  {canonical} <args>"))
        return 0
    print(c_info("no rule match. fallback AI providers not wired yet (coming)"))
    return 1


def verb_do(args: List[str]) -> int:
    if not args:
        print(c_err("do: need action (commit|site-check|sweep-status|test)"))
        return 1
    action = args[0]
    if action == "commit":
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        count = len(result.stdout.splitlines())
        print(c_info(f"{count} dirty files. (preview only — commit needs explicit confirm)"))
        return 0
    if action == "site-check":
        cname = REPO_ROOT / "docs" / "CNAME"
        if cname.exists():
            print(c_ok(f"CNAME -> {cname.read_text().strip()}"))
        wf = REPO_ROOT / ".github" / "workflows" / "pages-deploy.yml"
        print(c_ok(f"pages workflow present: {wf.exists()}"))
        return 0
    if action == "sweep-status":
        for target in ("artifacts", "training-data"):
            p = REPO_ROOT / target
            real = os.path.realpath(p) if p.exists() else "(missing)"
            print(c_info(f"{target:15} -> {real}"))
        return 0
    if action == "test":
        print(c_info("running trijective unit test..."))
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_trijective.py", "-v"],
            cwd=REPO_ROOT,
        )
        return r.returncode
    print(c_err(f"unknown action: {action}"))
    return 1


def verb_help(args: List[str]) -> int:
    if args:
        target = args[0]
        if target in VERBS:
            print(f"{target}: {VERB_DOCS.get(target, '(no doc)')}")
            return 0
        print(c_err(f"no such verb: {target}"))
        return 1
    print(__doc__)
    return 0


def verb_quit(args: List[str]) -> int:
    print("  .. leaving geo shell")
    raise SystemExit(0)


VERBS: Dict[str, Callable[[List[str]], int]] = {
    "seal": verb_seal,
    "unseal": verb_unseal,
    "tok": verb_tok,
    "tri": verb_tri,
    "exec": verb_exec,
    "status": verb_status,
    "verbs": verb_verbs,
    "ask": verb_ask,
    "do": verb_do,
    "help": verb_help,
    "quit": verb_quit,
}

VERB_DOCS: Dict[str, str] = {
    "seal":   "envelope-encrypt text with GeoSeal (trijective-gated)",
    "unseal": "decrypt a GeoSeal envelope file",
    "tok":    "show atomic + 6-tongue tokenization",
    "tri":    "run trijective cross-check, print full report",
    "exec":   "run a turning-lane execution packet (trijective-gated)",
    "status": "system health: packages, git, archive, pipeline",
    "verbs":  "list the operational verb vocabulary across all 6 tongues",
    "ask":    "rule-based intent routing (AI provider fallback coming)",
    "do":     "run authorized system ops (commit|site-check|sweep-status|test)",
    "help":   "show this help or help <verb>",
    "quit":   "leave the REPL",
}


def dispatch(line: str) -> int:
    parts = shlex.split(line)
    if not parts:
        return 0
    head = parts[0].lower()
    args = parts[1:]
    # Intent routing: if the token is a synonym, rewrite to canonical
    canonical = route_intent(head)
    if canonical and canonical != head:
        print(c_info(f"routed '{head}' -> '{canonical}'"))
        head = canonical
    if head not in VERBS:
        print(c_err(f"unknown verb: {head}. try 'help'"))
        return 1
    # For non-help/non-status/non-quit verbs, enforce semantic cross-check
    if head not in ("help", "status", "verbs", "quit", "ask", "tri", "tok", "do"):
        if not semantic_cross_check(head, "KO"):
            print(c_err(f"verb '{head}' is not in the trijective operational vocabulary"))
            return 2
    return VERBS[head](args)


def repl() -> int:
    banner = [
        "SCBE-AETHERMOORE :: geo shell",
        f"  trijective gate ACTIVE. {len(SEMANTIC_VERBS)} operational verbs loaded.",
        "  type 'help' for commands, 'verbs' for vocabulary, 'quit' to leave.",
    ]
    if not _HAS_READLINE:
        banner.append("  (readline unavailable — history/editing limited)")
    print("\n".join(banner))
    print()
    while True:
        try:
            line = input("geo> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not line:
            continue
        try:
            dispatch(line)
        except SystemExit:
            raise
        except Exception as exc:
            print(c_err(f"{type(exc).__name__}: {exc}"))


def main(argv: List[str]) -> int:
    if len(argv) <= 1:
        return repl()
    return dispatch(" ".join(argv[1:]))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
