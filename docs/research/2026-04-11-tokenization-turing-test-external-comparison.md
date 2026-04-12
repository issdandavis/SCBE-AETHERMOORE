# Tokenization and Turing-Test Comparison

Date: 2026-04-11
Status: external-research comparison note
Scope: compare the full SCBE tokenization stack against outside research baselines, and explicitly separate human-interpretability questions from transport-tokenization questions.

## 1. Why this note exists

The SCBE tokenizer stack has been described in at least two different ways:

1. as a language-like surface that a human could inspect or reason about,
2. as a deterministic transport and feature-construction stack for bytes, ops, and governance.

Those are not the same benchmark family.

The right comparison is therefore split:

- semantic or langue-facing layer -> compare against human interpretability and imitation-style criteria,
- transport tokenizer and atomic feature stack -> compare against tokenization, token-free modeling, and reversible encoding baselines.

This note makes that split explicit and compares each layer against outside research instead of internal claims only.

## 2. The live SCBE stack being evaluated

The live internal split, already documented in `docs/specs/TOKENIZER_ATOMIC_STACK_FULL.md`, is:

1. Canonical langues and semantic meaning
2. SS1 / Sacred Tongues byte transport tokenizer
3. Atomic 8-vector op feature layer
4. Adaptive op-binary / inverse-complexity routing layer
5. Spiral Ring temporal geometry

For external comparison, the important boundary is:

- layers 1 and part of 2 can be judged by human-facing criteria,
- layers 2 through 4 should be judged primarily by encoding, reversibility, efficiency, and compositional utility.

## 3. Outside-source baselines

### 3.1 Turing's imitation-game baseline

Alan Turing's 1950 paper does not define tokenization quality. It defines a behavioral indistinguishability test for conversational intelligence.

Source:
- Alan Turing, "Computing Machinery and Intelligence" (1950)
- URL: https://www.csee.umbc.edu/courses/471/papers/turing.pdf

What matters here:

- the test is about whether an interrogator can distinguish machine from human through conversation,
- it is not about reversible byte encoding,
- it is not about latent feature quality,
- it is not about semantic compositionality of a transport alphabet by itself.

Conclusion:

- a classic Turing test is the wrong primary benchmark for the SS1 transport tokenizer,
- it is only partially relevant to the langue-facing semantic presentation layer.

### 3.2 SentencePiece baseline

SentencePiece is a standard reference for subword tokenization that is language-independent and reversible over text normalization settings.

Source:
- Taku Kudo and John Richardson, "SentencePiece: A simple and language independent subword tokenizer and detokenizer for Neural Text Processing" (2018)
- URL: https://aclanthology.org/D18-2012/

What matters here:

- fixed/learned subword inventory,
- language-independent preprocessing,
- practical reversibility for text pipelines,
- widespread deployment value.

Conclusion:

- SentencePiece is a valid comparison for practical tokenization workflows,
- but it operates on text segmentation, not on a six-tongue byte-transport alphabet with section policy and harmonic metadata.

### 3.3 ByT5 baseline

ByT5 is a direct byte-to-byte modeling baseline that avoids standard subword tokenization entirely.

Source:
- Linting Xue et al., "ByT5: Towards a token-free future with pre-trained byte-to-byte models" (2021)
- URL: https://arxiv.org/abs/2105.13626

What matters here:

- bytes can be a first-class modeling substrate,
- token-free or byte-level modeling is viable,
- standard tokenization is not mandatory for competitive language systems.

Conclusion:

- ByT5 is one of the most relevant external baselines for SCBE's byte transport layer,
- it validates the research direction of byte-level primitives,
- it does not by itself validate SCBE's tongue semantics or governance overlays.

### 3.4 CANINE baseline

CANINE is another tokenization-free baseline, using character-level inputs with learned downsampling and global modeling.

Source:
- Jonathan H. Clark et al., "CANINE: Pre-training an Efficient Tokenization-Free Encoder for Language Representation" (2021)
- URL: https://arxiv.org/abs/2103.06874

What matters here:

- character-level modeling without classical tokenizer dependency,
- efficiency corrections for long-sequence character processing,
- representation quality without fixed subword lexicons.

Conclusion:

- CANINE is relevant when comparing SCBE against tokenization-free encoding strategies,
- especially on the question: does a fixed symbolic transport alphabet buy anything beyond raw byte or character processing?

### 3.5 Charformer baseline

Charformer introduces soft learned subword structures on top of character inputs, rather than relying on a static tokenizer.

Source:
- Yacine Tay et al., "Charformer: Fast Character Transformers via Gradient-based Subword Tokenization" (2021)
- URL: https://arxiv.org/abs/2106.12672

What matters here:

- learned grouping over low-level symbols,
- dynamic subword induction,
- performance and efficiency tradeoff versus static token vocabularies.

Conclusion:

- Charformer is the right baseline for the question "should token structure be fixed or induced?",
- SCBE currently takes the opposite stance for transport: fixed, deterministic, audit-friendly mapping.

### 3.6 Linguistic steganography baseline

Linguistic steganography is a useful side comparison because SCBE's spell-text can look language-like while still functioning as structured transport.

Source:
- Siyu Zhang et al., "Provably Secure Generative Linguistic Steganography" (2021)
- URL: https://aclanthology.org/2021.findings-acl.268/

What matters here:

- human-readable output does not imply semantic transparency,
- language-like surface forms can be used as covert or structured carriers,
- readability and transport utility are separable properties.

Conclusion:

