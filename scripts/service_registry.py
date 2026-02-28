"""Service Registry — Master connector for all external services.

The "pylons" of the SCBE infrastructure. Central hub that manages
connections to all external platforms, tracks health, and provides
unified access for the AI fleet.

Services managed:
    - Email (IMAP/SMTP): 3 Google + 1 Proton
    - Google Business Profile API
    - Google Cloud Platform (Compute, Vertex AI, DNS, etc.)
    - Shopify (Admin + Storefront API)
    - Firebase (Auth, Firestore, Hosting)
    - Figma (REST API)
    - AWS (Lambda, S3, SES)
    - GitHub (already connected via gh CLI)
    - Medium (read/write via RSS + API)
    - HuggingFace (Hub API)
    - Academic sources (arXiv, ORCID, USPTO, S2, CrossRef)

Usage::

    registry = ServiceRegistry()
    registry.load_from_env()
    report = registry.health_check_all()
    email = registry.get("email:gmail:primary")
    shopify = registry.get("shopify:admin")

CLI::

    python scripts/service_registry.py status
    python scripts/service_registry.py health
    python scripts/service_registry.py list
    python scripts/service_registry.py enable gmail
    python scripts/service_registry.py send-email gmail:primary "to@example.com" "Subject" "Body"

@component Infrastructure.ServiceRegistry
"""

from __future__ import annotations

import imaplib
import json
import logging
import os
import smtplib
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ==========================================================================
# Types
# ==========================================================================

class ServiceStatus(str, Enum):
    CONNECTED = "connected"
    CONFIGURED = "configured"  # Credentials present but not tested
    MISSING = "missing"        # No credentials
    ERROR = "error"            # Credentials present but connection failed


class ServiceCategory(str, Enum):
    EMAIL = "email"
    COMMERCE = "commerce"
    CLOUD = "cloud"
    DESIGN = "design"
    ACADEMIC = "academic"
    SOCIAL = "social"
    DEVOPS = "devops"


@dataclass
class ServiceInfo:
    """Metadata about a registered external service."""
    name: str
    category: ServiceCategory
    status: ServiceStatus = ServiceStatus.MISSING
    provider: str = ""
    endpoint: str = ""
    credentials_env: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    notes: str = ""
    last_health_check: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EmailAccount:
    """Configuration for an email account."""
    name: str           # e.g. "gmail:primary", "proton:business"
    address: str        # e.g. "issdandavis7795@gmail.com"
    imap_host: str
    imap_port: int
    smtp_host: str
    smtp_port: int
    username: str
    password_env: str   # env var name holding the password/app password
    use_ssl: bool = True


# ==========================================================================
# Email Connector
# ==========================================================================

