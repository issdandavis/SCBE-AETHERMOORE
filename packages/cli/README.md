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
scbe version
scbe selftest
scbe doctor --json
scbe credits
```

The same binary is also exposed as `geoseal` and `scbe-geoseal`.

## Tool Surface

- `version`: prints the installed `scbe-aethermoore` package version.
- `doctor --json`: verifies the installed GeoSeal shell and reports available
  API-routed commands.
- `selftest`: runs the npm-installable smoke test (`version` + `doctor`).
- `credits`: prints the hosted-run intake, service-credit policy, and top-up
  links for paid hosted work.

The full repo-local GeoSeal command set still lives in `scbe-aethermoore`.
Commands that require Python repo modules need a source checkout or a backend
API configured with `SCBE_API_BASE`.

## Free Local Use + Paid Hosted Runs

The CLI is free for local use. Use `scbe-agent-bus`, GeoSeal, local Node/Python,
and Ollama-first routing before spending credits.

When you want AetherMoore to run hosted routing, a governed report, a benchmark,
or provider/model-backed work, use:

```bash
scbe credits
```

That command prints:

- hosted run intake: https://aethermoore.com/SCBE-AETHERMOORE/hosted-run.html
- service credits: https://aethermoore.com/SCBE-AETHERMOORE/service-credits.html
- top-up: https://ko-fi.com/izdandavis

Credits are pay-as-you-go. Billable provider/model usage is passed through with
a 2-5% SCBE coordination fee.

## Self Test

```bash
scbe selftest
```
