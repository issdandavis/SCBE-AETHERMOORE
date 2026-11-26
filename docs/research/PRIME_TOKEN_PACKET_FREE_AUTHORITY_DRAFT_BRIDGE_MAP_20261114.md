# Prime-token packet-free authority draft bridge map — 2026-11-14

Status: `PROVENANCE_ADMITTED_TRAINING_NOT_AUTHORIZED`

## Capability and boundary

Build a deterministic, non-admitting bridge from the existing frozen-action
ordinary/retention candidate artifacts into reviewable packet-free authority
drafts. The bridge may prove exact provenance and prepare a review packet. It
must not set `ADMITTED`, authorize training, score a model, launch an optimizer,
promote a checkpoint, unfreeze a sector, or dispatch a tool.

The live v7 prime-token watcher remains a separate lane. It currently has four
accepted closed-session candidates against a preregistered minimum of 30. This
bridge does not lower that gate and does not relabel action candidates as
prospective prime-token queries.

## Nodes

| Node | Exact path or identity | Role | Authority/status |
|---|---|---|---|
| Authority implementation | `python/scbe/prime_token_packet_free_authority.py` at `786f2e90d` | Defines authority v1, identity/line-join transforms, canonical rows, runtime validation | Tested; no training authority |
| Candidate producer | `C:\dev\_wt_scbe_atomic_stitch_20261113\scripts\research\build_frozen_action_candidate_bundle.py` | Builds four nonlaunchable candidate lanes and source receipts | Commit lineage includes `f6fdb7f9b`; candidate only |
| Text-span producer | `C:\dev\_wt_scbe_atomic_stitch_20261113\scripts\research\audit_frozen_action_text_sources.py` | Selects and hashes exact CPython/Rust line blocks | Candidate only |
| Candidate bundle | `C:\dev\clay-training-runs\source-audits\frozen-action-material-candidate-v2-20261114` | Supplies 55 ordinary and 52 retention rows plus 7,912 source receipts | `COMPLETE_NOT_ADMITTED`; loader rejection intentional |
| Exact text ledger | `...\frozen-action-math-sources-20261114\TEXT_SOURCE_SPAN_AUDIT.rows.jsonl` | Supplies raw excerpt hash, transformed prompt hash and line span | 107 rows; independent reconstruction passed |
| CPython artifact | `...\frozen-action-math-sources-20261114\cpython-controlflow.rst` | Ordinary source bytes | SHA-256 `3d0ca7d818cf84cdeee42e3735ae78d3b82025f62c7ef36f5c1c14b9ef6eeeb8` |
| Rust artifact | `...\frozen-action-math-sources-20261114\rust-book-control-flow.md` | Retention source bytes | SHA-256 `dcf589530b27653579874f189bf572600a3061712964f525a06844642a2defb6` |
| Draft bridge | New pure module plus thin CLI in the authority worktree | Reconstructs bytes and writes review-only artifacts | New; must fail closed |
| Draft output | New immutable directory under `C:\dev\clay-training-runs\source-audits` | Two source JSONL drafts, two authority drafts, review packet and build receipt | `NOT_REVIEWED`; all execution/training fields disabled |

Inventory receipt:
`C:\dev\clay-training-runs\source-audits\PRIME_TOKEN_AUTHORITY_BRIDGE_INVENTORY_20261114.json`,
57,557 bytes, SHA-256
`2992e3260631580c857ac3dc487eb66de4226fe8907146ad8ac70b2a0b82912b`.

## Edges and invariants

```text
source artifact bytes
  -> verify artifact SHA-256 + byte count
  -> convert audited half-open line span to exact UTF-8 byte offsets
  -> verify raw excerpt SHA-256
  -> apply line_strip_join_space_v1
  -> verify transformed prompt and prompt SHA-256
  -> match candidate row + candidate source receipt
  -> write NOT_REVIEWED authority/source drafts
  -> independent validator must reject them until a separate review decision
```

- Candidate manifest, lane files, source-receipt file, source-audit receipt and
  text ledger are all hash- and count-checked before output.
