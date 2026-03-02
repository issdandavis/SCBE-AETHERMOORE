"""
BaaS Training Tap — SFT Pair Flywheel
=======================================
Records every browser action as an SFT training pair.
Buffers pairs in-memory per session, flushes to ResearchFunnel
which pushes to local JSONL and HuggingFace.

Every API call through the BaaS = one more training example
for the baby AI to learn screen navigation.

Used by: src/api/browser_saas.py
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("baas-training-tap")

# Output path for local JSONL
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TRAINING_DIR = PROJECT_ROOT / "training-data" / "baas"
TRAINING_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
#  SFT Pair
# ---------------------------------------------------------------------------

@dataclass
class SFTPair:
    """One supervised fine-tuning training pair from a browser action."""

    instruction: str
    input_context: Dict[str, Any]
    output_response: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    quality_score: float = 1.0

    def to_jsonl(self) -> str:
        return json.dumps({
            "instruction": self.instruction,
            "input": self.input_context,
            "output": self.output_response,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
            "quality_score": self.quality_score,
        }, ensure_ascii=False)

    def to_chat_format(self) -> Dict[str, Any]:
        """Convert to chat-style SFT format for fine-tuning."""
        return {
            "messages": [
                {"role": "user", "content": self.instruction},
                {"role": "assistant", "content": json.dumps(self.output_response)},
            ],
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
#  Training Tap
# ---------------------------------------------------------------------------

class TrainingTap:
    """Records browser actions as SFT pairs, flushes to disk and HuggingFace."""

    def __init__(self):
        self._total_generated = 0
        self._total_flushed = 0
        self._local_file = TRAINING_DIR / "baas_sft_pairs.jsonl"

    # -- Recording methods ---------------------------------------------------

    def record_navigate(
        self,
        session_id: str,
        url: str,
        result: Dict[str, Any],
        governance: Dict[str, Any],
    ) -> SFTPair:
        """Record a navigation action."""
        pair = SFTPair(
            instruction=f"Navigate the browser to {url}",
            input_context={"action": "navigate", "url": url},
            output_response={
                "action": "navigate",
                "url": result.get("url", url),
                "title": result.get("title", ""),
                "success": True,
            },
            metadata={
                "session_id": session_id,
                "action_type": "navigate",
                "governance_decision": governance.get("decision", "ALLOW"),
                "tongue": governance.get("tongue", "KO"),
                "risk_score": governance.get("risk_score", 0.0),
            },
        )
        self._total_generated += 1
        return pair

    def record_click(
        self,
        session_id: str,
        selector: str,
        result: Dict[str, Any],
        governance: Dict[str, Any],
        perception_before: Optional[Dict[str, Any]] = None,
    ) -> SFTPair:
        """Record a click action."""
        pair = SFTPair(
            instruction=f"Click the element matching '{selector}' on the current page",
            input_context={
                "action": "click",
                "selector": selector,
                "page_url": result.get("url", ""),
                "interactive_elements": (perception_before or {}).get("interactive_elements", [])[:10],
            },
            output_response={
                "action": "click",
                "selector": selector,
                "success": True,
                "resulting_url": result.get("url", ""),
            },
            metadata={
                "session_id": session_id,
                "action_type": "click",
                "governance_decision": governance.get("decision", "ALLOW"),
                "tongue": governance.get("tongue", "CA"),
            },
        )
        self._total_generated += 1
        return pair

    def record_type(
        self,
        session_id: str,
        selector: str,
        value: str,
        result: Dict[str, Any],
        governance: Dict[str, Any],
    ) -> SFTPair:
        """Record a type/fill action."""
        # Redact potential sensitive input (passwords, tokens)
        safe_value = value if len(value) < 100 and not any(
            w in selector.lower() for w in ["password", "token", "secret", "key"]
        ) else "[REDACTED]"

        pair = SFTPair(
            instruction=f"Type '{safe_value}' into the element '{selector}'",
            input_context={
                "action": "type",
                "selector": selector,
                "value": safe_value,
            },
            output_response={
                "action": "fill",
                "selector": selector,
                "success": True,
            },
            metadata={
                "session_id": session_id,
                "action_type": "type",
                "governance_decision": governance.get("decision", "ALLOW"),
                "tongue": governance.get("tongue", "CA"),
            },
        )
        self._total_generated += 1
        return pair

    def record_execute(
        self,
        session_id: str,
        goal: str,
        plan: Dict[str, Any],
        success: bool,
        governance: Dict[str, Any],
        perception: Optional[Dict[str, Any]] = None,
    ) -> SFTPair:
        """Record a natural-language execution (the most valuable training data)."""
        pair = SFTPair(
            instruction=goal,
            input_context={
                "action": "execute",
                "goal": goal,
                "page_url": (perception or {}).get("url", ""),
                "page_type": (perception or {}).get("page_type", ""),
                "interactive_elements": (perception or {}).get("interactive_elements", [])[:15],
                "forms": (perception or {}).get("forms", [])[:5],
            },
            output_response={
                "plan": plan,
                "success": success,
            },
            metadata={
                "session_id": session_id,
                "action_type": "execute",
                "governance_decision": governance.get("decision", "ALLOW"),
                "tongue": governance.get("tongue", "KO"),
                "risk_score": governance.get("risk_score", 0.0),
            },
            quality_score=0.9 if success else 0.3,
        )
        self._total_generated += 1
        return pair

    def record_search(
        self,
        query: str,
        results: List[Dict[str, Any]],
        governance: Dict[str, Any],
    ) -> SFTPair:
        """Record a web search action."""
        pair = SFTPair(
            instruction=f"Search the web for: {query}",
            input_context={"action": "search", "query": query},
            output_response={
                "action": "search",
                "results": results[:5],
                "result_count": len(results),
            },
            metadata={
                "action_type": "search",
                "governance_decision": governance.get("decision", "ALLOW"),
                "tongue": governance.get("tongue", "KO"),
            },
        )
        self._total_generated += 1
        return pair

    def record_compute(
        self,
        session_id: str,
        request: Dict[str, Any],
        result: Dict[str, Any],
        governance: Dict[str, Any],
    ) -> SFTPair:
        """Record compute jobs (e.g., Colab/remote model runs)."""
        pair = SFTPair(
            instruction=f"Run compute job: {request.get('purpose') or request.get('action', 'compute')}",
            input_context={
                "action": "compute",
                "provider": request.get("provider", "colab"),
                "purpose": request.get("purpose", ""),
                "payload": request.get("payload", {}),
            },
            output_response={
                "action": "compute",
                "provider": request.get("provider", "colab"),
                "result": result,
                "success": bool(result.get("success", True)),
            },
            metadata={
                "session_id": session_id,
                "action_type": "compute",
                "governance_decision": governance.get("decision", "ALLOW"),
                "tongue": governance.get("tongue", "KO"),
                "risk_score": governance.get("risk_score", 0.0),
            },
            quality_score=0.7,
        )
        self._total_generated += 1
        return pair

    # -- Flush to disk -------------------------------------------------------

    def flush_pairs(self, pairs: List[SFTPair]) -> int:
        """Write pairs to local JSONL file. Returns count written."""
        if not pairs:
            return 0

        with open(self._local_file, "a", encoding="utf-8") as f:
            for pair in pairs:
                f.write(pair.to_jsonl() + "\n")

        count = len(pairs)
        self._total_flushed += count
        logger.info("Flushed %d SFT pairs to %s (total: %d)", count, self._local_file, self._total_flushed)
        return count

    def flush_session(self, training_buffer: List[Any]) -> int:
        """Flush a session's training buffer (SFTPair or serialized record)."""
        if not training_buffer:
            return 0

        with open(self._local_file, "a", encoding="utf-8") as f:
            for entry in training_buffer:
                if isinstance(entry, SFTPair):
                    f.write(entry.to_jsonl() + "\n")
                    continue

                if isinstance(entry, str):
                    # If already serialized, sanitize and persist directly.
                    f.write(entry + "\n")
                    continue

                if isinstance(entry, dict):
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                else:
                    f.write(json.dumps({"raw": str(entry)}, ensure_ascii=False) + "\n")

        count = len(training_buffer)
        self._total_flushed += count
        logger.info("Flushed %d session pairs to %s", count, self._local_file)
        return count

    # -- Stats ---------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        file_size = self._local_file.stat().st_size if self._local_file.exists() else 0
        file_lines = 0
        if self._local_file.exists():
            with open(self._local_file, "r", encoding="utf-8") as f:
                file_lines = sum(1 for _ in f)

        return {
            "pairs_generated_this_session": self._total_generated,
            "pairs_flushed_to_disk": self._total_flushed,
            "local_file": str(self._local_file),
            "local_file_size_bytes": file_size,
            "local_file_pairs": file_lines,
        }
