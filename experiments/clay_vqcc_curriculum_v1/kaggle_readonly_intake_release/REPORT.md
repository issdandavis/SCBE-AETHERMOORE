# Clay VQCC read-only intake release

The full-mount intake is now staged as one self-contained Kaggle script, but it
has not been launched. The release remains fail-closed behind a separate
one-use admission.

## What changed

- The Kaggle source is pinned explicitly to
  `issacizrealdavis/clay-vqcc-research-corpus/2`. This matters because the
  dataset's unversioned default is now version 3.
- The entry point is a generated single file because Kaggle CLI 2.2.5 uploads
  only `code_file`, not arbitrary sibling modules.
- The script embeds the reviewed splitter, sampler, task builders, campaign
  spec, metadata, and admission in a deterministic compressed payload. It
  verifies the payload and every embedded file by SHA-256 before materializing
  a fresh temporary runtime.
- Corpus discovery is bounded to immediate Kaggle input mounts and selects the
  only manifest matching
  `e4a9e7e9911fd8cdd8f858595a57b047402eb32a51571a54db580f4be87597c5`.
- The unchanged 25 GiB `/tmp` storage floor is checked before the corpus is
  read. Persistent output is capped at 128 MiB and published atomically.

## Evidence

- 56 curriculum tests pass, including six release tests and five strict byte
  codec tests.
- The isolated release smoke copies only
  `clay_vqcc_readonly_intake.py` to an otherwise empty directory. It verifies
  all embedded sources and correctly refuses cloud execution because the
  admission is `NOT_CONSUMED` / `false`.
- Release content set:
  `bc4de083da4e9b9ca985246850fa5b977a4edeb3b80d0c4e0e115c474cfa0ad4`.
- Generated code file:
  `5553ffc97323448b5fd7da9636cdf001430baa1348939575fc80c2c240c75d25`.

## Boundary

No Kaggle kernel was pushed or run. No corpus row was read from Kaggle by this
release, no model was loaded or trained, no checkpoint was promoted, and no
competition submission was made. The next action requires explicit one-use
execution authorization for the read-only intake only; training remains a
different, later authorization.
