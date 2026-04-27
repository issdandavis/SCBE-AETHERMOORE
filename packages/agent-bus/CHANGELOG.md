# Changelog

All notable changes to `scbe-agent-bus` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

While the package is on `0.x`, the API may break between minor versions.

## [0.1.0] - 2026-04-27

### Added
- Initial public release on npm.
- `runEvent(event, options?)` — run a single AI / human / AI event through the SCBE governed runner.
- `runBatch(events, options?)` — run an ordered batch and receive per-event typed results.
- `SCHEMA_VERSION` constant — pinned to `scbe-agentbus-pipe-result-v1`.
- Type exports: `AgentBusEvent`, `AgentBusResult`, `Privacy`, `TaskType`, `RunnerOptions`.
- README documenting install, contract surface, and architecture (Node-side wrapper around the existing Python `agentbus_pipe.mjs` runner).

### Notes
- The Python side remains the source of truth for governance. This package only wraps the spawn glue.
- Consumers must provide a `repoRoot` pointing at an SCBE repo checkout that owns the runner and Python CLI.
- Branches 1, 2, 4 of the agent-bus feature plan (default rehearsal gate, mission envelope, trace spans) are not yet landed in this package; they are pre-1.0 roadmap items.
