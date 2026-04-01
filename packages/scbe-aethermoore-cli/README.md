# scbe-aethermoore-cli

Standalone CLI for the published `scbe-aethermoore` core library.

Install:

```bash
npm install -g scbe-aethermoore-cli
```

This package intentionally exposes only npm-safe commands built on the core TypeScript library. It does not ship the Python operator stack, repo-only servers, Notion tooling, MCP probes, Docker helpers, or the broader SCBE monorepo runtime.

## Commands

```bash
scbe --help
scbe version
scbe info
scbe tongues list
scbe tongues encode KO "hello world"
scbe tongues encode KO 68656c6c6f --hex --no-prefix
scbe tongues decode "ko:kaa ko:sila ..."
scbe tongues decode "kaa sila ..." --tongue KO --hex
scbe policy suggest deploy
scbe policy required critical
scbe offline trust-state --keys-valid true --time-trusted true --manifest-current true --key-rotation-needed false --integrity-ok true
scbe offline gate diagnostics.run --laws-present true --laws-hash-valid false --manifest-present false --manifest-sig-ok false --keys-present false --audit-intact false --voxel-root-ok false
scbe selftest
```

## Notes

- `tongues encode` accepts UTF-8 text by default. Use `--hex` to encode raw hex bytes.
- `tongues decode` prints UTF-8 text by default. Use `--hex` to print the decoded bytes as hex.
- Repo-only operational commands are intentionally blocked in this package. Use the SCBE repository itself for those workflows.
