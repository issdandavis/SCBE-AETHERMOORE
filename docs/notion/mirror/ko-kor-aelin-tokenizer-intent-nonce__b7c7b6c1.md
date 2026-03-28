---
source: notion_export_jsonl
notion_id: b7c7b6c1-0107-4c19-b1c8-f676f7299239
exported_at: 2026-02-16T07:45:08.773862
url: https://www.notion.so/KO-Kor-aelin-Tokenizer-Intent-Nonce-b7c7b6c101074c19b1c8f676f7299239
categories:
- technical
- lore
---

# KO — Kor'aelin Tokenizer (Intent / Nonce)

Language connection
Tongue code: KO
Language name: Kor'aelin
Domain meaning: Intent, flow, nonce material
SS1 default sections: nonce (see Section → Tongue routing table)
Corresponding tokenizer
Reference implementation: 🐍 Six Tongues + GeoSeal CLI - Python Implementation 
CLI usage:
Notes
Use compact spell-text in SS1 blobs: ko:<tokens...> (marker appears once per field).
Tokenizer tables (from reference implementation)
Prefixes (high nibble 0–15): kor, ael, lin, dah, ru, mel, ik, sor, in, tiv, ar, ul, mar, vex, yn, zha
Suffixes (low nibble 0–15): ah, el, in, or, ru, ik, mel, sor, tiv, ul, vex, zha, dah, lin, yn, mar
Token shape: prefix' suffix (ASCII apostrophe), lowercase only.