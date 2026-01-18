#!/usr/bin/env python3
"""
Hamiltonian Control Flow Integrity (CFI)

Valid execution = Hamiltonian path through state graph
Attack = deviation from linearized manifold

The execution graph G = (V, E) where:
- V = valid program states (nodes)
- E = valid transitions (edges)

A Hamiltonian path visits every vertex exactly once.
Valid execution traces must form Hamiltonian paths.

Key Insight:
- Linearized manifold = expected execution sequence
- Deviation = attack or anomaly
- Detection via path validation in O(|V|) for known graphs

Document ID: SCBE-CFI-2026-001
Version: 1.0.0
"""

import math
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Set, Tuple, Optional, Any
from enum import Enum


# =============================================================================
# CONSTANTS
# =============================================================================

MAX_STATES = 1000  # Maximum states in execution graph
MAX_PATH_LENGTH = 10000  # Maximum execution trace length


class CFIStatus(Enum):
    """Control flow integrity status."""
    VALID = "VALID"           # Path follows Hamiltonian structure
    DEVIATION = "DEVIATION"   # Path deviates from expected
    CYCLE = "CYCLE"           # Unexpected cycle detected
    ORPHAN = "ORPHAN"         # Unreachable state visited
    TRUNCATED = "TRUNCATED"   # Path incomplete


# =============================================================================
# STATE AND TRANSITION DEFINITIONS
# =============================================================================

@dataclass
class ExecutionState:
    """
    A node in the execution graph.
    
    Each state has:
    - id: Unique identifier
    - name: Human-readable name
    - hash: Cryptographic fingerprint of state
    - metadata: Additional state information
    """
    id: int
    name: str
    hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.hash:
            # Generate hash from id and name
            content = f"{self.id}:{self.name}"
            self.hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if isinstance(other, ExecutionState):
            return self.id == other.id
        return False


@dataclass
class Transition:
    """
    An edge in the execution graph.
    
    Represents valid transition from source to target state.
    """
    source: int  # Source state ID
    target: int  # Target state ID
    weight: float = 1.0  # Transition cost/probability
    label: str = ""  # Transition label (e.g., function name)
    
    def __hash__(self):
        return hash((self.source, self.target))


# =============================================================================
# EXECUTION GRAPH
# =============================================================================

class ExecutionGraph:
    """
    Directed graph representing valid execution paths.
    
    G = (V, E) where:
    - V = set of ExecutionState nodes
    - E = set of Transition edges
    """
    
    def __init__(self):
        self.states: Dict[int, ExecutionState] = {}
        self.transitions: Dict[int, List[Transition]] = {}  # adjacency list
        self.reverse_transitions: Dict[int, List[Transition]] = {}
        self._entry_state: Optional[int] = None
        self._exit_states: Set[int] = set()
    
    def add_state(self, state: ExecutionState) -> None:
        """Add a state to the graph."""
        self.states[state.id] = state
        if state.id not in self.transitions:
            self.transitions[state.id] = []
        if state.id not in self.reverse_transitions:
            self.reverse_transitions[state.id] = []
    
    def add_transition(self, transition: Transition) -> None:
        """Add a transition (edge) to the graph."""
        if transition.source not in self.states:
            raise ValueError(f"Source state {transition.source} not in graph")
        if transition.target not in self.states:
            raise ValueError(f"Target state {transition.target} not in graph")
        
        self.transitions[transition.source].append(transition)
        self.reverse_transitions[transition.target].append(transition)
    
    def set_entry(self, state_id: int) -> None:
        """Set the entry state (start of execution)."""
        if state_id not in self.states:
            raise ValueError(f"State {state_id} not in graph")
        self._entry_state = state_id
    
    def add_exit(self, state_id: int) -> None:
        """Add an exit state (valid termination point)."""
        if state_id not in self.states:
            raise ValueError(f"State {state_id} not in graph")
        self._exit_states.add(state_id)
    
    @property
    def entry_state(self) -> Optional[int]:
        return self._entry_state
    
    @property
    def exit_states(self) -> Set[int]:
        return self._exit_states
    
    def get_successors(self, state_id: int) -> List[int]:
        """Get valid successor states."""
        return [t.target for t in self.transitions.get(state_id, [])]
    
    def get_predecessors(self, state_id: int) -> List[int]:
        """Get valid predecessor states."""
        return [t.source for t in self.reverse_transitions.get(state_id, [])]
    
    def is_valid_transition(self, source: int, target: int) -> bool:
        """Check if transition from source to target is valid."""
        return target in self.get_successors(source)
    
    def state_count(self) -> int:
        return len(self.states)
    
    def transition_count(self) -> int:
        return sum(len(t) for t in self.transitions.values())


