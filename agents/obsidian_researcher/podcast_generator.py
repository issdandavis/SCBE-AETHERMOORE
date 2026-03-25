"""Generate podcast-style audio scripts from research ingestion results.

Inspired by Google NotebookLM's audio overview feature. Produces a
two-host conversational script that explains research findings in an
accessible format, suitable for text-to-speech rendering.

Pure stdlib. No external dependencies.
"""

from __future__ import annotations

import hashlib
import re
import textwrap
from dataclasses import dataclass, field
from typing import List

from .source_adapter import IngestionResult
from .cross_reference_engine import WikiLink


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_WORDS_PER_MINUTE = 150

_TRANSITION_PHRASES: List[str] = [
    "That's fascinating. So what you're saying is",
    "Let me make sure I understand this correctly.",
    "OK so building on that,",
    "Wait, that connects to something else we found.",
    "Here's where it gets really interesting.",
    "Oh that's a great point. And it ties into",
    "So in other words,",
    "That reminds me of something we saw earlier.",
    "Right, and I think the key insight here is",
    "Wow, I hadn't thought of it that way.",
]

_QUESTION_TEMPLATES: List[str] = [
    "But what does {concept} actually mean in practice?",
    "How does {concept} relate to {other_concept}?",
    "So if I'm a developer, why should I care about {concept}?",
    "What happens when {concept} fails or breaks down?",
    "Can you break down {concept} for someone who's never heard of it?",
    "What surprised you most about {concept}?",
    "Is {concept} something that's being used in production today?",
    "How would {concept} change the way we think about {other_concept}?",
]

