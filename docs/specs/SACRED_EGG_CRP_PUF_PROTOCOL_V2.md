# Sacred Egg CRP-PUF Protocol V2

**Status:** executable measurement protocol; physical security remains unmeasured.
**Implementation:** `scripts/experiments/sacred_egg_crp_puf_protocol.py`
**Tests:** `tests/experiments/test_sacred_egg_crp_puf_protocol.py`

## Evidence boundary

This protocol closes a measurement error in the exploratory CRP harness. The
older harness learned thresholds from every row and then scored those same
rows. V2 establishes an explicit time boundary:

1. enrollment rows alone determine thresholds, stable-bit masks, templates,
   and error radii;
2. verification rows cannot modify the model;
3. held-out genuine, wrong-device, and wrong-challenge attempts are measured
   separately;
4. a fresh nonce selects a registered challenge through a domain-separated
   hash with rejection sampling;
5. the report carries hashes and aggregate measurements, not raw responses or
   template bits.

A green result proves separation for one captured dataset. It does not prove
physical unclonability, joint entropy, resistance to modeling attacks, or a
production authenticator. The raw deterministic seeded-topology proposal
remains disconfirmed as a standalone PUF under the existing surrogate model.

## Enrollment equations

Let `x_(d,c,r,j)` be feature `j` from device `d`, challenge `c`, enrollment
read `r`. First compute one center per device/challenge group:

```text
m_(d,c,j) = median_r x_(d,c,r,j)
```

The global threshold for feature `j` is the median of group centers:

```text
tau_j = median_(d,c) m_(d,c,j)
```

Using one center per group prevents a heavily sampled device from pulling the
threshold toward itself. Quantization is then

```text
q_j(x) = 1[x_j >= tau_j].
```

For one device/challenge group, let `p_(d,c,j)` be the fraction of enrollment
reads for which `q_j = 1`. Given reliability floor `rho`, retain

```text
S_(d,c) = {j : max(p_(d,c,j), 1 - p_(d,c,j)) >= rho}.
```

The template bit is the majority value on each retained feature:

```text
t_(d,c,j) = 1[p_(d,c,j) >= 1/2],  j in S_(d,c).
```

The enrolled error radius is the worst observed enrollment error plus an
explicit operator margin `m`:

```text
r_(d,c) = max_r sum_(j in S_(d,c)) 1[q_j(x_(d,c,r)) != t_(d,c,j)] + m.
```

The code rejects any template whose radius consumes all of its retained bits.

## Verification equations

For a response `y` to the verifier-selected challenge `c`, the error is

```text
e(y; d,c) = sum_(j in S_(d,c)) 1[q_j(y) != t_(d,c,j)].
```

The measurement passes only when the challenge identity is correct and

```text
e(y; d,c) <= r_(d,c).
```

For devices `d != d'` enrolled under the same challenge, V2 computes a
conservative enrollment margin over shared stable positions:

```text
Delta_c(d,d') = d_H(t_(d,c), t_(d',c)) - r_(d,c) - r_(d',c).
Delta_min       = min_(c,d!=d') Delta_c(d,d').
```

The mechanical gate requires `Delta_min > 0`, enough retained bits, an
acceptable held-out false-reject rate, zero observed wrong-device accepts, and
zero observed wrong-challenge accepts. Zero observed accepts is evidence about
the finite test set only; a confidence bound still requires enough independent
trials.

## Challenge selection and replay

For `N` sorted registered challenges, V2 repeatedly computes

```text
h_k = SHA256(domain || len(seed) || seed || len(nonce) || nonce || k).
L   = 2^256 - (2^256 mod N).
```

The first integer `h_k < L` selects challenge `h_k mod N`. Rejecting values at
or above `L` removes modulo bias. The receipt contains hashes of the nonce and
selector seed, the selected challenge, the digest, and the rejection counter.
A verifier-owned replay guard admits a `(verifier, nonce)` pair once.

Challenge selection is an auditable scheduler. It is not authentication. A
successful physical measurement must still be bound to a standard
cryptographic authenticator and authorization decision.

## Three physical control models

The following physics gives useful control structure. It does not turn this
Python protocol into a plasma, primate, or insect simulation.

### 1. Magnetic reconnection: localize topology changes

In ideal magnetohydrodynamics, magnetic flux is frozen into the moving plasma:

```text
E + v x B = 0.
```

Field-line connectivity can change in a localized diffusion region where the
ideal condition fails. In a steady two-dimensional approximation,

```text
E_rec ~= v_in B_in ~= v_out B_out,
R     = v_in / v_A,
```

where `R` is the normalized reconnection rate. Space-plasma measurements and
theory commonly place fast collisionless reconnection around order `10^-1`,
with event-to-event variation. In a general three-dimensional treatment, a
nonzero parallel potential drop is a reconnection signature:

```text
Phi_parallel = integral E_parallel ds != 0.
```

Magnetic helicity is one measure of linkage or twist in an appropriate closed
domain:

```text
H = integral_V A . B dV,       B = curl A.
```

Boundary terms and gauge choice matter for open domains, where relative
helicity is used. “Field-line collapse” is therefore too vague for an
implementation rule. The precise rule is: preserve connectivity under the
ordinary flow, permit connectivity changes only inside a declared transition
region, and record the flux or invariant that crossed it.

