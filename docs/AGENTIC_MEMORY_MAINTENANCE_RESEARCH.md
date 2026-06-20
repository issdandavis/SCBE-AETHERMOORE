# Agentic Memory Maintenance Research

Updated: 2026-06-15

## Executive Summary

SCBE already contains most of the primitives needed for durable agent memory: sealed memory packets, hyperbolic retrieval, tokenizer-graph memory, hive-style tiering, sidekick JSONL logs, agent-bus ledgers, and life-ledger identity state. The gap is not another memory store. The gap is a governed maintenance loop that classifies, promotes, seals, retrieves, compacts, and quarantines memories across those stores.

The recommended architecture is an `AgenticMemoryMaintainer` service with five lanes:

1. **Session lane**: recent conversation/tool context, trimmed and compressed.
2. **Core lane**: small editable profile of durable operating facts.
3. **Recall lane**: append-only event log for actions, outcomes, tool calls, errors, and user preferences.
4. **Archival lane**: semantic and graph memory for long-term retrieval.
5. **Governance lane**: sealing, provenance, injection checks, retention policy, and audit receipts.

This maps cleanly onto existing SCBE modules instead of replacing them.

## External Baseline

OpenAI Agents SDK sessions provide thread-scoped memory for conversation history and remove the need to manually re-send prior turns during multi-turn runs. This is useful but not enough for cross-session agent learning.

LangGraph long-term memory stores JSON documents under namespaces and keys, supporting persistence across threads and content-based filtering. Its strongest idea for SCBE is namespacing: memory should be scoped by user, agent, project, domain, and risk tier.

Letta/MemGPT-style systems split memory into core, recall, and archival layers. Core memory is in-context and editable; archival memory is searched on demand; recall memory preserves message/event history. This is close to SCBE's natural split between sidekick logs, sealed packets, and hyperbolic/tokenizer graph retrieval.

Zep/Graphiti adds the strongest missing concept: temporal knowledge graphs. Facts are not just stored; they have provenance and time validity. That matters for agentic maintenance because repo state, goals, credentials, model choices, and user preferences change.

Operationally, agentic memory should be maintained like production infrastructure. Google SRE's four golden signals are latency, traffic, errors, and saturation. OpenTelemetry standardizes traces, metrics, and logs. NIST AI RMF frames ongoing governance as Govern, Map, Measure, and Manage. OWASP's GenAI risks highlight prompt injection, data poisoning, excessive agency, and memory/context poisoning.

## Current SCBE Memory Assets

### Sealed Memory Packets

File: `src/crypto/sealed_memory_packets.py`

This is the strongest security primitive. It encodes payloads into Sacred Tongue tokens, seals them with RWP v3, verifies metadata hashes, token hashes, payload hashes, and optionally uses PQC governance. This should be the write path for any memory that is durable, sensitive, high-value, or agent-controlling.

Use it for:

- user preferences and identity facts;
- agent operating instructions;
- successful workflows worth replaying;
- recovery checkpoints;
- security-sensitive memories;
- high-confidence summaries of long sessions.

Do not use it as the raw event log for every tiny observation; sealing every low-value event would add noise and cost.

### Hive Memory

File: `src/spiralverse/hive_memory.py`

This provides a tiered memory model: hot, warm, cold, plus CHARM-based eviction priority, snapshots, compression, checksums, and mission context. Its model is aligned with MemGPT/Letta's hierarchy, but SCBE-specific through CHARM and tongue metadata.

Use it as the tier manager:

- hot: active session context and current task state;
- warm: recent project memories and active repo facts;
- cold: sealed packets, archives, graph memory, and compressed snapshots.

### Sidekick Memory

File: `scripts/sidekick_memory.py`

This is a practical append-only JSONL memory and SFT bootstrap tool. It logs task, context, action, outcome, artifacts, tags, and score, then can convert that memory to supervised training rows.

Use it as the operator-facing memory feed. It should become the human-readable input into promotion, compaction, and training-data generation.

### Hyperbolic RAG

File: `src/ai_brain/hyperbolic_rag.py`

