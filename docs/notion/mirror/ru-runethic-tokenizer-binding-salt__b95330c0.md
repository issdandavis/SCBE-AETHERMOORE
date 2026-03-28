---
source: notion_export_jsonl
notion_id: b95330c0-8b7c-4df0-b5f1-a3611aa1c373
exported_at: 2026-02-16T07:45:09.189720
url: https://www.notion.so/RU-Runethic-Tokenizer-Binding-Salt-b95330c08b7c4df0b5f1a3611aa1c373
categories:
- technical
- lore
---

# RU — Runethic Tokenizer (Binding / Salt)

Language connection
Tongue code: RU
Language name: Runethic
Domain meaning: Binding, commitment material
SS1 default sections: salt
Corresponding tokenizer
Reference implementation: 🐍 Six Tongues + GeoSeal CLI - Python Implementation
CLI usage:
Notes
RU is the default for salts and other “commitment” bytes.
Keep canonicalization rules strict (lowercase + ASCII apostrophe).
Tokenizer tables (from reference implementation)
Prefixes (high nibble 0–15): run, eth, gar, hol, jid, kyr, lum, mor, nid, oth, pur, qar, sid, tor, uv, vyr
Suffixes (low nibble 0–15): eth, gar, hol, jid, kyr, lum, mor, nid, oth, pur, qar, sid, tor, uv, vyr, run
Token shape: prefix' suffix (ASCII apostrophe), lowercase only.