# Eyeballs Plan - 2026-03-25

## Objective

Get more qualified traffic to the public SCBE surfaces without collapsing the message into one giant claim pile.

The immediate goal is not broad brand awareness. The immediate goal is to create a clean path:

`post -> proof page -> offer or contact`

## Current public surfaces

### 1. Root offer page
- URL: `https://aethermoore.com/`
- Strength: clear one-product checkout path
- Weakness: does not show enough proof for skeptical technical traffic

### 2. GitHub Pages docs hub
- URL: `https://issdandavis.github.io/SCBE-AETHERMOORE/`
- Strength: public and easy to link
- Weakness: the generated homepage was too thin and looked like a generic docs landing page

### 3. Demo Lab
- Local source: `docs/demos/index.html`
- Strength: broad curiosity surface with multiple demos
- Weakness: needs to be treated as a top-of-funnel proof page, not an afterthought

### 4. Red Team Sandbox
- Local source: `docs/redteam.html`
- Strength: strongest proof-oriented page in the repo
- Weakness: not clearly connected to the GitHub Pages hub

### 5. Support + manuals
- Local source: `docs/support.html`
- Strength: good recovery path
- Weakness: should support conversion, not be part of the first-touch pitch

## Codebase review: what is marketable now

### A. Public proof surfaces
- `docs/redteam.html`
- `docs/demos/index.html`
- `demo/mars-communication.html`
- `docs/arena.html`

These are the highest-value attention pages because they show behavior, not theory.

### B. Buyer surfaces
- `docs/index.html`
- `docs/product-manual/`
- `docs/support.html`

These are for conversion and recovery after interest exists.

### C. Technical authority surfaces
- `README.md`
- `api/main.py`
- `src/api/main.py`
- `docs/01-architecture/README.md`
- benchmark and research pages

These are for validation after attention exists.

## Main messaging problem

The repo is trying to talk to three audiences at once:

1. builders who want proof
2. buyers who want a simple package
3. enterprise evaluators who want architecture and compliance

Those are different journeys. The fix is routing, not more words.

## Recommended traffic lanes

### Lane 1: Proof-first technical traffic

Use for:
- GitHub
- Hugging Face
- technical social posts
- benchmark posts

Send them to:
- GitHub Pages hub
- then `redteam.html`
- then `demos/index.html`
- then GitHub/API/docs

### Lane 2: Buyer traffic

Use for:
- product posts
- direct CTAs
- short social promos
- anything with "buy" in the post

Send them to:
- root offer page at `https://aethermoore.com/`

Do not send cold buyer traffic to the docs hub first.

### Lane 3: Enterprise or government traffic

Use for:
- outreach
- pilot inquiries
- architecture discussions
- NIST/governance messaging

Send them to:
- architecture overview
- executive summary
- pilot one-pager

Do not send enterprise evaluators to the novel or broad demo pile first.

## Best hook angles for posts

### 1. Red-team proof hook
Use:
- "91 adversarial attacks, 0/15 clean false positives."
- "Most guardrails are static filters. This one accumulates suspicion across the session."
- "Try the benchmark, not the slogan."

Why it works:
- concrete
- testable
- easy to compare

### 2. Visual demo hook
Use:
- Mars communication demo
- Demo Lab clips
- Arena screenshots

Why it works:
- people share visuals faster than architecture diagrams
- it gives you something to post repeatedly without inventing new claims

### 3. Runtime governance hook
Use:
- "This sits between agent intent and action."
- "ALLOW / QUARANTINE / DENY with audit trail."
- "Governance as a runtime layer, not a policy PDF."

Why it works:
- clearer than the full SCBE vocabulary for first-touch traffic

### 4. Builder hook
Use:
- npm/pip install
- public API docs
- open benchmark dataset

Why it works:
- developers trust things they can run

## Content cadence

### Weekly mix
1. one benchmark/proof post
2. one visual demo post
3. one builder post
4. one direct product CTA post

That is enough. More matters less than consistency.

## Recommended post sequence

### Sequence A: technical
1. Post benchmark claim
2. Link to GitHub Pages hub
3. Let people choose Red Team, Demo Lab, or API docs

### Sequence B: conversion
1. Post pain point
2. Link directly to root toolkit page
3. Keep the CTA simple: one product, one price, one manual

### Sequence C: enterprise
1. Post a governance/compliance angle
2. Link to executive summary or architecture
3. Follow with pilot one-pager in outreach

## Immediate fixes already made

1. GitHub Pages homepage was upgraded in `.github/workflows/docs.yml`
   so it routes visitors to the Demo Lab, Red Team Sandbox, API docs, Mars demo, support, and the toolkit offer.
2. `docs/support.html` now uses the same support address as the buyer manuals.
3. The docs deploy now copies `product-manual`, `static`, `arena.html`, `redteam.html`, and `support.html`
   so the public docs hub can actually expose those surfaces.

## Next marketing work to do

### Short term
1. Post screenshots or short clips from `docs/redteam.html` and `docs/arena.html`
2. Use the GitHub Pages hub as the main link for technical posts
3. Keep the root domain reserved for the direct $29 offer

### Medium term
1. Add simple analytics tags so you know which posts send clicks
2. Create a dedicated architecture overview page for enterprise traffic
3. Turn benchmark proof into one reusable image thread and one reusable article

## Hard rule

Do not lead with all of these at once:
- toolkit
- red team
- novel
- enterprise pilot
- HYDRA
- demos
- antivirus
- patent

Lead with one promise per post.

If the post is about proof, send people to proof.
If the post is about buying, send people to buy.
