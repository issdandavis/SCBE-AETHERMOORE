#!/usr/bin/env python3
"""
NPC Model Gateway — Multi-Model AI Backend for Aethermoor NPCs
================================================================
Manages a tiered fleet of small language models that serve as NPC brains.
Auto-detects hardware, loads appropriate model tiers, and routes NPC
dialogue requests to the best available backend.

Model Tiers (smallest → largest):
  Tier 0 — Template fallback (no model, uses npc_brain.py templates)
  Tier 1 — SmolLM2-135M  (~300MB) : Ambient NPCs, shopkeeper barks
  Tier 2 — SmolLM2-360M  (~700MB) : Quest givers, mid-tier dialogue
  Tier 3 — SmolLM2-1.7B  (~3.4GB) : Party members, personality-rich
  Tier 4 — Qwen2.5-3B    (~6GB)   : Narrator, dungeon master, bosses
  Tier 5 — Custom fine-tune        : Tongue-aware Aethermoor specialist

NPC importance tiers:
  AMBIENT   → Tier 1 (generic villagers, background chatter)
  MERCHANT  → Tier 2 (shops, inns, quest boards)
  COMPANION → Tier 3 (Polly, Clay, Eldrin, Aria, Zara, Kael)
  NARRATOR  → Tier 4 (story narrator, boss encounters)
  MASTER    → Tier 5 (fine-tuned lore expert)

Supports:
  - llama-cpp-python (GGUF files, CPU/GPU)
  - transformers (HF models, GPU preferred)
  - HuggingFace Inference API (cloud bridge to fine-tuned model)
  - Google Gemini API (cloud fallback)
  - Template responses (always available)
  - Tri-manifold personality enrichment (when src.gacha_isekai available)

Training data collection:
  Every NPC exchange is logged as an SFT pair for future fine-tuning.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import time
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import sys
sys.path.insert(0, str(Path(__file__).parent))

from engine import Tongue

# Tri-manifold personality (optional — enriches prompts when available)
try:
    from src.gacha_isekai.personality_tri_manifold import (
        TriManifoldPersonality,
        ManifoldID,
    )
    _HAS_TRI_MANIFOLD = True
except ImportError:
    _HAS_TRI_MANIFOLD = False

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MODEL_CACHE_DIR = Path(__file__).resolve().parent / "models"
SFT_OUTPUT_DIR = Path(__file__).resolve().parent / "training_output" / "npc_sft"

# HuggingFace model IDs for each tier
TIER_MODELS: Dict[int, Dict[str, str]] = {
    1: {
        "hf_id": "HuggingFaceTB/SmolLM2-135M-Instruct",
        "gguf_id": "",
        "name": "SmolLM2-135M",
        "vram_mb": 300,
    },
    2: {
        "hf_id": "HuggingFaceTB/SmolLM2-360M-Instruct",
        "gguf_id": "HuggingFaceTB/SmolLM2-360M-Instruct-GGUF",
        "name": "SmolLM2-360M",
        "vram_mb": 700,
    },
    3: {
        "hf_id": "HuggingFaceTB/SmolLM2-1.7B-Instruct",
        "gguf_id": "bartowski/SmolLM2-1.7B-Instruct-GGUF",
        "name": "SmolLM2-1.7B",
        "vram_mb": 3400,
    },
    4: {
        "hf_id": "Qwen/Qwen2.5-3B-Instruct",
        "gguf_id": "Qwen/Qwen2.5-3B-Instruct-GGUF",
        "name": "Qwen2.5-3B",
        "vram_mb": 6000,
    },
    5: {
        "hf_id": "issdandavis/aethermoor-npc-v1",
        "gguf_id": "",
        "name": "Aethermoor-NPC-v1",
        "vram_mb": 6000,
    },
}


# ---------------------------------------------------------------------------
# NPC Importance Levels
# ---------------------------------------------------------------------------
class NPCImportance(IntEnum):
    """How important an NPC is determines which model tier serves them."""
    AMBIENT = 1    # Background villagers
    MERCHANT = 2   # Shopkeepers, innkeepers
    COMPANION = 3  # Party members
    NARRATOR = 4   # Story narrator, bosses
    MASTER = 5     # Lore-master (fine-tuned model)


# NPC name -> importance mapping
NPC_IMPORTANCE: Dict[str, NPCImportance] = {
    # Party companions (Tier 3)
    "polly": NPCImportance.COMPANION,
    "clay": NPCImportance.COMPANION,
    "eldrin": NPCImportance.COMPANION,
    "aria": NPCImportance.COMPANION,
    "zara": NPCImportance.COMPANION,
    "kael": NPCImportance.COMPANION,
    # Town NPCs (Tier 2)
    "shopkeeper": NPCImportance.MERCHANT,
    "innkeeper": NPCImportance.MERCHANT,
    "blacksmith": NPCImportance.MERCHANT,
    "healer": NPCImportance.MERCHANT,
    # Story NPCs (Tier 4)
    "narrator": NPCImportance.NARRATOR,
    "grey": NPCImportance.NARRATOR,
    "boss": NPCImportance.NARRATOR,
    # Lore experts (Tier 5 if available)
    "elder": NPCImportance.MASTER,
    "oracle": NPCImportance.MASTER,
}

# Tongue personality flavor injected into prompts
TONGUE_PERSONALITY: Dict[str, str] = {
    "KO": "commanding, authoritative, speaks with certainty and weight",
    "AV": "curious, explorative, speaks of paths and connections",
    "RU": "measured, lawful, speaks of precedent and policy",
    "CA": "analytical, inventive, speaks of patterns and growth",
    "UM": "cryptic, perceptive, speaks of shadows and hidden truths",
    "DR": "bold, creative, speaks of forging and building",
}


# ---------------------------------------------------------------------------
# Hardware Detection
# ---------------------------------------------------------------------------
@dataclass
class HardwareProfile:
    """Detected hardware capabilities."""
    has_gpu: bool = False
    gpu_name: str = ""
    vram_mb: int = 0
    ram_mb: int = 0
    cpu_cores: int = 1
    platform: str = ""
    max_tier: int = 0  # Highest model tier we can load


def detect_hardware() -> HardwareProfile:
    """Detect available hardware for model loading."""
    profile = HardwareProfile()
    profile.platform = platform.system()
    profile.cpu_cores = os.cpu_count() or 1

    # Check system RAM
    try:
        import psutil
        profile.ram_mb = int(psutil.virtual_memory().total / (1024 * 1024))
    except ImportError:
        # Estimate 8GB default
        profile.ram_mb = 8192

    # Check for CUDA GPU
    try:
        import torch
        if torch.cuda.is_available():
            profile.has_gpu = True
            profile.gpu_name = torch.cuda.get_device_name(0)
            profile.vram_mb = int(torch.cuda.get_device_properties(0).total_mem / (1024 * 1024))
    except ImportError:
        pass

    # Determine max tier based on available memory
    available_mb = profile.vram_mb if profile.has_gpu else profile.ram_mb
    for tier in sorted(TIER_MODELS.keys(), reverse=True):
        if available_mb >= TIER_MODELS[tier]["vram_mb"]:
            profile.max_tier = tier
            break

    # Always allow at least tier 0 (templates)
    if profile.max_tier == 0 and profile.ram_mb >= 200:
        profile.max_tier = 1  # SmolLM2-135M fits almost anywhere

    return profile


# ---------------------------------------------------------------------------
# Model Backend Interface
# ---------------------------------------------------------------------------
class ModelBackend:
    """Abstract interface for a loaded model."""

    def __init__(self, tier: int, name: str) -> None:
        self.tier = tier
        self.name = name
        self.loaded = False

    def load(self) -> bool:
        """Load the model. Returns True on success."""
        raise NotImplementedError

    def generate(self, prompt: str, max_tokens: int = 150) -> str:
        """Generate text from a prompt."""
        raise NotImplementedError

    def unload(self) -> None:
        """Free model resources."""
        pass


class LlamaCppBackend(ModelBackend):
    """Backend using llama-cpp-python for GGUF models."""

    def __init__(self, tier: int, name: str, model_path: str) -> None:
        super().__init__(tier, name)
        self.model_path = model_path
        self._model: Any = None

    def load(self) -> bool:
        try:
            from llama_cpp import Llama
            self._model = Llama(
                model_path=self.model_path,
                n_ctx=2048,
                n_threads=max(1, (os.cpu_count() or 2) // 2),
                verbose=False,
            )
            self.loaded = True
            logger.info("Loaded GGUF model: %s", self.name)
            return True
        except Exception as e:
            logger.warning("Failed to load GGUF model %s: %s", self.name, e)
            return False

    def generate(self, prompt: str, max_tokens: int = 150) -> str:
        if not self._model:
            return ""
        try:
            output = self._model(
                prompt, max_tokens=max_tokens,
                stop=["Player:", "\n\n", "Human:"],
                temperature=0.7, top_p=0.9,
            )
            return output["choices"][0]["text"].strip()
        except Exception as e:
            logger.warning("GGUF generation failed: %s", e)
            return ""

    def unload(self) -> None:
        self._model = None
        self.loaded = False


class TransformersBackend(ModelBackend):
    """Backend using HuggingFace transformers."""

    def __init__(self, tier: int, name: str, model_id: str) -> None:
        super().__init__(tier, name)
        self.model_id = model_id
        self._model: Any = None
        self._tokenizer: Any = None

    def load(self) -> bool:
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
            dtype = torch.float16 if device == "cuda" else torch.float32

            self._tokenizer = AutoTokenizer.from_pretrained(
                self.model_id, trust_remote_code=True,
            )
            self._model = AutoModelForCausalLM.from_pretrained(
                self.model_id, dtype=dtype,
                trust_remote_code=True, device_map="auto",
            )
            self.loaded = True
            logger.info("Loaded transformers model: %s on %s", self.name, device)
            return True
        except Exception as e:
            logger.warning("Failed to load transformers model %s: %s", self.name, e)
            return False

    def generate(self, prompt: str, max_tokens: int = 150) -> str:
        if not self._model or not self._tokenizer:
            return ""
        try:
            import torch
            inputs = self._tokenizer(prompt, return_tensors="pt")
            inputs = {k: v.to(self._model.device) for k, v in inputs.items()}
            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs, max_new_tokens=max_tokens,
                    temperature=0.7, top_p=0.9,
                    do_sample=True, pad_token_id=self._tokenizer.eos_token_id,
                )
            generated = outputs[0][inputs["input_ids"].shape[1]:]
            return self._tokenizer.decode(generated, skip_special_tokens=True).strip()
        except Exception as e:
            logger.warning("Transformers generation failed: %s", e)
            return ""

    def unload(self) -> None:
        self._model = None
        self._tokenizer = None
        self.loaded = False


class HuggingFaceInferenceBackend(ModelBackend):
    """Backend using HuggingFace Inference API (cloud).

    Calls your fine-tuned adapter hosted on HuggingFace Hub.
    This is the bridge: Game Engine -> HF Inference API -> Response.

    Supports both:
      - Dedicated Inference Endpoints (paid, fast, persistent)
      - Serverless Inference API (free tier, cold starts)
    """

    def __init__(
        self,
        model_id: str = "issdandavis/aethermoor-npc-v1",
        endpoint_url: Optional[str] = None,
    ) -> None:
        super().__init__(tier=5, name=f"HF:{model_id.split('/')[-1]}")
        self.model_id = model_id
        self.endpoint_url = endpoint_url
        self._client: Any = None

    def load(self) -> bool:
        try:
            from huggingface_hub import InferenceClient

            token = os.environ.get("HF_TOKEN", "")
            # Use endpoint URL if provided, otherwise model ID
            target = self.endpoint_url or self.model_id
            self._client = InferenceClient(
                model=target,
                token=token or None,
            )
            self.loaded = True
            logger.info(
                "HF Inference bridge connected: %s%s",
                self.model_id,
                f" (endpoint: {self.endpoint_url})" if self.endpoint_url else " (serverless)",
            )
            return True
        except ImportError:
            logger.warning("huggingface_hub not installed — run: pip install huggingface_hub")
            return False
        except Exception as e:
            logger.warning("HF Inference bridge failed: %s", e)
            return False

    def generate(self, prompt: str, max_tokens: int = 150) -> str:
        if not self._client:
            return ""
        try:
            # Try chat completion first (for chat-tuned models)
            messages = self._parse_prompt_to_messages(prompt)
            resp = self._client.chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7,
                top_p=0.9,
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            # Fallback to text generation
            try:
                out = self._client.text_generation(
                    prompt=prompt,
                    max_new_tokens=max_tokens,
                    temperature=0.7,
                    top_p=0.9,
                )
                return out.strip() if isinstance(out, str) else str(out).strip()
            except Exception as e:
                logger.warning("HF Inference generation failed: %s", e)
                return ""

    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 256,
    ) -> str:
        """Generate from chat messages directly (bypasses prompt parsing)."""
        if not self._client:
            return ""
        try:
            resp = self._client.chat_completion(
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7,
                top_p=0.9,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            logger.warning("HF chat generation failed: %s", e)
            return ""

    @staticmethod
    def _parse_prompt_to_messages(prompt: str) -> List[Dict[str, str]]:
        """Convert a flat prompt string to chat messages.

        Extracts system prompt (everything before 'Player:') and
        user message (after 'Player:').
        """
        messages = []
        if "Player:" in prompt:
            parts = prompt.split("Player:", 1)
            system_text = parts[0].strip()
            user_text = parts[1].strip()
            # Remove trailing "NPCName:" if present
            for suffix in [":", "\n"]:
                if user_text.endswith(suffix):
                    user_text = user_text[:-len(suffix)].strip()
            # Clean trailing NPC name prompt
            lines = user_text.split("\n")
            if lines and lines[-1].endswith(":"):
                user_text = "\n".join(lines[:-1]).strip()
            messages.append({"role": "system", "content": system_text})
            messages.append({"role": "user", "content": user_text})
        else:
            messages.append({"role": "user", "content": prompt})
        return messages


class GeminiBackend(ModelBackend):
    """Backend using Google Gemini API (cloud)."""

    def __init__(self) -> None:
        super().__init__(tier=4, name="Gemini-Flash")
        self._model: Any = None

    def load(self) -> bool:
        try:
            import google.generativeai as genai
            key = os.environ.get("GOOGLE_AI_KEY", "")
            if not key:
                return False
            genai.configure(api_key=key)
            self._model = genai.GenerativeModel("gemini-2.0-flash")
            self.loaded = True
            return True
        except (ImportError, Exception) as e:
            logger.debug("Gemini not available: %s", e)
            return False

    def generate(self, prompt: str, max_tokens: int = 150) -> str:
        if not self._model:
            return ""
        try:
            result = self._model.generate_content(prompt)
            return (result.text or "").strip()
        except Exception as e:
            logger.warning("Gemini generation failed: %s", e)
            return ""


# ---------------------------------------------------------------------------
# NPC Model Gateway
# ---------------------------------------------------------------------------
class NPCGateway:
    """Central gateway that manages model loading and NPC routing.

    Usage:
        gateway = NPCGateway()
        gateway.initialize()  # Detects hardware, loads models

        # Get a response for an NPC
        response = gateway.generate_npc_response(
            npc_name="polly",
            tongue="KO",
            backstory="Ancient raven familiar...",
            player_input="What should I do next?",
            topic="dungeon_floor_5",
        )
    """

    def __init__(self, custom_model_path: Optional[str] = None) -> None:
        self.hardware = HardwareProfile()
        self.backends: Dict[int, ModelBackend] = {}
        self.active_tier: int = 0
        self.initialized: bool = False
        self.custom_model_path = custom_model_path

        # SFT collection
        self._sft_pairs: List[Dict] = []
        self._sft_flush_count: int = 0

        # Conversation memory per NPC
        self._npc_history: Dict[str, List[Dict[str, str]]] = {}

        # Performance tracking
        self._generation_times: List[float] = []

        # Tri-manifold personality cache per NPC
        self._tri_manifolds: Dict[str, Any] = {}

    def initialize(self, max_tier_override: Optional[int] = None) -> None:
        """Detect hardware and load the best available models."""
        self.hardware = detect_hardware()

        max_tier = max_tier_override if max_tier_override is not None else self.hardware.max_tier
        logger.info(
            "Hardware: %s, GPU=%s (%s), VRAM=%dMB, RAM=%dMB, max_tier=%d",
            self.hardware.platform,
            self.hardware.has_gpu,
            self.hardware.gpu_name or "none",
            self.hardware.vram_mb,
            self.hardware.ram_mb,
            max_tier,
        )

        # Try to load backends from highest tier down
        # We only load ONE local model at a time to conserve memory
        if max_tier > 0:
            for tier in range(min(max_tier, 4), 0, -1):
                backend = self._create_backend(tier)
                if backend and backend.load():
                    self.backends[tier] = backend
                    self.active_tier = tier
                    logger.info("Active model tier: %d (%s)", tier, backend.name)
                    break

        # Also try cloud backends: HF Inference (tier 5) and Gemini
        if max_tier > 0:
            # HF Inference API — fine-tuned model bridge
            hf_backend = self._create_backend(5)
            if hf_backend and hf_backend.load():
                self.backends[5] = hf_backend
                if self.active_tier == 0:
                    self.active_tier = 5
                logger.info("HF Inference bridge active: %s", hf_backend.name)

            # Gemini — general-purpose cloud fallback
            gemini = GeminiBackend()
            if gemini.load():
                self.backends[99] = gemini  # Cloud tier
                if self.active_tier == 0:
                    self.active_tier = 99

        self.initialized = True
        if self.active_tier == 0:
            logger.info("No models loaded — using template fallback only.")

    def _create_backend(self, tier: int) -> Optional[ModelBackend]:
        """Create a backend for the given tier."""
        tier_info = TIER_MODELS.get(tier)
        if not tier_info:
            return None

        # Check for local GGUF files first
        model_dir = MODEL_CACHE_DIR / f"tier_{tier}"
        if model_dir.exists():
            gguf_files = list(model_dir.glob("*.gguf"))
            if gguf_files:
                return LlamaCppBackend(tier, tier_info["name"], str(gguf_files[0]))

        # Try custom model path for tier 5
        if tier == 5 and self.custom_model_path:
            path = Path(self.custom_model_path)
            if path.exists() and path.suffix == ".gguf":
                return LlamaCppBackend(tier, "Aethermoor-Custom", str(path))

        # Tier 5: prefer HF Inference API (cloud bridge to fine-tuned model)
        if tier == 5:
            hf_id = tier_info.get("hf_id", "")
            endpoint = os.environ.get("HF_ENDPOINT_URL", "")
            if hf_id:
                return HuggingFaceInferenceBackend(
                    model_id=hf_id,
                    endpoint_url=endpoint or None,
                )
            return None

        # Fall back to HF transformers (will download on first use)
        hf_id = tier_info.get("hf_id", "")
        if hf_id:
            return TransformersBackend(tier, tier_info["name"], hf_id)

        return None

    def _get_backend_for_npc(self, npc_name: str) -> Optional[ModelBackend]:
        """Route an NPC to the appropriate model backend."""
        importance = NPC_IMPORTANCE.get(
            npc_name.lower(), NPCImportance.AMBIENT
        )

        # MASTER NPCs prefer the HF Inference bridge (fine-tuned model)
        if importance == NPCImportance.MASTER and 5 in self.backends:
            return self.backends[5]

        # COMPANION+ NPCs can also use HF bridge if no local model
        if importance >= NPCImportance.COMPANION and 5 in self.backends:
            if self.active_tier in (0, 99):  # No local model loaded
                return self.backends[5]

        # Use best available local model
        if self.active_tier > 0:
            if self.active_tier == 99:
                return self.backends[99]  # Gemini
            return self.backends.get(self.active_tier)

        return None

    def _get_tri_manifold_context(self, npc_name: str, tongue: str) -> str:
        """Get tri-manifold personality context for an NPC (if available)."""
        if not _HAS_TRI_MANIFOLD:
            return ""
        try:
            key = f"{npc_name}:{tongue}"
            if key not in self._tri_manifolds:
                tm = TriManifoldPersonality(name=npc_name, primary_tongue=tongue)
                tm.activate()
                self._tri_manifolds[key] = tm
            tm = self._tri_manifolds[key]
            state = tm.get_tri_state()
            prompt = tm.generate_system_prompt()
            # Extract the manifold state line (compact)
            lines = prompt.strip().split("\n")
            # Return just the manifold context (first few lines after header)
            manifold_lines = [l for l in lines if "manifold" in l.lower() or "M+" in l or "M-" in l or "M0" in l]
            if manifold_lines:
                return "Tri-Manifold State: " + "; ".join(manifold_lines[:3]) + "\n"
            # Fallback: use raw state
            addr = state.get("address", "")
            dom = state.get("dominant_manifold", "")
            bridge = state.get("bridge_strength", 0)
            if addr:
                return (
                    f"Tri-Manifold: address={addr}, dominant={dom}, "
                    f"bridge_strength={bridge:.2f}\n"
                )
        except Exception as e:
            logger.debug("Tri-manifold context unavailable: %s", e)
        return ""

    def _build_prompt(
        self,
        npc_name: str,
        tongue: str,
        backstory: str,
        player_input: str,
        topic: str = "",
    ) -> str:
        """Build a character prompt for the model."""
        personality = TONGUE_PERSONALITY.get(tongue, "mysterious and ancient")
        tongue_desc = {
            "KO": "Authority and Command",
            "AV": "Transport and Navigation",
            "RU": "Policy and Law",
            "CA": "Compute and Growth",
            "UM": "Shadows and Secrets",
            "DR": "Forge and Creation",
        }.get(tongue, "unknown")

        # Tri-manifold personality enrichment
        tri_context = self._get_tri_manifold_context(npc_name, tongue)

        # Get conversation history
        history = self._npc_history.get(npc_name, [])
        history_text = ""
        if history:
            recent = history[-6:]  # Last 3 exchanges
            lines = []
            for msg in recent:
                role = "Player" if msg["role"] == "user" else npc_name
                lines.append(f"{role}: {msg['content']}")
            history_text = "\n".join(lines) + "\n"

        topic_line = f"\nCurrent context: {topic}\n" if topic else ""

        return (
            f"You are {npc_name}, a character in Aethermoor.\n"
            f"Sacred Tongue: {tongue} ({tongue_desc})\n"
            f"Personality: {personality}\n"
            f"{tri_context}"
            f"Background: {backstory}\n"
            f"Rules: Stay in character. 1-3 sentences. Reference the Six Tongues "
            f"and Aethermoor lore naturally. Never break character.\n"
            f"{topic_line}"
            f"{history_text}"
            f"Player: {player_input}\n"
            f"{npc_name}:"
        )

    def generate_npc_response(
        self,
        npc_name: str,
        tongue: str,
        backstory: str,
        player_input: str,
        topic: str = "",
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate an NPC response using the best available model.

        Returns:
            (response_text, metadata_dict)
        """
        if not self.initialized:
            self.initialize()

        start = time.time()

        backend = self._get_backend_for_npc(npc_name)
        response = ""
        source = "template"

        if backend:
            prompt = self._build_prompt(npc_name, tongue, backstory, player_input, topic)
            response = backend.generate(prompt)
            if response:
                source = f"model:{backend.name}"

        # If no model response, return empty (caller uses template fallback)
        elapsed = time.time() - start
        self._generation_times.append(elapsed)

        # Update conversation history
        if npc_name not in self._npc_history:
            self._npc_history[npc_name] = []
        self._npc_history[npc_name].append({"role": "user", "content": player_input})
        if response:
            self._npc_history[npc_name].append({"role": "assistant", "content": response})

        # Collect SFT pair
        sft_pair = {
            "instruction": (
                f"You are {npc_name} in Aethermoor, aligned with the "
                f"{tongue} tongue. A player says: \"{player_input}\""
            ),
            "response": response or "(template fallback)",
            "metadata": {
                "npc": npc_name,
                "tongue": tongue,
                "topic": topic,
                "source": source,
                "latency_ms": int(elapsed * 1000),
                "timestamp": time.time(),
            },
        }
        self._sft_pairs.append(sft_pair)

        # Auto-flush SFT pairs every 50 exchanges
        if len(self._sft_pairs) >= 50:
            self.flush_sft_pairs()

        metadata = {
            "source": source,
            "tier": backend.tier if backend else 0,
            "latency_ms": int(elapsed * 1000),
            "model_name": backend.name if backend else "none",
        }

        return response, metadata

    def flush_sft_pairs(self) -> Optional[Path]:
        """Write accumulated SFT pairs to disk."""
        if not self._sft_pairs:
            return None

        SFT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self._sft_flush_count += 1
        filename = f"npc_sft_{int(time.time())}_{self._sft_flush_count}.jsonl"
        filepath = SFT_OUTPUT_DIR / filename

        with open(filepath, "w", encoding="utf-8") as f:
            for pair in self._sft_pairs:
                f.write(json.dumps(pair, ensure_ascii=False) + "\n")

        count = len(self._sft_pairs)
        self._sft_pairs.clear()
        logger.info("Flushed %d SFT pairs to %s", count, filepath)
        return filepath

    def get_status(self) -> Dict[str, Any]:
        """Return gateway status for debugging/dashboard."""
        avg_latency = (
            sum(self._generation_times) / len(self._generation_times)
            if self._generation_times else 0
        )
        return {
            "initialized": self.initialized,
            "active_tier": self.active_tier,
            "active_model": (
                self.backends[self.active_tier].name
                if self.active_tier in self.backends
                else "template-only"
            ),
            "hardware": {
                "platform": self.hardware.platform,
                "gpu": self.hardware.gpu_name or "none",
                "vram_mb": self.hardware.vram_mb,
                "ram_mb": self.hardware.ram_mb,
                "max_tier": self.hardware.max_tier,
            },
            "loaded_backends": {
                tier: b.name for tier, b in self.backends.items()
            },
            "sft_pairs_pending": len(self._sft_pairs),
            "total_generations": len(self._generation_times),
            "avg_latency_ms": int(avg_latency * 1000),
            "npc_histories": {
                name: len(hist) for name, hist in self._npc_history.items()
            },
        }

    def download_model(self, tier: int) -> bool:
        """Download a model for the given tier (for setup/provisioning).

        Uses huggingface_hub to download GGUF files to the local cache.
        """
        tier_info = TIER_MODELS.get(tier)
        if not tier_info:
            return False

        gguf_id = tier_info.get("gguf_id", "")
        if not gguf_id:
            logger.info("No GGUF repo for tier %d, will use transformers", tier)
            return True

        try:
            from huggingface_hub import hf_hub_download, list_repo_files

            model_dir = MODEL_CACHE_DIR / f"tier_{tier}"
            model_dir.mkdir(parents=True, exist_ok=True)

            # Find the Q4_K_M quantized file (good balance of speed/quality)
            files = list_repo_files(gguf_id)
            gguf_files = [f for f in files if f.endswith(".gguf")]

            # Prefer Q4_K_M, then Q4_K_S, then any Q4
            target = None
            for pattern in ["Q4_K_M", "Q4_K_S", "Q4", "q4"]:
                matches = [f for f in gguf_files if pattern in f]
                if matches:
                    target = matches[0]
                    break
            if not target and gguf_files:
                target = gguf_files[0]

            if target:
                logger.info("Downloading %s/%s ...", gguf_id, target)
                path = hf_hub_download(
                    gguf_id, target,
                    local_dir=str(model_dir),
                )
                logger.info("Downloaded to: %s", path)
                return True

        except Exception as e:
            logger.warning("Failed to download tier %d model: %s", tier, e)

        return False


