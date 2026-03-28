"""
Polly Vision — The Observation Window
=======================================

Gives each Polly bot (HydraHand finger) the ability to **see** web pages,
not just blindly extract text.  This is the SAO Alicization "monitoring
rectangle" — a small rendered viewport the AI peeks through for navigation.

Perception Tiers (research-backed, Feb 2026):
    Tier 1 — Accessibility tree only (fast, cheap, 200-500 tokens)
    Tier 2 — Accessibility tree + selective screenshots (production default)
    Tier 3 — Full screenshot with Set-of-Marks overlay (visual tasks)

Architecture:
    HydraHand.finger(Tongue.AV)  ──► PollyVision.observe()
         │                                   │
         │  Playwright page reference         ▼
         │                          ┌─────────────────┐
         └─────────────────────────►│  Accessibility   │
                                    │  Tree Snapshot   │
                                    ├─────────────────┤
                                    │  Screenshot      │ ◄── only when needed
                                    │  (PNG bytes)     │
                                    ├─────────────────┤
                                    │  Set-of-Marks    │ ◄── numbered element overlay
                                    │  Annotation      │
                                    └─────────────────┘
                                            │
                                            ▼
                                    PageObservation (dataclass)

Integration:
    from src.browser.polly_vision import PollyVision, ObservationTier

    vision = PollyVision(tier=ObservationTier.TIER_2)
    obs = await vision.observe(page)
    # obs.accessibility_tree  — compact text representation
    # obs.screenshot_bytes    — PNG bytes (None if Tier 1)
    # obs.interactive_elements — list of clickable/typeable elements
    # obs.page_summary        — one-line description

Layer compliance:
    L5  — Hyperbolic distance scoring for navigation decisions
    L8  — Adversarial resilience (injection detection in page content)
    L13 — Governance gate on observed content
"""

from __future__ import annotations

import base64
import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("polly-vision")


# ── Observation Tiers ─────────────────────────────────────────────────


class ObservationTier(str, Enum):
    """How much visual context each Polly bot gets."""

    TIER_1 = "accessibility_only"  # Fast, cheap, text-based
    TIER_2 = "accessibility_plus"  # Default: a11y + screenshots when stuck
    TIER_3 = "full_visual"  # Every step gets a screenshot + SoM overlay


# ── Data Structures ───────────────────────────────────────────────────


@dataclass
class InteractiveElement:
    """A clickable/typeable element on the page."""

    ref_id: int  # Set-of-Marks number (e.g. [1], [2])
    role: str  # button, link, textbox, etc.
    name: str  # Accessible name
    tag: str  # HTML tag
    selector: str  # CSS selector for Playwright
    bounding_box: Optional[Dict[str, float]] = None  # {x, y, width, height}
    state: str = ""  # disabled, checked, expanded, etc.


@dataclass
class PageObservation:
    """Complete observation of a page — what a Polly bot 'sees'."""

    url: str
    title: str
    accessibility_tree: str  # Compact text representation
    interactive_elements: List[InteractiveElement]
    screenshot_bytes: Optional[bytes]  # PNG bytes (None for Tier 1)
    screenshot_b64: Optional[str]  # Base64 encoded (for LLM APIs)
    page_summary: str  # One-line description
    observation_tier: ObservationTier
    content_hash: str  # SHA-256 of a11y tree
    elapsed_ms: float
    token_estimate: int  # Estimated LLM tokens for this observation
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_screenshot(self) -> bool:
        return self.screenshot_bytes is not None

    @property
    def element_count(self) -> int:
        return len(self.interactive_elements)

    def get_element(self, ref_id: int) -> Optional[InteractiveElement]:
        """Get element by its Set-of-Marks reference number."""
        for el in self.interactive_elements:
            if el.ref_id == ref_id:
                return el
        return None

    def compact_repr(self) -> str:
        """Compact representation for LLM context (minimal tokens)."""
        lines = [f"Page: {self.title} ({self.url})"]
        for el in self.interactive_elements:
            state = f" [{el.state}]" if el.state else ""
            lines.append(f"  @{el.ref_id} {el.role}: {el.name}{state}")
        return "\n".join(lines)


# ── Polly Vision Engine ──────────────────────────────────────────────


