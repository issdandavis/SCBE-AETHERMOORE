"""
HYDRA Apprentice Provider — Dual-Benefit Training Loop
=======================================================

Wraps a custom HuggingFace model (your fine-tuned SCBE model) so that any
HYDRA head (Claude, GPT, Codex, etc.) can delegate sub-tasks to it as an
"apprentice". Every interaction is recorded as SFT training data that flows
back to HuggingFace, creating a self-improving loop:

    ┌────────────┐     delegate()     ┌──────────────────┐
    │  HYDRA Head│────────────────────▶│ ApprenticeProvider│
    │  (Claude)  │◀────────────────────│  (Your HF Model) │
    │            │     response        │                  │
    └────────────┘                     └────────┬─────────┘
         │                                      │
         │  mentor_feedback()                   │ record_pair()
         ▼                                      ▼
    ┌─────────────────────────────────────────────────────┐
    │          SFT Training Buffer → HuggingFace Hub      │
    │   training-data/apprentice_sessions/*.jsonl          │
    └─────────────────────────────────────────────────────┘

Dual benefits:
1. The apprentice model gets better at SCBE-specific tasks over time
2. The mentor head gets a fast, cheap assistant for sub-tasks
3. Training data is governance-filtered (only ALLOW/QUARANTINE pairs kept)

Usage:
    apprentice = ApprenticeProvider(
        model_id="issdandavis/scbe-aethermoore-v1",
        mentor_type="claude",
    )

    # Mentor delegates a sub-task
    result = await apprentice.delegate(
        task="Classify this domain's risk level: banking.example.com",
        context={"tongue": "RU", "layer": 13},
    )

    # Mentor reviews and provides feedback (becomes training signal)
    await apprentice.mentor_feedback(
        interaction_id=result.interaction_id,
        approved=True,
        correction=None,  # or corrected response text
        quality_score=0.85,
    )
"""

import asyncio
import json
import os
import uuid
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional

from .llm_providers import (
    LLMProvider,
    LLMResponse,
    HuggingFaceProvider,
    HYDRA_SYSTEM_PROMPT,
    _retry_with_backoff,
)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class ApprenticeInteraction:
    """A single mentor-apprentice interaction record."""

    interaction_id: str
    timestamp: str
    mentor_type: str
    task_prompt: str
    apprentice_response: str
    context: Dict[str, Any]
    # Filled in after mentor review
    approved: Optional[bool] = None
    correction: Optional[str] = None
    quality_score: Optional[float] = None
    tongue: Optional[str] = None
    layers: Optional[List[int]] = None
    model_id: str = ""

    def to_sft_pair(self) -> Optional[Dict[str, Any]]:
        """Convert to SFT training pair if approved.

        Returns None if not yet reviewed or if rejected without correction.
        """
        if self.approved is None:
            return None

        # Use correction if provided, otherwise original response
        response = self.correction if self.correction else self.apprentice_response
        if not self.approved and not self.correction:
            return None  # Rejected with no correction = no training signal

        return {
            "instruction": self.task_prompt,
            "input": json.dumps(self.context) if self.context else "",
            "output": response,
            "metadata": {
                "source": "apprentice_loop",
                "mentor_type": self.mentor_type,
                "model_id": self.model_id,
                "quality_score": self.quality_score,
                "approved": self.approved,
                "corrected": self.correction is not None,
                "tongue": self.tongue,
                "layers": self.layers,
                "timestamp": self.timestamp,
                "interaction_id": self.interaction_id,
            },
        }


@dataclass
class DelegationResult:
    """Result from delegating a task to the apprentice."""

    interaction_id: str
    response: str
    model: str
    input_tokens: int
    output_tokens: int
    confidence: float  # Self-assessed confidence (0-1)
    latency_ms: float


@dataclass
class ApprenticeStats:
    """Running statistics for the apprentice session."""

    total_delegations: int = 0
    approved_count: int = 0
    corrected_count: int = 0
    rejected_count: int = 0
    pending_review: int = 0
    avg_quality_score: float = 0.0
    total_sft_pairs: int = 0
    session_id: str = field(
        default_factory=lambda: f"apprentice-{uuid.uuid4().hex[:8]}"
    )


# ---------------------------------------------------------------------------
# Apprentice system prompts per tongue
# ---------------------------------------------------------------------------

