from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas" / "typed-chain.schema.json"
CHAIN_PATH = ROOT / "references" / "arxiv-chain.yaml"
LINT_PATH = ROOT / "tools" / "chain_lint.py"


def _load_lint_module():
    spec = importlib.util.spec_from_file_location("chain_lint", str(LINT_PATH))
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load chain_lint module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_arxiv_chain_validates_against_schema() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    chain_doc = yaml.safe_load(CHAIN_PATH.read_text(encoding="utf-8"))
    jsonschema.validate(chain_doc, schema)


def test_arxiv_chain_lint_passes() -> None:
    chain_doc = yaml.safe_load(CHAIN_PATH.read_text(encoding="utf-8"))
    module = _load_lint_module()
    errors = module.lint_chain_document(chain_doc)
    assert errors == [], f"expected no lint errors, got: {errors}"


def test_chain_lint_rejects_unknown_tool_without_needs_configuration() -> None:
    bad_chain = {
        "chain": {
            "id": "bad",
            "name": "bad",
            "repo": "x/y",
            "steps": [
                {
                    "id": "s1",
                    "type": "tool",
                    "tool": "unknown.tool",
                    "input": {},
                    "output_key": "o1",
                }
            ],
        }
    }
    module = _load_lint_module()
    errors = module.lint_chain_document(bad_chain)
    assert any("unknown tool" in e for e in errors), f"missing unknown-tool error: {errors}"
