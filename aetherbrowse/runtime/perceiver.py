"""
AetherBrowse — Perceiver Module
=================================
Transforms raw browser state (accessibility tree, screenshots, DOM)
into structured JSON that the Planner can reason over.

Uses PollyVision's 3-tier observation model:
  Tier 1: Accessibility tree (fast, text-only)
  Tier 2: Screenshot + Set-of-Marks overlay
  Tier 3: Full DOM snapshot with computed styles

The Perceiver is Polly's domain — tongue UM (observer).
"""

import asyncio
import hashlib
import logging
import json
import re
import time
from collections import Counter
from pathlib import Path
from typing import Optional

logger = logging.getLogger("aetherbrowse-perceiver")


def _normalize_text(value: Optional[str]) -> str:
    return (value or "").strip()


def _as_str(value) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _sha256_snippet(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:16]


class PagePerception:
    """Structured representation of what the agent 'sees' on a page."""

    def __init__(self):
        self.url: str = ""
        self.title: str = ""
        self.timestamp: float = 0.0
        self.interactive_elements: list[dict] = []
        self.text_content: str = ""
        self.forms: list[dict] = []
        self.navigation: dict = {}
        self.page_type: str = "unknown"

    def to_planner_prompt(self) -> str:
        """Format perception as a prompt for the Planner LLM."""
        lines = [
            f"## Current Page: {self.title}",
            f"URL: {self.url}",
            f"Page type: {self.page_type}",
            "",
            "### Interactive Elements",
        ]

        for i, el in enumerate(self.interactive_elements):
            role = el.get("role", "unknown")
            name = el.get("name", "")
            tag = el.get("tag", "")
            idx = el.get("index", i)
            lines.append(f"  [{idx}] {role}: \"{name}\" ({tag})")

        if self.forms:
            lines.append("")
            lines.append("### Forms")
            for form in self.forms:
                lines.append(f"  Form: {form.get('action', 'no-action')}")
                for field in form.get("fields", []):
                    lines.append(f"    - {field['type']}: \"{field.get('label', '')}\" [{field.get('selector', '')}]")

        if self.navigation:
            lines.append("")
            lines.append("### Navigation")
            for k, v in self.navigation.items():
                lines.append(f"  {k}: {v}")

        lines.append("")
        lines.append(f"### Page Text (first 2000 chars)")
        lines.append(self.text_content[:2000])

        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "url": self.url,
            "title": self.title,
            "timestamp": self.timestamp,
            "page_type": self.page_type,
            "interactive_count": len(self.interactive_elements),
            "form_count": len(self.forms),
            "elements": self.interactive_elements,
            "forms": self.forms,
            "navigation": self.navigation,
            "text_length": len(self.text_content),
        }


