# E101 hyperpath component crosswalk to SCBE routing

Date: 2026-11-08  
Status: measured research crosswalk updated through E104; no runtime integration;
no promotion.

## Why this note exists

Clay E101 separates a fixed 64-dimensional byte-route table into three channel
families: route-winner frequency, route cost, and tie/signed derivative state.
This note identifies the exact SCBE surfaces that could consume analogous
*receipts* if the result replicates. It does not claim that Clay's byte features
and SCBE's section-retrieval features are interchangeable.

## Measured Clay result

E101 completed six arms by three seeds on the source-disjoint E100 corpus. The
independent artifact verifier reported zero errors. Mean held-input losses were:

| Arm | Mean loss | Controlled gain over parent and random | Full beats arm |
|---|---:|:---:|:---:|
| full sieve | 3.524617 | yes | — |
| route costs | 3.533751 | yes | yes |
| winner frequencies | 3.548910 | yes | yes |
| tie/signed state | 3.566731 | yes | yes |
| shuffled binding | 3.531583 | control | yes |
| random features | 3.580774 | control | yes |
| frozen parent | 3.589145 | baseline | yes |

The full table beat every component and all preregistered controls by more than
`2 x pooled SD`. Every component independently retained controlled loss gain.
Route costs were the strongest single component. Shuffled binding still had
higher mean top-1 accuracy than the full arm, so this is calibrated-loss and
component-attribution evidence, not universal ranking dominance.

Authority identities:

- E101 run pin:
  `f3353e7a08a07522a889f8d683a709b6b90be9b834d29f88cbf221ff301bb979`;
- matrix:
  `7ae143e024e3a8136424bd07b5e2b65da2f19e385a73649622f30c22d2d42fef`;
- verifier:
  `404777b02b8effd06ddd23ef04dd497a4a19cb66d4e3ef31fd2523c360f31847`;
- recovery receipt:
  `954263b4d71adeb11546c25b8351723c9f4dde189265b9a15629a97f321e6d49`.

The reference supervisor failed closed after training because the remote S:
share denied replacement of an existing mutable status file. Immutable results
passed recovery verification. At that point, an exact fresh-root replication
was still required.

## Fresh-seed robustness and parent-provenance correction

E103 validly repeated all six arms with three fresh seeds against the same
frozen step-13,400 slot-A parent. It preserved the parent bit-for-bit, used
source-ID/content-hash-disjoint E100 data, and passed independent verification
with zero errors and no promotion.

| Campaign | Full mean loss | Frozen parent | Full vs random | Full vs shuffled | Route cost marginal | Winner frequency marginal | Tie/signed marginal |
|---|---:|---:|:---:|:---:|:---:|:---:|:---:|
| E102, slot A, original seeds | 3.524484 | 3.589145 | pass | pass | pass | pass | **underpowered** |
| E103, slot A, fresh seeds | 3.524989 | 3.589145 | pass | pass | pass | pass | **fail threshold** |

For E103, full-sieve loss advantage was `0.064157` versus the frozen parent,
`0.055908` versus random features, and `0.008841` versus shuffled binding. Route
cost and winner frequency therefore survive a fresh-seed check. Tie/signed
state did not: its full-versus-ablation advantage was `0.000860`, below the
`0.002889` threshold, consistent with E102's underpowered result.

An attempted adjacent-parent E104 run is **not valid parent-robustness
evidence**. Although its run pin and model loader named checkpoint B, all 18
horse results and all 18 terminal adapter checkpoints inherited a hard-coded
checkpoint-A metadata hash. The strengthened verifier reports
`FAIL_PRESERVED_NO_PROMOTION`. E104 artifacts remain preserved but may not be
pooled or cited for checkpoint-B effects. A corrected E105 run is pending.

Therefore SCBE may retain the primary/mirror trits as lossless-to-audit derived
telemetry beside their raw values, but may not describe tie/signed state as a
causal routing feature or use it to authorize a route. This does not test the
v6 prospective retrieval benchmark: Clay byte identity and SCBE canonical
section identity remain different types.

Valid authority identities:

- E102 matrix `fdf75b1b02a5d780546de217d73641fbe9f3ad293ef0a7f211894742f46f1f54`;
- E102 verification `a0b321bc478eb334dd9eabc49389d96e23622bd17f1bf1a9478217a32348190c`;
- E103 matrix `dc9aff8d79da4728be396f37289a988cc01a0920f6afd4bd66e69c1326a33b47`;
- E103 verification `8a61c5543957221294a36129b3bd80bf2ab13deffc218bba8cb00f0892132f8b`.

## Concrete SCBE surfaces

### Route costs

`python/scbe/prime_token_catalog.py` already records prime route/residue/range
features and implements `search_late_output_fused()`. That function keeps
lexical and eligible auxiliary searches separate and fuses only their ranks
with fixed `k=60` reciprocal-rank contributions.

E101 supports testing route-cost telemetry here first. It does **not** justify
changing `k`, treating rank contributions as probabilities, or injecting a
Clay adapter. The first safe artifact is an output receipt containing each
lane's rank, reciprocal-rank contribution, and total fixed fusion score.

### Winner frequencies

`explicit_route()` declares which auxiliary views are eligible, while
`search_late_output_fused()` records `route_action`, selected views, and child
search IDs. An offline evaluator can count which eligible lane contributes the
best canonical-section rank across a fixed query set.

Winner counts must remain evaluation metadata until aligned binding beats
shuffled binding and lexical-only/no-intervention controls on a genuinely
source-disjoint benchmark. They must not become an adaptive production gate
from development-consumed queries.

### Tie and signed state

`src/ai_brain/dual-ternary.ts` provides a real `{-1, 0, +1}²` amplitude/mirror
encoding, and `src/ai_brain/hamiltonian-braid.ts` maps those states to governed
actions. Those modules passed their existing tests, but they are not the same
object as E101's signed path derivative and tie rate.

The only justified bridge remains optional telemetry:

- primary trit: bounded difference between lexical and auxiliary rank evidence;
- mirror trit: bounded change under aligned versus shuffled binding;
- `(0, 0)`: insufficient separation/hold, not automatic approval;
- raw rank values and thresholds retained beside every trit projection.

No security action may be inferred from a Clay trit without a separate SCBE
governance calibration and false-route test. E102 and E103 show that the
tie/signed channel must not be assigned causal route authority.

## Verified local baseline

- `tests/tokenizer/test_prime_token_benchmark.py`: `15 passed`.
- `tests/ai_brain/dual-ternary.test.ts` and
  `tests/ai_brain/hamiltonian-braid.test.ts`: `150 passed`.

These tests verify current mechanics only. They do not provide the missing
prospective retrieval evidence.

## Post-replication implementation sequence

1. Keep `search_late_output_fused()` behavior unchanged.
2. Keep the implemented deterministic route-evidence receipt recording raw
   ranks, fixed RRF contributions, winner counts, ties, aligned/shuffled deltas,
   and dual trits; keep trits non-authoritative.
3. Prove exact no-intervention identity when no auxiliary route is eligible.
4. Evaluate lexical-only, route-null, aligned, three shuffled-binding seeds,
   and a size-matched random receipt on at least 30 closed, reviewed,
   source-disjoint queries.
5. Require gains over both no intervention and the size-matched control by more
   than `2 x pooled SD`; report macro-source metrics and source caps.
6. Only after those gates pass may a fixed late-output route consume the receipt.
   Neural weights, token probabilities, and hidden states remain unchanged.

Implementation and current fail-closed benchmark status are recorded in
`route_evidence_receipt_20261108.md`. The receipt machinery is complete and
tested; the current 31-query historical set is rejected because all 31 queries
collide with the v6 catalog, while the prospective watcher is still waiting for
a closed post-freeze source.

## Explicit non-claims

- E101 does not prove that SCBE's six catalog views add retrieval capability.
- Byte identity, section identity, tongue identity, and governance state remain
  distinct types.
- The three channel families are correlated views of one deterministic table,
  not independent evidence sources.
- No Clay checkpoint is compatible with or imported into SCBE runtime code.
- No serving pointer, package release, model weight, or promotion state changes
  because of this note.
