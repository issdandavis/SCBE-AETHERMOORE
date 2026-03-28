from __future__ import annotations

import io
import json
import sys
import types
from pathlib import Path
from urllib import error as urllib_error

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from workflows.n8n import scbe_n8n_bridge as bridge  # noqa: E402
except (ImportError, Exception):
    pytest.skip("dependency not available (fastapi required by scbe_n8n_bridge)", allow_module_level=True)


def test_send_zapier_event_blocks_non_allowlisted_host(monkeypatch) -> None:
    monkeypatch.setattr(bridge, "_ZAPIER_WEBHOOK_URL", "https://evil.example.com/hook")
    result = bridge._send_zapier_event({"event": "llm_dispatch"})
    assert result["status"] == "blocked"
    assert "allowlist" in result["reason"]


def test_send_zapier_event_skips_when_no_env_hook(monkeypatch) -> None:
    monkeypatch.setattr(bridge, "_ZAPIER_WEBHOOK_URL", "")
    result = bridge._send_zapier_event({"event": "llm_dispatch"})
    assert result["status"] == "skipped"


def test_send_zapier_event_hides_exception_text(monkeypatch) -> None:
    monkeypatch.setattr(bridge, "_ZAPIER_WEBHOOK_URL", "https://hooks.zapier.com/hooks/catch/123/abc")

    def fake_urlopen(*args, **kwargs):
        raise RuntimeError("secret webhook failure")

    monkeypatch.setattr(bridge.urllib_request, "urlopen", fake_urlopen)
    result = bridge._send_zapier_event({"event": "llm_dispatch"})

    assert result["status"] == "failed"
    assert result["error"] == "zapier_webhook_failed"
    assert "secret webhook failure" not in json.dumps(result)


def test_browser_health_check_hides_internal_exception_text(monkeypatch) -> None:
    def fake_urlopen(*args, **kwargs):
        raise urllib_error.URLError("secret host details")

    monkeypatch.setattr(bridge.urllib_request, "urlopen", fake_urlopen)

    result = bridge._browser_health_check()

    assert result["reachable"] is False
    assert result["error"] == "browser_service_network_error"
    assert "secret host details" not in json.dumps(result)


@pytest.mark.asyncio
async def test_llm_dispatch_ignores_user_hook_override(monkeypatch) -> None:
    monkeypatch.setattr(bridge, "_API_KEYS", {"test-key"})

    monkeypatch.setattr(
        bridge,
        "_dispatch_openai_compatible",
        lambda *args, **kwargs: {"choices": [{"message": {"content": "ok"}}]},
    )
    monkeypatch.setattr(
        bridge,
        "_extract_openai_style_response",
        lambda _resp: {"text": "ok", "tool_calls": []},
    )
    monkeypatch.setattr(
        bridge,
        "_send_zapier_event",
        lambda **kwargs: {"status": "sent", "event": kwargs.get("event_payload", {}).get("event")},
    )

    req = bridge.LLMDispatchRequest.model_validate(
        {
            "provider": "openai",
            "messages": [{"role": "user", "content": "hello"}],
            "route_to_zapier": True,
            # this key should be ignored because it is not part of the model
            "zapier_hook_url": "https://evil.example.com/hook",
        }
    )
    result = await bridge.llm_dispatch(req, x_api_key="test-key")

    assert result["zapier"]["status"] == "sent"
    assert "zapier_hook_url" not in req.model_dump()


def test_dispatch_single_provider_hides_exception_text(monkeypatch) -> None:
    monkeypatch.setattr(
        bridge,
        "_dispatch_openai_compatible",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("secret stack details")),
    )

    result = bridge._dispatch_single_provider("openai", "hello", "system prompt")

    assert result["status"] == "error"
    assert result["error"] == "provider_dispatch_failed"
    assert "secret" not in json.dumps(result)


@pytest.mark.asyncio
async def test_execute_code_hides_kernel_runner_exception_text(monkeypatch) -> None:
    def fake_urlopen(*args, **kwargs):
        raise RuntimeError("secret kernel-runner details")

    monkeypatch.setattr(bridge.urllib_request, "urlopen", fake_urlopen)

    result = await bridge.execute_code(bridge.CodeExecRequest(code="print('hi')"))

    assert result["stderr"] == "kernel-runner request failed"
    assert "secret kernel-runner details" not in json.dumps(result)


