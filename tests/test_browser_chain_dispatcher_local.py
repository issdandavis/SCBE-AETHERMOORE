from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def _load_dispatcher_module():
    repo_root = Path(__file__).resolve().parents[1]
    script_path = repo_root / "scripts" / "system" / "browser_chain_dispatcher.py"
    spec = importlib.util.spec_from_file_location(
        "browser_chain_dispatcher_module", script_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load dispatcher module from {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _build_dispatcher():
    dispatcher_mod = _load_dispatcher_module()
    dispatcher = dispatcher_mod.BrowserChainDispatcher()
    for tentacle in dispatcher_mod.build_default_fleet():
        dispatcher.register_tentacle(tentacle)
    return dispatcher


@pytest.mark.parametrize(
    ("domain", "expected_host"),
    [
        ("10.0.2.2:8088", "10.0.2.2"),
        ("localhost:8400", "localhost"),
        ("http://127.0.0.1:8500/arena", "127.0.0.1"),
    ],
)
def test_local_preview_surfaces_route_to_preview_tentacle(
    domain: str, expected_host: str
):
    dispatcher = _build_dispatcher()

    result = dispatcher.assign_task(domain, "navigate", {})

    assert result["tentacle_id"] == "tentacle-preview-dr"
    assert result["task_type"] == "preview"
    assert result["host"] == expected_host
    assert result["execution_engine"] == "playwright"


def test_arxiv_query_defaults_to_research_task():
    dispatcher = _build_dispatcher()

    result = dispatcher.assign_task(
        "https://arxiv.org/search/?query=hyperbolic+governance",
        "navigate",
        {"query": "hyperbolic governance"},
    )

    assert result["tentacle_id"] == "tentacle-arxiv-um"
    assert result["task_type"] == "research"
    assert result["execution_engine"] == "playwright"


def test_huggingface_search_defaults_to_search_lane():
    dispatcher = _build_dispatcher()

    result = dispatcher.assign_task(
        "https://huggingface.co/models",
        "auto",
        {"query": "static embeddings"},
    )

    assert result["tentacle_id"] == "tentacle-huggingface-ca"
    assert result["task_type"] == "search"
    assert result["execution_engine"] == "playwright"


def test_web_search_surface_gets_explicit_search_tentacle():
    dispatcher = _build_dispatcher()

    result = dispatcher.assign_task(
        "https://html.duckduckgo.com/html/?q=scbe+aetherbrowser",
        "auto",
        {"query": "SCBE AetherBrowser"},
    )

    assert result["tentacle_id"] == "tentacle-web-search-um"
    assert result["task_type"] == "search"
    assert result["execution_engine"] == "playwright"


@pytest.mark.parametrize(
    ("domain", "payload", "expected_tentacle"),
    [
        (
            "https://github.com/issues",
            {"repo_query": "browser chain dispatcher"},
            "tentacle-github-ko",
        ),
        (
            "https://www.notion.so/workspace",
            {"page_query": "browser policy note"},
            "tentacle-notion-av",
        ),
        (
            "https://admin.shopify.com/store/demo",
            {"product_query": "agent console"},
            "tentacle-shopify-ru",
        ),
    ],
)
def test_signed_in_surfaces_promote_search_when_query_present(
    domain: str,
    payload: dict[str, str],
    expected_tentacle: str,
):
    dispatcher = _build_dispatcher()

    result = dispatcher.assign_task(domain, "navigate", payload)

    assert result["tentacle_id"] == expected_tentacle
    assert result["task_type"] == "search"
    assert result["execution_engine"] == "playwriter"


def test_explicit_engine_override_wins_over_task_default():
    dispatcher = _build_dispatcher()

    result = dispatcher.assign_task(
        "https://huggingface.co/datasets",
        "search",
        {"engine": "playwriter", "dataset_query": "multi agent browser evals"},
    )

    assert result["tentacle_id"] == "tentacle-huggingface-ca"
    assert result["task_type"] == "search"
    assert result["execution_engine"] == "playwriter"
    assert result["engine_source"] == "payload_override"
