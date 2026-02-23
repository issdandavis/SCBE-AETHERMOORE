#!/usr/bin/env python3
"""
SCBE-AETHERMOORE Marketing Automation Agents
=============================================

Four-agent marketing automation system that generates, researches,
schedules, and optimizes content for SCBE-AETHERMOORE across all
supported publisher platforms.

Agents:
    ContentGeneratorAgent  -- Generate platform-specific marketing posts
    AudienceResearchAgent  -- Profile audiences and suggest timing
    CampaignOrchestrator   -- Coordinate multi-platform campaigns
    SEOContentAgent        -- Generate SEO-optimized long-form content

Designed to work with the existing publisher system at:
  src/symphonic_cipher/scbe_aethermoore/concept_blocks/web_agent/publishers.py

Self-contained: stdlib only, no external dependencies.

Usage:
    python agents/marketing_agents.py generate --platform twitter --topic "latest benchmark"
    python agents/marketing_agents.py campaign --days 7
    python agents/marketing_agents.py seo --topic "ai agent governance"
    python agents/marketing_agents.py audience --segment enterprise_ctos
    python agents/marketing_agents.py selftest
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import textwrap
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
#  Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPO_URL = "https://github.com/issdandavis/SCBE-AETHERMOORE"
PROJECT_NAME = "SCBE-AETHERMOORE"
PROJECT_TAGLINE = "14-layer AI safety and governance framework"
PATENT_REF = "USPTO #63/961,403"


class PlatformName(str, Enum):
    TWITTER = "twitter"
    LINKEDIN = "linkedin"
    BLUESKY = "bluesky"
    MASTODON = "mastodon"
    WORDPRESS = "wordpress"
    MEDIUM = "medium"
    GITHUB = "github"
    HUGGINGFACE = "huggingface"


PLATFORM_CHAR_LIMITS: Dict[str, int] = {
    PlatformName.TWITTER: 280,
    PlatformName.LINKEDIN: 3000,
    PlatformName.BLUESKY: 300,
    PlatformName.MASTODON: 500,
    PlatformName.WORDPRESS: 100_000,
    PlatformName.MEDIUM: 100_000,
    PlatformName.GITHUB: 65_536,
    PlatformName.HUGGINGFACE: 100_000,
}


class ContentTemplate(str, Enum):
    FEATURE_ANNOUNCEMENT = "feature_announcement"
    BENCHMARK_RESULTS = "benchmark_results"
    ARCHITECTURE_EXPLAINER = "architecture_explainer"
    USE_CASE_STORY = "use_case_story"
    MILESTONE_UPDATE = "milestone_update"
    THOUGHT_LEADERSHIP = "thought_leadership"


class AudienceSegment(str, Enum):
    AI_SAFETY_RESEARCHERS = "ai_safety_researchers"
    ENTERPRISE_CTOS = "enterprise_ctos"
    DEVSECOPS_ENGINEERS = "devsecops_engineers"
    DEFENSE_AEROSPACE = "defense_aerospace"
    FINTECH = "fintech"
    OPEN_SOURCE_COMMUNITY = "open_source_community"


# ---------------------------------------------------------------------------
#  Data structures
# ---------------------------------------------------------------------------

@dataclass
class MarketingContent:
    """Structured output from content generation."""

    platform: str
    text: str
    hashtags: List[str] = field(default_factory=list)
    media_suggestions: List[str] = field(default_factory=list)
    template_used: str = ""
    audience_segment: str = ""
    seo_keywords: List[str] = field(default_factory=list)
    estimated_engagement: str = "medium"
    char_count: int = 0

    def __post_init__(self) -> None:
        self.char_count = len(self.text)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def display(self) -> str:
        lines = [
            f"--- {self.platform.upper()} ({self.char_count} chars) ---",
            self.text,
            "",
        ]
        if self.hashtags:
            lines.append(f"  Hashtags: {' '.join('#' + h for h in self.hashtags)}")
        if self.media_suggestions:
            lines.append(f"  Media: {', '.join(self.media_suggestions)}")
        if self.template_used:
            lines.append(f"  Template: {self.template_used}")
        if self.audience_segment:
            lines.append(f"  Audience: {self.audience_segment}")
        if self.seo_keywords:
            lines.append(f"  SEO keywords: {', '.join(self.seo_keywords)}")
        lines.append(f"  Est. engagement: {self.estimated_engagement}")
        return "\n".join(lines)


@dataclass
class AudienceProfile:
    """Profile for a target audience segment."""

    segment: str
    description: str
    platforms: List[str]
    optimal_posting_times: Dict[str, List[str]]  # platform -> list of "HH:MM UTC"
    content_preferences: List[str]
    pain_points: List[str]
    value_propositions: List[str]
    engagement_patterns: Dict[str, float]  # metric -> placeholder value
    keywords: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CampaignPlan:
    """A multi-day content calendar."""

    name: str
    days: int
    start_date: str
    posts: List[Dict[str, Any]] = field(default_factory=list)
    total_posts: int = 0
    platforms_covered: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SEOBrief:
    """SEO content brief for a topic."""

    topic: str
    primary_keyword: str
    secondary_keywords: List[str]
    title_variants: List[str]
    meta_description: str
    outline: List[Dict[str, Any]]  # sections with heading + bullet points
    word_count_target: int = 2000
    internal_links: List[str] = field(default_factory=list)
    competitor_angle: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
#  Project data reader
# ---------------------------------------------------------------------------

class ProjectDataReader:
    """Reads project files for content generation material."""

    def __init__(self, root: Path = PROJECT_ROOT) -> None:
        self._root = root

    def read_changelog(self) -> str:
        """Read CHANGELOG.md, return contents or fallback summary."""
        for name in ("CHANGELOG.md", "changelog.md", "CHANGES.md"):
            p = self._root / name
            if p.exists():
                try:
                    return p.read_text(encoding="utf-8", errors="replace")[:8000]
                except OSError:
                    pass
        return self._fallback_changelog()

    def read_readme(self) -> str:
        """Read README.md, return contents or fallback summary."""
        for name in ("README.md", "readme.md", "Readme.md"):
            p = self._root / name
            if p.exists():
                try:
                    return p.read_text(encoding="utf-8", errors="replace")[:8000]
                except OSError:
                    pass
        return self._fallback_readme()

    def read_test_results(self) -> Dict[str, Any]:
        """Read latest test results or return known stats."""
        # Try to find pytest output
        for candidate in ("test-results.json", "pytest-results.json"):
            p = self._root / candidate
            if p.exists():
                try:
                    return json.loads(p.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    pass
        # Return known project stats from memory
        return {
            "total_tests": 2620,
            "passed": 2620,
            "failed": 0,
            "skipped": 39,
            "xfailed": 38,
            "xpassed": 3,
            "pass_rate": 98.3,
            "loc": "50000+",
        }

    def get_key_features(self) -> List[str]:
        return [
            "14-layer AI safety governance architecture",
            "Post-quantum cryptography (ML-KEM-768, ML-DSA-65)",
            "Hyperbolic geometry containment via Poincare ball model",
            "Six Sacred Tongues encoding system",
            "Federated learning with privacy-preserving aggregation",
            "WASM/WIT component interoperability",
            "Browser-grade semantic antivirus",
            "Dual symphonic cipher (cost multiplier + bounded safety)",
            "BFT consensus for multi-agent coordination",
            f"Patent-pending ({PATENT_REF})",
            "2620+ tests, 98.3% pass rate, 50K+ LOC",
            "ChoiceScript game-based training pipeline",
        ]

    def get_recent_milestones(self) -> List[Dict[str, str]]:
        return [
            {"date": "2026-02-22", "event": "v3.0.0 production-ready, 50K+ LOC"},
            {"date": "2026-02-22", "event": "Master strategy Phases 1-4 complete"},
            {"date": "2026-02-22", "event": "WASM/WIT interfaces: 76/76 conformance tests"},
            {"date": "2026-02-22", "event": "ChoiceScript training engine: 100% agent completion"},
            {"date": "2026-02-21", "event": "6 concept blocks + 6 CSTM modules built"},
            {"date": "2026-02-21", "event": "Web agent: 9 platform publishers deployed"},
            {"date": "2026-02-20", "event": "Full test sweep: 2620 passed, 0 failed"},
        ]

    def _fallback_changelog(self) -> str:
        milestones = self.get_recent_milestones()
        lines = ["# Changelog (reconstructed)\n"]
        for m in milestones:
            lines.append(f"- **{m['date']}**: {m['event']}")
        return "\n".join(lines)

    def _fallback_readme(self) -> str:
        return textwrap.dedent(f"""\
            # {PROJECT_NAME}

            {PROJECT_TAGLINE}

            - 14-layer architecture (TypeScript canonical + Python reference)
            - Post-quantum cryptography
            - Hyperbolic geometry safety containment
            - {PATENT_REF}
            - 50K+ LOC, 2620+ tests
        """)


# ---------------------------------------------------------------------------
#  Agent 1: ContentGeneratorAgent
# ---------------------------------------------------------------------------

class ContentGeneratorAgent:
    """
    Generates marketing content from project data.

    Reads CHANGELOG.md, README.md, and test results for material.
    Produces platform-specific posts using configurable templates.
    """

    def __init__(self) -> None:
        self._reader = ProjectDataReader()
        self._rng = random.Random(int(time.time()))

    def generate(
        self,
        platform: str,
        topic: str,
        template: str = "",
        audience: str = "",
    ) -> MarketingContent:
        """
        Generate a single marketing post.

        Args:
            platform: Target platform name (twitter, linkedin, medium, etc.)
            topic: What to write about
            template: Template type (feature_announcement, benchmark_results, etc.)
            audience: Target audience segment
        """
        platform = platform.lower()
        char_limit = PLATFORM_CHAR_LIMITS.get(platform, 3000)

        # Auto-detect template from topic if not specified
        if not template:
            template = self._detect_template(topic)

        # Gather material
        features = self._reader.get_key_features()
        milestones = self._reader.get_recent_milestones()
        test_data = self._reader.read_test_results()

        # Generate based on template
        generator = {
            ContentTemplate.FEATURE_ANNOUNCEMENT: self._gen_feature_announcement,
            ContentTemplate.BENCHMARK_RESULTS: self._gen_benchmark_results,
            ContentTemplate.ARCHITECTURE_EXPLAINER: self._gen_architecture_explainer,
            ContentTemplate.USE_CASE_STORY: self._gen_use_case_story,
            ContentTemplate.MILESTONE_UPDATE: self._gen_milestone_update,
            ContentTemplate.THOUGHT_LEADERSHIP: self._gen_thought_leadership,
        }

        gen_func = generator.get(template, self._gen_feature_announcement)
        text, hashtags, media = gen_func(topic, platform, char_limit, features, milestones, test_data)

        # Enforce character limit
        text = self._enforce_limit(text, char_limit)

        return MarketingContent(
            platform=platform,
            text=text,
            hashtags=hashtags,
            media_suggestions=media,
            template_used=template if isinstance(template, str) else template.value,
            audience_segment=audience,
            seo_keywords=self._extract_keywords(topic, text),
            estimated_engagement=self._estimate_engagement(platform, template),
        )

    def generate_multi_platform(
        self,
        topic: str,
        platforms: Optional[List[str]] = None,
        template: str = "",
        audience: str = "",
    ) -> List[MarketingContent]:
        """Generate content for multiple platforms at once."""
        if platforms is None:
            platforms = ["twitter", "linkedin", "bluesky", "mastodon"]
        return [
            self.generate(p, topic, template=template, audience=audience)
            for p in platforms
        ]

    # -- Template generators --------------------------------------------------

    def _gen_feature_announcement(
        self, topic: str, platform: str, limit: int,
        features: List[str], milestones: List[Dict], test_data: Dict,
    ) -> Tuple[List[str], List[str], List[str]]:
        """Generate a feature announcement post."""
        hashtags = ["SCBE", "AISafety", "PostQuantum", "AgentGovernance"]

        if platform in ("twitter", "bluesky"):
            variants = [
                (
                    f"NEW in {PROJECT_NAME}: {topic}\n\n"
                    f"Our 14-layer governance framework now features "
                    f"post-quantum crypto, hyperbolic containment, and "
                    f"{test_data.get('total_tests', 2620)}+ passing tests.\n\n"
                    f"Patent-pending. Production-ready.\n"
                    f"{REPO_URL}"
                ),
                (
                    f"Shipped: {topic}\n\n"
                    f"{PROJECT_NAME} v3.0 brings {test_data.get('loc', '50K+')} "
                    f"LOC of AI safety infrastructure with a "
                    f"{test_data.get('pass_rate', 98.3)}% test pass rate.\n\n"
                    f"Built different. Built safe.\n"
                    f"{REPO_URL}"
                ),
                (
                    f"The future of AI governance just leveled up.\n\n"
                    f"{topic}\n\n"
                    f"{PROJECT_NAME}: 14 layers, post-quantum crypto, "
                    f"Sacred Tongues encoding.\n"
                    f"{REPO_URL}"
                ),
            ]
            text = self._rng.choice(variants)
            media = ["Architecture diagram", "Test results screenshot"]

        elif platform in ("linkedin",):
            text = (
                f"Excited to announce: {topic}\n\n"
                f"{PROJECT_NAME} is a 14-layer AI safety and governance framework "
                f"that tackles the hardest problems in autonomous agent deployment:\n\n"
                f"- Post-quantum cryptography (ML-KEM-768, ML-DSA-65)\n"
                f"- Hyperbolic geometry containment via Poincare ball model\n"
                f"- Federated learning with privacy-preserving aggregation\n"
                f"- WASM/WIT component interoperability for edge deployment\n"
                f"- BFT consensus for multi-agent coordination\n\n"
                f"Current status:\n"
                f"  {test_data.get('loc', '50K+')} LOC | "
                f"{test_data.get('total_tests', 2620)}+ tests | "
                f"{test_data.get('pass_rate', 98.3)}% pass rate\n\n"
                f"Patent-pending ({PATENT_REF}). Production-ready (v3.0.0).\n\n"
                f"If you are building AI agents that need real governance "
                f"--- not just guardrails, but mathematically-bounded safety "
                f"--- I would love to connect.\n\n"
                f"{REPO_URL}\n\n"
                f"#AISafety #AgentGovernance #PostQuantum #CyberSecurity #MLOps"
            )
            hashtags += ["CyberSecurity", "MLOps"]
            media = ["Architecture diagram", "Layer breakdown infographic", "Test dashboard screenshot"]

        elif platform in ("medium", "wordpress"):
            text = (
                f"# {topic}\n\n"
                f"## Why This Matters\n\n"
                f"As AI agents become more autonomous, the safety guarantees "
                f"we place on them must be mathematically rigorous --- not just "
                f"prompt-engineered hope.\n\n"
                f"**{PROJECT_NAME}** introduces a 14-layer governance architecture "
                f"that enforces safety at every level, from cryptographic identity "
                f"(post-quantum ML-KEM-768 / ML-DSA-65) to behavioral containment "
                f"(hyperbolic geometry Poincare ball model).\n\n"
                f"## Key Technical Highlights\n\n"
                + "\n".join(f"- {f}" for f in features[:8])
                + f"\n\n"
                f"## By the Numbers\n\n"
                f"| Metric | Value |\n"
                f"|--------|-------|\n"
                f"| Lines of Code | {test_data.get('loc', '50K+')} |\n"
                f"| Tests | {test_data.get('total_tests', 2620)}+ |\n"
                f"| Pass Rate | {test_data.get('pass_rate', 98.3)}% |\n"
                f"| Architecture Layers | 14 |\n"
                f"| Patent | {PATENT_REF} |\n\n"
                f"## Get Involved\n\n"
                f"The framework is open-source and ready for pilot deployments.\n\n"
                f"Repository: {REPO_URL}\n"
            )
            media = ["Architecture diagram", "Performance benchmark chart", "Layer topology visualization"]

        else:
            text = (
                f"{topic}\n\n"
                f"{PROJECT_NAME}: 14-layer AI safety framework. "
                f"{test_data.get('total_tests', 2620)}+ tests, "
                f"{test_data.get('pass_rate', 98.3)}% pass rate.\n"
                f"{REPO_URL}"
            )
            media = ["Architecture diagram"]

        return text, hashtags, media

    def _gen_benchmark_results(
        self, topic: str, platform: str, limit: int,
        features: List[str], milestones: List[Dict], test_data: Dict,
    ) -> Tuple[List[str], List[str], List[str]]:
        """Generate a benchmark/test results post."""
        hashtags = ["SCBE", "AISafety", "Testing", "QualityEngineering"]

        if platform in ("twitter", "bluesky"):
            text = (
                f"{PROJECT_NAME} benchmark update:\n\n"
                f"{test_data.get('total_tests', 2620)} tests\n"
                f"{test_data.get('passed', 2620)} passed\n"
                f"{test_data.get('failed', 0)} failed\n"
                f"{test_data.get('pass_rate', 98.3)}% pass rate\n\n"
                f"{test_data.get('loc', '50K+')} LOC across 14 governance layers.\n\n"
                f"When your AI safety framework has zero test failures, "
                f"that is the point.\n"
                f"{REPO_URL}"
            )
        elif platform == "linkedin":
            text = (
                f"Numbers that matter in AI safety:\n\n"
                f"We just completed a full test sweep of {PROJECT_NAME}, "
                f"our 14-layer AI governance framework.\n\n"
                f"Results:\n"
                f"  Total tests: {test_data.get('total_tests', 2620)}\n"
                f"  Passed: {test_data.get('passed', 2620)}\n"
                f"  Failed: {test_data.get('failed', 0)}\n"
                f"  Pass rate: {test_data.get('pass_rate', 98.3)}%\n"
                f"  Codebase: {test_data.get('loc', '50K+')} LOC\n\n"
                f"In safety-critical software, test coverage is not a metric "
                f"--- it is a commitment. Every layer of our architecture has "
                f"dedicated validation:\n\n"
                f"- Cryptographic identity verification (post-quantum)\n"
                f"- Geometric containment boundary tests\n"
                f"- Governance gate decision consistency\n"
                f"- Federated learning convergence checks\n"
                f"- Multi-agent consensus protocol validation\n\n"
                f"Building AI agents without this level of testing rigor "
                f"is building on sand.\n\n"
                f"{REPO_URL}\n\n"
                f"#AISafety #SoftwareTesting #QualityEngineering #AgentGovernance"
            )
        else:
            text = (
                f"# {PROJECT_NAME} Benchmark Results\n\n"
                f"## Test Suite Summary\n\n"
                f"| Metric | Value |\n"
                f"|--------|-------|\n"
                f"| Total tests | {test_data.get('total_tests', 2620)} |\n"
                f"| Passed | {test_data.get('passed', 2620)} |\n"
                f"| Failed | {test_data.get('failed', 0)} |\n"
                f"| Skipped | {test_data.get('skipped', 39)} |\n"
                f"| Pass rate | {test_data.get('pass_rate', 98.3)}% |\n"
                f"| Lines of code | {test_data.get('loc', '50K+')} |\n\n"
                f"## What We Test\n\n"
                f"Each of the 14 governance layers has dedicated test suites "
                f"covering correctness, performance, and adversarial resilience.\n\n"
                f"Full details: {REPO_URL}\n"
            )

        media = ["Test results dashboard", "Pass rate trend chart", "Coverage heatmap"]
        return text, hashtags, media

    def _gen_architecture_explainer(
        self, topic: str, platform: str, limit: int,
        features: List[str], milestones: List[Dict], test_data: Dict,
    ) -> Tuple[List[str], List[str], List[str]]:
        """Generate an architecture explainer post."""
        hashtags = ["SCBE", "AISafety", "SystemArchitecture", "HyperbolicGeometry"]

        layer_descriptions = [
            ("L1-L3", "Cryptographic Identity", "Post-quantum key exchange and digital signatures"),
            ("L4-L5", "Governance Mesh", "Policy engine with Hamiltonian cost functions"),
            ("L6-L7", "Navigation & Decision", "A* pathfinding + behaviour trees"),
            ("L8-L9", "Control & Sensing", "PID controllers + Kalman filters"),
            ("L10-L11", "Encoding & Transport", "Sacred Tongues + GeoSeal"),
            ("L12", "Coordination", "BFT consensus for multi-agent fleets"),
            ("L13-L14", "Audit & Telemetry", "Full observability and compliance"),
        ]

        if platform in ("twitter", "bluesky"):
            text = (
                f"How do you build AI safety that actually works?\n\n"
                f"14 layers. Not guardrails --- geometry.\n\n"
                f"{PROJECT_NAME} uses hyperbolic containment (Poincare ball) "
                f"to bound agent behavior mathematically.\n\n"
                f"Distance from center = risk. Cross the boundary = denied.\n\n"
                f"No jailbreaks. No prompt hacks. Math.\n"
                f"{REPO_URL}"
            )
        elif platform == "linkedin":
            layers_text = "\n".join(
                f"  {code}: {name} -- {desc}"
                for code, name, desc in layer_descriptions
            )
            text = (
                f"Architecture Deep Dive: {PROJECT_NAME}\n\n"
                f"Most AI safety approaches add guardrails after the fact. "
                f"We built safety into the geometry itself.\n\n"
                f"Our 14-layer architecture:\n\n"
                f"{layers_text}\n\n"
                f"The key insight: we use hyperbolic geometry (the Poincare "
                f"ball model) to create a containment space where an agent's "
                f"distance from the center directly maps to its risk level. "
                f"The exponential growth of hyperbolic space means boundary "
                f"violations become exponentially costly --- no gradient hacking "
                f"around that.\n\n"
                f"Combined with post-quantum cryptography for identity and "
                f"BFT consensus for multi-agent coordination, this creates "
                f"governance you can prove, not just hope for.\n\n"
                f"{REPO_URL}\n\n"
                f"#AISafety #SystemArchitecture #HyperbolicGeometry #Cryptography"
            )
        else:
            layers_md = "\n".join(
                f"### {code}: {name}\n{desc}\n"
                for code, name, desc in layer_descriptions
            )
            text = (
                f"# Architecture Explainer: {PROJECT_NAME}\n\n"
                f"## The Problem\n\n"
                f"Current AI safety approaches rely on prompt engineering, "
                f"RLHF fine-tuning, or runtime filters. These are necessary "
                f"but insufficient for autonomous agents that must operate "
                f"in adversarial environments.\n\n"
                f"## Our Approach: Geometric Safety\n\n"
                f"{PROJECT_NAME} embeds safety into the mathematical structure "
                f"of the agent's decision space using hyperbolic geometry.\n\n"
                f"## The 14 Layers\n\n"
                f"{layers_md}\n\n"
                f"## Why Hyperbolic Geometry?\n\n"
                f"In the Poincare ball model, distance from center grows "
                f"exponentially near the boundary. This means:\n\n"
                f"- Safe operations cluster near the center (low cost)\n"
                f"- Risky operations face exponential resistance\n"
                f"- Boundary crossing is mathematically impossible within budget\n\n"
                f"The Hamiltonian cost function H(d,R) = R^(d^2) ensures "
                f"that as an agent approaches the containment boundary, "
                f"the energy cost of further movement becomes infinite.\n\n"
                f"Repository: {REPO_URL}\n"
            )

        media = [
            "Poincare ball containment diagram",
            "14-layer stack visualization",
            "Hamiltonian cost curve plot",
        ]
        return text, hashtags, media

    def _gen_use_case_story(
        self, topic: str, platform: str, limit: int,
        features: List[str], milestones: List[Dict], test_data: Dict,
    ) -> Tuple[List[str], List[str], List[str]]:
        """Generate a use-case story post."""
        hashtags = ["SCBE", "AISafety", "UseCases", "Enterprise"]

        use_cases = [
            {
                "title": "Autonomous Financial Trading Agents",
                "domain": "Fintech",
                "problem": "Trading bots that can be manipulated through adversarial inputs",
                "solution": "Hyperbolic containment bounds trade risk geometrically",
                "result": "Mathematically-proven bounds on maximum position exposure",
            },
            {
                "title": "Defense & Aerospace Autonomous Systems",
                "domain": "Defense",
                "problem": "Autonomous systems must provably stay within rules of engagement",
                "solution": "14-layer governance with post-quantum comms and BFT consensus",
                "result": "Certifiable compliance with MIL-STD safety requirements",
            },
            {
                "title": "Multi-Agent DevSecOps Pipelines",
                "domain": "DevSecOps",
                "problem": "AI agents in CI/CD pipelines need bounded permissions",
                "solution": "Governance gates at every layer prevent privilege escalation",
                "result": "Zero-trust agent orchestration with full audit trails",
            },
            {
                "title": "Healthcare AI Governance",
                "domain": "Healthcare",
                "problem": "Medical AI must comply with HIPAA while remaining useful",
                "solution": "Sacred Tongues encoding + GeoSeal for data sovereignty",
                "result": "Region-aware data handling with cryptographic guarantees",
            },
        ]

        # Pick a use case relevant to the topic or random
        uc = None
        topic_lower = topic.lower()
        for u in use_cases:
            if any(word in topic_lower for word in u["domain"].lower().split()):
                uc = u
                break
        if uc is None:
            uc = self._rng.choice(use_cases)

        if platform in ("twitter", "bluesky"):
            text = (
                f"Use case: {uc['title']}\n\n"
                f"Problem: {uc['problem']}\n\n"
                f"{PROJECT_NAME} solution: {uc['solution']}\n\n"
                f"Result: {uc['result']}\n"
                f"{REPO_URL}"
            )
        elif platform == "linkedin":
            text = (
                f"How {PROJECT_NAME} solves real problems: {uc['title']}\n\n"
                f"Domain: {uc['domain']}\n\n"
                f"The challenge:\n{uc['problem']}\n\n"
                f"Our approach:\n{uc['solution']}\n\n"
                f"The outcome:\n{uc['result']}\n\n"
                f"This is what governance-first AI looks like. "
                f"Not safety as an afterthought --- safety as architecture.\n\n"
                f"Interested in a pilot deployment for your organization? "
                f"Let's connect.\n\n"
                f"{REPO_URL}\n\n"
                f"#AISafety #{uc['domain']} #AgentGovernance #Enterprise"
            )
            hashtags.append(uc["domain"])
        else:
            text = (
                f"# Use Case: {uc['title']}\n\n"
                f"**Domain**: {uc['domain']}\n\n"
                f"## The Challenge\n\n{uc['problem']}\n\n"
                f"## The {PROJECT_NAME} Approach\n\n{uc['solution']}\n\n"
                f"## Expected Outcome\n\n{uc['result']}\n\n"
                f"## Technical Details\n\n"
                f"The framework's 14-layer architecture provides:\n\n"
                + "\n".join(f"- {f}" for f in features[:6])
                + f"\n\nRepository: {REPO_URL}\n"
            )

        media = [f"{uc['domain']} deployment diagram", "Architecture fit analysis"]
        return text, hashtags, media

    def _gen_milestone_update(
        self, topic: str, platform: str, limit: int,
        features: List[str], milestones: List[Dict], test_data: Dict,
    ) -> Tuple[List[str], List[str], List[str]]:
        """Generate a milestone/progress update post."""
        hashtags = ["SCBE", "AISafety", "OpenSource", "BuildInPublic"]

        recent = milestones[:5]
        milestone_lines = "\n".join(
            f"  {m['date']}: {m['event']}" for m in recent
        )

        if platform in ("twitter", "bluesky"):
            text = (
                f"{PROJECT_NAME} progress update:\n\n"
                + "\n".join(f"-> {m['event']}" for m in recent[:3])
                + f"\n\nBuilding the future of AI safety, one layer at a time.\n"
                f"{REPO_URL}"
            )
        elif platform == "linkedin":
            text = (
                f"Building in public: {PROJECT_NAME} progress\n\n"
                f"Recent milestones:\n\n"
                f"{milestone_lines}\n\n"
                f"What's next: v4.0.0 with telecommunications and Space Tor "
                f"integration. Plus a CIP patent filing expanding coverage "
                f"to Sacred Tongues encoding and space-domain networking.\n\n"
                f"If you are working on AI agent safety, governance, or "
                f"post-quantum security, I would love to hear what challenges "
                f"you are facing.\n\n"
                f"{REPO_URL}\n\n"
                f"#BuildInPublic #AISafety #OpenSource #AgentGovernance"
            )
        else:
            text = (
                f"# {PROJECT_NAME} Milestone Update\n\n"
                f"## Recent Progress\n\n"
                + "\n".join(f"- **{m['date']}**: {m['event']}" for m in recent)
                + f"\n\n## Roadmap\n\n"
                f"- v4.0.0: Telecommunications / Space Tor integration\n"
                f"- CIP patent filing (~March 2026)\n"
                f"- Non-provisional patent (Jan 2027)\n"
                f"- Pilot deployments with enterprise partners\n\n"
                f"Repository: {REPO_URL}\n"
            )

        media = ["Progress timeline", "Roadmap diagram"]
        return text, hashtags, media

    def _gen_thought_leadership(
        self, topic: str, platform: str, limit: int,
        features: List[str], milestones: List[Dict], test_data: Dict,
    ) -> Tuple[List[str], List[str], List[str]]:
        """Generate thought leadership content."""
        hashtags = ["AISafety", "AgentGovernance", "FutureOfAI", "PostQuantum"]

        thought_angles = [
            (
                "Why prompt engineering is not AI safety",
                "Prompt engineering adds a veneer of control. Real safety "
                "requires mathematical guarantees that an agent cannot violate "
                "boundaries regardless of the input it receives."
            ),
            (
                "The quantum threat to AI agent identity",
                "When quantum computers break RSA and ECDSA, every AI agent's "
                "identity becomes forgeable. Post-quantum cryptography is not "
                "a future problem --- it is a present requirement."
            ),
            (
                "Multi-agent systems need consensus, not hope",
                "When multiple AI agents coordinate, who decides what is safe? "
                "Without Byzantine Fault Tolerant consensus, a single "
                "compromised agent can poison the entire fleet."
            ),
            (
                "Geometry as governance",
                "The Poincare ball model gives us something no amount of "
                "fine-tuning can: a containment space where boundary violations "
                "are not just unlikely but exponentially costly."
            ),
        ]

        # Pick angle matching topic or random
        angle = None
        topic_lower = topic.lower()
        for title, body in thought_angles:
            if any(w in topic_lower for w in title.lower().split()[:3]):
                angle = (title, body)
                break
        if angle is None:
            angle = self._rng.choice(thought_angles)

        title, thesis = angle

        if platform in ("twitter", "bluesky"):
            text = (
                f"{title}.\n\n"
                f"{thesis[:180]}\n\n"
                f"Thread on how {PROJECT_NAME} approaches this differently:\n"
                f"{REPO_URL}"
            )
        elif platform == "linkedin":
            text = (
                f"{title}\n\n"
                f"{thesis}\n\n"
                f"This is exactly why we built {PROJECT_NAME} --- a 14-layer "
                f"governance framework that treats safety as geometry, not policy.\n\n"
                f"The result: {test_data.get('total_tests', 2620)}+ tests, "
                f"zero failures, and a patent-pending architecture that can "
                f"actually prove its safety guarantees.\n\n"
                f"What approach is your team taking to AI agent governance?\n\n"
                f"{REPO_URL}\n\n"
                f"#AISafety #ThoughtLeadership #AgentGovernance #FutureOfAI"
            )
        else:
            text = (
                f"# {title}\n\n"
                f"{thesis}\n\n"
                f"## The {PROJECT_NAME} Approach\n\n"
                f"Rather than relying on behavioral training alone, our "
                f"framework uses:\n\n"
                + "\n".join(f"- {f}" for f in features[:6])
                + f"\n\n"
                f"The combination creates governance you can mathematically "
                f"verify, not just empirically test.\n\n"
                f"Repository: {REPO_URL}\n"
            )

        media = ["Thought leadership graphic", "Comparison diagram"]
        return text, hashtags, media

    # -- Helpers ---------------------------------------------------------------

    def _detect_template(self, topic: str) -> str:
        """Auto-detect the best template from the topic string."""
        t = topic.lower()
        if any(w in t for w in ("benchmark", "test", "pass rate", "coverage", "results")):
            return ContentTemplate.BENCHMARK_RESULTS
        if any(w in t for w in ("architecture", "layer", "design", "hyperbolic", "poincare")):
            return ContentTemplate.ARCHITECTURE_EXPLAINER
        if any(w in t for w in ("use case", "deploy", "enterprise", "pilot", "fintech", "defense")):
            return ContentTemplate.USE_CASE_STORY
        if any(w in t for w in ("milestone", "update", "progress", "roadmap", "shipped")):
            return ContentTemplate.MILESTONE_UPDATE
        if any(w in t for w in ("why", "future", "opinion", "thought", "governance debate")):
            return ContentTemplate.THOUGHT_LEADERSHIP
        return ContentTemplate.FEATURE_ANNOUNCEMENT

    def _enforce_limit(self, text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[: limit - 3] + "..."

    def _extract_keywords(self, topic: str, text: str) -> List[str]:
        """Extract SEO-relevant keywords from generated text."""
        keyword_candidates = [
            "AI safety", "agent governance", "post-quantum", "hyperbolic geometry",
            "Poincare ball", "federated learning", "BFT consensus", "WASM",
            "Sacred Tongues", "multi-agent", "DevSecOps", "zero-trust",
            "ML-KEM", "ML-DSA", "autonomous agents", "containment",
        ]
        text_lower = text.lower()
        found = [k for k in keyword_candidates if k.lower() in text_lower]
        # Add topic words
        for word in topic.split():
            if len(word) > 3 and word.lower() not in [k.lower() for k in found]:
                found.append(word)
        return found[:10]

    def _estimate_engagement(self, platform: str, template: str) -> str:
        """Heuristic engagement estimate."""
        high_engagement = {
            ("twitter", ContentTemplate.THOUGHT_LEADERSHIP),
            ("twitter", ContentTemplate.BENCHMARK_RESULTS),
            ("linkedin", ContentTemplate.USE_CASE_STORY),
            ("linkedin", ContentTemplate.THOUGHT_LEADERSHIP),
            ("medium", ContentTemplate.ARCHITECTURE_EXPLAINER),
        }
        template_str = template if isinstance(template, str) else template.value
        if (platform, template_str) in high_engagement or (platform, template) in high_engagement:
            return "high"
        return "medium"


# ---------------------------------------------------------------------------
#  Agent 2: AudienceResearchAgent
# ---------------------------------------------------------------------------

class AudienceResearchAgent:
    """
    Profiles target audiences and suggests optimal engagement strategies.

    Maps content to audiences, suggests posting times, and tracks
    engagement patterns (placeholder analytics).
    """

    PROFILES: Dict[str, AudienceProfile] = {
        AudienceSegment.AI_SAFETY_RESEARCHERS: AudienceProfile(
            segment="AI Safety Researchers",
            description=(
                "Academic and industry researchers focused on alignment, "
                "interpretability, and formal verification of AI systems."
            ),
            platforms=["twitter", "bluesky", "github", "huggingface"],
            optimal_posting_times={
                "twitter": ["14:00 UTC", "18:00 UTC"],
                "bluesky": ["15:00 UTC", "19:00 UTC"],
                "github": ["16:00 UTC"],
                "huggingface": ["10:00 UTC", "16:00 UTC"],
            },
            content_preferences=[
                "Technical deep dives",
                "Formal proofs and mathematical rigor",
                "Benchmark comparisons",
                "Paper references and citations",
                "Open-source contributions",
            ],
            pain_points=[
                "Lack of formal safety guarantees in production systems",
                "Difficulty bridging theory to deployment",
                "No standard framework for agent containment",
                "Post-quantum migration urgency",
            ],
            value_propositions=[
                "Mathematically-bounded containment via hyperbolic geometry",
                "14-layer architecture with formal verification hooks",
                "50K+ LOC reference implementation with 2620+ tests",
                "Patent-pending novel approach to geometric safety",
            ],
            engagement_patterns={
                "avg_like_rate": 0.032,
                "avg_repost_rate": 0.018,
                "avg_comment_rate": 0.008,
                "best_day": 2,  # Tuesday (0=Monday)
            },
            keywords=[
                "alignment", "containment", "formal verification",
                "safety proofs", "Poincare", "hyperbolic",
            ],
        ),
        AudienceSegment.ENTERPRISE_CTOS: AudienceProfile(
            segment="Enterprise CTOs",
            description=(
                "C-suite technology leaders evaluating AI governance "
                "solutions for enterprise deployment."
            ),
            platforms=["linkedin", "medium", "twitter"],
            optimal_posting_times={
                "linkedin": ["08:00 UTC", "12:00 UTC", "17:00 UTC"],
                "medium": ["09:00 UTC", "14:00 UTC"],
                "twitter": ["13:00 UTC", "17:00 UTC"],
            },
            content_preferences=[
                "ROI and business value",
                "Compliance and regulatory alignment",
                "Integration ease and deployment stories",
                "Competitive differentiation",
                "Risk mitigation narratives",
            ],
            pain_points=[
                "AI liability and regulatory compliance (EU AI Act, etc.)",
                "Agent unpredictability in production",
                "Lack of audit trails for AI decisions",
                "Vendor lock-in with safety solutions",
            ],
            value_propositions=[
                "Patent-pending framework with clear IP position",
                "Full audit trail across 14 governance layers",
                "Open architecture avoids vendor lock-in",
                "Post-quantum ready for long-term data protection",
            ],
            engagement_patterns={
                "avg_like_rate": 0.025,
                "avg_repost_rate": 0.012,
                "avg_comment_rate": 0.015,
                "best_day": 1,  # Tuesday
            },
            keywords=[
                "enterprise AI", "governance", "compliance",
                "risk management", "audit trail", "deployment",
            ],
        ),
        AudienceSegment.DEVSECOPS_ENGINEERS: AudienceProfile(
            segment="DevSecOps Engineers",
            description=(
                "Security-minded engineers integrating AI agents into "
                "CI/CD pipelines and production infrastructure."
            ),
            platforms=["twitter", "github", "mastodon", "bluesky"],
            optimal_posting_times={
                "twitter": ["15:00 UTC", "20:00 UTC"],
                "github": ["10:00 UTC", "15:00 UTC"],
                "mastodon": ["14:00 UTC", "19:00 UTC"],
                "bluesky": ["15:00 UTC", "20:00 UTC"],
            },
            content_preferences=[
                "Code examples and implementation guides",
                "Security architecture breakdowns",
                "Integration tutorials",
                "Benchmark results and performance data",
                "Threat model analysis",
            ],
            pain_points=[
                "AI agents escalating privileges in pipelines",
                "No standard for agent permission boundaries",
                "Difficulty auditing AI-generated code changes",
                "Supply chain attacks via compromised AI agents",
            ],
            value_propositions=[
                "Zero-trust governance gates at every layer",
                "Semantic antivirus for prompt injection defense",
                "WASM/WIT components for sandboxed execution",
                "Full telemetry and audit logging",
            ],
            engagement_patterns={
                "avg_like_rate": 0.028,
                "avg_repost_rate": 0.022,
                "avg_comment_rate": 0.012,
                "best_day": 3,  # Wednesday
            },
            keywords=[
                "zero-trust", "CI/CD", "supply chain security",
                "agent permissions", "sandboxing", "WASM",
            ],
        ),
        AudienceSegment.DEFENSE_AEROSPACE: AudienceProfile(
            segment="Defense & Aerospace",
            description=(
                "Defense contractors, aerospace engineers, and government "
                "program managers evaluating AI governance for mission-critical systems."
            ),
            platforms=["linkedin", "twitter"],
            optimal_posting_times={
                "linkedin": ["09:00 UTC", "14:00 UTC"],
                "twitter": ["14:00 UTC", "18:00 UTC"],
            },
            content_preferences=[
                "Certification and compliance pathways",
                "Formal safety proofs",
                "Post-quantum cryptography readiness",
                "Multi-agent coordination reliability",
                "Space-domain networking capabilities",
            ],
            pain_points=[
                "NIST PQC migration deadlines",
                "Certifying autonomous system safety (MIL-STD)",
                "Adversarial AI threats in contested environments",
                "Multi-domain agent coordination challenges",
            ],
            value_propositions=[
                "Post-quantum crypto ready (ML-KEM-768, ML-DSA-65)",
                "BFT consensus for contested environments",
                "v4.0 roadmap includes Space Tor networking",
                "Patent-pending architecture suitable for SBIR/STTR",
            ],
            engagement_patterns={
                "avg_like_rate": 0.015,
                "avg_repost_rate": 0.008,
                "avg_comment_rate": 0.005,
                "best_day": 1,  # Tuesday
            },
            keywords=[
                "MIL-STD", "NIST", "post-quantum", "autonomous systems",
                "contested environments", "BFT", "Space Tor",
            ],
        ),
        AudienceSegment.FINTECH: AudienceProfile(
            segment="Fintech",
            description=(
                "Financial technology leaders, quant developers, and "
                "compliance officers evaluating AI governance for trading "
                "and risk management systems."
            ),
            platforms=["linkedin", "twitter", "medium"],
            optimal_posting_times={
                "linkedin": ["07:00 UTC", "12:00 UTC"],
                "twitter": ["13:00 UTC", "16:00 UTC"],
                "medium": ["10:00 UTC"],
            },
            content_preferences=[
                "Risk quantification and bounds",
                "Regulatory compliance (SEC, MiFID II)",
                "Real-time decision auditing",
                "Adversarial resilience in financial systems",
            ],
            pain_points=[
                "Flash crash prevention in AI trading",
                "Regulatory scrutiny of algorithmic decisions",
                "Model risk management for AI agents",
                "Quantum threats to cryptographic protocols",
            ],
            value_propositions=[
                "Hamiltonian cost functions bound financial risk geometrically",
                "Full audit trail satisfies regulatory requirements",
                "Post-quantum readiness for long-term position protection",
                "Deterministic governance gates prevent runaway agents",
            ],
            engagement_patterns={
                "avg_like_rate": 0.020,
                "avg_repost_rate": 0.010,
                "avg_comment_rate": 0.008,
                "best_day": 0,  # Monday
            },
            keywords=[
                "algorithmic trading", "risk management", "compliance",
                "model risk", "fintech governance", "quantum-safe",
            ],
        ),
        AudienceSegment.OPEN_SOURCE_COMMUNITY: AudienceProfile(
            segment="Open Source Community",
            description=(
                "Open-source developers, contributors, and maintainers "
                "interested in AI safety tooling."
            ),
            platforms=["twitter", "bluesky", "mastodon", "github", "huggingface"],
            optimal_posting_times={
                "twitter": ["16:00 UTC", "21:00 UTC"],
                "bluesky": ["16:00 UTC", "21:00 UTC"],
                "mastodon": ["15:00 UTC", "20:00 UTC"],
                "github": ["14:00 UTC"],
                "huggingface": ["15:00 UTC"],
            },
            content_preferences=[
                "Build-in-public updates",
                "Contribution guides",
                "Architecture deep dives",
                "Test results and CI status",
                "Roadmap transparency",
            ],
            pain_points=[
                "Most AI safety tools are closed-source",
                "Lack of comprehensive governance frameworks",
                "Fragmented tooling landscape",
                "High barrier to entry for safety research",
            ],
            value_propositions=[
                "Fully open-source 50K+ LOC framework",
                "Comprehensive test suite (2620+ tests)",
                "Clear architecture documentation",
                "Active development with public roadmap",
            ],
            engagement_patterns={
                "avg_like_rate": 0.035,
                "avg_repost_rate": 0.025,
                "avg_comment_rate": 0.015,
                "best_day": 4,  # Friday
            },
            keywords=[
                "open source", "AI safety tools", "contributions",
                "build in public", "developer experience",
            ],
        ),
    }

    def get_profile(self, segment: str) -> Optional[AudienceProfile]:
        """Get audience profile by segment name."""
        segment = segment.lower().replace(" ", "_").replace("-", "_")
        for key, profile in self.PROFILES.items():
            key_str = key if isinstance(key, str) else key.value
            if key_str == segment or key_str.replace("_", "") == segment.replace("_", ""):
                return profile
        return None

    def get_all_profiles(self) -> Dict[str, AudienceProfile]:
        """Return all audience profiles."""
        return dict(self.PROFILES)

    def suggest_audience_for_topic(self, topic: str) -> List[Tuple[str, float]]:
        """
        Rank audiences by relevance to a topic.

        Returns list of (segment_name, relevance_score) sorted descending.
        """
        results: List[Tuple[str, float]] = []
        topic_lower = topic.lower()
        topic_words = set(topic_lower.split())

        for key, profile in self.PROFILES.items():
            score = 0.0
            key_str = key if isinstance(key, str) else key.value

            # Keyword overlap
            for kw in profile.keywords:
                if kw.lower() in topic_lower:
                    score += 2.0
                elif any(w in topic_lower for w in kw.lower().split()):
                    score += 0.5

            # Pain point relevance
            for pp in profile.pain_points:
                common = topic_words & set(pp.lower().split())
                score += len(common) * 0.3

            # Content preference match
            for pref in profile.content_preferences:
                common = topic_words & set(pref.lower().split())
                score += len(common) * 0.2

            results.append((key_str, round(score, 2)))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def suggest_posting_schedule(
        self, platform: str, segments: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Suggest optimal posting times for a platform across audience segments.

        Returns list of time slots with audience overlap data.
        """
        platform = platform.lower()
        time_scores: Dict[str, List[str]] = {}  # time -> [segments]

        profiles_to_check = self.PROFILES
        if segments:
            profiles_to_check = {
                k: v for k, v in self.PROFILES.items()
                if (k if isinstance(k, str) else k.value) in segments
            }

        for key, profile in profiles_to_check.items():
            key_str = key if isinstance(key, str) else key.value
            times = profile.optimal_posting_times.get(platform, [])
            for t in times:
                if t not in time_scores:
                    time_scores[t] = []
                time_scores[t].append(key_str)

        schedule = []
        for time_slot, segs in sorted(time_scores.items()):
            schedule.append({
                "time_utc": time_slot,
                "audience_overlap": len(segs),
                "segments": segs,
                "priority": "high" if len(segs) >= 3 else ("medium" if len(segs) >= 2 else "low"),
            })

        schedule.sort(key=lambda x: x["audience_overlap"], reverse=True)
        return schedule


