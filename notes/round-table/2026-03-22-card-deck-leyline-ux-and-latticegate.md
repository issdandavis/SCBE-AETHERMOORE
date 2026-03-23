# 2026-03-22 Card Deck, Leyline UX, and LatticeGate Slice

## Why this note exists

The current design thread is not random. It is converging on a usable operator metaphor:

- cards = bounded system actions
- leylines = dependencies and packet routes
- threats = failing checks, drift, or boundary pressure
- center = safe governed execution
- edge = expensive / risky / adversarial zones

That is a good fit for SCBE because the repo already thinks in lanes, gates, packets, and harmonic costs.

## Three separate assets in the latest paste

### 1. SpiralEngine

This is the right visual metaphor for the governed command mesh.

What it represents well:

- the Poincare disc as execution space
- central safe zone vs. edge-risk expansion
- structures as operator capabilities
- leylines as governed flow paths
- Omega gate as a live health decision
- tutorial overlay as onboarding for nontechnical users

What it should become in product terms:

- a visual swarm / workflow orchestrator
- a card-and-leyline mission board
- a live status surface for packet dispatch, governance, and recovery

Immediate architectural note:

This should live as its own app surface, not mixed with unrelated utilities.

Suggested repo lane:

- `src/ui/spiral-engine/`
- `src/ui/spiral-engine/SpiralEngine.tsx`
- `tests/ui/spiral-engine/`

### 2. QRCodeGenerator

This is a separate utility lane.

Good use cases:

- payment QR generation
- contact / vCard sharing
- download-and-copy marketing utility
- fast storefront or event support tooling

Important constraint:

This should not be in the same module as SpiralEngine. It is a clean standalone product widget.

Suggested repo lane:

- `src/ui/qr/QRCodeGenerator.tsx`
- `tests/ui/qr/`

### 3. latticegate-orchestrator

This is not UI. It is a skill / protocol / audit lane.

Strong parts:

- explicit Davis score definition
- explicit harmonic wall equation
- gate decision semantics
- machine JSON + narrative output contract
- calibration warning discipline

Critical rule:

Keep `UNCALIBRATED` in place until thresholds are empirically validated.

Suggested repo lane:

- `skills/latticegate-orchestrator/SKILL.md`
- `skills/latticegate-orchestrator/references/calibration.md`
- `skills/latticegate-orchestrator/references/model-card.md`

## Main blocker in the pasted form

The pasted artifact is not one runnable file. It is three different system slices concatenated together:

- React game UI
- React QR utility
- markdown/frontmatter skill docs

So the first engineering step is separation, not optimization.

## Card deck model for command systems

This should become a governed operator deck.

### Suit meaning

- `Spades` = core governance / math / security
- `Clubs` = workflow / automation / relay
- `Hearts` = content / contact / user-facing utility
- `Diamonds` = billing / deploy / package / productization

### Rank meaning

- `A` = start card / control node
- `2-5` = primary execution cards
- `6-10` = support or modifier cards
- `J/Q/K` = escalations, exceptions, or high-cost moves
- `Joker` = experimental or unsafe lane

### Leyline meaning

A leyline should mean:

- approved dependency path
- valid packet handoff route
- replayable action flow
- allowed combination of cards

That gives a clean mapping from metaphor to implementation.

## How this maps to current repo stabilization work

This is not a side idea. It maps directly to the foundation pass already in motion:

- premerge triage = deck sorting
- workflow audit = card state scan
- PR readiness = playable or blocked card state
- CodeQL blockers = hostile edge pressure
- packetization = leyline-ready action units

## Near-term build order

1. Split the three pasted assets into separate lanes.
2. Keep the card deck as the top-level operator metaphor.
3. Use SpiralEngine as the visual orchestration surface.
4. Use LatticeGate as the governance-audit skill layer beneath it.
5. Keep QR/payment as a utility card, not as part of the core kernel.

## Product interpretation

The strongest version of this idea is not "a game for its own sake."
It is:

- a governed workflow board that feels like a game
- where every action is bounded, scored, and replayable
- and where the visual metaphor helps users understand why some operations are cheap, risky, blocked, or expensive

That fits SCBE better than a generic dashboard.
