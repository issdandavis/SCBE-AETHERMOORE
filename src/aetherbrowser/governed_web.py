"""Governed web primitives for the unified MCP orchestrator.

Phase C goal:
- expose cheap web primitives first
- route through governance before network execution
- reuse existing SCBE browser modules instead of inventing a parallel stack
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from agents.antivirus_membrane import scan_text_for_threats, turnstile_action
from scripts.agentic_web_tool import (
    _capture_with_fallback,
    _resolve_output_dir,
    _save_capture,
)
from src.aetherbrowser.hyperlane_py import Decision, HyperLanePy, HyperLaneResult, Zone
from src.browser.toolkit import extract as toolkit_extract
from src.browser.toolkit import needs_js as toolkit_needs_js
from src.browser.toolkit import search as toolkit_search


def _lane_dict(result: HyperLaneResult) -> dict[str, Any]:
    return {
        "decision": (
            result.decision.value
            if isinstance(result.decision, Decision)
            else str(result.decision)
        ),
        "zone": (
            result.zone.value if isinstance(result.zone, Zone) else str(result.zone)
        ),
        "reason": result.reason,
        "latency_ms": result.latency_ms,
    }


class GovernedWebTools:
    """Governed fetch/search/extract helpers over existing browser infrastructure."""

    def __init__(self) -> None:
        self.hyperlane = HyperLanePy()
        # Search surfaces should be queryable, but still stay out of GREEN.
        for domain in (
            "google.com",
            "www.google.com",
            "duckduckgo.com",
            "html.duckduckgo.com",
            "arxiv.org",
        ):
            self.hyperlane.add_domain(domain, Zone.YELLOW)

    async def search(
        self, query: str, *, num_results: int = 8, agent_id: str = "KO"
    ) -> dict[str, Any]:
        lane = self.hyperlane.evaluate(
            "https://html.duckduckgo.com/html/", action="search", agent_id=agent_id
        )
        if lane.decision != Decision.ALLOW:
            return {
                "ok": False,
                "query": query,
                "governance": _lane_dict(lane),
                "results": [],
            }

        results = await toolkit_search(query, num_results=num_results)
        shaped_results: list[dict[str, Any]] = []
        for item in results:
            result_zone = self.hyperlane.classify_zone(item.url).value
            scan = scan_text_for_threats(f"{item.title}\n{item.snippet}\n{item.url}")
            shaped_results.append(
                {
                    "title": item.title,
                    "url": item.url,
                    "snippet": item.snippet,
                    "source": item.source,
                    "zone": result_zone,
                    "threat_verdict": scan.verdict,
                    "threat_risk": scan.risk_score,
                }
            )

        zone_counts: dict[str, int] = {"GREEN": 0, "YELLOW": 0, "RED": 0}
        for item in shaped_results:
            zone_counts[item["zone"]] = zone_counts.get(item["zone"], 0) + 1

        return {
            "ok": True,
            "query": query,
            "result_count": len(shaped_results),
            "zone_counts": zone_counts,
            "governance": _lane_dict(lane),
            "results": shaped_results,
        }

    async def fetch(
        self,
        url: str,
        *,
        engine: str = "auto",
        agent_id: str = "AV",
        output_dir: str = "artifacts/web_tool",
    ) -> dict[str, Any]:
        lane = self.hyperlane.evaluate(url, action="read", agent_id=agent_id)
        if lane.decision != Decision.ALLOW:
            return {
                "ok": False,
                "url": url,
                "governance": _lane_dict(lane),
                "status": "quarantined",
            }

        artifact_dir = _resolve_output_dir(output_dir)
        capture = _capture_with_fallback(url, artifact_dir, engine)
        artifact_path = _save_capture(artifact_dir, capture)

        combined_text = "\n".join(
            [
                capture.title or "",
                capture.text_snippet or "",
                " ".join(link.get("href", "") for link in capture.links),
            ]
        )
        scan = scan_text_for_threats(combined_text)
        membrane_action = turnstile_action("browser", scan)
        content_released = membrane_action == "ALLOW"

        return {
            "ok": True,
            "url": url,
            "governance": _lane_dict(lane),
            "method": capture.method,
            "status_code": capture.status_code,
            "title": capture.title,
            "artifact_path": str(artifact_path),
            "screenshot_path": capture.screenshot_path,
            "warning": capture.warning,
            "threat_scan": scan.to_dict(),
            "membrane_action": membrane_action,
            "content_released": content_released,
            "text_snippet": capture.text_snippet if content_released else "",
            "links": capture.links if content_released else [],
        }

    async def extract(
        self,
        url: str,
        *,
        pattern: str,
        agent_id: str = "AV",
    ) -> dict[str, Any]:
        lane = self.hyperlane.evaluate(url, action="read", agent_id=agent_id)
        if lane.decision != Decision.ALLOW:
            return {
                "ok": False,
                "url": url,
                "pattern": pattern,
                "governance": _lane_dict(lane),
                "items": [],
            }

        items = await toolkit_extract(url, pattern)
        serialized_items = [asdict(item) for item in items]
        scan_source = "\n".join(
            f"{item['value']} {item['context']}" for item in serialized_items
        )
        scan = scan_text_for_threats(scan_source)
        membrane_action = turnstile_action("browser", scan)

        return {
            "ok": True,
            "url": url,
            "pattern": pattern,
            "governance": _lane_dict(lane),
            "item_count": len(serialized_items),
            "threat_scan": scan.to_dict(),
            "membrane_action": membrane_action,
            "items": serialized_items if membrane_action == "ALLOW" else [],
        }

    async def needs_js(self, url: str, *, agent_id: str = "AV") -> dict[str, Any]:
        lane = self.hyperlane.evaluate(url, action="read", agent_id=agent_id)
        if lane.decision != Decision.ALLOW:
            return {
                "ok": False,
                "url": url,
                "governance": _lane_dict(lane),
            }

        result = await toolkit_needs_js(url)
        return {
            "ok": True,
            "url": url,
            "governance": _lane_dict(lane),
            "needs_js": result.needs_js,
            "reason": result.reason,
            "content_length": result.content_length,
            "script_count": result.script_count,
            "noscript_present": result.noscript_present,
            "meta_redirect": result.meta_redirect,
            "body_text_length": result.body_text_length,
            "elapsed_ms": result.elapsed_ms,
        }
