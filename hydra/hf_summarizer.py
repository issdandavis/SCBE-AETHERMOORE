"""Optional Hugging Face summarizer for page compression."""

from __future__ import annotations

import asyncio
from typing import Any, Optional


class HFSummarizer:
    """Lazy-loading text summarizer backed by transformers pipeline."""

    def __init__(
        self,
        model_name: str = "facebook/bart-large-cnn",
        *,
        max_input_chars: int = 12000,
        min_length: int = 60,
        max_length: int = 220,
    ):
        self.model_name = model_name
        self.max_input_chars = max_input_chars
        self.min_length = min_length
        self.max_length = max_length
        self._pipeline: Optional[Any] = None

    def _ensure_pipeline(self) -> Any:
        if self._pipeline is not None:
            return self._pipeline

        try:
            from transformers import pipeline  # type: ignore
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(
                "transformers is required for HFSummarizer. "
                "Install with: pip install transformers torch"
            ) from exc

        self._pipeline = pipeline("summarization", model=self.model_name)
        return self._pipeline

    def summarize(self, text: str) -> str:
        """Summarize text synchronously."""
        normalized = " ".join((text or "").split())
        if not normalized:
            return ""

        payload = normalized[: self.max_input_chars]
        model = self._ensure_pipeline()
        result = model(
            payload,
            min_length=self.min_length,
            max_length=self.max_length,
            do_sample=False,
        )
        if isinstance(result, list) and result:
            first = result[0]
            if isinstance(first, dict):
                return str(first.get("summary_text") or payload)
        return payload

    async def summarize_async(self, text: str) -> str:
        """Summarize text in a worker thread."""
        return await asyncio.to_thread(self.summarize, text)
