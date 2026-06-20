# SCBE Asset Value Assessment

Generated: 2026-05-31

## Scope And Evidence Sources

This catalog separates working product surfaces from proofs, research, private/IP material, content assets, and miscellaneous backlog.

Evidence used:

- local repo inventory from `package.json`, `packages/*/package.json`, `scripts/benchmark/*`, `docs/specs/*`, and current git branch;
- GitHub connector PR history through PR #2012;
- Google Drive connector root listing for private proof/proposal/supporting assets;
- current web research on agent CLIs, MCP, public agent benchmarks, and computational chemistry tools;
- local benchmark run: `python scripts/benchmark/scbe_full_system_benchmark.py --json`.

Current branch note:

- local branch: `feat/runtime-gate-durable-state`
- branch has chemistry/reaction-packet/evidence commits not on `origin/main` yet;
- `origin/main` has Polly Pad CLI, Polly Python package, and several agent-bus station/search/router features that are not merged into this branch;
- any public website/package claim must say whether it is on the feature branch, on `origin/main`, or published to a registry.

Semrush note:

- Semrush MCP traffic analytics is unavailable on the current Semrush plan, so no SEO/traffic numbers are included here.

## Executive Assessment

SCBE has several assets with real commercial value, but they are at different maturity levels.

The strongest current product wedge is not "AI governance" by itself. The valuable shape is:

> A durable terminal operating layer for AI work: commands, workspaces, receipts, benchmarks, tool routing, cross-language packets, chemistry/reaction packets, and private proof trails.

The highest-value split is:

1. **Polly / SCBE CLI Workpad** - user-facing utility surface.
2. **Agent Bus / Workspace Chain** - developer/operator infrastructure.
3. **Longform Bridge / Provenance Ledger** - IP and enterprise trust layer.
4. **Benchmark Evidence Hub** - proof and marketing layer.
5. **Chemistry + Reaction-State Packets** - differentiated research/product lane.
6. **STISTA / Sacred Tongues / GeoSeed** - internal conceptual engine and tokenizer layer.
7. **Private Proof / Patent / Proposal Assets** - internal licensing and moat material.
8. **AetherMoore / Everweave / Lore / Game/Web Assets** - content and brand expansion.
9. **Misc / Research / Content Backlog** - valuable but not yet product-shaped.

## Product-Ready Or Near-Product Assets

| Asset | Current Evidence | Value | Readiness | Next Action |
| --- | --- | --- | --- | --- |
| `scbe-aethermoore-cli` | `packages/cli/package.json` on this branch; `origin/main` package changelog says npm `4.4.0` aligned but new code pending publish. | General operator CLI; strongest public entrypoint. | Medium-high. | Reconcile branch with `origin/main`, fix bench JSON regression, publish next CLI release. |
| Polly Pad CLI | On `origin/main`: `packages/polly-pad-cli`, npm package name `scbe-polly-pad-cli@0.1.0`, PRs #1993-#2008. | Most understandable user product: terminal IDE/workpad for AI/human operators. | High on main, missing in current branch. | Merge/rebase into current branch; first npm publish after pack/test. |
| Polly Pad Python | On `origin/main`: `packages/polly-pad-py`, PyPI name `scbe-polly-pad@0.1.0`. | Python install path and automation wrapper. | Medium. | Verify wheel/sdist, publish only after CLI package is stable. |
| `scbe-agent-bus` | Published npm `0.4.1`; main has post-publish station, workflow, search, and routing work. | Backend infrastructure for governed multi-agent tools/workspaces. | High for developer infrastructure. | Bump and publish `0.5.0` after branch reconciliation and package-local tests. |
| Core `scbe-aethermoore` package | Root package version `4.2.0` on branch; package changelog says main `4.2.1` is pending publish. | Library/IP carrier for harmonic, crypto, tokenizer, governance, and benchmarks. | Medium-high. | Publish drift cleanup after main/branch merge. |
| Workspace audit commands | Agent-bus changelog: workspace new/ingest/export/import/verify/lineage/report. | Enterprise-grade chain-of-custody surface. | High. | Make this part of public CLI onboarding and docs. |
| Free-first model routing | PRs #2004-#2005 and Polly docs; routing through Ollama/Cerebras/Groq/HF/fallback depending environment. | Practical cost edge for end users. | Medium. | Add provider doctor command and quota/credential status card. |

## Proof And Benchmark Assets

