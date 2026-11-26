"""block_speech.py -- speech grounded in verified BINARY: the AI may only SAY what execution confirms
(Issac, 2026-07-18: "give it speech options that have values in binary that are functions related to
the context of messages, using python interpretation / my interpretability matrix -- extract simple
values from coding functions like 'this will fail' or 'this will pass' ... prime neural thoughts
cross-able to another number system that language rides along").

THE MOVE: a SPEECH BLOCK is a natural-language phrase bound to a binary predicate over a code RUN
(pass? fail? returns 0? positive? whole?). Given a function + its context (args), we run it and read the
predicates -- the TRUE ones are the only things the AI is allowed to say. So an utterance like "this
will pass" is not a hope; it is 1 iff the code actually passes. The full truth-vector of the blocks is
a BINARY FINGERPRINT of the code's behavior -- a number the language rides along (the 'prime neural
thought' as an integer, cross-able to any radix via the funnel).

CORPUS SPLIT (honest): the PHRASINGS ride on Issac's voice (pivot conversations / the new book / voice
corpus) -- swap the surface strings for his and the meaning is unchanged. The VALUE is always execution,
never the corpus. designed phrasing + verified value; the AI never says a block that ran false.
[[funnel]] [[model-proposes-verified-code]] [[honesty-firewall-in-code]] [[voice-corpus-is-the-asset]]
"""
from __future__ import annotations

from typing import Any


def run_code(fn, args) -> dict:
    """Run a coding function on its context (args) and read a simple result: value, or that it raised."""
    try:
        return {"value": fn(*args), "raised": False}
    except Exception as e:  # noqa: BLE001
        return {"value": None, "raised": True, "error": type(e).__name__}


def _num(r):
    return (not r["raised"]) and isinstance(r["value"], (int, float)) and not isinstance(r["value"], bool)


# each speech block: (phrase in Issac's-voice-slot, binary predicate over the run). Swap phrasings for
# his corpus; the predicate (the VALUE) stays execution-bound.
SPEECH_BLOCKS = [
    ("this will pass",          lambda r: not r["raised"]),
    ("this will fail",          lambda r: r["raised"]),
    ("it comes back empty",     lambda r: (not r["raised"]) and r["value"] is None),
    ("it lands on zero",        lambda r: _num(r) and r["value"] == 0),
    ("it comes out positive",   lambda r: _num(r) and r["value"] > 0),
    ("it comes out negative",   lambda r: _num(r) and r["value"] < 0),
    ("it holds a whole number", lambda r: _num(r) and float(r["value"]).is_integer()),
    ("it carries a remainder",  lambda r: _num(r) and not float(r["value"]).is_integer()),
    ("it says yes",             lambda r: (not r["raised"]) and r["value"] is True),
    ("it says no",              lambda r: (not r["raised"]) and r["value"] is False),
]

SPEECH_BLOCK_NAMES = (
    "PASS",
    "FAIL",
    "EMPTY",
    "ZERO",
    "POSITIVE",
    "NEGATIVE",
    "WHOLE",
    "REMAINDER",
    "YES",
    "NO",
)
SPEECH_BLOCK_OPCODE_BASE = 0xF0


def _balanced_trits(value: int, width: int = 3) -> tuple[int, ...]:
    """Return a fixed-width balanced-ternary address for a speech block."""

    out: list[int] = []
    carry = value
    for _ in range(width):
        digit = carry % 3
        carry //= 3
        if digit == 2:
            digit = -1
            carry += 1
        out.append(digit)
    return tuple(out)


def _applicable(index: int, result: dict[str, Any]) -> bool:
    """Distinguish a disproved predicate from one that does not apply."""

    if index in {0, 1}:
        return True
    if index == 2:
        return not result["raised"]
    if index in {3, 4, 5, 6, 7}:
        return _num(result)
    if index in {8, 9}:
        return (not result["raised"]) and isinstance(result["value"], bool)
    raise IndexError(index)


def speech_block_table() -> tuple[dict[str, Any], ...]:
    """Expose the immutable numeric speech vocabulary used by the action layer."""

    return tuple(
        {
            "token_id": index,
            "name": SPEECH_BLOCK_NAMES[index],
            "opcode": SPEECH_BLOCK_OPCODE_BASE + index,
            "opcode_bits": f"{SPEECH_BLOCK_OPCODE_BASE + index:08b}",
            "trit_address": list(_balanced_trits(index)),
            "phrase": phrase,
        }
        for index, (phrase, _) in enumerate(SPEECH_BLOCKS)
    )


