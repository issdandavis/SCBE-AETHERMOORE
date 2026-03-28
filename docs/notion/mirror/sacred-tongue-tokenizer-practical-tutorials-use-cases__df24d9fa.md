---
source: notion_export_jsonl
notion_id: df24d9fa-632f-4911-bada-5b12e8e6f63e
exported_at: 2026-02-16T07:45:10.913488
url: https://www.notion.so/Sacred-Tongue-Tokenizer-Practical-Tutorials-Use-Cases-df24d9fa632f4911bada5b12e8e6f63e
categories:
- lore
---

# 📚 Sacred Tongue Tokenizer — Practical Tutorials & Use Cases

Educational Materials Version: 1.0
Last Updated: January 2026
Difficulty: Beginner → Advanced
This document defines the canonical "compact" spell-text format used inside SS1 blobs (one tongue prefix per field), provides hands-on tutorials (manual + programmatic), and includes a test suite and integration note for the 21D state spine.
Canonical Format Decision: This tutorial uses compact format (one tongue marker per SS1 field) as the production standard. Verbose format (per-token markers) is for debugging/logging only.
0. Mini-Spec (Read This First)
0.1 Terms
Tongue: a 256-symbol, human-readable encoding for bytes (e.g., ko, ru, ca, dr, av, um)
Token: one byte encoded as a morpheme pair: prefix + "'" + suffix
Spell-text: a sequence of tokens representing bytes, with a tongue marker
Section: a semantic domain in SS1 (e.g., salt, nonce, ct) that routes to a default tongue
Compact format: one tongue marker per spell-text field
Verbose format: tongue marker repeated per token (for debugging/logging)
0.2 Token Format (Byte → Token)
A byte b ∈ [0,255] is encoded by splitting into two nibbles:
Each tongue defines:
prefixes[0..15] (16 strings)
suffixes[0..15] (16 strings)
Token:
Decode reverses the lookup:
Find h from prefix
Find l from suffix
Reconstruct b = (h << 4) | l
Requirement: The prefix and suffix tables must be 1-to-1 (no duplicates), or decode becomes ambiguous.
0.3 Canonicalization Rules (Non-Negotiable)
To guarantee deterministic parsing and safe round-trips:
Lowercase only for all tokens
Apostrophe must be ASCII ' (U+0027). Reject Unicode quotes like ' (U+2019)
Token must match prefix and suffix exactly from the tongue tables
Whitespace normalization: treat runs of whitespace as a single space when parsing
0.4 Spell-Text Formats
0.4.1 Canonical (Compact) — used in SS1 blobs
One tongue marker per field:
ko: appears exactly once at the start of the spell-text
Tokens follow, space-separated
0.4.2 Optional (Verbose) — CLI/logging/testing only
Tongue marker repeated per token:
Rule: SS1 blobs MUST use compact; verbose is for:
CLI debug output
Development logs
Token-by-token validation in tests
0.5 SS1 Blob Grammar (Pipe-Delimited)
Canonical SS1 grammar (recommended):
Optional fields can be appended (e.g., |redact=<spell>).
Constraints:
kid and aad are ASCII key/value fields
| is the delimiter: do not place raw | in values
If you must embed delimiter characters, percent-encode the value first (e.g., URL encoding) and decode after parsing
0.6 Section → Tongue Routing Table (Reference)
Even if your implementation allows override, this routing table is the reference convention:
[nested content]
0.7 Best Practice: Length-Prefix Authentication Bundles
When you concatenate multiple binary pieces into one spell-text field (e.g., auth_tag || signature), always make boundaries explicit.
Recommended pattern:
This prevents ambiguity if sizes ever change.
1. Tutorial 1 — Your First Sacred Tongue Encoding (Manual + Verifiable)
1.1 The Problem
You have a nonce (bytes) and want a representation that is:
Machine-readable ✓
Human-verifiable ✓
Phonetically elegant ✓
Deterministic ✓
1.2 Example Input (16 bytes)
Raw bytes:
We will use Kor'aelin (ko) as the default nonce tongue.
1.3 Manual Encoding (Learn the Nibbles)
Take the first byte: 0x3c
Token:
Your actual prefixes[] and suffixes[] determine the surface string.
1.4 Nibble Debug Printing (Recommended)
Use this helper to make the walkthrough self-verifying against your wordlists:
1.5 Programmatic Encoding (Compact Spell-Text)
1.6 Optional Verbose Debug Output
2. Tutorial 2 — Building a Complete SS1 Encrypted Backup (AES-GCM + PBKDF2)
2.1 Scenario
You want to encrypt a backup file with:
Plaintext: user data
Password: user-supplied passphrase
Output: SS1 spell-text blob for storage/transmission
2.2 Correct Implementation (PBKDF2 Fix + Compact Fields)
This tutorial uses hashlib.pbkdf2_hmac for portability.
2.3 Expected Output Shape (Canonical Compact)
Your format_ss1_blob() should produce fields like: