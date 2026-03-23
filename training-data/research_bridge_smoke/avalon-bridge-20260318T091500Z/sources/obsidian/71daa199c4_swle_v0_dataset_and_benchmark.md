# SWLE v0 Dataset Schema and Benchmark Protocol

**Status**: Experimental scaffold  
**Date**: 2026-03-15  
**Scope**: Prepare multilingual ingest and first-pass evaluation before the six target language packs arrive.

## Purpose

This note turns the broader SWLE research idea into a falsifiable `v0` experiment. The core decision is to start from `phonemes` and phonological features, not raw letters. English and many other orthographies are too inconsistent for a letter-native deterministic model to be a stable first test.

The immediate goal is not to prove that spelling fully determines meaning. The `v0` goal is narrower:

1. Determine whether phoneme-level structured particles capture transferable semantic signal beyond tokenizer statistics.
2. Measure whether an interpretable local energy model improves low-resource transfer, concept retrieval, or affect prediction relative to character and tokenizer baselines.
3. Keep the representation auditable enough that failure modes are easy to inspect.

## v0 Claims

The experiment is allowed to claim only the following if supported by results:

- Phoneme-level structure contains measurable semantic and affective signal.
- A particle-style representation can act as an interpretable inductive bias.
- Local interaction energies can improve some tasks over naive character baselines.
- Learned particle projections may transfer across multiple languages better than language-specific memorization.

The experiment is not allowed to claim the following without much stronger evidence:

- Full deterministic semantics from spelling alone.
- Replacement of lexical semantics, syntax, or large language models.
- Lossless compression of all meaning from a tiny particle table.

## Data Package Layout

Recommended layout once the six languages are available:

```text
lexicons/
  swle_manifest.json
  rows/
    lang-01.jsonl
    lang-02.jsonl
    lang-03.jsonl
    lang-04.jsonl
    lang-05.jsonl
    lang-06.jsonl
schemas/
  swle/
    swle_manifest.schema.json
    swle_lexicon_entry.schema.json
experiments/
  swle_v0/
    example_experiment_config.json
```

Each JSONL row should represent one lexical entry aligned to a stable concept identifier when possible.

## Required Per-Entry Fields

Every row must include:

- `entry_id`: stable row identifier.
- `language.language_id`: stable language code used in this project.
- `forms.surface`: original orthographic form.
- `forms.normalized`: normalized spelling used for deduplication.
- `forms.phonemes_ipa`: phoneme sequence in IPA or a documented phoneme inventory.
- `concept.concept_id`: stable multilingual concept identifier.
- `concept.english_gloss`: human-readable anchor gloss.
- `concept.pos`: coarse part of speech.
- `provenance.dataset_id`: source dataset identifier.
- `provenance.license`: source license.

Strongly recommended fields:

- `forms.graphemes`
- `forms.syllables`
- `forms.morphemes`
- `concept.translation_set_id`
- `alignment.cognate_class_id`
- `semantic_targets.valence`
- `semantic_targets.concreteness`
- `semantic_targets.frequency_log10`
- `tokenizations[]`

## Ingest Rules

When the six languages arrive, normalize each language pack with these rules:

1. Preserve the original surface form exactly.
2. Add a normalized spelling field for dedupe and join operations.
3. Convert spelling to phonemes or IPA before training.
4. Keep tokenizer outputs, but store them as auxiliary views, not the primary representation.
5. Attach a stable `concept_id` or `translation_set_id` so cross-language retrieval can be scored.
6. Record confidence and source provenance for every phoneme sequence and semantic target.
7. Do not mix inferred labels with gold labels without an explicit provenance flag.

## Representation

The `v0` primitive is a phoneme with a feature vector:

```text
f(p) = [
  voiced,
  sonorant,
  continuant,
  nasal,
  approximant,
  lateral,
  stop,
  fricative,
  affricate,
  vowel,
  place,
  manner,
  height,
  backness,
  rounding,
  stress,
  syllable_role
]
```

The SWLE particle parameters are learned projections of these grounded features:

```text
m(p) = sigmoid(w_m · f(p) + b_m)
q(p) = tanh(w_q · f(p) + b_q)
s(p) = sigmoid(w_s · f(p) + b_s)
field(p) = softmax(W_field · f(p) + b_field)
```

This avoids hand-authoring an arbitrary particle table before there is evidence.

## Word Energy Model

Use a small local energy function first:

```text
E(word) =
  sum_i U(p_i) +
  sum_i V(p_i, p_{i+1}) +
  sum_b B(boundary_b)
```

Where:

- `U(p_i)` is a unary phoneme term based on `m`, `q`, `s`, and `field`.
- `V(p_i, p_{i+1})` is an adjacent pairwise interaction.
- `B(boundary_b)` captures syllable or morpheme boundary effects.

One practical parameterization is:

```text
U(p_i) = a_m m_i + a_q q_i + a_s s_i + a_f · field_i
V(p_i, p_j) = b_mm m_i m_j + b_qq q_i q_j + b_ss s_i s_j + field_i^T C field_j
```

