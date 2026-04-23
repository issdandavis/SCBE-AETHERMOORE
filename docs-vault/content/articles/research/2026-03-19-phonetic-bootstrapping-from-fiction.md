# Phonetic Bootstrapping From Fiction: Using The Six Tongues Protocol as a Controlled Pronunciation Corpus

**Issac Davis**  
SCBE-AETHERMOORE research draft  
March 19, 2026

## Abstract

This article proposes a practical use for a published fictional language system: treat it as a controlled pronunciation corpus rather than as loose lore. The SCBE-AETHERMOORE project already contains deterministic token forms, canonical tongue names, and a full narrative manuscript built around those forms. Combined with standard phonetic references such as the IPA, CMUdict, and TIMIT-derived corpora, that gives a path toward a pronunciation-oriented lexicon for the Six Tongues that is more disciplined than ad hoc conlang notes and less noisy than web-scraped text.

## The corpus that already exists

Three things are already present in the repo.

First, there is a published long-form manuscript in [content/book/reader-edition/the-six-tongues-protocol-full.md](C:/Users/issda/SCBE-AETHERMOORE/content/book/reader-edition/the-six-tongues-protocol-full.md). That gives repeated canonical forms in narrative context.

Second, there is a deterministic token tutorial in [docs/sacred-tongue-tutorials.md](C:/Users/issda/SCBE-AETHERMOORE/docs/sacred-tongue-tutorials.md). Forms such as `zar'un`, `thul'ir`, `ael'esh`, and `keth'oth` are not arbitrary prose decorations. They are generated from fixed nibble-to-form mappings.

Third, there is an internal mathematical weighting and tongue contract in [docs/LANGUES_WEIGHTING_SYSTEM.md](C:/Users/issda/SCBE-AETHERMOORE/docs/LANGUES_WEIGHTING_SYSTEM.md). That means the language inventory is already tied to function, not only aesthetics.

Taken together, these materials create a controlled symbol system with:

- repeatable orthographic forms
- stable domain assignments
- reusable examples in story and tutorial settings

That is enough to begin phonetic bootstrapping.

## Why use external phonetic standards

If a fictional language is going to become useful for speech, voice rendering, or pronunciation-aware tooling, it needs to connect to real phonetic reference systems.

The International Phonetic Association maintains the IPA chart infrastructure and historical chart archive. Carnegie Mellon's CMU Pronouncing Dictionary provides a machine-readable English pronunciation resource with 39 ARPAbet phonemes and lexical stress markers. The Linguistic Data Consortium's TIMIT line of corpora was explicitly designed for acoustic-phonetic studies and automatic speech recognition evaluation, using phonetically rich sentences.

Those references matter because they separate three things that conlang projects often blur together:

- orthography
- pronunciation
- acoustic realization

SCBE already has orthography. It does not yet have a complete, benchmarked pronunciation lexicon.

## A workable method

The clean path is to build the Six Tongues phonetic layer in stages.

### Stage 1: Lexicon extraction

Extract all canonical tongue forms from:

- the published manuscript
- the sacred-tongue tutorials
- tokenizer outputs and test fixtures

This creates a source lexicon of stable spellings.

### Stage 2: Pronunciation normalization

Map each source form into:

- an IPA representation for human-readable phonetic inspection
- an ARPAbet representation for compatibility with existing speech tooling

The point is not to force the tongues to sound like English. The point is to make pronunciation explicit enough to synthesize, compare, and evaluate.

### Stage 3: Corpus discipline

Use the novel and supporting prose as style examples, but do not let the prose silently redefine pronunciation. A language corpus is more usable when canonical wordforms are stable and narrative variation sits on top of them rather than mutating them.

### Stage 4: Audio validation

Once a lexicon exists, the next layer is minimal speech data:

- word list recordings
- sentence list recordings
- contrast pairs for close phoneme decisions

That is where TIMIT-style thinking becomes useful. A phonetically rich evaluation set is better than a pile of beautiful but redundant voice lines.

## What the book contributes

The book matters because it shows how the forms behave in readable context. The phrase system is not buried in a spreadsheet. It is embedded in scenes, commands, and repeated narrative cues.

That makes it useful for two tasks:

- identifying high-frequency canonical forms
- collecting prosodic context for future voice rendering

In other words, the novel is not just lore. It is a constrained text environment.

## What is implemented versus proposed

Implemented in the repo today:

- deterministic spell-text examples
- canonical tongue names and domain assignments
- a long-form manuscript that repeatedly uses the core language inventory

Still proposed:

- a full IPA lexicon for the Six Tongues
- an ARPAbet-aligned pronunciation dictionary
- a recorded evaluation set
- benchmarked text-to-speech or forced-alignment experiments

That distinction is important. The honest claim is not that SCBE already has a phonetics stack. The honest claim is that it has unusually good raw materials for building one without relying on random web corpora.

## Research direction

The next serious step is to create a small canonical lexicon, maybe 250 to 500 core forms, and annotate each with:

- source location
- IPA
- ARPAbet
- stress pattern
- tongue/domain label

Once that exists, you can test whether generated speech stays consistent across narrators, engines, and future book volumes.

## Sources

### Official external sources

- International Phonetic Association historical chart archive: https://www.internationalphoneticassociation.org/content/historical-charts
- CMU Pronouncing Dictionary: https://www.speech.cs.cmu.edu/cgi-bin/cmudict?in=welcome
- LDC STC-TIMIT 1.0 / TIMIT reference: https://catalog.ldc.upenn.edu/LDC2008S03

### Internal SCBE sources

- [content/book/reader-edition/the-six-tongues-protocol-full.md](C:/Users/issda/SCBE-AETHERMOORE/content/book/reader-edition/the-six-tongues-protocol-full.md)
- [docs/sacred-tongue-tutorials.md](C:/Users/issda/SCBE-AETHERMOORE/docs/sacred-tongue-tutorials.md)
- [docs/LANGUES_WEIGHTING_SYSTEM.md](C:/Users/issda/SCBE-AETHERMOORE/docs/LANGUES_WEIGHTING_SYSTEM.md)
