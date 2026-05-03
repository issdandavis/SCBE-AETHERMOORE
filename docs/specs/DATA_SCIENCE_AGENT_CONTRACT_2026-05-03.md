# Data Science Agent Contract

Date: 2026-05-03

Purpose: define the first SCBE data-science agent surface without binding it to one cloud provider.

## Core Rule

The data science agent does not run cloud jobs by default. It first emits a governed workflow packet that can be routed to BigQuery, Python, Kaggle, or a notebook runner.

That packet must include:

- dataset identity,
- modality,
- task type,
- required lane signal,
- workflow steps,
- source inlet routes,
- SQL or Python skeleton when relevant,
- receipt fields,
- promotion gate evidence.

## Supported Surfaces

- `bigquery`: SQL-native feature building, BigQuery Machine Learning clustering/prediction, and vector search plans.
- `python`: local pandas/scikit-learn style pipeline plans.
- `kaggle`: remote notebook execution plans with artifact pullback.
- `notebook`: human-readable notebook sections with explicit manifests.

## Science Source Inlets

The agent can attach source inlets before the modeling workflow. These are route declarations, not live downloads.

Current inlet families:

- `arxiv_public`: computer science, physics, mathematics, statistics, and quantitative biology preprints.
- `pubmed_ncbi`: biomedical and public-health literature.
- `crossref_metadata`: DOI and publisher metadata.
- `openalex_graph`: scholarly graph metadata and citation context.
- `nasa_open_data`: astronomy, aerospace, robotics, and Earth science datasets.
- `noaa_open_data`: weather, climate, ocean, and storm datasets.
- `usgs_open_data`: geospatial, geology, hydrology, and earthquake datasets.
- `epa_open_data`: environmental, air-quality, water-quality, and chemistry-adjacent datasets.
- `materials_project`: materials science and chemistry records, subject to terms checks.
- `bigquery_public_datasets`: SQL-native public datasets with cost checks.

Every inlet must emit:

- inlet id,
- source URL,
- access mode,
- citation or dataset id,
- rights or terms status,
- retrieval time or snapshot id.

## Workflow

1. Ingest and profile the dataset.
2. Build explicit features.
3. Add visual or multimodal enrichment when modality requires it.
4. Train a model or build an index.
5. Run an evaluation gate and emit reproducibility evidence.

## CLI

```powershell
python scripts/system/data_science_agent.py --goal "cluster real estate listings with house images" --dataset demo.real_estate.listings --modality multimodal --surface bigquery --json
```

GeoSeal route:

```powershell
python -m src.geoseal_cli data-science-agent --goal "cluster real estate listings with house images" --dataset demo.real_estate.listings --modality multimodal --surface bigquery --json
```

Explicit inlet selection:

```powershell
python -m src.geoseal_cli data-science-agent --goal "profile biomedical chemistry papers" --dataset papers.jsonl --source-inlets pubmed_ncbi,materials_project,arxiv_public --json
```

## Promotion Gate

The packet is only executable after the runner can prove:

- source manifest with hashes,
- source inlets manifest,
- feature manifest,
- metric or profile report,
- reproducible command,
- no destructive source-data action,
- no public publish without review.
