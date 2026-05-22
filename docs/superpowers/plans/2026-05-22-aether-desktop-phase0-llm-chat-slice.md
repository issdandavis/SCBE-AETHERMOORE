# Aether Desktop — Phase 0 + llm.chat Vertical Slice — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the governed operation chokepoint end-to-end: workflow-engine shared TS types → FastAPI backend spine with governance gate and append-only audit → llm.chat Ollama handler with WS streaming → minimal React shell Chat window.

**Architecture:** Four thin layers wired through a single OperationRequest/Decision/Result contract. `packages/workflow-engine` lives in SCBE (publishable TS library). The backend and shell prototype in `apps/aether-desktop/` inside SCBE (moves to its own repo when stable). The gate is the only path to any handler — no component, app, or workflow bypasses it. Audit rows are written before the gate decides and completed after the handler returns.

**Tech Stack:** TypeScript 6 + Vitest (workflow-engine), Python 3.11+ + FastAPI + Pydantic v2 + httpx + pytest (backend), React 18 + Vite + Vitest (shell), Ollama at localhost:11434.

---

## File Structure

**`packages/workflow-engine/`** — shared TS contract and spec tools (SCBE repo)
- `package.json` — `@scbe/workflow-engine`, private, vitest
- `tsconfig.json` — extends `../../tsconfig.base.json`
- `src/types.ts` — all shared types: OperationRequest, OperationDecision, OperationResult, AuditRecord, WorkflowSpec, WorkflowStep, ValidationError, OperationClient, SCHEMA_VERSION
- `src/validate.ts` — `validate(spec): ValidationError[]`
- `src/preview.ts` — `preview(spec): OperationRequest[]` — no side effects
- `src/index.ts` — public exports
- `tests/validate.test.ts`
- `tests/preview.test.ts`

**`apps/aether-desktop/backend/`** — FastAPI backend (prototype in SCBE; moves to standalone when stable)
- `main.py` — FastAPI app: `/health`, `POST /v1/op`, `WS /v1/events`
- `models.py` — Pydantic: OperationRequest, OperationDecision, OperationResult, AuditRecord
- `gate.py` — `govern(req) -> OperationDecision`
- `audit.py` — `AuditWriter` (append-only JSONL to `.scbe/audit.jsonl`)
- `registry.py` — `OperationRegistry` (register handler, dispatch)
- `handlers/__init__.py`
- `handlers/echo.py` — echo op (spine prover, no external calls)
- `handlers/llm_chat.py` — `llm.chat` over Ollama `/api/chat`
- `tests/__init__.py`
- `tests/conftest.py` — pytest fixtures (TestClient, tmp audit path)
- `tests/test_gate.py`
- `tests/test_audit.py`
- `tests/test_op_endpoint.py`
- `requirements.txt`

**`apps/aether-desktop/shell/`** — clean Vite/React shell (no `eval`, no `dangerouslySetInnerHTML`)
- `package.json`
- `vite.config.ts`
- `src/main.tsx`
- `src/App.tsx`
- `src/BackendClient.ts` — the ONLY path to `/v1/op` and `/v1/events`
- `src/windows/ChatWindow.tsx`
- `tests/BackendClient.test.ts`

---

### Task 1: workflow-engine package scaffold + shared types

**Files:**
- Create: `packages/workflow-engine/package.json`
- Create: `packages/workflow-engine/tsconfig.json`
- Create: `packages/workflow-engine/src/types.ts`
- Create: `packages/workflow-engine/src/index.ts`
- Create: `packages/workflow-engine/tests/validate.test.ts`

- [ ] **Step 1: Write the first failing test**

Create `packages/workflow-engine/tests/validate.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { SCHEMA_VERSION } from '../src/index';

describe('workflow-engine types', () => {
  it('exports the canonical schema version', () => {
    expect(SCHEMA_VERSION).toBe('scbe.operation.v1');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run from repo root:

```powershell
npx vitest run packages/workflow-engine/tests/validate.test.ts
```

Expected: FAIL with `Cannot find module '../src/index'`.

- [ ] **Step 3: Create package.json**

Create `packages/workflow-engine/package.json`:

```json
{
  "name": "@scbe/workflow-engine",
  "version": "0.1.0",
  "private": true,
  "description": "Aether Desktop governed operation contract and workflow spec tools",
  "main": "./src/index.ts",
  "types": "./src/index.ts",
  "scripts": {
    "test": "vitest run"
  },
  "devDependencies": {
    "vitest": "^4.0.17"
  }
}
```

- [ ] **Step 4: Create tsconfig.json**

Create `packages/workflow-engine/tsconfig.json`:

```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "rootDir": "src",
    "outDir": "../../dist/packages/workflow-engine",
    "composite": true,
    "declaration": true,
    "declarationMap": true
  },
  "include": ["src/**/*"]
}
```

- [ ] **Step 5: Create src/types.ts**

Create `packages/workflow-engine/src/types.ts`:

```typescript
export const SCHEMA_VERSION = 'scbe.operation.v1' as const;

export interface OperationRequest {
  schema_version: typeof SCHEMA_VERSION;
  op: string;
  args: Record<string, unknown>;
  request_id: string;
  origin: { kind: 'app' | 'workflow' | 'agent'; id: string };
  workspace?: { id: string; root: string };
  privacy: 'local_only' | 'external_api';
  budget_cents?: number;
  dry_run?: boolean;
}

export type DecisionKind = 'ALLOW' | 'QUARANTINE' | 'ESCALATE' | 'DENY';
export type ZoneKind = 'GREEN' | 'YELLOW' | 'RED';

export interface OperationDecision {
  request_id: string;
  decision: DecisionKind;
  zone: ZoneKind;
  reason: string;
  policy: string;
  latency_ms: number;
}

export interface OperationResult {
  request_id: string;
  ok: boolean;
  output?: Record<string, unknown>;
  error?: { code: string; message: string };
  artifacts?: { kind: string; ref: string }[];
  duration_ms: number;
}

export interface AuditRecord {
  schema_version: typeof SCHEMA_VERSION;
  request_id: string;
  ts_request: string;
  op: string;
  origin: OperationRequest['origin'];
  privacy: string;
  decision: OperationDecision;
  ts_result?: string;
  result_summary?: {
    ok: boolean;
    error_code?: string;
    artifact_refs?: string[];
    output_shape?: string;
  };
}

export interface WorkflowStep {
  id: string;
  when?: string;
  op: string;
  args: Record<string, unknown>;
}

export interface WorkflowSpec {
  id: string;
  trigger: {
    kind: 'manual' | 'event' | 'schedule';
    match?: Record<string, unknown>;
  };
  steps: WorkflowStep[];
}

