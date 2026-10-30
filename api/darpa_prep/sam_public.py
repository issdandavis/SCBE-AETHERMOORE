"""Dependency-free client for the SAM.gov Opportunities v2 public API.

Only documented public-search parameters are accepted. The API key is kept in
memory and deliberately omitted from errors and public query metadata.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Iterable, Mapping, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

DEFAULT_OPPORTUNITIES_URL = "https://api.sam.gov/opportunities/v2/search"
OFFICIAL_HOSTS = frozenset({"api.sam.gov", "api-alpha.sam.gov"})
OFFICIAL_PATH = "/opportunities/v2/search"
MAX_PAGE_SIZE = 1000
MAX_RESULTS = 5000


class SamGovRequestError(RuntimeError):
    """A sanitized SAM.gov request failure safe to place in CI telemetry."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _environment_api_key() -> str:
    for name in ("SAM_GOV_API_KEY", "SAM_API_KEY"):
        value = os.environ.get(name, "").strip()
        if value:
            return value
    return ""


def validate_official_endpoint(value: str) -> str:
    """Reject endpoint overrides that could receive the API key."""

    candidate = value.strip().rstrip("/")
    parsed = urlsplit(candidate)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("SAM.gov endpoint must be the official HTTPS Opportunities v2 search endpoint") from exc
    if (
        parsed.scheme != "https"
        or parsed.hostname not in OFFICIAL_HOSTS
        or port not in (None, 443)
        or parsed.path != OFFICIAL_PATH
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
    ):
        raise ValueError("SAM.gov endpoint must be the official HTTPS Opportunities v2 search endpoint")
    return candidate


def _parse_date(value: str, *, field: str) -> date:
    try:
        return datetime.strptime(value, "%m/%d/%Y").date()
    except ValueError as exc:
        raise ValueError(f"{field} must use MM/DD/YYYY") from exc


def _date_window(
    *,
    days_back: int,
    posted_from: str | None,
    posted_to: str | None,
) -> tuple[str, str]:
    if (posted_from is None) != (posted_to is None):
        raise ValueError("posted_from and posted_to must be supplied together")
    if posted_from is not None and posted_to is not None:
        start = _parse_date(posted_from, field="posted_from")
        end = _parse_date(posted_to, field="posted_to")
    else:
        if not 0 <= days_back <= 365:
            raise ValueError("days_back must be between 0 and 365")
        end = datetime.now(UTC).date()
        start = end - timedelta(days=days_back)
    if start > end:
        raise ValueError("posted_from cannot be later than posted_to")
    if (end - start).days > 365:
        raise ValueError("SAM.gov posted-date windows cannot exceed one year")
    return start.strftime("%m/%d/%Y"), end.strftime("%m/%d/%Y")


def _clean_notice_types(values: str | Sequence[str] | None) -> list[str]:
    if values is None:
        return []
    raw_values = [values] if isinstance(values, str) else list(values)
    allowed = {"u", "p", "a", "r", "s", "o", "g", "k", "i"}
    cleaned: list[str] = []
    for raw in raw_values:
        for item in str(raw).split(","):
            code = item.strip().lower()
            if not code:
                continue
            if code not in allowed:
                raise ValueError(f"unsupported SAM.gov opportunity type: {code}")
            if code not in cleaned:
                cleaned.append(code)
    return cleaned


def _dedupe_key(row: Mapping[str, Any]) -> str:
    notice_id = str(row.get("noticeId") or "").strip()
    if notice_id:
        return f"notice:{notice_id}"
    parts = (
        row.get("solicitationNumber"),
        row.get("title"),
        row.get("postedDate"),
        row.get("fullParentPathCode"),
    )
    return "fallback:" + "|".join(str(value or "").strip() for value in parts)


def _is_active(row: Mapping[str, Any]) -> bool:
    value = str(row.get("active") or "").strip().lower()
    return value not in {"no", "false", "inactive", "archived", "cancelled", "deleted"}


