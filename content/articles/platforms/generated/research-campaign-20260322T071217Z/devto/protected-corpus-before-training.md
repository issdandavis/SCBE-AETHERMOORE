# Do Not Train on Raw Ops Logs: Build a Protected Corpus First

**By Issac Davis** | March 21, 2026

---

## Abstract

The fastest way to poison a training pipeline is to confuse “useful internal data” with “safe training data.” SCBE’s current privacy lane is important because it stops making that mistake. The repo now draws a hard line: reversible replacement is pseudonymization, not de-identification, and synthetic training should come from the protected layer rather than from raw operational logs.

## The key distinction the repo already makes

The privacy blueprint says this plainly: if the data can be decoded with a key, it is not de-identified. It is pseudonymized or tokenized. That line matters because it kills a common excuse. People often say data is “anonymized” when what they really mean is “we renamed the identifiers and hoped that was enough.”

SCBE does not need to play that game. It already has the right framing:

- protected corpus first
- synthetic generation second
- audit before publish

That is not philosophy. It is the only way to keep the training lane from leaking private operator context.

## What the code backs up

The privacy lane is not only a note. It is backed by three distinct surfaces.

First, `scripts/build_protected_corpus.py` exists to ingest notes and training rows, detect sensitive patterns, and replace them through a vault adapter.

Second, the builder is intentionally bounded. It includes a novelty-aware cycle guard and a max-cycle cap so the pipeline does not wander forever in non-productive loops. That matters because privacy prep can easily become one of those systems that claims to be “smart” while just spinning.

Third, `src/security/privacy_token_vault.py` explicitly implements a Windows-first reversible token vault for privacy-preserving pseudonymization. That is the right word and the right boundary.

## The workflow that should exist

The minimal safe workflow looks like this:

```bash
python scripts/build_protected_corpus.py --help
python scripts/privacy_leakage_audit.py --help
python scripts/programmatic_hf_training.py --dry-run
```

The important thing is the order:

1. build the protected layer
2. audit for leakage
3. only then promote toward Hugging Face or downstream training

That ordering is what turns privacy from a promise into a gate.

## Why this matters for synthetic data

The repo’s privacy blueprint already points in the right direction: publish synthetic conversations, method registries, and manifests, not raw reversible data. That is the usable compromise. You do not need to destroy the private source layer to build good training data. You need to keep it out of the public model lane and force a separate audited synthetic layer in between.

This also makes the training data easier to reason about later. Once the protected corpus exists as a real intermediate representation, it becomes possible to score leakage, extractiveness, and provenance without arguing about what happened after the fact.

## What is implemented versus proposed

Implemented now:

- privacy blueprint and policy framing
- protected-corpus builder
- reversible token vault
- privacy audit lane

Still not finished:

- mature synthetic conversation generation on top of the protected layer
- broader adversarial leakage evaluation
- repeatable publish gates that every remote push must pass

That is enough to say the privacy lane is real. It is not enough to say the system is finished.

## Why this should stay non-negotiable

Training quality does not justify privacy shortcuts. If the raw logs are too sensitive to publish, they are too sensitive to train on directly unless the whole downstream model is kept in the same protection regime. The better long-term move is what the repo is already converging on: use the private material to build protected and synthetic layers, then train on the audited output.

That is slower than dumping raw data into a training run, but it is also the difference between a system that can scale and a system that becomes unusable the second you care about governance.

## Sources

- `docs/research/2026-03-21-synthetic-data-privacy-blueprint.md`
- `scripts/build_protected_corpus.py`
- `scripts/privacy_leakage_audit.py`
- `src/security/privacy_token_vault.py`

---

## Why this article is code-backed

The fastest way to poison a training pipeline is to confuse “useful internal data” with “safe training data.” SCBE’s current privacy lane is important because it stops making that mistake. The repo now draws a hard line: reversible replacement is pseudonymization, not de-identification, and synthetic training should come from the protected layer rather than from raw operational logs.

## Code References

- `docs/research/2026-03-21-synthetic-data-privacy-blueprint.md`
  Public repo link: https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main/docs/research/2026-03-21-synthetic-data-privacy-blueprint.md
- `scripts/build_protected_corpus.py`
  Public repo link: https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main/scripts/build_protected_corpus.py
- `scripts/privacy_leakage_audit.py`
  Public repo link: https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main/scripts/privacy_leakage_audit.py
- `src/security/privacy_token_vault.py`
  Public repo link: https://github.com/issdandavis/SCBE-AETHERMOORE/blob/main/src/security/privacy_token_vault.py

## Repro Commands

```bash
python scripts/build_protected_corpus.py --help
python scripts/privacy_leakage_audit.py --help
python scbe.py colab review --json
```
