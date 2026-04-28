#!/usr/bin/env python3
"""MATHBAC PA-26-05 amendment watch — diff live SAM.gov resource list vs. sealed baseline.

Baseline is sealed at 2026-04-27 from artifacts/mathbac/sam_resources_raw.json (11
attachments, opportunityId 3b5f6dd94f45409b8b7995c83e4e7f94). Any size, postedDate,
name, fileExists, deletedFlag, or attachment-set delta is a material change that
requires re-running the compliance checklist.

Exit codes:
  0 - no material change
  1 - material change detected (report written; review required)
  2 - fetch failed (network / auth / endpoint)

Usage:
  python scripts/mathbac_amendment_watch.py                        # live fetch (needs SAM_GOV_API_KEY)
  python scripts/mathbac_amendment_watch.py --snapshot path.json   # compare offline snapshot
  python scripts/mathbac_amendment_watch.py --baseline other.json  # override baseline
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASELINE = REPO_ROOT / "artifacts" / "mathbac" / "sam_resources_raw.json"
DEFAULT_PA_PDF = REPO_ROOT / "artifacts" / "mathbac" / "sam_pa_26_05_attachments" / "DARPA-PA-26-05.pdf"
REPORT_DIR = REPO_ROOT / "artifacts" / "mathbac" / "amendment_watch"
OPPORTUNITY_ID = "3b5f6dd94f45409b8b7995c83e4e7f94"
PA_PDF_BASELINE_SIZE = 750447
SEARCH_URL = "https://api.sam.gov/opportunities/v2/search"
_RESOURCE_ID_RE = re.compile(r"/resources/files/([0-9a-f]{32})/download", re.IGNORECASE)

MATERIAL_FIELDS = ("name", "size", "postedDate", "fileExists", "deletedFlag", "deletedDate", "mimeType")


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _api_key() -> Optional[str]:
    for env_name in ("SAM_GOV_API_KEY", "DATA_GOV_API_KEY"):
        value = (os.getenv(env_name) or "").strip()
        if value:
            return value
    return None


def fetch_live_resources(opportunity_id: str, api_key: str, timeout: int = 30) -> Dict[str, Any]:
    """Fetch the live opportunity record via the public v2 search API and synthesize a
    baseline-shaped payload from `resourceLinks`.

    The legacy `prod/opps/v3/opportunities/{oid}/resources` endpoint is internal-only and
    returns 404 from the public host. v2 search exposes `resourceLinks` (one download URL
    per attachment) — the resourceId is embedded in the URL path. We diff at the
    resourceId-set level; per-attachment metadata fields (size/postedDate/mimeType) are
    not surfaced by the public API and are omitted from synthesized records, so the
    field-level diff in live mode degrades to a set-based diff (added/removed only).
    """
    params = {"noticeid": opportunity_id, "limit": "1", "api_key": api_key}
    request = Request(f"{SEARCH_URL}?{urlencode(params)}", method="GET")
    with urlopen(request, timeout=timeout) as response:
        search_payload = json.loads(response.read().decode("utf-8"))

    records = search_payload.get("opportunitiesData") or []
    if not records:
        raise URLError(f"v2 search returned no opportunitiesData for noticeid={opportunity_id}")
    opp = records[0]
    if (opp.get("noticeId") or "").lower() != opportunity_id.lower():
        raise URLError(
            f"v2 search returned mismatched noticeId={opp.get('noticeId')!r} "
            f"(expected {opportunity_id})"
        )

    resource_links: List[str] = list(opp.get("resourceLinks") or [])
    attachments: List[Dict[str, Any]] = []
    for link in resource_links:
        m = _RESOURCE_ID_RE.search(link)
        if not m:
            continue
        rid = m.group(1)
        attachments.append({"attachmentId": rid, "resourceId": rid, "downloadUrl": link})

    return {
        "_embedded": {
            "opportunityAttachmentList": [
                {"opportunityId": opportunity_id, "attachments": attachments},
            ]
        },
        "_fetch": {
            "source": "v2-search-resource-links",
            "endpoint": SEARCH_URL,
            "noticeId": opp.get("noticeId"),
            "postedDate": opp.get("postedDate"),
            "archiveDate": opp.get("archiveDate"),
            "responseDeadLine": opp.get("responseDeadLine"),
            "active": opp.get("active"),
            "resource_link_count": len(resource_links),
        },
    }


def extract_attachments(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    embedded = payload.get("_embedded") or {}
    opp_list = embedded.get("opportunityAttachmentList") or []
    out: List[Dict[str, Any]] = []
    for entry in opp_list:
        for att in entry.get("attachments") or []:
            out.append(att)
    return out


def index_by_id(attachments: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Index attachments by `resourceId` (preferred — exposed by both the sealed baseline
    and the public v2-search resourceLinks) with `attachmentId` as fallback. The legacy
    internal-only resources endpoint surfaced both ids; the public v2 search exposes only
    resourceId via the download URL path."""
    out: Dict[str, Dict[str, Any]] = {}
    for att in attachments:
        key = att.get("resourceId") or att.get("attachmentId")
        if key:
            out[key] = att
    return out


