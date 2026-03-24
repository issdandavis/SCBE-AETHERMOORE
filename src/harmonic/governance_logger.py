"""
Layer 13 governance audit logging decorator.
"""

import json
import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Iterable, Optional

# Configure basic logging for governance audit trail
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("SCBE_GOVERNANCE_AUDIT")


def _to_float_list(vector: Iterable[float]) -> list[float]:
    return [float(v) for v in vector]


def audit_state_transition(
    state_vector: Iterable[float],
    *,
    decision: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    strict: bool = False,
) -> Dict[str, Any]:
    """Emit canonical 21D state transition telemetry.

    This is the runtime Layer 13 callsite function used by governance pipelines.
    It validates shape and logs one structured JSON event.
    """
    vec = _to_float_list(state_vector)
    if len(vec) != 21:
        raise ValueError(f"Expected 21D state vector, got {len(vec)} values")

    validation: Dict[str, Any] = {}
    try:
        # Local import prevents hard dependency at module import time.
        from src.harmonic.state21_product_metric import parse_state21_v1, validate_state21_v1

        validation = validate_state21_v1(parse_state21_v1(vec))
    except Exception as exc:  # pragma: no cover - defensive fallback
        validation = {"validation_error": str(exc)}
        if strict:
            raise

    event = {
        "event": "state_transition",
        "schema": "state21_v1",
        "timestamp_unix": time.time(),
        "decision": decision or "UNKNOWN",
        "state_vector": vec,
        "validation": validation,
        "metadata": metadata or {},
    }
    logger.info("Governance State Transition: %s", json.dumps(event, sort_keys=True))
    return event


def audit_governance_decision(func: Callable) -> Callable:
    """
    Decorator for Layer 13 Auditability. Logs the inputs and outputs of a governance
    decision function. Ensures that every critical decision point has an audit trail.
    """

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        # 1. Capture function execution details
        func_name = func.__name__

        # 2. Extract key input parameters from kwargs or args
        message = kwargs.get("message", args[1] if len(args) > 1 else "N/A")
        agent_id = kwargs.get("agent_id", args[2] if len(args) > 2 else "N/A")

        # 3. Execute the function and capture the output
        try:
            result = func(*args, **kwargs)
            decision = result.get("decision", "UNKNOWN") if isinstance(result, dict) else str(result)
            deviation = result.get("hamiltonian_deviation", 0.0) if isinstance(result, dict) else 0.0

            # 4. Log the audit event (Layer 13 PQC Auditability)
            logger.info(
                f"Governance Decision Audit: Function={func_name}, Agent={agent_id}, Message='{message[:40]}...', "
                f"Result_Decision='{decision}', Hamiltonian_Deviation={deviation:.8f}"
            )
            return result
        except Exception as e:
            logger.error(f"Governance function '{func_name}' failed for Agent={agent_id}: {e}")
            raise

    return wrapper


# Example:
# @audit_governance_decision
# def route_conversation(self, message: str, agent_id: str) -> Dict:
#    ...
