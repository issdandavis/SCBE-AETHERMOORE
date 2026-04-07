# Phone As Training Lane

Status: active concept  
Date: 2026-03-31  
Scope: use the SCBE Pixel 6 emulator and future phone app as a staged curriculum lane for model training

## Core Idea

The phone should not be treated only as a QA target.

It should also be treated as a training stage where the model learns to behave like a personal extension of the operator:

1. small-screen interaction
2. persistent day-scale memory
3. interruption tolerance
4. task triage instead of essay generation
5. identity continuity across sessions

The emulator is useful because it creates pressure:
- less screen space
- higher friction for settings and context switching
- shorter interaction loops
- more realistic "do one useful thing now" behavior

That pressure is exactly what makes it a good curriculum surface.

## Why This Matters

Desktop chat teaches models to produce long answers.
Phone use teaches models to become an extension of the person using them.

That means the phone lane should optimize for:
- compact but high-value replies
- fast task decomposition
- carry-forward context from earlier turns
- suggestions that reduce taps
- awareness of whether the user is asking, deciding, drafting, or delegating

This is closer to an actual assistant than a benchmark chatbot.

## Training Progression

### Stage 0: Emulator apprenticeship

The SCBE Pixel 6 emulator is the first controlled training environment.

Goals:
- teach the model how a phone user asks for help
- capture short, real operator turns
- compare Polly against stronger models in the same mobile thread
- export thread bundles, SFT rows, and feedback rows

This stage is already supported by:
- [public/arena.html](/C:/Users/issda/SCBE-AETHERMOORE/public/arena.html)
- [kindle-app/www/index.html](/C:/Users/issda/SCBE-AETHERMOORE/kindle-app/www/index.html)
- [polly-hf-chat.js](/C:/Users/issda/SCBE-AETHERMOORE/kindle-app/www/static/polly-hf-chat.js)

### Stage 1: Personal extension mode

Once the phone lane is stable, the model should be trained to act like a personal extension of the user rather than a generic assistant.

Expected behaviors:
- remember active projects and unfinished tasks
- distinguish "note this" from "do this"
- keep tone and reply length appropriate for a phone
- provide one next action instead of five parallel essays
- route into the right working surface when needed

This stage should still be read-first and suggestion-heavy.

### Stage 2: Governed delegation mode

At this stage the model can begin handling bounded actions:
- draft replies
- queue follow-ups
- summarize documents
- prepare inventory or bookkeeping packets
- hand work off to other models or tools

This is where governance matters:
- reads are easy
- writes are quarantined
- financial, legal, or destructive actions are blocked or escalated

### Stage 3: Small-business helper mode

Only after the personal-extension behavior is good enough should the same lane become the small-business helper product.

The business helper is not a separate intelligence.
It is the phone-trained assistant with:
- stronger domain routing
- business profiles
- audit logging
- read-only connectors first
- explicit governance rules for risky actions

## Data We Should Capture

The phone lane should produce training data that desktop chat often misses:

- short queries with real urgency
- follow-up corrections
- compare-model judgments
- abandoned or interrupted threads
- "good enough for now" answers
- route preferences
- session continuity over hours or days

These should be preserved in the thread bundle, not flattened too early.

## What Makes The Phone Lane Different

### Good phone behaviors

- answer in one screen when possible
- offer one strong next step
- preserve ongoing session state
- bias toward action lists, drafts, triage, and handoff packets
- avoid forcing settings or secret-entry flows on the device

### Bad phone behaviors

- giant dashboards
- round-table theatrics
- nine parallel personas
- long-form theory when the user needs a quick decision
- requiring provider credentials on the device

## Architecture Implication

The phone lane becomes part of the model-development loop:

```text
operator uses phone lane
    ->
thread bundle + feedback captured
    ->
ingest into governed chat corpus
    ->
train smaller SCBE chat models
    ->
redeploy improved phone lane
```

That means the phone app is both:
- a product surface
- a data-collection and behavior-shaping surface

## Immediate Next Steps

1. Treat the Pixel 6 lane as the default mobile training surface.
2. Add explicit "personal extension" evaluation criteria to mobile QA.
3. Capture more operator threads before expanding tool execution.
4. Add session-memory review so the app learns continuity, not just one-turn answers.
5. Use compare lanes only when they improve training or decision quality.

## Product Consequence

If this works, the small-business helper app is no longer just "chat on a phone."

It becomes a disciplined training environment for building an assistant that first learns the person, then learns the business.
