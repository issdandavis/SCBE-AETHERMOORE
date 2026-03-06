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


class PageAnalyzer:
    def analyze_sync(self, *, url: str, title: str, text: str) -> dict:
        truncated = False
        words = text.split()
        if len(words) > MAX_WORDS:
            words = words[:MAX_WORDS]
            text = " ".join(words)
            truncated = True

        word_count = len(words)
        summary = self._extractive_summary(text) if word_count > 0 else ""
        topics = self._detect_topics(text)

        return {
            "url": url,
            "title": title,
            "word_count": word_count,
            "summary": summary,
            "topics": topics,
            "truncated": truncated,
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
