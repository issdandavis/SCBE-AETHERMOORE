# Context Capsule Loader (1-5 Windows)

Purpose: Keep Codex context small while backing it with a much larger local retrieval memory.

## Build Capsules

```powershell
python scripts/knowledge/build_context_capsules.py
```

Outputs:
- `training/context_capsules/library_chunks.jsonl`
- `training/context_capsules/capsule_1w.json`
- `training/context_capsules/capsule_3w.json`
- `training/context_capsules/capsule_5w.json`
- `training/context_capsules/manifest.json`

## How To Use In New Sessions

1. Load one capsule first (small context):
- Fast mode: `capsule_1w.json`
- Balanced mode: `capsule_3w.json`
- Deep mode: `capsule_5w.json`

2. Retrieve from `library_chunks.jsonl` only when needed.

3. Keep generated evidence and decisions in Obsidian + repo docs, not in the chat context window.

## Operational Pattern

- Active context: tiny (1-5 windows)
- Background memory: large JSONL corpus
- Retrieval trigger: intent/topic keywords
- Governance trigger: source trust + category + policy gates

This gives a compressed operator context with high recall across a larger source base.
