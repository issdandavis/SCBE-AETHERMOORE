from __future__ import annotations

from dataclasses import dataclass
from typing import AsyncIterator

HYDRA_SYSTEM_PROMPT = (
    "You are a HYDRA agent operating under SCBE governance. "
    "Plan actions clearly. Respond with structured JSON when asked for action plans."
)
DEFAULT_LOCAL_BASE_URL = "http://localhost:1234/v1"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    finish_reason: str = "stop"


class UnavailableProvider:
    def __init__(self, name: str, model: str | None = None) -> None:
        self.name = name
        self.model = model or name

    async def complete(self, prompt: str, **_: object) -> LLMResponse:
        raise RuntimeError(f"HYDRA provider '{self.name}' is not available in compatibility mode")

    async def stream(self, prompt: str, **_: object) -> AsyncIterator[str]:
        raise RuntimeError(f"HYDRA provider '{self.name}' is not available in compatibility mode")
        yield ""


def create_provider(name: str, **kwargs: object) -> UnavailableProvider:
    model = kwargs.get("model")
    return UnavailableProvider(str(name), str(model) if model is not None else None)
