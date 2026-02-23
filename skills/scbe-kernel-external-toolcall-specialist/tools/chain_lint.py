#!/usr/bin/env python3
"""Lint typed chain documents for SCBE kernel tool-call routes."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Set

import jsonschema

try:
    import yaml
except Exception:  # noqa: BLE001
    yaml = None


KNOWN_TOOLS: Set[str] = {
    "connector.discovery",
    "connector.action",
    "issue.create",
    "browser.playwright",
    "notion.harvest",
    "github.fetch",
    "huggingface.fetch",
    "npm.fetch",
    "latex.compile",
    "arxiv.collector",
    "local.exec",
}


def _load_obj(path: Path) -> Dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".yaml", ".yml"}:
        if yaml is None:
            raise RuntimeError("PyYAML is required for YAML input")
        obj = yaml.safe_load(raw)
    else:
        obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError("chain document must decode to an object")
    return obj


def _validate_schema(doc: Dict[str, Any], schema_path: Path) -> List[str]:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = jsonschema.Draft202012Validator(schema)
    return [f"schema: {err.message}" for err in sorted(validator.iter_errors(doc), key=lambda e: e.path)]


def _extract_gate_refs(condition: str) -> Set[str]:
    refs = set()
    for token in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\.", condition or ""):
        refs.add(token)
    return refs


def lint_chain_document(doc: Dict[str, Any]) -> List[str]:
    errors: List[str] = []
    chain = doc.get("chain")
    if not isinstance(chain, dict):
        return ["missing chain object"]

    steps = chain.get("steps")
    if not isinstance(steps, list):
        return ["chain.steps must be a list"]

    ids: Set[str] = set()
    output_keys: Set[str] = set()
    step_id_set: Set[str] = set()

    for step in steps:
        if not isinstance(step, dict):
            errors.append("all steps must be objects")
            continue
        step_id = str(step.get("id", "")).strip()
        if not step_id:
            errors.append("step missing id")
            continue
        if step_id in ids:
            errors.append(f"duplicate step id: {step_id}")
        ids.add(step_id)
        step_id_set.add(step_id)

        step_type = str(step.get("type", "")).strip()
        if step_type not in {"tool", "llm", "gate"}:
            errors.append(f"invalid step type for {step_id}: {step_type}")

        if step_type in {"tool", "llm"}:
            key = str(step.get("output_key", "")).strip()
            if key:
                output_keys.add(key)

        if step_type == "tool":
            tool_name = str(step.get("tool", "")).strip()
            needs_configuration = bool(step.get("needs_configuration", False))
            if tool_name not in KNOWN_TOOLS and not needs_configuration:
                errors.append(
                    f"unknown tool '{tool_name}' in step '{step_id}' (set needs_configuration: true to defer)"
                )

    for step in steps:
        if not isinstance(step, dict):
            continue
        if str(step.get("type", "")).strip() != "gate":
            continue

        gate_id = str(step.get("id", "")).strip()
        condition = str(step.get("condition", "")).strip()
        refs = _extract_gate_refs(condition)
        for ref in refs:
            if ref not in output_keys:
                errors.append(
                    f"gate '{gate_id}' condition references unknown output key '{ref}'"
                )

        on_true = str(step.get("on_true", "")).strip()
        on_false = str(step.get("on_false", "")).strip()
        if on_true and on_true not in step_id_set:
            errors.append(f"gate '{gate_id}' on_true target '{on_true}' not found")
        if on_false and on_false not in step_id_set:
            errors.append(f"gate '{gate_id}' on_false target '{on_false}' not found")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint SCBE typed chain")
    parser.add_argument("--chain", required=True, help="path to chain .yaml/.json")
    parser.add_argument(
        "--schema",
        default=str(Path(__file__).resolve().parents[1] / "schemas" / "typed-chain.schema.json"),
        help="path to typed-chain schema",
    )
    args = parser.parse_args()

    chain_path = Path(args.chain)
    schema_path = Path(args.schema)
    doc = _load_obj(chain_path)

    errors = _validate_schema(doc, schema_path)
    errors.extend(lint_chain_document(doc))

    if errors:
        print(
            json.dumps(
                {
                    "ok": False,
                    "chain": str(chain_path),
                    "errors": errors,
                },
                indent=2,
            )
        )
        return 2

    print(json.dumps({"ok": True, "chain": str(chain_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
