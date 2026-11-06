# Existing Colab and key-mirror dependency recovery

The unified Colab CLI and its security tests now load a tracked repository
script. The DPAPI mirror's security tests likewise no longer depend on an
absent ignored external checkout.

Both scripts were located in two existing C:\dev worktrees and matched their
original GitHub blobs after line-ending normalization. Exact upstream bytes
were recovered into `scripts/colab/colab_n8n_bridge.py` and
`scripts/security/key_mirror.py`. Their adjacent `SOURCE.md` files record Git
blob and SHA-256 identities. No cryptographic algorithm was changed, and no
live credential, vault or Colab profile was opened or modified.

The unified CLI now delegates to the tracked bridge. Existing assertions for
ciphertext-only storage, legacy migration and redacted status/probe outputs
remain. New tests verify real DPAPI roundtrip and wrong-entropy rejection with
dummy values, CLI help delegation, and passing a dummy token through the child
environment instead of process arguments. All 13 focused tests pass.

The full Python stage now collects 14,300 tests successfully. Its bounded run
passed 766 tests, skipped 9 and stopped after 5 failures: two refer to the absent
`kindle-app/www/static/polly-hf-chat.js`, and three lack the `neurogolf` module
needed by the ARC-style benchmark. These require separate component mapping;
no tests were removed or skipped to hide them. The complete repository suite
is not yet green. The preceding turn's full TypeScript result remains 6,741
passing tests; this turn changed no TypeScript runtime code.

Restoration proves the tools can be loaded and exercised from this checkout.
It is not a full vault or backend-network security audit. Existing output
escaping, path integrity, atomicity and caller authorization deserve review
before these utilities become services. Source notes state those limits.

Before bytes, source proof, test logs, scoped map and final hashes are in
`artifacts/skill_dependency_recovery_20260909/`. Its separate
`TRAINING_REVIEW.md` records the now-complete Clay comparison, the verified
TRAIN/evaluation framing mismatch, a bounded unchanged-weight inference
diagnostic, and a voice sample made from an actual model output.
