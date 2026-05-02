# Agentic Coding Training Data

SCBE-AETHERMOORE agentic coding training corpus. Teaches models to use tools,
edit files, run tests, debug errors, and follow git workflows.

## Structure

| File | Source | Description |
|------|--------|-------------|
| `packet_traces.jsonl` | `PacketGraphRunner` | **Canonical.** Real plan→verify→merge runs; response field is the actual `MergeReport` / `GraphRunResult` JSON, not prose. Byte-deterministic. |
| `ambiguity_action_traces.jsonl` | Ambiguity-action simulator | Deterministic traces for turning messy user commands into repo-grounded actions, clarity gates, compact delegation packets, context-bloat recovery, tiny composable skill deltas, and residual temp-artifact cleanup. |
| `from_skills.jsonl` | SKILL.md files | *Legacy prose-style* tool-use pairs generated from skill definitions (kept for reproducibility — see "Prose vs Executable" below) |
| `seed_dataset.jsonl` | Synthetic | *Legacy.* 100+ multi-turn ReAct trajectories for common dev tasks |
| `*_scbe.jsonl` | Open datasets | R2E-Gym, CodeActInstruct, SWE-smith, AgentInstruct (reformatted) |
| `sessions/*.jsonl` | AetherBrowse | Real agent session logs from the runtime |

### Prose vs Executable

The earlier `generate_agentic_sft.py` corpus emitted hand-written tool-call prose
(`<tool_call>{"name": "X", "args": {"param": "value"}}</tool_call>` →
`Success: operation completed.`). That trains verbose chain-of-thought when the
runtime contract only needs a structured delta.

The new `generate_packet_traces_sft.py` runs each canonical seed packet through
`build_default_packet_graph()` and records the actual `MergeReport` and
`GraphRunResult` produced by the runner. Two pair categories:

  - `agentic-merge-verdict` — one per checkpoint; response is a `MergeReport` JSON
  - `agentic-packet-trace`  — one per run;        response is a `GraphRunResult` JSON

`metadata.packet_fingerprint` is recoverable from a real seed via
`recompute_fingerprint_from_metadata()`, which proves the trace came from a real
run rather than a synthesized string.

## Schema

All files follow SCBE training schema v3.0.0 with agentic extensions:

```json
{
  "id": "ag-tool-00001",
  "category": "agentic-tool-use",
  "messages": [
    {"role": "system", "content": "You are SCBE-Coder..."},
    {"role": "user", "content": "Add a new API endpoint"},
    {"role": "assistant", "content": "<think>\nI need to check existing patterns...\n</think>\n<tool_call>\n{\"name\": \"read_file\", \"args\": {...}}\n</tool_call>"},
    {"role": "tool", "content": "[read_file] file contents..."},
    ...
  ],
  "metadata": {
    "source": "scbe_aethermoore",
    "version": "3.3.0",
    "tongues": ["KO", "CA", "DR"],
    "layers": [1, 3, 7, 12, 14],
    "difficulty": "medium",
    "turn_count": 8
  }
}
```

## Special Tokens

Agentic coding uses these special tokens (added to tokenizer):

| Token | Purpose |
|-------|---------|
| `<tool_call>` / `</tool_call>` | Tool invocation |
| `<tool_result>` / `</tool_result>` | Tool response |
| `<think>` / `</think>` | Reasoning chain |
| `<observe>` / `</observe>` | Environment observation |
| `<plan>` / `</plan>` | Action plan |
| `<governance>` / `</governance>` | SCBE governance decision |
| `<execute>` / `</execute>` | Action execution |
| `<error>` / `</error>` | Error state |
| `<recover>` / `</recover>` | Recovery action |
| `<finish>` / `</finish>` | Session completion |
| `<read_file>` / `</read_file>` | File read |
| `<apply_diff>` / `</apply_diff>` | File edit |
| `<terminal>` / `</terminal>` | Shell command |
| `<browser>` / `</browser>` | Browser action |

## Generation Scripts

```bash
# Canonical: record real packet-graph runs as SFT (byte-deterministic)
python scripts/training/generate_packet_traces_sft.py

# Ambiguous user command -> repo-grounded action traces with clarity gates
python scripts/training/generate_ambiguity_action_sft.py --json

# Promotion gate: prove packet_traces.jsonl still matches the executable generator
python scripts/eval/score_packet_trace_sft.py --json

# Legacy prose-style generator (kept for reproducibility — prefer packet_traces above)
python scripts/training/generate_agentic_sft.py

# Build seed trajectories
python scripts/training/build_agentic_seed.py --count 200

# Ingest open datasets
python scripts/training/ingest_open_datasets.py --all --max-samples 5000

# Convert existing AetherBrowse sessions
python aetherbrowse/runtime/trajectory_logger.py convert \
    aetherbrowse/sessions/ training-data/agentic_coding/sessions/
```

## Training

```bash
# Using LLaMA-Factory with Unsloth
llamafactory-cli train config/model_training/agentic-coding-qlora.json

# Or direct Python
python scripts/training/finetune_qwen_coder_qlora.py \
    --config config/model_training/agentic-coding-qlora.json
```

## Curriculum Phases

1. **Learn** — Atomic skills from SKILL.md + seed trajectories
2. **Gym** — Diverse open dataset trajectories (augmented)
3. **Quiz** — Eval-only on held-out real tasks
4. **Remediation** — GRPO on failed quiz tasks with 14-layer rewards
5. **Cooldown** — Easy trajectory review

## License

MIT — Same as SCBE-AETHERMOORE