def compile_observation(result: dict[str, Any]) -> dict[str, Any]:
    """Compile one observed result into binary and signed-trit speech blocks.

    The bit vector preserves the original truth fingerprint.  The trit vector
    adds the distinction the action layer needs: +1 asserted, -1 disproved,
    and 0 neutral/not-applicable.  Only asserted blocks are emitted as speech.
    """

    if "raised" not in result or "value" not in result:
        raise ValueError("speech observation requires raised and value fields")
    bits: list[int] = []
    trits: list[int] = []
    active_ids: list[int] = []
    phrases: list[str] = []
    for index, (phrase, predicate) in enumerate(SPEECH_BLOCKS):
        active = bool(predicate(result))
        applicable = _applicable(index, result)
        bits.append(int(active))
        trits.append(1 if active else (-1 if applicable else 0))
        if active:
            active_ids.append(index)
            phrases.append(phrase)
    bit_text = "".join(str(bit) for bit in bits)
    return {
        "schema": "clay.speech-block-program.v1",
        "width": len(bits),
        "bit_vector": bit_text,
        "trit_vector": trits,
        "fingerprint": int(bit_text, 2),
        "active_token_ids": active_ids,
        "active_opcodes": [SPEECH_BLOCK_OPCODE_BASE + index for index in active_ids],
        "blocks": phrases,
        "observed": dict(result),
    }


def speak(fn, args):
    """Run the code in its context; return (spoken, fingerprint): `spoken` = only the blocks that ran
    TRUE (what the AI may honestly say), `fingerprint` = the full block-truth bit-vector as one integer
    (the behavior as a number the language rides along)."""
    r = run_code(fn, args)
    program = compile_observation(r)
    return program["blocks"], program["fingerprint"], r


def _selftest() -> int:
    fails = []
    print("=== block speech: the AI may only SAY what execution confirms (binary, contextual) ===\n")

    cases = [
        ("div 10 by 2",   lambda a, b: a / b,          (10.0, 2.0)),   # 5.0  -> pass, positive, whole
        ("div 7 by 2",    lambda a, b: a / b,          (7.0, 2.0)),    # 3.5  -> pass, remainder
        ("div by zero",   lambda a, b: a / b,          (1.0, 0.0)),    # raises -> fail
        ("compare 3 < 4", lambda a, b: a < b,          (3, 4)),        # True -> says yes
        ("subtract",      lambda a, b: a - b,          (2.0, 9.0)),    # -7.0 -> negative, whole
    ]
    for name, fn, args in cases:
        spoken, fp, r = speak(fn, args)
        got = "raised" if r["raised"] else r["value"]
        print(f"  {name:16} -> ran={str(got):7}  fingerprint={fp:>4}  says: {', '.join(spoken)}")

    # VERIFY the speech is execution-true, not guessed.
    s_pass, _, _ = speak(lambda a, b: a / b, (10.0, 2.0))
    if "this will pass" not in s_pass or "it comes out positive" not in s_pass or "it holds a whole number" not in s_pass:
        fails.append("passing whole-positive case did not speak the true blocks")
    if "this will fail" in s_pass:
        fails.append("spoke 'this will fail' on code that PASSED (faked speech!)")

    s_fail, _, _ = speak(lambda a, b: a / b, (1.0, 0.0))
    if s_fail != ["this will fail"]:
        fails.append(f"div-by-zero should say only 'this will fail', got {s_fail}")

    s_rem, _, _ = speak(lambda a, b: a / b, (7.0, 2.0))
    if "it carries a remainder" not in s_rem or "it holds a whole number" in s_rem:
        fails.append("3.5 case mis-spoke whole/remainder")

    # the fingerprint is a deterministic behavior-number the language rides along
    fp1 = speak(lambda a, b: a / b, (10.0, 2.0))[1]
    fp2 = speak(lambda a, b: a / b, (10.0, 2.0))[1]
    fp3 = speak(lambda a, b: a / b, (1.0, 0.0))[1]
    if fp1 != fp2:
        fails.append("fingerprint not deterministic")
    if fp1 == fp3:
        fails.append("pass and fail produced the same fingerprint (no discrimination)")
    print(f"\n  behavior fingerprints: pass-whole-positive={fp1}, div-by-zero={fp3} "
          f"(distinct binary thoughts, {len(SPEECH_BLOCKS)} bits each)")

    print()
    if fails:
        print("  SELF-TEST: FAIL")
        for f in fails[:8]:
            print("   -", f)
        return 1
    print("  SELF-TEST: PASS  (every spoken block is 1 iff execution confirms it; a passing run never")
    print("                    says 'will fail'; the block-truth vector is a deterministic behavior")
    print("                    fingerprint (a number language rides along); phrasings swap for his voice.)")
    return 0


def main() -> int:
    try:
        import sys
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    return _selftest()


if __name__ == "__main__":
    raise SystemExit(main())
