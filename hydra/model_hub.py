"""
HYDRA Model Hub — Unified HuggingFace + Vertex AI Configuration
================================================================

Central registry that connects:
  training config → HF Hub models → Vertex AI deployment → HYDRA Head inference

Each Sacred Tongue head has:
  1. A base model (from HF Hub)
  2. A LoRA adapter (trained via vertex_hydra_trainer.py)
  3. A HF repo for storing adapters
  4. Vertex AI endpoints for production inference
  5. Fallback providers (Claude/Gemini/GPT) when custom models unavailable

Usage:
    from hydra.model_hub import ModelHub

    hub = ModelHub()
    hub.status()                          # Show all 6 heads + their models
    provider = hub.provider("KO")         # Get inference provider for KO head
    response = await provider.complete("Navigate to example.com")

    # Hot-swap a model
    hub.swap_model("DR", "mistralai/Mistral-7B-Instruct-v0.3")

    # Push trained adapter to HF
    await hub.push_to_hf("KO", "./hydra-models/hydra-ko-scout")

    # Deploy to Vertex AI
    await hub.deploy_to_vertex("DR")
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

# Ensure project root importable
_PROJECT = Path(__file__).resolve().parents[1]
if str(_PROJECT / "src") not in sys.path:
    sys.path.insert(0, str(_PROJECT / "src"))
if str(_PROJECT) not in sys.path:
    sys.path.append(str(_PROJECT))

from .llm_providers import (
    LLMProvider,
    LLMResponse,
    HuggingFaceProvider,
    create_provider,
)


# ---------------------------------------------------------------------------
#  Config loader
# ---------------------------------------------------------------------------

CONFIG_PATH = _PROJECT / "training" / "hydra_multi_model_config.yaml"

TONGUE_ORDER = ["KO", "AV", "RU", "CA", "UM", "DR"]
PHI = 1.618033988749895


@dataclass
class HeadConfig:
    """Parsed config for a single Sacred Tongue head."""
    tongue: str
    role: str
    description: str
    base_model: str
    hf_repo: str
    model_size_gb: float
    lora_r: int
    lora_alpha: int
    training_categories: List[str]
    vertex_machine: str
    vertex_accelerator: str
    weight: float  # phi-scaled tongue weight


@dataclass
class ModelState:
    """Runtime state for a head's model."""
    tongue: str
    active_model: str          # Currently loaded model ID
    adapter_path: Optional[str] = None  # Local LoRA adapter path
    hf_pushed: bool = False
    vertex_endpoint: Optional[str] = None
    provider: Optional[LLMProvider] = None
    provider_type: str = "fallback"  # "custom" | "hf" | "fallback"


def load_config(path: Optional[Path] = None) -> dict:
    p = path or CONFIG_PATH
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_heads(config: dict) -> Dict[str, HeadConfig]:
    """Parse all head configs from the YAML."""
    heads = {}
    weights = config.get("tongue_weights", {})
    for tongue in TONGUE_ORDER:
        h = config.get("heads", {}).get(tongue)
        if not h:
            continue
        lora = h.get("lora", {})
        vc = h.get("vertex_compute", {})
        td = h.get("training_data", {})
        heads[tongue] = HeadConfig(
            tongue=tongue,
            role=h.get("role", ""),
            description=h.get("description", ""),
            base_model=h.get("base_model", ""),
            hf_repo=h.get("hf_repo", ""),
            model_size_gb=h.get("model_size_gb", 0),
            lora_r=lora.get("r", 16),
            lora_alpha=lora.get("alpha", 32),
            training_categories=td.get("categories", []),
            vertex_machine=vc.get("machine_type", "n1-standard-4"),
            vertex_accelerator=vc.get("accelerator", "NVIDIA_TESLA_T4"),
            weight=weights.get(tongue, 1.0),
        )
    return heads


# ---------------------------------------------------------------------------
#  Model Hub
# ---------------------------------------------------------------------------

