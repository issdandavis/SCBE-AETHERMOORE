# Model Collapse, Synthetic Data, and SCBE Training Provenance

Date: 2026-06-27
Status: source-backed research brief

## Research question

How should SCBE train on AI-generated material without collapsing into generic AI output, while preserving human voice, spelling/noise, tokenizer structure, and conlang/coding-system context?

## Bottom line

The danger is not "any synthetic data." The danger is **indiscriminate recursive training** where AI-generated output is mixed back in as if it were human ground truth.

SCBE's mitigation should be:

1. Keep human-origin text explicitly tagged.
2. Keep AI-origin text explicitly tagged.
3. Preserve human spelling/noise instead of over-normalizing it away.
4. Store corrections as paired annotations, for example `coool(cool)`.
5. Keep verified AI separate from unverified AI.
6. Preserve source/license/provenance.
7. Use tokenizer and conlang lanes as semantic structure, not decorative lore.
8. Score/curate synthetic examples before they enter training.

## Key evidence

### 1. Recursive AI-on-AI training can cause model collapse

Shumailov et al. describe model collapse as a degenerative process where models trained recursively on generated data lose the true underlying data distribution. The 2024 Nature paper states that indiscriminate model-generated data use can create irreversible defects and make tails of the original distribution disappear.

Sources:

- https://www.nature.com/articles/s41586-024-07566-y
- https://arxiv.org/abs/2305.17493

SCBE implication:

- Do not let AI-generated examples masquerade as human examples.
- Do not train on AI-only corpora.
- Track tails: misspellings, odd phrasing, rough notes, partial ideas, human hesitation, and weird project-specific terms.

### 2. Self-consuming loops can go bad, but curation changes the picture

The "Self-Consuming Generative Models Go MAD" line of work studies repeated training on generated data. Other work on self-consuming models with curated data argues that human/user curation can change stability outcomes.

Sources:

- https://arxiv.org/abs/2307.01850
- https://openreview.net/forum?id=cyv0LkIaoH

SCBE implication:

- Verified AI output can be useful.
- It must be curated, scored, tagged, and mixed with human/source-grounded data.
- Receipts and adventure/code assignment scores should decide whether AI output enters the corpus.

### 3. Genuine human interactions become more valuable as AI content spreads

The original "Curse of Recursion" abstract explicitly notes that genuine human interaction data becomes increasingly valuable when web data contains more model-generated content.

Source:

- https://arxiv.org/abs/2305.17493

SCBE implication:

- Issac's raw typed words, spelling errors, corrections, preferences, and voice guides are high-value training assets.
- Do not "clean" them into generic AI style before tagging.
- Keep `raw_user_text` and `corrected_reading` together.

## Human-noise preservation

Instead of normalizing:

```text
coool -> cool
```

Store:

```json
{
  "surface": "coool",
  "correction": "cool",
  "notation": "coool(cool)",
  "tags": {
    "source": ["user_original"],
    "confidence": ["verified_human"],
    "function": ["human_typo", "correction_pair"],
    "training": ["preserve_surface", "teach_likely_correction"]
  }
}
```

Why:

- The model sees real human typing.
- The model learns likely correction.
- The model does not overwrite the original.
- The tokenizer can learn both surface form and normalized form.
- Unknown words can be handled by context rather than erased.

## Unknown word handling

When a word is not known:

```json
{
  "surface": "aethredesk",
  "possible_corrections": ["AetherDesk"],
  "context_clues": ["browser", "home screen", "terminal", "AI workbench"],
  "decision": "project_term_or_typo",
  "action": "preserve surface and add bracketed canonical form"
}
```

Render:

```text
aethredesk(AetherDesk?)
```

The question mark means likely correction but not certain.

## Training tags to add

| Tag | Meaning |
|---|---|
| `human_typo` | User typed non-standard spelling. |
| `human_dialect` | Intentional user style/voice variation. |
| `correction_pair` | Surface form plus likely normalized form. |
| `canonical_form` | Preferred normalized project spelling. |
| `unknown_word` | Word not known to system. |
| `context_inferred` | Correction inferred from surrounding context. |
| `preserve_surface` | Do not replace raw word silently. |
| `ai_normalization` | AI-proposed correction, not original text. |

## Tokenizer/conlang role

SCBE tokenizer and conlang coding systems should help by splitting each token into layers:

```text
surface token:       aethredesk
canonical token:     AetherDesk
source token:        user_original
confidence token:    context_inferred
project token:       browser/workbench
conlang lane:        thalen/velmari for browser+signal, draumric for build/system
code role:           tool/product/runtime
```

That gives small models a structured bridge from messy human text to executable project context.

## Corpus policy update

Every training row should carry:

```json
{
  "provenance": "user_original | ai_output | verified_ai | human_external",
  "surface_preserved": true,
  "corrections": [],
  "confidence": "verified_human | verified_ai | unverified",
  "license": "if external",
  "source_refs": [],
  "tokenizer_lanes": [],
  "conlang_lanes": []
}
```

## What this prevents

- AI-only mirror training.
- Generic AI prose drift.
- Loss of human voice.
- Loss of rare project terms.
- Loss of spelling/noise tails.
- Confusing facts, feelings, hypotheses, and verified claims.
- Treating AI-generated research as human ground truth.

## What this enables

- Better small-LLM service following.
- User-voice preservation.
- More robust typo/context handling.
- Training examples that retain real human messiness.
- Cleaner release gates.
- Multi-layer book writing with visible provenance.

