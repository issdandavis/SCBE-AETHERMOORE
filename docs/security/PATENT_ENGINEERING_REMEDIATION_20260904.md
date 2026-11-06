# Patent engineering remediation — 2026-09-04

Scope: local engineering changes, not amendments to filed documents or a legal
claim-coverage opinion. Original patent evidence and Clay training are untouched.

## Pre-build system map

Baseline: `feat/trichromatic-state-chain`, HEAD
`8ac5000d8df462b64939ad911d30faf939d28b57`, pre-existing dirty worktree.
Inventory: `artifacts/patent_hardening_20260904/system_inventory.json`.
Post-change inventory: `artifacts/patent_hardening_20260904/system_inventory_after.json`.

| Node | Input -> output / consumer | Authority / status before repair |
|---|---|---|
| `src/symphonic_cipher/topological_cfi.py` | directed CFG -> embeddings, runtime verdicts | Primary Python; illegal known-block edges accepted |
| `symphonic_cipher/topological_cfi.py` | same contract via legacy package | Duplicate Python; same edge hole, stale directed-graph test |
| `packages/kernel/src/hamiltonianCFI.ts` | CFG/state stream -> runtime verdicts | TS exported by `src/harmonic/hamiltonianCFI.ts`; undirected analysis mixed with enforcement |
| Both `symphonic_cipher/scbe_aethermoore/constants.py` trees | base strength + geometry -> reported strength | Unsupported security-bit inflation |
| Both `symphonic_cipher/scbe_aethermoore/pqc/pqc_harmonic.py` trees | geometry/algorithm labels -> reports and table | Unsupported work-factor and AES-equivalence claims |
| Both `symphonic_cipher/scbe_aethermoore/dual_lattice.py` trees | simulated results/time -> purported key | Demonstration, not real PQC; unsafe as a default security API |
| `src/crypto/rwp_v3.py`, `src/crypto/pqc_liboqs.py` | actual KEM/signature + AEAD -> authenticated envelope | Existing real backend; pre-existing edits, preserve |
| Preserved sources in `C:/dev/patent-evidence-20260820` | specification -> claim/evidence comparison | Immutable reference, not edited |

Exact policy will remain separate from geometric anomaly signals. Frozen directed
edge membership authorizes transitions; curve proximity cannot add permissions.
Original CFG mutation must not silently change an initialized monitor's policy.
Loops are legal only when explicitly in the original directed policy.

Plan: add failing counterexamples, repair both Python routes and the TS runtime,
separate governance scores from cryptographic strength, fence the simulated wave
engine from production use, and run focused plus affected compatibility tests.

Budget: local CPU tests with bounded threads, no new dependencies, no cloud
compute, no model/checkpoint changes. No commits/pushes or deployment. Changes are
limited to named source/test files and this engineering note; rollback is a review
of this task's patch, never a reset of the shared dirty worktree.

## Proof boundary

- Exact edge rejection is ordinary CFI enforcement, not proof that geometry alone
  detects all malicious computation or control-flow bending within legal edges.
- Dimensional embedding does not change original graph connectivity.
- Geometry remains useful as a scoring/representation mechanism; it does not add
  cryptographic key entropy or independently certified work factors.
- A public sinusoidal time function is visualization, not secure key release.
- Global Lyapunov stability and complete timing/event-indistinguishability remain
  open proof obligations. No new proof is implied by passing unit tests.

## Verification

Completed locally on September 4, 2026, approximately 18:17 PDT. The initial
18-case Python regression suite produced **16 failures and 2 passes before the
repair**. The expanded 24-case suite now passes. No GPU/cloud training was used.

| Check | Result | What it establishes |
|---|---|---|
| New regressions plus directed-graph, patent-math and real-PQC regression files | 57 passed, zero skipped | Both Python copies reject unauthorized edges; existing native crypto checks still work |
| `tests/test_aethermoore.py`, import explicitly pinned to `src` | 56 passed | Primary callers accept the corrected baseline-only reporting contract |
| Same suite, import explicitly pinned to repository root | 56 passed | Legacy callers use the same contract |
| `src/symphonic_cipher/tests/test_patent_modules.py` | 16 passed | Primary compatibility harness uses declared execution policy |
| `symphonic_cipher/tests/test_patent_modules.py` | 16 passed | Legacy compatibility harness uses declared execution policy |
| Both TypeScript CFI suites | 51 passed | Directed enforcement, immutable policy, safe reset and preferred-path validation |
| Strict standalone TypeScript check of `packages/kernel/src/hamiltonianCFI.ts` | Passed | Type correctness of the modified module; not a repository-wide build |
| Black check of new/updated top-level Python tests; Prettier check of modified TS files | Passed | Selected-file formatting |

These are 252 test executions, including repeated compatibility cases against
different import paths, **not 252 independent security proofs**. Native-PQC tests
were not skipped. The legacy patent harness is a compatibility test, not evidence
for its historical claims of multiplied quantum resistance.

Exhaustive finite oracles, per Python copy:

- All **4,165** loopless directed graphs on 1–4 vertices against a brute-force
  Hamiltonian-path oracle.
- All **530** directed policies on 1–3 vertices including self-loops, checking
  every ordered block pair: **4,674** transition checks per copy.
