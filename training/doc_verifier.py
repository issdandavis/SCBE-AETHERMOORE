#!/usr/bin/env python3
"""
Document Verification Pipeline — Round Table Consensus

Scans project documentation, computes content hashes, and produces a
doc_manifest.json suitable for HuggingFace dataset provenance.

Uses the Round Table consensus pattern from hydra/consensus.py:
each AI council member (mapped to a Sacred Tongue) can attest a document,
and a configurable quorum determines verification status.

Usage:
  python training/doc_verifier.py                      # Generate manifest
  python training/doc_verifier.py --check               # Verify existing manifest
  python training/doc_verifier.py --json                # JSON output
  python training/doc_verifier.py --attest openai,anthropic  # Add attestations

@module training/doc_verifier
@layer Layer 14
@component Document Verification Pipeline
@version 1.0.0
"""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent.parent

# ═══════════════════════════════════════════════════════════════
# Round Table Council Configuration
# Maps AI providers to Sacred Tongues for verification tiers
# ═══════════════════════════════════════════════════════════════

COUNCIL_MEMBERS = [
    {
        "id": "gpt",
        "provider": "openai",
        "role": "Analytical Strategist",
        "tongue": "AV",
        "signature_suffix": "-- GPT (OpenAI)",
    },
    {
        "id": "claude",
        "provider": "anthropic",
        "role": "Thoughtful Advisor",
        "tongue": "KO",
        "signature_suffix": "-- Claude (Anthropic)",
    },
    {
        "id": "grok",
        "provider": "xai",
        "role": "Creative Challenger",
        "tongue": "CA",
        "signature_suffix": "-- Grok (xAI)",
    },
    {
        "id": "sonar",
        "provider": "perplexity",
        "role": "Research Specialist",
        "tongue": "RU",
        "signature_suffix": "-- Sonar (Perplexity)",
    },
    {
        "id": "gemini",
        "provider": "google",
        "role": "Multimodal Expert",
        "tongue": "UM",
        "signature_suffix": "-- Gemini (Google)",
    },
]

# BFT quorum: need >2/3 for Byzantine fault tolerance (3 of 5)
DEFAULT_QUORUM = 3

# ═══════════════════════════════════════════════════════════════
# Document Categories and Discovery
# ═══════════════════════════════════════════════════════════════

CATEGORY_RULES: List[Tuple[str, str, List[str]]] = [
    # (glob pattern, category, layer tags)
    ("paper/*.tex", "whitepaper", ["L1", "L5", "L12"]),
    ("ARCHITECTURE.md", "architecture", ["L1", "L14"]),
    ("SYSTEM_ARCHITECTURE.md", "architecture", ["L1", "L14"]),
    ("LAYER_INDEX.md", "architecture", ["L1", "L14"]),
    ("SCBE_SYSTEM_OVERVIEW.md", "architecture", ["L1", "L14"]),
    ("api/governance-schema.yaml", "api-spec", ["L13"]),
    ("SCBE_PATENT_PORTFOLIO.md", "patent", []),
    ("PATENT_CLAIMS_COVERAGE.md", "patent", []),
    ("SECURITY.md", "security", ["L5", "L8", "L12", "L13"]),
    ("docs/05-industry-guides/*.md", "industry-guide", ["L13"]),
    ("docs/03-deployment/*.md", "deployment", ["L14"]),
    ("docs/00-overview/*.md", "tutorial", []),
    ("CHANGELOG.md", "changelog", []),
    ("README.md", "reference", []),
    ("CONTRIBUTING.md", "reference", []),
    ("CLAUDE.md", "reference", ["L1", "L14"]),
    ("DEMOS.md", "tutorial", []),
    ("docs/**/*.md", "reference", []),
]


