# Polly Chat Model Blueprint

## Purpose
Build a dedicated small chat model for Aethermoore support, product navigation, and operator assistance.

Target model:
- `issdandavis/polly-chat-qwen-0.5b`

Base model:
- `issdandavis/scbe-pivot-qwen-0.5b`

Models not to overload:
- `issdandavis/phdm-21d-embedding` is embeddings-only
- `issdandavis/spiralverse-ai-federated-v1` is a federated-learning lane, not the default chatbot

## Job Definition
Polly is not a general research model. Polly should be strong at:
- buyer onboarding
- product bundle orientation
- support triage
- site navigation
- Kindle app help
- concise operator answers
- collecting structured feedback for future training

Polly should avoid:
- pretending to know hidden package contents
- long speculative answers
- raw system-internals leakage
- unsafe direct payment or credential handling

## Voice
Desired voice:
- calm
- concise
- practical
- archivist-like rather than mascot-like
- helpful without overexplaining

Response shape:
- answer directly
- point to the next concrete step
- separate what exists now from what still needs setup

## Training Data Lanes
Stage 1 seed data:
- buyer manuals
- delivery and access instructions
- support flows
- package descriptions
- Kindle app help flows
- site navigation prompts

Stage 2 expansion:
- real chat transcripts from Kindle app and sidebar sessions
- thumbs-up / needs-work feedback exported from the chat widget
- support email summaries redacted into training pairs

Stage 3 alignment:
- preference pairs for better refusal behavior
- concise-vs-rambling comparisons
- navigation success examples

## Dataset Format
Primary SFT format:
- JSONL with a top-level `messages` field
- each record contains `system`, `user`, and `assistant` turns
- optional metadata fields: `track`, `source_type`, `quality`, `surface`

## Evaluation Targets
Polly should be benchmarked on:
- product navigation accuracy
- delivery/access help accuracy
- support classification accuracy
- short-answer quality
- refusal quality for unknown or unsafe asks

Minimum first-pass eval themes:
- Where do I start?
- What did I buy?
- How do I get access?
- Which package contains what?
- Which model should power the chatbot?
- What belongs in the public site vs private app?

## Deployment Targets
Use the same model across:
- Kindle app chat lane
- future Polly sidebar on the site
- internal support console
- lightweight app embeds

Security split:
- private apps may use a local Hugging Face token
- public web surfaces should call a proxy endpoint instead of exposing tokens client-side

## Immediate Build Order
1. Ship the chat surface in the Kindle app and Android assets.
2. Train a seed LoRA/SFT adapter on the local seed dataset.
3. Evaluate against base Qwen 0.5B on support and navigation prompts.
4. Export real feedback from the widget into the next dataset revision.
5. Promote only after the model beats the base on the defined support/navigation tasks.
