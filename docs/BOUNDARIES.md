# BOUNDARIES — the things that look like one thing but are two

Single source of truth for concepts in this repo that share a name or a
neighbourhood and get conflated. When two ideas wear one word, code quietly
routes the wrong one and a guarantee evaporates. Each entry below names the two
sides, says where each lives, and gives the **keep-apart rule**. In-place files
point here; this file does not point back out (so it can't drift).

Last updated: 2026-06-10.

---

## 1. Six-Tongues **IR** vs Six-Tongues **Tokenizer**  — risk: HIGH

The "Six Tongues" (KO/AV/RU/CA/UM/DR) play **two unrelated roles**. They are not
the same object and must never share a code path.

| | **IR** (routing / typing) | **Tokenizer** (encoding / crypto) |
|---|---|---|
| What it is | a typed intermediate representation an orchestrator **type-checks before dispatch** — the tongue is an *effect/authority family* | a **bijective byte↔token alphabet** (16 prefixes × 16 suffixes = 256 tokens/tongue) used for cryptographic binding and human-readable encoding |
| Job | decide *which lane / how dangerous* a task is, then route | turn bytes into pronounceable tokens and back, losslessly |
| Lives in | `src/coding_spine/shared_ir.py` (`SemanticIR`, `RouteIR`), `src/coding_spine/router.py` (`route_task`), `src/cli/cross_build_ir.py` (`LatticeOp`) | `src/crypto/sacred_tongues.py` (`SacredTongueTokenizer`), `packages/sixtongues/`, `src/tokenizer/` (`ss1.ts`, patent claims 26–28) |
| Patent | routing/effect side | bijective vocabulary (Claims 26, 28) |

**Why they're distinct (the load-bearing reason):** the IR is the *enforceable*
boundary — you type-check it to forbid I/O or secrets statically. The tokenizer
is an *encoding* — it has no authority semantics at all. You can only retokenize
a model **you train yourself**; you cannot retokenize Claude/Grok, so for models
you *orchestrate*, the Tongues are an IR, never a tokenizer. Conflating them is
exactly where the static guarantee silently disappears.

**Keep-apart rule:** byte↔token code imports from `src/crypto/sacred_tongues.py`
or `packages/sixtongues/`; routing/typing code imports from
`src/coding_spine/`. A module that needs both (e.g. `src/geoseal_cli.py`) keeps
the **encode stage** and the **route/type stage** in separate, labelled blocks.

**Collision point to watch:** `src/geoseal_cli.py` — uses the tokenizer (to
encode payloads) *and* the router (to route the task) in one command. The
docstring there marks the two stages.

> Note: `src/harmonic/atomic_tokenizer.py` is **neither** of these — it maps
> natural-language surface forms to a 10-atom intent vocabulary for tongue
> selection. It is a *semantic-atom classifier*, not a byte tokenizer. (Rename
> deferred — it is imported under its current name; do not break it casually.)

---

## 2. **Authority** axis vs **Capability** axis  — risk: MEDIUM

Two different questions about a task, and the word **"escalate"** is overloaded
across them. They are orthogonal: a task can be high-authority/easy (one `sign`
call) or low-authority/hard (a brutal pure proof).

| | **Authority** (how *dangerous*) | **Capability** (how *hard*) |
|---|---|---|
| Measures | how much ambient authority / blast radius an action carries | how much model horsepower solving it needs |
| Scale | effect/tongue lattice: `⊥(CA, DR_pure) < {KO, RU} < AV < UM` | model ladder: `small (ollama) → mid (hf) → big (claude)` |
| Decision | gate verdict **ALLOW / QUARANTINE / ESCALATE / DENY** | which model **rung** to try next |
| "escalate" means | tighten policy because danger rose | try a *smarter model* because the last one failed |
| Lives in | `src/governance/runtime_gate.py`, `src/governance/negative_tongue_lattice.py`, `src/crypto/geoseal_execution_gate.py` | `scripts/tools/mason.py` (`MODEL_LADDER`, `escalate_to`), `src/cli/slm_router.py` |

**Keep-apart rule:** "escalate" in `runtime_gate.py` / gate code = **authority**
(a danger verdict). "escalate" in `mason.py` / model-router code = **capability**
(a bigger model). Routing reads **both** axes: `height(E)` picks the gate lane;
difficulty picks the model rung. Never let one stand in for the other.

> The mason's `escalate_to` key keeps its name (it is under test in
> `tests/test_mason.py` and `scripts/eval/mason_model_benchmark.py`). It means
> *capability escalation*; the label is here, not a rename.

---

## 3. Dual `symphonic_cipher/`  — risk: LOW (already disambiguated)

Two packages, **different math**, same name — already handled, recorded here for
completeness. Disambiguated at runtime by variant tags; see also the "Critical
Gotcha" section of `CLAUDE.md`.

| | root `symphonic_cipher/` | `src/symphonic_cipher/` |
|---|---|---|
| Formula | `H(d,R) = R^(d²)` — exponential cost multiplier | `H(d,pd) = 1/(1+d+2·pd)` — bounded safety score in (0,1] |
| Detect at runtime | `_VARIANT == "root"` | `_VARIANT == "src"`, `_IS_SAFETY_SCORE == True` |

**Keep-apart rule:** new tests state which they need explicitly;
`tests/conftest.py` adds the project root to `sys.path`. Check `_VARIANT` /
`_IS_SAFETY_SCORE` when import resolution is ambiguous.

---

## How to extend this file

When you find a third thing wearing a second thing's name: add a row, name both
sides, give the keep-apart rule, and drop a one-line pointer (`# boundary: see
docs/BOUNDARIES.md §N`) at the collision site — not a copy of the explanation.