This supports Poincare-ball retrieval with distance gating, phase alignment, trust scoring, and quarantine behavior. This is better than plain vector search for SCBE because the memory system already encodes tongue/phase/ring concepts.

Use it for recall after the governance lane has filtered candidate memories.

### Tokenizer Graph Memory

File: `src/knowledge/tokenizer_graph/memory_chain.py`

This stores chunks as 6D Sacred Tongue coordinates, auto-links nearby chunks, creates scenes, and records chain/governance hashes. It is the best local foundation for SCBE's "memory as graph" direction.

Use it as the semantic map:

- nodes: facts, decisions, repo chunks, theories, workflows;
- edges: dependency, contradiction, refinement, lineage, replay;
- scenes: clusters such as `chemistry-tokenizer`, `prime-theory`, `color-theory`, `geoseal-pqc`, `agent-maintenance`.

### Agent Bus and Life Ledger

Files:

- `agents/agent_bus_ledger.py`
- `packages/agent-bus/src/life-ledger.ts`

The bus ledger mirrors agent events into HYDRA/SQLite when available. Life ledger stores persistent identity, known agents, alignment scores, skills, career entries, and groups.

Use these for agentic continuity:

- who did what;
- which agent is trusted for which lane;
- skill growth;
- failed actions;
- task lineage;
- maintenance history.

## Proposed SCBE Architecture

### PC Resource Memory

Agentic memory maintenance also needs machine-resource memory. Users will run SCBE on ordinary PCs, not only cloud servers. The agent should remember and check local constraints before expensive work: RAM pressure, pagefile use, disk headroom, cloud-sync load, cache hotspots, and backup recursion hazards.

Operational source:

`scbe system health`

Detailed Windows report:

`scripts/system/pc_memory_health.ps1`

User-facing policy:

- run a shallow PC health preflight before PQC builds, repo-wide scans, RAG indexing, browser swarms, local model training, and backup/recovery;
- warn above 85% RAM use;
- warn below 25 GB free on target drives;
- warn when OneDrive/Dropbox/Drive is consuming more than 1 GB RAM;
- never kill processes, delete caches, empty Recycle Bin, or move user files without explicit confirmation;
- write health reports to `artifacts/pc-memory/` so future agents can recall the machine state.

This creates a second kind of memory: not semantic user memory, but operational machine memory. It prevents the agent from repeating unsafe heavy actions on a constrained PC.

### Memory Packet Schema

Every durable memory should normalize to:

```json
{
  "id": "mem_...",
  "kind": "fact|event|preference|workflow|checkpoint|warning|theory|receipt",
  "scope": ["user", "agent", "repo", "project", "domain"],
  "source": {"type": "chat|tool|git|file|test|web", "uri": "..."},
  "content": "...",
  "summary": "...",
  "evidence": [],
  "confidence": 0.0,
  "risk": "low|medium|high|sealed",
  "valid_from": "ISO-8601",
  "valid_until": null,
  "supersedes": [],
  "contradicts": [],
  "tags": [],
  "tongue": "KO|AV|RU|CA|UM|DR",
  "embedding": [],
  "hash": "...",
  "seal": null
}
```

### Maintenance Loop

The maintainer should run after each significant task and on a schedule:

1. **Ingest**: read sidekick logs, agent-bus events, git commits, test results, docs, and explicit user memories.
2. **Classify**: decide whether each item is fact, preference, workflow, checkpoint, warning, theory, or trash.
3. **Validate**: attach evidence: file path, command output hash, commit hash, source URL, or human confirmation.
4. **Score**: compute confidence, novelty, recurrence, risk, CHARM, and retrieval value.
5. **Promote**: move important items into core memory, sealed memory, graph memory, or archival memory.
6. **Compact**: summarize repeated low-level events into one higher-level durable fact.
7. **Quarantine**: isolate memory that came from untrusted web/tool output or conflicts with stronger evidence.
8. **Recall**: retrieve relevant memory by namespace, hyperbolic distance, graph neighborhood, and time validity.
9. **Audit**: write a ledger event for every promotion, deletion, contradiction, or seal operation.

