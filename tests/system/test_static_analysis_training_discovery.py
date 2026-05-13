from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOCS = REPO_ROOT / "docs"


def test_static_analysis_training_dataset_is_discoverable() -> None:
    llms = (DOCS / "llms.txt").read_text(encoding="utf-8")
    robot_md = (DOCS / "robot.md").read_text(encoding="utf-8")
    robot_html = (DOCS / "robot.html").read_text(encoding="utf-8")

    hf_url = "https://huggingface.co/datasets/issdandavis/scbe-static-analysis-training"
    kaggle_url = "https://www.kaggle.com/datasets/issacizrealdavis/scbe-static-analysis-training"

    assert hf_url in llms
    assert kaggle_url in llms
    assert hf_url in robot_md
    assert kaggle_url in robot_md
    assert hf_url in robot_html