def test_forward_to_browser_service_hides_upstream_body(monkeypatch) -> None:
    error = urllib_error.HTTPError(
        url="http://127.0.0.1:8011/v1/integrations/n8n/browse",
        code=502,
        msg="Bad Gateway",
        hdrs=None,
        fp=io.BytesIO(b'{"error":"token=secret-browser-token"}'),
    )

    def fake_urlopen(*args, **kwargs):
        raise error

    monkeypatch.setattr(bridge.urllib_request, "urlopen", fake_urlopen)

    with pytest.raises(bridge.HTTPException) as exc:
        bridge._forward_to_browser_service({"actions": []}, "test-key")

    detail = exc.value.detail
    assert detail["error"] == "browser_service_http_error"
    assert detail["upstream_status"] == 502
    assert detail["detail_present"] is True
    assert "secret-browser-token" not in json.dumps(detail)


def test_notion_request_hides_upstream_body(monkeypatch) -> None:
    monkeypatch.setenv("NOTION_TOKEN", "test-token")

    error = urllib_error.HTTPError(
        url="https://api.notion.com/v1/search",
        code=502,
        msg="Bad Gateway",
        hdrs=None,
        fp=io.BytesIO(b'{"error":"secret-notion-token"}'),
    )

    def fake_urlopen(*args, **kwargs):
        raise error

    monkeypatch.setattr(bridge.urllib_request, "urlopen", fake_urlopen)

    with pytest.raises(bridge.HTTPException) as exc:
        bridge._notion_request(method="POST", path="/v1/search", payload={})

    detail = exc.value.detail
    assert detail["error"] == "notion_http_error"
    assert detail["upstream_status"] == 502
    assert detail["detail_present"] is True
    assert "secret-notion-token" not in json.dumps(detail)


def test_get_trainer_hides_startup_exception_text(monkeypatch) -> None:
    class BoomTrainer:
        def __init__(self):
            raise RuntimeError("secret trainer boot detail")

    fake_module = types.SimpleNamespace(RealTimeHFTrainer=BoomTrainer, load_dotenv=lambda: None)
    monkeypatch.setitem(sys.modules, "hf_trainer", fake_module)
    monkeypatch.setattr(bridge, "_trainer", None)

    with pytest.raises(bridge.HTTPException) as exc:
        bridge._get_trainer()

    assert exc.value.status_code == 503
    assert exc.value.detail == "Training pipeline unavailable."


@pytest.mark.asyncio
async def test_workflow_lattice25d_accepts_inline_notes(monkeypatch) -> None:
    monkeypatch.setattr(bridge, "_API_KEYS", {"test-key"})

    req = bridge.Lattice25DRequest.model_validate(
        {
            "notes": [
                {
                    "note_id": "n1",
                    "text": "Swarm lane note with 2026-03-05 checkpoint and metric tags.",
                    "tags": ["swarm", "checkpoint"],
                    "source": "notion",
                    "authority": "internal",
                    "tongue": "DR",
                },
                {
                    "note_id": "n2",
                    "text": "Council synthesis note with url https://example.com and fallback plan.",
                    "tags": ["council"],
                    "source": "repo",
                    "authority": "sealed",
                    "tongue": "KO",
                },
            ],
            "include_repo_notes": False,
            "query_top_k": 2,
        }
    )
    result = await bridge.workflow_lattice25d(req, x_api_key="test-key")

    assert result["ingested_count"] == 2
    assert result["source"] == "n8n-bridge"
    assert result["stats"]["bundle_count"] == 2
    assert len(result["nearest"]) == 2
    assert any("tag:swarm" in tag for tag in result["notes"][0]["metric_tags"])


