# SAM.gov Public API Integration Map

Status date: 2026-10-30

This map covers SCBE consumers of the SAM.gov Opportunities v2 public API. It
does not cover Opportunity Management write APIs or controlled entity data.
The API key is an input credential and must never appear in reports, logs,
receipts, tests, or command output.

## Current Nodes

| Node | Path or authority | Role | Status | Consumers |
| --- | --- | --- | --- | --- |
| GitHub Actions secret | `SAM_GOV_API_KEY` | Supplies the individual public API key at runtime | PROVEN present; value intentionally inaccessible | Scheduled workflows |
| Official API contract | `https://open.gsa.gov/api/get-opportunities-public-api/` | Defines Opportunities v2 endpoint, filters, pagination, and response fields | AUTHORITATIVE | All SAM clients |
| Weekly opportunity check | `.github/workflows/weekly-gov-contracts-check.yml` | Searches recent notices, uploads a report, and reconciles one rolling issue | PROVEN complete on 2026-10-30 across 16 title, organization, and NAICS profiles | GitHub Actions, maintainers |
| DARPA Prep client | `api/darpa_prep/client.py`, `api/darpa_prep/sam_public.py` | Validated API search and domain normalization | PROVEN against the live Opportunities v2 API | API routes, research API bus, CLI ingest |
| DARPA Prep HTTP router | api/main.py, api/darpa_prep/routes.py | Exposes search and normalization to authenticated SCBE tenants | HARDENED; deployed router inherits the core API-key dependency | API clients |
| Research API bus | `scripts/research_api_bus.py` | Exposes SAM results beside other research providers | REPAIRED; maps the current normalized record schema | Agent/research callers |
| Research feed | `scripts/system/generate_research_feed.py` | Adds DARPA opportunities to the public research feed | REPAIRED; uses documented organization, date, and notice-type filters | Hourly research-feed workflow |
| Coding opportunity collector | `scripts/system/collect_sam_coding_opportunities.py` | Collects public metadata for task-shaping records | REPAIRED; uses the canonical endpoint and documented title filter | Training-data preparation |
| Research triangle | `scripts/system/research_triangle.py` | Pairs public opportunity metadata with public research papers | REPAIRED; uses documented organization, title, and notice-type filters | Research bridge dataset |
| Rolling issue helper | `.github/scripts/issue-lifecycle.cjs` | Keeps one actionable issue open and closes it on a clean scan | PROVEN and reused | Weekly workflow |

## Intended Flow

```text
official Opportunities v2 contract
        + runtime API key
        -> dependency-free validated SAM transport
        -> query profiles (title, organization, NAICS, notice type, dates)
        -> canonical public opportunity records
        -> ranked weekly report + artifact
        -> GitHub summary / one rolling issue
        -> optional API bus, research feed, and metadata-only research consumers
```

The API response is the canonical external record. Ranking is derived metadata,
not independent evidence. A notice remains unqualified until a human checks its
official record, attachments, eligibility, and deadline.

## Edge Contracts and Invariants

1. The key enters only from `SAM_GOV_API_KEY` or an explicit in-memory test
   argument. It is sent only to the configured HTTPS SAM.gov endpoint.
2. Persisted query plans replace the key with `<redacted>` and never persist a
   complete request URL.
3. Supported request names follow the official v2 contract: `title`, `ptype`,
   `ncode`, `organizationName`, `organizationCode`, `postedFrom`, `postedTo`,
   `rdlfrom`, `rdlto`, `limit`, and `offset`.
4. HTTP 404 means a successful empty result. HTTP 401/403 and malformed JSON are
   scanner errors, never clean zero-result evidence.
5. Pagination is bounded by the requested result limit and the API's 1,000-row
   page maximum. Notice IDs deduplicate overlapping query profiles.
6. Only public opportunity metadata is stored. Attachments are links, not
   automatically downloaded or ingested.
7. Reports record successful and failed query counts so partial outages cannot
   masquerade as a clean scan.

## Build Gate