class Perceiver:
    """Transforms raw browser output into structured PagePerception."""

    # Roles that indicate interactive elements
    INTERACTIVE_ROLES = {
        "button", "link", "textbox", "checkbox", "radio",
        "combobox", "slider", "switch", "tab", "menuitem",
        "searchbox", "spinbutton", "option", "file",
    }

    # Patterns for classifying page types
    PAGE_PATTERNS = {
        "login": r"(sign.?in|log.?in|password|authenticate)",
        "product_listing": r"(products?|catalog|shop|store|collection)",
        "product_detail": r"(add.to.cart|buy.now|price|product.detail)",
        "upload": r"(upload|drag.and.drop|choose.file|browse.files)",
        "form": r"(submit|form|register|sign.?up|apply)",
        "dashboard": r"(dashboard|overview|analytics|admin|panel)",
        "search": r"(search.results|results.for|found.\d+)",
        "article": r"(article|blog|post|read.more|published)",
        "checkout": r"(checkout|payment|billing|order.summary)",
        "settings": r"(settings|preferences|account|profile)",
    }

    def __init__(self):
        self._element_index = 0

    def perceive_from_accessibility_tree(self, tree: dict, url: str = "", title: str = "") -> PagePerception:
        """
        Tier 1 perception: Parse Playwright's accessibility snapshot.
        This is the fastest and most common perception mode.
        """
        perception = PagePerception()
        perception.url = url
        perception.title = title
        perception.timestamp = time.time()
        self._element_index = 0

        if tree:
            self._walk_tree(tree, perception)

        # Classify page type from title + elements
        perception.page_type = self._classify_page(perception)

        # Extract forms from grouped elements
        perception.forms = self._extract_forms(perception.interactive_elements)

        # Build navigation info
        perception.navigation = self._extract_navigation(perception.interactive_elements, url)

        return perception

    def perceive_from_text(self, text: str, url: str = "", title: str = "") -> PagePerception:
        """
        Fallback perception: Build perception from raw page text.
        Used when accessibility tree is unavailable.
        """
        perception = PagePerception()
        perception.url = url
        perception.title = title
        perception.timestamp = time.time()
        perception.text_content = text
        perception.page_type = self._classify_page(perception)
        return perception

    # ------------------------------------------------------------------
    #  Tree walking
    # ------------------------------------------------------------------

    def _walk_tree(self, node: dict, perception: PagePerception, depth: int = 0):
        """Recursively walk the accessibility tree, extracting interactive elements."""
        if not isinstance(node, dict):
            return

        role = node.get("role", "")
        name = node.get("name", "")

        # Collect text content
        if name and role not in ("generic", "none"):
            perception.text_content += name + " "

        # Identify interactive elements
        if role in self.INTERACTIVE_ROLES:
            self._element_index += 1
            element = {
                "index": self._element_index,
                "role": role,
                "name": name.strip()[:200],
                "tag": node.get("tag", ""),
                "value": node.get("value", ""),
                "checked": node.get("checked"),
                "disabled": node.get("disabled", False),
                "required": node.get("required", False),
                "depth": depth,
            }

            # Try to build a useful selector
            element["selector"] = self._build_selector(node, element)

            perception.interactive_elements.append(element)

        # Recurse into children
        for child in node.get("children", []):
            self._walk_tree(child, perception, depth + 1)

    def _build_selector(self, node: dict, element: dict) -> str:
        """Build a CSS selector for an element from its accessibility info."""
        role = element["role"]
        name = element["name"]

        # Prefer aria-label selectors (most stable)
        if name:
            safe_name = name.replace('"', '\\"')[:80]
            if role == "link":
                return f'a:has-text("{safe_name}")'
            elif role == "button":
                return f'button:has-text("{safe_name}")'
            elif role == "textbox":
                return f'input[aria-label="{safe_name}"], input[placeholder="{safe_name}"]'
            elif role == "combobox":
                return f'select[aria-label="{safe_name}"]'
            else:
                return f'[aria-label="{safe_name}"]'

        return f'[role="{role}"]'

    # ------------------------------------------------------------------
    #  Page classification
    # ------------------------------------------------------------------

    def _classify_page(self, perception: PagePerception) -> str:
        """Classify the page type from its content."""
        search_text = (
            (perception.title or "") + " " +
            (perception.url or "") + " " +
            perception.text_content[:3000]
        ).lower()

        scores = {}
        for page_type, pattern in self.PAGE_PATTERNS.items():
            matches = len(re.findall(pattern, search_text, re.IGNORECASE))
            if matches > 0:
                scores[page_type] = matches

        if scores:
            return max(scores, key=scores.get)
        return "unknown"

    # ------------------------------------------------------------------
    #  Form extraction
    # ------------------------------------------------------------------

    def _extract_forms(self, elements: list[dict]) -> list[dict]:
        """Group text inputs and buttons into logical forms."""
        forms = []
        current_fields = []

        for el in elements:
            if el["role"] in ("textbox", "searchbox", "combobox", "checkbox", "radio", "slider", "spinbutton", "file"):
                current_fields.append({
                    "type": el["role"],
                    "label": el["name"],
                    "selector": el["selector"],
                    "value": el.get("value", ""),
                    "required": el.get("required", False),
                })
            elif el["role"] == "button" and current_fields:
                # Button after inputs = form submit
                forms.append({
                    "fields": current_fields,
                    "submit_selector": el["selector"],
                    "submit_label": el["name"],
                })
                current_fields = []

        # Leftover fields without a submit button
        if current_fields:
            forms.append({
                "fields": current_fields,
                "submit_selector": None,
                "submit_label": None,
            })

        return forms

    # ------------------------------------------------------------------
    #  Navigation extraction
    # ------------------------------------------------------------------

    def _extract_navigation(self, elements: list[dict], url: str) -> dict:
        """Extract navigation-relevant links."""
        nav = {"links_count": 0, "buttons_count": 0, "inputs_count": 0}
        key_links = []

        for el in elements:
            if el["role"] == "link":
                nav["links_count"] += 1
                name_lower = el["name"].lower()
                # Flag important navigation links
                if any(kw in name_lower for kw in ("home", "dashboard", "settings", "account", "cart", "sign out", "log out")):
                    key_links.append({"name": el["name"], "selector": el["selector"]})
            elif el["role"] == "button":
                nav["buttons_count"] += 1
            elif el["role"] in ("textbox", "searchbox", "combobox"):
                nav["inputs_count"] += 1

        if key_links:
            nav["key_links"] = key_links[:10]

        return nav


