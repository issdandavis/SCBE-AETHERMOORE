"""Tests for Polly commerce + auto-training capture."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.api.polly_commerce import (
    PRODUCT_CATALOG,
    append_training_record,
    classify_intent,
    render_buy_reply,
    render_custom_reply,
    render_membership_reply,
    train_corpus_dir,
)

# ---------------------------------------------------------------------------
# Catalog sanity
# ---------------------------------------------------------------------------


def test_catalog_is_nonempty_and_has_real_stripe_links() -> None:
    assert len(PRODUCT_CATALOG) >= 2
    for product in PRODUCT_CATALOG:
        assert product.sku
        assert product.name
        assert product.price_label
        assert product.short
        assert product.checkout_url.startswith(
            ("https://buy.stripe.com/", "https://ko-fi.com/")
        )


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "message,expected_intent",
    [
        ("How much is the toolkit?", "buy"),
        ("I want to buy the training vault", "buy"),
        ("Can I purchase the SCBE governance toolkit?", "buy"),
        ("Add to cart please", "buy"),
        ("Sign me up for the toolkit", "buy"),
        ("I want to buy service credits", "buy"),
        ("hosted routing credits", "buy"),
        ("toolkit", "buy"),
        ("training vault", "buy"),
        ("buy a coffee", "buy"),  # tip jar keyword
        ("I need something custom for my team", "custom"),
        ("Can you do a custom build for my company?", "custom"),
        ("hire you for an audit", "custom"),
        ("I want to research recent prompt-injection papers", "research"),
        ("look up the latest sources on AI safety", "research"),
        ("how do I become a member?", "membership"),
        ("can I sponsor the project?", "membership"),
        ("subscribe to your newsletter", "membership"),
        ("what is the harmonic wall formula?", "general"),
        ("", "general"),
    ],
)
def test_classify_intent_basic(message: str, expected_intent: str) -> None:
    intent = classify_intent(message)
    assert intent.name == expected_intent


def test_classify_intent_buy_resolves_specific_product() -> None:
    intent = classify_intent("How much is the AI Governance Toolkit?")
    assert intent.name == "buy"
    assert intent.product is not None
    assert intent.product.sku == "ai-governance-toolkit"


def test_classify_intent_buy_resolves_training_vault() -> None:
    intent = classify_intent("I want to purchase the training vault")
    assert intent.name == "buy"
    assert intent.product is not None
    assert intent.product.sku == "ai-security-training-vault"


def test_classify_intent_buy_resolves_service_credits() -> None:
    intent = classify_intent("Can I buy service credits for cloud models?")
    assert intent.name == "buy"
    assert intent.product is not None
    assert intent.product.sku == "scbe-service-credits"


def test_classify_intent_buy_without_product_keyword() -> None:
    intent = classify_intent("How much does it cost?")
    assert intent.name == "buy"
    assert intent.product is None
    assert intent.confidence < 0.8  # lower confidence without specific product


def test_classify_intent_custom_takes_precedence_over_research() -> None:
    """Custom-build language wins when both 'custom' and 'research' tokens appear."""
    intent = classify_intent("I want a custom audit and some research on top")
    assert intent.name == "custom"


# ---------------------------------------------------------------------------
# Reply rendering
# ---------------------------------------------------------------------------


def test_render_buy_reply_with_product_returns_link() -> None:
    product = PRODUCT_CATALOG[0]
    text, actions = render_buy_reply(product)
    assert product.name in text
    assert product.checkout_url in text
    assert any(a["url"] == product.checkout_url for a in actions)


def test_render_buy_reply_without_product_lists_full_catalog() -> None:
    text, actions = render_buy_reply(None)
    assert len(actions) >= len(PRODUCT_CATALOG)
    for product in PRODUCT_CATALOG:
        assert product.name in text


def test_render_custom_reply_includes_mailto_with_user_context() -> None:
    text, actions = render_custom_reply(
        "I need a governance overlay for our finance LLM"
    )
    mailto_action = next((a for a in actions if a["url"].startswith("mailto:")), None)
    assert mailto_action is not None
    # mailto: URLs treat @ as a safe character; urllib.parse.quote leaves it as-is.
    assert "issdandavis7795@gmail.com" in mailto_action["url"]
    assert "finance" in mailto_action["url"].lower() or "finance" in text.lower()


def test_render_membership_reply_returns_kofi_link() -> None:
    text, actions = render_membership_reply()
    kofi = next((a for a in actions if "ko-fi.com" in a["url"]), None)
    credits = next((a for a in actions if "service-credits" in a["url"]), None)
    assert credits is not None
    assert kofi is not None
    assert "Ko-fi" in text or "ko-fi" in text.lower()
    assert "2-5%" in text


# ---------------------------------------------------------------------------
# Auto-training capture
# ---------------------------------------------------------------------------


def test_append_training_record_writes_jsonl_with_consent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("POLLY_TRAIN_CORPUS_DIR", str(tmp_path))
    shard = append_training_record(
        consent=True,
        user_message="hi",
        assistant_reply="hello",
        intent="general",
    )
    assert shard is not None
    assert shard.exists()
    line = shard.read_text(encoding="utf-8").strip()
    record = json.loads(line)
    assert record["user"] == "hi"
    assert record["assistant"] == "hello"
    assert record["intent"] == "general"
    assert "ts" in record


def test_append_training_record_skips_without_consent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("POLLY_TRAIN_CORPUS_DIR", str(tmp_path))
    shard = append_training_record(
        consent=False,
        user_message="hi",
        assistant_reply="hello",
        intent="general",
    )
    assert shard is None
    assert list(tmp_path.glob("*.jsonl")) == []


def test_append_training_record_appends_multiple_turns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("POLLY_TRAIN_CORPUS_DIR", str(tmp_path))
    for i in range(3):
        append_training_record(
            consent=True,
            user_message=f"user-{i}",
            assistant_reply=f"reply-{i}",
            intent="general",
            session_id="session-1",
        )
    shards = list(tmp_path.glob("*.jsonl"))
    assert len(shards) == 1
    lines = shards[0].read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 3
    for i, line in enumerate(lines):
        record = json.loads(line)
        assert record["user"] == f"user-{i}"
        assert record["session_id"] == "session-1"


def test_append_training_record_records_feedback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("POLLY_TRAIN_CORPUS_DIR", str(tmp_path))
    shard = append_training_record(
        consent=True,
        user_message="useful?",
        assistant_reply="yes",
        intent="general",
        feedback="up",
    )
    assert shard is not None
    record = json.loads(shard.read_text(encoding="utf-8").strip())
    assert record["feedback"] == "up"


def test_append_training_record_truncates_long_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("POLLY_TRAIN_CORPUS_DIR", str(tmp_path))
    shard = append_training_record(
        consent=True,
        user_message="x" * 10_000,
        assistant_reply="y" * 20_000,
        intent="general",
    )
    assert shard is not None
    record = json.loads(shard.read_text(encoding="utf-8").strip())
    assert len(record["user"]) <= 4096
    assert len(record["assistant"]) <= 8192


def test_train_corpus_dir_respects_env_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("POLLY_TRAIN_CORPUS_DIR", str(tmp_path))
    assert train_corpus_dir() == tmp_path