class ModelHub:
    """Unified model registry for all 6 HYDRA heads.

    Manages the lifecycle: config → train → push → deploy → infer.
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.config = load_config(config_path)
        self.heads = parse_heads(self.config)
        self.states: Dict[str, ModelState] = {}
        self._hf_api = None
        self._hf_token = os.environ.get("HF_TOKEN", "")

        # Initialize states from config
        for tongue, hc in self.heads.items():
            self.states[tongue] = ModelState(
                tongue=tongue,
                active_model=hc.base_model,
            )

    # ------------------------------------------------------------------
    #  Status
    # ------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        """Full status of all 6 heads."""
        result = {"heads": {}, "hf_token_set": bool(self._hf_token)}
        for tongue in TONGUE_ORDER:
            hc = self.heads.get(tongue)
            st = self.states.get(tongue)
            if not hc or not st:
                continue
            result["heads"][tongue] = {
                "role": hc.role,
                "base_model": hc.base_model,
                "active_model": st.active_model,
                "hf_repo": hc.hf_repo,
                "adapter": st.adapter_path or "none",
                "provider_type": st.provider_type,
                "vertex_endpoint": st.vertex_endpoint or "none",
                "weight": hc.weight,
                "size_gb": hc.model_size_gb,
                "categories": hc.training_categories,
            }
        return result

    def status_text(self) -> str:
        """Human-readable status string."""
        s = self.status()
        lines = ["HYDRA Model Hub — 6 Sacred Tongue Heads", "=" * 45]
        lines.append(f"HF Token: {'SET' if s['hf_token_set'] else 'NOT SET'}")
        lines.append("")
        for tongue in TONGUE_ORDER:
            h = s["heads"].get(tongue, {})
            lines.append(
                f"  {tongue} ({h.get('role', '?'):8s}) | "
                f"{h.get('active_model', '?'):40s} | "
                f"{h.get('provider_type', '?'):8s} | "
                f"w={h.get('weight', 0):.3f}"
            )
        return "\n".join(lines)

    # ------------------------------------------------------------------
    #  Provider management
    # ------------------------------------------------------------------

    def provider(self, tongue: str) -> LLMProvider:
        """Get or create an LLM provider for a head.

        Priority — we're training our own models, so HF first:
        1. Custom fine-tuned HF model (issdandavis/hydra-{tongue}-{role})
        2. HF Inference with the base model from config
        3. HF repo for the tongue's hf_repo (even if not trained yet — test it)
        4. Fallback provider from config (loose — just needs to work)
        5. Offline dummy (last resort)
        """
        st = self.states.get(tongue)
        if not st:
            raise ValueError(f"Unknown tongue: {tongue}")

        if st.provider:
            return st.provider

        hc = self.heads[tongue]

        # 1. Custom HF model (trained adapter pushed to Hub)
        if self._hf_token and st.adapter_path:
            try:
                st.provider = HuggingFaceProvider(
                    model=hc.hf_repo,
                    api_key=self._hf_token,
                )
                st.provider_type = "custom"
                return st.provider
            except Exception:
                pass

        # 2. HF Inference with base model (the one we're training FROM)
        if self._hf_token:
            try:
                st.provider = HuggingFaceProvider(
                    model=hc.base_model,
                    api_key=self._hf_token,
                )
                st.provider_type = "hf_base"
                return st.provider
            except Exception:
                pass

        # 3. Try the HF repo directly (might have been pushed outside this session)
        if self._hf_token and hc.hf_repo:
            try:
                st.provider = HuggingFaceProvider(
                    model=hc.hf_repo,
                    api_key=self._hf_token,
                )
                st.provider_type = "hf_repo"
                return st.provider
            except Exception:
                pass

        # 4. Fallback — loose, just pick whatever works
        fallbacks = self.config.get("inference", {}).get("fallback_providers", {})
        fb = fallbacks.get(tongue, {"provider": "hf", "model": "mistralai/Mistral-7B-Instruct-v0.3"})
        try:
            st.provider = create_provider(fb["provider"], model=fb.get("model"))
            st.provider_type = "fallback"
        except Exception:
            # 5. Offline — still returns a response explaining the situation
            st.provider = _DummyProvider(tongue)
            st.provider_type = "offline"

        return st.provider

    def swap_model(self, tongue: str, model_id: str, provider_type: str = "hf") -> None:
        """Hot-swap a head's model without restart."""
        st = self.states.get(tongue)
        if not st:
            raise ValueError(f"Unknown tongue: {tongue}")

        st.active_model = model_id
        st.provider = None  # Force re-creation on next .provider() call
        st.provider_type = provider_type
        print(f"[MODEL-HUB] {tongue} swapped to {model_id}")

    def temperatures(self) -> Dict[str, float]:
        """Get per-tongue temperature settings."""
        return self.config.get("inference", {}).get("temperatures", {
            "KO": 0.3, "AV": 0.5, "RU": 0.4, "CA": 0.2, "UM": 0.1, "DR": 0.0,
        })

    # ------------------------------------------------------------------
    #  HuggingFace Hub operations
    # ------------------------------------------------------------------

    def _ensure_hf_api(self):
        if self._hf_api:
            return self._hf_api
        if not self._hf_token:
            raise RuntimeError("HF_TOKEN not set — cannot access HuggingFace Hub")
        from huggingface_hub import HfApi
        self._hf_api = HfApi(token=self._hf_token)
        return self._hf_api

    async def push_to_hf(self, tongue: str, adapter_dir: str) -> Dict[str, Any]:
        """Push a trained LoRA adapter to HuggingFace Hub."""
        hc = self.heads.get(tongue)
        if not hc:
            return {"success": False, "error": f"Unknown tongue: {tongue}"}

        api = self._ensure_hf_api()
        loop = asyncio.get_event_loop()

        try:
            await loop.run_in_executor(
                None,
                lambda: api.create_repo(repo_id=hc.hf_repo, repo_type="model", exist_ok=True),
            )
            await loop.run_in_executor(
                None,
                lambda: api.upload_folder(
                    folder_path=adapter_dir,
                    repo_id=hc.hf_repo,
                    repo_type="model",
                ),
            )
            self.states[tongue].adapter_path = adapter_dir
            self.states[tongue].hf_pushed = True
            return {"success": True, "repo": hc.hf_repo, "url": f"https://huggingface.co/{hc.hf_repo}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def list_hf_models(self) -> List[Dict[str, Any]]:
        """List all HYDRA models on HuggingFace Hub."""
        api = self._ensure_hf_api()
        hf_org = self.config.get("project", {}).get("hf_org", "issdandavis")
        loop = asyncio.get_event_loop()

        try:
            models = await loop.run_in_executor(
                None, lambda: list(api.list_models(author=hf_org, search="hydra"))
            )
            return [
                {"id": m.modelId, "downloads": getattr(m, "downloads", 0), "updated": str(getattr(m, "lastModified", ""))}
                for m in models
            ]
        except Exception as e:
            return [{"error": str(e)}]

    async def pull_adapter(self, tongue: str, output_dir: str = "./hydra-models") -> Dict[str, Any]:
        """Pull a trained adapter from HuggingFace Hub."""
        hc = self.heads.get(tongue)
        if not hc:
            return {"success": False, "error": f"Unknown tongue: {tongue}"}

        api = self._ensure_hf_api()
        local_dir = os.path.join(output_dir, f"hydra-{tongue.lower()}-{hc.role}")
        loop = asyncio.get_event_loop()

        try:
            await loop.run_in_executor(
                None,
                lambda: api.snapshot_download(repo_id=hc.hf_repo, local_dir=local_dir),
            )
            self.states[tongue].adapter_path = local_dir
            return {"success": True, "path": local_dir, "repo": hc.hf_repo}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    #  Vertex AI operations
    # ------------------------------------------------------------------

    async def deploy_to_vertex(self, tongue: str) -> Dict[str, Any]:
        """Deploy a trained model to a Vertex AI endpoint."""
        hc = self.heads.get(tongue)
        if not hc:
            return {"success": False, "error": f"Unknown tongue: {tongue}"}

        try:
            from google.cloud import aiplatform

            project = self.config.get("project", {}).get("gcp_project_id", "")
            region = self.config.get("project", {}).get("gcp_region", "us-central1")
            aiplatform.init(project=project, location=region)

            loop = asyncio.get_event_loop()

            # Upload model
            display_name = f"hydra-{tongue.lower()}-{hc.role}"
            model = await loop.run_in_executor(
                None,
                lambda: aiplatform.Model.upload(
                    display_name=display_name,
                    serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/pytorch-gpu.2-0:latest",
                    artifact_uri=f"gs://scbe-vertex-staging/models/{display_name}",
                ),
            )

            # Deploy to endpoint
            endpoint = await loop.run_in_executor(
                None,
                lambda: aiplatform.Endpoint.create(display_name=f"{display_name}-endpoint"),
            )

            await loop.run_in_executor(
                None,
                lambda: endpoint.deploy(
                    model=model,
                    machine_type=hc.vertex_machine,
                    accelerator_type=hc.vertex_accelerator,
                    accelerator_count=1,
                    min_replica_count=0,
                    max_replica_count=2,
                ),
            )

            self.states[tongue].vertex_endpoint = endpoint.resource_name
            return {
                "success": True,
                "endpoint": endpoint.resource_name,
                "model": model.resource_name,
            }
        except ImportError:
            return {"success": False, "error": "google-cloud-aiplatform not installed"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def submit_vertex_training(self, tongue: str) -> Dict[str, Any]:
        """Submit a QLoRA training job to Vertex AI."""
        hc = self.heads.get(tongue)
        if not hc:
            return {"success": False, "error": f"Unknown tongue: {tongue}"}

        try:
            from google.cloud import aiplatform

            project = self.config.get("project", {}).get("gcp_project_id", "")
            region = self.config.get("project", {}).get("gcp_region", "us-central1")
            registry = self.config.get("project", {}).get("artifact_registry", "")
            aiplatform.init(project=project, location=region)

            import time
            display_name = f"hydra-{tongue.lower()}-train-{int(time.time())}"

            loop = asyncio.get_event_loop()
            job = await loop.run_in_executor(
                None,
                lambda: aiplatform.CustomContainerTrainingJob(
                    display_name=display_name,
                    container_uri=f"{registry}/trainer:latest",
                    command=["python", "training/vertex_hydra_trainer.py", "--head", tongue, "--push"],
                ),
            )

            await loop.run_in_executor(
                None,
                lambda: job.run(
                    machine_type=hc.vertex_machine,
                    accelerator_type=hc.vertex_accelerator,
                    accelerator_count=1,
                    environment_variables={
                        "HF_TOKEN": self._hf_token,
                        "TONGUE": tongue,
                    },
                ),
            )

            return {"success": True, "job": display_name, "tongue": tongue}
        except ImportError:
            return {"success": False, "error": "google-cloud-aiplatform not installed"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    #  Governance integration
    # ------------------------------------------------------------------

    def governance_config(self) -> Dict[str, Any]:
        """Return the governance section of the config."""
        return self.config.get("governance", {})

    def quality_gates(self) -> Dict[str, Any]:
        """Return quality gate thresholds."""
        return self.config.get("quality_gates", {})

    # ------------------------------------------------------------------
    #  Bulk operations
    # ------------------------------------------------------------------

    async def train_all_local(self, output_base: str = "./hydra-models", push: bool = False) -> Dict[str, str]:
        """Train all 6 heads sequentially on local GPU."""
        from training.vertex_hydra_trainer import train_head_local
        results = {}
        for tongue in TONGUE_ORDER:
            try:
                path = train_head_local(tongue, self.config, output_base, push)
                results[tongue] = path or "skipped"
                if path:
                    self.states[tongue].adapter_path = path
            except Exception as e:
                results[tongue] = f"error: {e}"
        return results

    async def push_all_to_hf(self, adapter_base: str = "./hydra-models") -> Dict[str, Any]:
        """Push all trained adapters to HuggingFace Hub."""
        results = {}
        for tongue in TONGUE_ORDER:
            hc = self.heads[tongue]
            adapter_dir = os.path.join(adapter_base, f"hydra-{tongue.lower()}-{hc.role}")
            if os.path.isdir(adapter_dir):
                results[tongue] = await self.push_to_hf(tongue, adapter_dir)
            else:
                results[tongue] = {"success": False, "error": "adapter not found locally"}
        return results


# ---------------------------------------------------------------------------
#  Dummy provider for offline mode
# ---------------------------------------------------------------------------

class _DummyProvider(LLMProvider):
    """Returns an error message instead of calling an API."""

    def __init__(self, tongue: str):
        self._tongue = tongue

    async def complete(self, prompt, system=None, max_tokens=4096, temperature=0.7):
        return LLMResponse(
            text=f"[OFFLINE] {self._tongue} head has no active provider. Set HF_TOKEN or API keys.",
            model="dummy",
            input_tokens=0,
            output_tokens=0,
            finish_reason="error",
        )

    async def stream(self, prompt, system=None, max_tokens=4096, temperature=0.7):
        yield f"[OFFLINE] {self._tongue} head unavailable."