def diff_attachments(baseline: Dict[str, Dict[str, Any]], current: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    added = sorted(set(current) - set(baseline))
    removed = sorted(set(baseline) - set(current))
    changed: Dict[str, Dict[str, Tuple[Any, Any]]] = {}
    for att_id in sorted(set(baseline) & set(current)):
        b = baseline[att_id]
        c = current[att_id]
        deltas: Dict[str, Tuple[Any, Any]] = {}
        for f in MATERIAL_FIELDS:
            bv = b.get(f)
            cv = c.get(f)
            # Treat "field absent on either side" as not-observed; only flag when both
            # sides report a value AND those values differ. v2-search-derived current
            # records carry only attachmentId/resourceId, so per-field diff is silent
            # for the live path and only added/removed signal change.
            if bv is None or cv is None:
                continue
            if bv != cv:
                deltas[f] = (bv, cv)
        if deltas:
            changed[att_id] = deltas
    return {"added": added, "removed": removed, "changed": changed}


def hash_local_pa_pdf(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"present": False, "path": str(path), "sha256": None, "size": None}
    raw = path.read_bytes()
    return {
        "present": True,
        "path": str(path),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size": len(raw),
        "size_matches_baseline": len(raw) == PA_PDF_BASELINE_SIZE,
    }


def write_report(report: Dict[str, Any]) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    out = REPORT_DIR / f"amendment_watch_{_utc_stamp()}.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Watch DARPA-PA-26-05 for SAM.gov amendments")
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE,
                        help="Sealed baseline JSON (default: artifacts/mathbac/sam_resources_raw.json)")
    parser.add_argument("--snapshot", type=Path, default=None,
                        help="Offline snapshot JSON to diff against baseline (skips live fetch)")
    parser.add_argument("--opportunity-id", default=OPPORTUNITY_ID,
                        help=f"SAM.gov opportunity id (default: {OPPORTUNITY_ID})")
    parser.add_argument("--pa-pdf", type=Path, default=DEFAULT_PA_PDF,
                        help="Local working copy of DARPA-PA-26-05.pdf")
    parser.add_argument("--quiet", action="store_true", help="Only emit report path on stdout")
    args = parser.parse_args()

    if not args.baseline.exists():
        print(f"ERROR: baseline not found: {args.baseline}", file=sys.stderr)
        return 2

    baseline_payload = json.loads(args.baseline.read_text(encoding="utf-8"))
    baseline_attachments = index_by_id(extract_attachments(baseline_payload))

    if args.snapshot is not None:
        if not args.snapshot.exists():
            print(f"ERROR: snapshot not found: {args.snapshot}", file=sys.stderr)
            return 2
        current_payload = json.loads(args.snapshot.read_text(encoding="utf-8"))
        fetch_mode = "snapshot"
        fetch_error: Optional[str] = None
    else:
        api_key = _api_key()
        if not api_key:
            print("ERROR: SAM_GOV_API_KEY / DATA_GOV_API_KEY not set; pass --snapshot for offline diff",
                  file=sys.stderr)
            return 2
        try:
            current_payload = fetch_live_resources(args.opportunity_id, api_key)
            fetch_mode = "live"
            fetch_error = None
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            print(f"SAM.gov returned HTTP {exc.code}: {body}", file=sys.stderr)
            return 2
        except URLError as exc:
            print(f"SAM.gov fetch failed: {exc}", file=sys.stderr)
            return 2

    current_attachments = index_by_id(extract_attachments(current_payload))
    diff = diff_attachments(baseline_attachments, current_attachments)
    pa_pdf_state = hash_local_pa_pdf(args.pa_pdf)

    material = bool(diff["added"] or diff["removed"] or diff["changed"])
    deadline_warning_days = 50  # 2026-04-27 -> 2026-06-16
    fetch_meta = current_payload.get("_fetch") if isinstance(current_payload, dict) else None

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "opportunity_id": args.opportunity_id,
        "solicitation": "DARPA-PA-26-05 (MATHBAC)",
        "due": "2026-06-16T16:00:00-04:00",
        "fetch_mode": fetch_mode,
        "fetch_meta": fetch_meta,
        "baseline_path": str(args.baseline),
        "baseline_attachment_count": len(baseline_attachments),
        "current_attachment_count": len(current_attachments),
        "material_change": material,
        "diff": diff,
        "pa_pdf_local": pa_pdf_state,
        "follow_up_actions": [
            "If diff.added is non-empty: fetch new attachment, update PA_26_05_compliance_checklist_v1.md",
            "If diff.removed is non-empty: confirm intent (deprecation vs. amendment); flag in spine doc",
            "If diff.changed contains 'size' or 'postedDate': re-download attachment, re-seal SHA-256",
            "If pa_pdf_local.size_matches_baseline is false: working copy is stale, re-pull from SAM.gov",
            f"If days_to_due < {deadline_warning_days}: prioritize amendment review same-day",
        ],
    }

    out_path = write_report(report)

    if args.quiet:
        print(out_path)
    else:
        print(f"[mathbac-amendment-watch] mode={fetch_mode} material_change={material}")
        print(f"  baseline_count={len(baseline_attachments)} current_count={len(current_attachments)}")
        if diff["added"]:
            print(f"  ADDED: {len(diff['added'])} -> {diff['added']}")
        if diff["removed"]:
            print(f"  REMOVED: {len(diff['removed'])} -> {diff['removed']}")
        if diff["changed"]:
            print(f"  CHANGED: {len(diff['changed'])} attachment(s)")
            for att_id, deltas in diff["changed"].items():
                name = (baseline_attachments.get(att_id) or current_attachments.get(att_id) or {}).get("name", "?")
                print(f"    - {att_id} ({name}): {sorted(deltas.keys())}")
        if pa_pdf_state["present"] and not pa_pdf_state.get("size_matches_baseline", True):
            print(f"  WARN: local PA PDF size {pa_pdf_state['size']} != baseline {PA_PDF_BASELINE_SIZE}")
        print(f"  report: {out_path}")

    return 1 if material else 0


if __name__ == "__main__":
    sys.exit(main())