export interface ValidationError {
  step_id?: string;
  field: string;
  message: string;
}

export interface OperationClient {
  run(req: OperationRequest): Promise<OperationResult>;
}
```

- [ ] **Step 6: Create src/index.ts**

Create `packages/workflow-engine/src/index.ts`:

```typescript
export { SCHEMA_VERSION } from './types';
export type {
  OperationRequest,
  OperationDecision,
  OperationResult,
  AuditRecord,
  WorkflowSpec,
  WorkflowStep,
  ValidationError,
  OperationClient,
  DecisionKind,
  ZoneKind,
} from './types';
export { validate } from './validate';
export { preview } from './preview';
```

Create `packages/workflow-engine/src/validate.ts` (stub to unblock test):

```typescript
import type { ValidationError, WorkflowSpec } from './types';

export function validate(_spec: WorkflowSpec): ValidationError[] {
  return [];
}
```

Create `packages/workflow-engine/src/preview.ts` (stub):

```typescript
import type { OperationRequest, WorkflowSpec } from './types';

export function preview(_spec: WorkflowSpec): OperationRequest[] {
  return [];
}
```

- [ ] **Step 7: Run test to verify it passes**

```powershell
npx vitest run packages/workflow-engine/tests/validate.test.ts
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add packages/workflow-engine
git commit -m "feat(workflow-engine): scaffold package with shared operation contract types"
```

---

### Task 2: validate(spec) — catches malformed workflow specs

**Files:**
- Modify: `packages/workflow-engine/src/validate.ts`
- Modify: `packages/workflow-engine/tests/validate.test.ts`

- [ ] **Step 1: Add failing validate tests**

Append to `packages/workflow-engine/tests/validate.test.ts`:

```typescript
import { validate } from '../src/validate';
import type { WorkflowSpec } from '../src/types';

const validSpec: WorkflowSpec = {
  id: 'test-workflow',
  trigger: { kind: 'manual' },
  steps: [
    { id: 'step-1', op: 'echo', args: {} },
    { id: 'step-2', op: 'llm.chat', args: { messages: [] } },
  ],
};

describe('validate', () => {
  it('returns empty errors for a valid spec', () => {
    expect(validate(validSpec)).toEqual([]);
  });

  it('errors when spec id is empty', () => {
    const errors = validate({ ...validSpec, id: '' });
    expect(errors).toContainEqual({ field: 'id', message: expect.stringContaining('empty') });
  });

  it('errors when steps is empty', () => {
    const errors = validate({ ...validSpec, steps: [] });
    expect(errors).toContainEqual({ field: 'steps', message: expect.stringContaining('empty') });
  });

  it('errors on duplicate step ids', () => {
    const errors = validate({
      ...validSpec,
      steps: [
        { id: 'dup', op: 'echo', args: {} },
        { id: 'dup', op: 'llm.chat', args: {} },
      ],
    });
    expect(errors.some(e => e.step_id === 'dup' && e.field === 'id')).toBe(true);
  });

  it('errors when a step op is empty', () => {
    const errors = validate({
      ...validSpec,
      steps: [{ id: 'step-1', op: '', args: {} }],
    });
    expect(errors).toContainEqual({ step_id: 'step-1', field: 'op', message: expect.stringContaining('empty') });
  });
});
```

- [ ] **Step 2: Run to verify they fail**

```powershell
npx vitest run packages/workflow-engine/tests/validate.test.ts
```

Expected: 4 FAILs (the valid-spec test passes since stub returns `[]`).

- [ ] **Step 3: Implement validate.ts**

Replace `packages/workflow-engine/src/validate.ts`:

```typescript
import type { ValidationError, WorkflowSpec } from './types';

export function validate(spec: WorkflowSpec): ValidationError[] {
  const errors: ValidationError[] = [];

  if (!spec.id || spec.id.trim() === '') {
    errors.push({ field: 'id', message: 'spec id must not be empty' });
  }

  if (!spec.steps || spec.steps.length === 0) {
    errors.push({ field: 'steps', message: 'steps must not be empty' });
    return errors;
  }

  const seenIds = new Set<string>();
  for (const step of spec.steps) {
    if (seenIds.has(step.id)) {
      errors.push({ step_id: step.id, field: 'id', message: `duplicate step id: ${step.id}` });
    }
    seenIds.add(step.id);

    if (!step.op || step.op.trim() === '') {
      errors.push({ step_id: step.id, field: 'op', message: 'step op must not be empty' });
    }
  }

  return errors;
}
```

- [ ] **Step 4: Run to verify all pass**

```powershell
npx vitest run packages/workflow-engine/tests/validate.test.ts
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```powershell
git add packages/workflow-engine/src/validate.ts packages/workflow-engine/tests/validate.test.ts
git commit -m "feat(workflow-engine): implement validate() — catches malformed workflow specs"
```

---

### Task 3: preview(spec) — returns ordered OperationRequests without side effects

**Files:**
- Modify: `packages/workflow-engine/src/preview.ts`
- Create: `packages/workflow-engine/tests/preview.test.ts`

- [ ] **Step 1: Write failing preview tests**

Create `packages/workflow-engine/tests/preview.test.ts`:

```typescript
import { describe, it, expect } from 'vitest';
import { preview } from '../src/preview';
import { SCHEMA_VERSION } from '../src/types';
import type { WorkflowSpec } from '../src/types';

const twoStepSpec: WorkflowSpec = {
  id: 'demo',
  trigger: { kind: 'manual' },
  steps: [
    { id: 's1', op: 'echo', args: { msg: 'hello' } },
    { id: 's2', op: 'llm.chat', args: { messages: [] } },
  ],
};

describe('preview', () => {
  it('returns one OperationRequest per step', () => {
    const reqs = preview(twoStepSpec);
    expect(reqs).toHaveLength(2);
  });

  it('each request has the correct op', () => {
    const reqs = preview(twoStepSpec);
    expect(reqs[0].op).toBe('echo');
    expect(reqs[1].op).toBe('llm.chat');
  });

  it('each request carries the step args', () => {
    const reqs = preview(twoStepSpec);
    expect(reqs[0].args).toEqual({ msg: 'hello' });
    expect(reqs[1].args).toEqual({ messages: [] });
  });

  it('each request has a non-empty request_id', () => {
    const reqs = preview(twoStepSpec);
    expect(reqs[0].request_id).toBeTruthy();
    expect(reqs[1].request_id).toBeTruthy();
    expect(reqs[0].request_id).not.toBe(reqs[1].request_id);
  });

  it('each request has the canonical schema_version', () => {
    const reqs = preview(twoStepSpec);
    for (const req of reqs) {
      expect(req.schema_version).toBe(SCHEMA_VERSION);
    }
  });

  it('each request has dry_run set to true', () => {
    const reqs = preview(twoStepSpec);
    for (const req of reqs) {
      expect(req.dry_run).toBe(true);
    }
  });

  it('returns empty array for spec with no steps', () => {
    const spec: WorkflowSpec = { id: 'empty', trigger: { kind: 'manual' }, steps: [] };
    expect(preview(spec)).toEqual([]);
  });
});
```

