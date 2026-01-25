"""
SCBE Self-Healing Orchestrator
==============================
Production-grade self-healing workflow for SCBE cryptographic operations.

Last Updated: January 18, 2026
Version: 1.0.0

Features:
- Circuit breaker pattern with configurable thresholds
- Exponential backoff retry with jitter
- Health monitoring and metrics
- Audit logging for compliance
- Adaptive recovery strategies
- Multi-level healing (quick fix -> deep healing)

Compliance: NIST 800-53 SI-13 (Predictable Failure Prevention)
"""

import time
import threading
import random
import json
from typing import Callable, Any, Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import hashlib


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Blocking all requests
    HALF_OPEN = "half_open"  # Testing recovery


class HealingStrategy(Enum):
    """Available healing strategies."""
    RETRY = "retry"
    FALLBACK = "fallback"
    CIRCUIT_BREAK = "circuit_break"
    ESCALATE = "escalate"
    QUARANTINE = "quarantine"


@dataclass
class HealingEvent:
    """Record of a healing event for audit trail."""
    timestamp: float
    operation_id: str
    strategy: HealingStrategy
    success: bool
    details: Dict[str, Any]
    duration_ms: float


@dataclass
class HealthMetrics:
    """System health metrics."""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    healed_operations: int = 0
    circuit_breaks: int = 0
    avg_latency_ms: float = 0.0
    error_rate: float = 0.0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None


