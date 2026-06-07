"""Read-only browser corridor atlas.

This is the browser analogue of the prime atlas:

    page state -> interaction neighborhood -> valid action corridors

It does not click. It maps a page snapshot into deterministic nodes and
candidate action edges so a governed browser agent can choose corridors instead
of issuing blind actions.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urljoin

from src.aetherbrowser.page_analyzer import PageAnalyzer

_TOKEN_RE = re.compile(r"[a-z0-9]+")

_RISK_HINTS_HIGH = {
    "approve",
    "buy",
    "checkout",
    "delete",
    "deploy",
    "merge",
    "order",
    "pay",
    "payment",
    "publish",
    "push",
    "remove",
    "send",
    "submit",
    "transfer",
    "wallet",
}
_RISK_HINTS_MEDIUM = {
    "auth",
    "credential",
    "email",
    "fill",
    "login",
    "password",
    "select",
    "sign in",
    "signin",
    "type",
    "upload",
    "username",
}

_ACTION_PRIMES = {
    "navigate": 2,
    "click": 3,
    "fill": 5,
    "select": 7,
    "wait": 11,
    "inspect": 13,
}
_ROLE_PRIMES = {
    "link": 17,
    "button": 19,
    "textbox": 23,
    "input": 29,
    "form": 31,
    "tab": 37,
    "generic": 41,
}
_RISK_PRIMES = {
    "low": 43,
    "medium": 47,
    "high": 53,
    "blocked": 59,
}


@dataclass(frozen=True)
class ElementAddress:
    """Visible element address inside a page state."""

    text: str
    role: str
    selector: str | None
    href: str | None = None
    bbox: tuple[float, float, float, float] | None = None
    source: str = "snapshot"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PageNode:
    """A browser state node."""

    node_id: str
    url: str
    title: str
    dom_signature: str
    visible_text_hash: str
    semantic_label: str
    risk_level: str
    intent: str
    topic_labels: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["topic_labels"] = list(self.topic_labels)
        return payload


@dataclass(frozen=True)
class ActionEdge:
    """A possible read-only corridor from one page state to another."""

    edge_id: str
    source_node: str
    target_hint: str | None
    action_type: str
    selector: str | None
    visible_label: str
    role: str
    confidence: float
    goal_relevance: float
    ambiguity_penalty: float
    risk_level: str
    risk_penalty: float
    corridor_score: float
    factor_address: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BrowserCorridorGraph:
    """Read-only page-state graph with ranked action corridors."""

    schema_version: str
    goal: str
    page_node: PageNode
    element_count: int
    edges: tuple[ActionEdge, ...]
    chosen_corridor: ActionEdge | None
    safety_contract: str
    ranker_contract: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "goal": self.goal,
            "page_node": self.page_node.to_dict(),
            "element_count": self.element_count,
            "edges": [edge.to_dict() for edge in self.edges],
            "chosen_corridor": (
                self.chosen_corridor.to_dict() if self.chosen_corridor else None
            ),
            "safety_contract": self.safety_contract,
            "ranker_contract": dict(self.ranker_contract),
        }


def build_corridor_graph(
    *,
    url: str,
    title: str,
    text: str = "",
    goal: str = "",
    headings: list[dict[str, Any]] | None = None,
    links: list[dict[str, Any]] | None = None,
    buttons: list[dict[str, Any]] | None = None,
    forms: list[dict[str, Any]] | None = None,
    tabs: list[dict[str, Any]] | None = None,
    max_edges: int = 20,
) -> BrowserCorridorGraph:
    """Build a read-only corridor graph from a page snapshot."""

    headings = headings or []
    links = links or []
    buttons = buttons or []
    forms = forms or []
    tabs = tabs or []
    if max_edges < 1:
        raise ValueError("max_edges must be positive")

    analysis = PageAnalyzer().analyze_sync(
        url=url,
        title=title,
        text=text,
        headings=headings,
        links=links,
        forms=forms,
        buttons=buttons,
        tabs=tabs,
    )
    node = _page_node(
        url=url,
        title=title,
        text=text,
        analysis=analysis,
        elements=[*links, *buttons, *forms, *tabs],
    )
    elements = _element_addresses(
        url=url, links=links, buttons=buttons, forms=forms, tabs=tabs
    )
    duplicate_counts = _duplicate_label_counts(elements)
    edges = tuple(
        sorted(
            (
                _edge_from_element(
                    node_id=node.node_id,
                    element=element,
                    goal=goal,
                    duplicate_count=duplicate_counts[_label_key(element)],
                )
                for element in elements
            ),
            key=lambda edge: (
                -edge.corridor_score,
                edge.risk_penalty,
                edge.visible_label.lower(),
            ),
        )[:max_edges]
    )
    chosen = next(
        (edge for edge in edges if edge.risk_level == "low"),
        edges[0] if edges else None,
    )
    return BrowserCorridorGraph(
        schema_version="aetherbrowser_corridor_atlas_v1",
        goal=goal,
        page_node=node,
        element_count=len(elements),
        edges=edges,
        chosen_corridor=chosen,
        safety_contract="read_only_map_no_clicks_no_form_submission",
        ranker_contract={
            "status": "HEURISTIC_SMOKE_TESTED",
            "goal_relevance_version": "token_overlap_v1",
            "score_inputs": [
                "selector_confidence",
                "goal_relevance",
                "risk_penalty",
                "ambiguity_penalty",
            ],
            "factor_address_score_participation": "not_used_for_ranking_audit_label_only",
            "baseline_scope": (
                "tiny labeled smoke beats risk-only-first-safe and random-expected baselines; "
                "live routing still needs broader eval"
            ),
        },
    )


def _page_node(
    *,
    url: str,
    title: str,
    text: str,
    analysis: dict[str, Any],
    elements: list[dict[str, Any]],
) -> PageNode:
    visible_text = " ".join(
        [title, text[:4000], " ".join(_element_text(item) for item in elements)]
    )
    dom_sig = _hash(
        "|".join(
            [
                url,
                title,
                *(
                    f"{item.get('text', '')}:{item.get('href', '')}"
                    for item in elements
                ),
            ]
        )
    )
    semantic = analysis.get("page_type") or analysis.get("intent") or "page"
    return PageNode(
        node_id=f"page:{_hash(url + '|' + title + '|' + visible_text)[:16]}",
        url=url,
        title=title,
        dom_signature=dom_sig,
        visible_text_hash=_hash(visible_text),
        semantic_label=str(semantic),
        risk_level=str(analysis.get("risk_tier", "low")),
        intent=str(analysis.get("intent", "inspect_page")),
        topic_labels=tuple(analysis.get("topics", [])),
    )


def _element_addresses(
    *,
    url: str,
    links: list[dict[str, Any]],
    buttons: list[dict[str, Any]],
    forms: list[dict[str, Any]],
    tabs: list[dict[str, Any]],
) -> list[ElementAddress]:
    out: list[ElementAddress] = []
    for i, link in enumerate(links):
        href = str(link.get("href") or "")
        out.append(
            ElementAddress(
                text=_element_text(link) or href,
                role=str(link.get("role") or "link").lower(),
                selector=_selector(link, fallback=f"a:nth-of-type({i + 1})"),
                href=urljoin(url, href) if href else None,
                bbox=_bbox(link),
                source="link",
            )
        )
    for i, button in enumerate(buttons):
        out.append(
            ElementAddress(
                text=_element_text(button) or "button",
                role=str(button.get("role") or "button").lower(),
                selector=_selector(button, fallback=f"button:nth-of-type({i + 1})"),
                bbox=_bbox(button),
                source="button",
            )
        )
    for i, form in enumerate(forms):
        label = _element_text(form) or str(form.get("name") or form.get("id") or "form")
        out.append(
            ElementAddress(
                text=label,
                role=str(form.get("role") or "form").lower(),
                selector=_selector(form, fallback=f"form:nth-of-type({i + 1})"),
                bbox=_bbox(form),
                source="form",
            )
        )
    for i, tab in enumerate(tabs):
        out.append(
            ElementAddress(
                text=_element_text(tab) or "tab",
                role=str(tab.get("role") or "tab").lower(),
                selector=_selector(tab, fallback=f"[role='tab']:nth-of-type({i + 1})"),
                bbox=_bbox(tab),
                source="tab",
            )
        )
    return out


def _edge_from_element(
    *, node_id: str, element: ElementAddress, goal: str, duplicate_count: int
) -> ActionEdge:
    action_type = _action_type(element)
    risk = _risk_level(element, action_type)
    selector_confidence = _selector_confidence(element)
    goal_relevance = _goal_relevance(goal, element)
    ambiguity_penalty = min(0.30, max(0, duplicate_count - 1) * 0.10)
    risk_penalty = {"low": 0.0, "medium": 0.18, "high": 0.42, "blocked": 1.0}[risk]
    raw_score = selector_confidence + goal_relevance - risk_penalty - ambiguity_penalty
    corridor_score = round(max(0.0, min(1.0, raw_score / 2.0)), 6)
    edge_id = f"edge:{_hash('|'.join([node_id, action_type, element.role, element.text, element.selector or '']))[:16]}"
    return ActionEdge(
        edge_id=edge_id,
        source_node=node_id,
        target_hint=element.href,
        action_type=action_type,
        selector=element.selector,
        visible_label=element.text,
        role=element.role,
        confidence=round(selector_confidence, 6),
        goal_relevance=round(goal_relevance, 6),
        ambiguity_penalty=round(ambiguity_penalty, 6),
        risk_level=risk,
        risk_penalty=round(risk_penalty, 6),
        corridor_score=corridor_score,
        factor_address=_factor_address(action_type, element.role, risk),
    )


def _factor_address(action_type: str, role: str, risk: str) -> dict[str, Any]:
    action_prime = _ACTION_PRIMES.get(action_type, _ACTION_PRIMES["inspect"])
    role_prime = _ROLE_PRIMES.get(role, _ROLE_PRIMES["generic"])
    risk_prime = _RISK_PRIMES.get(risk, _RISK_PRIMES["blocked"])
    product = action_prime * role_prime * risk_prime
    return {
        "encoding": "prime_factor_address_v1",
        "action_prime": action_prime,
        "role_prime": role_prime,
        "risk_prime": risk_prime,
        "product": product,
        "log_product": round(math.log(product), 12),
        "meaning": "categorical corridor factors encoded as unique prime products",
        "score_participation": "not_used_for_ranking_audit_label_only",
    }


def _action_type(element: ElementAddress) -> str:
    if element.role == "link" or element.href:
        return "navigate"
    if element.role in {"textbox", "input", "form"}:
        return "fill"
    if element.role == "tab":
        return "click"
    return "click"


def _risk_level(element: ElementAddress, action_type: str) -> str:
    label = f"{element.text} {element.role} {element.selector or ''}".lower()
    if any(hint in label for hint in _RISK_HINTS_HIGH):
        return "high"
    if action_type == "fill" or any(hint in label for hint in _RISK_HINTS_MEDIUM):
        return "medium"
    return "low"


def _selector_confidence(element: ElementAddress) -> float:
    score = 0.35
    if element.selector:
        score += 0.25
    if element.text and element.text != element.role:
        score += 0.20
    if element.role in _ROLE_PRIMES:
        score += 0.10
    if element.href:
        score += 0.10
    return min(score, 1.0)


def _goal_relevance(goal: str, element: ElementAddress) -> float:
    goal_tokens = set(_TOKEN_RE.findall(goal.lower()))
    if not goal_tokens:
        return 0.0
    haystack = " ".join([element.text, element.role, element.href or ""]).lower()
    element_tokens = set(_TOKEN_RE.findall(haystack))
    if not element_tokens:
        return 0.0
    overlap = len(goal_tokens & element_tokens) / max(len(goal_tokens), 1)
    phrase_bonus = (
        0.25 if goal.lower().strip() and goal.lower().strip() in haystack else 0.0
    )
    return min(1.0, overlap + phrase_bonus)


def _duplicate_label_counts(elements: list[ElementAddress]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for element in elements:
        key = _label_key(element)
        counts[key] = counts.get(key, 0) + 1
    return counts


def _label_key(element: ElementAddress) -> str:
    return f"{element.role}:{element.text.strip().lower()}"


def _element_text(item: dict[str, Any]) -> str:
    for key in ("text", "label", "name", "aria_label", "aria-label", "title"):
        value = item.get(key)
        if value:
            return str(value).strip()
    return ""


def _selector(item: dict[str, Any], *, fallback: str) -> str | None:
    for key in ("selector", "css", "locator"):
        value = item.get(key)
        if value:
            return str(value)
    return fallback


def _bbox(item: dict[str, Any]) -> tuple[float, float, float, float] | None:
    box = item.get("bbox") or item.get("bounding_box")
    if isinstance(box, dict):
        try:
            return (
                float(box.get("x", 0)),
                float(box.get("y", 0)),
                float(box.get("width", 0)),
                float(box.get("height", 0)),
            )
        except TypeError, ValueError:
            return None
    if isinstance(box, (list, tuple)) and len(box) == 4:
        try:
            return tuple(float(value) for value in box)  # type: ignore[return-value]
        except TypeError, ValueError:
            return None
    return None


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()