| Asset | Evidence | Value | Readiness | Claim Boundary |
| --- | --- | --- | --- | --- |
| Full evidence matrix | Latest local run: 14/14 artifacts, 10 pass, 2 partial. | Gives a real report-card spine. | High. | Local evidence matrix, not a public leaderboard aggregate. |
| Longform chain integrity | `longform-chain-integrity` PASS `105/105`. | Strong proof surface for durable memory/provenance. | High. | Custom SCBE benchmark. |
| Longform CLI | `longform-cli` PASS. | Demonstrates user-facing durable workflows. | Medium-high. | Local CLI fixture, not autonomous task guarantee. |
| Chemistry capability | `chemistry-cli-capability` PASS. | Differentiator; few AI CLIs have chemistry-native evidence. | Medium. | Symbolic/computational only, not wet lab. |
| Compound decomposition/recomposition | `compound-decompose` PASS `3/3`, RDKit enabled. | Strong product benchmark: atom bag ambiguity + descriptor recovery. | Medium-high. | Computational identity/recomposition benchmark only. |
| Reaction-state packet | Commit `cf1982373`, tests `7 passed`. | Unifying object across code, chemistry, tokenizer routing, and audit. | Medium-high. | Schema and local harness; needs public CLI command next. |
| BFCL adapter | Local BFCL-compatible lane; latest list marks claim-safe boundary. | Tool-calling benchmark bridge. | Medium. | Not official BFCL leaderboard. |
| tau-bench policy microbench | Local hand-authored SCBE governance fixtures. | Good for policy routing, less strong for broad agent value. | Medium. | Not official tau-bench leaderboard. |
| Rubix browser | Local browser permission-hypercube fixture. | Differentiated UI/browser-control research lane. | Medium. | Not WebArena/OSWorld score. |
| Terminal adapter | Local answer-file contract. | Good stepping stone to Terminal-Bench. | Medium. | Not official Terminal-Bench. |
| NeuroGolf / ARC-style grid | `neurogolf-blind-submission` partial `398/400`; ARC-style partial `0.8`. | Strong research/test lane. | Medium. | Local/fixture score unless submitted officially. |

## Chemistry / Scientific Research Assets

| Asset | Evidence | Value | Readiness | Next Action |
| --- | --- | --- | --- | --- |
| RDKit-backed compound lane | `scripts/benchmark/compound_decomposition_recomposition.py`; PASS `3/3`. | Real computational chemistry substrate. | Medium-high. | Expand corpus to 25-100 formula-isomer cases. |
| Reaction-state schema | `python/scbe/reaction_state.py`; docs/specs model. | Turns chemistry/code/tokenizer transforms into one packet object. | Medium-high. | Add `scbe react chem/code/audit/compare`. |
| STISTA / atomic tokenizer | `python/scbe/atomic_tokenization.py`, `chemical_fusion.py`, memory points to `src/tokenizer/ss1.ts`. | Distinct internal theory-to-code layer. | Medium. | Keep as internal engine until packet outputs are repeatable. |
| GeoSeed orbital/transfer | Main PRs #2006/#2007 and branch geoseed commits. | Useful visualization/analogy and transfer-matrix research layer. | Medium-low for product; medium for IP narrative. | Keep claim boundaries; use as visual/explanatory support. |
| Chemistry toolchain skill | Local Codex skill `scbe-chem-research-loop`; detector shows RDKit installed, ASE/DeepChem/PySCF/Psi4/etc missing. | Operational research loop. | Medium. | Add optional adapters behind capability detection. |
| Layered-lattice molecular AI research | `docs/research/layered_lattice_molecular_ai_targets_2026-05-31.md`. | Clear beatable target: topology loss, activity cliffs, scaffold leakage, explanation. | Medium. | Build activity-cliff and scaffold-leakage fixtures. |

Market context:

- RDKit is the standard open-source cheminformatics toolkit; SCBE should use it, not compete with it.
- Schrödinger is the high-end physics/platform target; SCBE should not claim to beat it at quantum chemistry.
- ChemCrow/Coscientist prove LLM + chemistry tools is a serious category; SCBE's angle is terminal receipts, loss accounting, and safe computational-only operation.

## Agentic CLI / Terminal OS Assets