- [ ] **Step 2: Run to verify they fail**

```powershell
npx vitest run packages/workflow-engine/tests/preview.test.ts
```

Expected: multiple FAILs (stub returns `[]`).

- [ ] **Step 3: Implement preview.ts**

Replace `packages/workflow-engine/src/preview.ts`:

```typescript
import type { OperationRequest, WorkflowSpec } from './types';
import { SCHEMA_VERSION } from './types';

export function preview(spec: WorkflowSpec): OperationRequest[] {
  return spec.steps.map((step, idx): OperationRequest => ({
    schema_version: SCHEMA_VERSION,
    op: step.op,
    args: step.args,
    request_id: `preview-${spec.id}-${step.id}-${idx}`,
    origin: { kind: 'workflow', id: spec.id },
    privacy: 'local_only',
    dry_run: true,
  }));
}
```

- [ ] **Step 4: Run to verify all pass**

```powershell
npx vitest run packages/workflow-engine/tests/preview.test.ts
```

Expected: all PASS.

- [ ] **Step 5: Run full workflow-engine suite**

```powershell
npx vitest run packages/workflow-engine/tests/
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```powershell
git add packages/workflow-engine/src/preview.ts packages/workflow-engine/tests/preview.test.ts
git commit -m "feat(workflow-engine): implement preview() — returns dry-run OperationRequest sequence"
```

---

### Task 4: backend scaffold — FastAPI app, Pydantic models, /health

**Files:**
- Create: `apps/aether-desktop/backend/requirements.txt`
- Create: `apps/aether-desktop/backend/models.py`
- Create: `apps/aether-desktop/backend/main.py`
- Create: `apps/aether-desktop/backend/tests/__init__.py`
- Create: `apps/aether-desktop/backend/tests/conftest.py`
- Create: `apps/aether-desktop/backend/tests/test_op_endpoint.py`

- [ ] **Step 1: Write failing health test**

Create `apps/aether-desktop/backend/tests/__init__.py` (empty).

Create `apps/aether-desktop/backend/tests/test_op_endpoint.py`:

```python
from fastapi.testclient import TestClient


def test_health_returns_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
```

Create `apps/aether-desktop/backend/tests/conftest.py`:

```python
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    from apps.aether_desktop.backend.main import app
    return TestClient(app)
```

- [ ] **Step 2: Run to verify it fails**

Run from repo root with `PYTHONPATH=.`:

```powershell
$env:PYTHONPATH = "."; python -m pytest apps/aether-desktop/backend/tests/test_op_endpoint.py::test_health_returns_ok -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Create requirements.txt**

Create `apps/aether-desktop/backend/requirements.txt`:

```
fastapi>=0.115.0
uvicorn[standard]>=0.34.0
pydantic>=2.9.0
httpx>=0.28.0
```

Install:

```powershell
pip install fastapi uvicorn pydantic httpx
```

- [ ] **Step 4: Create the package init**

Create `apps/aether-desktop/__init__.py` (empty).

Create `apps/aether-desktop/backend/__init__.py` (empty).

- [ ] **Step 5: Create models.py**

Create `apps/aether-desktop/backend/models.py`:

```python
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


SCHEMA_VERSION = "scbe.operation.v1"

DecisionKind = Literal["ALLOW", "QUARANTINE", "ESCALATE", "DENY"]
ZoneKind = Literal["GREEN", "YELLOW", "RED"]


class OperationOrigin(BaseModel):
    kind: Literal["app", "workflow", "agent"]
    id: str


class OperationWorkspace(BaseModel):
    id: str
    root: str


class OperationRequest(BaseModel):
    schema_version: str = SCHEMA_VERSION
    op: str
    args: dict[str, Any] = Field(default_factory=dict)
    request_id: str
    origin: OperationOrigin
    workspace: OperationWorkspace | None = None
    privacy: Literal["local_only", "external_api"] = "local_only"
    budget_cents: float | None = None
    dry_run: bool = False


class OperationDecision(BaseModel):
    request_id: str
    decision: DecisionKind
    zone: ZoneKind
    reason: str
    policy: str
    latency_ms: float


class OperationError(BaseModel):
    code: str
    message: str


class ArtifactRef(BaseModel):
    kind: str
    ref: str


class OperationResult(BaseModel):
    request_id: str
    ok: bool
    output: dict[str, Any] | None = None
    error: OperationError | None = None
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    duration_ms: float = 0.0


class AuditResultSummary(BaseModel):
    ok: bool
    error_code: str | None = None
    artifact_refs: list[str] = Field(default_factory=list)
    output_shape: str | None = None


class AuditRecord(BaseModel):
    schema_version: str = SCHEMA_VERSION
    request_id: str
    ts_request: str
    op: str
    origin: OperationOrigin
    privacy: str
    decision: OperationDecision
    ts_result: str | None = None
    result_summary: AuditResultSummary | None = None
```

- [ ] **Step 6: Create main.py**

Create `apps/aether-desktop/backend/main.py`:

```python
from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="Aether Desktop Backend", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 7: Run test to verify it passes**

```powershell
$env:PYTHONPATH = "."; python -m pytest apps/aether-desktop/backend/tests/test_op_endpoint.py::test_health_returns_ok -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add apps/aether-desktop/
git commit -m "feat(aether-desktop): backend scaffold — FastAPI app, Pydantic models, /health"
```

---

### Task 5: governance gate — govern(req) → OperationDecision

**Files:**
- Create: `apps/aether-desktop/backend/gate.py`
- Create: `apps/aether-desktop/backend/tests/test_gate.py`

- [ ] **Step 1: Write failing gate tests**

Create `apps/aether-desktop/backend/tests/test_gate.py`:

```python
import pytest
from apps.aether_desktop.backend.gate import govern
from apps.aether_desktop.backend.models import OperationOrigin, OperationRequest, OperationWorkspace


def _req(op: str, workspace_root: str | None = None, dry_run: bool = False) -> OperationRequest:
    ws = OperationWorkspace(id="test", root=workspace_root) if workspace_root else None
    return OperationRequest(
        op=op,
        args={},
        request_id="test-req-001",
        origin=OperationOrigin(kind="app", id="test-app"),
        workspace=ws,
        privacy="local_only",
        dry_run=dry_run,
    )


