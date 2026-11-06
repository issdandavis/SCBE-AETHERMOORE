# Condensed Boundary Density — working mathematical specification

This is a falsifiable working model for Issac Davis's proposal. It is not a claim
that the combination is novel or that it improves a neural network.

## 1. Boundary cells become nodes

Let (X_k) be the finite set of oriented (k)-cells and

\[
B_k:C_k(X)\rightarrow C_{k-1}(X),\qquad B_kB_{k+1}=0.
\]

CBD uses the barycentric or Hasse lift: every cell in every (X_k) becomes a
node. A path exists between two lifted nodes when one occurs in the boundary of
the other, or when a declared typed sibling map joins them across model layers.
The sign of an incidence is retained as connection phase (0) or (pi).

Each lifted cell (c) carries

\[
(d_c,\ell_c,s_c,m_c,a_c,\theta_c,\omega_c,\tau_c),
\]

where (d) is topological dimension, (ell) is model layer, (s) is a stable
concept seed, (m>0) is density or mass, (a e^{i\theta}) is complex state,
(omega) is intrinsic frequency, and (	au\in\{-1,0,+1\}^r) is MultiSign state.

## 2. Energy and dimensional flow

Ordinary within-dimension topology uses the Hodge operator

\[
L_k=B_k^*B_k+B_{k+1}B_{k+1}^*.
\]

For a typed connection (i\rightarrow j) with weight (w_{ij}>0) and transport
(T_{ij}=e^{i\phi_{ij}}), the connection energy is

\[
E(z)=\frac12\sum_{(i,j)}w_{ij}|z_j-T_{ij}z_i|^2
     =\frac12 z^*\mathcal L z.
\]

(mathcal L) is Hermitian positive semidefinite. Sibling transport is legal only
when both endpoints share (s_c), unless the edge is explicitly marked as a
comparison or contradiction. This gives cross-layer concepts a typed sheaf-like
binding rather than concatenating their coordinates.

## 3. Condensed poly-nodal state

For cluster (C), define total mass, effective population, and phase coherence:

\[
M_C=\sum_{i\in C}m_i,\qquad
N_{\mathrm{eff}}=\frac{M_C^2}{\sum_{i\in C}m_i^2},\qquad
R_C=\frac{|\sum_{i\in C}m_i z_i|}{\sum_{i\in C}m_i|z_i|}.
\]

Let (W_{in}) be coupling inside (C), (W_{cut}) its coupling to surrounding
cells, and (Q_C=e^{-\epsilon_C}(1-v_C/e_C)) the sibling consistency from
normalized restriction residual (epsilon_C), violations (v_C), and sibling
edge count (e_C). The preregisterable diagnostic is

\[
\chi_C=R_C\frac{W_{in}}{W_{in}+W_{cut}}
       \left(1-\frac1{N_{\mathrm{eff}}}\right)Q_C.
\]

(chi_C=0) for a singleton. It rises only when several cells act coherently,
retain internal coupling, and respect cross-layer bindings. Its threshold and
persistence window must be selected on development data and frozen before the
holdout. Calling a cluster "condensed" without that gate is rhetoric.

## 4. Clumps as weighted meta-nodes

Let (P\in\{0,1\}^{n\times q}) lift (q) cluster values to their member cells.
Galerkin coarsening gives

\[
\mathcal L_C=P^*\mathcal LP,\qquad M_C=P^*MP,
\]

where (M=\operatorname{diag}(m_1,\ldots,m_n)). For every cluster-constant state
(y), energy is exactly preserved:

\[
y^*\mathcal L_Cy=(Py)^*\mathcal L(Py).
\]

The natural clump frequencies solve the blanket or trampoline equation

\[
\mathcal L_Cu_r=\omega_r^2M_Cu_r.
\]

Thus cluster weight and frequency are coupled without inventing extra dimensions:
holding stiffness fixed while multiplying mass by four divides every nonzero
frequency by two.

## 5. Traceable dynamics

The first implementation keeps an audited linear transport core:

\[
z^{t+1}=D_{\omega}(\Delta t)
  (I-\eta\mathcal L)z^t+u^t,
\qquad
D_{\omega}=\operatorname{diag}(e^{i\omega_c\Delta t}).
\]

For real readout (y=\Re(r^*z^{t+1})), source-cell contribution is

\[
q_j=\Re\left(r^*A_{:,j}z_j^t\right),\qquad
y=\sum_jq_j+\Re(r^*u^t).
\]

The implementation refuses a result if this ledger does not reconstruct the
output within tolerance. A later nonlinear shell may use Jacobian or integrated
path attribution, but it cannot replace this exact transport receipt with an
unverified explanation.

