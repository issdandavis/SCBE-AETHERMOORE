# SCBE package release audit — 2026-11-13

Status: `4.3.4` synchronized npm/PyPI candidate verified locally; **not
published**.

## Market report

| Surface | Version / state | Functional result | Measured footprint | Verdict |
| --- | --- | --- | --- | --- |
| PyPI current | `4.3.2`, registry | `5/5` installed commands pass | package 15,427,454 B; environment delta 178,048,901 B; 52 distributions | Works, but the default dependency declaration is a space and supply-chain failure. Do not market it as lean. |
| PyPI current, forced `--no-deps` | `4.3.2`, registry | `5/5` pass | 15,427,454 B; 2 distributions | Proves the scanner and CLIs did not need the 51 extra distributions. This was diagnostic, not an installation recommendation. |
| PyPI candidate | `4.3.4`, local wheel | `5/5`; all four clean-installed entry points pass; README scanner examples pass | wheel 2,286,144 B; package 7,673,184 B; environment delta 17,274,604 B; 2 distributions | **Release candidate.** Default install is dependency-free; numerical, governance, crypto, vision, MCP, and ML stacks are explicit extras. |
| npm current suite | registry releases | `9/9` published command claims pass | root 8,411,249 B; CLI 979,434 B; bus 1,108,062 B; Polly 162,789 B | Existing products work. Versions are not synchronized across packages. |
| npm candidate suite | local packages | `10/10` command claims plus CommonJS, ESM, scanner, GeoSeal, agent-bus API/server and governed-task consumer smoke | root 8,470,703 B / 51,936,413 B installed; CLI 1,442,342 B / 53,559,394 B; bus 1,250,933 B / 7,453,243 B; Polly 190,133 B / 192,235 B | **Root `4.3.4` candidate passes.** CLI local `4.5.0` is older than registry `4.5.2`, so it must not be republished. Polly `0.2.0` needs its own release decision. |

The npm strict pack receipt reports a 1,909,163-byte compressed root tarball,
1,407 entries, and a clean content guard.  The production dependency audit is
zero vulnerabilities after refreshing transitive `@hono/node-server` to
`2.1.8` and `hono` to `4.13.18`.  Five moderate development-only findings may
remain outside `--omit=dev`; they are not shipped runtime dependencies and
should be handled in a separate toolchain update.

## What sold

- The dependency-light Python scanner is a concrete AI-security product: it
  locates prompt/SQL/shell injection signals, returns deterministic decisions,
  and works immediately after a normal wheel install.
- The npm SDK exposes CommonJS and ESM APIs plus a working `scbe-scan` command.
- The agent bus installs in about 7.45 MB with dependencies and proves local
  server health, API exports, and a governed task path from a clean consumer.
- Polly Pad remains the smallest workflow surface at about 192 KB installed.
- Release harnesses now use disposable caches and remove temporary installs and
  tarballs, so verifying the products does not steadily consume the PC.

These checks prove packaging and declared behavior.  They do not prove that the
scanner catches every attack or that the research geometry improves a learned
model.

## What did not sell

- Published PyPI `4.3.2` pulled 178 MB and 52 distributions for a scanner that
  runs with the standard library.  Optional feature dependencies were wrongly
  presented as mandatory runtime dependencies.
- `scbe-convert-to-sft` initially crashed in the lean wheel because importing
  the historical `symphonic_cipher` facade eagerly imported NumPy.  The
  `scbe_aethermoore.sft_cli` launcher now loads the standard-library leaf
  converter without importing that facade.
- The Python wheel still contains 497 entries, including legacy test-like
  modules, and exposes a generic top-level package named `python`.  At 2.29 MB
  compressed it is not a disk hog, but it is not a minimal scanner-only wheel.
  Rename/remove the generic namespace in the next major version.
- The Docker/API surface is still `preview`; it is not the primary product
  door.  AetherDesk is external and was not independently checked in this
  worktree.

## Build and compiler boundary

Normal users do not need the development compiler:

- npm receives precompiled JavaScript in `dist/`;
- PyPI receives a platform-independent `py3-none-any` wheel;
- this worktree reuses the primary checkout's existing `node_modules` through a
  directory junction instead of storing another dependency tree.

If native Rust/C/C++ components become part of a later release, build a signed
OS/architecture matrix in GitHub Actions or another cloud compiler and attach
checksums/SBOMs.  Keep source compilation as an opt-in route.  No native binary
or cross-compiler product is claimed by this audit.

## Paid hosted-service boundary

The packages remain useful without an account: local scanning, deterministic
Clay actions, and local agent routing do not consume hosted credits.  A future
paid lane is specified separately in
`docs/specs/HOSTED_CREDITS_AND_MODEL_ROUTER.md`: scoped user API tokens,
prepaid worst-case reservation before dispatch, local/Clay-first routing,
provider-usage reconciliation, transparent service fees, and automatic spend
circuit breakers.  Stripe Checkout and Metronome are design choices for the
sandbox implementation; no wallet, payment endpoint, provider call, or live
billing state was created during this audit.

## Promotion gates and evidence

- npm usability: `packages/_usability/RECEIPT.json` — `10/10`.
- PyPI published baseline: `packages/_usability/PYPI_RECEIPT.json` — `5/5`,
  bloated dependency baseline.
- PyPI candidate: `packages/_usability/PYPI_LOCAL_LEAN_RECEIPT.json` — `5/5`.
- Packaging/version tests: `15/15`.
- Release-surface audit: `9/9` configured surfaces resolve; one expected warning
  for the external AetherDesk checkout.
- npm production audit: zero vulnerabilities.

Candidate artifacts:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `scbe_aethermoore-4.3.4-py3-none-any.whl` | 2,286,144 | `df5c4ffd82b6dcb57385ef215e1eb93ddb253274b7b447e6dd5f3787a1741419` |
| `scbe_aethermoore-4.3.4.tar.gz` | 2,076,477 | `705d911dcced194c9e606fdf042aee3ca55d0dd68e39093b86ea3a48deeae4a4` |

Publishing is an external state change and was not performed.  Before an
authorized publish, rerun the strict npm pack guard, clean-wheel gate, and
registry version check from the exact commit intended for release.
