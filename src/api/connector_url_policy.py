"""Outbound URL policy for explicitly configured mobile connectors.

Public https endpoints such as Zapier hooks, Shopify Admin GraphQL, and
internet-facing n8n webhooks stay valid. Loopback, private, link-local,
multicast, and cloud-metadata destinations are rejected unless an operator
opts in. Metadata addresses and hostnames stay blocked in every mode.

Environment:
    SCBE_CONNECTOR_ALLOW_PRIVATE_NETWORKS=1
        Allow loopback, RFC1918/ULA, and single-label or ``.local`` /
        ``.internal`` names. Link-local and cloud metadata stay blocked.
    SCBE_CONNECTOR_ALLOW_INSECURE_HTTP=1
        Allow the http scheme. https remains the default.

Connector dispatch ignores HTTP(S)_PROXY. A redirect is fetched only after
the same policy accepts the Location target. The connected peer is checked
again before the request body is kept; see docs/security/GHSA-7rh5-2f26-qfj7.md
for the residual DNS-rebinding window.
"""

from __future__ import annotations

import http.client
import ipaddress
import os
import re
import socket
import ssl
import urllib.request
from typing import Mapping
from urllib.parse import urlsplit, urlunsplit

_SHOP_DOMAIN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.myshopify\.com$")
_API_VERSION = re.compile(r"^[0-9]{4}-[0-9]{2}$")
_CANONICAL_IPV4 = re.compile(r"^(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)$")
_HEADER_NAME = re.compile(r"^[A-Za-z0-9-]{1,128}$")
_DNS_NAME = re.compile(
    r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"
)
_MAX_URL_LENGTH = 2048
_REDIRECT_KEEP_HEADERS = frozenset({"user-agent", "accept"})
_FORBIDDEN_HEADER_NAMES = frozenset(
    {
        "host",
        "content-length",
        "transfer-encoding",
        "connection",
        "keep-alive",
        "upgrade",
        "proxy-authorization",
        "te",
        "trailer",
    }
)
_METADATA_HOSTS = frozenset(
    {
        "metadata",
        "metadata.google.internal",
        "metadata.google.com",
        "instance-data",
        "instance-data.ec2.internal",
    }
)
_PRIVATE_ONLY_SUFFIXES = (".localhost", ".local", ".internal", ".localdomain")
_ALWAYS_BLOCKED_NETWORKS = (
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("192.0.0.0/24"),
    ipaddress.ip_network("100.100.100.200/32"),
    ipaddress.ip_network("255.255.255.255/32"),
    ipaddress.ip_network("::/128"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("fd00:ec2::254/128"),
)


class ConnectorURLRejected(ValueError):
    """A connector URL or header failed the egress policy."""

    def __init__(self, code: str, public_detail: str) -> None:
        self.code = code
        self.public_detail = public_detail
        super().__init__(public_detail)


def _env_enabled(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def allow_private_networks() -> bool:
    """Return whether explicitly configured private connector targets are enabled."""
    return _env_enabled("SCBE_CONNECTOR_ALLOW_PRIVATE_NETWORKS")


def allow_insecure_http() -> bool:
    """Return whether plain http connector targets are enabled."""
    return _env_enabled("SCBE_CONNECTOR_ALLOW_INSECURE_HTTP")


def _reject(detail: str, code: str = "connector_destination_blocked") -> None:
    raise ConnectorURLRejected(code, detail)


def address_is_blocked(
    ip: ipaddress.IPv4Address | ipaddress.IPv6Address,
    *,
    allow_private: bool | None = None,
) -> bool:
    """Return True when an address is not an acceptable connector peer.

    IPv4-mapped IPv6 answers are judged by the embedded IPv4 address. Python
    marks those mapped addresses reserved even when the IPv4 peer is public,
    and ``getaddrinfo`` can return them for ordinary https connectors.
    """
    if allow_private is None:
        allow_private = allow_private_networks()
    mapped = getattr(ip, "ipv4_mapped", None)
    if mapped is not None:
        return address_is_blocked(mapped, allow_private=allow_private)
    if any(ip in network for network in _ALWAYS_BLOCKED_NETWORKS):
        return True
    if ip.is_multicast or ip.is_unspecified or ip.is_link_local:
        return True
    if ip.is_loopback or ip.is_private or not ip.is_global:
        return not allow_private
    return False


def _parse_ip_literal(host: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    candidate = host.strip("[]")
    if not candidate:
        _reject("connector endpoint is not allowed")
    if re.fullmatch(r"\d+", candidate) or candidate.lower().startswith("0x"):
        _reject("connector endpoint is not allowed")
    if re.fullmatch(r"[0-9.]+", candidate):
        if not _CANONICAL_IPV4.fullmatch(candidate):
            _reject("connector endpoint is not allowed")
        return ipaddress.ip_address(candidate)
    try:
        return ipaddress.ip_address(candidate)
    except ValueError:
        return None


def _host_name_blocked(host: str, *, allow_private: bool) -> bool:
    normalized = host.lower().rstrip(".")
    if normalized in _METADATA_HOSTS or normalized.endswith(".metadata.google.internal"):
        return True
    if normalized == "localhost" or normalized.endswith(".localhost"):
        return not allow_private
    if not allow_private and any(normalized.endswith(suffix) for suffix in _PRIVATE_ONLY_SUFFIXES):
        return True
    return False


def _normalized_host(host: str) -> str:
    try:
        return host.encode("idna").decode("ascii").lower().rstrip(".")
    except UnicodeError:
        _reject("connector endpoint is not allowed")
        raise AssertionError("unreachable")


def validate_header_name(name: str) -> str:
    """Return a single connector header name, or reject hop-by-hop and Host overrides."""
    header_name = str(name or "").strip()
    if not _HEADER_NAME.fullmatch(header_name) or header_name.lower() in _FORBIDDEN_HEADER_NAMES:
        _reject("connector header is not allowed")
    return header_name


def sanitize_connector_headers(headers: Mapping[str, str] | None) -> dict[str, str]:
    """Copy caller headers after rejecting names that can retarget the request."""
    clean: dict[str, str] = {}
    for raw_key, raw_value in (headers or {}).items():
        key = validate_header_name(str(raw_key))
        value = str(raw_value)
        if any(ord(char) < 32 or ord(char) == 127 for char in value):
            _reject("connector header is not allowed")
        clean[key] = value
    return clean


def normalize_shop_domain(raw: str) -> str:
    """Return a bare ``<shop>.myshopify.com`` hostname, or empty when unset."""
    value = (raw or "").strip().lower()
    if not value:
        return ""
    if any(char in value for char in "\r\n\x00\\@"):
        _reject("shop_domain must be a *.myshopify.com hostname")
    if "://" in value:
        parsed = urlsplit(value)
        if parsed.scheme not in {"https", "http"} or not parsed.hostname:
            _reject("shop_domain must be a *.myshopify.com hostname")
        if parsed.username or parsed.password or parsed.port or parsed.query or parsed.fragment:
            _reject("shop_domain must be a *.myshopify.com hostname")
        if parsed.path not in {"", "/"}:
            _reject("shop_domain must be a *.myshopify.com hostname")
        value = parsed.hostname.lower()
    elif any(char in value for char in "/?#:"):
        _reject("shop_domain must be a *.myshopify.com hostname")
    value = value.rstrip(".")
    if not _SHOP_DOMAIN.fullmatch(value):
        _reject("shop_domain must be a *.myshopify.com hostname")
    return value


def build_shopify_endpoint(shop_domain: str, api_version: str) -> str:
    """Build the Admin GraphQL URL for a validated myshopify hostname."""
    domain = normalize_shop_domain(shop_domain)
    if not domain:
        return ""
    version = (api_version or "").strip()
    if not _API_VERSION.fullmatch(version):
        _reject("shopify api version is not allowed")
    return validate_connector_endpoint(
        f"https://{domain}/admin/api/{version}/graphql.json",
        resolve_dns=False,
    )


def _format_netloc(host: str, port: int | None) -> str:
    host_part = f"[{host}]" if ":" in host else host
    if port is None:
        return host_part
    return f"{host_part}:{port}"


def validate_connector_endpoint(url: str, *, resolve_dns: bool) -> str:
    """Validate a connector URL and return a normalized https (or allowed http) URL.

    DNS resolution runs only when ``resolve_dns`` is true. Registration uses the
    syntactic check so configured names can be stored before they resolve;
    dispatch resolves and rejects any answer that is not an allowed peer.
    """
    raw = (url or "").strip()
    if not raw or len(raw) > _MAX_URL_LENGTH or any(char in raw for char in "\r\n\x00\\"):
        _reject("connector endpoint is not allowed")
    parsed = urlsplit(raw)
    scheme = parsed.scheme.lower()
    if scheme == "http":
        if not allow_insecure_http():
            _reject("connector endpoint must use https")
    elif scheme != "https":
        _reject("connector endpoint is not allowed")
    if parsed.username or parsed.password or "@" in parsed.netloc:
        _reject("connector endpoint must not include credentials")
    host = parsed.hostname
    if not host:
        _reject("connector endpoint is not allowed")
    if parsed.port == 0:
        _reject("connector endpoint is not allowed")
    allow_private = allow_private_networks()
    ascii_host = _normalized_host(host)
    if _host_name_blocked(ascii_host, allow_private=allow_private):
        _reject("connector endpoint is not allowed")
    literal = _parse_ip_literal(ascii_host)
    if literal is not None:
        if address_is_blocked(literal, allow_private=allow_private):
            _reject("connector endpoint is not allowed")
    elif not allow_private and not _DNS_NAME.fullmatch(ascii_host):
        _reject("connector endpoint is not allowed")
    elif allow_private and not (_DNS_NAME.fullmatch(ascii_host) or _single_label_host(ascii_host)):
        _reject("connector endpoint is not allowed")
    if resolve_dns and literal is None:
        _reject_blocked_resolution(ascii_host, parsed.port or (443 if scheme == "https" else 80))
    path = parsed.path or "/"
    return urlunsplit((scheme, _format_netloc(ascii_host, parsed.port), path, parsed.query, ""))


def _single_label_host(host: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", host))


def _reject_blocked_resolution(host: str, port: int) -> None:
    try:
        answers = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ConnectorURLRejected("connector_network_error", "connector network error") from exc
    peers: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for *_, sockaddr in answers:
        peers.append(ipaddress.ip_address(str(sockaddr[0]).split("%", 1)[0]))
    if not peers or any(address_is_blocked(peer) for peer in peers):
        _reject("connector endpoint is not allowed")


def enforce_connected_peer(sock: socket.socket) -> None:
    """Close and reject a socket whose peer is outside the connector policy."""
    try:
        peer = sock.getpeername()
    except OSError as exc:
        sock.close()
        raise ConnectorURLRejected("connector_destination_blocked", "connector endpoint is not allowed") from exc
    ip_text = str(peer[0]).split("%", 1)[0]
    try:
        ip = ipaddress.ip_address(ip_text)
    except ValueError as exc:
        sock.close()
        raise ConnectorURLRejected("connector_destination_blocked", "connector endpoint is not allowed") from exc
    if address_is_blocked(ip):
        sock.close()
        raise ConnectorURLRejected("connector_destination_blocked", "connector endpoint is not allowed")


class _PeerCheckedHTTPConnection(http.client.HTTPConnection):
    def connect(self) -> None:
        super().connect()
        if self.sock is None:
            _reject("connector endpoint is not allowed")
        enforce_connected_peer(self.sock)


class _PeerCheckedHTTPSConnection(http.client.HTTPSConnection):
    def connect(self) -> None:
        super().connect()
        if self.sock is None:
            _reject("connector endpoint is not allowed")
        enforce_connected_peer(self.sock)


class _PolicyHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req: urllib.request.Request):
        return self.do_open(_PeerCheckedHTTPConnection, req)


class _PolicyHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req: urllib.request.Request):
        return self.do_open(_PeerCheckedHTTPSConnection, req, context=self._context or ssl.create_default_context())


def _authority(url: str) -> tuple[str, str, int | None]:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme.lower(), host, parsed.port


def _strip_cross_origin_headers(request: urllib.request.Request) -> None:
    for key in list(request.headers):
        if key.lower() not in _REDIRECT_KEEP_HEADERS:
            del request.headers[key]
    unredirected = getattr(request, "unredirected_hdrs", None)
    if isinstance(unredirected, dict):
        for key in list(unredirected):
            if key.lower() not in _REDIRECT_KEEP_HEADERS:
                del unredirected[key]


class GuardedRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Re-apply the connector policy to each redirect and drop credentials on origin changes."""

    max_redirections = 3

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = str(newurl).replace(" ", "%20")
        validate_connector_endpoint(target, resolve_dns=True)
        redirected = super().redirect_request(req, fp, code, msg, headers, target)
        if redirected is None:
            return None
        old_scheme, old_host, old_port = _authority(req.full_url)
        new_scheme, new_host, new_port = _authority(redirected.full_url)
        if (new_scheme, new_host, new_port) != (old_scheme, old_host, old_port) or new_scheme != "https":
            _strip_cross_origin_headers(redirected)
        return redirected


def build_connector_opener() -> urllib.request.OpenerDirector:
    """Build an opener that does not read process proxy variables or file/ftp handlers."""
    opener = urllib.request.OpenerDirector()
    opener.add_handler(urllib.request.ProxyHandler({}))
    opener.add_handler(urllib.request.UnknownHandler())
    opener.add_handler(_PolicyHTTPHandler())
    opener.add_handler(_PolicyHTTPSHandler())
    opener.add_handler(urllib.request.HTTPDefaultErrorHandler())
    opener.add_handler(GuardedRedirectHandler())
    opener.add_handler(urllib.request.HTTPErrorProcessor())
    return opener


def open_connector_request(req: urllib.request.Request, timeout: float):
    """Open one connector request after policy, resolution, and redirect checks."""
    normalized = validate_connector_endpoint(req.full_url, resolve_dns=True)
    if normalized != req.full_url:
        req.full_url = normalized
    return build_connector_opener().open(req, timeout=timeout)