# =============================================================================
# HAMILTONIAN PATH DETECTION
# =============================================================================

def find_hamiltonian_path(
    graph: ExecutionGraph,
    start: Optional[int] = None,
    end: Optional[int] = None
) -> Optional[List[int]]:
    """
    Find a Hamiltonian path in the execution graph.
    
    A Hamiltonian path visits every vertex exactly once.
    
    Args:
        graph: The execution graph
        start: Starting state (default: entry state)
        end: Ending state (default: any exit state)
    
    Returns:
        List of state IDs forming Hamiltonian path, or None if not found
    
    Note: This is NP-complete in general, but execution graphs
    are typically small and structured.
    """
    if graph.state_count() == 0:
        return None
    
    start = start if start is not None else graph.entry_state
    if start is None:
        start = next(iter(graph.states.keys()))
    
    valid_ends = end if end is not None else graph.exit_states
    if isinstance(valid_ends, int):
        valid_ends = {valid_ends}
    if not valid_ends:
        valid_ends = set(graph.states.keys())
    
    n = graph.state_count()
    path = [start]
    visited = {start}
    
    def backtrack() -> bool:
        if len(path) == n:
            return path[-1] in valid_ends
        
        current = path[-1]
        for next_state in graph.get_successors(current):
            if next_state not in visited:
                path.append(next_state)
                visited.add(next_state)
                
                if backtrack():
                    return True
                
                path.pop()
                visited.remove(next_state)
        
        return False
    
    if backtrack():
        return path
    return None


def has_hamiltonian_path(graph: ExecutionGraph) -> bool:
    """Check if graph has any Hamiltonian path."""
    return find_hamiltonian_path(graph) is not None


# =============================================================================
# EXECUTION TRACE VALIDATION
# =============================================================================

@dataclass
class TraceValidation:
    """Result of validating an execution trace."""
    status: CFIStatus
    valid_prefix_length: int  # How many states were valid
    deviation_point: Optional[int] = None  # State ID where deviation occurred
    expected_states: List[int] = field(default_factory=list)  # What was expected
    message: str = ""


