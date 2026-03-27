---
pretty_name: Polly Chat Seed
license: mit
tags:
  - chat
  - instruction-tuning
  - customer-support
  - navigation
  - scbe
  - aethermoore
task_categories:
  - text-generation
language:
  - en
size_categories:
  - n<1K
---

# Polly Chat Seed

Seed supervised fine-tuning dataset for the Aethermoore `Polly` support and navigation assistant.

## Purpose
This dataset is designed to fine-tune a small chat model for:
- buyer onboarding
- delivery and access help
- package explanation
- support triage
- site and app navigation
- concise operator-facing answers

## Base model target
Primary target model:
- `issdandavis/polly-chat-qwen-0.5b`

Initial base checkpoint:
- `issdandavis/scbe-pivot-qwen-0.5b`

## What this dataset is not
This is not a general research corpus and not an embeddings dataset.
- `issdandavis/phdm-21d-embedding` remains embeddings-only
- `issdandavis/spiralverse-ai-federated-v1` remains a federated-learning lane

## Format
Records are JSONL with:
- `messages`
- `track`
- `source_type`
- `quality`
- `surface`

The `messages` field contains `system`, `user`, and `assistant` turns.

## Current coverage
The seed set covers:
- buyer manuals
- product pages
- delivery and access flows
- support responses
- app/site model routing guidance
- uncertainty/refusal policy for unknown features

## Limitations
- small seed dataset
- English only
- focused on Aethermoore support and navigation use cases
- not intended for open-ended research answers

## Next expansion lanes
- real Kindle app chat transcripts
- sidebar support transcripts
- exported thumbs-up / needs-work feedback
- redacted support email summaries
- preference pairs for concise safe answers
