# SCBE Full System Inventory - 2026-05-31

This is a working inventory of the SCBE/AetherMoore asset base as verified from
the local checkout, GitHub, the live website, Hugging Face, and Kaggle on
2026-05-31. It is not a proposal-only map. These are owned systems and assets
unless and until a customer, grant, or commissioning agreement scopes them into
outside delivery.

## Product Direction

The strongest near-term product is not "another AI agent." The gap is production
governance for agents that already work in pilot form.

Product shape:

- SCBE Governance SDK: a drop-in wrapper for existing agent stacks.
- REST endpoint: a language-neutral scan service for Python, TypeScript, n8n,
  LangChain, CrewAI, AutoGen, and internal tools.
- Receipts now, report generator later: store every scan as a stable receipt
  hash; render compliance PDFs only after the hose is connected.

Practical pitch:

> Move your agents from pilot to production without rewriting them.

Build priority:

1. SDK packaging and REST scan endpoint.
2. Framework examples for LangChain, CrewAI, AutoGen, and n8n.
3. Hosted dashboard and PDF compliance reports after real scan traffic exists.

## Local Workspace

Repository root: `C:\Users\issda\SCBE-AETHERMOORE`

Current local shape from `rg --files`:

| Area | Files | Notes |
| --- | ---: | --- |
| `src/` | 1031 | Main TypeScript/Python codebase: harmonic pipeline, crypto, governance, tokenizer, API pieces. |
| `scripts/` | 874 | Benchmark, training, publishing, system, revenue, Kaggle/HF, and operational tooling. |
| `docs/` | 514 | Website source, public docs, benchmarks, legal/patent workbench, business notes. |
| `content/` | 250 | Book/manuscript/canon/content vault material. |
| `notes/` | 223 | Theory, tokenizer, sphere-grid, and working notes. |
| `packages/` | 213 | Agent bus, CLI, kernel, BookForge, Polly Pad, workflow engine, Python packages. |
| `api/` | 77 | Production-facing FastAPI/Vercel-style API surfaces, billing, auth, audit export. |
| `agents/` | 73 | Agent schemas, ledgers, researcher/orchestrator components. |
| `python/` | 61 | Python SCBE modules, reaction harness, atomic tokenizer bridge, PQC package. |
| `config/` | 86 | Model training configs, eval contracts, governance and security registries. |
| `benchmarks/` | 38 | SCBE benchmark package and benchmark task fixtures. |
| `schemas/` | 30 | Training, SWLE, hydra packet, and token schemas. |
| `services/` | 22 | Service-level support code. |

Generated/local-heavy areas include `artifacts/`, `training/runs/`, `.worktrees/`,
`.claude/worktrees/`, local caches, external repos, and benchmark datasets. Treat
those as evidence or scratch unless intentionally promoted.

## Product Systems

### Governance / Agent Production

- `api/main.py` and `src/api/main.py`: API surfaces with authenticated
  governance, auth, billing, metering, audit export, and SaaS/mobile endpoints.
- `packages/agent-bus/`: Node governed execution surface with queue, plugins,
  GeoSeal pipeline, tool registry, circuit breakers, and CLI.
- `packages/agent-bus-py/`: Python package for governed event running and now a
  lightweight governance scan SDK.
- `bin/geoseal.cjs`, `src/geoseal*.py`, `src/geoseal*.ts`: GeoSeal command and
  governance implementations.
- `src/governance/`, `src/crypto/`, `packages/kernel/`: governance math,
  decision envelopes, audit ledger, runtime gate, and kernel primitives.

Newly connected production-hose piece:

- `scbe_agent_bus.scan_agent_request(...)`
- `scbe_agent_bus.scan_command(...)`
- `scbe-agent-bus --scan`
- `POST /v1/governance/scan` in both API surfaces

These return `ALLOW`, `QUARANTINE`, or `DENY`, plus `score`, `d_H`,
`pattern_drift`, reason codes, and a stable `receipt_hash`.

### Benchmarks / Harnesses

Local benchmark evidence areas:

- `artifacts/benchmarks/hydra_jobsite_conservation/`
- `artifacts/benchmarks/tb-neutral-compare/`
- `artifacts/benchmarks/terminal_bench_adapter/`
- `artifacts/benchmarks/compound_decomposition_recomposition/`
- `artifacts/benchmarks/chemistry_cli_capability/`
- `artifacts/benchmarks/scbe_full_system/`
- `artifacts/benchmarks/arc_style_grid/`
- `artifacts/benchmarks/arc_agi2_local/`
- `artifacts/benchmarks/rubix_browser_hypercube/`
- `artifacts/benchmarks/research_agent_fixtures/`
- `artifacts/benchmarks/tau_bench_policy/`
- `artifacts/benchmarks/bfcl_tool_call_adapter/`
- `artifacts/benchmarks/longform_chain_integrity/`