def test_echo_op_is_allowed():
    decision = govern(_req("echo"))
    assert decision.decision == "ALLOW"
    assert decision.zone == "GREEN"


def test_llm_chat_is_allowed():
    decision = govern(_req("llm.chat"))
    assert decision.decision == "ALLOW"
    assert decision.zone == "GREEN"


def test_terminal_shell_raw_is_denied():
    decision = govern(_req("terminal.shell.raw"))
    assert decision.decision == "DENY"
    assert decision.zone == "RED"


def test_unknown_op_is_quarantined():
    decision = govern(_req("unknown.made.up.op"))
    assert decision.decision == "QUARANTINE"


def test_dry_run_echo_is_still_allowed():
    decision = govern(_req("echo", dry_run=True))
    assert decision.decision == "ALLOW"


def test_workspace_path_is_checked_when_provided(tmp_path):
    decision = govern(_req("fs.read", workspace_root=str(tmp_path)))
    assert decision.decision == "ALLOW"


def test_workspace_outside_cwd_is_probe_only(tmp_path):
    # path that exists but is not a real expected workspace
    outside = str(tmp_path / "some" / "outside" / "path")
    decision = govern(_req("fs.write", workspace_root=outside))
    # fs.write with unverified workspace → QUARANTINE or DENY
    assert decision.decision in ("QUARANTINE", "DENY")
```

- [ ] **Step 2: Run to verify they fail**

```powershell
$env:PYTHONPATH = "."; python -m pytest apps/aether-desktop/backend/tests/test_gate.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'apps.aether_desktop.backend.gate'`.

- [ ] **Step 3: Implement gate.py**

Create `apps/aether-desktop/backend/gate.py`:

```python
from __future__ import annotations

import time
from pathlib import Path

from .models import DecisionKind, OperationDecision, OperationRequest, ZoneKind

# Ops that are always blocked, regardless of context.
_DENY_OPS: frozenset[str] = frozenset(
    {"terminal.shell.raw", "os.exec", "fs.delete", "deploy.publish", "hardware.actuate"}
)

# Ops that are always allowed (read-only, local, non-destructive).
_ALLOW_OPS: frozenset[str] = frozenset(
    {"echo", "llm.chat", "metrics.read", "fs.read", "fs.list", "git.status", "time.read"}
)

# Ops with elevated risk — require workspace scoping.
_HIGH_RISK_OPS: frozenset[str] = frozenset(
    {"fs.write", "terminal.command.request", "browser.navigate", "web.search", "git.push"}
)


def govern(req: OperationRequest) -> OperationDecision:
    t0 = time.monotonic()

    decision, zone, reason, policy = _evaluate(req)

    return OperationDecision(
        request_id=req.request_id,
        decision=decision,
        zone=zone,
        reason=reason,
        policy=policy,
        latency_ms=(time.monotonic() - t0) * 1000,
    )


def _evaluate(req: OperationRequest) -> tuple[DecisionKind, ZoneKind, str, str]:
    op = req.op

    # 1. Hard deny list.
    if op in _DENY_OPS:
        return "DENY", "RED", f"op '{op}' is in the deny list", "deny-ops-list"

    # 2. Explicit allow list — no workspace checks needed.
    if op in _ALLOW_OPS:
        return "ALLOW", "GREEN", f"op '{op}' is in the allow list", "allow-ops-list"

    # 3. High-risk ops: require a workspace and verify it exists.
    if op in _HIGH_RISK_OPS:
        if req.workspace is None:
            return (
                "QUARANTINE",
                "YELLOW",
                f"op '{op}' requires a workspace but none was provided",
                "high-risk-requires-workspace",
            )
        ws_path = Path(req.workspace.root)
        if not ws_path.exists():
            return (
                "DENY",
                "RED",
                f"workspace path does not exist: {req.workspace.root}",
                "workspace-not-found",
            )
        return "ALLOW", "GREEN", f"op '{op}' allowed with valid workspace", "high-risk-workspace-ok"

    # 4. Unknown op — quarantine for review.
    return (
        "QUARANTINE",
        "YELLOW",
        f"op '{op}' is not in any known op set; quarantined pending review",
        "unknown-op",
    )
```

- [ ] **Step 4: Run gate tests**

```powershell
$env:PYTHONPATH = "."; python -m pytest apps/aether-desktop/backend/tests/test_gate.py -q
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```powershell
git add apps/aether-desktop/backend/gate.py apps/aether-desktop/backend/tests/test_gate.py
git commit -m "feat(aether-desktop): governance gate — govern() maps op to ALLOW/QUARANTINE/DENY"
```

---

### Task 6: audit writer — append-only rows, no secrets

**Files:**
- Create: `apps/aether-desktop/backend/audit.py`
- Create: `apps/aether-desktop/backend/tests/test_audit.py`

- [ ] **Step 1: Write failing audit tests**

Create `apps/aether-desktop/backend/tests/test_audit.py`:

```python
import json
from pathlib import Path

import pytest

from apps.aether_desktop.backend.audit import AuditWriter
from apps.aether_desktop.backend.models import (
    OperationDecision,
    OperationError,
    OperationOrigin,
    OperationRequest,
    OperationResult,
)


def _make_req() -> OperationRequest:
    return OperationRequest(
        op="echo",
        args={"msg": "hello"},
        request_id="audit-test-001",
        origin=OperationOrigin(kind="app", id="test"),
        privacy="local_only",
    )


def _make_decision(req: OperationRequest) -> OperationDecision:
    return OperationDecision(
        request_id=req.request_id,
        decision="ALLOW",
        zone="GREEN",
        reason="test",
        policy="test",
        latency_ms=0.5,
    )


def test_write_request_creates_file(tmp_path):
    writer = AuditWriter(audit_dir=tmp_path)
    req = _make_req()
    decision = _make_decision(req)
    writer.write_request(req, decision)
    log = tmp_path / "audit.jsonl"
    assert log.exists()
    rows = [json.loads(line) for line in log.read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["request_id"] == "audit-test-001"
    assert rows[0]["decision"]["decision"] == "ALLOW"


def test_complete_appends_result_row(tmp_path):
    writer = AuditWriter(audit_dir=tmp_path)
    req = _make_req()
    decision = _make_decision(req)
    writer.write_request(req, decision)
    result = OperationResult(request_id=req.request_id, ok=True, output={"echo": "hello"}, duration_ms=12.0)
    writer.complete(req.request_id, result)
    rows = [json.loads(line) for line in (tmp_path / "audit.jsonl").read_text().splitlines()]
    assert len(rows) == 2
    assert rows[1]["result_summary"]["ok"] is True


def test_audit_never_records_raw_secrets(tmp_path):
    writer = AuditWriter(audit_dir=tmp_path)
    req = OperationRequest(
        op="llm.chat",
        args={"messages": [{"role": "user", "content": "hello"}], "api_key": "sk-secret-value"},
        request_id="audit-secret-test",
        origin=OperationOrigin(kind="app", id="test"),
        privacy="local_only",
    )
    decision = _make_decision(req)
    writer.write_request(req, decision)
    content = (tmp_path / "audit.jsonl").read_text()
    assert "sk-secret-value" not in content


def test_audit_rows_are_append_only(tmp_path):
    writer = AuditWriter(audit_dir=tmp_path)
    for i in range(3):
        req = OperationRequest(
            op="echo",
            args={},
            request_id=f"req-{i}",
            origin=OperationOrigin(kind="app", id="test"),
            privacy="local_only",
        )
        writer.write_request(req, _make_decision(req))
    rows = (tmp_path / "audit.jsonl").read_text().splitlines()
    assert len(rows) == 3
```

