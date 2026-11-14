# Prime-token packet-free authority draft bridge map — 2026-11-14

Status: `BUILT_NOT_REVIEWED_NOT_AUTHORIZED`

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