TONGUE_APPRENTICE_PROMPTS = {
    "KO": (
        "You are an SCBE apprentice specializing in execution and trust "
        "assessment (KO tongue). Respond with precise, actionable analysis. "
        "Focus on operational safety and trust scoring."
    ),
    "AV": (
        "You are an SCBE apprentice specializing in ethical evaluation "
        "(AV tongue). Assess moral implications and alignment with human values. "
        "Be nuanced but decisive."
    ),
    "RU": (
        "You are an SCBE apprentice specializing in logical analysis and "
        "research (RU tongue). Apply rigorous reasoning and cite evidence. "
        "Identify logical fallacies and gaps."
    ),
    "CA": (
        "You are an SCBE apprentice specializing in causal reasoning "
        "(CA tongue). Trace cause-effect chains, identify confounders, "
        "and predict downstream consequences."
    ),
    "UM": (
        "You are an SCBE apprentice specializing in memory and historical "
        "pattern matching (UM tongue). Reference past interactions and learned "
        "patterns. Detect drift from established baselines."
    ),
    "DR": (
        "You are an SCBE apprentice specializing in risk assessment and "
        "predictive analysis (DR tongue). Evaluate threats, assign risk scores, "
        "and recommend mitigations with confidence intervals."
    ),
}


# ---------------------------------------------------------------------------
# Apprentice Provider
# ---------------------------------------------------------------------------


