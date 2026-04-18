# Expanded-First Naming Policy

This policy keeps the governance system readable without breaking executable identifiers.

## Rule

Use expanded names in prose first. Keep shortforms only when they are required for:

- repository names
- package names
- command names
- environment variables
- file paths
- protocol labels that must stay machine-stable

## Default Style

- Prefer `Sacred Tongues governance system` over `SCBE`
- Prefer `roundtable witness protocol` over `RWP`
- Prefer `post-quantum cryptography` over `PQC`
- Prefer `application interface` over `API`
- Prefer `command-line interface` over `CLI`
- Prefer `continuous integration` over `CI`

## Compatibility Rule

Executable names remain unchanged unless a separate refactor explicitly updates code, tests, and deployment surfaces together.

Examples:

- keep `SCBE-AETHERMOORE` when referring to the repository path or project identifier
- keep `scbe-system-cli.py` when referring to the actual command entrypoint
- keep tongue codes like `KO`, `AV`, `RU`, `CA`, `UM`, `DR` when a command or machine-facing protocol requires them

## Canonical Naming Targets

Use these expanded labels in human-facing docs whenever possible:

| Expanded Label | Legacy / Machine-Stable Shortform | Context / When to Use |
|---|---|---|
| Sacred Tongues governance system | `SCBE`, `SCBE-AETHERMOORE` | Use the expanded form in prose and headings. Keep the shortform only for repository paths, package names, and import statements. |
| governance and geometry core | `SCBE core` | Preferred when referring to the legacy mathematical and runtime engine. |
| multi-agent orchestration layer | `HYDRA` | Use the expanded form in prose. Keep `HYDRA` for layer-specific module names. |
| phase-breath hyperbolic governance mapping | `PHDM` | Expand in narrative text. Keep the shortform only where an existing file, command, or specification surface depends on it. |
| canonical compact representation profile | `SS1` | Use the full phrase in human-facing text. Keep `SS1` for internal profile identifiers and code surfaces. |
| roundtable witness protocol | `RWP` | Expand in documentation and comments. Keep `RWP` in protocol labels and code. |
| application interface gateway | `API Gateway` | Expand everywhere except where exact route prefixes, framework decorators, or published endpoint labels must stay unchanged. |
| command-line interface guide | `CLI Guide` | Expand in documentation. Keep `CLI` in command names, launcher text, and help output. |
| post-quantum cryptography | `PQC` | Expand in prose. Keep `PQC` in compliance checklists, library references, and implementation labels. |
| additional authenticated data | `AAD` | Expand except in cryptographic function signatures and implementation-specific parameter names. |
| hardware security module | `HSM` | Expand in documentation. Keep `HSM` in configuration keys and integration points. |
| transport layer security | `TLS` | Expand except in protocol specifications, certificate details, and cipher-suite lists. |
| continuous integration pipeline | `CI pipeline` | Expand in prose. Keep `CI` in workflow filenames, badges, and automation triggers. |
| governance runtime metadata | `SCBE runtime metadata` | Expand in prose. Keep the machine-stable label only where runtime artifacts or emitted fields already depend on it. |
| Six Sacred Tongues governance phases | `KO/AV/RU/CA/UM/DR` | Use the full phrase in prose. Tongue codes remain mandatory in machine-facing protocol and tokenizer logic. |
| HMAC-based key derivation function | `HKDF` | Expand except inside the actual `hkdf.ts` module, function calls, or test labels that depend on the shortform. |
| spectral identity | none | Use the full descriptive phrase for the eigenvalue-based agent fingerprint. |

## Scope

This policy applies first to:

- canonical state documents
- architecture overviews
- operator guides
- public-facing summaries

It does not force immediate renaming of code symbols, repo folders, or published command surfaces.