- Every candidate row, text-ledger row and matching authority receipt is consumed
  exactly once. Missing, duplicate or extra records stop the build.
- Re-encoding all decoded source lines must reproduce the artifact bytes before
  line indices are converted into byte offsets.
- The raw span hash and transformed prompt hash remain distinct receipts.
- Ordinary and retention artifact paths, artifact hashes and transformed prompt
  hashes must be disjoint.
- Draft authorities use the production authority schema but carry
  `review_status = NOT_REVIEWED`; every authority field remains
  `NOT_AUTHORIZED`.
- Output is atomic and refuses an existing destination. A failed pending
  directory remains available for inspection.

## Controls and success criteria

Unit controls must cover valid reconstruction, artifact drift, candidate-text
tampering, source-receipt tampering, missing coverage, line-span bounds,
ordinary/retention content overlap, destination overwrite, and confirmation
that the production validator rejects the draft review status.

Success for this build is only:

1. all 107 rows reconstructed from exact bytes;
2. all input and output descriptors sealed in one receipt;
3. focused tests and the complete tokenizer regression pass; and
4. the resulting artifacts remain unusable for training until a separate,
   explicit review/admission step.

No baseline/model/control comparison is run here because this component only
prepares provenance. Any later learned claim still requires the frozen parent,
no-intervention arm, size-matched random-fixed arm, one-to-one shuffled-binding
arm, fresh source-disjoint holdout, multiple seeds, uncertainty gate and
independent checkpoint replay.

## Budget and stop conditions

Expected work is CPU-only, under 20 MiB of input, under 2 MiB of new output and
under one minute per build. The existing 25 GiB training floor is unchanged.
Stop without output if any hash, count, span, transform, authority boundary or
cross-lane disjointness check fails. Rollback is removal of the new isolated
output directory and branch commit; existing candidates, weights and watcher
state are never modified.

## Measured build result

The direct CLI was executed from outside the repository on 2026-11-14 after a
subprocess regression established that the entry point imports correctly without
an inherited `PYTHONPATH`. It reconstructed all `107` audited records (`55`
ordinary and `52` retention), found no cross-lane source-artifact or transformed-
content overlap, and confirmed that the production validator rejects both draft
authorities.

- Output: `C:\dev\clay-training-runs\source-audits\prime-token-packet-free-authority-draft-v1-20261114`
- Build receipt: `3,103` bytes, SHA-256
  `6446981a6d1dfd58cd40ff89b4992beaae58a55992118638773707fb865cea71`
- Review packet: `107` rows, `157,452` bytes, SHA-256
  `e718ec2b2fd98f0f1c5d0f7b64b6f6f985d8772e4a59da0d0f2ed0379656a7da`
- Source audit: SHA-256
  `cfee86638e08d7db1267526f9fb9b38706a4748a9477a25e7efbbdf69c7a8f23`
- Authority remains `NONE` for dataset admission, execution, material evidence,
  optimization, partial unfreeze, promotion, and training intake; tool dispatch
  remains `DISABLED`.

This result proves a portable provenance bridge only. It does not admit the
candidate bundle, open the v7 30-candidate gate, or establish a model gain.

## Mapped next edge: independent provenance admission

The next concrete capability is a separate admission compiler, not a field edit
to either draft authority. It will consume the immutable draft build plus an
explicit row-decision ledger and emit a new immutable authority directory. The
draft producer remains unable to admit its own output.

```text
immutable REVIEW_PACKET.jsonl + immutable draft authority/source files
  -> independently authored decision ledger, exactly one decision per row
  -> recheck draft descriptors, source bytes, spans, transforms and content hashes
  -> retain only explicitly ADMIT rows; preserve rejected IDs and reason codes
  -> write ADMITTED provenance authorities with every operational authority disabled
  -> production validator replay + cross-lane disjointness replay
  -> immutable admission receipt
```

The existing source validator and deterministic text transforms are reused.
The genuinely new component is the decision-ledger/admission compiler. Its
downstream risk is that `review_status = ADMITTED` is accepted by the material
case runtime, so admission must remain distinct from training authorization and
must fail closed on missing, duplicate, stale, or hash-mismatched decisions.

