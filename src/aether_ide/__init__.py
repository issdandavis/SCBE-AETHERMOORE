"""AetherIDE -- Self-improving IDE with SCBE governance.

Every IDE action passes through the TernaryHybridEncoder pipeline.
Built on existing PollyPad, HydraSpine, ModelMatrix, SemanticMesh,
and n8n bridge components.

@layer Layer 1-14
@component AetherIDE
"""

from src.aether_ide.types import IDEAction, IDEEvent, IDEConfig, SessionState
from src.aether_ide.session import AetherIDESession
from src.aether_ide.editor import GovernedEditor
from src.aether_ide.chat import IDEChat
from src.aether_ide.spin_engine import SpinEngine
from src.aether_ide.code_search import GovernedCodeSearch
from src.aether_ide.workflow import WorkflowTrigger
from src.aether_ide.self_improve import SelfImproveLoop

__all__ = [
    "AetherIDESession",
    "GovernedEditor",
    "IDEChat",
    "SpinEngine",
    "GovernedCodeSearch",
    "WorkflowTrigger",
    "SelfImproveLoop",
    "IDEAction",
    "IDEEvent",
    "IDEConfig",
    "SessionState",
]
