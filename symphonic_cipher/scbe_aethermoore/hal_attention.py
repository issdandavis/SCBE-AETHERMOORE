"""
HAL-Attention - Harmonic Attention Layer
=========================================
Extends standard transformer attention with harmonic weighting
derived from the H(d,R) scaling law.

HAL-Attention(Q, K, V, d) = softmax(H_weight(Q, K, d)) · V

Where H_weight(Q, K, d) = (QKᵀ / √d_k) ⊙ Λ(d)
And Λ(d)[i,j] = R₅^(d_i · d_j)

Document ID: AETHER-SPEC-2026-001
Section: 4 (HAL-Attention Mathematics)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict, Any, Union

from .constants import (
    R_FIFTH, PHI, DEFAULT_D_MAX, DEFAULT_R,
    harmonic_scale, CONSTANTS
)


# =============================================================================
# TYPE DEFINITIONS
# =============================================================================

# Simple tensor types (for pure Python implementation)
Vector = List[float]
Matrix = List[List[float]]
Tensor3D = List[Matrix]  # [batch, seq_len, d_model]
Tensor2D = List[Vector]  # [batch, seq_len] or [seq_len, seq_len]


@dataclass
class HALConfig:
    """
    Harmonic Attention Layer configuration.

    Attributes:
        d_model: Model dimension (embedding size)
        n_heads: Number of attention heads
        R: Harmonic ratio (default 1.5 = perfect fifth)
        d_max: Maximum dimension depth (default 6)
        normalize: Apply overflow prevention (default True)
        dropout: Attention dropout rate (default 0.0)
    """
    d_model: int = 512
    n_heads: int = 8
    R: float = R_FIFTH
    d_max: int = DEFAULT_D_MAX
    normalize: bool = True
    dropout: float = 0.0

    def __post_init__(self):
        if self.d_model % self.n_heads != 0:
            raise ValueError(f"d_model ({self.d_model}) must be divisible by n_heads ({self.n_heads})")
        self.d_k = self.d_model // self.n_heads


@dataclass
class AttentionOutput:
    """Result of HAL-Attention computation."""
    output: Matrix              # [seq_len, d_model]
    attention_weights: Matrix   # [seq_len, seq_len]
    coupling_matrix: Matrix     # Λ matrix
    dimension_depths: Vector    # d values used


# =============================================================================
# HARMONIC COUPLING MATRIX Λ
# =============================================================================

def harmonic_coupling_matrix(
    d_Q: List[float],
    d_K: List[float],
    R: float = R_FIFTH,
    normalize: bool = True
) -> Matrix:
    """
    Compute the harmonic coupling matrix Λ.

    Definition 4.4.1 (Coupling Matrix Λ):
        Λ(d_Q, d_K)[i,j] = R^(d_Q[i] · d_K[j])

    Properties:
        - Symmetric when d_Q = d_K
        - All entries positive (R > 1)
        - Trace(Λ) = Σᵢ R^(d[i]²)

    Args:
        d_Q: Query dimension depths [n]
        d_K: Key dimension depths [m]
        R: Harmonic ratio (default 1.5)
        normalize: Apply overflow prevention

    Returns:
        Coupling matrix Λ of shape [n, m]

    Example:
        >>> d = [1, 2, 3]
        >>> coupling = harmonic_coupling_matrix(d, d, 1.5)
        >>> coupling[2][2]  # R^(3*3) = 1.5^9 = 38.44...
        38.443359375
    """
    n = len(d_Q)
    m = len(d_K)

    # Compute raw coupling values
    coupling: Matrix = []
    max_val = 0.0

    for i in range(n):
        row = []
        for j in range(m):
            exponent = d_Q[i] * d_K[j]
            val = R ** exponent
            row.append(val)
            if val > max_val:
                max_val = val
        coupling.append(row)

    # Apply normalization if requested
    if normalize and max_val > 0:
        # Λ_norm[i,j] = Λ[i,j] / max(Λ) = R^(d_Q[i]·d_K[j] - d_max²)
        for i in range(n):
            for j in range(m):
                coupling[i][j] /= max_val

    return coupling


def compute_coupling_trace(coupling: Matrix) -> float:
    """
    Compute trace of coupling matrix.

    Trace(Λ) = Σᵢ R^(d[i]²)

    Args:
        coupling: Square coupling matrix

    Returns:
        Trace value
    """
    n = min(len(coupling), len(coupling[0]) if coupling else 0)
    return sum(coupling[i][i] for i in range(n))


# =============================================================================
# DIMENSION DEPTH ASSIGNMENT
# =============================================================================

def assign_dimension_depths(
    sequence_length: int,
    method: str = 'positional',
    d_max: int = DEFAULT_D_MAX,
    **kwargs
) -> List[float]:
    """
    Assign dimension depth values to each token position.

    Methods:
        - 'positional': Linear scaling based on position
        - 'uniform': Same depth for all positions
        - 'random': Random depths (for training)
        - 'semantic': Based on token importance (requires embeddings)
        - 'golden': Golden ratio-based assignment

    Args:
        sequence_length: Number of tokens
        method: Assignment method
        d_max: Maximum dimension depth
        **kwargs: Method-specific parameters

    Returns:
        List of dimension depths [seq_len]
    """
    if method == 'positional':
        # Linear scaling: position 0 → 1, position N-1 → d_max
        if sequence_length == 1:
            return [1.0]
        return [1 + (d_max - 1) * i / (sequence_length - 1)
                for i in range(sequence_length)]

    elif method == 'uniform':
        # Same depth for all positions
        d = kwargs.get('depth', d_max / 2)
        return [d] * sequence_length

    elif method == 'random':
        # Random depths (useful for training)
        import random
        return [random.uniform(1, d_max) for _ in range(sequence_length)]

    elif method == 'golden':
        # Golden ratio-based: more attention to early tokens
        depths = []
        for i in range(sequence_length):
            # φ^(-i) gives decreasing importance
            d = 1 + (d_max - 1) * (PHI ** (-i))
            d = max(1, min(d_max, d))  # Clamp to [1, d_max]
            depths.append(d)
        return depths

    elif method == 'semantic':
        # Requires embeddings or importance scores
        importance = kwargs.get('importance', None)
        if importance is None:
            # Fallback to positional
            return assign_dimension_depths(sequence_length, 'positional', d_max)
        # Scale importance to [1, d_max]
        min_imp = min(importance)
        max_imp = max(importance)
        if max_imp == min_imp:
            return [d_max / 2] * sequence_length
        return [1 + (d_max - 1) * (imp - min_imp) / (max_imp - min_imp)
                for imp in importance]

    else:
        raise ValueError(f"Unknown method: {method}")


# =============================================================================
# SOFTMAX FUNCTION
# =============================================================================

def softmax(x: List[float]) -> List[float]:
    """
    Compute softmax of a vector.

    Args:
        x: Input vector

    Returns:
        Softmax probabilities
    """
    # Subtract max for numerical stability
    max_x = max(x)
    exp_x = [math.exp(xi - max_x) for xi in x]
    sum_exp = sum(exp_x)
    return [e / sum_exp for e in exp_x]


def softmax_2d(matrix: Matrix) -> Matrix:
    """
    Apply softmax to each row of a matrix.

    Args:
        matrix: Input matrix [n, m]

    Returns:
        Softmax matrix [n, m]
    """
    return [softmax(row) for row in matrix]


# =============================================================================
# MATRIX OPERATIONS
# =============================================================================

def matmul(A: Matrix, B: Matrix) -> Matrix:
    """Matrix multiplication A @ B."""
    n = len(A)
    m = len(B[0])
    k = len(B)

    result = [[0.0] * m for _ in range(n)]
    for i in range(n):
        for j in range(m):
            for p in range(k):
                result[i][j] += A[i][p] * B[p][j]
    return result


def transpose(A: Matrix) -> Matrix:
    """Matrix transpose."""
    if not A:
        return []
    return [[A[i][j] for i in range(len(A))] for j in range(len(A[0]))]


def hadamard(A: Matrix, B: Matrix) -> Matrix:
    """Element-wise (Hadamard) product."""
    return [[A[i][j] * B[i][j] for j in range(len(A[0]))]
            for i in range(len(A))]


def scale_matrix(A: Matrix, scalar: float) -> Matrix:
    """Scale matrix by scalar."""
    return [[A[i][j] * scalar for j in range(len(A[0]))]
            for i in range(len(A))]


# =============================================================================
# HAL-ATTENTION CORE
# =============================================================================

def hal_attention(
    Q: Matrix,
    K: Matrix,
    V: Matrix,
    d_Q: Optional[List[float]] = None,
    d_K: Optional[List[float]] = None,
    config: Optional[HALConfig] = None
) -> AttentionOutput:
    """
    Compute HAL-Attention with harmonic weighting.

    Definition 4.3.1 (Harmonic Attention):
        HAL-Attention(Q, K, V, d) = softmax(H_weight(Q, K, d)) · V

    Where:
        H_weight(Q, K, d) = (QKᵀ / √d_k) ⊙ Λ(d)

    Args:
        Q: Query matrix [seq_len, d_model]
        K: Key matrix [seq_len, d_model]
        V: Value matrix [seq_len, d_model]
        d_Q: Query dimension depths [seq_len]
        d_K: Key dimension depths [seq_len]
        config: HAL configuration

    Returns:
        AttentionOutput with output, weights, coupling matrix

    Example:
        >>> Q = [[1.0, 0.0], [0.0, 1.0]]
        >>> K = [[1.0, 0.0], [0.0, 1.0]]
        >>> V = [[1.0, 2.0], [3.0, 4.0]]
        >>> result = hal_attention(Q, K, V)
        >>> len(result.output)
        2
    """
    if config is None:
        config = HALConfig(d_model=len(Q[0]) if Q else 512)

    seq_len = len(Q)
    d_k = len(Q[0]) if Q else config.d_k

    # Assign dimension depths if not provided
    if d_Q is None:
        d_Q = assign_dimension_depths(seq_len, 'positional', config.d_max)
    if d_K is None:
        d_K = assign_dimension_depths(len(K), 'positional', config.d_max)

    # Step 1: Compute standard attention scores QKᵀ / √d_k
    K_T = transpose(K)
    scores = matmul(Q, K_T)
    scale_factor = 1.0 / math.sqrt(d_k)
    scores = scale_matrix(scores, scale_factor)

    # Step 2: Compute harmonic coupling matrix Λ
    coupling = harmonic_coupling_matrix(d_Q, d_K, config.R, config.normalize)

    # Step 3: Apply Hadamard product (element-wise)
    # H_weight(Q, K, d) = (QKᵀ / √d_k) ⊙ Λ(d)
    weighted_scores = hadamard(scores, coupling)

    # Step 4: Apply softmax
    attention_weights = softmax_2d(weighted_scores)

    # Step 5: Compute output
    output = matmul(attention_weights, V)

    return AttentionOutput(
        output=output,
        attention_weights=attention_weights,
        coupling_matrix=coupling,
        dimension_depths=d_Q
    )


# =============================================================================
# MULTI-HEAD HAL-ATTENTION
# =============================================================================

def split_heads(x: Matrix, n_heads: int) -> List[Matrix]:
    """
    Split matrix into multiple heads.

    Args:
        x: Input matrix [seq_len, d_model]
        n_heads: Number of heads

    Returns:
        List of matrices [n_heads][seq_len, d_k]
    """
    seq_len = len(x)
    d_model = len(x[0]) if x else 0
    d_k = d_model // n_heads

    heads = []
    for h in range(n_heads):
        head = []
        for i in range(seq_len):
            start = h * d_k
            end = start + d_k
            head.append(x[i][start:end])
        heads.append(head)

    return heads


def concat_heads(heads: List[Matrix]) -> Matrix:
    """
    Concatenate heads back together.

    Args:
        heads: List of matrices [n_heads][seq_len, d_k]

    Returns:
        Combined matrix [seq_len, d_model]
    """
    if not heads:
        return []

    seq_len = len(heads[0])
    result = []

    for i in range(seq_len):
        row = []
        for head in heads:
            row.extend(head[i])
        result.append(row)

    return result


def multi_head_hal_attention(
    Q: Matrix,
    K: Matrix,
    V: Matrix,
    d_Q: Optional[List[float]] = None,
    d_K: Optional[List[float]] = None,
    config: Optional[HALConfig] = None
) -> AttentionOutput:
    """
    Multi-head HAL-Attention.

    Splits input into multiple heads, applies HAL-Attention to each,
    then concatenates results.

    Args:
        Q: Query matrix [seq_len, d_model]
        K: Key matrix [seq_len, d_model]
        V: Value matrix [seq_len, d_model]
        d_Q: Query dimension depths
        d_K: Key dimension depths
        config: HAL configuration

    Returns:
        AttentionOutput with combined output
    """
    if config is None:
        config = HALConfig(d_model=len(Q[0]) if Q else 512)

    n_heads = config.n_heads
    seq_len = len(Q)

    # Assign depths if not provided
    if d_Q is None:
        d_Q = assign_dimension_depths(seq_len, 'positional', config.d_max)
    if d_K is None:
        d_K = assign_dimension_depths(len(K), 'positional', config.d_max)

    # Split into heads
    Q_heads = split_heads(Q, n_heads)
    K_heads = split_heads(K, n_heads)
    V_heads = split_heads(V, n_heads)

    # Apply HAL-Attention to each head
    head_outputs = []
    all_weights = []
    coupling = None

    for h in range(n_heads):
        head_config = HALConfig(
            d_model=len(Q_heads[h][0]) if Q_heads[h] and Q_heads[h][0] else config.d_k,
            n_heads=1,
            R=config.R,
            d_max=config.d_max,
            normalize=config.normalize
        )
        result = hal_attention(Q_heads[h], K_heads[h], V_heads[h], d_Q, d_K, head_config)
        head_outputs.append(result.output)
        all_weights.append(result.attention_weights)
        if coupling is None:
            coupling = result.coupling_matrix

    # Concatenate heads
    output = concat_heads(head_outputs)

    # Average attention weights across heads
    avg_weights = [[0.0] * len(all_weights[0][0]) for _ in range(len(all_weights[0]))]
    for weights in all_weights:
        for i in range(len(weights)):
            for j in range(len(weights[0])):
                avg_weights[i][j] += weights[i][j] / n_heads

    return AttentionOutput(
        output=output,
        attention_weights=avg_weights,
        coupling_matrix=coupling or [],
        dimension_depths=d_Q
    )


# =============================================================================
# HAL ATTENTION LAYER CLASS
# =============================================================================

class HALAttentionLayer:
    """
    Harmonic Attention Layer - drop-in replacement for standard attention.

    Usage:
        layer = HALAttentionLayer(d_model=512, n_heads=8)
        output = layer(query, key, value)

    For integration with PyTorch/TensorFlow, use the provided
    framework-specific wrappers.
    """

    def __init__(
        self,
        d_model: int = 512,
        n_heads: int = 8,
        R: float = R_FIFTH,
        d_max: int = DEFAULT_D_MAX,
        normalize: bool = True,
        depth_method: str = 'positional'
    ):
        """
        Initialize HAL Attention Layer.

        Args:
            d_model: Model dimension
            n_heads: Number of attention heads
            R: Harmonic ratio (default 1.5)
            d_max: Maximum dimension depth
            normalize: Apply overflow prevention
            depth_method: How to assign dimension depths
        """
        self.config = HALConfig(
            d_model=d_model,
            n_heads=n_heads,
            R=R,
            d_max=d_max,
            normalize=normalize
        )
        self.depth_method = depth_method

    def __call__(
        self,
        query: Matrix,
        key: Matrix,
        value: Matrix,
        d_Q: Optional[List[float]] = None,
        d_K: Optional[List[float]] = None
    ) -> AttentionOutput:
        """
        Apply HAL-Attention.

        Args:
            query: Query matrix
            key: Key matrix
            value: Value matrix
            d_Q: Optional query depths
            d_K: Optional key depths

        Returns:
            AttentionOutput
        """
        if d_Q is None:
            d_Q = assign_dimension_depths(
                len(query), self.depth_method, self.config.d_max
            )
        if d_K is None:
            d_K = assign_dimension_depths(
                len(key), self.depth_method, self.config.d_max
            )

        return multi_head_hal_attention(
            query, key, value, d_Q, d_K, self.config
        )

    def get_coupling_info(self, seq_len: int) -> Dict[str, Any]:
        """
        Get information about coupling matrix for given sequence length.

        Args:
            seq_len: Sequence length

        Returns:
            Dict with coupling statistics
        """
        depths = assign_dimension_depths(seq_len, self.depth_method, self.config.d_max)
        coupling = harmonic_coupling_matrix(depths, depths, self.config.R, self.config.normalize)

        return {
            'seq_len': seq_len,
            'depths': depths,
            'coupling_shape': (len(coupling), len(coupling[0]) if coupling else 0),
            'trace': compute_coupling_trace(coupling),
            'max_value': max(max(row) for row in coupling) if coupling else 0,
            'min_value': min(min(row) for row in coupling) if coupling else 0,
            'R': self.config.R,
            'd_max': self.config.d_max,
        }


# =============================================================================
# UTILITIES
# =============================================================================

def visualize_coupling_matrix(coupling: Matrix, title: str = "Λ Matrix") -> str:
    """
    Create ASCII visualization of coupling matrix.

    Args:
        coupling: Coupling matrix
        title: Plot title

    Returns:
        ASCII art string
    """
    if not coupling:
        return "Empty matrix"

    n = len(coupling)
    m = len(coupling[0])

    # Find min/max for scaling
    flat = [v for row in coupling for v in row]
    min_val = min(flat)
    max_val = max(flat)

    # ASCII gradient
    gradient = " ░▒▓█"

    lines = [f"  {title} ({n}x{m})"]
    lines.append("  " + "─" * (m + 2))

    for i in range(n):
        row_str = "  │"
        for j in range(m):
            # Scale to 0-4
            if max_val == min_val:
                idx = 2
            else:
                idx = int(4 * (coupling[i][j] - min_val) / (max_val - min_val))
            row_str += gradient[idx]
        row_str += "│"
        lines.append(row_str)

    lines.append("  " + "─" * (m + 2))
    lines.append(f"  Range: [{min_val:.4f}, {max_val:.4f}]")

    return "\n".join(lines)


def get_hal_stats() -> Dict[str, Any]:
    """Get HAL module statistics and constants."""
    return {
        'R_default': R_FIFTH,
        'd_max_default': DEFAULT_D_MAX,
        'depth_methods': ['positional', 'uniform', 'random', 'golden', 'semantic'],
        'harmonic_scale_d6': harmonic_scale(6, R_FIFTH),
        'phi': PHI,
        'constants': CONSTANTS,
    }
