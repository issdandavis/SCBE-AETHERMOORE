from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "system" / "data_science_agent.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("data_science_agent", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_bigquery_multimodal_cluster_packet_has_sql_and_visual_step() -> None:
    module = _load_module()

    packet = module.build_data_science_packet(
        module.DataScienceRequest(
            goal="Cluster real estate listings with house images and vector search",
            dataset="demo.real_estate.listings",
            modality="multimodal",
            task_type="",
            surface="bigquery",
        )
    )

    assert packet["schema_version"] == "scbe_data_science_agent_packet_v1"
    assert packet["request"]["task_type"] == "cluster"
    assert packet["route"]["required_signal"] == "data-science:bigquery:cluster"
    assert any(step["step_id"] == "S3_visual_enrichment" for step in packet["workflow"])
    assert any(
        "CREATE OR REPLACE MODEL" in sql for sql in packet["artifacts"]["sql_skeleton"]
    )
    assert len(packet["packet_sha256"]) == 64


def test_python_search_packet_has_embedding_index_skeleton() -> None:
    module = _load_module()

    packet = module.build_data_science_packet(
        module.DataScienceRequest(
            goal="Build visual search over product images using embeddings",
            dataset="products.csv",
            modality="image",
            task_type="",
            surface="python",
        )
    )

    assert packet["request"]["task_type"] == "search"
    assert packet["request"]["surface"] == "python"
    assert any(
        "NearestNeighbors" in line for line in packet["artifacts"]["python_skeleton"]
    )
    assert packet["promotion_gate"]["minimum_evidence"] == [
        "source manifest with hashes",
        "feature manifest",
        "metric or profile report",
        "repro command",
    ]


def test_cli_json_is_valid() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(MODULE_PATH),
            "--goal",
            "segment customers with kmeans",
            "--dataset",
            "customers.csv",
            "--surface",
            "python",
            "--json",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )

    packet = json.loads(proc.stdout)
    assert packet["request"]["task_type"] == "cluster"
    assert packet["route"]["fallback_surface"] == "notebook"


def test_geoseal_cli_routes_data_science_agent() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "data-science-agent",
            "--goal",
            "cluster real estate listings with images",
            "--dataset",
            "demo.real_estate.listings",
            "--modality",
            "multimodal",
            "--surface",
            "bigquery",
            "--json",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )

    packet = json.loads(proc.stdout)
    assert packet["request"]["surface"] == "bigquery"
    assert packet["route"]["required_signal"] == "data-science:bigquery:cluster"
    assert any("ML.EVALUATE" in sql for sql in packet["artifacts"]["sql_skeleton"])
