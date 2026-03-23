"""
SCBE HYDRA System
=================

"Many Heads, One Governed Body"

A universal AI armor that any AI can wear - Claude, Codex, GPT, local LLMs.
Terminal-native with multi-tab browser support and central ledger.

Components loaded lazily to avoid import hangs from heavy dependencies
(playwright, websockets, LLM SDKs, scipy).

Core modules (spine, ledger, switchboard) load eagerly.
Everything else loads on first access.
"""

import importlib as _importlib

# ═══════════════════════════════════════════════════════════
# Eager imports — core modules only (sqlite, dataclasses, stdlib)
# ═══════════════════════════════════════════════════════════

from .ledger import Ledger, LedgerEntry, EntryType
from .switchboard import Switchboard

# ═══════════════════════════════════════════════════════════
# Lazy imports — heavy modules (browsers, LLM providers, websockets)
# ═══════════════════════════════════════════════════════════

_LAZY_MODULES = {
    # Spine (imports crypto)
    "HydraSpine": ".spine",
    # Head
    "HydraHead": ".head",
    "create_claude_head": ".head",
    "create_codex_head": ".head",
    "create_gpt_head": ".head",
    "create_local_head": ".head",
    # Limbs
    "BrowserLimb": ".limbs",
    "TerminalLimb": ".limbs",
    "APILimb": ".limbs",
    "MultiTabBrowserLimb": ".limbs",
    # Memory
    "Librarian": ".librarian",
    "MemoryQuery": ".librarian",
    "MemoryResult": ".librarian",
    # arXiv
    "ArxivClient": ".arxiv_retrieval",
    "ArxivSearchResult": ".arxiv_retrieval",
    "ArxivPaper": ".arxiv_retrieval",
    "AI2AIRetrievalService": ".arxiv_retrieval",
    "ArxivAPIError": ".arxiv_retrieval",
    # Spectral
    "GraphFourierAnalyzer": ".spectral",
    "ByzantineDetector": ".spectral",
    "SpectralAnomaly": ".spectral",
    "analyze_hydra_system": ".spectral",
    # Consensus
    "ByzantineConsensus": ".consensus",
    "RoundtableConsensus": ".consensus",
    "Vote": ".consensus",
    "Proposal": ".consensus",
    "ConsensusResult": ".consensus",
    "VoteDecision": ".consensus",
    # WebSocket
    "WebSocketManager": ".websocket_manager",
    "WebSocketClient": ".websocket_manager",
    "SubscriptionChannel": ".websocket_manager",
    "ClientState": ".websocket_manager",
    "create_websocket_manager": ".websocket_manager",
    "run_websocket_server": ".websocket_manager",
    # Swarm Governance
    "SwarmGovernance": ".swarm_governance",
    "SwarmAgent": ".swarm_governance",
    "AgentRole": ".swarm_governance",
    "AgentState": ".swarm_governance",
    "GovernanceConfig": ".swarm_governance",
    "AutonomousCodeAgent": ".swarm_governance",
    "create_swarm_governance": ".swarm_governance",
    "create_autonomous_coder": ".swarm_governance",
    "simulate_swarm_attack": ".swarm_governance",
    # Research
    "ResearchOrchestrator": ".research",
    "ResearchConfig": ".research",
    "ResearchReport": ".research",
    "ResearchSubTask": ".research",
    "ResearchSource": ".research",
    # LLM Providers
    "LLMProvider": ".llm_providers",
    "LLMResponse": ".llm_providers",
    "ClaudeProvider": ".llm_providers",
    "OpenAIProvider": ".llm_providers",
    "GeminiProvider": ".llm_providers",
    "HuggingFaceProvider": ".llm_providers",
    "LocalProvider": ".llm_providers",
    "create_provider": ".llm_providers",
    "HYDRA_SYSTEM_PROMPT": ".llm_providers",
    # HF Summarizer
    "HFSummarizer": ".hf_summarizer",
    # Browsers
    "BrowserBackend": ".browsers",
    "PlaywrightBackend": ".browsers",
    "SeleniumBackend": ".browsers",
    "CDPBackend": ".browsers",
    # Swarm Browser
    "SwarmBrowser": ".swarm_browser",
    "SWARM_AGENTS": ".swarm_browser",
}


def __getattr__(name: str):
    if name in _LAZY_MODULES:
        mod = _importlib.import_module(_LAZY_MODULES[name], package=__name__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__version__ = "1.3.0"
