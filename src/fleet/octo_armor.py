"""
OctoArmor — HYDRA Multi-Tentacle AI Connector Hub
==================================================

Eight tentacles of the HYDRA octopus, each reaching to free AI providers.
Polly the raven flies above, observing all interactions and building
the mind map. Every interaction generates training data that flows
back to HuggingFace, creating a self-improving flywheel.

Architecture::

    ┌─────── POLLY (Raven Observer) ───────┐
    │  Watches all traffic, builds mind map │
    │  Logs training pairs, quality scores  │
    └──────────────┬───────────────────────┘
                   │
    ┌──────── HYDRA CORE ────────┐
    │   SCBE Tokenizer Gateway   │
    │   Sacred Tongue Encoding   │
    │   Octree Knowledge Index   │
    └────────┬─────────┬─────────┘
             │ TENTACLES │
    ┌────────┴─────────┴─────────┐
    │ Groq  Cerebras  Mistral    │
    │ OpenRouter  Google  Cohere │
    │ GitHub  Cloudflare  +more  │
    └────────────────────────────┘

The Everweave game lore seeds the tokenizer.
The logs ARE the training data.
Every use makes the model smarter.

@module fleet/octo_armor
@layer Layer 5, Layer 13, Layer 14
@patent USPTO #63/961,403
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .switchboard import NoticeBoard, TaskType, CostTier, classify_task
from src.security.secret_store import pick_secret


def _pick_provider_secret(*names: str) -> Optional[str]:
    """Read a provider key from local secret store first, then env fallback."""
    for name in names:
        if not name:
            continue
        env_value = os.environ.get(name)
        if env_value and str(env_value).strip():
            return str(env_value).strip()

    for name in names:
        if not name:
            continue
        if os.environ.get(name) == "":
            continue
        _, value = pick_secret(name)
        if value:
            return value

    return None


# ═══════════════════════════════════════════════════════════════
# Free Provider Registry — All the tentacles
# ═══════════════════════════════════════════════════════════════

class Tentacle(str, Enum):
    """Each tentacle reaches to a free AI provider."""
    GROQ = "groq"
    CEREBRAS = "cerebras"
    MISTRAL_FREE = "mistral_free"
    OPENROUTER = "openrouter"
    GOOGLE_AI = "google_ai"
    COHERE = "cohere"
    GITHUB_MODELS = "github_models"
    CLOUDFLARE = "cloudflare"
    TOGETHER = "together"
    SAMBANOVA = "sambanova"
    DEEPINFRA = "deepinfra"
    NVIDIA_NIM = "nvidia_nim"
    NOVITA = "novita"
    FIREWORKS = "fireworks"
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"           # Local
    XAI = "xai"                 # Paid (user's Grok)
    GROK_CLI = "grok_cli"       # Local CLI (grok-cli npm package)
    CLAUDE = "claude"           # Paid (user's Anthropic)
    OPENAI = "openai"           # Paid (user's ChatGPT)
    GOOGLE_VERTEX = "google_vertex"  # Paid (user's Google Cloud)


@dataclass
class TentacleConfig:
    """Configuration for a single HYDRA tentacle (provider connector)."""
    tentacle: Tentacle
    base_url: str
    api_key_env: str            # Environment variable name for key
    default_model: str
    free_models: List[str]      # Models available on free tier
    rate_limit_rpm: int = 30    # Requests per minute
    rate_limit_rpd: int = 1000  # Requests per day
    daily_token_limit: int = 500_000
    openai_compatible: bool = True
    cost_per_1k: float = 0.0   # Free = 0
    notes: str = ""

    @property
    def api_key(self) -> Optional[str]:
        if not self.api_key_env:
            return None
        envs = [self.api_key_env]
        if self.tentacle == Tentacle.HUGGINGFACE:
            envs.extend(["HUGGINGFACE_TOKEN", "HF_HUB_TOKEN"])
        elif self.tentacle == Tentacle.CLOUDFLARE:
            envs.append("CLOUDFLARE_TOKEN")
        elif self.tentacle == Tentacle.GITHUB_MODELS:
            envs.append("GITHUB_PAT")
        elif self.tentacle == Tentacle.GROK_CLI:
            envs.extend(["GROK_API_KEY", "XAI_API_KEY"])
        return _pick_provider_secret(*envs)

    @property
    def available(self) -> bool:
        if not self.api_key_env:
            return True  # No key needed (Ollama)
        if self.tentacle == Tentacle.GROK_CLI:
            if not shutil.which("grok"):
                return False
            if self.api_key:
                return True
            # Fallback path: allow preconfigured grok key in user settings file.
            grok_settings = Path.home() / ".grok" / "user-settings.json"
            if grok_settings.exists():
                try:
                    obj = json.loads(grok_settings.read_text(encoding="utf-8"))
                    if isinstance(obj, dict):
                        return bool(str(obj.get("apiKey", "")).strip())
                except Exception:
                    return False
            return False
        return bool(self.api_key)


# All free provider configurations
TENTACLE_REGISTRY: Dict[Tentacle, TentacleConfig] = {
    Tentacle.GROQ: TentacleConfig(
        tentacle=Tentacle.GROQ,
        base_url="https://api.groq.com/openai/v1/",
        api_key_env="GROQ_API_KEY",
        default_model="llama-3.3-70b-versatile",
        free_models=[
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "meta-llama/llama-4-scout-17b-16e-instruct",
            "qwen/qwen3-32b",
            "moonshotai/kimi-k2-instruct",
            "openai/gpt-oss-120b",
        ],
        rate_limit_rpm=30,
        rate_limit_rpd=14400,
        daily_token_limit=500_000,
        notes="Fastest inference (LPU). Permanent free tier.",
    ),
    Tentacle.CEREBRAS: TentacleConfig(
        tentacle=Tentacle.CEREBRAS,
        base_url="https://api.cerebras.ai/v1/",
        api_key_env="CEREBRAS_API_KEY",
        default_model="llama-3.3-70b",
        free_models=[
            "llama-3.3-70b",
            "llama-3.1-8b",
            "qwen3-235b-a22b",
            "gpt-oss-120b",
        ],
        rate_limit_rpm=30,
        daily_token_limit=1_000_000,
        notes="Wafer-scale, ~3000 tok/sec. Permanent free tier.",
    ),
    Tentacle.MISTRAL_FREE: TentacleConfig(
        tentacle=Tentacle.MISTRAL_FREE,
        base_url="https://api.mistral.ai/v1/",
        api_key_env="MISTRAL_API_KEY",
        default_model="mistral-small-latest",
        free_models=[
            "mistral-small-latest",
            "mistral-large-latest",
            "codestral-latest",
            "open-mistral-7b",
            "open-mixtral-8x7b",
        ],
        rate_limit_rpm=2,         # Very slow RPS on free
        daily_token_limit=30_000_000,  # ~1B/month
        notes="1B tokens/month but ~2 RPM. Best for async/batch.",
    ),
    Tentacle.OPENROUTER: TentacleConfig(
        tentacle=Tentacle.OPENROUTER,
        base_url="https://openrouter.ai/api/v1/",
        api_key_env="OPENROUTER_API_KEY",
        default_model="meta-llama/llama-3.3-70b-instruct:free",
        free_models=[
            "meta-llama/llama-3.3-70b-instruct:free",
            "qwen/qwen3-coder:free",
            "nousresearch/hermes-3-llama-3.1-405b:free",
            "openai/gpt-oss-120b:free",
            "google/gemma-3-27b-it:free",
            "mistralai/mistral-small-3.1-24b-instruct:free",
            "qwen/qwen3-235b-a22b-thinking-2507:free",
            "openrouter/free",
        ],
        rate_limit_rpm=20,
        rate_limit_rpd=50,        # 50/day without purchase
        notes="29 free models. Best variety. Append :free to model ID.",
    ),
    Tentacle.GOOGLE_AI: TentacleConfig(
        tentacle=Tentacle.GOOGLE_AI,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key_env="GOOGLE_AI_API_KEY",
        default_model="gemini-2.5-flash",
        free_models=[
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemma-3-27b-it",
        ],
        rate_limit_rpm=10,
        rate_limit_rpd=250,
        daily_token_limit=250_000,
        notes="Best overall free tier. 1M context. Multimodal.",
    ),
    Tentacle.COHERE: TentacleConfig(
        tentacle=Tentacle.COHERE,
        base_url="https://api.cohere.com/v2/",
        api_key_env="COHERE_API_KEY",
        default_model="command-r-plus",
        free_models=[
            "command-a-03-2025",
            "command-r-plus",
            "command-r",
            "embed-v4.0",
            "rerank-v3.5",
        ],
        rate_limit_rpm=20,
        rate_limit_rpd=33,  # ~1000/month
        openai_compatible=False,
        notes="1000 req/month. Includes embeddings + reranking for RAG.",
    ),
    Tentacle.GITHUB_MODELS: TentacleConfig(
        tentacle=Tentacle.GITHUB_MODELS,
        base_url="https://models.inference.ai.azure.com/",
        api_key_env="GITHUB_TOKEN",
        default_model="gpt-4o",
        free_models=[
            "gpt-4o",
            "DeepSeek-R1",
            "Meta-Llama-3.1-405B-Instruct",
            "Mistral-Large",
        ],
        rate_limit_rpm=10,
        rate_limit_rpd=50,
        notes="Uses GitHub PAT. Restrictive token limits. Good for testing.",
    ),
    Tentacle.CLOUDFLARE: TentacleConfig(
        tentacle=Tentacle.CLOUDFLARE,
        base_url="https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/",
        api_key_env="CLOUDFLARE_API_KEY",
        default_model="@cf/meta/llama-3.3-70b-instruct-fp8-fast",
        free_models=[
            "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
            "@cf/mistral/mistral-small-3.1-24b-instruct",
            "@cf/qwen/qwen2.5-72b-instruct",
        ],
        rate_limit_rpd=10000,
        openai_compatible=False,  # Partial — has gateway mode
        notes="10K neurons/day. 50+ models. Includes image gen.",
    ),
    Tentacle.TOGETHER: TentacleConfig(
        tentacle=Tentacle.TOGETHER,
        base_url="https://api.together.xyz/v1/",
        api_key_env="TOGETHER_API_KEY",
        default_model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
        free_models=[
            "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
            "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
            "mistralai/Mixtral-8x7B-Instruct-v0.1",
        ],
        rate_limit_rpm=60,
        notes="$5-$100 trial credits. 200+ models. OpenAI-compatible.",
    ),
    Tentacle.SAMBANOVA: TentacleConfig(
        tentacle=Tentacle.SAMBANOVA,
        base_url="https://api.sambanova.ai/v1/",
        api_key_env="SAMBANOVA_API_KEY",
        default_model="Meta-Llama-3.3-70B-Instruct",
        free_models=[
            "Meta-Llama-3.3-70B-Instruct",
            "DeepSeek-R1",
            "DeepSeek-V3-0324",
        ],
        rate_limit_rpm=30,
        notes="$5 trial credits. 3-month expiry.",
    ),
    Tentacle.DEEPINFRA: TentacleConfig(
        tentacle=Tentacle.DEEPINFRA,
        base_url="https://api.deepinfra.com/v1/openai/",
        api_key_env="DEEPINFRA_API_KEY",
        default_model="meta-llama/Meta-Llama-3.1-70B-Instruct",
        free_models=[
            "meta-llama/Meta-Llama-3.1-70B-Instruct",
            "mistralai/Mixtral-8x7B-Instruct-v0.1",
        ],
        rate_limit_rpm=30,
        notes="100+ models. Unauthenticated requests rate-limited by IP.",
    ),
    Tentacle.NVIDIA_NIM: TentacleConfig(
        tentacle=Tentacle.NVIDIA_NIM,
        base_url="https://integrate.api.nvidia.com/v1/",
        api_key_env="NVIDIA_API_KEY",
        default_model="meta/llama-3.3-70b-instruct",
        free_models=[
            "meta/llama-3.3-70b-instruct",
            "deepseek-ai/deepseek-r1",
            "nvidia/nemotron-3-nano-30b-a3b",
        ],
        rate_limit_rpm=40,
        notes="1000 credits on signup. OpenAI-compatible.",
    ),
    Tentacle.NOVITA: TentacleConfig(
        tentacle=Tentacle.NOVITA,
        base_url="https://api.novita.ai/v3/openai/",
        api_key_env="NOVITA_API_KEY",
        default_model="qwen/qwen2.5-7b-instruct",
        free_models=[
            "qwen/qwen2.5-7b-instruct",
            "meta-llama/llama-3.2-1b-instruct",
            "thudm/glm-4-9b-chat",
        ],
        notes="$0.50 trial. Some models permanently free.",
    ),
    Tentacle.FIREWORKS: TentacleConfig(
        tentacle=Tentacle.FIREWORKS,
        base_url="https://api.fireworks.ai/inference/v1/",
        api_key_env="FIREWORKS_API_KEY",
        default_model="accounts/fireworks/models/llama-v3p1-70b-instruct",
        free_models=[
            "accounts/fireworks/models/llama-v3p1-70b-instruct",
            "accounts/fireworks/models/mixtral-8x7b-instruct",
        ],
        notes="$1 trial credit. OpenAI-compatible.",
    ),
    Tentacle.HUGGINGFACE: TentacleConfig(
        tentacle=Tentacle.HUGGINGFACE,
        base_url="https://router.huggingface.co/models/",
        api_key_env="HF_TOKEN",
        default_model="meta-llama/Meta-Llama-3-8B-Instruct",
        free_models=[
            "meta-llama/Meta-Llama-3-8B-Instruct",
            "mistralai/Mistral-7B-Instruct-v0.3",
            "google/gemma-2-9b-it",
        ],
        rate_limit_rpm=30,
        openai_compatible=False,
        notes="~$0.10/month free credits. Good for embeddings.",
    ),
    Tentacle.OLLAMA: TentacleConfig(
        tentacle=Tentacle.OLLAMA,
        base_url="http://localhost:11434/",
        api_key_env="",
        default_model="llama3",
        free_models=["llama3", "mistral", "deepseek-coder", "phi3", "gemma2"],
        rate_limit_rpm=999,
        rate_limit_rpd=99999,
        daily_token_limit=999_999_999,
        notes="Local. No limits. No API key needed.",
    ),
    Tentacle.XAI: TentacleConfig(
        tentacle=Tentacle.XAI,
        base_url="https://api.x.ai/v1/",
        api_key_env="XAI_API_KEY",
        default_model="grok-4-latest",
        free_models=[],
        cost_per_1k=0.005,
        notes="Paid (user's Grok subscription). Web-connected.",
    ),
    Tentacle.GROK_CLI: TentacleConfig(
        tentacle=Tentacle.GROK_CLI,
        base_url="",  # CLI-based, no HTTP endpoint
        api_key_env="XAI_API_KEY",
        default_model="grok-code-fast-1",
        free_models=["grok-code-fast-1", "grok-4-latest"],
        rate_limit_rpm=20,
        rate_limit_rpd=500,
        openai_compatible=False,
        cost_per_1k=0.005,
        notes="Local grok-cli (@vibe-kit/grok-cli). Headless mode via -p flag.",
    ),
    Tentacle.CLAUDE: TentacleConfig(
        tentacle=Tentacle.CLAUDE,
        base_url="https://api.anthropic.com/",
        api_key_env="ANTHROPIC_API_KEY",
        default_model="claude-sonnet-4-6",
        free_models=[],
        cost_per_1k=0.015,
        openai_compatible=False,
        notes="Paid (user's Anthropic). Best reasoning/governance.",
    ),
    Tentacle.OPENAI: TentacleConfig(
        tentacle=Tentacle.OPENAI,
        base_url="https://api.openai.com/v1/",
        api_key_env="OPENAI_API_KEY",
        default_model="gpt-4o",
        free_models=[],
        cost_per_1k=0.005,
        notes="Paid (user's ChatGPT). Strong code/analysis.",
    ),
    Tentacle.GOOGLE_VERTEX: TentacleConfig(
        tentacle=Tentacle.GOOGLE_VERTEX,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key_env="GOOGLE_AI_API_KEY",
        default_model="gemini-2.5-flash",
        free_models=[
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemma-3-27b-it",
        ],
        rate_limit_rpm=10,
        rate_limit_rpd=250,
        cost_per_1k=0.0001,
        notes="Free tier + paid. 1M context. Multimodal. Best value.",
    ),
}


# Sacred Tongue roles — which tongues each task type maps to
TONGUE_TASK_MAP: Dict[str, str] = {
    "code": "CA",          # Compute
    "research": "RU",      # Security/constraint
    "creative": "AV",      # Creative/boundary
    "governance": "UM",    # Governance/entropic
    "analysis": "KO",      # Intent/flow
    "architecture": "DR",  # Structure/tensor
    "translation": "AV",
    "summarize": "KO",
    "general": "KO",
}


# ═══════════════════════════════════════════════════════════════
# Polly — The Raven Observer
# ═══════════════════════════════════════════════════════════════

@dataclass
class PollyObservation:
    """A single observation by Polly the raven.
    Each observation becomes a training pair.
    """
    obs_id: str
    timestamp: float
    tentacle: str
    model: str
    tongue: str
    prompt_hash: str
    prompt_preview: str       # First 200 chars
    response_preview: str     # First 200 chars
    response_length: int
    latency_ms: float
    quality_score: float      # 0-1, estimated by heuristics
    topic_tags: List[str]
    training_pair: Optional[Dict[str, str]] = None  # SFT pair


class PollyLog:
    """Polly's flight log — records every interaction for training.

    The raven sees all. The raven remembers all.
    The logs ARE the tokenizer seeds.
    The lore IS the token vocabulary.
    """

    def __init__(self, log_dir: Optional[str] = None):
        self._observations: List[PollyObservation] = []
        self._mind_map: Dict[str, List[str]] = {}  # topic → subtopics
        self._topic_counts: Dict[str, int] = {}
        self._log_dir = Path(log_dir or "training-data/polly_logs")

    def observe(
        self,
        tentacle: str,
        model: str,
        tongue: str,
        prompt: str,
        response: str,
        latency_ms: float,
    ) -> PollyObservation:
        """Record an interaction. Returns the observation with training pair."""
        obs = PollyObservation(
            obs_id=f"polly-{uuid.uuid4().hex[:8]}",
            timestamp=time.time(),
            tentacle=tentacle,
            model=model,
            tongue=tongue,
            prompt_hash=hashlib.sha256(prompt.encode()).hexdigest()[:16],
            prompt_preview=prompt[:200],
            response_preview=response[:200],
            response_length=len(response),
            latency_ms=latency_ms,
            quality_score=self._estimate_quality(response),
            topic_tags=self._extract_topics(prompt),
            training_pair={
                "instruction": prompt,
                "output": response,
                "tongue": tongue,
                "source": f"{tentacle}/{model}",
            },
        )
        self._observations.append(obs)
        self._update_mind_map(obs)
        return obs

    def flush_training_data(self) -> Path:
        """Write accumulated training pairs to JSONL file."""
        self._log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        outfile = self._log_dir / f"polly_sft_{timestamp}.jsonl"

        pairs = []
        for obs in self._observations:
            if obs.training_pair and obs.quality_score > 0.3:
                pairs.append(obs.training_pair)

        if pairs:
            with open(outfile, "w", encoding="utf-8") as f:
                for pair in pairs:
                    f.write(json.dumps(pair, ensure_ascii=False) + "\n")

        return outfile

    def get_mind_map(self) -> Dict[str, Any]:
        """Return the current knowledge mind map."""
        return {
            "topics": dict(self._topic_counts),
            "connections": dict(self._mind_map),
            "total_observations": len(self._observations),
            "unique_topics": len(self._topic_counts),
        }

    def stats(self) -> Dict[str, Any]:
        """Polly's flight stats."""
        if not self._observations:
            return {"total": 0}
        by_tentacle: Dict[str, int] = {}
        by_tongue: Dict[str, int] = {}
        total_quality = 0.0
        for obs in self._observations:
            by_tentacle[obs.tentacle] = by_tentacle.get(obs.tentacle, 0) + 1
            by_tongue[obs.tongue] = by_tongue.get(obs.tongue, 0) + 1
            total_quality += obs.quality_score
        return {
            "total": len(self._observations),
            "by_tentacle": by_tentacle,
            "by_tongue": by_tongue,
            "avg_quality": total_quality / len(self._observations),
            "training_pairs": sum(
                1 for o in self._observations
                if o.training_pair and o.quality_score > 0.3
            ),
            "mind_map_topics": len(self._topic_counts),
        }

    def _estimate_quality(self, response: str) -> float:
        """Heuristic quality score for a response."""
        if not response or response.startswith("[MOCK") or response.startswith("["):
            return 0.0
        score = 0.5
        # Length bonus (prefer substantive responses)
        if len(response) > 100:
            score += 0.1
        if len(response) > 500:
            score += 0.1
        # Structure bonus (has paragraphs or lists)
        if "\n" in response:
            score += 0.1
        if any(c in response for c in ["- ", "* ", "1.", "##"]):
            score += 0.1
        # Penalty for error responses
        if "error" in response.lower()[:50]:
            score -= 0.3
        return max(0.0, min(1.0, score))

    def _extract_topics(self, prompt: str) -> List[str]:
        """Extract topic tags from a prompt using keyword matching."""
        p = prompt.lower()
        topics = []
        topic_keywords = {
            "code": ["code", "function", "class", "implement", "debug", "test"],
            "ai": ["ai", "machine learning", "neural", "model", "training"],
            "security": ["security", "safety", "governance", "risk", "threat"],
            "math": ["math", "geometry", "hyperbolic", "fibonacci", "manifold"],
            "web": ["web", "browser", "http", "api", "scrape", "crawl"],
            "data": ["data", "dataset", "csv", "json", "database", "storage"],
            "business": ["revenue", "sell", "product", "customer", "market"],
            "creative": ["story", "write", "blog", "content", "narrative"],
        }
        for topic, keywords in topic_keywords.items():
            if any(kw in p for kw in keywords):
                topics.append(topic)
        return topics or ["general"]

    def _update_mind_map(self, obs: PollyObservation) -> None:
        """Update the knowledge mind map with new observation."""
        for tag in obs.topic_tags:
            self._topic_counts[tag] = self._topic_counts.get(tag, 0) + 1
            # Cross-link topics that co-occur
            for other_tag in obs.topic_tags:
                if other_tag != tag:
                    if tag not in self._mind_map:
                        self._mind_map[tag] = []
                    if other_tag not in self._mind_map[tag]:
                        self._mind_map[tag].append(other_tag)


