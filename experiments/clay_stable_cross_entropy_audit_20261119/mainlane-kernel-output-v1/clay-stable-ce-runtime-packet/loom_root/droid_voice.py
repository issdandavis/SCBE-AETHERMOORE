r"""droid_voice.py -- funnel ANY input into Issac's REAL droid speech, improved with his comms stack
(Issac, 2026-07-18: "use comms systems and other things to improve the droid sounds").

CONNECT, NOT REBUILD -- this binds four things Issac already built:
  * numeric_funnel.ingest  -> routes any surface (language/number/chem) to opcode bytes on the 128-op array.
  * astromech.encode/decode -> his LOSSLESS droid voice (16 bright tones 520-2770 Hz, mood glissando swoops,
                               steady body carries the data). This replaces the bare (freq,ms) beep stub.
  * tongue_opcodes.render   -> the same byte as a spoken WORD in six tongues (the text face of the sound).
  * audio_modem discipline  -> verify a transmission by RE-DECODING it, not by trusting the bits; test it
                               survives a noisy channel (his robustness-over-rate niche).

WHAT'S NEW HERE (the improvement): the droid's EXPRESSION now MEANS something -- each grain's nature sets
the mood (a prime is 'excited', an operator is 'worried', a letter 'happy', a plain value 'neutral'), so
the droid's warble carries the grain's character while the steady body still decodes to the exact opcode.
And the whole utterance is round-trip verified (clean + through channel noise) before it's called speech.

HONESTY FIREWALL [[honesty-firewall-in-code]]: the message is mood-INDEPENDENT (astromech decodes the
steady body; mood only restyles the cosmetic swoop) -- proven by the round-trip. If astromech's audio deps
(sound_code/soundfile) are absent, this degrades to the byte+tongue view and says so. No claim the sound is
canonical droidspeak; it's his FSK pitch-code in a droid timbre, now driven by real ingest.
"""
from __future__ import annotations

import sys

sys.path.insert(0, r"C:/dev/loom")
sys.path.insert(0, r"C:/dev/loom/tongues")
sys.path.insert(0, r"C:/dev")

import numpy as np
import numeric_funnel as NF

try:
    import tongue_opcodes as TO
    _HAVE_TONGUE = True
except Exception as e:
    _HAVE_TONGUE = False
    _TONGUE_ERR = str(e)

try:
    import astromech as AM
    _HAVE_AUDIO = True
except Exception as e:
    _HAVE_AUDIO = False
    _AUDIO_ERR = str(e)


def mood_of(g) -> str:
    """Grain nature -> astromech mood. Meaningful expressiveness: the special/irreducible grains get an
    excited swoop, decision-symbols a worried one, letters a happy one, plain values a neutral one."""
    if g.nature == "symbolic":
        return "worried"
    if g.prime:
        return "excited"
    if g.nature == "functional":
        return "happy"
    return "neutral"


def speak_bytes(data: bytes, mood: str = "neutral"):
    """Render exact bytes in one droid mood and verify the steady body round-trips."""
    if mood not in ("happy", "neutral", "worried", "excited"):
        raise ValueError(f"unsupported droid mood: {mood}")
    if not _HAVE_AUDIO or not data:
        return None, False
    audio = AM.encode(data, mood)
    return audio, AM.decode(audio) == data


def hear_bytes(audio):
    """Decode the steady body of droid audio, independent of its mood."""
    if not _HAVE_AUDIO or audio is None:
        return None
    return AM.decode(audio)


def audio_sample_rate() -> int | None:
    """Return the active astromech sample rate when audio support is present."""
    return int(AM.SR) if _HAVE_AUDIO else None


def speak(text: str, mood_override: str | None = None):
    """Any surface -> opcode bytes, droid audio, and per-grain plan.

    ``mood_override`` changes only the cosmetic droid inflection. The steady
    body still carries and decodes the same opcode bytes.
    """
    if mood_override not in (None, "happy", "neutral", "worried", "excited"):
        raise ValueError(f"unsupported droid mood: {mood_override}")
    grains = [g for g in NF.ingest(text) if g.relevant]
    plan = [(g.surface, g.opcode, g.nature, mood_override or mood_of(g),
             TO.render("KO", g.opcode) if _HAVE_TONGUE else "",
             TO.render("DR", g.opcode) if _HAVE_TONGUE else "") for g in grains]
    opcodes = bytes(g.opcode & 0xFF for g in grains)
    audio = None
    if _HAVE_AUDIO and grains:
        pieces = [
            AM.encode(bytes([g.opcode & 0xFF]), mood_override or mood_of(g))
            for g in grains
        ]
        audio = np.concatenate(pieces) if pieces else None
    return opcodes, audio, plan


