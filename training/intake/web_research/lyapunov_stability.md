# Lyapunov Stability

Lyapunov stability describes how dynamical systems behave near equilibrium points. The theory, developed by Aleksandr Lyapunov and published in 1892, provides methods to analyze whether solutions of differential equations remain close to or converge toward equilibrium states without requiring explicit solutions.

## Types of Stability

Lyapunov stability means solutions starting within distance δ of equilibrium remain within distance ε for all future time, regardless of how small ε is chosen. Asymptotic stability means the equilibrium is both Lyapunov stable AND solutions converge to it as time approaches infinity — combining stability with attractiveness. Exponential stability guarantees a minimum convergence rate: ||x(t) - x_e|| ≤ α||x(0) - x_e||e^(-βt), providing quantitative convergence bounds.

## Lyapunov Functions (Second Method)

Lyapunov's second method avoids solving differential equations explicitly. It uses a Lyapunov function V(x) analogous to system energy. Requirements: V(x) = 0 only at equilibrium, V(x) > 0 elsewhere, V̇(x) ≤ 0 along trajectories. If such a function exists, stability is guaranteed without explicit solutions. If V̇(x) < 0 (strictly negative), the equilibrium is asymptotically stable.

## Linear Systems Stability

For linear systems ẋ = Ax, the system is asymptotically stable when all eigenvalues of matrix A have strictly negative real parts. This connects algebraic spectral properties directly to dynamical stability.

## Time-Varying Systems

For non-autonomous systems where dynamics depend explicitly on time, Barbalat's Lemma provides a key tool: if a function has finite limits and bounded derivatives, its derivative approaches zero. This enables stability proofs for time-dependent systems where classical methods fail.

## LaSalle's Invariance Principle

For autonomous systems, LaSalle's invariance principle extends Lyapunov stability. If V̇(x) ≤ 0 in a compact region, solutions converge to the largest invariant set where V̇(x) = 0. This allows proving asymptotic stability even when V̇ is only negative semidefinite.

## Applications

Aerospace guidance systems used Lyapunov analysis critically during the Cold War when nonlinear control systems required stability verification. Control engineering uses it to determine if feedback systems remain stable under perturbations. Biological systems use it for population dynamics with environmental variation. Traffic flow equilibrium analysis and network stability also rely on Lyapunov methods. Unlike linearization which only indicates local behavior, Lyapunov's approach provides global stability analysis capabilities.