- [ ] **Step 2: Run to verify they fail**

```powershell
$env:PYTHONPATH = "."; python -m pytest apps/aether-desktop/backend/tests/test_audit.py -q
```

Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement audit.py**

Create `apps/aether-desktop/backend/audit.py`:

```python
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import AuditRecord, AuditResultSummary, OperationDecision, OperationRequest, OperationResult

# Fields in args that should never appear verbatim in audit rows.
_REDACTED_KEYS: frozenset[str] = frozenset(
    {"api_key", "secret", "password", "token", "bearer", "credential"}
)


def _redact_args(args: dict) -> dict:
    return {k: "[REDACTED]" if k.lower() in _REDACTED_KEYS else v for k, v in args.items()}


class AuditWriter:
    def __init__(self, audit_dir: Path | None = None) -> None:
        if audit_dir is None:
            audit_dir = Path(".scbe")
        self._log_path = Path(audit_dir) / "audit.jsonl"
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    def write_request(self, req: OperationRequest, decision: OperationDecision) -> None:
        record = AuditRecord(
            request_id=req.request_id,
            ts_request=datetime.now(timezone.utc).isoformat(),
            op=req.op,
            origin=req.origin,
            privacy=req.privacy,
            decision=decision,
        )
        self._append(record.model_dump())

    def complete(self, request_id: str, result: OperationResult) -> None:
        summary = AuditResultSummary(
            ok=result.ok,
            error_code=result.error.code if result.error else None,
            artifact_refs=[a.ref for a in result.artifacts],
            output_shape=str(type(result.output).__name__) if result.output else None,
        )
        completion = {
            "schema_version": "scbe.operation.v1",
            "request_id": request_id,
            "ts_result": datetime.now(timezone.utc).isoformat(),
            "result_summary": summary.model_dump(),
        }
        self._append(completion)

    def _append(self, record: dict) -> None:
        with self._log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
```

- [ ] **Step 4: Run audit tests**

```powershell
$env:PYTHONPATH = "."; python -m pytest apps/aether-desktop/backend/tests/test_audit.py -q
```

Expected: all PASS.

- [ ] **Step 5: Commit**

```powershell
git add apps/aether-desktop/backend/audit.py apps/aether-desktop/backend/tests/test_audit.py
git commit -m "feat(aether-desktop): append-only audit writer with secret redaction"
```

---

### Task 7: operation registry + echo handler + /v1/op endpoint

**Files:**
- Create: `apps/aether-desktop/backend/registry.py`
- Create: `apps/aether-desktop/backend/handlers/__init__.py`
- Create: `apps/aether-desktop/backend/handlers/echo.py`
- Modify: `apps/aether-desktop/backend/main.py`
- Modify: `apps/aether-desktop/backend/tests/test_op_endpoint.py`

- [ ] **Step 1: Add failing /v1/op tests**

Append to `apps/aether-desktop/backend/tests/test_op_endpoint.py`:

```python
import json


def test_echo_op_returns_ok(client):
    payload = {
        "op": "echo",
        "args": {"msg": "hello world"},
        "request_id": "test-echo-001",
        "origin": {"kind": "app", "id": "test"},
        "privacy": "local_only",
    }
    resp = client.post("/v1/op", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["request_id"] == "test-echo-001"
    assert data["output"]["echo"] == "hello world"


def test_denied_op_returns_ok_false_without_calling_handler(client):
    payload = {
        "op": "terminal.shell.raw",
        "args": {"cmd": "rm -rf /"},
        "request_id": "test-deny-001",
        "origin": {"kind": "app", "id": "test"},
        "privacy": "local_only",
    }
    resp = client.post("/v1/op", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["error"]["code"] == "DENIED"


def test_unknown_op_returns_quarantined(client):
    payload = {
        "op": "magic.unicorn",
        "args": {},
        "request_id": "test-unknown-001",
        "origin": {"kind": "app", "id": "test"},
        "privacy": "local_only",
    }
    resp = client.post("/v1/op", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    # quarantined: gate decided QUARANTINE, not dispatched to handler
    assert data["ok"] is False
    assert data["error"]["code"] in ("QUARANTINE", "OP_NOT_FOUND")
```

- [ ] **Step 2: Run to verify they fail**

```powershell
$env:PYTHONPATH = "."; python -m pytest apps/aether-desktop/backend/tests/test_op_endpoint.py -q
```

Expected: 3 FAILs.

- [ ] **Step 3: Create registry.py**

Create `apps/aether-desktop/backend/registry.py`:

```python
from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Coroutine
from typing import Any

from .models import OperationError, OperationRequest, OperationResult

Handler = Callable[[OperationRequest], Coroutine[Any, Any, OperationResult]]


class OperationRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, Handler] = {}

    def register(self, op: str, handler: Handler) -> None:
        self._handlers[op] = handler

    async def dispatch(self, req: OperationRequest) -> OperationResult:
        handler = self._handlers.get(req.op)
        if handler is None:
            return OperationResult(
                request_id=req.request_id,
                ok=False,
                error=OperationError(code="OP_NOT_FOUND", message=f"No handler registered for op: {req.op}"),
            )
        t0 = time.monotonic()
        result = await handler(req)
        result = result.model_copy(update={"duration_ms": (time.monotonic() - t0) * 1000})
        return result
```

- [ ] **Step 4: Create handlers/echo.py**

Create `apps/aether-desktop/backend/handlers/__init__.py` (empty).

Create `apps/aether-desktop/backend/handlers/echo.py`:

```python
from __future__ import annotations

from ..models import OperationRequest, OperationResult


async def echo_handler(req: OperationRequest) -> OperationResult:
    return OperationResult(
        request_id=req.request_id,
        ok=True,
        output={"echo": req.args.get("msg", ""), "op": req.op, "args": req.args},
    )
```

