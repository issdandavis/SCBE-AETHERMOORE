"""DeBERTa prompt-injection guard -- loads ProtectAI's model from HuggingFace.

Model: protectai/deberta-v3-base-prompt-injection-v2

This is a real ML-based guard that classifies prompts as injection/benign.
Falls back gracefully if transformers or torch are not installed.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from benchmarks.scbe.config import DEBERTA_MODEL_NAME, DEBERTA_THRESHOLD

logger = logging.getLogger(__name__)


class DeBERTaGuard:
    """ProtectAI DeBERTa-v3 prompt injection classifier.

    Wraps the HuggingFace transformers pipeline for text-classification.
    If the model cannot be loaded, all calls return (False, [], metadata)
    with a warning in metadata.
    """

    name = "deberta_guard"
    description = "ProtectAI DeBERTa-v3 prompt-injection classifier"

    def __init__(
        self,
        model_name: str = DEBERTA_MODEL_NAME,
        threshold: float = DEBERTA_THRESHOLD,
    ):
        self.model_name = model_name
        self.threshold = threshold
        self._pipeline: Optional[Any] = None
        self._available = False
        self._load_error: Optional[str] = None
        self._try_load()

    def _try_load(self) -> None:
        """Attempt to load the transformers pipeline."""
        try:
            from transformers import pipeline as hf_pipeline  # type: ignore[import-untyped]

            self._pipeline = hf_pipeline(
                "text-classification",
                model=self.model_name,
                truncation=True,
                max_length=512,
            )
            self._available = True
            logger.info("DeBERTa guard loaded: %s", self.model_name)
        except ImportError:
            self._load_error = (
                "transformers library not installed. "
                "Install with: pip install transformers torch"
            )
            logger.warning("DeBERTa guard unavailable: %s", self._load_error)
        except Exception as exc:
            self._load_error = f"Failed to load model: {exc}"
            logger.warning("DeBERTa guard unavailable: %s", self._load_error)

    @property
    def available(self) -> bool:
        return self._available

    def calibrate(self, clean_texts: List[str]) -> None:
        """No calibration needed -- model is pre-trained."""
        pass

    def detect(self, prompt: str) -> Tuple[bool, List[str], Dict[str, Any]]:
        """Classify a prompt as injection or benign.

        Returns:
            (detected, signals, metadata)
        """
        if not self._available or self._pipeline is None:
            return False, [], {
                "system": self.name,
                "verdict": "UNAVAILABLE",
                "error": self._load_error,
            }

        try:
            result = self._pipeline(prompt[:512])
            if not result:
                return False, [], {"system": self.name, "verdict": "NO_RESULT"}

            # The model returns [{"label": "INJECTION"/"SAFE", "score": float}]
            top = result[0]
            label = top.get("label", "").upper()
            score = top.get("score", 0.0)

            # "INJECTION" label with score above threshold = detected
            detected = label == "INJECTION" and score >= self.threshold
            signals = []
            if detected:
                signals.append(f"deberta_injection(score={score:.4f})")

            return detected, signals, {
                "system": self.name,
                "label": label,
                "score": round(score, 4),
                "threshold": self.threshold,
                "verdict": "DENY" if detected else "ALLOW",
            }
        except Exception as exc:
            logger.error("DeBERTa inference error: %s", exc)
            return False, [], {
                "system": self.name,
                "verdict": "ERROR",
                "error": str(exc),
            }

    def detect_batch(
        self, prompts: List[str]
    ) -> List[Tuple[bool, List[str], Dict[str, Any]]]:
        """Batch detection using the pipeline.

        Falls back to sequential if batch inference fails.
        """
        if not self._available or self._pipeline is None:
            return [self.detect(p) for p in prompts]

        try:
            truncated = [p[:512] for p in prompts]
            results = self._pipeline(truncated, batch_size=32)
            outputs = []
            for prompt_text, result in zip(prompts, results):
                top = result if isinstance(result, dict) else result[0]
                label = top.get("label", "").upper()
                score = top.get("score", 0.0)
                detected = label == "INJECTION" and score >= self.threshold
                signals = []
                if detected:
                    signals.append(f"deberta_injection(score={score:.4f})")
                outputs.append((
                    detected,
                    signals,
                    {
                        "system": self.name,
                        "label": label,
                        "score": round(score, 4),
                        "threshold": self.threshold,
                        "verdict": "DENY" if detected else "ALLOW",
                    },
                ))
            return outputs
        except Exception:
            # Fall back to sequential
            return [self.detect(p) for p in prompts]