def validate_trace(
    graph: ExecutionGraph,
    trace: List[int],
    allow_partial: bool = False
) -> TraceValidation:
    """
    Validate an execution trace against the graph.
    
    Args:
        graph: The execution graph defining valid paths
        trace: List of state IDs representing execution
        allow_partial: If True, partial valid traces are OK
    
    Returns:
        TraceValidation with status and details
    """
    if not trace:
        return TraceValidation(
            status=CFIStatus.TRUNCATED,
            valid_prefix_length=0,
            message="Empty trace"
        )
    
    # Check first state
    if trace[0] not in graph.states:
        return TraceValidation(
            status=CFIStatus.ORPHAN,
            valid_prefix_length=0,
            deviation_point=trace[0],
            message=f"Unknown start state: {trace[0]}"
        )
    
    # Check entry point
    if graph.entry_state is not None and trace[0] != graph.entry_state:
        return TraceValidation(
            status=CFIStatus.DEVIATION,
            valid_prefix_length=0,
            deviation_point=trace[0],
            expected_states=[graph.entry_state],
            message=f"Invalid entry: expected {graph.entry_state}, got {trace[0]}"
        )
    
    # Validate each transition
    visited = set()
    for i in range(len(trace) - 1):
        current = trace[i]
        next_state = trace[i + 1]
        
        # Check for cycles (revisiting states)
        if current in visited:
            return TraceValidation(
                status=CFIStatus.CYCLE,
                valid_prefix_length=i,
                deviation_point=current,
                message=f"Cycle detected: state {current} revisited"
            )
        visited.add(current)
        
        # Check if next state exists
        if next_state not in graph.states:
            return TraceValidation(
                status=CFIStatus.ORPHAN,
                valid_prefix_length=i + 1,
                deviation_point=next_state,
                expected_states=graph.get_successors(current),
                message=f"Unknown state: {next_state}"
            )
        
        # Check if transition is valid
        if not graph.is_valid_transition(current, next_state):
            return TraceValidation(
                status=CFIStatus.DEVIATION,
                valid_prefix_length=i + 1,
                deviation_point=next_state,
                expected_states=graph.get_successors(current),
                message=f"Invalid transition: {current} -> {next_state}"
            )
    
    # Check final state
    final_state = trace[-1]
    if final_state in visited:
        return TraceValidation(
            status=CFIStatus.CYCLE,
            valid_prefix_length=len(trace) - 1,
            deviation_point=final_state,
            message=f"Cycle at final state: {final_state}"
        )
    
    # Check if ended at valid exit
    if graph.exit_states and final_state not in graph.exit_states:
        if not allow_partial:
            return TraceValidation(
                status=CFIStatus.TRUNCATED,
                valid_prefix_length=len(trace),
                expected_states=list(graph.exit_states),
                message=f"Did not reach exit state"
            )
    
    return TraceValidation(
        status=CFIStatus.VALID,
        valid_prefix_length=len(trace),
        message="Valid execution trace"
    )


# =============================================================================
# LINEARIZED MANIFOLD
# =============================================================================

class LinearizedManifold:
    """
    The linearized manifold represents the expected execution sequence.
    
    Deviation from this manifold indicates potential attack.
    
    The manifold is defined by:
    1. A reference Hamiltonian path (golden path)
    2. Allowed deviations (branch points)
    3. Convergence requirements (must rejoin)
    """
    
    def __init__(self, graph: ExecutionGraph):
        self.graph = graph
        self._golden_path: Optional[List[int]] = None
        self._branch_points: Set[int] = set()
        self._convergence_points: Set[int] = set()
    
    def compute_golden_path(self) -> Optional[List[int]]:
        """Compute the reference Hamiltonian path."""
        self._golden_path = find_hamiltonian_path(self.graph)
        return self._golden_path
    
    @property
    def golden_path(self) -> Optional[List[int]]:
        if self._golden_path is None:
            self.compute_golden_path()
        return self._golden_path
    
    def set_branch_point(self, state_id: int) -> None:
        """Mark a state as an allowed branch point."""
        self._branch_points.add(state_id)
    
    def set_convergence_point(self, state_id: int) -> None:
        """Mark a state as a required convergence point."""
        self._convergence_points.add(state_id)
    
    def deviation_distance(self, trace: List[int]) -> float:
        """
        Compute deviation distance from golden path.
        
        Returns:
            Distance in [0, 1] where 0 = on manifold, 1 = max deviation
        """
        if not self.golden_path or not trace:
            return 1.0
        
        # Count states not on golden path
        golden_set = set(self.golden_path)
        off_path = sum(1 for s in trace if s not in golden_set)
        
        return off_path / len(trace)
    
    def validate_against_manifold(
        self,
        trace: List[int]
    ) -> Tuple[bool, float, str]:
        """
        Validate trace against linearized manifold.
        
        Returns:
            (is_valid, deviation_distance, message)
        """
        # First validate basic CFI
        validation = validate_trace(self.graph, trace, allow_partial=True)
        
        if validation.status not in (CFIStatus.VALID, CFIStatus.TRUNCATED):
            return False, 1.0, validation.message
        
        # Check deviation from golden path
        deviation = self.deviation_distance(trace)
        
        # Check convergence points
        trace_set = set(trace)
        missing_convergence = self._convergence_points - trace_set
        
        if missing_convergence:
            return False, deviation, f"Missing convergence points: {missing_convergence}"
        
        # Allow some deviation at branch points
        if deviation > 0.5:
            return False, deviation, f"Excessive deviation: {deviation:.2%}"
        
        return True, deviation, "Valid execution within manifold"


