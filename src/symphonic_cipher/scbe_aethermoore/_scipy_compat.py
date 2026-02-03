"""
Scipy Compatibility Layer - Optional Dependencies with Numpy Fallbacks
=======================================================================

This module provides scipy functionality with graceful fallbacks when scipy
is not installed. All functions maintain API compatibility with scipy.

Usage:
    from ._scipy_compat import fft, fftfreq, expm, sqrtm, solve_ivp

If scipy is available, it uses scipy. Otherwise, provides numpy-based fallbacks.

Fallback limitations:
    - expm: Uses Padé approximation (less accurate for large matrices)
    - sqrtm: Uses Newton iteration (may not converge for all matrices)
    - solve_ivp: Uses RK4 method (less sophisticated than scipy's adaptive methods)
    - hilbert: Uses FFT-based implementation (equivalent to scipy)
"""

import numpy as np
from typing import Callable, Tuple, Optional, Any
import warnings

# Track which backend is being used
SCIPY_AVAILABLE = False

# =============================================================================
# FFT Functions
# =============================================================================

try:
    from scipy.fft import fft, fftfreq, ifft
    from scipy.fftpack import fft as fft_pack, fftfreq as fftfreq_pack
    SCIPY_AVAILABLE = True
except ImportError:
    # Numpy fallback for FFT
    fft = np.fft.fft
    ifft = np.fft.ifft
    fftfreq = np.fft.fftfreq
    fft_pack = np.fft.fft
    fftfreq_pack = np.fft.fftfreq

# =============================================================================
# Linear Algebra Functions
# =============================================================================

try:
    from scipy.linalg import expm as _scipy_expm, sqrtm as _scipy_sqrtm
    expm = _scipy_expm
    sqrtm = _scipy_sqrtm
