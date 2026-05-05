#!/usr/bin/env python3
"""Build governed data-science workflow packets for SCBE agents.

This is intentionally deterministic. It does not call BigQuery, Kaggle, or an
LLM by itself. It turns a data-science goal into a routeable packet with SQL,
Python, evaluation, and receipt expectations so later runners can execute the
right surface without guessing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "scbe_data_science_agent_packet_v1"
SURFACES = ("bigquery", "python", "kaggle", "notebook")
MODALITIES = ("tabular", "image", "text", "multimodal")
TASK_TYPES = ("cluster", "predict", "search", "profile", "classify")
DATA_INLETS: dict[str, dict[str, Any]] = {
    "arxiv_public": {
        "title": "arXiv public research papers",
        "fields": [
            "computer_science",
            "physics",
            "mathematics",
            "quantitative_biology",
            "statistics",
        ],
        "source_url": "https://arxiv.org",
        "access_mode": "public_metadata_or_abs_page",
        "safety_tier": "ALLOW_WITH_CITATION",
        "training_status": "allowed_public_training",
        "receipt_fields": [
            "arxiv_id",
            "title",
            "authors",
            "abstract",
            "categories",
            "url",
        ],
    },
    "pubmed_ncbi": {
        "title": "PubMed / NCBI biomedical literature",
        "fields": ["biology", "medicine", "chemistry", "public_health"],
        "source_url": "https://pubmed.ncbi.nlm.nih.gov",
        "access_mode": "public_metadata_or_api",
        "safety_tier": "ALLOW_WITH_CITATION",
        "training_status": "retrieval_summary_only",
        "receipt_fields": ["pmid", "title", "journal", "publication_date", "url"],
    },
    "crossref_metadata": {
        "title": "Crossref DOI metadata",
        "fields": ["all_science", "literature_graph", "citation_metadata"],
        "source_url": "https://api.crossref.org",
        "access_mode": "public_api",
        "safety_tier": "ALLOW_WITH_CITATION",
        "training_status": "metadata_training_allowed",
        "receipt_fields": ["doi", "title", "publisher", "issued", "url"],
    },
    "openalex_graph": {
        "title": "OpenAlex scholarly graph",
        "fields": ["all_science", "citation_graph", "institutions", "topics"],
        "source_url": "https://openalex.org",
        "access_mode": "public_api",
        "safety_tier": "ALLOW_WITH_CITATION",
        "training_status": "metadata_training_allowed",
        "receipt_fields": ["openalex_id", "title", "concepts", "cited_by_count", "url"],
    },
    "nasa_open_data": {
        "title": "NASA open data and software catalogs",
        "fields": ["astronomy", "aerospace", "earth_science", "robotics"],
        "source_url": "https://data.nasa.gov",
        "access_mode": "public_api_or_catalog",
        "safety_tier": "ALLOW_PUBLIC_DATA",
        "training_status": "allowed_public_training",
        "receipt_fields": [
            "dataset_id",
            "mission_or_program",
            "license",
            "url",
            "source_sha256",
        ],
    },
    "noaa_open_data": {
        "title": "NOAA open weather, climate, and ocean data",
        "fields": ["climate", "weather", "oceanography", "earth_science"],
        "source_url": "https://www.noaa.gov/information-technology/open-data-dissemination",
        "access_mode": "public_api_or_bucket",
        "safety_tier": "ALLOW_PUBLIC_DATA",
        "training_status": "allowed_public_training",
        "receipt_fields": [
            "dataset_id",
            "station_or_grid",
            "time_range",
            "url",
            "source_sha256",
        ],
    },
    "usgs_open_data": {
        "title": "USGS open geospatial and hazard data",
        "fields": ["geology", "hydrology", "earthquake", "geospatial"],
        "source_url": "https://www.usgs.gov/products/data-and-tools/data-and-tools-topics",
        "access_mode": "public_api_or_catalog",
        "safety_tier": "ALLOW_PUBLIC_DATA",
        "training_status": "allowed_public_training",
        "receipt_fields": [
            "dataset_id",
            "region",
            "time_range",
            "url",
            "source_sha256",
        ],
    },
    "epa_open_data": {
        "title": "EPA environmental open data",
        "fields": ["environment", "chemistry", "air_quality", "water_quality"],
        "source_url": "https://www.epa.gov/data",
        "access_mode": "public_api_or_catalog",
        "safety_tier": "ALLOW_PUBLIC_DATA",
        "training_status": "allowed_public_training",
        "receipt_fields": ["dataset_id", "program", "region", "url", "source_sha256"],
    },
    "materials_project": {
        "title": "Materials Project scientific materials database",
        "fields": ["materials_science", "chemistry", "physics"],
        "source_url": "https://materialsproject.org",
        "access_mode": "public_docs_auth_api",
        "safety_tier": "ALLOW_WITH_TERMS_CHECK",
        "training_status": "retrieval_only_until_terms_checked",
        "receipt_fields": [
            "material_id",
            "formula",
            "property",
            "license_or_terms",
            "url",
        ],
    },
    "bigquery_public_datasets": {
        "title": "BigQuery public datasets",
        "fields": ["all_science", "structured_data", "benchmarking"],
        "source_url": "https://cloud.google.com/bigquery/public-data",
        "access_mode": "bigquery_public_dataset",
        "safety_tier": "ALLOW_WITH_COST_CHECK",
        "training_status": "derived_records_only",
        "receipt_fields": [
            "project_dataset_table",
            "row_count",
            "schema_sha256",
            "query_job_id",
        ],
    },
    "polymarket_public_prediction_markets": {
        "title": "Polymarket public prediction market APIs",
        "fields": ["prediction_markets", "forecasting", "probability", "events", "public_market_data"],
        "source_url": "https://docs.polymarket.com/api-reference/introduction",
        "access_mode": "public_gamma_data_and_clob_read_endpoints",
        "safety_tier": "READ_ONLY_NO_TRADING",
        "training_status": "retrieval_summary_and_calibration_only",
        "receipt_fields": [
            "endpoint",
            "query_or_market_id",
            "market_slug",
            "token_id",
            "retrieved_at_unix",
            "probability_or_price_field",
        ],
    },
}


@dataclass(frozen=True)
class DataScienceRequest:
    goal: str
    dataset: str = "unknown_dataset"
    modality: str = "tabular"
    task_type: str = "profile"
    surface: str = "python"
    target: str = ""
    safety_tier: str = "ALLOW"
    source_inlets: str = "auto"


def _sha256_json(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _normalize_choice(value: str, allowed: tuple[str, ...], fallback: str) -> str:
    clean = str(value or "").strip().lower().replace("-", "_")
    return clean if clean in allowed else fallback


def _infer_task_type(goal: str, explicit: str) -> str:
    explicit_clean = _normalize_choice(explicit, TASK_TYPES, "")
    if explicit_clean:
        return explicit_clean
    text = goal.lower()
    if any(token in text for token in ("cluster", "segment", "k-means", "kmeans")):
        return "cluster"
    if any(token in text for token in ("search", "similar", "embedding", "vector")):
        return "search"
    if any(token in text for token in ("predict", "forecast", "regression")):
        return "predict"
    if any(token in text for token in ("classify", "label")):
        return "classify"
    return "profile"


def _selected_inlet_ids(goal: str, source_inlets: str, surface: str) -> list[str]:
    requested = [item.strip() for item in str(source_inlets or "").split(",") if item.strip()]
    if requested and requested != ["auto"]:
        selected = [item for item in requested if item in DATA_INLETS]
        return selected or ["arxiv_public", "crossref_metadata", "openalex_graph"]

    text = goal.lower()
    selected: list[str] = []
    keyword_map = {
        "arxiv_public": (
            "paper",
            "preprint",
            "arxiv",
            "algorithm",
            "model",
            "math",
            "physics",
            "llm",
            "ai",
        ),
        "pubmed_ncbi": (
            "pubmed",
            "clinical",
            "biomedical",
            "medical",
            "medicine",
            "biology",
            "protein",
            "gene",
        ),
        "nasa_open_data": (
            "nasa",
            "space",
            "satellite",
            "mars",
            "aerospace",
            "astronomy",
            "orbital",
        ),
        "noaa_open_data": ("weather", "climate", "ocean", "storm", "forecast", "noaa"),
        "usgs_open_data": (
            "geology",
            "earthquake",
            "hydrology",
            "geospatial",
            "terrain",
            "usgs",
        ),
        "epa_open_data": (
            "environment",
            "pollution",
            "air quality",
            "water quality",
            "epa",
        ),
        "materials_project": (
            "material",
            "crystal",
            "battery",
            "catalyst",
            "compound",
            "materials",
        ),
        "bigquery_public_datasets": (
            "bigquery",
            "public dataset",
            "warehouse",
            "sql",
            "structured",
        ),
        "polymarket_public_prediction_markets": (
            "polymarket",
            "prediction market",
            "forecast",
            "probability",
            "market odds",
            "clob",
            "gamma api",
        ),
    }
    for inlet_id, tokens in keyword_map.items():
        if any(token in text for token in tokens):
            selected.append(inlet_id)
    for default_id in ("arxiv_public", "crossref_metadata", "openalex_graph"):
        if default_id not in selected:
            selected.append(default_id)
    if surface == "bigquery" and "bigquery_public_datasets" not in selected:
        selected.append("bigquery_public_datasets")
    return selected[:6]


def _data_inlet_packet(goal: str, source_inlets: str, surface: str) -> dict[str, Any]:
    selected_ids = _selected_inlet_ids(goal, source_inlets, surface)
    selected = []
    for inlet_id in selected_ids:
        spec = dict(DATA_INLETS[inlet_id])
        spec["inlet_id"] = inlet_id
        selected.append(spec)
    return {
        "schema_version": "scbe_data_science_source_inlets_v1",
        "selection_mode": ("auto" if str(source_inlets or "").strip() in {"", "auto"} else "explicit"),
        "recommended": selected,
        "available_inlet_ids": sorted(DATA_INLETS),
        "route_rule": "Use inlets to build source manifests and citations before feature/model work; do not treat discovery snippets as facts.",
        "minimum_receipts": [
            "inlet_id",
            "source_url",
            "access_mode",
            "citation_or_dataset_id",
            "rights_or_terms_status",
            "retrieved_at_or_snapshot_id",
        ],
    }


def _steps(req: DataScienceRequest) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = [
        {
            "step_id": "S1_ingest_profile",
            "purpose": "Validate dataset identity, columns, row counts, nulls, leakage risk, and access boundary.",
            "surface_action": {
                "bigquery": "INFORMATION_SCHEMA inspection plus SAFE_CAST feature audit",
                "python": "pandas read/profile with dtype and null summaries",
                "kaggle": "kernel input inventory and file hash manifest",
                "notebook": "first notebook cell builds a source manifest",
            }[req.surface],
            "receipt_fields": [
                "dataset_ref",
                "row_count",
                "column_count",
                "source_sha256",
            ],
        },
        {
            "step_id": "S2_feature_build",
            "purpose": "Build explicit features before modeling; keep raw fields and engineered fields separate.",
            "surface_action": {
                "bigquery": "CREATE OR REPLACE TABLE feature_table AS SELECT ...",
                "python": "fit deterministic sklearn/pandas preprocessing pipeline",
                "kaggle": "write working/features.parquet and feature_manifest.json",
                "notebook": "feature-engineering cell emits feature_manifest.json",
            }[req.surface],
            "receipt_fields": [
                "feature_manifest_sha256",
                "dropped_fields",
                "leakage_checks",
            ],
        },
    ]

    if req.modality in {"image", "multimodal"}:
        steps.append(
            {
                "step_id": "S3_visual_enrichment",
                "purpose": "Extract image or multimodal features without overwriting source data.",
                "surface_action": {
                    "bigquery": "use BigQuery AI/ML remote model features or precomputed image embeddings",
                    "python": "load image metadata and generate local/open embedding vectors",
                    "kaggle": "cache image embeddings under working/embeddings.jsonl",
                    "notebook": "image-feature cell emits embedding_manifest.json",
                }[req.surface],
                "receipt_fields": [
                    "embedding_model",
                    "embedding_dim",
                    "embedding_manifest_sha256",
                ],
            }
        )

    model_action = {
        "cluster": "train clustering model and report cluster sizes, silhouette proxy, and examples",
        "predict": "train supervised model with held-out split and leakage checks",
        "search": "build vector index or nearest-neighbor search table and test known queries",
        "profile": "produce data profile, anomaly list, and next-model recommendation",
        "classify": "train classifier with confusion-matrix style eval and label audit",
    }[req.task_type]
    steps.append(
        {
            "step_id": "S4_model_or_index",
            "purpose": model_action,
            "surface_action": {
                "bigquery": _bigquery_model_action(req),
                "python": _python_model_action(req),
                "kaggle": "run the same Python action in a versioned Kaggle kernel with artifacts pulled back",
                "notebook": "execute a readable notebook section with model/index outputs saved as JSON",
            }[req.surface],
            "receipt_fields": [
                "model_or_index_id",
                "train_eval_split",
                "metric_report_sha256",
            ],
        }
    )
    steps.append(
        {
            "step_id": "S5_eval_gate",
            "purpose": "Block promotion unless metrics, provenance, and reproducibility evidence are present.",
            "surface_action": "emit gate_report.json and mark PASS/HOLD",
            "receipt_fields": [
                "gate_decision",
                "metric_thresholds",
                "repro_command",
                "artifact_paths",
            ],
        }
    )
    return steps


def _bigquery_model_action(req: DataScienceRequest) -> str:
    if req.task_type == "cluster":
        return "CREATE MODEL ... OPTIONS(model_type='kmeans') then ML.EVALUATE and ML.PREDICT"
    if req.task_type == "search":
        return "GENERATE_EMBEDDING or stored vectors plus VECTOR_SEARCH over embedding table"
    if req.task_type == "predict":
        return "CREATE MODEL ... OPTIONS(model_type='boosted_tree_regressor' or 'linear_reg')"
    if req.task_type == "classify":
        return "CREATE MODEL ... OPTIONS(model_type='boosted_tree_classifier' or 'logistic_reg')"
    return "CREATE profile tables and anomaly views; defer model training until target is explicit"


def _python_model_action(req: DataScienceRequest) -> str:
    if req.task_type == "cluster":
        return "sklearn KMeans pipeline with StandardScaler and cluster audit"
    if req.task_type == "search":
        return "sentence/image embeddings plus sklearn NearestNeighbors or FAISS when installed"
    if req.task_type == "predict":
        return "sklearn train/test pipeline with baseline and target leakage check"
    if req.task_type == "classify":
        return "sklearn classifier pipeline with stratified split and confusion matrix"
    return "pandas profiling plus suggested next model family"


def _sql_skeleton(req: DataScienceRequest) -> list[str]:
    if req.surface != "bigquery":
        return []
    table = req.dataset if "." in req.dataset else "`project.dataset.table`"
    feature_table = "`project.dataset.scbe_feature_table`"
    model = "`project.dataset.scbe_model`"
    statements = [
        f"-- S1 profile\nSELECT COUNT(*) AS row_count FROM {table};",
        f"-- S2 features\nCREATE OR REPLACE TABLE {feature_table} AS SELECT * FROM {table};",
    ]
    if req.task_type == "cluster":
        statements.append(
            "-- S4 clustering\n"
            f"CREATE OR REPLACE MODEL {model} OPTIONS(model_type='kmeans', num_clusters=5) AS "
            f"SELECT * FROM {feature_table};"
        )
        statements.append(f"-- S5 eval\nSELECT * FROM ML.EVALUATE(MODEL {model});")
    elif req.task_type == "search":
        statements.append("-- S4 search\n-- Build or reference an embedding column, then call VECTOR_SEARCH.")
    else:
        statements.append("-- S4 model/profile\n-- Select an explicit target and model_type before training.")
    return statements


def _python_skeleton(req: DataScienceRequest) -> list[str]:
    if req.surface not in {"python", "kaggle", "notebook"}:
        return []
    if req.task_type == "cluster":
        return [
            "import pandas as pd",
            "from sklearn.cluster import KMeans",
            "from sklearn.preprocessing import StandardScaler",
            "df = pd.read_csv(DATASET_PATH)",
            "X = StandardScaler().fit_transform(df.select_dtypes('number').fillna(0))",
            "model = KMeans(n_clusters=5, random_state=47, n_init='auto').fit(X)",
            "df['scbe_cluster'] = model.labels_",
        ]
    if req.task_type == "search":
        return [
            "import pandas as pd",
            "from sklearn.neighbors import NearestNeighbors",
            "vectors = load_embeddings(DATASET_PATH)",
            "index = NearestNeighbors(metric='cosine').fit(vectors)",
        ]
    return [
        "import pandas as pd",
        "df = pd.read_csv(DATASET_PATH)",
        "profile = {'rows': len(df), 'columns': list(df.columns), 'nulls': df.isna().sum().to_dict()}",
    ]


def build_data_science_packet(request: DataScienceRequest) -> dict[str, Any]:
    modality = _normalize_choice(request.modality, MODALITIES, "tabular")
    surface = _normalize_choice(request.surface, SURFACES, "python")
    task_type = _infer_task_type(request.goal, request.task_type)
    req = DataScienceRequest(
        goal=request.goal.strip() or "Profile dataset and recommend next data-science step.",
        dataset=request.dataset.strip() or "unknown_dataset",
        modality=modality,
        task_type=task_type,
        surface=surface,
        target=request.target.strip(),
        safety_tier=(request.safety_tier.strip().upper() or "ALLOW"),
        source_inlets=request.source_inlets.strip() or "auto",
    )
    packet: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "request": req.__dict__,
        "agent_role": "scbe_data_science_agent",
        "route": {
            "primary_surface": req.surface,
            "fallback_surface": "python" if req.surface != "python" else "notebook",
            "required_signal": f"data-science:{req.surface}:{req.task_type}",
            "allowed_tools": [
                "select_source_inlets",
                "read_dataset",
                "profile",
                "feature_build",
                "train_or_index",
                "evaluate",
            ],
            "blocked_tools": ["delete_source_data", "publish_publicly_without_review"],
        },
        "source_inlets": _data_inlet_packet(req.goal, req.source_inlets, req.surface),
        "workflow": _steps(req),
        "artifacts": {
            "expected": [
                "source_inlets_manifest.json",
                "source_manifest.json",
                "feature_manifest.json",
                "gate_report.json",
            ],
            "sql_skeleton": _sql_skeleton(req),
            "python_skeleton": _python_skeleton(req),
        },
        "promotion_gate": {
            "decision_rule": "PASS only when dataset provenance, feature manifest, metric report, and reproducible command exist.",
            "minimum_evidence": [
                "source inlets manifest",
                "source manifest with hashes",
                "feature manifest",
                "metric or profile report",
                "repro command",
            ],
        },
    }
    packet["packet_sha256"] = _sha256_json(packet)
    return packet


def render_text(packet: dict[str, Any]) -> str:
    req = packet["request"]
    lines = [
        "SCBE Data Science Agent",
        f"goal: {req['goal']}",
        f"surface: {req['surface']} task: {req['task_type']} modality: {req['modality']}",
        f"signal: {packet['route']['required_signal']}",
        f"packet: {packet['packet_sha256'][:16]}",
        "",
        "source inlets:",
    ]
    for inlet in packet["source_inlets"]["recommended"]:
        lines.append(f"- {inlet['inlet_id']}: {inlet['title']}")
    lines.extend(
        [
            "",
            "workflow:",
        ]
    )
    for step in packet["workflow"]:
        lines.append(f"- {step['step_id']}: {step['purpose']}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a governed SCBE data-science agent packet")
    parser.add_argument("--goal", default="Profile dataset and recommend next data-science step.")
    parser.add_argument("--dataset", default="unknown_dataset")
    parser.add_argument("--modality", default="tabular", choices=MODALITIES)
    parser.add_argument("--task-type", default="", choices=("", *TASK_TYPES))
    parser.add_argument("--surface", default="python", choices=SURFACES)
    parser.add_argument("--target", default="")
    parser.add_argument("--safety-tier", default="ALLOW")
    parser.add_argument(
        "--source-inlets",
        default="auto",
        help="Comma-separated inlet ids or auto. Examples: arxiv_public,pubmed_ncbi,nasa_open_data",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    packet = build_data_science_packet(
        DataScienceRequest(
            goal=args.goal,
            dataset=args.dataset,
            modality=args.modality,
            task_type=args.task_type,
            surface=args.surface,
            target=args.target,
            safety_tier=args.safety_tier,
            source_inlets=args.source_inlets,
        )
    )
    print(json.dumps(packet, indent=2, sort_keys=True) if args.json else render_text(packet))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