| Asset | Evidence | Value | Readiness | Competitive Position |
| --- | --- | --- | --- | --- |
| SCBE CLI | `packages/cli`, bench commands, longform surface. | Primary public terminal product. | Medium-high. | Needs polish to match Claude Code/Codex/Aider ease-of-use. |
| Polly Pad CLI | `origin/main:packages/polly-pad-cli`. | Best end-user shell/workpad concept. | High after merge/publish. | Differentiated by persistent pad, audit, tool registry, cross packets. |
| Agent Bus | `packages/agent-bus`; server, queue, pipeline, tools, compass, workspace. | Backend for AI-native terminal operations. | High for developers. | More infrastructure-heavy than user-friendly. |
| Longform Bridge | `src/longform`, `scbe do/work/land/agent`, Kaggle chain integrity. | Durable memory/provenance moat. | Medium-high. | Strong if surfaced simply. |
| MCP readiness | Root dependency `@modelcontextprotocol/sdk`; existing tool bus maps naturally to MCP tools. | Makes SCBE usable by other agents. | Medium-low until server is shipped. | Important for ecosystem integration. |
| Search-space router / board/pathfinding | `origin/main` PR #2001; agent-bus pathfinding docs. | Differentiated constructed-space routing. | Medium. | More research than immediate CLI utility. |

Market context:

- Claude Code, Codex CLI, Aider, OpenCode, and similar tools focus on terminal coding/editing loops.
- MCP is now the standard adapter layer for exposing tools/resources/prompts to models.
- SCBE's strongest angle is not "another coding agent"; it is a persistent workpad + audit + benchmark + packet ledger that other agents can run inside.

## Private Proof / IP / Licensing Assets

| Asset | Location/Evidence | Value | Readiness | Handling |
| --- | --- | --- | --- | --- |
| Patent submission packet | Google Drive root: `01_SUBMIT_THESE_TO_PATENT_CENTER`, `README_FILE_THIS_PACKET.md`; repo `docs/legal/patent-workbench/*`. | High. Core IP/provenance material. | Private/internal. | Move/keep in private repo; do not publish raw. |
| Signed IP/teaming PDFs | Google Drive root: `ip_carveout_v1_signed.pdf`, `teaming_agreement_v1_signed.pdf`. | High supporting business/legal evidence. | Private/internal. | Catalog privately; do not expose in public site. |
| SCBE-private repo | GitHub connector: `issdandavis/SCBE-private`, private. | High. Store private proof/license material. | Exists. | Use as patent/license/private proof home. |
| RAG archive | Google Drive: `SCBE_RAG_ARCHIVE`; repo has docs/training archives. | Medium-high. Useful for retrieval and future products. | Mixed. | Deduplicate, manifest, and keep searchable. |
| CMMC/proposal docs | Google Drive root: CMMC docs/checklists; repo legal/proposal docs. | Medium for gov/enterprise path. | Research/support. | Keep as sales/proposal support, not public product. |
| Patent workbench scripts | `bin/scbe-patent.cjs`, `scripts/legal/*`, `docs/legal/patent-workbench/*`. | High internal workflow. | Medium. | Harden privately; public only as generic status/changelog if needed. |

## Content / Brand / Website / Game Assets

| Asset | Evidence | Value | Readiness | Bucket |
| --- | --- | --- | --- | --- |
| AetherMoore website | `docs/index.html`, PR #2011 proof-first homepage. | Public trust and conversion surface. | Medium. | Product/marketing. |
| Everweave / Gate Town | Google Drive root has Everweave export; GitHub has `scbe-gate-town` private repo. | Strong lore/brand/game potential. | Medium-low for product; high for content. | Content/game. |
| Kindle / Pip-Boy style app | `kindle-app/package.json`; Polly Pad concept. | Useful UI metaphor for agent workpads. | Low in current repo. | Research/content until active package selected. |
| Miracle Memory / books | Google Drive docs and memory. | Content/IP product lane. | Separate from SCBE CLI. | Content bucket. |
| YouTube tooling | package/review scripts and Apollo transcript tooling. | Useful distribution pipeline. | Medium. | Marketing/content ops. |
| Web/game/page ideas | AetherDesk, browser, pop-out book concepts. | Good brand differentiator. | Low until scoped. | Misc/content backlog. |

## Misc / Research / Content Bucket

These are not throwaways; they are just not ready to sell as product claims.

- GeoSeed orbital visualizations and shell duality theory beyond tested invariants.
- Rubix/tesseract browser as an agent UI model.
- Dwarf Fortress / tower dungeon / Citadel-style web game references.
- Drone/robotics/flight-sim controller mapping.
- NASA/USAF certification target matrix beyond local gap maps.
- Acoustic/vacuum physics and audio-axis work.
- Older archived SCBE repos and duplicated worktrees.
- Training-data corpora unless scrubbed, licensed, and documented.
- Articles, lore exports, and Obsidian notes not connected to a shipped command.

## Value Ranking

### Tier 1 - Sellable Soon

1. Polly Pad CLI / Python wrapper
2. SCBE CLI benchmark/evidence hub
3. Agent Bus workspace/audit-chain commands
4. Longform Bridge durable workflow commands

