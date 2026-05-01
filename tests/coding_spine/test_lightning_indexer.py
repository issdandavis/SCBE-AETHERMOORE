from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from src.coding_spine.agent_tool_bridge import build_agent_harness_manifest_v1
from src.coding_spine.agent_tool_policy import geoseal_command_to_tool_class
from src.coding_spine.lightning_indexer import select_sparse_candidates

ROOT = Path(__file__).resolve().parents[2]


def test_lightning_indexer_selects_relevant_sparse_candidate() -> None:
    payload = select_sparse_candidates(
        "route binary hexadecimal tokenizer conversion through geoseal",
        [
            {"candidate_id": "ui", "text": "landing page card layout", "kind": "doc"},
            {
                "candidate_id": "convert-code",
                "text": "convert binary hexadecimal token rows through GeoSeal tokenizer",
                "kind": "tool",
                "lane": "tokenizer",
                "priority": 2,
            },
            {"candidate_id": "email", "text": "proton mail outreach draft", "kind": "route"},
        ],
        top_k=1,
        block_size=2,
    )

    assert payload["schema_version"] == "scbe_lightning_indexer_v1"
    assert payload["selected"][0]["candidate_id"] == "convert-code"
    assert "binary" in payload["selected"][0]["matched_tokens"]
    assert set(payload["context_channels"]) == {"local_window", "sparse_semantic", "global_anchor"}
    assert payload["hybrid_attention_plan"]["schema_version"] == "scbe_hybrid_attention_plan_v1"
    assert payload["hybrid_attention_plan"]["analogue"]["dense_local_attention"] == "local_window"
    assert payload["hybrid_attention_plan"]["analogue"]["compressed_sparse_attention"] == "sparse_semantic"
    assert payload["hybrid_attention_plan"]["analogue"]["heavily_compressed_attention"] == "global_anchor"
    assert payload["hybrid_attention_plan"]["analogue"]["spatial_sparse_index"] == "octree_retrieval"
    assert payload["octree_retrieval"]["schema_version"] == "scbe_sparse_octree_retrieval_v1"
    assert payload["multiview_projection"]["views"]["kind"]["tool"] == ["convert-code"]


def test_lightning_indexer_uses_block_first_sparse_shape() -> None:
    candidates = [
        {"candidate_id": f"noise-{idx}", "text": "generic unrelated candidate"}
        for idx in range(12)
    ]
    candidates.append({"candidate_id": "tests", "text": "pytest geoseal agent verification benchmark", "priority": 5})

    payload = select_sparse_candidates("geoseal benchmark tests", candidates, top_k=2, block_size=4, block_multiplier=1)

    assert payload["candidate_count"] == 13
    assert payload["selected_block_count"] <= 2
    assert any(row["candidate_id"] == "tests" for row in payload["selected"])
    assert any(row["candidate_id"] == "tests" for row in payload["context_channels"]["global_anchor"])
    assert "tests" in payload["hybrid_attention_plan"]["pack_order"]


def test_lightning_indexer_octree_retrieval_uses_explicit_spatial_coords() -> None:
    payload = select_sparse_candidates(
        "mars terrain route",
        [
            {
                "candidate_id": "near",
                "text": "terrain route local map",
                "spatial_coords": [0.1, 0.2, 0.3],
                "priority": 1,
            },
            {
                "candidate_id": "far",
                "text": "unrelated archive",
                "spatial_coords": [-0.9, -0.8, -0.7],
                "priority": 10,
            },
        ],
        top_k=1,
        channel_budget=1,
    )

    rows = payload["octree_retrieval"]["rows"]
    assert len(rows) == 1
    assert rows[0]["candidate_id"] in {"near", "far"}
    assert "octree_point" in rows[0]
    assert "target_point" in rows[0]


def test_geoseal_lightning_indexer_cli_accepts_inline_candidates() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "src.geoseal_cli",
            "lightning-indexer",
            "--goal",
            "multi agent call collision route",
            "--inline-candidates",
            json.dumps(
                [
                    {"candidate_id": "visual", "text": "demo colors and layout"},
                    {
                        "candidate_id": "switchboard",
                        "text": "multi agent call switchboard collision route",
                        "kind": "tool",
                    },
                ]
            ),
            "--top-k",
            "1",
            "--json",
        ],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=120,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["selected"][0]["candidate_id"] == "switchboard"


def test_lightning_indexer_is_read_policy_and_harness_visible() -> None:
    assert geoseal_command_to_tool_class("lightning-indexer") == "read"

    manifest = build_agent_harness_manifest_v1(inline_goal="select sparse tool context", permission_mode="observe")
    assert "lightning_indexer_json" in manifest["geoseal_cli"]
    assert "lightning_indexer" in manifest["mcp_style_exports"]["resources"]
    read_contract = next(row for row in manifest["tool_contracts"] if row["tool"] == "read")
    assert "lightning-indexer" in read_contract["routes"]
