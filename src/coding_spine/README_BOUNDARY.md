# boundary marker — this directory is the IR role

`src/coding_spine/` is the Six-Tongues **typed routing IR** (`SemanticIR`,
`RouteIR`, `route_task`) — the representation an orchestrator type-checks to
decide *which lane / how dangerous* a task is. It is **not** the byte tokenizer.

- Routing / typing **IR** role → here, `src/cli/cross_build_ir.py`
- Encoding / tokenizer role → `src/tokenizer/`, `src/crypto/sacred_tongues.py`, `packages/sixtongues/`

Also note: "escalate" in the router is the **capability** axis (which model), not
the gate's **authority** ESCALATE verdict. Full rules: **`docs/BOUNDARIES.md` §1–2**.
