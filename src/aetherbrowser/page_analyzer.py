"""
Page Analyzer — 'This Page' handler
=====================================

Analyzes the current tab's content when the user clicks 'This Page'.
Uses local heuristics first (zero API cost), then optionally enriches
with a model call via OctoArmor routing.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from urllib.parse import urlparse

MAX_WORDS = 50_000
POINCARE_RADIUS_CAP = 0.98
POINCARE_EPSILON = 1e-9

_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "AI/ML": [
        "machine learning",
        "artificial intelligence",
        "neural network",
        "deep learning",
        "model",
        "training",
    ],
    "Security": [
        "security",
        "vulnerability",
        "threat",
        "attack",
        "defense",
        "governance",
        "encryption",
    ],
    "Research": ["research", "paper", "study", "findings", "experiment", "analysis"],
    "Finance": ["financial", "payment", "revenue", "pricing", "investment", "market"],
    "Code": [
        "code",
        "programming",
        "developer",
        "api",
        "function",
        "class",
        "repository",
    ],
}

_AUTH_HINTS = {
    "auth",
    "credential",
    "email",
    "login",
    "password",
    "sign in",
    "signin",
    "username",
}
_PAYMENT_HINTS = {
    "billing",
    "buy",
    "card",
    "checkout",
    "invoice",
    "order",
    "pay",
    "payment",
    "wallet",
}
_DESTRUCTIVE_HINTS = {
    "delete",
    "deploy",
    "merge",
    "publish",
    "push",
    "remove",
    "submit",
    "transfer",
}


class PageAnalyzer:
    def analyze_sync(
        self,
        *,
        url: str,
        title: str,
        text: str,
        headings: list[dict] | None = None,
        links: list[dict] | None = None,
        forms: list[dict] | None = None,
        buttons: list[dict] | None = None,
        tabs: list[dict] | None = None,
        selection: str = "",
        page_type: str = "generic",
        screenshot: str = "",
    ) -> dict:
        truncated = False
        words = text.split()
        if len(words) > MAX_WORDS:
            words = words[:MAX_WORDS]
            text = " ".join(words)
            truncated = True

        word_count = len(words)
        summary = self._extractive_summary(text) if word_count > 0 else ""
        topics = self._detect_topics(text)
        headings = headings or []
        links = links or []
        forms = forms or []
        buttons = buttons or []
        tabs = tabs or []
        selected_text = selection.strip()
        if selected_text:
            summary = f"Selected: {selected_text}\n\n{summary}".strip()
        intent = self._infer_intent(
            url=url,
            title=title,
            text=text,
            page_type=page_type,
            forms=forms,
            buttons=buttons,
        )
        risk_tier, required_approvals = self._infer_risk(
            title=title,
            text=text,
            page_type=page_type,
            forms=forms,
            buttons=buttons,
        )
        page_summary = self._build_page_summary(
            title=title,
            page_type=page_type,
            headings=headings,
            links=links,
            forms=forms,
            buttons=buttons,
        )
        next_actions = self._suggest_next_actions(
            intent=intent,
            risk_tier=risk_tier,
            headings=headings,
            links=links,
            forms=forms,
            buttons=buttons,
            selected_text=selected_text,
        )
        topology_lens = self._build_topology_lens(
            url=url,
            title=title,
            text=text,
            headings=headings,
            links=links,
            forms=forms,
            buttons=buttons,
            intent=intent,
            risk_tier=risk_tier,
            word_count=word_count,
        )

        return {
            "url": url,
            "title": title,
            "word_count": word_count,
            "summary": summary,
            "page_summary": page_summary,
            "topics": topics,
            "truncated": truncated,
            "page_type": page_type,
            "intent": intent,
            "risk_tier": risk_tier,
            "required_approvals": required_approvals,
            "next_actions": next_actions,
            "heading_count": len(headings),
            "link_count": len(links),
            "button_count": len(buttons),
            "form_count": len(forms),
            "tab_count": len(tabs),
            "headings": headings[:8],
            "links": links[:8],
            "forms": forms[:4],
            "tabs": tabs[:8],
            "topology_lens": topology_lens,
            "selected_text": selected_text,
            "has_screenshot": bool(screenshot),
        }

    def _extractive_summary(self, text: str, max_sentences: int = 3) -> str:
        sentences = re.split(r"(?<=[.!?])\s+", text.strip())
        if not sentences:
            return ""
        word_freq = Counter(text.lower().split())
        scored = []
        for i, s in enumerate(sentences):
            score = sum(word_freq.get(w.lower(), 0) for w in s.split())
            scored.append((score, i, s))
        scored.sort(key=lambda x: x[0], reverse=True)
        top = sorted(scored[:max_sentences], key=lambda x: x[1])
        return " ".join(s for _, _, s in top)

    def _detect_topics(self, text: str) -> list[str]:
        text_lower = text.lower()
        found = []
        for topic, keywords in _TOPIC_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                found.append(topic)
        return found

    def _infer_intent(
        self,
        *,
        url: str,
        title: str,
        text: str,
        page_type: str,
        forms: list[dict],
        buttons: list[dict],
    ) -> str:
        combined = " ".join([url, title, text[:2000], page_type]).lower()
        tokens = set(re.findall(r"[a-z0-9]+", combined))
        if forms and (
            self._contains_hint(combined, _AUTH_HINTS)
            or self._buttons_match(buttons, _AUTH_HINTS)
        ):
            return "authenticate"
        if forms and (
            self._contains_hint(combined, _PAYMENT_HINTS)
            or self._buttons_match(buttons, _PAYMENT_HINTS)
        ):
            return "checkout"
        if "github.com" in url or "repository" in combined:
            return "repository_review"
        if {"query", "results", "search"} & tokens:
            return "search_results"
        if page_type == "form":
            return "form_review"
        if page_type == "article" or "article" in combined or "research" in combined:
            return "read_article"
        return "inspect_page"

    def _infer_risk(
        self,
        *,
        title: str,
        text: str,
        page_type: str,
        forms: list[dict],
        buttons: list[dict],
    ) -> tuple[str, list[str]]:
        combined = " ".join([title, text[:3000], page_type]).lower()
        approvals: list[str] = []
        if forms and (
            self._contains_hint(combined, _AUTH_HINTS)
            or self._buttons_match(buttons, _AUTH_HINTS)
        ):
            approvals.append("Page contains authentication or credential entry")
        if forms and (
            self._contains_hint(combined, _PAYMENT_HINTS)
            or self._buttons_match(buttons, _PAYMENT_HINTS)
        ):
            approvals.append("Page contains payment or checkout flow")
        if self._contains_hint(combined, _DESTRUCTIVE_HINTS) or self._buttons_match(
            buttons, _DESTRUCTIVE_HINTS
        ):
            approvals.append("Page exposes a high-impact state-changing action")
        unique_approvals = list(dict.fromkeys(approvals))
        if any(
            "payment" in item.lower() or "high-impact" in item.lower()
            for item in unique_approvals
        ):
            return "high", unique_approvals
        if unique_approvals or forms:
            return "medium", unique_approvals
        return "low", []

    def _build_page_summary(
        self,
        *,
        title: str,
        page_type: str,
        headings: list[dict],
        links: list[dict],
        forms: list[dict],
        buttons: list[dict],
    ) -> str:
        parts = [title or "Untitled page"]
        if page_type and page_type != "generic":
            parts.append(page_type)
        counts: list[str] = []
        if headings:
            counts.append(f"{len(headings)} headings")
        if links:
            counts.append(f"{len(links)} links")
        if forms:
            counts.append(f"{len(forms)} forms")
        if buttons:
            counts.append(f"{len(buttons)} buttons")
        if counts:
            parts.append(" | ".join(counts))
        return " | ".join(parts)

    def _suggest_next_actions(
        self,
        *,
        intent: str,
        risk_tier: str,
        headings: list[dict],
        links: list[dict],
        forms: list[dict],
        buttons: list[dict],
        selected_text: str,
    ) -> list[dict]:
        actions: list[dict] = [
            {
                "label": "Capture page snapshot",
                "reason": "Preserve evidence before navigating deeper or changing state.",
                "risk_tier": "low",
                "requires_approval": False,
            }
        ]
        if selected_text:
            actions.append(
                {
                    "label": "Ground analysis on the selected text",
                    "reason": "The active selection usually marks the user’s immediate target.",
                    "risk_tier": "low",
                    "requires_approval": False,
                }
            )
        elif headings:
            heading = (headings[0].get("text") or "").strip()[:80]
            if heading:
                actions.append(
                    {
                        "label": f"Inspect heading: {heading}",
                        "reason": "Lead with the main visible section before scanning the full page.",
                        "risk_tier": "low",
                        "requires_approval": False,
                    }
                )
        elif links:
            link = (links[0].get("text") or links[0].get("href") or "").strip()[:80]
            if link:
                actions.append(
                    {
                        "label": f"Inspect primary link: {link}",
                        "reason": "Top links usually reveal the page’s next navigation branch.",
                        "risk_tier": "low",
                        "requires_approval": False,
                    }
                )
        if forms or buttons:
            actions.append(
                {
                    "label": f"Review {intent.replace('_', ' ')} controls before input",
                    "reason": "Forms and action buttons should be validated before typing or clicking.",
                    "risk_tier": risk_tier,
                    "requires_approval": risk_tier != "low",
                }
            )
        return actions[:3]

    def _build_topology_lens(
        self,
        *,
        url: str,
        title: str,
        text: str,
        headings: list[dict],
        links: list[dict],
        forms: list[dict],
        buttons: list[dict],
        intent: str,
        risk_tier: str,
        word_count: int,
    ) -> dict:
        combined = " ".join(
            part
            for part in [
                title,
                text[:6000],
                " ".join((heading.get("text") or "") for heading in headings[:10]),
            ]
            if part
        ).lower()
        semantic_compass = self._semantic_compass(combined)
        best_axis = max(
            semantic_compass,
            key=lambda axis: axis["score"],
            default={"axis": "General", "score": 0.0},
        )
        # P2 fix: if no topic scored above zero, report "General" not the first keyword group
        primary_axis = best_axis if best_axis.get("score", 0) > 0 else {"axis": "General", "score": 0.0}
        link_pressure = self._link_pressure(url, links)
        interaction_pressure = self._interaction_pressure(combined, forms, buttons)
        content_depth = min(1.0, word_count / 2200) if word_count else 0.0
        heading_pressure = min(1.0, len(headings) / 10) if headings else 0.0
        curvature = min(
            1.0, 0.45 * content_depth + 0.25 * heading_pressure + 0.3 * link_pressure
        )
        risk_bias = {"low": 0.08, "medium": 0.2, "high": 0.36}.get(risk_tier, 0.15)
        radius = min(
            POINCARE_RADIUS_CAP,
            0.08
            + 0.35 * interaction_pressure
            + 0.2 * link_pressure
            + 0.15 * curvature
            + risk_bias,
        )
        trust_distance = self._hyperbolic_distance_from_origin(radius)
        boundary_signals = self._boundary_signals(
            url=url,
            text=combined,
            links=links,
            forms=forms,
            buttons=buttons,
            interaction_pressure=interaction_pressure,
            link_pressure=link_pressure,
        )
        zone = {"low": "GREEN", "medium": "YELLOW", "high": "RED"}.get(
            risk_tier, "YELLOW"
        )
        growth_signal = min(
            1.0,
            0.5 * content_depth + 0.3 * interaction_pressure + 0.2 * heading_pressure,
        )

        return {
            "zone": zone,
            "radius": round(radius, 3),
            "trust_distance": round(trust_distance, 3),
            "curvature": round(curvature, 3),
            "link_pressure": round(link_pressure, 3),
            "interaction_pressure": round(interaction_pressure, 3),
            "growth_signal": round(growth_signal, 3),
            "growth_label": intent.replace("_", " "),
            "primary_axis": primary_axis.get("axis", "General"),
            "semantic_compass": semantic_compass,
            "boundary_signals": boundary_signals,
            "summary": self._topology_summary(
                zone=zone,
                primary_axis=primary_axis.get("axis", "General"),
                trust_distance=trust_distance,
                boundary_signals=boundary_signals,
            ),
        }

    def _semantic_compass(self, text: str) -> list[dict]:
        raw_scores = {
            axis: sum(text.count(keyword) for keyword in keywords)
            for axis, keywords in _TOPIC_KEYWORDS.items()
        }
        max_score = max(raw_scores.values(), default=0)
        compass = []
        for axis, score in raw_scores.items():
            normalized = score / max_score if max_score > 0 else 0.0
            compass.append({"axis": axis, "score": round(normalized, 3), "hits": score})
        compass.sort(key=lambda item: (-item["score"], item["axis"]))
        return compass

    def _link_pressure(self, url: str, links: list[dict]) -> float:
        if not links:
            return 0.0
        current_domain = self._extract_domain(url)
        external_links = 0
        for link in links:
            href = str(link.get("href", "")).strip()
            if not href:
                continue
            domain = self._extract_domain(href)
            if domain and current_domain and domain != current_domain:
                external_links += 1
        density = min(1.0, len(links) / 24)
        external_ratio = external_links / max(1, len(links))
        return min(1.0, 0.55 * density + 0.45 * external_ratio)

    def _interaction_pressure(
        self, text: str, forms: list[dict], buttons: list[dict]
    ) -> float:
        form_pressure = min(1.0, len(forms) * 0.45)
        button_pressure = min(1.0, len(buttons) / 8)
        auth_pressure = 0.35 if self._contains_hint(text, _AUTH_HINTS) else 0.0
        payment_pressure = 0.35 if self._contains_hint(text, _PAYMENT_HINTS) else 0.0
        destructive_pressure = (
            0.2 if self._contains_hint(text, _DESTRUCTIVE_HINTS) else 0.0
        )
        return min(
            1.0,
            0.35 * form_pressure
            + 0.2 * button_pressure
            + auth_pressure
            + payment_pressure
            + destructive_pressure,
        )

    def _boundary_signals(
        self,
        *,
        url: str,
        text: str,
        links: list[dict],
        forms: list[dict],
        buttons: list[dict],
        interaction_pressure: float,
        link_pressure: float,
    ) -> list[str]:
        signals: list[str] = []
        if self._contains_hint(text, _AUTH_HINTS):
            signals.append("identity boundary present")
        if self._contains_hint(text, _PAYMENT_HINTS):
            signals.append("commerce boundary present")
        if self._contains_hint(text, _DESTRUCTIVE_HINTS) or self._buttons_match(
            buttons, _DESTRUCTIVE_HINTS
        ):
            signals.append("state-change controls exposed")
        if forms:
            signals.append(f"{len(forms)} form surface(s)")
        # P3 fix: only flag outward pressure when external links actually exist
        if links and link_pressure >= 0.45:
            current_domain = self._extract_domain(url)
            has_external = any(
                self._extract_domain(str(link.get("href", ""))) not in (None, "", current_domain)
                for link in links
            )
            if has_external:
                signals.append("high outward navigation pressure")
        if interaction_pressure >= 0.6:
            signals.append("dense interaction surface")
        domain = self._extract_domain(url)
        if domain:
            signals.append(f"anchor domain: {domain}")
        return signals[:5]

    def _topology_summary(
        self,
        *,
        zone: str,
        primary_axis: str,
        trust_distance: float,
        boundary_signals: list[str],
    ) -> str:
        boundary_text = (
            boundary_signals[0] if boundary_signals else "no strong boundary signal"
        )
        return (
            f"{zone} topology with {primary_axis} as the dominant axis. "
            f"Hyperbolic trust distance sits at {trust_distance:.2f}; {boundary_text}."
        )

    @staticmethod
    def _hyperbolic_distance_from_origin(radius: float) -> float:
        r_sq = radius * radius
        denominator = max(POINCARE_EPSILON, 1 - r_sq)
        return math.acosh(max(1.0, 1 + (2 * r_sq) / denominator))

    @staticmethod
    def _extract_domain(url: str) -> str:
        try:
            return urlparse(url).hostname or ""
        except ValueError:
            return ""

    @staticmethod
    def _contains_hint(text: str, hints: set[str]) -> bool:
        return any(hint in text for hint in hints)

    @staticmethod
    def _buttons_match(buttons: list[dict], hints: set[str]) -> bool:
        for button in buttons:
            button_text = " ".join(
                str(button.get(key, "")) for key in ("text", "type", "name")
            ).lower()
            if any(hint in button_text for hint in hints):
                return True
        return False
