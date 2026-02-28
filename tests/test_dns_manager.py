"""Tests for the DNS Manager (Google Cloud DNS + Cloudflare)."""

from __future__ import annotations

import json
import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.dns_manager import (
    DNSManager,
    DNSRecord,
    ZoneInfo,
    DomainStatus,
    GoogleCloudDNS,
    CloudflareDNS,
)


# ==========================================================================
# Google Cloud DNS Tests
# ==========================================================================


class TestGoogleCloudDNS(unittest.TestCase):
    """Test Google Cloud DNS provider."""

    def setUp(self):
        self.provider = GoogleCloudDNS(project="test-project")

    @patch("scripts.dns_manager.subprocess.run")
    def test_list_zones(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([
                {
                    "name": "aethermoorgames-com",
                    "dnsName": "aethermoorgames.com.",
                    "nameServers": ["ns1.google.com", "ns2.google.com"],
                }
            ]),
            stderr="",
        )
        zones = self.provider.list_zones()
        self.assertEqual(len(zones), 1)
        self.assertEqual(zones[0].domain, "aethermoorgames.com")
        self.assertEqual(zones[0].zone_name, "aethermoorgames-com")

    @patch("scripts.dns_manager.subprocess.run")
    def test_list_records(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([
                {
                    "type": "A",
                    "name": "api.aethermoorgames.com.",
                    "ttl": 300,
                    "rrdatas": ["34.134.99.90"],
                },
                {
                    "type": "CNAME",
                    "name": "www.aethermoorgames.com.",
                    "ttl": 300,
                    "rrdatas": ["issdandavis.github.io."],
                },
            ]),
            stderr="",
        )
        records = self.provider.list_records("aethermoorgames-com")
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].record_type, "A")
        self.assertEqual(records[0].value, "34.134.99.90")
        self.assertEqual(records[1].record_type, "CNAME")

    @patch("scripts.dns_manager.subprocess.run")
    def test_add_record(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Created", stderr="")
        record = DNSRecord("A", "api.aethermoorgames.com", "34.134.99.90", ttl=300)
        ok = self.provider.add_record("aethermoorgames-com", record)
        self.assertTrue(ok)

    @patch("scripts.dns_manager.subprocess.run")
    def test_add_cname_appends_dot(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Created", stderr="")
        record = DNSRecord("CNAME", "www.example.com", "issdandavis.github.io")
        self.provider.add_record("example-com", record)
        # Verify the command was called with trailing dot
        call_args = mock_run.call_args[0][0]
        self.assertTrue(any("issdandavis.github.io." in str(a) for a in call_args))

    @patch("scripts.dns_manager.subprocess.run")
    def test_gcloud_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError("gcloud not found")
        zones = self.provider.list_zones()
        self.assertEqual(zones, [])

    @patch("scripts.dns_manager.subprocess.run")
    def test_gcloud_timeout(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd="gcloud", timeout=30)
        zones = self.provider.list_zones()
        self.assertEqual(zones, [])

    @patch("scripts.dns_manager.subprocess.run")
    def test_health_check_healthy(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
        self.assertTrue(self.provider.health_check())

    @patch("scripts.dns_manager.subprocess.run")
    def test_health_check_unhealthy(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        self.assertFalse(self.provider.health_check())


# ==========================================================================
# Cloudflare DNS Tests
# ==========================================================================


class TestCloudflareDNS(unittest.TestCase):
    """Test Cloudflare DNS provider."""

    def setUp(self):
        self.provider = CloudflareDNS(
            api_token="test-token",
            zone_id="test-zone-id",
        )

    @patch("scripts.dns_manager.urllib.request.urlopen")
    def test_list_zones(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "success": True,
            "result": [
                {
                    "id": "zone123",
                    "name": "aethermoorgames.com",
                    "name_servers": ["ns1.cloudflare.com"],
                }
            ],
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        zones = self.provider.list_zones()
        self.assertEqual(len(zones), 1)
        self.assertEqual(zones[0].domain, "aethermoorgames.com")

    @patch("scripts.dns_manager.urllib.request.urlopen")
    def test_list_records(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "success": True,
            "result": [
                {
                    "id": "rec1",
                    "type": "A",
                    "name": "api.aethermoorgames.com",
                    "content": "34.134.99.90",
                    "ttl": 300,
                    "proxied": False,
                },
            ],
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        records = self.provider.list_records("test-zone-id")
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].value, "34.134.99.90")

    @patch("scripts.dns_manager.urllib.request.urlopen")
    def test_add_record(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "success": True,
            "result": {"id": "new-rec"},
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        record = DNSRecord("A", "api.example.com", "1.2.3.4")
        ok = self.provider.add_record("zone123", record)
        self.assertTrue(ok)

    def test_no_token_health_check(self):
        provider = CloudflareDNS(api_token="", zone_id="")
        self.assertFalse(provider.health_check())


# ==========================================================================
# DNS Manager Tests
# ==========================================================================


class TestDNSManager(unittest.TestCase):
    """Test the unified DNS Manager."""

    def _make_manager(self, zones=None, records=None):
        """Create a manager with mocked provider."""
        mgr = DNSManager.__new__(DNSManager)
        mgr._provider_name = "mock"
        mock_provider = MagicMock()
        mock_provider.list_zones.return_value = zones or []
        mock_provider.list_records.return_value = records or []
        mock_provider.add_record.return_value = True
        mock_provider.create_zone.return_value = ZoneInfo(
            zone_name="test-com", domain="test.com", provider="mock"
        )
        mock_provider.health_check.return_value = True
        mgr._provider = mock_provider
        return mgr

    def test_status_no_zone(self):
        mgr = self._make_manager()
        status = mgr.status("missing.com")
        self.assertFalse(status.zone_exists)
        self.assertGreater(len(status.issues), 0)

    def test_status_with_zone_and_records(self):
        zones = [ZoneInfo("test-com", "test.com", ["ns1"], provider="mock")]
        records = [
            DNSRecord("A", "test.com", "185.199.108.153", 300),
            DNSRecord("CNAME", "www.test.com", "issdandavis.github.io", 300),
        ]
        mgr = self._make_manager(zones=zones, records=records)
        status = mgr.status("test.com")
        self.assertTrue(status.zone_exists)
        self.assertTrue(status.has_a_record)
        self.assertTrue(status.has_cname)
        self.assertTrue(status.github_pages_ready)
        self.assertTrue(status.ssl_possible)

    def test_add_record(self):
        zones = [ZoneInfo("test-com", "test.com", provider="mock")]
        mgr = self._make_manager(zones=zones)
        ok = mgr.add_record("A", "api.test.com", "1.2.3.4")
        self.assertTrue(ok)

    def test_add_record_no_zones(self):
        mgr = self._make_manager()
        ok = mgr.add_record("A", "api.test.com", "1.2.3.4")
        self.assertFalse(ok)

    def test_setup_github_pages(self):
        zones = [ZoneInfo("test-com", "test.com", provider="mock")]
        mgr = self._make_manager(zones=zones)
        ok = mgr.setup_github_pages("test.com")
        self.assertTrue(ok)
        # Should have called add_record 6 times (4 A + 1 CNAME + 1 TXT)
        self.assertEqual(mgr._provider.add_record.call_count, 6)

    def test_setup_api_subdomain(self):
        zones = [ZoneInfo("test-com", "test.com", provider="mock")]
        mgr = self._make_manager(zones=zones)
        ok = mgr.setup_api_subdomain("test.com", "34.134.99.90")
        self.assertTrue(ok)

    def test_list_all(self):
        zones = [ZoneInfo("test-com", "test.com", provider="mock")]
        records = [DNSRecord("A", "test.com", "1.2.3.4")]
        mgr = self._make_manager(zones=zones, records=records)
        all_records = mgr.list_all()
        self.assertIn("test.com", all_records)

    def test_health(self):
        mgr = self._make_manager()
        self.assertTrue(mgr.health())

    def test_github_pages_ips(self):
        """Verify we have the correct GitHub Pages IPs."""
        self.assertEqual(len(DNSManager._GITHUB_PAGES_IPS), 4)
        self.assertIn("185.199.108.153", DNSManager._GITHUB_PAGES_IPS)


class TestDNSRecord(unittest.TestCase):
    """Test DNS record dataclass."""

    def test_creation(self):
        r = DNSRecord("A", "test.com", "1.2.3.4", ttl=600)
        self.assertEqual(r.record_type, "A")
        self.assertEqual(r.ttl, 600)

    def test_default_ttl(self):
        r = DNSRecord("CNAME", "www.test.com", "test.com")
        self.assertEqual(r.ttl, 300)

    def test_mx_priority(self):
        r = DNSRecord("MX", "test.com", "mail.test.com", priority=10)
        self.assertEqual(r.priority, 10)


if __name__ == "__main__":
    unittest.main()
