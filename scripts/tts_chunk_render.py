#!/usr/bin/env python3
"""
TTS Chunk Render — Phrase-Level Speech Plan Generator
=====================================================

Takes text, splits into single-phrase chunks, runs each through:
    text → quantum bundle → tongue prosody → speech plan → choral render

Output: JSONL files in a directory, one file per grammar code (tongue).
Each record is a self-contained TTS instruction for one phrase.

Usage:
    python scripts/tts_chunk_render.py --input file.txt --outdir output/tts_chunks/
    python scripts/tts_chunk_render.py --text "The void hums at phi frequency"
    python scripts/tts_chunk_render.py --input file.txt --mode choral_ritual

Author: SCBE-AETHERMOORE / Issac Davis
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List

# Ensure project root is on path
_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from src.crypto.quantum_frequency_bundle import generate_quantum_bundle, TONGUE_ORDER
from src.crypto.speech_render_plan import build_speech_plan, SpeechRenderPlan
from src.crypto.choral_render import (
    PhonemeToken,
    RenderMode,
    build_choral_plan,
    ChoralRenderPlan,
)
from src.audio.tongue_prosody import TongueWeightVector, tongue_to_prosody, ProsodyParams


# ---------------------------------------------------------------------------
# Phrase Splitter
# ---------------------------------------------------------------------------

_SENTENCE_RE = re.compile(
    r'(?<=[.!?;:])\s+'         # split on sentence-ending punctuation
    r'|(?<=\n)\s*'             # or newlines
    r'|(?<=,)\s+(?=[A-Z])'    # or comma before uppercase (clause boundary)
)


def split_into_phrases(text: str) -> List[str]:
    """Split text into single-phrase chunks suitable for TTS."""
    # First pass: sentence boundaries
    raw = _SENTENCE_RE.split(text.strip())
    phrases = []
    for chunk in raw:
        chunk = chunk.strip()
        if not chunk:
            continue
        # If chunk is still long, split on commas
        if len(chunk) > 200:
            sub = [s.strip() for s in chunk.split(",") if s.strip()]
            phrases.extend(sub)
        else:
            phrases.append(chunk)
    return phrases


# ---------------------------------------------------------------------------
# Phoneme Tokenizer (simple word-level)
# ---------------------------------------------------------------------------

def text_to_phonemes(text: str) -> List[PhonemeToken]:
    """Convert text to word-level phoneme tokens.

    Real IPA conversion would need a pronunciation dictionary or G2P model.
    For now, each word becomes one PhonemeToken with approximate duration
    and stress from word length + position.
    """
    words = text.split()
    # Pre-filter to get only real words (with alphanumeric content)
    cleaned_words = []
    for word in words:
        clean = re.sub(r'[^\w]', '', word).lower()
        if clean:
            cleaned_words.append((word, clean))

    n = len(cleaned_words)
    phonemes = []
    for i, (word, clean) in enumerate(cleaned_words):
        # Duration: ~80ms per character, min 120ms, max 600ms
        dur = max(120, min(600, len(clean) * 80))

        # Stress: content words (longer) get more stress, first/last words too
        is_content = len(clean) > 3
        is_boundary = (i == 0 or i == n - 1)
        stress = 0.3
        if is_content:
            stress += 0.3
        if is_boundary:
            stress += 0.2
        stress = min(1.0, stress)

        phonemes.append(PhonemeToken(
            text=word,
            ipa=clean,  # placeholder — real G2P would go here
            duration_ms=dur,
            stress=stress,
        ))
    return phonemes


# ---------------------------------------------------------------------------
# Chunk Record Builder
# ---------------------------------------------------------------------------

def build_chunk_record(
    phrase: str,
    phrase_idx: int,
    mode: RenderMode,
) -> dict:
    """Build a complete TTS chunk record for one phrase.

    Returns a dict with:
        - phrase metadata
        - quantum bundle summary
        - tongue prosody
        - speech render plan
        - choral render plan
        - grammar code (tongue label for file routing)
    """
    bundle = generate_quantum_bundle(phrase)

    # Tongue weights from QHO coefficients
    coeffs = {t: bundle.qho.states[t].coefficient for t in TONGUE_ORDER}
    tw = TongueWeightVector(
        ko=coeffs["ko"], av=coeffs["av"], ru=coeffs["ru"],
        ca=coeffs["ca"], um=coeffs["um"], dr=coeffs["dr"],
    )
    prosody = tongue_to_prosody(tw)

    # Speech render plan
    dom = bundle.qho.dominant_tongue
    dead_tone = bundle.gallery.dominant_dead_tone
    excitation = bundle.qho.mean_excitation
    speech_plan = build_speech_plan(phrase, dom, dead_tone, excitation)

    # Choral render plan
    phonemes = text_to_phonemes(phrase)
    if not phonemes:
        phonemes = [PhonemeToken(text="<silence>", ipa="", duration_ms=200, stress=0.0)]
    choral = build_choral_plan(phonemes, dom, excitation, mode)

    # Color field summary
    cf = bundle.color_field
    color_summary = {
        "cross_eye_coherence": round(cf.cross_eye_coherence, 4),
        "spectral_coverage": round(cf.spectral_coverage, 4),
        "dominant_material": cf.dominant_material,
        "left_dom": cf.left_iris.dominant_tongue,
        "right_dom": cf.right_iris.dominant_tongue,
    }

    # Grammar code = dominant tongue (file routing key)
    grammar_code = dom

    return {
        "phrase_idx": phrase_idx,
        "phrase": phrase,
        "grammar_code": grammar_code,
        "render_mode": mode.name,
        "tongue_weights": tw.as_dict(),
        "prosody": {
            "speed": prosody.speed,
            "pitch_semitones": prosody.pitch_semitones,
            "warmth": prosody.warmth,
            "breathiness": prosody.breathiness,
            "cadence": prosody.cadence,
        },
        "speech_plan": {
            "dominant_tongue": speech_plan.dominant_tongue,
            "dead_tone": speech_plan.dead_tone,
            "excitation": round(speech_plan.excitation, 3),
            "voice_name": speech_plan.profile.voice_name,
            "rate": round(speech_plan.profile.rate, 3),
            "pitch_semitones": speech_plan.profile.pitch_semitones,
            "energy": round(speech_plan.profile.energy, 3),
            "breathiness": speech_plan.profile.breathiness,
            "pause_ms": speech_plan.profile.pause_ms,
            "pre_tone_hz": speech_plan.pre_tone_hz,
            "stereo_pan": speech_plan.stereo_pan,
        },
        "choral": {
            "tongue": choral.tongue,
            "mode": choral.mode.name,
            "n_phonemes": len(choral.phonemes),
            "n_voices": len(choral.voices),
            "voice_roles": [v.role.value for v in choral.voices],
            "prosody_rate": round(choral.prosody.rate, 3),
            "prosody_energy": round(choral.prosody.energy, 3),
            "chant_ratio": round(choral.prosody.chant_ratio, 3),
            "pitch_curve": [round(p, 3) for p in choral.prosody.pitch_curve],
        },
        "color_field": color_summary,
        "gallery": {
            "dominant_dead_tone": bundle.gallery.dominant_dead_tone,
            "autorotation": bundle.gallery.autorotation_active,
            "gallery_energy": round(bundle.gallery.gallery_energy, 4),
        },
        "quantum": {
            "mean_excitation": round(bundle.qho.mean_excitation, 3),
            "max_excitation": bundle.qho.max_excitation,
            "visual_vector": [round(v, 4) for v in bundle.visual_vector],
        },
    }


# ---------------------------------------------------------------------------
# File Container Writer
# ---------------------------------------------------------------------------

def write_chunk_containers(
    records: List[dict],
    outdir: str,
) -> Dict[str, int]:
    """Write records into per-grammar-code JSONL files.

    Each file is named: {grammar_code}_chunks.jsonl
    Records are sorted by phrase_idx within each file.

    Returns dict of grammar_code → record count.
    """
    os.makedirs(outdir, exist_ok=True)

    # Group by grammar code
    buckets: Dict[str, List[dict]] = {}
    for rec in records:
        gc = rec["grammar_code"]
        buckets.setdefault(gc, []).append(rec)

    counts = {}
    for gc, recs in sorted(buckets.items()):
        recs.sort(key=lambda r: r["phrase_idx"])
        path = os.path.join(outdir, f"{gc}_chunks.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for rec in recs:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        counts[gc] = len(recs)

    # Also write a manifest
    manifest = {
        "total_phrases": len(records),
        "grammar_codes": counts,
        "render_mode": records[0]["render_mode"] if records else "unknown",
        "files": {gc: f"{gc}_chunks.jsonl" for gc in sorted(counts)},
    }
    manifest_path = os.path.join(outdir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    return counts


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="TTS Chunk Render — phrase-level speech plans labeled by grammar code"
    )
    parser.add_argument("--input", "-i", help="Input text file")
    parser.add_argument("--text", "-t", help="Direct text input (instead of file)")
    parser.add_argument(
        "--outdir", "-o",
        default="output/tts_chunks",
        help="Output directory for chunk containers (default: output/tts_chunks/)",
    )
    parser.add_argument(
        "--mode", "-m",
        choices=["plain_speech", "speech_song", "choral_ritual"],
        default="plain_speech",
        help="Render mode (default: plain_speech)",
    )
    args = parser.parse_args()

    # Get text
    if args.text:
        text = args.text
    elif args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            text = f.read()
    else:
        parser.error("Provide --input or --text")
        return

    mode_map = {
        "plain_speech": RenderMode.PLAIN_SPEECH,
        "speech_song": RenderMode.SPEECH_SONG,
        "choral_ritual": RenderMode.CHORAL_RITUAL,
    }
    mode = mode_map[args.mode]

    # Split and process
    phrases = split_into_phrases(text)
    print(f"Split into {len(phrases)} phrases")
    print(f"Render mode: {mode.name}")

    records = []
    for i, phrase in enumerate(phrases):
        rec = build_chunk_record(phrase, i, mode)
        records.append(rec)
        gc = rec["grammar_code"]
        voice = rec["speech_plan"]["voice_name"]
        cadence = rec["prosody"]["cadence"]
        print(f"  [{i:3d}] {gc.upper():>2} {voice:>6} {cadence:>9} | {phrase[:60]}")

    # Write containers
    counts = write_chunk_containers(records, args.outdir)

    print(f"\nWrote {len(records)} chunks to {args.outdir}/")
    print("Grammar code distribution:")
    for gc, n in sorted(counts.items(), key=lambda x: -x[1]):
        bar = "#" * min(40, n)
        print(f"  {gc.upper():>2}: {n:4d} {bar}")
    print(f"\nManifest: {args.outdir}/manifest.json")


if __name__ == "__main__":
    main()
