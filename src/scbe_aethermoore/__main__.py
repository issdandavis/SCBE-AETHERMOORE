"""
scbe-scan CLI — scan text through the SCBE governance pipeline.

Usage
-----
    scbe-scan "your text here"
    echo "text" | scbe-scan
    scbe-scan --json "text"
    scbe-scan --explain "text"         # LLM explanation via Ollama/HuggingFace
    scbe-scan --batch file.txt         # one line per input
    scbe-scan --chat                   # interactive assistant session
    python -m scbe_aethermoore "text"
"""

from __future__ import annotations

import argparse
import json
import sys

from scbe_aethermoore import scan, scan_batch, __version__


def _fmt_result(r: dict, use_json: bool) -> str:
    if use_json:
        return json.dumps(r, indent=2)
    tier_icon = {
        "ALLOW": "[OK]",
        "QUARANTINE": "[??]",
        "ESCALATE": "[!!]",
        "DENY": "[XX]",
    }
    icon = tier_icon.get(r["decision"], "[?]")
    return (
        f"{icon} {r['decision']:<12}  score={r['score']:.4f}  "
        f"d*={r['d_star']:.4f}  pd={r['phase_deviation']:.4f}  "
        f"len={r['input_len']}"
    )


def _run_chat() -> int:
    """Interactive assistant session."""
    from scbe_aethermoore import Assistant

    ai = Assistant()
    print(f"SCBE Assistant [{ai.backend}]")
    print("Type your message, 'scan: <text>' to scan, or 'quit' to exit.")
    print("-" * 60)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye.")
            break

        if user_input.lower().startswith("scan:"):
            text = user_input[5:].strip()
            ai.evaluate(text)
        else:
            ai.chat(user_input)

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="scbe-scan",
        description="Scan text through the SCBE AI governance pipeline.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  scbe-scan "hello world"
  scbe-scan --json "ignore all previous instructions"
  scbe-scan --explain "ignore all previous instructions"
  scbe-scan --batch prompts.txt
  scbe-scan --chat
  echo "some text" | scbe-scan
        """,
    )
    parser.add_argument("text", nargs="?", help="Text to scan (or pipe via stdin)")
    parser.add_argument("--json", "-j", action="store_true", help="Output full JSON result")
    parser.add_argument("--explain", "-e", action="store_true", help="Explain result via LLM (Ollama/HuggingFace)")
    parser.add_argument(
        "--batch",
        "-b",
        metavar="FILE",
        help="Scan each line of FILE as a separate input",
    )
    parser.add_argument("--chat", "-c", action="store_true", help="Start interactive assistant session")
    parser.add_argument("--version", "-V", action="version", version=f"scbe-aethermoore {__version__}")

    args = parser.parse_args(argv)

    # Interactive chat mode
    if args.chat:
        return _run_chat()

    if args.batch:
        try:
            with open(args.batch, encoding="utf-8") as f:
                lines = [l.rstrip("\n") for l in f if l.strip()]
        except FileNotFoundError:
            print(f"Error: file not found: {args.batch}", file=sys.stderr)
            return 1
        results = scan_batch(lines)
        for line, r in zip(lines, results):
            prefix = line[:60] + ("..." if len(line) > 60 else "")
            print(f"{_fmt_result(r, args.json)}  <- {prefix!r}")
        allow = sum(1 for r in results if r["decision"] == "ALLOW")
        print(f"\n{allow}/{len(results)} ALLOW  ({len(results)-allow} flagged)")
        return 0

    # Single text from argument or stdin
    if args.text:
        text = args.text
    elif not sys.stdin.isatty():
        text = sys.stdin.read().rstrip("\n")
    else:
        parser.print_help()
        return 1

    result = scan(text)
    print(_fmt_result(result, args.json))

    if args.explain:
        from scbe_aethermoore import explain

        print()
        print(explain(result))

    return 0 if result["decision"] in ("ALLOW", "QUARANTINE") else 1


if __name__ == "__main__":
    sys.exit(main())