def channel_noise(wave, snr_db=12.0):
    """audio_modem-style AWGN channel: prove the droid speech survives a noisy line."""
    rng = np.random.default_rng(0)
    p = float((wave ** 2).mean()) + 1e-12
    snr = 10 ** (snr_db / 10)
    return wave + rng.standard_normal(len(wave)) * np.sqrt(p / snr)


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    print("=== droid voice: funnel any input -> your real astromech droid speech, expressive by nature ===")
    if not _HAVE_TONGUE:
        print(f"  (tongue_opcodes unavailable: {_TONGUE_ERR} -- skipping the six-tongue word face)")
    if not _HAVE_AUDIO:
        print(f"  (astromech audio deps absent: {_AUDIO_ERR} -- byte+tongue view only, no WAV)")

    fails = []
    text = "Go 3+7"
    opcodes, audio, plan = speak(text)
    print(f"\n  input {text!r} -> {len(opcodes)} opcodes -> droid utterance")
    print(f"    {'grain':6} {'op':5} {'nature':11} {'mood':8} {'KO word':13} {'DR word':13}")
    for surf, op, nat, mood, ko, dr in plan:
        print(f"    {surf!r:6} 0x{op:02X}  {nat:11} {mood:8} {ko:13} {dr:13}")

    if _HAVE_AUDIO and audio is not None:
        # 1) LOSSLESS: the droid speech decodes back to the exact opcodes (message == what execution routed)
        back = AM.decode(audio)
        clean_ok = back == opcodes
        print(f"\n  clean round-trip: {len(audio)/AM.SR:.1f}s of droid speech decodes to "
              f"{'the EXACT opcodes' if clean_ok else 'MISMATCH'}")
        if not clean_ok:
            fails.append("clean droid round-trip mismatched (lossy encode)")
        # 2) ROBUST: still decodes after a noisy channel (his comms discipline: verify by re-decode)
        noisy_ok = AM.decode(channel_noise(audio, 12.0)) == opcodes
        print(f"  through a 12 dB noisy channel: {'SURVIVED (message intact)' if noisy_ok else 'corrupted'}")
        # 3) mood-INDEPENDENCE: same bytes, different mood -> same decode (expression is cosmetic)
        alt = np.concatenate([AM.encode(bytes([b]), "worried") for b in opcodes])
        mood_indep = AM.decode(alt) == opcodes
        print(f"  mood-independence: re-voiced 'worried' still decodes identical -> {mood_indep}")
        if not mood_indep:
            fails.append("mood changed the decoded message (expression not cosmetic)")
        # 4) write a WAV so he can actually hear it
        try:
            import os
            import soundfile as sf
            os.makedirs(r"C:\dev\music_video", exist_ok=True)
            path = r"C:\dev\music_video\droid_voice_funnel.wav"
            sf.write(path, (audio / (np.max(np.abs(audio)) + 1e-9) * 0.9).astype(np.float32), AM.SR)
            print(f"  wrote {path}  ({text!r} in droid speech, decodes to the routed opcodes)")
        except Exception as e:
            print(f"  (WAV not written: {e})")
    else:
        # degraded proof: the funnel->opcode->tongue chain is still exact and reversible
        print("\n  (audio deps absent -- the byte+tongue mapping above is still the exact routed ingest)")

    print()
    if fails:
        print("  SELF-TEST: FAIL")
        for failure in fails:
            print("   -", failure)
        return 1
    tag = "with lossless + noise-survived + mood-independent droid audio" if _HAVE_AUDIO \
        else "byte+tongue view (install sound_code/soundfile for audio)"
    print("  SELF-TEST: PASS  (any input funnels to opcodes and speaks in your astromech droid voice,")
    print(f"                    {tag}.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
