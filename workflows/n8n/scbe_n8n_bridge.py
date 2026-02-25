"""
SCBE n8n Bridge — FastAPI service connecting n8n workflows to SCBE Web Agent
=============================================================================

Endpoints:
  POST /v1/governance/scan        — Semantic antivirus scan
  POST /v1/tongue/encode          — Sacred Tongue encoding
  POST /v1/buffer/post            — Content Buffer posting
  POST /v1/agent/task             — Submit web agent task
  GET  /v1/agent/task/{id}/status — Poll task status
  POST /v1/telemetry/post-result  — Log post telemetry
  POST /v1/training/ingest        — Ingest game events into HF training pipeline
  GET  /v1/training/status        — Training pipeline status
  POST /v1/vertex/train           — Submit Vertex AI training job
  GET  /v1/vertex/job/{id}        — Poll Vertex AI job status
  POST /v1/vertex/predict         — Run Vertex AI prediction
  POST /v1/vertex/push-to-hf     — Push Vertex artifacts to HuggingFace
  POST /v1/hf/pull-model          — Pull model from HuggingFace for Vertex
  GET  /v1/vertex/models           — List Vertex AI models
  GET  /health                    — Health check

Start:
  uvicorn workflows.n8n.scbe_n8n_bridge:app --host 0.0.0.0 --port 8001
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

# Resolve project paths — src/ MUST come before project root to avoid
# the root symphonic_cipher/ shadowing src/symphonic_cipher/ (see CLAUDE.md)
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT = os.path.abspath(os.path.join(_HERE, "..", ".."))
_SRC = os.path.join(_PROJECT, "src")
_DEMO = os.path.join(_PROJECT, "demo")
# Insert src first so concept_blocks resolves correctly
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)
if _DEMO not in sys.path:
    sys.path.insert(0, _DEMO)
if _PROJECT not in sys.path:
    sys.path.append(_PROJECT)  # append, not insert — avoid shadowing

logger = logging.getLogger("scbe_n8n_bridge")

try:
    from fastapi import FastAPI, HTTPException, Header, Request
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel
except ImportError:
    print("pip install fastapi uvicorn  # required for n8n bridge")
    raise

from symphonic_cipher.scbe_aethermoore.concept_blocks.web_agent import (
    SemanticAntivirus,
    ContentBuffer,
    Platform,
    PlatformPublisher,
    AgentOrchestrator,
    WebTask,
    TaskStatus,
)
from symphonic_cipher.scbe_aethermoore.concept_blocks.web_agent.publishers import create_publisher

# ---------------------------------------------------------------------------
#  App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="SCBE n8n Bridge",
    version="1.0.0",
    description="Connects n8n workflow automation to SCBE-AETHERMOORE web agent pipeline",
)

# Shared instances
_antivirus = SemanticAntivirus()
_buffer = ContentBuffer(antivirus=_antivirus)
_orchestrator = AgentOrchestrator(antivirus=_antivirus)
_telemetry: List[Dict[str, Any]] = []

# Register dry-run publishers (replace with real credentials in production)
for plat in Platform:
    _buffer.register_publisher(PlatformPublisher(plat))

# API key validation
_API_KEYS = set(
    k.strip()
    for k in os.environ.get("SCBE_API_KEYS", "scbe-dev-key,test-key").split(",")
    if k.strip()
)


def _check_key(api_key: Optional[str] = None):
    if api_key and api_key in _API_KEYS:
        return
    raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ---------------------------------------------------------------------------
#  Request/response models
# ---------------------------------------------------------------------------

class ScanRequest(BaseModel):
    content: str
    platforms: Optional[List[str]] = None
    scan_mode: str = "full"


class TongueEncodeRequest(BaseModel):
    text: str
    tongue: str = "KO"
    seal: bool = False
    context: Optional[List[float]] = None


class BufferPostRequest(BaseModel):
    text: str
    platforms: List[str] = ["twitter"]
    tags: Optional[List[str]] = None
    schedule_at: Optional[float] = None
    tongue_encode: bool = False
    tongue: Optional[str] = None


class TaskRequest(BaseModel):
    task_type: str = "navigate"
    target_url: Optional[str] = None
    goal: str = ""
    max_steps: int = 50
    parameters: Dict[str, Any] = {}
    # Content posting fields
    text: Optional[str] = None
    platforms: Optional[List[str]] = None


class TelemetryRequest(BaseModel):
    platform: str
    success: bool
    post_url: Optional[str] = None
    timestamp: Optional[str] = None


class TrainingIngestRequest(BaseModel):
    """Game event forwarded from n8n for training data collection."""
    event_type: str
    context: str = ""
    outcome: str = ""
    tongue: str = "KO"
    metadata: Dict[str, Any] = {}


# ---------------------------------------------------------------------------
#  Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "scbe-n8n-bridge",
        "version": "1.0.0",
        "buffer_queue": _buffer.summary(),
        "orchestrator": _orchestrator.summary(),
        "telemetry_count": len(_telemetry),
    }


@app.post("/v1/governance/scan")
async def governance_scan(req: ScanRequest, x_api_key: Optional[str] = Header(None)):
    _check_key(x_api_key)
    profile = _antivirus.scan(req.content)
    return profile.to_dict()


@app.post("/v1/tongue/encode")
async def tongue_encode(req: TongueEncodeRequest, x_api_key: Optional[str] = Header(None)):
    _check_key(x_api_key)
    try:
        from symphonic_cipher.scbe_aethermoore.concept_blocks.web_agent.tongue_transport import TongueTransport
        transport = TongueTransport()
        if req.seal and req.context:
            env = transport.seal(req.text, tongue=req.tongue, context=req.context)
            return {
                "tongue": env.tongue,
                "encoded_text": env.encoded_text,
                "geoseal": env.geoseal,
                "transport": "tongue+geoseal",
            }
        else:
            env = transport.encode(req.text, tongue=req.tongue)
            return {
                "tongue": env.tongue,
                "encoded_text": env.encoded_text,
                "token_count": len(env.tokens),
                "transport": "tongue",
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/buffer/post")
async def buffer_post(req: BufferPostRequest, x_api_key: Optional[str] = Header(None)):
    _check_key(x_api_key)
    text = req.text

    # Optional tongue encoding
    if req.tongue_encode:
        try:
            from symphonic_cipher.scbe_aethermoore.concept_blocks.web_agent.tongue_transport import TongueTransport
            transport = TongueTransport()
            tongue = req.tongue or "KO"
            env = transport.encode(text, tongue=tongue)
            text = env.encoded_text
        except Exception:
            pass  # Fall through to plain text

    post = _buffer.create_post(
        text=text,
        platforms=req.platforms,
        tags=req.tags,
        schedule_at=req.schedule_at,
    )

    if post.status.value == "blocked":
        return {
            "status": "blocked",
            "governance_verdict": post.governance_verdict,
            "governance_risk": post.governance_risk,
        }

    # Publish immediately if no schedule
    results = []
    if not req.schedule_at:
        publish_results = _buffer.publish_due()
        results = [
            {"platform": r.platform.value, "success": r.success, "url": r.post_url}
            for r in publish_results
        ]

    return {
        "post_id": post.post_id,
        "status": post.status.value,
        "platforms": [p.value for p in post.platforms],
        "governance_verdict": post.governance_verdict,
        "governance_risk": post.governance_risk,
        "results": results,
    }


@app.post("/v1/agent/task")
async def submit_task(req: TaskRequest, x_api_key: Optional[str] = Header(None)):
    _check_key(x_api_key)
    from symphonic_cipher.scbe_aethermoore.concept_blocks.web_agent.agent_orchestrator import TaskType

    task = WebTask(
        task_type=TaskType(req.task_type),
        target_url=req.target_url,
        goal=req.goal,
        max_steps=req.max_steps,
        parameters=req.parameters,
    )

    if req.text:
        task.post_content = req.text
    if req.platforms:
        task.post_platforms = req.platforms

    task_id = _orchestrator.submit_task(task)
    return {
        "task_id": task_id,
        "status": task.status.value,
        "task_type": task.task_type.value,
    }


@app.get("/v1/agent/task/{task_id}/status")
async def task_status(task_id: str, x_api_key: Optional[str] = Header(None)):
    _check_key(x_api_key)
    task = _orchestrator.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    result = None
    if task.result:
        result = task.result.to_dict()
    return {
        "task_id": task.task_id,
        "status": task.status.value,
        "task_type": task.task_type.value,
        "result": result,
    }


@app.post("/v1/telemetry/post-result")
async def telemetry_log(req: TelemetryRequest, x_api_key: Optional[str] = Header(None)):
    _check_key(x_api_key)
    entry = {
        "platform": req.platform,
        "success": req.success,
        "post_url": req.post_url,
        "timestamp": req.timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "logged_at": time.time(),
    }
    _telemetry.append(entry)
    return {"status": "logged", "total_entries": len(_telemetry)}


@app.get("/v1/telemetry")
async def telemetry_list(x_api_key: Optional[str] = Header(None)):
    _check_key(x_api_key)
    return {"entries": _telemetry[-100:], "total": len(_telemetry)}


# ---------------------------------------------------------------------------
#  Training pipeline integration (game events -> RealTimeHFTrainer)
# ---------------------------------------------------------------------------

_trainer = None
_trainer_lock = threading.Lock()


def _get_trainer():
    """Lazy-initialise and return the shared RealTimeHFTrainer.

    The trainer is created and started on the first request so that
    importing this module alone does not spawn background threads.
    """
    global _trainer
    if _trainer is not None:
        return _trainer
    with _trainer_lock:
        # Double-check after acquiring the lock
        if _trainer is not None:
            return _trainer
        try:
            from hf_trainer import RealTimeHFTrainer, load_dotenv

            load_dotenv()
            _trainer = RealTimeHFTrainer()
            _trainer.start()
            logger.info("RealTimeHFTrainer started via n8n bridge")
        except Exception as exc:
            logger.error("Failed to start RealTimeHFTrainer: %s", exc)
            raise HTTPException(
                status_code=503,
                detail=f"Training pipeline unavailable: {exc}",
            )
    return _trainer


# Map n8n game event types to TrainingEvent event_type values
_EVENT_TYPE_MAP: Dict[str, str] = {
    "battle_won": "battle",
    "battle_lost": "battle",
    "choice_made": "choice",
    "scene_transition": "dialogue",
    "evolution": "evolution",
    "gacha_pull": "choice",
    "level_up": "evolution",
    "quest_complete": "choice",
    "npc_dialogue": "dialogue",
    "dungeon_floor_cleared": "tower_floor",
    "boss_defeated": "battle",
    "tongue_mastered": "evolution",
    "companion_evolved": "evolution",
    "quest_progress": "choice",
}


@app.post("/v1/training/ingest")
async def training_ingest(
    req: TrainingIngestRequest,
    x_api_key: Optional[str] = Header(None),
):
    """Accept a game event from n8n and feed it to the RealTimeHFTrainer.

    The event is converted into a TrainingEvent (prompt/response SFT pair)
    and enqueued for governance validation, local JSONL export, and
    optional HuggingFace Hub upload.
    """
    _check_key(x_api_key)

    trainer = _get_trainer()

    from hf_trainer import TrainingEvent

    # Build the SFT prompt/response pair from the game event
    mapped_type = _EVENT_TYPE_MAP.get(req.event_type, req.event_type)
    tongue = req.tongue or "KO"

    prompt = f"[{tongue}] {req.event_type}: {req.context}" if req.context else f"[{tongue}] {req.event_type}"
    response = req.outcome or f"{req.event_type} recorded"

    meta: Dict[str, Any] = {
        "tongue": tongue,
        "source": "n8n",
        "original_event_type": req.event_type,
    }
    if req.metadata:
        meta.update(req.metadata)

    event = TrainingEvent(
        event_type=mapped_type,
        prompt=prompt,
        response=response,
        metadata=meta,
    )

    trainer.put_event(event)

    return {
        "status": "queued",
        "event_type": mapped_type,
        "trainer_stats": trainer.get_stats(),
    }


@app.get("/v1/training/status")
async def training_status(x_api_key: Optional[str] = Header(None)):
    """Return the current trainer pipeline status."""
    _check_key(x_api_key)
    trainer = _get_trainer()
    return trainer.get_status_dict()


# ---------------------------------------------------------------------------
#  Vertex AI <-> HuggingFace bridge
# ---------------------------------------------------------------------------

_GCP_PROJECT = os.environ.get("GCP_PROJECT_ID", "gen-lang-client-0103521392")
_GCP_REGION = os.environ.get("GCP_REGION", "us-central1")
_HF_TOKEN = os.environ.get("HF_TOKEN", "")
_HF_MODEL_REPO = os.environ.get("HF_MODEL_REPO", "issdandavis/phdm-21d-embedding")
_HF_DATASET_REPO = os.environ.get("HF_DATASET_REPO", "issdandavis/scbe-aethermoore-datasets")

# Track submitted Vertex jobs
_vertex_jobs: Dict[str, Dict[str, Any]] = {}


def _get_aiplatform():
    """Lazy import and initialise google.cloud.aiplatform."""
    try:
        from google.cloud import aiplatform
        aiplatform.init(project=_GCP_PROJECT, location=_GCP_REGION)
        return aiplatform
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="google-cloud-aiplatform not installed. Run: pip install google-cloud-aiplatform",
        )


def _get_hf_api():
    """Return a HuggingFace Hub API client."""
    try:
        from huggingface_hub import HfApi
        return HfApi(token=_HF_TOKEN or None)
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="huggingface_hub not installed. Run: pip install huggingface_hub",
        )


class VertexTrainRequest(BaseModel):
    """Submit a Vertex AI custom training job."""
    display_name: str = "scbe-training-job"
    container_image_uri: str = "us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-1:latest"
    model_display_name: Optional[str] = None
    training_data_uri: Optional[str] = None  # gs:// path
    args: List[str] = []
    machine_type: str = "n1-standard-4"
    accelerator_type: Optional[str] = None  # e.g. NVIDIA_TESLA_T4
    accelerator_count: int = 0
    push_to_hf: bool = True  # Auto-push result to HuggingFace
    hf_repo: Optional[str] = None


class VertexPredictRequest(BaseModel):
    """Run a Vertex AI online prediction."""
    endpoint_id: str
    instances: List[Dict[str, Any]]
    parameters: Dict[str, Any] = {}


class HFPushRequest(BaseModel):
    """Push local or GCS artifacts to a HuggingFace repo."""
    local_path: Optional[str] = None  # Local dir to upload
    gcs_uri: Optional[str] = None  # gs:// path to download first
    hf_repo: Optional[str] = None
    repo_type: str = "model"  # model, dataset, space
    commit_message: str = "Vertex AI training artifacts"
    path_in_repo: str = "."


class HFPullRequest(BaseModel):
    """Pull a model from HuggingFace to local or GCS."""
    hf_repo: Optional[str] = None
    revision: str = "main"
    local_dir: str = "/tmp/hf_model"
    upload_to_gcs: Optional[str] = None  # gs:// destination


@app.post("/v1/vertex/train")
async def vertex_train(req: VertexTrainRequest, x_api_key: Optional[str] = Header(None)):
    """Submit a Vertex AI custom training job."""
    _check_key(x_api_key)
    aip = _get_aiplatform()

    job_id = str(uuid.uuid4())[:8]

    try:
        job = aip.CustomContainerTrainingJob(
            display_name=req.display_name,
            container_uri=req.container_image_uri,
            model_display_name=req.model_display_name or f"{req.display_name}-model",
        )

        # Run async — store the job reference
        _vertex_jobs[job_id] = {
            "status": "submitted",
            "display_name": req.display_name,
            "push_to_hf": req.push_to_hf,
            "hf_repo": req.hf_repo or _HF_MODEL_REPO,
            "created_at": time.time(),
            "vertex_job": None,
            "machine_type": req.machine_type,
        }

        # For dry-run capability, check if training data exists
        if req.training_data_uri:
            _vertex_jobs[job_id]["training_data"] = req.training_data_uri

        # Submit the training job
        model = job.run(
            args=req.args,
            replica_count=1,
            machine_type=req.machine_type,
            accelerator_type=req.accelerator_type if req.accelerator_count > 0 else None,
            accelerator_count=req.accelerator_count if req.accelerator_count > 0 else None,
            sync=False,
        )

        _vertex_jobs[job_id]["status"] = "running"
        _vertex_jobs[job_id]["vertex_job"] = job.resource_name if hasattr(job, "resource_name") else str(job)

        return {
            "job_id": job_id,
            "status": "running",
            "display_name": req.display_name,
            "vertex_resource": _vertex_jobs[job_id]["vertex_job"],
            "push_to_hf": req.push_to_hf,
            "hf_repo": req.hf_repo or _HF_MODEL_REPO,
        }

    except Exception as e:
        _vertex_jobs[job_id]["status"] = "failed"
        _vertex_jobs[job_id]["error"] = str(e)
        raise HTTPException(status_code=500, detail=f"Vertex training submission failed: {e}")


@app.get("/v1/vertex/job/{job_id}")
async def vertex_job_status(job_id: str, x_api_key: Optional[str] = Header(None)):
    """Poll Vertex AI job status."""
    _check_key(x_api_key)
    if job_id not in _vertex_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return _vertex_jobs[job_id]


@app.post("/v1/vertex/predict")
async def vertex_predict(req: VertexPredictRequest, x_api_key: Optional[str] = Header(None)):
    """Run prediction against a Vertex AI endpoint."""
    _check_key(x_api_key)
    aip = _get_aiplatform()

    try:
        endpoint = aip.Endpoint(req.endpoint_id)
        response = endpoint.predict(
            instances=req.instances,
            parameters=req.parameters,
        )
        return {
            "predictions": [p if isinstance(p, dict) else {"value": p} for p in response.predictions],
            "deployed_model_id": response.deployed_model_id,
            "model_version_id": getattr(response, "model_version_id", None),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {e}")


@app.post("/v1/vertex/push-to-hf")
async def vertex_push_to_hf(req: HFPushRequest, x_api_key: Optional[str] = Header(None)):
    """Push Vertex AI training artifacts to HuggingFace Hub."""
    _check_key(x_api_key)
    api = _get_hf_api()
    repo = req.hf_repo or _HF_MODEL_REPO

    try:
        # If GCS URI provided, download first
        local_path = req.local_path
        if req.gcs_uri and not local_path:
            import subprocess
            local_path = f"/tmp/vertex_artifacts_{uuid.uuid4().hex[:8]}"
            os.makedirs(local_path, exist_ok=True)
            result = subprocess.run(
                ["gsutil", "-m", "cp", "-r", req.gcs_uri, local_path],
                capture_output=True, text=True, timeout=300,
            )
            if result.returncode != 0:
                raise HTTPException(status_code=500, detail=f"GCS download failed: {result.stderr}")

        if not local_path or not os.path.exists(local_path):
            raise HTTPException(status_code=400, detail="No valid local_path or gcs_uri provided")

        # Ensure repo exists
        try:
            api.create_repo(repo_id=repo, repo_type=req.repo_type, exist_ok=True)
        except Exception:
            pass  # Repo already exists

        # Upload to HuggingFace
        upload_info = api.upload_folder(
            folder_path=local_path,
            repo_id=repo,
            repo_type=req.repo_type,
            path_in_repo=req.path_in_repo,
            commit_message=req.commit_message,
        )

        return {
            "status": "pushed",
            "hf_repo": repo,
            "repo_type": req.repo_type,
            "commit_url": str(upload_info) if upload_info else None,
            "source": req.gcs_uri or req.local_path,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Push to HF failed: {e}")


@app.post("/v1/hf/pull-model")
async def hf_pull_model(req: HFPullRequest, x_api_key: Optional[str] = Header(None)):
    """Pull a model from HuggingFace to local storage or GCS."""
    _check_key(x_api_key)
    api = _get_hf_api()
    repo = req.hf_repo or _HF_MODEL_REPO

    try:
        from huggingface_hub import snapshot_download

        local_dir = snapshot_download(
            repo_id=repo,
            revision=req.revision,
            local_dir=req.local_dir,
            token=_HF_TOKEN or None,
        )

        result: Dict[str, Any] = {
            "status": "downloaded",
            "hf_repo": repo,
            "revision": req.revision,
            "local_dir": str(local_dir),
        }

        # Optionally upload to GCS for Vertex AI
        if req.upload_to_gcs:
            import subprocess
            gcs_result = subprocess.run(
                ["gsutil", "-m", "cp", "-r", str(local_dir), req.upload_to_gcs],
                capture_output=True, text=True, timeout=600,
            )
            if gcs_result.returncode == 0:
                result["gcs_uri"] = req.upload_to_gcs
                result["gcs_status"] = "uploaded"
            else:
                result["gcs_status"] = "failed"
                result["gcs_error"] = gcs_result.stderr

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"HF pull failed: {e}")


@app.get("/v1/vertex/models")
async def vertex_list_models(x_api_key: Optional[str] = Header(None)):
    """List models registered in Vertex AI Model Registry."""
    _check_key(x_api_key)
    aip = _get_aiplatform()
    try:
        models = aip.Model.list()
        return {
            "models": [
                {
                    "display_name": m.display_name,
                    "resource_name": m.resource_name,
                    "create_time": str(m.create_time),
                    "update_time": str(m.update_time),
                }
                for m in models
            ],
            "count": len(models),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"List models failed: {e}")
