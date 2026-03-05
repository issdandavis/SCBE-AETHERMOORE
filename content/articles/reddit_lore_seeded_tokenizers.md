# [R] Lore-Seeded Tokenizers: Using Narrative Corpora Instead of Web Scrapes for Tokenizer Training

**TL;DR**: I trained a tokenizer on 12,596 paragraphs of AI-generated D&D game logs instead of Wikipedia/Common Crawl. The resulting tokens carry narrative structure, emotional context, and internal consistency that flat web scrapes lack. This enables a context-drift detection layer where tokens produced without knowledge of the seed corpus measurably diverge from canonical embeddings. Code is open source.

## What This Is

A tokenizer architecture (Sacred Tongues) with 6 semantic domains, 256 tokens each (1,536 total), weighted by the golden ratio. The training seed is a fixed, auditable narrative corpus generated through months of collaborative AI storytelling on Everweave (an AI D&D platform).

## What Makes It Different

Standard tokenizer seeds (Wikipedia, Common Crawl, BookCorpus) are:
- Statistically massive but contextually flat
- No emotional texture across the corpus
- No character consistency or narrative arcs
- No internal world rules that persist

The Everweave game logs have all of these. When used as a tokenizer seed, the resulting tokens carry contextual associations that web-scraped seeds don't encode.

## The Security Application

Context-drift detection: if someone generates token sequences without knowledge of the lore seed, their tokens will drift from canonical embeddings. This is measurable via hyperbolic distance in a Poincare ball model.

```python
def measure_context_drift(token_sequence, canonical_embeddings):
    drift_scores = []
    for token in token_sequence:
        embedding = get_embedding(token)
        d_H = hyperbolic_distance(embedding, canonical_embeddings[token.tongue])
        drift_scores.append(d_H)

    avg_drift = sum(drift_scores) / len(drift_scores)
    # Legitimate: avg_drift < 0.3
    # Suspicious: 0.3 < avg_drift < 0.7
    # Adversarial: avg_drift > 0.7
    return avg_drift
```

This isn't primary authentication — it's an additional contextual verification layer.

## The Math

The harmonic wall function: `H(d,R) = R^(d^2)`

Adversarial behavior (large d) costs exponentially more. The six tongues generate a Clifford algebra Cl(6,0) with 64 components, 15 bivector cross-tongue interaction channels.

Tongue weights: KO=1.0, AV=1.618, RU=2.618, CA=4.236, UM=6.854, DR=11.09 (golden ratio scaling).

## Limitations

- Small vocabulary (1,536 tokens) compared to tiktoken (100K+)
- Context-drift detection is probabilistic, not deterministic
- The approach assumes the attacker doesn't have the seed corpus
- Poincare ball distance computation adds overhead
- Haven't benchmarked against standard tokenizers on downstream NLP tasks

## Links

- **Code**: https://github.com/issdandavis/SCBE-AETHERMOORE
- **Dataset**: https://huggingface.co/datasets/issdandavis/scbe-aethermoore-training-data
- **Patent**: USPTO #63/961,403 (provisional)
- **The game**: https://everweave.ai/

Looking for feedback on:
1. Has anyone else explored narrative-structured tokenizer seeds?
2. Thoughts on the context-drift detection approach?
3. Interest in a benchmark comparison against standard tokenizers?