## 6. Repeated wafer fabric, stated without the hardware metaphor

The Quine Wafer intent is a recurrent compute fabric, not merely an embedding.
Each leaf cell has a stable address, fixed candidate neighbors, a bounded message
interface, state, and a repeated update contract. A minimal neural form is

\[
h_i^{t+1}=h_i^t+f_\theta\!\left(h_i^t,x_i,
 \sum_{j\in\mathcal N(i)}g_\psi(h_i^t,h_j^t,a_i,a_j)m_{ji}^t\right)
 +\Delta_{\sigma(i)}(h_i^t),
\]

where every cell shares the base rule \(f_\theta\), the candidate graph
\(\mathcal N\) stays fixed and auditable, and a sector residual \(\Delta\) is
optional and separately identified. Dynamic gates may weight declared routes;
they may not silently create an unbounded graph. The first test must specify
synchronous, asynchronous, or alternating-block updates before training.

The same interface is retained after condensation. A cluster becomes a meta-cell
through a restriction/prolongation pair, and multiple lifts compose:

\[
P_{0\to r}=P_{0\to1}P_{1\to2}\cdots P_{r-1\to r},\qquad
L_r=P_{0\to r}^*L_0P_{0\to r}.
\]

The implementation verifies this recursion and preserves the exact fine-scale
lineage of every meta-cell. This is the concrete version of leaf cell -> clump ->
larger wafer cell.

The word "quine" needs four separate gates:

1. **Q0 record replay:** the same template and inputs reproduce the same record.
2. **Q1 architectural self-description:** a manifest reconstructs addresses,
   interfaces, rule hashes, children, and routes.
3. **Q2 functional reproduction:** an extracted or copied cell reproduces its
   declared input/output behavior under held-out interventions.
4. **Q3 developmental reproduction:** local rules grow or repair an equivalent
   working fabric after damage.

The current variable-injection quine demonstrates Q0. The new
RepeatedCellContract provides a checkable piece of Q1. Neither is Q2 or Q3.
The phase-conjugate loss is a convergence mechanism, not proof of reproduction.

The current wafer_core.py also needs precise classification: WaferBlock routes
into 64 independently parameterized OpcodeExpert modules. It is a sparse
mixture-of-experts layer with fixed coordinate features. It does not yet apply
one recurrent local rule across 64 communicating cells, so it is not the
intended neural cellular wafer by itself. That implementation can remain as a
matched specialist baseline or provide sector residuals around a shared cell
rule.

Physical GPU-wafer manufacture is a later compilation target. The software
contract can map to packets, local SRAM, routing tables, DMA, and tile kernels,
but no speed, energy, fabrication, or xGeMM claim follows until equal-work
hardware benchmarks exist.

## 7. What would count as neural evidence

The hypothesis is that seeded, typed, frequency-bearing cluster state improves
task behavior and policy traceability. It passes only if it beats both the
unchanged parent and an equal-parameter ordinary graph layer, across at least
three matched seeds by the predeclared uncertainty rule. It must also lose its
advantage under stable-ID shuffling, show component necessity by ablation, and
show that removing top traced cells changes the claimed output more than removing
random or magnitude-matched cells.

The current Wafer result does not pass that bar: all measured 33×2310 Jacobians
were full row rank, but the desired external effect passed only one of twelve
gates. That supports measurable internal geometry and rejects a current gain
claim.

The comparison must include both the existing independent-expert WaferBlock and
a truly shared recurrent-cell implementation. Otherwise a gain cannot be
attributed to the wafer topology rather than extra private expert capacity.

## 8. Relation to established mathematics

CBD combines known tools rather than renaming them: Hodge operators and
simplicial convolutions, cellular-sheaf restrictions, Hermitian connection
Laplacians, generalized mass/stiffness modes, graph coarse-graining, and coupled
oscillatory dynamics. Relevant primary references include:

- [Simplicial Convolutional Neural Networks](https://arxiv.org/abs/2110.02585)
- [Sheaf Neural Networks](https://arxiv.org/abs/2012.06333)
- [Neural Sheaf Diffusion](https://arxiv.org/abs/2202.04579)
- [KuramotoGNN](https://arxiv.org/abs/2311.03260)
- [Stability of Graph Scattering Transforms](https://arxiv.org/abs/1906.04784)
- [Spectral Properties of Hypergraph Laplacian](https://arxiv.org/abs/1605.01483)

The system-specific proposition is their composition around stable seeded
concept cells, MultiSign state, cluster condensation, and mandatory provenance.
That proposition remains **MODEL GAIN UNTESTED**.