Why: These are understandable, installable, demonstrable, and useful even without accepting the full SCBE theory.

### Tier 2 - High-Value Proof/IP

1. Patent/private proof packet
2. Longform provenance ledger and semantic anchor work
3. Reaction-state packet schema
4. Benchmark evidence matrix

Why: These support licensing, enterprise trust, and defensible claims.

### Tier 3 - Differentiated Research/Product Candidates

1. Chemistry/reaction-state lane
2. Cross-language hex/binary/patchwork packets
3. Search-space router and pathfinding lattice
4. Rubix browser/permission hypercube

Why: These could become unique, but need larger corpora and official benchmark adapters.

### Tier 4 - Brand And Content

1. Everweave/Gate Town
2. AetherMoore lore/game/website surfaces
3. Books, YouTube, article factory

Why: Useful for audience, narrative, and product feel, but should not carry technical claims.

## Recommended Buckets

### 1. Public Product

- `scbe-aethermoore-cli`
- `scbe-agent-bus`
- `scbe-polly-pad-cli`
- `scbe-polly-pad`
- selected benchmark commands
- public docs with claim boundaries

### 2. Public Proof

- full evidence matrix
- longform chain benchmark
- compound decomposition/recomposition benchmark
- BFCL/tau/terminal adapters with non-official boundaries
- package registry changelog

### 3. Private Proof / Licensing

- patent packet
- signed IP/teaming agreements
- private proof hashes
- patent workbench support scans
- prosecution/fallback strategy
- licensing terms and tiered usage templates

### 4. Research-To-Product

- reaction-state packet CLI
- activity-cliff fixture
- scaffold-leakage detector
- PubChem/ChEMBL bridge
- MCP server over agent bus
- official benchmark adapters

### 5. Content / World / Brand

- Everweave / Gate Town
- AetherMoore lore
- web game / pop-out book site
- YouTube packaging/review
- book/manuscript assets

### 6. Misc / Archive

- old repo mirrors
- unused worktrees
- generated artifacts
- speculative notes not attached to a command
- duplicated packages pending reconciliation

## Biggest Gaps Blocking Higher Valuation

1. Branch divergence: current chemistry branch and `origin/main` both contain valuable work, but they are split.
2. Registry drift: package changelog says several packages are merged but not published.
3. CLI polish: strong internals, but the user-facing command hierarchy needs one clean "start here" path.
4. Official benchmark adapters: many local lanes exist; fewer official leaderboard-ready runs exist.
5. Chemistry corpus size: 3/3 proves shape, not market-level robustness.
6. Private/public separation: patent/proof docs should move to private repo and public site should expose only bounded evidence.
7. SEO/traffic data unavailable through current Semrush MCP plan.

## Next 5 Moves

1. Reconcile `feat/runtime-gate-durable-state` with `origin/main` without losing chemistry/reaction-packet commits.
2. Create `docs/ops/ASSET_CATALOG.json` from this report so the website/package docs can consume stable categories.
3. Fix the `rubix-browser` JSON CLI bench regression.
4. Publish/package sequence:
   - `scbe-aethermoore`
   - `scbe-agent-bus@0.5.0`
   - `scbe-aethermoore-cli`
   - `scbe-polly-pad-cli`
   - `scbe-polly-pad`
5. Start `feat(chem): bijective reaction harness` and expand atom-mud corpus to 25+ cases.

## Sources

- GitHub PR history via connector: PRs #1993-#2012 in `issdandavis/SCBE-AETHERMOORE`.
- Google Drive root listing via connector: patent packet, private PDFs, RAG archive, Everweave export, CMMC docs.
- SCBE package registry changelog on `origin/main`: `docs/ops/PACKAGE_REGISTRY_CHANGELOG_2026-05-30.md`.
- MCP specification: https://modelcontextprotocol.io/specification/latest
- MCP tools spec: https://modelcontextprotocol.io/specification/2024-11-05/server/tools
- Claude Code CLI reference: https://docs.claude.com/en/docs/claude-code/cli-reference
- OpenAI Codex CLI help: https://help.openai.com/en/articles/11096431
- Aider docs: https://aider.chat/docs/
- SWE-bench leaderboard: https://www.swebench.com/index.html
- OpenAI SWE-bench Verified reassessment: https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/
- Terminal-Bench: https://www.tbench.ai/
- BFCL paper: https://proceedings.mlr.press/v267/patil25a.html
- RDKit: https://www.rdkit.org/
- Schrödinger platform: https://www.schrodinger.com/platform
- ChemCrow: https://www.nature.com/articles/s42256-024-00832-8
