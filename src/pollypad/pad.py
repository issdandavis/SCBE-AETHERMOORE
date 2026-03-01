"""
PollyPad — The Interface Skin
================================

The PollyPad is where users interact with Polly.
Every interaction:
1. Gets a 6D address
2. Passes through SCBE governance (the mantle)
3. Gets stored in persistent memory
4. Generates a training pair (SFT or DPO)
5. Returns a response

Training data generation is a BYPRODUCT of natural conversation.
Not a separate pipeline. Not a special mode. Every message = data.

The pad doesn't filter content by word — it understands intent through
the 14-layer stack. "pussy" in a veterinary context vs. a sexual context
vs. a profanity context are different points in the 6D space. The
governance decision comes from hyperbolic distance, not regex.

@patent USPTO #63/961,403
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .memory import PersistentMemory, MemoryCell, MemoryQuery, SixDAddress


# ---------------------------------------------------------------------------
#  Training Pair Generation
# ---------------------------------------------------------------------------

@dataclass
class TrainingPair:
    """
    SFT or DPO training pair generated from natural interaction.

    SFT: {"prompt": ..., "completion": ...}
    DPO: {"prompt": ..., "chosen": ..., "rejected": ...}

    Every conversation turn generates at least one SFT pair.
    DPO pairs are generated when governance intervenes (the rejected
    response is what would have happened without governance).
    """
    pair_type: str           # "sft" or "dpo"
    prompt: str
    completion: str          # For SFT: the response. For DPO: the chosen response.
    rejected: Optional[str] = None  # For DPO only
    tongue: str = "KO"
    context: str = "conversation"
    governance_decision: str = "ALLOW"
    risk_score: float = 0.0
    timestamp: float = field(default_factory=time.time)
    pair_id: str = ""

    def __post_init__(self):
        if not self.pair_id:
            raw = f"{self.prompt[:30]}:{self.timestamp}"
            self.pair_id = hashlib.sha256(raw.encode()).hexdigest()[:12]

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "pair_id": self.pair_id,
            "type": self.pair_type,
            "prompt": self.prompt,
            "completion": self.completion,
            "tongue": self.tongue,
            "context": self.context,
            "governance": self.governance_decision,
            "risk_score": self.risk_score,
            "timestamp": self.timestamp,
        }
        if self.rejected:
            d["rejected"] = self.rejected
        return d

    def to_jsonl(self) -> str:
        return json.dumps(self.to_dict())


# ---------------------------------------------------------------------------
#  Interaction Record
# ---------------------------------------------------------------------------

@dataclass
class Interaction:
    """One complete interaction: user message + response + metadata."""
    user_text: str
    response_text: str
    address: SixDAddress
    governance_decision: str = "ALLOW"
    risk_score: float = 0.0
    training_pair: Optional[TrainingPair] = None
    timestamp: float = field(default_factory=time.time)
    session_id: str = ""
    interaction_id: str = ""

    def __post_init__(self):
        if not self.interaction_id:
            raw = f"{self.user_text[:30]}:{self.timestamp}"
            self.interaction_id = hashlib.sha256(raw.encode()).hexdigest()[:12]

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "interaction_id": self.interaction_id,
            "session_id": self.session_id,
            "user_text": self.user_text,
            "response_text": self.response_text,
            "address": self.address.to_dict(),
            "governance": self.governance_decision,
            "risk_score": self.risk_score,
            "timestamp": self.timestamp,
        }
        if self.training_pair:
            d["training_pair"] = self.training_pair.to_dict()
        return d


# ---------------------------------------------------------------------------
#  PollyPad — The App Shell
# ---------------------------------------------------------------------------

class PollyPad:
    """
    The PollyPad — Polly's interface to the world.

    This is the skin of the octopus. Users touch it.
    Under the skin: governance, memory, training generation.

    Every interaction:
    1. User sends text
    2. Text gets a 6D address (2 coords known by design)
    3. Governance scan (14-layer SCBE pipeline)
    4. Response generated (or governance intervention)
    5. Both stored in persistent memory
    6. Training pair emitted
    7. Response returned to user

    The pad doesn't block words. It understands intent.
    Governance is about WHERE you are in the manifold,
    not WHAT words you used.
    """

    def __init__(
        self,
        data_dir: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        base_dir = data_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "artifacts", "pollypad"
        )

        self.memory = PersistentMemory(
            data_dir=os.path.join(base_dir, "memory")
        )
        self.training_dir = os.path.join(base_dir, "training")
        self.session_id = session_id or hashlib.sha256(
            str(time.time()).encode()
        ).hexdigest()[:12]

        self._interactions: List[Interaction] = []
        self._training_pairs: List[TrainingPair] = []
        self._response_handler: Optional[Any] = None

        # Load previous memories
        self.memory.load()

    # -------------------------------------------------------------------
    #  Core Interaction Loop
    # -------------------------------------------------------------------

    def interact(
        self,
        user_text: str,
        context: str = "conversation",
        intent: str = "tell",
        response_text: Optional[str] = None,
    ) -> Interaction:
        """
        Process one interaction. This is the main entry point.

        If response_text is provided, it's used directly (for recording
        external AI responses). If not, a simple echo is used
        (real AI response generation plugs in via set_responder).
        """
        # 1. Build 6D address
        address = SixDAddress.from_interaction(user_text, context, intent)

        # 2. Governance scan (lightweight inline version)
        governance = self._governance_scan(user_text, address)

        # 3. Generate response
        if response_text is None:
            if self._response_handler:
                response_text = self._response_handler(user_text, address, governance)
            else:
                response_text = f"[Polly heard: {user_text[:100]}]"

        # 4. Store in memory
        self.memory.remember_text(
            user_text, role="user", context=context,
            intent=intent, importance=0.5,
        )
        self.memory.remember_text(
            response_text, role="assistant", context=context,
            intent="tell", importance=0.5,
        )

        # 5. Generate training pair
        pair = self._generate_training_pair(
            user_text, response_text, address, governance
        )

        # 6. Build interaction record
        interaction = Interaction(
            user_text=user_text,
            response_text=response_text,
            address=address,
            governance_decision=governance["decision"],
            risk_score=governance["risk_score"],
            training_pair=pair,
            session_id=self.session_id,
        )
        self._interactions.append(interaction)

        return interaction

    def set_responder(self, handler) -> None:
        """
        Plug in a response generator.
        handler(user_text, address, governance) -> response_text
        """
        self._response_handler = handler

    # -------------------------------------------------------------------
    #  Governance (Lightweight Inline)
    # -------------------------------------------------------------------

    def _governance_scan(self, text: str, address: SixDAddress) -> Dict[str, Any]:
        """
        Lightweight governance scan. Not word-blocking — intent evaluation.

        Uses the 6D address to determine risk. Words don't matter.
        Position in the manifold matters.
        """
        # Try to import the full governance engine
        try:
            import sys
            src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if src_dir not in sys.path:
                sys.path.insert(0, src_dir)
            from api.governance_saas import evaluate_text
            result = evaluate_text(text)
            return {
                "decision": result["decision"],
                "risk_score": result["risk_score"],
                "tongue": result["tongue"],
                "harmonic_wall": result["harmonic_wall"],
            }
        except (ImportError, Exception):
            # Fallback: basic intent-based governance
            return self._fallback_governance(text, address)

    def _fallback_governance(self, text: str, address: SixDAddress) -> Dict[str, Any]:
        """Simple fallback when full SCBE engine isn't available."""
        # Not word-based. Position-based.
        # High-weight tongues (DR, UM) in governance context = higher scrutiny
        weight_factor = address.weight / max(v for v in TONGUE_WEIGHTS.values())
        context_risk = 0.3 if address.context == "governance" else 0.1

        risk = min(1.0, weight_factor * 0.3 + context_risk)
        decision = "ALLOW" if risk < 0.5 else "QUARANTINE"

        return {
            "decision": decision,
            "risk_score": risk,
            "tongue": address.tongue,
            "harmonic_wall": 1.0,
        }

    # -------------------------------------------------------------------
    #  Training Pair Generation
    # -------------------------------------------------------------------

    def _generate_training_pair(
        self, prompt: str, completion: str,
        address: SixDAddress, governance: Dict[str, Any],
    ) -> TrainingPair:
        """
        Every interaction = one training pair. Always.
        SFT by default. DPO if governance intervened.
        """
        decision = governance["decision"]

        if decision == "ALLOW":
            pair = TrainingPair(
                pair_type="sft",
                prompt=prompt,
                completion=completion,
                tongue=address.tongue,
                context=address.context,
                governance_decision=decision,
                risk_score=governance["risk_score"],
            )
        else:
            # DPO pair: the governed response is "chosen",
            # an ungoverned response would be "rejected"
            pair = TrainingPair(
                pair_type="dpo",
                prompt=prompt,
                completion=completion,  # The safe/governed response
                rejected=f"[UNGOVERNED: {prompt}]",  # What would have happened
                tongue=address.tongue,
                context=address.context,
                governance_decision=decision,
                risk_score=governance["risk_score"],
            )

        self._training_pairs.append(pair)
        return pair

    # -------------------------------------------------------------------
    #  Memory Recall
    # -------------------------------------------------------------------

    def recall(self, query_text: str, context: Optional[str] = None) -> List[MemoryCell]:
        """Recall relevant memories for a query."""
        address = SixDAddress.from_interaction(query_text, context or "conversation")
        nearest = self.memory.recall_nearest(address, k=10)
        return [cell for _, cell in nearest]

    def conversation_history(self, n: int = 20) -> List[Dict[str, str]]:
        """Get recent conversation as a list of {role, content} dicts."""
        window = self.memory.conversation_window(n)
        return [{"role": c.role, "content": c.content} for c in window]

    # -------------------------------------------------------------------
    #  Export / Persistence
    # -------------------------------------------------------------------

    def save(self) -> Dict[str, str]:
        """Save everything: memory + training pairs."""
        memory_path = self.memory.save()

        # Save training pairs
        os.makedirs(self.training_dir, exist_ok=True)
        training_path = os.path.join(
            self.training_dir, f"session_{self.session_id}.jsonl"
        )
        with open(training_path, "w") as f:
            for pair in self._training_pairs:
                f.write(pair.to_jsonl() + "\n")

        return {
            "memory": memory_path,
            "training": training_path,
            "memories_saved": len(self.memory.cells),
            "pairs_saved": len(self._training_pairs),
        }

    def export_training_data(self, format: str = "jsonl") -> List[Dict[str, Any]]:
        """Export all training pairs for HuggingFace upload."""
        return [p.to_dict() for p in self._training_pairs]

    # -------------------------------------------------------------------
    #  Stats
    # -------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "interactions": len(self._interactions),
            "training_pairs": len(self._training_pairs),
            "sft_pairs": sum(1 for p in self._training_pairs if p.pair_type == "sft"),
            "dpo_pairs": sum(1 for p in self._training_pairs if p.pair_type == "dpo"),
            "memory": self.memory.stats(),
        }


# Import TONGUE_WEIGHTS from memory module for fallback governance
from .memory import TONGUE_WEIGHTS
