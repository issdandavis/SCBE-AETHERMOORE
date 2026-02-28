"""ORCID source adapter for the Obsidian researcher agent.

Queries the ORCID public API (https://pub.orcid.org/v3.0/) for
researcher profiles, publications, and works.

ORCID is the de-facto academic identity system. This connector:
- Pulls publication records from an ORCID profile
- Pushes work metadata back to ORCID (requires member API)
- Cross-references with arXiv, DOI, and USPTO identifiers

No API key required for public read access.
Member API (write) requires ORCID OAuth credentials.

@layer Layer 1 (identity), Layer 14 (telemetry)
@component ResearchPipeline.ORCID
"""

from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

from ..source_adapter import IngestionResult, SourceAdapter, SourceType

logger = logging.getLogger(__name__)

_PUB_API_BASE = "https://pub.orcid.org/v3.0"
_USER_AGENT = "SCBE-AETHERMOORE/1.0 (mailto:issdandavis7795@aethermoorgames.com)"
_DEFAULT_TIMEOUT = 15


class ORCIDSource(SourceAdapter):
    """Adapter that queries the ORCID public API and emits
    IngestionResult records for publication tracking and indexing.

    Parameters
    ----------
    config : dict
        Optional keys:

        * ``orcid_id``  -- ORCID iD to query (default: env ORCID_ID
          or 0009-0002-3936-9369)
        * ``timeout``   -- HTTP timeout in seconds (default 15)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(source_type=SourceType.WEB, config=config or {})
        self._orcid_id: str = self.config.get(
            "orcid_id",
            os.environ.get("ORCID_ID", "0009-0002-3936-9369"),
        )
        self._timeout: int = int(self.config.get("timeout", _DEFAULT_TIMEOUT))

    def _get_json(self, url: str) -> Optional[Any]:
        """GET request returning parsed JSON."""
        headers = {
            "User-Agent": _USER_AGENT,
            "Accept": "application/json",
        }
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return json.loads(resp.read())
        except (urllib.error.URLError, urllib.error.HTTPError) as exc:
            logger.warning("ORCID HTTP error for %s: %s", url, exc)
            return None
        except Exception:
            logger.exception("ORCID unexpected error for %s", url)
            return None

    def fetch_profile(self, orcid_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch the full ORCID profile record."""
        oid = orcid_id or self._orcid_id
        url = f"{_PUB_API_BASE}/{oid}/record"
        data = self._get_json(url)
        if not data:
            return None

        # Extract key fields
        person = data.get("person", {})
        name_data = person.get("name", {})
        given = name_data.get("given-names", {}).get("value", "")
        family = name_data.get("family-name", {}).get("value", "")

        emails = []
        email_data = person.get("emails", {}).get("email", [])
        for e in email_data:
            if isinstance(e, dict) and e.get("email"):
                emails.append(e["email"])

        return {
            "orcid_id": oid,
            "name": f"{given} {family}".strip(),
            "given_name": given,
            "family_name": family,
            "emails": emails,
            "url": f"https://orcid.org/{oid}",
        }

    def fetch_works(self, orcid_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch all works (publications) from an ORCID profile."""
        oid = orcid_id or self._orcid_id
        url = f"{_PUB_API_BASE}/{oid}/works"
        data = self._get_json(url)
        if not data:
            return []

        works = []
        groups = data.get("group", [])
        for group in groups:
            summaries = group.get("work-summary", [])
            if not summaries:
                continue
            summary = summaries[0]  # Take the preferred source

            title_obj = summary.get("title", {})
            title = ""
            if title_obj.get("title"):
                title = title_obj["title"].get("value", "")

            # Extract external identifiers (DOI, arXiv, etc.)
            ext_ids = {}
            ext_id_list = summary.get("external-ids", {}).get("external-id", [])
            for eid in ext_id_list:
                id_type = eid.get("external-id-type", "")
                id_value = eid.get("external-id-value", "")
                if id_type and id_value:
                    ext_ids[id_type] = id_value

            pub_date = ""
            pub_date_obj = summary.get("publication-date", {})
            if pub_date_obj:
                year = pub_date_obj.get("year", {}).get("value", "")
                month = pub_date_obj.get("month", {}).get("value", "")
                day = pub_date_obj.get("day", {}).get("value", "")
                parts = [p for p in [year, month, day] if p]
                pub_date = "-".join(parts)

            work_type = summary.get("type", "")
            put_code = summary.get("put-code", "")

            works.append({
                "title": title,
                "type": work_type,
                "publication_date": pub_date,
                "external_ids": ext_ids,
                "put_code": put_code,
                "journal": summary.get("journal-title", {}).get("value", "") if summary.get("journal-title") else "",
                "url": summary.get("url", {}).get("value", "") if summary.get("url") else "",
            })

        return works

    def fetch(self, query: str, **kwargs: Any) -> List[IngestionResult]:
        """Fetch works from ORCID and filter by query string."""
        works = self.fetch_works(kwargs.get("orcid_id"))
        results = []
        query_lower = query.lower()

        for work in works:
            title = work.get("title", "")
            if query_lower and query_lower not in title.lower():
                continue

            identifiers = dict(work.get("external_ids", {}))
            identifiers["orcid_put_code"] = str(work.get("put_code", ""))

            tags = [f"orcid:{self._orcid_id}"]
            if work.get("type"):
                tags.append(f"work_type:{work['type']}")

            results.append(IngestionResult(
                source_type=SourceType.WEB,
                raw_content=title,
                title=title,
                authors=[],  # Not available in works summary
                url=work.get("url", f"https://orcid.org/{self._orcid_id}"),
                timestamp=work.get("publication_date", ""),
                identifiers=identifiers,
                tags=tags,
                metadata={
                    "journal": work.get("journal", ""),
                    "work_type": work.get("type", ""),
                    "orcid_id": self._orcid_id,
                },
                summary=title,
            ))

        return results

    def fetch_by_id(self, identifier: str) -> Optional[IngestionResult]:
        """Fetch a specific work by put-code."""
        url = f"{_PUB_API_BASE}/{self._orcid_id}/work/{identifier}"
        data = self._get_json(url)
        if not data:
            return None

        title_obj = data.get("title", {})
        title = title_obj.get("title", {}).get("value", "") if title_obj else ""

        return IngestionResult(
            source_type=SourceType.WEB,
            raw_content=json.dumps(data, indent=2),
            title=title,
            authors=[],
            url=f"https://orcid.org/{self._orcid_id}",
            timestamp="",
            identifiers={"orcid_put_code": str(identifier)},
            tags=[f"orcid:{self._orcid_id}"],
            metadata=data,
            summary=title,
        )

    def health_check(self) -> bool:
        """Verify ORCID API is reachable."""
        url = f"{_PUB_API_BASE}/{self._orcid_id}/record"
        try:
            data = self._get_json(url)
            return data is not None
        except Exception:
            return False
