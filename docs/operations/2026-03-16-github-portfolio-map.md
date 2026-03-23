# GitHub Portfolio Map

Date: 2026-03-16

## Purpose

This note converts the account cleanup into an operating portfolio map.

The goal is not to classify every repo by sentimental value. The goal is to make it obvious which repositories should carry identity, which ones should stay as technical modules, which ones are commercial support lanes, and which ones are now archive/reference only.

## Category 1: Main Product

These are the repos that should define the account's present-tense identity.

- `SCBE-AETHERMOORE`
  - Main runtime and product monorepo.
  - Contains kernel, control plane, HYDRA operator lane, phone lane, and webtoon/manhwa production lane.

## Category 2: Core Modules To Keep Active

These are useful as extracted technical surfaces that support the main repo and can stand alone cleanly.

- `aetherbrowser`
  - Browser/runtime extraction candidate.
- `hyperbolica`
  - Math primitives extraction.
- `phdm-21d-embedding`
  - Training/model/data research lane.
- `six-tongues-geoseal`
  - Crypto/protocol extraction.
- `spiralverse-protocol`
  - AI-to-AI/protocol module lane.
- `scbe-security-gate`
  - Security hardening/extracted gate lane.

## Category 3: Commercial / Front-End Support

These repos matter because they connect the technical work to actual offers, storefronts, or public entry points.

- `aethermoore-creator-os`
  - Private storefront/theme lane.
- `Shopify-Command-Center`
  - Private commerce operations lane.
- `scbe-promo`
  - Public promo/marketing materials lane.

## Category 4: Proprietary IP / Data

These repos should be treated as moat and source material, not random side projects.

- `SCBE-private`
  - Private assets, training data, lore, personal files.
- `aethromoor-novel`
  - Primary manuscript / story IP repo.
- `spiralverse-chronicles`
  - Lore/worldbuilding support repo.

## Category 5: Playground / R&D / Fun

These are worth keeping because they support experimentation, training ideas, or long-term worldbuilding/game ambitions.

They should not dominate the account's public identity unless the product direction explicitly shifts toward games.

- `tuxemon-spiralverse`
- `endless-sky`
- `orbiter`
- `isaac_ros_pose_estimation`

## Category 6: Reference Forks / Borrowed Tooling

These are useful to learn from, adapt ideas from, or compare architecture against.

They are not the primary product surface.

- `gemini-cli`
- `Mava`
- `LocalAI`
- `transformers`
- `browser-use`
- `n8n`
- `playwright-mcp`
- `openclaw`
- `arckit`
- `arckit-codex`
- `HunyuanVideo`
- `suno-api`

## Category 7: Archive / Museum

These repos now read as historical layers, experiments, demos, Replit forks, or repo-sprawl. They should be treated as archive, not active backlog.

- `scbe-aethermoore-demo`
- `scbe-aethermoore.2`
- `scbe-ultimate`
- `scbe-core`
- `SCBE_Production_Pack`
- `SCBE_Production_Pack.0.1`
- `SCBE-QUANTUM-PROTO`
- `Spiralverse-AetherMoore`
- `AI-Workflow-Architect`
- `AI-Workflow-Architect-1`
- `AI-Workflow-Architect-1.2.2`
- `ai-workflow-architect-main`
- `ai-workflow-architect-pro`
- `ai-workflow-architect-replit`
- `ai-workflow-platform`
- `ai-workflow-systems`
- `ai-orchestration-hub`
- `forgemind-ai-orchestrator`
- `gumroad-automation-demo`
- `shopify-development`
- `chat-archive-system`
- `dropbox-auto-organizer`
- `perplexity-memory-timeline`
- old Avalon/manuscript/writing side repos unless intentionally revived

## Current Queue After Cleanup

### SCBE-AETHERMOORE

Open PRs: `0`

Open issues:

- `#521` Daily Review Failure - 2026-03-16
- `#520` Workflow Audit: 23 high-risk CI masking issue(s) found
- `#517` fix(security): Resolve all 29 CodeQL security alerts

### Other Writable Repos With Open PRs

- `aws-lambda-simple-web-app#20`
- `aws-lambda-simple-web-app#3`
- `aethermoore-creator-os#1`

Everything else left in the account-wide PR queue is mostly in archived/read-only repos and should not be treated as current operating work.

## Recommended Public Identity

If the account needs to look coherent, center it around:

1. `SCBE-AETHERMOORE`
2. `aetherbrowser`
3. `hyperbolica`
4. `phdm-21d-embedding`
5. `aethermoore-creator-os`
6. `spiralverse-protocol`

That gives one visible story:

- one main system repo
- a browser lane
- a math lane
- a model/data lane
- a commercial lane
- a protocol lane

## Operating Rule Going Forward

Use this rule to avoid rebuilding backlog noise:

- ideas go to docs, notes, or issues
- experiments go to branches or playground repos
- PRs open only when they are intended to merge
- archived repos do not keep active PR queues

That one rule will do more for account clarity than any future mass cleanup.
