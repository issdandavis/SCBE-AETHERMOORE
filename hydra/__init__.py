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
from .ledger import Ledger, LedgerEntry, EntryType

# --- Optional imports: modules with heavy dependencies (numpy, httpx, etc.) ---
# Wrapped in try/except so that missing optional deps don't break the entire package.

try:
    from .arxiv_retrieval import (
        ArxivClient, ArxivSearchResult, ArxivPaper,
        AI2AIRetrievalService, ArxivAPIError,
    )
except ImportError:
    ArxivClient = ArxivSearchResult = ArxivPaper = None
    AI2AIRetrievalService = ArxivAPIError = None

try:
    from .spectral import (
        GraphFourierAnalyzer, ByzantineDetector,
        SpectralAnomaly, analyze_hydra_system,
    )
except ImportError:
    GraphFourierAnalyzer = ByzantineDetector = SpectralAnomaly = None
    analyze_hydra_system = None

try:
    from .consensus import (
        ByzantineConsensus, RoundtableConsensus,
        Vote, Proposal, ConsensusResult, VoteDecision,
    )
except ImportError:
    ByzantineConsensus = RoundtableConsensus = None
    Vote = Proposal = ConsensusResult = VoteDecision = None

try:
    from .websocket_manager import (
        WebSocketManager, WebSocketClient, SubscriptionChannel,
        ClientState, create_websocket_manager, run_websocket_server,
    )
except ImportError:
    WebSocketManager = WebSocketClient = SubscriptionChannel = None
    ClientState = create_websocket_manager = run_websocket_server = None

try:
    from .swarm_governance import (
        SwarmGovernance, SwarmAgent, AgentRole, AgentState,
        GovernanceConfig, AutonomousCodeAgent,
        create_swarm_governance, create_autonomous_coder, simulate_swarm_attack,
    )
except ImportError:
    SwarmGovernance = SwarmAgent = AgentRole = AgentState = None
    GovernanceConfig = AutonomousCodeAgent = None
    create_swarm_governance = create_autonomous_coder = simulate_swarm_attack = None

try:
    from .switchboard import Switchboard
except ImportError:
    Switchboard = None

try:
    from .research import (
        ResearchOrchestrator, ResearchConfig, ResearchReport,
        ResearchSubTask, ResearchSource,
    )
except ImportError:
    ResearchOrchestrator = ResearchConfig = ResearchReport = None
    ResearchSubTask = ResearchSource = None

try:
    from .llm_providers import (
        LLMProvider, LLMResponse, ClaudeProvider, OpenAIProvider,
        GeminiProvider, LocalProvider, create_provider, HYDRA_SYSTEM_PROMPT,
    )
except ImportError:
    LLMProvider = LLMResponse = ClaudeProvider = OpenAIProvider = None
    GeminiProvider = LocalProvider = create_provider = HYDRA_SYSTEM_PROMPT = None

try:
    from .hf_summarizer import HFSummarizer
except ImportError:
    HFSummarizer = None

try:
    from .browsers import BrowserBackend, PlaywrightBackend, SeleniumBackend, CDPBackend
except ImportError:
    BrowserBackend = PlaywrightBackend = SeleniumBackend = CDPBackend = None

try:
    from .swarm_browser import SwarmBrowser, AGENTS as SWARM_AGENTS
except ImportError:
    SwarmBrowser = None
    SWARM_AGENTS = None

try:
    from .llm_providers import HuggingFaceProvider
except ImportError:
    HuggingFaceProvider = None

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
