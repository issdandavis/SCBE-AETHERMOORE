"""
Voice Clone Test Pipeline
==========================

Tests voice cloning approaches using Issac's voice recordings.

Strategy:
  1. Convert M4A reference audio to WAV
  2. Use Kokoro ONNX as baseline TTS (pre-built voice)
  3. Attempt HuggingFace Inference API for XTTS voice cloning
  4. Compare outputs
  5. Generate test chapter audio

Voice files:
  - C:/Users/issda/OneDrive/Downloads/My voice.m4a (25s)
  - C:/Users/issda/OneDrive/Downloads/Voice 260314_204021.m4a (95s)

Run:
  python scripts/voice_clone_test.py
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOME = Path("C:/Users/issda")
VOICE_DIR = ROOT / "artifacts" / "voice_clone"
VOICE_DIR.mkdir(parents=True, exist_ok=True)


def load_hf_token() -> str:
    env_path = ROOT / "config" / "connector_oauth" / ".env.connector.oauth"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            if "HF_TOKEN=" in line or "HUGGINGFACE_TOKEN=" in line:
                token = line.split("=", 1)[1].strip().strip('"')
                if token:
                    return token
    return os.environ.get("HF_TOKEN", "")


def convert_m4a_to_wav(m4a_path: Path, wav_path: Path) -> bool:
    """Convert M4A to WAV using ffmpeg."""
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(m4a_path), "-acodec", "pcm_s16le", "-ar", "24000", "-ac", "1", str(wav_path)],
            capture_output=True,
            check=True,
        )
        return True
    except Exception as e:
        print(f"  FFmpeg error: {e}")
        return False


def generate_kokoro_baseline(text: str, output_path: Path) -> bool:
    """Generate baseline audio using Kokoro ONNX (am_adam voice)."""
    try:
        import kokoro_onnx
        import soundfile as sf
        import numpy as np

        kokoro = kokoro_onnx.Kokoro(
            str(HOME / "kokoro-v1.0.onnx"),
            str(HOME / "voices-v1.0.bin"),
        )

        samples, sample_rate = kokoro.create(
            text,
            voice="am_adam",
            speed=0.92,
        )

        sf.write(str(output_path), samples, sample_rate)
        return True
    except Exception as e:
        print(f"  Kokoro error: {e}")
        return False


def analyze_voice(wav_path: Path) -> dict:
    """Basic voice analysis using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-show_entries",
                "format=duration,size,bit_rate",
                "-show_entries",
                "stream=codec_name,sample_rate,channels",
                "-of",
                "json",
                str(wav_path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)
        return {
            "duration": float(data.get("format", {}).get("duration", 0)),
            "sample_rate": data.get("streams", [{}])[0].get("sample_rate", ""),
            "channels": data.get("streams", [{}])[0].get("channels", 0),
            "size_kb": round(int(data.get("format", {}).get("size", 0)) / 1024),
        }
    except Exception:
        return {}


def attempt_hf_voice_clone(reference_wav: Path, text: str, output_path: Path, hf_token: str) -> bool:
    """Attempt voice cloning via HuggingFace Inference API (XTTS)."""
    try:
        import requests

        # Try coqui/XTTS-v2 endpoint
        api_url = "https://api-inference.huggingface.co/models/coqui/XTTS-v2"
        headers = {"Authorization": f"Bearer {hf_token}"}

        # Read reference audio
        with open(reference_wav, "rb") as f:
            audio_bytes = f.read()

        # XTTS expects multipart with audio reference
        response = requests.post(
            api_url,
            headers=headers,
            json={
                "inputs": text,
                "parameters": {
                    "language": "en",
                },
            },
            timeout=120,
        )

        if response.status_code == 200:
            output_path.write_bytes(response.content)
            return True
        else:
            print(f"  HF API response: {response.status_code} - {response.text[:200]}")
            return False
    except Exception as e:
        print(f"  HF voice clone error: {e}")
        return False


def get_test_text() -> str:
    """Get a passage from Six Tongues Protocol Chapter 1."""
    ch1 = HOME / "OneDrive" / "Books" / "The Six Tongues Protocol" / "ch01.md"
    if ch1.exists():
        text = ch1.read_text(encoding="utf-8")
        # Get first meaningful paragraph (skip markdown headers)
        paragraphs = [
            p.strip()
            for p in text.split("\n\n")
            if p.strip() and not p.strip().startswith("#") and len(p.strip()) > 100
        ]
        if paragraphs:
            return paragraphs[0][:500]
    return (
        "The Six Tongues Protocol was not a language you spoke. "
        "It was a language that spoke you. Marcus Chen learned this "
        "the hard way, standing at the edge of the Resonance Chamber "
        "with nothing but a borrowed key and a raven who wouldn't stop talking."
    )


