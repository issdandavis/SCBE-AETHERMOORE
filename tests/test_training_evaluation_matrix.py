from scripts.eval.build_training_evaluation_matrix import loose_adapter_match


def test_loose_adapter_match_rejects_different_versioned_runs():
    left = "artifacts/kaggle_output/polly-auto-bijective-tongue-coder-v1/polly-bijective-tongue-coder-v1"
    right = "artifacts/kaggle_output/polly-auto-bijective-tongue-coder-v2/polly-bijective-tongue-coder-v2"

    assert not loose_adapter_match(left, right)


def test_loose_adapter_match_accepts_same_version_path_variants():
    left = "artifacts/kaggle_output/polly-auto-bijective-tongue-coder-v2/polly-bijective-tongue-coder-v2"
    right = "artifacts-kaggle_output-polly-auto-bijective-tongue-coder-v2-polly-bijective-tongue-coder-v2-20260427T043147Z"

    assert loose_adapter_match(left, right)
