# RNN, GNMT, Tokenization, Retro-Thought, and AetherDesk Academy Research Brief

Date: 2026-06-27
Scope: Convert the user request into an actionable product/research plan for a Boot.dev-like AetherDesk coding academy with an AI sidekick, compile-gated coding lessons, and training traces.

## One-sentence answer

Build our version as a verified coding dojo: Boot.dev-style paths and challenges, Claude-Artifacts-style side panel, Claude-Code/computer-use-style agent controls, SCBE compiler/conlang/tokenizer lanes, and a receipt pipeline where every AI suggestion must compile/test or become training data for repair.

Do not clone Boot.dev's brand, text, art, lesson content, pricing, or source. Clone the functional pattern: map, lessons, quizzes, CLI submitter, mentor sidekick, progress/XP, and compiler/test receipts.

## Research findings

### 1. RNN and GNMT matter because they prove sequence-to-sequence translation can be a real production system

Established facts:
- RNN encoder-decoder models encode an input sequence and decode an output sequence. Cho et al. introduced an RNN Encoder-Decoder trained to maximize conditional target-sequence probability and showed it learned meaningful phrase representations.
- Bahdanau attention fixed the fixed-vector bottleneck by letting the decoder search/source-align relevant parts of the input while generating target words.
- GNMT put the full idea into production scale: deep LSTM encoder/decoder, attention, residual connections, low-precision inference, WordPiece/subword handling for rare words, and beam search with length/coverage controls.
- Transformers later replaced recurrence for many sequence tasks because attention-only architectures parallelize better, but RNN-style state is still useful for streaming progress, lesson state, and tutoring memory.

Product translation:
- AetherDesk Academy should treat every learner/code action as sequence transduction: user intent + lesson state + files + test logs -> next action/code patch/explanation.
- Attention is the alignment layer: connect words/conlang tokens to code spans, test failures, compiler errors, and UI actions.
- RNN-style recurrence is still useful outside the core LLM: maintain a compact per-lesson state machine and progress memory without needing the whole chat history forever.

### 2. Full tokenization process for our system

Canonical pipeline:
1. Text boundary: read UTF-8/UTF-16/BOM safely, normalize line endings, preserve user spelling where useful.
2. Raw text and provenance tags: mark user-original, AI-output, verified fact, unverified idea, code, test, tool output, and compiler receipt.
3. Pre-tokenization or raw-sentence tokenization: classic tokenizers split first; SentencePiece can train directly from raw sentences.
4. Subword vocabulary learning: BPE/WordPiece/Unigram convert rare words into smaller reusable units.
5. Byte fallback: byte-level BPE makes every UTF-8 string encodable, useful for spelling errors, conlangs, code symbols, and weird user text.
6. ID encoding: text -> token IDs plus special tokens, masks, position info, and segment/provenance channels.
7. Decode/detokenize: token IDs -> text, with receipt metadata preserved outside plain text.
8. SCBE extension: sidecar channels map tokens to language face, conlang lane, opcode, compiler target, proof level, and source provenance.

Design rule for us:
- Do not train on plain text alone. Store `(surface_text, normalized_text, token_ids, byte_span, provenance_tags, code_face, compile_receipt, source_url_or_user_id)`.
- Preserve human typos with correction sidecars, e.g. `claoimed -> claimed`, instead of overwriting the human signal.
- Use byte fallback for everything unknown, but promote recurring useful chunks into Rosetta/lexicon entries after review.

### 3. Semi-token prediction and retro-thought should be verifier-driven, not blind generation

Established facts:
- Non-autoregressive translation predicts outputs in parallel for speed, trading some quality for latency.
- Speculative decoding drafts multiple future tokens with a faster model and verifies with the main model, preserving the target model's distribution when done exactly.
- Medusa-style heads predict multiple future tokens in parallel without a separate draft model, then verify candidate continuations.
- Self-Refine, Reflexion, ReAct, and Tree-of-Thoughts show a durable pattern: generate, act, observe feedback, reflect, revise, and sometimes branch/backtrack.