class SelfHealingOrchestrator:
    """
    Production-grade self-healing orchestrator for SCBE operations.
    
    Implements:
    - Circuit breaker pattern (NIST 800-53 SI-13)
    - Exponential backoff with jitter
    - Multi-level healing strategies
    - Comprehensive audit logging
    - Real-time health monitoring
    """
    
    def __init__(
        self,
        max_retries: int = 3,
        circuit_threshold: int = 5,
        circuit_timeout: float = 30.0,
        base_delay: float = 0.01,
        max_delay: float = 1.0,
        jitter_factor: float = 0.1,
    ):
        """
        Initialize the self-healing orchestrator.
        
        Args:
            max_retries: Maximum retry attempts before failure
            circuit_threshold: Failures before circuit opens
            circuit_timeout: Seconds before circuit half-opens
            base_delay: Base delay for exponential backoff (seconds)
            max_delay: Maximum delay cap (seconds)
            jitter_factor: Random jitter factor (0-1)
        """
        self.max_retries = max_retries
        self.circuit_threshold = circuit_threshold
        self.circuit_timeout = circuit_timeout
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter_factor = jitter_factor
        
        # Circuit breaker state
        self._circuit_state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._lock = threading.RLock()
        
        # Metrics and logging
        self._metrics = HealthMetrics()
        self._healing_log: deque = deque(maxlen=1000)
        self._latencies: deque = deque(maxlen=100)
        
        # Callbacks for custom healing
        self._fallback_handlers: Dict[str, Callable] = {}
        self._escalation_handlers: List[Callable] = []
    
    def register_fallback(self, error_type: str, handler: Callable):
        """Register a fallback handler for specific error types."""
        self._fallback_handlers[error_type] = handler
    
    def register_escalation(self, handler: Callable):
        """Register an escalation handler for unrecoverable errors."""
        self._escalation_handlers.append(handler)
    
    def _get_circuit_state(self) -> CircuitState:
        """Get current circuit state with timeout check."""
        with self._lock:
            if self._circuit_state == CircuitState.OPEN:
                if time.time() - self._last_failure_time > self.circuit_timeout:
                    self._circuit_state = CircuitState.HALF_OPEN
            return self._circuit_state
    
    def _record_success(self, latency_ms: float):
        """Record successful operation."""
        with self._lock:
            self._failure_count = 0
            self._circuit_state = CircuitState.CLOSED
            self._metrics.successful_operations += 1
            self._metrics.last_success_time = time.time()
            self._latencies.append(latency_ms)
            self._update_metrics()
    
    def _record_failure(self, error: Exception, context: Dict):
        """Record failed operation and update circuit state."""
        with self._lock:
            self._failure_count += 1
            self._metrics.failed_operations += 1
            self._metrics.last_failure_time = time.time()
            self._last_failure_time = time.time()
            
            if self._failure_count >= self.circuit_threshold:
                self._circuit_state = CircuitState.OPEN
                self._metrics.circuit_breaks += 1
                self._log_healing_event(
                    "circuit_break",
                    HealingStrategy.CIRCUIT_BREAK,
                    False,
                    {"error": str(error), "context": context}
                )
            
            self._update_metrics()
    
    def _update_metrics(self):
        """Update computed metrics."""
        total = self._metrics.successful_operations + self._metrics.failed_operations
        if total > 0:
            self._metrics.error_rate = self._metrics.failed_operations / total
        if self._latencies:
            self._metrics.avg_latency_ms = sum(self._latencies) / len(self._latencies)
        self._metrics.total_operations = total
    
    def _log_healing_event(
        self,
        operation_id: str,
        strategy: HealingStrategy,
        success: bool,
        details: Dict,
        duration_ms: float = 0.0
    ):
        """Log a healing event for audit trail."""
        event = HealingEvent(
            timestamp=time.time(),
            operation_id=operation_id,
            strategy=strategy,
            success=success,
            details=details,
            duration_ms=duration_ms
        )
        self._healing_log.append(event)
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter."""
        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
        jitter = delay * self.jitter_factor * random.random()
        return delay + jitter
    
    def _is_security_violation(self, error: Exception) -> bool:
        """Check if error indicates a security violation (should not retry)."""
        security_indicators = [
            "AAD mismatch",
            "Authentication failed",
            "tamper",
            "invalid signature",
            "key mismatch",
            "unauthorized",
        ]
        error_str = str(error).lower()
        return any(ind.lower() in error_str for ind in security_indicators)

    def execute(
        self,
        operation: Callable,
        *args,
        operation_id: str = None,
        **kwargs
    ) -> Tuple[bool, Any, List[str]]:
        """
        Execute operation with self-healing capabilities.
        
        Args:
            operation: The callable to execute
            *args: Positional arguments for the operation
            operation_id: Optional identifier for logging
            **kwargs: Keyword arguments for the operation
        
        Returns:
            Tuple of (success, result, healing_actions_taken)
        """
        if operation_id is None:
            operation_id = hashlib.sha256(
                f"{operation.__name__}:{time.time()}".encode()
            ).hexdigest()[:16]
        
        healing_actions = []
        start_time = time.perf_counter()
        
        # Check circuit breaker
        circuit_state = self._get_circuit_state()
        if circuit_state == CircuitState.OPEN:
            healing_actions.append("circuit_breaker_blocked")
            self._log_healing_event(
                operation_id,
                HealingStrategy.CIRCUIT_BREAK,
                False,
                {"reason": "circuit_open"}
            )
            return False, None, healing_actions
        
        # Attempt operation with retries
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                result = operation(*args, **kwargs)
                
                # Success
                latency_ms = (time.perf_counter() - start_time) * 1000
                self._record_success(latency_ms)
                
                if attempt > 0:
                    self._metrics.healed_operations += 1
                    healing_actions.append(f"retry_success_attempt_{attempt}")
                    self._log_healing_event(
                        operation_id,
                        HealingStrategy.RETRY,
                        True,
                        {"attempt": attempt},
                        latency_ms
                    )
                
                return True, result, healing_actions
            
            except Exception as e:
                last_error = e
                error_type = type(e).__name__
                healing_actions.append(f"attempt_{attempt}_{error_type}")
                
                # Security violations should not be retried
                if self._is_security_violation(e):
                    healing_actions.append("security_violation_detected")
                    self._record_failure(e, {"type": "security_violation"})
                    self._log_healing_event(
                        operation_id,
                        HealingStrategy.QUARANTINE,
                        False,
                        {"error": str(e), "type": "security_violation"}
                    )
                    return False, None, healing_actions
                
                # Try fallback handler
                if error_type in self._fallback_handlers:
                    try:
                        fallback_result = self._fallback_handlers[error_type](e, *args, **kwargs)
                        healing_actions.append(f"fallback_{error_type}")
                        self._log_healing_event(
                            operation_id,
                            HealingStrategy.FALLBACK,
                            True,
                            {"error_type": error_type}
                        )
                        return True, fallback_result, healing_actions
                    except Exception:
                        pass
                
                # Last attempt - no more retries
                if attempt == self.max_retries:
                    self._record_failure(e, {"type": "max_retries_exceeded"})
                    
                    # Escalate to handlers
                    for handler in self._escalation_handlers:
                        try:
                            handler(e, operation_id, healing_actions)
                        except Exception:
                            pass
                    
                    self._log_healing_event(
                        operation_id,
                        HealingStrategy.ESCALATE,
                        False,
                        {"error": str(e), "attempts": attempt + 1}
                    )
                    return False, None, healing_actions
                
                # Wait before retry
                delay = self._calculate_delay(attempt)
                time.sleep(delay)
                healing_actions.append(f"backoff_{int(delay*1000)}ms")
        
        return False, None, healing_actions
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status."""
        with self._lock:
            return {
                "healthy": (
                    self._circuit_state == CircuitState.CLOSED and
                    self._metrics.error_rate < 0.05
                ),
                "circuit_state": self._circuit_state.value,
                "metrics": {
                    "total_operations": self._metrics.total_operations,
                    "successful_operations": self._metrics.successful_operations,
                    "failed_operations": self._metrics.failed_operations,
                    "healed_operations": self._metrics.healed_operations,
                    "circuit_breaks": self._metrics.circuit_breaks,
                    "error_rate": round(self._metrics.error_rate, 4),
                    "avg_latency_ms": round(self._metrics.avg_latency_ms, 2),
                },
                "last_failure": self._metrics.last_failure_time,
                "last_success": self._metrics.last_success_time,
            }
    
    def get_audit_log(self, limit: int = 100) -> List[Dict]:
        """Get audit log of healing events."""
        events = list(self._healing_log)[-limit:]
        return [
            {
                "timestamp": e.timestamp,
                "operation_id": e.operation_id,
                "strategy": e.strategy.value,
                "success": e.success,
                "details": e.details,
                "duration_ms": e.duration_ms,
            }
            for e in events
        ]
    
    def reset(self):
        """Reset circuit breaker and metrics."""
        with self._lock:
            self._circuit_state = CircuitState.CLOSED
            self._failure_count = 0
            self._metrics = HealthMetrics()
            self._healing_log.clear()
            self._latencies.clear()
    
    def force_open_circuit(self):
        """Manually open circuit (for maintenance)."""
        with self._lock:
            self._circuit_state = CircuitState.OPEN
            self._last_failure_time = time.time()
    
    def force_close_circuit(self):
        """Manually close circuit (after maintenance)."""
        with self._lock:
            self._circuit_state = CircuitState.CLOSED
            self._failure_count = 0


# Convenience function for simple usage
def with_healing(
    operation: Callable,
    *args,
    max_retries: int = 3,
    **kwargs
) -> Tuple[bool, Any]:
    """
    Execute operation with default self-healing.
    
    Args:
        operation: The callable to execute
        *args: Arguments for the operation
        max_retries: Maximum retry attempts
        **kwargs: Keyword arguments for the operation
    
    Returns:
        Tuple of (success, result)
    """
    orchestrator = SelfHealingOrchestrator(max_retries=max_retries)
    success, result, _ = orchestrator.execute(operation, *args, **kwargs)
    return success, result
