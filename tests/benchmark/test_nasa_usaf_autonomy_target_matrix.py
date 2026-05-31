from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "benchmark" / "nasa_usaf_autonomy_target_matrix.py"


def _load_module():
    spec = importlib.util.spec_from_file_location(
        "nasa_usaf_autonomy_target_matrix_test", MODULE_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_report_exposes_failures_as_targets() -> None:
    module = _load_module()

    report = module.build_report()

    assert report["schema_version"] == "scbe_nasa_usaf_autonomy_target_matrix_v1"
    assert report["decision"] == "TARGETS_REQUIRED"
    assert report["summary"]["target_count"] >= 8
    assert report["summary"]["fail"] >= 3
    assert report["summary"]["partial"] >= 3
    assert any(t["target_id"] == "detect_avoid_well_clear" for t in report["targets"])
    assert any(
        "DAA-lite" in target
        for target in report["summary"]["highest_value_next_targets"]
    )


def test_sources_are_primary_nasa_or_air_force_urls() -> None:
    module = _load_module()

    report = module.build_report()
    urls = [source["url"] for source in report["sources"]]

    assert any("nasa.gov" in url for url in urls)
    assert any("af.mil" in url for url in urls)
    assert any("afresearchlab.com" in url for url in urls)


def test_markdown_contains_target_matrix() -> None:
    module = _load_module()

    markdown = module.render_markdown(module.build_report())

    assert "# NASA/USAF Autonomy Target Matrix" in markdown
    assert "Runtime assurance safety filter" in markdown
    assert "SCBE Autonomy Reference Interface" in markdown
