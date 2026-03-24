---
name: scbe-product-docs-autolog
description: "Auto-log product documentation as it's built. Captures setup steps, commands, screenshots, troubleshooting into the 3-tier manual (Pro/Beginner/Visual). Use when building features, writing setup guides, fixing bugs, or anytime something should be in the user manual."
---

# Product Docs Auto-Logger

When you do ANY of the following, log it to the appropriate manual section:

1. **Run a setup command** → log to Setup Guide
2. **Fix a bug** → log to Troubleshooting
3. **Discover a gotcha** → log to "Need to Know"
4. **Write integration code** → log to Integration Guide
5. **Create a diagram or screenshot** → log to Visual Guide assets

## How to Log

Append to `docs/product-manual/AUTOLOG.jsonl`:

```json
{"timestamp": "ISO8601", "section": "setup|integration|troubleshooting|cli|api|visual", "tier": "pro|beginner|visual", "title": "short title", "content": "what happened / what to document", "commands": ["any CLI commands"], "files": ["relevant file paths"]}
```

## Manual Structure (at docs/product-manual/)

Three tiers, same content, different depth:

- `pro-guide.md` — Dense, command-heavy, assumes expertise
- `beginner-guide.md` — Hand-holding, fallbacks, AI-assisted setup
- `visual-guide.md` — Screenshots, diagrams, tables, minimal text

All auto-generated from AUTOLOG.jsonl entries.

## Rules
- Log EVERY setup-relevant action, even small ones
- Include exact commands that worked (not theoretical ones)
- Note OS (Windows/Mac/Linux) when it matters
- Flag anything that failed before it worked (troubleshooting gold)
- Never skip logging because "it's obvious" — beginners need it
