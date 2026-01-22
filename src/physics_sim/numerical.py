#!/usr/bin/env python3
"""
Numerical Methods Module

Comprehensive numerical methods for physics simulations:
- ODE solvers (Euler, RK4, Verlet, adaptive)
- Root finding (Newton-Raphson, bisection, secant)
- Integration (Simpson, Gaussian quadrature)
- Interpolation (linear, cubic spline)
- Optimization (gradient descent, PSO)
- Linear algebra helpers

All methods designed for physics applications.
"""

import math
from typing import Dict, Any, Tuple, Optional, Callable, List, Union
from dataclasses import dataclass
import random

# =============================================================================
# TYPE ALIASES
# =============================================================================

Vector = List[float]
Matrix = List[List[float]]
ODEFunc = Callable[[float, Vector], Vector]
ScalarFunc = Callable[[float], float]


# =============================================================================
# VECTOR OPERATIONS
# =============================================================================


def vec_add(a: Vector, b: Vector) -> Vector:
    """Add two vectors."""
    return [ai + bi for ai, bi in zip(a, b)]


def vec_sub(a: Vector, b: Vector) -> Vector:
    """Subtract two vectors."""
    return [ai - bi for ai, bi in zip(a, b)]


def vec_scale(a: Vector, s: float) -> Vector:
    """Scale a vector."""
    return [ai * s for ai in a]


def vec_dot(a: Vector, b: Vector) -> float:
    """Dot product of two vectors."""
    return sum(ai * bi for ai, bi in zip(a, b))


def vec_norm(a: Vector) -> float:
    """Euclidean norm of a vector."""
    return math.sqrt(sum(ai**2 for ai in a))


def vec_normalize(a: Vector) -> Vector:
    """Normalize a vector."""
    n = vec_norm(a)
    if n < 1e-15:
        return a
    return vec_scale(a, 1 / n)


def vec_cross_3d(a: Vector, b: Vector) -> Vector:
    """Cross product of two 3D vectors."""
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


# =============================================================================
# ODE SOLVERS
# =============================================================================


def euler_step(f: ODEFunc, t: float, y: Vector, h: float) -> Vector:
    """
    Single Euler step.

    y_{n+1} = y_n + h * f(t_n, y_n)

    Args:
        f: Derivative function f(t, y)
        t: Current time
        y: Current state vector
        h: Step size

    Returns:
        New state vector
    """
    k = f(t, y)
    return vec_add(y, vec_scale(k, h))


def euler_solve(
    f: ODEFunc, y0: Vector, t_span: Tuple[float, float], h: float
) -> Tuple[List[float], List[Vector]]:
    """
    Solve ODE using Euler method.

    Args:
        f: Derivative function f(t, y)
        y0: Initial state
        t_span: (t_start, t_end)
        h: Step size

    Returns:
        Tuple of (time points, state vectors)
    """
    t_start, t_end = t_span
    t = t_start
    y = y0[:]

    times = [t]
    states = [y[:]]

    while t < t_end:
        h_actual = min(h, t_end - t)
        y = euler_step(f, t, y, h_actual)
        t += h_actual
        times.append(t)
        states.append(y[:])

    return times, states


def rk4_step(f: ODEFunc, t: float, y: Vector, h: float) -> Vector:
    """
    Single Runge-Kutta 4th order step.

    k1 = f(t, y)
    k2 = f(t + h/2, y + h*k1/2)
    k3 = f(t + h/2, y + h*k2/2)
    k4 = f(t + h, y + h*k3)
    y_{n+1} = y_n + h*(k1 + 2*k2 + 2*k3 + k4)/6

    Args:
        f: Derivative function f(t, y)
        t: Current time
        y: Current state vector
        h: Step size

    Returns:
        New state vector
    """
    k1 = f(t, y)
    k2 = f(t + h / 2, vec_add(y, vec_scale(k1, h / 2)))
    k3 = f(t + h / 2, vec_add(y, vec_scale(k2, h / 2)))
    k4 = f(t + h, vec_add(y, vec_scale(k3, h)))

    # y + h/6 * (k1 + 2*k2 + 2*k3 + k4)
    weighted = vec_add(vec_add(k1, vec_scale(k2, 2)), vec_add(vec_scale(k3, 2), k4))
    return vec_add(y, vec_scale(weighted, h / 6))


