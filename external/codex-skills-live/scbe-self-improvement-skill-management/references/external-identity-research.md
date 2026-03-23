# External Identity Research (Verification-First)

Use this file when user asks for profile/repo lookup across names such as:

- `issdandavis`
- `@davisissac`
- `Issac Davis`
- `Isaac Daniel Davis`
- SCBE/AETHERMOORE/PHDM references

## Canonical Identifier Block

Treat this block as the primary normalization target:

- GitHub owner: `issdandavis`
- SCBE repo slug: `SCBE-AETHERMOORE`
- HF model slug: `phdm-21d-embedding`
- HF dataset slug pattern: `issdandavis/*`
- X handle candidate: `@davisissac`

## Verification Policy

Do not promote external profile claims to canonical SCBE knowledge unless verified from primary sources.

Verification tiers:

1. `confirmed`: primary source and cross-checked
2. `provisional`: single source, plausible, not cross-checked
3. `unverified`: user-provided or aggregator-only

Always label findings with a tier.

## Disambiguation Guidance

When names collide (`Issac` vs `Isaac`, sports/actor/historical profiles):

1. Anchor on project identifiers first (`SCBE-AETHERMOORE`, `issdandavis`).
2. Reject matches with no project overlap.
3. Keep non-matching persons in a separate "excluded matches" section.

## Output Template

Use this structure for lookup outputs:

1. `confirmed identifiers`
2. `provisional identifiers`
3. `excluded matches`
4. `open verification tasks`

## Safety

- Avoid sharing personal data not required for technical workflow.
- Do not treat social profile text as canonical constants/specs.
- Keep formula/constants sourced from SCBE canonical docs, not social bios.