class EmailConnector:
    """IMAP/SMTP email connector supporting multiple accounts.

    Supports:
        - Gmail (via App Passwords, IMAP/SMTP)
        - Proton Mail (via ProtonMail Bridge, localhost IMAP/SMTP)
        - Any IMAP/SMTP provider

    Gmail setup:
        1. Enable 2FA on your Google account
        2. Go to https://myaccount.google.com/apppasswords
        3. Create an App Password for "Mail"
        4. Set GMAIL_APP_PASSWORD_1=xxxx in .env

    Proton setup:
        1. Install ProtonMail Bridge (desktop app)
        2. Bridge runs IMAP on 127.0.0.1:1143, SMTP on 127.0.0.1:1025
        3. Set PROTON_BRIDGE_PASSWORD=xxxx in .env
    """

    # Pre-configured providers
    PROVIDERS = {
        "gmail": {
            "imap_host": "imap.gmail.com",
            "imap_port": 993,
            "smtp_host": "smtp.gmail.com",
            "smtp_port": 587,
            "use_ssl": True,
        },
        "proton": {
            "imap_host": "127.0.0.1",
            "imap_port": 1143,
            "smtp_host": "127.0.0.1",
            "smtp_port": 1025,
            "use_ssl": False,  # Bridge handles encryption
        },
        "outlook": {
            "imap_host": "outlook.office365.com",
            "imap_port": 993,
            "smtp_host": "smtp.office365.com",
            "smtp_port": 587,
            "use_ssl": True,
        },
    }

    def __init__(self) -> None:
        self._accounts: Dict[str, EmailAccount] = {}

    def add_account(self, account: EmailAccount) -> None:
        self._accounts[account.name] = account

    def add_gmail(
        self,
        name: str,
        address: str,
        password_env: str = "GMAIL_APP_PASSWORD",
    ) -> None:
        """Register a Gmail account."""
        cfg = self.PROVIDERS["gmail"]
        self._accounts[name] = EmailAccount(
            name=name,
            address=address,
            username=address,
            password_env=password_env,
            **cfg,
        )

    def add_proton(
        self,
        name: str,
        address: str,
        password_env: str = "PROTON_BRIDGE_PASSWORD",
    ) -> None:
        """Register a Proton Mail account (via Bridge)."""
        cfg = self.PROVIDERS["proton"]
        self._accounts[name] = EmailAccount(
            name=name,
            address=address,
            username=address,
            password_env=password_env,
            **cfg,
        )

    def list_accounts(self) -> List[str]:
        return list(self._accounts.keys())

    def check_connection(self, account_name: str) -> Tuple[bool, str]:
        """Test IMAP connection to an email account."""
        account = self._accounts.get(account_name)
        if not account:
            return False, f"Account {account_name} not registered"

        password = os.environ.get(account.password_env, "")
        if not password:
            return False, f"Password env var {account.password_env} not set"

        try:
            if account.use_ssl:
                imap = imaplib.IMAP4_SSL(account.imap_host, account.imap_port)
            else:
                imap = imaplib.IMAP4(account.imap_host, account.imap_port)
            imap.login(account.username, password)
            status, data = imap.select("INBOX", readonly=True)
            msg_count = data[0].decode() if data else "0"
            imap.logout()
            return True, f"Connected. {msg_count} messages in INBOX"
        except Exception as exc:
            return False, f"Connection failed: {exc}"

    def fetch_recent(
        self,
        account_name: str,
        folder: str = "INBOX",
        count: int = 10,
    ) -> List[Dict[str, str]]:
        """Fetch recent email headers from an account."""
        account = self._accounts.get(account_name)
        if not account:
            return []

        password = os.environ.get(account.password_env, "")
        if not password:
            return []

        try:
            if account.use_ssl:
                imap = imaplib.IMAP4_SSL(account.imap_host, account.imap_port)
            else:
                imap = imaplib.IMAP4(account.imap_host, account.imap_port)
            imap.login(account.username, password)
            imap.select(folder, readonly=True)

            # Search for recent messages
            status, data = imap.search(None, "ALL")
            if status != "OK" or not data[0]:
                imap.logout()
                return []

            msg_ids = data[0].split()
            recent_ids = msg_ids[-count:]  # Last N messages

            messages = []
            for msg_id in reversed(recent_ids):
                status, msg_data = imap.fetch(msg_id, "(BODY[HEADER.FIELDS (FROM SUBJECT DATE)])")
                if status == "OK" and msg_data[0]:
                    raw = msg_data[0][1]
                    if isinstance(raw, bytes):
                        raw = raw.decode("utf-8", errors="replace")
                    # Parse headers
                    headers: Dict[str, str] = {"id": msg_id.decode()}
                    for line in raw.strip().split("\n"):
                        line = line.strip()
                        if line.lower().startswith("from:"):
                            headers["from"] = line[5:].strip()
                        elif line.lower().startswith("subject:"):
                            headers["subject"] = line[8:].strip()
                        elif line.lower().startswith("date:"):
                            headers["date"] = line[5:].strip()
                    messages.append(headers)

            imap.logout()
            return messages

        except Exception as exc:
            logger.warning("Email fetch failed for %s: %s", account_name, exc)
            return []

    def send_email(
        self,
        account_name: str,
        to: str,
        subject: str,
        body: str,
        html: bool = False,
    ) -> Tuple[bool, str]:
        """Send an email from a registered account."""
        account = self._accounts.get(account_name)
        if not account:
            return False, f"Account {account_name} not registered"

        password = os.environ.get(account.password_env, "")
        if not password:
            return False, f"Password env var {account.password_env} not set"

        msg = MIMEMultipart("alternative")
        msg["From"] = account.address
        msg["To"] = to
        msg["Subject"] = subject

        content_type = "html" if html else "plain"
        msg.attach(MIMEText(body, content_type, "utf-8"))

        try:
            if account.smtp_port == 465:
                smtp = smtplib.SMTP_SSL(account.smtp_host, account.smtp_port)
            else:
                smtp = smtplib.SMTP(account.smtp_host, account.smtp_port)
                if account.use_ssl:
                    smtp.starttls()
            smtp.login(account.username, password)
            smtp.send_message(msg)
            smtp.quit()
            return True, "Sent"
        except Exception as exc:
            return False, f"Send failed: {exc}"


