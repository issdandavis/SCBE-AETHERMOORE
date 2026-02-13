import importlib


def test_kernel_manifest_load_and_validate():
    mod = importlib.import_module("training.kernel_manifest")
    manifest = mod.load_manifest()

    missing = mod.validate_manifest_entries(manifest)

    assert manifest["version"] == 1
    assert len(manifest["kernel"]) >= 10
    assert missing == []


def test_kernel_manifest_summary_has_sha():
    mod = importlib.import_module("training.kernel_manifest")
    manifest = mod.load_manifest()

    summary = mod.to_summary(manifest)

    assert summary["kernel_file_count"] == len(manifest["kernel"])
    assert len(summary["kernel_manifest_sha"]) == 64
