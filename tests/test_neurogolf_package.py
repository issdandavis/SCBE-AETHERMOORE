from __future__ import annotations

import pytest

from neurogolf.package import build_submission_zip, canonical_task_filename


def test_canonical_task_filename_accepts_competition_key():
    assert canonical_task_filename("task001") == "task001.onnx"


@pytest.mark.parametrize("task_id", ["136b0064", "task1", "task0001", "TASK001"])
def test_canonical_task_filename_rejects_noncanonical_key(task_id):
    with pytest.raises(ValueError, match="canonical competition key"):
        canonical_task_filename(task_id)


def test_build_submission_zip_rejects_noncanonical_arc_hash(tmp_path):
    model_path = tmp_path / "task001.onnx"
    model_path.write_bytes(b"test model")

    with pytest.raises(ValueError, match="canonical competition key"):
        build_submission_zip({"136b0064": model_path}, tmp_path / "submission.zip")