### Promotion Rules

Promote to core memory only when a fact is stable, frequently useful, and low risk. Examples: repo root, preferred command style, user project goals.

Promote to sealed memory when it controls future behavior, contains sensitive data, or would be costly to lose. Examples: user strategy, recovery checkpoints, trusted build instructions.

Promote to graph memory when relationships matter. Examples: chemical token notation, prime/color theories, compiler target mappings, geoseal/PQC flow.

Keep in recall/event log when it is useful for audit but not worth injecting into context. Examples: command outputs, failed experiments, one-off test runs.

Reject or quarantine memories when they are unsupported, tool-output-only, prompt-injected, contradictory, or stale.

## Agentic Maintenance Controls

The maintainer should expose commands:

```powershell
scbe memory ingest --from agent-bus --since 24h
scbe memory promote --kind workflow --tag geoseal
scbe memory recall "how does chemical tokenization map to valence"
scbe memory audit --agent geoseal --since 7d
scbe memory compact --namespace repo:SCBE-AETHERMOORE
scbe memory quarantine --source web --reason prompt-injection
scbe memory seal --risk high --tag user-system
```

It should also emit health metrics:

- recall latency;
- memory write volume;
- retrieval hit rate;
- contradiction count;
- quarantine count;
- stale memory count;
- failed seal/unseal count;
- context injection token cost;
- source coverage by namespace.

## Safety Model

Memory writes are an attack surface. Treat all web pages, emails, tool outputs, model outputs, and unverified documents as untrusted until validated.

Minimum controls:

- source provenance required for durable memory;
- separate "observed claim" from "trusted fact";
- human-confirmed memories get stronger weight;
- sealed packets for behavior-changing memories;
- no automatic promotion from untrusted web text to core memory;
- contradiction tracking instead of overwriting;
- expiration for volatile facts;
- audit receipts for promotion/deletion;
- prompt-injection screening before memory write;
- retrieval gating before context injection.

## Best Fit for SCBE

SCBE should not adopt a generic memory stack wholesale. Its differentiator is a governed symbolic memory substrate:

- Sacred Tongue/tokenizer graph for structured meaning;
- hyperbolic retrieval for geometric relevance;
- sealed memory packets for integrity;
- hive memory for tiering and compression;
- sidekick JSONL for human-readable task memory;
- agent-bus/HYDRA ledger for event provenance;
- life-ledger for persistent agent identity and skill growth.

The next implementation target should be a thin orchestrator, not a rewrite:

`src/memory/agentic_maintainer.py`

It should call existing modules and write a single governed memory index under:

`artifacts/memory/agentic_memory_index.jsonl`

That gives the system durable recall, safety gates, and maintenance without forcing every subsystem to change at once.

## References

- OpenAI Agents SDK Sessions: https://openai.github.io/openai-agents-python/sessions/
- OpenAI Agents SDK session memory cookbook: https://developers.openai.com/cookbook/examples/agents_sdk/session_memory
- LangGraph memory overview: https://docs.langchain.com/oss/python/concepts/memory
- LangGraph long-term memory: https://docs.langchain.com/oss/python/langchain/long-term-memory
- Letta archival memory: https://docs.letta.com/guides/core-concepts/memory/archival-memory/
- Letta stateful agents: https://docs.letta.com/guides/core-concepts/stateful-agents/
- MemGPT paper: https://arxiv.org/abs/2310.08560
- Generative Agents paper: https://arxiv.org/abs/2304.03442
- Graphiti repository: https://github.com/getzep/graphiti
- Graphiti overview: https://help.getzep.com/graphiti/getting-started/overview
- Zep temporal knowledge graph paper: https://arxiv.org/html/2501.13956v1
- Google SRE monitoring golden signals: https://sre.google/sre-book/monitoring-distributed-systems/
- OpenTelemetry documentation: https://opentelemetry.io/docs/
- NIST AI RMF: https://www.nist.gov/itl/ai-risk-management-framework
- OWASP Top 10 for LLM Applications: https://owasp.org/www-project-top-10-for-large-language-model-applications/