except ImportError:
    def expm(A: np.ndarray, q: int = 7) -> np.ndarray:
        """
        Matrix exponential using Padé approximation.

        Computes exp(A) for square matrix A using (q,q) Padé approximant.

        Args:
            A: Square matrix
            q: Order of Padé approximation (default 7)

        Returns:
            Matrix exponential exp(A)

        Note:
            Less accurate than scipy for matrices with large norm.
            For production use, install scipy.
        """
        A = np.asarray(A)
        if A.ndim != 2 or A.shape[0] != A.shape[1]:
            raise ValueError("Matrix must be square")

        n = A.shape[0]

        # Scale matrix to reduce norm
        norm_A = np.linalg.norm(A, ord=np.inf)
        s = max(0, int(np.ceil(np.log2(norm_A + 1))))
        A_scaled = A / (2 ** s)

        # Padé coefficients
        c = [1.0]
        for k in range(1, q + 1):
            c.append(c[-1] * (q - k + 1) / (k * (2 * q - k + 1)))

        # Compute U and V for Padé approximant
        I = np.eye(n)
        A2 = A_scaled @ A_scaled

        U = c[1] * I
        V = c[0] * I

        A_power = I
        for k in range(1, q // 2 + 1):
            A_power = A_power @ A2
            U = U + c[2 * k + 1] * A_power
            V = V + c[2 * k] * A_power

        U = A_scaled @ U

        # Padé approximant: exp(A) ≈ (V - U)^(-1) @ (V + U)
        result = np.linalg.solve(V - U, V + U)

        # Undo scaling: exp(A) = exp(A_scaled)^(2^s)
        for _ in range(s):
            result = result @ result

        return result

    def sqrtm(A: np.ndarray, max_iter: int = 50, tol: float = 1e-10) -> np.ndarray:
        """
        Matrix square root using Newton iteration (Denman-Beavers).

        Computes X such that X @ X = A for positive definite matrix A.

        Args:
            A: Square positive definite matrix
            max_iter: Maximum iterations
            tol: Convergence tolerance

        Returns:
            Matrix square root

        Note:
            May not converge for non-positive-definite matrices.
            For production use, install scipy.
        """
        A = np.asarray(A)
        if A.ndim != 2 or A.shape[0] != A.shape[1]:
            raise ValueError("Matrix must be square")

        n = A.shape[0]
        Y = A.copy()
        Z = np.eye(n)

        for i in range(max_iter):
            Y_new = 0.5 * (Y + np.linalg.inv(Z))
            Z_new = 0.5 * (Z + np.linalg.inv(Y))

            if np.linalg.norm(Y_new - Y, ord='fro') < tol:
                return Y_new

            Y, Z = Y_new, Z_new

        warnings.warn(f"sqrtm: Did not converge in {max_iter} iterations")
        return Y

# =============================================================================
# ODE Solver
# =============================================================================

try:
    from scipy.integrate import solve_ivp as _scipy_solve_ivp
    solve_ivp = _scipy_solve_ivp
except ImportError:
    class OdeResult:
        """Container for ODE solution results (scipy-compatible)."""
        def __init__(self, t: np.ndarray, y: np.ndarray, success: bool = True):
            self.t = t
            self.y = y
            self.success = success
            self.message = "Integration successful" if success else "Integration failed"

    def solve_ivp(
        fun: Callable,
        t_span: Tuple[float, float],
        y0: np.ndarray,
        method: str = 'RK45',
        t_eval: Optional[np.ndarray] = None,
        dense_output: bool = False,
        events: Any = None,
        vectorized: bool = False,
        **options
    ) -> OdeResult:
        """
        Solve initial value problem using RK4 method.

        This is a simplified fallback that implements 4th-order Runge-Kutta.

        Args:
            fun: Right-hand side of the ODE: dy/dt = fun(t, y)
            t_span: (t0, tf) integration interval
            y0: Initial state
            method: Ignored (always uses RK4)
            t_eval: Times at which to store solution
            dense_output: Ignored
            events: Ignored
            vectorized: Ignored
            **options: max_step can be specified

        Returns:
            OdeResult with t and y arrays

        Note:
            This is a basic RK4 implementation without adaptive stepping.
            For production use, install scipy.
        """
        y0 = np.asarray(y0)
        t0, tf = t_span

        # Determine step size
        max_step = options.get('max_step', (tf - t0) / 100)
        n_steps = max(int(np.ceil((tf - t0) / max_step)), 10)

        if t_eval is None:
            t_eval = np.linspace(t0, tf, n_steps + 1)

        # Initialize
        t = t0
        y = y0.copy()

        # Check if t_eval starts at t0
        t_eval_array = np.asarray(t_eval)
        if np.isclose(t_eval_array[0], t0):
            # t_eval includes t0, so we can include it in results
            t_values = [t0]
            y_values = [y0.copy()]
            eval_points = t_eval_array[1:]
        else:
            # t_eval doesn't start at t0, compute all points
            t_values = []
            y_values = []
            eval_points = t_eval_array

        for t_next in eval_points:
            # RK4 steps to reach t_next
            while t < t_next:
                h = min(max_step, t_next - t)

                k1 = np.asarray(fun(t, y))
                k2 = np.asarray(fun(t + h/2, y + h*k1/2))
                k3 = np.asarray(fun(t + h/2, y + h*k2/2))
                k4 = np.asarray(fun(t + h, y + h*k3))

                y = y + h * (k1 + 2*k2 + 2*k3 + k4) / 6
                t = t + h

            t_values.append(t)
            y_values.append(y.copy())

        return OdeResult(
            t=np.array(t_values),
            y=np.array(y_values).T,
            success=True
        )

# =============================================================================
# Signal Processing
# =============================================================================

try:
    from scipy.signal import hilbert as _scipy_hilbert
    hilbert = _scipy_hilbert
except ImportError:
    def hilbert(x: np.ndarray, N: Optional[int] = None) -> np.ndarray:
        """
        Compute analytic signal using Hilbert transform.

        The analytic signal has the original signal as real part
        and Hilbert transform as imaginary part.

        Args:
            x: Signal array
            N: FFT length (default: len(x))

        Returns:
            Analytic signal (complex array)
        """
        x = np.asarray(x)
        if N is None:
            N = len(x)

        Xf = np.fft.fft(x, N)

        h = np.zeros(N)
        if N % 2 == 0:
            h[0] = h[N // 2] = 1
            h[1:N // 2] = 2
        else:
            h[0] = 1
            h[1:(N + 1) // 2] = 2

        return np.fft.ifft(Xf * h)

try:
    from scipy.signal import lfilter as _scipy_lfilter
    lfilter = _scipy_lfilter
except ImportError:
    def lfilter(b: np.ndarray, a: np.ndarray, x: np.ndarray) -> np.ndarray:
        """
        Filter data with IIR or FIR filter.

        Implements difference equation:
        a[0]*y[n] = b[0]*x[n] + b[1]*x[n-1] + ... - a[1]*y[n-1] - ...

        Args:
            b: Numerator coefficients
            a: Denominator coefficients
            x: Input signal

        Returns:
            Filtered signal
        """
        b = np.asarray(b)
        a = np.asarray(a)
        x = np.asarray(x)

        # Normalize by a[0]
        b = b / a[0]
        a = a / a[0]

        n = len(x)
        nb = len(b)
        na = len(a)

        y = np.zeros(n)

        for i in range(n):
            # FIR part
            for j in range(min(nb, i + 1)):
                y[i] += b[j] * x[i - j]

            # IIR part
            for j in range(1, min(na, i + 1)):
                y[i] -= a[j] * y[i - j]

        return y

try:
    from scipy.signal import fftconvolve as _scipy_fftconvolve
    fftconvolve = _scipy_fftconvolve
except ImportError:
    def fftconvolve(in1: np.ndarray, in2: np.ndarray, mode: str = 'full') -> np.ndarray:
        """
        Convolve two arrays using FFT.

        Args:
            in1: First input array
            in2: Second input array
            mode: 'full', 'same', or 'valid'

        Returns:
            Convolution result
        """
        in1 = np.asarray(in1)
        in2 = np.asarray(in2)

        n1 = len(in1)
        n2 = len(in2)
        n = n1 + n2 - 1

        # FFT convolution
        fft_size = 2 ** int(np.ceil(np.log2(n)))
        result = np.fft.ifft(np.fft.fft(in1, fft_size) * np.fft.fft(in2, fft_size))
        result = np.real(result[:n])

        if mode == 'full':
            return result
        elif mode == 'same':
            start = (n2 - 1) // 2
            return result[start:start + n1]
        elif mode == 'valid':
            return result[n2 - 1:n1]
        else:
            raise ValueError(f"Unknown mode: {mode}")

# =============================================================================
# Utility
# =============================================================================

def check_scipy_available() -> bool:
    """Check if scipy is available."""
    return SCIPY_AVAILABLE

def require_scipy(feature: str = "this feature"):
    """Raise ImportError if scipy is not available."""
    if not SCIPY_AVAILABLE:
        raise ImportError(
            f"scipy is required for {feature}. "
            "Install with: pip install scipy"
        )