def rk4_solve(
    f: ODEFunc, y0: Vector, t_span: Tuple[float, float], h: float
) -> Tuple[List[float], List[Vector]]:
    """
    Solve ODE using RK4 method.

    Args:
        f: Derivative function f(t, y)
        y0: Initial state
        t_span: (t_start, t_end)
        h: Step size

    Returns:
        Tuple of (time points, state vectors)
    """
    t_start, t_end = t_span
    t = t_start
    y = y0[:]

    times = [t]
    states = [y[:]]

    while t < t_end:
        h_actual = min(h, t_end - t)
        y = rk4_step(f, t, y, h_actual)
        t += h_actual
        times.append(t)
        states.append(y[:])

    return times, states


def rk45_adaptive_step(
    f: ODEFunc, t: float, y: Vector, h: float, tol: float = 1e-6
) -> Tuple[Vector, float, float]:
    """
    Adaptive RK4-5 (Fehlberg) step with error estimation.

    Uses embedded 4th and 5th order methods to estimate error.

    Args:
        f: Derivative function
        t: Current time
        y: Current state
        h: Initial step size guess
        tol: Error tolerance

    Returns:
        Tuple of (new_state, actual_step_used, next_step_suggestion)
    """
    # Fehlberg coefficients
    a2 = 1 / 4
    a3, b31, b32 = 3 / 8, 3 / 32, 9 / 32
    a4, b41, b42, b43 = 12 / 13, 1932 / 2197, -7200 / 2197, 7296 / 2197
    a5, b51, b52, b53, b54 = 1, 439 / 216, -8, 3680 / 513, -845 / 4104
    a6, b61, b62, b63, b64, b65 = 1 / 2, -8 / 27, 2, -3544 / 2565, 1859 / 4104, -11 / 40

    # 4th order coefficients
    c1, c3, c4, c5 = 25 / 216, 1408 / 2565, 2197 / 4104, -1 / 5

    # 5th order coefficients
    d1, d3, d4, d5, d6 = 16 / 135, 6656 / 12825, 28561 / 56430, -9 / 50, 2 / 55

    k1 = f(t, y)
    k2 = f(t + a2 * h, vec_add(y, vec_scale(k1, a2 * h)))
    k3 = f(
        t + a3 * h, vec_add(vec_add(y, vec_scale(k1, b31 * h)), vec_scale(k2, b32 * h))
    )
    k4 = f(
        t + a4 * h,
        vec_add(
            vec_add(vec_add(y, vec_scale(k1, b41 * h)), vec_scale(k2, b42 * h)),
            vec_scale(k3, b43 * h),
        ),
    )
    k5 = f(
        t + a5 * h,
        vec_add(
            vec_add(
                vec_add(vec_add(y, vec_scale(k1, b51 * h)), vec_scale(k2, b52 * h)),
                vec_scale(k3, b53 * h),
            ),
            vec_scale(k4, b54 * h),
        ),
    )
    k6 = f(
        t + a6 * h,
        vec_add(
            vec_add(
                vec_add(
                    vec_add(vec_add(y, vec_scale(k1, b61 * h)), vec_scale(k2, b62 * h)),
                    vec_scale(k3, b63 * h),
                ),
                vec_scale(k4, b64 * h),
            ),
            vec_scale(k5, b65 * h),
        ),
    )

    # 4th order solution
    y4 = vec_add(
        y,
        vec_scale(
            vec_add(
                vec_add(
                    vec_add(vec_scale(k1, c1), vec_scale(k3, c3)), vec_scale(k4, c4)
                ),
                vec_scale(k5, c5),
            ),
            h,
        ),
    )

    # 5th order solution
    y5 = vec_add(
        y,
        vec_scale(
            vec_add(
                vec_add(
                    vec_add(
                        vec_add(vec_scale(k1, d1), vec_scale(k3, d3)), vec_scale(k4, d4)
                    ),
                    vec_scale(k5, d5),
                ),
                vec_scale(k6, d6),
            ),
            h,
        ),
    )

    # Error estimate
    error = vec_norm(vec_sub(y5, y4))

    # Adaptive step size
    if error < 1e-15:
        h_new = h * 2
    else:
        h_new = h * min(2, max(0.1, 0.9 * (tol / error) ** 0.2))

    return y5, h, h_new


