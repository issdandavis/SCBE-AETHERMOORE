"""Render IngestionResult + WikiLinks into Obsidian-compatible markdown.

Each source type has its own template (arXiv, Reddit, web page, brainstorm).
A separate ``render_discrepancy`` method produces conflict-tracking notes.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.parse import urlparse

from .source_adapter import SourceType, IngestionResult
from .cross_reference_engine import WikiLink


class NoteRenderer:
    """Produces Obsidian-flavoured markdown strings from ingestion data."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(self, result: IngestionResult, links: List[WikiLink]) -> str:
        """Dispatch to the correct template based on *result.source_type*."""
        dispatch = {
            SourceType.ARXIV: self.render_arxiv,
            SourceType.REDDIT: self.render_reddit,
            SourceType.WEB_PAGE: self.render_web_page,
            SourceType.BRAINSTORM: self.render_brainstorm,
        }
        handler = dispatch.get(result.source_type, self.render_web_page)
        return handler(result, links)

    # ------------------------------------------------------------------
    # Template: arXiv
    # ------------------------------------------------------------------

    def render_arxiv(self, result: IngestionResult, links: List[WikiLink]) -> str:
        arxiv_id = result.identifiers.get("arxiv_id", "")
        pdf_url = result.identifiers.get("pdf_url", "")
        abs_url = result.url or ""
        categories = [t for t in result.tags if t]

        fm = self._render_frontmatter({
            "title": result.title,
            "date": self._now_iso(),
            "source": "arxiv",
            "arxiv_id": arxiv_id,
            "pdf_url": pdf_url,
            "authors": result.authors,
            "categories": categories,
            "tags": list(set(categories + ["arxiv", "research"])),
        })

        body_parts: List[str] = [
            fm,
            f"# {result.title}\n",
        ]

        # Links line
        link_parts: List[str] = []
        if abs_url:
            link_parts.append(f"[arXiv]({abs_url})")
        if pdf_url:
            link_parts.append(f"[PDF]({pdf_url})")
        if link_parts:
            body_parts.append(" | ".join(link_parts) + "\n")

        # Authors
        if result.authors:
            body_parts.append("**Authors:** " + ", ".join(result.authors) + "\n")

        # Published
        if result.timestamp:
            body_parts.append(f"**Published:** {result.timestamp}\n")

        # Abstract
        body_parts.append("## Abstract\n")
        body_parts.append((result.summary or result.raw_content).strip() + "\n")

        # SCBE Relevance
        if result.scbe_relevance:
            body_parts.append("## SCBE Relevance\n")
            for concept, score in sorted(
                result.scbe_relevance.items(), key=lambda kv: kv[1], reverse=True
            ):
                bar = self._confidence_bar(score)
                body_parts.append(f"- **{concept}**: {score:.2f} {bar}")
            body_parts.append("")

        # Cross-References
        body_parts.append(self._render_cross_refs(links))

        # Notes placeholder
        body_parts.append("## Notes\n")
        body_parts.append("_Add your notes here._\n")

        return "\n".join(body_parts)

    # ------------------------------------------------------------------
    # Template: Reddit
    # ------------------------------------------------------------------

    def render_reddit(self, result: IngestionResult, links: List[WikiLink]) -> str:
        subreddit = result.metadata.get("subreddit", "unknown")
        score = result.metadata.get("score", 0)

        fm = self._render_frontmatter({
            "title": result.title,
            "date": self._now_iso(),
            "source": "reddit",
            "subreddit": subreddit,
            "url": result.url or "",
            "score": score,
        })

        body_parts: List[str] = [
            fm,
            f"# {result.title}\n",
        ]

        # Summary
        body_parts.append("## Summary\n")
        body_parts.append((result.summary or result.raw_content).strip() + "\n")

        # Key Points
        key_points: List[str] = result.metadata.get("key_points", [])
        if key_points:
            body_parts.append("## Key Points\n")
            for point in key_points:
                body_parts.append(f"- {point}")
            body_parts.append("")

        # Cross-References
        body_parts.append(self._render_cross_refs(links))

        return "\n".join(body_parts)

    # ------------------------------------------------------------------
    # Template: Web Page
    # ------------------------------------------------------------------

    def render_web_page(self, result: IngestionResult, links: List[WikiLink]) -> str:
        domain = ""
        if result.url:
            try:
                domain = urlparse(result.url).netloc
            except Exception:
                domain = ""

        fm = self._render_frontmatter({
            "title": result.title,
            "date": self._now_iso(),
            "source": "web_page",
            "url": result.url or "",
            "domain": domain,
        })

        body_parts: List[str] = [
            fm,
            f"# {result.title}\n",
        ]

        # Summary
        body_parts.append("## Summary\n")
        body_parts.append((result.summary or result.raw_content).strip() + "\n")

        # Key Takeaways
        body_parts.append("## Key Takeaways\n")
        body_parts.append("- _Summarize key points here._\n")

        # Cross-References
        body_parts.append(self._render_cross_refs(links))

        return "\n".join(body_parts)

    # ------------------------------------------------------------------
    # Template: Brainstorm
    # ------------------------------------------------------------------

    def render_brainstorm(self, result: IngestionResult, links: List[WikiLink]) -> str:
        fm = self._render_frontmatter({
            "title": result.title,
            "date": self._now_iso(),
            "source": "brainstorm",
            "author": "Issac Davis",
            "status": "draft",
        })

        body_parts: List[str] = [
            fm,
            f"# {result.title}\n",
        ]

        # Raw Idea
        body_parts.append("## Raw Idea\n")
        body_parts.append(result.raw_content.strip() + "\n")

        # Cross-References
        body_parts.append(self._render_cross_refs(links))

        # Follow-Up Actions
        body_parts.append("## Follow-Up Actions\n")
        body_parts.append("- [ ] Search arXiv for supporting literature")
        body_parts.append("- [ ] Prototype implementation")
        body_parts.append("- [ ] Evaluate SCBE layer alignment")
        body_parts.append("- [ ] Write formal design note\n")

        return "\n".join(body_parts)

    # ------------------------------------------------------------------
    # Discrepancy Note
    # ------------------------------------------------------------------

    def render_discrepancy(
        self,
        concept: str,
        source_a_title: str,
        claim_a: str,
        source_b_title: str,
        claim_b: str,
        severity: str,
        links: List[WikiLink],
    ) -> str:
        """Produce a conflict-tracking note for contradictory claims."""
        title = f"Discrepancy \u2014 {concept}"

        fm = self._render_frontmatter({
            "title": title,
            "date": self._now_iso(),
            "severity": severity,
            "status": "unresolved",
        })

        body_parts: List[str] = [
            fm,
            f"# {title}\n",
        ]

        # Conflicting Claims
        body_parts.append("## Conflicting Claims\n")
        body_parts.append(f"### Source A: [[{source_a_title}]]\n")
        body_parts.append(f"> {claim_a}\n")
        body_parts.append(f"### Source B: [[{source_b_title}]]\n")
        body_parts.append(f"> {claim_b}\n")

        # Analysis placeholder
        body_parts.append("## Analysis\n")
        body_parts.append("_Pending investigation._\n")

        # Resolution Status
        body_parts.append("## Resolution Status\n")
        body_parts.append("- [ ] Claims verified against primary sources")
        body_parts.append("- [ ] Root cause identified")
        body_parts.append("- [ ] Resolution documented")
        body_parts.append("- [ ] Affected notes updated\n")

        # Cross-References
        body_parts.append(self._render_cross_refs(links))

        return "\n".join(body_parts)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _now_iso() -> str:
        """Return current UTC time in ISO 8601."""
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _render_frontmatter(data: Dict[str, Any]) -> str:
        """Convert *data* to a YAML frontmatter block between ``---`` fences.

        Lists are rendered as YAML sequences.  Strings that contain colons or
        other special characters are double-quoted.
        """
        lines: List[str] = ["---"]
        for key, value in data.items():
            if isinstance(value, list):
                if not value:
                    lines.append(f"{key}: []")
                else:
                    lines.append(f"{key}:")
                    for item in value:
                        lines.append(f"  - \"{item}\"" if _needs_quoting(str(item)) else f"  - {item}")
            elif isinstance(value, bool):
                lines.append(f"{key}: {'true' if value else 'false'}")
            elif isinstance(value, (int, float)):
                lines.append(f"{key}: {value}")
            else:
                s = str(value)
                if _needs_quoting(s):
                    lines.append(f'{key}: "{s}"')
                else:
                    lines.append(f"{key}: {s}")
        lines.append("---")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _render_cross_refs(links: List[WikiLink]) -> str:
        """Render WikiLinks as an Obsidian cross-references section."""
        if not links:
            return "## Cross-References\n\n_No cross-references found._\n"
        lines: List[str] = ["## Cross-References\n"]
        for link in links:
            reason = getattr(link, "reason", "")
            target = getattr(link, "target_page", str(link))
            if reason:
                lines.append(f"- [[{target}]] \u2014 {reason}")
            else:
                lines.append(f"- [[{target}]]")
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _confidence_bar(score: float) -> str:
        """Return a tiny Unicode bar chart for a 0-1 score."""
        filled = round(score * 10)
        return "\u2588" * filled + "\u2591" * (10 - filled)


# ------------------------------------------------------------------
# Module-level helpers
# ------------------------------------------------------------------

def _needs_quoting(s: str) -> bool:
    """Return True if the YAML value string needs double-quoting."""
    if not s:
        return True
    # Quote if it contains characters that confuse YAML parsers
    for ch in (":", "#", "{", "}", "[", "]", ",", "&", "*", "?", "|", "-", "<", ">", "=", "!", "%", "@", "`", '"', "'"):
        if ch in s:
            return True
    # Quote if it looks like a boolean or null
    if s.lower() in ("true", "false", "yes", "no", "null", "~"):
        return True
    return False
