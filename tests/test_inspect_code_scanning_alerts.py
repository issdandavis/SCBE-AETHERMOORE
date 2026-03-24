from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = (
    ROOT / "skills" / "codex-mirror" / "scbe-code-scanning-ops" / "scripts" / "inspect_code_scanning_alerts.py"
)


def _load_module():
    spec = importlib.util.spec_from_file_location("test_code_scanning_alerts", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_summarize_alerts_groups_rule_and_path_counts() -> None:
    module = _load_module()
    alerts = [
        {
            "number": 2261,
            "state": "open",
            "tool": {"name": "CodeQL"},
            "rule": {
                "id": "py/incomplete-url-substring-sanitization",
                "name": "Incomplete URL substring sanitization",
                "security_severity_level": "high",
            },
            "most_recent_instance": {"location": {"path": "src/aetherbrowser/page_analyzer.py", "start_line": 152}},
            "html_url": "https://example.test/2261",
        },
        {
            "number": 2258,
            "state": "open",
            "tool": {"name": "CodeQL"},
            "rule": {
                "id": "py/incomplete-url-substring-sanitization",
                "name": "Incomplete URL substring sanitization",
                "security_severity_level": "high",
            },
            "most_recent_instance": {"location": {"path": "src/browser/toolkit.py", "start_line": 189}},
            "html_url": "https://example.test/2258",
        },
        {
            "number": 2259,
            "state": "open",
            "tool": {"name": "CodeQL"},
            "rule": {"id": "js/bad-tag-filter", "name": "Bad HTML filtering regexp", "security_severity_level": "high"},
            "most_recent_instance": {"location": {"path": "src/browser/toolkit.py", "start_line": 136}},
            "html_url": "https://example.test/2259",
        },
    ]

    summary = module.summarize_alerts(alerts)

    assert summary["alert_count"] == 3
    assert summary["rule_counts"]["py/incomplete-url-substring-sanitization"] == 2
    assert summary["rule_counts"]["js/bad-tag-filter"] == 1
    top_paths = {row["path"]: row["count"] for row in summary["top_paths"]}
    assert top_paths["src/browser/toolkit.py"] == 2
    assert top_paths["src/aetherbrowser/page_analyzer.py"] == 1


def test_render_text_mentions_alert_ids_and_locations() -> None:
    module = _load_module()
    summary = {
        "alert_count": 1,
        "rule_counts": {"py/path-injection": 1},
        "severity_counts": {"high": 1},
        "top_paths": [{"path": "scripts/system/ai_bridge.py", "count": 1}],
        "alerts": [
            {
                "number": 2249,
                "rule_id": "py/path-injection",
                "severity": "high",
                "path": "scripts/system/ai_bridge.py",
                "start_line": 60,
            }
        ],
    }

    text = module.render_text(summary, top=5)

    assert "#2249" in text
    assert "scripts/system/ai_bridge.py:60" in text
    assert "py/path-injection" in text
