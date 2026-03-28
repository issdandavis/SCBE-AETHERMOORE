---
source: notion_export_jsonl
notion_id: ae16d484-05d6-4ac7-a37e-fcd8f7c3c844
exported_at: 2026-02-16T07:45:07.080567
url: https://www.notion.so/CA-Cassivadan-Tokenizer-Compute-Ciphertext-ae16d48405d64ac7a37efcd8f7c3c844
categories:
- technical
- lore
---

# CA — Cassivadan Tokenizer (Compute / Ciphertext)

Language connection
Tongue code: CA
Language name: Cassivadan (Cassivadan / Cassisivadan)
Domain meaning: Compute, bitcraft, payload bytes
SS1 default sections: ct
Corresponding tokenizer
Reference implementation: 🐍 Six Tongues + GeoSeal CLI - Python Implementation
CLI usage:
Notes
For AEAD payloads, CA typically carries the ciphertext body bytes (tag is separate in DR).
Tokenizer tables (from reference implementation)
Prefixes (high nibble 0–15): cas, si, va, dan, elo, fri, gla, hir, ilo, jun, kal, lor, min, nor, opi, pul
Suffixes (low nibble 0–15): si, va, dan, elo, fri, gla, hir, ilo, jun, kal, lor, min, nor, opi, pul, cas
Token shape: prefix' suffix (ASCII apostrophe), lowercase only.