"""Tests for scripts/kaggle/scbe_kaggle.py.

The bridge calls out to the Kaggle service in production, so we mock
the Python `KaggleApi` for everything that would touch the network.
The pure functions (validation, env-aliasing, keyword filtering) are
tested directly with no mocks.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "kaggle" / "scbe_kaggle.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("_scbe_kaggle", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def sk():
    return _load_module()


# ---------------------------------------------------------------------------
# Pure: ensure_auth_env
# ---------------------------------------------------------------------------


def test_ensure_auth_env_aliases_token_to_key(sk, monkeypatch) -> None:
    monkeypatch.delenv("KAGGLE_KEY", raising=False)
    monkeypatch.setenv("KAGGLE_API_TOKEN", "KGAT_test_value_xyz")
    sk.ensure_auth_env()
    assert os.environ["KAGGLE_KEY"] == "KGAT_test_value_xyz"


def test_ensure_auth_env_noop_when_key_already_set(sk, monkeypatch) -> None:
    monkeypatch.setenv("KAGGLE_KEY", "already_set")
    monkeypatch.setenv("KAGGLE_API_TOKEN", "should_not_overwrite")
    sk.ensure_auth_env()
    assert os.environ["KAGGLE_KEY"] == "already_set"


def test_ensure_auth_env_raises_when_neither_set(sk, monkeypatch) -> None:
    monkeypatch.delenv("KAGGLE_KEY", raising=False)
    monkeypatch.delenv("KAGGLE_API_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="Kaggle auth missing"):
        sk.ensure_auth_env()


# ---------------------------------------------------------------------------
# Pure: validate_metadata
# ---------------------------------------------------------------------------


def _good_meta() -> dict:
    return {
        "id": "issacizrealdavis/scbe-thing-v1",
        "title": "SCBE Thing v1 example title",
        "subtitle": "Twenty-character minimum subtitle here for tests",
        "licenses": [{"name": "other"}],
        "keywords": ["chemistry", "education"],
    }


def test_validate_metadata_happy_path(sk) -> None:
    v = sk.validate_metadata(_good_meta())
    assert v.ok
    assert v.errors == []


def test_validate_metadata_rejects_short_title(sk) -> None:
    meta = _good_meta()
    meta["title"] = "abc"  # too short
    v = sk.validate_metadata(meta)
    assert not v.ok
    assert any("title must be" in e for e in v.errors)


def test_validate_metadata_rejects_long_title(sk) -> None:
    meta = _good_meta()
    meta["title"] = "x" * 51
    v = sk.validate_metadata(meta)
    assert not v.ok
    assert any("title must be" in e for e in v.errors)


def test_validate_metadata_rejects_short_subtitle(sk) -> None:
    meta = _good_meta()
    meta["subtitle"] = "too short"
    v = sk.validate_metadata(meta)
    assert not v.ok
    assert any("subtitle must be" in e for e in v.errors)


def test_validate_metadata_rejects_invalid_license(sk) -> None:
    meta = _good_meta()
    meta["licenses"] = [{"name": "MIT"}]  # MIT is NOT a valid Kaggle slug
    v = sk.validate_metadata(meta)
    assert not v.ok
    assert any("not in valid set" in e for e in v.errors)


def test_validate_metadata_rejects_zero_licenses(sk) -> None:
    meta = _good_meta()
    meta["licenses"] = []
    v = sk.validate_metadata(meta)
    assert not v.ok
    assert any("exactly one entry" in e for e in v.errors)


def test_validate_metadata_warns_on_multiword_keywords(sk) -> None:
    meta = _good_meta()
    meta["keywords"] = ["chemistry", "instruction tuning"]
    v = sk.validate_metadata(meta)
    assert v.ok  # warning, not error
    assert any("instruction tuning" in w for w in v.warnings)


def test_validate_metadata_rejects_bad_id(sk) -> None:
    meta = _good_meta()
    meta["id"] = "no_slash_here"
    v = sk.validate_metadata(meta)
    assert not v.ok
    assert any("owner/slug" in e for e in v.errors)


# ---------------------------------------------------------------------------
# Pure: filter_invalid_keywords
# ---------------------------------------------------------------------------


def test_filter_invalid_keywords_partitions(sk) -> None:
    kept, dropped = sk.filter_invalid_keywords(
        ["chemistry", "instruction tuning", "education", "fine_tuning", "agents"]
    )
    assert kept == ["chemistry", "education", "agents"]
    assert dropped == ["instruction tuning", "fine_tuning"]


def test_filter_invalid_keywords_handles_non_strings(sk) -> None:
    kept, dropped = sk.filter_invalid_keywords(["chemistry", 42, None])
    assert kept == ["chemistry"]
    assert dropped == ["42", "None"]


# ---------------------------------------------------------------------------
# Mocked: KaggleBridge wraps Python KaggleApi
# ---------------------------------------------------------------------------


def _bridge_with_mock_api(sk) -> tuple[object, MagicMock]:
    bridge = sk.KaggleBridge()
    api_mock = MagicMock()
    bridge._api = api_mock  # bypass auth + lazy import
    return bridge, api_mock


def test_list_my_datasets_shapes_results(sk) -> None:
    bridge, api = _bridge_with_mock_api(sk)
    fake_ds = MagicMock(ref="me/x", title="X", totalBytes=100, lastUpdated="2026-05-11", isPrivate=True)
    api.dataset_list.return_value = [fake_ds]
    rows = bridge.list_my_datasets(limit=10)
    api.dataset_list.assert_called_once_with(mine=True)
    assert rows == [{"ref": "me/x", "title": "X", "size": 100, "last_updated": "2026-05-11", "is_private": True}]


def test_info_round_trips_via_dataset_metadata(sk, tmp_path) -> None:
    bridge, api = _bridge_with_mock_api(sk)

    captured: dict = {}

    def fake_dataset_metadata(ref: str, path: str) -> None:
        captured["ref"] = ref
        captured["path"] = path
        meta = {
            "id": "me/x",
            "title": "X",
            "subtitle": "sub",
            "licenses": [{"name": "other"}],
            "keywords": ["chemistry"],
            "isPrivate": False,
        }
        Path(path, "dataset-metadata.json").write_text(json.dumps(meta), encoding="utf-8")

    api.dataset_metadata.side_effect = fake_dataset_metadata
    info = bridge.info("me/x")
    assert captured["ref"] == "me/x"
    assert info["ref"] == "me/x"
    assert info["license"] == "other"
    assert info["keywords"] == ["chemistry"]
    assert info["is_private"] is False


def test_pull_invokes_download_files(sk, tmp_path) -> None:
    bridge, api = _bridge_with_mock_api(sk)
    out = bridge.pull("me/x", tmp_path / "downloads")
    assert (tmp_path / "downloads").exists()
    api.dataset_download_files.assert_called_once()
    assert out == tmp_path / "downloads"


def test_push_create_validates_metadata_first(sk, tmp_path) -> None:
    bridge, api = _bridge_with_mock_api(sk)
    folder = tmp_path / "ds"
    folder.mkdir()
    bad_meta = {"id": "no_slash", "title": "x", "licenses": []}
    (folder / "dataset-metadata.json").write_text(json.dumps(bad_meta), encoding="utf-8")
    with pytest.raises(ValueError, match="metadata invalid"):
        bridge.push_create(folder, is_public=True)
    api.dataset_create_new.assert_not_called()


def test_push_create_drops_invalid_keywords_then_uploads(sk, tmp_path, capsys) -> None:
    bridge, api = _bridge_with_mock_api(sk)
    folder = tmp_path / "ds"
    folder.mkdir()
    meta = _good_meta()
    meta["keywords"] = ["chemistry", "instruction tuning", "education"]
    (folder / "dataset-metadata.json").write_text(json.dumps(meta), encoding="utf-8")
    ref = bridge.push_create(folder, is_public=True)
    assert ref == "issacizrealdavis/scbe-thing-v1"
    api.dataset_create_new.assert_called_once()
    rewritten = json.loads((folder / "dataset-metadata.json").read_text(encoding="utf-8"))
    assert "instruction tuning" not in rewritten["keywords"]
    assert rewritten["keywords"] == ["chemistry", "education"]
    captured = capsys.readouterr()
    assert "dropping invalid keywords" in captured.err


def test_push_version_calls_create_version(sk, tmp_path) -> None:
    bridge, api = _bridge_with_mock_api(sk)
    folder = tmp_path / "ds"
    folder.mkdir()
    (folder / "dataset-metadata.json").write_text(json.dumps(_good_meta()), encoding="utf-8")
    ref = bridge.push_version(folder, message="bump")
    assert ref == "issacizrealdavis/scbe-thing-v1"
    api.dataset_create_version.assert_called_once()
    kwargs = api.dataset_create_version.call_args.kwargs
    assert kwargs["version_notes"] == "bump"


def test_update_metadata_calls_dataset_metadata_update(sk, tmp_path) -> None:
    bridge, api = _bridge_with_mock_api(sk)
    folder = tmp_path / "ds"
    folder.mkdir()
    (folder / "dataset-metadata.json").write_text(json.dumps(_good_meta()), encoding="utf-8")
    ref = bridge.update_metadata(folder)
    assert ref == "issacizrealdavis/scbe-thing-v1"
    api.dataset_metadata_update.assert_called_once_with("issacizrealdavis/scbe-thing-v1", str(folder))


# ---------------------------------------------------------------------------
# CLI exit codes
# ---------------------------------------------------------------------------


def test_cli_unknown_subcommand_exits_2(sk) -> None:
    with pytest.raises(SystemExit) as exc:
        sk.main([])  # no subcommand given
    assert exc.value.code != 0


def test_cli_pull_with_missing_auth_exits_2(sk, monkeypatch) -> None:
    monkeypatch.delenv("KAGGLE_KEY", raising=False)
    monkeypatch.delenv("KAGGLE_API_TOKEN", raising=False)
    rc = sk.main(["pull", "me/x"])
    assert rc == 2


# ---------------------------------------------------------------------------
# Bus context hint
# ---------------------------------------------------------------------------


def test_format_kaggle_context_hint_empty_when_env_unset(sk, monkeypatch) -> None:
    monkeypatch.delenv("SCBE_KAGGLE_CONTEXT_SLUGS", raising=False)
    assert sk.format_kaggle_context_hint() == ""


def test_format_kaggle_context_hint_pulls_per_slug(sk, monkeypatch) -> None:
    monkeypatch.setenv("SCBE_KAGGLE_CONTEXT_SLUGS", "me/a,me/b")
    bridge = sk.KaggleBridge()
    bridge._api = MagicMock()  # unused — we override info() below
    bridge.info = MagicMock(  # type: ignore[method-assign]
        side_effect=[
            {"ref": "me/a", "title": "Alpha", "license": "other", "is_private": False},
            {"ref": "me/b", "title": "Beta", "license": "cc", "is_private": True},
        ]
    )
    out = sk.format_kaggle_context_hint(bridge=bridge)
    assert "Kaggle context datasets" in out
    assert "me/a — Alpha (license=other, public)" in out
    assert "me/b — Beta (license=cc, private)" in out


def test_format_kaggle_context_hint_handles_per_slug_failures(sk, monkeypatch) -> None:
    monkeypatch.setenv("SCBE_KAGGLE_CONTEXT_SLUGS", "me/a,me/b")
    bridge = sk.KaggleBridge()
    bridge._api = MagicMock()
    bridge.info = MagicMock(  # type: ignore[method-assign]
        side_effect=[
            {"ref": "me/a", "title": "Alpha", "license": "other", "is_private": False},
            RuntimeError("kaggle 404"),
        ]
    )
    out = sk.format_kaggle_context_hint(bridge=bridge)
    assert "me/a — Alpha" in out
    assert "me/b (fetch failed: kaggle 404)" in out


def test_format_kaggle_context_hint_swallows_auth_error(sk, monkeypatch) -> None:
    """If env var is set but auth is missing, return '' rather than crash the bus."""
    monkeypatch.setenv("SCBE_KAGGLE_CONTEXT_SLUGS", "me/a")
    monkeypatch.delenv("KAGGLE_KEY", raising=False)
    monkeypatch.delenv("KAGGLE_API_TOKEN", raising=False)
    # The default bridge construction tries to authenticate, which raises.
    assert sk.format_kaggle_context_hint() == ""
