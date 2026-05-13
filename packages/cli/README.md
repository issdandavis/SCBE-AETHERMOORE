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
scbe demo
scbe demo --json
scbe selftest
scbe doctor --json
scbe credits
scbe shell
scbe run "npm test"
scbe status
scbe history --limit 20
scbe ca-plan --ops "abs abs add" --json
scbe compile ca --opcodes "0x09 0x09 0x00" --target python
scbe render-op --op add --target KO --a left --b right
scbe route --program "encode \"run tests\" in tongue KO"
```

The same binary is also exposed as `geoseal` and `scbe-geoseal`.

## Tool Surface

- `version`: prints the installed `scbe-aethermoore` package version.
- `demo`: runs the 5-minute agent safety demo. It sends a risky AI-agent tool
  request through the GeoSeal execution gate and prints the governed output
  packet: output, decision, reasons, suggested correction, and audit id.
- `doctor --json`: verifies the installed GeoSeal shell and reports available
  API-routed commands.
- `selftest`: runs the npm-installable smoke test (`version` + `doctor`).
- `credits`: prints the hosted-run intake, service-credit policy, and top-up
  links for paid hosted work.
- `shell`: opens the SCBE terminal wrapper.
- `run`: executes a normal shell command with Compass metadata, Clock metadata,
  GeoSeal governance, exit-code preservation, and JSONL history.
- `status`: prints local terminal/compiler/router capability status.
- `history`: prints recent SCBE terminal runs.
- `ca-plan`: resolves Cassisivadan operation names into canonical opcode bytes.
- `compile ca`: compiles CA opcode bytes into target source (`python`,
  `typescript`, or `go`) with a round-trip trace.
- `render-op`: renders one cross-language conlang/code operation template.
- `route`: parses Aether++ speech-to-code source into a governed route packet.

The full repo-local GeoSeal command set still lives in `scbe-aethermoore`.
Commands that require Python repo modules need a source checkout or a backend
API configured with `SCBE_API_BASE`.

## Five-Minute Magic Moment

The first product proof is intentionally small:

```bash
npm i -g scbe-aethermoore-cli
scbe demo --json
```

The demo does not execute the risky command. It shows what happens when SCBE is
placed between an AI agent and its tools:

- the proposed tool call,
- the governance decision,
- reason codes,
- a suggested correction,
- a deterministic GeoSeal audit id.

This is the buyer-facing promise: put SCBE in front of an AI agent and see what
it catches, why it caught it, and what audit trail it leaves behind.

## Local Compiler Lane

From a source checkout, the CLI exposes the local speech/code compiler directly:

```bash
scbe compile plan --ops "abs abs add" --json
scbe compile ca --opcodes "0x09 0x09 0x00" --target typescript --fn score --args a,b
scbe route --program "encode \"run tests\" in tongue KO"
```

This is the start of the SCBE terminal shape: conlang routing, code-language
emission, command execution, and governance should be reached from one command
surface instead of hidden Python scripts.

## SCBE Terminal Lane

Use `scbe run` when you want a normal command to behave like a governed SCBE
operation:

```bash
scbe run "npm test"
scbe run "python -m pytest tests/system -q" --json
scbe history --limit 10
```

Each run records:

- Compass: inferred lane, language, and intent.
- Clock: timestamp, timezone, and duration.
- Governance: local GeoSeal execution-gate result.
- Outcome: exit code, pass/fail, and first failure classification.

Use `scbe shell` to stay inside that wrapper while typing normal terminal
commands.

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
