"""
SCBE Web Agent — Autonomous Web Navigation Service
====================================================

Deployable AI agent that operates on the web under SCBE-AETHERMOORE
14-layer governance.  Integrates concept blocks (DECIDE/PLAN/SENSE/STEER/
COORDINATE), Polly Pad actuators, semantic antivirus membrane, and CSTM
personality kernels.

Modules
-------
- ``semantic_antivirus`` — Content scanning + prompt injection + governance gate
- ``web_polly_pad``      — Browser actuator: goals → actions, recovery on stuck
- ``navigation_engine``  — Combines PLAN + SENSE + STEER + DECIDE for web nav
- ``agent_orchestrator``  — Long-running task management + state persistence
- ``task_api``           — REST API for submitting/monitoring web tasks
- ``federated_deploy``   — Flower client for distributed training/deployment
- ``tongue_transport``   — Sacred Tongue encoding + GeoSeal for agent-to-agent comms
"""

from .semantic_antivirus import (
    ContentVerdict,
    SemanticAntivirus,
    ThreatProfile,
)
from .web_polly_pad import (
    BrowserAction,
    PadMode,
    RecoveryStrategy,
    WebPollyPad,
)
from .navigation_engine import (
    NavigationEngine,
    NavigationState,
    PageUnderstanding,
)
from .agent_orchestrator import (
    AgentOrchestrator,
    WebTask,
    TaskStatus,
    TaskResult,
)
from .buffer_integration import (
    ContentBuffer,
    Platform,
    PlatformPublisher,
    PostContent,
    PostStatus,
    ScheduledPost,
    PublishResult,
)
from .publishers import (
    TwitterPublisher,
    LinkedInPublisher,
    BlueskyPublisher,
    MastodonPublisher,
    WordPressPublisher,
    MediumPublisher,
    GitHubPublisher,
    HuggingFacePublisher,
    CustomAPIPublisher,
    create_publisher,
)

__all__ = [
    "SemanticAntivirus", "ContentVerdict", "ThreatProfile",
    "WebPollyPad", "BrowserAction", "PadMode", "RecoveryStrategy",
    "NavigationEngine", "NavigationState", "PageUnderstanding",
    "AgentOrchestrator", "WebTask", "TaskStatus", "TaskResult",
    "ContentBuffer", "Platform", "PlatformPublisher",
    "PostContent", "PostStatus", "ScheduledPost", "PublishResult",
    "TwitterPublisher", "LinkedInPublisher", "BlueskyPublisher",
    "MastodonPublisher", "WordPressPublisher", "MediumPublisher",
    "GitHubPublisher", "HuggingFacePublisher", "CustomAPIPublisher",
    "create_publisher",
    "TongueTransport", "TongueEnvelope",
]

# Lazy import for tongue_transport (requires six-tongues-cli.py at project root)
def __getattr__(name):
    if name in ("TongueTransport", "TongueEnvelope"):
        from .tongue_transport import TongueTransport, TongueEnvelope
        globals()["TongueTransport"] = TongueTransport
        globals()["TongueEnvelope"] = TongueEnvelope
        return globals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