# ---------------------------------------------------------------------------
#  HydraArmor / Multi-head perceiver
# ---------------------------------------------------------------------------


class HydraPerceiver:
    """Multi-head consensus perceiver for Hydra Armor API clients."""

    def __init__(self):
        self._perceiver = Perceiver()
        self.active_tongue = "UM"
        self.consensus_threshold = 0.8
        self._destructive_terms = (
            "delete",
            "remove",
            "drop",
            "destroy",
            "reset",
            "revoke",
            "disable",
            "cancel",
            "terminate",
            "purge",
        )

        self._armor = None
        try:
            import sys

            sys.path.append(str(Path(__file__).resolve().parents[2]))
            from fleet.octo_armor import OctoArmor

            self._armor = OctoArmor()
        except Exception:
            self._armor = None

        # Keep optional so non-LLM runtime environments can still use this path.
        self._vision = None
        self._vision_available = False
        try:
            from src.browser.polly_vision import PollyVision

            self._vision = PollyVision()
            self._vision_available = True
        except Exception:
            self._vision = None

    # ------------------------------ public API --------------------------------

    async def perceive_and_verify(self, browser_snapshot: dict, intent: str | None = None) -> dict:
        """Run vision, DOM, and governance heads and return consensus."""
        if not isinstance(browser_snapshot, dict):
            return {
                "consensus_score": 0.0,
                "elements": [],
                "governance_status": "BLOCKED",
                "active_tongue": self.active_tongue,
                "error": "Invalid snapshot payload; expected object.",
            }

        intent_text = _normalize_text(intent)
        if not intent_text:
            intent_text = _normalize_text(browser_snapshot.get("intent") or browser_snapshot.get("context"))

        vision_head, dom_head, governance_head = await asyncio.gather(
            self._vision_head(browser_snapshot),
            self._dom_head(browser_snapshot, intent_text),
            self._governance_head(browser_snapshot, intent_text),
        )

        heads = {"vision": vision_head, "dom": dom_head, "governance": governance_head}
        statuses = [head.get("status", "DENY").upper() for head in heads.values()]
        raw_scores = [float(head.get("confidence", 0.0)) for head in heads.values()]

        status_score = {"ALLOW": 1.0, "QUARANTINE": 0.5, "WARN": 0.5, "DENY": 0.0}
        score = sum(status_score.get(s, 0.0) for s in statuses) / len(statuses)
        consensus = max(Counter(statuses).values()) / len(statuses)

        governance_status = governance_head.get("status", "DENY").upper()
        if governance_status == "DENY":
            status = "BLOCKED"
        elif governance_status == "QUARANTINE" or consensus < self.consensus_threshold:
            status = "CAUTION"
        else:
            status = "SECURE"

        return {
            "consensus_score": round((score * 0.6 + consensus * 0.4), 3),
            "heads": heads,
            "elements": dom_head.get("elements", []),
            "primary_action": dom_head.get("primary_action"),
            "governance_status": status,
            "active_tongue": self.active_tongue,
            "decision": "ALLOW" if status == "SECURE" else ("QUARANTINE" if status == "CAUTION" else "DENY"),
            "snapshot_hash": vision_head.get("snapshot_hash") or dom_head.get("snapshot_hash"),
            "intent": intent_text,
            "meta": {
                "head_confidence": {
                    "vision": vision_head.get("confidence", 0.0),
                    "dom": dom_head.get("confidence", 0.0),
                    "governance": governance_head.get("confidence", 0.0),
                },
                "head_consensus": round(consensus, 3),
                "raw_scores": {
                    "vision": raw_scores[0],
                    "dom": raw_scores[1],
                    "governance": raw_scores[2],
                },
            },
        }

    # ------------------------------ vision head --------------------------------

    async def _vision_head(self, browser_snapshot: dict) -> dict:
        screenshot = browser_snapshot.get("screenshot") or browser_snapshot.get("screenshot_b64")
        if not screenshot:
            return {
                "head": "vision",
                "status": "QUARANTINE",
                "confidence": 0.45,
                "reason": "No screenshot payload found.",
                "elements": [],
            }

        if self._vision_available and self._vision:
            return {
                "head": "vision",
                "status": "ALLOW",
                "confidence": 0.85,
                "reason": "Screenshot payload available for visual grounding.",
                "elements": [],
                "snapshot_hash": _sha256_snippet(_as_str(screenshot)[:4000]),
            }

        length = len(_as_str(screenshot))
        return {
            "head": "vision",
            "status": "ALLOW" if length > 0 else "DENY",
            "confidence": 0.7 if length > 128 else 0.55,
            "reason": "Screenshot payload present; basic visual signal only.",
            "snapshot_hash": _sha256_snippet(_as_str(screenshot)[:4000]),
        }

    # ------------------------------ DOM head -----------------------------------

    async def _dom_head(self, browser_snapshot: dict, intent: str) -> dict:
        tree = browser_snapshot.get("tree")
        text = _as_str(browser_snapshot.get("text") or browser_snapshot.get("text_content"))
        url = _normalize_text(browser_snapshot.get("url"))
        title = _normalize_text(browser_snapshot.get("title"))
        dom_snapshot = browser_snapshot.get("dom_snapshot")

        if isinstance(tree, dict) and tree:
            perception = self._perceiver.perceive_from_accessibility_tree(tree, url=url, title=title)
        elif text:
            perception = self._perceiver.perceive_from_text(text, url=url, title=title)
        elif dom_snapshot:
            perception = self._perceiver.perceive_from_text(_normalize_text(str(dom_snapshot)), url=url, title=title)
        else:
            perception = PagePerception()
            perception.url = url
            perception.title = title
            perception.timestamp = time.time()

        selected = self._pick_candidate_element(perception, intent)
        if selected:
            status = "ALLOW"
            confidence = 0.9 if intent else 0.7
            reason = f"Candidate action target found: {selected['selector']}"
        elif perception.interactive_elements:
            status = "QUARANTINE"
            confidence = 0.56
            selected = None
            reason = "Intent too noisy or no direct match in page elements."
        else:
            status = "DENY"
            confidence = 0.78
            reason = "No interactive elements detected from DOM snapshot."

        if not selected and text:
            selected = {
                "action": "evaluate",
                "selector": "text-eval",
                "description": (text[:120] + "…") if len(text) > 120 else text,
            }

        return {
            "head": "dom",
            "status": status,
            "confidence": confidence,
            "reason": reason,
            "page_type": perception.page_type,
            "text_hash": _sha256_snippet(_normalize_text(perception.text_content)[:4000]),
            "snapshot_hash": _sha256_snippet(_normalize_text(_as_str(browser_snapshot.get("tree"))[:4000])),
            "elements": perception.interactive_elements,
            "primary_action": selected,
        }

    # ----------------------------- policy head ---------------------------------

    async def _governance_head(self, browser_snapshot: dict, intent: str) -> dict:
        action = _normalize_text(browser_snapshot.get("action", "unknown")).lower()
        selector = _normalize_text(browser_snapshot.get("selector"))
        dom_snippet = _normalize_text(browser_snapshot.get("dom_snapshot"))
        if not dom_snippet and isinstance(browser_snapshot.get("tree"), str):
            dom_snippet = browser_snapshot.get("tree", "")
        if not dom_snippet and browser_snapshot.get("text"):
            dom_snippet = _as_str(browser_snapshot.get("text"))
        context = _normalize_text(browser_snapshot.get("context", intent))

        risk = 0.2
        for term in self._destructive_terms:
            if term in selector or term in action or term in context:
                risk += 0.24

        if risk >= 0.7:
            status = "DENY"
            confidence = 0.85
            reason = "High-risk destructive pattern in action/selector/context."
        elif risk >= 0.35:
            status = "QUARANTINE"
            confidence = 0.72
            reason = "Moderate risk detected."
        else:
            status = "ALLOW"
            confidence = 0.9
            reason = "No destructive signal in governance context."

        if self._armor:
            try:
                prompt = (
                    f"Action intent: {action}\n"
                    f"Selector: {selector}\n"
                    f"Context: {context}\n"
                    f"DOM context: {dom_snippet[:1000]}\n\n"
                    "Return exactly one of ALLOW, QUARANTINE, DENY and one-line rationale."
                )
                response = await self._armor.route_task("govern", prompt)
                text = _normalize_text(response.get("text") if isinstance(response, dict) else str(response))
                upper = text.upper()
                if "DENY" in upper:
                    status = "DENY"
                    reason = text[:240]
                    confidence = 0.95
                elif "QUARANTINE" in upper or "WARN" in upper:
                    status = "QUARANTINE"
                    reason = text[:240]
                    confidence = max(confidence, 0.78)
                elif "ALLOW" in upper:
                    status = "ALLOW"
                    reason = text[:240]
                    confidence = 0.94
            except Exception as exc:
                logger.warning("Hydra perception policy model failed: %s", exc)

        return {
            "head": "governance",
            "status": status,
            "confidence": confidence,
            "reason": reason,
            "action": action,
            "selector": selector,
            "risk_score": round(min(risk, 1.0), 3),
            "consensus": {"model_based": status},
        }

    # ----------------------------- helpers -------------------------------------

    def _pick_candidate_element(self, perception: PagePerception, intent: str):
        if not perception.interactive_elements:
            return None

        if not intent:
            return perception.interactive_elements[0]

        intent_lower = intent.lower()
        for el in perception.interactive_elements:
            el_name = _normalize_text(el.get("name", "")).lower()
            if el_name and any(token in el_name for token in intent_lower.split()):
                return el

        for el in perception.interactive_elements:
            if el.get("role") in ("button", "link"):
                return el

        return perception.interactive_elements[0]


# ---------------------------------------------------------------------------
#  Convenience function for the agent runtime
# ---------------------------------------------------------------------------

_perceiver = Perceiver()
_hydra_perceiver = HydraPerceiver()


def perceive(tree: Optional[dict], url: str = "", title: str = "", text: str = "") -> PagePerception:
    """One-shot perception from whatever data is available."""
    if tree:
        return _perceiver.perceive_from_accessibility_tree(tree, url, title)
    elif text:
        return _perceiver.perceive_from_text(text, url, title)
    else:
        p = PagePerception()
        p.url = url
        p.title = title
        p.timestamp = time.time()
        return p


async def perceive_with_consensus(
    browser_snapshot: Optional[dict],
    intent: str | None = None,
) -> dict:
    """Get Hydra consensus on a browser snapshot + intent."""
    return await _hydra_perceiver.perceive_and_verify(browser_snapshot, intent=intent)