def discover_docs() -> List[Dict[str, Any]]:
    """Scan repo for documentation files and categorize them."""
    seen: set[str] = set()
    docs: List[Dict[str, Any]] = []

    for pattern, category, layers in CATEGORY_RULES:
        for p in sorted(REPO_ROOT.glob(pattern)):
            rel = str(p.relative_to(REPO_ROOT))
            if rel in seen:
                continue
            seen.add(rel)

            content = p.read_bytes()
            sha = hashlib.sha256(content).hexdigest()

            doc_id = re.sub(r"[^a-z0-9]", "-", rel.lower()).strip("-")
            doc_id = re.sub(r"-+", "-", doc_id)

            docs.append({
                "id": doc_id,
                "filename": rel,
                "content_hash": f"sha256:{sha}",
                "size_bytes": len(content),
                "version": "1.0.0",
                "category": category,
                "layers": layers,
                "verification": {
                    "status": "unverified",
                    "consensus_required": DEFAULT_QUORUM,
                    "verified_by": [],
                    "signatures": [],
                },
            })

    return docs


# ═══════════════════════════════════════════════════════════════
# Attestation (HMAC-based, compatible with providers.ts)
# ═══════════════════════════════════════════════════════════════

def compute_attestation_hash(
    content_hash: str,
    verified_by: List[str],
    timestamp: str,
    secret_key: bytes = b"scbe-doc-verification-v1",
) -> str:
    """HMAC-SHA256 attestation hash binding content to verifiers and time."""
    payload = f"{content_hash}|{','.join(sorted(verified_by))}|{timestamp}"
    return hmac.new(secret_key, payload.encode(), hashlib.sha256).hexdigest()


def attest_document(
    doc: Dict[str, Any],
    provider_ids: List[str],
    secret_key: bytes = b"scbe-doc-verification-v1",
) -> Dict[str, Any]:
    """Add Round Table attestations to a document entry."""
    member_map = {m["id"]: m for m in COUNCIL_MEMBERS}

    for pid in provider_ids:
        if pid not in member_map:
            raise ValueError(f"Unknown council member: {pid}")

    verification = doc["verification"]

    # Add new attestations (don't duplicate)
    existing = set(verification["verified_by"])
    for pid in provider_ids:
        if pid not in existing:
            verification["verified_by"].append(pid)
            verification["signatures"].append(member_map[pid]["signature_suffix"])

    # Check quorum
    if len(verification["verified_by"]) >= verification["consensus_required"]:
        now = datetime.now(timezone.utc).isoformat()
        verification["status"] = "verified"
        verification["verified_at"] = now
        verification["attestation_hash"] = compute_attestation_hash(
            doc["content_hash"],
            verification["verified_by"],
            now,
            secret_key,
        )
    else:
        verification["status"] = "pending"

    return doc


# ═══════════════════════════════════════════════════════════════
# Manifest generation and verification
# ═══════════════════════════════════════════════════════════════