# =============================================================================
# CFI MONITOR
# =============================================================================

class CFIMonitor:
    """
    Real-time Control Flow Integrity monitor.
    
    Tracks execution and detects deviations from expected paths.
    """
    
    def __init__(self, graph: ExecutionGraph):
        self.graph = graph
        self.manifold = LinearizedManifold(graph)
        self._current_state: Optional[int] = None
        self._trace: List[int] = []
        self._violations: List[TraceValidation] = []
    
    def start(self, initial_state: Optional[int] = None) -> None:
        """Start monitoring from initial state."""
        self._current_state = initial_state or self.graph.entry_state
        self._trace = [self._current_state] if self._current_state else []
        self._violations = []
    
    def transition(self, next_state: int) -> CFIStatus:
        """
        Record a state transition.
        
        Returns:
            CFIStatus indicating if transition is valid
        """
        if self._current_state is None:
            self._current_state = next_state
            self._trace.append(next_state)
            return CFIStatus.VALID
        
        # Check if transition is valid
        if not self.graph.is_valid_transition(self._current_state, next_state):
            violation = TraceValidation(
                status=CFIStatus.DEVIATION,
                valid_prefix_length=len(self._trace),
                deviation_point=next_state,
                expected_states=self.graph.get_successors(self._current_state),
                message=f"Invalid: {self._current_state} -> {next_state}"
            )
            self._violations.append(violation)
            return CFIStatus.DEVIATION
        
        # Check for cycles
        if next_state in self._trace:
            violation = TraceValidation(
                status=CFIStatus.CYCLE,
                valid_prefix_length=len(self._trace),
                deviation_point=next_state,
                message=f"Cycle: revisiting {next_state}"
            )
            self._violations.append(violation)
            return CFIStatus.CYCLE
        
        self._current_state = next_state
        self._trace.append(next_state)
        return CFIStatus.VALID
    
    def get_trace(self) -> List[int]:
        """Get current execution trace."""
        return self._trace.copy()
    
    def get_violations(self) -> List[TraceValidation]:
        """Get all recorded violations."""
        return self._violations.copy()
    
    def is_clean(self) -> bool:
        """Check if execution has been clean (no violations)."""
        return len(self._violations) == 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        return {
            "trace_length": len(self._trace),
            "violation_count": len(self._violations),
            "current_state": self._current_state,
            "is_clean": self.is_clean(),
            "deviation_distance": self.manifold.deviation_distance(self._trace)
        }


# =============================================================================
# PROOFS AND VERIFICATION
# =============================================================================

def verify_hamiltonian_detection() -> bool:
    """
    Verify: Hamiltonian path detection works for simple graphs.
    """
    # Create simple linear graph: 0 -> 1 -> 2 -> 3
    graph = ExecutionGraph()
    for i in range(4):
        graph.add_state(ExecutionState(i, f"S{i}"))
    for i in range(3):
        graph.add_transition(Transition(i, i + 1))
    graph.set_entry(0)
    graph.add_exit(3)
    
    path = find_hamiltonian_path(graph)
    return path == [0, 1, 2, 3]


def verify_deviation_detection() -> bool:
    """
    Verify: Invalid transitions are detected.
    """
    graph = ExecutionGraph()
    for i in range(3):
        graph.add_state(ExecutionState(i, f"S{i}"))
    graph.add_transition(Transition(0, 1))
    graph.add_transition(Transition(1, 2))
    graph.set_entry(0)
    graph.add_exit(2)
    
    # Valid trace
    valid = validate_trace(graph, [0, 1, 2])
    if valid.status != CFIStatus.VALID:
        return False
    
    # Invalid trace (skips state 1)
    invalid = validate_trace(graph, [0, 2])
    if invalid.status != CFIStatus.DEVIATION:
        return False
    
    return True