@dataclass
class SamGovPublicClient:
    api_key: str | None = None
    base_url: str = DEFAULT_OPPORTUNITIES_URL
    timeout_seconds: int = 30

    def __post_init__(self) -> None:
        self.api_key = (self.api_key or _environment_api_key()).strip() or None
        override = os.environ.get("SAM_GOV_OPPORTUNITIES_URL", "").strip()
        self.base_url = validate_official_endpoint(override or self.base_url)
        if not 1 <= int(self.timeout_seconds) <= 120:
            raise ValueError("timeout_seconds must be between 1 and 120")

    def build_query(
        self,
        *,
        query: str = "",
        limit: int = 10,
        offset: int = 0,
        days_back: int = 180,
        posted_from: str | None = None,
        posted_to: str | None = None,
        notice_types: str | Sequence[str] | None = None,
        naics_code: str | None = None,
        organization_name: str | None = None,
        organization_code: str | None = None,
        state: str | None = None,
        set_aside: str | None = None,
        response_deadline_from: str | None = None,
        response_deadline_to: str | None = None,
        include_api_key: bool = False,
    ) -> list[tuple[str, str]]:
        """Build an ordered query using only documented Opportunities v2 names."""

        start, end = _date_window(days_back=days_back, posted_from=posted_from, posted_to=posted_to)
        bounded_limit = int(limit)
        if not 1 <= bounded_limit <= MAX_PAGE_SIZE:
            raise ValueError(f"limit must be between 1 and {MAX_PAGE_SIZE}")
        if int(offset) < 0:
            raise ValueError("offset cannot be negative")

        params: list[tuple[str, str]] = [
            ("postedFrom", start),
            ("postedTo", end),
            ("limit", str(bounded_limit)),
            ("offset", str(int(offset))),
        ]
        clean_query = query.strip()
        if len(clean_query) > 500:
            raise ValueError("query cannot exceed 500 characters")
        if clean_query:
            params.append(("title", clean_query))
        for notice_type in _clean_notice_types(notice_types):
            params.append(("ptype", notice_type))

        optional = {
            "ncode": naics_code,
            "organizationName": organization_name,
            "organizationCode": organization_code,
            "state": state,
            "typeOfSetAside": set_aside,
            "rdlfrom": response_deadline_from,
            "rdlto": response_deadline_to,
        }
        for name, value in optional.items():
            if value is not None and str(value).strip():
                clean_value = str(value).strip()
                if len(clean_value) > 500:
                    raise ValueError(f"{name} cannot exceed 500 characters")
                params.append((name, clean_value))

        if response_deadline_from:
            _parse_date(response_deadline_from, field="response_deadline_from")
        if response_deadline_to:
            _parse_date(response_deadline_to, field="response_deadline_to")
        if naics_code and (not str(naics_code).isdigit() or len(str(naics_code)) > 6):
            raise ValueError("naics_code must contain at most six digits")
        if state and len(str(state).strip()) != 2:
            raise ValueError("state must be a two-letter code")

        if include_api_key:
            if not self.api_key:
                raise ValueError("SAM_GOV_API_KEY or SAM_API_KEY is not configured")
            params.append(("api_key", self.api_key))
        return params

    def public_query(self, **kwargs: Any) -> dict[str, Any]:
        """Return persisted query metadata with no credential material."""

        pairs = self.build_query(include_api_key=False, **kwargs)
        output: dict[str, Any] = {}
        for name, value in pairs:
            if name in output:
                current = output[name]
                output[name] = current + [value] if isinstance(current, list) else [current, value]
            else:
                output[name] = value
        return output

    def _request_page(self, pairs: Iterable[tuple[str, str]]) -> dict[str, Any]:
        if not self.api_key:
            raise ValueError("SAM_GOV_API_KEY or SAM_API_KEY is not configured")
        request_pairs = list(pairs) + [("api_key", self.api_key)]
        request = Request(
            f"{self.base_url}?{urlencode(request_pairs, doseq=True)}",
            headers={"Accept": "application/json", "User-Agent": "SCBE-AETHERMOORE sam-public/2.0"},
            method="GET",
        )
        try:
            with urlopen(
                request, timeout=int(self.timeout_seconds)
            ) as response:  # noqa: S310 - validated official host
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code == 404:
                return {"opportunitiesData": [], "totalRecords": 0}
            if exc.code == 401:
                message = "SAM.gov request failed with HTTP 401 (API key missing, invalid, or expired)"
            elif exc.code == 403:
                message = "SAM.gov request failed with HTTP 403 (not authorized or rate limited)"
            else:
                message = f"SAM.gov request failed with HTTP {exc.code}"
            raise SamGovRequestError(message, status_code=exc.code) from exc
        except URLError as exc:
            raise SamGovRequestError("SAM.gov request failed because the service was unreachable") from exc
        except (TimeoutError, OSError) as exc:
            raise SamGovRequestError("SAM.gov request failed because the service was unreachable") from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise SamGovRequestError("SAM.gov returned an invalid JSON response") from exc

        if not isinstance(payload, dict):
            raise SamGovRequestError("SAM.gov returned an unexpected response shape")
        rows = payload.get("opportunitiesData", [])
        if rows is not None and not isinstance(rows, list):
            raise SamGovRequestError("SAM.gov returned an invalid opportunitiesData field")
        return payload

    def search_opportunities(
        self,
        *,
        query: str = "",
        limit: int = 10,
        active_only: bool = True,
        days_back: int = 180,
        posted_from: str | None = None,
        posted_to: str | None = None,
        notice_types: str | Sequence[str] | None = None,
        naics_code: str | None = None,
        organization_name: str | None = None,
        organization_code: str | None = None,
        state: str | None = None,
        set_aside: str | None = None,
        response_deadline_from: str | None = None,
        response_deadline_to: str | None = None,
    ) -> list[dict[str, Any]]:
        requested = int(limit)
        if not 1 <= requested <= MAX_RESULTS:
            raise ValueError(f"limit must be between 1 and {MAX_RESULTS}")

        common = {
            "query": query,
            "days_back": days_back,
            "posted_from": posted_from,
            "posted_to": posted_to,
            "notice_types": notice_types,
            "naics_code": naics_code,
            "organization_name": organization_name,
            "organization_code": organization_code,
            "state": state,
            "set_aside": set_aside,
            "response_deadline_from": response_deadline_from,
            "response_deadline_to": response_deadline_to,
        }
        found: list[dict[str, Any]] = []
        seen: set[str] = set()
        offset = 0

        while len(found) < requested:
            page_size = min(MAX_PAGE_SIZE, requested - len(found))
            pairs = self.build_query(limit=page_size, offset=offset, include_api_key=False, **common)
            payload = self._request_page(pairs)
            rows = payload.get("opportunitiesData") or []
            if not rows:
                break

            added = 0
            for raw in rows:
                if not isinstance(raw, dict) or (active_only and not _is_active(raw)):
                    continue
                key = _dedupe_key(raw)
                if key in seen:
                    continue
                seen.add(key)
                found.append(raw)
                added += 1
                if len(found) >= requested:
                    break

            total_records = payload.get("totalRecords")
            try:
                total = int(total_records)
            except (TypeError, ValueError):
                total = None
            if len(rows) < page_size or (total is not None and len(seen) >= total) or added == 0:
                break
            # The SAM.gov contract describes offset as a page index.
            offset += 1

        return found
