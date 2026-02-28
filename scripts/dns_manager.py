"""DNS & Custom Domain Manager for SCBE infrastructure.

Manages DNS records and custom domain routing across providers.
Supports Google Cloud DNS (primary) and Cloudflare (secondary).

Usage::

    # CLI
    python scripts/dns_manager.py status
    python scripts/dns_manager.py add A api.aethermoorgames.com 34.134.99.90
    python scripts/dns_manager.py add CNAME www.aethermoorgames.com issdandavis.github.io.
    python scripts/dns_manager.py list
    python scripts/dns_manager.py verify aethermoorgames.com
    python scripts/dns_manager.py setup-github-pages aethermoorgames.com

    # Python
    from scripts.dns_manager import DNSManager
    mgr = DNSManager(provider="gcloud")
    mgr.add_record("A", "api.aethermoorgames.com", "34.134.99.90", ttl=300)

Providers:
    - gcloud:     Google Cloud DNS (requires gcloud CLI + project)
    - cloudflare: Cloudflare API (requires CLOUDFLARE_API_TOKEN + CLOUDFLARE_ZONE_ID)

@component Infrastructure.DNS
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ==========================================================================
# Data types
# ==========================================================================

@dataclass
class DNSRecord:
    """A single DNS record."""
    record_type: str  # A, AAAA, CNAME, TXT, MX, NS
    name: str         # e.g. "api.aethermoorgames.com"
    value: str        # e.g. "34.134.99.90" or "issdandavis.github.io."
    ttl: int = 300
    priority: int = 0  # For MX records
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ZoneInfo:
    """DNS zone metadata."""
    zone_name: str
    domain: str
    nameservers: List[str] = field(default_factory=list)
    record_count: int = 0
    provider: str = ""


@dataclass
class DomainStatus:
    """Overall domain health."""
    domain: str
    zone_exists: bool = False
    nameservers_correct: bool = False
    has_a_record: bool = False
    has_cname: bool = False
    has_txt_verification: bool = False
    ssl_possible: bool = False
    github_pages_ready: bool = False
    records: List[DNSRecord] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)


# ==========================================================================
# Provider interface
# ==========================================================================

class DNSProvider(ABC):
    """Abstract DNS provider interface."""

    @abstractmethod
    def list_zones(self) -> List[ZoneInfo]:
        ...

    @abstractmethod
    def create_zone(self, domain: str, description: str = "") -> Optional[ZoneInfo]:
        ...

    @abstractmethod
    def list_records(self, zone: str) -> List[DNSRecord]:
        ...

    @abstractmethod
    def add_record(self, zone: str, record: DNSRecord) -> bool:
        ...

    @abstractmethod
    def delete_record(self, zone: str, record: DNSRecord) -> bool:
        ...

    @abstractmethod
    def health_check(self) -> bool:
        ...


# ==========================================================================
# Google Cloud DNS Provider
# ==========================================================================

class GoogleCloudDNS(DNSProvider):
    """Google Cloud DNS via gcloud CLI.

    Requires:
        - gcloud CLI installed and authenticated
        - Cloud DNS API enabled on project
        - GCP_PROJECT env var or --project flag
    """

    def __init__(self, project: Optional[str] = None) -> None:
        self._project = project or os.environ.get(
            "GCP_PROJECT",
            os.environ.get("GOOGLE_CLOUD_PROJECT", "issac-ai-vtfqup"),
        )

    def _run_gcloud(self, args: List[str], parse_json: bool = True) -> Optional[Any]:
        """Run a gcloud command and return parsed output."""
        cmd = ["gcloud"] + args + [
            f"--project={self._project}",
            "--format=json",
            "--quiet",
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.warning("gcloud error: %s", result.stderr.strip())
                return None
            if parse_json and result.stdout.strip():
                return json.loads(result.stdout)
            return result.stdout
        except FileNotFoundError:
            logger.error("gcloud CLI not found — install Google Cloud SDK")
            return None
        except subprocess.TimeoutExpired:
            logger.error("gcloud command timed out")
            return None
        except json.JSONDecodeError:
            logger.warning("gcloud output not valid JSON")
            return None

    def list_zones(self) -> List[ZoneInfo]:
        data = self._run_gcloud(["dns", "managed-zones", "list"])
        if not data:
            return []
        zones = []
        for z in data:
            zones.append(ZoneInfo(
                zone_name=z.get("name", ""),
                domain=z.get("dnsName", "").rstrip("."),
                nameservers=z.get("nameServers", []),
                provider="gcloud",
            ))
        return zones

    def create_zone(self, domain: str, description: str = "") -> Optional[ZoneInfo]:
        # Zone name: replace dots with dashes
        zone_name = domain.replace(".", "-")
        dns_name = domain if domain.endswith(".") else f"{domain}."
        desc = description or f"SCBE managed zone for {domain}"

        data = self._run_gcloud([
            "dns", "managed-zones", "create", zone_name,
            f"--dns-name={dns_name}",
            f"--description={desc}",
            "--visibility=public",
        ])
        if data is None:
            # Check if it already exists
            zones = self.list_zones()
            for z in zones:
                if z.domain == domain or z.zone_name == zone_name:
                    return z
            return None

        # Fetch the created zone
        zones = self.list_zones()
        for z in zones:
            if z.zone_name == zone_name:
                return z
        return ZoneInfo(zone_name=zone_name, domain=domain, provider="gcloud")

    def list_records(self, zone: str) -> List[DNSRecord]:
        data = self._run_gcloud([
            "dns", "record-sets", "list",
            f"--zone={zone}",
        ])
        if not data:
            return []
        records = []
        for r in data:
            rtype = r.get("type", "")
            name = r.get("name", "").rstrip(".")
            ttl = r.get("ttl", 300)
            for rdata in r.get("rrdatas", []):
                records.append(DNSRecord(
                    record_type=rtype,
                    name=name,
                    value=rdata.rstrip(".") if rtype == "CNAME" else rdata,
                    ttl=ttl,
                ))
        return records

    def add_record(self, zone: str, record: DNSRecord) -> bool:
        name = record.name if record.name.endswith(".") else f"{record.name}."
        value = record.value
        if record.record_type == "CNAME" and not value.endswith("."):
            value = f"{value}."

        result = self._run_gcloud([
            "dns", "record-sets", "create", name,
            f"--zone={zone}",
            f"--type={record.record_type}",
            f"--ttl={record.ttl}",
            f"--rrdatas={value}",
        ], parse_json=False)
        return result is not None

    def delete_record(self, zone: str, record: DNSRecord) -> bool:
        name = record.name if record.name.endswith(".") else f"{record.name}."
        result = self._run_gcloud([
            "dns", "record-sets", "delete", name,
            f"--zone={zone}",
            f"--type={record.record_type}",
        ], parse_json=False)
        return result is not None

    def health_check(self) -> bool:
        result = self._run_gcloud(["dns", "managed-zones", "list"])
        return result is not None


# ==========================================================================
# Cloudflare DNS Provider
# ==========================================================================

class CloudflareDNS(DNSProvider):
    """Cloudflare DNS via REST API.

    Requires:
        - CLOUDFLARE_API_TOKEN (scoped to DNS edit)
        - CLOUDFLARE_ZONE_ID (from dashboard)
    """

    _API_BASE = "https://api.cloudflare.com/client/v4"

    def __init__(
        self,
        api_token: Optional[str] = None,
        zone_id: Optional[str] = None,
    ) -> None:
        self._token = api_token or os.environ.get("CLOUDFLARE_API_TOKEN", "")
        self._zone_id = zone_id or os.environ.get("CLOUDFLARE_ZONE_ID", "")

    def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Optional[Any]:
        url = f"{self._API_BASE}{path}"
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read())
                if not result.get("success"):
                    errors = result.get("errors", [])
                    logger.warning("Cloudflare API error: %s", errors)
                    return None
                return result.get("result")
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            logger.warning("Cloudflare HTTP error: %s", exc)
            return None
        except Exception:
            logger.exception("Cloudflare unexpected error")
            return None

    def list_zones(self) -> List[ZoneInfo]:
        data = self._request("GET", "/zones")
        if not data:
            return []
        return [
            ZoneInfo(
                zone_name=z.get("id", ""),
                domain=z.get("name", ""),
                nameservers=z.get("name_servers", []),
                provider="cloudflare",
            )
            for z in data
        ]

    def create_zone(self, domain: str, description: str = "") -> Optional[ZoneInfo]:
        data = self._request("POST", "/zones", {"name": domain, "jump_start": True})
        if not data:
            return None
        return ZoneInfo(
            zone_name=data.get("id", ""),
            domain=data.get("name", domain),
            nameservers=data.get("name_servers", []),
            provider="cloudflare",
        )

    def list_records(self, zone: str) -> List[DNSRecord]:
        zone_id = zone or self._zone_id
        data = self._request("GET", f"/zones/{zone_id}/dns_records")
        if not data:
            return []
        return [
            DNSRecord(
                record_type=r.get("type", ""),
                name=r.get("name", ""),
                value=r.get("content", ""),
                ttl=r.get("ttl", 1),
                metadata={"proxied": r.get("proxied", False), "id": r.get("id", "")},
            )
            for r in data
        ]

    def add_record(self, zone: str, record: DNSRecord) -> bool:
        zone_id = zone or self._zone_id
        payload: Dict[str, Any] = {
            "type": record.record_type,
            "name": record.name,
            "content": record.value,
            "ttl": record.ttl,
        }
        if record.record_type == "MX":
            payload["priority"] = record.priority
        result = self._request("POST", f"/zones/{zone_id}/dns_records", payload)
        return result is not None

    def delete_record(self, zone: str, record: DNSRecord) -> bool:
        zone_id = zone or self._zone_id
        record_id = record.metadata.get("id", "")
        if not record_id:
            # Find it first
            records = self.list_records(zone_id)
            for r in records:
                if r.name == record.name and r.record_type == record.record_type:
                    record_id = r.metadata.get("id", "")
                    break
        if not record_id:
            return False
        result = self._request("DELETE", f"/zones/{zone_id}/dns_records/{record_id}")
        return result is not None

    def health_check(self) -> bool:
        if not self._token:
            return False
        data = self._request("GET", "/user/tokens/verify")
        return data is not None


# ==========================================================================
# Main DNS Manager
# ==========================================================================

class DNSManager:
    """Unified DNS management across providers.

    Parameters
    ----------
    provider : str
        ``"gcloud"`` or ``"cloudflare"``.
    config : dict, optional
        Provider-specific configuration.
    """

    _GITHUB_PAGES_IPS = [
        "185.199.108.153",
        "185.199.109.153",
        "185.199.110.153",
        "185.199.111.153",
    ]

    def __init__(
        self,
        provider: str = "gcloud",
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        config = config or {}
        if provider == "cloudflare":
            self._provider: DNSProvider = CloudflareDNS(
                api_token=config.get("api_token"),
                zone_id=config.get("zone_id"),
            )
        else:
            self._provider = GoogleCloudDNS(
                project=config.get("project"),
            )
        self._provider_name = provider

    def status(self, domain: str) -> DomainStatus:
        """Get full domain health status."""
        result = DomainStatus(domain=domain)

        zones = self._provider.list_zones()
        zone = None
        for z in zones:
            if z.domain == domain or domain.endswith(f".{z.domain}"):
                zone = z
                result.zone_exists = True
                break

        if not zone:
            result.issues.append(f"No DNS zone found for {domain}")
            return result

        records = self._provider.list_records(zone.zone_name)
        result.records = records

        for r in records:
            if r.record_type == "A":
                result.has_a_record = True
                if r.value in self._GITHUB_PAGES_IPS:
                    result.github_pages_ready = True
            elif r.record_type == "CNAME":
                result.has_cname = True
                if "github.io" in r.value:
                    result.github_pages_ready = True
            elif r.record_type == "TXT":
                result.has_txt_verification = True

        if zone.nameservers:
            result.nameservers_correct = True

        result.ssl_possible = result.has_a_record or result.has_cname

        if not result.has_a_record and not result.has_cname:
            result.issues.append("No A or CNAME record — domain won't resolve")

        return result

    def add_record(
        self,
        record_type: str,
        name: str,
        value: str,
        ttl: int = 300,
        zone: Optional[str] = None,
    ) -> bool:
        """Add a DNS record."""
        if not zone:
            zones = self._provider.list_zones()
            if zones:
                zone = zones[0].zone_name
            else:
                logger.error("No zones found — create one first")
                return False

        record = DNSRecord(
            record_type=record_type.upper(),
            name=name,
            value=value,
            ttl=ttl,
        )
        return self._provider.add_record(zone, record)

    def setup_github_pages(self, domain: str, zone: Optional[str] = None) -> bool:
        """Configure DNS for GitHub Pages custom domain.

        Creates:
            - 4 A records pointing to GitHub's IPs
            - 1 CNAME for www → username.github.io
        """
        if not zone:
            zone_name = domain.replace(".", "-")
            zones = self._provider.list_zones()
            for z in zones:
                if z.zone_name == zone_name or z.domain == domain:
                    zone = z.zone_name
                    break
            if not zone:
                logger.info("Creating zone for %s", domain)
                zone_info = self._provider.create_zone(domain)
                if zone_info:
                    zone = zone_info.zone_name
                else:
                    return False

        success = True

        # A records for apex domain
        for ip in self._GITHUB_PAGES_IPS:
            ok = self._provider.add_record(zone, DNSRecord(
                record_type="A",
                name=domain,
                value=ip,
                ttl=300,
            ))
            if not ok:
                success = False

        # CNAME for www
        ok = self._provider.add_record(zone, DNSRecord(
            record_type="CNAME",
            name=f"www.{domain}",
            value="issdandavis.github.io.",
            ttl=300,
        ))
        if not ok:
            success = False

        # TXT verification record
        ok = self._provider.add_record(zone, DNSRecord(
            record_type="TXT",
            name=f"_github-pages-challenge-issdandavis.{domain}",
            value='"github-pages-verification"',
            ttl=300,
        ))

        return success

    def setup_api_subdomain(
        self,
        domain: str,
        ip: str = "34.134.99.90",
        zone: Optional[str] = None,
    ) -> bool:
        """Point api.domain to the SCBE bridge VM."""
        if not zone:
            zones = self._provider.list_zones()
            for z in zones:
                if z.domain == domain:
                    zone = z.zone_name
                    break
        if not zone:
            return False

        return self._provider.add_record(zone, DNSRecord(
            record_type="A",
            name=f"api.{domain}",
            value=ip,
            ttl=300,
        ))

    def list_all(self) -> Dict[str, List[DNSRecord]]:
        """List all records across all zones."""
        result: Dict[str, List[DNSRecord]] = {}
        for zone in self._provider.list_zones():
            result[zone.domain] = self._provider.list_records(zone.zone_name)
        return result

    def health(self) -> bool:
        """Check provider health."""
        return self._provider.health_check()


# ==========================================================================
# CLI
# ==========================================================================

def _cli():
    """Command-line interface for DNS management."""
    import argparse

    parser = argparse.ArgumentParser(
        description="SCBE DNS Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python dns_manager.py status aethermoorgames.com
  python dns_manager.py add A api.aethermoorgames.com 34.134.99.90
  python dns_manager.py add CNAME www.aethermoorgames.com issdandavis.github.io.
  python dns_manager.py list
  python dns_manager.py setup-github-pages aethermoorgames.com
  python dns_manager.py setup-api aethermoorgames.com 34.134.99.90
  python dns_manager.py health
        """,
    )
    parser.add_argument(
        "--provider", choices=["gcloud", "cloudflare"], default="gcloud",
        help="DNS provider (default: gcloud)",
    )
    sub = parser.add_subparsers(dest="command")

    # status
    p_status = sub.add_parser("status", help="Check domain status")
    p_status.add_argument("domain")

    # add
    p_add = sub.add_parser("add", help="Add a DNS record")
    p_add.add_argument("type", choices=["A", "AAAA", "CNAME", "TXT", "MX", "NS"])
    p_add.add_argument("name")
    p_add.add_argument("value")
    p_add.add_argument("--ttl", type=int, default=300)

    # list
    sub.add_parser("list", help="List all DNS records")

    # setup-github-pages
    p_gh = sub.add_parser("setup-github-pages", help="Configure GitHub Pages DNS")
    p_gh.add_argument("domain")

    # setup-api
    p_api = sub.add_parser("setup-api", help="Point api.domain to VM")
    p_api.add_argument("domain")
    p_api.add_argument("ip", nargs="?", default="34.134.99.90")

    # health
    sub.add_parser("health", help="Check provider health")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    mgr = DNSManager(provider=args.provider)

    if args.command == "status":
        s = mgr.status(args.domain)
        print(f"Domain: {s.domain}")
        print(f"  Zone exists:      {'yes' if s.zone_exists else 'NO'}")
        print(f"  A record:         {'yes' if s.has_a_record else 'NO'}")
        print(f"  CNAME:            {'yes' if s.has_cname else 'NO'}")
        print(f"  TXT verification: {'yes' if s.has_txt_verification else 'NO'}")
        print(f"  GitHub Pages:     {'ready' if s.github_pages_ready else 'not configured'}")
        print(f"  SSL possible:     {'yes' if s.ssl_possible else 'NO'}")
        if s.issues:
            print(f"  Issues: {', '.join(s.issues)}")
        if s.records:
            print(f"\n  Records ({len(s.records)}):")
            for r in s.records:
                print(f"    {r.record_type:6s} {r.name:40s} → {r.value}")

    elif args.command == "add":
        ok = mgr.add_record(args.type, args.name, args.value, args.ttl)
        print("OK" if ok else "FAILED")

    elif args.command == "list":
        all_records = mgr.list_all()
        if not all_records:
            print("No zones found.")
        for domain, records in all_records.items():
            print(f"\n{domain} ({len(records)} records)")
            for r in records:
                print(f"  {r.record_type:6s} {r.name:40s} → {r.value} (TTL {r.ttl})")

    elif args.command == "setup-github-pages":
        ok = mgr.setup_github_pages(args.domain)
        print("GitHub Pages DNS configured" if ok else "FAILED")

    elif args.command == "setup-api":
        ok = mgr.setup_api_subdomain(args.domain, args.ip)
        print(f"api.{args.domain} → {args.ip}" if ok else "FAILED")

    elif args.command == "health":
        ok = mgr.health()
        print(f"Provider health: {'OK' if ok else 'UNHEALTHY'}")


if __name__ == "__main__":
    _cli()
