---
name: scbe-training-pipeline
description: Manage the SCBE SFT training data pipeline — merge sources, validate quality, track corpus statistics, generate new SFT pairs from codebase, trigger training runs, and push to HuggingFace. Use when working with training data, SFT generation, data quality, or model fine-tuning.
---

# SCBE Training Pipeline

End-to-end management of the Ouroboros training loop: codebase -> SFT data -> model training -> governance -> codebase.

## The Ouroboros Loop

```
Codebase (docs, tests, specs)
    |
    v
SFT Generation (scripts/generate_*.py)
    |
    v
Merge & Dedup (scripts/merge_and_upload.py)
    |
    v
Quality Gates (min length, legacy quota, track balance)
    |
    v
Upload to HuggingFace (issdandavis/scbe-aethermoore-training-data)
    |
    v
Fine-tune Model (3 specialty heads)
    |
    v
Model governs Codebase -> repeat
```

## SFT Source Files

Located in `training-data/`:

| Source | Content |
|--------|---------|
| `instruction-tuning/scbe_instructions.jsonl` | Core architecture Q&A |
| `knowledge-base/system_knowledge.jsonl` | System knowledge base |
| `knowledge-base/crypto_knowledge.jsonl` | Cryptography knowledge |
| `sft_notion.jsonl` | Notion export conversions |
| `sft_spiralverse.jsonl` | Spiralverse lore/canon |
| `sft_iseki.jsonl` | Iseki narrative data |
| `sft_kernel_manifest.jsonl` | Kernel manifest entries |
| `sft_codebase.jsonl` | Self-referential codebase docs |
| `sft_ouroboros.jsonl` | Ouroboros loop data |
| `sft_hydra_arch.jsonl` | HYDRA architecture data |

## Pipeline Operations

### 1. Merge All Sources
```bash
python scripts/merge_and_upload.py
```
- Loads all JSONL sources
- Deduplicates by instruction text
- Enriches metadata (track, source_type, quality)
- Applies legacy quota (max 15% legacy docstrings)
- Filters short responses (< 50 chars)
- Writes `sft_combined.jsonl` + `sft_combined_chat.jsonl`
- Splits into track files: `sft_system.jsonl`, `sft_governance.jsonl`, `sft_functions.jsonl`

### 2. Quality Validation
Check corpus health:
```python
# Track balance (aim for roughly equal)
tracks = {"system": N, "governance": N, "functions": N}

# Legacy ratio (should be <= 15%)
legacy_ratio = legacy_count / total_count

# Response quality metrics
avg_response_length  # aim for > 200 chars
min_response_length  # floor at 50 chars
dedup_ratio          # unique / total
```

### 3. Generate New SFT Pairs
When new code is written, generate SFT pairs from it:

```python
# For each new/modified Python file:
# 1. Extract docstrings, class/function signatures
# 2. Generate instruction: "What does {function_name} do?"
# 3. Generate response from docstring + code analysis
# 4. Tag with metadata: source_file, track, source_type
```

### 4. Upload to HuggingFace
```bash
python scripts/merge_and_upload.py --upload --repo-id issdandavis/scbe-aethermoore-training-data
```

### 5. Trigger Training Run
```bash
# Local 3-specialty training
python training/train_node_fleet_three_specialty.py \
    --epochs 12 \
    --embedding-dim 320 \
    --push-to-hub

# Federated artifact fusion
python training/federated_orchestrator.py \
    --manifests training/manifests/*.json \
    --output training/fused_release.json
```

### 6. Corpus Stats
Track these metrics over time:
- Total records, records per track, records per category
- Average response length, instruction diversity
- Legacy share percentage
- Deduplication ratio
- Category coverage (all 14 layers represented?)

## Training Tracks

| Track | Focus | Target Agent Role |
|-------|-------|-------------------|
| system | Architecture, math, narrative | LEADER |
| governance | Policy, safety, risk, FSGS | VALIDATOR |
| functions | Code, crypto, implementation | EXECUTOR |

## Key Files

| File | Purpose |
|------|---------|
| `scripts/merge_and_upload.py` | Main merge + upload pipeline |
| `training/train_node_fleet_three_specialty.py` | 3-head specialty training |
| `training/federated_orchestrator.py` | Multi-cloud artifact fusion |
| `training/doc_verifier.py` | Documentation verification |
| `training/kernel_manifest.py` | Kernel manifest generation |
| `training-data/` | All SFT source files |

## Quality Gates (from federated_orchestrator.py)

```python
Gates(
    min_quality=0.80,
    min_safety=0.95,
    max_latency_ms_p95=200,
    max_cost_per_1k_tokens=1.0,
)
```

## SFT Pairs from SaaS/Billing API Interactions

Every API call through the SaaS routes (`src/api/saas_routes.py`) is a natural source of training data. The request/response pairs demonstrate real usage patterns, governance decisions, and error handling.

### What to Capture

| API Endpoint | SFT Instruction Pattern | Track |
|-------------|------------------------|-------|
| `POST /saas/tenants` | "How do I provision a new tenant with plan X?" | system |
| `POST /saas/flocks` | "Create a flock with N agents for task Y" | functions |
| `POST /saas/flocks/{id}/governance` | "Evaluate this payload against governance rules" | governance |
| `GET /saas/flocks/{id}/metrics` | "What are the current metrics for flock X?" | system |
| `POST /saas/audit-report` | "Generate an audit report for tenant X" | governance |
| Error responses (401, 403, 429) | "What happens when rate limit / auth fails?" | governance |

### Generation Pattern

```python
import json
from datetime import datetime

def api_call_to_sft(method: str, path: str, request_body: dict, response_body: dict, status: int) -> dict:
    """Convert an API request/response pair into an SFT training record."""
    if status < 400:
        instruction = f"Using the SCBE SaaS API, {method} {path} with the following parameters: {json.dumps(request_body, indent=2)}"
        response = f"The API responds with status {status}:\n```json\n{json.dumps(response_body, indent=2)}\n```"
    else:
        instruction = f"What happens when you call {method} {path} with invalid or unauthorized parameters?"
        response = f"The API returns status {status} with error: {json.dumps(response_body)}"

    return {
        "instruction": instruction,
        "response": response,
        "metadata": {
            "source_type": "api_interaction",
            "track": "governance" if "governance" in path or status >= 400 else "functions",
            "endpoint": f"{method} {path}",
            "status_code": status,
            "generated_at": datetime.utcnow().isoformat(),
        }
    }
```

### Integration Points

1. **Middleware logger**: Add a FastAPI middleware that captures request/response pairs to a JSONL file at `training-data/sft_api_interactions.jsonl`.
2. **Merge pipeline**: Add `sft_api_interactions.jsonl` as a source in `scripts/merge_and_upload.py`.
3. **Governance-heavy data**: Error responses (auth failures, rate limits, plan violations) are high-value governance training data -- weight them 2x in the merge.
4. **Metering data**: The `MeteringStore` counters (`GOVERNANCE_EVALUATIONS`, `WORKFLOW_EXECUTIONS`, `AUDIT_REPORT_GENERATIONS`) provide aggregate stats for system-level SFT pairs.

### Privacy and Safety

- Strip API keys and tenant identifiers before writing SFT records.
- Replace real tenant names with synthetic placeholders (e.g., `tenant_alpha`, `tenant_beta`).
- Never include raw request headers in training data.
- Run governance scan on generated SFT pairs before merging into the corpus.
