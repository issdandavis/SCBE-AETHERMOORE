# Repository Consolidation Map

## Current State: 47 repos scattered

## Target State: 3 clear products

---

## Product 1: SCBE Core (AI Governance)
**Single repo**: `SCBE-AETHERMOORE` (keep as main)

### Repos to MERGE into SCBE-AETHERMOORE:

| Repo | Action | What to Take |
|------|--------|--------------|
| `scbe-security-gate` | MERGE | Gateway code → `/src/gateway/` |
| `scbe-quantum-prototype` | MERGE | PQC proofs → `/src/pqc/` |
| `Spiralverse-AetherMoore` | MERGE | Protocol docs → `/docs/protocol/` |
| `spiralverse-protocol` | MERGE | Specs → `/docs/specs/` |
| `pypqc` | MERGE | Python crypto → `/python/pqc/` |
| `SCBE_Production_Pack` | ARCHIVE | Old version |
| `SCBE_Production_Pack.0.1` | ARCHIVE | Old version |
| `scbe-aethermoore-demo` | KEEP SEPARATE | Demo site |

### After merge, SCBE-AETHERMOORE structure:
```
SCBE-AETHERMOORE/
├── src/
│   ├── core/           # 14-layer pipeline
│   ├── agent/          # Multi-agent system (NEW)
│   ├── tokenizer/      # SS1 + quantum-lattice (NEW)
│   ├── gateway/        # FROM scbe-security-gate
│   ├── pqc/            # FROM scbe-quantum-prototype
│   └── harmonic/       # Audio axis
├── python/
│   ├── scbe/           # Python implementation
│   └── pqc/            # FROM pypqc
├── api/
│   └── governance-schema.yaml  # (NEW)
├── k8s/
│   └── agent-manifests/        # (NEW)
├── docs/
│   ├── AGENT_ARCHITECTURE.md
│   ├── SWARM_CODER_ONEPAGER.md
│   ├── protocol/       # FROM Spiralverse-AetherMoore
│   └── specs/          # FROM spiralverse-protocol
└── tests/
```

---

## Product 2: AI Workflow Architect (Orchestration Platform)
**Single repo**: `AI-Workflow-Architect` (keep as main)

### Repos to MERGE or ARCHIVE:

| Repo | Action | Reason |
|------|--------|--------|
| `ai-workflow-platform` | MERGE | Duplicate |
| `forgemind-ai-orchestrator` | MERGE | Agent system → use |
| `AI-Agent-Workflow` | ARCHIVE | Old version |
| `ai-orchestration-hub` | ARCHIVE | Old version |
| `Kiro_Version_ai-workflow-architect` | ARCHIVE | Kiro fork |
| `ai-workflow-architect-replit` | ARCHIVE | Replit version |
| `ai-workflow-architect-main` | ARCHIVE | Old main |
| `ai-workflow-architect-pro` | ARCHIVE | Pro version |
| `AI-Workflow-Architect-1.2.2` | ARCHIVE | Version snapshot |
| `AI-Workflow-Architect-1` | ARCHIVE | Version 1 |
| `ai-workflow-systems` | ARCHIVE | Old |

### Keep separate:
- `gumroad-automation-demo` → Sales demo

---

## Product 3: Shopify Apps
**Keep as separate repos** (Shopify deployment requirement)

| Repo | Status |
|------|--------|
| `shopify-development` | KEEP |
| `Shopify-Command-Center` | KEEP (private) |
| `shopguide-ai-merchant-assistant` | KEEP |
| `AI-Shopping-Agent` | MERGE into shopguide |

---

## Archive (Not Core Business)

| Repo | Reason |
|------|--------|
| `endless-sky` | Fork of game |
| `orbiter` | Space sim fork |
| `CopilotForXcode` | Fork |
| `aethromoor-novel` | Creative writing |
| `avalon-world-building` | Creative |
| `avalon-manuscript` | Creative |
| `book-manuscripts` | Creative |
| `writing-projects` | Creative |
| `Omni-Heal-` | Old project |
| `my-hybrid-app` | Test app |
| `Replit.gt` | Replit test |
| `Repelit` | Replit test |
| `github-learning-projects` | Learning |
| `AI-Generated-Agents` | Experiments |
| `chat-archive-system` | Utility |
| `perplexity-memory-timeline` | Utility |
| `config` | Dotfiles |

---

## Utility (Keep but not products)

| Repo | Purpose |
|------|---------|
| `aws-lambda-simple-web-app` | Lambda examples |
| `dropbox-auto-organizer` | Automation tool |
| `visual-computer-kindle-ai` | Kindle tool |

---

## Execution Order

### Week 1: SCBE Consolidation
1. [ ] Merge `scbe-security-gate` into SCBE-AETHERMOORE
2. [ ] Merge `scbe-quantum-prototype` → `/src/pqc/`
3. [ ] Merge `pypqc` → `/python/pqc/`
4. [ ] Archive old SCBE_Production_Pack repos

### Week 2: AI Workflow Consolidation
1. [ ] Merge `forgemind-ai-orchestrator` best parts
2. [ ] Archive all old versions
3. [ ] Clean up AI-Workflow-Architect

### Week 3: Shopify Cleanup
1. [ ] Merge AI-Shopping-Agent into shopguide
2. [ ] Archive old Shopify tests

### Week 4: Archive Everything Else
1. [ ] Archive all creative writing repos
2. [ ] Archive all forks
3. [ ] Archive all experiments

---

## Result

**Before**: 47 repos, confusing
**After**:
- `SCBE-AETHERMOORE` → AI Governance product
- `AI-Workflow-Architect` → Orchestration product
- 3 Shopify app repos
- ~5 utility repos
- Everything else archived

**Total active repos**: ~10 instead of 47
