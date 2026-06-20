"""colab_run: the terminal Colab driver. Browser interaction can't be unit-tested headlessly, so these
lock the PURE logic that decides what runs and when it's done -- notebook resolution, the completion
marker extraction, and the CLI's mode guard. The transport (Playwright connect_over_cdp) is smoke-tested
manually against a real Chrome; see the module docstring runbook."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "colab"))

import colab_run as C  # noqa: E402


def test_resolve_notebook_default_and_url():
    assert C.resolve_notebook(None) == C.DEFAULT_NOTEBOOK
    assert "vtc_lift_qwen15_colab.ipynb" in C.DEFAULT_NOTEBOOK
    u = "https://colab.research.google.com/github/foo/bar/blob/main/x.ipynb"
    assert C.resolve_notebook(u) == u  # a full URL passes through untouched


def test_extract_block_finds_the_result_after_the_last_marker():
    text = "installing...\n\nVTC CODE LIFT\n  base solved: 1 / 5\n  NET LIFT      : +2\n"
    block = C._extract_block(text, "NET LIFT")
    assert block is not None and "NET LIFT      : +2" in block
    assert block.startswith("VTC CODE LIFT")  # grabs from the preceding blank line, not mid-stream noise


def test_extract_block_absent_marker_is_none():
    assert C._extract_block("no result yet, still training", "NET LIFT") is None
    assert C._extract_block("", "NET LIFT") is None


def test_extract_block_uses_the_last_occurrence():
    text = "NET LIFT: stale\n\nfresh run\n\nNET LIFT: +3"
    block = C._extract_block(text, "NET LIFT")
    assert block.endswith("+3")  # the most recent result, not an earlier one


def test_cli_requires_a_mode():
    with pytest.raises(SystemExit):  # neither --run nor --dry-run -> argparse error
        C.main([])
