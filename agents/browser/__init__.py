"""
@file __init__.py
@module agents/browser
@layer Layer 5, Layer 12, Layer 13
@component Geometrically-Contained Browser Agent
@version 1.0.0

Browser agent with provable geometric containment using Poincaré ball model.

Core components:
- SimplePHDM: Poincaré Hyperbolic Distance Model for safety containment
- PlaywrightWrapper: Safe browser automation with timeouts
- VisionEmbedder: CLIP to Poincaré ball projection
- FastAPI app: /v1/browse endpoint

Safety guarantee:
Actions are only executed if their embeddings fall within the safe radius (0.92)
of the Poincaré ball. This creates provable geometric containment where
adversarial drift becomes exponentially more costly.

Example usage:
    from agents.browser import SimplePHDM, create_phdm_brain

    # Create PHDM brain
    brain = create_phdm_brain(safe_radius=0.92, dim=16)

    # Check if action is safe
    embedding = some_embedding_vector  # 16-dimensional
    if brain.is_safe(embedding):
        execute_action()
    else:
        block_action()

    # Or use full containment check with governance decision
    result = brain.check_containment(embedding)
    if result.decision == SafetyDecision.ALLOW:
        execute_action()

Run server:
    python -m uvicorn agents.browser.main:app --host 0.0.0.0 --port 8001
"""

from .phdm_brain import (
    SimplePHDM,
    SafetyDecision,
    ContainmentResult,
    create_phdm_brain,
    EPSILON,
    PHI,
)

from .playwright_wrapper import (
    PlaywrightWrapper,
    BrowserConfig,
    BrowserAction,
    BrowserActionType,
    ScreenshotResult,
    create_browser,
)

from .vision_embedding import (
    VisionEmbedder,
    EmbeddingResult,
    create_vision_embedder,
)

from .main import app

__all__ = [
    # PHDM Brain
    "SimplePHDM",
    "SafetyDecision",
    "ContainmentResult",
    "create_phdm_brain",
    "EPSILON",
    "PHI",
    # Browser Wrapper
    "PlaywrightWrapper",
    "BrowserConfig",
    "BrowserAction",
    "BrowserActionType",
    "ScreenshotResult",
    "create_browser",
    # Vision Embedding
    "VisionEmbedder",
    "EmbeddingResult",
    "create_vision_embedder",
    # FastAPI App
    "app",
]

__version__ = "1.0.0"