def compute_manifest_hash(documents: List[Dict[str, Any]]) -> str:
    """SHA256 over the full document list for manifest integrity."""
    payload = json.dumps(documents, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def build_manifest(
    documents: List[Dict[str, Any]],
    orchestration_mode: str = "round_robin",
) -> Dict[str, Any]:
    """Assemble the full doc_manifest.json."""
    return {
        "schema_version": "1.0.0",
        "verification_protocol": "roundtable-consensus",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "council": {
            "members": COUNCIL_MEMBERS,
            "quorum": DEFAULT_QUORUM,
            "orchestration_mode": orchestration_mode,
        },
        "documents": documents,
        "manifest_hash": compute_manifest_hash(documents),
    }


def verify_manifest(manifest: Dict[str, Any]) -> List[str]:
    """Verify an existing manifest — check hashes and attestations."""
    errors: List[str] = []

    # Check manifest integrity
    expected_hash = compute_manifest_hash(manifest["documents"])
    if manifest.get("manifest_hash") != expected_hash:
        errors.append(f"Manifest hash mismatch: expected {expected_hash[:16]}...")

    # Check each document
    for doc in manifest["documents"]:
        filepath = REPO_ROOT / doc["filename"]
        if not filepath.exists():
            errors.append(f"Missing file: {doc['filename']}")
            continue

        # Verify content hash
        content = filepath.read_bytes()
        actual_hash = f"sha256:{hashlib.sha256(content).hexdigest()}"
        if actual_hash != doc["content_hash"]:
            errors.append(
                f"Hash mismatch: {doc['filename']} "
                f"(expected {doc['content_hash'][:30]}..., got {actual_hash[:30]}...)"
            )

        # Verify attestation if claimed verified
        v = doc["verification"]
        if v["status"] == "verified":
            if len(v["verified_by"]) < v["consensus_required"]:
                errors.append(
                    f"Insufficient attestations: {doc['filename']} "
                    f"({len(v['verified_by'])}/{v['consensus_required']})"
                )

    return errors


# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(
        description="SCBE Document Verification Pipeline (Round Table Consensus)"
    )
    parser.add_argument("--check", type=str, help="Verify existing manifest JSON file")
    parser.add_argument("--json", action="store_true", help="Output full manifest as JSON")
    parser.add_argument(
        "--attest", type=str,
        help="Comma-separated provider IDs to attest (e.g., openai,anthropic,perplexity)"
    )
    parser.add_argument(
        "--out", type=str, default=None,
        help="Write manifest to file (default: stdout)"
    )
    parser.add_argument(
        "--mode", choices=["round_robin", "topic_based", "free_form"],
        default="round_robin",
        help="Orchestration mode"
    )
    args = parser.parse_args()

    # Verify existing manifest
    if args.check:
        with open(args.check, "r") as f:
            manifest = json.load(f)
        errors = verify_manifest(manifest)
        if errors:
            print(f"Verification FAILED ({len(errors)} errors):")
            for e in errors:
                print(f"  - {e}")
            return 1
        verified = sum(1 for d in manifest["documents"] if d["verification"]["status"] == "verified")
        total = len(manifest["documents"])
        print(f"Manifest OK: {total} docs, {verified} verified, hash={manifest['manifest_hash'][:16]}...")
        return 0

    # Discover and build
    docs = discover_docs()

    # Apply attestations if requested
    if args.attest:
        provider_ids = [p.strip() for p in args.attest.split(",")]
        for doc in docs:
            attest_document(doc, provider_ids)

    manifest = build_manifest(docs, orchestration_mode=args.mode)

    if args.json or args.out:
        output = json.dumps(manifest, indent=2, ensure_ascii=False)
        if args.out:
            Path(args.out).write_text(output + "\n")
            verified = sum(1 for d in docs if d["verification"]["status"] == "verified")
            print(f"Wrote {args.out}: {len(docs)} docs, {verified} verified")
        else:
            print(output)
    else:
        # Summary mode
        verified = sum(1 for d in docs if d["verification"]["status"] == "verified")
        pending = sum(1 for d in docs if d["verification"]["status"] == "pending")
        unverified = sum(1 for d in docs if d["verification"]["status"] == "unverified")

        print(f"SCBE Document Manifest — Round Table Consensus")
        print(f"  Protocol:    {manifest['verification_protocol']}")
        print(f"  Quorum:      {DEFAULT_QUORUM}/{len(COUNCIL_MEMBERS)} council members")
        print(f"  Documents:   {len(docs)}")
        print(f"  Verified:    {verified}")
        print(f"  Pending:     {pending}")
        print(f"  Unverified:  {unverified}")
        print(f"  Hash:        {manifest['manifest_hash'][:32]}...")
        print()

        # Category breakdown
        cats: Dict[str, int] = {}
        for d in docs:
            cats[d["category"]] = cats.get(d["category"], 0) + 1
        print("By Category:")
        for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
            print(f"  {cat}: {count}")

        print()
        print("Council Members:")
        for m in COUNCIL_MEMBERS:
            print(f"  {m['tongue']} | {m['id']:<8} | {m['role']:<25} | {m['signature_suffix']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