def verlet_step(
    x: Vector, v: Vector, a_func: Callable[[Vector], Vector], h: float
) -> Tuple[Vector, Vector]:
    """
    Velocity Verlet integration step (for position-dependent forces).

    x_{n+1} = x_n + v_n*h + a(x_n)*h²/2
    a_{n+1} = a(x_{n+1})
    v_{n+1} = v_n + (a_n + a_{n+1})*h/2

    Args:
        x: Current position
        v: Current velocity
        a_func: Acceleration function a(x)
        h: Time step

    Returns:
        Tuple of (new_position, new_velocity)
    """
    a = a_func(x)

    # Update position
    x_new = vec_add(vec_add(x, vec_scale(v, h)), vec_scale(a, h**2 / 2))

    # Calculate new acceleration
    a_new = a_func(x_new)

    # Update velocity
    v_new = vec_add(v, vec_scale(vec_add(a, a_new), h / 2))

    return x_new, v_new


def leapfrog_step(
    x: Vector, v: Vector, a_func: Callable[[Vector], Vector], h: float
) -> Tuple[Vector, Vector]:
    """
    Leapfrog integration step.

    v_{n+1/2} = v_n + a(x_n)*h/2
    x_{n+1} = x_n + v_{n+1/2}*h
    v_{n+1} = v_{n+1/2} + a(x_{n+1})*h/2

    Args:
        x: Current position
        v: Current velocity
        a_func: Acceleration function a(x)
        h: Time step

    Returns:
        Tuple of (new_position, new_velocity)
    """
    a = a_func(x)

    # Half velocity update
    v_half = vec_add(v, vec_scale(a, h / 2))

    # Full position update
    x_new = vec_add(x, vec_scale(v_half, h))

    # Calculate new acceleration
    a_new = a_func(x_new)

    # Remaining half velocity update
    v_new = vec_add(v_half, vec_scale(a_new, h / 2))

    return x_new, v_new


# =============================================================================
# ROOT FINDING
# =============================================================================


def bisection(
    f: ScalarFunc, a: float, b: float, tol: float = 1e-10, max_iter: int = 100
) -> Tuple[float, int]:
    """
    Find root using bisection method.

    Args:
        f: Function to find root of
        a, b: Bracket endpoints (f(a) and f(b) must have opposite signs)
        tol: Tolerance for convergence
        max_iter: Maximum iterations

    Returns:
        Tuple of (root, iterations)
    """
    fa, fb = f(a), f(b)

    if fa * fb > 0:
        raise ValueError("f(a) and f(b) must have opposite signs")

    for i in range(max_iter):
        c = (a + b) / 2
        fc = f(c)

        if abs(fc) < tol or (b - a) / 2 < tol:
            return c, i + 1

        if fa * fc < 0:
            b = c
            fb = fc
        else:
            a = c
            fa = fc

    return (a + b) / 2, max_iter


def newton_raphson(
    f: ScalarFunc, df: ScalarFunc, x0: float, tol: float = 1e-10, max_iter: int = 100
) -> Tuple[float, int]:
    """
    Find root using Newton-Raphson method.

    x_{n+1} = x_n - f(x_n) / f'(x_n)

    Args:
        f: Function to find root of
        df: Derivative of f
        x0: Initial guess
        tol: Tolerance for convergence
        max_iter: Maximum iterations

    Returns:
        Tuple of (root, iterations)
    """
    x = x0

    for i in range(max_iter):
        fx = f(x)
        dfx = df(x)

        if abs(dfx) < 1e-15:
            raise ValueError("Derivative too small")

        x_new = x - fx / dfx

        if abs(x_new - x) < tol:
            return x_new, i + 1

        x = x_new

    return x, max_iter


def secant_method(
    f: ScalarFunc, x0: float, x1: float, tol: float = 1e-10, max_iter: int = 100
) -> Tuple[float, int]:
    """
    Find root using secant method (derivative-free).

    x_{n+1} = x_n - f(x_n) * (x_n - x_{n-1}) / (f(x_n) - f(x_{n-1}))

    Args:
        f: Function to find root of
        x0, x1: Initial guesses
        tol: Tolerance
        max_iter: Maximum iterations

    Returns:
        Tuple of (root, iterations)
    """
    f0, f1 = f(x0), f(x1)

    for i in range(max_iter):
        if abs(f1 - f0) < 1e-15:
            break

        x2 = x1 - f1 * (x1 - x0) / (f1 - f0)

        if abs(x2 - x1) < tol:
            return x2, i + 1

        x0, x1 = x1, x2
        f0, f1 = f1, f(x2)

    return x1, max_iter


