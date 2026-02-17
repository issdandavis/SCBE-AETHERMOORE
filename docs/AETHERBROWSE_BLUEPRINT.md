# AETHERBROWSE Blueprint (Phase-1)

## Goal

Wire the existing SCBE browser stack to an auditable CDP-first CLI path where every browser action is
validated through local geometric governance before execution.

## Current Phase-1 Files

- `agents/aetherbrowse_cli.py`
  - CLI entrypoint with backend/session/action flags.
  - Supports single actions (`navigate`, `click`, `type`, `scroll`, `snapshot`, `extract`, `screenshot`) and scripted action batches.

- `agents/browser/action_validator.py`
  - Converts actions into embeddings using `vision_embedding`.
  - Applies PHDM containment (`SimplePHDM`) and bounds checks (`BoundsChecker`).
  - Emits structured `ActionValidationResult`.

- `agents/browser/dom_snapshot.py`
  - Low-dependency HTML → normalized text snapshot utility.
  - Produces concise counts + content hash for audit trail continuity.

- `agents/browser/session_manager.py`
  - `AetherbrowseSession` orchestrates backend creation, validation, execution, and per-action audit logging.
  - Currently supports CDP backend by default.

- `agents/browser/fleet_coordinator.py`
  - Multi-session round-robin coordinator for future swarm scaling.

## Immediate Execution Notes

- CDP backend is implemented in `agents/browsers/cdp_backend.py` and already available in repository.
- Browser state and decision events are recorded in-session and can be consumed by downstream audit pipelines.
- This phase intentionally avoids external dependency on an external SCBE API service, while preserving
  compatibility for future integration.

## Recommended Next Step

1. Add tests for:
   - validator decision mapping for DENY/ESCALATE paths
   - snapshot generation and hash stability
   - session execution with a mocked backend
2. Add backend adapters for Playwright/Selenium behind the same session interface.
3. Add Spiralverse message envelope logging for roundtable/mesh events.
