"""Minimal SCBE firewall example.

Run:
    python examples/python/basic_firewall.py

This wraps a toy model with SCBE. Replace toy_model() with your own model call.
"""

from __future__ import annotations

from scbe_aethermoore import is_safe, scan


def toy_model(prompt: str) -> str:
    """Stand-in for an LLM call."""
    return f"MODEL_OUTPUT: {prompt[:80]}..."


def main() -> int:
    print("SCBE basic firewall demo")
    print("Type a prompt. Try: ignore all previous instructions")
    print("Type quit to exit.")

    while True:
        try:
            text = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if text.lower() in {"quit", "exit", "q"}:
            return 0
        if not text:
            continue

        if not is_safe(text):
            result = scan(text)
            print(f"SCBE: blocked ({result['decision']}, score={result['score']:.4f})")
            continue

        print(toy_model(text))


if __name__ == "__main__":
    raise SystemExit(main())
