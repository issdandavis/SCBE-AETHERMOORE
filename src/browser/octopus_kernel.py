# src/browser/octopus_kernel.py
"""Tri-Kernel Octopus Browser -- Eye (vision) + Judge (verify) + Forge (tools)."""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.browser.mode_switcher import (
    compute_phi_weight,
    domain_sensitivity,
    select_mode,
)
from src.browser.site_log import SiteLog, SiteLogStore


# -- Data structures -----------------------------------------------------------


@dataclass
class PageVision:
    url: str = ""
    page_type: str = "unknown"
    layout_description: str = ""
    interactive_elements: List[Dict[str, Any]] = field(default_factory=list)
    navigation_instructions: str = ""
    confidence: float = 0.0
    observation_tier: int = 1


@dataclass
class TriangulationResult:
    consensus: bool = False
    confidence: float = 0.0
    agreement_ratio: float = 0.0
    sources: Dict[str, List[str]] = field(default_factory=dict)


@dataclass
class ForgedTool:
    tool_id: str = ""
    domain: str = ""
    trigger: str = ""
    action_sequence: List[Dict[str, Any]] = field(default_factory=list)
    created_by: str = "forge"
    success_rate: float = 0.0
    ttl_hours: int = 72
    sacred_egg_tier: str = "solitary"


@dataclass
class ExecutionResult:
    mode: str = "sightless"
    success: bool = False
    data: Any = None
    vision: Optional[PageVision] = None
    triangulation: Optional[TriangulationResult] = None
    elapsed_ms: int = 0
    training_pairs: List[Dict] = field(default_factory=list)


# -- The Eye (KO -- Visual Perception) ----------------------------------------


class TheEye:
    """Kernel 1: Observes pages, classifies layout, identifies elements."""

    PAGE_TYPE_PATTERNS = {
        "login": ["login", "sign in", "log in", "password"],
        "product": ["add to cart", "buy now", "price", "$"],
        "checkout": ["checkout", "payment", "billing", "shipping"],
        "dashboard": ["dashboard", "overview", "analytics", "stats"],
        "article": ["published", "author", "read more", "comments"],
        "search": ["search results", "found", "showing"],
        "form": ["submit", "required", "fill out"],
    }

    async def observe_mock(
        self,
        url: str,
        a11y_tree: Optional[Dict] = None,
        page_text: str = "",
    ) -> PageVision:
        elements = []
        if a11y_tree:
            elements = self._extract_elements(a11y_tree)
        page_type = self._classify_page(page_text, elements)
        confidence = 0.8 if elements else 0.4
        return PageVision(
            url=url,
            page_type=page_type,
            interactive_elements=elements,
            navigation_instructions=f"Page has {len(elements)} interactive elements",
            confidence=confidence,
            observation_tier=2 if elements else 1,
        )

    def _extract_elements(self, tree: Dict, depth: int = 0) -> List[Dict]:
        elements = []
        role = tree.get("role", "")
        name = tree.get("name", "")
        interactive_roles = {"button", "link", "textbox", "checkbox", "combobox", "menuitem"}
        if role in interactive_roles:
            elements.append({"role": role, "name": name, "depth": depth})
        for child in tree.get("children", []):
            elements.extend(self._extract_elements(child, depth + 1))
        return elements

    def _classify_page(self, text: str, elements: List[Dict]) -> str:
        text_lower = text.lower()
        el_text = " ".join(e.get("name", "") for e in elements).lower()
        combined = text_lower + " " + el_text
        best_type, best_score = "unknown", 0
        for ptype, keywords in self.PAGE_TYPE_PATTERNS.items():
            score = sum(1 for kw in keywords if kw in combined)
            if score > best_score:
                best_type, best_score = ptype, score
        return best_type


# -- The Judge (RU -- Verification + Triangulation) ----------------------------


