# Research Vault to Agent Harness, Bus, and CLI Integration Plan

Purpose: make the Researcher-Guided Knowledge RAG / SCBE Research Vault lane visible to other agents before implementation. This is a product and infrastructure concept, not yet a completed backend.

## Boundary

Keep this lane separate from MATHBAC unless it is mentioned only as broader SCBE capability.

- Book/product framing: source cards, style cards, retrieval packets, human review, audit trails.
- Internal backend: ingestion, vector/retrieval store, reviewer queue, SCBE governance, export system.
- Commercial product later: SCBE Research Vault or Researcher-Guided Knowledge RAG.

Do not claim that the full Research Vault backend exists until ingestion, retrieval, reviewer approval, and audit emission are implemented and tested.

## Existing Surfaces to Reuse

Agent harness:

- `src/coding_spine/agent_tool_bridge.py`
- Emits `scbe_agent_harness_manifest_v1`.
- Gives model-neutral tool contracts, permission profiles, language routes, service URLs, and replay commands.

Command compiler:

- `src/coding_spine/command_compiler.py`
- Emits `scbe_command_plan_v1`.
- Current flow: `intent -> tool_class -> policy -> command_template`.
- This is the right place to compile Research Vault tasks into bounded commands.

Policy gate:

- `src/coding_spine/agent_tool_policy.py`
- Evaluates tool class against permission mode.
- Research ingestion and retrieval should start as `read` or `write_workspace`; network-backed research should require `network_or_cloud`.

GeoSeal HTTP service:

- `src/api/geoseal_service.py`
- Current harness endpoints:
  - `POST /v1/harness/tool-bridge`
  - `POST /v1/harness/agent-harness`
  - `POST /v1/geoseal/compile`

Agent bus:

- `packages/agent-bus/tools.json`
- `packages/agent-bus/bin/scbe-agent-bus.cjs`
- `packages/agent-bus-py/`
- Existing tools already include `geoseal-compile`, `scbe-agentbus`, and research APIs for arXiv, Semantic Scholar, OpenAlex, CrossRef, PubMed, SAM.gov, USPTO, Hugging Face, and GitHub repositories.

Browser/operator CLI:

- `scripts/aetherbrowser/api_server.py`
- Existing safe CLI dispatch already recognizes harness and agent-bus lanes.

## Proposed Research Vault Schemas

Start with files and JSON packets before building a database-backed service.

`source_card_v1`:

```json
{
  "schema_version": "source_card_v1",
  "source_id": "sha256:<content-or-record-hash>",
  "title": "",
  "author": "",
  "source_type": "book|paper|video|interview|note|web|primary_doc",
  "locator": "path/url/citation",
  "rights_status": "owned|public_domain|licensed|citation_only|unknown",
  "claims": [],
  "quotes": [],
  "verified_notes": [],
  "quality": "raw|reviewed|trusted",
  "created_at": ""
}
```

`style_card_v1`:

```json
{
  "schema_version": "style_card_v1",
  "style_id": "",
  "scope": "author|project|chapter|scene|proposal",
  "allowed_moves": [],
  "banned_moves": [],
  "cadence_notes": [],
  "quote_rules": [],
  "mechanics_visibility": "hidden|light|explicit",
  "created_at": ""
}
```

`retrieval_packet_v1`:

```json
{
  "schema_version": "retrieval_packet_v1",
  "task_id": "",
  "query": "",
  "source_cards": [],
  "style_cards": [],
  "selected_notes": [],
  "blocked_sources": [],
  "citation_requirements": [],
  "review_required": true
}
```

`review_decision_v1`:

```json
{
  "schema_version": "review_decision_v1",
  "packet_id": "",
  "reviewer": "human|agent",
  "decision": "approve|revise|reject",
  "reasons": [],
  "approved_output_path": "",
  "audit_hash": ""
}
```

## Bracket Labels for Writing Workflows

Use explicit bracket labels during drafting and collapse them before publication:

- `[author_voice_guides_framed_phrases]`
- `[author_quotes]`
- `[quotes_from_sources]`
- `[extrapolation]`
- `[history]`
- `[sources]`
- `[ai_prose]`
- `[author_prose]`
- `[author_quotes_with_extensions]`
- `[lore_sources]`
- `[citation_needed]`
- `[human_review_required]`

These labels let agents reason about source provenance without exposing AI mechanics in the final reader-facing draft.

## Minimum Workflow

1. Ingest folders, Obsidian vault notes, PDFs, transcripts, and manually curated notes into source cards.
2. Build style cards from user-authored voice guides and project-specific style rules.
3. Compile a user goal into `scbe_command_plan_v1`.
4. Build a retrieval packet with only relevant source/style cards.
5. Generate a draft with bracket labels preserved.
6. Run human review and source-label cleanup.
7. Export clean manuscript/proposal text plus a private audit packet.

## Research Backing to Keep Attached

The existing harness research note is `docs/ops/AGENTIC_CLI_HARNESS_RESEARCH_2026-04-29.md`. It already records these primary-source design patterns:

- OpenAI Codex: sandbox modes and approval separation.
- Claude Code: MCP integration, hooks, and permission processing.
- OpenHands: sandboxed environments, coordination, and evaluation benchmarks.
- Aider: Git-centered terminal workflow.
- Model Context Protocol: tools, resources, prompts, and host-controlled authorization.

Research gaps before product claims:

- RAG provenance and citation tracing practices.
- Human-in-the-loop approval queue patterns.
- Local-first document ingestion and vector store tradeoffs.
- Audit JSON schema conventions.
- Secure tunnel/auth deployment patterns.
- Copyright-safe quote handling and source transformation rules.

## Test Gates

API and tunnel smoke:

```powershell
Invoke-RestMethod -Uri 'http://localhost:8000/health'
Invoke-WebRequest -Uri 'http://127.0.0.1:20241/metrics' |
  Select-String -Pattern 'cloudflared_tunnel_ha_connections|cloudflared_tunnel_request_errors'
```

Harness tests:

```powershell
python -m pytest tests/test_agent_task_run_and_external_eval.py -q
python -m pytest tests/coding_spine/test_agent_tool_policy.py tests/coding_spine/test_skill_harness_tools.py -q
```

Agent bus package:

```powershell
npm --prefix packages/agent-bus run build
npm --prefix packages/agent-bus test
npm --prefix packages/agent-bus run typecheck
```

Python agent bus:

```powershell
python -m pytest packages/agent-bus-py/tests -q
```

## Implementation Order

1. Add schema files for `source_card_v1`, `style_card_v1`, `retrieval_packet_v1`, and `review_decision_v1`.
2. Add a local folder ingestion command that emits source cards only.
3. Add a retrieval packet builder that reads source/style cards and writes a deterministic packet.
4. Register Research Vault commands in `packages/agent-bus/tools.json`.
5. Expose a `geoseal compile` pathway for Research Vault tasks.
6. Add tests that prove permission boundaries:
   - local read-only retrieval under `observe`;
   - local card generation under `workspace-write`;
   - network research only under `cloud-dispatch` or explicit approval;
   - secrets never appear in retrieval packets.
7. Add reviewer queue and SCBE audit JSON only after the local packet workflow is stable.

