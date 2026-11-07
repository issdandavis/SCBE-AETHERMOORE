# Prime Token Catalog Result — 2026-11-06

Status: `MECHANICS_PROVEN_RETRIEVAL_GAIN_UNESTABLISHED`

## Outcome

The bounded implementation now converts attributed local sources into an
immutable word-occurrence catalog with six typed retrieval views: lexical, 5W,
speech/grammar, atomic, prime topology and source provenance. Canonical identity
remains exact UTF-8 source spans. Clay's frozen BPE-4096 tokenizer is a typed view,
not a replacement for the active byte-token model identity.

Goal search separately ranks content/idea/evidence tokens and returns function
words as grammar constraints. Sparse shared-feature topology raises and lowers
section scores. An optional probability lookup is a separate append-only SQLite
sidecar anchored to a caller-supplied checkpoint SHA-256; it never writes neural
tensors or changes the serving pointer.

## Pilot Evidence

Pilot directory:
`C:/dev/clay-training-runs/prime-token-catalog-20261106/local-pilot-v3/`

- Sources: 11
- Sections: 364
- Word occurrences: 10,220
- Relationship memberships: 20,923
- Catalog SHA-256:
  `0c051ab5c27da8f70fd0d77830994e03bf55cda0224c696d06ac3cedf404b403`
- Frozen tokenizer SHA-256:
  `6c14a5cd26188678f920273cff49483f535e340caa98e3a7eb4d3285286c37c6`
- Weight anchor SHA-256:
  `003c7b846f59aa67fe6cefb04647bd93d94b896ad2617ad79384f1ac8246fd1f`
- Probability events: 256; normalized sum: 1.0

For the goal asking why prime-sieve routing connects token relationships while
grammar remains secondary, the aligned search ranked the relevant
`C:/dev/loom/clay_sieve.py` section first at 1.031711. The size-matched shuffled
binding control ranked unrelated packaging prose first at 0.898709. The 5W
ablation scored 1.032159 and retained the same leading section, so this query does
not demonstrate an independent 5W benefit.

These are structural pilot observations, not a capability claim. A promotion
decision requires source-disjoint queries over multiple seeds and must beat both
the lexical/no-intervention baseline and the shuffled size-matched control by the
existing pooled-variance gate.

## Verification

- Black: pass
- Flake8: pass
- Pytest: 48 passed across the new catalog, prime sieve, atomic/fusion and
  function-lexicon suites
- Catalog hash remained unchanged after the probability sidecar update
- No tokenizer, model checkpoint, serving pointer or active training output was
  modified

The first pilot exposed excessive occurrence-level storage and was stopped. Its
1,062,961,987-byte output was moved, not deleted, to the verified reversible hold
at
`C:/Users/issda/.quarantine/held-deletions/20261107T004424184Z-7a13dc21/local-pilot`.
The v3 design analyzes unique words once, caps sparse memberships and stays well
inside the declared disk budget.

## Tablet and Internet Boundary

The laptop remains the canonical writer. The detached tablet may later consume a
compact read-only packet keyed by catalog/search hashes and return selected IDs or
annotations. It must not directly edit the catalog, sidecar or weights. No tablet
deployment occurred in this run.

Internet material may be added only as downloaded, attributed records with source
kind, content hash and license metadata. The catalog core performs no network
fetch. This provides the pre-tagging layer needed before a separately authorized
large-corpus ingestion or frozen-core input-sidecar experiment.

## Successor Evaluation

The 2026-11-07 controlled benchmark supersedes the one-query pilot as ranking
evidence. Full six-view retrieval scored below lexical-only and no-intervention
baselines on 11 curated source-record-disjoint queries. The result is underpowered
and blocks promotion; see
`docs/tokenizer/PRIME_TOKEN_CATALOG_BENCHMARK_RESULT_20261107.md`.