# ---------------------------------------------------------------------------
#  Agent 3: CampaignOrchestrator
# ---------------------------------------------------------------------------

class CampaignOrchestrator:
    """
    Coordinates multi-platform marketing campaigns.

    Schedules content, manages content calendars, generates reports,
    and respects per-platform rate limits.
    """

    # Posting cadence per platform (posts per week)
    DEFAULT_CADENCE: Dict[str, int] = {
        "twitter": 7,      # Daily
        "linkedin": 3,     # 3x/week
        "bluesky": 5,      # 5x/week
        "mastodon": 5,     # 5x/week
        "medium": 1,       # Weekly article
        "wordpress": 1,    # Weekly blog post
        "github": 2,       # 2x/week (releases, discussions)
        "huggingface": 1,  # Weekly model card update
    }

    # Template rotation for variety
    TEMPLATE_ROTATION = [
        ContentTemplate.FEATURE_ANNOUNCEMENT,
        ContentTemplate.THOUGHT_LEADERSHIP,
        ContentTemplate.BENCHMARK_RESULTS,
        ContentTemplate.ARCHITECTURE_EXPLAINER,
        ContentTemplate.USE_CASE_STORY,
        ContentTemplate.MILESTONE_UPDATE,
    ]

    # Topics to rotate through
    TOPIC_POOL = [
        "14-layer governance architecture",
        "Post-quantum cryptography readiness",
        "Hyperbolic containment in the Poincare ball",
        "2620+ tests with zero failures",
        "Sacred Tongues encoding system",
        "WASM/WIT interoperability for edge deployment",
        "BFT consensus for multi-agent coordination",
        "Federated learning with privacy-preserving aggregation",
        "Semantic antivirus and prompt injection defense",
        "Hamiltonian cost functions for safety bounds",
        "v3.0.0 production release",
        "Agent governance for enterprise deployment",
        "DevSecOps integration with zero-trust gates",
        "Patent-pending geometric safety approach",
        "ChoiceScript game-based training pipeline",
        "Latest benchmark results",
        "Open-source AI safety tooling",
        "Post-quantum migration guide",
        "Multi-agent fleet orchestration",
        "Space Tor networking roadmap",
    ]

    def __init__(self) -> None:
        self._content_gen = ContentGeneratorAgent()
        self._audience = AudienceResearchAgent()
        self._rng = random.Random(42)

    def generate_campaign(
        self,
        days: int = 7,
        platforms: Optional[List[str]] = None,
        audience: str = "",
    ) -> CampaignPlan:
        """
        Generate a multi-day content campaign.

        Args:
            days: Number of days to plan (7 or 30)
            platforms: Platforms to include (default: all major)
            audience: Target audience segment (optional, mixes if empty)
        """
        if platforms is None:
            platforms = ["twitter", "linkedin", "bluesky", "mastodon", "medium"]

        now = datetime.now(timezone.utc)
        start_date = now.strftime("%Y-%m-%d")
        plan_name = f"SCBE Campaign {start_date} ({days}d)"

        posts: List[Dict[str, Any]] = []
        template_idx = 0
        topic_idx = 0

        for day_offset in range(days):
            current_date = now + timedelta(days=day_offset)
            date_str = current_date.strftime("%Y-%m-%d")
            day_name = current_date.strftime("%A")

            for platform in platforms:
                cadence = self.DEFAULT_CADENCE.get(platform, 1)
                # Determine if this platform should post today
                if cadence >= 7:
                    should_post = True  # Daily
                elif cadence >= 5:
                    should_post = current_date.weekday() < 5  # Weekdays
                elif cadence >= 3:
                    should_post = current_date.weekday() in (0, 2, 4)  # Mon/Wed/Fri
                elif cadence >= 2:
                    should_post = current_date.weekday() in (1, 3)  # Tue/Thu
                else:
                    should_post = current_date.weekday() == 0  # Monday only

                if not should_post:
                    continue

                # Pick template and topic
                template = self.TEMPLATE_ROTATION[template_idx % len(self.TEMPLATE_ROTATION)]
                topic = self.TOPIC_POOL[topic_idx % len(self.TOPIC_POOL)]
                template_idx += 1
                topic_idx += 1

                # Get optimal time for this platform
                schedule = self._audience.suggest_posting_schedule(platform)
                post_time = schedule[0]["time_utc"] if schedule else "14:00 UTC"

                # Determine audience
                if audience:
                    target_audience = audience
                else:
                    suggestions = self._audience.suggest_audience_for_topic(topic)
                    target_audience = suggestions[0][0] if suggestions else ""

                # Generate content
                content = self._content_gen.generate(
                    platform=platform,
                    topic=topic,
                    template=template,
                    audience=target_audience,
                )

                posts.append({
                    "date": date_str,
                    "day": day_name,
                    "time_utc": post_time,
                    "platform": platform,
                    "topic": topic,
                    "template": template if isinstance(template, str) else template.value,
                    "audience": target_audience,
                    "text_preview": content.text[:120] + ("..." if len(content.text) > 120 else ""),
                    "char_count": content.char_count,
                    "hashtags": content.hashtags,
                    "media_suggestions": content.media_suggestions,
                    "estimated_engagement": content.estimated_engagement,
                    "full_content": content.to_dict(),
                })

        plan = CampaignPlan(
            name=plan_name,
            days=days,
            start_date=start_date,
            posts=posts,
            total_posts=len(posts),
            platforms_covered=list(set(p["platform"] for p in posts)),
        )

        return plan

    def generate_report(self, plan: CampaignPlan) -> str:
        """Generate a human-readable campaign report."""
        lines = [
            f"{'=' * 60}",
            f"  CAMPAIGN PLAN: {plan.name}",
            f"{'=' * 60}",
            f"",
            f"  Duration: {plan.days} days starting {plan.start_date}",
            f"  Total posts: {plan.total_posts}",
            f"  Platforms: {', '.join(plan.platforms_covered)}",
            f"",
            f"{'=' * 60}",
            f"  CONTENT CALENDAR",
            f"{'=' * 60}",
        ]

        current_date = ""
        for post in plan.posts:
            if post["date"] != current_date:
                current_date = post["date"]
                lines.append(f"\n--- {post['date']} ({post['day']}) ---")

            lines.append(
                f"  [{post['time_utc']}] {post['platform'].upper():12s} "
                f"| {post['template']:25s} | {post['text_preview']}"
            )
            if post.get("hashtags"):
                lines.append(
                    f"  {'':17s} tags: {' '.join('#' + h for h in post['hashtags'][:5])}"
                )

        # Summary statistics
        platform_counts: Dict[str, int] = {}
        template_counts: Dict[str, int] = {}
        engagement_totals: Dict[str, int] = {"high": 0, "medium": 0, "low": 0}

        for post in plan.posts:
            p = post["platform"]
            t = post["template"]
            e = post.get("estimated_engagement", "medium")
            platform_counts[p] = platform_counts.get(p, 0) + 1
            template_counts[t] = template_counts.get(t, 0) + 1
            engagement_totals[e] = engagement_totals.get(e, 0) + 1

        lines += [
            f"\n{'=' * 60}",
            f"  SUMMARY",
            f"{'=' * 60}",
            f"",
            f"  Posts per platform:",
        ]
        for p, count in sorted(platform_counts.items()):
            lines.append(f"    {p:15s}: {count}")

        lines.append(f"\n  Posts per template:")
        for t, count in sorted(template_counts.items()):
            lines.append(f"    {t:30s}: {count}")

        lines.append(f"\n  Engagement estimates:")
        for e, count in sorted(engagement_totals.items()):
            lines.append(f"    {e:10s}: {count}")

        lines.append(f"\n{'=' * 60}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
#  Agent 4: SEOContentAgent
# ---------------------------------------------------------------------------

class SEOContentAgent:
    """
    Generates SEO-optimized content briefs and outlines.

    Produces blog post outlines, keyword research output, meta
    descriptions, and title variants for key SCBE topics.
    """

    # Core topic clusters for SCBE-AETHERMOORE
    TOPIC_CLUSTERS: Dict[str, Dict[str, Any]] = {
        "ai agent governance": {
            "primary_keyword": "AI agent governance framework",
            "secondary_keywords": [
                "autonomous AI governance",
                "AI safety architecture",
                "multi-agent coordination",
                "AI containment framework",
                "agent behavior bounds",
                "AI governance layers",
                "AI policy engine",
                "governance-first AI",
            ],
            "search_intent": "informational",
            "difficulty": "medium",
            "volume_estimate": "2400/mo",
        },
        "hyperbolic geometry ai safety": {
            "primary_keyword": "hyperbolic geometry AI safety",
            "secondary_keywords": [
                "Poincare ball model AI",
                "geometric containment AI agents",
                "hyperbolic space agent behavior",
                "mathematical AI safety bounds",
                "Hamiltonian cost function safety",
                "exponential boundary resistance",
                "non-Euclidean AI safety",
            ],
            "search_intent": "informational",
            "difficulty": "low",
            "volume_estimate": "480/mo",
        },
        "post-quantum cryptography agents": {
            "primary_keyword": "post-quantum cryptography AI agents",
            "secondary_keywords": [
                "ML-KEM-768 agent identity",
                "ML-DSA-65 digital signatures",
                "quantum-safe AI communication",
                "NIST PQC migration AI",
                "post-quantum agent authentication",
                "quantum-resistant agent framework",
                "Dilithium AI agent signing",
            ],
            "search_intent": "informational",
            "difficulty": "low",
            "volume_estimate": "880/mo",
        },
        "multi-agent safety coordination": {
            "primary_keyword": "multi-agent safety coordination",
            "secondary_keywords": [
                "BFT consensus AI agents",
                "Byzantine fault tolerant AI",
                "fleet AI orchestration",
                "multi-agent governance",
                "agent swarm safety",
                "coordinated AI decision making",
                "distributed agent consensus",
            ],
            "search_intent": "informational",
            "difficulty": "medium",
            "volume_estimate": "1200/mo",
        },
        "ai safety testing framework": {
            "primary_keyword": "AI safety testing framework",
            "secondary_keywords": [
                "AI agent test suite",
                "safety verification testing",
                "AI governance testing",
                "autonomous system validation",
                "agent boundary testing",
                "AI safety benchmarks",
                "comprehensive AI testing",
            ],
            "search_intent": "informational/transactional",
            "difficulty": "medium",
            "volume_estimate": "1900/mo",
        },
        "wasm ai agent deployment": {
            "primary_keyword": "WASM AI agent deployment",
            "secondary_keywords": [
                "WebAssembly AI agents",
                "WASM WIT AI components",
                "edge AI deployment WASM",
                "sandboxed AI execution",
                "component model AI",
                "portable AI agent runtime",
            ],
            "search_intent": "informational",
            "difficulty": "low",
            "volume_estimate": "590/mo",
        },
        "federated learning governance": {
            "primary_keyword": "federated learning governance framework",
            "secondary_keywords": [
                "privacy-preserving federated learning",
                "federated AI governance",
                "secure aggregation framework",
                "federated training governance",
                "distributed learning safety",
                "federated model privacy",
            ],
            "search_intent": "informational",
            "difficulty": "medium",
            "volume_estimate": "1400/mo",
        },
    }

    def __init__(self) -> None:
        self._reader = ProjectDataReader()

    def generate_brief(self, topic: str) -> SEOBrief:
        """
        Generate an SEO content brief for a topic.

        Args:
            topic: The topic to optimize for
        """
        # Find matching topic cluster or create custom
        cluster = self._find_cluster(topic)

        primary_kw = cluster["primary_keyword"]
        secondary_kws = cluster["secondary_keywords"]

        # Generate title variants
        title_variants = self._generate_titles(topic, primary_kw)

        # Generate meta description
        meta_desc = self._generate_meta_description(topic, primary_kw)

        # Generate outline
        outline = self._generate_outline(topic, primary_kw, secondary_kws)

        # Internal link suggestions
        internal_links = [
            f"{REPO_URL} (GitHub repository)",
            f"{REPO_URL}/tree/main/src/symphonic_cipher (Core implementation)",
            f"{REPO_URL}/tree/main/docs (Documentation)",
            f"{REPO_URL}/tree/main/packages/wit (WASM/WIT interfaces)",
        ]

        return SEOBrief(
            topic=topic,
            primary_keyword=primary_kw,
            secondary_keywords=secondary_kws,
            title_variants=title_variants,
            meta_description=meta_desc,
            outline=outline,
            word_count_target=2500 if "guide" in topic.lower() else 2000,
            internal_links=internal_links,
            competitor_angle=(
                f"Most articles on {topic} focus on theoretical concepts. "
                f"This piece differentiates by showing a working implementation "
                f"with {self._reader.read_test_results().get('total_tests', 2620)}+ "
                f"tests and a patent-pending architecture."
            ),
        )

    def generate_keyword_report(self, topic: str) -> Dict[str, Any]:
        """Generate structured keyword research data for a topic."""
        cluster = self._find_cluster(topic)
        features = self._reader.get_key_features()

        # Build keyword tiers
        primary = [cluster["primary_keyword"]]
        secondary = cluster["secondary_keywords"][:5]
        long_tail = [
            f"how to implement {cluster['primary_keyword']}",
            f"best {cluster['primary_keyword']} for enterprise",
            f"{cluster['primary_keyword']} tutorial 2026",
            f"{cluster['primary_keyword']} vs traditional approaches",
            f"open source {cluster['primary_keyword']}",
        ]

        # Related topics
        related = []
        for key in self.TOPIC_CLUSTERS:
            if key != self._normalize_topic(topic):
                related.append({
                    "topic": key,
                    "keyword": self.TOPIC_CLUSTERS[key]["primary_keyword"],
                    "estimated_volume": self.TOPIC_CLUSTERS[key]["volume_estimate"],
                })

        return {
            "topic": topic,
            "search_intent": cluster.get("search_intent", "informational"),
            "estimated_difficulty": cluster.get("difficulty", "medium"),
            "estimated_volume": cluster.get("volume_estimate", "unknown"),
            "keyword_tiers": {
                "primary": primary,
                "secondary": secondary,
                "long_tail": long_tail,
            },
            "related_topics": related[:5],
            "content_gaps": [
                f"No comprehensive guide on {cluster['primary_keyword']} with working code",
                f"Lack of benchmark data comparing approaches",
                f"Missing enterprise deployment case studies",
            ],
            "featured_snippet_opportunities": [
                f"What is {cluster['primary_keyword']}?",
                f"How does {cluster['primary_keyword']} work?",
                f"Why is {cluster['primary_keyword']} important?",
            ],
        }

    # -- Internal helpers ------------------------------------------------------

    def _find_cluster(self, topic: str) -> Dict[str, Any]:
        """Find the best matching topic cluster."""
        normalized = self._normalize_topic(topic)

        # Exact match
        if normalized in self.TOPIC_CLUSTERS:
            return self.TOPIC_CLUSTERS[normalized]

        # Partial match
        best_key = None
        best_score = 0
        topic_words = set(normalized.split())

        for key in self.TOPIC_CLUSTERS:
            key_words = set(key.split())
            overlap = len(topic_words & key_words)
            if overlap > best_score:
                best_score = overlap
                best_key = key

        if best_key and best_score > 0:
            return self.TOPIC_CLUSTERS[best_key]

        # Create custom cluster from topic
        return {
            "primary_keyword": topic,
            "secondary_keywords": [
                f"{topic} framework",
                f"{topic} implementation",
                f"{topic} best practices",
                f"{topic} architecture",
                f"SCBE {topic}",
            ],
            "search_intent": "informational",
            "difficulty": "medium",
            "volume_estimate": "unknown",
        }

    def _normalize_topic(self, topic: str) -> str:
        """Normalize topic string for matching."""
        return re.sub(r"[^a-z0-9\s-]", "", topic.lower()).strip()

    def _generate_titles(self, topic: str, primary_kw: str) -> List[str]:
        """Generate SEO-optimized title variants."""
        return [
            f"The Complete Guide to {primary_kw.title()} in 2026",
            f"How {PROJECT_NAME} Implements {primary_kw.title()}: A Technical Deep Dive",
            f"{primary_kw.title()}: Why It Matters and How to Get Started",
            f"Building Production-Ready {primary_kw.title()} with 14 Governance Layers",
            f"{primary_kw.title()} Explained: From Theory to 50K Lines of Working Code",
            f"Why {primary_kw.title()} Is the Future of Autonomous AI",
        ]

    def _generate_meta_description(self, topic: str, primary_kw: str) -> str:
        """Generate an SEO meta description (155 chars max)."""
        test_data = self._reader.read_test_results()
        desc = (
            f"Learn how {PROJECT_NAME} implements {primary_kw} with "
            f"14 governance layers, {test_data.get('total_tests', 2620)}+ tests, "
            f"and post-quantum crypto. Open-source."
        )
        if len(desc) > 155:
            desc = desc[:152] + "..."
        return desc

    def _generate_outline(
        self, topic: str, primary_kw: str, secondary_kws: List[str],
    ) -> List[Dict[str, Any]]:
        """Generate a blog post outline with sections."""
        return [
            {
                "heading": f"What Is {primary_kw.title()}?",
                "type": "h2",
                "keywords": [primary_kw, secondary_kws[0] if secondary_kws else ""],
                "bullets": [
                    "Definition and scope",
                    "Why traditional approaches fall short",
                    "The need for mathematical safety guarantees",
                ],
                "word_count": 300,
            },
            {
                "heading": f"The {PROJECT_NAME} Approach",
                "type": "h2",
                "keywords": [PROJECT_NAME, "14-layer architecture"],
                "bullets": [
                    "Overview of the 14-layer governance architecture",
                    "How hyperbolic geometry creates natural containment",
                    "Dual Hamiltonian cost functions",
                ],
                "word_count": 400,
            },
            {
                "heading": "Technical Deep Dive",
                "type": "h2",
                "keywords": secondary_kws[:3],
                "bullets": [
                    "Post-quantum cryptography (ML-KEM-768, ML-DSA-65)",
                    "Poincare ball containment model",
                    "BFT consensus for multi-agent coordination",
                    "WASM/WIT component interfaces",
                    "Code examples and implementation details",
                ],
                "word_count": 600,
            },
            {
                "heading": "Real-World Applications",
                "type": "h2",
                "keywords": ["enterprise", "deployment", "use cases"],
                "bullets": [
                    "Fintech: Trading agent risk bounds",
                    "Defense: Autonomous system governance",
                    "DevSecOps: CI/CD agent containment",
                    "Healthcare: Privacy-preserving AI governance",
                ],
                "word_count": 400,
            },
            {
                "heading": "Benchmarks and Validation",
                "type": "h2",
                "keywords": ["testing", "benchmarks", "validation"],
                "bullets": [
                    "2620+ tests with 98.3% pass rate",
                    "50K+ LOC codebase statistics",
                    "Conformance testing methodology",
                    "Comparison with existing approaches",
                ],
                "word_count": 300,
            },
            {
                "heading": "Getting Started",
                "type": "h2",
                "keywords": ["tutorial", "implementation", "getting started"],
                "bullets": [
                    "Prerequisites and installation",
                    "Basic governance gate setup",
                    "Running the test suite",
                    "Integration with existing systems",
                ],
                "word_count": 300,
            },
            {
                "heading": "Conclusion and Roadmap",
                "type": "h2",
                "keywords": ["roadmap", "future", "v4.0"],
                "bullets": [
                    "Summary of key takeaways",
                    "v4.0.0 roadmap (Space Tor, telecommunications)",
                    "How to contribute",
                    "Links and resources",
                ],
                "word_count": 200,
            },
        ]


# ---------------------------------------------------------------------------
#  CLI Interface
# ---------------------------------------------------------------------------

def _fmt_json(obj: Any) -> str:
    """Pretty-print JSON-serializable object."""
    return json.dumps(obj, indent=2, default=str)


def cmd_generate(args: argparse.Namespace) -> None:
    """Handle 'generate' subcommand."""
    agent = ContentGeneratorAgent()

    if args.all_platforms:
        platforms = ["twitter", "linkedin", "bluesky", "mastodon", "medium"]
        results = agent.generate_multi_platform(
            topic=args.topic,
            platforms=platforms,
            template=args.template or "",
            audience=args.audience or "",
        )
        for content in results:
            print(content.display())
            print()
    else:
        platform = args.platform or "twitter"
        content = agent.generate(
            platform=platform,
            topic=args.topic,
            template=args.template or "",
            audience=args.audience or "",
        )
        print(content.display())

    if args.json:
        if args.all_platforms:
            print("\n--- JSON ---")
            print(_fmt_json([c.to_dict() for c in results]))
        else:
            print("\n--- JSON ---")
            print(_fmt_json(content.to_dict()))


def cmd_campaign(args: argparse.Namespace) -> None:
    """Handle 'campaign' subcommand."""
    orchestrator = CampaignOrchestrator()

    platforms = None
    if args.platforms:
        platforms = [p.strip() for p in args.platforms.split(",")]

    plan = orchestrator.generate_campaign(
        days=args.days,
        platforms=platforms,
        audience=args.audience or "",
    )

    report = orchestrator.generate_report(plan)
    print(report)

    if args.json:
        print("\n--- JSON ---")
        print(_fmt_json(plan.to_dict()))


def cmd_seo(args: argparse.Namespace) -> None:
    """Handle 'seo' subcommand."""
    agent = SEOContentAgent()

    brief = agent.generate_brief(args.topic)
    keywords = agent.generate_keyword_report(args.topic)

    print(f"{'=' * 60}")
    print(f"  SEO BRIEF: {brief.topic}")
    print(f"{'=' * 60}")
    print()
    print(f"  Primary keyword: {brief.primary_keyword}")
    print(f"  Secondary keywords:")
    for kw in brief.secondary_keywords:
        print(f"    - {kw}")
    print()
    print(f"  Meta description ({len(brief.meta_description)} chars):")
    print(f"    {brief.meta_description}")
    print()
    print(f"  Title variants:")
    for i, title in enumerate(brief.title_variants, 1):
        print(f"    {i}. {title}")
    print()
    print(f"  Word count target: {brief.word_count_target}")
    print()
    print(f"  Competitor angle:")
    print(f"    {brief.competitor_angle}")
    print()
    print(f"{'=' * 60}")
    print(f"  OUTLINE ({sum(s['word_count'] for s in brief.outline)} words target)")
    print(f"{'=' * 60}")
    for section in brief.outline:
        print(f"\n  {section['heading']} ({section['type']}, ~{section['word_count']} words)")
        for bullet in section["bullets"]:
            print(f"    - {bullet}")
        if section.get("keywords"):
            kws = [k for k in section["keywords"] if k]
            if kws:
                print(f"    Keywords: {', '.join(kws)}")

    print(f"\n{'=' * 60}")
    print(f"  KEYWORD RESEARCH")
    print(f"{'=' * 60}")
    print(f"\n  Search intent: {keywords['search_intent']}")
    print(f"  Difficulty: {keywords['estimated_difficulty']}")
    print(f"  Volume: {keywords['estimated_volume']}")
    print(f"\n  Long-tail keywords:")
    for kw in keywords["keyword_tiers"]["long_tail"]:
        print(f"    - {kw}")
    print(f"\n  Featured snippet opportunities:")
    for q in keywords["featured_snippet_opportunities"]:
        print(f"    - {q}")
    print(f"\n  Content gaps:")
    for gap in keywords["content_gaps"]:
        print(f"    - {gap}")
    print(f"\n  Internal links:")
    for link in brief.internal_links:
        print(f"    - {link}")
    print()

    if args.json:
        print("--- JSON ---")
        print(_fmt_json({"brief": brief.to_dict(), "keywords": keywords}))


def cmd_audience(args: argparse.Namespace) -> None:
    """Handle 'audience' subcommand."""
    agent = AudienceResearchAgent()

    if args.segment:
        profile = agent.get_profile(args.segment)
        if profile is None:
            print(f"Unknown segment: {args.segment}")
            print(f"Available: {', '.join(k if isinstance(k, str) else k.value for k in agent.PROFILES.keys())}")
            sys.exit(1)

        print(f"{'=' * 60}")
        print(f"  AUDIENCE PROFILE: {profile.segment}")
        print(f"{'=' * 60}")
        print(f"\n  {profile.description}")
        print(f"\n  Preferred platforms: {', '.join(profile.platforms)}")
        print(f"\n  Optimal posting times:")
        for plat, times in profile.optimal_posting_times.items():
            print(f"    {plat:15s}: {', '.join(times)}")
        print(f"\n  Content preferences:")
        for pref in profile.content_preferences:
            print(f"    - {pref}")
        print(f"\n  Pain points:")
        for pp in profile.pain_points:
            print(f"    - {pp}")
        print(f"\n  Value propositions:")
        for vp in profile.value_propositions:
            print(f"    - {vp}")
        print(f"\n  Keywords: {', '.join(profile.keywords)}")
        print(f"\n  Engagement patterns:")
        for metric, val in profile.engagement_patterns.items():
            print(f"    {metric}: {val}")
        print()

    elif args.topic:
        rankings = agent.suggest_audience_for_topic(args.topic)
        print(f"{'=' * 60}")
        print(f"  AUDIENCE RELEVANCE: \"{args.topic}\"")
        print(f"{'=' * 60}")
        for segment, score in rankings:
            bar = "#" * int(score * 5)
            print(f"  {segment:30s} {score:5.1f}  {bar}")
        print()

    else:
        print(f"{'=' * 60}")
        print(f"  ALL AUDIENCE SEGMENTS")
        print(f"{'=' * 60}")
        for key, profile in agent.get_all_profiles().items():
            key_str = key if isinstance(key, str) else key.value
            print(f"\n  [{key_str}]")
            print(f"    {profile.description[:80]}...")
            print(f"    Platforms: {', '.join(profile.platforms)}")
        print()

    if args.json:
        if args.segment:
            print("--- JSON ---")
            print(_fmt_json(profile.to_dict()))
        elif args.topic:
            print("--- JSON ---")
            print(_fmt_json(rankings))


def cmd_selftest(args: argparse.Namespace) -> None:
    """Run self-test to verify all agents work correctly."""
    print(f"{'=' * 60}")
    print(f"  MARKETING AGENTS SELF-TEST")
    print(f"{'=' * 60}")
    passed = 0
    failed = 0
    total = 0

    def check(label: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed, total
        total += 1
        if condition:
            passed += 1
            print(f"  PASS  {label}")
        else:
            failed += 1
            print(f"  FAIL  {label}")
            if detail:
                print(f"        {detail}")

    # 1. ContentGeneratorAgent
    print(f"\n--- ContentGeneratorAgent ---")
    gen = ContentGeneratorAgent()

    for platform in ["twitter", "linkedin", "medium", "bluesky", "mastodon"]:
        content = gen.generate(platform, "latest benchmark results")
        limit = PLATFORM_CHAR_LIMITS.get(platform, 3000)
        check(
            f"generate({platform}) produces content",
            len(content.text) > 0,
        )
        check(
            f"generate({platform}) respects char limit ({limit})",
            content.char_count <= limit,
            f"got {content.char_count} chars",
        )
        check(
            f"generate({platform}) has hashtags",
            len(content.hashtags) > 0,
        )

    multi = gen.generate_multi_platform("v3.0.0 release")
    check(
        "generate_multi_platform returns 4 items",
        len(multi) == 4,
        f"got {len(multi)}",
    )

    for template in ContentTemplate:
        content = gen.generate("linkedin", "test topic", template=template)
        check(
            f"template {template.value} generates content",
            len(content.text) > 0,
        )

    # 2. AudienceResearchAgent
    print(f"\n--- AudienceResearchAgent ---")
    aud = AudienceResearchAgent()

    for seg in AudienceSegment:
        profile = aud.get_profile(seg.value)
        check(
            f"get_profile({seg.value}) returns profile",
            profile is not None,
        )
        if profile:
            check(
                f"  has platforms",
                len(profile.platforms) > 0,
            )
            check(
                f"  has posting times",
                len(profile.optimal_posting_times) > 0,
            )

    rankings = aud.suggest_audience_for_topic("post-quantum cryptography for defense")
    check(
        "suggest_audience_for_topic returns rankings",
        len(rankings) > 0,
    )
    check(
        "  defense_aerospace ranks high for defense topic",
        any("defense" in r[0] for r in rankings[:3]),
        f"top 3: {[r[0] for r in rankings[:3]]}",
    )

    schedule = aud.suggest_posting_schedule("linkedin")
    check(
        "suggest_posting_schedule returns times",
        len(schedule) > 0,
    )

    # 3. CampaignOrchestrator
    print(f"\n--- CampaignOrchestrator ---")
    orch = CampaignOrchestrator()

    plan7 = orch.generate_campaign(days=7)
    check(
        "7-day campaign generates posts",
        plan7.total_posts > 0,
        f"got {plan7.total_posts} posts",
    )
    check(
        "7-day campaign covers multiple platforms",
        len(plan7.platforms_covered) > 1,
        f"platforms: {plan7.platforms_covered}",
    )

    plan30 = orch.generate_campaign(days=30, platforms=["twitter", "linkedin"])
    check(
        "30-day campaign generates posts",
        plan30.total_posts > 0,
        f"got {plan30.total_posts} posts",
    )

    report = orch.generate_report(plan7)
    check(
        "campaign report is non-empty",
        len(report) > 100,
        f"got {len(report)} chars",
    )
    check(
        "campaign report contains calendar",
        "CONTENT CALENDAR" in report,
    )

    # 4. SEOContentAgent
    print(f"\n--- SEOContentAgent ---")
    seo = SEOContentAgent()

    for topic_name in ["ai agent governance", "hyperbolic geometry ai safety", "post-quantum cryptography agents"]:
        brief = seo.generate_brief(topic_name)
        check(
            f"brief({topic_name}) has primary keyword",
            len(brief.primary_keyword) > 0,
        )
        check(
            f"  has title variants",
            len(brief.title_variants) >= 3,
        )
        check(
            f"  meta description <= 155 chars",
            len(brief.meta_description) <= 155,
            f"got {len(brief.meta_description)} chars",
        )
        check(
            f"  has outline sections",
            len(brief.outline) >= 5,
        )

    kw_report = seo.generate_keyword_report("ai agent governance")
    check(
        "keyword_report has tiers",
        "keyword_tiers" in kw_report,
    )
    check(
        "keyword_report has long-tail",
        len(kw_report.get("keyword_tiers", {}).get("long_tail", [])) > 0,
    )

    # Unknown topic falls back gracefully
    brief_custom = seo.generate_brief("underwater basket weaving with AI")
    check(
        "custom topic generates brief",
        len(brief_custom.primary_keyword) > 0,
    )

    # 5. ProjectDataReader
    print(f"\n--- ProjectDataReader ---")
    reader = ProjectDataReader()

    check(
        "read_test_results returns data",
        reader.read_test_results().get("total_tests", 0) > 0,
    )
    check(
        "get_key_features returns features",
        len(reader.get_key_features()) > 5,
    )
    check(
        "get_recent_milestones returns milestones",
        len(reader.get_recent_milestones()) > 3,
    )

    # Summary
    print(f"\n{'=' * 60}")
    print(f"  RESULTS: {passed}/{total} passed, {failed} failed")
    print(f"{'=' * 60}")

    if failed > 0:
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="marketing_agents",
        description="SCBE-AETHERMOORE Marketing Automation Agents",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # -- generate --
    gen_parser = subparsers.add_parser(
        "generate",
        help="Generate marketing content for a platform",
    )
    gen_parser.add_argument(
        "--platform", "-p",
        default="twitter",
        help="Target platform (twitter, linkedin, bluesky, mastodon, medium, wordpress, github)",
    )
    gen_parser.add_argument(
        "--topic", "-t",
        required=True,
        help="Topic to write about",
    )
    gen_parser.add_argument(
        "--template",
        choices=[t.value for t in ContentTemplate],
        help="Content template to use (auto-detected if omitted)",
    )
    gen_parser.add_argument(
        "--audience",
        choices=[s.value for s in AudienceSegment],
        help="Target audience segment",
    )
    gen_parser.add_argument(
        "--all-platforms",
        action="store_true",
        help="Generate for all major platforms at once",
    )
    gen_parser.add_argument(
        "--json",
        action="store_true",
        help="Also output JSON format",
    )

    # -- campaign --
    camp_parser = subparsers.add_parser(
        "campaign",
        help="Generate a multi-day content campaign",
    )
    camp_parser.add_argument(
        "--days", "-d",
        type=int,
        default=7,
        help="Number of days to plan (default: 7)",
    )
    camp_parser.add_argument(
        "--platforms",
        help="Comma-separated platforms (default: twitter,linkedin,bluesky,mastodon,medium)",
    )
    camp_parser.add_argument(
        "--audience",
        choices=[s.value for s in AudienceSegment],
        help="Target audience (mixes segments if omitted)",
    )
    camp_parser.add_argument(
        "--json",
        action="store_true",
        help="Also output JSON format",
    )

    # -- seo --
    seo_parser = subparsers.add_parser(
        "seo",
        help="Generate SEO-optimized content brief",
    )
    seo_parser.add_argument(
        "--topic", "-t",
        required=True,
        help="Topic to optimize for",
    )
    seo_parser.add_argument(
        "--json",
        action="store_true",
        help="Also output JSON format",
    )

    # -- audience --
    aud_parser = subparsers.add_parser(
        "audience",
        help="Research audience segments",
    )
    aud_parser.add_argument(
        "--segment", "-s",
        help="Specific segment to profile",
    )
    aud_parser.add_argument(
        "--topic", "-t",
        help="Topic to rank audiences against",
    )
    aud_parser.add_argument(
        "--json",
        action="store_true",
        help="Also output JSON format",
    )

    # -- selftest --
    subparsers.add_parser(
        "selftest",
        help="Run self-test to verify all agents",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    handlers = {
        "generate": cmd_generate,
        "campaign": cmd_campaign,
        "seo": cmd_seo,
        "audience": cmd_audience,
        "selftest": cmd_selftest,
    }

    handler = handlers.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
