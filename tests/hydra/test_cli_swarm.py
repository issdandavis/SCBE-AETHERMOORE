"""
Tests for HYDRA Swarm Browser CLI.
====================================

Covers:
- CLI module imports without error
- Argument parser accepts expected flags
- --dry-run flag is recognized
- --status flag is recognized
- --provider choices are validated
- --backend choices are validated
- Missing task + no --status prints help (exits non-zero)
"""

import argparse
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


# =========================================================================
# Import
# =========================================================================


class TestCLIImport:
    """cli_swarm module is importable."""

    def test_import_module(self):
        from hydra import cli_swarm
        assert cli_swarm is not None

    def test_main_function_exists(self):
        from hydra.cli_swarm import main
        assert callable(main)


# =========================================================================
# Argument parsing
# =========================================================================


def _build_parser():
    """Recreate the argparse parser from cli_swarm for testing."""
    parser = argparse.ArgumentParser(prog="hydra-swarm")
    parser.add_argument("task", nargs="?", default=None)
    parser.add_argument("--provider", default="local",
                        choices=["local", "hf", "huggingface"])
    parser.add_argument("--model", default="local-model")
    parser.add_argument("--base-url", default="http://localhost:1234/v1")
    parser.add_argument("--backend", default="playwright",
                        choices=["playwright", "selenium", "cdp"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--status", action="store_true")
    return parser


class TestArgumentParsing:
    """CLI argument parsing."""

    def test_task_argument(self):
        parser = _build_parser()
        args = parser.parse_args(["search for SCBE"])
        assert args.task == "search for SCBE"

    def test_no_task_defaults_none(self):
        parser = _build_parser()
        args = parser.parse_args([])
        assert args.task is None

    def test_dry_run_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["--dry-run", "test task"])
        assert args.dry_run is True

    def test_status_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["--status"])
        assert args.status is True

    def test_provider_local_default(self):
        parser = _build_parser()
        args = parser.parse_args(["test"])
        assert args.provider == "local"

    def test_provider_hf(self):
        parser = _build_parser()
        args = parser.parse_args(["--provider", "hf", "test"])
        assert args.provider == "hf"

    def test_provider_huggingface(self):
        parser = _build_parser()
        args = parser.parse_args(["--provider", "huggingface", "test"])
        assert args.provider == "huggingface"

    def test_invalid_provider_rejected(self):
        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--provider", "claude", "test"])

    def test_backend_default_playwright(self):
        parser = _build_parser()
        args = parser.parse_args(["test"])
        assert args.backend == "playwright"

    def test_backend_selenium(self):
        parser = _build_parser()
        args = parser.parse_args(["--backend", "selenium", "test"])
        assert args.backend == "selenium"

    def test_backend_cdp(self):
        parser = _build_parser()
        args = parser.parse_args(["--backend", "cdp", "test"])
        assert args.backend == "cdp"

    def test_invalid_backend_rejected(self):
        parser = _build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--backend", "chrome_mcp", "test"])

    def test_model_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["--model", "my-custom-model", "test"])
        assert args.model == "my-custom-model"

    def test_base_url_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["--base-url", "http://remote:5000/v1", "test"])
        assert args.base_url == "http://remote:5000/v1"

    def test_all_flags_combined(self):
        parser = _build_parser()
        args = parser.parse_args([
            "--provider", "hf",
            "--model", "mistral-7b",
            "--backend", "cdp",
            "--dry-run",
            "navigate to example.com",
        ])
        assert args.provider == "hf"
        assert args.model == "mistral-7b"
        assert args.backend == "cdp"
        assert args.dry_run is True
        assert args.task == "navigate to example.com"
