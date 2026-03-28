from __future__ import annotations

import importlib.util
import json
from pathlib import Path

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "system"
    / "build_repurpose_manifest.py"
)
SPEC = importlib.util.spec_from_file_location("build_repurpose_manifest", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def test_build_manifest_classifies_top_level_paths(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    (repo_root / "src").mkdir()
    (repo_root / "src" / "index.ts").write_text(
        "export const ok = true;\n", encoding="utf-8"
    )

    (repo_root / "artifacts").mkdir()
    (repo_root / "artifacts" / "run.log").write_text("hello\n", encoding="utf-8")

    (repo_root / "training-data").mkdir()
    (repo_root / "training-data" / "records.jsonl").write_text(
        '{"ok": true}\n', encoding="utf-8"
    )

    (repo_root / ".env").write_text("SECRET=1\n", encoding="utf-8")

    policy_path = tmp_path / "policy.json"
    policy_path.write_text(
        json.dumps(
            {
                "rules": [
                    {
                        "name": "keep-source",
                        "patterns": ["src"],
                        "bucket": "keep-in-repo",
                        "destinations": ["github"],
                        "reason": "live code",
                    },
                    {
                        "name": "cloud-artifacts",
                        "patterns": ["artifacts"],
                        "bucket": "archive-or-cloud",
                        "destinations": ["gdrive"],
                        "reason": "generated output",
                    },
                    {
                        "name": "datasets",
                        "patterns": ["training-data"],
                        "bucket": "manual-review",
                        "destinations": ["huggingface", "gdrive"],
                        "reason": "needs curation",
                    },
                    {
                        "name": "secrets",
                        "patterns": [".env", ".env.*"],
                        "bucket": "security-now",
                        "destinations": [],
                        "reason": "sensitive",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )

    policy = MODULE.load_policy(policy_path)
    manifest = MODULE.build_manifest(repo_root, policy)
    entries = {entry["name"]: entry for entry in manifest["entries"]}

    assert entries["src"]["bucket"] == "keep-in-repo"
    assert entries["src"]["destinations"] == ["github"]

    assert entries["artifacts"]["bucket"] == "archive-or-cloud"
    assert entries["artifacts"]["destinations"] == ["gdrive"]

    assert entries["training-data"]["bucket"] == "manual-review"
    assert entries["training-data"]["destinations"] == ["huggingface", "gdrive"]

    assert entries[".env"]["bucket"] == "security-now"
    assert entries[".env"]["destinations"] == []