class TheJudge:
    """Kernel 2: Triangulates observations, runs verification, detects faults."""

    async def triangulate(
        self,
        a11y_elements: List[str],
        dom_elements: List[str],
        visual_elements: List[str],
    ) -> TriangulationResult:
        all_sources = {
            "a11y": set(a11y_elements),
            "dom": set(dom_elements),
            "visual": set(visual_elements),
        }
        a11y_dom = all_sources["a11y"] & all_sources["dom"]
        a11y_vis = all_sources["a11y"] & all_sources["visual"]
        dom_vis = all_sources["dom"] & all_sources["visual"]
        all_agree = all_sources["a11y"] & all_sources["dom"] & all_sources["visual"]

        all_unique = all_sources["a11y"] | all_sources["dom"] | all_sources["visual"]
        if not all_unique:
            return TriangulationResult(consensus=False, confidence=0.0)

        agreement_ratio = len(all_agree) / len(all_unique) if all_unique else 0.0
        pairwise = (len(a11y_dom) + len(a11y_vis) + len(dom_vis)) / (3 * len(all_unique)) if all_unique else 0.0

        confidence = (agreement_ratio * 0.6) + (pairwise * 0.4)
        consensus = confidence > 0.5

        return TriangulationResult(
            consensus=consensus,
            confidence=confidence,
            agreement_ratio=agreement_ratio,
            sources={"a11y": a11y_elements, "dom": dom_elements, "visual": visual_elements},
        )


# -- The Forge (CA -- Tool Creation + Site Memory) -----------------------------


class TheForge:
    """Kernel 3: Creates tools, maintains site logs, manages RAG pipeline."""

    def __init__(self, site_log_store: Optional[SiteLogStore] = None):
        self.site_log_store = site_log_store or SiteLogStore()
        self._tool_counter = 0

    def create_tool(
        self,
        domain: str,
        trigger: str,
        steps: List[Dict[str, Any]],
        ttl_hours: int = 72,
    ) -> ForgedTool:
        self._tool_counter += 1
        tool_id = f"forged-{domain.replace('.', '-')}-{self._tool_counter}"
        tool = ForgedTool(
            tool_id=tool_id,
            domain=domain,
            trigger=trigger,
            action_sequence=steps,
            created_by="judge_randomtest",
            ttl_hours=ttl_hours,
        )
        # Register in site log
        log = self.site_log_store.get_or_create(domain)
        if tool_id not in log.custom_tools:
            log.custom_tools.append(tool_id)
        return tool


# -- The Octopus (Tri-Kernel Orchestrator) -------------------------------------


class OctopusKernel:
    """Main orchestrator: routes tasks through Eye -> Judge -> Forge -> Tentacles."""

    def __init__(self, site_log_dir: str = "artifacts/site_logs"):
        self.site_log_store = SiteLogStore(base_dir=site_log_dir)
        self.eye = TheEye()
        self.judge = TheJudge()
        self.forge = TheForge(site_log_store=self.site_log_store)

    def select_mode(self, domain: str, action: str) -> str:
        sens = domain_sensitivity(domain)
        # Infer auth from explicit high-sensitivity domains and write-type actions
        high_risk_actions = ("submit", "pay", "upload", "execute_script")
        auth_required = sens >= 0.7 or (sens > 0.3 and action in high_risk_actions)
        # Data sensitivity mirrors domain for known domains, stays low for unknown
        data_sens = sens if sens != 0.5 else 0.1  # 0.5 is the default/unknown
        phi = compute_phi_weight(
            domain_sensitivity=sens,
            action_type=action,
            data_sensitivity=data_sens,
            auth_required=auth_required,
        )
        return select_mode(phi)

    async def execute_mock(
        self,
        task: str,
        domain: str,
        action: str = "read",
    ) -> ExecutionResult:
        start = time.time()
        mode = self.select_mode(domain, action)
        result = ExecutionResult(mode=mode, success=True)

        if mode == "sightless":
            result.data = f"Sightless scrape of {domain}"
        elif mode == "visual":
            vision = await self.eye.observe_mock(
                url=f"https://{domain}",
                page_text=task,
            )
            result.vision = vision
            result.data = f"Visual observation: {vision.page_type}"
        elif mode in ("full_octopus", "governed_critical"):
            vision = await self.eye.observe_mock(
                url=f"https://{domain}",
                page_text=task,
            )
            tri = await self.judge.triangulate(
                a11y_elements=[e.get("name", "") for e in vision.interactive_elements],
                dom_elements=[e.get("name", "") for e in vision.interactive_elements],
                visual_elements=[e.get("name", "") for e in vision.interactive_elements],
            )
            result.vision = vision
            result.triangulation = tri

        # Update site log
        log = self.site_log_store.get_or_create(domain)
        log.record_visit(
            path=[f"https://{domain}"],
            success=result.success,
            time_ms=int((time.time() - start) * 1000),
        )

        result.elapsed_ms = int((time.time() - start) * 1000)
        return result
