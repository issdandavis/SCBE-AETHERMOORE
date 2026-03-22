# Knowledge Propagation

## Objective

Propagate SCBE knowledge to other AI systems with consistent, self-contained artifacts.

## Procedure

1. Identify target AI and runtime context.
2. Scope required SCBE layers/components/constants.
3. Generate context document from `assets/context-template.md`.
4. Generate machine-readable knowledge file from `assets/scbe-knowledge-v4.yaml`.
5. Include only relevant glossary subset for target.
6. If requested, package files for HF dataset publication.

## Publishing Pattern

Dataset example: `issdandavis/scbe-knowledge-base`

Suggested files:

- `scbe-knowledge-v4.yaml`
- `context-templates/ko-agent.md`
- `context-templates/ca-agent.md`
- `glossary.json`

## Output Contract

When producing system prompts or context docs, require:

1. `state_vector` JSON with coherence, energy, drift
2. `decision_record` JSON with action, signature, timestamp