# ---------------------------------------------------------------------------
# Convenience: Patch into existing NPCBrain
# ---------------------------------------------------------------------------
_GATEWAY: Optional[NPCGateway] = None


def get_gateway() -> NPCGateway:
    """Get or create the global NPC gateway singleton."""
    global _GATEWAY
    if _GATEWAY is None:
        _GATEWAY = NPCGateway()
    return _GATEWAY


def enhanced_npc_response(
    brain: Any,  # npc_brain.NPCBrain
    player_input: str,
    topic: str = "",
) -> str:
    """Drop-in enhancement for NPCBrain.get_response().

    Tries the model gateway first; falls back to the brain's
    existing logic (Gemini or templates) if the gateway has no model.
    """
    gateway = get_gateway()
    if not gateway.initialized:
        gateway.initialize()

    response, meta = gateway.generate_npc_response(
        npc_name=brain.npc_name,
        tongue=brain.tongue_affinity,
        backstory=brain.backstory,
        player_input=player_input,
        topic=topic,
    )

    if response:
        # Still sanitize through L9
        response = brain._sanitize_response(response)
        # Record in brain's history too
        brain.conversation_history.append({"role": "user", "content": player_input})
        brain.conversation_history.append({"role": "assistant", "content": response})
        return response

    # Fall back to existing brain logic
    return brain.get_response(player_input, topic)


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
def selftest() -> None:
    print(f"\n{'='*60}")
    print("  NPC Model Gateway — Self-Test")
    print(f"{'='*60}\n")

    passed = 0
    failed = 0

    def check(name: str, cond: bool, detail: str = ""):
        nonlocal passed, failed
        if cond:
            passed += 1
            print(f"  PASS  {name}")
        else:
            failed += 1
            print(f"  FAIL  {name}  {detail}")

    # Hardware detection
    hw = detect_hardware()
    check("Hardware detected", hw.platform != "")
    check("RAM detected", hw.ram_mb > 0)
    check("CPU cores detected", hw.cpu_cores > 0)
    check("Max tier >= 0", hw.max_tier >= 0)
    print(f"    Platform: {hw.platform}")
    print(f"    RAM: {hw.ram_mb}MB")
    print(f"    GPU: {hw.gpu_name or 'none'} ({hw.vram_mb}MB)")
    print(f"    Max tier: {hw.max_tier}")

    # Tier models configured
    check("5 tiers defined", len(TIER_MODELS) == 5)
    for tier in range(1, 6):
        info = TIER_MODELS[tier]
        check(f"  Tier {tier} has name", bool(info["name"]))
        check(f"  Tier {tier} has vram_mb", info["vram_mb"] > 0)

    # HF Inference backend class
    check("HF Inference backend exists", HuggingFaceInferenceBackend is not None)
    check("Tier 5 has model ID", TIER_MODELS[5]["hf_id"] == "issdandavis/aethermoor-npc-v1")
    check("Tier 5 name is correct", TIER_MODELS[5]["name"] == "Aethermoor-NPC-v1")

    # NPC importance mapping
    check("Polly is COMPANION", NPC_IMPORTANCE["polly"] == NPCImportance.COMPANION)
    check("Shopkeeper is MERCHANT", NPC_IMPORTANCE["shopkeeper"] == NPCImportance.MERCHANT)
    check("Narrator is NARRATOR", NPC_IMPORTANCE["narrator"] == NPCImportance.NARRATOR)
    check("Elder is MASTER", NPC_IMPORTANCE["elder"] == NPCImportance.MASTER)

    # Tongue personalities
    check("6 tongue personalities", len(TONGUE_PERSONALITY) == 6)
    for code in ("KO", "AV", "RU", "CA", "UM", "DR"):
        check(f"  {code} personality exists", code in TONGUE_PERSONALITY)

    # Gateway creation (no models loaded — just template mode)
    gw = NPCGateway()
    check("Gateway created", gw is not None)
    check("Not yet initialized", not gw.initialized)

    # Initialize in template-only mode (force max_tier=0 to skip downloads)
    gw.initialize(max_tier_override=0)
    check("Gateway initialized", gw.initialized)
    check("Active tier 0 or cloud", gw.active_tier >= 0)

    # Prompt building
    prompt = gw._build_prompt(
        npc_name="Polly",
        tongue="KO",
        backstory="Ancient raven familiar of the first tongue-keeper.",
        player_input="What lies ahead?",
        topic="dungeon_floor_3",
    )
    check("Prompt contains NPC name", "Polly" in prompt)
    check("Prompt contains tongue", "KO" in prompt)
    check("Prompt contains player input", "What lies ahead?" in prompt)
    check("Prompt contains topic", "dungeon_floor_3" in prompt)

    # Generate response (template mode — returns empty, caller uses fallback)
    response, meta = gw.generate_npc_response(
        npc_name="polly",
        tongue="KO",
        backstory="Ancient raven familiar.",
        player_input="Hello Polly!",
        topic="greeting",
    )
    check("Response is string", isinstance(response, str))
    check("Metadata has source", "source" in meta)
    check("Metadata has tier", "tier" in meta)
    check("Metadata has latency", "latency_ms" in meta)

    # Conversation history tracked
    check("Polly history recorded", "polly" in gw._npc_history)
    check("History has entries", len(gw._npc_history["polly"]) >= 1)

    # SFT pair collected
    check("SFT pair collected", len(gw._sft_pairs) >= 1)
    pair = gw._sft_pairs[0]
    check("SFT has instruction", "instruction" in pair)
    check("SFT has response", "response" in pair)
    check("SFT has metadata", "metadata" in pair)
    check("SFT metadata has npc", pair["metadata"]["npc"] == "polly")
    check("SFT metadata has tongue", pair["metadata"]["tongue"] == "KO")

    # Status report
    status = gw.get_status()
    check("Status has initialized", status["initialized"])
    check("Status has hardware", "hardware" in status)
    check("Status has active_tier", "active_tier" in status)
    check("Status has total_generations", status["total_generations"] >= 1)
    print(f"    Active model: {status['active_model']}")
    print(f"    Loaded backends: {status['loaded_backends']}")

    # Multiple NPC interactions
    for name, tongue in [("clay", "RU"), ("eldrin", "AV"), ("zara", "DR")]:
        resp, _ = gw.generate_npc_response(
            npc_name=name, tongue=tongue,
            backstory=f"A character in Aethermoor.",
            player_input="Tell me about yourself.",
        )
        check(f"  {name} response OK", isinstance(resp, str))

    check("Multiple NPCs tracked", len(gw._npc_history) >= 4)
    check("SFT pairs accumulated", len(gw._sft_pairs) >= 4)

    # Flush SFT pairs
    SFT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    path = gw.flush_sft_pairs()
    if path:
        check("SFT flush wrote file", path.exists())
        check("SFT pairs cleared", len(gw._sft_pairs) == 0)
        # Clean up test file
        path.unlink(missing_ok=True)
    else:
        check("SFT flush (no pairs)", True)

    # Enhanced NPC response integration
    from npc_brain import create_npc_brain
    brain = create_npc_brain("polly", "Polly", "KO", "Ancient raven familiar.")
    check("NPCBrain created", brain is not None)

    # Set the global gateway to our test instance (no model downloads)
    global _GATEWAY
    _GATEWAY = gw

    # Test the enhancement function
    enhanced = enhanced_npc_response(brain, "What should I do?", "tutorial")
    check("Enhanced response is string", isinstance(enhanced, str))
    check("Enhanced response not empty", len(enhanced) > 0)

    # Reset global
    _GATEWAY = None

    # Summary
    print(f"\n{'='*60}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    selftest()