- Capability being added: one tested Opportunities v2 transport and a useful
  SCBE discovery profile covering title, DARPA organization, and relevant NAICS
  lanes.
- Reused components: the DARPA Prep normalizer, weekly artifact/issue lifecycle,
  and existing metadata-only policy.
- New downstream obligation: broader searches can return noisy matches, so each
  result needs transparent match provenance and deterministic relevance scoring.
- Inputs: date window, bounded result limit, documented filters, and an in-memory
  API key. Output: JSON-safe public metadata with query provenance and no key.
- Baseline: current eight-title weekly scan. Control: mocked empty 404 response.
  Boundary tests: invalid endpoint, authentication failure, malformed payload,
  pagination, overlap deduplication, and secret-redaction assertions.
- Budget: at most a few dozen requests per weekly run; no attachment downloads;
  20-minute Actions timeout remains the hard stop.
- Rollback: revert the focused commit; the existing title-only workflow remains
  available in Git history and the key is unaffected.
- Stop conditions: any credential appears in output, an undocumented filter is
  required, a partial scan is reported as clean, or focused tests fail.

## Remaining Boundaries

- Whether every older consumer needs to remain active after the canonical client
  is wired in.
- Broad NAICS profiles are useful discovery lanes but intentionally noisy; a
  ranked notice is not a bid recommendation and still needs human qualification.
- Entity-registration monitoring requires a user-selected public UEI and is out
  of this change; no identity is inferred from repository files.

## Implementation Update — 2026-10-30

- Added the credential-safe transport at `api/darpa_prep/sam_public.py` and
  retained proposal normalization through `api/darpa_prep/client.py`.
- Added the ranked profile scanner at
  `scripts/system/scan_sam_opportunities.py`; the weekly workflow now calls this
  executable surface instead of carrying a second inline client, publishes an
  incomplete-scan issue, and then fails the run so missing evidence stays visible.
- Rewired the DARPA research feed and research triangle to documented
  `organizationName`, `title`, and repeated `ptype` parameters.
- Corrected the metadata collector's endpoint and title filter, and repaired the
  research API bus mapping to the current `OpportunityRecord` schema.
- Moved the deployed DARPA Prep router behind the existing SCBE tenant
  authentication dependency so anonymous callers cannot spend the server's
  SAM.gov request quota.
- Added deterministic regression coverage in
  `tests/api/test_sam_gov_public.py`, `tests/test_scan_sam_opportunities.py`,
  `tests/test_sam_consumers.py`, and the existing workflow/collector tests.
- Local evidence: the combined SAM transport, scanner, consumers, workflow,
  authenticated API, DARPA parser, and proposal-schema suite passed 38/38.
  Ruff, Black, compileall, the governance gate, secret scan, and
  `git diff --check` passed.
- Live profile quality and the real API response were subsequently verified by
  the branch runs recorded below.

## First Live Branch Run — 2026-10-30

- Run 41123624154 proved the key valid and the report/artifact path operational.
- Fifteen of sixteen profiles succeeded: 212 unique public notices were
  collected and 36 passed the deterministic relevance threshold.
- One title profile encountered a transient network failure. The workflow
  published the incomplete evidence and then failed as designed.
- The shared client now retries only transient network, HTTP 408/429, and HTTP
  5xx failures with a bounded exponential backoff. Authentication failures still
  fail immediately. A second live run is required before this status becomes
  PROVEN complete.

## Successful Live Branch Run — 2026-10-30

- Run 41124064073 completed successfully with all 16 profiles, no query errors,
  and a credential-free JSON artifact whose GitHub digest is
  `sha256:61e190879d9c0eeb76deb2db4f9cacbf174f46ec78ce5fd987fc9be2a5c38878`.
- The 14-day scan deduplicated 215 public notices and retained 39 ranked
  opportunities. The strongest matches included current cybersecurity/RMF,
  information-assurance, DARPA verification, and distributed-AI notices.
- This proves the stored key, official endpoint, documented filters, pagination,
  retry policy, ranking path, artifact upload, issue reconciliation, and
  fail-closed completeness gate as one live branch workflow.