- The four-block chain's nine illegal non-self jumps that previously passed now
  all fail; missing self-loops are denied too. Explicit cycles remain allowed.

Pytest used `--noconftest -o addopts='' -p no:cacheprovider` and
`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `PYTHONDONTWRITEBYTECODE=1`,
`OMP_NUM_THREADS=2`, `MKL_NUM_THREADS=2`. This avoids unrelated global fixtures
and extra caches while another task owns the shared workspace. Two warnings
about disabled asyncio-plugin configuration remain; they are not test failures.
Vitest warns about pre-existing esbuild/oxc options; selected suites pass.

Core reproduction commands (PowerShell, repository root):

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:PYTHONDONTWRITEBYTECODE='1'
$env:OMP_NUM_THREADS='2'
$env:MKL_NUM_THREADS='2'
python -m pytest --noconftest -o addopts='' -p no:cacheprovider -q tests/test_patent_security_regressions.py tests/test_topological_cfi_hamiltonian.py tests/governance/test_patent_math_support.py tests/crypto/test_pqc_liboqs_status.py tests/crypto/test_rwp_v3_pqc.py
node node_modules/vitest/vitest.mjs run tests/harmonic/hamiltonianCFI.security.test.ts tests/harmonic/hamiltonianCFI.test.ts --maxWorkers=1 --no-file-parallelism
node node_modules/typescript/bin/tsc --ignoreConfig --noEmit --target ES2022 --module NodeNext --moduleResolution NodeNext --strict --skipLibCheck packages/kernel/src/hamiltonianCFI.ts
```

Run the two `test_patent_modules.py` files in separate pytest processes, because
their existing import conventions share module names. For the AETHERMOORE suite,
start a fresh Python process, prepend either `src` or `.` to `sys.path`, import
`symphonic_cipher.scbe_aethermoore.pqc.pqc_harmonic`, print `__file__` to verify the
selected implementation, then call `pytest.main` with the same flags and
`tests/test_aethermoore.py`.

## Updated contracts and reuse map

- Python: `initialize(cfg)` freezes the integer block IDs and directed edges.
  `verify_execution_path` now requires canonical string IDs from that policy;
  arbitrary unique names cannot authorize. Failed initialization revokes the old
  policy. Consumers must accept only `CFIResult.VALID` / `valid == True`.
- TypeScript: construction freezes policy. `setGoldenPath` validates and copies
  its input. Every subsequent step must use a legal directed edge, including
  wraparound. Non-VALID results latch rejection until a trusted reset. The first
  event establishes a start block; authentication of entry points is external.
  `analyzeGraph`, `hasEdge` and `getNeighbors` retain undirected diagnostic
  semantics for compatibility; use `hasDirectedEdge` for execution permissions.
- `security_bits` and `security_level` return the caller-supplied baseline.
  `harmonic_scale` still provides the geometric score. Analysis reports preserve
  `H_value` and expose `governance_multiplier`; `computational_multiplier` and
  `equivalent_aes` are now null, `enhancement_bits` is zero, and unknown algorithm
  labels raise `ValueError`. Baseline numbers are nominal metadata, not backend
  certification or an exact quantum attack-cost assessment.
- The historical `scbe_aethermoore/dual_lattice.py` constructor now refuses use
  unless `allow_simulation=True` is explicitly supplied. Simulation results are
  marked `simulation_only`. This preserves visualization/research, **not secure
  time-based key release**. No production caller should enable the simulation
  just to make an error disappear. Use the existing real KEM/signature/AEAD path
  with explicitly required PQC instead. Other modules with similar names are not
  automatically audited by this change.
- Reused the primary tree's directed-graph implementation in the legacy tree;
  retained geometry and the real native-PQC implementation. The needed building
  blocks existed locally, so no additional GitHub repository was needed here.

Changed source paths are the seven original map targets, plus both
`scbe_aethermoore/pqc/pqc_harmonic.py` files. Changed tests are the two new CFI
security suites, `tests/test_aethermoore.py`, and both existing
`symphonic_cipher/tests/test_patent_modules.py` files. Exact scope and outcomes
are also in `artifacts/patent_hardening_20260904/verification.json`.

## Remaining proof work / next resume point

1. Connect trustworthy CFG extraction and complete runtime instrumentation to
   the exact-edge monitor. Test real programs, legal-edge attacks, policy update
   authorization and measured overhead. Unit tests cannot prove those surfaces.
2. For an expiring key-release feature, specify identity, secret material,
   authenticated policy, replay protection and trusted time. A sinusoidal wave
   is not a replacement for any of these. Native PQC alone does not establish
   the full protocol's security.
3. Establish a whole-system Lyapunov argument or narrow the stability claim;
   separately measure timing, output-length and event leakage of fail-to-noise.
4. To test benefit to Clay, run held-out, matched-budget, multi-seed ablations of
   geometry/multiview features. This security patch is not a training result.
5. Obtain the authoritative filed nonprovisional artifact before asserting that
   a draft's claim set exactly matches the filing. No filing was amended here.

No commits, source-repository pushes, deployment, paid compute, model changes or
patent-source edits were performed. The shared context ledger records this task
separately under `patent-hardening-20260904`. Review and revert only this task's
individual hunks if needed; never reset the pre-existing dirty worktree.
