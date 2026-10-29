# Python Dependency Security

Status: active

Last verified: 2026-10-29

The Python dependency graph spans root requirements snapshots, tool-specific
requirements files, and a nested `uv.lock`. Auditing whichever packages happen
to be installed on a CI runner does not audit those files. The repository-wide
auditor instead discovers every active exact pin, queries each unique
package/version once, and maps a vulnerability back to every file that contains
it.

## Commands

Install the pinned scanner, then run the same blocking check used by CI:

```powershell
python -m pip install "pip-audit==2.10.1"
npm run security:audit:pip
```

Write the aggregate evidence artifact:

```powershell
python scripts/security/pip_audit_all.py --report pip-audit-report.json
```

List every discovered surface and its exact-pin count without querying the
registry:

```powershell
python scripts/security/pip_audit_all.py --list
```

The scanner reads exact `==` entries from requirements files and registry-backed
packages from `uv.lock`. It does not install project code or execute package build
scripts. Range-only, editable, VCS, and direct-URL entries are counted as skipped
because they do not identify one registry version; recursive Dependabot coverage
monitors those manifests and their resolved locks.

## Enforcement

- `.github/workflows/python-security-gate.yml` runs on Python dependency pull
  requests, on relevant pushes, and daily. It tests the inventory parser, blocks
  any known advisory or scanner coverage error, uploads the JSON report, and runs
  GitHub dependency review.
- `.github/workflows/security-checks.yml` uses the same repository-wide command
  as a blocking main-branch check.
- `.github/workflows/weekly-security-scan.yml` reports audited surfaces,
  vulnerable packages, advisory counts, and scanner errors in the rolling issue.
- `.github/dependabot.yml` recursively covers pip manifests throughout the
  monorepo and groups compatible security updates.
- `tests/security/test_pip_audit_all.py` protects discovery, requirements/hash
  parsing, uv registry filtering, finding attribution, security floors, and
  workflow wiring.

The root dependency snapshot submitted to GitHub comes from
`requirements-lock.txt`. Therefore a fix is incomplete until both the declaring
manifest floor and every affected exact lock/snapshot entry are safe.

## Remediation rules

1. Use the highest first-patched version required across all advisories for that
   package; prefer a minimal compatible upgrade over an unrelated major update.
2. Regenerate native lock formats with their own resolver (`uv lock` for
   `uv.lock`) and run its frozen/check mode afterward.
3. If an unused parent package pins a vulnerable transitive dependency, remove
   that parent rather than publishing an internally inconsistent lock.
4. Regenerate hashes when a hashed requirement changes, then validate a
   `--require-hashes` install or download.
5. Run the affected package tests and the aggregate scanner before merging.

The 2026-10-29 repair applied these rules to the root snapshot, lint lock,
binary-build hash lock, and `examples/SCBEAgent/uv.lock`. The unused AWS
OpenTelemetry bundle was removed from all three AgentCore example manifests. The
Strands tools bundle was also removed because its current Pillow ceiling forces a
vulnerable release. `SCBEAgent` and `TestAgent` did not use it; `MyAgent` now uses
the supported `bedrock-agentcore` `code_session` API documented in the
[AgentCore Code Interpreter guide](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/code-interpreter-building-agents.html).

## Verification record

The post-remediation live audit covered 17 dependency surfaces and 225 unique
exact package/version pairs. It reported zero vulnerable packages, zero known
advisories, and zero scanner errors. The SCBEAgent lock resolved in frozen mode,
installed into a clean environment, imported the real agent module, and returned
its system configuration. Root requirements also completed a clean Python 3.12
resolve, the root wheel built, and the hashed binary-build requirements passed a
`pip download --require-hashes` check on Windows.
