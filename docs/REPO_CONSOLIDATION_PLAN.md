# Repo & Surface Consolidation Plan

**Goal:** collapse a ~100-repo GitHub galaxy into one legible product surface a skeptical buyer can trust in 30 seconds. The sprawl itself is the trust problem — two dozen 0-star, half-overlapping repos by one person read as bus-factor-1, not a product line.

**Status:** planning doc. Every GitHub-side action (archive / make-private / delete / redirect) is outward and left for the owner to execute. Nothing here is destructive on its own. Not for `main` (planning artifact).

_Snapshot taken 2026-06-09 from `gh repo list issdandavis`._

---

## 1. The canonical surface (keep + polish — this is "the product")

| Surface | Repo | Action |
|---|---|---|
| Code | `SCBE-AETHERMOORE` (monorepo) | Canonical. Honest README pass done. Pin #1. |
| CLI / package | published `scbe-aethermoore` + `scbe-aethermoore-cli` | One npm + one PyPI story. Bump version, fix `geoseal` bin collision. |
| Site | **pick ONE** of `aethermoore.com` (monorepo `docs/`) or `aethermoorgames.com` (`issdandavis.github.io`) | Two live domains for one product is a confusion tax. Choose one, 301 the other. |
| Profile | `issdandavis` (profile README) | One honest line: "Local-first AI governance gate — ALLOW/QUARANTINE/ESCALATE/DENY + audit receipt." |

**Pin exactly 6** on the profile: monorepo, CLI, site, `phdm-21d-embedding` (has a star), `six-tongues-geoseal`, and one demo. Everything else should not compete for first-impression attention.

---

## 2. Two-domain decision (do this first — it's free and high-impact)

- `aethermoore.com` and `aethermoorgames.com` currently both present the product.
- **Recommend:** keep `aethermoore.com` as the product/trust domain (cleaner for a security buyer); send `aethermoorgames.com` to it or scope it to the game/lore only.
- Fix every hard-coded canonical URL to the single chosen domain (they're currently split across `docs/`).

---

## 3. Identity unification (table stakes — the report flagged it)

- GitHub / npm / email are consistent: **issdandavis / Issac Daniel Davis**. Good.
- Drift to fix: **Ko-fi handle is `izdandavis`** (~20 links). Either rename the Ko-fi page to match, or accept it but never present it as a different person.
- Remove the archived `archive/demos/scbe_demo.py:8` line "Author: Isaac Davis / SpiralVerse OS." No third persona on a trust product.
- (No "Isaac Thorne" string found in this repo — that leak appears already cleaned here; check the separate `scbe-aethermoore-demo` repo.)

---

## 4. Satellite triage (the ~25 SCBE-owned public repos)

Default bias: **fewer surfaces = more trust.** Each row is KEEP / FOLD / ARCHIVE / PRIVATE.

| Repo | State now | Recommendation | Why |
|---|---|---|---|
| `scbe-experiments` | archived public | **KEEP, add honest banner** | Holds the contradicting benchmark data — that's honesty, not shame. Banner: "superseded by monorepo `experiments/`; results show simpler baselines win — by design we publish this." |
| `scbe-docs-archive` | archived public | PRIVATE | 277-file doc dump dilutes; no buyer value. |
| `scbe-tongues-toolchain` | archived public | KEEP or FOLD | Real toolchain; fold into monorepo `packages/` or keep as a clean single-purpose repo. |
| `scbe-training-lab` | archived public | PRIVATE | Training data/configs — not a product face. |
| `scbe-agents` | archived public | FOLD | Overlaps HYDRA in monorepo. |
| `hyperbolica` | public | PRIVATE or FOLD | "Hyperbolic geometry primitives" — now a research claim we're de-emphasizing. |
| `cyber-suite` | private | LEAVE | Already private; `H(d,R)=R^(d²)` is the un-shipped research formula. |
| `six-tongues-geoseal` | public, 1★ | KEEP | Clean, single-purpose, crypto toolkit. Pin candidate. |
| `scbe-nodal-network` | public | PRIVATE or FOLD | Niche; dilutes. |
| `phdm-21d-embedding` | public, 1★ | KEEP | Has external interest; standalone model. Pin candidate. |
| `scbe-aethermoore-demo` | public, 1★ | KEEP, audit | Front-line demo — re-check for the "Isaac Thorne" / stat-counter issues the report cited. |
| `aetherbrowser` | public | KEEP or FOLD | Real product direction; decide if standalone or monorepo module. |
| `aethercivil` | public | PRIVATE | Civic MVP, off the core story. |
| `ai-core` | public | PRIVATE | Nix infra; not a buyer face. |
| `spiralverse-chronicles` | public | KEEP (lore-scoped) | The lore home — good, *if* it's clearly the lore lane, not mixed into product. |
| `aethromoor-novel` | public | KEEP (lore-scoped) | Same; quarantine narrative away from product surfaces. |
| `Entropicdefenseengineproposal` | public | PRIVATE | DARPA proposal; not public-buyer material. |
| `scbe-research` | private | LEAVE | Correct home for research scripts. |

**Quarantine the lore** (per the external report): the novel, game, Spiralverse, Sacred-Tongues mythology stay in clearly-labeled lore repos and a `/story` site section — never the product first screen.

---

## 5. The fork pile (~50 forks)

`transformers`, `ollama`, `n8n`, `telegram`, `obs-studio`, `openclaw`, `DeepGEMM`, etc. — these clutter the profile and add zero product signal.

- **Recommend:** delete forks you're not actively patching. Keeping a fork is only justified if you have un-merged local changes you depend on.
- At minimum, none should be pinned, and the profile should read as a focused builder, not a fork hoarder.

---

## 6. Sequenced execution (cheapest-first)

1. **This hour:** pick the one domain; set the 6 pins; rewrite the profile README one-liner. (Free, pure signal.)
2. **This day:** PRIVATE/ARCHIVE the dilution repos in §4; add the honest banner to `scbe-experiments`; fix the Ko-fi identity + the archived author line.
3. **This week:** fold the genuine-overlap repos (`scbe-agents`, maybe `hyperbolica`, `scbe-nodal-network`) into the monorepo; delete dead forks.
4. **Then:** the next real milestone is the embedding + NeMo/Guardrails benchmark (`experiments/honest_injection_benchmark.py` is the harness) — the number that earns a price.

---

## 7. Done-state test

A stranger Googling "SCBE" lands on: one repo, one site, one package, one honest benchmark, one name. Not a nebula. That is the whole point.