# ═══════════════════════════════════════════════════════════════
# SCBE Tokenizer Gateway — Sacred Tongue encoding on all traffic
# ═══════════════════════════════════════════════════════════════

class TokenizerGateway:
    """Wraps all prompts/responses with SCBE Sacred Tongue encoding.

    Every request gets:
    1. Tongue classification (which Sacred Tongue domain)
    2. SHA-256 fingerprint for dedup / octree indexing
    3. Governance preamble injection (the system prompt armor)
    """

    GOVERNANCE_PREAMBLE = (
        "You are operating within the SCBE-AETHERMOORE governance framework. "
        "Respond accurately, concisely, and safely. "
        "Tag any uncertainty. Cite sources when possible."
    )

    TONGUE_SYSTEM_PROMPTS: Dict[str, str] = {
        "KO": "Focus: intent analysis, flow orientation, pattern recognition.",
        "AV": "Focus: creative expression, boundary exploration, narrative quality.",
        "RU": "Focus: security constraints, validation, rule enforcement.",
        "CA": "Focus: computation, optimization, code quality, performance.",
        "UM": "Focus: governance, policy compliance, ethical evaluation.",
        "DR": "Focus: architecture, structure, system design, scalability.",
    }

    def encode_request(self, prompt: str, task_type: str = "general") -> Dict[str, Any]:
        """Encode a request with SCBE tokenizer metadata."""
        tongue = TONGUE_TASK_MAP.get(task_type, "KO")
        fingerprint = hashlib.sha256(prompt.encode()).hexdigest()

        system_prompt = (
            f"{self.GOVERNANCE_PREAMBLE} "
            f"{self.TONGUE_SYSTEM_PROMPTS.get(tongue, '')}"
        )

        return {
            "tongue": tongue,
            "fingerprint": fingerprint,
            "system_prompt": system_prompt,
            "original_prompt": prompt,
            "encoded_at": time.time(),
        }

    def decode_response(self, response: str, tongue: str) -> Dict[str, Any]:
        """Decode and tag a response with SCBE metadata."""
        fingerprint = hashlib.sha256(response.encode()).hexdigest()
        return {
            "tongue": tongue,
            "fingerprint": fingerprint,
            "content": response,
            "length": len(response),
            "decoded_at": time.time(),
        }


