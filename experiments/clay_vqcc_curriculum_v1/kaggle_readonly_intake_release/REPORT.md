# Clay VQCC read-only intake release

The release remains a private, offline, launch-disabled Kaggle CPU packet. It
now materializes the exact task rows and the comparison-level training controls
instead of retaining only aggregate task-ID hashes.

## Implemented

- Exact balanced and natural-prevalence gate comparisons are canonical JSONL.
- The gate shuffled-binding arm is a dataset-wide one-to-one target occurrence
  permutation.
- Finding truth rows remain strict evaluation records. Candidate and synthetic
  shuffled training rows use a separate typed schema, preserving actual answer
  provenance while changing the bound destination one-to-one within task and
  answer-length strata.
- Every task artifact is content-addressed in `TASK_MANIFEST.json`; the intake
  rejects noncanonical JSONL, changed prompts/payloads, undeclared files, and
  incomplete or non-bijective mappings.
- The three pinned parent checkpoints were read through bounded ZIP metadata and
  `pickletools` only. No pickle was executed and no model was loaded. All three
  contain the exact same 276-token vocabulary, including `U+E100..U+E1FF`.
- The vocabulary hash now uses the parent campaign's canonical algorithm and
  equals `bb0541789d0cfac2e02f7c3321d93ce1b9dc5513e2852499d81122a1e600e5b1`.

## Evidence

- `62 passed` across the curriculum and release suite.
- Ruff and compileall pass.
- Release verifier: `PASS_PREPARED_ONLY`.
- Release content set:
  `a9de77b6a1676f785d2b2f753776a5f045b8b1266e4b266937251eb371065bc3`.
- Self-contained code file:
  `132eb7c21dfaf4769678343297e4f1f51a8e91da08d0673f84a70514fb70ceb7`.

## Boundary

No Kaggle kernel was pushed or run. No cloud corpus was read by this packet, no
model was loaded or trained, no checkpoint was promoted, and no competition
submission was made. Admission is still `NOT_CONSUMED` with
`execution_authorized=false`.