Recent benchmark claims that need to stay evidence-linked:

- Terminal-bench neutral governance parity: 13/13 SCBE matching oracle.
- Hydra jobsite conservation lane: 6/6 conservation benchmark, baseline margin
  recorded in local benchmark artifacts.
- Adversarial governance/Petri claims should remain tied to exact artifact paths
  and scripts before being used in sales copy.

### Chemistry / Tokenizer / Science Layer

Local evidence of chemistry tied into tokenizer and governance:

- `python/scbe/atomic_tokenization.py`
- `python/scbe/chemical_fusion.py`
- `python/scbe/reaction_state.py`
- `python/scbe/reaction_harness.py`
- `src/tokenizer/atomic_workflow_units.py`
- `src/tokenizer/chemistry_command_stack.py`
- `src/governance/chemical_bonds.py`
- `src/minimal/ternary_dirichlet_chemistry.py`
- `scripts/benchmark/compound_decomposition_recomposition.py`
- `scripts/benchmark/chemistry_cli_capability.py`
- `docs/specs/CHEM_SEMANTIC_DECOMPOSITION_BRIDGE.md`
- `docs/specs/CROSS_LANGUAGE_REACTION_STATE_MODEL.md`
- `notes/theory/atomic-tokenizer-chemistry-unified.md`

This is an owned research/product lane. It should be inventoried as a tokenizer,
reaction-state, and benchmark system before being framed as proposal content.

### Books / Proprietary Training Data

Owned manuscript and publishing assets:

- `content/book/reader-edition/`: chapters, interludes, canon maps, continuity flags.
- `content/book/AVALON_WRITING_BIBLE.md`, `HOUSE_STYLE.md`, `FINAL_TOPOGRAPHY.md`,
  `CRAFT_COMPARISON_MATRIX.md`, and related editorial system files.
- `book/ai-governance-fundamentals/`: governance book chapters and `book.yaml`.
- `docs/books.html`, `docs/books.json`, and `docs/books/*.html`: public bookshelf.
- `docs/downloads/*`: writing and security/governance downloadable guides.
- `packages/bookforge/`: book packaging/publishing tooling.

These assets can become proprietary training data only after a rights and source
registry pass. The first split should be:

- `train-ok-owned`: original drafts, house style, canon notes, generated internal
  examples with known provenance.
- `review-only`: external references, market analysis, copied snippets, and
  mixed-source notes.
- `do-not-train`: secrets, customer data, credentials, private emails, and
  unclear-origin material.

## GitHub

Verified with `gh` as user `issdandavis`.

Primary repository:

- `issdandavis/SCBE-AETHERMOORE`
- Visibility: public
- Homepage: `https://aethermoore.com`
- Default branch: `main`
- Primary language: Python
- Topics include AI governance, AI safety, cryptography, hyperbolic geometry,
  post-quantum cryptography, autonomous agents, LLM security, multi-agent
  systems, prompt injection, runtime governance, and geometric security.
- GitHub Pages source: `main` branch, `/docs` path.

Repository ecosystem observed from `gh repo list`:

- Core/public: `SCBE-AETHERMOORE`, `aetherbrowser`, `phdm-21d-embedding`,
  `aethermoore-youtube-automation`, `scientific-agent-skills`, `scbe-experiments`,
  `scbe-training-lab`, `scbe-agents`, `scbe-tongues-toolchain`,
  `six-tongues-geoseal`.
- Private/proprietary: `SCBE-private`, `scbe-gate-town`, `miracle-memory-archive`,
  `book-workshop`, `watershed-cultivation`, `devoted-novel`,
  `miracle-memory-book`, `claude-memory-archive`, `mathbac-archive`.
- Training/infrastructure/forks: Kaggle, kernels, automation, navigation,
  trading, and vendor-fork repositories.

GitHub cleanup need: define which repositories are product source, private IP
vault, training source, deployment surface, or fork/vendor reference.

## Live Website

Verified URLs:

| URL | Status | Current message |
| --- | ---: | --- |
| `https://aethermoore.com/` | 200 | Lead offer: stop AI from creating legal exposure. |
| `https://aethermoore.com/SCBE-AETHERMOORE/` | 200 | Experimental agentic operating system for durable workflows, governed tool use, audit trails, cross-language transformation, and evidence-backed automation. |
| `https://aethermoore.com/SCBE-AETHERMOORE/books.html` | 200 | AetherMoore Bookshelf with books, formats, purchase links, and publishing process. |
| `https://aethermoore.com/SCBE-AETHERMOORE/hosted-run.html` | 200 | Hosted run intake with local/Ollama-first framing. |
| `https://aethermoore.com/SCBE-AETHERMOORE/benchmarks.html` | 404 | Gap: benchmark evidence exists locally but is not surfaced at this route. |