# ==========================================================================
# Google Business Profile Connector
# ==========================================================================

class GoogleBusinessConnector:
    """Google Business Profile API connector.

    Manages business listing, posts, reviews, and Q&A.

    Requires:
        - Google Business Profile API enabled
        - OAuth2 credentials or service account
        - GBP_ACCESS_TOKEN env var (or use gcloud auth)

    Enable API:
        https://console.cloud.google.com/apis/api/mybusinessbusinessinformation.googleapis.com

    Scopes needed:
        - https://www.googleapis.com/auth/business.manage
    """

    _API_BASE = "https://mybusinessbusinessinformation.googleapis.com/v1"
    _ACCOUNT_API = "https://mybusinessaccountmanagement.googleapis.com/v1"

    def __init__(self, access_token: Optional[str] = None) -> None:
        self._token = access_token or os.environ.get("GBP_ACCESS_TOKEN", "")
        if not self._token:
            # Try gcloud auth
            self._token = self._get_gcloud_token()

    @staticmethod
    def _get_gcloud_token() -> str:
        """Get access token from gcloud CLI."""
        try:
            result = subprocess.run(
                ["gcloud", "auth", "print-access-token"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return ""

    def _request(self, method: str, url: str, data: Optional[Dict] = None) -> Optional[Any]:
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        body = json.dumps(data).encode() if data else None
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except Exception as exc:
            logger.warning("Google Business API error: %s", exc)
            return None

    def list_accounts(self) -> Optional[List[Dict[str, Any]]]:
        """List all Google Business accounts."""
        data = self._request("GET", f"{self._ACCOUNT_API}/accounts")
        if not data:
            return None
        return data.get("accounts", [])

    def list_locations(self, account_name: str) -> Optional[List[Dict[str, Any]]]:
        """List locations for a business account."""
        url = f"{self._API_BASE}/{account_name}/locations?readMask=name,title,storefrontAddress"
        data = self._request("GET", url)
        if not data:
            return None
        return data.get("locations", [])

    def create_post(
        self,
        location_name: str,
        summary: str,
        call_to_action_url: str = "",
    ) -> Optional[Dict[str, Any]]:
        """Create a Google Business post."""
        post_data: Dict[str, Any] = {
            "summary": summary,
            "topicType": "STANDARD",
        }
        if call_to_action_url:
            post_data["callToAction"] = {
                "actionType": "LEARN_MORE",
                "url": call_to_action_url,
            }
        url = f"https://mybusiness.googleapis.com/v4/{location_name}/localPosts"
        return self._request("POST", url, post_data)

    def health_check(self) -> Tuple[bool, str]:
        if not self._token:
            return False, "No access token (set GBP_ACCESS_TOKEN or authenticate with gcloud)"
        accounts = self.list_accounts()
        if accounts is None:
            return False, "API call failed — enable Business Profile API in GCP console"
        return True, f"{len(accounts)} account(s) found"


# ==========================================================================
# Figma Connector
# ==========================================================================

class FigmaConnector:
    """Figma REST API connector for design asset management.

    Requires FIGMA_ACCESS_TOKEN (personal access token from Figma settings).
    """

    _API_BASE = "https://api.figma.com/v1"

    def __init__(self, token: Optional[str] = None) -> None:
        self._token = token or os.environ.get("FIGMA_ACCESS_TOKEN", "")

    def _request(self, path: str) -> Optional[Any]:
        if not self._token:
            return None
        url = f"{self._API_BASE}{path}"
        headers = {"X-Figma-Token": self._token}
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read())
        except Exception as exc:
            logger.warning("Figma API error: %s", exc)
            return None

    def get_file(self, file_key: str) -> Optional[Dict[str, Any]]:
        """Get a Figma file's metadata and structure."""
        return self._request(f"/files/{file_key}")

    def get_images(self, file_key: str, node_ids: List[str], fmt: str = "png", scale: float = 2.0) -> Optional[Dict[str, str]]:
        """Export nodes as images. Returns {node_id: image_url}."""
        ids = ",".join(node_ids)
        data = self._request(f"/images/{file_key}?ids={ids}&format={fmt}&scale={scale}")
        if not data:
            return None
        return data.get("images", {})

    def list_projects(self, team_id: str) -> Optional[List[Dict[str, Any]]]:
        """List projects in a team."""
        data = self._request(f"/teams/{team_id}/projects")
        if not data:
            return None
        return data.get("projects", [])

    def health_check(self) -> Tuple[bool, str]:
        if not self._token:
            return False, "No Figma token (set FIGMA_ACCESS_TOKEN)"
        data = self._request("/me")
        if data and data.get("id"):
            return True, f"Authenticated as {data.get('handle', 'unknown')}"
        return False, "Authentication failed"


# ==========================================================================
# Service Registry
# ==========================================================================

class ServiceRegistry:
    """Master registry for all external service connections.

    The StarCraft pylon — everything builds from here.
    """

    def __init__(self) -> None:
        self._services: Dict[str, ServiceInfo] = {}
        self._email = EmailConnector()
        self._google_business: Optional[GoogleBusinessConnector] = None
        self._figma: Optional[FigmaConnector] = None
        self._register_all()

    def _register_all(self) -> None:
        """Register all known services with their status."""

        # --- Email (4 accounts: 3 Gmail + 1 Proton) ---
        self._register("email:gmail:primary", ServiceCategory.EMAIL,
                       provider="Gmail",
                       credentials_env=["GMAIL_APP_PASSWORD_1"],
                       capabilities=["imap", "smtp", "send", "receive", "search"],
                       notes="Primary Google account (issdandavis7795@gmail.com)")

        self._register("email:gmail:business", ServiceCategory.EMAIL,
                       provider="Gmail",
                       credentials_env=["GMAIL_APP_PASSWORD_2"],
                       capabilities=["imap", "smtp", "send", "receive"],
                       notes="Business Google account")

        self._register("email:gmail:dev", ServiceCategory.EMAIL,
                       provider="Gmail",
                       credentials_env=["GMAIL_APP_PASSWORD_3"],
                       capabilities=["imap", "smtp", "send", "receive"],
                       notes="Dev/testing Google account")

        self._register("email:proton:business", ServiceCategory.EMAIL,
                       provider="ProtonMail Bridge",
                       credentials_env=["PROTON_BRIDGE_PASSWORD"],
                       capabilities=["imap", "smtp", "send", "receive", "encrypted"],
                       notes="Proton business account (requires Bridge desktop app)")

        # --- Commerce ---
        self._register("shopify:admin", ServiceCategory.COMMERCE,
                       provider="Shopify",
                       endpoint="https://{store}.myshopify.com/admin/api/2025-10/graphql.json",
                       credentials_env=["SHOPIFY_ADMIN_API_TOKEN", "SHOPIFY_STORE_DOMAIN"],
                       capabilities=["products", "orders", "customers", "themes", "webhooks"],
                       notes="Shopify Admin API — full store management")

        self._register("shopify:storefront", ServiceCategory.COMMERCE,
                       provider="Shopify",
                       endpoint="https://{store}.myshopify.com/api/2025-10/graphql.json",
                       credentials_env=["SHOPIFY_STOREFRONT_TOKEN", "SHOPIFY_STORE_DOMAIN"],
                       capabilities=["catalog", "checkout", "cart", "collections"],
                       notes="Shopify Storefront API — customer-facing")

        # --- Cloud ---
        self._register("gcp:compute", ServiceCategory.CLOUD,
                       provider="Google Cloud",
                       credentials_env=["GOOGLE_APPLICATION_CREDENTIALS"],
                       capabilities=["vms", "dns", "cloud-run", "vertex-ai", "storage"],
                       notes="Project: issac-ai-vtfqup, VM: scbe-mesh-foundry @ 34.134.99.90")

        self._register("aws", ServiceCategory.CLOUD,
                       provider="Amazon Web Services",
                       credentials_env=["AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"],
                       capabilities=["lambda", "s3", "ses", "cloudfront", "route53"],
                       notes="AWS account for Lambda + S3 + SES")

        self._register("firebase", ServiceCategory.CLOUD,
                       provider="Firebase (Google)",
                       credentials_env=["FIREBASE_SERVICE_ACCOUNT"],
                       capabilities=["auth", "firestore", "hosting", "functions", "storage"],
                       notes="Firebase for auth + realtime features")

        # --- Design ---
        self._register("figma", ServiceCategory.DESIGN,
                       provider="Figma",
                       endpoint="https://api.figma.com/v1",
                       credentials_env=["FIGMA_ACCESS_TOKEN"],
                       capabilities=["files", "images", "components", "export"],
                       notes="Design assets, color palettes, character designs")

        # --- Social / Business ---
        self._register("google:business", ServiceCategory.SOCIAL,
                       provider="Google Business Profile",
                       credentials_env=["GBP_ACCESS_TOKEN"],
                       capabilities=["listing", "posts", "reviews", "analytics", "photos"],
                       notes="Google Business Profile management")

        self._register("medium", ServiceCategory.SOCIAL,
                       provider="Medium",
                       credentials_env=["MEDIUM_INTEGRATION_TOKEN", "MEDIUM_USERNAME"],
                       capabilities=["read_articles", "publish", "drafts"],
                       notes="Read via RSS, write via Integration Token")

        self._register("huggingface", ServiceCategory.SOCIAL,
                       provider="HuggingFace",
                       credentials_env=["HF_TOKEN"],
                       capabilities=["models", "datasets", "spaces", "inference"],
                       notes="Model + dataset hosting, inference API")

        # --- Academic ---
        self._register("orcid", ServiceCategory.ACADEMIC,
                       provider="ORCID",
                       credentials_env=["ORCID_ID"],
                       capabilities=["profile", "works", "publications"],
                       notes="ORCID: 0009-0002-3936-9369")

        self._register("arxiv", ServiceCategory.ACADEMIC,
                       provider="arXiv",
                       capabilities=["search", "fetch_paper"],
                       notes="No auth required for public API")

        self._register("uspto", ServiceCategory.ACADEMIC,
                       provider="USPTO",
                       credentials_env=["USPTO_API_KEY"],
                       capabilities=["search", "patents", "prior_art"],
                       notes="Patent search and filing tracker")

        self._register("perplexity", ServiceCategory.ACADEMIC,
                       provider="Perplexity",
                       credentials_env=["PERPLEXITY_API_KEY"],
                       capabilities=["search", "research", "competitive_analysis",
                                     "patent_landscape", "market_research"],
                       notes="AI-powered web search — sonar/sonar-pro/sonar-deep-research")

        # --- DevOps ---
        self._register("github", ServiceCategory.DEVOPS,
                       provider="GitHub",
                       credentials_env=["GITHUB_TOKEN"],
                       capabilities=["repos", "issues", "prs", "actions", "pages"],
                       notes="issdandavis/SCBE-AETHERMOORE")

        # --- Update status based on env vars ---
        self._refresh_status()

    def _register(self, name: str, category: ServiceCategory, **kwargs: Any) -> None:
        self._services[name] = ServiceInfo(name=name, category=category, **kwargs)

    def _refresh_status(self) -> None:
        """Check which services have credentials configured."""
        for name, svc in self._services.items():
            if not svc.credentials_env:
                svc.status = ServiceStatus.CONFIGURED
                continue
            has_any = any(os.environ.get(env, "") for env in svc.credentials_env)
            svc.status = ServiceStatus.CONFIGURED if has_any else ServiceStatus.MISSING

    def get(self, name: str) -> Optional[ServiceInfo]:
        return self._services.get(name)

    def list_services(self, category: Optional[ServiceCategory] = None) -> List[ServiceInfo]:
        if category:
            return [s for s in self._services.values() if s.category == category]
        return list(self._services.values())

    def list_by_status(self, status: ServiceStatus) -> List[ServiceInfo]:
        return [s for s in self._services.values() if s.status == status]

    def setup_email_accounts(
        self,
        gmail_accounts: Optional[List[Tuple[str, str, str]]] = None,
        proton_accounts: Optional[List[Tuple[str, str, str]]] = None,
    ) -> None:
        """Configure email accounts.

        gmail_accounts: list of (name, address, password_env_var)
        proton_accounts: list of (name, address, password_env_var)
        """
        if gmail_accounts:
            for name, addr, pwd_env in gmail_accounts:
                self._email.add_gmail(name, addr, pwd_env)
        if proton_accounts:
            for name, addr, pwd_env in proton_accounts:
                self._email.add_proton(name, addr, pwd_env)

    def load_default_email_accounts(self) -> None:
        """Load the default 4 email accounts from env vars."""
        gmail_addr_1 = os.environ.get("GMAIL_ADDRESS_1", "issdandavis7795@gmail.com")
        gmail_addr_2 = os.environ.get("GMAIL_ADDRESS_2", "")
        gmail_addr_3 = os.environ.get("GMAIL_ADDRESS_3", "")
        proton_addr = os.environ.get("PROTON_ADDRESS", "")

        self._email.add_gmail("gmail:primary", gmail_addr_1, "GMAIL_APP_PASSWORD_1")
        if gmail_addr_2:
            self._email.add_gmail("gmail:business", gmail_addr_2, "GMAIL_APP_PASSWORD_2")
        if gmail_addr_3:
            self._email.add_gmail("gmail:dev", gmail_addr_3, "GMAIL_APP_PASSWORD_3")
        if proton_addr:
            self._email.add_proton("proton:business", proton_addr, "PROTON_BRIDGE_PASSWORD")

    @property
    def email(self) -> EmailConnector:
        return self._email

    @property
    def google_business(self) -> GoogleBusinessConnector:
        if self._google_business is None:
            self._google_business = GoogleBusinessConnector()
        return self._google_business

    @property
    def figma(self) -> FigmaConnector:
        if self._figma is None:
            self._figma = FigmaConnector()
        return self._figma

    def health_check_all(self) -> Dict[str, Tuple[ServiceStatus, str]]:
        """Run health checks on all configured services."""
        results: Dict[str, Tuple[ServiceStatus, str]] = {}

        for name, svc in self._services.items():
            if svc.status == ServiceStatus.MISSING:
                results[name] = (ServiceStatus.MISSING, "No credentials configured")
                continue

            try:
                ok, msg = self._check_service(name)
                status = ServiceStatus.CONNECTED if ok else ServiceStatus.ERROR
                results[name] = (status, msg)
                svc.status = status
            except Exception as exc:
                results[name] = (ServiceStatus.ERROR, str(exc))
                svc.status = ServiceStatus.ERROR

        return results

    def _check_service(self, name: str) -> Tuple[bool, str]:
        """Check a specific service's health."""
        if name.startswith("email:"):
            account_name = name.replace("email:", "")
            if account_name in self._email.list_accounts():
                return self._email.check_connection(account_name)
            return False, "Email account not configured"

        if name == "google:business":
            return self.google_business.health_check()

        if name == "figma":
            return self.figma.health_check()

        if name == "github":
            try:
                result = subprocess.run(
                    ["gh", "auth", "status"],
                    capture_output=True, text=True, timeout=10,
                )
                if result.returncode == 0:
                    return True, "Authenticated via gh CLI"
                return False, result.stderr.strip()
            except Exception as exc:
                return False, str(exc)

        if name == "gcp:compute":
            try:
                result = subprocess.run(
                    ["gcloud", "auth", "list", "--format=json"],
                    capture_output=True, text=True, timeout=10,
                )
                if result.returncode == 0:
                    accounts = json.loads(result.stdout)
                    active = [a for a in accounts if a.get("status") == "ACTIVE"]
                    if active:
                        return True, f"Authenticated as {active[0].get('account', '?')}"
                return False, "No active GCP auth"
            except Exception as exc:
                return False, str(exc)

        if name == "huggingface":
            token = os.environ.get("HF_TOKEN", "")
            if not token:
                return False, "HF_TOKEN not set"
            return True, "Token configured"

        if name == "uspto":
            key = os.environ.get("USPTO_API_KEY", "")
            return (True, "API key configured") if key else (False, "USPTO_API_KEY not set")

        if name == "orcid":
            oid = os.environ.get("ORCID_ID", "")
            return (True, f"ORCID: {oid}") if oid else (False, "ORCID_ID not set")

        # Default: just check env vars
        svc = self._services.get(name)
        if svc:
            has_creds = any(os.environ.get(e, "") for e in svc.credentials_env)
            return (True, "Credentials configured") if has_creds else (False, "Missing credentials")

        return False, "Unknown service"

    def status_report(self) -> str:
        """Generate a human-readable status report."""
        lines = ["SCBE Service Registry Status", "=" * 50, ""]
        by_category: Dict[str, List[ServiceInfo]] = {}
        for svc in self._services.values():
            cat = svc.category.value
            by_category.setdefault(cat, []).append(svc)

        status_icon = {
            ServiceStatus.CONNECTED: "[OK]",
            ServiceStatus.CONFIGURED: "[--]",
            ServiceStatus.MISSING: "[  ]",
            ServiceStatus.ERROR: "[!!]",
        }

        for cat, services in sorted(by_category.items()):
            lines.append(f"  {cat.upper()}")
            for svc in services:
                icon = status_icon.get(svc.status, "[??]")
                lines.append(f"    {icon} {svc.name:30s} {svc.provider}")
            lines.append("")

        # Summary
        total = len(self._services)
        connected = sum(1 for s in self._services.values() if s.status == ServiceStatus.CONNECTED)
        configured = sum(1 for s in self._services.values() if s.status == ServiceStatus.CONFIGURED)
        missing = sum(1 for s in self._services.values() if s.status == ServiceStatus.MISSING)

        lines.append(f"Total: {total} | Connected: {connected} | Configured: {configured} | Missing: {missing}")
        lines.append("")
        lines.append("Legend: [OK] = connected  [--] = configured  [  ] = missing  [!!] = error")

        return "\n".join(lines)

    def env_template(self) -> str:
        """Generate .env template with all required env vars."""
        lines = ["# SCBE Service Registry — Required Environment Variables", ""]
        seen = set()
        for svc in self._services.values():
            for env in svc.credentials_env:
                if env not in seen:
                    seen.add(env)
                    lines.append(f"# {svc.name} ({svc.provider})")
                    lines.append(f"{env}=")
                    lines.append("")
        return "\n".join(lines)


# ==========================================================================
# CLI
# ==========================================================================

def _cli():
    import argparse

    parser = argparse.ArgumentParser(description="SCBE Service Registry")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show all services and their status")
    sub.add_parser("health", help="Run health checks on all configured services")
    sub.add_parser("list", help="List all registered services")
    sub.add_parser("env-template", help="Generate .env template")

    p_enable = sub.add_parser("enable", help="Show setup instructions for a service")
    p_enable.add_argument("service")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    registry = ServiceRegistry()

    if args.command == "status":
        print(registry.status_report())

    elif args.command == "health":
        results = registry.health_check_all()
        for name, (status, msg) in sorted(results.items()):
            icon = {"connected": "OK", "error": "!!", "missing": "  ", "configured": "--"}.get(status.value, "??")
            print(f"  [{icon}] {name:30s} {msg}")

    elif args.command == "list":
        for svc in registry.list_services():
            print(f"  {svc.name:30s} [{svc.category.value:10s}] {svc.provider}")
            if svc.capabilities:
                print(f"    Capabilities: {', '.join(svc.capabilities)}")

    elif args.command == "env-template":
        print(registry.env_template())

    elif args.command == "enable":
        svc = registry.get(args.service)
        if not svc:
            # Try partial match
            matches = [s for s in registry.list_services() if args.service in s.name]
            if matches:
                svc = matches[0]
        if svc:
            print(f"\n{svc.name} ({svc.provider})")
            print(f"Category: {svc.category.value}")
            print(f"Status: {svc.status.value}")
            print(f"Capabilities: {', '.join(svc.capabilities)}")
            if svc.notes:
                print(f"Notes: {svc.notes}")
            if svc.credentials_env:
                print(f"\nRequired env vars:")
                for env in svc.credentials_env:
                    val = os.environ.get(env, "")
                    status = "SET" if val else "NOT SET"
                    print(f"  {env} = [{status}]")
        else:
            print(f"Service '{args.service}' not found")


if __name__ == "__main__":
    _cli()
