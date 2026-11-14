# Prime-token packet-free source authority — 2026-11-14

Status: `IMPLEMENTED_AND_SYNTHETICALLY_TESTED_NOT_IN_LIVE_V7`

## Capability and boundary

The ordinary and retention controls can no longer establish source separation
with caller-supplied family labels. Every row must be recoverable from one
reviewed authority file, one hash-pinned source artifact, and one exact UTF-8
byte span. The final control prompt is either that exact span or the output of
one allow-listed deterministic transform over it. Its family identity is:

```text
packet-free-authority:<SHA-256(authority file)>
```

The authority file may admit data provenance. It cannot authorize training,
optimization, promotion, partial unfreezing, or tool dispatch.

## Node and edge map

```text
reviewed source artifact
  -- exact path + SHA-256 + byte count --> packet-free authority v1
  -- exact byte span + excerpt SHA-256 -> named deterministic transform
  -- transformed-text SHA-256 ---------> ordinary/retention source row
  -- authority-derived family ----------> material-case builder
  -- path/hash disjointness ------------> material source-family audit
  -- canonical row + authority receipt -> material source manifest v2
  -- re-open + re-hash + re-slice ------> runtime control evaluator
  -- separate reconstruction code ------> independent replay receipt
```

| Node | Authority | Output | Consumer |
|---|---|---|---|
| Source artifact | Exact local file bytes | SHA-256, byte count, spans | Authority validator |
| Packet-free authority | Reviewed `ADMITTED` JSON; no execution authority | Derived family ID and source receipt | Builder/runtime/replay |
| Source row | Exact source span plus named transform | Canonical text, bytes, provenance | Bundle writer |
| Source-family audit | Existing catalog manifests | Material paths and hashes | Cross-lane overlap gate |
| Source manifest v2 | Hashes all source inputs and both authorities | Immutable authority receipts | Runtime and replay |
| Runtime | Producer implementation | Packet-free control scores | Evidence aggregator |
| Independent replay | Separate span/hash reconstruction | Replay receipt | Promotion gate |

## Enforced invariants

- Human labels such as `python-cpython-documentation` are not family evidence.
- A supplied `source_family` must equal the authority-derived identity.
- The raw byte span must match `excerpt_sha256`; the allow-listed transform must
  reproduce the row text; and that exact text must match `content_sha256`.
- Supported transforms are identity UTF-8 and the audit pipeline's deterministic
  non-empty-line strip/join operation. Unknown transforms fail closed.
- Every admitted authority record is consumed exactly once.
- Material, ordinary, and retention lanes may share neither normalized source
  paths nor source-artifact hashes.
- Copying one artifact to another path does not create a new source family.
- The runtime repeats the producer validation before evaluating controls.
- Independent replay performs its own source-file, span, digest, family, and
  overlap reconstruction without importing the producer validator.
- All authority surfaces remain `NOT_AUTHORIZED` for training and execution.

## Controls and verification

Synthetic tests cover:

- valid exact-span reconstruction;
- multiline source reconstruction through the named strip/join transform;
- arbitrary family-label spoofing;
- altered text with a refreshed row digest;
- artifact drift after authority admission;
- authority escalation;
- an unconsumed authority record;
- identical artifacts under distinct ordinary/retention authorities;
- producer target tampering and independent source replay;
- runtime source-family relabeling.

Focused command:

```powershell
python -m pytest `
  tests\tokenizer\test_prime_token_packet_free_authority.py `
  tests\tokenizer\test_prime_token_material_cases.py `
  tests\tokenizer\test_prime_token_material_runtime.py `
  -q -p no:cacheprovider
```

Measured result: `28/28` focused tests passed. Black and Ruff passed on every
changed Python file. The complete tokenizer regression passed `392/392` in
62.96 seconds after the final producer-versus-independent-replay assertion was
added, then passed `392/392` again in 66.73 seconds after the pre-commit hook's
mechanical formatting.

## Live-system separation

The running v7 E92 and source-family watchers remain pinned to commit
`6db589b73da4d2de371c36edafcadec3d1897097` and their recorded source hashes.
This work is isolated on branch
`research/prime-packet-free-authority-20261114`; no live watcher, label file,
model weight, optimizer, promotion gate, or partial-unfreeze decision was
changed.

## Remaining gate

Real ordinary and retention sources still need reviewed authority files with
exact source artifacts, spans, excerpt hashes, transform identifiers, and final
text hashes. Candidate labels are not converted into authorities automatically.
Until those reviewed artifacts exist, material training, promotion, and partial
unfreezing remain `NONE`.

