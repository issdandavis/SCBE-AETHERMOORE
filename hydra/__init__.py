"""
SCBE HYDRA System
=================

"Many Heads, One Governed Body"

A universal AI armor that any AI can wear - Claude, Codex, GPT, local LLMs.
Terminal-native with multi-tab browser support and central ledger.

Research Validation:
- SentinelAgent (2025) - Graph Fourier anomaly detection
- ML-KEM/ML-DSA (FIPS 203/204) - Quantum-resistant crypto
- SwarmRaft (2025) - Byzantine consensus f<n/3
- Spectral Regularization (2024) - Adversarial robustness

Components:
- HydraSpine: Central coordinator (terminal API)
- HydraHead: Interface for any AI to connect
- HydraLimb: Execution backends (browser, terminal, API)
- Librarian: Central ledger manager with cross-session memory
- Ledger: SQLite-based action/decision history
- Spectral: Graph Fourier analysis for anomaly detection
- Consensus: Byzantine fault-tolerant voting
"""

from .spine import HydraSpine
from .head import HydraHead, create_claude_head, create_codex_head, create_gpt_head, create_local_head
from .limbs import BrowserLimb, TerminalLimb, APILimb, MultiTabBrowserLimb
from .librarian import Librarian, MemoryQuery, MemoryResult
from .arxiv_retrieval import (
    ArxivClient,
    ArxivSearchResult,
    ArxivPaper,
    AI2AIRetrievalService,
    ArxivAPIError,
)
from .ledger import Ledger, LedgerEntry, EntryType
from .spectral import (
    GraphFourierAnalyzer,
    ByzantineDetector,
    SpectralAnomaly,
    analyze_hydra_system,
)
from .consensus import (
    ByzantineConsensus,
    RoundtableConsensus,
    Vote,
    Proposal,
    ConsensusResult,
    VoteDecision,
)
from .websocket_manager import (
    WebSocketManager,
    WebSocketClient,
    SubscriptionChannel,
    ClientState,
    create_websocket_manager,
    run_websocket_server,
)
from .swarm_governance import (
    SwarmGovernance,
    SwarmAgent,
    AgentRole,
    AgentState,
    GovernanceConfig,
    AutonomousCodeAgent,
    create_swarm_governance,
    create_autonomous_coder,
    simulate_swarm_attack,
)
from .switchboard import Switchboard
from .research import (
    ResearchOrchestrator,
    ResearchConfig,
    ResearchReport,
    ResearchSubTask,
    ResearchSource,
)
from .llm_providers import (
    LLMProvider,
    LLMResponse,
    ClaudeProvider,
    OpenAIProvider,
    GeminiProvider,
    LocalProvider,
    create_provider,
    HYDRA_SYSTEM_PROMPT,
)
from .hf_summarizer import HFSummarizer
from .browsers import BrowserBackend, PlaywrightBackend, SeleniumBackend, CDPBackend
from .swarm_browser import SwarmBrowser, AGENTS as SWARM_AGENTS
from .llm_providers import HuggingFaceProvider
from .extensions import (
    ColabLimb,
    VertexLimb,
    ZapierLimb,
    N8nLimb,
    TelegramLimb,
    PlaywrightCloudLimb,
    ExtensionRegistry,
    register_all_extensions,
)
from .model_hub import ModelHub, HeadConfig, ModelState
from .multi_screen_swarm import MultiScreenSwarm, CrossTalkBus, AgentScreen, DimensionalState as SwarmDimensionalState
from .self_healing import SelfHealingMesh, ServiceNode, ServiceHealth, ServiceCategory
from .training_funnel import TrainingFunnel, SFTPair, DPOTriple

__all__ = [
    # Core
    "HydraSpine",
    "HydraHead",
    "create_claude_head",
    "create_codex_head",
    "create_gpt_head",
    # Limbs
    "BrowserLimb",
    "TerminalLimb",
    "APILimb",
    "MultiTabBrowserLimb",
    # Memory + Retrieval
    "Librarian",
    "MemoryQuery",
    "MemoryResult",
    "ArxivClient",
    "ArxivSearchResult",
    "ArxivPaper",
    "AI2AIRetrievalService",
    "ArxivAPIError",
    "Ledger",
    "LedgerEntry",
    "EntryType",
    # Spectral Analysis (GFSS)
    "GraphFourierAnalyzer",
    "ByzantineDetector",
    "SpectralAnomaly",
    "analyze_hydra_system",
    # Consensus
    "ByzantineConsensus",
    "RoundtableConsensus",
    "Vote",
    "Proposal",
    "ConsensusResult",
    "VoteDecision",
    # WebSocket (Phase 1 Q2 2026)
    "WebSocketManager",
    "WebSocketClient",
    "SubscriptionChannel",
    "ClientState",
    "create_websocket_manager",
    "run_websocket_server",
    # Swarm Governance (Phase 1 Q2 2026)
    "SwarmGovernance",
    "SwarmAgent",
    "AgentRole",
    "AgentState",
    "GovernanceConfig",
    "AutonomousCodeAgent",
    "create_swarm_governance",
    "create_autonomous_coder",
    "simulate_swarm_attack",
    # Switchboard
    "Switchboard",
    # Research
    "ResearchOrchestrator",
    "ResearchConfig",
    "ResearchReport",
    "ResearchSubTask",
    "ResearchSource",
    "HFSummarizer",
    # LLM Providers
    "LLMProvider",
    "LLMResponse",
    "ClaudeProvider",
    "OpenAIProvider",
    "GeminiProvider",
    "HuggingFaceProvider",
    "LocalProvider",
    "create_provider",
    "HYDRA_SYSTEM_PROMPT",
    # Browser Backends
    "BrowserBackend",
    "PlaywrightBackend",
    "SeleniumBackend",
    "CDPBackend",
    # Swarm Browser
    "SwarmBrowser",
    "SWARM_AGENTS",
    # Extensions — Compute & Orchestration Limbs
    "ColabLimb",
    "VertexLimb",
    "ZapierLimb",
    "N8nLimb",
    "TelegramLimb",
    "PlaywrightCloudLimb",
    "ExtensionRegistry",
    "register_all_extensions",
    # Model Hub
    "ModelHub",
    "HeadConfig",
    "ModelState",
    # Multi-Screen Swarm
    "MultiScreenSwarm",
    "CrossTalkBus",
    "AgentScreen",
    "SwarmDimensionalState",
    # Self-Healing Mesh
    "SelfHealingMesh",
    "ServiceNode",
    "ServiceHealth",
    "ServiceCategory",
    # Training Funnel
    "TrainingFunnel",
    "SFTPair",
    "DPOTriple",
]

__version__ = "1.4.0"