class ApprenticeProvider(LLMProvider):
    """An LLM provider that wraps a HuggingFace model as a training apprentice.

    Implements the LLMProvider interface so it can be used as a standard
    HYDRA head, while adding dual-benefit training capabilities.
    """

    def __init__(
        self,
        model_id: str = "issdandavis/scbe-aethermoore-v1",
        mentor_type: str = "claude",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        output_dir: str = "training-data/apprentice_sessions",
        auto_flush_interval: int = 10,
        tongue: Optional[str] = None,
    ):
        """Initialize the apprentice provider.

        Args:
            model_id: HuggingFace model ID or Inference Endpoint URL.
            mentor_type: What kind of AI is mentoring (for metadata).
            api_key: HF_TOKEN (defaults to env var).
            base_url: Custom inference endpoint URL (for dedicated endpoints).
            output_dir: Where to write JSONL training pairs.
            auto_flush_interval: Flush to disk every N interactions.
            tongue: Sacred Tongue specialization (KO/AV/RU/CA/UM/DR).
        """
        self.model_id = model_id
        self.mentor_type = mentor_type
        self.tongue = tongue
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._auto_flush_interval = auto_flush_interval

        # Initialize the underlying HF provider
        self._hf_provider = HuggingFaceProvider(
            model=model_id,
            api_key=api_key,
            base_url=base_url,
        )

        # Interaction buffer
        self._interactions: Dict[str, ApprenticeInteraction] = {}
        self._sft_buffer: List[Dict[str, Any]] = []
        self._stats = ApprenticeStats()

        # Session file
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self._session_file = self.output_dir / f"apprentice_{ts}_{self._stats.session_id}.jsonl"

    # ------------------------------------------------------------------
    # Core LLMProvider interface
    # ------------------------------------------------------------------

    async def complete(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """Standard completion — delegates to the HF model."""
        if system is None and self.tongue and self.tongue in TONGUE_APPRENTICE_PROMPTS:
            system = TONGUE_APPRENTICE_PROMPTS[self.tongue]
        return await self._hf_provider.complete(prompt, system, max_tokens, temperature)

    async def stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Standard streaming — delegates to the HF model."""
        if system is None and self.tongue and self.tongue in TONGUE_APPRENTICE_PROMPTS:
            system = TONGUE_APPRENTICE_PROMPTS[self.tongue]
        async for chunk in self._hf_provider.stream(prompt, system, max_tokens, temperature):
            yield chunk

    # ------------------------------------------------------------------
    # Dual-benefit delegation interface
    # ------------------------------------------------------------------

    async def delegate(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        tongue: Optional[str] = None,
        layers: Optional[List[int]] = None,
        max_tokens: int = 2048,
        temperature: float = 0.5,
    ) -> DelegationResult:
        """Delegate a sub-task to the apprentice model.

        The mentor (e.g., Claude) calls this to offload work to the
        custom HF model. The interaction is recorded for training.

        Args:
            task: The sub-task instruction/prompt.
            context: Additional context (domain, session state, etc.).
            tongue: Sacred Tongue to use (overrides default).
            layers: SCBE layers relevant to this task.
            max_tokens: Max response length.
            temperature: Sampling temperature (lower = more deterministic).

        Returns:
            DelegationResult with the apprentice's response and metadata.
        """
        interaction_id = f"appr-{uuid.uuid4().hex[:12]}"
        active_tongue = tongue or self.tongue
        context = context or {}

        # Pick system prompt based on tongue
        system = None
        if active_tongue and active_tongue in TONGUE_APPRENTICE_PROMPTS:
            system = TONGUE_APPRENTICE_PROMPTS[active_tongue]

        # Enhance prompt with context
        enhanced_prompt = task
        if context:
            ctx_str = ", ".join(f"{k}={v}" for k, v in context.items())
            enhanced_prompt = f"[Context: {ctx_str}]\n\n{task}"

        # Call the model
        import time

        start = time.monotonic()
        response = await self._hf_provider.complete(
            enhanced_prompt, system, max_tokens, temperature
        )
        latency = (time.monotonic() - start) * 1000

        # Estimate confidence from response characteristics
        confidence = self._estimate_confidence(response)

        # Record the interaction
        interaction = ApprenticeInteraction(
            interaction_id=interaction_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            mentor_type=self.mentor_type,
            task_prompt=task,
            apprentice_response=response.text,
            context=context,
            tongue=active_tongue,
            layers=layers,
            model_id=self.model_id,
        )
        self._interactions[interaction_id] = interaction
        self._stats.total_delegations += 1
        self._stats.pending_review += 1

        return DelegationResult(
            interaction_id=interaction_id,
            response=response.text,
            model=response.model,
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            confidence=confidence,
            latency_ms=latency,
        )

    async def mentor_feedback(
        self,
        interaction_id: str,
        approved: bool,
        correction: Optional[str] = None,
        quality_score: float = 0.7,
    ) -> Optional[Dict[str, Any]]:
        """Mentor provides feedback on an apprentice response.

        This is the training signal. Approved responses (possibly with
        corrections) become SFT training pairs.

        Args:
            interaction_id: ID from the DelegationResult.
            approved: Whether the response was acceptable.
            correction: Corrected response text (optional).
            quality_score: 0-1 quality rating.

        Returns:
            The SFT pair if one was generated, else None.
        """
        interaction = self._interactions.get(interaction_id)
        if not interaction:
            return None

        interaction.approved = approved
        interaction.correction = correction
        interaction.quality_score = quality_score

        self._stats.pending_review = max(0, self._stats.pending_review - 1)

        if approved:
            self._stats.approved_count += 1
        elif correction:
            self._stats.corrected_count += 1
        else:
            self._stats.rejected_count += 1

        # Update running average quality
        reviewed = self._stats.approved_count + self._stats.corrected_count
        if reviewed > 0:
            prev_total = self._stats.avg_quality_score * (reviewed - 1)
            self._stats.avg_quality_score = (prev_total + quality_score) / reviewed

        # Generate SFT pair
        sft_pair = interaction.to_sft_pair()
        if sft_pair:
            self._sft_buffer.append(sft_pair)
            self._stats.total_sft_pairs += 1

            # Auto-flush
            if len(self._sft_buffer) >= self._auto_flush_interval:
                await self.flush_training_data()

        return sft_pair

    # ------------------------------------------------------------------
    # Batch delegation (for parallel sub-tasks)
    # ------------------------------------------------------------------

    async def delegate_batch(
        self,
        tasks: List[Dict[str, Any]],
        max_concurrency: int = 3,
    ) -> List[DelegationResult]:
        """Delegate multiple sub-tasks concurrently.

        Args:
            tasks: List of dicts with keys: task, context, tongue, layers.
            max_concurrency: Max parallel requests.

        Returns:
            List of DelegationResults in the same order as tasks.
        """
        semaphore = asyncio.Semaphore(max_concurrency)

        async def _bounded_delegate(t: Dict[str, Any]) -> DelegationResult:
            async with semaphore:
                return await self.delegate(
                    task=t.get("task", ""),
                    context=t.get("context"),
                    tongue=t.get("tongue"),
                    layers=t.get("layers"),
                )

        return await asyncio.gather(*[_bounded_delegate(t) for t in tasks])

    # ------------------------------------------------------------------
    # Auto-approve pattern (mentor trusts apprentice on low-risk tasks)
    # ------------------------------------------------------------------

    async def delegate_and_auto_approve(
        self,
        task: str,
        context: Optional[Dict[str, Any]] = None,
        tongue: Optional[str] = None,
        min_confidence: float = 0.7,
        auto_quality: float = 0.6,
    ) -> DelegationResult:
        """Delegate and auto-approve if confidence exceeds threshold.

        For low-risk tasks where mentor trusts the apprentice above
        a confidence threshold. Below threshold, leaves pending for
        manual review.
        """
        result = await self.delegate(task, context, tongue)

        if result.confidence >= min_confidence:
            await self.mentor_feedback(
                result.interaction_id,
                approved=True,
                quality_score=auto_quality,
            )

        return result

    # ------------------------------------------------------------------
    # Training data I/O
    # ------------------------------------------------------------------

    async def flush_training_data(self) -> int:
        """Write buffered SFT pairs to JSONL on disk.

        Returns:
            Number of pairs written.
        """
        if not self._sft_buffer:
            return 0

        count = len(self._sft_buffer)
        with open(self._session_file, "a", encoding="utf-8") as f:
            for pair in self._sft_buffer:
                f.write(json.dumps(pair, ensure_ascii=False) + "\n")

        self._sft_buffer.clear()
        return count

    async def push_to_huggingface(
        self,
        repo_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Push accumulated training data to HuggingFace Hub.

        Requires HF_TOKEN environment variable.

        Args:
            repo_id: Target dataset repo (defaults to model_id + "-training").

        Returns:
            Upload result metadata.
        """
        # Flush any remaining buffer
        await self.flush_training_data()

        if not self._session_file.exists():
            return {"status": "no_data", "pairs": 0}

        target_repo = repo_id or f"{self.model_id}-training"
        token = os.environ.get("HF_TOKEN", "")

        try:
            from huggingface_hub import HfApi

            api = HfApi(token=token)

            # Ensure repo exists
            try:
                api.create_repo(
                    repo_id=target_repo,
                    repo_type="dataset",
                    exist_ok=True,
                )
            except Exception:
                pass  # Repo may already exist

            # Upload the session file
            remote_path = f"apprentice_sessions/{self._session_file.name}"
            api.upload_file(
                path_or_fileobj=str(self._session_file),
                path_in_repo=remote_path,
                repo_id=target_repo,
                repo_type="dataset",
            )

            return {
                "status": "uploaded",
                "repo_id": target_repo,
                "remote_path": remote_path,
                "pairs": self._stats.total_sft_pairs,
                "session_id": self._stats.session_id,
            }

        except ImportError:
            return {
                "status": "error",
                "message": "huggingface_hub not installed. Run: pip install huggingface_hub",
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    # ------------------------------------------------------------------
    # Statistics and introspection
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return current session statistics."""
        return {
            "session_id": self._stats.session_id,
            "model_id": self.model_id,
            "mentor_type": self.mentor_type,
            "tongue": self.tongue,
            "total_delegations": self._stats.total_delegations,
            "approved": self._stats.approved_count,
            "corrected": self._stats.corrected_count,
            "rejected": self._stats.rejected_count,
            "pending_review": self._stats.pending_review,
            "avg_quality_score": round(self._stats.avg_quality_score, 3),
            "total_sft_pairs": self._stats.total_sft_pairs,
            "buffer_size": len(self._sft_buffer),
            "session_file": str(self._session_file),
        }

    def get_pending_reviews(self) -> List[ApprenticeInteraction]:
        """Get all interactions awaiting mentor review."""
        return [
            i for i in self._interactions.values()
            if i.approved is None
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _estimate_confidence(self, response: LLMResponse) -> float:
        """Heuristic confidence estimation from response characteristics.

        Real implementations would use calibrated confidence from the model.
        This approximates based on response length, token efficiency, and
        finish reason.
        """
        confidence = 0.5

        # Longer, more detailed responses suggest higher confidence
        word_count = len(response.text.split())
        if word_count > 50:
            confidence += 0.1
        if word_count > 150:
            confidence += 0.1

        # Proper finish (not truncated) is a good sign
        if response.finish_reason in ("stop", "end_turn"):
            confidence += 0.15
        elif response.finish_reason == "length":
            confidence -= 0.1  # Truncated = less confident

        # Token efficiency (output/input ratio)
        if response.input_tokens > 0:
            ratio = response.output_tokens / response.input_tokens
            if 0.3 < ratio < 3.0:
                confidence += 0.05  # Balanced ratio

        return max(0.0, min(1.0, confidence))


# ---------------------------------------------------------------------------
# Factory function for create_provider compatibility
# ---------------------------------------------------------------------------


def create_apprentice(
    model_id: str = "issdandavis/scbe-aethermoore-v1",
    mentor_type: str = "claude",
    tongue: Optional[str] = None,
    **kwargs,
) -> ApprenticeProvider:
    """Create an apprentice provider instance.

    This is the recommended entry point. Can be used alongside
    create_provider() from llm_providers.py.

    Args:
        model_id: HuggingFace model/endpoint ID.
        mentor_type: What AI is mentoring this apprentice.
        tongue: Sacred Tongue specialization.
        **kwargs: Passed to ApprenticeProvider constructor.

    Returns:
        Configured ApprenticeProvider instance.
    """
    return ApprenticeProvider(
        model_id=model_id,
        mentor_type=mentor_type,
        tongue=tongue,
        **kwargs,
    )
