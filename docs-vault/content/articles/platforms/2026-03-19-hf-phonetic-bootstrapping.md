# Phonetic Bootstrapping From Fiction: Building a Controlled Pronunciation Corpus from the Six Tongues

I’m treating a published fiction system as a possible pronunciation corpus instead of treating it as loose lore.

SCBE-AETHERMOORE already has three useful ingredients:

1. A long-form manuscript with repeated canonical tongue forms  
Book manuscript: https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main/content/book/reader-edition/the-six-tongues-protocol-full.md

2. Deterministic spell-text examples  
Tutorial: https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main/docs/sacred-tongue-tutorials.md

3. A tongue weighting contract that keeps the language inventory tied to function  
Weighting doc: https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main/docs/LANGUES_WEIGHTING_SYSTEM.md

That is enough to propose a disciplined pronunciation build.

## Why this is interesting

Most conlang work stays trapped between vibe and notation. The Six Tongues corpus is different because the orthographic forms are already constrained by deterministic examples.

For example, the tutorial already contains stable forms like:

- `zar'un`
- `thul'ir`
- `ael'esh`
- `keth'oth`

That means we are not starting from arbitrary fantasy prose.

## The external phonetics baseline

Three external references make this buildable:

- The International Phonetic Association maintains the IPA chart infrastructure and chart history.
- CMUdict maps words to pronunciations and uses a 39-phoneme set with lexical stress markers on vowels.
- TIMIT was designed for acoustic-phonetic studies and automatic speech recognition evaluation; STC-TIMIT is the telephone version of TIMIT.

Official sources:

- IPA historical charts: https://www.internationalphoneticassociation.org/content/historical-charts
- CMUdict: https://www.speech.cs.cmu.edu/cgi-bin/cmudict?in=welcome
- TIMIT/STC-TIMIT reference: https://catalog.ldc.upenn.edu/LDC2008S03

## Practical build path

The practical path is:

1. Extract canonical Six Tongue forms from the manuscript, tutorials, and tokenizer outputs.
2. Assign each form an IPA transcription.
3. Add an ARPAbet version for compatibility with existing speech tooling.
4. Build a small evaluation set of word lists, short phrases, and contrast pairs.

The claim here is not that SCBE already has a finished phonetics stack.

The claim is narrower:

The project already has unusually good raw materials for building a pronunciation-aware lexicon without relying on random web text.

## What is implemented versus proposed

Implemented:

- deterministic spell-text examples
- canonical tongue names and domain assignments
- a narrative corpus with recurring forms

Proposed:

- a full IPA lexicon
- an ARPAbet-aligned pronunciation dictionary
- recorded evaluation prompts
- benchmarked voice or alignment experiments

If you’re working on TTS, forced alignment, or pronunciation-aware conlang tooling, that is the interesting boundary here.
