from __future__ import annotations

import json
from pathlib import Path

from scripts import render_full_book_router


def write_packet(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def test_process_packet_blocks_when_source_cannot_be_resolved(tmp_path: Path) -> None:
    packet_path = write_packet(
        tmp_path / "broken_prompts.json",
        {
            "chapter_id": "custom01",
            "title": "Broken Packet",
            "panels": [
                {
                    "scene_prompt": "Marcus studies terminal logs in the office before reality whites out.",
                }
            ],
        },
    )

    summary = render_full_book_router.process_packet(
        packet_path,
        output_root=tmp_path / "out",
        backend_override="hf",
        dry_run=True,
        no_skip_existing=False,
    )

    assert summary["status"] == "blocked-source"
    assert summary["source_verification"]["ok"] is False
    assert (
        "source_markdown could not be resolved"
        in summary["source_verification"]["errors"]
    )
    assert (
        "key_script could not be resolved" in summary["source_verification"]["errors"]
    )


def test_process_packet_blocks_when_prompt_governance_fails(tmp_path: Path) -> None:
    source_path = tmp_path / "source.md"
    source_path.write_text("# chapter", encoding="utf-8")
    key_script_path = tmp_path / "script.md"
    key_script_path.write_text("# beats", encoding="utf-8")

    packet_path = write_packet(
        tmp_path / "unknown_character_prompts.json",
        {
            "chapter_id": "custom02",
            "title": "Unknown Character",
            "source_markdown": str(source_path),
            "key_script": str(key_script_path),
            "panels": [
                {
                    "scene_prompt": "A stranger studies Marcus from the office doorway.",
                    "environment": "earth_office",
                    "characters": ["mystery_guest"],
                    "arc_lock": "earth_protocol_noir",
                    "cornerstone_style": "standard_dialogue",
                    "mood": "tension",
                    "w": 720,
                    "h": 1280,
                }
            ],
        },
    )

    summary = render_full_book_router.process_packet(
        packet_path,
        output_root=tmp_path / "out",
        backend_override="hf",
        dry_run=True,
        no_skip_existing=False,
    )

    assert summary["status"] == "blocked-prompt"
    assert summary["prompt_governance"]["approved"] is False
    assert any(
        "unknown character 'mystery_guest'" in error
        for error in summary["prompt_governance"]["errors"]
    )


def test_process_packet_writes_governed_packet_before_render(
    tmp_path: Path, monkeypatch
) -> None:
    source_path = tmp_path / "source.md"
    source_path.write_text("# chapter", encoding="utf-8")
    key_script_path = tmp_path / "script.md"
    key_script_path.write_text("# beats", encoding="utf-8")

    packet_path = write_packet(
        tmp_path / "valid_prompts.json",
        {
            "chapter_id": "custom03",
            "title": "Valid Packet",
            "source_markdown": str(source_path),
            "key_script": str(key_script_path),
            "panels": [
                {
                    "scene_prompt": "Marcus studies terminal logs in the office before reality whites out.",
                }
            ],
        },
    )

    def fake_run_packet(
        packet_path_arg: str | Path,
        *,
        output_root: str | None = None,
        only_ids: list[str] | None = None,
        limit: int | None = None,
        backend_override: str | None = None,
        dry_run: bool = False,
    ) -> Path:
        packet = json.loads(Path(packet_path_arg).read_text(encoding="utf-8"))
        chapter_id = str(packet.get("chapter_id") or "packet")
        manifest_path = (
            Path(output_root or tmp_path / "out")
            / chapter_id
            / f"{Path(packet_path_arg).stem}_router_manifest.json"
        )
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "packet": str(packet_path_arg),
                    "chapter_id": chapter_id,
                    "panels": [{"id": f"{chapter_id}-p01", "ok": True}],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return manifest_path

    monkeypatch.setattr(render_full_book_router, "run_packet", fake_run_packet)

    summary = render_full_book_router.process_packet(
        packet_path,
        output_root=tmp_path / "out",
        backend_override="hf",
        dry_run=True,
        no_skip_existing=False,
    )

    governed_packet_path = Path(summary["governed_packet"])
    governed_packet = json.loads(governed_packet_path.read_text(encoding="utf-8"))
    source_report_path = Path(summary["source_verification"]["report"])
    prompt_report_path = Path(summary["prompt_governance"]["report"])

    assert summary["status"] == "done"
    assert source_report_path.exists()
    assert prompt_report_path.exists()
    assert governed_packet_path.exists()
    assert governed_packet["panels"][0]["compiled_prompt"].startswith(
        "manhwa webtoon panel"
    )
    assert governed_packet["panels"][0]["negative_prompt"]
    assert summary["render"]["ok"] == 1


def test_source_stage_falls_back_to_direct_reader_source_and_title_matched_key_script(
    tmp_path: Path,
    monkeypatch,
) -> None:
    root = tmp_path / "repo"
    (root / "content" / "book" / "reader-edition").mkdir(parents=True)
    (root / "artifacts" / "webtoon").mkdir(parents=True)
    reader_source = root / "content" / "book" / "reader-edition" / "ch14.md"
    reader_source.write_text("# Chapter 14: Threshold Country", encoding="utf-8")
    key_script_file = root / "artifacts" / "webtoon" / "act3_panel_scripts.md"
    key_script_file.write_text("# Act 3 Panel Scripts", encoding="utf-8")
    manifest_path = root / "artifacts" / "webtoon" / "series_storyboard_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "episodes": [
                    {
                        "episode_id": "ep24",
                        "title": "Chapter 17: Threshold Country",
                        "source_markdown": "content/book/reader-edition/ch17.md",
                        "key_script": "artifacts/webtoon/act3_panel_scripts.md",
                        "section_type": "chapter",
                        "target_panel_min": 10,
                        "target_panel_max": 14,
                    }
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    packet_path = write_packet(
        tmp_path / "ch14_prompts.json",
        {
            "chapter_id": "ch14",
            "title": "Chapter 14: Threshold Country",
            "panels": [{"scene_prompt": "Marcus leaves the Spire."}],
        },
    )

    monkeypatch.setattr(render_full_book_router, "ROOT", root)
    monkeypatch.setattr(render_full_book_router, "SERIES_MANIFEST", manifest_path)
    monkeypatch.setattr(
        render_full_book_router,
        "READER_EDITION_DIR",
        root / "content" / "book" / "reader-edition",
    )
    monkeypatch.setattr(
        render_full_book_router, "lookup_episode_metadata", lambda **_: None
    )

    resolved_packet, report = render_full_book_router.source_stage(
        json.loads(packet_path.read_text(encoding="utf-8")), packet_path
    )

    assert report["ok"] is True
    assert resolved_packet["source_markdown"] == "content/book/reader-edition/ch14.md"
    assert resolved_packet["key_script"] == "artifacts/webtoon/act3_panel_scripts.md"
    assert resolved_packet["episode_id"] == "ep24"
