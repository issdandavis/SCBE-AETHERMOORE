from scripts.system.build_training_bucket_index import build_bucket_index


def test_training_bucket_index_has_useful_buckets():
    index = build_bucket_index()
    bucket_ids = {bucket["bucket_id"] for bucket in index["buckets"]}

    assert "coding_transport" in bucket_ids
    assert "aligned_foundations_chemistry" in bucket_ids
    assert "interop_social_civic" in bucket_ids
    assert "story_manhwa_social" in bucket_ids
    assert index["summary"]["bucket_count"] >= 8


def test_interop_social_bucket_captures_new_pillars():
    index = build_bucket_index()
    bucket = next(bucket for bucket in index["buckets"] if bucket["bucket_id"] == "interop_social_civic")
    paths = {item["path"] for item in bucket["files"]}

    assert "src/interop/view_token_envelope.py" in paths
    assert "docs/architecture/SOCIAL_CONSTRUCT_FRAMING_PILLARS_2026-04-28.md" in paths
    assert "docs/architecture/VIEW_DEPENDENT_TOKENIZER_INTEROP_RESEARCH_2026-04-28.md" in paths
    assert bucket["gate"] == "dual-frame payload identity, formation route, and social appeal path"