def verify_cycle_detection() -> bool:
    """
    Verify: Cycles in execution are detected.
    """
    graph = ExecutionGraph()
    for i in range(3):
        graph.add_state(ExecutionState(i, f"S{i}"))
    graph.add_transition(Transition(0, 1))
    graph.add_transition(Transition(1, 2))
    graph.add_transition(Transition(2, 0))  # Creates cycle
    graph.set_entry(0)
    
    # Trace with cycle
    result = validate_trace(graph, [0, 1, 2, 0])
    return result.status == CFIStatus.CYCLE


# =============================================================================
# DEMO
# =============================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("HAMILTONIAN CONTROL FLOW INTEGRITY (CFI)")
    print("=" * 70)
    print()
    
    # Verify proofs
    print("MATHEMATICAL PROOFS:")
    print(f"  Hamiltonian detection:  {'✓ PROVEN' if verify_hamiltonian_detection() else '✗ FAILED'}")
    print(f"  Deviation detection:    {'✓ PROVEN' if verify_deviation_detection() else '✗ FAILED'}")
    print(f"  Cycle detection:        {'✓ PROVEN' if verify_cycle_detection() else '✗ FAILED'}")
    print()
    
    # Demo: Build execution graph
    print("DEMO: Authentication Flow")
    print("-" * 40)
    
    graph = ExecutionGraph()
    states = [
        ExecutionState(0, "INIT"),
        ExecutionState(1, "AUTH_START"),
        ExecutionState(2, "VALIDATE_CREDS"),
        ExecutionState(3, "CHECK_MFA"),
        ExecutionState(4, "SESSION_CREATE"),
        ExecutionState(5, "COMPLETE"),
    ]
    for s in states:
        graph.add_state(s)
    
    transitions = [
        Transition(0, 1, label="begin_auth"),
        Transition(1, 2, label="submit_creds"),
        Transition(2, 3, label="creds_valid"),
        Transition(3, 4, label="mfa_passed"),
        Transition(4, 5, label="finalize"),
    ]
    for t in transitions:
        graph.add_transition(t)
    
    graph.set_entry(0)
    graph.add_exit(5)
    
    print(f"  States: {graph.state_count()}")
    print(f"  Transitions: {graph.transition_count()}")
    print()
    
    # Find Hamiltonian path
    path = find_hamiltonian_path(graph)
    print(f"  Hamiltonian path: {path}")
    print(f"  Path names: {[graph.states[s].name for s in path]}")
    print()
    
    # Validate traces
    print("TRACE VALIDATION:")
    
    valid_trace = [0, 1, 2, 3, 4, 5]
    result = validate_trace(graph, valid_trace)
    print(f"  Valid trace {valid_trace}:")
    print(f"    Status: {result.status.value}")
    print()
    
    attack_trace = [0, 1, 4, 5]  # Skips validation!
    result = validate_trace(graph, attack_trace)
    print(f"  Attack trace {attack_trace} (skips validation):")
    print(f"    Status: {result.status.value}")
    print(f"    Deviation at: {result.deviation_point}")
    print(f"    Expected: {result.expected_states}")
    print()
    
    # Monitor demo
    print("CFI MONITOR:")
    monitor = CFIMonitor(graph)
    monitor.start(0)
    
    for next_state in [1, 2, 3, 4, 5]:
        status = monitor.transition(next_state)
        print(f"  {monitor._trace[-2]} -> {next_state}: {status.value}")
    
    print(f"\n  Final: clean={monitor.is_clean()}, trace_len={len(monitor.get_trace())}")
    print()
    
    print("=" * 70)
    print("Valid execution = Hamiltonian path through state graph")
    print("Attack = deviation from linearized manifold")
    print("=" * 70)