# =============================================================================
# NUMERICAL INTEGRATION
# =============================================================================


def simpson_rule(f: ScalarFunc, a: float, b: float, n: int = 100) -> float:
    """
    Integrate using Simpson's rule.

    ∫f(x)dx ≈ (h/3) * [f(a) + 4f(a+h) + 2f(a+2h) + ... + f(b)]

    Args:
        f: Function to integrate
        a, b: Integration limits
        n: Number of subintervals (must be even)

    Returns:
        Approximate integral
    """
    if n % 2 == 1:
        n += 1

    h = (b - a) / n
    total = f(a) + f(b)

    for i in range(1, n):
        x = a + i * h
        if i % 2 == 0:
            total += 2 * f(x)
        else:
            total += 4 * f(x)

    return total * h / 3


def trapezoid_rule(f: ScalarFunc, a: float, b: float, n: int = 100) -> float:
    """
    Integrate using trapezoidal rule.

    ∫f(x)dx ≈ (h/2) * [f(a) + 2f(a+h) + 2f(a+2h) + ... + f(b)]

    Args:
        f: Function to integrate
        a, b: Integration limits
        n: Number of subintervals

    Returns:
        Approximate integral
    """
    h = (b - a) / n
    total = (f(a) + f(b)) / 2

    for i in range(1, n):
        total += f(a + i * h)

    return total * h


def gauss_legendre_5(f: ScalarFunc, a: float, b: float) -> float:
    """
    5-point Gaussian quadrature.

    Args:
        f: Function to integrate
        a, b: Integration limits

    Returns:
        Approximate integral
    """
    # Gauss-Legendre nodes and weights for 5 points
    nodes = [0, -0.5384693101, 0.5384693101, -0.9061798459, 0.9061798459]
    weights = [0.5688888889, 0.4786286705, 0.4786286705, 0.2369268851, 0.2369268851]

    # Transform from [-1, 1] to [a, b]
    mid = (b + a) / 2
    half_width = (b - a) / 2

    total = 0
    for node, weight in zip(nodes, weights):
        x = mid + half_width * node
        total += weight * f(x)

    return total * half_width


def adaptive_simpson(f: ScalarFunc, a: float, b: float, tol: float = 1e-8) -> float:
    """
    Adaptive Simpson's rule integration.

    Args:
        f: Function to integrate
        a, b: Integration limits
        tol: Error tolerance

    Returns:
        Approximate integral
    """

    def _simpson(fa, fb, fc, a, b):
        return (b - a) / 6 * (fa + 4 * fc + fb)

    def _adaptive(a, b, fa, fb, fc, S, tol):
        c = (a + b) / 2
        d = (a + c) / 2
        e = (c + b) / 2
        fd = f(d)
        fe = f(e)

        S_left = _simpson(fa, fc, fd, a, c)
        S_right = _simpson(fc, fb, fe, c, b)
        S_total = S_left + S_right

        if abs(S_total - S) < 15 * tol:
            return S_total + (S_total - S) / 15  # Richardson extrapolation
        else:
            return _adaptive(a, c, fa, fc, fd, S_left, tol / 2) + _adaptive(
                c, b, fc, fb, fe, S_right, tol / 2
            )

    fa = f(a)
    fb = f(b)
    fc = f((a + b) / 2)
    S = _simpson(fa, fb, fc, a, b)

    return _adaptive(a, b, fa, fb, fc, S, tol)


# =============================================================================
# INTERPOLATION
# =============================================================================


def linear_interpolate(x: float, x_data: List[float], y_data: List[float]) -> float:
    """
    Linear interpolation.

    Args:
        x: Point to interpolate at
        x_data: Known x values (sorted)
        y_data: Known y values

    Returns:
        Interpolated y value
    """
    # Find bracketing indices
    for i in range(len(x_data) - 1):
        if x_data[i] <= x <= x_data[i + 1]:
            t = (x - x_data[i]) / (x_data[i + 1] - x_data[i])
            return y_data[i] + t * (y_data[i + 1] - y_data[i])

    # Extrapolation
    if x < x_data[0]:
        return y_data[0]
    return y_data[-1]


