#!/usr/bin/env python3
"""
AETHERMOORE Antivirus CLI
=========================

Usage:
    python -m aethermoore_av scan <path>        # Scan file or directory
    python -m aethermoore_av quick <path>       # Quick scan (executables only)
    python -m aethermoore_av deep <path>        # Deep scan (all files)
    python -m aethermoore_av watch <path>       # Real-time monitoring
    python -m aethermoore_av trust <path>       # Show trust status
    python -m aethermoore_av stats              # Show trust database stats
"""

import sys
import os
import argparse
import signal

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.aethermoore_av.scanner import Scanner
from src.aethermoore_av.monitor import Monitor, watch
from src.aethermoore_av.trust_db import TrustDatabase
from src.aethermoore_av.threat_engine import ThreatLevel


def print_banner():
    """Print AETHERMOORE banner."""
    print("""
╔══════════════════════════════════════════════════════════════╗
║             AETHERMOORE ANTIVIRUS ENGINE v1.0                ║
║         Physics-Based Threat Detection & Response            ║
║                                                              ║
║  Lorentz Dilation | Hyperbolic Trust | Byzantine Consensus  ║
╚══════════════════════════════════════════════════════════════╝
""")


def cmd_scan(args):
    """Scan a file or directory."""
    scanner = Scanner()
    path = args.path

    if os.path.isfile(path):
        print(f"\n[SCAN] File: {path}")
        result = scanner.scan_file(path)
    elif os.path.isdir(path):
        print(f"\n[SCAN] Directory: {path}")
        result = scanner.scan_directory(path, recursive=not args.no_recursive)
    else:
        print(f"Error: Path not found: {path}")
        return 1

    # Print results
    print("\n" + "="*60)
    print(result.summary())
    print("="*60)

    # Show threats
    threats = result.get_threats()
    if threats:
        print("\nTHREATS DETECTED:")
        print("-"*60)
        for assessment in threats:
            level = assessment.threat_level.name
            gamma = assessment.lorentz_factor
            print(f"\n  [{level}] {assessment.target}")
            print(f"    Lorentz factor: γ = {gamma:.2f}x")
            print(f"    Threat velocity: v = {assessment.threat_velocity:.2f}c")
            print(f"    {assessment.recommendation}")

            if args.verbose:
                print("    Signals:")
                for sig in assessment.signals:
                    if sig.score > 0:
                        print(f"      - {sig.details} (score: {sig.score:.2f})")

    return 0 if result.is_clean else 1


def cmd_quick(args):
    """Quick scan (executables only)."""
    scanner = Scanner()
    path = args.path

    print(f"\n[QUICK SCAN] {path}")
    result = scanner.quick_scan(path)

    print("\n" + "="*60)
    print(result.summary())
    print("="*60)

    if not result.is_clean:
        print(f"\n⚠ Found {result.threats_found} potential threats")

    return 0 if result.is_clean else 1


def cmd_deep(args):
    """Deep scan (all files)."""
    scanner = Scanner()
    path = args.path

    print(f"\n[DEEP SCAN] {path}")
    print("This may take a while...")

    result = scanner.deep_scan(path)

    print("\n" + "="*60)
    print(result.summary())
    print("="*60)

    return 0 if result.is_clean else 1


def cmd_watch(args):
    """Real-time monitoring."""
    path = args.path

    print(f"\n[MONITOR] Watching: {path}")
    print("Press Ctrl+C to stop\n")

    def on_threat(assessment):
        print(f"\n⚠ THREAT DETECTED: {assessment.target}")
        print(f"  Level: {assessment.threat_level.name}")
        print(f"  γ = {assessment.lorentz_factor:.2f}x")

    monitor = Monitor(path)
    monitor.on_threat = on_threat
    monitor.start()

    # Wait for Ctrl+C
    def signal_handler(sig, frame):
        print("\n\nStopping monitor...")
        monitor.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    while True:
        try:
            signal.pause()
        except AttributeError:
            # Windows doesn't have signal.pause
            import time
            time.sleep(1)


def cmd_trust(args):
    """Show trust status for a file."""
    path = args.path
    db = TrustDatabase()

    if not os.path.exists(path):
        print(f"Error: Path not found: {path}")
        return 1

    entry = db.get_entry(path)

    if entry:
        print(f"\n[TRUST STATUS] {path}")
        print("-"*60)
        print(f"  Hash: {entry.file_hash[:16]}...")
        print(f"  Trust radius: {entry.trust_radius:.2f} (0=trusted, 4=untrusted)")
        print(f"  Trust score: {entry.trust_score:.1%}")
        print(f"  Reputation: {entry.reputation:.1%}")
        print(f"  First seen: {entry.first_seen}")
        print(f"  Scan count: {entry.scan_count}")
        print(f"  Clean scans: {entry.clean_count}")
        print(f"  Threat flags: {entry.threat_count}")
        print(f"  System file: {entry.is_system}")
    else:
        # Get initial trust
        radius = db.get_trust_radius(path)
        print(f"\n[NEW FILE] {path}")
        print(f"  Initial trust radius: {radius:.2f}")
        print("  (File will be tracked after first scan)")

    return 0


def cmd_stats(args):
    """Show trust database statistics."""
    db = TrustDatabase()
    stats = db.get_statistics()

    print("\n[TRUST DATABASE STATISTICS]")
    print("-"*40)
    print(f"  Total entries: {stats.get('total', 0)}")
    print(f"  Trusted files: {stats.get('trusted', 0)}")
    print(f"  Suspicious files: {stats.get('suspicious', 0)}")
    print(f"  Untrusted files: {stats.get('untrusted', 0)}")
    print(f"  System files: {stats.get('system_files', 0)}")

    if stats.get('total', 0) > 0:
        print(f"  Avg trust radius: {stats.get('avg_trust_radius', 0):.2f}")

    print(f"\n  Database location: {db.db_path}")

    return 0


def main():
    """Main entry point."""
    print_banner()

    parser = argparse.ArgumentParser(
        description="AETHERMOORE Antivirus - Physics-Based Threat Detection"
    )
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # scan
    scan_parser = subparsers.add_parser("scan", help="Scan file or directory")
    scan_parser.add_argument("path", help="Path to scan")
    scan_parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    scan_parser.add_argument("--no-recursive", action="store_true", help="Don't scan subdirectories")

    # quick
    quick_parser = subparsers.add_parser("quick", help="Quick scan (executables only)")
    quick_parser.add_argument("path", help="Path to scan")

    # deep
    deep_parser = subparsers.add_parser("deep", help="Deep scan (all files)")
    deep_parser.add_argument("path", help="Path to scan")

    # watch
    watch_parser = subparsers.add_parser("watch", help="Real-time monitoring")
    watch_parser.add_argument("path", help="Path to monitor")

    # trust
    trust_parser = subparsers.add_parser("trust", help="Show trust status")
    trust_parser.add_argument("path", help="Path to check")

    # stats
    stats_parser = subparsers.add_parser("stats", help="Show database statistics")

    args = parser.parse_args()

    if args.command == "scan":
        return cmd_scan(args)
    elif args.command == "quick":
        return cmd_quick(args)
    elif args.command == "deep":
        return cmd_deep(args)
    elif args.command == "watch":
        return cmd_watch(args)
    elif args.command == "trust":
        return cmd_trust(args)
    elif args.command == "stats":
        return cmd_stats(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