- [ ] **Step 5: Wire up /v1/op in main.py**

Replace `apps/aether-desktop/backend/main.py`:

```python
from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI

from .audit import AuditWriter
from .gate import govern
from .handlers.echo import echo_handler
from .models import OperationError, OperationRequest, OperationResult
from .registry import OperationRegistry

app = FastAPI(title="Aether Desktop Backend", version="0.1.0")

# Registry — no handler is reachable except through /v1/op.
_registry = OperationRegistry()
_registry.register("echo", echo_handler)

# Audit writer — writes to .scbe/audit.jsonl relative to cwd.
_audit = AuditWriter()

# WS event queues keyed by request_id (populated in Task 8).
_event_queues: dict[str, asyncio.Queue] = {}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/op")
async def op_endpoint(req: OperationRequest) -> OperationResult:
    # 1. Govern — mandatory; gate is the only path.
    decision = govern(req)
    _audit.write_request(req, decision)

    if decision.decision in ("DENY", "QUARANTINE"):
        result = OperationResult(
            request_id=req.request_id,
            ok=False,
            error=OperationError(
                code=decision.decision,
                message=decision.reason,
            ),
        )
        _audit.complete(req.request_id, result)
        return result

    # 2. Dispatch through registry.
    result = await _registry.dispatch(req)
    _audit.complete(req.request_id, result)
    return result
```

- [ ] **Step 6: Run all backend tests**

```powershell
$env:PYTHONPATH = "."; python -m pytest apps/aether-desktop/backend/tests/ -q
```

Expected: all PASS.

- [ ] **Step 7: Commit**

```powershell
git add apps/aether-desktop/backend/
git commit -m "feat(aether-desktop): operation registry + echo handler + /v1/op chokepoint"
```

---

### Task 8: llm.chat handler + WS streaming at /v1/events

**Files:**
- Create: `apps/aether-desktop/backend/handlers/llm_chat.py`
- Modify: `apps/aether-desktop/backend/main.py`
- Modify: `apps/aether-desktop/backend/tests/test_op_endpoint.py`

- [ ] **Step 1: Add failing llm.chat tests**

Append to `apps/aether-desktop/backend/tests/test_op_endpoint.py`:

```python
import respx
import httpx


@respx.mock
def test_llm_chat_calls_ollama_and_returns_ok(client):
    # Mock Ollama streaming response.
    stream_lines = [
        b'{"model":"llama3","message":{"role":"assistant","content":"Hello"},"done":false}\n',
        b'{"model":"llama3","message":{"role":"assistant","content":" world"},"done":false}\n',
        b'{"model":"llama3","message":{"role":"assistant","content":""},"done":true}\n',
    ]
    respx.post("http://localhost:11434/api/chat").mock(
        return_value=httpx.Response(200, content=b"".join(stream_lines))
    )

    payload = {
        "op": "llm.chat",
        "args": {"messages": [{"role": "user", "content": "hi"}], "model": "llama3"},
        "request_id": "test-chat-001",
        "origin": {"kind": "app", "id": "chat-window"},
        "privacy": "local_only",
    }
    resp = client.post("/v1/op", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert "content" in data["output"]


@respx.mock
def test_llm_chat_returns_error_when_ollama_unavailable(client):
    respx.post("http://localhost:11434/api/chat").mock(
        side_effect=httpx.ConnectError("refused")
    )
    payload = {
        "op": "llm.chat",
        "args": {"messages": [{"role": "user", "content": "hi"}]},
        "request_id": "test-chat-002",
        "origin": {"kind": "app", "id": "chat-window"},
        "privacy": "local_only",
    }
    resp = client.post("/v1/op", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["error"]["code"] == "OLLAMA_UNAVAILABLE"
```

Install respx (Ollama mock library):

```powershell
pip install respx
```

- [ ] **Step 2: Run to verify they fail**

```powershell
$env:PYTHONPATH = "."; python -m pytest apps/aether-desktop/backend/tests/test_op_endpoint.py -k "llm_chat" -q
```

Expected: FAIL (no llm_chat handler registered).

- [ ] **Step 3: Create handlers/llm_chat.py**

Create `apps/aether-desktop/backend/handlers/llm_chat.py`:

```python
from __future__ import annotations

import asyncio
import json

import httpx

from ..models import OperationError, OperationRequest, OperationResult

OLLAMA_URL = "http://localhost:11434/api/chat"
DEFAULT_MODEL = "llama3"


async def llm_chat_handler(
    req: OperationRequest,
    event_queue: asyncio.Queue | None = None,
) -> OperationResult:
    messages = req.args.get("messages", [])
    model = req.args.get("model", DEFAULT_MODEL)
    content_parts: list[str] = []

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                OLLAMA_URL,
                json={"model": model, "messages": messages, "stream": True},
            ) as resp:
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        content_parts.append(token)
                        if event_queue is not None:
                            await event_queue.put(
                                {"type": "token", "request_id": req.request_id, "content": token}
                            )
    except httpx.ConnectError:
        return OperationResult(
            request_id=req.request_id,
            ok=False,
            error=OperationError(
                code="OLLAMA_UNAVAILABLE",
                message="Could not connect to Ollama at localhost:11434",
            ),
        )

    if event_queue is not None:
        await event_queue.put({"type": "done", "request_id": req.request_id})

    return OperationResult(
        request_id=req.request_id,
        ok=True,
        output={"content": "".join(content_parts)},
    )
```

- [ ] **Step 4: Register llm.chat and add WS endpoint in main.py**

Replace `apps/aether-desktop/backend/main.py`:

```python
from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI, WebSocket

from .audit import AuditWriter
from .gate import govern
from .handlers.echo import echo_handler
from .handlers.llm_chat import llm_chat_handler
from .models import OperationError, OperationRequest, OperationResult
from .registry import OperationRegistry

app = FastAPI(title="Aether Desktop Backend", version="0.1.0")

_registry = OperationRegistry()
_registry.register("echo", echo_handler)

_audit = AuditWriter()

# WS event queues keyed by request_id; populated before /v1/op is called.
_event_queues: dict[str, asyncio.Queue] = {}


async def _llm_chat_with_events(req: OperationRequest) -> OperationResult:
    queue = _event_queues.get(req.request_id)
    return await llm_chat_handler(req, event_queue=queue)


_registry.register("llm.chat", _llm_chat_with_events)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/op")
async def op_endpoint(req: OperationRequest) -> OperationResult:
    decision = govern(req)
    _audit.write_request(req, decision)

    if decision.decision in ("DENY", "QUARANTINE"):
        result = OperationResult(
            request_id=req.request_id,
            ok=False,
            error=OperationError(code=decision.decision, message=decision.reason),
        )
        _audit.complete(req.request_id, result)
        return result

    result = await _registry.dispatch(req)
    _audit.complete(req.request_id, result)
    return result


@app.websocket("/v1/events")
async def events_ws(websocket: WebSocket, request_id: str) -> None:
    await websocket.accept()
    queue: asyncio.Queue = asyncio.Queue()
    _event_queues[request_id] = queue
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=120.0)
            except asyncio.TimeoutError:
                break
            await websocket.send_json(event)
            if event.get("type") == "done":
                break
    finally:
        _event_queues.pop(request_id, None)
        await websocket.close()
```

