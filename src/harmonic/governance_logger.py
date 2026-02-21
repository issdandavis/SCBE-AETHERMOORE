"""
Layer 13 governance audit logging decorator.
"""

import logging
from functools import wraps
from typing import Callable, Any

# Configure basic logging for governance audit trail
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('SCBE_GOVERNANCE_AUDIT')


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
        message = kwargs.get('message', args[1] if len(args) > 1 else 'N/A')
        agent_id = kwargs.get('agent_id', args[2] if len(args) > 2 else 'N/A')

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