Product translation:
- Our "semi-token prediction" is a lesson/IDE accelerator: draft possible next code chunks, but only accept chunks that pass compile/test/gate checks.
- Our "retro thought" is not mystical hidden thinking. It is saved external reflection: attempt -> compiler/test output -> diagnosis -> patch -> passing receipt.
- This generates training data safely because failed attempts are labeled failed, not mixed into the successful-answer corpus.

### 4. Boot.dev pattern worth copying functionally

Observed official/product facts:
- Boot.dev markets itself as a game-like coding curriculum focused on writing lots of code, backend/devops paths, portfolio projects, progress, community, and interactive challenges.
- Boot.dev has an AI mentor named Boots positioned as Socratic help, not direct answer dumping.
- Boot.dev has an official CLI used to submit lessons/challenges, authenticate, configure base URLs for HTTP tests, and support lesson workflows.

AetherDesk version:
- Home screen map: paths, worlds, challenge nodes, daily streak, proof badges.
- Lesson panel: story prompt, concept, objective, starter files, tests, terminal, browser preview.
- AI Pal: asks Socratic questions by default, can inspect compiler/test logs, can suggest a patch only after the learner requests it, and can execute only through allowlisted tool lanes.
- Submitter CLI/API: `aether lesson run`, `aether lesson submit`, `aether lesson receipt`, `aether lesson explain`.
- Training recorder: every run writes a compact trace row for future AI training.

### 5. Claude/Anthropic patterns worth copying functionally

Verified official primitives:
- Artifacts: a dedicated window to see, iterate, and build code/documents/visualizations while chatting.
- Computer use: screenshot plus mouse/keyboard desktop interaction, but Anthropic explicitly treats it as beta and riskier around the internet.
- Claude Code: local coding agent that reads codebases, edits files, runs terminal commands, and asks permission before risky changes.

Unverified/ambiguous item:
- I did not find a stable first-party source for a feature literally named "Claude Pal". The closest useful product pattern is the combination of Artifacts + Claude Code + computer use + recent reported collaborative/team-agent patterns. Treat "Pal" as our own product name/pattern, not as a sourced Anthropic feature.

## AetherDesk Academy architecture

### Core surfaces

1. `academy-web`: Boot.dev-style map, lessons, quizzes, XP, badges, receipts.
2. `academy-runtime`: sandboxed runner for Python/JS/Go/Rust/SCBE compiler lanes.
3. `academy-pal`: AI mentor sidecar with modes: hint, explain, inspect, patch, test, reflect.
4. `academy-cli`: local submitter similar in role to Boot.dev CLI, but Aether-native.
5. `academy-traces`: training recorder that emits JSONL rows.
6. `academy-rosetta`: lexicon/promoter for unknown conlang/code/token chunks.

### Lesson schema MVP

```json
{
  "id": "py.variables.001",
  "title": "Variables as inventory slots",
  "path": "python-foundations",
  "world": "starter-island",
  "objective": "Make the function return the player name.",
  "concepts": ["variable", "return", "string"],
  "starter_files": [{"path": "main.py", "content": "def player_name():\n    pass\n"}],
  "tests": [{"kind": "pytest", "command": "python -m pytest -q"}],
  "hints": ["What value should the function hand back?", "Which keyword returns a value?"],
  "ai_pal_policy": {"default": "socratic", "patch_requires_user_request": true},
  "training_tags": ["human-learning", "compile-gated", "python"]
}
```

### Training trace row MVP

```json
{
  "trace_id": "uuid",
  "lesson_id": "py.variables.001",
  "actor": "human|ai_pal|system",
  "input_text": "user attempt or prompt",
  "files_before_hash": "sha256",
  "action": "edit|run|hint|submit|reflect",
  "tool_result": {"exit_code": 1, "stdout_tail": "...", "stderr_tail": "..."},
  "reflection": "why it failed or passed",
  "files_after_hash": "sha256",
  "verdict": "pass|fail|blocked|clarify",
  "provenance": {"human_original": true, "ai_generated": false, "source_urls": []}
}
```

### AI Pal modes

