---
name: combo-stack
description: "Pre-built skill stacks for common multi-skill tasks. Use when user needs research, training, publishing, governance, deployment, story writing, or game dev — loads the right combination of skills automatically."
---

# Combo Stack — Skill Combinator

When a task spans multiple SCBE skills, load the right combination as a coordinated stack.

## Available Stacks

### /combo research
**Skills**: spiral-search + scbe-web-research-verified + scbe-browser-swarm-ops + scbe-context-catalog
**Use when**: Deep research, market analysis, competitor scanning, fact-checking
**Invoke**: `Skill spiral-search`, then `Skill scbe-web-research-verified` for verification

### /combo train
**Skills**: scbe-training-pipeline + hf-model-trainer + scbe-colab-compute + scbe-fleet-deploy
**Use when**: Preparing training data, running fine-tuning, deploying models
**Invoke**: `Skill scbe-training-pipeline` for data prep, `Skill hf-model-trainer` for training

### /combo publish
**Skills**: scbe-content-publisher + scbe-article-posting + scbe-youtube-factory + scbe-doc-maker
**Use when**: Publishing content across platforms, creating articles, videos, docs
**Invoke**: `Skill scbe-article-posting` for writing, `Skill scbe-content-publisher` for distribution

### /combo govern
**Skills**: scbe-governance-gate + scbe-9d-state-engine + scbe-manifold-validate + scbe-gate-swap
**Use when**: Evaluating governance decisions, validating state, checking integrity
**Invoke**: `Skill scbe-governance-gate` for evaluation

### /combo deploy
**Skills**: scbe-fleet-deploy + scbe-github-release + publish + scbe-shopify-store-ops
**Use when**: Releasing versions, deploying to npm/PyPI, updating Shopify
**Invoke**: `Skill scbe-github-release` for version, `Skill publish` for package managers

### /combo story
**Skills**: scbe-story-canon-writer + book-manuscript-edit + speed-line-delivery + webtoon-storyboard
**Use when**: Writing/editing book chapters, creating manhwa, story development
**Invoke**: `Skill scbe-story-canon-writer` for drafting, `Skill speed-line-delivery` for editing

### /combo game
**Skills**: aethermoor-scbe-integration + tuxemon-mod-system + tuxemon-monster-creator + tuxemon-map-editor
**Use when**: Game development, adding monsters, building maps, wiring SCBE into gameplay
**Invoke**: `Skill aethermoor-scbe-integration` for bridge work

### /combo full
**Skills**: ALL of the above + scbe-ops-control + scbe-flock-shepherd + hydra-clawbot-synthesis
**Use when**: User says "full HYDRA", "everything", "all systems"
**Invoke**: Start with `Skill hydra-clawbot-synthesis` as orchestrator

## How to Use
When you identify the user's task, announce which combo you're loading and invoke the primary skill for that stack. The skill content will guide you on when to invoke the secondary skills.