- [ ] **Step 5: Run llm.chat tests**

```powershell
$env:PYTHONPATH = "."; python -m pytest apps/aether-desktop/backend/tests/test_op_endpoint.py -k "llm_chat" -q
```

Expected: PASS.

- [ ] **Step 6: Run full backend test suite**

```powershell
$env:PYTHONPATH = "."; python -m pytest apps/aether-desktop/backend/tests/ -q
```

Expected: all PASS.

- [ ] **Step 7: Commit**

```powershell
git add apps/aether-desktop/backend/handlers/llm_chat.py apps/aether-desktop/backend/main.py apps/aether-desktop/backend/tests/test_op_endpoint.py
git commit -m "feat(aether-desktop): llm.chat Ollama handler with WS event streaming"
```

---

### Task 9: minimal React shell — BackendClient + ChatWindow

**Files:**
- Create: `apps/aether-desktop/shell/package.json`
- Create: `apps/aether-desktop/shell/vite.config.ts`
- Create: `apps/aether-desktop/shell/src/main.tsx`
- Create: `apps/aether-desktop/shell/src/App.tsx`
- Create: `apps/aether-desktop/shell/src/BackendClient.ts`
- Create: `apps/aether-desktop/shell/src/windows/ChatWindow.tsx`
- Create: `apps/aether-desktop/shell/tests/BackendClient.test.ts`

- [ ] **Step 1: Create package.json**

Create `apps/aether-desktop/shell/package.json`:

```json
{
  "name": "@scbe/aether-desktop-shell",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "test": "vitest run"
  },
  "dependencies": {
    "@scbe/workflow-engine": "file:../../workflow-engine",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.0",
    "typescript": "^6.0.0",
    "vite": "^6.0.0",
    "vitest": "^4.0.17",
    "@vitest/globals": "^4.0.17",
    "jsdom": "^26.0.0"
  }
}
```

Install:

```powershell
cd apps/aether-desktop/shell && npm install && cd ../../..
```

- [ ] **Step 2: Create vite.config.ts**

Create `apps/aether-desktop/shell/vite.config.ts`:

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
  },
});
```

- [ ] **Step 3: Write failing BackendClient test**

Create `apps/aether-desktop/shell/tests/BackendClient.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createBackendClient } from '../src/BackendClient';
import { SCHEMA_VERSION } from '@scbe/workflow-engine';

describe('BackendClient', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
    vi.stubGlobal('WebSocket', vi.fn(() => ({ onmessage: null, close: vi.fn() })));
  });

  it('runOp POSTs to /v1/op with the correct body', async () => {
    const mockResult = { request_id: 'r1', ok: true, output: {}, duration_ms: 1 };
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValue({
      json: async () => mockResult,
    });

    const client = createBackendClient('http://localhost:8001');
    const result = await client.runOp({
      schema_version: SCHEMA_VERSION,
      op: 'echo',
      args: { msg: 'hi' },
      request_id: 'r1',
      origin: { kind: 'app', id: 'test' },
      privacy: 'local_only',
    });

    expect(global.fetch).toHaveBeenCalledWith(
      'http://localhost:8001/v1/op',
      expect.objectContaining({ method: 'POST' })
    );
    expect(result.ok).toBe(true);
  });

  it('subscribeEvents opens a WebSocket to /v1/events', () => {
    const client = createBackendClient('http://localhost:8001');
    const unsub = client.subscribeEvents('r2', () => {}, () => {});
    expect(global.WebSocket).toHaveBeenCalledWith(
      'ws://localhost:8001/v1/events?request_id=r2'
    );
    unsub();
  });
});
```

- [ ] **Step 4: Run to verify it fails**

```powershell
cd apps/aether-desktop/shell && npx vitest run tests/BackendClient.test.ts; cd ../../..
```

Expected: FAIL with `Cannot find module '../src/BackendClient'`.

- [ ] **Step 5: Create BackendClient.ts**

Create `apps/aether-desktop/shell/src/BackendClient.ts`:

```typescript
import type { OperationRequest, OperationResult } from '@scbe/workflow-engine';

export interface BackendClient {
  runOp(req: OperationRequest): Promise<OperationResult>;
  subscribeEvents(
    requestId: string,
    onEvent: (event: Record<string, unknown>) => void,
    onDone: () => void
  ): () => void;
}

export function createBackendClient(baseUrl: string): BackendClient {
  const wsBase = baseUrl.replace(/^http/, 'ws');

  return {
    async runOp(req: OperationRequest): Promise<OperationResult> {
      const resp = await fetch(`${baseUrl}/v1/op`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
      });
      return resp.json() as Promise<OperationResult>;
    },

    subscribeEvents(requestId, onEvent, onDone) {
      const ws = new WebSocket(`${wsBase}/v1/events?request_id=${requestId}`);
      ws.onmessage = (e: MessageEvent) => {
        const event = JSON.parse(e.data as string) as Record<string, unknown>;
        if (event['type'] === 'done') {
          onDone();
          ws.close();
        } else {
          onEvent(event);
        }
      };
      return () => ws.close();
    },
  };
}
```

- [ ] **Step 6: Run BackendClient test**

```powershell
cd apps/aether-desktop/shell && npx vitest run tests/BackendClient.test.ts; cd ../../..
```

Expected: PASS.

- [ ] **Step 7: Create ChatWindow.tsx**

Create `apps/aether-desktop/shell/src/windows/ChatWindow.tsx`:

```tsx
import { useCallback, useRef, useState } from 'react';
import { createBackendClient } from '../BackendClient';
import { SCHEMA_VERSION } from '@scbe/workflow-engine';
import type { OperationRequest } from '@scbe/workflow-engine';

const client = createBackendClient(
  (import.meta as Record<string, Record<string, string>>).env?.['VITE_BACKEND_URL'] ?? 'http://localhost:8001'
);

