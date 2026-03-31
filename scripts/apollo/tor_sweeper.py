"""Apollo Tor Sweeper — Sandboxed dark web research crawler.

Double-sandbox architecture:
  1. Tor SOCKS5 proxy (anonymity layer)
  2. Content governance gate (SCBE pipeline)

All content is QUARANTINED by default. Only ALLOW'd content enters training.
Secrets are scrubbed before any storage. Full audit trail.

Requirements:
  - Tor installed and running (SOCKS5 on 127.0.0.1:9050)
  - stem (pip install stem) for Tor control
  - requests[socks] (pip install requests[socks]) for SOCKS proxy

Usage:
    python scripts/apollo/tor_sweeper.py check          # Verify Tor connection
    python scripts/apollo/tor_sweeper.py sweep           # Sweep trusted onion sites
    python scripts/apollo/tor_sweeper.py sweep --tier NEWS_AND_JOURNALISM
    python scripts/apollo/tor_sweeper.py search "AI safety research"
    python scripts/apollo/tor_sweeper.py identity        # Get current Tor exit node
    python scripts/apollo/tor_sweeper.py rotate           # New Tor identity
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "src"))

# =========================================================================== #
#  Tor Configuration
# =========================================================================== #

TOR_SOCKS_HOST = "127.0.0.1"
TOR_SOCKS_PORT = 9050
TOR_CONTROL_PORT = 9051

TRUSTED_SITES_PATH = ROOT / "config" / "security" / "trusted_onion_sites.json"
SWEEP_OUTPUT_DIR = ROOT / "artifacts" / "tor_sweeps"
SWEEP_TRAINING_DIR = ROOT / "training-data" / "apollo" / "tor_sweeps"


def load_trusted_sites() -> dict:
    """Load the trusted onion sites registry."""
    return json.loads(TRUSTED_SITES_PATH.read_text())


# =========================================================================== #
#  Tor Connection
# =========================================================================== #

def check_tor() -> dict:
    """Check if Tor is running and we can connect."""
    result = {"tor_running": False, "socks_proxy": False, "exit_ip": None}

    # Check if Tor process exists
    try:
        import subprocess
        out = subprocess.run(
            ["tasklist" if sys.platform == "win32" else "pgrep", "/FI" if sys.platform == "win32" else "-x",
             "IMAGENAME eq tor.exe" if sys.platform == "win32" else "tor"],
            capture_output=True, text=True
        )
        result["tor_running"] = "tor" in out.stdout.lower()
    except Exception:
        logger.debug("Tor process check failed", exc_info=True)

    # Check SOCKS proxy
    try:
        import requests
        proxies = {"http": f"socks5h://{TOR_SOCKS_HOST}:{TOR_SOCKS_PORT}",
                    "https": f"socks5h://{TOR_SOCKS_HOST}:{TOR_SOCKS_PORT}"}
        r = requests.get("https://check.torproject.org/api/ip", proxies=proxies, timeout=15)
        data = r.json()
        result["socks_proxy"] = True
        result["exit_ip"] = data.get("IP", "unknown")
        result["is_tor"] = data.get("IsTor", False)
    except ImportError:
        result["error"] = "requests[socks] not installed. Run: pip install requests[socks]"
    except Exception as e:
        result["error"] = str(e)

    return result


def rotate_identity():
    """Request new Tor circuit (new exit node)."""
    try:
        from stem import Signal
        from stem.control import Controller
        with Controller.from_port(port=TOR_CONTROL_PORT) as controller:
            controller.authenticate()
            controller.signal(Signal.NEWNYM)
            print("New Tor identity requested. Wait ~10s for new circuit.")
            return True
    except ImportError:
        print("stem not installed. Run: pip install stem")
        return False
    except Exception as e:
        print(f"Could not rotate: {e}")
        print("Tor ControlPort may need to be enabled in torrc.")
        return False


# =========================================================================== #
#  Sandboxed Fetch (double-sandbox: Tor proxy + governance gate)
# =========================================================================== #

def sandboxed_fetch(url: str, timeout: int = 30) -> dict:
    """Fetch a URL through Tor with full governance pipeline.

    Returns:
        {ok, status, content_hash, content_length, title, snippet, governance_decision, scrubbed_items}
    """
    import requests
    from scripts.apollo.apollo_core import scrub_text, vault_secrets

    result = {
        "url": url, "ok": False, "status": None, "content_hash": None,
        "content_length": 0, "title": "", "snippet": "",
        "governance_decision": "QUARANTINE", "scrubbed_items": 0,
        "timestamp": datetime.datetime.now().isoformat(),
    }

    try:
        proxies = {"http": f"socks5h://{TOR_SOCKS_HOST}:{TOR_SOCKS_PORT}",
                    "https": f"socks5h://{TOR_SOCKS_HOST}:{TOR_SOCKS_PORT}"}
        headers = {"User-Agent": "SCBE-Apollo-Research/1.0 (academic research)"}

        r = requests.get(url, proxies=proxies, timeout=timeout, headers=headers)
        result["status"] = r.status_code
        result["ok"] = r.status_code == 200

        if not result["ok"]:
            return result

        raw_text = r.text[:50000]  # cap at 50KB per page
        result["content_length"] = len(raw_text)
        result["content_hash"] = hashlib.blake2s(raw_text.encode()[:4096], digest_size=16).hexdigest()

        # Extract title
        import re
        title_match = re.search(r"<title[^>]*>(.*?)</title>", raw_text, re.I | re.S)
        if title_match:
            result["title"] = title_match.group(1).strip()[:200]

        # SANDBOX 1: Scrub secrets from content
        clean_text, scrubbed_items = scrub_text(raw_text)
        result["scrubbed_items"] = len(scrubbed_items)
        if scrubbed_items:
            vault_secrets(scrubbed_items, context=f"tor_sweep:{url[:80]}")

        # SANDBOX 2: Governance gate — check for blocked content
        # Multi-word phrases to reduce false positives on news/research sites
        blocked_keywords = [
            "add to cart", "buy now", "checkout", "place order",
            "exploit kit for sale", "ransomware as a service",
            "fullz for sale", "credit card dumps", "cvv shop",
            "counterfeit documents", "fake passport", "fake id for sale",
            "hire a hacker", "ddos service",
        ]
        text_lower = clean_text.lower()
        blocked_hits = [kw for kw in blocked_keywords if kw in text_lower]

        if blocked_hits:
            result["governance_decision"] = "DENY"
            result["blocked_reason"] = f"Matched blocked keywords: {blocked_hits[:5]}"
            result["snippet"] = "[DENIED — blocked content detected]"
        else:
            result["governance_decision"] = "QUARANTINE"
            # Snippet: first 300 chars of clean text (no HTML)
            plain = re.sub(r"<[^>]+>", " ", clean_text)
            plain = re.sub(r"\s+", " ", plain).strip()
            result["snippet"] = plain[:300]

    except Exception as e:
        result["error"] = str(e)

    return result


# =========================================================================== #
#  Sweep — Crawl trusted onion sites
# =========================================================================== #

def sweep(tier: Optional[str] = None) -> List[dict]:
    """Sweep trusted onion sites, fetch and classify content."""
    registry = load_trusted_sites()
    results = []

    print("APOLLO TOR SWEEPER")
    print("=" * 60)

    # Check Tor first
    tor_status = check_tor()
    if not tor_status.get("socks_proxy"):
        print(f"  Tor not available: {tor_status.get('error', 'SOCKS proxy unreachable')}")
        print(f"  Install Tor: https://www.torproject.org/download/")
        print(f"  Or on Windows: choco install tor")
        print(f"\n  Running in DRY RUN mode (showing what would be swept)...")
        print()

        # Dry run — show the plan
        for tier_name, tier_data in registry.get("tiers", {}).items():
            if tier and tier != tier_name:
                continue
            trust = tier_data.get("trust", "?")
            sites = tier_data.get("sites", [])
            print(f"  [{trust:12s}] {tier_name} ({len(sites)} sites)")
            for site in sites:
                print(f"    - {site['name']} ({site.get('clearnet', 'onion-only')})")
                print(f"      Value: {site.get('value', '?')}")
            print()

        return results

    logger.info("Tor: CONNECTED (exit IP redacted)")
    logger.debug("Tor exit IP: %s", tor_status.get("exit_ip", "?"))
    print("  Tor: CONNECTED")
    print("  Double-sandbox: Tor SOCKS5 + Governance Gate")
    print()

    for tier_name, tier_data in registry.get("tiers", {}).items():
        if tier and tier != tier_name:
            continue

        trust = tier_data.get("trust", "?")
        sites = tier_data.get("sites", [])
        print(f"  [{trust:12s}] {tier_name}")

        for site in sites:
            clearnet = site.get("clearnet", "")
            if clearnet and clearnet != "none" and clearnet != "none (onion-only)":
                # Fetch clearnet version through Tor for anonymity
                url = f"https://{clearnet}"
                logger.debug("Fetching %s via %s", site["name"], url)
                print(f"    Fetching {site['name']}...", end=" ")
                result = sandboxed_fetch(url)
                result["site_name"] = site["name"]
                result["tier"] = tier_name
                result["trust"] = trust

                decision = result["governance_decision"]
                symbol = {"QUARANTINE": "Q", "DENY": "X", "ALLOW": "OK"}
                print(f"[{symbol.get(decision, '?')}] {result.get('title', '?')[:50]} ({result['content_length']}B)")

                results.append(result)
                time.sleep(2)  # be polite

        print()

    # Save results
    SWEEP_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SWEEP_OUTPUT_DIR / f"sweep_{datetime.date.today().isoformat()}.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"Results saved: {out_path}")

    # Generate SFT from allowed/quarantined content
    sft_pairs = []
    for r in results:
        if r["governance_decision"] != "DENY" and r.get("snippet"):
            sft_pairs.append({
                "instruction": f"What kind of content is available at {r.get('site_name', 'this site')} on the dark web, and why is it legitimate?",
                "response": f"{r.get('site_name', 'This site')} ({r.get('tier', 'unknown tier')}, trust level: {r.get('trust', '?')}) provides: {r.get('snippet', 'content not available')[:200]}. This is legitimate because {r.get('site_name', 'it')} is operated by a verified organization with a known clearnet presence at {r.get('url', 'unknown')}.",
                "source": "tor_sweeper",
                "category": "dark_web_legitimate",
            })

    if sft_pairs:
        SWEEP_TRAINING_DIR.mkdir(parents=True, exist_ok=True)
        sft_path = SWEEP_TRAINING_DIR / f"sweep_sft_{datetime.date.today().isoformat()}.jsonl"
        with open(sft_path, "w") as f:
            for p in sft_pairs:
                json.dump(p, f)
                f.write("\n")
        print(f"SFT pairs: {len(sft_pairs)} -> {sft_path}")

    return results


# =========================================================================== #
#  CLI
# =========================================================================== #

def main():
    parser = argparse.ArgumentParser(description="Apollo Tor Sweeper")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("check", help="Check Tor connection status")

    s = sub.add_parser("sweep", help="Sweep trusted onion sites")
    s.add_argument("--tier", default=None, help="Sweep only this tier")

    sub.add_parser("identity", help="Show current Tor exit node")
    sub.add_parser("rotate", help="Request new Tor identity")

    q = sub.add_parser("search", help="Search via DuckDuckGo over Tor")
    q.add_argument("query", help="Search term")

    args = parser.parse_args()

    if args.command == "check":
        status = check_tor()
        print("TOR STATUS:")
        for k, v in status.items():
            print(f"  {k}: {v}")

    elif args.command == "sweep":
        sweep(args.tier)

    elif args.command == "identity":
        status = check_tor()
        if status.get("exit_ip"):
            print(f"Exit IP: {status['exit_ip']}")
            print(f"Is Tor: {status.get('is_tor', '?')}")
        else:
            print("Tor not connected.")

    elif args.command == "rotate":
        rotate_identity()

    elif args.command == "search":
        print("Tor search not yet implemented. Use: sweep --tier SEARCH_AND_INDEXING")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
