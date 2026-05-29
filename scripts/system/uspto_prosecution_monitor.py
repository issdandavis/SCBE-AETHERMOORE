#!/usr/bin/env python3
"""
USPTO prosecution monitor — Patent File Wrapper + Office Action Rejections.

APIs:
  Patent File Wrapper  https://api.uspto.gov/api/v1/patent/applications/search
  OA Rejections        https://api.uspto.gov/api/v1/patent/oa/oa_actions/v1/records

Diffs against a saved state snapshot.
Exit 0 = no changes, 1 = changes found, 2 = fetch error.

Usage:
    python scripts/system/uspto_prosecution_monitor.py --app 18045436
    python scripts/system/uspto_prosecution_monitor.py --app 18045436 --api-key KEY

    # Use env var instead of flag:
    set USPTO_ODP_API_KEY=your_key
    python scripts/system/uspto_prosecution_monitor.py --app 18045436

    # Reset baseline after deliberate state change:
    python scripts/system/uspto_prosecution_monitor.py --app 18045436 --reset

State file: artifacts/patent_monitor/<app_number>_state.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PFW_URL = "https://api.uspto.gov/api/v1/patent/applications/search"
OA_URL  = "https://api.uspto.gov/api/v1/patent/oa/oa_actions/v1/records"
STATE_DIR = Path(__file__).parent.parent.parent / "artifacts" / "patent_monitor"

# Document codes → human labels
DOC_CODE_LABELS = {
    "CTNF": "Non-Final Action",
    "CTFR": "Final Action",
    "NOA":  "Notice of Allowance",
    "N271": "§ 371(c) Notice",
    "SRNT": "Search Report",
}

# SCBE-specific rejection risk flags
ALICE_RISK_FIELDS = ("aliceIndicator", "bilskiIndicator", "mayoIndicator", "myriadIndicator")


# ---------------------------------------------------------------------------
#  HTTP helper
# ---------------------------------------------------------------------------

def _get_json(url: str, params: Dict, api_key: Optional[str]) -> Optional[Dict]:
    full = f"{url}?{urlencode(params)}"
    headers = {"Accept": "application/json"}
    if api_key:
        headers["X-API-KEY"] = api_key
    try:
        with urlopen(Request(full, headers=headers), timeout=30) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        print(f"[ERROR] HTTP {e.code}: {e.reason}  ({full})", file=sys.stderr)
    except URLError as e:
        print(f"[ERROR] Network: {e.reason}", file=sys.stderr)
    return None


# ---------------------------------------------------------------------------
#  Patent File Wrapper fetch
# ---------------------------------------------------------------------------

def fetch_file_wrapper(app_number: str, api_key: Optional[str]) -> Optional[Dict]:
    data = _get_json(PFW_URL, {"q": f"applicationNumberText:{app_number}", "rows": 1}, api_key)
    if not data:
        return None
    bag = data.get("patentFileWrapperDataBag", [])
    if not bag:
        print(f"[WARN] No file wrapper record for {app_number}", file=sys.stderr)
        return None
    return bag[0]


# ---------------------------------------------------------------------------
#  OA Rejections fetch
# ---------------------------------------------------------------------------

def fetch_oa_rejections(app_number: str, api_key: Optional[str]) -> List[Dict]:
    data = _get_json(OA_URL, {"patentApplicationNumber": app_number, "rows": 50}, api_key)
    if not data:
        return []
    return data.get("response", {}).get("docs", [])


# ---------------------------------------------------------------------------
#  State persistence
# ---------------------------------------------------------------------------

def _state_path(app_number: str) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / f"{app_number}_state.json"


def load_state(app_number: str) -> Optional[Dict]:
    p = _state_path(app_number)
    return json.loads(p.read_text("utf-8")) if p.exists() else None


def save_state(app_number: str, wrapper: Dict, oa_docs: List[Dict]) -> None:
    snap = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "wrapper": wrapper,
        "oa_docs": oa_docs,
    }
    _state_path(app_number).write_text(json.dumps(snap, indent=2, default=str), "utf-8")


# ---------------------------------------------------------------------------
#  Diffing
# ---------------------------------------------------------------------------

def _wrapper_key_fields(wrapper: Dict) -> Dict[str, Any]:
    meta = wrapper.get("applicationMetaData", {})
    events: List[Dict] = wrapper.get("eventDataBag", [])
    return {
        "status_code":  meta.get("applicationStatusCode"),
        "status_text":  meta.get("applicationStatusDescriptionText"),
        "status_date":  meta.get("applicationStatusDate"),
        "examiner":     meta.get("examinerNameText"),
        "art_unit":     meta.get("groupArtUnitNumber"),
        "grant_date":   meta.get("grantDate"),
        "patent_number":meta.get("patentNumber"),
        "events": sorted(
            (e.get("eventDate",""), e.get("eventCode",""), e.get("eventDescriptionText",""))
            for e in events
        ),
    }


def _oa_fingerprint(doc: Dict) -> Tuple:
    return (
        doc.get("submissionDate", ""),
        doc.get("legacyDocumentCodeIdentifier", ""),
        doc.get("legalSectionCode", ""),
        ",".join(doc.get("claimNumberArrayDocument", [])),
    )


def diff_state(old: Dict, new_wrapper: Dict, new_oa: List[Dict]) -> List[str]:
    changes: List[str] = []

    # File wrapper diff
    of = _wrapper_key_fields(old["wrapper"])
    nf = _wrapper_key_fields(new_wrapper)
    for key, label in [
        ("status_code","Status code"), ("status_text","Status"),
        ("status_date","Status date"), ("examiner","Examiner"),
        ("art_unit","Art unit"), ("grant_date","Grant date"),
        ("patent_number","Patent number"),
    ]:
        if of.get(key) != nf.get(key):
            changes.append(f"  {label}: {of.get(key)!r} → {nf.get(key)!r}")
    old_evts = set(map(tuple, of["events"]))
    new_evts = set(map(tuple, nf["events"]))
    for date, code, desc in sorted(new_evts - old_evts):
        changes.append(f"  NEW EVENT  [{date}] {code}: {desc}")
    for date, code, desc in sorted(old_evts - new_evts):
        changes.append(f"  GONE EVENT [{date}] {code}: {desc}")

    # OA rejections diff
    old_oa_fps = {_oa_fingerprint(d) for d in old.get("oa_docs", [])}
    new_oa_fps = {_oa_fingerprint(d) for d in new_oa}
    for fp in sorted(new_oa_fps - old_oa_fps):
        date, code, section, claims = fp
        label = DOC_CODE_LABELS.get(code, code)
        changes.append(f"  NEW OA     [{date}] {label} § {section}  claims: {claims}")
    for fp in sorted(old_oa_fps - new_oa_fps):
        date, code, section, claims = fp
        changes.append(f"  GONE OA    [{date}] {code} § {section}  claims: {claims}")

    return changes


# ---------------------------------------------------------------------------
#  Summary printer
# ---------------------------------------------------------------------------

def _rej_flags(doc: Dict) -> str:
    flags = []
    if doc.get("hasRej101"): flags.append("§101")
    if doc.get("hasRej102"): flags.append("§102")
    if doc.get("hasRej103"): flags.append("§103")
    if doc.get("hasRej112"): flags.append("§112")
    if any(doc.get(f) for f in ALICE_RISK_FIELDS): flags.append("ALICE")
    return " ".join(flags) if flags else "—"


def print_summary(
    wrapper: Dict,
    oa_docs: List[Dict],
    changes: Optional[List[str]] = None,
) -> None:
    meta  = wrapper.get("applicationMetaData", {})
    events: List[Dict] = wrapper.get("eventDataBag", [])
    children = wrapper.get("childContinuityBag", [])

    W = 62
    print(f"\n{'='*W}")
    print(f"Application : {wrapper.get('applicationNumberText')}")
    print(f"Title       : {meta.get('inventionTitle','—')[:W-14]}")
    print(f"Status      : [{meta.get('applicationStatusCode')}] {meta.get('applicationStatusDescriptionText')}")
    print(f"Status date : {meta.get('applicationStatusDate')}")
    print(f"Examiner    : {meta.get('examinerNameText','—')}  (AU {meta.get('groupArtUnitNumber','—')})")
    print(f"Entity      : {meta.get('entityStatusData',{}).get('businessEntityStatusCategory','—')}")
    if meta.get("patentNumber"):
        print(f"Patent No.  : {meta['patentNumber']}  (granted {meta.get('grantDate')})")

    # Events (most recent first)
    if events:
        print(f"\nEvents ({len(events)} total, 8 shown):")
        for ev in sorted(events, key=lambda e: e.get("eventDate",""), reverse=True)[:8]:
            print(f"  {ev.get('eventDate','?'):12s}  [{ev.get('eventCode','?'):6s}]  "
                  f"{ev.get('eventDescriptionText','')}")

    # OA rejection breakdown
    if oa_docs:
        # Group by submission date + doc code
        grouped: Dict[Tuple, List[Dict]] = {}
        for doc in oa_docs:
            key = (doc.get("submissionDate","")[:10], doc.get("legacyDocumentCodeIdentifier",""))
            grouped.setdefault(key, []).append(doc)

        print(f"\nOffice Action rejections ({len(oa_docs)} records):")
        for (date, code), docs in sorted(grouped.items(), reverse=True):
            label = DOC_CODE_LABELS.get(code, code)
            # Aggregate flags across all paragraphs in this OA
            agg_101 = any(d.get("hasRej101") for d in docs)
            agg_102 = any(d.get("hasRej102") for d in docs)
            agg_103 = any(d.get("hasRej103") for d in docs)
            agg_112 = any(d.get("hasRej112") for d in docs)
            alice   = any(d.get("aliceIndicator") for d in docs)
            flags   = " ".join(f for f, v in [
                ("§101",agg_101),("§102",agg_102),("§103",agg_103),("§112",agg_112),("ALICE",alice)
            ] if v) or "—"
            # Collect all claim numbers mentioned
            all_claims = sorted({c.strip() for d in docs
                                  for cs in d.get("claimNumberArrayDocument",[])
                                  for c in cs.split(",")},
                                 key=lambda x: int(x) if x.isdigit() else 0)
            print(f"  {date}  {label:<20s}  {flags:<26s}  claims: {','.join(all_claims)}")

        # SCBE-specific risk callout
        alice_oas = [d for d in oa_docs if any(d.get(f) for f in ALICE_RISK_FIELDS)]
        sec112_oas = [d for d in oa_docs if d.get("hasRej112")]
        if alice_oas:
            print(f"\n  ⚑ Alice/§101 doctrine applied in {len(alice_oas)} rejection paragraph(s)")
        if sec112_oas:
            claim_set = sorted({c.strip() for d in sec112_oas
                                 for cs in d.get("claimNumberArrayDocument",[])
                                 for c in cs.split(",")},
                                key=lambda x: int(x) if x.isdigit() else 0)
            print(f"  ⚑ §112 rejections touching claims: {','.join(claim_set)}")
    else:
        print("\nNo OA rejection records found.")

    # Continuations
    if children:
        print(f"\nChild applications ({len(children)}):")
        for ch in children:
            print(f"  {ch.get('childApplicationNumberText')}  "
                  f"filed {ch.get('childApplicationFilingDate')}  "
                  f"[{ch.get('childApplicationStatusCode')}] "
                  f"{ch.get('childApplicationStatusDescriptionText')}")

    # Changes
    if changes is not None:
        if changes:
            print(f"\n*** CHANGES SINCE LAST CHECK ***")
            for c in changes:
                print(c)
        else:
            print("\nNo changes since last check.")

    print(f"{'='*W}\n")


# ---------------------------------------------------------------------------
#  Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="USPTO prosecution monitor")
    parser.add_argument("--app", required=True,
                        help="Application number, digits only (e.g. 18045436)")
    parser.add_argument("--api-key", default=os.environ.get("USPTO_ODP_API_KEY"),
                        help="ODP API key (or set USPTO_ODP_API_KEY env var)")
    parser.add_argument("--reset", action="store_true",
                        help="Clear saved state baseline and exit")
    args = parser.parse_args()

    app_number = args.app.replace("/", "").replace("-", "").strip()

    if args.reset:
        p = _state_path(app_number)
        if p.exists():
            p.unlink()
            print(f"State cleared for {app_number}")
        return 0

    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{ts}] Checking application {app_number} …")

    wrapper = fetch_file_wrapper(app_number, args.api_key)
    if wrapper is None:
        return 2

    oa_docs = fetch_oa_rejections(app_number, args.api_key)

    old_snap = load_state(app_number)
    save_state(app_number, wrapper, oa_docs)

    if old_snap is None:
        print("First run — baseline saved.")
        print_summary(wrapper, oa_docs)
        return 0

    changes = diff_state(old_snap, wrapper, oa_docs)
    print_summary(wrapper, oa_docs, changes=changes)
    return 1 if changes else 0


if __name__ == "__main__":
    sys.exit(main())
