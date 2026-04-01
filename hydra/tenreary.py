"""
MCP Tenreary Engine
===================

Custom multi-step itinerary type for HYDRA that can orchestrate:
- Dual browser lanes (primary + secondary)
- GitHub REST and GraphQL calls
- Connector automations (n8n / Zapier / others via ConnectorBridge)
- Content analysis backends (rule-based, OpenAI API, transformers, langchain)
- Notion run logging (append workflow summaries to page/block)
- Optional desktop notifications through PyQt5/PySide2
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .limbs import MultiTabBrowserLimb

try:
    from src.fleet.connector_bridge import ConnectorBridge, ConnectorResult
    from src.security.secret_store import get_secret
except Exception:  # pragma: no cover - fallback for limited environments
    ConnectorBridge = None  # type: ignore[assignment]
    ConnectorResult = None  # type: ignore[assignment]

    def get_secret(name: str, default: str = "") -> str:  # type: ignore[override]
        return os.environ.get(name, default)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso_now() -> str:
    return _utc_now().isoformat()


def _get_env_or_secret(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if val:
        return val
    return str(get_secret(name, "")).strip()


def _normalize_notion_id(value: str) -> str:
    return str(value or "").strip().replace("-", "")


def _ctx_lookup(context: Dict[str, Any], key_path: str) -> Any:
    key_path = key_path.strip()
    if not key_path:
        return ""

    # Prefer exact-key hit first so keys like "github.owner" work directly.
    if key_path in context:
        return context.get(key_path, "")

    if "." not in key_path:
        return context.get(key_path, "")

    node: Any = context
    for part in key_path.split("."):
        if isinstance(node, dict):
            node = node.get(part)
        else:
            return ""
    return node


def _ctx_inject(value: Any, context: Dict[str, Any]) -> Any:
    if isinstance(value, str):
        pattern = re.compile(r"\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}")

        def repl(match: re.Match[str]) -> str:
            raw = _ctx_lookup(context, match.group(1))
            if raw is None:
                return ""
            if isinstance(raw, (dict, list)):
                return json.dumps(raw, ensure_ascii=False)
            return str(raw)

        return pattern.sub(repl, value)

    if isinstance(value, list):
        return [_ctx_inject(v, context) for v in value]
    if isinstance(value, dict):
        return {k: _ctx_inject(v, context) for k, v in value.items()}
    return value


def _to_json_safe(obj: Any) -> Any:
    try:
        json.dumps(obj)
        return obj
    except Exception:
        return str(obj)


@dataclass
class MCPTenrearyStep:
    """Single executable tenreary step."""

    id: str
    type: str
    params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    if_env: List[str] = field(default_factory=list)

    @staticmethod
    def from_dict(payload: Dict[str, Any], idx: int) -> "MCPTenrearyStep":
        return MCPTenrearyStep(
            id=str(payload.get("id", f"step-{idx}")),
            type=str(payload.get("type", "")).strip(),
            params=dict(payload.get("params", {}) or {}),
            enabled=bool(payload.get("enabled", True)),
            if_env=[str(x).strip() for x in payload.get("if_env", []) if str(x).strip()],
        )


@dataclass
class MCPTenreary:
    """Custom MCP tenreary document."""

    tenreary_type: str
    name: str
    dual_browser: Dict[str, Any]
    metadata: Dict[str, Any]
    steps: List[MCPTenrearyStep]

    @staticmethod
    def from_dict(payload: Dict[str, Any]) -> "MCPTenreary":
        raw_steps = payload.get("steps", [])
        steps: List[MCPTenrearyStep] = []
        if isinstance(raw_steps, list):
            for idx, row in enumerate(raw_steps):
                if isinstance(row, dict):
                    steps.append(MCPTenrearyStep.from_dict(row, idx=idx))

        return MCPTenreary(
            tenreary_type=str(payload.get("tenreary_type", "mcp.tenreary.v1")),
            name=str(payload.get("name", "unnamed-tenreary")),
            dual_browser=dict(payload.get("dual_browser", {}) or {}),
            metadata=dict(payload.get("metadata", {}) or {}),
            steps=steps,
        )


def load_tenreary(path: Path) -> MCPTenreary:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Tenreary JSON must be an object.")
    return MCPTenreary.from_dict(payload)


class MCPTenrearyRunner:
    """Execute custom MCP tenreary workflows."""

    def __init__(self, *, scbe_url: str = "http://127.0.0.1:8080", allow_network: bool = True):
        self.scbe_url = scbe_url
        self.allow_network = allow_network
        self.context: Dict[str, Any] = {}
        self._connector = ConnectorBridge() if ConnectorBridge else None
        self._browser_limbs: Dict[str, MultiTabBrowserLimb] = {}
        self._tab_aliases: Dict[Tuple[str, str], str] = {}

    async def _init_browsers(self, dual_browser: Dict[str, Any]) -> None:
        enabled = bool(dual_browser.get("enabled", True))
        if not enabled:
            return

        max_tabs = int(dual_browser.get("max_tabs", 4))
        primary_engine = str(dual_browser.get("primary_engine", "playwright")).strip() or "playwright"
        secondary_engine = str(dual_browser.get("secondary_engine", "cdp")).strip() or "cdp"

        primary = MultiTabBrowserLimb(backend_type=primary_engine, max_tabs=max_tabs, scbe_url=self.scbe_url)
        await primary.activate()
        self._browser_limbs["primary"] = primary

        if str(secondary_engine).lower() != str(primary_engine).lower() or bool(
            dual_browser.get("force_secondary", True)
        ):
            secondary = MultiTabBrowserLimb(backend_type=secondary_engine, max_tabs=max_tabs, scbe_url=self.scbe_url)
            await secondary.activate()
            self._browser_limbs["secondary"] = secondary

    async def _close_browsers(self) -> None:
        for limb in self._browser_limbs.values():
            try:
                for tab_id in list(limb.tabs.keys()):
                    await limb.execute("close_tab", "", {"tab_id": tab_id})
            except Exception:
                pass
            try:
                await limb.deactivate()
            except Exception:
                pass
        self._browser_limbs.clear()
        self._tab_aliases.clear()

    async def run(self, tenreary: MCPTenreary, context_seed: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if context_seed:
            self.context.update(context_seed)
        self.context.setdefault("tenreary_name", tenreary.name)
        self.context.setdefault("tenreary_type", tenreary.tenreary_type)
        if not isinstance(self.context.get("step"), dict):
            self.context["step"] = {}

        await self._init_browsers(tenreary.dual_browser)

        step_results: List[Dict[str, Any]] = []
        try:
            for step in tenreary.steps:
                result = await self._run_step(step)
                step_results.append(result)
                self.context[f"step.{step.id}"] = result
                step_store = self.context.get("step")
                if isinstance(step_store, dict):
                    step_store[step.id] = result
        finally:
            await self._close_browsers()

        ok_count = sum(1 for row in step_results if row.get("status") in {"ok", "skipped"})
        return {
            "ok": ok_count == len(step_results),
            "tenreary_name": tenreary.name,
            "tenreary_type": tenreary.tenreary_type,
            "generated_at": _iso_now(),
            "steps_total": len(step_results),
            "steps_ok": ok_count,
            "steps_failed": len(step_results) - ok_count,
            "results": step_results,
            "context_keys": sorted(self.context.keys()),
        }

    async def _run_step(self, step: MCPTenrearyStep) -> Dict[str, Any]:
        started = time.perf_counter()
        base = {
            "id": step.id,
            "type": step.type,
            "status": "ok",
            "started_at": _iso_now(),
        }

        if not step.enabled:
            base["status"] = "skipped"
            base["reason"] = "disabled"
            base["elapsed_ms"] = 0.0
            return base

        for env_key in step.if_env:
            if not _get_env_or_secret(env_key):
                base["status"] = "skipped"
                base["reason"] = f"missing_env:{env_key}"
                base["elapsed_ms"] = 0.0
                return base

        params = _ctx_inject(step.params, self.context)
        try:
            data = await self._dispatch_step(step.type, params)
            base["data"] = _to_json_safe(data)
        except Exception as exc:
            base["status"] = "error"
            base["error"] = f"{type(exc).__name__}: {exc}"
        finally:
            base["elapsed_ms"] = round((time.perf_counter() - started) * 1000.0, 2)
        return base

    async def _dispatch_step(self, step_type: str, params: Dict[str, Any]) -> Any:
        step_type = (step_type or "").strip().lower()

        if step_type == "context.set":
            key = str(params.get("key", "")).strip()
            if not key:
                raise ValueError("context.set requires 'key'.")
            self.context[key] = params.get("value")
            return {"key": key, "value": self.context[key]}

        if step_type in {"browser.navigate", "browser.action", "browser.get_content"}:
            return await self._step_browser(step_type=step_type, params=params)

        if step_type == "github.rest":
            return self._step_github_rest(params)

        if step_type == "github.graphql":
            return self._step_github_graphql(params)

        if step_type == "connector.execute":
            return await self._step_connector_execute(params)

        if step_type == "automation.emit":
            return await self._step_automation_emit(params)

        if step_type == "analysis.content":
            return await self._step_analysis_content(params)

        if step_type == "desktop.notify":
            return self._step_desktop_notify(params)

        if step_type == "notion.append":
            return self._step_notion_append(params)

        raise ValueError(f"Unknown tenreary step type: {step_type}")

    async def _ensure_browser_tab(self, role: str, tab_alias: str) -> Tuple[MultiTabBrowserLimb, str]:
        role = role.lower().strip() or "primary"
        if role not in self._browser_limbs:
            raise RuntimeError(f"Browser role not available: {role}")
        limb = self._browser_limbs[role]
        key = (role, tab_alias)
        if key not in self._tab_aliases:
            created = await limb.execute("create_tab", tab_alias, {})
            tab_id = str(created.get("tab_id") or tab_alias)
            self._tab_aliases[key] = tab_id
        return limb, self._tab_aliases[key]

    async def _step_browser(self, *, step_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        role = str(params.get("role", "primary")).strip().lower()
        tab = str(params.get("tab", "main")).strip() or "main"
        fallback_to_primary = bool(params.get("fallback_to_primary", True))
        try:
            limb, tab_id = await self._ensure_browser_tab(role, tab)
        except Exception:
            if role == "secondary" and fallback_to_primary:
                role = "primary"
                limb, tab_id = await self._ensure_browser_tab(role, tab)
            else:
                raise

        if step_type == "browser.navigate":
            url = str(params.get("url", "")).strip()
            if not url:
                raise ValueError("browser.navigate requires 'url'.")
            try:
                result = await limb.execute("navigate", url, {"tab_id": tab_id})
            except Exception:
                if role == "secondary" and fallback_to_primary:
                    role = "primary"
                    limb, tab_id = await self._ensure_browser_tab(role, tab)
                    result = await limb.execute("navigate", url, {"tab_id": tab_id})
                else:
                    raise
            self.context[f"tab.{role}.{tab}.url"] = url
            return result

        if step_type == "browser.get_content":
            result = await limb.execute("get_content", "", {"tab_id": tab_id})
            if isinstance(result, dict) and isinstance(result.get("data"), dict):
                preview = str(result["data"].get("preview", ""))
                self.context[f"tab.{role}.{tab}.content_preview"] = preview
            return result

        action = str(params.get("action", "")).strip().lower()
        target = str(params.get("target", "")).strip()
        if not action:
            raise ValueError("browser.action requires 'action'.")
        exec_params = {k: v for k, v in params.items() if k not in {"action", "target", "role", "tab"}}
        exec_params["tab_id"] = tab_id
        result = await limb.execute(action, target, exec_params)
        return result

    def _step_github_rest(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.allow_network:
            return {"status": "skipped", "reason": "network_disabled"}

        token = _get_env_or_secret("GITHUB_TOKEN") or _get_env_or_secret("GH_TOKEN")
        method = str(params.get("method", "GET")).upper()
        path = str(params.get("path", "")).strip()
        query = params.get("query", {})
        body = params.get("body", {})

        if not path:
            raise ValueError("github.rest requires 'path' (e.g. /repos/owner/repo).")

        base = "https://api.github.com"
        if path.startswith("http://") or path.startswith("https://"):
            url = path
        else:
            url = f"{base}{path if path.startswith('/') else '/' + path}"

        if isinstance(query, dict) and query:
            encoded = urllib.parse.urlencode({k: str(v) for k, v in query.items()})
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{encoded}"

        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "SCBE-MCPTenreary/1.0",
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"

        payload = None
        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            payload = json.dumps(body or {}).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url=url, method=method, headers=headers, data=payload)
        try:
            with urllib.request.urlopen(request, timeout=30) as resp:
                text = resp.read().decode("utf-8", errors="replace")
                data = json.loads(text) if text else {}
                return {"status_code": getattr(resp, "status", 200), "url": url, "data": data}
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            return {"status_code": exc.code, "url": url, "error": body_text[:2000]}

    def _step_github_graphql(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self.allow_network:
            return {"status": "skipped", "reason": "network_disabled"}

        token = _get_env_or_secret("GITHUB_TOKEN") or _get_env_or_secret("GH_TOKEN")
        if not token:
            raise ValueError("github.graphql requires GITHUB_TOKEN or GH_TOKEN.")

        query = str(params.get("query", "")).strip()
        variables = params.get("variables", {})
        if not query:
            raise ValueError("github.graphql requires 'query'.")

        body = {"query": query, "variables": variables if isinstance(variables, dict) else {}}
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url="https://api.github.com/graphql",
            method="POST",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/vnd.github+json",
                "User-Agent": "SCBE-MCPTenreary/1.0",
            },
            data=data,
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                text = resp.read().decode("utf-8", errors="replace")
                return {"status_code": getattr(resp, "status", 200), "data": json.loads(text) if text else {}}
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            return {"status_code": exc.code, "error": body_text[:2000]}

    async def _step_connector_execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if not self._connector:
            return {"status": "error", "error": "ConnectorBridge unavailable"}
        platform = str(params.get("platform", "")).strip().lower()
        action = str(params.get("action", "")).strip()
        payload = params.get("payload", {})
        if not platform or not action:
            raise ValueError("connector.execute requires 'platform' and 'action'.")
        result = await self._connector.execute(platform, action, payload if isinstance(payload, dict) else {})
        return {
            "success": bool(result.success),
            "platform": result.platform,
            "elapsed_ms": result.elapsed_ms,
            "credits_earned": result.credits_earned,
            "error": result.error,
            "data": result.data,
        }

    async def _step_automation_emit(self, params: Dict[str, Any]) -> Dict[str, Any]:
        payload = params.get("payload", {})
        channels = params.get("channels", ["n8n", "zapier"])
        action = str(params.get("action", "trigger")).strip() or "trigger"
        if not isinstance(payload, dict):
            raise ValueError("automation.emit payload must be an object.")
        if not isinstance(channels, list):
            raise ValueError("automation.emit channels must be a list.")

        out: Dict[str, Any] = {}
        for channel in channels:
            platform = str(channel).strip().lower()
            if not platform:
                continue
            out[platform] = await self._step_connector_execute(
                {"platform": platform, "action": action, "payload": payload}
            )
        return out

    async def _step_analysis_content(self, params: Dict[str, Any]) -> Dict[str, Any]:
        backend = str(params.get("backend", "rule")).strip().lower()
        text = str(params.get("text", "")).strip()
        if not text and params.get("source_key"):
            text = str(_ctx_lookup(self.context, str(params.get("source_key"))))

        if not text:
            raise ValueError("analysis.content requires text or source_key.")

        prompt = str(params.get("prompt", "Summarize key monetization opportunities in 5 bullets.")).strip()

        if backend == "openai":
            return self._analyze_openai(text=text, prompt=prompt, model=str(params.get("model", "gpt-4o-mini")))
        if backend == "transformers":
            return self._analyze_transformers(text=text)
        if backend == "langchain":
            return await self._analyze_langchain(
                text=text, prompt=prompt, model=str(params.get("model", "gpt-4o-mini"))
            )
        return self._analyze_rule(text=text)

    def _analyze_openai(self, *, text: str, prompt: str, model: str) -> Dict[str, Any]:
        if not self.allow_network:
            return {"status": "skipped", "reason": "network_disabled"}

        api_key = _get_env_or_secret("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for backend=openai.")

        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a concise monetization analyst."},
                {"role": "user", "content": f"{prompt}\n\n{text[:12000]}"},
            ],
            "temperature": 0.2,
        }
        req = urllib.request.Request(
            url="https://api.openai.com/v1/chat/completions",
            method="POST",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            data=json.dumps(body).encode("utf-8"),
        )
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                payload = json.loads(raw)
                content = payload.get("choices", [{}])[0].get("message", {}).get("content", "")
                return {"backend": "openai", "model": model, "analysis": content, "raw": payload}
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            return {"backend": "openai", "error": body_text[:3000], "status_code": exc.code}

    def _analyze_transformers(self, *, text: str) -> Dict[str, Any]:
        try:
            from transformers import pipeline  # type: ignore
        except Exception as exc:
            return {"backend": "transformers", "status": "unavailable", "error": str(exc)}

        try:
            summarizer = pipeline("summarization")
            summary = summarizer(text[:4000], max_length=160, min_length=40, do_sample=False)
            return {"backend": "transformers", "analysis": summary}
        except Exception as exc:
            return {"backend": "transformers", "error": str(exc)}

    async def _analyze_langchain(self, *, text: str, prompt: str, model: str) -> Dict[str, Any]:
        try:
            from langchain_openai import ChatOpenAI  # type: ignore
            from langchain_core.messages import HumanMessage, SystemMessage  # type: ignore
        except Exception as exc:
            return {"backend": "langchain", "status": "unavailable", "error": str(exc)}

        api_key = _get_env_or_secret("OPENAI_API_KEY")
        if not api_key:
            return {"backend": "langchain", "status": "missing_env", "error": "OPENAI_API_KEY not set"}

        try:
            llm = ChatOpenAI(model=model, temperature=0.2, api_key=api_key)
            response = await llm.ainvoke(
                [
                    SystemMessage(content="You are a concise monetization analyst."),
                    HumanMessage(content=f"{prompt}\n\n{text[:12000]}"),
                ]
            )
            return {"backend": "langchain", "model": model, "analysis": str(response.content)}
        except Exception as exc:
            return {"backend": "langchain", "error": str(exc)}

    def _analyze_rule(self, *, text: str) -> Dict[str, Any]:
        lowered = text.lower()
        keywords = [
            "shopify",
            "stripe",
            "lead",
            "outreach",
            "checkout",
            "conversion",
            "pricing",
            "offer",
            "n8n",
            "zapier",
        ]
        hits = {k: lowered.count(k) for k in keywords}
        ranked = sorted(hits.items(), key=lambda kv: kv[1], reverse=True)
        top = [k for k, v in ranked if v > 0][:5]
        return {
            "backend": "rule",
            "analysis": {
                "top_keywords": top,
                "keyword_counts": hits,
                "recommendation": "Prioritize channels with highest keyword overlap and immediate checkout paths.",
            },
        }

    def _step_desktop_notify(self, params: Dict[str, Any]) -> Dict[str, Any]:
        title = str(params.get("title", "HYDRA Tenreary")).strip() or "HYDRA Tenreary"
        message = str(params.get("message", "Step complete")).strip() or "Step complete"

        try:
            from PyQt5.QtWidgets import QApplication, QMessageBox  # type: ignore

            app = QApplication.instance() or QApplication([])
            box = QMessageBox()
            box.setWindowTitle(title)
            box.setText(message)
            box.exec_()
            return {"backend": "PyQt5", "shown": True}
        except Exception:
            pass

        try:
            from PySide2.QtWidgets import QApplication, QMessageBox  # type: ignore

            app = QApplication.instance() or QApplication([])
            box = QMessageBox()
            box.setWindowTitle(title)
            box.setText(message)
            box.exec_()
            return {"backend": "PySide2", "shown": True}
        except Exception as exc:
            return {"backend": "none", "shown": False, "error": str(exc), "title": title, "message": message}

    def _notion_request(self, *, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.allow_network:
            return {"status": "skipped", "reason": "network_disabled"}

        token = (
            _get_env_or_secret("NOTION_TOKEN")
            or _get_env_or_secret("NOTION_API_KEY")
            or _get_env_or_secret("NOTION_MCP_TOKEN")
        )
        if not token:
            return {"status": "skipped", "reason": "missing_notion_token"}

        notion_version = os.environ.get("NOTION_VERSION", "2022-06-28").strip() or "2022-06-28"
        url = f"https://api.notion.com{path if path.startswith('/') else '/' + path}"
        data = None
        headers = {
            "Authorization": f"Bearer {token}",
            "Notion-Version": notion_version,
            "Accept": "application/json",
            "User-Agent": "SCBE-MCPTenreary/1.0",
        }
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(url=url, method=method.upper().strip(), headers=headers, data=data)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                body = json.loads(raw) if raw else {}
                return {"status": "ok", "status_code": getattr(resp, "status", 200), "data": body}
        except urllib.error.HTTPError as exc:
            body_text = exc.read().decode("utf-8", errors="replace")
            return {"status": "error", "status_code": exc.code, "error": body_text[:3000]}
        except Exception as exc:
            return {"status": "error", "error": f"{type(exc).__name__}: {exc}"}

    def _step_notion_append(self, params: Dict[str, Any]) -> Dict[str, Any]:
        block_id = _normalize_notion_id(str(params.get("block_id", "")))
        page_id = _normalize_notion_id(str(params.get("page_id", "")))
        target_id = block_id or page_id
        if not target_id:
            return {"status": "skipped", "reason": "missing_page_or_block_id"}

        text = str(params.get("text", "")).strip()
        source_key = str(params.get("source_key", "")).strip()
        if not text and source_key:
            raw = _ctx_lookup(self.context, source_key)
            if raw is None:
                text = ""
            elif isinstance(raw, (dict, list)):
                text = json.dumps(raw, ensure_ascii=False)
            else:
                text = str(raw)
        if not text:
            return {"status": "skipped", "reason": "empty_text"}

        max_chars = int(params.get("max_chars", 1800) or 1800)
        max_chars = max(100, min(max_chars, 1800))
        prepend_timestamp = bool(params.get("prepend_timestamp", True))
        heading = str(params.get("heading", "")).strip()

        lines: List[str] = []
        if prepend_timestamp:
            lines.append(f"[{_iso_now()}]")
        lines.append(text)
        content = "\n".join(lines).strip()

        chunks = [content[i : i + max_chars] for i in range(0, len(content), max_chars)] or [content]
        children: List[Dict[str, Any]] = []
        if heading:
            children.append(
                {
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {"rich_text": [{"type": "text", "text": {"content": heading[:200]}}]},
                }
            )
        for idx, chunk in enumerate(chunks):
            children.append(
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"type": "text", "text": {"content": chunk}}]},
                }
            )

        result = self._notion_request(
            method="PATCH",
            path=f"/v1/blocks/{target_id}/children",
            payload={"children": children},
        )
        result["target_id"] = target_id
        result["appended_blocks"] = len(children)
        return result