Website action items:

- Add or redirect a benchmark landing page to `docs/benchmarks/dashboard.html`.
- Add a Governance SDK page with the 3-line Python example and REST example.
- Make evidence pages link to exact local/generated artifact names, not broad claims.

## Hugging Face

Verified account:

- User: `issdandavis`
- Orgs: `blog-explorers`, `SCBE-AETHER`

Assets observed:

- 50 model repos returned by CLI limit, including `phdm-21d-embedding`,
  `spiralverse-ai-federated-v1`, `scbe-ops-assets`, `geoseed-network`,
  `scbe-pivot-qwen-0.5b`, Polly Qwen variants, SCBE 7B variants, Qwen coding
  agents, bijective tongue coder models, approval metrics models, Geoseal
  harness models, and chemistry/atomic workflow models.
- Datasets include private knowledge base and interaction logs, Polly training
  data, kernel datasets, life science research demo, code-flow pretraining,
  prompt-injection bit signatures, backups, drill/tongue/codeflow datasets, and
  multiple private coding-agent SFT/DPO datasets.
- Spaces include `SCBE-AETHERMOORE-Demo`, private AI hub, `phdm-21d-embedding`,
  `six-tongues-protocol`, red-team sandbox, Polly sandbox/proxy, and mesh foundry.

Hugging Face cleanup need:

- Model cards should identify which models are current, experimental, archived,
  or unsafe for customers.
- Dataset cards need train-rights labels and provenance summaries.
- The local HF CLI warned that the installed `huggingface_hub` is behind the
  latest available version.

## Kaggle

Verified Kaggle user: `issacizrealdavis`

Datasets observed:

- `scbe-system-hygiene-training`
- `scbe-polly-training-data` - title says 92K SFT pairs
- `scbe-bijective-tongue-coder-holdout`
- `scbe-coding-agent-stage6-repair-v7`
- `scbe-governance-research-results`
- `scbe-agentic-coding`
- `scbe-dense-bundle-sft-v1`

Kernels observed:

- `scbe-aethermoore-chain-integrity-benchmark`
- `scbe-longform-chain-integrity-benchmark`
- `polly-tokenizer-probe-qwen-coder`
- `polly-auto-chemistry-science-v9-strict`
- `polly-auto-chemistry-science-v8`
- `polly-auto-dsl-syn-v3-fast`
- `polly-auto-bijective-coder-v2-fmt-repair`
- `polly-auto-bijective-tongue-coder-v2`

Kaggle cleanup need:

- Improve dataset usability scores with complete metadata, licenses, dataset
  cards, and expected-input/expected-output examples.
- Add links from Kaggle kernels back to the current repo evidence docs.

## Active Gaps

1. Product packaging gap: SDK and REST scan are now started, but framework
   examples are still missing.
2. Website evidence gap: public benchmark route returns 404.
3. Inventory gap: GitHub/HF/Kaggle assets need a machine-readable registry with
   owner, status, public/private, training rights, and product relevance.
4. Training rights gap: books and notes need explicit train/hold/do-not-train
   classification before becoming a model corpus.
5. API startup gap: full API imports can hang in the current local environment;
   targeted module compile works, but app-startup needs separate triage.
6. Python lint debt: broad `npm run lint:python` is known to fail on pre-existing
   repository-wide flake8 issues; new files should be kept clean and checked
   targeted.

## Verification Commands

Commands used for this pass:

- `rg --files`
- `gh auth status`
- `gh repo view issdandavis/SCBE-AETHERMOORE --json ...`
- `gh api repos/issdandavis/SCBE-AETHERMOORE/pages`
- `gh repo list issdandavis --limit 100`
- `hf auth whoami`
- `hf models list --author issdandavis --limit 50 --format json`
- `hf datasets list --author issdandavis --limit 50 --format json`
- `hf spaces list --author issdandavis --limit 50 --format json`
- `kaggle config view`
- `kaggle datasets list -m --search scbe`
- `kaggle kernels list --mine`
- `Invoke-WebRequest` against the live website URLs above.

Targeted code verification for the SDK/REST scan work:

- `python -m py_compile packages/agent-bus-py/src/scbe_agent_bus/governance.py packages/agent-bus-py/src/scbe_agent_bus/__init__.py packages/agent-bus-py/src/scbe_agent_bus/__main__.py api/main.py src/api/main.py`
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest packages/agent-bus-py/tests/test_governance_scan.py packages/agent-bus-py/tests/test_smoke.py -q`

Result: 11 package tests passed with plugin autoload disabled. Direct SDK smoke
returned `ALLOW` for `cat README.md` and `DENY` for a reverse shell command.