_BRIDGE_TEMPLATES: List[str] = [
    "You know what's interesting? This idea of {concept_a} actually leads "
    "right into the next thing we found about {concept_b}.",
    "And speaking of {concept_a}, there's a really natural connection to "
    "{concept_b} that I want to explore.",
    "So {concept_a} is one piece of the puzzle. But the next piece, "
    "{concept_b}, is where it all starts to come together.",
    "That's a perfect segue actually, because {concept_a} opens the door "
    "to a related topic: {concept_b}.",
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class PodcastSegment:
    """A single exchange in the podcast."""

    speaker: str  # "Host A" or "Host B"
    text: str
    segment_type: str  # "intro", "exposition", "question", "bridge", "deep_dive", "takeaway", "outro"
    duration_estimate_sec: float = 0.0  # estimated speaking time at 150 wpm

    def word_count(self) -> int:
        """Return the number of words in the segment text."""
        return len(self.text.split())


@dataclass
class PodcastScript:
    """Complete podcast script with metadata."""

    title: str
    segments: List[PodcastSegment] = field(default_factory=list)
    total_duration_sec: float = 0.0
    source_count: int = 0
    topics: List[str] = field(default_factory=list)

    def render_markdown(self) -> str:
        """Render as Obsidian-compatible markdown with speaker labels."""
        lines: List[str] = [
            "---",
            f"title: {self.title}",
            "type: podcast-script",
            f"source_count: {self.source_count}",
            f"duration_min: {self.total_duration_sec / 60:.1f}",
            "---\n",
            f"# {self.title}\n",
            f"**Estimated duration:** {self._format_duration()}  ",
            f"**Sources covered:** {self.source_count}\n",
        ]

        if self.topics:
            lines.append("**Topics:** " + ", ".join(self.topics) + "\n")

        lines.append("---\n")

        current_type = ""
        for seg in self.segments:
            if seg.segment_type != current_type:
                current_type = seg.segment_type
                header = current_type.replace("_", " ").title()
                lines.append(f"### {header}\n")
            lines.append(f"**{seg.speaker}:** {seg.text}\n")

        return "\n".join(lines)

    def render_transcript(self) -> str:
        """Render as plain text transcript."""
        lines: List[str] = [
            f"PODCAST TRANSCRIPT: {self.title}",
            f"Duration: {self._format_duration()}",
            f"Sources: {self.source_count}",
            "=" * 60,
            "",
        ]
        for seg in self.segments:
            lines.append(f"[{seg.speaker}]")
            # Wrap at 72 chars for readability
            wrapped = textwrap.fill(seg.text, width=72)
            lines.append(wrapped)
            lines.append("")

        return "\n".join(lines)

    def _format_duration(self) -> str:
        """Format total_duration_sec as 'Xm Ys'."""
        minutes = int(self.total_duration_sec // 60)
        seconds = int(self.total_duration_sec % 60)
        if minutes == 0:
            return f"{seconds}s"
        return f"{minutes}m {seconds}s"


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------


class PodcastGenerator:
    """Generate podcast scripts from research results.

    Host A: The explainer -- breaks down complex topics clearly.
    Host B: The curious questioner -- asks follow-ups, makes analogies,
            keeps the conversation accessible.
    """

    def __init__(
        self,
        host_a_name: str = "Host A",
        host_b_name: str = "Host B",
    ) -> None:
        self.host_a = host_a_name
        self.host_b = host_b_name

    # ------------------------------------------------------------------ #
    # Public API                                                          #
    # ------------------------------------------------------------------ #

    def generate(
        self,
        results: List[IngestionResult],
        links: List[WikiLink],
        title: str = "SCBE Research Overview",
    ) -> PodcastScript:
        """Generate a full podcast script from ingestion results.

        Structure:
        1. Intro -- welcome and topic overview (Host A)
        2. For each result:
           a. Exposition -- Host A explains the key finding
           b. Question -- Host B asks a clarifying question
           c. Deep dive -- Host A elaborates
           d. Bridge -- Host B connects to the next topic
        3. Takeaway -- both summarise key insights
        4. Outro -- Host A wraps up
        """
        if not results:
            return PodcastScript(title=title)

        segments: List[PodcastSegment] = []

        # 1. Intro
        segments.extend(self._generate_intro(title, results))

        # 2. Per-result discussion
        for i, result in enumerate(results):
            result_links = self._links_for_result(result, links)
            segments.extend(self._generate_result_discussion(result, result_links, i))

            # Bridge to next topic if not last
            if i < len(results) - 1:
                segments.extend(self._generate_bridge(result, results[i + 1], links))

        # 3. Takeaway
        segments.extend(self._generate_takeaway(results, links))

        # 4. Outro
        segments.extend(self._generate_outro(title))

        # Estimate durations at 150 words per minute
        for seg in segments:
            wc = seg.word_count()
            seg.duration_estimate_sec = (wc / _WORDS_PER_MINUTE) * 60

        total_duration = sum(s.duration_estimate_sec for s in segments)
        topics = [r.title for r in results]

        return PodcastScript(
            title=title,
            segments=segments,
            total_duration_sec=total_duration,
            source_count=len(results),
            topics=topics,
        )

    # ------------------------------------------------------------------ #
    # Segment generators                                                   #
    # ------------------------------------------------------------------ #

    def _generate_intro(
        self,
        title: str,
        results: List[IngestionResult],
    ) -> List[PodcastSegment]:
        """Generate the opening segment."""
        topic_list = ", ".join(r.title for r in results[:3])
        more = f" and {len(results) - 3} more topics" if len(results) > 3 else ""

        greeting = (
            f"Welcome to {title}! Today we're diving into some really "
            f"exciting research findings. We've pulled together "
            f"{len(results)} sources covering {topic_list}{more}."
        )

        tag_set = set()
        for r in results:
            for t in r.tags[:3]:
                tag_set.add(t)
        tag_str = ", ".join(sorted(tag_set)[:5]) if tag_set else "cutting-edge research"

        response = (
            f"Yeah, this is a great batch. We're seeing themes around "
            f"{tag_str}, and there are some surprising connections between "
            f"these sources that I think people are really going to find "
            f"valuable. Let's jump right in."
        )

        return [
            PodcastSegment(
                speaker=self.host_a,
                text=greeting,
                segment_type="intro",
            ),
            PodcastSegment(
                speaker=self.host_b,
                text=response,
                segment_type="intro",
            ),
        ]

    def _generate_result_discussion(
        self,
        result: IngestionResult,
        result_links: List[WikiLink],
        index: int,
    ) -> List[PodcastSegment]:
        """Generate the exposition/question/deep-dive for a single result."""
        segments: List[PodcastSegment] = []

        summary = self._summarize_result(result)
        source_label = self._source_label(result)

        # Exposition: Host A explains the finding
        exposition_text = (
            f"So our {'next' if index > 0 else 'first'} source is "
            f"{source_label}. It's titled \"{result.title}\". {summary}"
        )
        segments.append(PodcastSegment(
            speaker=self.host_a,
            text=exposition_text,
            segment_type="exposition",
        ))

        # Question: Host B asks a clarifying question
        concepts = self._extract_concepts(result)
        primary_concept = concepts[0] if concepts else result.title
        secondary_concept = concepts[1] if len(concepts) > 1 else "the broader system"

        question_template = self._pick_phrase(_QUESTION_TEMPLATES, result.title)
        question_text = question_template.format(
            concept=primary_concept,
            other_concept=secondary_concept,
        )
        segments.append(PodcastSegment(
            speaker=self.host_b,
            text=question_text,
            segment_type="question",
        ))

        # Deep dive: Host A elaborates
        deep_dive_text = self._generate_deep_dive(result, result_links, primary_concept)
        segments.append(PodcastSegment(
            speaker=self.host_a,
            text=deep_dive_text,
            segment_type="deep_dive",
        ))

        # Host B reacts
        transition = self._pick_phrase(_TRANSITION_PHRASES, result.title + str(index))
        if result_links:
            link_target = result_links[0].target_page
            reaction = (
                f"{transition} it also connects to [[{link_target}]] "
                f"in the vault, which means this isn't just theoretical, "
                f"it's part of a bigger picture we've been building."
            )
        else:
            reaction = (
                f"{transition} this is definitely an area we should "
                f"keep tracking as more research comes out."
            )
        segments.append(PodcastSegment(
            speaker=self.host_b,
            text=reaction,
            segment_type="deep_dive",
        ))

        return segments

    def _generate_bridge(
        self,
        current: IngestionResult,
        next_result: IngestionResult,
        links: List[WikiLink],
    ) -> List[PodcastSegment]:
        """Generate a bridge segment connecting two results."""
        connection = self._find_connection(current, next_result, links)
        concept_a = current.title
        concept_b = next_result.title

        template = self._pick_phrase(_BRIDGE_TEMPLATES, concept_a + concept_b)
        bridge_text = template.format(
            concept_a=concept_a,
            concept_b=concept_b,
        )

        if connection:
            bridge_text += f" {connection}"

        return [
            PodcastSegment(
                speaker=self.host_b,
                text=bridge_text,
                segment_type="bridge",
            ),
        ]

    def _generate_takeaway(
        self,
        results: List[IngestionResult],
        links: List[WikiLink],
    ) -> List[PodcastSegment]:
        """Generate the takeaway/summary section."""
        segments: List[PodcastSegment] = []

        # Host A summarises high-level themes
        theme_parts: List[str] = []
        for r in results[:4]:
            concepts = self._extract_concepts(r)
            if concepts:
                theme_parts.append(concepts[0])
            else:
                theme_parts.append(r.title)

        themes_str = ", ".join(theme_parts[:-1])
        if len(theme_parts) > 1:
            themes_str += f", and {theme_parts[-1]}"
        elif theme_parts:
            themes_str = theme_parts[0]

        host_a_takeaway = (
            f"Alright, so stepping back and looking at the big picture "
            f"here. We covered {themes_str}. The throughline across all "
            f"of this research is that these concepts aren't isolated. "
            f"They reinforce each other and create a much stronger "
            f"foundation when you consider them together."
        )
        segments.append(PodcastSegment(
            speaker=self.host_a,
            text=host_a_takeaway,
            segment_type="takeaway",
        ))

        # Host B highlights the most interesting connection
        link_count = len(links)
        if link_count > 0:
            best_link = max(links, key=lambda lk: lk.confidence)
            host_b_takeaway = (
                f"Absolutely. And what I keep coming back to is that "
                f"connection to [[{best_link.target_page}]], "
                f"because {best_link.reason}. We found {link_count} "
                f"cross-references across these sources, which tells me "
                f"this research area is converging in a really productive "
                f"way."
            )
        else:
            host_b_takeaway = (
                f"Exactly. And I think the practical takeaway for our "
                f"listeners is that this is a space that's moving fast. "
                f"Each of these {len(results)} sources adds another "
                f"piece to the puzzle, and I'm excited to see where it "
                f"goes next."
            )
        segments.append(PodcastSegment(
            speaker=self.host_b,
            text=host_b_takeaway,
            segment_type="takeaway",
        ))

        return segments

    def _generate_outro(self, title: str) -> List[PodcastSegment]:
        """Generate the closing segment."""
        return [
            PodcastSegment(
                speaker=self.host_a,
                text=(
                    f"That's a wrap for this edition of {title}. "
                    f"If you found this useful, all the sources and "
                    f"cross-references we discussed are linked in the "
                    f"vault notes below. Until next time, keep "
                    f"researching and keep building."
                ),
                segment_type="outro",
            ),
            PodcastSegment(
                speaker=self.host_b,
                text="See you next time!",
                segment_type="outro",
            ),
        ]

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _summarize_result(self, result: IngestionResult) -> str:
        """Create a spoken-language summary of a result.

        Uses the summary field if available, otherwise extracts the first
        few sentences from raw_content and rewrites them for spoken delivery.
        """
        source_text = result.summary if result.summary else result.raw_content

        if not source_text.strip():
            return f"This source covers {result.title} but we don't have a detailed summary available."

        # Extract first 3 meaningful sentences
        sentences = self._split_sentences(source_text)
        key_sentences = [s for s in sentences if len(s.split()) > 4][:3]

        if not key_sentences:
            return f"The key finding here is about {result.title}."

        # Build spoken summary
        summary = " ".join(key_sentences)

        # Add author attribution if available
        if result.authors:
            author_str = (
                result.authors[0]
                if len(result.authors) == 1
                else f"{result.authors[0]} and colleagues"
            )
            summary = f"The research by {author_str} shows that {summary[0].lower()}{summary[1:]}"

        # Add relevance context if SCBE relevance scores exist
        if result.scbe_relevance:
            top_concept = max(result.scbe_relevance, key=result.scbe_relevance.get)
            score = result.scbe_relevance[top_concept]
            summary += (
                f" This is particularly relevant to {top_concept}, "
                f"where it scored a {score:.0%} relevance match."
            )

        return summary

    def _generate_deep_dive(
        self,
        result: IngestionResult,
        result_links: List[WikiLink],
        primary_concept: str,
    ) -> str:
        """Generate the deep-dive elaboration for a result."""
        parts: List[str] = []

        parts.append(
            f"Great question. So {primary_concept} is important because "
            f"it addresses a real gap in how we think about these systems."
        )

        # Add detail from tags
        if result.tags:
            tag_context = ", ".join(result.tags[:4])
            parts.append(
                f"The research touches on {tag_context}, which gives you "
                f"a sense of the scope here."
            )

        # Add detail from cross-references
        if result_links:
            link_reasons = [lk.reason for lk in result_links[:2]]
            for reason in link_reasons:
                parts.append(
                    f"One thing worth noting is the {reason}, which tells "
                    f"us this isn't happening in isolation."
                )

        # Add metadata context
        if result.metadata:
            if "subreddit" in result.metadata:
                parts.append(
                    f"This was actually a hot topic in r/{result.metadata['subreddit']}, "
                    f"so the community is clearly paying attention."
                )
            if "score" in result.metadata and isinstance(result.metadata["score"], (int, float)):
                score = result.metadata["score"]
                if score > 100:
                    parts.append(
                        f"It got a score of {score} on the platform, "
                        f"which shows significant community engagement."
                    )

        # Fallback for short deep dives
        if len(parts) < 3:
            parts.append(
                f"The bottom line is that {result.title} gives us a "
                f"concrete framework for thinking about these challenges, "
                f"and that's what makes it so useful."
            )

        return " ".join(parts)

    def _find_connection(
        self,
        result_a: IngestionResult,
        result_b: IngestionResult,
        links: List[WikiLink],
    ) -> str:
        """Find how two results connect via WikiLinks or shared concepts."""
        # Strategy 1: Check for shared WikiLink targets
        targets_a = set()
        targets_b = set()
        for lk in links:
            text_a = f"{result_a.title} {result_a.raw_content} {result_a.summary}".lower()
            text_b = f"{result_b.title} {result_b.raw_content} {result_b.summary}".lower()
            target_lower = lk.target_page.lower()
            if target_lower in text_a or any(t.lower() in text_a for t in result_a.tags):
                targets_a.add(lk.target_page)
            if target_lower in text_b or any(t.lower() in text_b for t in result_b.tags):
                targets_b.add(lk.target_page)

        shared = targets_a & targets_b
        if shared:
            target = sorted(shared)[0]
            return (
                f"Both of these sources connect to [[{target}]], which is "
                f"a strong signal that there's a deeper relationship here."
            )

        # Strategy 2: Check for shared tags
        tags_a = set(t.lower() for t in result_a.tags)
        tags_b = set(t.lower() for t in result_b.tags)
        shared_tags = tags_a & tags_b
        if shared_tags:
            tag = sorted(shared_tags)[0]
            return (
                f"They both share the '{tag}' theme, which suggests "
                f"they're approaching the same problem from different angles."
            )

        # Strategy 3: Check for overlapping SCBE relevance
        if result_a.scbe_relevance and result_b.scbe_relevance:
            shared_concepts = set(result_a.scbe_relevance) & set(result_b.scbe_relevance)
            if shared_concepts:
                concept = sorted(shared_concepts)[0]
                return (
                    f"Both sources have strong relevance to {concept}, "
                    f"so they're clearly part of the same conversation."
                )

        return ""

    def _links_for_result(
        self,
        result: IngestionResult,
        all_links: List[WikiLink],
    ) -> List[WikiLink]:
        """Filter links that are relevant to a specific result.

        A link is considered relevant if its reason text overlaps with
        the result's title, tags, or content keywords.
        """
        text_lower = f"{result.title} {' '.join(result.tags)}".lower()
        relevant: List[WikiLink] = []
        for lk in all_links:
            # Check if any word from the link reason appears in the result text
            reason_words = set(lk.reason.lower().split())
            title_words = set(text_lower.split())
            overlap = reason_words & title_words
            # Require at least 2 overlapping words to avoid noise
            if len(overlap) >= 2:
                relevant.append(lk)
            # Also include if the target page name appears in result text
            elif lk.target_page.lower() in text_lower:
                relevant.append(lk)
        return relevant

    def _extract_concepts(self, result: IngestionResult) -> List[str]:
        """Extract the main concepts from a result for question generation.

        Returns up to 3 concepts drawn from tags, SCBE relevance keys,
        and title fragments.
        """
        concepts: List[str] = []

        # From SCBE relevance (most specific)
        if result.scbe_relevance:
            for concept in sorted(
                result.scbe_relevance,
                key=result.scbe_relevance.get,
                reverse=True,
            ):
                if concept not in concepts:
                    concepts.append(concept)
                if len(concepts) >= 2:
                    break

        # From tags
        for tag in result.tags:
            if tag and tag not in concepts and len(tag) > 3:
                concepts.append(tag)
            if len(concepts) >= 3:
                break

        # Fallback to title
        if not concepts:
            concepts.append(result.title)

        return concepts[:3]

    @staticmethod
    def _split_sentences(text: str) -> List[str]:
        """Split text into sentences using simple regex.

        Handles abbreviations like 'e.g.' and 'i.e.' gracefully.
        """
        # Replace common abbreviations to avoid false splits
        cleaned = text.replace("e.g.", "eg").replace("i.e.", "ie")
        cleaned = cleaned.replace("et al.", "et al").replace("Fig.", "Fig")
        cleaned = cleaned.replace("vs.", "vs").replace("Dr.", "Dr")
        # Split on sentence-ending punctuation followed by space or end
        parts = re.split(r"(?<=[.!?])\s+", cleaned.strip())
        return [p.strip() for p in parts if p.strip()]

    @staticmethod
    def _source_label(result: IngestionResult) -> str:
        """Return a human-friendly label for the source type."""
        labels = {
            "arxiv": "an arXiv paper",
            "reddit": "a Reddit discussion",
            "web_page": "a web article",
            "brainstorm": "one of our brainstorm notes",
            "vault": "an existing vault page",
        }
        source_str = (
            result.source_type.value
            if hasattr(result.source_type, "value")
            else str(result.source_type)
        )
        return labels.get(source_str, "a research source")

    @staticmethod
    def _pick_phrase(phrases: List[str], seed: str) -> str:
        """Deterministically pick a phrase based on a seed string.

        Uses a hash so the same input always produces the same phrase,
        giving reproducible scripts.
        """
        h = int(hashlib.md5(seed.encode("utf-8")).hexdigest(), 16)
        return phrases[h % len(phrases)]
