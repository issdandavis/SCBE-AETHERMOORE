# Independent Request Gate — 2026-11-07

Status: collection tooling implemented; raw requests remain private runtime data.

The 11-query mechanics benchmark was authored after reading its target sources.
It cannot establish retrieval capability. The next benchmark draws only from a
scrubbed private Codex session authored on 2026-09-05, before the November
catalog benchmark.

## Frozen collection protocol

1. Parse only `Issac:` request turns from the hash-verified scrubbed session
   chunks.
2. Keep requests between 20 and 1,600 characters.
3. Reject agent instructions, environment blocks, skill catalogs, and goal
   continuation envelopes.
4. Select with broad preregistered topic expressions for prime/sieve, 5W,
   tongue/braid, publication/terminal, and source/research requests. The
   expressions contain no wording copied from the target documents or the
   original 11 benchmark questions.
5. Deduplicate exact whitespace-normalized, case-folded text.
6. A reviewer accepts or rejects candidates by SHA-256 and assigns the relevant
   catalog source suffix. Labels do not contain query text and cannot be joined
   to another dataset hash.
7. Refuse final benchmark creation below 30 accepted requests.

The review queue and final benchmark are runtime-only because they contain
private conversation text. Git stores the extractor, tests, and protocol, not
the requests. The emitted benchmark uses unique `private-session://` identities;
the evaluator still rejects any query source that entered the retrieval catalog.

No scoring weight may be tuned on the final accepted requests. The first run
must compare the frozen full field, lexical-only, no-intervention, every existing
ablation, and three shuffled-binding seeds. A lexical-first cascade remains a
future candidate and must be implemented before seeing its own test result.

## Frozen-field result

Status: `NO_GAIN`; no promotion.

The deterministic collector found 184 candidate turns. Semantic review accepted
31 requests: 14 prime/sieve, five 5W, eight tongue/braid, and four
terminal/package-publication requests. Every accepted label is bound to the
scrubbed dataset SHA-256 and the final benchmark contains unique
`private-session://` source identities.

| Arm | MRR | Recall@1 | Recall@5 |
|---|---:|---:|---:|
| lexical only | 0.5143 | 0.4516 | 0.6129 |
| no intervention | 0.5105 | 0.4516 | 0.6452 |
| no speech | 0.5124 | 0.4516 | 0.6452 |
| no atomic | 0.5103 | 0.4516 | 0.6452 |
| full six-view | 0.5092 | 0.4516 | 0.6452 |
| no topology | 0.5098 | 0.4516 | 0.6452 |
| no prime | 0.5062 | 0.4516 | 0.6452 |
| no 5W | 0.5016 | 0.4516 | 0.6452 |
| shuffled binding, three-seed mean | 0.2708 | 0.0860 | 0.4839 |

Full minus lexical MRR was `-0.0051`; full minus no-intervention was
`-0.0014`. Full exceeded shuffled controls by `0.2384`, below the required
two-pooled-SD threshold of `0.7542`. No gate passed.

This independently authored set confirms the earlier no-promotion result: the
complete six-view score does not improve over lexical retrieval. The four source
families are intentionally narrow and reviewer labels were not blind, so this is
not a broad retrieval benchmark. It is sufficient to reject promotion of this
field revision. Auxiliary views remain cataloged evidence and may be tested only
as a zero-parameter lexical tie-break/fallback layer on a new holdout.

Runtime receipts:

- review queue SHA-256:
  `3061114faa17d5904120a0e0a509a4f3be1f002d9f9d68e05657ba9d5d544b98`;
- review labels SHA-256:
  `36a470f1d2c1dfbdace85977d0802e4000397a9ac76e34af42bac81fc73631f2`;
- benchmark SHA-256:
  `886cef763c7e2eafdae338e40f0b53c0b8fce52086f110065b0461577a7e380d`;
- result SHA-256:
  `2aef71e703848ed5a4e8ec23704a1b8e8388fcb93eae7538d43be63400012471`;
- runtime directory:
  `C:/dev/clay-training-runs/prime-token-catalog-20261106/independent-requests-20261107/`.