# ═══════════════════════════════════════════════════════════════
# Rate Limiter — Track per-tentacle usage
# ═══════════════════════════════════════════════════════════════

class TentacleThrottle:
    """Per-tentacle rate limiting and usage tracking."""

    def __init__(self):
        self._minute_buckets: Dict[str, List[float]] = {}
        self._day_buckets: Dict[str, List[float]] = {}
        self._token_usage: Dict[str, int] = {}

    def can_use(self, tentacle: Tentacle) -> bool:
        """Check if this tentacle has capacity."""
        config = TENTACLE_REGISTRY.get(tentacle)
        if not config:
            return False
        if not config.available:
            return False

        now = time.time()
        name = tentacle.value

        # Check RPM
        minute_requests = self._minute_buckets.get(name, [])
        minute_requests = [t for t in minute_requests if now - t < 60]
        self._minute_buckets[name] = minute_requests
        if len(minute_requests) >= config.rate_limit_rpm:
            return False

        # Check RPD
        day_requests = self._day_buckets.get(name, [])
        day_requests = [t for t in day_requests if now - t < 86400]
        self._day_buckets[name] = day_requests
        if len(day_requests) >= config.rate_limit_rpd:
            return False

        return True

    def record_use(self, tentacle: Tentacle, tokens: int = 0) -> None:
        """Record a use of this tentacle."""
        now = time.time()
        name = tentacle.value
        if name not in self._minute_buckets:
            self._minute_buckets[name] = []
        if name not in self._day_buckets:
            self._day_buckets[name] = []
        self._minute_buckets[name].append(now)
        self._day_buckets[name].append(now)
        self._token_usage[name] = self._token_usage.get(name, 0) + tokens

    def usage_report(self) -> Dict[str, Any]:
        """Usage report for all tentacles."""
        now = time.time()
        report = {}
        for tentacle in Tentacle:
            name = tentacle.value
            config = TENTACLE_REGISTRY.get(tentacle)
            if not config:
                continue
            minute_reqs = len([
                t for t in self._minute_buckets.get(name, [])
                if now - t < 60
            ])
            day_reqs = len([
                t for t in self._day_buckets.get(name, [])
                if now - t < 86400
            ])
            report[name] = {
                "available": config.available,
                "rpm_used": minute_reqs,
                "rpm_limit": config.rate_limit_rpm,
                "rpd_used": day_reqs,
                "rpd_limit": config.rate_limit_rpd,
                "tokens_used": self._token_usage.get(name, 0),
                "daily_token_limit": config.daily_token_limit,
            }
        return report


