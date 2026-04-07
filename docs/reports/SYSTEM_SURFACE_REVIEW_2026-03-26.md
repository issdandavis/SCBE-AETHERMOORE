# System Surface Review - 2026-03-26

## Scope

This review covered the local public-facing and evaluator-facing surfaces that currently shape first-contact trust for SCBE-AETHERMOORE:

- [README.md](C:/Users/issda/SCBE-AETHERMOORE/README.md)
- [docs/index.html](C:/Users/issda/SCBE-AETHERMOORE/docs/index.html)
- [docs/redteam.html](C:/Users/issda/SCBE-AETHERMOORE/docs/redteam.html)
- [docs/research/index.html](C:/Users/issda/SCBE-AETHERMOORE/docs/research/index.html)
- [docs/specs/SYSTEM_BLUEPRINT_v2_CURRENT.md](C:/Users/issda/SCBE-AETHERMOORE/docs/specs/SYSTEM_BLUEPRINT_v2_CURRENT.md)
- [tests/adversarial/test_adversarial_benchmark.py](C:/Users/issda/SCBE-AETHERMOORE/tests/adversarial/test_adversarial_benchmark.py)
- [scripts/research/verify_benchmark_suite.py](C:/Users/issda/SCBE-AETHERMOORE/scripts/research/verify_benchmark_suite.py)

## Executive summary

The system is more coherent than the public packaging. The highest-value corrective action is compression:

1. one product sentence
2. one benchmark story
3. one canonical architecture map
4. one eval-pack path
5. one hero mechanism

For the current public surface, that hero mechanism should be **null-space signatures** and the install/eval story should run through **Hydra / HydraArmor + the canonical eval pack**.

## Findings

### High

1. README had placeholder API walkthrough domains and mixed product, theory, and proof layers in one opening packet.
2. The red-team page pointed at a test-mode checkout URL instead of an honest live CTA.
3. Public 14-layer semantics were inconsistent across README, legacy architecture docs, and blueprint/spec surfaces.
4. The red-team page linked to a missing homepage anchor.

### Medium

1. Canonical domain strategy was split between `aethermoore.com` and GitHub Pages.
2. The homepage and red-team page behaved like disconnected funnels.
3. Benchmark proof paths existed in code, but not as one public eval pack.
4. Legacy docs still contain mojibake / corrupted box drawing and should not be treated as canonical first-contact surfaces.

### Low

1. Several legacy commercial/documentation links remain broader or more ambiguous than they need to be.
2. Some older architecture pages are still useful as history, but not as authority.

## Canonical benchmark/eval path

The current clean local evaluation spine is:

- [tests/adversarial/attack_corpus.py](C:/Users/issda/SCBE-AETHERMOORE/tests/adversarial/attack_corpus.py)
- [tests/adversarial/test_adversarial_benchmark.py](C:/Users/issda/SCBE-AETHERMOORE/tests/adversarial/test_adversarial_benchmark.py)
- [scripts/benchmark/scbe_vs_industry.py](C:/Users/issda/SCBE-AETHERMOORE/scripts/benchmark/scbe_vs_industry.py)
- [docs/research/BENCHMARK_VERIFICATION_2026-03-23.md](C:/Users/issda/SCBE-AETHERMOORE/docs/research/BENCHMARK_VERIFICATION_2026-03-23.md)

Recommended public reproduction commands:

```powershell
pytest tests/adversarial/test_adversarial_benchmark.py -v
python scripts/benchmark/scbe_vs_industry.py
Get-Content artifacts\benchmark\industry_benchmark_report.json
```

## Changes completed in this pass

### Public-surface fixes

- Rewrote the top of [README.md](C:/Users/issda/SCBE-AETHERMOORE/README.md) to:
  - lead with one product sentence
  - elevate null-space signatures
  - point to one eval spine
  - replace placeholder API base URLs with `$SCBE_BASE_URL`
- Updated [docs/index.html](C:/Users/issda/SCBE-AETHERMOORE/docs/index.html) so the homepage links directly to the red-team proof surface.
- Updated [docs/redteam.html](C:/Users/issda/SCBE-AETHERMOORE/docs/redteam.html) to:
  - use the primary domain as canonical
  - remove the test-mode checkout link
  - route to the eval pack and architecture overview
  - fix the broken internal CTA
- Updated [docs/research/index.html](C:/Users/issda/SCBE-AETHERMOORE/docs/research/index.html) to send traffic directly to:
  - architecture overview
  - eval pack
  - null-space signatures
- Updated [docs/static/polly-sidebar.js](C:/Users/issda/SCBE-AETHERMOORE/docs/static/polly-sidebar.js) and [docs/sitemap.xml](C:/Users/issda/SCBE-AETHERMOORE/docs/sitemap.xml) to reflect the new proof surfaces and primary domain.

### New docs spine

- [docs/research/architecture-overview.html](C:/Users/issda/SCBE-AETHERMOORE/docs/research/architecture-overview.html)
- [docs/research/eval-pack.html](C:/Users/issda/SCBE-AETHERMOORE/docs/research/eval-pack.html)
- [docs/research/null-space-signatures.html](C:/Users/issda/SCBE-AETHERMOORE/docs/research/null-space-signatures.html)
- [docs/eval/README.md](C:/Users/issda/SCBE-AETHERMOORE/docs/eval/README.md)
- [docs/eval/manifest.json](C:/Users/issda/SCBE-AETHERMOORE/docs/eval/manifest.json)
- [scripts/eval/run_scbe_eval.ps1](C:/Users/issda/SCBE-AETHERMOORE/scripts/eval/run_scbe_eval.ps1)

## Deferred / remaining work

1. Normalize or retire [docs/ARCHITECTURE.md](C:/Users/issda/SCBE-AETHERMOORE/docs/ARCHITECTURE.md) and any other legacy 14-layer maps that conflict with the canonical public map.
2. Replace broad or stale external links in older docs and markdown entrypoints.
3. Decide whether the hosted red-team sandbox stays manual-request, returns to self-serve checkout, or moves behind another product surface.
4. If public claims will continue to use `91 / 91` prominently, keep the eval pack and dataset links adjacent everywhere the claim appears.

## Authority order for public readers

For first-contact readers, use this order:

1. [README.md](C:/Users/issda/SCBE-AETHERMOORE/README.md)
2. [docs/research/architecture-overview.html](C:/Users/issda/SCBE-AETHERMOORE/docs/research/architecture-overview.html)
3. [docs/research/eval-pack.html](C:/Users/issda/SCBE-AETHERMOORE/docs/research/eval-pack.html)
4. [docs/research/null-space-signatures.html](C:/Users/issda/SCBE-AETHERMOORE/docs/research/null-space-signatures.html)
5. [docs/specs/SYSTEM_BLUEPRINT_v2_CURRENT.md](C:/Users/issda/SCBE-AETHERMOORE/docs/specs/SYSTEM_BLUEPRINT_v2_CURRENT.md)

Legacy architecture markdown with corrupted rendering should be treated as historical until normalized.
