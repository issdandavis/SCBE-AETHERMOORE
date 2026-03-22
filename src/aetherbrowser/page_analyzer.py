"""
Page Analyzer — 'This Page' handler
=====================================

Analyzes the current tab's content when the user clicks 'This Page'.
Uses local heuristics first (zero API cost), then optionally enriches
with a model call via OctoArmor routing.
"""
from __future__ import annotations

import re
from collections import Counter

MAX_WORDS = 50_000

_TOPIC_KEYWORDS: dict[str, list[str]] = {
    "AI/ML": ["machine learning", "artificial intelligence", "neural network", "deep learning", "model", "training"],
    "Security": ["security", "vulnerability", "threat", "attack", "defense", "governance", "encryption"],
    "Research": ["research", "paper", "study", "findings", "experiment", "analysis"],
    "Finance": ["financial", "payment", "revenue", "pricing", "investment", "market"],
    "Code": ["code", "programming", "developer", "api", "function", "class", "repository"],
}

_AUTH_HINTS = {"auth", "credential", "email", "login", "password", "sign in", "signin", "username"}
_PAYMENT_HINTS = {"billing", "buy", "card", "checkout", "invoice", "order", "pay", "payment", "wallet"}
_DESTRUCTIVE_HINTS = {"delete", "deploy", "merge", "publish", "push", "remove", "submit", "transfer"}


def _hostname_matches(url: str, domain: str) -> bool:
    try:
        hostname = (urlparse(url).hostname or "").lower().rstrip(".")
    except ValueError:
        return False
    normalized = domain.lower().rstrip(".")
    return hostname == normalized or hostname.endswith(f".{normalized}")


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
        intent = self._infer_intent(url=url, title=title, text=text, page_type=page_type, forms=forms, buttons=buttons)
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
            "selected_text": selected_text,
            "has_screenshot": bool(screenshot),
        }

    def _extractive_summary(self, text: str, max_sentences: int = 3) -> str:
        sentences = re.split(r'(?<=[.!?])\s+', text.strip())
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
        if forms and (self._contains_hint(combined, _AUTH_HINTS) or self._buttons_match(buttons, _AUTH_HINTS)):
            return "authenticate"
        if forms and (self._contains_hint(combined, _PAYMENT_HINTS) or self._buttons_match(buttons, _PAYMENT_HINTS)):
            return "checkout"
        if _hostname_matches(url, "github.com") or "repository" in combined:
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
        if forms and (self._contains_hint(combined, _AUTH_HINTS) or self._buttons_match(buttons, _AUTH_HINTS)):
            approvals.append("Page contains authentication or credential entry")
        if forms and (self._contains_hint(combined, _PAYMENT_HINTS) or self._buttons_match(buttons, _PAYMENT_HINTS)):
            approvals.append("Page contains payment or checkout flow")
        if self._contains_hint(combined, _DESTRUCTIVE_HINTS) or self._buttons_match(buttons, _DESTRUCTIVE_HINTS):
            approvals.append("Page exposes a high-impact state-changing action")
        unique_approvals = list(dict.fromkeys(approvals))
        if any("payment" in item.lower() or "high-impact" in item.lower() for item in unique_approvals):
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

    @staticmethod
    def _contains_hint(text: str, hints: set[str]) -> bool:
        return any(hint in text for hint in hints)

    @staticmethod
    def _buttons_match(buttons: list[dict], hints: set[str]) -> bool:
        for button in buttons:
            button_text = " ".join(str(button.get(key, "")) for key in ("text", "type", "name")).lower()
            if any(hint in button_text for hint in hints):
                return True
        return False
