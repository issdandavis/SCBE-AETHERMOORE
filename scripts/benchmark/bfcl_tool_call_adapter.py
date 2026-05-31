#!/usr/bin/env python3
"""SCBE → BFCL Tool-Call Adapter.

Two lanes:

1. **Schema export** (always runs, offline):
   Reads packages/agent-bus/tools.json and emits BFCL-compatible OpenAI
   function schemas (name, description, parameters with extracted {param}
   placeholders).  Each schema is AST-validated for structural correctness.
   This is the primary deliverable — any BFCL-compliant evaluator can consume
   the exported schemas directly.

2. **Description-clarity probe** (optional, requires Ollama):
   Sends 20 hand-authored test cases to a local model via the OpenAI-compatible
   Ollama endpoint.  The model sees all 54 tool schemas and must pick the right
   one (or correctly abstain for irrelevance cases).

   **Honest caveat** baked into every report:
   - Test cases are hand-authored from tool descriptions, not from BFCL's
     official dataset.  This measures *description clarity + model instruction-
     following*, not a leaderboard-comparable BFCL score.
   - Use the exported schemas with the official BFCL dataset for leaderboard-
     comparable evaluation.

Each model call produces a SHA-256 receipt that chains from the prior receipt,
giving an auditable eval transcript.

Usage:
    python scripts/benchmark/bfcl_tool_call_adapter.py
    python scripts/benchmark/bfcl_tool_call_adapter.py --export-only
    python scripts/benchmark/bfcl_tool_call_adapter.py --model llama3.2
    python scripts/benchmark/bfcl_tool_call_adapter.py --endpoint http://localhost:11434/v1
    python scripts/benchmark/bfcl_tool_call_adapter.py --out-dir artifacts/benchmarks

  Against Groq (free tier, supports tool calling):
    python scripts/benchmark/bfcl_tool_call_adapter.py \\
      --endpoint https://api.groq.com/openai/v1 \\
      --model llama-3.3-70b-versatile \\
      --auth-env GROQ_API_KEY

  Against Cerebras (fastest free tier):
    python scripts/benchmark/bfcl_tool_call_adapter.py \\
      --endpoint https://api.cerebras.ai/v1 \\
      --model gpt-oss-120b \\
      --auth-env CEREBRAS_API_KEY
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
TOOLS_JSON = ROOT / "packages" / "agent-bus" / "tools.json"
ARTIFACT_DIR = ROOT / "artifacts" / "benchmarks"

# ── Parameter extraction ───────────────────────────────────────────────────────

_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")

# Known placeholder descriptions derived from tools.ts template variable docs.
_PARAM_DESCRIPTIONS: dict[str, str] = {
    "task": "The task, query, or payload to process",
    "taskType": "Task type classification (e.g. 'general', 'research', 'coding')",
    "seriesId": "Series or run identifier for grouping related events",
    "privacy": "Privacy scope (e.g. 'local_only', 'shared')",
    "repoRoot": "Repository root path (substituted automatically at dispatch time)",
}


def _extract_params(args: list[str]) -> list[str]:
    """Return deduplicated placeholder names found in args, preserving order."""
    seen: list[str] = []
    for arg in args:
        for name in _PLACEHOLDER_RE.findall(arg):
            if name not in seen:
                seen.append(name)
    return seen


# ── Schema export ──────────────────────────────────────────────────────────────

def tools_to_bfcl_schemas(tools_path: Path) -> list[dict[str, Any]]:
    """Convert tools.json → list of BFCL-compatible OpenAI function schemas."""
    tools: list[dict[str, Any]] = json.loads(tools_path.read_text(encoding="utf-8"))
    schemas: list[dict[str, Any]] = []
    for tool in tools:
        params = _extract_params(tool.get("args", []))
        properties = {
            p: {
                "type": "string",
                "description": _PARAM_DESCRIPTIONS.get(p, f"Value for {p}"),
            }
            for p in params
        }
        # Exclude repoRoot — it's substituted by the bus, never caller-supplied.
        required = [p for p in params if p != "repoRoot"]
        schema: dict[str, Any] = {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        }
        schemas.append(schema)
    return schemas


# ── AST validation ─────────────────────────────────────────────────────────────

@dataclass
class SchemaValidationResult:
    name: str
    ok: bool
    errors: list[str] = field(default_factory=list)


def validate_bfcl_schema(schema: dict[str, Any]) -> SchemaValidationResult:
    """Structural AST check: verify schema is BFCL/OpenAI-compatible."""
    errors: list[str] = []
    name = schema.get("name", "<unnamed>")

    if not isinstance(schema.get("name"), str) or not schema["name"].strip():
        errors.append("missing or empty 'name'")
    if not isinstance(schema.get("description"), str):
        errors.append("missing or non-string 'description'")

    params = schema.get("parameters")
    if not isinstance(params, dict):
        errors.append("'parameters' must be an object")
    else:
        if params.get("type") != "object":
            errors.append("parameters.type must be 'object'")
        if not isinstance(params.get("properties"), dict):
            errors.append("parameters.properties must be an object")
        if not isinstance(params.get("required"), list):
            errors.append("parameters.required must be an array")
        else:
            props = params.get("properties", {})
            for req_param in params["required"]:
                if req_param not in props:
                    errors.append(f"required param '{req_param}' missing from properties")

    return SchemaValidationResult(name=name, ok=not errors, errors=errors)


def validate_all_schemas(
    schemas: list[dict[str, Any]]
) -> dict[str, Any]:
    results = [validate_bfcl_schema(s) for s in schemas]
    ok_count = sum(1 for r in results if r.ok)
    return {
        "total": len(results),
        "ok": ok_count,
        "failed": len(results) - ok_count,
        "pass_rate": round(ok_count / len(results), 4) if results else 0.0,
        "failures": [
            {"name": r.name, "errors": r.errors} for r in results if not r.ok
        ],
    }


# ── Test fixtures ──────────────────────────────────────────────────────────────
# Rules for authoring:
#   1. User phrasing must NOT contain the tool name.
#   2. User phrasing must NOT restate the tool description verbatim.
#   3. Irrelevance cases expect no function call (ground_truth_tool = None).
#   4. Args express the value the caller should fill — not "task='...'" syntax.

TEST_CASES: list[dict[str, Any]] = [
    # ── Geoseal / governance ──────────────────────────────────────────────────
    {
        "id": "tc_01",
        "question": "Turn this into a structured governance action plan: 'validate user session before every API call'",
        "ground_truth_tool": "geoseal-compile",
        "ground_truth_args": {"task": "validate user session before every API call"},
        "category": "governance",
    },
    {
        "id": "tc_02",
        "question": "I want to stamp this payload with its permission tier before routing it: {\"action\":\"deploy\",\"env\":\"prod\"}",
        "ground_truth_tool": "geoseal-seal",
        "ground_truth_args": {"task": "{\"action\":\"deploy\",\"env\":\"prod\"}"},
        "category": "governance",
    },
    {
        "id": "tc_03",
        "question": "Which Sacred Tongue language is best for this Python snippet and why? `def add(x, y): return x + y`",
        "ground_truth_tool": "geoseal-explain-route",
        "ground_truth_args": {"task": "def add(x, y): return x + y"},
        "category": "governance",
    },
    {
        "id": "tc_04",
        "question": "I wrote a function template in Python. Can you re-express it in Rust?",
        "ground_truth_tool": "geoseal-cross-build",
        "ground_truth_args": {"task": "def add(x, y): return x + y"},
        "category": "bijective-transport",
    },
    {
        "id": "tc_05",
        "question": "Translate this template into every supported language at once: `(x + y)`",
        "ground_truth_tool": "geoseal-cross-build-broadcast",
        "ground_truth_args": {"task": "(x + y)"},
        "category": "bijective-transport",
    },
    # ── Research APIs ─────────────────────────────────────────────────────────
    {
        "id": "tc_06",
        "question": "Find preprints about hyperbolic geometry applied to neural networks",
        "ground_truth_tool": "research-arxiv",
        "ground_truth_args": {"task": "hyperbolic geometry neural networks"},
        "category": "research",
    },
    {
        "id": "tc_07",
        "question": "What are the most highly-cited papers on adversarial machine learning?",
        "ground_truth_tool": "research-semantic-scholar",
        "ground_truth_args": {"task": "adversarial machine learning"},
        "category": "research",
    },
    {
        "id": "tc_08",
        "question": "Are there any open government contracts looking for AI safety evaluation tools?",
        "ground_truth_tool": "research-sam-gov",
        "ground_truth_args": {"task": "AI safety evaluation"},
        "category": "research",
    },
    {
        "id": "tc_09",
        "question": "Search the patent database for applications about post-quantum key exchange",
        "ground_truth_tool": "research-uspto",
        "ground_truth_args": {"task": "post-quantum key exchange"},
        "category": "research",
    },
    {
        "id": "tc_10",
        "question": "I need to find open-source governance models already uploaded to the model hub",
        "ground_truth_tool": "research-hf-models",
        "ground_truth_args": {"task": "governance models"},
        "category": "research",
    },
    # ── Encoding / tokenizer ──────────────────────────────────────────────────
    {
        "id": "tc_11",
        "question": "Show me the raw hex and binary bytes for: hello world",
        "ground_truth_tool": "binary-hex-compiler",
        "ground_truth_args": {"task": "hello world"},
        "category": "encoding",
    },
    {
        "id": "tc_12",
        "question": "Run the text 'pipeline integrity must hold' through the six-dimensional semantic routing layer",
        "ground_truth_tool": "semantic-hex-bridge",
        "ground_truth_args": {"task": "pipeline integrity must hold"},
        "category": "encoding",
    },
    {
        "id": "tc_13",
        "question": "This paragraph is too long for the packet. Trim it to fit without losing meaning: "
        "'The SCBE framework uses hyperbolic geometry to impose exponential cost scaling on adversarial "
        "behavior, making attacks computationally infeasible while keeping benign operations efficient.'",
        "ground_truth_tool": "auto-abridge",
        "ground_truth_args": {
            "task": "The SCBE framework uses hyperbolic geometry to impose exponential cost scaling "
            "on adversarial behavior, making attacks computationally infeasible while keeping "
            "benign operations efficient."
        },
        "category": "encoding",
    },
    # ── Agent routing / harness ───────────────────────────────────────────────
    {
        "id": "tc_14",
        "question": "What's the current UTC time?",
        "ground_truth_tool": "scbe-clock-ticker",
        "ground_truth_args": {"task": ""},
        "category": "harness",
    },
    {
        "id": "tc_15",
        "question": "I need a development plan for building a REST API with authentication",
        "ground_truth_tool": "chessboard-dev-stack",
        "ground_truth_args": {"task": "REST API with authentication"},
        "category": "harness",
    },
    {
        "id": "tc_16",
        "question": "Route this question to the cheapest available AI for a quick answer: what is 2+2?",
        "ground_truth_tool": "ai-router-call",
        "ground_truth_args": {"task": "what is 2+2?"},
        "category": "harness",
    },
    {
        "id": "tc_17",
        "question": "Are all my AI model providers currently reachable?",
        "ground_truth_tool": "ai-router-health",
        "ground_truth_args": {},
        "category": "harness",
    },
    {
        "id": "tc_18",
        "question": "Scan the workspace for anything that looks unsafe or malicious",
        "ground_truth_tool": "scbe-antivirus",
        "ground_truth_args": {},
        "category": "security",
    },
    # ── Irrelevance ───────────────────────────────────────────────────────────
    {
        "id": "tc_19",
        "question": "What's the weather forecast in Seattle tomorrow?",
        "ground_truth_tool": None,
        "ground_truth_args": {},
        "category": "irrelevance",
    },
    {
        "id": "tc_20",
        "question": "Book me a flight from Seattle to Chicago next Tuesday",
        "ground_truth_tool": None,
        "ground_truth_args": {},
        "category": "irrelevance",
    },
]


# ── Receipt chaining ───────────────────────────────────────────────────────────

def _sha256(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def _make_receipt(
    case_id: str,
    question: str,
    expected_tool: str | None,
    model_tool: str | None,
    model_args: dict[str, Any],
    correct: bool,
    prev_hash: str,
    ts: str,
) -> dict[str, Any]:
    payload = json.dumps(
        {
            "case_id": case_id,
            "expected_tool": expected_tool,
            "model_tool": model_tool,
            "correct": correct,
            "ts": ts,
        },
        sort_keys=True,
    )
    receipt_hash = _sha256(prev_hash + payload)
    return {
        "case_id": case_id,
        "question": question[:120] + ("..." if len(question) > 120 else ""),
        "expected_tool": expected_tool,
        "model_tool": model_tool,
        "model_args": model_args,
        "correct": correct,
        "ts": ts,
        "prev_hash": prev_hash,
        "receipt_hash": receipt_hash,
    }


# ── Ollama model call ──────────────────────────────────────────────────────────

def _call_model(
    endpoint: str,
    model: str,
    question: str,
    tool_schemas: list[dict[str, Any]],
    timeout: int = 60,
    auth_token: str | None = None,
) -> tuple[str | None, dict[str, Any], str]:
    """Call model with tool schemas. Returns (tool_name, args, raw_response_snippet)."""
    try:
        import openai  # type: ignore[import]
    except ImportError as exc:
        raise ConnectionError(
            "openai SDK not installed; run: pip install openai"
        ) from exc

    try:
        client = openai.OpenAI(
            base_url=endpoint.rstrip("/"),
            api_key=auth_token or "no-key",
            timeout=timeout,
        )
        tools_payload = [
            {"type": "function", "function": s} for s in tool_schemas
        ]
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": question}],
            tools=tools_payload,
            tool_choice="auto",
            max_tokens=256,
            temperature=0,
        )
    except Exception as exc:  # noqa: BLE001
        raise ConnectionError(f"Model call failed ({endpoint}): {exc}") from exc

    message = resp.choices[0].message
    raw_snippet = json.dumps(message.model_dump(), default=str)[:500]
    tool_calls = message.tool_calls or []
    if tool_calls:
        fn = tool_calls[0].function
        called_name = fn.name
        raw_args = fn.arguments or "{}"
        try:
            called_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
        except json.JSONDecodeError:
            called_args = {"_raw": raw_args}
        return called_name, called_args, raw_snippet
    return None, {}, raw_snippet


# ── Scoring ────────────────────────────────────────────────────────────────────

def _score_tool_selection(
    expected: str | None, got: str | None
) -> bool:
    """A call is correct when expected == got (both None counts as correct abstention)."""
    return expected == got


# ── Main benchmark flow ────────────────────────────────────────────────────────

def run_export_and_validate(
    tools_path: Path,
) -> dict[str, Any]:
    schemas = tools_to_bfcl_schemas(tools_path)
    validation = validate_all_schemas(schemas)
    return {
        "schema_export": {
            "tools_source": str(tools_path),
            "tool_count": len(schemas),
            "schemas": schemas,
        },
        "ast_validation": validation,
    }


def run_model_eval(
    schemas: list[dict[str, Any]],
    endpoint: str,
    model: str,
    timeout: int = 60,
    auth_token: str | None = None,
) -> dict[str, Any]:
    receipts: list[dict[str, Any]] = []
    prev_hash = "0" * 64
    correct = 0
    errors: list[str] = []
    category_scores: dict[str, list[bool]] = {}

    for case in TEST_CASES:
        ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        try:
            model_tool, model_args, _ = _call_model(
                endpoint, model, case["question"], schemas,
                timeout=timeout, auth_token=auth_token,
            )
        except ConnectionError as exc:
            err_str = str(exc)
            errors.append(f"{case['id']}: {err_str}")
            # Auth/connectivity errors affect all cases — stop early.
            stop_keywords = ("401", "403", "AuthenticationError", "unreachable",
                             "not installed", "Connection")
            if any(kw in err_str for kw in stop_keywords):
                break
            model_tool, model_args = None, {}
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{case['id']}: unexpected error — {exc}")
            model_tool, model_args = None, {}

        is_correct = _score_tool_selection(case["ground_truth_tool"], model_tool)
        if is_correct:
            correct += 1

        cat = case.get("category", "other")
        category_scores.setdefault(cat, []).append(is_correct)

        receipt = _make_receipt(
            case_id=case["id"],
            question=case["question"],
            expected_tool=case["ground_truth_tool"],
            model_tool=model_tool,
            model_args=model_args,
            correct=is_correct,
            prev_hash=prev_hash,
            ts=ts,
        )
        receipts.append(receipt)
        prev_hash = receipt["receipt_hash"]
        time.sleep(0.05)  # rate-limit courtesy

    total_run = len(receipts)
    return {
        "model": model,
        "endpoint": endpoint,
        "cases_run": total_run,
        "cases_total": len(TEST_CASES),
        "correct": correct,
        "accuracy": round(correct / total_run, 4) if total_run else 0.0,
        "category_accuracy": {
            cat: round(sum(v) / len(v), 4) for cat, v in category_scores.items()
        },
        "receipts": receipts,
        "errors": errors,
        "caveat": (
            "Test cases are hand-authored from tool descriptions — "
            "this measures description clarity and model instruction-following, "
            "NOT a leaderboard-comparable BFCL score. "
            "Use the exported schemas with the official BFCL dataset for "
            "leaderboard-comparable evaluation."
        ),
    }


def run_benchmark(
    tools_path: Path,
    export_only: bool,
    endpoint: str,
    model: str,
    timeout: int,
    auth_token: str | None = None,
) -> dict[str, Any]:
    export = run_export_and_validate(tools_path)
    report: dict[str, Any] = {
        "schema_version": "scbe.bfcl_tool_call_adapter.v1",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "tools_source": str(tools_path),
        **export,
    }

    if export_only:
        report["model_eval"] = {"skipped": True, "reason": "--export-only flag set"}
        return report

    try:
        eval_result = run_model_eval(
            export["schema_export"]["schemas"], endpoint, model, timeout,
            auth_token=auth_token,
        )
        report["model_eval"] = eval_result
    except ConnectionError as exc:
        is_local = "localhost" in endpoint or "127.0.0.1" in endpoint
        hint = (
            f"Start Ollama with 'ollama serve' and pull '{model}' to enable model eval."
            if is_local
            else f"Check that {endpoint} is reachable and --auth-env is set correctly."
        )
        report["model_eval"] = {
            "skipped": True,
            "reason": str(exc),
            "hint": hint,
        }

    return report


# ── Markdown report ────────────────────────────────────────────────────────────

def render_markdown(report: dict[str, Any]) -> str:
    val = report["ast_validation"]
    lines = [
        "# SCBE BFCL Tool-Call Adapter Report",
        "",
        f"Generated: `{report['generated_at']}`",
        "",
        "## Schema Export",
        "",
        f"- Tools source: `{report['tools_source']}`",
        f"- Tool count: **{report['schema_export']['tool_count']}**",
        f"- AST pass rate: **{val['pass_rate'] * 100:.1f}%** "
        f"({val['ok']}/{val['total']})",
        "",
    ]
    if val["failures"]:
        lines += [
            "### Schema Failures",
            "",
            "| Tool | Errors |",
            "|---|---|",
        ]
        for f in val["failures"]:
            lines.append(f"| `{f['name']}` | {'; '.join(f['errors'])} |")
        lines.append("")

    model_eval = report.get("model_eval", {})
    if model_eval.get("skipped"):
        lines += [
            "## Model Eval",
            "",
            f"**Skipped**: {model_eval.get('reason', '')}",
            "",
        ]
        if model_eval.get("hint"):
            lines.append(f"*Hint*: {model_eval['hint']}")
            lines.append("")
    else:
        acc = model_eval.get("accuracy", 0.0)
        lines += [
            "## Model Eval",
            "",
            f"> {model_eval.get('caveat', '')}",
            "",
            f"- Model: `{model_eval.get('model')}`",
            f"- Endpoint: `{model_eval.get('endpoint')}`",
            f"- Cases run: {model_eval.get('cases_run')} / {model_eval.get('cases_total')}",
            f"- **Accuracy: {acc * 100:.1f}%** "
            f"({model_eval.get('correct')}/{model_eval.get('cases_run')})",
            "",
            "### Category Breakdown",
            "",
            "| Category | Accuracy |",
            "|---|---|",
        ]
        for cat, cat_acc in sorted(model_eval.get("category_accuracy", {}).items()):
            lines.append(f"| {cat} | {cat_acc * 100:.1f}% |")
        lines.append("")

        if model_eval.get("errors"):
            lines += [
                "### Errors",
                "",
            ]
            for err in model_eval["errors"]:
                lines.append(f"- {err}")
            lines.append("")

        lines += [
            "### Per-Case Results",
            "",
            "| ID | Expected | Got | Correct |",
            "|---|---|---|---|",
        ]
        for r in model_eval.get("receipts", []):
            ok_mark = "✓" if r["correct"] else "✗"
            exp = r["expected_tool"] or "*(none)*"
            got = r["model_tool"] or "*(none)*"
            lines.append(f"| {r['case_id']} | `{exp}` | `{got}` | {ok_mark} |")
        lines.append("")

    return "\n".join(lines)


# ── CLI ────────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tools-json", default=str(TOOLS_JSON))
    parser.add_argument("--export-only", action="store_true",
                        help="Skip model eval; only export + validate schemas")
    parser.add_argument("--endpoint", default="http://localhost:11434/v1",
                        help="OpenAI-compatible endpoint (default: Ollama)")
    parser.add_argument("--model", default="llama3.2",
                        help="Model name to use for eval (default: llama3.2)")
    parser.add_argument("--timeout", type=int, default=60,
                        help="Per-call timeout in seconds (default: 60)")
    parser.add_argument(
        "--auth-env",
        default=None,
        metavar="ENV_VAR",
        help="Name of env var holding the Bearer token (e.g. GROQ_API_KEY). "
             "Never pass the token itself on the command line.",
    )
    parser.add_argument("--out-dir", default=str(ARTIFACT_DIR))
    args = parser.parse_args()

    auth_token: str | None = None
    if args.auth_env:
        auth_token = os.environ.get(args.auth_env)
        if not auth_token:
            print(json.dumps({
                "ok": False,
                "error": f"--auth-env '{args.auth_env}' is set but the env var is empty or missing",
            }, indent=2))
            return 1

    report = run_benchmark(
        tools_path=Path(args.tools_json),
        export_only=args.export_only,
        endpoint=args.endpoint,
        model=args.model,
        timeout=args.timeout,
        auth_token=auth_token,
    )

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = out_dir / f"bfcl_tool_call_adapter_{stamp}.json"
    md_path = out_dir / f"bfcl_tool_call_adapter_{stamp}.md"
    latest_json = out_dir / "bfcl_tool_call_adapter_latest.json"
    latest_md = out_dir / "bfcl_tool_call_adapter_latest.md"

    json_text = json.dumps(report, indent=2)
    md_text = render_markdown(report)

    json_path.write_text(json_text + "\n", encoding="utf-8")
    md_path.write_text(md_text + "\n", encoding="utf-8")
    latest_json.write_text(json_text + "\n", encoding="utf-8")
    latest_md.write_text(md_text + "\n", encoding="utf-8")

    val = report["ast_validation"]
    model_eval = report.get("model_eval", {})
    summary: dict[str, Any] = {
        "ok": val["failed"] == 0,
        "tool_count": report["schema_export"]["tool_count"],
        "ast_pass_rate": val["pass_rate"],
        "ast_failures": val["failed"],
        "json": str(json_path),
        "markdown": str(md_path),
        "latest_json": str(latest_json),
        "latest_markdown": str(latest_md),
    }
    if not model_eval.get("skipped"):
        summary["model_eval_accuracy"] = model_eval.get("accuracy")
        summary["model_eval_correct"] = model_eval.get("correct")
        summary["model_eval_cases"] = model_eval.get("cases_run")
        summary["model_eval_caveat"] = model_eval.get("caveat")
    else:
        summary["model_eval_skipped"] = model_eval.get("reason")

    print(json.dumps(summary, indent=2))
    return 0 if val["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
