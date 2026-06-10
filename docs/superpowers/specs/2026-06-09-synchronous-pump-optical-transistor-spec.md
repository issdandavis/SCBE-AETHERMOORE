# Synchronous-Pump Time-Domain Optical Transistor — Spec

**Date:** 2026-06-09
**Extends:** `src/physics_sim/optical_transistor.py` (averaged model, PR #2124)
**Status:** spec — not yet implemented
**Purpose:** de-average the Adler/iterated-map model into an explicit pulse-train
time-domain model, and use it to **try to falsify** the clean bistable result the
averaged model reported. The averaged model is *autonomous and noiseless*; it is
structurally blind to the two effects that actually kill real cavity logic
(finite gain recovery, spontaneous-emission seeding). If the bistability and the
2×10⁶ extinction survive de-averaging **plus** those two stressors, the claim is
much stronger. If they collapse, we have found where the averaging was decorative.

This is a null-test instrument, not a fidelity upgrade. Every section below states
what would make the result *fail*, up front, before any tuning.

---

## 0. Symbol legend

| Symbol | Meaning | Units (non-dim unless noted) |
|---|---|---|
| `a(t)` | slowly-varying signal field envelope (complex) | √photons |
| `S(t)` | intracavity photon number, `S = |a|²` | photons |
| `N(t)` | population inversion of the gain medium | carriers |
| `g(N)` | gain coefficient, `g = σ(N − N_tr)` | 1/length |
| `q(S)` | saturable-absorber loss, `q = q₀/(1 + S/S_sat)` | 1/length |
| `α` | residual linear loss | 1/length |
| `R₁,R₂` | mirror power reflectivities | — |
| `L` | cavity length | length |
| `τ_rt` | round-trip time `= 2L/v_g` | time |
| `τ₂` | upper-state (gain-recovery) lifetime | time |
| `ρ` | **recovery ratio `τ₂/τ_rt`** — the Probe-1 control knob | — |
| `T` | pump-pulse period | time |
| `E_p` | energy per pump pulse | carriers injected |
| `σ` | stimulated-emission cross-section | — |
| `V` | mode volume | — |
| `Δω` | injection detuning (signal vs cavity resonance) | 1/time |
| `K` | injection-locking half-bandwidth (Adler) | 1/time |
| `β` | spontaneous-emission factor into the lasing mode | — |
| `G` | round-trip power gain `= R₁R₂·exp[(ḡ − q̄ − α)L]` | — |

---

## 1. The anchor the new model MUST reproduce (non-negotiable)

A valid time-domain model reduces to the averaged model in the correct limit. In
the limit **`ρ → ∞`** (gain effectively CW, no inter-pulse sag) **and `β → 0`**
(no spontaneous floor), the time-domain model must reproduce, to ≤2% relative:

- bistable fixed points: stable `0`, unstable `P_t = 0.029`, stable `P* = 2.62`;
- contraction `f′(P*) = 0.562 < 1`;
- Adler locked transfer `T_lock(Δω) = √(1 − (Δω/K)²)` with the window edge at
  `|Δω| = K`;
- scrambled-injection collapse (≈210× in the averaged run — direction, not the
  exact factor, is what must reproduce);
- multi-beam extinction → `ratio = 1.000` when the shared reservoir is severed.

**If the time-domain model cannot recover these in the `ρ→∞, β→0` corner, it is a
different model, not an extension — stop and reconcile before proceeding.** This
check is a required regression test (`test_reduces_to_averaged_in_cw_limit`).

---

## 2. Time-domain model

### 2.1 State and clock

Discretize fast time within a round trip with step `dt ≪ τ_rt`; index round trips
by `n`. The pump is an explicit train at period `T`:

```
R_p(t) = E_p · Σ_m  h(t − mT)          # h = narrow pulse shape, ∫h dt = 1
```

Default `T = τ_rt` (synchronous pumping). `T` is a free parameter precisely so the
**timing null** (§4.4) can detune it.

### 2.2 Inversion ODE (the part the averaged model erased)

```
dN/dt = R_p(t)  −  N/τ₂  −  (σ c / V) · N · S(t)
```

- term 1: pulsed re-pumping at the surface;
- term 2: relaxation on `τ₂` (this is the gain-recovery clock — set by `ρ`);
- term 3: stimulated depletion by the circulating signal.

The gain seen by the signal is `g(t) = σ(N(t) − N_tr)`, **instantaneous**, not
round-trip-averaged.

### 2.3 Field map per round trip

Propagate the envelope once around the cavity, applying instantaneous gain, the
saturable absorber, linear loss, mirror loss, detuning phase, and the injected
seed:

```
a_{n+1}(t) = √(R₁R₂) · exp[ ½ (g(t) − q(S) − α) L ] · e^{ i Δω τ_rt } · a_n(t)
             +  κ_inj · a_inj · e^{ i φ_inj }                       # injection
             +  ξ_sp(t)                                             # §3.2 noise (β)
```

For a first implementation a **lumped** per-round-trip update (evaluate `g`,`q` at
the pulse-peak `S`) is acceptable and tractable; a finer sub-`τ_rt` integration is
the stretch goal. The lumped form must still carry the `N` ODE between round trips
so `ρ` enters.

### 2.4 Injection locking is now emergent, not assumed

The Adler equation `dΔφ/dt = Δω − K sin Δφ` was an *input* to the averaged model.
Here it must **emerge** from §2.3: sweep `Δω`, measure the steady-state phase lock,
and confirm the locking window `|Δω| < K` appears on its own. (Anchor check, §1.)

---

## 3. The two falsification probes

### 3.1 Probe 1 — gain-recovery boundary `ρ = τ₂/τ_rt`

**Question:** does `N` recover between pump pulses well enough to hold a "1"?

**Procedure:** sweep `ρ ∈ [10⁻², 10²]` (log-spaced, ≥25 points). At each `ρ`, run
the single-stage map to its fixed point(s) and record: (a) whether bistability
survives (two stable fixed points with an unstable threshold between), (b) the
upper fixed point `P*(ρ)`, (c) the gating extinction (signal-present vs absent).

**Stated prediction (falsifiable, pre-registered):**
- `ρ ≪ 1`: gain dies between pulses → no sustained "1" → **bistability lost**,
  the cavity cannot hold state across a round trip.
- `ρ ~ 1`: the interesting regime — inversion persists ~one round trip and is
  re-pumped each cycle; gating should be strongest here.
- `ρ ≫ 1`: medium acts CW → recovers the averaged/Adler result (§1).

**Acceptance:** report `ρ_crit` (the lower edge where bistability collapses) as a
*measured* number with the curve, **not** tuned to a target. The result is "real"
if a non-degenerate bistable window exists for some physically plausible `ρ`
(roughly `ρ ≳ 0.5`); it is *decorative/averaging-artifact* if bistability only
exists as `ρ → ∞`.

### 3.2 Probe 2 — spontaneous-emission floor at the threshold edge

**Question:** at `G ≈ 1` (the lasing edge the device must sit on), can spontaneous
emission seed the *wrong* fixed point and flip a bit?

**Procedure:** add a Langevin source to §2.3,
```
ξ_sp(t) = √(β · N(t) / dt) · η(t)          # η: unit complex white noise
```
Run an ensemble (≥200 trajectories) of the **300-stage cascade** with a clean "0"
input and, separately, a clean "1" input. Measure the per-stage and cumulative
**bit-flip probability** vs the noise margin `Δ = P_t − P_noise_floor`.

**Stated prediction:** flip rate falls roughly exponentially in the margin
`(P_t − ⟨P_0⟩)²/⟨ξ²⟩`. The averaged model's deterministic "survives 300 stages"
becomes a **probability** — report it as "≥X% of 300-stage runs hold the bit at
β = β₀", with the `β` at which 300-stage survival drops below 99%.

**Acceptance:** the claim "cascadable to 300 stages" is upheld only if survival
≥99% at a physically defensible `β` (state the value and cite a regime, e.g.
microcavity polariton `β ~ 10⁻²`–`10⁻³`). If survival collapses at realistic `β`,
that is the honest finding: the clean cascade was a noiseless-model artifact.

---

## 4. Null gates (must all hold; the last one is new)

1. **Remove the saturable absorber** (`q₀ = 0`) → bistability gone, collapses to a
   linear amplifier (non-cascadable). Carried over from the averaged model.
2. **Scramble injection phase** (`φ_inj` random per round trip) → gain collapse
   (the kinetic-rectifier observable; direction must reproduce, factor may differ).
3. **Sever the multi-beam reservoir** (decouple the shared `N`) → extinction ratio
   → `1.000`. Carried over.
4. **NEW — timing null:** randomize the pump period (`T` drawn i.i.d. around
   `τ_rt` with spread ≳ `τ_rt`) instead of `T = τ_rt`. Gating must **collapse**.
   This directly tests the load-bearing claim that *synchronous* surface injection
   — not just any pumping — is what enables the transistor. If random-timing pumping
   gates just as well, the synchrony is decorative and the "pulse injection on the
   surfaces" framing is unsupported.

A result that passes Probes 1–2 but fails null 4 means the device works for a
reason other than the one claimed — surface it, do not bury it.

---

## 5. Module interface

Add to `src/physics_sim/optical_transistor.py` (or a sibling
`synchronous_pump.py` importing the shared map primitives):

```python
def simulate_synchronous_pump(
    *, rho: float, T_over_tau_rt: float = 1.0, beta: float = 0.0,
    detuning: float = 0.0, n_round_trips: int = 2000, seed: int | None = None,
) -> dict:
    """One stage, explicit pulse-train pump. Returns:
      {"fixed_points": [...], "bistable": bool, "P_star": float,
       "contraction": float, "extinction": float, "locked": bool}"""

def probe_recovery_boundary(rho_grid) -> dict:        # Probe 1 -> rho_crit, curve
def probe_spontaneous_floor(beta_grid, n_traj=200) -> dict:  # Probe 2 -> survival(beta)
def reduces_to_averaged(tol=0.02) -> dict:            # §1 anchor check
def timing_null(spread) -> dict:                      # §4.4
```

All return JSON-serializable dicts (instrument-family convention): every run
reports its own null/collapse alongside the positive number, never a bare metric.

### Tests (`tests/physics_sim/test_synchronous_pump.py`)

- `test_reduces_to_averaged_in_cw_limit` — §1 anchor, ≤2% on P\*, threshold,
  contraction, locking-window edge.
- `test_recovery_boundary_has_bistable_window` — Probe 1, `ρ_crit` finite and a
  bistable window exists for `ρ ≳ 0.5`.
- `test_spontaneous_floor_survival` — Probe 2, survival ≥99% at stated `β₀`,
  monotone-decreasing in `β`.
- `test_null_no_absorber_is_linear` / `test_null_scrambled_phase` /
  `test_null_severed_reservoir` / `test_null_random_timing_collapses_gating`.

---

## 6. What a clean PASS vs a real FAIL looks like

**PASS (stronger than the averaged result):** there exists a physically plausible
`(ρ, β)` region where all three figures of merit hold simultaneously — `G ≥ 1`,
fan-out `F ≥ 2`, `|f′(P*)| < 1` — *and* all four null gates bite. The averaged
result was not an averaging artifact.

**FAIL (the valuable outcome):** any of —
- bistability exists only as `ρ → ∞` (it was a CW/averaging artifact);
- 300-stage survival drops below 99% at realistic `β` (noiseless-model artifact);
- random-timing pumping gates as well as synchronous (the synchrony claim is unsupported).

Either way the module reports it. A FAIL is not a setback; it is the null
discipline doing its job — the same blade that retired the spin-voxel "structure"
and the wettability-diode threshold-gaming. Report the boundary, never tune to clear it.

---

## 7. Honest risks / non-goals

- **Lumped vs distributed:** the lumped per-round-trip update may itself hide
  intra-cavity pulse-shaping (gain narrowing, soliton effects). State this as a
  model limit; the sub-`τ_rt` integration is the follow-on, not this spec.
- **No claim of manufacturability.** This is a reduced model. It can falsify a
  mechanism; it cannot validate a device. Coupon/experimental validation is out of
  scope (same posture as the transpiration-skin work).
- **Parameter realism gates the verdict.** `ρ`, `β`, `S_sat` must be tied to a
  cited material regime (microcavity polariton organic semiconductor) before any
  PASS is asserted; an arbitrary parameter set can make anything bistable.