export function ChatWindow() {
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState('');
  const streamRef = useRef('');
  const unsubRef = useRef<(() => void) | null>(null);

  const send = useCallback(async () => {
    const text = input.trim();
    if (!text) return;

    const userMsg = { role: 'user', content: text };
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setInput('');
    streamRef.current = '';
    setStreaming('');

    const requestId = crypto.randomUUID();
    const req: OperationRequest = {
      schema_version: SCHEMA_VERSION,
      op: 'llm.chat',
      args: { messages: nextMessages, model: 'llama3' },
      request_id: requestId,
      origin: { kind: 'app', id: 'chat-window' },
      privacy: 'local_only',
    };

    unsubRef.current = client.subscribeEvents(
      requestId,
      (e) => {
        if (e['type'] === 'token' && typeof e['content'] === 'string') {
          streamRef.current += e['content'];
          setStreaming(streamRef.current);
        }
      },
      () => {
        setMessages((prev) => [...prev, { role: 'assistant', content: streamRef.current }]);
        streamRef.current = '';
        setStreaming('');
        unsubRef.current = null;
      }
    );

    await client.runOp(req);
  }, [input, messages]);

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', padding: 8, fontFamily: 'monospace' }}>
      <div style={{ flex: 1, overflowY: 'auto', marginBottom: 8 }}>
        {messages.map((m, i) => (
          <div key={i} style={{ marginBottom: 4 }}>
            <strong>{m.role}:</strong> {m.content}
          </div>
        ))}
        {streaming && (
          <div style={{ marginBottom: 4 }}>
            <strong>assistant:</strong> {streaming}
          </div>
        )}
      </div>
      <div style={{ display: 'flex', gap: 8 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') void send(); }}
          style={{ flex: 1, padding: '4px 8px' }}
          placeholder="Type a message and press Enter..."
        />
        <button onClick={() => void send()} style={{ padding: '4px 12px' }}>
          Send
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 8: Create App.tsx and main.tsx**

Create `apps/aether-desktop/shell/src/App.tsx`:

```tsx
import { ChatWindow } from './windows/ChatWindow';

export function App() {
  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column' }}>
      <header style={{ padding: '8px 16px', borderBottom: '1px solid #ccc', fontFamily: 'monospace' }}>
        Aether Desktop — Phase 0
      </header>
      <main style={{ flex: 1, overflow: 'hidden' }}>
        <ChatWindow />
      </main>
    </div>
  );
}
```

Create `apps/aether-desktop/shell/src/main.tsx`:

```tsx
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';

const root = document.getElementById('root');
if (!root) throw new Error('Root element not found');
createRoot(root).render(<StrictMode><App /></StrictMode>);
```

Create `apps/aether-desktop/shell/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Aether Desktop</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 9: Create tsconfig.json for shell**

Create `apps/aether-desktop/shell/tsconfig.json`:

```json
{
  "extends": "../../../tsconfig.base.json",
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "lib": ["ES2022", "DOM"],
    "outDir": "../../../dist/apps/aether-desktop/shell",
    "composite": true,
    "declaration": true,
    "declarationMap": true
  },
  "include": ["src/**/*", "tests/**/*"]
}
```

- [ ] **Step 10: Run shell tests**

```powershell
cd apps/aether-desktop/shell && npx vitest run; cd ../../..
```

Expected: PASS.

- [ ] **Step 11: Commit**

```powershell
git add apps/aether-desktop/shell/
git commit -m "feat(aether-desktop): minimal React shell — BackendClient + ChatWindow (no eval, no dangerouslySetInnerHTML)"
```

---

### Task 10: Vertical slice verification

- [ ] **Step 1: Run all workflow-engine tests**

```powershell
npx vitest run packages/workflow-engine/tests/
```

Expected: all PASS (types, validate, preview).

- [ ] **Step 2: Run all backend tests**

```powershell
$env:PYTHONPATH = "."; python -m pytest apps/aether-desktop/backend/tests/ -v
```

Expected: all PASS (health, gate, audit, op-endpoint × 5 + llm_chat × 2).

- [ ] **Step 3: Run shell tests**

```powershell
cd apps/aether-desktop/shell && npx vitest run; cd ../../..
```

Expected: PASS (BackendClient × 2).

- [ ] **Step 4: Confirm package is isolated from SCBE governance**

```powershell
Select-String -Recurse -Path apps/aether-desktop/backend -Pattern "geoseal_legitimacy|agentbus|harmonic|liboqs" -SimpleMatch
```

Expected: no matches. The gate is a standalone local policy; full GeoSeal integration is a future slice.

- [ ] **Step 5: Start backend and confirm /health**

```powershell
$env:PYTHONPATH = "."; python -m uvicorn apps.aether_desktop.backend.main:app --host 127.0.0.1 --port 8001
```

In another terminal:

```powershell
Invoke-RestMethod http://localhost:8001/health
```

Expected: `status ok`.

- [ ] **Step 6: Manual chat round-trip (requires Ollama running)**

Verify Ollama is running:

```powershell
Invoke-RestMethod http://localhost:11434/api/tags
```

Start the shell dev server:

```powershell
cd apps/aether-desktop/shell && npx vite; cd ../../..
```

Open `http://localhost:5173`, type a message, press Enter. Expected: tokens stream into the window; an audit row exists at `.scbe/audit.jsonl`.

- [ ] **Step 7: Final commit if any verification fixes were needed**

Only if files changed:

```powershell
git add apps/aether-desktop/ packages/workflow-engine/
git commit -m "fix(aether-desktop): stabilize vertical slice verification"
```

---

## Self-Review

**Spec coverage:**

| Spec requirement | Task |
|---|---|
| No UI component ever touches a real capability directly | Task 9: only BackendClient.runOp reaches /v1/op |
| The gate wraps every operation | Tasks 5 + 7: govern() is the only path in op_endpoint |
| Audit before AND after | Tasks 6 + 7: write_request before handler, complete after |
| OperationRequest/Decision/Result/AuditRecord contract | Task 1 |
| dry_run flag supported | Types carry it; gate/handler respect it in later slices |
| validate + preview (workflow spec tools) | Tasks 2 + 3 |
| llm.chat → gated → provider → streamed WS | Tasks 8 + 9 |
| Minimal shell with BackendClient as only fetch path | Task 9 |
| /health endpoint | Task 4 |
| Phase 2 workflow builder | Intentionally excluded |
| browser.navigate slice | Intentionally deferred (second slice) |

**Placeholder scan:** No TBD/TODO/fill-in phrases. Every step has exact commands or exact code.

**Type consistency:** `OperationRequest.request_id` (string) is consistent across types.ts, models.py, BackendClient.ts, and all tests. `OperationResult.ok` (bool) is consistent. `decision.decision` (DecisionKind / Literal string) matches between gate.py, models.py, and op_endpoint tests.
