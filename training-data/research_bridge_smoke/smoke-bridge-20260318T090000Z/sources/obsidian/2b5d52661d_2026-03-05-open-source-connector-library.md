# Open Source Knowledge Connector Deep Research (2026-03-05)

## Scope
This research validates high-value public connectors for a scalable SCBE knowledge library pipeline:
- Pull from trusted sources
- Normalize into local storage and Obsidian notes
- Push selected subsets into Hugging Face datasets
- Keep active agent context compact (1-5 windows)

## Confirmed Connectors (Official Docs)

| Connector | Category | API/Base | Auth | Primary Use |
|---|---|---|---|---|
| arXiv API | Academic | `https://export.arxiv.org/api/query` | None | Preprints + metadata |
| arXiv OAI-PMH | Academic bulk | `https://export.arxiv.org/oai2` | None | Harvest metadata at scale |
| OpenAlex | Academic graph | `https://api.openalex.org` | None (email recommended) | Works/authors/citations |
| Crossref REST | DOI metadata | `https://api.crossref.org` | None | DOI, references, publisher metadata |
| Semantic Scholar | Academic AI | `https://api.semanticscholar.org/graph/v1` | Optional key | Paper graphs + recommendations |
| Wikidata Query Service | Knowledge graph | `https://query.wikidata.org/sparql` | None | SPARQL entity graph queries |
| Wikidata Action API | Knowledge graph | `https://www.wikidata.org/w/api.php` | None | Entity search and claims |
| NVD Vulnerabilities | Security | `https://services.nvd.nist.gov/rest/json/cves/2.0` | Optional key | CVE and vulnerability intelligence |
| SEC EDGAR APIs | Regulatory | `https://data.sec.gov/` | None | Company filings + facts |
| USPTO Open Data | IP | USPTO developer portal | Varies | Patent/trademark records |
| NCBI E-utilities | Biomedical | `https://eutils.ncbi.nlm.nih.gov/entrez/eutils/` | Optional key | PubMed and biomedical retrieval |
| Library of Congress APIs | Library/archives | `https://www.loc.gov/` | None | Historical and cultural records |
| Open Library API | Library | `https://openlibrary.org` | None | Books/authors/editions |
| Internet Archive APIs | Archive | `https://archive.org` | Mostly none | Archived texts/media and metadata |
| Common Crawl Index | Web corpus | `https://index.commoncrawl.org/` | None | Large web-scale corpus retrieval |
| NASA Open APIs | Science | `https://api.nasa.gov/` | API key | Space/science feeds |
| World Bank Data API | Economics | `https://api.worldbank.org/v2/` | None | Indicators and country metrics |
| US Census APIs | Economics/demographics | `https://api.census.gov/data/` | Key recommended | Demographic and economic datasets |
| Dataverse Native API | Datasets | Dataverse `/api` | Optional token | Dataset discovery and files |
| MIT TIMDEX | Library discovery | `https://timdex.mit.edu/` | Public discovery | MIT library index |
| GitHub REST API | Code intelligence | `https://api.github.com` | Token for higher limits | Repos/issues/PRs/docs |
| Hugging Face Hub API | AI data/model ops | `https://huggingface.co/api` | Token for write | Dataset/model push/pull |
| Notion API | Workspace ingestion | `https://api.notion.com/v1` | Bearer token | Notes/databases |
| Zotero Web API | Research ops | `https://api.zotero.org` | API key for private | Citation libraries |

## Confirmation Requested by User
- MIT-related dataset/library connectors: confirmed via Dataverse API docs and MIT TIMDEX docs.
- NVD connector: confirmed via NIST NVD developer page.
- Wikidata connector: confirmed via Wikidata Query Service and API docs.

## Pipeline Design (Library from Lore -> RAG)

### 1. Ingest Layer
- Source adapters per connector (REST/SPARQL/Atom/OAI-PMH).
- Anti-injection and provenance tags at ingest time.
- Normalize every record into a shared `knowledge_chunk` schema.

### 2. Storage Layer
- Local: `training/intake/knowledge_base/` + `training/context_capsules/`
- Mirror: Obsidian notes (human-facing operational memory)
- Publish subset: Hugging Face dataset repo for model-training-ready views

### 3. Retrieval Layer
- Build compact context capsules (`1w`, `3w`, `5w`) from high-signal chunks.
- Keep long-tail data in JSONL library and only retrieve by intent query.
- Use semantic + governance tags to prioritize trusted sources.

### 4. Output Layer
- Aether Web pages pull from curated capsules and source-attributed summaries.
- Article/posting workflows consume capsules instead of raw full corpus.

## Files Added in This Pass
- `src/knowledge/storage/open_source_api_library.json`
- `scripts/knowledge/build_context_capsules.py`
- Generated outputs in `training/context_capsules/`

## Primary Sources
- https://info.arxiv.org/help/api/user-manual.html
- https://info.arxiv.org/help/oa/index.html
- https://docs.openalex.org/
- https://www.crossref.org/documentation/retrieve-metadata/rest-api/
- https://www.semanticscholar.org/product/api
- https://www.mediawiki.org/wiki/Wikidata_Query_Service/User_Manual
- https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service
- https://nvd.nist.gov/developers/vulnerabilities
- https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- https://developer.uspto.gov/
- https://www.ncbi.nlm.nih.gov/books/NBK25501/
- https://www.loc.gov/apis/
- https://openlibrary.org/developers/api
- https://archive.org/developers/
- https://index.commoncrawl.org/
- https://api.nasa.gov/
- https://datahelpdesk.worldbank.org/knowledgebase/articles/889392-about-the-indicators-api-documentation
- https://www.census.gov/data/developers.html
- https://guides.dataverse.org/en/latest/api/native-api.html
- https://mitlibraries.github.io/timdex/
- https://docs.github.com/en/rest
- https://huggingface.co/docs/hub/api
- https://developers.notion.com/reference/intro
- https://www.zotero.org/support/dev/web_api/v3/start
