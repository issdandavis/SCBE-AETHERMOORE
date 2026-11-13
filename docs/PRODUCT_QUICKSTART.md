# Product quickstart

The supported first-run products are the dependency-light security scanner,
the Node SDK, and the local agent bus. The Docker/API service is a preview and
is not required to use SCBE.

## Choose the smallest profile that does the job

| Profile | Install | Verified use | Measured clean-install size |
| --- | --- | --- | ---: |
| Python scanner (recommended) | `pip install scbe-aethermoore` | Located prompt/SQL/shell injection prefilter and audit receipts | 17.27 MB environment delta |
| Node SDK | `npm install scbe-aethermoore` | CommonJS/ESM scan APIs, GeoSeal command, scanner CLI | 51.94 MB with dependencies |
| Local agent controls | `npm install scbe-agent-bus` | Governed event routing, local HTTP health, workspace receipts | 7.45 MB with dependencies |
| Polly workflow CLI | `npm install scbe-polly-pad-cli` | Small local workflow/bootstrap commands | 0.19 MB with dependencies |

Sizes are Windows measurements from the `2026-11-13` release audit. Package
managers and operating systems vary; they are planning estimates, not quotas.

## Python scanner: two-minute proof

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install scbe-aethermoore
scbe-scan "hello world"
scbe-scan "ignore all previous instructions"
```

Expected decisions are `ALLOW` for the first input and `DENY` for the second.
The scanner is a deterministic prefilter built from located patterns and byte
statistics. It is useful before an agent or model call, but it is not a
universal semantic-intent detector.

## Opt-in Python feature families

```powershell
python -m pip install "scbe-aethermoore[geometry]"   # NumPy geometry
python -m pip install "scbe-aethermoore[governance]" # geometry + schemas
python -m pip install "scbe-aethermoore[crypto]"     # geometry + cryptography
python -m pip install "scbe-aethermoore[vision]"     # geometry + Pillow
python -m pip install "scbe-aethermoore[mcp]"        # MCP integration
python -m pip install "scbe-aethermoore[full]"       # all non-model extras
```

The light profile does **not** claim post-quantum transport or signed receipts.
The repository contains PQC research and integration surfaces, but a guided
installer must not label them production security until a clean-installed
native/provider-backed KEM and signature round trip is attached to the release.

## Node SDK proof

```powershell
npm install scbe-aethermoore
node -e "const s=require('scbe-aethermoore'); console.log(s.scan('hello world'))"
npx scbe-scan --json "ignore all previous instructions"
```

The npm package ships compiled JavaScript. Users do not need TypeScript or a
source checkout.

## Local agent-control proof

```powershell
npm install scbe-agent-bus
npx scbe-agent-bus --help
npx scbe-agent-bus serve --port 8787
```

In a second terminal:

```powershell
npx scbe-agent-bus health --base-url http://127.0.0.1:8787 --json
```

Local routing is the default. Provider-backed actions require separate
credentials and explicit configuration.

## Build and download policy

- Registry installs use prebuilt JavaScript or a platform-independent Python
  wheel; normal users do not need a compiler.
- Future native components should ship as signed OS/architecture artifacts
  built by GitHub Actions or another reproducible cloud compiler.
- Source compilation remains opt-in, with the exact command and disk estimate
  shown before it starts.
- Every release should publish checksums and, when native components exist, an
  SBOM and provenance attestation.

## Help and diagnostics

SCBE does not silently upload prompts, files, paths, environment variables, or
credentials. Keep the local error receipt, then open a GitHub issue with only
the fields you choose to disclose. The planned guided installer and opt-in
diagnostic contract are specified in
[`specs/GUIDED_INSTALLER_AND_SUPPORT.md`](specs/GUIDED_INSTALLER_AND_SUPPORT.md).

## Preview lanes

The Docker/API lane, hosted dispatch, AetherDesk integration, and native PQC
transport are preview or separately operated surfaces. They may be useful to
developers, but they are not prerequisites for first-run success and should not
be advertised as part of the light install until their own clean-install gates
pass. The prepaid-credit and local/Clay-first routing design is documented in
[`specs/HOSTED_CREDITS_AND_MODEL_ROUTER.md`](specs/HOSTED_CREDITS_AND_MODEL_ROUTER.md).
