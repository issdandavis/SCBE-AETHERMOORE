from __future__ import annotations

from pathlib import Path

import pytest

from scripts.build_hf_webtoon_job import build_uv_job_script, load_prompt_pack
from scripts.submit_hf_webtoon_job import build_submit_command


def test_load_prompt_pack_counts_current_repo_data() -> None:
    chapters, total_panels = load_prompt_pack()
    derived_total = sum(len(chapter.get("panels", [])) for chapter in chapters)
    ch01 = next(chapter for chapter in chapters if chapter["chapter_id"] == "ch01")
    first_panel = ch01["panels"][0]

    assert len(chapters) == 38
    assert total_panels == derived_total
    assert total_panels >= 305
    assert chapters[0]["chapter_id"] == "ch01"
    assert ch01.get("reference_chapter") is True
    assert len(ch01.get("panels", [])) >= 10
    assert first_panel["compiled_prompt"].startswith("sixtongues_style, manhwa webtoon panel")
    assert "Marcus" in first_panel["compiled_prompt"]


def test_build_uv_job_script_embeds_prompt_pack_and_defaults() -> None:
    chapters, _ = load_prompt_pack()

    script = build_uv_job_script(chapters)

    assert "# /// script" in script
    assert "PROMPT_PACK = json.loads" in script
    assert 'DEFAULT_OUTPUT_REPO = "issdandavis/six-tongues-webtoon-panels"' in script
    assert '"chapter_id": "ch01"' in script
    assert '"compiled_prompt": "sixtongues_style, manhwa webtoon panel' in script
    assert 'prompt = panel.get("compiled_prompt") or panel.get("prompt") or ""' in script


def test_build_uv_job_script_rejects_empty_pack() -> None:
    with pytest.raises(ValueError, match="empty"):
        build_uv_job_script([])


def test_build_submit_command_includes_expected_hf_jobs_flags() -> None:
    command = build_submit_command(
        Path("artifact.py"),
        flavor="a10g-small",
        timeout="8h",
        output_repo="issdandavis/six-tongues-webtoon-panels",
        model_id="black-forest-labs/FLUX.1-schnell",
        max_panels=5,
        only_chapters="ch01,ch02",
        run_name="smoke-run",
        detach=True,
    )

    assert command[:4] == ["hf", "jobs", "uv", "run"]
    assert "--secrets" in command
    assert "HF_TOKEN" in command
    assert "--detach" in command
    assert "--max-panels" in command
    assert "--only-chapters" in command
    assert command[-8:] == [
        "--model-id",
        "black-forest-labs/FLUX.1-schnell",
        "--max-panels",
        "5",
        "--only-chapters",
        "ch01,ch02",
        "--run-name",
        "smoke-run",
    ]