def cubic_spline_coefficients(
    x_data: List[float], y_data: List[float]
) -> List[Tuple[float, ...]]:
    """
    Calculate natural cubic spline coefficients.

    Args:
        x_data: Known x values (sorted)
        y_data: Known y values

    Returns:
        List of (a, b, c, d) coefficients for each interval
    """
    n = len(x_data) - 1
    h = [x_data[i + 1] - x_data[i] for i in range(n)]

    # Solve tridiagonal system for second derivatives
    # Natural spline: second derivatives at endpoints are zero

    # Build tridiagonal matrix equation
    alpha = [0.0] * (n + 1)
    for i in range(1, n):
        alpha[i] = 3 / h[i] * (y_data[i + 1] - y_data[i]) - 3 / h[i - 1] * (
            y_data[i] - y_data[i - 1]
        )

    l = [1.0] + [0.0] * n
    mu = [0.0] * (n + 1)
    z = [0.0] * (n + 1)

    for i in range(1, n):
        l[i] = 2 * (x_data[i + 1] - x_data[i - 1]) - h[i - 1] * mu[i - 1]
        mu[i] = h[i] / l[i]
        z[i] = (alpha[i] - h[i - 1] * z[i - 1]) / l[i]

    l[n] = 1.0
    z[n] = 0.0
    c = [0.0] * (n + 1)

    for j in range(n - 1, -1, -1):
        c[j] = z[j] - mu[j] * c[j + 1]

    # Calculate coefficients
    coeffs = []
    for i in range(n):
        a = y_data[i]
        b = (y_data[i + 1] - y_data[i]) / h[i] - h[i] * (c[i + 1] + 2 * c[i]) / 3
        d = (c[i + 1] - c[i]) / (3 * h[i])
        coeffs.append((a, b, c[i], d, x_data[i]))

    return coeffs


def cubic_spline_interpolate(
    x: float, x_data: List[float], coeffs: List[Tuple[float, ...]]
) -> float:
    """
    Evaluate cubic spline at point.

    Args:
        x: Point to interpolate at
        x_data: Original x data
        coeffs: Spline coefficients from cubic_spline_coefficients

    Returns:
        Interpolated y value
    """
    # Find interval
    for i, (a, b, c, d, x0) in enumerate(coeffs):
        x_upper = x_data[i + 1] if i < len(coeffs) - 1 else float("inf")
        if x0 <= x <= x_upper or i == len(coeffs) - 1:
            dx = x - x0
            return a + b * dx + c * dx**2 + d * dx**3

    # Use first interval for extrapolation below
    a, b, c, d, x0 = coeffs[0]
    dx = x - x0
    return a + b * dx + c * dx**2 + d * dx**3


# =============================================================================
# OPTIMIZATION
# =============================================================================


def gradient_descent(
    f: Callable[[Vector], float],
    grad_f: Callable[[Vector], Vector],
    x0: Vector,
    learning_rate: float = 0.01,
    tol: float = 1e-8,
    max_iter: int = 10000,
) -> Tuple[Vector, float, int]:
    """
    Gradient descent optimization.

    Args:
        f: Objective function to minimize
        grad_f: Gradient of f
        x0: Initial guess
        learning_rate: Step size
        tol: Convergence tolerance
        max_iter: Maximum iterations

    Returns:
        Tuple of (optimal_x, optimal_f, iterations)
    """
    x = x0[:]

    for i in range(max_iter):
        grad = grad_f(x)

        # Update
        x_new = vec_sub(x, vec_scale(grad, learning_rate))

        # Check convergence
        if vec_norm(vec_sub(x_new, x)) < tol:
            return x_new, f(x_new), i + 1

        x = x_new

    return x, f(x), max_iter


