from __future__ import annotations

import json

from scripts.system import news_pipeline, pipeline_to_hf


def _sample_item() -> dict:
    return {
        "title": "Kor'aelin transport alignment reaches stable delta",
        "url": "https://example.com/story",
        "source": "hn",
        "region": "us",
    }


def _fake_braid() -> dict:
    return {
        "aligned_score": 1.0,
        "aligned_components": {
            "semantic_alignment": 1.0,
            "roundtrip_ok": True,
            "atomic_home_alignment": 1.0,
            "phi_underlay_alignment": 1.0,
            "harmonic_fingerprint": 1.0,
        },
        "tongue_matrix": {
            "KO": 1.0,
            "AV": 0.492707,
            "RU": 0.61,
            "CA": 0.58,
            "UM": 0.57,
            "DR": 0.56,
        },
        "worst_mismatch_score": 0.492707,
        "best_mismatch_score": 0.61,
        "discriminatory_delta": 0.507293,
    }


def test_stage_tokenize_includes_braid_payload(monkeypatch):
    monkeypatch.setattr(news_pipeline, "_BRAID_AVAILABLE", True)
    monkeypatch.setattr(news_pipeline, "_braid_score", lambda payload, tongue: _fake_braid())

    tokenized = news_pipeline.stage_tokenize(news_pipeline.stage_geotag(_sample_item()))

    assert tokenized["tokenization"]["primary_tongue"] == "KO"
    assert tokenized["tokenization"]["all_roundtrip_ok"] is True
    assert tokenized["tokenization"]["braid"]["aligned_score"] == 1.0
    assert tokenized["tokenization"]["braid"]["discriminatory_delta"] == 0.507293


def test_sft_braid_alignment_skips_without_braid():
    tok = {"tokenization": {"braid": None}}
    assert news_pipeline.sft_braid_alignment(tok, 0) is None


def test_sft_braid_alignment_emits_cross_tongue_pair():
    tok = {
        "title": "Stable braid packet",
        "source": "hn",
        "tokenization": {
            "primary_tongue": "KO",
            "tongue_matrix": {"KO": {"tokens_preview": ["ko'61", "ko'62"]}},
            "braid": _fake_braid(),
        },
    }

    pair = news_pipeline.sft_braid_alignment(tok, 7)

    assert pair is not None
    assert pair["id"] == "news:braid-align:KO:7"
    assert "4-component alignment score" in pair["instruction"]
    assert "tongue_matrix" in pair["output"]
    assert "0.507293" in pair["output"]


def test_run_item_appends_braid_pair(monkeypatch):
    monkeypatch.setattr(news_pipeline, "_BRAID_AVAILABLE", True)
    monkeypatch.setattr(news_pipeline, "_braid_score", lambda payload, tongue: _fake_braid())
    monkeypatch.setattr(news_pipeline, "LIBOQS_AVAILABLE", False)
    monkeypatch.setattr(news_pipeline, "CRYPTOGRAPHY_AVAILABLE", False)
    monkeypatch.setattr(news_pipeline, "CRYPTO_TIER", "hmac-only")

    record, pairs = news_pipeline.run_item(_sample_item(), 3)

    assert record["stages"]["tokenized"]["all_roundtrip_ok"] is True
    assert record["crypto_tier"] == "hmac-only"
    assert len(pairs) == 8
    assert any(pair["id"] == "news:braid-align:KO:3" for pair in pairs)


def test_to_chatml_preserves_instruction_input_and_output():
    pair = {
        "id": "news:braid-align:KO:3",
        "instruction": "Explain the braid score.",
        "input": '{"source":"hn"}',
        "output": '{"aligned_score":1.0}',
        "pipeline": "news-pipeline",
        "version": "v1",
    }

    record = pipeline_to_hf.to_chatml(pair)

    assert record["id"] == pair["id"]
    assert record["pipeline"] == "news-pipeline"
    assert record["conversations"][0]["role"] == "system"
    assert record["conversations"][1]["content"] == 'Explain the braid score.\n\n{"source":"hn"}'
    assert record["conversations"][2]["content"] == '{"aligned_score":1.0}'


def test_main_writes_summary_with_braid_flag(monkeypatch, tmp_path):
    feed_path = tmp_path / "feed.json"
    summary_path = tmp_path / "research-pipeline.json"
    records_dir = tmp_path / "records"
    sft_dir = tmp_path / "sft"
    records_dir.mkdir()
    sft_dir.mkdir()
    feed_path.write_text(json.dumps({"generated": "2026-04-17T00:00:00Z", "items": [_sample_item()]}), encoding="utf-8")

    monkeypatch.setattr(news_pipeline, "_BRAID_AVAILABLE", True)
    monkeypatch.setattr(news_pipeline, "_braid_score", lambda payload, tongue: _fake_braid())
    monkeypatch.setattr(news_pipeline, "LIBOQS_AVAILABLE", False)
    monkeypatch.setattr(news_pipeline, "CRYPTOGRAPHY_AVAILABLE", False)
    monkeypatch.setattr(news_pipeline, "CRYPTO_TIER", "hmac-only")
    monkeypatch.setattr(news_pipeline, "FEED_PATH", feed_path)
    monkeypatch.setattr(news_pipeline, "SUMMARY_PATH", summary_path)
    monkeypatch.setattr(news_pipeline, "RECORDS_DIR", records_dir)
    monkeypatch.setattr(news_pipeline, "SFT_DIR", sft_dir)

    news_pipeline.main()

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["items_processed"] == 1
    assert summary["sft_pairs_generated"] == 8
    assert summary["crypto_tier"] == "hmac-only"
    assert summary["braid_available"] is True
