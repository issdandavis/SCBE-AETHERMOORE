# Frontier Small Models / Liquid AI Review

Date: 2026-05-03

Source request:

- YouTube: `https://youtu.be/fLUtUkqYHnQ?si=Q9BnKF55g6EkeY1V`
- Local evidence capture: `docs/research/evidence/youtube_fLUtUkqYHnQ.json`

## Source Status

The YouTube page resolved locally to the title `Everything I Learned Training Frontier Small Models - Maxime Labonne, Liquid AI - YouTube`.

Transcript capture was not available in this local environment. The local browser evidence only captured generic YouTube page text, so this review is grounded in the captured title plus public corroborating sources:

- Maxime Labonne slide deck: `https://www.slideshare.net/slideshow/everything-i-learned-training-frontier-small-models/286935677?nway-content_model=D`
- Liquid AI model page: `https://www.liquid.ai/models`
- Liquid AI LFM2.5-350M release post: `https://www.liquid.ai/blog/lfm2-5-350m-no-size-left-behind`
- LFM2 technical report: `https://arxiv.org/abs/2511.23404`
- Distil Labs tool-calling fine-tune report: `https://www.distillabs.ai/blog/fine-tuning-liquids-lfm25-accurate-tool-calling-at-350m-parameters/`

Confidence:

- High confidence: the talk topic, speaker, and date match the public slide deck.
- High confidence: Liquid AI's public claims about LFM2/LFM2.5 architecture, 32K context, edge deployment, and task-specific tuning.
- Medium confidence: exact verbal emphasis in the video, because no transcript was captured.

## Core Takeaway

Small models should not be treated as shrunken general chatbots. The useful pattern is:

1. Pick a narrow operational task.
2. Generate or collect task-specific examples.
3. Validate examples with deterministic gates.
4. Fine-tune a small model for that lane.
5. Use the small model as a cheap worker behind a stricter harness.

That maps cleanly onto GeoSeal. The small model is not the authority. The harness is the authority. The model is a fast lane worker that proposes commands, tool calls, classifications, or repair candidates inside a governed envelope.

## What Matters For SCBE

1. Task-specific beats generic

Liquid's public material frames edge models as memory-bound, latency-sensitive, and task-specific rather than general-purpose chatbots. For SCBE, that means we should train small workers for:

- GeoSeal command routing.
- GitHub issue and workflow triage.
- chemistry adapter verification.
- coding repair approval.
- active research source selection.
- release readiness checks.
- AI-to-AI handoff packet compression.

2. Hard gates are the training advantage

The Distil Labs report is especially relevant because it shows tool-call equivalence improving sharply after task-specific fine-tuning. Their metric is binary and inspectable. That is the right kind of target for SCBE:

- exact tool call equivalence;
- command family match;
- JSON schema validity;
- test pass/fail;
- chemistry valence/invariant checks;
- source receipt completeness;
- forbidden secret leakage absent.

Do not use reinforcement-style loops on vague prose quality first. Use them where rewards are mechanically checkable.

3. On-device and local-first matter

Liquid positions LFM2/LFM2.5 as efficient, deployable models for local, cloud, and hybrid use. SCBE should treat this as validation for the fleet shape:

- local Ollama / llama.cpp style workers for cheap repeated routing;
- paid or large models only for teacher, judge, or rare synthesis lanes;
- provider-pair signals when crossing local to remote lanes;
- no raw secret or private source exfiltration into third-party training calls.

4. Synthetic data only helps after filtering

The useful training recipe is not "generate lots of examples." It is:

- generate candidate examples from a larger teacher or existing traces;
- reject examples that fail schema, receipt, or domain gates;
- keep only examples with evidence fields and reproducible commands;
- train the small worker on the accepted rows;
- evaluate with held-out tool and command cases.

This is exactly where SCBE's chemistry manual verification, active research API usage, and industry command packs are strongest.

## Current Repo Alignment

Already aligned:

- `scripts/training_data/build_active_research_api_sft.py` teaches public source selection, receipts, and no secret exfiltration.
- `scripts/training_data/build_geoseal_industry_commands_sft.py` teaches command family routing for train, bench, release, GitHub, models, and factory lanes.
- `scripts/training_data/build_chemistry_adapter_sft.py` and `scripts/training_data/build_chemistry_adapter_sft_v1.py` teach deterministic chemistry adapter and verification behavior.
- `scripts/training_data/build_agentic_preference_math_dpo.py` already separates chosen/rejected examples for DPO/ORPO-style preference training.
- `docs/specs/AI_TRAINING_CONSOLIDATION_PLAN_2026-04-25.md` already says to use GRPO only where rewards are mechanically verifiable.

Gap:

- We still need a clean small-model worker profile that says "this model only routes or proposes, never decides promotion."
- We need public benchmark tasks for small model command routing and tool-call equivalence.
- We need a stable report format that compares base vs tuned small workers across repeated command and tool tasks.

## Training Decision

Use this video as a design signal for the next training round:

- Add small-model-specialist source rows to `active_research_api_usage_v1`.
- Keep the data lane open-source/public-source only.
- Use Kimi, Moonshot, Claude, or GPT-class models as teacher/judge only when explicitly approved, not as automatic data collectors.
- Evaluate small workers on exact JSON output, command choice, receipt completeness, and refusal boundaries.

## Benchmark Target

For a public GeoSeal benchmark, use a 100-point small-worker score:

- 20 points: valid JSON / schema compliance.
- 20 points: correct command or tool family.
- 20 points: exact required safety fields.
- 20 points: minimal context packet and source receipts.
- 20 points: stable behavior across two or more turns.

This gives SCBE a fair comparison surface against tool-calling and agentic CLI baselines without pretending a tiny model is a full coding agent.

## Implementation Recommendation

Next practical slice:

1. Rebuild active research SFT with a small-model specialist case.
2. Add it to the Kaggle mirror.
3. Keep the current chemistry and industry command gates in the same repair-v7 dataset.
4. Run the Kaggle round as a pipeline benchmark, not as final quality proof.
5. After the dataset stabilizes, train one small local worker profile for command routing and compare it against base model behavior.

## Sources

- YouTube evidence capture: `docs/research/evidence/youtube_fLUtUkqYHnQ.json`
- Slide deck: `https://www.slideshare.net/slideshow/everything-i-learned-training-frontier-small-models/286935677?nway-content_model=D`
- Liquid AI models: `https://www.liquid.ai/models`
- LFM2.5-350M release: `https://www.liquid.ai/blog/lfm2-5-350m-no-size-left-behind`
- LFM2 technical report: `https://arxiv.org/abs/2511.23404`
- Distil Labs tool-calling report: `https://www.distillabs.ai/blog/fine-tuning-liquids-lfm25-accurate-tool-calling-at-350m-parameters/`