# ═══════════════════════════════════════════════════════════════
# OctoArmor — The HYDRA Connector Hub
# ═══════════════════════════════════════════════════════════════

class OctoArmor:
    """HYDRA multi-tentacle AI connector with SCBE governance armor.

    Usage::

        armor = OctoArmor()
        result = await armor.reach("Explain hyperbolic geometry")
        print(result["response"])
        print(armor.polly.stats())

    The flywheel:
    1. User sends prompt → SCBE tokenizer encodes it
    2. OctoArmor routes to cheapest available free tentacle
    3. Response comes back → Polly observes → training pair generated
    4. Training data accumulates → flush to JSONL → push to HuggingFace
    5. Model improves → users get better results → more usage → more data
    """

    def __init__(
        self,
        board: Optional[NoticeBoard] = None,
        log_dir: Optional[str] = None,
    ):
        self.board = board or NoticeBoard()
        self.polly = PollyLog(log_dir=log_dir)
        self.gateway = TokenizerGateway()
        self.throttle = TentacleThrottle()
        self._interaction_count = 0
        self._tried_tentacles: List[Tentacle] = []  # Track per-request failures
        self._provider_health_cache: Dict[Tentacle, Tuple[float, bool, str]] = {}

    async def reach(
        self,
        prompt: str,
        *,
        task_type: Optional[str] = None,
        preferred_tentacle: Optional[Tentacle] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extend a tentacle to an AI provider and get a response.

        Routes to the best available free provider unless a specific
        tentacle is requested. Every interaction is observed by Polly
        and generates training data.
        """
        self._interaction_count += 1
        # Reset tried list for new top-level requests (not fallbacks)
        if not getattr(self, '_in_fallback', False):
            self._tried_tentacles = []

        # Classify task
        if task_type is None:
            task_type = classify_task(prompt).value

        # Encode through SCBE tokenizer gateway
        encoded = self.gateway.encode_request(prompt, task_type)
        tongue = encoded["tongue"]

        # Track failures with root-cause diagnostics for this request.
        self._failure_chain: List[Dict[str, str]] = []

        # Select tentacle (excluding already-tried ones)
        tentacle, config = self._select_tentacle(
            preferred_tentacle, task_type,
            exclude=self._tried_tentacles,
        )
        if not config:
            return {
                "status": "error",
                "error": "No available tentacles — check API keys",
                "failure_chain": self._failure_chain,
                "tentacle": None,
                "response": None,
            }

        # Select model
        actual_model = model or config.default_model

        # Post to notice board
        self.board.post(
            author="hydra",
            task_id=f"octo-{self._interaction_count}",
            status="reaching",
            message=f"Tentacle {tentacle.value} → {actual_model}",
            tags=[tentacle.value, tongue, task_type],
        )

        # Execute the call
        start = time.time()
        try:
            response = await self._call_tentacle(
                config, actual_model, prompt,
                context=context or encoded["system_prompt"],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            latency_ms = (time.time() - start) * 1000
            self.throttle.record_use(tentacle, tokens=len(response) // 4)

            # Polly observes
            obs = self.polly.observe(
                tentacle=tentacle.value,
                model=actual_model,
                tongue=tongue,
                prompt=prompt,
                response=response,
                latency_ms=latency_ms,
            )

            # Decode response through gateway
            decoded = self.gateway.decode_response(response, tongue)

            self.board.post(
                author="hydra",
                task_id=f"octo-{self._interaction_count}",
                status="done",
                message=f"Done in {latency_ms:.0f}ms via {tentacle.value}",
                result=response[:200],
                tags=["completed"],
            )

            return {
                "status": "ok",
                "tentacle": tentacle.value,
                "model": actual_model,
                "tongue": tongue,
                "response": response,
                "latency_ms": latency_ms,
                "quality": obs.quality_score,
                "fingerprint": decoded["fingerprint"],
                "observation_id": obs.obs_id,
                "training_pair_generated": obs.training_pair is not None,
            }

        except Exception as exc:
            latency_ms = (time.time() - start) * 1000
            self._tried_tentacles.append(tentacle)
            self._failure_chain.append({
                "tentacle": tentacle.value,
                "error": str(exc),
            })
            self.board.post(
                author="hydra",
                task_id=f"octo-{self._interaction_count}",
                status="error",
                message=f"{tentacle.value} error: {exc}",
                tags=["error"],
            )
            # Try fallback tentacle (max 5 attempts to prevent runaway)
            if len(self._tried_tentacles) >= 5:
                return {
                    "status": "error",
                    "error": f"Exhausted 5 tentacles. Last: {exc}",
                    "failure_chain": self._failure_chain,
                    "tried": [t.value for t in self._tried_tentacles],
                    "tentacle": tentacle.value,
                    "response": None,
                }
            self._in_fallback = True
            try:
                return await self.reach(
                    prompt,
                    task_type=task_type,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    context=context,
                )
            finally:
                self._in_fallback = False

    async def batch_reach(
        self,
        prompts: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Send multiple prompts across tentacles concurrently."""
        import asyncio
        tasks = [
            self.reach(
                p["prompt"],
                task_type=p.get("task_type"),
                preferred_tentacle=(
                    Tentacle(p["tentacle"]) if "tentacle" in p else None
                ),
            )
            for p in prompts
        ]
        return await asyncio.gather(*tasks, return_exceptions=False)

    def tentacle_status(self) -> List[Dict[str, Any]]:
        """Status of all tentacles — which are available, rate limits, usage."""
        status = []
        usage = self.throttle.usage_report()
        for tentacle, config in TENTACLE_REGISTRY.items():
            u = usage.get(tentacle.value, {})
            status.append({
                "tentacle": tentacle.value,
                "available": config.available,
                "has_key": bool(config.api_key) if config.api_key_env else True,
                "cost": "FREE" if config.cost_per_1k == 0 else f"${config.cost_per_1k:.4f}/1k",
                "rpm": f"{u.get('rpm_used', 0)}/{config.rate_limit_rpm}",
                "rpd": f"{u.get('rpd_used', 0)}/{config.rate_limit_rpd}",
                "default_model": config.default_model,
                "free_models": len(config.free_models),
                "notes": config.notes,
            })
        return status

    def available_tentacles(self) -> List[Tentacle]:
        """List tentacles that are currently available and under rate limits."""
        return [
            t for t in Tentacle
            if TENTACLE_REGISTRY[t].available and self.throttle.can_use(t)
        ]

    def all_free_models(self) -> Dict[str, List[str]]:
        """List all free models across all tentacles."""
        models = {}
        for tentacle, config in TENTACLE_REGISTRY.items():
            if config.free_models:
                models[tentacle.value] = config.free_models
        return models

    def flush_training_data(self) -> str:
        """Write Polly's observations to JSONL training file."""
        path = self.polly.flush_training_data()
        return str(path)

    def diagnostics(self) -> Dict[str, Any]:
        """Full system diagnostics."""
        available = self.available_tentacles()
        return {
            "hydra_status": "ONLINE" if available else "NO_TENTACLES",
            "available_tentacles": len(available),
            "total_tentacles": len(Tentacle),
            "tentacle_names": [t.value for t in available],
            "polly_stats": self.polly.stats(),
            "mind_map": self.polly.get_mind_map(),
            "throttle": self.throttle.usage_report(),
            "notice_board": self.board.summary(),
            "interactions": self._interaction_count,
            "total_free_models": sum(
                len(c.free_models) for c in TENTACLE_REGISTRY.values()
            ),
        }

    # ─── Internal ──────────────────────────────────────────────

    def _select_tentacle(
        self,
        preferred: Optional[Tentacle],
        task_type: str,
        exclude: Optional[List[Tentacle]] = None,
    ) -> Tuple[Optional[Tentacle], Optional[TentacleConfig]]:
        """Select the best tentacle for this task."""
        skip = set(exclude or [])

        # If user specified one, try it first (unless excluded)
        if preferred and preferred not in skip:
            config = TENTACLE_REGISTRY.get(preferred)
            if config and self._is_usable_tentacle(preferred, config):
                return preferred, config

        # Priority order: free tentacles first, then paid
        # Within free, prefer fastest/most capable
        free_priority = [
            Tentacle.GROQ,        # Fastest
            Tentacle.CEREBRAS,    # Also very fast
            Tentacle.GOOGLE_AI,   # Best free tier
            Tentacle.OPENROUTER,  # Most models
            Tentacle.MISTRAL_FREE,  # Huge token limit
            Tentacle.GITHUB_MODELS,  # Uses existing token
            Tentacle.OLLAMA,      # Local fallback
            Tentacle.DEEPINFRA,
            Tentacle.TOGETHER,
            Tentacle.SAMBANOVA,
            Tentacle.NVIDIA_NIM,
            Tentacle.CLOUDFLARE,
            Tentacle.NOVITA,
            Tentacle.FIREWORKS,
            Tentacle.HUGGINGFACE,
            Tentacle.COHERE,
        ]

        # Task-specific preference overrides
        if task_type == "code":
            # Prefer models good at code
            free_priority = [
                Tentacle.GROQ,      # Has deepseek-coder variants
                Tentacle.OPENROUTER,  # Has qwen3-coder
                Tentacle.CEREBRAS,
            ] + [t for t in free_priority if t not in (
                Tentacle.GROQ, Tentacle.OPENROUTER, Tentacle.CEREBRAS
            )]
        elif task_type == "research":
            # Prefer web-connected or large context
            free_priority = [
                Tentacle.GOOGLE_AI,   # 1M context
                Tentacle.OPENROUTER,  # 405B models
                Tentacle.GROQ,
            ] + [t for t in free_priority if t not in (
                Tentacle.GOOGLE_AI, Tentacle.OPENROUTER, Tentacle.GROQ
            )]

        for tentacle in free_priority:
            if tentacle in skip:
                continue
            config = TENTACLE_REGISTRY.get(tentacle)
            if config and self._is_usable_tentacle(tentacle, config):
                return tentacle, config

        # Last resort: paid tentacles (user's subscriptions)
        # Grok CLI is tried before cloud-only paid providers
        for tentacle in [Tentacle.GOOGLE_VERTEX, Tentacle.XAI, Tentacle.GROK_CLI, Tentacle.OPENAI, Tentacle.CLAUDE]:
            if tentacle in skip:
                continue
            config = TENTACLE_REGISTRY.get(tentacle)
            if config and self._is_usable_tentacle(tentacle, config):
                return tentacle, config

        return None, None

    def _is_usable_tentacle(self, tentacle: Tentacle, config: TentacleConfig) -> bool:
        """Return whether this tentacle is currently usable."""
        if not (config.available and self.throttle.can_use(tentacle)):
            return False

        now = time.time()
        cached = self._provider_health_cache.get(tentacle)
        if cached and (now - cached[0]) < 60:
            if not cached[1]:
                # Refresh health only if requested key changed.
                if tentacle in (Tentacle.GITHUB_MODELS, Tentacle.HUGGINGFACE, Tentacle.GROK_CLI):
                    pass
                else:
                    return False

        if tentacle == Tentacle.OLLAMA:
            ok, reason = self._probe_ollama()
        elif tentacle == Tentacle.GITHUB_MODELS:
            api_key = (config.api_key or "").strip()
            if api_key.startswith("github_pat_"):
                return True
            ok, reason = False, "GitHub model token appears to be legacy PAT (ghp_), use github_pat_"
        elif tentacle == Tentacle.HUGGINGFACE:
            api_key = (config.api_key or "").strip()
            if not api_key.startswith("hf_"):
                ok, reason = False, "HF token does not start with hf_"
            else:
                return True
        elif tentacle == Tentacle.GROK_CLI:
            if not config.api_key:
                return False
            ok, reason = True, ""
        else:
            ok, reason = True, ""

        if not ok:
            self._failure_chain.append({
                "tentacle": tentacle.value,
                "error": reason,
            })
            self._provider_health_cache[tentacle] = (now, False, reason)
            return False

        self._provider_health_cache[tentacle] = (now, True, "")
        return True

    def _probe_ollama(self) -> Tuple[bool, str]:
        import urllib.request
        req = urllib.request.Request("http://localhost:11434/api/tags")
        try:
            with urllib.request.urlopen(req, timeout=1.5):
                return True, ""
        except Exception as exc:
            return False, f"Ollama check failed: {exc}"

    async def _call_tentacle(
        self,
        config: TentacleConfig,
        model: str,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Call a tentacle's API. Most are OpenAI-compatible."""
        if config.tentacle == Tentacle.OLLAMA:
            return await self._call_ollama(config, model, prompt, context)

        if config.tentacle == Tentacle.GROK_CLI:
            return await self._call_grok_cli(config, model, prompt, context)

        if config.tentacle == Tentacle.HUGGINGFACE:
            return await self._call_huggingface(
                config, model, prompt, context, temperature, max_tokens
            )

        if config.tentacle == Tentacle.COHERE:
            return await self._call_cohere(config, model, prompt, context,
                                           temperature, max_tokens)

        if config.tentacle == Tentacle.CLOUDFLARE:
            return await self._call_cloudflare(config, model, prompt, context)

        # Providers behind Cloudflare bot protection need openai SDK (urllib gets 403/1010)
        if config.tentacle in (
            Tentacle.GROQ, Tentacle.CEREBRAS, Tentacle.XAI, Tentacle.OPENAI,
            Tentacle.MISTRAL_FREE, Tentacle.TOGETHER, Tentacle.SAMBANOVA,
            Tentacle.DEEPINFRA, Tentacle.NVIDIA_NIM, Tentacle.FIREWORKS,
        ):
            return await self._call_via_openai_sdk(
                config, model, prompt, context, temperature, max_tokens
            )

        # Claude uses Anthropic SDK (completely different API)
        if config.tentacle == Tentacle.CLAUDE:
            return await self._call_claude(
                config, model, prompt, context, temperature, max_tokens
            )

        # Google Vertex/AI Studio — OpenAI-compatible endpoint works
        if config.tentacle == Tentacle.GOOGLE_VERTEX:
            return await self._call_via_openai_sdk(
                config, model, prompt, context, temperature, max_tokens
            )

        # All other OpenAI-compatible providers via urllib
        return await self._call_openai_compatible(
            config, model, prompt, context, temperature, max_tokens
        )

    async def _call_via_openai_sdk(
        self,
        config: TentacleConfig,
        model: str,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Call via openai SDK — needed for providers that reject raw urllib."""
        try:
            import openai  # type: ignore[import-untyped]
        except ImportError:
            # Fall back to urllib if SDK not installed
            return await self._call_openai_compatible(
                config, model, prompt, context, temperature, max_tokens
            )

        key = config.api_key
        if not key:
            raise RuntimeError(f"{config.tentacle.value}: no API key")

        base = config.base_url.rstrip("/")
        client = openai.OpenAI(api_key=key, base_url=base)
        messages = []
        if context:
            messages.append({"role": "system", "content": context})
        messages.append({"role": "user", "content": prompt})

        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp.choices[0].message.content or "[empty response]"

    async def _call_claude(
        self,
        config: TentacleConfig,
        model: str,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Call Anthropic Claude API via anthropic SDK."""
        try:
            import anthropic  # type: ignore[import-untyped]
        except ImportError:
            raise RuntimeError("anthropic SDK not installed: pip install anthropic")

        key = config.api_key
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY not set")

        client = anthropic.Anthropic(api_key=key)
        messages = []
        if context:
            messages.append({"role": "user", "content": context})
            messages.append({"role": "assistant", "content": "Understood."})
        messages.append({"role": "user", "content": prompt})

        resp = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=messages,
        )
        return resp.content[0].text  # type: ignore[union-attr]

    async def _call_openai_compatible(
        self,
        config: TentacleConfig,
        model: str,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Generic OpenAI-compatible API call. Works for 12+ providers."""
        import urllib.request

        messages = []
        if context:
            messages.append({"role": "system", "content": context})
        messages.append({"role": "user", "content": prompt})

        payload = json.dumps({
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }).encode()

        base = config.base_url.rstrip("/")
        url = f"{base}/chat/completions"

        headers = {"Content-Type": "application/json"}
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"

        # OpenRouter wants extra headers
        if config.tentacle == Tentacle.OPENROUTER:
            headers["HTTP-Referer"] = "https://scbe-aethermoore.dev"
            headers["X-Title"] = "SCBE OctoArmor"

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode())
                choices = body.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "[empty]")
                return "[empty response]"
        except Exception as exc:
            raise RuntimeError(f"{config.tentacle.value} API error: {exc}")

    async def _call_ollama(
        self, config: TentacleConfig, model: str,
        prompt: str, context: Optional[str] = None,
    ) -> str:
        """Call local Ollama instance."""
        import urllib.request

        payload = json.dumps({
            "model": model,
            "prompt": f"{context}\n\n{prompt}" if context else prompt,
            "stream": False,
        }).encode()

        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode())
                return body.get("response", "[empty Ollama response]")
        except Exception as exc:
            raise RuntimeError(f"Ollama error: {exc}")

    async def _call_huggingface(
        self,
        config: TentacleConfig,
        model: str,
        prompt: str,
        context: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Call HuggingFace Inference API (chat-first, legacy fallback)."""
        import urllib.error
        import urllib.request
        from urllib.parse import quote

        full_prompt = f"{context}\n\n{prompt}" if context else prompt
        model_path = quote(model, safe="")
        base = config.base_url.rstrip("/")

        auth_header = None
        if config.api_key:
            auth_header = f"Bearer {config.api_key}"
        headers = {"Content-Type": "application/json"}
        if auth_header:
            headers["Authorization"] = auth_header

        chat_messages = [
            {"role": "system", "content": self.gateway.GOVERNANCE_PREAMBLE},
            {"role": "user", "content": full_prompt},
        ]

        chat_payload = json.dumps({
            "model": model,
            "messages": chat_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }).encode()

        legacy_payload = json.dumps({
            "inputs": full_prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "return_full_text": False,
            },
        }).encode()

        def _extract_text(body: Any) -> str:
            if isinstance(body, dict):
                if "error" in body:
                    raise RuntimeError(str(body["error"]))

                choices = body.get("choices")
                if isinstance(choices, list) and choices:
                    msg = choices[0].get("message", {})
                    if isinstance(msg, dict):
                        content = msg.get("content")
                        if isinstance(content, str) and content.strip():
                            return content

                direct = body.get("generated_text")
                if isinstance(direct, str) and direct.strip():
                    return direct
                direct_list = body.get("generated_texts")
                if isinstance(direct_list, list) and direct_list:
                    first = direct_list[0]
                    if isinstance(first, str) and first.strip():
                        return first

            if isinstance(body, list) and body:
                first = body[0]
                if isinstance(first, dict):
                    direct = first.get("generated_text")
                    if isinstance(direct, str) and direct.strip():
                        return direct
                    if isinstance(direct, str) and direct.strip():
                        return direct
                if isinstance(first, str) and first.strip():
                    return first

            return ""

        endpoints = [
            (f"{base}/{model_path}/v1/chat/completions", chat_payload),
            (f"{base}/{model_path}", legacy_payload),
        ]

        last_err = None
        for idx, (url, payload) in enumerate(endpoints):
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    body = json.loads(resp.read().decode())
                    response_text = _extract_text(body)
                    if response_text:
                        return response_text
                    return str(body)
            except urllib.error.HTTPError as exc:
                raw = exc.read().decode("utf-8", errors="replace")
                try:
                    body = json.loads(raw)
                except json.JSONDecodeError:
                    body = {"raw": raw}
                if idx == 0 and exc.code in {404, 405}:
                    # Newer HF inference deployments may not expose /v1/chat endpoint.
                    last_err = str(body)
                    continue
                if isinstance(body, dict) and body:
                    msg = body.get("error") or body.get("message") or body.get("raw") or str(body)
                else:
                    msg = raw
                last_err = f"{exc.code} {msg}"
                if idx == 0 and exc.code in {400, 500}:
                    # Some providers report chat route mismatch; fallback may still work.
                    continue
                raise RuntimeError(f"HuggingFace chat error: {last_err}")
            except Exception as exc:
                last_err = str(exc)
                if idx == 0:
                    continue
                raise RuntimeError(f"HuggingFace error: {last_err}")

        raise RuntimeError(f"HuggingFace request failed: {last_err}")

    async def _call_cohere(
        self, config: TentacleConfig, model: str,
        prompt: str, context: Optional[str] = None,
        temperature: float = 0.7, max_tokens: int = 2048,
    ) -> str:
        """Call Cohere v2 API (non-OpenAI format)."""
        import urllib.request

        payload = json.dumps({
            "model": model,
            "message": prompt,
            "preamble": context or "",
            "temperature": temperature,
            "max_tokens": max_tokens,
        }).encode()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.api_key}",
        }

        req = urllib.request.Request(
            "https://api.cohere.com/v2/chat",
            data=payload, headers=headers, method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode())
                return body.get("text", "[empty Cohere response]")
        except Exception as exc:
            raise RuntimeError(f"Cohere error: {exc}")

    async def _call_cloudflare(
        self, config: TentacleConfig, model: str,
        prompt: str, context: Optional[str] = None,
    ) -> str:
        """Call Cloudflare Workers AI."""
        import urllib.request

        account_id = _pick_provider_secret("CLOUDFLARE_ACCOUNT_ID", "CLOUDFLARE_ACCOUNT", "CLOUDFLARE_ID")
        if not account_id:
            raise RuntimeError("CLOUDFLARE_ACCOUNT_ID not set")

        messages = []
        if context:
            messages.append({"role": "system", "content": context})
        messages.append({"role": "user", "content": prompt})

        payload = json.dumps({"messages": messages}).encode()

        url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.api_key}",
        }

        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = json.loads(resp.read().decode())
                result = body.get("result", {})
                return result.get("response", "[empty Cloudflare response]")
        except Exception as exc:
            raise RuntimeError(f"Cloudflare error: {exc}")

    async def _call_grok_cli(
        self,
        config: TentacleConfig,
        model: str,
        prompt: str,
        context: Optional[str] = None,
    ) -> str:
        """Call xAI Grok via the local grok-cli npm package.

        Uses headless mode: grok -p "<prompt>" -m <model>
        Binary: @vibe-kit/grok-cli installed globally via npm.
        """
        import asyncio

        # Find the grok binary
        grok_bin = shutil.which("grok")
        if not grok_bin:
            # Check common npm global paths
            npm_global = Path(os.environ.get("APPDATA", "")) / "npm" / "grok.cmd"
            if npm_global.exists():
                grok_bin = str(npm_global)
            else:
                raise RuntimeError(
                    "grok-cli not found. Install: npm install -g @vibe-kit/grok-cli"
                )

        full_prompt = f"{context}\n\n{prompt}" if context else prompt

        cmd = [grok_bin, "-p", full_prompt, "-m", model]

        # Pass API key if available
        key = config.api_key
        if key:
            cmd.extend(["-k", key])

        try:
            proc = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=False,
                timeout=120,
            )

            if proc.returncode != 0:
                stderr = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""
                raise RuntimeError(f"grok-cli exited {proc.returncode}: {stderr}")

            response = proc.stdout.decode("utf-8", errors="replace") if proc.stdout else ""
            response = response.strip()
            if not response:
                return "[empty grok-cli response]"
            return response

        except subprocess.TimeoutExpired:
            raise RuntimeError("grok-cli timed out after 120s")
        except FileNotFoundError:
            raise RuntimeError(f"grok-cli binary not found at {grok_bin}")

    # _fallback is now handled inline in reach() via _tried_tentacles tracking