For this protocol, the corresponding rule is that an enrolled model is frozen
during verification. Re-enrollment is an explicit reconnection event that
creates a new model digest; verification data never silently reshape the old
model.

### 2. Brachiation: smooth swing plus discrete handoff

A first approximation to continuous-contact brachiation is a driven pendulum:

```text
m l^2 theta_ddot + b theta_dot + m g l sin(theta) = tau.
```

Without actuation and damping, mechanical energy is

```text
E = 1/2 m l^2 theta_dot^2 + m g l (1 - cos(theta)).
```

Slow gibbon brachiation exhibits pendulum-like exchange between gravitational
potential and translational kinetic energy. Fast ricochetal brachiation also
exchanges translational and rotational energy. Release timing, limb length,
body configuration, and the next handhold alter the handoff.

A multi-link model has the standard manipulator form

```text
M(q) q_ddot + C(q,q_dot) q_dot + g(q) = B u.
```

Grasp and release make the complete system hybrid. Between contacts,

```text
x_dot = f_s(x,u),
```

and at a contact guard `g_h(x)=0`,

```text
x_plus = R_h(x_minus).
```

The protocol uses the same division: quantization and comparison are the
continuous swing; fresh-nonce challenge selection is the handoff; a receipt
records the pre-state, selected branch, and post-state. A long route is valid
only if each handoff closes locally.

### 3. Metamorphosis: preserve organizers while changing form

Butterfly and moth metamorphosis is a staged developmental program, not a
single geometric interpolation. Juvenile hormone and ecdysteroid timing help
control larval molts, pupal commitment, and differentiation. Imaginal tissues
and developmental organizers persist and elaborate while many larval tissues
are remodeled. The animal is not accurately described as dissolving entirely
and being reconstructed from nothing.

After emergence, insect wing deployment provides a measured mechanical example
of stable expansion. Pressure-driven hemolymph flow unfolds a compact wing;
material and geometric nonlinearities create an operating region governed in
part by the dimensionless pressure-to-stiffness ratio

```text
Pi = P / E,
```

where `P` is internal pressure and `E` is an effective elastic modulus. The
wing combines unfolding, cell flattening, cuticle unwrinkling, strain
stiffening, and pillar constraints.

For an engineered stage transform, define an idempotent projector `P_A` onto
the anchor subspace (`P_A^2 = P_A`) and a stage-specific transform `F_s`:

```text
x_(k+1) = P_A x_k + (I - P_A) F_s(x_k).
```

Then

```text
P_A x_(k+1) = P_A x_k,
```

so anchors remain invariant while the complementary state can reorganize. This
projector equation is our engineering model, not a biological law. In the CRP
protocol, the feature schema, device/challenge identity, model digest, and
enroll/verify boundary are anchors; thresholds and templates may change only
through a new enrollment stage.

## Unified hybrid field model

The three patterns combine as

```text
continuous flow:       x_dot = f_s(x,u),        x not in D
declared transition:   x_plus = R_e(x_minus),   x in D and guard_e(x)=0
anchor invariant:      P_A x_plus = P_A x_minus
receipt invariant:     hash(previous, event, next, model) is recorded
```

`D` is the explicit transition region. Reconnection explains why topology
changes belong there; brachiation explains why a long path is a sequence of
locally verified handoffs; metamorphosis explains how the representation can
change while selected organizers remain fixed.

## Command

```powershell
python scripts/experiments/sacred_egg_crp_puf_protocol.py measurements.csv `
  --report artifacts/aetherfab/sacred_egg_crp_puf_protocol_v2.json `
  --reliability-floor 0.90 `
  --min-stable-bits 64 `
  --maximum-frr 0.05
```

CSV columns are:

```csv
device_id,challenge_id,split,read_id,environment_id,r_0,r_1,r_2
unit-a,c-001,enroll,e-000,room-20c,0.10,0.90,0.11
unit-a,c-001,verify,v-000,room-25c,0.12,0.88,0.10
```

## Primary sources

- M. Hesse et al., “Magnetic Reconnection in the Space Sciences: Past,
  Present, and Future,” *JGR Space Physics* (2020),
  <https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2018JA025935>.
- R. Nakamura et al., “Measurement of the Magnetic Reconnection Rate in the
  Earth's Magnetotail,” *JGR Space Physics* (2018),
  <https://agupubs.onlinelibrary.wiley.com/doi/full/10.1029/2018JA025713>.
- J. Nakanishi, T. Fukuda, and D. E. Koditschek, “A Brachiating Robot
  Controller,” *IEEE Transactions on Robotics and Automation* 16(2) (2000),
  <https://repository.upenn.edu/bitstreams/694b0b83-8e10-496f-a97c-f2f057b7d319/download>.
- J. E. A. Bertram and Y.-H. Chang, “Mechanical energy oscillations of two
  brachiation gaits,” *American Journal of Physical Anthropology* (2001),
  <https://onlinelibrary.wiley.com/doi/10.1002/ajpa.1088/abstract>.
- S. Hadjaje et al., “Mechanics of Drosophila wing deployment,” *Nature
  Communications* 15, 10577 (2024),
  <https://www.nature.com/articles/s41467-024-54527-0>.
- L. M. Riddiford et al., “Control of pupal commitment in the imaginal disks
  of Precis coenia,” *Journal of Insect Physiology* (2003),
  <https://pubmed.ncbi.nlm.nih.gov/12769963/>.