- this is the strongest outside-source comparison for the "looks like language, acts like transport" aspect of SCBE spell-text,
- it is still not the same thing as langue canon or human-facing explanation.

## 4. The split benchmark model

### 4.1 Layer A: semantic/langue-facing surface

Questions to ask:

- can a human consistently interpret the generated forms,
- does the mapping preserve intended semantic role,
- do cross-tongue relations communicate stable meaning,
- can the layer support teaching, review, and narrative/public presentation?

Closest outside family:

- Turing-style human-facing interpretation questions,
- human readability and semantic transparency work,
- linguistic steganography only as a caution that readable surface does not guarantee shared meaning.

### 4.2 Layer B: transport and atomic stack

Questions to ask:

- is the mapping deterministic,
- is it bijective or at least loss-bounded where required,
- does it cover arbitrary byte payloads,
- can it support section policy, audit, governance, and downstream feature construction,
- does it produce useful compositional features for higher layers?

Closest outside family:

- SentencePiece,
- ByT5,
- CANINE,
- Charformer,
- byte/character/token-free model literature.

## 5. Side-by-side comparison matrix

| System / paper | Primary unit | Learned or fixed | Reversible transport | Human-readable by design | Semantic layer built in | Main benchmark family |
|---|---|---:|---:|---:|---:|---|
| Turing 1950 imitation game | conversational behavior | N/A | No | Yes | Yes, but only at behavior level | human indistinguishability |
| SentencePiece | subword pieces | learned | practical text detokenization | No | No | subword tokenization |
| ByT5 | bytes | fixed input alphabet | yes at input representation level | No | No | byte-level language modeling |
| CANINE | characters | fixed low-level input + learned compression | not a transport codec | No | No | tokenization-free encoding |
| Charformer | characters + learned latent subwords | mixed | not a transport codec | No | No | learned subword induction |
| linguistic steganography | natural-language carrier text | generative | not normally exact byte transport | Yes | weak / task-specific | covert language transport |
| SCBE langue-facing layer | tongue semantics / canon phrases | fixed canon, potentially authored | not the primary goal | Yes, if surfaced carefully | Yes | semantic presentation / governance language |
| SCBE SS1 + Sacred Tongues transport | bytes split to tongue tokens | fixed | Yes | Partially, but not the main target | No | deterministic byte transport |
| SCBE atomic 8-vector layer | op rows + 8-float features | fixed scaffold | N/A | No | No | feature construction / control lattice |
| SCBE adaptive op-binary layer | op paths | adaptive | N/A | No | No | path-cost shaping / routing |

## 6. Main findings

### Finding 1

The classic Turing test is the wrong benchmark for the full SCBE tokenization process.

Reason:

- most of the SCBE stack is not trying to imitate human conversation,
- the byte transport and atomic layers should be evaluated like encoders, codecs, or feature systems,
- only the langue-facing semantic layer has a meaningful connection to human interpretability.

### Finding 2

SCBE's transport layer is closer to byte-level and tokenization-free research than to subword tokenization research, but it still occupies a distinct niche.

Reason:

- like ByT5 and CANINE, it takes low-level units seriously,
- unlike ByT5 and CANINE, it is explicitly deterministic, section-aware, and audit-oriented,
- unlike SentencePiece, it is not a learned segmentation scheme over natural text.

### Finding 3

SCBE's spell-text should be compared partly to linguistic steganography, but only at the transport-surface level.

Reason:

- both use language-like output as a structured carrier,
- but SCBE also claims an upstream semantic/canonical tongue layer,
- therefore the system must keep "surface carrier" and "semantic language" separated or it will drift.

### Finding 4

The strongest defensible external claim is not "SCBE passes a Turing test."

The strongest defensible claim is:

"SCBE combines a deterministic byte-level transport alphabet with a separate semantic canon layer and an atomic control-feature lattice, which places it closer to byte/character/token-free and structured-transport research than to standard learned subword tokenizers."

## 7. Recommended evaluation split for SCBE

### Semantic/langue-facing evaluation

Measure:

- human interpretation consistency,
- cross-tongue semantic stability,
- explanation quality,
- governance-language usability.

Do not call this a Turing test unless the system is actually being evaluated in imitation-game conditions.

### Transport evaluation

Measure:

- byte coverage,
- strict reversibility,
- corruption sensitivity,
- section-policy integrity,
- encoding length overhead,
- throughput,
- deterministic decode.

### Atomic/control evaluation

Measure:

- feature stability,
- collision behavior,
- downstream task utility,
- routing quality,
- remap stability under sustained use.

## 8. Bottom-line verdict

If the question is:

"Should the full SCBE tokenization stack be judged by a Turing-test comparison?"

The answer is:

- no for the transport and atomic layers,
- partially yes for the human-facing semantic/langue layer,
- and the correct full-stack evaluation is a split benchmark, not a single benchmark.

If the question is:

"What outside research family is the best comparison?"

The answer is:

- Turing 1950 for the human-facing interpretability boundary,
- SentencePiece for mainstream practical tokenizer comparison,
- ByT5 and CANINE for tokenization-free and byte/character-first modeling,
- Charformer for learned grouping over low-level units,
- linguistic steganography for the readable-carrier-vs-meaning distinction.

## 9. Practical next step

For repo work, the correct next artifact is a benchmark harness with three lanes:

1. semantic/langue review lane,
2. transport codec lane,
3. atomic/routing feature lane.

That will produce a real comparison instead of mixing incompatible evaluation goals.