Sentence or phrase composition should stay simple in `v0`:

```text
E(sequence) = sum_words E(word) + sum_adjacent_words G(word_i, word_{i+1})
```

Do not start with full PDE or field-theory machinery. First prove that the local energy terms outperform basic baselines on controlled tasks.

## Benchmark Tasks

### Task 1: Cross-Lingual Concept Retrieval

Goal: retrieve the correct aligned concept across languages from the learned word representation.

- Input: one lexical item in language A.
- Candidate set: aligned items in languages B-F.
- Primary metrics: `MRR@10`, `Recall@1`, `Recall@10`.
- Minimum requirement: every evaluated row must have `concept_id` or `translation_set_id`.

### Task 2: Valence Prediction

Goal: predict affective polarity from the lexical form representation.

- Input: one lexical item with phoneme sequence.
- Target: scalar `valence` in `[-1, 1]` or normalized `[0, 1]`.
- Metrics: `Spearman`, `Pearson`, `MAE`.
- Notes: use only rows with provenance-tagged affect labels.

### Task 3: Morphology Prediction

Goal: test whether the representation preserves morphophonological structure.

- Input: lexical item and representation.
- Targets: coarse `POS`, inflectional feature bundle, or derivational family label.
- Metrics: macro `F1`, exact-match accuracy for feature bundles.

### Task 4: Cognate or Etymon Clustering

Goal: test whether structure captures related form-meaning history.

- Input: lexical items with `cognate_class_id` or `etymon_id`.
- Metrics: `NMI`, `ARI`, cluster purity.
- Optional if etymological data is unavailable.

### Task 5: Semantic Nearest-Neighbor Quality

Goal: inspect whether nearest neighbors preserve meaning better than surface-only baselines.

- Input: lexical item embedding.
- Labels: shared `concept_id`, semantic domain, or expert relevance judgments.
- Metrics: `Precision@k`, `nDCG@k`.

## Baselines

Every SWLE run should be compared against:

1. `bag_of_char_ngrams`
2. `char_cnn` or character BiLSTM
3. `bpe_embedding` using the existing tokenizer outputs
4. `phonological_features_only` without particle projections
5. `fastText`-style subword baseline if a corpus is available

The key ablation is:

- `phonological_features_only` versus `SWLE local energy`

If SWLE cannot beat or clearly complement that baseline, the particle framing is not yet justified.

## Split Strategy

Run all three split families:

### Split A: Within-Language Random

- Stratified by part of speech and semantic domain.
- Purpose: basic sanity check.

### Split B: Leave-One-Language-Out

- Train on five languages, test on the sixth.
- Purpose: cross-lingual transfer and overfitting detection.

### Split C: Leave-One-Concept-Domain-Out

- Hold out semantic domains such as motion, body, social, color, or artifact.
- Purpose: evaluate compositional generalization rather than memorization.

If there is enough data, also add:

### Split D: Orthographic Noise Robustness

- Inject spelling variation or transliteration noise.
- Purpose: measure whether phoneme-first SWLE is more stable than tokenizer-first baselines.

## Success Criteria

The experiment clears `v0` only if all of the following are true:

1. SWLE beats the character baseline on at least three benchmark tasks.
2. SWLE is competitive with tokenizer baselines on within-language tasks.
3. SWLE beats tokenizer baselines on at least one transfer-oriented task, ideally leave-one-language-out retrieval or valence transfer.
4. Error inspection shows interpretable failure modes rather than opaque collapse.

If these are not met, the correct conclusion is:

`SWLE is an interesting structured prior, but not yet a superior semantic representation.`

## What To Do When the Six Languages Arrive

1. Create `lexicons/swle_manifest.json`.
2. Convert each source lexicon into one JSONL file matching `swle_lexicon_entry.schema.json`.
3. Fill tokenizer views in `tokenizations[]` for comparison, not supervision leakage.
4. Resolve or mint shared `concept_id` values.
5. Mark which labels are gold, inferred, or projected from another resource.
6. Run the first benchmark pass with the provided example config.

## Immediate Deliverables Prepared in This Repo

- [`docs/research/SWLE_V0_DATASET_AND_BENCHMARK.md`](/C:/Users/issda/SCBE-AETHERMOORE/docs/research/SWLE_V0_DATASET_AND_BENCHMARK.md)
- [`schemas/swle/swle_manifest.schema.json`](/C:/Users/issda/SCBE-AETHERMOORE/schemas/swle/swle_manifest.schema.json)
- [`schemas/swle/swle_lexicon_entry.schema.json`](/C:/Users/issda/SCBE-AETHERMOORE/schemas/swle/swle_lexicon_entry.schema.json)
- [`experiments/swle_v0/example_experiment_config.json`](/C:/Users/issda/SCBE-AETHERMOORE/experiments/swle_v0/example_experiment_config.json)