- `Socratic`: asks one targeted question, no code patch.
- `Explain`: explains the failing test/compiler error in plain language.
- `Inspect`: reads current lesson files and test output, no edits.
- `Patch`: proposes a minimal diff; user must accept.
- `Run`: executes allowlisted tests only.
- `Reflect`: writes a compact failure/success lesson for training traces.

### Tokenizer/Rosetta integration

- Unknown chunk enters byte fallback and gets logged.
- If repeated and useful, it becomes a candidate lexicon entry.
- Human can approve: surface spelling, corrected spelling, conlang binding, opcode binding, source/provenance, examples.
- Once approved, it becomes a Rosetta token and can be used by lessons/macros.

## Build backlog

### Phase 0: Repo-local design artifacts

- [x] Save this research brief.
- [ ] Add `docs/specs/AETHERDESK_ACADEMY_MVP.md` from this brief.
- [ ] Add `schemas/academy_lesson.schema.json`.
- [ ] Add `schemas/academy_trace.schema.json`.

### Phase 1: MVP shell

- [ ] Create `apps/aetherdesk-academy` or plug into existing AetherDesk web shell.
- [ ] Build home map with 3 hardcoded lessons.
- [ ] Build lesson page: prompt, editor, test output, AI Pal panel.
- [ ] Build local API: run tests in sandbox/allowlisted profiles only.
- [ ] Write receipts for every run.

### Phase 2: AI Pal

- [ ] Implement rule-based pal first: hints, explain test output, no model required.
- [ ] Add local/remote LLM adapter with strict mode gates.
- [ ] Add "patch requires user accept" and "run requires allowlisted command".
- [ ] Add reflection writer for trace rows.

### Phase 3: Training data

- [ ] Emit JSONL traces for all lesson interactions.
- [ ] Split human, AI, system, tool, source, test output channels.
- [ ] Add compile/test verdict labels.
- [ ] Add typo/correction sidecars.
- [ ] Add held-out lesson split for validation.

### Phase 4: Semi-token / retro-thought experiments

- [ ] Draft multiple next-code candidates.
- [ ] Verify candidates through compile/test gate.
- [ ] Accept only passing candidates or ask clarify.
- [ ] Store rejected candidates as failed examples, not positive training rows.
- [ ] Compare pass@1/pass@k against baseline pal.

## Honest constraints

- Boot.dev is a competitor/reference, not a code/content source.
- "Claude Pal" is not verified as a first-party feature name; use our own "AI Pal" language.
- Computer-use agents are risky on the open internet; use browser/desktop actions only through bounded lessons and allowlisted commands.
- Training traces must be storage-bounded: keep compact receipts and hashes, not full session dumps forever.

## Sources

- GNMT paper: https://arxiv.org/abs/1609.08144
- Bahdanau attention NMT: https://arxiv.org/abs/1409.0473
- Cho RNN Encoder-Decoder / GRU: https://arxiv.org/abs/1406.1078
- Transformer: https://arxiv.org/abs/1706.03762
- BPE for rare words: https://arxiv.org/abs/1508.07909
- SentencePiece: https://arxiv.org/abs/1808.06226
- Speculative decoding: https://arxiv.org/abs/2211.17192
- Non-autoregressive NMT: https://arxiv.org/abs/1711.02281
- Medusa: https://arxiv.org/abs/2401.10774
- Self-Refine: https://arxiv.org/abs/2303.17651
- Reflexion: https://arxiv.org/abs/2303.11366
- ReAct: https://arxiv.org/abs/2210.03629
- Tree of Thoughts: https://arxiv.org/abs/2305.10601
- Boot.dev homepage: https://www.boot.dev/
- Boot.dev CLI: https://github.com/bootdotdev/bootdev
- Boot.dev pricing/features: https://www.boot.dev/pricing
- Anthropic computer use announcement: https://www.anthropic.com/news/3-5-models-and-computer-use
- Anthropic computer use docs: https://platform.claude.com/docs/en/agents-and-tools/tool-use/computer-use-tool
- Anthropic Artifacts: https://claude.com/blog/artifacts
- Claude Code product page: https://claude.com/product/claude-code
