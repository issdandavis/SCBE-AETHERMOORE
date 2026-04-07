# AI2AI arXiv Retrieval Service

This service adds agent-to-agent research retrieval and handoff packets for arXiv.

## What was added

- `hydra/arxiv_retrieval.py`
  - `ArxivClient` for arXiv API queries
  - `AI2AIRetrievalService` for packetized handoff + related-work outline
- `hydra/cli.py`
  - New command surface: `hydra arxiv ...`
- `scripts/arxiv_ai2ai_service.py`
  - FastAPI service for local AI-to-AI retrieval APIs
- `tests/test_arxiv_ai2ai_retrieval.py`
  - Unit tests for query, parsing, packetization, memory handoff

## arXiv usage model

The client uses the arXiv Atom API endpoint:

- `https://export.arxiv.org/api/query`

It also sets a custom `User-Agent` and supports polite request spacing (default 3s between requests) for repeated calls.

Set custom identity if needed:

```powershell
$env:ARXIV_USER_AGENT = "AETHERMOORE-HYDRA/1.0 (mailto:issdandavis7795@aethermoore.com)"
```

## HYDRA CLI commands

### Search

```powershell
python -m hydra arxiv search "dual lattice governance" --cat cs.AI --max 5
```

### Fetch known IDs

```powershell
python -m hydra arxiv get 2501.00001v1,2501.00002
```

### Generate related-work outline

```powershell
python -m hydra arxiv outline "hyperbolic multi-agent retrieval" --cat cs.AI --max 8
```

Optional flags:

- `--no-memory` disables Librarian storage for this query
- `--raw-query` sends the query directly (no `all:` prefix)

## Run as API service

```powershell
uvicorn scripts.arxiv_ai2ai_service:app --host 127.0.0.1 --port 8099
```

### Endpoints

- `GET /health`
- `POST /retrieve/arxiv`
- `POST /retrieve/arxiv/outline`

Example request:

```json
{
  "requester": "polly",
  "query": "dual lattice post-quantum ai",
  "category": "cs.AI",
  "max_results": 5,
  "remember": true,
  "raw_query": false
}
```

If `AI2AI_API_KEY` is set in env, pass it in `x-api-key` header.

## Paper-writing flow (recommended)

1. `hydra arxiv search` for a focused query and category.
2. `hydra arxiv outline` to create a related-work skeleton.
3. Feed packet IDs into existing scripts:
   - `scripts/arxiv_aggregate_docs.py`
   - `scripts/arxiv_synthesize_paper.py`
   - `scripts/arxiv_generate_manifest.py`
4. Bundle with `scripts/arxiv_bundle.py` and final-review submit.
