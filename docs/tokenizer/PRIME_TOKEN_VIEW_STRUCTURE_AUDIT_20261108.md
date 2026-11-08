# Prime Token Six-View Structure Audit

Status: `STRUCTURAL_VIEW_AUDIT_PASS`; structural evidence only, no promotion

Date: 2026-11-08

## Question

Does the frozen v6 catalog actually expose all six typed views for every
section, and how much structural diversity does each view contain? This audit
does not ask whether any view improves retrieval. It also does not treat six
correlated representations of one occurrence as six independent observations.

## Frozen input and execution

- Catalog:
  `C:/dev/clay-training-runs/prime-token-catalog-20261106/catalog-v6-codex-user-20261107/catalog.sqlite3`
- Catalog SHA-256 before and after:
  `1839d609bc8e7263263e4c83d1bac2c3645285a9a664abfc6e9f292cc0b2fba0`
- Receipt:
  `S:/ClayRuns/prime-token-view-audit-20261108/VIEW_STRUCTURE_AUDIT.json`
- Receipt SHA-256:
  `2d93aa24a4b14164254d639b1787c968268d214dc32f5cdc07b818785b501b6d`
- Receipt size: 5,625 bytes
- Sections: 9,750

The command opened SQLite in read-only mode, streamed the existing primary-key
order, hashed each section/view feature signature, and independently hashed the
database before and after. It did not read a prospective query, calculate a
retrieval score, or write the catalog.

## Result

All 9,750 sections expose all six declared views. There are no unknown view
rows, no orphan feature rows, and the catalog hash is unchanged.

| View | Feature rows | Distinct keys | Distinct section signatures | Largest repeated signature | Interpretation |
|---|---:|---:|---:|---:|---|
| lexical | 653,493 | 31,179 | 8,800 | 32 | canonical content anchor |
| five-W | 19,500 | 12 | 524 | 301 | coarse deterministic section label |
| speech | 186,281 | 144 | 6,714 | 373 | deterministic lexical annotation |
| atomic | 211,138 | 31 | 6,426 | 148 | deterministic lexical annotation |
| prime | 503,589 | 29,274 | 9,750 | 1 | unique positional/routing signature for every section |
| source | 19,500 | 2,159 | 5,671 | 64 | external provenance plus section-frequency weight |

The prime view is structurally unique for every section. That is useful as a
routing address, but uniqueness is not semantic evidence. Its keys are derived
from global occurrence ordinal, factorization, range, and the five-W-selected
route prime. Letting that view vote as if it were an independent semantic
measurement creates a position/identity channel. This observation is
consistent with earlier negative full-six-view evaluations, but it does not by
itself establish their cause.

## Provenance boundary

The implementation graph classifies the views as follows:

- lexical: canonical anchor built from source bytes and word spans, with the
  frozen BPE representation attached;
- speech and atomic: deterministic functions of lexical tokens;
- five-W: deterministic function of the section's lexical, speech, and atomic
  annotations;
- prime: deterministic function of occurrence ordinal and five-W role;
- source: external manifest and source-identity metadata.

Therefore the catalog has zero additional independent semantic observations.
It has one canonical content anchor, four deterministic derived views, and one
external metadata view. This does not make the derived views useless; it means
they must be evaluated as routing transforms or constraints with ablations and
shuffled-binding controls, not counted as independent supporting witnesses.

## Decision

Keep E92's explicit eligibility, lexical baseline, route-null control, and
shuffled-binding controls unchanged. Do not promote the full six-view field and
do not change any probability lookup or neural weight. A future experiment may
test prime features only for explicitly prime/sieve-oriented requests, while
keeping positional identity out of ordinary semantic scoring. That experiment
would require a new preregistration and a genuinely independent post-freeze
query set.

## Verification

- Focused catalog tests: `13 passed`.
- Ruff on the changed implementation, CLI, and tests: `All checks passed!`.
- Full v6 structural audit: `STRUCTURAL_VIEW_AUDIT_PASS`.
- Catalog SHA-256 before/after: identical.