Required decision fields are a decision-ledger schema, the pinned review-packet
SHA-256, row ID, lane, content SHA-256, `ADMIT` or `REJECT`, one or more bounded
reason codes, and a non-empty reviewer identity/role. Every review-packet row
must appear exactly once. The compiler must reject `PENDING`, unknown reason
codes, unreviewed rows, changed text, cross-lane source/content reuse, empty
admitted lanes, and any operational authority other than `NOT_AUTHORIZED`.

The admitted source JSONL and authority JSON remain byte-token inputs only.
They may satisfy provenance for a later material-case build, but they do not
authorize training intake, optimization, promotion, partial unfreeze, execution,
or tool dispatch. A later model experiment still needs the frozen baseline,
matched controls, source-disjoint holdout, multi-seed uncertainty gate and
independent checkpoint replay already named above.

Controls must cover complete mixed admit/reject review, stale review-packet
hash, missing/duplicate/extra decisions, content/lane mismatch, unsupported
decision/reason, all-rejected lane, tampered draft descriptor, authority
escalation, destination overwrite, production-validator replay and ordinary /
retention disjointness. The build is CPU-only, expected below 2 MiB of output
and one minute, writes through a new `.pending` directory, never mutates the
draft, and stops before output on any failed invariant.

## Measured provenance admission result

Two separate read-only semantic-review sessions inspected the complete ordinary
and retention lanes, after which the main session inspected all `107` rows and
added one conservative incomplete-context rejection. Their distinct thread IDs
are recorded, but the compiler explicitly labels them
`THREAD_IDS_DECLARED_NOT_AUTHENTICATED`; this is procedural separation, not a
cryptographic identity proof. The immutable decision ledger contains exactly
one hash-bound decision per review-packet row:

- Decision ledger:
  `docs/research/PRIME_TOKEN_PACKET_FREE_REVIEW_DECISIONS_20261114.json`
- Ledger SHA-256:
  `3b99ca198225de2d3f88f468670c81db7f54c76de3b0bfb067defc2807b709b6`
- Ordinary: `47` admitted, `8` rejected
- Retention: `35` admitted, `17` rejected
- Rejection reasons: bounded `MARKUP_ONLY`, `INCOMPLETE_CONTEXT`,
  `WRONG_LANE`, or `OTHER_REVIEWED_REJECTION` codes with short review notes

The final admission compiler reverified the draft descriptors, exact source
bytes and spans, transformed hashes, source-audit binding, license artifacts,
decision coverage, lane disjointness, and production-validator replay. Its
authoritative output is:

- Output:
  `C:\dev\clay-training-runs\source-audits\prime-token-packet-free-authority-admitted-v3-20261114`
- Build receipt: `13,408` bytes, SHA-256
  `f16516982e889e0089dbb38ab190f2edd995f91b06832152a8a392e4cc9c0ede`
- Ordinary authority SHA-256:
  `75d5328503311fb7620aac0c22c4e9cdd66d6c3f14991c94cdf43fa83d7fb273`
- Retention authority SHA-256:
  `7ac4d65a0abecdbc0d3f3fa9ad8cb4129334fa423da9eddefe61974a5b9ea641`
- All six output descriptors independently matched their byte counts and
  SHA-256 hashes; both recorded production-validation paths exist after the
  atomic publication rename.
- The focused admission suite passed `19/19` after the final compiler and
  receipt fixes; the complete tokenizer suite passed `417/417`.

The earlier v1 output is retained as a negative engineering receipt: its
validation metadata recorded temporary `.pending` paths that no longer existed
after publication. V2 corrected those paths but lacked machine-readable
supersession metadata. The v3 receipt hash-binds both prior build receipts under
its `supersedes` field, so automated consumers can reject v1 and v2. No source
decision changed across these receipt-only rebuilds.

A narrow read-only second-pass review reported both prior findings resolved and
no new findings. Its 297-byte receipt is
`C:\dev\clay-training-runs\source-audits\prime-token-packet-free-admission-review-20261114\FINAL_REVIEW_V3.txt`,
SHA-256 `c104b60ddf61d0915ad0b6f97fda02796f21ffaa38d535e03db4986243fffbbb`.
Residual risk remains explicit: review separation is procedural, and consumers
must verify and honor v3's `supersedes` entries.

