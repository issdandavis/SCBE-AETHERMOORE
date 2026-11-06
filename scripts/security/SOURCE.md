# Local DPAPI mirror source

`key_mirror.py` is the existing owner-maintained script from
`issdandavis/codex-skills-live`,
`scbe-api-key-local-mirror/scripts/key_mirror.py`.

- Git blob: `0f482baed68b6f9dd11c4886e395fe999f1fc483`
- SHA-256: `f132c6cf550fed32d32c0f2b32b87852c3fc289539d3d83f6d4a5522ca680ae0`
- Size: 10,475 bytes; upstream bytes preserved without algorithm changes.
- Verified 2026-09-09 against GitHub and two existing C:\dev worktree copies
  after local CRLF normalization.

This component requires Windows DPAPI. Importing it binds Windows functions;
vault operations require explicit calls. Tests use temporary vaults and dummy
values to exercise real encryption, decryption and wrong-entropy rejection.
No live user credential was opened, mirrored, resolved or displayed during
recovery. The CLI supports intentionally revealing values with `--raw` and
`--env-out`; those features were not used against live credentials.

The recovered version is a functional baseline, not a complete vault security
audit. In particular, path integrity, atomicity/concurrency, output escaping
and caller authorization require separate review before service integration.