def main():
    print("=" * 60)
    print("VOICE CLONE TEST PIPELINE")
    print("=" * 60)

    hf_token = load_hf_token()
    test_text = get_test_text()
    print(f"\nTest text ({len(test_text)} chars):")
    print(f'  "{test_text[:150]}..."')

    # ============================================================
    # STEP 1: Convert reference audio
    # ============================================================
    print("\n[1/5] Converting reference audio M4A -> WAV...")
    voice_files = [
        (HOME / "OneDrive" / "Downloads" / "My voice.m4a", "my_voice.wav"),
        (HOME / "OneDrive" / "Downloads" / "Voice 260314_204021.m4a", "voice_long.wav"),
    ]

    ref_wavs = []
    for m4a, wav_name in voice_files:
        if m4a.exists():
            wav_path = VOICE_DIR / wav_name
            ok = convert_m4a_to_wav(m4a, wav_path)
            if ok:
                info = analyze_voice(wav_path)
                print(
                    f"  {wav_name}: {info.get('duration', 0):.1f}s, "
                    f"{info.get('sample_rate', '?')}Hz, {info.get('size_kb', 0)}KB"
                )
                ref_wavs.append(wav_path)
            else:
                print(f"  FAILED: {m4a.name}")
        else:
            print(f"  SKIP: {m4a.name} not found")

    # Combine both voice files into one reference
    if len(ref_wavs) == 2:
        combined = VOICE_DIR / "combined_reference.wav"
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(ref_wavs[0]),
                    "-i",
                    str(ref_wavs[1]),
                    "-filter_complex",
                    "[0:a][1:a]concat=n=2:v=0:a=1",
                    "-acodec",
                    "pcm_s16le",
                    "-ar",
                    "24000",
                    "-ac",
                    "1",
                    str(combined),
                ],
                capture_output=True,
                check=True,
            )
            info = analyze_voice(combined)
            print(f"  combined_reference.wav: {info.get('duration', 0):.1f}s total")
            ref_wavs.append(combined)
        except Exception as e:
            print(f"  Combine error: {e}")

    # ============================================================
    # STEP 2: Generate Kokoro baseline
    # ============================================================
    print("\n[2/5] Generating Kokoro baseline (am_adam voice)...")
    kokoro_out = VOICE_DIR / "kokoro_baseline.wav"
    t0 = time.time()
    ok = generate_kokoro_baseline(test_text, kokoro_out)
    if ok:
        info = analyze_voice(kokoro_out)
        print(
            f"  kokoro_baseline.wav: {info.get('duration', 0):.1f}s, "
            f"{info.get('size_kb', 0)}KB ({time.time()-t0:.1f}s)"
        )
    else:
        print("  FAILED — Kokoro model files may not be present")

    # ============================================================
    # STEP 3: Attempt HF voice clone
    # ============================================================
    print("\n[3/5] Attempting HuggingFace XTTS voice clone...")
    if hf_token and ref_wavs:
        hf_out = VOICE_DIR / "hf_voice_clone.wav"
        t0 = time.time()
        ok = attempt_hf_voice_clone(ref_wavs[0], test_text, hf_out, hf_token)
        if ok:
            info = analyze_voice(hf_out)
            print(f"  hf_voice_clone.wav: {info.get('duration', 0):.1f}s ({time.time()-t0:.1f}s)")
        else:
            print("  XTTS API not available — will need local setup or ElevenLabs")
    else:
        print("  SKIP — no HF token or reference audio")

    # ============================================================
    # STEP 4: Voice analysis comparison
    # ============================================================
    print("\n[4/5] Voice analysis...")
    for wav in ref_wavs + [kokoro_out]:
        if wav.exists():
            info = analyze_voice(wav)
            print(
                f"  {wav.name}: dur={info.get('duration', 0):.1f}s "
                f"rate={info.get('sample_rate', '?')}Hz "
                f"size={info.get('size_kb', 0)}KB"
            )

    # ============================================================
    # STEP 5: Summary & next steps
    # ============================================================
    print("\n[5/5] Summary...")
    print(f"\n  Reference audio available:")
    for w in ref_wavs:
        info = analyze_voice(w)
        print(f"    {w.name} — {info.get('duration', 0):.1f}s")

    total_ref = sum(analyze_voice(w).get("duration", 0) for w in ref_wavs[:2])
    print(f"\n  Total reference: {total_ref:.0f}s ({total_ref/60:.1f} minutes)")

    print(f"\n  Output files in: {VOICE_DIR}")
    for f in sorted(VOICE_DIR.glob("*.wav")):
        info = analyze_voice(f)
        print(f"    {f.name}: {info.get('duration', 0):.1f}s, {info.get('size_kb', 0)}KB")

    print(f"\n  RECOMMENDATIONS:")
    if total_ref >= 120:
        print(f"    You have {total_ref:.0f}s — enough for F5-TTS and XTTS basic clone")
    if total_ref < 360:
        print(f"    Record {max(0, 360-total_ref):.0f}s more for best XTTS quality")
    print(f"    ElevenLabs Instant clone works NOW with your {total_ref:.0f}s")
    print(f"    For audiobook chapters, use the combined_reference.wav as the voice seed")

    print(f"\n{'='*60}")
    print(f"VOICE CLONE TEST COMPLETE")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
