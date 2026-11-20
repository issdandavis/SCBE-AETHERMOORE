from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import shutil

import pytest

import prepare_release
import verify_release


HERE = Path(__file__).resolve().parent
PACKET = HERE / "packet"


def load_packet_runner():
    path = PACKET / "run_kaggle_readonly_intake.py"
    spec = importlib.util.spec_from_file_location("tested_vqcc_intake_release", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_monolith():
    path = PACKET / "clay_vqcc_readonly_intake.py"
    spec = importlib.util.spec_from_file_location("tested_vqcc_intake_monolith", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_packet_manifest_and_authority_are_sealed() -> None:
    receipt = verify_release.verify_packet()
    assert receipt["status"] == "PASS_PREPARED_ONLY"
    assert receipt["admission_state"] == "NOT_CONSUMED"
    assert receipt["execution_authorized"] is False
    metadata = json.loads((PACKET / "kernel-metadata.json").read_text(encoding="utf-8"))
    assert metadata["code_file"] == "clay_vqcc_readonly_intake.py"
    assert metadata["dataset_sources"] == [
        "issacizrealdavis/clay-vqcc-research-corpus/2"
    ]


def test_release_build_is_reproducible(tmp_path: Path) -> None:
    rebuilt = tmp_path / "packet"
    expected = prepare_release.build_packet(rebuilt)
    actual = json.loads((PACKET / "RELEASE_MANIFEST.json").read_text(encoding="utf-8"))
    assert expected == actual
    for row in expected["files"]:
        assert (rebuilt / row["path"]).read_bytes() == (PACKET / row["path"]).read_bytes()


def test_monolith_materializes_exact_runtime_and_fails_closed() -> None:
    monolith = load_monolith()
    root = monolith.materialize_runtime()
    try:
        path = root / "runtime_main.py"
        spec = importlib.util.spec_from_file_location("tested_embedded_vqcc_intake", path)
        assert spec is not None and spec.loader is not None
        runner = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = runner
        spec.loader.exec_module(runner)
        assert runner.verify_bundled_sources() == runner.EXPECTED_SOURCE_HASHES
        with pytest.raises(runner.ReleaseError, match="staged but not authorized"):
            runner.require_execution_admission()
    finally:
        shutil.rmtree(root)


def test_mount_discovery_is_hash_pinned_and_ambiguity_fails(tmp_path: Path) -> None:
    runner = load_packet_runner()
    first = tmp_path / "first"
    first.mkdir()
    (first / "CORPUS_MANIFEST.json").write_bytes((PACKET / "CAMPAIGN_SPEC.json").read_bytes())
    with pytest.raises(runner.ReleaseError, match="found 0"):
        runner.discover_corpus_root(tmp_path)

    # Use monkeypatching only for the hermetic mount-discovery fixture; runtime
    # still pins the production manifest constant embedded in the packet.
    expected = runner.sha256_file(first / "CORPUS_MANIFEST.json")
    original = runner.EXPECTED_MANIFEST_SHA256
    runner.EXPECTED_MANIFEST_SHA256 = expected
    try:
        assert runner.discover_corpus_root(tmp_path) == first.resolve()
        second = tmp_path / "second"
        second.mkdir()
        (second / "CORPUS_MANIFEST.json").write_bytes((first / "CORPUS_MANIFEST.json").read_bytes())
        with pytest.raises(runner.ReleaseError, match="found 2"):
            runner.discover_corpus_root(tmp_path)
    finally:
        runner.EXPECTED_MANIFEST_SHA256 = original


def test_local_smoke_reads_no_corpus_and_starts_no_cloud_work(tmp_path: Path) -> None:
    isolated = tmp_path / "isolated"
    isolated.mkdir()
    code_file = isolated / "clay_vqcc_readonly_intake.py"
    shutil.copyfile(PACKET / code_file.name, code_file)
    output = tmp_path / "SMOKE.json"
    completed = subprocess.run(
        [sys.executable, str(code_file), "--smoke-output", str(output)],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0, completed.stderr
    receipt = json.loads(output.read_text(encoding="utf-8"))
    assert receipt["status"] == "PASS_NO_CORPUS_READ_NO_CLOUD_EXECUTION"
    assert receipt["cloud_execution"] is False
    assert receipt["training"] is False
    assert receipt["competition_submission"] is False


def test_packet_has_no_provider_mutator_or_network_client() -> None:
    text = (PACKET / "clay_vqcc_readonly_intake.py").read_text(encoding="utf-8")
    forbidden = (
        "kernels push",
        "dataset_create",
        "dataset_new",
        "competition_submit",
        "requests.",
        "urllib.request",
        "http://",
        "https://",
    )
    assert all(token not in text for token in forbidden)
