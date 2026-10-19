# Companion repositories and dependency decisions

Baseline: 2026-10-07. Owner: issdandavis unless a third-party owner is named.
This map covers public companions referenced by the main code/docs and the product lanes under
review. It is not a claim that every repository on the account is needed or has been audited.

## Active candidates and archive boundaries

A companion becomes a required dependency only when a named deployment profile uses its artifact
or service. Record that choice, a full commit/artifact digest, a compatibility contract, and an owner.
Main-repository tests do not establish companion behavior.

| Repository | Reviewed head | Role and activation rule | Readiness finding / next evidence |
| --- | --- | --- | --- |
| [aetherbrowser](https://github.com/issdandavis/aetherbrowser) | 532ea8a11055a8451b7de2644cbac05a8199e21a | Standalone extraction of browser runtime and extension; choose it OR main as the shipping source for P2 | CI/toolchain exists, but provider bridge depends on absent standalone HYDRA and falls back to echo. Explicitly verify real provider operation, source sync and authorization before promotion |
| [six-tongues-geoseal](https://github.com/issdandavis/six-tongues-geoseal) | 312b74a60b9b803e60d60728a46b51891fa2714a | Optional stdlib tokenization/blend/GeoSeal CLI and polyglot demonstration | HMAC integrity envelope, visible payload, deterministic demo key fallback, no replay/freshness enforcement in verification; do not substitute it for the main authenticated-encryption/PQC contract |
| [phdm-21d-embedding](https://github.com/issdandavis/phdm-21d-embedding) | cdeb4862e040c341b3a2bed8fb503f10974193a2 | Optional embedding/dataset research, not automatically a runtime dependency | README advertises PHDMEmbedder, but inspected tree has a spaceflight analogy module and dataset scripts, not that importable package. Resolve artifact and vector schema before using in a model-serving profile |
| [scbe-aethermoore-demo](https://github.com/issdandavis/scbe-aethermoore-demo) | 5a1e0369b69e4a0da482063de190d47dc1b99844 | Optional public demonstration and experiments for P5 | Reproduce each advertised benchmark and public flow; README claims are not measured production evidence |
| [Entropicdefenseengineproposal](https://github.com/issdandavis/Entropicdefenseengineproposal) | c28e873f90fd9eca394dab45606185af8947d92f | Optional Vite/Figma proposal UI | Install/build/preview and content checks if published; a proposal UI is not an operational security engine |
| [scbe-agents](https://github.com/issdandavis/scbe-agents) | effc778f4d31ed674616b63a94590a4273803271 | Archived agent snapshot; **not a maintained P4 runtime source** | Main HYDRA/MCP docs point here, while this README points back to main. Resolve canonical runtime and ownership, then test an actual dispatched tool |
| [spiralverse-protocol](https://github.com/issdandavis/spiralverse-protocol) | 14e5aa4e3a39a957559ac92b4a047340e798fd2c | Archived protocol/history reference; opt-in compatibility only | Pin legacy use and specify migration; do not treat old tongue/domain descriptions as current runtime authority |

Head SHAs were read from each default branch, not inferred from repository “last pushed” timestamps.
README/tree and selected source inspection support this map; no companion was deployed or had its
full suite run in this review. Demo/proposal/archive entries received a narrower metadata/README review.

## Standalone browser: source findings to resolve

At the pinned head:

- [serve.py](https://github.com/issdandavis/aetherbrowser/blob/532ea8a11055a8451b7de2644cbac05a8199e21a/src/aetherbrowser/serve.py)
  configures wildcard CORS and accepts /ws before any explicit authentication or origin validation
  in that handler. CORS middleware does not establish WebSocket authorization. Keep the standalone
  profile blocked for remote/multi-user exposure until authentication, origin policy, session
  isolation, quotas and approval binding are proven. Test local-browser threat cases too.
- [model_bridge.py](https://github.com/issdandavis/aetherbrowser/blob/532ea8a11055a8451b7de2644cbac05a8199e21a/src/aetherbrowser/model_bridge.py)
  imports hydra.llm_providers optionally and emits echo responses when keys/provider creation are
  unavailable. The inspected standalone tree has no HYDRA package. A successful response or
  /health status can therefore be a demonstration fallback, not a working model service.
- [router.py](https://github.com/issdandavis/aetherbrowser/blob/532ea8a11055a8451b7de2644cbac05a8199e21a/src/aetherbrowser/router.py)
  selects preferred providers by role/complexity and tracks rate limits. Prove configured
  provider/model availability, cost policy and allowed fallback at runtime; the preference is
  not a hard spending boundary.
- Toolchain: the standalone extension's current CI uses Node 24; its Vitest/toolchain needs a
  compatible newer Node release. Do not transfer the root package's Node 20 consumer guarantee
  to this separate development build.

Acceptance: clean standalone install, real provider receipt without echo, unauthorized WebSocket
rejection, origin/session tests, approval/action match, bounded browser research, provider-failure
and reconnect tests, packaged extension smoke, pinned main/companion compatibility. REP-01 / REL-01.

## GeoSeal CLI: preserve the actual contract

[aethermoore.py](https://github.com/issdandavis/six-tongues-geoseal/blob/312b74a60b9b803e60d60728a46b51891fa2714a/aethermoore.py)
does implement reversible byte/token translation and blend/unblend. Its GeoSeal envelope stores
payload_hex and authenticates context plus payload with HMAC-SHA256. Without GEOSEAL_KEY it selects
a public deterministic self-test key. Verification checks the MAC and optional tag, but does not
enforce timestamp age, nonce uniqueness, or a caller's expected location.

For production integration, require a configured secret and reject missing-key fallback; specify
whether confidentiality is needed; enforce expected domain/location, schema and freshness at the
verifier; test replay and boundary quantization; validate positive blend counts; and retain exact
cross-language round-trip fixtures. Do not describe bijective tokenization as encryption or infer
PQC from an environment-variable name. This is a reusable codec/integrity component with a narrower
contract than the main crypto stack. KEY-01 / SEC-02 / REL-01.

## Embedding companion: separate shape from authentication

The repository's documented 21D layout is 6 hyperbolic + 6 phase + 3 flux + 6 audit, whereas the main
AI-brain comments describe a different partition. Require a schema/versioned adapter and fixtures;
equal vector length does not establish semantic compatibility.

[src/scbe_spaceflight.py](https://github.com/issdandavis/phdm-21d-embedding/blob/cdeb4862e040c341b3a2bed8fb503f10974193a2/src/scbe_spaceflight.py)
is explicitly a protocol analogy module. Its custody-chain check validates order, digest shape and
unique relay IDs; it does not verify a keyed signature against the payload and a trusted relay key.
Use it as a simulation/structural validator unless a separately verified authentication layer is
added. EVAL-01 / REP-01.

## All configured submodule entries

Source: [.gitmodules](../../.gitmodules). These eleven entries are cataloged without cloning or
running third-party code. Resolve and record the superproject's pinned gitlink plus upstream state
when a profile activates one. Entries can outlive actual runtime usage.

| Path | Upstream | Classification / action |
| --- | --- | --- |
| external/Entropicdefenseengineproposal | issdandavis/Entropicdefenseengineproposal | Optional proposal UI; see above |
| external/claude-code-plugins-plus-skills | jeremylongshore/claude-code-plugins-plus-skills | Third-party operator tooling; license/pin/permissions review before use |
| external/designer-skills | Owl-Listener/designer-skills | Third-party design tooling; license/pin/permissions review before use |
| external_repos/Spiralverse-AetherMoore | issdandavis/Spiralverse-AetherMoore | Protocol/history candidate; current support and runtime dependency unverified |
| external_repos/aws-lambda-simple-web-app | issdandavis/aws-lambda-simple-web-app | Archived example; not the current hosted API authority |
| external_repos/scbe-quantum-prototype | issdandavis/scbe-quantum-prototype | Prototype; no active dependency established |
| external_repos/scbe-security-gate | issdandavis/scbe-security-gate | Candidate gate/tool; no active dependency established |
| spiralverse-protocol | issdandavis/spiralverse-protocol | Archived; legacy compatibility only |
| external_repos/ai-workflow-architect | issdandavis/Kiro_Version_ai-workflow-architect | Archived workflow example |
| external_repos/visual-computer-kindle-ai | issdandavis/visual-computer-kindle-ai | Archived application example |
| external_repos/spiralverse-protocol | issdandavis/spiralverse-protocol | Duplicate configured protocol upstream; resolve purpose before activation |

## Required dependency record

For each active profile, record: upstream, canonical source path, owner, full commit/artifact digest,
license, dependency purpose, runtime/toolchain, contract/schema, secret/service requirements,
compatibility test receipt, update/rollback process, and support/archive status.

Keep unrelated repositories out of the runtime graph. Private dependencies, if later activated,
need a restricted inventory and a redacted public record; this review publishes no private repo data.
Each active companion gets its own monthly HIS-01 interval and REP-01 result. The initial full
commit catalogs cover main only; companion activation and historical cataloging remain first-cycle
work rather than being represented as complete.
