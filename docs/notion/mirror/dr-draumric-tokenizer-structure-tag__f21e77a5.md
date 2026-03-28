---
source: notion_export_jsonl
notion_id: f21e77a5-c3b1-4e42-a220-59e7908117f3
exported_at: 2026-02-16T07:45:04.943868
url: https://www.notion.so/DR-Draumric-Tokenizer-Structure-Tag-f21e77a5c3b14e42a22059e7908117f3
categories:
- technical
- lore
---

# DR — Draumric Tokenizer (Structure / Tag)

Language connection
Tongue code: DR
Language name: Draumric
Domain meaning: Structure, integrity, authentication
SS1 default sections: tag
Corresponding tokenizer
Reference implementation: 🐍 Six Tongues + GeoSeal CLI - Python Implementation
CLI usage:
Notes
DR is the canonical home for authentication tags, signatures, and integrity artifacts.
If you concatenate multiple auth pieces, length-prefix them first (per best practice).
Tokenizer tables (from reference implementation)
Prefixes (high nibble 0–15): dra, um, ric, sel, tor, vyl, wyn, xel, yor, zil, aum, bel, cil, del, eel, fil
Suffixes (low nibble 0–15): um, ric, sel, tor, vyl, wyn, xel, yor, zil, aum, bel, cil, del, eel, fil, dra
Token shape: prefix' suffix (ASCII apostrophe), lowercase only.