@pytest.mark.asyncio
async def test_workflow_lattice25d_rejects_empty_input(monkeypatch) -> None:
    monkeypatch.setattr(bridge, "_API_KEYS", {"test-key"})

    req = bridge.Lattice25DRequest.model_validate(
        {
            "notes": [],
            "include_repo_notes": False,
        }
    )
    with pytest.raises(bridge.HTTPException) as exc:
        await bridge.workflow_lattice25d(req, x_api_key="test-key")

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_workflow_lattice25d_includes_notion_notes(monkeypatch) -> None:
    monkeypatch.setattr(bridge, "_API_KEYS", {"test-key"})
    monkeypatch.setattr(
        bridge,
        "_fetch_notion_notes",
        lambda **kwargs: [
            {
                "note_id": "notion:abc",
                "text": "Notion lane note with governance details",
                "tags": ["notion", "governance"],
                "source": "notion",
                "authority": "internal",
                "tongue": "KO",
            }
        ],
    )

    req = bridge.Lattice25DRequest.model_validate(
        {
            "notes": [],
            "include_notion_notes": True,
            "include_repo_notes": False,
            "max_notes": 5,
        }
    )
    result = await bridge.workflow_lattice25d(req, x_api_key="test-key")
    assert result["ingested_count"] == 1
    assert result["input_notion_enabled"] is True
    assert result["notes"][0]["note_id"] == "notion:abc"


@pytest.mark.asyncio
async def test_workflow_lattice25d_hf_export_staged(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(bridge, "_API_KEYS", {"test-key"})
    repo_root = tmp_path / "repo-root"
    repo_root.mkdir()
    monkeypatch.setattr(bridge, "_PROJECT", str(repo_root))
    out_path = repo_root / "artifacts" / "hf" / "lattice_export.jsonl"

    req = bridge.Lattice25DRequest.model_validate(
        {
            "notes": [
                {
                    "note_id": "n1",
                    "text": "Export note",
                    "tags": ["export"],
                    "source": "repo",
                    "authority": "internal",
                    "tongue": "DR",
                }
            ],
            "include_repo_notes": False,
            "hf_output_path": "artifacts/hf/lattice_export.jsonl",
            "hf_dataset_repo": "issdandavis/scbe-lattice-notes",
            "hf_push": False,
        }
    )
    result = await bridge.workflow_lattice25d(req, x_api_key="test-key")

    assert result["hf_export"]["status"] == "staged"
    assert out_path.exists()
    lines = out_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    first = json.loads(lines[0])
    assert first["note_id"] == "n1"


def test_resolve_repo_relative_output_path_rejects_absolute_path(tmp_path) -> None:
    with pytest.raises(bridge.HTTPException) as exc:
        bridge._resolve_repo_relative_output_path(str(tmp_path / "bad.jsonl"))

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_workflow_lattice25d_rejects_invalid_hf_dataset_repo(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(bridge, "_API_KEYS", {"test-key"})
    repo_root = tmp_path / "repo-root"
    repo_root.mkdir()
    monkeypatch.setattr(bridge, "_PROJECT", str(repo_root))

    req = bridge.Lattice25DRequest.model_validate(
        {
            "notes": [
                {
                    "note_id": "n1",
                    "text": "Export note",
                    "tags": ["export"],
                    "source": "repo",
                    "authority": "internal",
                    "tongue": "DR",
                }
            ],
            "include_repo_notes": False,
            "hf_output_path": "artifacts/hf/lattice_export.jsonl",
            "hf_dataset_repo": "../../evil",
            "hf_push": False,
        }
    )

    with pytest.raises(bridge.HTTPException) as exc:
        await bridge.workflow_lattice25d(req, x_api_key="test-key")

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_workflow_lattice25d_push_requires_allowlisted_repo(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(bridge, "_API_KEYS", {"test-key"})
    monkeypatch.setattr(bridge, "_HF_ALLOWED_DATASET_REPOS", set())
    monkeypatch.setattr(bridge, "_HF_ROUTER_TOKEN", "hf_test_token")
    repo_root = tmp_path / "repo-root"
    repo_root.mkdir()
    monkeypatch.setattr(bridge, "_PROJECT", str(repo_root))

    req = bridge.Lattice25DRequest.model_validate(
        {
            "notes": [
                {
                    "note_id": "n1",
                    "text": "Export note",
                    "tags": ["export"],
                    "source": "repo",
                    "authority": "internal",
                    "tongue": "DR",
                }
            ],
            "include_repo_notes": False,
            "hf_output_path": "artifacts/hf/lattice_export.jsonl",
            "hf_dataset_repo": "issdandavis/scbe-lattice-notes",
            "hf_push": True,
        }
    )

    with pytest.raises(bridge.HTTPException) as exc:
        await bridge.workflow_lattice25d(req, x_api_key="test-key")

    assert exc.value.status_code == 403
