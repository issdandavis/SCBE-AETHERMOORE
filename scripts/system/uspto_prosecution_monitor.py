#!/usr/bin/env python3
"""
USPTO prosecution monitor — Patent File Wrapper + Office Action Rejections + Enriched Citations.

APIs:
  Patent File Wrapper  GET  https://api.uspto.gov/api/v1/patent/applications/search
  OA Rejections        GET  https://api.uspto.gov/api/v1/patent/oa/oa_actions/v1/records
  Enriched Citations   POST https://api.uspto.gov/api/v1/patent/oa/enriched_cited_reference_metadata/v3/records

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
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# DSAPI datasets that use form-encoded POST (criteria= Lucene, start=, rows=)
# vs enriched citations which uses JSON POST (q= Lucene, start=, rows=)
_DSAPI_FORM_DATASETS = frozenset({"oa_rejections"})

PFW_URL = "https://api.uspto.gov/api/v1/patent/applications/search"
OA_URL  = "https://api.uspto.gov/api/v1/patent/oa/oa_rejections/v2/records"
EC_URL  = "https://api.uspto.gov/api/v1/patent/oa/enriched_cited_reference_metadata/v3/records"
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

# SCBE independent claim numbers (claims 1, 9, 15 in the non-provisional spec)
SCBE_INDEPENDENT_CLAIMS: frozenset = frozenset({"1", "9", "15"})

# Citation category codes (EPO/WIPO IPCR standard, used by USPTO OA examiners)
CITATION_CATEGORY_LABELS = {
    "X": "Anticipates claim (§102)",          # single reference — highest threat
    "Y": "Obviousness combination (§103)",    # used in combination with another Y ref
    "A": "Background / general state of art",
    "E": "Earlier-filed document (§102(e))",
    "O": "Non-written disclosure",
    "P": "Intermediate publication (priority window)",
    "T": "Theory / definition",
    "D": "Patent family member",
    "L": "Prior art acknowledged by applicant",
}


# ---------------------------------------------------------------------------
#  HTTP helpers  (header: x-api-key per ODP docs; 429 retry with backoff)
# ---------------------------------------------------------------------------

# ODP rate limits (https://developer.uspto.gov/api-catalog/rate-limits):
#   Burst = 1 (one active request per key; NO parallel calls)
#   Rate  = 4–15 req/s depending on API type
#   429 retry: minimum 5 second delay required before retrying
#   Weekly quota resets Sunday 00:00 UTC
_RETRY_MAX   = 5
_RETRY_SLEEP = 5.0   # seconds — ODP strongly discourages < 5s retry delay
_PAGE_SLEEP  = 0.25  # seconds between pagination hops (burst=1, sequential only)


def _base_headers(api_key: Optional[str]) -> Dict[str, str]:
    h = {"Accept": "application/json"}
    if api_key:
        h["x-api-key"] = api_key   # lowercase per ODP API syntax examples
    return h


def _get_json(
    url: str,
    params: Dict,
    api_key: Optional[str],
    _retry: int = 0,
) -> Optional[Dict]:
    full = f"{url}?{urlencode(params)}"
    try:
        with urlopen(Request(full, headers=_base_headers(api_key)), timeout=30) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        if e.code == 429 and _retry < _RETRY_MAX:
            time.sleep(_RETRY_SLEEP)
            return _get_json(url, params, api_key, _retry + 1)
        print(f"[ERROR] HTTP {e.code}: {e.reason}  ({full})", file=sys.stderr)
    except URLError as e:
        print(f"[ERROR] Network: {e.reason}", file=sys.stderr)
    return None


def _post_json(
    url: str,
    body: Dict,
    api_key: Optional[str],
    _retry: int = 0,
) -> Optional[Dict]:
    data = json.dumps(body).encode("utf-8")
    h = _base_headers(api_key)
    h["Content-Type"] = "application/json"
    try:
        with urlopen(Request(url, data=data, headers=h), timeout=30) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        if e.code == 429 and _retry < _RETRY_MAX:
            time.sleep(_RETRY_SLEEP)
            return _post_json(url, body, api_key, _retry + 1)
        print(f"[ERROR] HTTP {e.code}: {e.reason}  (POST {url})", file=sys.stderr)
    except URLError as e:
        print(f"[ERROR] Network: {e.reason}", file=sys.stderr)
    return None


def _post_form(
    url: str,
    criteria: str,
    start: int,
    rows: int,
    api_key: Optional[str],
    _retry: int = 0,
) -> Optional[Dict]:
    """DSAPI form-encoded POST: criteria= Lucene query, start=, rows=."""
    data = urlencode({"criteria": criteria, "start": start, "rows": rows}).encode("utf-8")
    h = _base_headers(api_key)
    h["Content-Type"] = "application/x-www-form-urlencoded"
    try:
        with urlopen(Request(url, data=data, headers=h), timeout=30) as resp:
            return json.loads(resp.read().decode())
    except HTTPError as e:
        if e.code == 429 and _retry < _RETRY_MAX:
            time.sleep(_RETRY_SLEEP)
            return _post_form(url, criteria, start, rows, api_key, _retry + 1)
        print(f"[ERROR] HTTP {e.code}: {e.reason}  (POST form {url})", file=sys.stderr)
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
    # DSAPI form-encoded POST: criteria= Lucene query (GET /fields, POST /records)
    data = _post_form(OA_URL, f"patentApplicationNumber:{app_number}", 0, 100, api_key)
    if not data:
        return []
    return data.get("response", {}).get("docs", [])


def fetch_enriched_citations(app_number: str, api_key: Optional[str]) -> List[Dict]:
    """
    POST endpoint — returns prior-art citations from examiner OAs with category codes,
    passage locations, and claim-level targeting data.

    Category codes (EPO/WIPO standard):
      X = anticipates a claim (§102 single-reference rejection — highest threat)
      Y = cited in combination for obviousness (§103)
      A = background / general state of art (informational only)

    Uses the advanced OpenSearch body format (pagination object) per ODP API syntax docs.
    Paginates automatically if numFound > first-page limit.
    """
    # Same DSAPI form-encoded pattern as OA rejections: criteria= Lucene, start=, rows=
    limit = 100
    criteria = f"patentApplicationNumber:{app_number}"
    first = _post_form(EC_URL, criteria, 0, limit, api_key)
    if not first:
        return []
    response_block = first.get("response", {})
    docs: List[Dict] = list(response_block.get("docs", []))
    num_found = response_block.get("numFound", len(docs))

    # Page through remaining results (burst=1 → sequential; sleep between pages)
    start = limit
    while start < num_found:
        time.sleep(_PAGE_SLEEP)
        page = _post_form(EC_URL, criteria, start, limit, api_key)
        if not page:
            break
        page_docs = page.get("response", {}).get("docs", [])
        if not page_docs:
            break
        docs.extend(page_docs)
        start += limit

    return docs


# ---------------------------------------------------------------------------
#  State persistence
# ---------------------------------------------------------------------------

def _state_path(app_number: str) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / f"{app_number}_state.json"


def load_state(app_number: str) -> Optional[Dict]:
    p = _state_path(app_number)
    return json.loads(p.read_text("utf-8")) if p.exists() else None


def save_state(
    app_number: str,
    wrapper: Dict,
    oa_docs: List[Dict],
    citations: List[Dict],
) -> None:
    snap = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "wrapper": wrapper,
        "oa_docs": oa_docs,
        "citations": citations,
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


def _oa_doc_code(doc: Dict) -> str:
    val = doc.get("legacyDocumentCodeIdentifier", "")
    return val[0] if isinstance(val, list) else (val or "")


def _oa_fingerprint(doc: Dict) -> Tuple:
    return (
        (doc.get("submissionDate", "") or "")[:10],
        _oa_doc_code(doc),
        doc.get("legalSectionCode", "") or "",
        ",".join(doc.get("claimNumberArrayDocument", []) or []),
    )


def _citation_fingerprint(doc: Dict) -> Tuple:
    return (
        doc.get("officeActionDate", "")[:10],
        doc.get("citedDocumentIdentifier", "") or doc.get("publicationNumber", ""),
        doc.get("relatedClaimNumberText", ""),
        doc.get("citationCategoryCode", ""),
    )


def diff_state(
    old: Dict,
    new_wrapper: Dict,
    new_oa: List[Dict],
    new_citations: List[Dict],
) -> List[str]:
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

    # Enriched citations diff
    old_cite_fps = {_citation_fingerprint(d) for d in old.get("citations", [])}
    new_cite_fps = {_citation_fingerprint(d) for d in new_citations}
    for fp in sorted(new_cite_fps - old_cite_fps):
        date, ref_id, claims, cat = fp
        label = CITATION_CATEGORY_LABELS.get(cat, cat)
        changes.append(f"  NEW CITE   [{date}] [{cat}] {ref_id}  claims: {claims}  — {label}")
    for fp in sorted(old_cite_fps - new_cite_fps):
        date, ref_id, claims, cat = fp
        changes.append(f"  GONE CITE  [{date}] [{cat}] {ref_id}  claims: {claims}")

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


def _claims_hit(claim_text: str) -> frozenset:
    """Parse '1,2-5,9' → frozenset of string claim numbers."""
    result = set()
    for part in claim_text.replace(" ", "").split(","):
        if "-" in part:
            lo, hi = part.split("-", 1)
            if lo.isdigit() and hi.isdigit():
                result.update(str(n) for n in range(int(lo), int(hi) + 1))
        elif part.isdigit():
            result.add(part)
    return frozenset(result)


def print_summary(
    wrapper: Dict,
    oa_docs: List[Dict],
    citations: Optional[List[Dict]] = None,
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
            key = ((doc.get("submissionDate","") or "")[:10], _oa_doc_code(doc))
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

    # Enriched citations
    if citations:
        # Group by OA date (officeActionDate[:10])
        cite_groups: Dict[str, List[Dict]] = {}
        for doc in citations:
            key = (doc.get("officeActionDate", "") or "")[:10]
            cite_groups.setdefault(key, []).append(doc)

        print(f"\nEnriched citations ({len(citations)} records):")
        indep_hits: List[str] = []  # X/Y citations against independent claims

        for oa_date in sorted(cite_groups.keys(), reverse=True):
            docs = cite_groups[oa_date]
            # Sort: X first, then Y, then others
            docs_sorted = sorted(docs, key=lambda d: (
                {"X": 0, "Y": 1}.get(d.get("citationCategoryCode", ""), 2),
                d.get("citedDocumentIdentifier", ""),
            ))
            print(f"  OA {oa_date}  ({len(docs)} reference(s)):")
            for doc in docs_sorted:
                ref_id   = doc.get("citedDocumentIdentifier") or doc.get("publicationNumber") or "?"
                cat      = doc.get("citationCategoryCode", "?")
                label    = CITATION_CATEGORY_LABELS.get(cat, cat)
                inventor = doc.get("inventorNameText", "") or ""
                claims   = doc.get("relatedClaimNumberText", "") or ""
                passage  = doc.get("passageLocationText", "") or ""
                is_npl   = doc.get("nplIndicator") or doc.get("applicantCitedExaminerReferenceIndicator")
                examiner = doc.get("examinerCitedReferenceIndicator", False)

                src_tag = "[PTO-892]" if examiner else "[IDS]"
                npl_tag = "[NPL]" if is_npl else ""

                ref_line = f"    [{cat}] {ref_id}"
                if inventor:
                    ref_line += f"  ({inventor[:40]})"
                ref_line += f"  {src_tag}{npl_tag}"
                print(ref_line)
                print(f"         claims: {claims or '—'}  — {label}")
                if passage:
                    # passageLocationText is an array in the API schema; join if needed
                    if isinstance(passage, list):
                        passage = " | ".join(passage)
                    p = passage[:100] + ("…" if len(passage) > 100 else "")
                    print(f"         passage: {p}")

                # Flag X/Y hits against SCBE independent claims
                if cat in ("X", "Y") and claims:
                    hit = _claims_hit(claims) & SCBE_INDEPENDENT_CLAIMS
                    if hit:
                        indep_hits.append(
                            f"[{cat}] {ref_id}  → indep claim(s) {','.join(sorted(hit, key=int))}"
                        )

        if indep_hits:
            print(f"\n  ⚑ CRITICAL — prior art cited against independent claim(s):")
            for h in indep_hits:
                print(f"    {h}")

    elif citations is not None:
        print("\nNo enriched citation records found.")

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

    oa_docs   = fetch_oa_rejections(app_number, args.api_key)
    citations = fetch_enriched_citations(app_number, args.api_key)

    old_snap = load_state(app_number)
    save_state(app_number, wrapper, oa_docs, citations)

    if old_snap is None:
        print("First run — baseline saved.")
        print_summary(wrapper, oa_docs, citations=citations)
        return 0

    changes = diff_state(old_snap, wrapper, oa_docs, citations)
    print_summary(wrapper, oa_docs, citations=citations, changes=changes)
    return 1 if changes else 0


if __name__ == "__main__":
    sys.exit(main())