class PollyVision:
    """
    The observation window for Polly bots.

    Wraps a Playwright page and provides structured perception:
    - Accessibility tree snapshots (always)
    - Screenshots (on-demand or always, depending on tier)
    - Set-of-Marks element annotation
    - Compact representations optimized for LLM context windows

    Usage:
        vision = PollyVision(tier=ObservationTier.TIER_2)
        obs = await vision.observe(page)
        print(obs.compact_repr())  # Minimal token representation
        element = obs.get_element(3)  # Get element @3
        await page.click(element.selector)
    """

    def __init__(
        self,
        tier: ObservationTier = ObservationTier.TIER_2,
        viewport_width: int = 1280,
        viewport_height: int = 720,
        max_elements: int = 50,
        screenshot_quality: int = 60,  # JPEG quality (lower = smaller)
    ):
        self.tier = tier
        self.viewport_width = viewport_width
        self.viewport_height = viewport_height
        self.max_elements = max_elements
        self.screenshot_quality = screenshot_quality

        # Session tracking
        self._observation_count = 0
        self._screenshot_count = 0
        self._total_tokens = 0

    async def observe(
        self,
        page,
        force_screenshot: bool = False,
        reason: str = "",
    ) -> PageObservation:
        """
        Observe the current page state.

        Args:
            page: Playwright page object
            force_screenshot: Take screenshot regardless of tier
            reason: Why this observation is needed (for logging)

        Returns:
            PageObservation with all perception data
        """
        start = time.monotonic()
        self._observation_count += 1

        # Always get title and URL
        try:
            title = await page.title()
        except Exception:
            title = ""
        url = page.url

        # Step 1: Get accessibility tree (always)
        a11y_tree, elements = await self._get_accessibility_snapshot(page)

        # Step 2: Screenshot (based on tier)
        screenshot_bytes = None
        screenshot_b64 = None
        take_screenshot = (
            self.tier == ObservationTier.TIER_3
            or force_screenshot
            or (self.tier == ObservationTier.TIER_2 and not elements)
        )

        if take_screenshot:
            screenshot_bytes, screenshot_b64 = await self._capture_screenshot(page)
            self._screenshot_count += 1

        # Step 3: Build content hash
        content_hash = hashlib.sha256(a11y_tree.encode()).hexdigest()[:16]

        # Step 4: Estimate tokens
        token_est = self._estimate_tokens(a11y_tree, screenshot_bytes)
        self._total_tokens += token_est

        # Step 5: Generate summary
        summary = self._generate_summary(title, url, elements)

        elapsed = (time.monotonic() - start) * 1000

        logger.debug(
            "observe: %s | %d elements | screenshot=%s | %.0fms | ~%d tokens",
            title[:40],
            len(elements),
            take_screenshot,
            elapsed,
            token_est,
        )

        return PageObservation(
            url=url,
            title=title,
            accessibility_tree=a11y_tree,
            interactive_elements=elements,
            screenshot_bytes=screenshot_bytes,
            screenshot_b64=screenshot_b64,
            page_summary=summary,
            observation_tier=self.tier,
            content_hash=content_hash,
            elapsed_ms=elapsed,
            token_estimate=token_est,
            metadata={"reason": reason, "obs_number": self._observation_count},
        )

    async def observe_and_annotate(self, page) -> PageObservation:
        """Observe with Set-of-Marks overlay injected into the page.

        Injects numbered labels onto interactive elements before taking
        a screenshot, so the AI can reference elements by number.
        This is Tier 3 perception — most expensive but most reliable
        for visual navigation.
        """
        # Inject SoM overlay
        await self._inject_som_overlay(page)

        # Observe with forced screenshot
        obs = await self.observe(page, force_screenshot=True, reason="set-of-marks")

        # Remove overlay after screenshot
        await self._remove_som_overlay(page)

        return obs

    # ── Accessibility Tree ────────────────────────────────────────────

    async def _get_accessibility_snapshot(
        self, page
    ) -> tuple[str, List[InteractiveElement]]:
        """Extract accessibility tree and interactive elements."""
        elements: List[InteractiveElement] = []
        tree_lines: List[str] = []

        try:
            # Get all interactive elements via Playwright's locator API
            interactive_roles = [
                "link",
                "button",
                "textbox",
                "checkbox",
                "radio",
                "combobox",
                "menuitem",
                "tab",
                "switch",
                "searchbox",
            ]

            ref_id = 1
            for role in interactive_roles:
                try:
                    locator = page.get_by_role(role)
                    count = await locator.count()
                    for i in range(min(count, self.max_elements - len(elements))):
                        if len(elements) >= self.max_elements:
                            break
                        try:
                            el = locator.nth(i)
                            name = await el.get_attribute("aria-label") or ""
                            if not name:
                                name = (
                                    (await el.inner_text())[:80]
                                    if role != "textbox"
                                    else ""
                                )
                            if not name:
                                name = await el.get_attribute("placeholder") or ""
                            if not name:
                                name = await el.get_attribute("title") or ""

                            tag = await el.evaluate("e => e.tagName.toLowerCase()")

                            # Build a reliable selector
                            test_id = await el.get_attribute("data-testid")
                            el_id = await el.get_attribute("id")
                            if test_id:
                                selector = f'[data-testid="{test_id}"]'
                            elif el_id:
                                selector = f"#{el_id}"
                            else:
                                selector = f"role={role} >> nth={i}"

                            # Get bounding box if visible
                            bbox = None
                            try:
                                box = await el.bounding_box()
                                if box:
                                    bbox = {
                                        "x": box["x"],
                                        "y": box["y"],
                                        "width": box["width"],
                                        "height": box["height"],
                                    }
                            except Exception:
                                pass

                            # Check state
                            state_parts = []
                            try:
                                if await el.is_disabled():
                                    state_parts.append("disabled")
                            except Exception:
                                pass
                            try:
                                if role in ("checkbox", "radio"):
                                    if await el.is_checked():
                                        state_parts.append("checked")
                            except Exception:
                                pass

                            element = InteractiveElement(
                                ref_id=ref_id,
                                role=role,
                                name=name.strip()[:100],
                                tag=tag,
                                selector=selector,
                                bounding_box=bbox,
                                state=" ".join(state_parts),
                            )
                            elements.append(element)
                            state_str = f" [{element.state}]" if element.state else ""
                            tree_lines.append(
                                f"@{ref_id} {role}: {element.name}{state_str}"
                            )
                            ref_id += 1
                        except Exception:
                            continue
                except Exception:
                    continue

        except Exception as e:
            tree_lines.append(f"[accessibility error: {e}]")

        tree_text = "\n".join(tree_lines) if tree_lines else "[empty page]"
        return tree_text, elements

    # ── Screenshot Capture ────────────────────────────────────────────

    async def _capture_screenshot(self, page) -> tuple[Optional[bytes], Optional[str]]:
        """Capture viewport screenshot as JPEG bytes + base64."""
        try:
            png_bytes = await page.screenshot(
                type="jpeg",
                quality=self.screenshot_quality,
                full_page=False,  # Viewport only (not full scroll)
            )
            b64 = base64.b64encode(png_bytes).decode("ascii")
            return png_bytes, b64
        except Exception as e:
            logger.warning("Screenshot failed: %s", e)
            return None, None

    # ── Set-of-Marks Overlay ──────────────────────────────────────────

    async def _inject_som_overlay(self, page) -> None:
        """Inject numbered labels onto interactive elements (Set-of-Marks)."""
        js = """
        () => {
            // Remove any existing overlay
            document.querySelectorAll('.polly-som-label').forEach(e => e.remove());

            const roles = ['a', 'button', 'input', 'select', 'textarea',
                           '[role="button"]', '[role="link"]', '[role="tab"]',
                           '[role="menuitem"]', '[role="checkbox"]'];
            const selector = roles.join(', ');
            const elements = document.querySelectorAll(selector);

            let refId = 1;
            elements.forEach(el => {
                if (refId > 50) return;
                const rect = el.getBoundingClientRect();
                if (rect.width === 0 || rect.height === 0) return;
                if (rect.top < 0 || rect.top > window.innerHeight) return;

                const label = document.createElement('div');
                label.className = 'polly-som-label';
                label.textContent = refId.toString();
                label.style.cssText = `
                    position: fixed;
                    left: ${rect.left - 2}px;
                    top: ${rect.top - 16}px;
                    background: #ff4444;
                    color: white;
                    font-size: 11px;
                    font-weight: bold;
                    padding: 1px 4px;
                    border-radius: 3px;
                    z-index: 999999;
                    pointer-events: none;
                    font-family: monospace;
                `;
                document.body.appendChild(label);
                refId++;
            });
        }
        """
        try:
            await page.evaluate(js)
        except Exception as e:
            logger.warning("SoM inject failed: %s", e)

    async def _remove_som_overlay(self, page) -> None:
        """Remove Set-of-Marks overlay labels."""
        try:
            await page.evaluate(
                "() => document.querySelectorAll('.polly-som-label').forEach(e => e.remove())"
            )
        except Exception:
            pass

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _estimate_tokens(a11y_tree: str, screenshot_bytes: Optional[bytes]) -> int:
        """Rough token estimate for LLM context planning."""
        # ~4 chars per token for text
        text_tokens = len(a11y_tree) // 4
        # Screenshot at 1280x720 JPEG ~85 tokens (low detail) to ~765 (high)
        image_tokens = 200 if screenshot_bytes else 0
        return text_tokens + image_tokens

    @staticmethod
    def _generate_summary(
        title: str, url: str, elements: List[InteractiveElement]
    ) -> str:
        """One-line page summary."""
        roles = {}
        for el in elements:
            roles[el.role] = roles.get(el.role, 0) + 1
        role_str = ", ".join(f"{c} {r}s" for r, c in roles.items())
        return f"{title} | {role_str}" if role_str else title or url

    # ── Session Stats ─────────────────────────────────────────────────

    @property
    def session_stats(self) -> Dict[str, Any]:
        return {
            "observations": self._observation_count,
            "screenshots": self._screenshot_count,
            "total_tokens_est": self._total_tokens,
            "tier": self.tier.value,
            "screenshot_rate": (
                self._screenshot_count / max(self._observation_count, 1)
            ),
        }
