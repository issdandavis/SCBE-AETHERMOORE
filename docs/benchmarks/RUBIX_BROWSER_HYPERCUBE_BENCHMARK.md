# Rubix Browser Hypercube Benchmark

Status: local browser-control geometry fixture, not a WebArena, VisualWebArena,
BrowserGym, or OSWorld score.

The idea: AI agents do not need a human-first flat browser as their primary
control surface. They need a permission-defined action manifold.

Instead of treating every DOM element as another clickable object, the agent
rotates through system-defined faces:

- `READ`
- `NAV`
- `FORM`
- `FILE_APPROVAL`
- `AUTH`
- `PREVIEW`
- `SANITIZE`
- `SUBMIT`
- denied faces such as `PAYMENT`, `DELETE`, `SECRET`, `COOKIE`

Because the dimensions are defined by the system and not by natural 3D law, the
browser can be a tesseract/Rubix formation with as many faces as the permission
model requires.

## Command

```bash
python scripts/benchmark/rubix_browser_hypercube_benchmark.py
```

Artifacts:

- `artifacts/benchmarks/rubix_browser_hypercube/latest_report.json`
- `artifacts/benchmarks/rubix_browser_hypercube/LATEST.md`

## Latest Expected Result

```text
decision=PASS
baseline=0/3
hypercube=3/3
```

The flat DOM greedy baseline follows tempting trap routes through denied faces.
The permission hypercube lane completes all tasks while emitting rotations,
permission checks, approvals, denial counts, and receipt hashes.

## Proof / Goal Split

- Proof layer: face rotations, permission checks, approvals, denied-face counts,
  route receipts, and hashes.
- Goal layer: real browser automation through a permission-defined action
  manifold.
- Boundary: this proves the routing abstraction on fixtures, not public browser
  benchmark performance.

## Public Benchmark Targets

Useful external targets to map this idea onto:

- WebArena: realistic web tasks over self-hosted websites:
  https://webarena.dev/
- VisualWebArena: web tasks requiring visual grounding:
  https://arxiv.org/abs/2401.13649
- BrowserGym: browser-agent environment and benchmark wrapper:
  https://github.com/ServiceNow/BrowserGym
- OSWorld: desktop/browser operation tasks across real applications:
  https://os-world.github.io/

## Related Design References

- Tesseract / 4D puzzle games show the interface precedent: a
  higher-dimensional state can be made operable through projected rotations, not
  by pretending the user or agent is limited to a flat 2D board.
- Dwarf Fortress shows the simulation precedent: many local agents can route
  through jobs, terrain, permissions, needs, hazards, and consequences without a
  single global "click the obvious thing" surface.
- ASI:One-style CLI tools show the market precedent: a model can be exposed
  through direct command-line/API calls without a dashboard-first product. The
  SCBE-specific difference to prove is governed execution: receipts, permission
  faces, route reversibility, benchmark envelopes, and recoverable drift.

The local path should be:

1. Keep this fixture as the geometry/control proof.
2. Add a Playwright-backed local page fixture.
3. Convert the same face-route receipts into a BrowserGym/WebArena adapter.
4. Only then report public benchmark scores.

## Patent Provenance Boundary

This is implementation evidence only. It should be treated as support material
for geometric governance and audit-receipt concepts, not as a legal conclusion.

Linked local references:

- `docs/PATENT_DETAILED_DESCRIPTION.md`
- `docs/specs/EVALUATION_CONTRACT_v1.md`

External research/context references:

- https://4d.pardesco.com/shapes/tesseract
- https://superliminal.com/cube/
- https://www.dwarffortresswiki.org/index.php/DF2014%3APath
- https://docs.asi1.ai/docs
- https://pypi.org/project/asi1-mcp-cli/
