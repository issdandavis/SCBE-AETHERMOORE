# npm Dependency Security

Status: active

Last verified: 2026-10-29

SCBE-AETHERMOORE contains independent npm dependency trees rather than one npm
workspace. A root-only `npm audit` therefore gives an incomplete result. The
repository-wide security path discovers every active `package-lock.json`, audits
each tree, aggregates the findings, and fails when a selected severity threshold
is reached.

## System map

```text
package.json + package-lock.json (each project)
                 |
                 +--> Dependabot recursive discovery
                 |          |
                 |          +--> dependency update PR
                 |                       |
                 +-----------------------+--> dependency-review (PR delta)
                                             + repository-wide npm audit
                                                        |
                                             build/test/release gates

Daily + weekly schedule --> repository-wide npm audit --> JSON artifact + rolling issue
```

The active lockfile-backed projects at the time of this verification are:

1. repository root
2. `apps/aether-desktop/shell`
3. `apps/mobile/pwa`
4. `conference-app`
5. `game/spiral-engine`
6. `packages/agent-bus`
7. `packages/cli`
8. `scbe-visual-system`
9. `services/scbe-shim`
10. `src`

The list is discovered at runtime. Adding a new active lockfile automatically
adds it to local and CI audits. Archived, generated, vendored, and external trees
are excluded in `scripts/security/npm_audit_all.py`; exclusions must be narrow and
reviewed when changed.

## Commands

Run the blocking high/critical gate from the repository root:

```powershell
npm run security:audit:npm
```

Produce a complete report, including low and moderate findings:

```powershell
python scripts/security/npm_audit_all.py --audit-level low --report npm-audit-report.json
```

List the dependency trees that will be audited:

```powershell
python scripts/security/npm_audit_all.py --list
```

Remediate in the affected project directory. Prefer the smallest compatible
direct dependency update or override, regenerate that project's lockfile with
scripts disabled, then build and test that project. Do not apply a forced major
upgrade without checking the migration and runtime behavior.

```powershell
npm install --package-lock-only --ignore-scripts
npm audit
```

## Enforcement

- `.github/workflows/npm-security-gate.yml` blocks pull requests and pushes when
  any active tree has a high or critical advisory, and runs every day to catch a
  newly published advisory even when the lockfiles have not changed.
- GitHub dependency review blocks a pull request that introduces a dependency
  with a high or critical known vulnerability.
- `.github/dependabot.yml` recursively monitors manifests and lockfiles and groups
  compatible security updates.
- `.github/workflows/weekly-security-scan.yml` reports aggregate counts for every
  npm project in one rolling issue. Trivy is intentionally not part of this npm
  path.
- Every public npm publish workflow performs a blocking audit before it can
  publish. The agent-bus workflow also runs its test suite, and the CLI workflow
  runs its self-test and package-content check.
- Agent-bus CI and formatting workflows use immutable `npm ci` installs so a
  Linux runner cannot silently rewrite cross-platform lockfile metadata.
- `tests/security/test_npm_audit_all.py` protects project discovery, thresholds,
  workflow wiring, recursive Dependabot coverage, and the no-Trivy decision.

GitHub documents recursive `directories` globbing and `exclude-paths` in the
[Dependabot options reference](https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference).
The audit flags and lockfile-only behavior are defined in the
[npm audit documentation](https://docs.npmjs.com/cli/v11/commands/npm-audit/).

## Publishing and rollback

The public packages are released only after their project tests and package
smoke checks pass. Publish in dependency order when several packages change:

1. `scbe-aethermoore`
2. `scbe-agent-bus`
3. `scbe-aethermoore-cli`

Publishing is performed by the existing GitHub Actions workflows using the
repository's npm token; credentials are never written to the checkout or logs.
If a release fails validation, do not reuse or overwrite an npm version. Correct
the source, increment the patch version, rerun the same gates, and publish the
new immutable version. For a bad published release, deprecate it and point users
to the last known-good or corrected version rather than unpublishing it.

## Verification record

The 2026-10-29 remediation began with 60 advisories across the ten active npm
trees. The post-remediation aggregate audit reported zero critical, high,
moderate, or low findings in all ten trees.

Local release evidence:

| Surface | Result |
|---|---|
| Aggregate auditor regression suite | 9 passed |
| GitHub Actions workflow lint | passed |
| Root package | typecheck, build, package guard, and clean-consumer tarball smoke passed |
| Root Vitest suite | 6,740 passed, 23 skipped; one load-sensitive p99 assertion missed by 5 ms during the parallel run and passed in an isolated 8-test rerun |
| Desktop shell | build passed; 21 tests passed |
| Mobile PWA | build passed; manifest JSON, service-worker syntax, registration, and output files verified |
| Conference app | typecheck and build passed; no tests are currently present |
| Spiral engine | build passed |
| Agent bus | typecheck and build passed; 708 tests passed; package dry-run passed |
| CLI | self-test and package dry-run passed; 7 MCP/task API integration tests passed against the exact agent-bus 0.5.0 tarball |
| Visual system | build passed; 153 tests passed |
| Cloudflare shim | typecheck and build passed |
| Standalone `src` tree | audit passed; its existing TypeScript root boundary is invalid and it currently contains no discoverable tests |

The GitHub pull-request checks provide the independent Linux/Node 20 validation.
Release tags must not be created until those checks pass.
