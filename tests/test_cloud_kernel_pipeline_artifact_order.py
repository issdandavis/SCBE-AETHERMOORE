from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "scripts" / "cloud_kernel_data_pipeline.py"


def _call_line(tree: ast.AST, owner: str | None, name: str) -> int:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if owner is None and isinstance(func, ast.Name) and func.id == name:
            return node.lineno
        if (
            owner is not None
            and isinstance(func, ast.Attribute)
            and func.attr == name
            and isinstance(func.value, ast.Name)
            and func.value.id == owner
        ):
            return node.lineno
    raise AssertionError(f"missing expected call: {owner + '.' if owner else ''}{name}")


def test_verification_report_exists_before_archive_and_cloud_upload() -> None:
    """The scheduled pipeline must not ship an artifact it has not created yet."""
    tree = ast.parse(PIPELINE.read_text(encoding="utf-8"), filename=str(PIPELINE))

    write_report = _call_line(tree, "verification_json", "write_text")
    make_archive = _call_line(tree, "shutil", "make_archive")
    github_upload = _call_line(tree, None, "upload_to_github_release")

    assert write_report < make_archive < github_upload
