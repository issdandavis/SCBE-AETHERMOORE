"""AetherIDE Session -- Central IDE orchestrator.

Every IDE action flows through:
  1. GovernedEditor validates mode/zone constraints
  2. TernaryHybridEncoder runs the 7-module pipeline
  3. Decision gates the action (ALLOW/QUARANTINE/DENY)
  4. Event is logged for training data
  5. SelfImproveLoop monitors coherence

@layer Layer 1-14
@component AetherIDE.Session
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from src.aether_ide.types import (
    IDEAction,
    IDEEvent,
    IDEConfig,
    SessionState,
)
from src.aether_ide.editor import GovernedEditor
from src.aether_ide.chat import IDEChat
from src.aether_ide.spin_engine import SpinEngine
from src.aether_ide.code_search import GovernedCodeSearch
from src.aether_ide.workflow import WorkflowTrigger
from src.aether_ide.self_improve import SelfImproveLoop
from src.hybrid_encoder import TernaryHybridEncoder, EncoderInput, EncoderResult


class AetherIDESession:
    """Manages a complete IDE session with governance.

    Lifecycle:
      session = AetherIDESession(config)
      decision, result = session.execute(IDEAction(...))
      state = session.get_state()
      session.close()
    """

    def __init__(self, config: Optional[IDEConfig] = None):
        self.config = config or IDEConfig()
        self.session_id = f"aide-{uuid.uuid4().hex[:8]}"
        self._encoder = TernaryHybridEncoder(
            chemistry_threat_level=self.config.chemistry_threat_level,
        )
        self._editor = GovernedEditor(
            mode=self.config.initial_mode,
            zone=self.config.initial_zone,
        )
        self._chat = IDEChat()
        self._spin = SpinEngine()
        self._search = GovernedCodeSearch()
        self._workflow = WorkflowTrigger(bridge_url=self.config.n8n_bridge_url)
        self._improve = SelfImproveLoop(
            coherence_threshold=self.config.coherence_threshold,
        )
        self._events: List[IDEEvent] = []

    def execute(self, action: IDEAction) -> Tuple[str, EncoderResult]:
        """Execute a governed IDE action.

        Returns (decision, encoder_result).
        """
        # Convert action to encoder input
        enc_input = self._action_to_encoder_input(action)

        # Run 7-module pipeline
        result = self._encoder.encode(enc_input)
        decision = result.decision

        # Log event
        event = IDEEvent(
            action=action,
            decision=decision,
            encoder_result=result,
            timestamp=time.time(),
            session_id=self.session_id,
        )
        self._events.append(event)

        # Self-improvement check
        if self.config.auto_improve:
            self._improve.observe(event)

        # Log chat if chat action
        if action.kind == "chat":
            self._chat.send(
                content=action.content,
                tongue=action.tongue_hint or "KO",
                role="user",
            )

        return decision, result

    def _action_to_encoder_input(self, action: IDEAction) -> EncoderInput:
        """Convert an IDE action to an EncoderInput."""
        if action.kind in ("edit", "save", "refactor", "review") and action.content:
            return EncoderInput(
                code_text=action.content,
                tongue_hint=action.tongue_hint,
                context={"action_kind": action.kind, "file_path": action.file_path},
            )
        elif action.kind in ("search", "chat"):
            return EncoderInput(
                raw_signal=len(action.content) / 100.0,
                tongue_hint=action.tongue_hint or "KO",
                context={"action_kind": action.kind},
            )
        else:
            return EncoderInput(
                raw_signal=0.5,
                tongue_hint=action.tongue_hint,
                context={"action_kind": action.kind},
            )

    def switch_mode(self, mode: str) -> bool:
        """Switch the editor pad mode. Returns True on success."""
        try:
            self._editor.switch_mode(mode)
            return True
        except (KeyError, ValueError):
            return False

    def promote_zone(self) -> bool:
        """Try to promote from HOT to SAFE zone."""
        coherence = self._improve.current_coherence
        return self._editor.try_promote(
            d_star=0.1,
            coherence=coherence,
            h_eff=1.0 - coherence,
        )

    def demote_zone(self) -> None:
        """Demote from SAFE to HOT zone."""
        self._editor.demote()

    def get_state(self) -> SessionState:
        """Return current session state snapshot."""
        deny_count = sum(1 for e in self._events if e.decision == "DENY")
        quarantine_count = sum(1 for e in self._events if e.decision == "QUARANTINE")
        allow_count = sum(1 for e in self._events if e.decision == "ALLOW")

        return SessionState(
            session_id=self.session_id,
            mode=self._editor.mode,
            zone=self._editor.zone,
            coherence=self._improve.current_coherence,
            encode_count=self._encoder.encode_count,
            event_count=len(self._events),
            deny_count=deny_count,
            quarantine_count=quarantine_count,
            allow_count=allow_count,
            active_spins=self._spin.spin_count,
            improvement_tasks_pending=len(self._improve.pending_tasks),
        )

    def export_training_data(self) -> List[Dict[str, Any]]:
        """Export all events as SFT training pairs.

        Each event becomes:
          instruction: the action content
          output: the governance decision + rationale
          metadata: encoder diagnostics
        """
        pairs: List[Dict[str, Any]] = []
        for event in self._events:
            instruction = f"[{event.action.kind}] {event.action.content[:200]}"
            output = f"Decision: {event.decision}"
            if hasattr(event.encoder_result, "governance_summary"):
                output += f" | {event.encoder_result.governance_summary}"

            pairs.append({
                "instruction": instruction,
                "output": output,
                "metadata": {
                    "session_id": event.session_id,
                    "timestamp": event.timestamp,
                    "tongue_trits": getattr(event.encoder_result, "tongue_trits", []),
                    "threat_score": getattr(event.encoder_result, "threat_score", 0.0),
                },
            })
        return pairs

    def close(self) -> None:
        """Close the session."""
        pass

    # Convenience accessors
    @property
    def editor(self) -> GovernedEditor:
        return self._editor

    @property
    def chat(self) -> IDEChat:
        return self._chat

    @property
    def spin(self) -> SpinEngine:
        return self._spin

    @property
    def search(self) -> GovernedCodeSearch:
        return self._search

    @property
    def workflow(self) -> WorkflowTrigger:
        return self._workflow

    @property
    def improve(self) -> SelfImproveLoop:
        return self._improve
