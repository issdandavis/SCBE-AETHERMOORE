# scbe-aethermoore-cli

`scbe-aethermoore-cli` is the terminal interface for SCBE-AETHERMOORE. It exposes
the GeoSeal shell from the main `scbe-aethermoore` package under small-agent
friendly commands.

## Install

```bash
npm i -g scbe-aethermoore-cli
```

## Commands

```bash
scbe --help
scbe doctor --json
scbe toolbox --json
scbe calc --expr "sqrt(2)^2 + phi" --json
scbe dimensions --unit "kg*m/s^2" --json
scbe web-search --query "site:docs.python.org pathlib" --json
scbe url-fetch --url https://example.com --json
scbe terminal-ui
scbe agent-bus-ui
scbe agent-bus-server --port 8787
scbe agent-bus-send --task "review changed files" --json
scbe tokenizer-code-lanes --command shl --tongues KO,AV --json
```

The same binary is also exposed as `geoseal` and `scbe-geoseal`.

## Tool Surface

- `calc`: deterministic arithmetic with `pi`, `tau`, `phi`, and common math
  functions.
- `dimensions`: SI dimensional analysis over base and common derived units.
- `web-search`: no-key public web lookup through DuckDuckGo Instant Answer.
- `url-fetch`: public HTTP/HTTPS fetch with text preview and SHA-256 receipt.
- `terminal-ui`: optional menu mode over the safe local tools and public no-key lookup helpers.
- `agent-bus-ui`, `agent-bus-server`, `agent-bus-send`: terminal frontend,
  local HTTP backend, and one-shot dispatch bridge for `scbe-agent-bus`.
- `tokenizer-code-lanes`: code command to tongue-scoped binary/hex lanes.
- `verify-code-lanes` and `decode-code-lanes`: lane packet verification and
  decode tools.

Remote API commands are routed through the installed `scbe-aethermoore` GeoSeal
shell. Local tools do not send secrets to remote models.

## Self Test

```bash
scbe selftest
```
