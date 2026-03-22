# SCBE Tiered Subagent System

## Status: Phase 1 Built (Context Broker MCP)

### What's Built
- `src/mcp/context_broker_mcp.py` — 5 MCP tools, phdm-21d routing, 4-tier classification
- Tongue classification working: T1 Scout → T4 Architect
- 31 memory files indexed, Poincare ball nearest-neighbor retrieval
- Session journal persistence

### Architecture
See the full architecture document in the git history or ask Claude to explain it.

### Tools
| Tool | What |
|------|------|
| `context_inject` | Embed intent → find relevant memories → classify tier |
| `context_retrieve` | Pull memory files by topic |
| `memory_update` | Write new memory entries |
| `session_summarize` | Journal session for next-session persistence |
| `tongue_classify` | Classify intent → tongue domain + agent tier |

### Tiers
| Tier | Name | Tongues | Context Budget |
|------|------|---------|---------------|
| 1 | Scout | KO | 2K tokens |
| 2 | Worker | KO+AV | 8K tokens |
| 3 | Analyst | KO+AV+RU | 32K tokens |
| 4 | Architect | All 6 | 128K tokens |

### Next Phases
- Phase 2: SCBE Gateway MCP (authorization gate)
- Phase 3: Tier Dispatcher MCP (subagent spawning)
- Phase 4: HYDRA Consensus (multi-agent voting)
- Phase 5: Package as sellable plugin
