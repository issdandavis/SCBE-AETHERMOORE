# Elastic/Funnel Hashing Research Brief

Date: 2026-06-14

## Question

What should SCBE copy from the Krapivin/Farach-Colton/Kuszmaul open-addressing work before wiring a bijective hash into the tokenizer and memory lanes?

## Key Findings

1. The primary source is "Optimal Bounds for Open Addressing Without Reordering" by Martin Farach-Colton, Andrew Krapivin, and William Kuszmaul, posted to arXiv on 2025-01-04. It studies open-addressed hash tables where inserted items are not later reordered.

2. The paper separates two constructions:
   - Elastic hashing: non-greedy. It can probe far into a sequence during insertion, then place the item earlier/elsewhere so search probe complexity stays low.
   - Funnel hashing: greedy. It uses geometrically decreasing levels plus a special overflow area and disproves Yao's greedy-conjecture direction.

3. The current local `python/scbe/elastic_bijective_hash.py` is not the paper's elastic algorithm. It is a reversible-mix, double-hashing open-addressed map. That is still useful as a deterministic bijective-memory primitive, but it should be renamed/scoped honestly unless the real multi-array batch construction is implemented.

4. For SCBE tokenizer work, the safe copy is the invariant pattern, not the exact theorem yet:
   - reversible key scramble;
   - full-cycle probe orbit;
   - exact item/value storage for lossless round-trip;
   - deterministic schema seed so modes/scales can offset the same base language.

5. The next real implementation should be a two-track module:
   - `BijectiveDoubleHashMap`: production-safe, tested now, deterministic and reversible where intended.
   - `ElasticFunnelPrototype`: research implementation of the paper's subarray/batch/funnel structure, benchmarked separately before it is used in tokenizer hot paths.

## Implementation Recommendation

Do not wire the current file directly into the tokenizer under the name "elastic hashing." First rename it or adjust the docstring to "Krapivin-inspired bijective double hashing." Then add a second prototype file that follows the paper:

1. Partition the table into subarrays/levels.
2. Generate a deterministic two-dimensional probe sequence per key.
3. Preserve insertion/search probe distinction in metrics.
4. Add benchmarks at 90%, 99%, 99.9%, and 99.99% load.
5. Gate tokenizer adoption on round-trip tests and probe-tail tests.

## Sources

- Farach-Colton, Krapivin, Kuszmaul, "Optimal Bounds for Open Addressing Without Reordering," arXiv, 2025-01-04: https://arxiv.org/abs/2501.02305
- arXiv HTML version, introduction and algorithm sections: https://arxiv.org/html/2501.02305v1
- PyPI `open-elastic-hash` package, released 2025-03-02, useful as a non-authoritative implementation reference: https://pypi.org/project/open-elastic-hash/
- Quanta Magazine background article, 2025-02-10, useful for non-technical context only: https://www.quantamagazine.org/undergraduate-upends-a-40-year-old-data-science-conjecture-20250210/
