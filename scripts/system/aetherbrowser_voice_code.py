#!/usr/bin/env python3
"""Aetherbrowser voice-code receipt tool.

This turns the repo's existing audio/coding experiments into one bounded tool
surface for Aetherbrowser and MCP:

* holophonor: note phrase -> CA ops -> code faces + execution receipt
* guitar: governed key/mode phrase -> Brainfuck-class Machine Crystal receipt
* proof: key-bijection and any-instrument coding proofs
* expressive: inflection-marked speech text -> SSML/prosody receipt + optional WAV

The tool writes full receipts to artifacts while returning a compact JSON summary
to callers, so MCP output stays readable.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT_DIR = ROOT / "artifacts" / "aetherbrowser_voice_code"

sys.path.insert(0, str(ROOT))

from python.scbe.expressive_tts import speak_expressive, strip_notation, to_ssml  # noqa: E402
from python.scbe.instrument_computer import (  # noqa: E402
    KEY_DIALECTS,
    holophonor_receipt,
    key_bijection_proof,
    legal_notes,
    prove_any_instrument,
    run_key_phrase,
)
from python.scbe.tts_backend import available as tts_available, speak as plain_speak  # noqa: E402


def utc_stamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip())[:80].strip("-")
    return slug or "voice-code"


def compact_preview(value: str, limit: int = 180) -> str:
    return " ".join(str(value or "").split())[:limit]


def parse_numeric_args(value: str) -> tuple[float, ...]:
    values: list[float] = []
    for part in re.split(r"[,\s]+", value.strip()):
        if not part:
            continue
        values.append(float(part))
    return tuple(values or (2.0, 3.0, 4.0))


def parse_notes(value: str) -> list[str]:
    notes = [part.strip() for part in re.split(r"[,\s]+", value.strip()) if part.strip()]
    if not notes:
        raise ValueError("No notes provided.")
    return notes


def normalize_song(value: str) -> str:
    return " ".join(parse_notes(value))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def build_output(
    *,
    ok: bool,
    action: str,
    out_dir: Path,
    receipt_path: Path | None,
    summary: dict[str, Any] | None = None,
    artifacts: dict[str, Any] | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "ok": ok,
        "schema_version": "aetherbrowser-voice-code-v1",
        "status": "VOICE_CODE_READY" if ok else "VOICE_CODE_FAILED",
        "action": action,
        "out_dir": str(out_dir),
        "receipt_path": str(receipt_path) if receipt_path else None,
        "summary": summary or {},
        "artifacts": artifacts or {},
        "error": error,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }


def inventory() -> dict[str, Any]:
    return {
        "schema": "aetherbrowser_voice_code_inventory_v1",
        "lanes": [
            {
                "name": "holophonor",
                "use": "Compile a played note phrase into SCBE CA ops, colors, melodies, code faces, and an execution value.",
                "example": 'voice-code --action holophonor --song "C E" --args 2,3,4',
            },
            {
                "name": "guitar",
                "use": "Compile in-key notes in a governed musical dialect into a Machine Crystal tape program.",
                "dialects": {
                    name: legal_notes(name)
                    for name in sorted(KEY_DIALECTS)
                },
                "example": 'voice-code --action guitar --dialect "E minor" --notes "E E G"',
            },
            {
                "name": "proof",
                "use": "Return key-bijection and any-instrument proofs that the voice/music layer maps down to executable code.",
                "example": "voice-code --action proof --proof all",
            },
            {
                "name": "expressive",
                "use": "Compile inflection-marked speech into SSML/prosody receipt and optional WAV.",
                "notation": {
                    "*word*": "emphasis",
                    "^word^": "pitch up",
                    "~word~": "pitch down",
                    "+word+": "louder",
                    "=word=": "softer",
                    "|": "short pause",
                    "||": "long pause",
                },
                "example": 'voice-code --action expressive --text "compile *the button* | ^then verify^" --speak',
            },
        ],
        "local_tts_engine": tts_available(),
        "honest_boundary": "Voice and instruments are coding alphabets and rendering surfaces; execution still happens in verified SCBE runtimes.",
    }


def run_holophonor(args: argparse.Namespace, out_dir: Path, base: str) -> tuple[dict[str, Any], dict[str, Any]]:
    song = normalize_song(args.song or args.notes or "C E")
    wav_path = out_dir / f"{base}.wav" if args.speak else None
    receipt = holophonor_receipt(
        song,
        mode=args.mode,
        args=parse_numeric_args(args.args),
        speak=args.speak,
        wav_path=wav_path,
    )
    summary = {
        "song": receipt["song"],
        "mode": receipt["mode"],
        "args": receipt["args"],
        "ops": receipt["ops"],
        "byte_codes": receipt["byte_codes"],
        "ca_words": receipt["ca_words"],
        "value": receipt["value"],
        "colors": receipt["colors"],
        "melody": receipt["melody"],
        "primary_face_count": receipt["primary_face_count"],
        "primary_faces": receipt["primary_faces"],
        "broad_face_count": receipt["broad_face_count"],
        "voice": receipt["voice"],
        "honest_boundary": receipt["honest_boundary"],
    }
    artifacts = {"wav_path": str(wav_path) if wav_path else None}
    return receipt, {"summary": summary, "artifacts": artifacts}


def run_guitar(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    notes = parse_notes(args.notes or args.song or "E E G")
    receipt = run_key_phrase(args.dialect, notes)
    machine_receipt = receipt.get("receipt", {})
    summary = {
        "dialect": receipt["dialect"],
        "legal_notes": receipt["legal_notes"],
        "notes": receipt["notes"],
        "brainfuck": receipt["brainfuck"],
        "steps": machine_receipt.get("steps"),
        "tape_window": machine_receipt.get("tape_window"),
        "output": machine_receipt.get("output"),
        "output_text": machine_receipt.get("output_text"),
    }
    return receipt, {"summary": summary, "artifacts": {}}


def run_proof(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    proof = (args.proof or "all").lower()
    if proof == "key":
        receipt = {"schema": "aetherbrowser_voice_code_proof_v1", "key_bijection": key_bijection_proof()}
    elif proof in {"instrument", "any-instrument", "any_instrument"}:
        receipt = {"schema": "aetherbrowser_voice_code_proof_v1", "any_instrument": prove_any_instrument()}
    elif proof == "all":
        receipt = {
            "schema": "aetherbrowser_voice_code_proof_v1",
            "key_bijection": key_bijection_proof(),
            "any_instrument": prove_any_instrument(),
        }
    else:
        raise ValueError("proof must be one of: key, instrument, all")
    summary = {
        "proof": proof,
        "key_bijection_verdict": receipt.get("key_bijection", {}).get("verdict"),
        "any_instrument_verdict": receipt.get("any_instrument", {}).get("verdict"),
        "same_result": receipt.get("key_bijection", {}).get("same_result"),
    }
    return receipt, {"summary": summary, "artifacts": {}}


def run_expressive(args: argparse.Namespace, out_dir: Path, base: str) -> tuple[dict[str, Any], dict[str, Any]]:
    marked = str(args.text or "").strip()
    if not marked:
        raise ValueError("expressive action requires --text")
    if len(marked) > 20_000:
        raise ValueError("text too long for one expressive voice-code call; limit is 20000 characters")

    plain = strip_notation(marked)
    ssml = to_ssml(marked)
    wav_path = out_dir / f"{base}.wav" if args.speak else None
    expressive_wav_path = out_dir / f"{base}.expressive.wav" if args.speak else None
    spoken_to_device = False
    expressive_rendered = False
    fallback_used = False
    expressive_error = None
    if args.speak:
        try:
            speak_expressive(marked, out_path=str(expressive_wav_path), rate=args.rate, voice=args.voice or None)
            expressive_rendered = True
            wav_path = expressive_wav_path
        except Exception as exc:
            expressive_error = f"{type(exc).__name__}: {exc}"
            plain_speak(plain, out_path=str(wav_path), rate=args.rate, voice=args.voice or None)
            fallback_used = True
    if args.speak_now:
        try:
            speak_expressive(marked, out_path=None, rate=args.rate, voice=args.voice or None)
            expressive_rendered = True
        except Exception as exc:
            expressive_error = expressive_error or f"{type(exc).__name__}: {exc}"
            plain_speak(plain, out_path=None, rate=args.rate, voice=args.voice or None)
            fallback_used = True
        spoken_to_device = True

    receipt = {
        "schema": "aetherbrowser_expressive_voice_code_v1",
        "text_sha256": hashlib.sha256(marked.encode("utf-8")).hexdigest(),
        "text_length": len(marked),
        "plain_text_length": len(plain),
        "plain_preview": compact_preview(plain),
        "ssml_preview": compact_preview(ssml),
        "rate": args.rate,
        "voice": args.voice or None,
        "wrote_wav": bool(wav_path),
        "spoken_to_device": spoken_to_device,
        "expressive_rendered": expressive_rendered,
        "plain_tts_fallback_used": fallback_used,
        "expressive_error": expressive_error,
        "wav_path": str(wav_path) if wav_path else None,
        "expressive_wav_path": str(expressive_wav_path) if expressive_wav_path else None,
        "wav_bytes": wav_path.stat().st_size if wav_path and wav_path.exists() else 0,
        "local_tts_engine": tts_available(),
        "notation": {
            "*word*": "emphasis",
            "^word^": "pitch up",
            "~word~": "pitch down",
            "+word+": "louder",
            "=word=": "softer",
            "|": "short pause",
            "||": "long pause",
        },
    }
    summary = dict(receipt)
    return receipt, {"summary": summary, "artifacts": {"wav_path": str(wav_path) if wav_path else None}}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compile voice/music coding surfaces into SCBE receipts.")
    parser.add_argument(
        "--action",
        choices=["inventory", "holophonor", "guitar", "proof", "expressive"],
        default="inventory",
        help="Voice-code lane to run.",
    )
    parser.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="Directory for voice-code artifacts.")
    parser.add_argument("--basename", default="", help="Optional safe artifact filename stem.")
    parser.add_argument("--song", default="", help='Note phrase, e.g. "C E" or "E,E,G".')
    parser.add_argument("--notes", default="", help='Mode phrase notes, e.g. "E E G" or "E,E,G".')
    parser.add_argument("--mode", default="coding", help="Holophonor mode.")
    parser.add_argument("--dialect", default="E minor", help='Guitar/key dialect, e.g. "E minor".')
    parser.add_argument("--args", default="2,3,4", help="Holophonor numeric args, comma or space separated.")
    parser.add_argument("--proof", default="all", help="Proof kind: key, instrument, or all.")
    parser.add_argument("--text", default="", help="Expressive voice-code text.")
    parser.add_argument("--voice", default="", help="Optional local voice name substring.")
    parser.add_argument("--rate", type=int, default=None, help="Speech rate, usually -10 to 10 for SAPI.")
    parser.add_argument("--speak", action="store_true", help="Write a WAV when the selected lane supports speech.")
    parser.add_argument("--speak-now", action="store_true", help="Also speak through the default audio device.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    base_seed = args.basename or f"{args.action}-{utc_stamp()}"
    base = safe_slug(base_seed)
    receipt_path = out_dir / f"{base}.json"

    try:
        if args.action == "inventory":
            receipt = inventory()
            result_bits = {"summary": receipt, "artifacts": {}}
        elif args.action == "holophonor":
            receipt, result_bits = run_holophonor(args, out_dir, base)
        elif args.action == "guitar":
            receipt, result_bits = run_guitar(args)
        elif args.action == "proof":
            receipt, result_bits = run_proof(args)
        elif args.action == "expressive":
            receipt, result_bits = run_expressive(args, out_dir, base)
        else:
            raise ValueError(f"unknown action: {args.action}")

        write_json(receipt_path, receipt)
        output = build_output(
            ok=True,
            action=args.action,
            out_dir=out_dir,
            receipt_path=receipt_path,
            summary=result_bits["summary"],
            artifacts=result_bits["artifacts"],
        )
        write_json(out_dir / "last_voice_code.json", output)
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        output = build_output(
            ok=False,
            action=args.action,
            out_dir=out_dir,
            receipt_path=None,
            error=f"{type(exc).__name__}: {exc}",
        )
        write_json(out_dir / "last_voice_code.json", output)
        print(json.dumps(output, indent=2, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