# ═══════════════════════════════════════════════════════════════
# Training Flywheel — Auto-push to HuggingFace
# ═══════════════════════════════════════════════════════════════

class TrainingFlywheel:
    """Automated training data pipeline.

    Collects Polly's observations → JSONL → HuggingFace push.
    Every interaction makes the model smarter.
    Free compute from Colab/cloud trains the model.
    Users get better results → more usage → more data → repeat.
    """

    def __init__(
        self,
        armor: OctoArmor,
        hf_repo: str = "issdandavis/scbe-aethermoore-training-data",
        data_dir: str = "training-data/polly_logs",
    ):
        self.armor = armor
        self.hf_repo = hf_repo
        self.data_dir = Path(data_dir)
        self._push_count = 0

    def collect(self) -> Dict[str, Any]:
        """Collect current training stats."""
        stats = self.armor.polly.stats()
        return {
            "observations": stats.get("total", 0),
            "training_pairs": stats.get("training_pairs", 0),
            "mind_map_topics": stats.get("mind_map_topics", 0),
            "push_count": self._push_count,
        }

    def flush(self) -> str:
        """Flush training data to disk."""
        return self.armor.flush_training_data()

    def push_to_hf(self) -> Dict[str, Any]:
        """Push accumulated training data to HuggingFace.

        Returns status dict. Requires HF_TOKEN in env.
        """
        try:
            from huggingface_hub import HfApi  # type: ignore[import-untyped]

            token = os.environ.get("HF_TOKEN")
            if not token:
                return {"status": "error", "error": "HF_TOKEN not set"}

            stats = self.collect()
            if stats.get("training_pairs", 0) <= 0:
                return {"status": "skipped", "reason": "no training pairs above quality threshold"}

            # Flush latest data
            filepath = Path(self.flush()).expanduser().resolve()
            if not filepath.exists():
                return {
                    "status": "error",
                    "error": f"no training payload file found at {filepath}",
                }

            api = HfApi(token=token)
            api.upload_file(
                path_or_fileobj=str(filepath),
                path_in_repo=f"polly_logs/{Path(filepath).name}",
                repo_id=self.hf_repo,
                repo_type="dataset",
            )
            self._push_count += 1

            return {
                "status": "ok",
                "file": filepath,
                "repo": self.hf_repo,
                "push_count": self._push_count,
            }
        except ImportError:
            return {"status": "error", "error": "huggingface_hub not installed"}
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    def mind_map(self) -> Dict[str, Any]:
        """Get the current knowledge mind map."""
        return self.armor.polly.get_mind_map()

    def daily_report(self) -> str:
        """Generate a daily training report."""
        stats = self.collect()
        mind = self.mind_map()
        lines = [
            "=== POLLY DAILY TRAINING REPORT ===",
            f"Total observations: {stats['observations']}",
            f"Training pairs generated: {stats['training_pairs']}",
            f"Mind map topics: {stats['mind_map_topics']}",
            f"HF pushes today: {stats['push_count']}",
            "",
            "Top topics:",
        ]
        topics = mind.get("topics", {})
        for topic, count in sorted(topics.items(), key=lambda x: -x[1])[:10]:
            lines.append(f"  {topic}: {count} observations")
        lines.append("")
        lines.append("Topic connections:")
        connections = mind.get("connections", {})
        for topic, linked in list(connections.items())[:5]:
            lines.append(f"  {topic} → {', '.join(linked)}")
        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# Quick API — One-liners
# ═══════════════════════════════════════════════════════════════

async def hydra_ask(prompt: str, task_type: Optional[str] = None) -> str:
    """One-liner: ask the HYDRA and get a response."""
    armor = OctoArmor()
    result = await armor.reach(prompt, task_type=task_type)
    return result.get("response", "[no response]")


def list_free_models() -> Dict[str, List[str]]:
    """List all available free models across all providers."""
    armor = OctoArmor()
    return armor.all_free_models()


def tentacle_dashboard() -> List[Dict[str, Any]]:
    """Quick dashboard of all tentacle statuses."""
    armor = OctoArmor()
    return armor.tentacle_status()