`ADMITTED` here means source provenance only. The v3 receipt declares
`dataset_admission = NONE`, `training_intake = NONE`, `optimization = NONE`,
`execution = NONE`, `material_evidence = NONE`, `promotion = NONE`,
`partial_unfreeze = NONE`, and `tool_dispatch = DISABLED`. No model weights,
training labels, watcher gates, or promotion state changed.

## Mapped next edge: four-lane provenance-bound staging manifest

The next edge reuses the existing frozen-action candidate bundle and the v3
packet-free admission instead of regenerating any source rows. It will compile
one replayable, four-lane staging bundle:

```text
candidate train + holdout rows and source receipts
  + v3 admitted ordinary + retention identities and source authorities
  -> recheck every candidate descriptor and authority receipt
  -> retain only admitted ordinary/retention rows
  -> prove record-ID, prompt, excerpt-hash, locator and artifact agreement
  -> prove four-way source-ID, source-family and exact-prompt disjointness
  -> write immutable staged lanes + replayable source-authority ledger
```

### Inputs and schemas

- Candidate root:
  `C:\dev\clay-training-runs\source-audits\frozen-action-material-candidate-v2-20261114`
  with manifest schema `clay.full-system-action-dataset-candidate.v1` and build
  status `COMPLETE_NOT_ADMITTED`.
- Provenance admission root:
  `C:\dev\clay-training-runs\source-audits\prime-token-packet-free-authority-admitted-v3-20261114`
  with build schema
  `scbe.prime-token-packet-free-authority-admission-build.v1` and status
  `PROVENANCE_ADMITTED_TRAINING_NOT_AUTHORIZED`.
- The staged manifest will use a schema distinct from
  `clay.full-system-action-dataset.v1`. The existing campaign loader must reject
  it until a later, separately reviewed action-mapping admission changes both
  schema and authority.
- The source ledger will use the campaign's replayable authority fields, while
  hash-binding both producer receipts and retaining all per-source receipts.

### Outputs and authority boundary

The output contains `train.jsonl`, `holdout.jsonl`, `ordinary.jsonl`,
`retention.jsonl`, `SOURCE_AUTHORITIES.json`, `MANIFEST.json`, and one build
receipt. Train and holdout remain action-mapping candidates. Ordinary and
retention carry admitted source provenance but no action target. Every row keeps
`training_eligible = false`; the manifest keeps material evidence, training,
execution, optimization, promotion, partial unfreeze and tool dispatch disabled.

The staging manifest is deliberately non-launchable. It is not substituted into
the active frozen-multiview campaign, the prime-token prospective watcher, or an
independent replay. A later action-mapping review must consume this immutable
receipt and emit a different manifest rather than editing these files in place.

### Controls, budget and stop conditions

Controls cover stale candidate/admission descriptors, missing or extra admitted
identities, excerpt/prompt/locator mismatch, authority-receipt replay, duplicate
record/source IDs, cross-lane source-family or prompt overlap, operational
authority escalation, destination overwrite, and confirmation that the campaign
schema rejects the staged manifest. The expected output is under 12 MiB and the
build is CPU-only. Stop before publication on any mismatch or if the existing
25 GiB training floor would be crossed. Rollback is deletion of only the new
isolated staging directory; no active checkpoint, watcher, or source artifact is
modified.

### Deferred chemistry hypothesis

The proposed chemistry cross-vector is recorded as a later controlled model
experiment, not folded into this provenance compiler. For a regional state
`z`, a bounded selector `p(z) = sigmoid(w^T z)` may choose or blend two
opposite-gauge routes `F+` and `F-` that must solve the same task. The quantum
circuit emitted after search remains deterministic and reversible; probability
belongs to architecture search, not to an unverifiable final circuit. Promotion
requires the selector to beat a vanilla route, a parameter-matched random route,
and a shuffled-region route across multiple seeds while preserving endpoint
equivalence and reducing the actual task cost.

