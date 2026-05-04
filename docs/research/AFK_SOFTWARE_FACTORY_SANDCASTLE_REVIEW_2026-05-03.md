# AFK Software Factory / Sandcastle Review

Date: 2026-05-03

Source request:

- YouTube: `https://youtu.be/E5-QK3CDVQM?si=ChLJfbWaRjqYVyTH`
- Local evidence capture: `docs/research/evidence/youtube_E5-QK3CDVQM.json`

## Source Status

The YouTube page resolved to the title `I Open-Sourced My Own AFK Software Factory - YouTube`.

Transcript capture was not available in this local environment because `youtube_transcript_api` is not installed and the Hydra browser capture only returned generic YouTube page text. The concrete review below is therefore grounded in public source pages that match the video title/topic, especially Matt Pocock's open-source Sandcastle repository and the matching daily.dev share page.

Confidence:

- High confidence: Sandcastle repository features and public API surface.
- Medium confidence: the video topic maps to Sandcastle, because the public title and repository framing match.
- Low confidence: exact claims made verbally in the video, because no transcript was captured.

## What Sandcastle Actually Is

Sandcastle is a TypeScript library for orchestrating AI coding agents in isolated sandboxes. Its useful primitives are operational rather than decorative:

- `run()` as a single programmatic entrypoint for an agent task.
- Provider-neutral sandbox abstraction with Docker, Podman, Vercel, and custom providers.
- Branch/worktree strategies for direct-head, temporary merge-to-head, or explicit branch work.
- Prompt files and prompt arguments as reusable task packets.
- Lifecycle hooks for host and sandbox setup.
- Per-run logging and stream events.
- Completion signals to stop an agent loop cleanly.
- Commit capture and branch reporting as run outputs.
- Reusable sandboxes for implement-then-review loops on the same branch.

## Comparison To GeoSeal / SCBE Harness

Sandcastle is strong at:

- giving one clean TypeScript API to run coding agents;
- isolating agent execution from the host;
- making branch/worktree state part of the task lifecycle;
- persisting logs and commits from each run;
- supporting repeated agent rounds in one sandbox.

GeoSeal / SCBE is stronger at:

- governed provider routing and lane-switch signaling;
- AI-to-AI packet traces and provenance;
- Sacred Tongues / atomic tokenizer packet verification;
- multi-model council and Hydra-style gate review;
- Kaggle / Hugging Face training loops;
- security gates and deterministic promotion checks;
- domain-specific lanes like chemistry, coding, research, and writing quality.

The right move is not to copy Sandcastle whole. The right move is to absorb the clean execution contracts into GeoSeal's stronger governance stack.

## Borrow These Ideas

1. Provider-neutral sandbox contract

GeoSeal should expose a common task-runner shape for local, Docker, Podman, Vercel, Kaggle, Hugging Face Jobs, and no-sandbox diagnostic runs. Each provider should return the same result envelope.

2. Branch and worktree policy as first-class metadata

Every agent run should declare one of:

- `head`: direct local diagnostic only;
- `merge_to_head`: temporary branch merged after gate pass;
- `branch`: explicit review branch;
- `scratch`: disposable temp directory with compressed receipt only.

3. Completion signal contract

Standardize completion signals across Codex, Claude, Kimi, Ollama, Hugging Face, and future model lanes. GeoSeal can keep richer receipts, but every agent should be able to say `COMPLETE`, `HOLD`, `BLOCKED`, or `NEEDS_REVIEW` in a parseable packet.

4. Log and stream normalization

Sandcastle's per-run logging maps directly to SCBE's context vault and AI-to-AI channels. GeoSeal should normalize text chunks, tool calls, commits, tests, failures, and final packets into one event log.

5. Reusable sandbox for implement-then-review

This matches the user's "do not reset between rounds" idea. The same worktree should support:

- Round 1: implement.
- Round 2: review and repair.
- Round 3: compress lessons into a skill, dataset row, or harness rule.

## Do Not Borrow Blindly

Avoid cargo-culting these parts:

- A single Claude-first assumption. GeoSeal needs Codex, Claude, Kimi Code, Ollama, Hugging Face, DeepSeek, and local models.
- Sandbox-only framing. Some SCBE lanes are research, training, publishing, or chemistry verification, not just repo edits.
- Prompt-file-only context. GeoSeal should keep prompt files, but also route compact context packets, receipts, source manifests, and model comparison reports.
- Direct model output trust. GeoSeal should keep deterministic gates before merge, publish, or promotion.

## GeoSeal Upgrade Target

Add a `software-factory` harness mode with this contract:

```json
{
  "schema_version": "scbe_software_factory_run_v1",
  "task_id": "string",
  "provider": "local|docker|podman|vercel|kaggle|huggingface|no_sandbox",
  "agent_ref": "codex|claude|kimi|ollama:<model>|hf:<model>",
  "branch_strategy": "head|merge_to_head|branch|scratch",
  "prompt_packet": {
    "prompt_file": "string|null",
    "prompt_sha256": "string",
    "context_receipt": "string"
  },
  "signals": {
    "start": "string",
    "completion": "COMPLETE|HOLD|BLOCKED|NEEDS_REVIEW"
  },
  "outputs": {
    "log_path": "string",
    "commits": [],
    "changed_paths": [],
    "test_evidence": [],
    "gate_report": "string|null"
  },
  "governance": {
    "lane_signal": "string",
    "packet_fingerprint": "string",
    "promotion_decision": "PASS|HOLD|DENY"
  }
}
```

## Benchmark Use

Sandcastle gives GeoSeal a good public comparison target. A fair benchmark should test:

- setup time from clean repo;
- number of models/providers supported;
- repeatability of branch/worktree outputs;
- ability to run implement-then-review without losing context;
- deterministic completion signal parsing;
- security boundary for untrusted prompts;
- cost and local/free-model support;
- final artifact quality after gates.

Proposed scoring:

- 20 points: provider coverage.
- 20 points: sandbox/worktree isolation.
- 20 points: completion/log/commit evidence.
- 20 points: review and repair loop quality.
- 20 points: governance, security, and training-data capture.

Expected current standing:

- Sandcastle likely scores higher on clean TypeScript packaging and sandbox/worktree lifecycle.
- GeoSeal likely scores higher on multi-provider routing, governance, training evidence, and AI-to-AI packetization.
- GeoSeal needs a cleaner user-facing terminal mode and a standardized software-factory run envelope to win the public comparison.

## Next Implementation Slice

1. Add a GeoSeal software-factory result schema.
2. Wrap existing harness-provider matrix output into that schema.
3. Add a no-sandbox local dry-run provider for cheap tests.
4. Add a Docker/Podman/Vercel provider adapter only after the schema is stable.
5. Add a benchmark command that compares GeoSeal against Sandcastle's public feature checklist without requiring Sandcastle to be installed.

## Sources

- YouTube evidence capture: `docs/research/evidence/youtube_E5-QK3CDVQM.json`
- Sandcastle repository: `https://github.com/mattpocock/sandcastle`
- daily.dev post for the matching title: `https://app.daily.dev/posts/i-open-sourced-my-own-afk-software-factory-jrrd9bxuu`
