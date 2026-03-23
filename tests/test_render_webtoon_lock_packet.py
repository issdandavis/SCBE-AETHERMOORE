from __future__ import annotations

import json
from pathlib import Path

import scripts.render_webtoon_lock_packet as renderer


def write_lock_packet(path: Path) -> None:
    payload = {
        "lock_name": "ch01-marcus-face-lock",
        "panel_id": "ch01-v4-p11",
        "shot_label": "CH01-011",
        "preferred_backend": "imagen-ultra",
        "fallback_backend": "hf",
        "prompt": "single vertical Korean webtoon panel. Character lock: marcus: Asian-American man early 30s Close on Marcus in green light.",
        "negative_prompt": "speech bubbles, white man, text overlays",
        "width": 720,
        "height": 1280,
        "acceptance_criteria": ["Marcus must clearly read as Asian-American."],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_run_lock_packet_dry_run_writes_manifest(tmp_path: Path, monkeypatch) -> None:
    lock_packet_path = tmp_path / "lock_packet.json"
    write_lock_packet(lock_packet_path)

    monkeypatch.setattr(
        renderer,
        "check_backends",
        lambda: {"imagen": True, "imagen-ultra": True, "hf": True, "zimage": False},
    )
    monkeypatch.setattr(renderer, "pick_best_backend", lambda preference=None: "imagen")

    manifest_path = renderer.run_lock_packet(lock_packet_path, dry_run=True)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["dry_run"] is True
    assert manifest["panel_id"] == "ch01-v4-p11"
    assert manifest["backend"] == "imagen-ultra"
    assert manifest["ok"] is True
    assert manifest["output"].endswith("ch01-v4-p11.png")


def test_run_lock_packet_retries_with_fallback(tmp_path: Path, monkeypatch) -> None:
    lock_packet_path = tmp_path / "lock_packet.json"
    write_lock_packet(lock_packet_path)
    calls: list[str] = []

    monkeypatch.setattr(
        renderer,
        "check_backends",
        lambda: {"imagen": True, "imagen-ultra": True, "hf": True, "zimage": False},
    )
    monkeypatch.setattr(renderer, "pick_best_backend", lambda preference=None: "imagen")

    def fake_generate(*, backend, prompt, output, aspect, reference, negative_prompt, width, height):
        calls.append(backend)
        if backend == "imagen-ultra":
            raise RuntimeError("429 RESOURCE_EXHAUSTED quota")
        Path(output).write_bytes(b"ok")
        return output

    monkeypatch.setattr(renderer, "generate", fake_generate)

    manifest_path = renderer.run_lock_packet(lock_packet_path, dry_run=False)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert calls == ["imagen-ultra", "hf"]
    assert manifest["ok"] is True
    assert manifest["backend"] == "hf"
    assert manifest["fallback_from"] == "imagen-ultra"
