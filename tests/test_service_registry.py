"""Tests for the Service Registry — master connector hub."""

from __future__ import annotations

import json
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.service_registry import (
    ServiceRegistry,
    ServiceInfo,
    ServiceStatus,
    ServiceCategory,
    EmailConnector,
    EmailAccount,
    GoogleBusinessConnector,
    FigmaConnector,
)


class TestServiceRegistry(unittest.TestCase):
    """Test the master service registry."""

    def setUp(self):
        self.registry = ServiceRegistry()

    def test_all_services_registered(self):
        services = self.registry.list_services()
        self.assertGreater(len(services), 10)

    def test_list_by_category(self):
        emails = self.registry.list_services(ServiceCategory.EMAIL)
        self.assertEqual(len(emails), 4)  # 3 Gmail + 1 Proton

    def test_get_service(self):
        svc = self.registry.get("github")
        self.assertIsNotNone(svc)
        self.assertEqual(svc.provider, "GitHub")

    def test_get_missing_service(self):
        self.assertIsNone(self.registry.get("nonexistent"))

    def test_status_report(self):
        report = self.registry.status_report()
        self.assertIn("Service Registry", report)
        self.assertIn("gmail", report.lower())
        self.assertIn("shopify", report.lower())

    def test_env_template(self):
        template = self.registry.env_template()
        self.assertIn("GMAIL_APP_PASSWORD_1", template)
        self.assertIn("SHOPIFY_ADMIN_API_TOKEN", template)
        self.assertIn("FIGMA_ACCESS_TOKEN", template)

    @patch.dict(os.environ, {"HF_TOKEN": "test", "GITHUB_TOKEN": "test"})
    def test_refresh_status_detects_configured(self):
        registry = ServiceRegistry()
        hf = registry.get("huggingface")
        self.assertEqual(hf.status, ServiceStatus.CONFIGURED)

    def test_services_have_capabilities(self):
        for svc in self.registry.list_services():
            if svc.name not in ("arxiv",):  # arxiv has no creds
                self.assertTrue(
                    len(svc.capabilities) > 0 or len(svc.credentials_env) == 0,
                    f"{svc.name} has no capabilities",
                )

    def test_categories_are_complete(self):
        categories = {svc.category for svc in self.registry.list_services()}
        self.assertIn(ServiceCategory.EMAIL, categories)
        self.assertIn(ServiceCategory.COMMERCE, categories)
        self.assertIn(ServiceCategory.CLOUD, categories)
        self.assertIn(ServiceCategory.ACADEMIC, categories)

    def test_list_by_status_missing(self):
        missing = self.registry.list_by_status(ServiceStatus.MISSING)
        # Most services will be missing in test env
        self.assertIsInstance(missing, list)


class TestEmailConnector(unittest.TestCase):
    """Test email connector."""

    def setUp(self):
        self.connector = EmailConnector()

    def test_add_gmail(self):
        self.connector.add_gmail("test", "test@gmail.com", "TEST_PWD")
        self.assertIn("test", self.connector.list_accounts())

    def test_add_proton(self):
        self.connector.add_proton("proton", "test@proton.me", "PROTON_PWD")
        accounts = self.connector.list_accounts()
        self.assertIn("proton", accounts)

    def test_gmail_provider_config(self):
        cfg = EmailConnector.PROVIDERS["gmail"]
        self.assertEqual(cfg["imap_host"], "imap.gmail.com")
        self.assertEqual(cfg["smtp_host"], "smtp.gmail.com")
        self.assertEqual(cfg["imap_port"], 993)

    def test_proton_provider_config(self):
        cfg = EmailConnector.PROVIDERS["proton"]
        self.assertEqual(cfg["imap_host"], "127.0.0.1")
        self.assertEqual(cfg["imap_port"], 1143)
        self.assertFalse(cfg["use_ssl"])

    def test_check_connection_no_account(self):
        ok, msg = self.connector.check_connection("nonexistent")
        self.assertFalse(ok)
        self.assertIn("not registered", msg)

    def test_check_connection_no_password(self):
        self.connector.add_gmail("test", "test@gmail.com", "NONEXISTENT_ENV_VAR")
        ok, msg = self.connector.check_connection("test")
        self.assertFalse(ok)
        self.assertIn("not set", msg)

    def test_send_email_no_account(self):
        ok, msg = self.connector.send_email("nonexistent", "to@x.com", "S", "B")
        self.assertFalse(ok)

    def test_send_email_no_password(self):
        self.connector.add_gmail("test", "t@g.com", "MISSING_VAR_XYZ")
        ok, msg = self.connector.send_email("test", "to@x.com", "S", "B")
        self.assertFalse(ok)

    def test_multiple_accounts(self):
        self.connector.add_gmail("g1", "a@g.com", "P1")
        self.connector.add_gmail("g2", "b@g.com", "P2")
        self.connector.add_proton("p1", "c@p.me", "P3")
        self.assertEqual(len(self.connector.list_accounts()), 3)

    def test_outlook_provider_exists(self):
        self.assertIn("outlook", EmailConnector.PROVIDERS)


class TestGoogleBusinessConnector(unittest.TestCase):
    """Test Google Business connector."""

    def test_no_token(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("scripts.service_registry.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")
                connector = GoogleBusinessConnector(access_token="")
                ok, msg = connector.health_check()
                self.assertFalse(ok)

    @patch("scripts.service_registry.urllib.request.urlopen")
    def test_list_accounts(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "accounts": [{"name": "accounts/123", "accountName": "Test Biz"}]
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        connector = GoogleBusinessConnector(access_token="test-token")
        accounts = connector.list_accounts()
        self.assertIsNotNone(accounts)
        self.assertEqual(len(accounts), 1)


class TestFigmaConnector(unittest.TestCase):
    """Test Figma connector."""

    def test_no_token(self):
        connector = FigmaConnector(token="")
        ok, msg = connector.health_check()
        self.assertFalse(ok)

    def test_no_token_returns_none(self):
        connector = FigmaConnector(token="")
        self.assertIsNone(connector.get_file("abc"))

    @patch("scripts.service_registry.urllib.request.urlopen")
    def test_health_check_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "id": "12345",
            "handle": "testuser",
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        connector = FigmaConnector(token="test-token")
        ok, msg = connector.health_check()
        self.assertTrue(ok)
        self.assertIn("testuser", msg)


class TestEmailAccount(unittest.TestCase):
    """Test EmailAccount dataclass."""

    def test_creation(self):
        acc = EmailAccount(
            name="test",
            address="test@example.com",
            imap_host="imap.example.com",
            imap_port=993,
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="test@example.com",
            password_env="TEST_PWD",
        )
        self.assertEqual(acc.name, "test")
        self.assertTrue(acc.use_ssl)  # Default

    def test_proton_no_ssl(self):
        acc = EmailAccount(
            name="proton",
            address="test@proton.me",
            imap_host="127.0.0.1",
            imap_port=1143,
            smtp_host="127.0.0.1",
            smtp_port=1025,
            username="test@proton.me",
            password_env="PROTON_PWD",
            use_ssl=False,
        )
        self.assertFalse(acc.use_ssl)


class TestServiceInfo(unittest.TestCase):
    """Test ServiceInfo dataclass."""

    def test_defaults(self):
        info = ServiceInfo(name="test", category=ServiceCategory.EMAIL)
        self.assertEqual(info.status, ServiceStatus.MISSING)
        self.assertEqual(info.capabilities, [])


if __name__ == "__main__":
    unittest.main()
