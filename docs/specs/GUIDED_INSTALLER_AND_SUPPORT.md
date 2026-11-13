# Guided installer and support contract

Status: design contract; no GUI installer or telemetry endpoint is claimed by
the `4.3.4` candidate.

## Goal

Give a new user one download/setup interface that defaults to the smallest
verified security surface, explains every optional cost before installation,
and can produce a privacy-preserving issue report when something fails.

## Wizard sequence

1. Detect OS, architecture, free disk, Python, Node, and package-manager
   versions locally.
2. Recommend **Light scanner** unless the user selects another job.
3. Show package names, estimated download/install size, commands, permissions,
   network use, and rollback steps.
4. Let the user add independent feature cards rather than one opaque `full`
   button.
5. Display the exact command and require confirmation before package-manager or
   cloud actions.
6. Run first-use proofs and save a local receipt.
7. On failure, offer **View report**, **Copy report**, **Open GitHub issue**, and
   an unselected **Send diagnostic** option.

## Profiles

| Profile | Components | Default | Current status |
| --- | --- | --- | --- |
| Light scanner | Python scanner, located findings, local receipts | Yes | Verified |
| Node SDK | Precompiled CommonJS/ESM SDK and scanner CLI | No | Verified |
| Agent controls | Agent bus, local server, workspace/event receipts | No | Verified |
| Geometry/governance | NumPy and schema extras | No | Verified packaging; capability tests remain feature-specific |
| MCP/vision/model | Named optional extras | No | Opt-in integrations |
| PQ transport | Real KEM + signature provider, key lifecycle, signed receipts | No | Future until clean-installed cryptographic round trip passes |
| Hosted credits | Scoped API token, prepaid balance, model router | No | Future; see `HOSTED_CREDITS_AND_MODEL_ROUTER.md` |
| Full lab | All non-model extras plus selected developer tools | No | Advanced/source users only |

## Cloud compiler and binaries

The wizard should prefer registry artifacts. If a native artifact is unavailable
for the user's OS/architecture, offer these routes in order:

1. download a signed release binary with checksum and provenance;
2. start a reproducible GitHub Actions/cloud build after showing source commit,
   target triple, estimated duration, and any cost;
3. generate a local cross-compile command without running it;
4. fall back to the verified pure Python/JavaScript profile.

Cloud compilation is never a hidden fallback. A build result must identify the
source commit, toolchain, target, artifact hash, SBOM, and signer.

## Diagnostic report schema

Diagnostics are off by default. The local report may contain:

- SCBE package and installer versions;
- selected profile and install phase;
- OS family/architecture and major runtime versions;
- package-manager exit code and a stable SCBE error code;
- dependency names/versions involved in the failure;
- hashed stack signature and pass/fail checks;
- user-written description, if supplied.

The report must exclude by default:

- prompts, model outputs, source files, datasets, and file contents;
- full paths, usernames, hostnames, IP addresses, device identifiers, and cloud
  account IDs;
- environment-variable values, API keys, tokens, cookies, and credentials;
- command history and unrelated process lists.

Before any upload, show the complete JSON payload, let the user remove fields,
name the destination and retention policy, and require an unchecked consent
box. A failed upload leaves the local receipt intact and never blocks use.

## Implementation gates

- Build the first interface as a command generator/validator; do not let a web
  page claim it installed software when the browser only copied commands.
- Sign installer artifacts and publish checksums.
- Test clean Windows, macOS, and Linux virtual machines for every profile.
- Measure download bytes, installed bytes, time, and rollback residue.
- Threat-model update channels and diagnostic ingestion before enabling either.
- Keep the issue collector separate from training data. User diagnostics enter
  model training only through a later explicit, reviewed consent pipeline.
- Keep paid routing separate from local installation. The hosted economic and
  security contract is defined in `HOSTED_CREDITS_AND_MODEL_ROUTER.md`.
