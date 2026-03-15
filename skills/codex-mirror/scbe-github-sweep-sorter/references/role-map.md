# Role Map

Use these roles for shared-codebase roundtables.

## Six Tongues

- `KO` / architecture-curator
  - validates structure, boundaries, and doctrine
  - best for specs, architecture, and design review

- `AV` / transport-discovery
  - gathers repo, PR, issue, and connector state
  - best for search, inventory, routing, and reproduction steps

- `RU` / policy-governance
  - checks rules, permissions, rollout gates, and non-goals
  - best for approval logic and action bounds

- `CA` / implementation-engineer
  - writes code in owned paths
  - best for feature work and fixes

- `UM` / security-auditor
  - checks threat surfaces, alerts, secrets, permissions, and abuse paths
  - best for high-risk reviews and security fixes

- `DR` / schema-release-memory
  - owns schemas, evidence, changelogs, release memory, and persistent records
  - best for structured output and handoff durability

## Spine

- `SPINE` / integration-coordinator
  - optional coordination lane
  - tracks mission state, packet routing, conflicts, and completion
  - should avoid taking overlapping edit ownership unless explicitly assigned
