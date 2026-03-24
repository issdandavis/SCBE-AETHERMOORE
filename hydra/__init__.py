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
try:
    from .arxiv_retrieval import (
        ArxivClient,
        ArxivSearchResult,
        ArxivPaper,
        AI2AIRetrievalService,
        ArxivAPIError,
    )
except ImportError:
    # httpx may not be installed; arxiv_retrieval is optional
    ArxivClient = None  # type: ignore[assignment,misc]
    ArxivSearchResult = None  # type: ignore[assignment,misc]
    ArxivPaper = None  # type: ignore[assignment,misc]
    AI2AIRetrievalService = None  # type: ignore[assignment,misc]
    ArxivAPIError = None  # type: ignore[assignment,misc]
from .ledger import Ledger, LedgerEntry, EntryType
try:
    from .spectral import (
        GraphFourierAnalyzer,
        ByzantineDetector,
        SpectralAnomaly,
        analyze_hydra_system,
    )
except ImportError:
    # numpy may not be installed; spectral analysis is optional
    GraphFourierAnalyzer = None  # type: ignore[assignment,misc]
    ByzantineDetector = None  # type: ignore[assignment,misc]
    SpectralAnomaly = None  # type: ignore[assignment,misc]
    analyze_hydra_system = None  # type: ignore[assignment,misc]
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
try:
    from .research import (
        ResearchOrchestrator,
        ResearchConfig,
        ResearchReport,
        ResearchSubTask,
        ResearchSource,
    )
except ImportError:
    # httpx may not be installed; research orchestrator is optional
    ResearchOrchestrator = None  # type: ignore[assignment,misc]
    ResearchConfig = None  # type: ignore[assignment,misc]
    ResearchReport = None  # type: ignore[assignment,misc]
    ResearchSubTask = None  # type: ignore[assignment,misc]
    ResearchSource = None  # type: ignore[assignment,misc]
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
]

__version__ = "1.3.0"
