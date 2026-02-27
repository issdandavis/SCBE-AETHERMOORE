"""
@file test_browser_extensions.py
@module tests/test_browser_extensions
@layer Layer 12, Layer 13
@description Tests for headless browser productivity extensions:
    DocHandler, ConnectorDispatcher, and headless_productivity CLI.

These tests run WITHOUT Playwright (no browser needed) — they verify
document creation, connector dispatch logic, and governance integration.

pytest markers: unit, integration, agentic
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure src/ is importable
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT))


# ── DocHandler Tests ────────────────────────────────────────────────────


@pytest.mark.unit
class TestDocHandler:
    """Tests for document creation and local save."""

    def test_extract_to_doc_basic(self):
        from browser.extensions.doc_handler import DocHandler

        handler = DocHandler(output_dir=tempfile.mkdtemp())
        doc = handler.extract_to_doc(
            title="Test Document",
            content="Hello world content",
            source_urls=["https://example.com"],
        )
        assert doc.title == "Test Document"
        assert doc.content == "Hello world content"
        assert doc.source_urls == ["https://example.com"]
        assert len(doc.doc_id) == 16

    def test_merge_extractions(self):
        from browser.extensions.doc_handler import DocHandler

        handler = DocHandler(output_dir=tempfile.mkdtemp())
        extractions = [
            {"url": "https://a.com", "title": "Page A", "text": "Content A", "links": ["https://link1.com"]},
            {"url": "https://b.com", "title": "Page B", "text": "Content B", "links": ["https://link2.com"]},
        ]
        doc = handler.merge_extractions(title="Merged", extractions=extractions)
        assert "Content A" in doc.content
        assert "Content B" in doc.content
        assert len(doc.source_urls) == 2
        assert doc.metadata["extraction_count"] == 2

    def test_save_markdown(self):
        from browser.extensions.doc_handler import DocHandler

        with tempfile.TemporaryDirectory() as tmp:
            handler = DocHandler(output_dir=tmp)
            doc = handler.extract_to_doc(
                title="MD Test",
                content="Test content here",
                source_urls=["https://src.com"],
            )
            path = handler.save_markdown(doc)
            assert Path(path).exists()
            text = Path(path).read_text()
            assert "# MD Test" in text
            assert "Test content here" in text
            assert "https://src.com" in text

    def test_save_plain_text(self):
        from browser.extensions.doc_handler import DocHandler

        with tempfile.TemporaryDirectory() as tmp:
            handler = DocHandler(output_dir=tmp)
            doc = handler.extract_to_doc(title="TXT Test", content="Plain text body")
            path = handler.save_plain_text(doc)
            assert Path(path).exists()
            text = Path(path).read_text()
            assert "TXT Test" in text
            assert "Plain text body" in text

    def test_save_json(self):
        from browser.extensions.doc_handler import DocHandler

        with tempfile.TemporaryDirectory() as tmp:
            handler = DocHandler(output_dir=tmp)
            doc = handler.extract_to_doc(
                title="JSON Test",
                content="JSON body",
                metadata={"key": "value"},
            )
            path = handler.save_json(doc)
            assert Path(path).exists()
            data = json.loads(Path(path).read_text())
            assert data["title"] == "JSON Test"
            assert data["content"] == "JSON body"
            assert data["metadata"]["key"] == "value"

    def test_save_docx_fallback_to_markdown(self):
        """If python-docx is not installed, save_docx should fall back to markdown."""
        from browser.extensions.doc_handler import DocHandler

        with tempfile.TemporaryDirectory() as tmp:
            handler = DocHandler(output_dir=tmp)
            doc = handler.extract_to_doc(title="DOCX Fallback", content="Content")
            # This will either create a real DOCX or fall back to MD
            path = handler.save_docx(doc)
            assert Path(path).exists()

    def test_to_markdown_includes_sources(self):
        from browser.extensions.doc_handler import ExtractedDocument

        doc = ExtractedDocument(
            title="Source Test",
            content="Body text",
            source_urls=["https://a.com", "https://b.com"],
            links=["https://link.com"],
        )
        md = doc.to_markdown()
        assert "## Sources" in md
        assert "https://a.com" in md
        assert "## Related Links" in md

    def test_to_plain_text(self):
        from browser.extensions.doc_handler import ExtractedDocument

        doc = ExtractedDocument(title="Plain", content="Body")
        txt = doc.to_plain_text()
        assert txt.startswith("Plain")
        assert "Body" in txt

    def test_doc_id_deterministic(self):
        from browser.extensions.doc_handler import ExtractedDocument

        doc1 = ExtractedDocument(title="Same", content="Same", created_at="2026-01-01T00:00:00")
        doc2 = ExtractedDocument(title="Same", content="Same", created_at="2026-01-01T00:00:00")
        assert doc1.doc_id == doc2.doc_id

    def test_doc_id_unique_for_different_content(self):
        from browser.extensions.doc_handler import ExtractedDocument

        doc1 = ExtractedDocument(title="A", content="Content A")
        doc2 = ExtractedDocument(title="B", content="Content B")
        assert doc1.doc_id != doc2.doc_id


# ── ConnectorDispatcher Tests ───────────────────────────────────────────


@pytest.mark.unit
class TestConnectorDispatcher:
    """Tests for connector registration and dispatch logic."""

    def test_register_and_list(self):
        from browser.extensions.connector_dispatch import ConnectorConfig, ConnectorDispatcher

        with tempfile.TemporaryDirectory() as tmp:
            dispatcher = ConnectorDispatcher(audit_dir=tmp)
            config = ConnectorConfig(
                connector_id="test-conn",
                kind="zapier",
                endpoint_url="https://hooks.zapier.com/test",
            )
            dispatcher.register(config)
            listed = dispatcher.list_connectors()
            assert len(listed) == 1
            assert listed[0]["connector_id"] == "test-conn"
            assert listed[0]["kind"] == "zapier"

    def test_register_from_template(self):
        from browser.extensions.connector_dispatch import ConnectorDispatcher

        with tempfile.TemporaryDirectory() as tmp:
            dispatcher = ConnectorDispatcher(audit_dir=tmp)
            template = {
                "template_id": "zapier_catch_hook",
                "kind": "zapier",
                "recommended_fields": {
                    "endpoint_url": "https://hooks.zapier.com/placeholder",
                    "auth_type": "none",
                    "payload_mode": "scbe_step",
                },
            }
            config = dispatcher.register_from_template(
                "my-zapier",
                template,
                overrides={"endpoint_url": "https://hooks.zapier.com/real"},
            )
            assert config.connector_id == "my-zapier"
            assert config.endpoint_url == "https://hooks.zapier.com/real"
            assert config.kind == "zapier"

    def test_unregister(self):
        from browser.extensions.connector_dispatch import ConnectorConfig, ConnectorDispatcher

        with tempfile.TemporaryDirectory() as tmp:
            dispatcher = ConnectorDispatcher(audit_dir=tmp)
            config = ConnectorConfig(
                connector_id="remove-me",
                kind="n8n",
                endpoint_url="https://n8n.example.com/webhook/test",
            )
            dispatcher.register(config)
            assert len(dispatcher.list_connectors()) == 1
            assert dispatcher.unregister("remove-me") is True
            assert len(dispatcher.list_connectors()) == 0
            assert dispatcher.unregister("nonexistent") is False

    def test_dispatch_unregistered_connector(self):
        from browser.extensions.connector_dispatch import ConnectorDispatcher

        with tempfile.TemporaryDirectory() as tmp:
            dispatcher = ConnectorDispatcher(audit_dir=tmp)
            result = dispatcher.dispatch("nonexistent", {"data": "test"})
            assert result.success is False
            assert "not registered" in result.error

    def test_dispatch_disabled_connector(self):
        from browser.extensions.connector_dispatch import ConnectorConfig, ConnectorDispatcher

        with tempfile.TemporaryDirectory() as tmp:
            dispatcher = ConnectorDispatcher(audit_dir=tmp)
            config = ConnectorConfig(
                connector_id="disabled",
                kind="generic_webhook",
                endpoint_url="https://example.com/webhook",
                enabled=False,
            )
            dispatcher.register(config)
            result = dispatcher.dispatch("disabled", {"data": "test"})
            assert result.success is False
            assert "disabled" in result.error

    def test_build_body_scbe_step(self):
        from browser.extensions.connector_dispatch import ConnectorConfig, ConnectorDispatcher

        with tempfile.TemporaryDirectory() as tmp:
            dispatcher = ConnectorDispatcher(audit_dir=tmp)
            config = ConnectorConfig(
                connector_id="test",
                kind="zapier",
                endpoint_url="https://hooks.zapier.com/test",
                payload_mode="scbe_step",
            )
            body = dispatcher._build_body(config, {"action": "notify"})
            assert body["source"] == "scbe-aetherbrowse"
            assert body["payload"]["action"] == "notify"
            assert "timestamp_utc" in body

    def test_build_body_shopify(self):
        from browser.extensions.connector_dispatch import ConnectorConfig, ConnectorDispatcher

        with tempfile.TemporaryDirectory() as tmp:
            dispatcher = ConnectorDispatcher(audit_dir=tmp)
            config = ConnectorConfig(
                connector_id="shopify",
                kind="shopify",
                endpoint_url="https://shop.myshopify.com/admin/api/graphql.json",
                payload_mode="shopify_graphql_read",
            )
            body = dispatcher._build_body(config, {"query": "{ orders(first: 5) { edges { node { id } } } }"})
            assert "query" in body
            assert "variables" in body

    def test_build_body_raw(self):
        from browser.extensions.connector_dispatch import ConnectorConfig, ConnectorDispatcher

        with tempfile.TemporaryDirectory() as tmp:
            dispatcher = ConnectorDispatcher(audit_dir=tmp)
            config = ConnectorConfig(
                connector_id="raw",
                kind="generic_webhook",
                endpoint_url="https://example.com",
                payload_mode="raw",
            )
            payload = {"custom": "data", "nested": {"key": True}}
            body = dispatcher._build_body(config, payload)
            assert body == payload

    def test_build_headers_bearer(self):
        from browser.extensions.connector_dispatch import ConnectorConfig, ConnectorDispatcher

        with tempfile.TemporaryDirectory() as tmp:
            dispatcher = ConnectorDispatcher(audit_dir=tmp)
            config = ConnectorConfig(
                connector_id="test",
                kind="generic_webhook",
                endpoint_url="https://example.com",
                auth_type="bearer",
                auth_token="my-secret-token",
            )
            headers = dispatcher._build_headers(config)
            assert headers["Authorization"] == "Bearer my-secret-token"

    def test_build_headers_custom(self):
        from browser.extensions.connector_dispatch import ConnectorConfig, ConnectorDispatcher

        with tempfile.TemporaryDirectory() as tmp:
            dispatcher = ConnectorDispatcher(audit_dir=tmp)
            config = ConnectorConfig(
                connector_id="n8n",
                kind="n8n",
                endpoint_url="https://n8n.example.com",
                auth_type="header",
                auth_header_name="x-n8n-key",
                auth_token="secret123",
            )
            headers = dispatcher._build_headers(config)
            assert headers["x-n8n-key"] == "secret123"

    def test_audit_log(self):
        from browser.extensions.connector_dispatch import ConnectorConfig, ConnectorDispatcher

        with tempfile.TemporaryDirectory() as tmp:
            dispatcher = ConnectorDispatcher(audit_dir=tmp, max_retries=0)
            config = ConnectorConfig(
                connector_id="audit-test",
                kind="generic_webhook",
                endpoint_url="https://httpbin.org/status/418",
            )
            dispatcher.register(config)
            # This will fail (no real server), but should still audit
            dispatcher.dispatch("audit-test", {"test": True})
            log = dispatcher.get_audit_log()
            assert len(log) == 1
            assert log[0]["connector_id"] == "audit-test"
            # Verify audit file was written
            files = list(Path(tmp).glob("*.json"))
            assert len(files) == 1


# ── Governance Integration Tests ────────────────────────────────────────


@pytest.mark.unit
class TestGovernanceIntegration:
    """Test that governance evaluation works correctly for browser extensions."""

    def test_trusted_domain_allows(self):
        from browser.persistent_limb import GovernanceDecision, evaluate_browser_action

        result = evaluate_browser_action("CA", "https://github.com/test", "navigate")
        assert result.decision == GovernanceDecision.ALLOW

    def test_blocked_domain_denies(self):
        from browser.persistent_limb import GovernanceDecision, evaluate_browser_action

        result = evaluate_browser_action("CA", "https://malware.com/bad", "navigate")
        assert result.decision == GovernanceDecision.DENY

    def test_unknown_domain_low_action_allows(self):
        from browser.persistent_limb import GovernanceDecision, evaluate_browser_action

        # Unknown domain (0.5 risk) + navigate (0.10 action) + CA tongue
        # Composite: 0.5*0.35 + 0.10*0.30 + (4.236/20)*0.15 = ~0.237 → ALLOW
        result = evaluate_browser_action("CA", "https://random-unknown-site.xyz", "navigate")
        assert result.decision == GovernanceDecision.ALLOW
        assert result.domain_decision == "QUARANTINE"  # domain itself is quarantine-level

    def test_run_js_high_risk(self):
        from browser.persistent_limb import evaluate_browser_action

        # DR tongue (11.09 weight) + run_js (0.80 action) + unknown domain (0.50)
        # Composite: 0.175 + 0.24 + 0.083 + 0 = ~0.498 → QUARANTINE
        result = evaluate_browser_action("DR", "https://random-site.com", "run_js")
        assert result.risk_score > 0.45  # high risk range
        assert result.harmonic_cost > 5.0  # exponentially expensive

    def test_harmonic_cost_increases_with_risk(self):
        from browser.persistent_limb import evaluate_browser_action

        safe = evaluate_browser_action("KO", "https://github.com", "navigate")
        risky = evaluate_browser_action("DR", "https://unknown-site.com", "run_js")
        assert risky.harmonic_cost > safe.harmonic_cost

    def test_session_risk_accumulation(self):
        from browser.persistent_limb import GovernanceDecision, PersistentBrowserLimb

        limb = PersistentBrowserLimb.__new__(PersistentBrowserLimb)
        limb.session_id = "test"
        limb.governance_enabled = True
        limb._session_risk = 0.0
        limb._audit_log = []

        # Trigger a DENY to increase session risk
        limb._gate("CA", "https://malware.com", "navigate")
        assert limb._session_risk > 0.0

    def test_allow_decays_session_risk(self):
        from browser.persistent_limb import PersistentBrowserLimb

        limb = PersistentBrowserLimb.__new__(PersistentBrowserLimb)
        limb.session_id = "test"
        limb.governance_enabled = True
        limb._session_risk = 0.10
        limb._audit_log = []

        # ALLOW on trusted domain should decay session risk
        limb._gate("KO", "https://github.com", "navigate")
        assert limb._session_risk < 0.10


# ── CLI Integration Tests ──────────────────────────────────────────────


@pytest.mark.unit
class TestCLIParsing:
    """Test that CLI argument parsing works correctly."""

    def test_research_parser(self):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from headless_productivity import build_parser

        parser = build_parser()
        args = parser.parse_args([
            "research",
            "--query", "AI safety",
            "--max-urls", "3",
            "--format", "markdown",
        ])
        assert args.command == "research"
        assert args.query == "AI safety"
        assert args.max_urls == 3
        assert args.format == "markdown"

    def test_extract_parser(self):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from headless_productivity import build_parser

        parser = build_parser()
        args = parser.parse_args([
            "extract",
            "--urls", "https://a.com", "https://b.com",
            "--format", "docx",
        ])
        assert args.command == "extract"
        assert args.urls == ["https://a.com", "https://b.com"]
        assert args.format == "docx"

    def test_dispatch_parser(self):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from headless_productivity import build_parser

        parser = build_parser()
        args = parser.parse_args([
            "dispatch",
            "--connector", "my-zap",
            "--endpoint", "https://hooks.zapier.com/test",
            "--payload", '{"key": "value"}',
        ])
        assert args.command == "dispatch"
        assert args.connector == "my-zap"
        assert json.loads(args.payload) == {"key": "value"}

    def test_push_parser(self):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from headless_productivity import build_parser

        parser = build_parser()
        args = parser.parse_args([
            "push",
            "--file", "test.md",
            "--repo", "owner/repo",
            "--path", "docs/test.md",
            "--branch", "develop",
        ])
        assert args.command == "push"
        assert args.repo == "owner/repo"
        assert args.branch == "develop"

    def test_workflow_parser(self):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from headless_productivity import build_parser

        parser = build_parser()
        args = parser.parse_args([
            "workflow",
            "--workflow-file", "examples/productivity_workflow.json",
        ])
        assert args.command == "workflow"

    def test_interactive_parser(self):
        sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
        from headless_productivity import build_parser

        parser = build_parser()
        args = parser.parse_args([
            "interactive",
            "--session", "my-session",
            "--tongues", "KO,CA",
            "--no-governance",
        ])
        assert args.command == "interactive"
        assert args.session == "my-session"
        assert args.tongues == "KO,CA"
        assert args.no_governance is True
