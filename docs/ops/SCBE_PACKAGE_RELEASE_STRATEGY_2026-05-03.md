# SCBE Package Release Strategy

Date: 2026-05-03

Purpose: keep npm and PyPI releases small, finished, and useful while the larger
SCBE-AETHERMOORE repository keeps moving fast.

## Published npm Surface

Current public npm packages:

| Package | Current role | Release direction |
| --- | --- | --- |
| `scbe-aethermoore` | Main framework package with core governance, tokenizer, and TypeScript exports. | Keep as the full SDK. Publish only after strict tarball guard, build, tests, and README review. |
| `scbe-aethermoore-cli` | Older standalone command-line interface surface. | Treat as legacy or compatibility until reconciled with `geoseal`. Do not expand without a reason. |
| `scbe-agent-bus` | Typed Node surface over the governed event runner. | Rename language in docs toward "agentic transit station" while preserving bus compatibility in APIs. |

Author metadata must use the full name:

```text
Issac Daniel Davis
```

This is already present in the main npm and PyPI metadata. Keep it in README
and package pages so public indexes do not shorten it.

## Product Slices

Release smaller, finished tools instead of one giant package push.

### 1. GeoSeal Terminal

User promise: install one CLI and get a readable local control panel for
agentic routing, provider checks, and source finding.

Candidate commands:

```powershell
geoseal harness-terminal --models ollama:local,huggingface:coder --no-health
geoseal research-terminal --family science --query "agentic coding benchmarks"
geoseal data-science-agent --goal "cluster real estate listings" --dataset "demo.real_estate.listings" --modality multimodal --surface bigquery
```

Release package:

- npm: `geoseal-cli` or upgrade `scbe-aethermoore-cli`
- PyPI: keep under `scbe-aethermoore` unless a clean `geoseal-cli` Python
  package is split later

Gate:

- terminal output must be readable by humans,
- JSON output must be stable for agents,
- no secrets printed,
- no cloud dispatch unless explicitly requested.

### 2. SCBE Agentic Transit Station

User promise: coordinate local and cloud AI helpers through small packets instead
of dumping full prompts everywhere.

Core idea:

- local-first Ollama and offline lanes,
- optional Hugging Face, NVIDIA, DeepSeek, OpenRouter, or hosted SCBE router,
- lane-switch signals required when crossing provider boundaries,
- compact `AgentPacketV1` handoffs with path/hash references instead of raw
  context bloat.

Release package:

- npm: evolve `scbe-agent-bus`
- package docs can say: "bus-compatible transit station runtime"

Gate:

- provider matrix works,
- lane-switch rules are visible,
- packet size is measured,
- a local-only mode exists,
- cloud mode is opt-in.

### 3. SCBE Source Finder

User promise: one terminal command finds and packages research sources for
agents without making users wire arXiv, PubMed, Crossref, OpenAlex, NASA, NOAA,
USGS, EPA, and BigQuery by hand.

Candidate command:

```powershell
geoseal research-terminal --family science --query "chemical reaction agent benchmark"
```

Release package:

- either keep inside GeoSeal CLI,
- or later split as `scbe-source-finder` if it becomes useful enough alone.

Gate:

- source metadata is separated from claims,
- raw copyrighted source text is not dumped into packages,
- generated packets cite source IDs and URLs,
- training rows preserve "source says" versus "system infers".

## Hosted Router Path

The hosted router should be optional. It becomes valuable only if it saves users
from wiring many provider keys themselves.

Recommended shape:

1. Free local mode:
   - Ollama,
   - local HTTP-compatible runtimes,
   - offline deterministic fallback.
2. User-key mode:
   - user brings Hugging Face, NVIDIA, DeepSeek, OpenRouter, or other keys,
   - keys stay local unless the user explicitly stores them in the hosted router.
3. SCBE hosted router mode:
   - one SCBE API key,
   - server-side provider pool,
   - capacity gate checks quota before routing,
   - logs only metadata, hashes, token counts, provider, route, and outcome,
   - never logs raw secrets.

The AWS free-tier demo stack is the first prototype of this capacity gate:

- DynamoDB customers table,
- DynamoDB usage-events table,
- Lambda capacity-gate function,
- SNS upgrade-events topic,
- SES quota inspection.

Next hosted-router gate:

```text
Customer API key -> Lambda capacity gate -> provider router -> compact response envelope
```

Do not add a public endpoint until authentication, quotas, logs, abuse limits,
and billing upgrade behavior are tested.

## Update Notifications

npm and PyPI do not push notifications to every anonymous downloader.

Use three channels:

1. Package-native:
   - npm dist-tags: `latest`, `next`, `beta`,
   - PyPI release RSS feed.
2. CLI-native:
   - `geoseal update-check`,
   - optional local notice when the CLI runs,
   - no tracking by default.
3. Customer-native:
   - buyer email after purchase,
   - release guide generated from the same demo/prototype artifacts,
   - changelog links in fulfillment emails.

## Sunday Release Order

1. Fix active security advisory workflow and push patch.
2. Run package content review on all three npm packages.
3. Pick one finished CLI slice for release, probably GeoSeal Terminal.
4. Build and test package tarballs locally.
5. Publish npm first.
6. Build and check PyPI dist.
7. Publish PyPI only after package contents match the intended surface.
8. Send/update customer guide after the package is live.

## Do Not Ship

- Raw repo sprawl as a package feature.
- Generated caches, local settings, secrets, or model blobs.
- A hosted cloud router without quota gates.
- AI-to-AI cloud dispatch that silently sends private repo context to third
  parties.
- Public workflow automation that lets untrusted content steer authenticated
  repo comments.
