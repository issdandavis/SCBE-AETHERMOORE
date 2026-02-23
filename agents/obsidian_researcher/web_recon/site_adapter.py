"""Adaptive Extraction Rules -- match content patterns to domains and learn
new extraction strategies from page structure.

Pre-built adapters are provided for well-known research sites (arXiv,
GitHub, Wikipedia, StackOverflow, HuggingFace).  The
:class:`AdaptiveToolBuilder` can infer rules from a
:class:`SemanticSkeleton` for unknown domains.

All pure stdlib.  No external dependencies.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .recon_goggles import SemanticSkeleton


# ------------------------------------------------------------------
# Data structures
# ------------------------------------------------------------------

@dataclass
class ExtractionRule:
    """A single extraction strategy for a named content region."""

    name: str
    css_selector: str       # simplified CSS selector (for documentation)
    regex_pattern: str      # actual extraction regex
    attribute: str = ""     # "href", "src", "text", etc.
    confidence: float = 0.5


@dataclass
class SiteAdapter:
    """Extraction configuration for a specific domain."""

    domain: str
    extraction_rules: List[ExtractionRule] = field(default_factory=list)
    pagination_selector: str = ""
    search_selector: str = ""
    rate_strategy: str = "polite"  # polite, moderate, aggressive


# ------------------------------------------------------------------
# Pre-built adapters for known sites
# ------------------------------------------------------------------

KNOWN_ADAPTERS: Dict[str, SiteAdapter] = {
    "arxiv.org": SiteAdapter(
        domain="arxiv.org",
        extraction_rules=[
            ExtractionRule(
                name="abstract",
                css_selector="blockquote.abstract",
                regex_pattern=r'<blockquote[^>]*class="abstract[^"]*"[^>]*>(.*?)</blockquote>',
                attribute="text",
                confidence=0.9,
            ),
            ExtractionRule(
                name="title",
                css_selector="h1.title",
                regex_pattern=r'<h1[^>]*class="title[^"]*"[^>]*>(.*?)</h1>',
                attribute="text",
                confidence=0.9,
            ),
            ExtractionRule(
                name="authors",
                css_selector="div.authors",
                regex_pattern=r'<div[^>]*class="authors[^"]*"[^>]*>(.*?)</div>',
                attribute="text",
                confidence=0.85,
            ),
        ],
        pagination_selector="",
        search_selector='input[name="query"]',
        rate_strategy="polite",
    ),
    "github.com": SiteAdapter(
        domain="github.com",
        extraction_rules=[
            ExtractionRule(
                name="readme",
                css_selector="article.markdown-body",
                regex_pattern=r'<article[^>]*class="[^"]*markdown-body[^"]*"[^>]*>(.*?)</article>',
                attribute="text",
                confidence=0.85,
            ),
            ExtractionRule(
                name="repo_description",
                css_selector="p.f4",
                regex_pattern=r'<p[^>]*class="[^"]*f4[^"]*"[^>]*>(.*?)</p>',
                attribute="text",
                confidence=0.7,
            ),
        ],
        pagination_selector='a[rel="next"]',
        rate_strategy="polite",
    ),
    "en.wikipedia.org": SiteAdapter(
        domain="en.wikipedia.org",
        extraction_rules=[
            ExtractionRule(
                name="article_body",
                css_selector="div#mw-content-text",
                regex_pattern=r'<div[^>]*id="mw-content-text"[^>]*>(.*?)<div[^>]*class="printfooter"',
                attribute="text",
                confidence=0.9,
            ),
            ExtractionRule(
                name="title",
                css_selector="h1#firstHeading",
                regex_pattern=r'<h1[^>]*id="firstHeading"[^>]*>(.*?)</h1>',
                attribute="text",
                confidence=0.95,
            ),
            ExtractionRule(
                name="infobox",
                css_selector="table.infobox",
                regex_pattern=r'<table[^>]*class="[^"]*infobox[^"]*"[^>]*>(.*?)</table>',
                attribute="text",
                confidence=0.75,
            ),
        ],
        pagination_selector="",
        search_selector='input[name="search"]',
        rate_strategy="polite",
    ),
    "stackoverflow.com": SiteAdapter(
        domain="stackoverflow.com",
        extraction_rules=[
            ExtractionRule(
                name="question",
                css_selector="div.s-prose",
                regex_pattern=r'<div[^>]*class="[^"]*s-prose[^"]*"[^>]*>(.*?)</div>',
                attribute="text",
                confidence=0.8,
            ),
            ExtractionRule(
                name="accepted_answer",
                css_selector="div.accepted-answer div.s-prose",
                regex_pattern=r'<div[^>]*class="[^"]*accepted-answer[^"]*"[^>]*>.*?<div[^>]*class="[^"]*s-prose[^"]*"[^>]*>(.*?)</div>',
                attribute="text",
                confidence=0.8,
            ),
        ],
        pagination_selector='a[rel="next"]',
        search_selector='input[name="q"]',
        rate_strategy="polite",
    ),
    "huggingface.co": SiteAdapter(
        domain="huggingface.co",
        extraction_rules=[
            ExtractionRule(
                name="model_card",
                css_selector="div.prose",
                regex_pattern=r'<div[^>]*class="[^"]*prose[^"]*"[^>]*>(.*?)</div>',
                attribute="text",
                confidence=0.75,
            ),
            ExtractionRule(
                name="model_name",
                css_selector="h1",
                regex_pattern=r'<h1[^>]*>(.*?)</h1>',
                attribute="text",
                confidence=0.8,
            ),
        ],
        rate_strategy="polite",
    ),
}

_STRIP_TAGS_RE = re.compile(r"<[^>]+>")


# ------------------------------------------------------------------
# AdaptiveToolBuilder
# ------------------------------------------------------------------

class AdaptiveToolBuilder:
    """Create or retrieve :class:`SiteAdapter` instances for domains.

    Falls back to heuristic rule generation from a
    :class:`SemanticSkeleton` when no pre-built adapter exists.
    """

    def __init__(self) -> None:
        self._custom_adapters: Dict[str, SiteAdapter] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_adapter(self, domain: str) -> SiteAdapter:
        """Return the best adapter for *domain*.

        Lookup order: custom learned adapters, pre-built known adapters,
        then a minimal fallback adapter.
        """
        if domain in self._custom_adapters:
            return self._custom_adapters[domain]
        if domain in KNOWN_ADAPTERS:
            return KNOWN_ADAPTERS[domain]
        # Minimal fallback
        return SiteAdapter(
            domain=domain,
            extraction_rules=[
                ExtractionRule(
                    name="body_text",
                    css_selector="body",
                    regex_pattern=r"<body[^>]*>(.*?)</body>",
                    attribute="text",
                    confidence=0.3,
                ),
            ],
            rate_strategy="polite",
        )

    def learn_from_skeleton(
        self,
        skeleton: SemanticSkeleton,
        domain: str,
    ) -> SiteAdapter:
        """Infer extraction rules from page structure and cache the result.

        Heuristics:
        - High heading count -> content site, add heading + paragraph rules.
        - Many forms -> interactive / form site, add form extraction.
        - Many links -> navigation hub, add link extraction.
        - Many media -> media-heavy site, add media extraction.
        """
        rules: List[ExtractionRule] = []
        rate_strategy = "polite"

        dist = skeleton.tongue_distribution
        archetype = skeleton.page_archetype

        # Always add a body-text fallback
        rules.append(ExtractionRule(
            name="body_text",
            css_selector="body",
            regex_pattern=r"<body[^>]*>(.*?)</body>",
            attribute="text",
            confidence=0.3,
        ))

        # Content-heavy: headings + paragraphs
        if len(skeleton.headings) >= 3 or dist.get("RU", 0) > 0.4:
            rules.append(ExtractionRule(
                name="headings",
                css_selector="h1, h2, h3",
                regex_pattern=r"<h[1-3][^>]*>(.*?)</h[1-3]>",
                attribute="text",
                confidence=0.7,
            ))
            rules.append(ExtractionRule(
                name="paragraphs",
                css_selector="p",
                regex_pattern=r"<p[^>]*>(.*?)</p>",
                attribute="text",
                confidence=0.6,
            ))

        # Navigation-heavy: links
        if len(skeleton.links) >= 20 or dist.get("KO", 0) > 0.3:
            rules.append(ExtractionRule(
                name="links",
                css_selector="a[href]",
                regex_pattern=r'<a\s[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
                attribute="href",
                confidence=0.6,
            ))

        # Form-heavy
        if skeleton.forms >= 2 or dist.get("UM", 0) > 0.2:
            rules.append(ExtractionRule(
                name="forms",
                css_selector="form",
                regex_pattern=r"<form[^>]*>(.*?)</form>",
                attribute="text",
                confidence=0.5,
            ))
            rate_strategy = "moderate"

        # Media-heavy
        if skeleton.media >= 5 or dist.get("AV", 0) > 0.3:
            rules.append(ExtractionRule(
                name="images",
                css_selector="img[src]",
                regex_pattern=r'<img\s[^>]*src="([^"]*)"',
                attribute="src",
                confidence=0.5,
            ))

        # Table-heavy
        if skeleton.tables >= 2:
            rules.append(ExtractionRule(
                name="tables",
                css_selector="table",
                regex_pattern=r"<table[^>]*>(.*?)</table>",
                attribute="text",
                confidence=0.6,
            ))

        adapter = SiteAdapter(
            domain=domain,
            extraction_rules=rules,
            rate_strategy=rate_strategy,
        )
        self._custom_adapters[domain] = adapter
        return adapter

    # ------------------------------------------------------------------
    # Extraction execution
    # ------------------------------------------------------------------

    def extract(self, html: str, adapter: SiteAdapter) -> Dict[str, Any]:
        """Run all extraction rules from *adapter* against *html*.

        Returns a dict mapping rule name -> extracted content string.
        """
        results: Dict[str, Any] = {}

        for rule in adapter.extraction_rules:
            try:
                match = re.search(rule.regex_pattern, html, re.IGNORECASE | re.DOTALL)
            except re.error:
                continue

            if match is None:
                continue

            raw = match.group(1) if match.lastindex else match.group(0)

            if rule.attribute == "text":
                # Strip HTML tags for text extraction
                results[rule.name] = _STRIP_TAGS_RE.sub(" ", raw).strip()
            elif rule.attribute in ("href", "src"):
                results[rule.name] = raw.strip()
            else:
                results[rule.name] = raw.strip()

        return results
