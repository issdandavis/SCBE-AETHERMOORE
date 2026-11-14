# Clay frozen-multiview Kaggle compatibility map — 2026-11-14

Status: `PRELAUNCH_PACKET_VALIDATED`

## Capability and boundary

Run a reduced-budget copy of the existing frozen-core multiview adapter campaign
on Kaggle Linux/CPU while the full local Windows/CPU lineage continues. This
adds cross-platform loader, optimizer, checkpoint, recovery, and artifact
compatibility evidence. It does not replicate the full experiment budget and
cannot promote, merge, execute, dispatch tools, or authorize partial unfreezing.

The cloud lineage is intentionally separate:

```text
local immutable trainer/source bytes
  -> deterministic hash manifest + private packet ZIP
  -> private Kaggle dataset version
  -> private Kaggle CPU script (new seeds, reduced rows/steps)
  -> two-slot checkpoints + RESULT.json
  -> bounded recovery download + hash/load replay

local full campaign -------------------------------------> independent replay
```

## Nodes

| Node | Exact identity | Role | Authority/status |
|---|---|---|---|
| Local canonical campaign | `C:\dev\clay-training-runs\frozen-multiview-adapter-20261113-v1` | Full 3-seed, 28k/18k-step comparison | Running; canonical; no promotion authority |
| Local source commit | `da5536eb8e39dfff18073d300a307c39f0e2b851` | SCBE trainer and data-builder lineage | Clean source worktree |
| Local run manifest | `...\RUN_MANIFEST.json` | Pins config, source hashes, trainer, data builder and preregistration | Immutable input to packet builder |
| Action source | `C:\dev\_wt_clay_action_byte_confirm_20261110\experiments\clay_action_compiler_20261109` | Deterministic sandbox/policy data authority | Four consumed files hash-pinned; no execution |
| Packet builder | `scripts/research/build_clay_frozen_multiview_kaggle_packet.py` | Copies exact bytes, emits deterministic ZIP and private Kaggle metadata | New; local CPU only |
| Kaggle entry | `scripts/research/run_clay_frozen_multiview_kaggle_compat.py` | Verifies packet, records environment, runs unchanged trainer, seals recovery | New; private cloud CPU |
| Private dataset | `issacizrealdavis/clay-frozen-multiview-compat-input-20261114` | Immutable code/source packet | Proposed until uploaded |
| Private kernel | `issacizrealdavis/clay-frozen-multiview-compat-20261114` | Three new seeds and all four matched arms | Proposed until launched |
| Recovery root | `C:\dev\clay-training-runs\cloud-review\frozen-multiview-compat-20261114` | Downloaded cloud receipts/checkpoints | Proposed until completion |

Read-only inventory:
`docs/research/CLAY_FROZEN_MULTIVIEW_KAGGLE_COMPAT_INVENTORY_20261114.json`,
61,422 bytes, SHA-256
`ce6d849b2ad1a35de7a03a4ae91090e91d587dc9c6261708e94e873b9b787cc0`.

## Edge invariants

- The packet builder consumes the active local `RUN_MANIFEST.json`; it verifies
  the runner, data-builder, preregistration, and four action-source hashes before
  copying anything.
- The private packet preserves working bytes. It does not rely on Git checkout
  line-ending normalization for the active preregistration receipt.
- The Kaggle entry rejects ambiguous datasets, archive path traversal, byte/hash
  drift, missing packet files, a non-CPU packet, or a non-empty output root.
- Local and cloud checkpoints never share a writable directory. The cloud run
  uses seeds `20261141`, `20261142`, and `20261143`.
- Cloud uses all four original arms, but only `200` rows/view, `300` held rows,
  `1,000` parent steps, and `1,000` adapter steps. Its metrics are diagnostics,
  not substitutes for the full local 28k/18k experiment.
- The 25 GiB free-space floor remains unchanged. No disk, statistical, or
  promotion gate is lowered.
- The exact deterministic compiler remains label authority only. Tool dispatch
  and action execution stay disabled.

## Preflight and terminal conditions

Missing capability: a recovered Linux/cloud checkpoint produced by the same
Clay loader and trainer surface. The earlier Kaggle rook run proved provider and
PyTorch artifact transport, but it exercised a different model and a refuted
topology claim.

Expected cloud work is 12,000 optimizer updates (three seeds; one parent and
three trained arms per seed), CPU-only, with checkpoints every 250 updates. The
live Kaggle account reports 30 GPU hours and 20 TPU hours available; this branch
uses neither quota because the pinned campaign is CPU deterministic. The job
stops on packet/hash mismatch, missing Torch/NumPy, less than 25 GiB free space,
non-finite training, checkpoint failure, nonzero trainer exit, or missing final
`RESULT.json`.

Success is limited to:

1. one private Kaggle version runs the exact packet;
2. all four arms train for all three compatibility seeds;
3. recovered checkpoint and receipt hashes match the saved Kaggle output;
4. recovered tensors load safely on the local Torch runtime; and
5. no output is merged or promoted.

Rollback is abandoning the separate cloud branch and private Kaggle artifacts.
The advancing local campaign and its checkpoints are never modified.

## Measured prelaunch result

Packet v1 was deliberately not uploaded after the local replay found that it
contained the pinned trainer module but omitted the thin direct-launch wrapper.
Packet v2 adds that exact wrapper and passed a three-seed local end-to-end smoke:

- Stage: `C:\dev\_kaggle_stage\clay-frozen-multiview-compat-20261114-v2`
- Build receipt: `1,665` bytes, SHA-256
  `4ef7104855ed74c8dc21c540d8d8f6731c6fcab44724d77bd8fb0e4db39ee152`
- Deterministic packet ZIP: `1,186,394` bytes, SHA-256
  `4a6a8eb1776752cc7d5042e7f57cf7e955387b017a0d5c3454e206ff53da9f0c`
- Packet files: `313`
- Local compatibility smoke: three seeds, all four arms, `8` parent and `8`
  adapter updates per trained arm, two-slot checkpoints, final result and recovery
  manifest present
- Smoke receipt: SHA-256
  `37b4969574f73e0b3a0b32e0bd8347b8fa57632ecbcf05a1de98e8173b343f07`
- Safe local reload: all `36` generated `.pt` artifacts opened with
  `torch.load(..., weights_only=True)` and yielded mappings
- Focused regression: `21 passed` across the existing adapter, replay,
  supervisor, and new cloud-packet tests

The eight-update smoke produced zero task accuracy, as expected for a transport
check this short. It is mechanics evidence only. The private Kaggle run retains
the preregistered three-seed compatibility budget of 1,000/1,000 updates.