def particle_swarm_optimization(
    f: Callable[[Vector], float],
    bounds: List[Tuple[float, float]],
    n_particles: int = 30,
    max_iter: int = 100,
    w: float = 0.7,
    c1: float = 1.5,
    c2: float = 1.5,
) -> Tuple[Vector, float, int]:
    """
    Particle Swarm Optimization (PSO).

    Args:
        f: Objective function to minimize
        bounds: List of (min, max) for each dimension
        n_particles: Number of particles
        max_iter: Maximum iterations
        w: Inertia weight
        c1: Cognitive coefficient
        c2: Social coefficient

    Returns:
        Tuple of (best_position, best_value, iterations)
    """
    dim = len(bounds)

    # Initialize particles
    particles = []
    velocities = []
    personal_best_pos = []
    personal_best_val = []

    for _ in range(n_particles):
        pos = [random.uniform(lo, hi) for lo, hi in bounds]
        vel = [(hi - lo) * (random.random() - 0.5) * 0.1 for lo, hi in bounds]
        particles.append(pos)
        velocities.append(vel)
        personal_best_pos.append(pos[:])
        personal_best_val.append(f(pos))

    # Global best
    global_best_idx = min(range(n_particles), key=lambda i: personal_best_val[i])
    global_best_pos = personal_best_pos[global_best_idx][:]
    global_best_val = personal_best_val[global_best_idx]

    # Main loop
    for iteration in range(max_iter):
        for i in range(n_particles):
            pos = particles[i]
            vel = velocities[i]

            # Update velocity
            for d in range(dim):
                r1, r2 = random.random(), random.random()
                cognitive = c1 * r1 * (personal_best_pos[i][d] - pos[d])
                social = c2 * r2 * (global_best_pos[d] - pos[d])
                vel[d] = w * vel[d] + cognitive + social

            # Update position
            for d in range(dim):
                pos[d] += vel[d]
                # Clamp to bounds
                pos[d] = max(bounds[d][0], min(bounds[d][1], pos[d]))

            # Evaluate
            val = f(pos)

            # Update personal best
            if val < personal_best_val[i]:
                personal_best_val[i] = val
                personal_best_pos[i] = pos[:]

                # Update global best
                if val < global_best_val:
                    global_best_val = val
                    global_best_pos = pos[:]

    return global_best_pos, global_best_val, max_iter


def golden_section_search(
    f: ScalarFunc, a: float, b: float, tol: float = 1e-8
) -> Tuple[float, float, int]:
    """
    Golden section search for 1D optimization.

    Args:
        f: Function to minimize
        a, b: Search interval
        tol: Tolerance

    Returns:
        Tuple of (optimal_x, optimal_f, iterations)
    """
    phi = (1 + math.sqrt(5)) / 2  # Golden ratio
    resp = phi - 1

    x1 = b - resp * (b - a)
    x2 = a + resp * (b - a)
    f1, f2 = f(x1), f(x2)

    iteration = 0
    while abs(b - a) > tol:
        iteration += 1

        if f1 < f2:
            b = x2
            x2 = x1
            f2 = f1
            x1 = b - resp * (b - a)
            f1 = f(x1)
        else:
            a = x1
            x1 = x2
            f1 = f2
            x2 = a + resp * (b - a)
            f2 = f(x2)

    x_opt = (a + b) / 2
    return x_opt, f(x_opt), iteration


# =============================================================================
# COMPREHENSIVE NUMERICAL METHODS
# =============================================================================


def numerical_methods(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Demonstrate numerical methods.

    Args:
        params: Dictionary specifying method and parameters

    Returns:
        Results dictionary
    """
    results = {}
    method = params.get("method", "rk4")

    if method == "root_finding":
        # Example: find root of x² - 2 (i.e., √2)
        f = lambda x: x**2 - 2
        df = lambda x: 2 * x

        root, iters = bisection(f, 1, 2)
        results["bisection_root"] = root
        results["bisection_iterations"] = iters

        root, iters = newton_raphson(f, df, 1.5)
        results["newton_root"] = root
        results["newton_iterations"] = iters

    elif method == "integration":
        # Example: integrate sin(x) from 0 to π (should be 2)
        import math

        f = math.sin

        results["simpson"] = simpson_rule(f, 0, math.pi, n=100)
        results["trapezoid"] = trapezoid_rule(f, 0, math.pi, n=100)
        results["gauss_5pt"] = gauss_legendre_5(f, 0, math.pi)
        results["exact"] = 2.0

    elif method == "ode_harmonic":
        # Simple harmonic oscillator: x'' = -ω²x
        # State: [x, v], derivatives: [v, -ω²x]
        omega = params.get("omega", 1.0)
        f = lambda t, y: [y[1], -(omega**2) * y[0]]

        y0 = [1.0, 0.0]  # x=1, v=0
        t_span = (0, 2 * math.pi / omega)  # One period
        h = 0.01

        times, states = rk4_solve(f, y0, t_span, h)

        # Final state should be close to initial
        results["initial_state"] = y0
        results["final_state"] = states[-1]
        results["num_steps"] = len(times)
        results["final_error"] = vec_norm(vec_sub(states[-1], y0))

    return results
