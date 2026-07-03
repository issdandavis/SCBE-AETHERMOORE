"""Regression tests for the shape->chord->audio benchmark pipeline."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys
import wave


SCRIPT_DIR = Path(__file__).resolve().parents[2] / "scripts" / "audio"
SHAPE_MODULES = [
    "shape_music",
    "shape_audio",
    "shape_manifest",
    "shape_dataset",
    "shape_listen",
    "shape_hard",
]


def _fresh_modules(monkeypatch, tmp_path, *, clips: int = 28):
    monkeypatch.syspath_prepend(str(SCRIPT_DIR))
    monkeypatch.setenv("SCBE_SHAPE_CHORD_WAV_DIR", str(tmp_path / "wav"))
    monkeypatch.setenv("SCBE_SHAPE_DATASET_DIR", str(tmp_path / "dataset"))
    monkeypatch.setenv("SCBE_SHAPE_DATASET_CLIPS", str(clips))
    monkeypatch.setenv("SCBE_SHAPE_LISTEN_CLIPS", str(clips))
    monkeypatch.setenv("SCBE_SHAPE_HARD_CLIPS", str(clips))
    for name in SHAPE_MODULES:
        sys.modules.pop(name, None)
    return {name: importlib.import_module(name) for name in SHAPE_MODULES}


def test_shape_music_core_geometry_cases(monkeypatch, tmp_path):
    mods = _fresh_modules(monkeypatch, tmp_path)
    sm = mods["shape_music"]

    assert sm.polygon_voice_chord(3) == [0, 4, 8]
    assert sm.name_chord(sm.polygon_voice_chord(4)) == "diminished 7th"
    assert sm.polygon_voice_chord(6) == [0, 2, 4, 6, 8, 10]
    assert sm.polygon_voice_chord(12) == list(range(12))

    octa_angles, octa_pcs = sm.relations_chord(sm.PLATONIC["octahedron (our crystal)"])
    assert octa_angles == [90.0, 180.0]
    assert octa_pcs == [3, 6]

    cube_angles, cube_pcs = sm.relations_chord(sm.PLATONIC["cube"])
    assert any(abs(angle - 70.5) < 0.2 for angle in cube_angles)
    assert cube_pcs == [2, 4, 6]
    assert len(sm.FOUR_D["24-cell (4D)"]) == 24


def test_wav_manifest_and_dataset_receipts(monkeypatch, tmp_path):
    mods = _fresh_modules(monkeypatch, tmp_path, clips=14)
    shape_audio = mods["shape_audio"]
    shape_manifest = mods["shape_manifest"]
    shape_dataset = mods["shape_dataset"]

    assert shape_audio.main() == 0
    wav_dir = Path(shape_audio.OUT)
    wavs = sorted(wav_dir.glob("*.wav"))
    assert len(wavs) == 10
    with wave.open(str(wavs[0]), "rb") as wav:
        assert wav.getframerate() == shape_audio.SR
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getnframes() > 0

    assert shape_manifest.main() == 0
    manifest_path = wav_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["meta"]["rows"] == 16
    assert len(manifest["seal_sha256"]) == 64
    assert any(row["shape"] == "six-tongues" for row in manifest["shapes"])

    assert shape_dataset.main() == 0
    dataset_dir = Path(shape_dataset.OUT)
    labels = (dataset_dir / "labels.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(labels) == 14
    first = json.loads(labels[0])
    assert set(first) >= {"file", "shape", "pitch_classes", "notes", "freqs_hz"}
    assert (dataset_dir / first["file"]).exists()


def test_easy_listener_recovers_ground_truth_chords(monkeypatch, tmp_path):
    mods = _fresh_modules(monkeypatch, tmp_path, clips=28)
    assert mods["shape_listen"].main() == 0


def test_hard_benchmark_stays_above_floor(monkeypatch, tmp_path):
    mods = _fresh_modules(monkeypatch, tmp_path, clips=28)
    shape_hard = mods["shape_hard"]
    sm = mods["shape_music"]

    cat = shape_hard.shape_catalog()
    clips = []
    shape_hard.random.seed(23)
    for i in range(shape_hard.N_CLIPS):
        name, _dim, pcs = cat[i % len(cat)]
        octave = shape_hard.random.choice([3, 4])
        detune = shape_hard.random.choice([8.0, 15.0, 20.0])
        noise = shape_hard.random.choice([0.02, 0.04, 0.06])
        frames = shape_hard.make_hard_clip(pcs, octave, detune, noise)
        chroma = shape_hard.chroma_of(frames)
        clips.append(
            {
                "shape": name,
                "true": pcs,
                "l1": shape_hard.L1_naive(chroma),
                "l2": shape_hard.L2_overtone_aware(chroma),
                "l3": shape_hard.L3_hybrid(chroma),
            }
        )

    common = max({tuple(c["true"]) for c in clips}, key=lambda chord: sum(tuple(c["true"]) == chord for c in clips))
    floor = sum(1 for c in clips if tuple(c["true"]) == common) / len(clips)

    def exact(key: str) -> float:
        return sum(1 for c in clips if c[key] == c["true"]) / len(clips)

    assert exact("l1") > floor
    assert exact("l2") > floor
    assert exact("l3") >= max(exact("l1"), exact("l2"))

    collisions = {}
    for name, _dim, pcs in cat:
        collisions.setdefault(tuple(pcs), []).append(name)
    assert set(collisions[(3, 6)]) == {"octahedron", "16-cell"}
    assert "whole-tone scale" == sm.name_chord([0, 2, 4, 6, 8, 10])
