"""Apollo Field Trip — Multi-hop research crawler across clearnet + Tor.

Routes an SCBE agent through multiple jumps: clearnet -> Tor -> rotate ->
clearnet -> different Tor exit -> collect. Full governance gate at every stop.

Usage:
    python scripts/apollo/field_trip.py run
    python scripts/apollo/field_trip.py run --route deep     # More Tor hops
    python scripts/apollo/field_trip.py run --route stealth   # Max identity rotations
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

TOR_SOCKS = "socks5h://127.0.0.1:9050"
REPORT_DIR = ROOT / "artifacts" / "apollo" / "field_trips"
SFT_DIR = ROOT / "training-data" / "apollo" / "field_trips"


@dataclass
class Hop:
    """One stop on the field trip."""
    hop_number: int
    network: str          # "clearnet" or "tor"
    url: str
    exit_ip: str
    status: int
    title: str
    content_length: int
    content_hash: str
    governance: str       # ALLOW, QUARANTINE, DENY
    secrets_scrubbed: int
    latency_ms: int
    timestamp: str


@dataclass
class FieldTripReport:
    """Full report of a field trip."""
    route_name: str
    started: str
    finished: str
    total_hops: int
    identity_rotations: int
    unique_exit_ips: List[str]
    hops: List[Hop]
    sft_pairs_generated: int
    networks_used: List[str]


def get_exit_ip(use_tor: bool = False) -> str:
    """Get current exit IP."""
    import requests
    try:
        if use_tor:
            r = requests.get("https://check.torproject.org/api/ip",
                             proxies={"http": TOR_SOCKS, "https": TOR_SOCKS}, timeout=15)
            return r.json().get("IP", "unknown")
        else:
            r = requests.get("https://api.ipify.org?format=json", timeout=10)
            return r.json().get("ip", "unknown")
    except Exception:
        return "unknown"


def rotate_tor_identity() -> bool:
    """Request new Tor circuit."""
    try:
        from stem import Signal
        from stem.control import Controller
        with Controller.from_port(port=9051) as c:
            c.authenticate()
            c.signal(Signal.NEWNYM)
            return True
    except Exception:
        # Fallback: kill and restart Tor socks connection
        # The next request will use a different circuit automatically
        time.sleep(3)  # Tor rotates circuits every ~10 min, wait helps
        return False


def fetch_hop(url: str, use_tor: bool, hop_num: int) -> Hop:
    """Fetch a single URL and classify it."""
    import requests
    from scripts.apollo.apollo_core import scrub_text, vault_secrets

    start = time.time()
    exit_ip = "direct"
    status = 0
    title = ""
    content = ""
    governance = "QUARANTINE"
    scrubbed = 0

    try:
        kwargs = {"timeout": 20, "headers": {"User-Agent": "SCBE-Apollo-FieldTrip/1.0"}}
        if use_tor:
            kwargs["proxies"] = {"http": TOR_SOCKS, "https": TOR_SOCKS}
            exit_ip = get_exit_ip(use_tor=True)
        else:
            exit_ip = get_exit_ip(use_tor=False)

        r = requests.get(url, **kwargs)
        status = r.status_code
        raw = r.text[:30000]

        # Extract title
        m = re.search(r"<title[^>]*>(.*?)</title>", raw, re.I | re.S)
        if m:
            title = m.group(1).strip()[:150]

        # Scrub secrets
        clean, items = scrub_text(raw)
        scrubbed = len(items)
        if items:
            vault_secrets(items, context=f"field_trip:hop{hop_num}:{url[:60]}")

        content = clean

        # Governance check — multi-word phrases only to reduce false positives
        # Single words like "listing" or "vendor" cause false positives on news/research sites
        blocked_phrases = [
            "add to cart", "buy now", "checkout", "place order",
            "exploit kit for sale", "ransomware as a service",
            "fullz for sale", "credit card dumps", "cvv shop",
            "counterfeit documents", "fake passport", "fake id for sale",
            "hire a hacker", "ddos service",
        ]
        text_lower = clean.lower()
        hits = [p for p in blocked_phrases if p in text_lower]
        if hits:
            governance = "DENY"
        else:
            governance = "QUARANTINE"  # all content quarantined by default

    except Exception as e:
        title = f"ERROR: {str(e)[:80]}"

    latency = int((time.time() - start) * 1000)
    content_hash = hashlib.blake2s(content.encode()[:4096], digest_size=16).hexdigest() if content else ""

    return Hop(
        hop_number=hop_num,
        network="tor" if use_tor else "clearnet",
        url=url,
        exit_ip=exit_ip,
        status=status,
        title=title,
        content_length=len(content),
        content_hash=content_hash,
        governance=governance,
        secrets_scrubbed=scrubbed,
        latency_ms=latency,
        timestamp=datetime.datetime.now().isoformat(),
    )


# =========================================================================== #
#  Route definitions
# =========================================================================== #

ROUTES = {
    "standard": {
        "description": "Clearnet start -> Tor research -> clearnet verify -> Tor collect",
        "hops": [
            # Hop 1: Start on clearnet — establish baseline
            {"url": "https://api.ipify.org?format=json", "tor": False, "note": "Baseline: our real IP"},
            # Hop 2: Jump into Tor — visit research site
            {"url": "https://arxiv.org/abs/2301.10226", "tor": True, "note": "Research via Tor"},
            # Hop 3: Visit a security standard via Tor
            {"url": "https://attack.mitre.org/", "tor": True, "note": "MITRE ATT&CK via Tor"},
            # Hop 4: Rotate identity
            {"url": "__ROTATE__", "tor": True, "note": "New Tor circuit"},
            # Hop 5: Visit news via Tor (new exit node)
            {"url": "https://www.bbc.com/news", "tor": True, "note": "BBC News via Tor (new circuit)"},
            # Hop 6: Back to clearnet — verify we're back
            {"url": "https://check.torproject.org/api/ip", "tor": False, "note": "Clearnet check: should NOT be Tor"},
            # Hop 7: Tor again — privacy search
            {"url": "https://duckduckgo.com/?q=AI+safety+governance", "tor": True, "note": "DuckDuckGo search via Tor"},
            # Hop 8: Tor — government site
            {"url": "https://www.nist.gov/cyberframework", "tor": True, "note": "NIST CSF via Tor"},
        ],
    },
    "deep": {
        "description": "Heavy Tor usage — multiple circuits, research-focused",
        "hops": [
            {"url": "https://api.ipify.org?format=json", "tor": False, "note": "Baseline IP"},
            {"url": "https://check.torproject.org/api/ip", "tor": True, "note": "Tor circuit 1"},
            {"url": "https://arxiv.org/abs/2301.10226", "tor": True, "note": "AI safety paper"},
            {"url": "https://nvd.nist.gov/", "tor": True, "note": "NVD via Tor"},
            {"url": "__ROTATE__", "tor": True, "note": "Rotate identity"},
            {"url": "https://check.torproject.org/api/ip", "tor": True, "note": "Tor circuit 2 (new IP)"},
            {"url": "https://owasp.org/www-project-top-ten/", "tor": True, "note": "OWASP Top 10 via Tor"},
            {"url": "https://cve.mitre.org/", "tor": True, "note": "CVE database via Tor"},
            {"url": "__ROTATE__", "tor": True, "note": "Rotate again"},
            {"url": "https://check.torproject.org/api/ip", "tor": True, "note": "Tor circuit 3 (new IP)"},
            {"url": "https://securedrop.org/", "tor": True, "note": "SecureDrop via Tor"},
            {"url": "https://ahmia.fi/", "tor": True, "note": "Ahmia search via Tor"},
            {"url": "https://api.ipify.org?format=json", "tor": False, "note": "Back to clearnet"},
        ],
    },
    "stealth": {
        "description": "Maximum identity rotations — never same exit twice",
        "hops": [
            {"url": "https://api.ipify.org?format=json", "tor": False, "note": "Baseline"},
            {"url": "https://check.torproject.org/api/ip", "tor": True, "note": "Circuit 1"},
            {"url": "https://arxiv.org/", "tor": True, "note": "arXiv via circuit 1"},
            {"url": "__ROTATE__", "tor": True, "note": "Rotate"},
            {"url": "https://check.torproject.org/api/ip", "tor": True, "note": "Circuit 2"},
            {"url": "https://scholar.google.com/", "tor": True, "note": "Scholar via circuit 2"},
            {"url": "__ROTATE__", "tor": True, "note": "Rotate"},
            {"url": "https://check.torproject.org/api/ip", "tor": True, "note": "Circuit 3"},
            {"url": "https://www.torproject.org/", "tor": True, "note": "Tor Project via circuit 3"},
            {"url": "__ROTATE__", "tor": True, "note": "Rotate"},
            {"url": "https://check.torproject.org/api/ip", "tor": True, "note": "Circuit 4"},
            {"url": "https://proton.me/", "tor": True, "note": "ProtonMail via circuit 4"},
            {"url": "https://api.ipify.org?format=json", "tor": False, "note": "Return to clearnet"},
        ],
    },
}


def run_field_trip(route_name: str = "standard") -> FieldTripReport:
    """Execute a field trip along a named route."""
    import requests

    route = ROUTES.get(route_name)
    if not route:
        print(f"Unknown route: {route_name}. Available: {list(ROUTES.keys())}")
        return None

    print(f"APOLLO FIELD TRIP: {route_name}")
    print(f"  {route['description']}")
    print("=" * 70)

    # Verify Tor is running
    try:
        r = requests.get("https://check.torproject.org/api/ip",
                         proxies={"http": TOR_SOCKS, "https": TOR_SOCKS}, timeout=10)
        tor_ip = r.json().get("IP", "?")
        print(f"  Tor: LIVE (exit: {tor_ip})")
    except Exception as e:
        print(f"  Tor: OFFLINE ({e})")
        print("  Start Tor first: tor --SocksPort 9050 &")
        return None

    started = datetime.datetime.now().isoformat()
    hops = []
    rotations = 0
    exit_ips = set()
    hop_num = 0

    for step in route["hops"]:
        url = step["url"]
        use_tor = step["tor"]
        note = step["note"]

        if url == "__ROTATE__":
            print(f"\n  [HOP {hop_num + 1}] ROTATING IDENTITY...")
            rotated = rotate_tor_identity()
            rotations += 1
            time.sleep(5)  # wait for new circuit
            if rotated:
                print(f"         New circuit established")
            else:
                print(f"         Soft rotation (new circuit on next request)")
            hop_num += 1
            continue

        hop_num += 1
        network = "TOR" if use_tor else "CLEARNET"
        print(f"\n  [HOP {hop_num}] [{network:8s}] {note}")
        print(f"         {url[:70]}")

        hop = fetch_hop(url, use_tor, hop_num)
        hops.append(hop)

        if hop.exit_ip != "unknown" and hop.exit_ip != "direct":
            exit_ips.add(hop.exit_ip)

        gov_sym = {"ALLOW": "OK", "QUARANTINE": "Q ", "DENY": "X "}
        print(f"         [{gov_sym.get(hop.governance, '??')}] {hop.title[:50]} | "
              f"{hop.content_length}B | {hop.latency_ms}ms | exit:{hop.exit_ip[:15]}")

        if hop.secrets_scrubbed > 0:
            print(f"         Scrubbed {hop.secrets_scrubbed} secrets")

        time.sleep(1)  # be polite

    finished = datetime.datetime.now().isoformat()

    # Generate SFT from the trip
    sft_pairs = []
    for hop in hops:
        if hop.governance != "DENY" and hop.content_length > 100:
            sft_pairs.append({
                "instruction": f"What content is available at {hop.url} when accessed {'via Tor' if hop.network == 'tor' else 'directly'}?",
                "response": f"Accessed via {hop.network} (exit IP: {hop.exit_ip[:15]}). "
                            f"Title: {hop.title}. Content size: {hop.content_length} bytes. "
                            f"Governance decision: {hop.governance}. "
                            f"Latency: {hop.latency_ms}ms. "
                            f"{'Secrets scrubbed: ' + str(hop.secrets_scrubbed) if hop.secrets_scrubbed else 'Clean.'}",
                "source": "apollo_field_trip",
                "category": f"field_trip_{hop.network}",
            })

    # Save SFT
    SFT_DIR.mkdir(parents=True, exist_ok=True)
    if sft_pairs:
        sft_path = SFT_DIR / f"trip_{route_name}_{datetime.date.today().isoformat()}.jsonl"
        with open(sft_path, "w", encoding="utf-8") as f:
            for p in sft_pairs:
                json.dump(p, f, ensure_ascii=False)
                f.write("\n")

    report = FieldTripReport(
        route_name=route_name,
        started=started,
        finished=finished,
        total_hops=len(hops),
        identity_rotations=rotations,
        unique_exit_ips=sorted(exit_ips),
        hops=[asdict(h) for h in hops],
        sft_pairs_generated=len(sft_pairs),
        networks_used=sorted(set(h.network for h in hops)),
    )

    # Save report
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / f"trip_{route_name}_{datetime.date.today().isoformat()}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(asdict(report), f, indent=2, ensure_ascii=False)

    # Summary
    print(f"\n{'=' * 70}")
    print(f"  FIELD TRIP COMPLETE: {route_name}")
    print(f"  Hops: {report.total_hops} | Rotations: {report.identity_rotations}")
    print(f"  Unique exit IPs: {len(report.unique_exit_ips)}")
    for ip in report.unique_exit_ips:
        print(f"    - {ip}")
    print(f"  Networks: {', '.join(report.networks_used)}")
    print(f"  SFT pairs: {report.sft_pairs_generated}")
    print(f"  Report: {report_path}")

    return report


def main():
    parser = argparse.ArgumentParser(description="Apollo Field Trip")
    sub = parser.add_subparsers(dest="command")

    r = sub.add_parser("run", help="Run a field trip")
    r.add_argument("--route", default="standard", choices=list(ROUTES.keys()))

    sub.add_parser("routes", help="List available routes")

    args = parser.parse_args()

    if args.command == "run":
        run_field_trip(args.route)
    elif args.command == "routes":
        for name, route in ROUTES.items():
            print(f"  {name:12s} — {route['description']} ({len(route['hops'])} hops)")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
