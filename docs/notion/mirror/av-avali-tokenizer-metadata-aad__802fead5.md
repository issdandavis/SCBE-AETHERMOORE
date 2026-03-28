---
source: notion_export_jsonl
notion_id: 802fead5-ccfe-4b07-89cd-f263bc858345
exported_at: 2026-02-16T07:45:06.255197
url: https://www.notion.so/AV-Avali-Tokenizer-Metadata-AAD-802fead5ccfe4b0789cdf263bc858345
categories:
- technical
- lore
---

# AV — Avali Tokenizer (Metadata / AAD)

Language connection
Tongue code: AV
Language name: Avali
Domain meaning: Transport, context metadata
SS1 default sections: aad
Corresponding tokenizer
Reference implementation: 🐍 Six Tongues + GeoSeal CLI - Python Implementation
CLI usage:
Notes
Treat AV spell-text as human-auditable metadata. Keep it ASCII-clean upstream, then encode.
Tokenizer tables (from reference implementation)
Prefixes (high nibble 0–15): av, ki, ree, tal, shk, fir, nol, pyr, zek, qil, vyr, xan, bol, cim, dyr, ept
Suffixes (low nibble 0–15): i, ree, tal, shk, fir, nol, pyr, zek, qil, vyr, xan, bol, cim, dyr, ept, av
Token shape: prefix' suffix (ASCII apostrophe), lowercase only.