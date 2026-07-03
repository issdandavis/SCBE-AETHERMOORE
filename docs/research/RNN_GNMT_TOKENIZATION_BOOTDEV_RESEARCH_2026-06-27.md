# RNN, GNMT, Tokenization, and SCBE Coding Trainer Research

Date: 2026-06-27
Status: source-backed research brief

## Research question

What should SCBE copy from RNN/GNMT sequence modeling, modern tokenization, semi-token prediction, and Boot.dev-style coding practice to build a verified coding trainer with an AI chat mentor?

## Bottom line

The strongest product is not a literal Boot.dev clone. It is an SCBE-native coding dojo:

```text
lesson path
  -> coding challenge
  -> local test runner
  -> AI mentor chat
  -> tokenizer/opcode/provenance receipt
  -> repair/reflection loop
  -> training row, if verified
```

Boot.dev supplies the useful product pattern: short hands-on exercises, game mechanics, projects, spaced repetition, and an AI mentor. RNN/GNMT supplies the sequence-to-sequence history: encode an input sequence, align against the relevant source parts, decode an output sequence, and verify the generated result. Tokenization supplies the exact substrate SCBE needs to preserve user text, conlang words, opcodes, spans, and training provenance.

## Key findings

### 1. RNN encoder-decoder gave sequence-to-sequence a practical shape

Cho et al. proposed an RNN Encoder-Decoder where one RNN encodes a symbol sequence into a fixed-length representation and another decodes it into another sequence. Bahdanau, Cho, and Bengio then attacked the fixed-vector bottleneck with attention: the decoder can soft-search relevant source positions while predicting target words.

SCBE implication:

- Treat a user/conlang phrase as a source sequence.
- Keep an explicit alignment map from source tokens to opcode/IR fields.
- Do not claim "understanding" unless the alignment and execution receipt survive checks.

### 2. GNMT is the concrete production bridge from RNNs to verified language tooling

The GNMT paper describes Google's production NMT system as deep LSTM encoder/decoder stacks with attention, residual connections, low-precision inference, wordpieces, and beam-search corrections such as length normalization and coverage penalty. It also reports that GNMT handled rare words with limited common subword units and reduced translation errors by an average of 60% versus Google's phrase-based production system on isolated simple sentences.

SCBE implication:

- Wordpieces/subwords are not decorative. They are the bridge between rare words and reliable sequence generation.
- Coverage matters. If a source token does not map into the output plan, the receipt should show the gap.
- Beam-like candidate generation is useful only when followed by verifier gates.

### 3. Full tokenization is a pipeline, not just a vocabulary

Modern tokenization has several separable steps:

```text
raw text / bytes
  -> source hash and byte span table
  -> Unicode/normalization policy
  -> pre-tokenization with offsets
  -> tokenizer model: BPE, Unigram, WordPiece, or word-level
  -> token ids plus token strings plus offsets
  -> post-processing / special tokens
  -> model prediction
  -> decode / detokenize
  -> round-trip and provenance checks
```

Hugging Face documents this as normalization, pre-tokenization, model, post-processing, and decoding. SentencePiece is important because it can train directly from raw sentences instead of assuming pre-tokenized word sequences. OpenAI's `tiktoken` describes BPE as reversible and lossless for converting tokens back into original text.

SCBE implication:

- Keep `surface_text` separate from `canonical_text`.
- Keep offsets and hashes so we can prove where a token came from.
- Keep semantic tokens separate from transport bytes.
- Keep conlang words, opcodes, host-language emission, and execution targets as separate fields.

Suggested SCBE token packet:

```json
{
  "surface": "bip'a",
  "canonical": "bip'a",
  "token_class": "conlang_opcode_word",
  "binds_to": ["CA:0x00:add"],
  "emits_to": ["python", "typescript", "go", "rust", "c", "julia", "haskell", "zig"],
  "executed_on": ["python", "rust"],
  "offset": [0, 5],
  "source_sha256": "...",
  "tokenizer_version": "scbe-tokenizer-v0"
}
```

### 4. Semi-token prediction maps to draft, verify, and repair

The user's "semi token prediction / retro thought" idea lines up with several existing research threads:

- Semi-autoregressive translation: keep global autoregressive structure but emit several local tokens in parallel.
- Speculative decoding: a cheaper draft model proposes multiple future tokens and the stronger model verifies them without changing the final distribution.
- Multi-token prediction: train the model to predict several future tokens from the same position using multiple heads.
- Reflexion and Self-Refine: agents use feedback from failed attempts to improve later attempts without necessarily changing weights.

SCBE interpretation:

```text
draft future tokens
  -> attach confidence and source coverage
  -> compile candidate IR
  -> run verifier/tests
  -> write retro note explaining why the draft passed or failed
  -> admit only verified rows into training
```

Honesty boundary:

- This is not proof of a new cognitive architecture yet.
- It is a strong product pattern: propose more than one token, verify after, preserve failure receipts, and use repair history as training material.

### 5. Boot.dev's current product pattern is a good template, but not something to copy literally

Boot.dev currently presents itself as a hands-on coding platform with Backend and DevOps paths, game-like curriculum, portfolio projects, an AI mentor named Boots, and Training Grounds with personalized challenges. Their Training Grounds page claims over 40,000 student-rated challenges, spaced repetition, three challenge types, custom instructions, XP, streaks, and quests.

SCBE should copy the pattern, not the brand/content/assets:

```text
Boot.dev-like mechanic       SCBE version
hands-on lesson              opcode/conlang coding lesson
course path                  forge path / tongue path / backend path
AI mentor                    local SCBE mentor chat
write-code challenge         runnable local test harness
fix-bug challenge            broken packet/code repair
interview chat               explain token/opcode/runtime reasoning
XP/streaks/quests            receipts, ranks, badges, verified gates
spaced repetition            retry queue from failed concepts
portfolio projects           shareable SCBE apps and language faces
```

## Product sketch: SCBE Forge

First version:

```text
left rail: path tree
center: lesson + code editor + tests
right rail: mentor chat + tokenizer receipt
bottom: run output, failing tests, provenance packet
```

Required modules:

- `courses`: lessons, challenge metadata, prerequisites, tags.
- `runner`: sandboxed test execution for Python first, then JS/Rust.
- `mentor`: chat that asks Socratic questions by default but can explain after failed attempts.
- `tokenizer`: shows source tokens, conlang tokens, opcode binding, emission targets, and execution targets.
- `spaced_review`: schedules failed concepts for later.
- `training_capture`: writes only verified human/AI rows with source, license, prompt, attempt, feedback, tests, and final result.

The mentor should be closer to Boot.dev's "help me understand" assistant than a free-answer bot:

```text
student asks
  -> mentor inspects current code/test/receipt
  -> mentor asks one targeted question
  -> if still blocked, gives a hint
  -> after run, writes a compact reflection row
```

For coding-agent behavior, use the Claude-style documented pattern: a tool-using assistant can return structured tool calls that the application executes, and Claude Code demonstrates the broader product surface of reading code, editing files, and running commands. For SCBE, keep the tool lane allowlisted and receipt-first.

## Training-data policy

Every completed exercise can become training data only if it passes gates:

```json
{
  "lesson_id": "forge.ca.add.001",
  "raw_user_text": "...",
  "attempt_code": "...",
  "mentor_messages": [],
  "tests": {"passed": true, "count": 6},
  "token_receipt": {},
  "provenance": "user_original_plus_verified_ai_feedback",
  "license": "local_user_project",
  "admit_to_training": true
}
```

Reject or quarantine rows when:

- tests fail
- source text is missing
- external content lacks a license
- mentor gave a final answer without showing the user's attempt
- conlang/opcode/emits/executes fields collapse into one claim

## First build target

Build one vertical slice:

```text
Lesson: CA add opcode
User writes: bip'a 3 4
Tokenizer binds: bip'a -> CA:0x00:add
Compiler emits: Python function
Runner executes: Python tests
Mentor explains: one hint at a time
Receipt records: binds_to, emits_to, executed_on, test result
Training row writes: only if verified
```

This gives the user the Boot.dev-style loop, the Claude-style coding companion, and the SCBE honesty firewall in one small app.

## Sources

- https://arxiv.org/abs/1406.1078
- https://arxiv.org/abs/1409.0473
- https://arxiv.org/abs/1609.08144
- https://research.google/blog/a-neural-network-for-machine-translation-at-production-scale/
- https://aclanthology.org/P16-1162/
- https://arxiv.org/abs/1808.06226
- https://huggingface.co/docs/tokenizers/en/pipeline
- https://github.com/openai/tiktoken
- https://arxiv.org/abs/1808.08583
- https://arxiv.org/abs/2211.17192
- https://arxiv.org/abs/2404.19737
- https://arxiv.org/abs/2303.11366
- https://arxiv.org/abs/2303.17651
- https://www.boot.dev/
- https://www.boot.dev/training
- https://www.anthropic.com/news/claude-3-5-sonnet
- https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview
- https://code.claude.com/docs/en/overview
- https://claude.com/claude-for-chrome
