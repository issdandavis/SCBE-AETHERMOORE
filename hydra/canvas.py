"""
HYDRA Canvas — Multi-Step Orchestrated Workflows with Model Spectrum
====================================================================

The "painting palette" concept:
- Each LLM provider is a COLOR (non-overlapping specialty lanes)
- Steps are BRUSH STROKES (10-100 step pipelines)
- The canvas is the KNOWLEDGE PRODUCT (merged output from all colors)
- Roundabouts enable INTELLIGENT BACKTRACKING (self-healing loops)

Architecture:
  ┌─────────────┐
  │  Canvas CLI  │ ← hydra canvas run <recipe>
  └──────┬──────┘
         │
  ┌──────▼──────┐
  │  Orchestrator│ ← Manages step execution, model assignment, backtracking
  └──────┬──────┘
         │
  ┌──────▼──────────────────────────────────────────────────┐
  │  Model Spectrum                                          │
  │  ┌────────┬────────┬────────┬────────┬────────┬────────┐ │
  │  │ Claude │  GPT   │ Gemini │  Grok  │  HF    │ Local  │ │
  │  │ VIOLET │  BLUE  │ GREEN  │ ORANGE │ RED    │ WHITE  │ │
  │  │ Arch.  │ Draft  │ Research│ Debate │ Embed  │ Code   │ │
  │  └────────┴────────┴────────┴────────┴────────┴────────┘ │
  └──────────────────────────────────────────────────────────┘
         │
  ┌──────▼──────┐
  │   Branching  │ ← ChoiceScript engine for multi-path steps
  │   Engine     │
  └──────┬──────┘
         │
  ┌──────▼──────┐
  │  Knowledge   │ ← Final merged canvas from all model outputs
  │  Canvas      │
  └─────────────┘

Usage:
    hydra canvas list                     # List available recipes
    hydra canvas run article              # Run a recipe
    hydra canvas run research --topic "chladni modes"
    hydra canvas show article             # Show recipe steps
    hydra canvas paint "topic" --steps 20 # Freeform canvas
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

try:
    from hydra.color_dimension import (
        SpectrumAllocator,
        ColorBand,
    )

    HAS_COLOR_DIMENSION = True
except ImportError:
    HAS_COLOR_DIMENSION = False


# ---------------------------------------------------------------------------
#  Model Spectrum — non-overlapping color lanes for each provider
# ---------------------------------------------------------------------------


class ModelColor(str, Enum):
    """Each provider gets a color lane defining its specialty."""

    VIOLET = "violet"  # Claude — architecture, synthesis, governance
    BLUE = "blue"  # GPT — drafting, expansion, formatting
    GREEN = "green"  # Gemini — research, fact-checking, citations
    ORANGE = "orange"  # Grok — debate, contrarian, edge cases
    RED = "red"  # HuggingFace — embeddings, classification, similarity
    WHITE = "white"  # Local — code generation, data processing


PROVIDER_SPECTRUM: Dict[str, Dict[str, Any]] = {
    "claude": {
        "color": ModelColor.VIOLET,
        "specialty": "architecture",
        "strengths": ["synthesis", "governance", "planning", "safety analysis"],
        "default_steps": ["plan", "synthesize", "govern", "review_final"],
    },
    "gpt": {
        "color": ModelColor.BLUE,
        "specialty": "drafting",
        "strengths": ["writing", "expansion", "formatting", "translation"],
        "default_steps": ["draft", "expand", "format", "edit"],
    },
    "gemini": {
        "color": ModelColor.GREEN,
        "specialty": "research",
        "strengths": ["fact_check", "citations", "search", "comparison"],
        "default_steps": ["research", "fact_check", "cite", "compare"],
    },
    "grok": {
        "color": ModelColor.ORANGE,
        "specialty": "debate",
        "strengths": ["contrarian", "edge_cases", "humor", "trends"],
        "default_steps": ["challenge", "edge_case", "reframe"],
    },
    "hf": {
        "color": ModelColor.RED,
        "specialty": "embedding",
        "strengths": ["classify", "embed", "similarity", "summarize"],
        "default_steps": ["classify", "embed", "similarity_check"],
    },
    "local": {
        "color": ModelColor.WHITE,
        "specialty": "code",
        "strengths": ["code_gen", "data_transform", "local_compute"],
        "default_steps": ["generate_code", "transform_data"],
    },
}


# ---------------------------------------------------------------------------
#  Step definitions — the LEGO blocks
# ---------------------------------------------------------------------------


class StepType(str, Enum):
    """Types of steps in a canvas workflow."""

    RESEARCH = "research"  # HYDRA research command
    ARXIV = "arxiv"  # HYDRA arxiv search/outline
    DRAFT = "draft"  # LLM writes content
    EDIT = "edit"  # LLM revises content
    EXPAND = "expand"  # LLM expands sections
    SYNTHESIZE = "synthesize"  # Merge multiple model outputs
    FACT_CHECK = "fact_check"  # Verify claims against sources
    GOVERNANCE = "governance"  # SCBE governance scan
    PUBLISH = "publish"  # Push to platform
    REMEMBER = "remember"  # Store in HYDRA memory
    BRANCH = "branch"  # ChoiceScript branching decision
    ROUNDABOUT = "roundabout"  # Backtracking checkpoint
    CANVAS_MERGE = "canvas_merge"  # Merge all color outputs into final
    DEBATE = "debate"  # Multi-model debate round
    CLASSIFY = "classify"  # Categorize content
    TRANSFORM = "transform"  # Data transformation
    WAIT = "wait"  # Barrier — wait for parallel steps
    BROWSER_NAV = "browser_nav"  # AetherBrowser navigation (arxiv, github, notion)
    OBSIDIAN_NOTE = "obsidian_note"  # Write to Obsidian vault
    CROSS_TALK = "cross_talk"  # Send cross-talk packet to another agent
    CUSTOM = "custom"  # User-defined action


@dataclass
class CanvasStep:
    """A single step in a multi-step canvas workflow."""

    step_id: str
    step_type: StepType
    description: str = ""
    assigned_color: Optional[ModelColor] = None  # Which model lane
    assigned_provider: Optional[str] = None  # Explicit provider override
    params: Dict[str, Any] = field(default_factory=dict)
    depends_on: List[str] = field(default_factory=list)  # Step IDs this depends on
    retry_limit: int = 2
    backtrack_to: Optional[str] = None  # Step ID to backtrack to on failure
    timeout_sec: float = 120.0
    tags: List[str] = field(default_factory=list)


@dataclass
class StepResult:
    """Result from executing a single step."""

    step_id: str
    status: str = "pending"  # pending | running | done | failed | backtracked
    output: str = ""
    artifacts: Dict[str, Any] = field(default_factory=dict)
    provider_used: str = ""
    color: str = ""
    duration_ms: float = 0.0
    retries: int = 0
    error: Optional[str] = None


@dataclass
class RoundaboutState:
    """Checkpoint for intelligent backtracking."""

    checkpoint_id: str
    step_id: str
    context_snapshot: Dict[str, Any]
    quality_score: float = 0.0
    visits: int = 0
    max_visits: int = 3


# ---------------------------------------------------------------------------
#  Knowledge Canvas — the final merged product
# ---------------------------------------------------------------------------


@dataclass
class KnowledgeCanvas:
    """The 'painting' — merged output from all model colors."""

    canvas_id: str
    topic: str
    colors_used: Dict[str, List[str]] = field(default_factory=dict)  # color -> [step outputs]
    sections: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    quality_score: float = 0.0
    timestamp: str = ""

    def add_stroke(self, color: str, content: str, source_step: str):
        """Add a brush stroke (model output) to the canvas."""
        if color not in self.colors_used:
            self.colors_used[color] = []
        self.colors_used[color].append(content)
        self.sections.append(
            {
                "color": color,
                "content": content,
                "source_step": source_step,
            }
        )

    def render(self) -> str:
        """Render the canvas as a coherent document."""
        parts: List[str] = []
        parts.append(f"# Knowledge Canvas: {self.topic}")
        parts.append(f"*Generated: {self.timestamp}*")
        parts.append(f"*Colors: {', '.join(sorted(self.colors_used.keys()))}*")
        parts.append("")

        # Group by color for the palette view
        for color, strokes in sorted(self.colors_used.items()):
            spec = next((s for s in PROVIDER_SPECTRUM.values() if s["color"].value == color), None)
            label = spec["specialty"] if spec else color
            parts.append(f"## [{color.upper()}] {label.title()}")
            for i, stroke in enumerate(strokes, 1):
                if stroke.strip():
                    parts.append(f"### Stroke {i}")
                    parts.append(stroke.strip())
                    parts.append("")

        return "\n".join(parts)


# ---------------------------------------------------------------------------
#  Canvas Recipes — pre-built multi-step workflows
# ---------------------------------------------------------------------------


def recipe_article(topic: str = "AI safety", target_length: int = 2000) -> List[CanvasStep]:
    """Full article pipeline: research -> outline -> draft -> edit -> expand -> fact-check -> publish."""
    return [
        CanvasStep(
            "research",
            StepType.RESEARCH,
            f"Deep research on: {topic}",
            assigned_color=ModelColor.GREEN,
            params={"query": topic, "max_subtasks": 3},
        ),
        CanvasStep(
            "arxiv_scan",
            StepType.ARXIV,
            f"Find academic papers on: {topic}",
            assigned_color=ModelColor.GREEN,
            params={"query": topic, "max": 5},
        ),
        CanvasStep(
            "outline",
            StepType.DRAFT,
            "Create structured outline from research",
            assigned_color=ModelColor.VIOLET,
            depends_on=["research", "arxiv_scan"],
            params={
                "instruction": (
                    f"Create a detailed outline for a {target_length}-word article on"
                    f" '{topic}'. Use the research findings."
                )
            },
        ),
        CanvasStep(
            "roundabout_outline", StepType.ROUNDABOUT, "Quality checkpoint: outline", params={"min_quality": 0.6}
        ),
        CanvasStep(
            "draft_body",
            StepType.DRAFT,
            "Write first draft",
            assigned_color=ModelColor.BLUE,
            depends_on=["outline"],
            params={
                "instruction": f"Write a {target_length}-word article following this outline. Be detailed and engaging."
            },
        ),
        CanvasStep(
            "challenge",
            StepType.DEBATE,
            "Contrarian review of draft",
            assigned_color=ModelColor.ORANGE,
            depends_on=["draft_body"],
            params={"instruction": "Challenge this draft. Find weak arguments, missing evidence, logical gaps."},
        ),
        CanvasStep(
            "edit",
            StepType.EDIT,
            "Revise based on challenges",
            assigned_color=ModelColor.BLUE,
            depends_on=["draft_body", "challenge"],
            params={"instruction": "Revise the draft addressing these critiques. Strengthen weak points."},
        ),
        CanvasStep(
            "expand",
            StepType.EXPAND,
            "Expand thin sections",
            assigned_color=ModelColor.BLUE,
            depends_on=["edit"],
            params={"instruction": f"Expand any sections under 200 words. Target total: {target_length} words."},
        ),
        CanvasStep(
            "fact_check",
            StepType.FACT_CHECK,
            "Verify all claims",
            assigned_color=ModelColor.GREEN,
            depends_on=["expand"],
            params={"instruction": "Verify every factual claim. Flag unverifiable statements."},
        ),
        CanvasStep(
            "roundabout_quality",
            StepType.ROUNDABOUT,
            "Quality checkpoint: final",
            depends_on=["fact_check"],
            params={"min_quality": 0.7},
            backtrack_to="edit",
        ),
        CanvasStep("governance_scan", StepType.GOVERNANCE, "SCBE governance check", depends_on=["expand"]),
        CanvasStep(
            "synthesize",
            StepType.SYNTHESIZE,
            "Final synthesis from all colors",
            assigned_color=ModelColor.VIOLET,
            depends_on=["expand", "fact_check", "governance_scan"],
            params={"instruction": "Synthesize the expanded draft with fact-check results into the final article."},
        ),
        CanvasStep(
            "remember",
            StepType.REMEMBER,
            "Store article in memory",
            depends_on=["synthesize"],
            params={"key": f"article_{topic.replace(' ', '_')[:30]}"},
        ),
        CanvasStep("canvas_merge", StepType.CANVAS_MERGE, "Merge all color outputs", depends_on=["synthesize"]),
    ]


def recipe_research_deep(topic: str = "quantum computing") -> List[CanvasStep]:
    """Deep multi-source research: arxiv + web + debate + synthesis."""
    return [
        CanvasStep(
            "arxiv_survey",
            StepType.ARXIV,
            f"ArXiv survey: {topic}",
            assigned_color=ModelColor.GREEN,
            params={"query": topic, "max": 10},
        ),
        CanvasStep(
            "web_research",
            StepType.RESEARCH,
            f"Web research: {topic}",
            assigned_color=ModelColor.GREEN,
            params={"query": topic, "max_subtasks": 5},
        ),
        CanvasStep(
            "classify_sources",
            StepType.CLASSIFY,
            "Categorize all sources",
            assigned_color=ModelColor.RED,
            depends_on=["arxiv_survey", "web_research"],
            params={"categories": ["theory", "application", "security", "governance"]},
        ),
        CanvasStep(
            "synthesis_violet",
            StepType.SYNTHESIZE,
            "Claude: architecture analysis",
            assigned_color=ModelColor.VIOLET,
            depends_on=["classify_sources"],
            params={"instruction": f"Analyze the architectural implications of {topic} research."},
        ),
        CanvasStep(
            "synthesis_blue",
            StepType.DRAFT,
            "GPT: accessible summary",
            assigned_color=ModelColor.BLUE,
            depends_on=["classify_sources"],
            params={"instruction": f"Write a clear, accessible summary of {topic} findings."},
        ),
        CanvasStep(
            "debate_round",
            StepType.DEBATE,
            "Multi-model debate",
            assigned_color=ModelColor.ORANGE,
            depends_on=["synthesis_violet", "synthesis_blue"],
            params={"instruction": "Compare these two perspectives. Where do they agree? Disagree?"},
        ),
        CanvasStep(
            "roundabout_depth",
            StepType.ROUNDABOUT,
            "Depth checkpoint",
            depends_on=["debate_round"],
            params={"min_quality": 0.5},
            backtrack_to="web_research",
        ),
        CanvasStep(
            "final_canvas",
            StepType.CANVAS_MERGE,
            "Paint the knowledge canvas",
            depends_on=["synthesis_violet", "synthesis_blue", "debate_round"],
        ),
    ]


def recipe_content_pipeline(topic: str = "SCBE update", platforms: Optional[List[str]] = None) -> List[CanvasStep]:
    """Multi-platform content: write -> adapt per platform -> govern -> publish."""
    platforms = platforms or ["twitter", "linkedin", "github", "medium"]
    steps: List[CanvasStep] = [
        CanvasStep(
            "core_draft",
            StepType.DRAFT,
            f"Core content about: {topic}",
            assigned_color=ModelColor.BLUE,
            params={"instruction": f"Write the core message about '{topic}' in 500 words."},
        ),
        CanvasStep("governance", StepType.GOVERNANCE, "Governance scan", depends_on=["core_draft"]),
    ]

    for platform in platforms:
        adapt_id = f"adapt_{platform}"
        pub_id = f"publish_{platform}"
        steps.append(
            CanvasStep(
                adapt_id,
                StepType.EDIT,
                f"Adapt for {platform}",
                assigned_color=ModelColor.BLUE,
                depends_on=["core_draft", "governance"],
                params={
                    "instruction": f"Adapt this content for {platform}. Follow {platform}'s style and length limits.",
                    "platform": platform,
                },
            )
        )
        steps.append(
            CanvasStep(
                pub_id,
                StepType.PUBLISH,
                f"Publish to {platform}",
                depends_on=[adapt_id],
                params={"platform": platform},
            )
        )

    steps.append(
        CanvasStep(
            "canvas_merge", StepType.CANVAS_MERGE, "Merge all adaptations", depends_on=[f"adapt_{p}" for p in platforms]
        )
    )
    return steps


def recipe_training_data(topic: str = "SCBE governance") -> List[CanvasStep]:
    """Training data generation: research -> generate pairs -> quality check -> export."""
    return [
        CanvasStep(
            "source_research",
            StepType.RESEARCH,
            f"Gather source material: {topic}",
            assigned_color=ModelColor.GREEN,
            params={"query": topic},
        ),
        CanvasStep(
            "generate_pairs",
            StepType.DRAFT,
            "Generate SFT prompt-response pairs",
            assigned_color=ModelColor.VIOLET,
            depends_on=["source_research"],
            params={"instruction": f"Generate 20 high-quality SFT pairs about {topic}. Format: prompt/response."},
        ),
        CanvasStep(
            "quality_check",
            StepType.DEBATE,
            "Quality review of pairs",
            assigned_color=ModelColor.ORANGE,
            depends_on=["generate_pairs"],
            params={"instruction": "Review these SFT pairs. Flag low-quality, ambiguous, or biased entries."},
        ),
        CanvasStep(
            "roundabout_quality",
            StepType.ROUNDABOUT,
            "Quality gate",
            depends_on=["quality_check"],
            params={"min_quality": 0.7},
            backtrack_to="generate_pairs",
        ),
        CanvasStep("governance_check", StepType.GOVERNANCE, "Governance scan", depends_on=["generate_pairs"]),
        CanvasStep(
            "export",
            StepType.TRANSFORM,
            "Export to JSONL",
            depends_on=["quality_check", "governance_check"],
            params={"format": "jsonl", "output": "training-data/canvas/"},
        ),
        CanvasStep(
            "remember",
            StepType.REMEMBER,
            "Store in HYDRA memory",
            depends_on=["export"],
            params={"key": f"training_{topic.replace(' ', '_')[:20]}"},
        ),
    ]


def recipe_full_loop(topic: str = "SCBE update") -> List[CanvasStep]:
    """Full development loop: browser research -> draft -> obsidian -> cross-talk -> publish.

    Combines all available lego blocks including browser navigation,
    Obsidian vault notes, and cross-talk agent coordination.
    """
    return [
        # Phase 1: Multi-source research
        CanvasStep(
            "browse_arxiv",
            StepType.BROWSER_NAV,
            f"Browse arXiv for: {topic}",
            params={"target": "arxiv", "query": topic},
        ),
        CanvasStep(
            "browse_github",
            StepType.BROWSER_NAV,
            f"Browse GitHub for: {topic}",
            params={"target": "github", "query": topic},
        ),
        CanvasStep(
            "arxiv_papers",
            StepType.ARXIV,
            f"Fetch papers: {topic}",
            assigned_color=ModelColor.GREEN,
            params={"query": topic, "max": 5},
        ),
        CanvasStep(
            "web_research",
            StepType.RESEARCH,
            f"Web research: {topic}",
            assigned_color=ModelColor.GREEN,
            params={"query": topic},
        ),
        # Phase 2: AI analysis (parallel model lanes)
        CanvasStep(
            "architect_analysis",
            StepType.SYNTHESIZE,
            "Claude: architectural analysis",
            assigned_color=ModelColor.VIOLET,
            depends_on=["arxiv_papers", "web_research"],
            params={"instruction": f"Analyze the architectural implications of {topic}."},
        ),
        CanvasStep(
            "draft_article",
            StepType.DRAFT,
            "GPT: write article draft",
            assigned_color=ModelColor.BLUE,
            depends_on=["arxiv_papers", "web_research"],
            params={"instruction": f"Write a 2000-word article on {topic}."},
        ),
        CanvasStep(
            "challenge_review",
            StepType.DEBATE,
            "Grok: contrarian review",
            assigned_color=ModelColor.ORANGE,
            depends_on=["draft_article"],
            params={"instruction": "Challenge this draft. Find weak points."},
        ),
        # Phase 3: Quality roundabout
        CanvasStep(
            "quality_gate",
            StepType.ROUNDABOUT,
            "Quality checkpoint",
            depends_on=["draft_article", "challenge_review"],
            params={"min_quality": 0.6},
            backtrack_to="draft_article",
        ),
        CanvasStep(
            "edit_revision",
            StepType.EDIT,
            "Revise based on review",
            assigned_color=ModelColor.BLUE,
            depends_on=["draft_article", "challenge_review", "quality_gate"],
            params={"instruction": "Revise the draft addressing all critiques."},
        ),
        CanvasStep(
            "fact_check",
            StepType.FACT_CHECK,
            "Verify all claims",
            assigned_color=ModelColor.GREEN,
            depends_on=["edit_revision"],
        ),
        # Phase 4: Governance + notes
        CanvasStep("governance", StepType.GOVERNANCE, "SCBE governance scan", depends_on=["edit_revision"]),
        CanvasStep(
            "obsidian_research_note",
            StepType.OBSIDIAN_NOTE,
            f"Research note: {topic}",
            depends_on=["architect_analysis", "fact_check"],
            params={"vault": "AI Workspace", "title": f"Research: {topic}"},
        ),
        CanvasStep(
            "obsidian_article_note",
            StepType.OBSIDIAN_NOTE,
            f"Article draft: {topic}",
            depends_on=["edit_revision"],
            params={"vault": "AI Workspace", "title": f"Article: {topic}"},
        ),
        # Phase 5: Cross-talk + synthesis
        CanvasStep(
            "cross_talk_codex",
            StepType.CROSS_TALK,
            f"Handoff to Codex: {topic}",
            depends_on=["governance"],
            params={
                "recipient": "agent.codex",
                "task_id": f"canvas-{topic[:20]}",
                "summary": f"Canvas pipeline complete for {topic}",
            },
        ),
        CanvasStep(
            "final_synthesis",
            StepType.SYNTHESIZE,
            "Final canvas synthesis",
            assigned_color=ModelColor.VIOLET,
            depends_on=["edit_revision", "fact_check", "governance", "architect_analysis"],
            params={"instruction": "Merge all model outputs into final knowledge product."},
        ),
        CanvasStep(
            "remember_result",
            StepType.REMEMBER,
            "Store in HYDRA memory",
            depends_on=["final_synthesis"],
            params={"key": f"canvas_{topic.replace(' ', '_')[:25]}"},
        ),
        # Phase 6: Multi-platform publish
        CanvasStep(
            "adapt_twitter",
            StepType.EDIT,
            "Adapt for Twitter/X",
            assigned_color=ModelColor.BLUE,
            depends_on=["final_synthesis"],
            params={"instruction": "Create a tweet thread from this article.", "platform": "twitter"},
        ),
        CanvasStep(
            "adapt_linkedin",
            StepType.EDIT,
            "Adapt for LinkedIn",
            assigned_color=ModelColor.BLUE,
            depends_on=["final_synthesis"],
            params={"instruction": "Adapt for LinkedIn professional audience.", "platform": "linkedin"},
        ),
        CanvasStep(
            "publish_twitter",
            StepType.PUBLISH,
            "Publish to Twitter",
            depends_on=["adapt_twitter"],
            params={"platform": "twitter"},
        ),
        CanvasStep(
            "publish_linkedin",
            StepType.PUBLISH,
            "Publish to LinkedIn",
            depends_on=["adapt_linkedin"],
            params={"platform": "linkedin"},
        ),
        # Final merge
        CanvasStep(
            "canvas_merge",
            StepType.CANVAS_MERGE,
            "Paint the knowledge canvas",
            depends_on=[
                "final_synthesis",
                "publish_twitter",
                "publish_linkedin",
                "obsidian_research_note",
                "obsidian_article_note",
            ],
        ),
    ]


RECIPE_REGISTRY: Dict[str, Callable] = {
    "article": recipe_article,
    "research": recipe_research_deep,
    "content": recipe_content_pipeline,
    "training": recipe_training_data,
    "full_loop": recipe_full_loop,
}


# ---------------------------------------------------------------------------
#  Canvas Orchestrator — executes multi-step workflows
# ---------------------------------------------------------------------------


class CanvasOrchestrator:
    """Execute canvas recipes with model spectrum assignment and backtracking."""

    def __init__(
        self,
        available_providers: Optional[List[str]] = None,
        max_retries: int = 2,
        max_roundabout_visits: int = 3,
    ):
        self.available_providers = available_providers or ["claude"]
        self.max_retries = max_retries
        self.max_roundabout_visits = max_roundabout_visits
        self.results: Dict[str, StepResult] = {}
        self.roundabouts: Dict[str, RoundaboutState] = {}
        self.canvas: Optional[KnowledgeCanvas] = None
        # Color dimension: frequency-based flow isolation
        self.spectrum: Optional[SpectrumAllocator] = None
        self.flow_channels: Dict[str, Any] = {}  # step_id -> ColorChannel
        if HAS_COLOR_DIMENSION:
            self.spectrum = SpectrumAllocator(min_separation_nm=15)

    def _assign_provider(self, step: CanvasStep) -> str:
        """Assign a provider based on color lane or step type."""
        if step.assigned_provider and step.assigned_provider in self.available_providers:
            return step.assigned_provider

        if step.assigned_color:
            # Find provider matching this color
            for pname, spec in PROVIDER_SPECTRUM.items():
                if spec["color"] == step.assigned_color and pname in self.available_providers:
                    return pname

        # Fallback: match step type to provider specialty
        type_to_specialty = {
            StepType.RESEARCH: "research",
            StepType.ARXIV: "research",
            StepType.DRAFT: "drafting",
            StepType.EDIT: "drafting",
            StepType.EXPAND: "drafting",
            StepType.SYNTHESIZE: "architecture",
            StepType.FACT_CHECK: "research",
            StepType.DEBATE: "debate",
            StepType.CLASSIFY: "embedding",
            StepType.TRANSFORM: "code",
        }
        needed_specialty = type_to_specialty.get(step.step_type, "architecture")
        for pname, spec in PROVIDER_SPECTRUM.items():
            if spec["specialty"] == needed_specialty and pname in self.available_providers:
                return pname

        # Ultimate fallback: first available
        return self.available_providers[0] if self.available_providers else "claude"

    def _allocate_color_channel(self, step: CanvasStep, provider: str) -> Optional[Any]:
        """Allocate a frequency-isolated color channel for this step."""
        if not HAS_COLOR_DIMENSION or not self.spectrum:
            return None
        band = None
        if provider in {
            "claude": ColorBand.VIOLET,
            "gpt": ColorBand.BLUE,
            "gemini": ColorBand.GREEN,
            "grok": ColorBand.ORANGE,
            "hf": ColorBand.RED,
            "local": ColorBand.CYAN,
        }:
            band = {
                "claude": ColorBand.VIOLET,
                "gpt": ColorBand.BLUE,
                "gemini": ColorBand.GREEN,
                "grok": ColorBand.ORANGE,
                "hf": ColorBand.RED,
                "local": ColorBand.CYAN,
            }.get(provider)
        tongue = "KO"
        # Map step complexity to tongue overtone
        if step.step_type in (StepType.GOVERNANCE, StepType.SYNTHESIZE):
            tongue = "UM"  # governance = higher overtone
        elif step.step_type in (StepType.DEBATE, StepType.FACT_CHECK):
            tongue = "RU"  # security/structure
        tags = set(step.tags) if step.tags else {step.step_type.value, provider}
        ch = self.spectrum.allocate(step.step_id, preferred_band=band, tongue=tongue, tags=tags)
        self.flow_channels[step.step_id] = ch
        return ch

    def _resolve_dependencies(self, step: CanvasStep) -> Dict[str, str]:
        """Gather outputs from dependency steps."""
        dep_outputs: Dict[str, str] = {}
        for dep_id in step.depends_on:
            if dep_id in self.results and self.results[dep_id].status == "done":
                dep_outputs[dep_id] = self.results[dep_id].output
        return dep_outputs

    def _execute_step_stub(self, step: CanvasStep, provider: str, dep_outputs: Dict[str, str]) -> StepResult:
        """Execute a step in stub mode (no actual LLM calls — simulates execution)."""
        t0 = time.time()
        color = PROVIDER_SPECTRUM.get(provider, {}).get("color", ModelColor.WHITE)
        color_val = color.value if isinstance(color, ModelColor) else str(color)

        # Simulate execution based on step type
        output = ""
        artifacts: Dict[str, Any] = {}

        if step.step_type == StepType.RESEARCH:
            output = f"[{provider}] Research findings for: {step.params.get('query', step.description)}\n"
            output += "- Finding 1: Key insight from web sources\n"
            output += "- Finding 2: Academic perspective\n"
            output += "- Finding 3: Industry application\n"
            artifacts["sources"] = 5
            artifacts["chars"] = 3000

        elif step.step_type == StepType.ARXIV:
            query = step.params.get("query", "")
            output = f"[{provider}] ArXiv scan: {query}\n"
            output += "- Paper 1: Relevant theoretical framework\n"
            output += "- Paper 2: Empirical validation study\n"
            artifacts["papers_found"] = step.params.get("max", 5)

        elif step.step_type in (StepType.DRAFT, StepType.EDIT, StepType.EXPAND):
            instruction = step.params.get("instruction", step.description)
            dep_context = "\n".join(f"[from {k}]: {v[:200]}..." for k, v in dep_outputs.items()) if dep_outputs else ""
            output = f"[{provider}] {step.step_type.value}: {instruction[:100]}...\n"
            if dep_context:
                output += f"Context from {len(dep_outputs)} upstream steps.\n"
            output += f"[Generated {step.step_type.value} content — {provider} {color_val} lane]\n"

        elif step.step_type == StepType.DEBATE:
            output = f"[{provider}] Debate/challenge:\n"
            output += "- Point of contention 1: Needs stronger evidence\n"
            output += "- Point of contention 2: Alternative interpretation\n"
            output += "- Agreement: Core thesis is sound\n"

        elif step.step_type == StepType.SYNTHESIZE:
            output = f"[{provider}] Synthesis from {len(dep_outputs)} inputs:\n"
            for dep_id, dep_out in dep_outputs.items():
                output += f"  Integrated [{dep_id}]: {dep_out[:80]}...\n"
            output += "[Coherent synthesis produced]\n"

        elif step.step_type == StepType.FACT_CHECK:
            output = f"[{provider}] Fact check results:\n"
            output += "- Claim 1: VERIFIED\n- Claim 2: VERIFIED\n- Claim 3: NEEDS SOURCE\n"

        elif step.step_type == StepType.GOVERNANCE:
            output = "Governance scan: ALLOW (risk_score=0.12)\n"
            artifacts["verdict"] = "ALLOW"
            artifacts["risk_score"] = 0.12

        elif step.step_type == StepType.CLASSIFY:
            output = f"[{provider}] Classification:\n"
            cats = step.params.get("categories", ["general"])
            for cat in cats:
                output += f"  {cat}: {hash(cat) % 30 + 1} items\n"

        elif step.step_type == StepType.PUBLISH:
            platform = step.params.get("platform", "unknown")
            output = f"Published to {platform} (dry-run)\n"
            artifacts["platform"] = platform
            artifacts["status"] = "dry_run"

        elif step.step_type == StepType.REMEMBER:
            key = step.params.get("key", step.step_id)
            output = f"Stored in HYDRA memory: {key}\n"

        elif step.step_type == StepType.TRANSFORM:
            output = f"[{provider}] Data transformed: {step.params.get('format', 'json')}\n"

        elif step.step_type == StepType.BROWSER_NAV:
            target = step.params.get("target", "arxiv")
            url = step.params.get("url", "")
            output = f"[browser] Navigate: {target} {url}\n"
            output += "  Script: scripts/system/browser_chain_dispatcher.py\n"
            artifacts["target"] = target
            artifacts["status"] = "navigated"

        elif step.step_type == StepType.OBSIDIAN_NOTE:
            vault = step.params.get("vault", "AI Workspace")
            title = step.params.get("title", step.description)
            output = f"[obsidian] Note created: {title}\n"
            output += f"  Vault: {vault}\n"
            output += "  Script: scripts/system/obsidian_byproduct_note.py\n"
            artifacts["vault"] = vault
            artifacts["title"] = title

        elif step.step_type == StepType.CROSS_TALK:
            recipient = step.params.get("recipient", "agent.codex")
            task_id = step.params.get("task_id", step.step_id)
            output = f"[cross-talk] Sent to {recipient}: {step.description}\n"
            output += f"  Task: {task_id}\n"
            artifacts["recipient"] = recipient
            artifacts["surfaces"] = 3

        elif step.step_type == StepType.ROUNDABOUT:
            # Quality checkpoint
            min_q = step.params.get("min_quality", 0.5)
            # Simulate quality evaluation
            quality = 0.75  # Simulated
            output = f"Roundabout checkpoint: quality={quality:.2f} (min={min_q})\n"
            artifacts["quality_score"] = quality
            artifacts["passed"] = quality >= min_q

        elif step.step_type == StepType.CANVAS_MERGE:
            output = "Canvas merge: all color outputs combined into knowledge canvas\n"

        elif step.step_type == StepType.WAIT:
            output = "Barrier: all dependencies satisfied\n"

        else:
            output = f"[{provider}] Custom step: {step.description}\n"

        duration_ms = (time.time() - t0) * 1000

        return StepResult(
            step_id=step.step_id,
            status="done",
            output=output,
            artifacts=artifacts,
            provider_used=provider,
            color=color_val,
            duration_ms=duration_ms,
        )

    def execute_recipe(
        self,
        steps: List[CanvasStep],
        topic: str = "",
        dry_run: bool = True,
    ) -> KnowledgeCanvas:
        """Execute a full recipe, respecting dependencies and backtracking."""
        self.results = {}
        self.roundabouts = {}
        self.canvas = KnowledgeCanvas(
            canvas_id=hashlib.md5(f"{topic}-{time.time()}".encode()).hexdigest()[:12],
            topic=topic,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

        # Build dependency graph
        executed: Set[str] = set()
        max_iterations = len(steps) * (self.max_retries + 1) * self.max_roundabout_visits
        iteration = 0

        while len(executed) < len(steps) and iteration < max_iterations:
            iteration += 1
            progress = False

            for step in steps:
                if step.step_id in executed:
                    continue

                # Check dependencies
                deps_met = all(d in executed for d in step.depends_on)
                if not deps_met:
                    continue

                # Assign provider
                provider = self._assign_provider(step)
                dep_outputs = self._resolve_dependencies(step)

                # Handle roundabouts
                if step.step_type == StepType.ROUNDABOUT:
                    rb_id = step.step_id
                    if rb_id not in self.roundabouts:
                        self.roundabouts[rb_id] = RoundaboutState(
                            checkpoint_id=rb_id,
                            step_id=step.step_id,
                            context_snapshot={k: v.output[:200] for k, v in self.results.items()},
                        )
                    rb = self.roundabouts[rb_id]
                    rb.visits += 1

                    if rb.visits > self.max_roundabout_visits:
                        # Force through
                        result = StepResult(
                            step_id=step.step_id,
                            status="done",
                            output=f"Roundabout {rb_id}: forced through after {rb.visits} visits\n",
                            provider_used="system",
                            color="white",
                        )
                    else:
                        result = self._execute_step_stub(step, provider, dep_outputs)
                        passed = result.artifacts.get("passed", True)
                        if not passed and step.backtrack_to and step.backtrack_to in executed:
                            # Backtrack: re-execute from backtrack target
                            result.output += f"BACKTRACKING to {step.backtrack_to}\n"
                            executed.discard(step.backtrack_to)
                            # Also invalidate steps that depend on backtrack target
                            for s in steps:
                                if step.backtrack_to in s.depends_on:
                                    executed.discard(s.step_id)
                            continue

                elif step.step_type == StepType.CANVAS_MERGE:
                    # Merge all results into canvas
                    for sid, sresult in self.results.items():
                        if sresult.output.strip() and sresult.color:
                            self.canvas.add_stroke(sresult.color, sresult.output, sid)
                    result = StepResult(
                        step_id=step.step_id,
                        status="done",
                        output=(
                            f"Canvas merged: {len(self.canvas.sections)} strokes"
                            f" from {len(self.canvas.colors_used)} colors\n"
                        ),
                        provider_used="system",
                        color="white",
                    )

                else:
                    # Normal execution
                    result = self._execute_step_stub(step, provider, dep_outputs)

                # Allocate color channel for frequency isolation tracking
                ch = self._allocate_color_channel(step, provider)
                if ch is not None:
                    result.artifacts["color_channel_nm"] = ch.wavelength_nm
                    result.artifacts["color_channel_hex"] = ch.hex_color()
                    result.artifacts["color_tongue"] = ch.tongue

                self.results[step.step_id] = result
                executed.add(step.step_id)
                progress = True

            if not progress:
                # Deadlock — break remaining steps
                for step in steps:
                    if step.step_id not in executed:
                        self.results[step.step_id] = StepResult(
                            step_id=step.step_id,
                            status="failed",
                            error="deadlock: unmet dependencies",
                        )
                        executed.add(step.step_id)
                break

        return self.canvas

    def summary(self) -> Dict[str, Any]:
        """Generate execution summary."""
        done = [r for r in self.results.values() if r.status == "done"]
        failed = [r for r in self.results.values() if r.status == "failed"]
        colors_used: Dict[str, int] = {}
        for r in done:
            c = r.color or "unassigned"
            colors_used[c] = colors_used.get(c, 0) + 1

        total_ms = sum(r.duration_ms for r in self.results.values())
        summary: Dict[str, Any] = {
            "total_steps": len(self.results),
            "completed": len(done),
            "failed": len(failed),
            "colors_used": colors_used,
            "roundabouts_triggered": sum(1 for r in self.roundabouts.values() if r.visits > 1),
            "total_duration_ms": round(total_ms, 1),
            "canvas_strokes": len(self.canvas.sections) if self.canvas else 0,
        }
        if self.spectrum:
            summary["spectrum_utilization"] = f"{self.spectrum.utilization():.0%}"
            summary["color_channels_allocated"] = len(self.flow_channels)
        return summary


# ---------------------------------------------------------------------------
#  CLI integration helpers
# ---------------------------------------------------------------------------


def list_recipes() -> List[Dict[str, Any]]:
    """List available canvas recipes."""
    recipes = []
    for name, builder in RECIPE_REGISTRY.items():
        steps = builder("example_topic")
        recipes.append(
            {
                "name": name,
                "steps": len(steps),
                "colors": list(
                    set(
                        PROVIDER_SPECTRUM.get(
                            next((p for p, s in PROVIDER_SPECTRUM.items() if s["color"] == st.assigned_color), ""), {}
                        )
                        .get("color", ModelColor.WHITE)
                        .value
                        for st in steps
                        if st.assigned_color
                    )
                ),
                "description": {
                    "article": (
                        "Full article pipeline (14 steps): research -> draft -> edit"
                        " -> expand -> fact-check -> publish"
                    ),
                    "research": "Deep multi-source research (8 steps): arxiv + web + debate + synthesis",
                    "content": (
                        "Multi-platform content (variable): write -> adapt per platform" " -> govern -> publish"
                    ),
                    "training": (
                        "Training data generation (7 steps): research -> generate pairs" " -> quality check -> export"
                    ),
                    "full_loop": "End-to-end loop: browser nav + research + writing + obsidian + cross-talk + publish",
                }.get(name, ""),
            }
        )
    return recipes


def run_recipe(
    recipe_name: str, topic: str, providers: Optional[List[str]] = None, max_steps: int = 0
) -> Dict[str, Any]:
    """Run a canvas recipe and return results."""
    builder = RECIPE_REGISTRY.get(recipe_name)
    if not builder:
        return {"error": f"Unknown recipe: {recipe_name}. Available: {list(RECIPE_REGISTRY.keys())}"}

    steps = builder(topic)
    if max_steps > 0:
        steps = steps[:max_steps]
    orchestrator = CanvasOrchestrator(available_providers=providers or ["claude"])
    canvas = orchestrator.execute_recipe(steps, topic=topic)

    return {
        "canvas_id": canvas.canvas_id,
        "topic": canvas.topic,
        "summary": orchestrator.summary(),
        "step_results": [
            {
                "step_id": r.step_id,
                "status": r.status,
                "provider": r.provider_used,
                "color": r.color,
                "output_preview": r.output[:200],
                "duration_ms": r.duration_ms,
            }
            for r in orchestrator.results.values()
        ],
        "canvas_render": canvas.render(),
        "colors_used": {k: len(v) for k, v in canvas.colors_used.items()},
    }


# ---------------------------------------------------------------------------
#  Demo
# ---------------------------------------------------------------------------


def _run_demo():
    print("=" * 70)
    print("  HYDRA Canvas — Multi-Step Orchestrated Workflows")
    print("=" * 70)
    print()

    # List recipes
    print("Available Recipes:")
    for r in list_recipes():
        print(f"  [{r['name']}] {r['steps']} steps | colors: {', '.join(r['colors'])} | {r['description'][:60]}")
    print()

    # Run article recipe
    print("-" * 70)
    print("Running: article recipe for 'signed Chladni mode addressing'")
    print("-" * 70)
    result = run_recipe("article", "signed Chladni mode addressing", providers=["claude", "gpt", "gemini", "grok"])

    print(f"\nCanvas ID: {result['canvas_id']}")
    print(f"Topic: {result['topic']}")
    summary = result["summary"]
    print(f"Steps: {summary['completed']}/{summary['total_steps']} completed, {summary['failed']} failed")
    print(f"Colors used: {summary['colors_used']}")
    print(f"Canvas strokes: {summary['canvas_strokes']}")
    print(f"Duration: {summary['total_duration_ms']:.1f}ms")
    print()

    print("Step execution order:")
    for sr in result["step_results"]:
        color_badge = f"[{sr['color']:6s}]" if sr["color"] else "[      ]"
        provider = f"({sr['provider']})" if sr["provider"] else ""
        print(f"  {sr['status']:4s} {color_badge} {sr['step_id']:25s} {provider}")
    print()

    # Show canvas render (first 40 lines)
    print("-" * 70)
    print("KNOWLEDGE CANVAS (preview)")
    print("-" * 70)
    for line in result["canvas_render"].splitlines()[:40]:
        print(f"  {line}")
    print("  ...")
    print()

    # Run research recipe
    print("-" * 70)
    result2 = run_recipe("research", "hyperbolic geometry AI safety", providers=["claude", "gpt", "grok"])
    print(
        f"Research canvas: {result2['summary']['completed']}/{result2['summary']['total_steps']} steps, "
        f"{result2['summary']['canvas_strokes']} strokes"
    )
    print(f"Colors: {result2['colors_used']}")


if __name__ == "__main__":
    _run_demo()
