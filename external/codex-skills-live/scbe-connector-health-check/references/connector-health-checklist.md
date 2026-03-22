# SCBE Connector Health Checklist

## Core Health Signals

- Connector appears in discovery.
- Non-destructive call succeeds.
- Auth required only where expected.
- Latency is consistent and below local threshold.

## Severity Flags

- `ok`: fully functional for non-destructive calls.
- `requires_auth`: tool exists but needs token/scope/user login.
- `degraded`: intermittent errors or high latency.
- `down`: unavailable or returning hard failures.

## Standard Verification Steps

1. **Discovery check**: confirm connector/service is discoverable.
2. **Permission check**: ensure required environment or auth tokens exist.
3. **Function call check**: run one safe read/list/search call.
4. **Error capture**: log exact code + message.
5. **Fallback assignment**: switch to safe branch or defer workflows.

## Triage Template

- connector: `<name>`
- status: `<ok | requires_auth | degraded | down>`
- impact: `<none | low | medium | high>`
- evidence: `<command + error>`
- next_step: `<one action with owner>`

## Weekly Maintenance

- run health check before any campaign batch
- rerun after credential changes
- archive stale connectors from active routing lists
