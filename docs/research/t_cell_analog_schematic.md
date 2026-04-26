# T-Cell Analog Schematic — Honest Engineering Review

**Function under evaluation**

$$T(x,y,z) = \frac{\exp(x)}{\ln(x)} \cdot \frac{\ln(z)}{\exp(y)}$$

evaluated on three voltage inputs `Vx, Vy, Vz` with one voltage output `Vout`, intended as a stamped silicon primitive analogous to a CMOS NAND.

**Bottom line up front:** *This function does not survive the translation from symbol to silicon as a clean repeatable primitive.* The reasons are physical, not engineering polish — they are (a) a hard sign restriction on every log node, (b) an integrable singularity at `Vx = V_ref` that the divider cannot tolerate, (c) a dynamic-range collision between exp() and ln() that consumes every decade an analog rail can give you, and (d) a thermal-drift coefficient on `Vt` that changes the *function being computed* by ~0.33%/K. Detailed reasoning below.

---

## 1. Block-level netlist

Notation. Every analog log/exp block in BJT translinear technology computes, **not** the mathematician's `ln(x)`, but

$$V_{\log} = -V_t \ln\!\left(\frac{V_{\text{in}}}{R\,I_s}\right) = -V_t \ln\!\left(\frac{V_{\text{in}}}{V_{\text{ref}}}\right)$$

with `V_t = kT/q ≈ 25.85 mV` at 300 K and `V_ref ≡ R·I_s` (typically a few hundred mV given `I_s ~ 10⁻¹⁵ A` and `R ~ 100 kΩ`, but in practice `V_ref` is set by a bandgap reference because `I_s` drifts ~7%/K). The "natural log" demanded by the formula and the "log" that silicon delivers differ by the multiplicative constant `−V_t` and by the reference `V_ref`. *That constant is not removable* — it is baked into every translinear identity.

| Block | Type | Inputs | Output | Math |
|------|------|--------|--------|------|
| A1 | Log amp (BJT-in-feedback op-amp) | Vx | V_A1 | `V_A1 = -Vt · ln(Vx/V_ref)` — requires `Vx > 0` |
| A2 | Exp amp (BJT in feedback) | Vx | V_A2 | `V_A2 = V_ref · exp(Vx/Vt)` |
| A3 | Log amp | Vz | V_A3 | `V_A3 = -Vt · ln(Vz/V_ref)` — requires `Vz > 0` |
| A4 | Exp amp | Vy | V_A4 | `V_A4 = V_ref · exp(Vy/Vt)` |
| D1 | Translinear divider (Gilbert-style log-domain) | V_A2 (num), V_A1 (den) | V_D1 | `V_D1 ∝ V_A2 / V_A1` |
| D2 | Translinear divider | V_A3 (num), V_A4 (den) | V_D2 | `V_D2 ∝ V_A3 / V_A4` |
| M1 | Four-quadrant Gilbert multiplier | V_D1, V_D2 | Vout | `Vout = K · V_D1 · V_D2` |
| BG | Bandgap reference + PTAT bias | — | V_ref, I_bias | Sets V_ref ≈ 1.20 V, gives `Vt` cancellation in translinear loops where possible |
| C1–C4 | Input clamps / range guards | Vx, Vy, Vz | clamped versions | Forces `V > V_floor` so log amps don't saturate |

This is **roughly 8 active analog blocks**, each containing an op-amp (≥15 transistors for a decent one), at least one matched-BJT pair, biasing, and compensation. **Realistic transistor count per T-cell: 150–300 devices**, plus passive R/C, plus a shared bandgap (amortizable across many cells but still real). Compare to a CMOS NAND2 at **4 transistors**.

---

## 2. End-to-end math (with the constants you cannot wish away)

Working forward through the netlist:

$$V_{A1} = -V_t \ln(V_x/V_{\text{ref}})$$
$$V_{A2} = V_{\text{ref}} \exp(V_x/V_t)$$
$$V_{D1} = \frac{V_{A2}}{V_{A1}} = \frac{V_{\text{ref}}\,\exp(V_x/V_t)}{-V_t \ln(V_x/V_{\text{ref}})}$$

Similarly

$$V_{D2} = \frac{V_{A3}}{V_{A4}} = \frac{-V_t \ln(V_z/V_{\text{ref}})}{V_{\text{ref}} \exp(V_y/V_t)}$$

Multiplied:

$$V_{\text{out}} = K \cdot V_{D1} \cdot V_{D2} = K \cdot \frac{\exp(V_x/V_t)\,\ln(V_z/V_{\text{ref}})}{\ln(V_x/V_{\text{ref}})\,\exp(V_y/V_t)}$$

Compare to the requested

$$T = \frac{\exp(x)\ln(z)}{\ln(x)\exp(y)}$$

Two things to notice immediately, both fatal to "drop-in primitive" framing:

**(a) Argument scaling.** The silicon does not compute `exp(x)`, it computes `exp(V_x / V_t)`. To make those agree the inputs must be encoded in units of `V_t ≈ 26 mV`. So `x = 1` literal in the math → 26 mV on the rail. `x = 10` → 260 mV. `x = 30` → 780 mV (already at the rail of a 1 V analog supply). The exp amp goes nonlinear / saturates around `x ≈ 25` because the collector current pegs to the bias source. **Dynamic range of the `x` argument: ≈ 0–25 in dimensionless units, period.**

**(b) Log argument scaling.** `ln(V_x/V_ref)` ≠ `ln(x)` unless you adopt the encoding `V_x = V_ref · exp(x)` — which is the *opposite* encoding from (a). The exp port wants `V_x` small-and-linear-in-x; the log port wants `V_x` exponential-in-x. **A single `Vx` input cannot satisfy both ports of the same variable simultaneously.** You'd have to feed two pre-conditioned versions of x — one through an inverse-encoder, one through a direct one — and the inverse encoder is itself a log/exp amp, so you've just moved the problem.

This is the crux: the formula `exp(x)/ln(x)` mixes the two opposite encodings of the same variable. Translinear circuits are *good* at products of exponentials because everything stays in current-domain log representation. A formula that uses both `exp(x)` and `ln(x)` of the same `x` forces you to leave and re-enter the log domain, paying noise and offset each crossing.

---

## 3. Honest limitations

### 3.1 Domain violation: `ln(x)` for `x ≤ 0`

Log amps are BJT-based. The BJT's `Vbe = Vt·ln(Ic/Is)` is defined only for `Ic > 0`. If `Vx` swings negative (or is rectified TENG output that is bipolar), the log amp **does not produce a complex number** — it produces either rail saturation, latch-up, or a junction breakdown event that damages the device. There is no graceful "log of a negative" branch in silicon. Standard mitigations: precision absolute-value front-end (adds 2 op-amps, doubles offset error) plus a sign-tracking digital sideband. That sideband alone undoes the "single primitive" framing.

### 3.2 The pole at `Vx = V_ref`

`ln(V_x/V_ref) → 0` as `V_x → V_ref`. The divider `V_D1 = V_A2 / V_A1` therefore has a pole at `V_x = V_ref`. In a real circuit this looks like:

- For `V_x` within ~5 mV of `V_ref`: `V_A1` is below the noise floor of the log amp (~100 µV·√Hz at the input referred), the divider output is dominated by 1/f noise of the denominator amp, and the cell outputs garbage at full gain.
- For `V_x` exactly at `V_ref`: divide-by-zero, output rails.

A practical analog ASIC would need either (a) a clamp that excludes a window around `V_ref` (introduces a dead zone the math doesn't have), (b) a piecewise mode switch (not a "primitive" anymore), or (c) regularization `ln(V_x/V_ref) → ln(V_x/V_ref) + ε`, which changes the function being computed. None of these is acceptable if T is meant to be a *math* primitive.

### 3.3 Dynamic range collision

- `exp(V_x/V_t)`: 1 mV input change → 4% output change. 60 mV → factor of 10. 240 mV → factor of 10⁴. **Output spans ~10⁵ over a 300 mV input window.** Above ~600 mV input the bias transistor exits forward-active.
- `ln(V_x/V_ref)`: roughly 60 mV output per input decade. To get `ln` to span 10 in dimensionless units (i.e. a factor of `e¹⁰ ≈ 22 000` in input), the input must span ~4.3 decades, ~600 µV to ~13 V. That's 4.3 decades of `V_x` for the log path.

The exp path wants `V_x` ∈ ~[0, 600 mV] linearly. The log path wants `V_x` ∈ ~[1 mV, 10 V] logarithmically. These ranges are **incompatible on the same wire**. With any reasonable rail (1.2 V to 3.3 V analog supply), you can serve one well, the other poorly, and the divider blows up wherever they disagree.

### 3.4 Noise

A good monolithic log amp (e.g., ADL5304-class) has an input-referred noise of ~3–10 nA/√Hz, which translates to roughly **±200 µV of jitter on a 60 mV/decade output** — about 3–5 bits of effective resolution in the log path *before* you stack two of them and a divider. Stacked log–exp–log–divide–multiply chains compound this. **Realistic end-to-end precision of a T-cell: 5–7 bits, falling to 2–3 bits within half a decade of the singularity.** For comparison, a reasonable inference accelerator wants 8 bits sustained. T-cells will not deliver that without averaging across many cells, which defeats the per-cell-primitive framing.

### 3.5 Temperature drift

`V_t = kT/q` carries 0.33%/K linearly. `I_s` carries ~7%/K exponentially (band-gap variation in the saturation current). A naive log amp drifts ~0.3 mV/K at the output and ~7%/K in scale. Translinear loops that pair matched BJTs at the same temperature cancel `V_t` to first order in *products of exponentials*, but:

- The exp/log mixing in `T(x,y,z)` does not collapse to a clean translinear loop. The `V_t` factors in the numerator and denominator do not cancel pairwise because one path is `exp(V/V_t)` and the other is `−V_t·ln(V/V_ref)` — the `V_t` shows up multiplicatively in one place and as a scale of the argument in another.
- Result: T-cell output has a residual `~0.3%/K` thermal coefficient *on the function itself*, before you even discuss device mismatch (~3–10% σ across a die for un-trimmed BJTs).

Compensation requires a PTAT/CTAT scheme tuned per-cell or a shared bias driving the whole array, which works only if you accept that the array operates at one global temperature — fine for a single chip, not fine for the local thermal gradients that real silicon experiences under load (5–15 K hotspot deltas are routine).

### 3.6 The TENG-noise → T-cell → 1 claim

A triboelectric nanogenerator (TENG) does not output "a clean voltage of fixed sign and magnitude." Measured TENG output is:

- **Bipolar** by construction (charge transfer reverses on each contact–separation cycle).
- **Bursty / impulsive** — characteristic spikes at 10²–10⁴ V open-circuit, dropping to mV under load, with sub-millisecond rise times.
- **High output impedance** (10⁸–10¹² Ω), so "voltage" is meaningless without specifying the load — under any low-Z load it collapses; under high-Z it floats and picks up ambient noise.
- **Heavy 1/f and shot-noise contributions** with non-Gaussian tails.

Feeding a TENG into a log-amp input guarantees that for ~50% of the duty cycle the input is negative — the regime where the log path is undefined. The claim that this signal, processed by a T-cell, converges to "1" assumes structure (fixed sign, bounded magnitude, sufficient SNR) that TENG outputs *do not have* without a substantial conditioning front-end (rectifier, charge pump, voltage regulator, band-limit filter). Once that front-end is in place, the "harvester noise" you're computing T of is not the TENG's noise anymore — it's the front-end's residual.

---

## 4. ASCII / Mermaid topology

```
                              ┌──────────────┐
   Vx ───────┬────────────────►   A1: Log    │── V_A1 = -Vt·ln(Vx/Vref) ─┐
             │                └──────────────┘                            │
             │                ┌──────────────┐                            │
             └────────────────►   A2: Exp    │── V_A2 = Vref·exp(Vx/Vt) ──┤
                              └──────────────┘                            │
                                                                          ▼
                                                                  ┌──────────────┐
                                                                  │ D1: Divider  │── V_D1 ──┐
                                                                  └──────────────┘          │
                                                                                            │
                              ┌──────────────┐                                              │
   Vz ──────────────────────► │   A3: Log    │── V_A3 = -Vt·ln(Vz/Vref) ─┐                  │
                              └──────────────┘                            │                 │
                                                                          ▼                 ▼
                              ┌──────────────┐                    ┌──────────────┐  ┌──────────────┐
   Vy ──────────────────────► │   A4: Exp    │── V_A4 ───────────►│ D2: Divider  │─►│ M1: Mult.    │── Vout
                              └──────────────┘                    └──────────────┘  └──────────────┘
                                                                          ▲
                                                                          │
                                                                       V_D2

   ┌──────────────┐                ┌──────────────┐
   │  BG bandgap  │── Vref, Ibias ►│ C1..C4 clamps│  (input range guards, sign rectifier, dead-zone around Vref)
   └──────────────┘                └──────────────┘
```

Mermaid version:

```mermaid
graph LR
    Vx --> A1[A1: Log amp]
    Vx --> A2[A2: Exp amp]
    Vz --> A3[A3: Log amp]
    Vy --> A4[A4: Exp amp]
    A2 --> D1[D1: Divider]
    A1 --> D1
    A3 --> D2[D2: Divider]
    A4 --> D2
    D1 --> M1[M1: Gilbert mult]
    D2 --> M1
    M1 --> Vout
    BG[Bandgap + PTAT bias] -.-> A1
    BG -.-> A2
    BG -.-> A3
    BG -.-> A4
    Clamps[Input clamps / |·| / dead-zone] -.-> A1
    Clamps -.-> A3
```

---

## 5. Verdict

**Not realizable as a stamped per-cell primitive in the NAND sense.** Concretely:

1. **Transistor count**: 150–300 devices per cell vs. NAND's 4. You will fit ~10⁵ T-cells on a die where you'd fit ~10⁷ NANDs. That is not a primitive, it is a *macro*.
2. **Function is undefined on a measure-nonzero subset of its input space**: `Vx ≤ 0` (log domain), `Vx = Vref` (singularity), and a noise-dominated dead zone of finite width around `Vref`. There is no closed-form analog handling of these cases — only out-of-band scaffolding (rectifiers, mode switches, clamps, digital sign tracking).
3. **The exp/log mixing of the same variable forces two incompatible voltage encodings of `Vx`** simultaneously, which translinear topology fundamentally cannot deliver on one wire. The natural way out is to encode all variables in log-domain currents from the start — but then the user no longer has a "T-cell on three voltages," they have a translinear loop where `exp` and `ln` are the *interpretation*, not separate operations.
4. **Precision is 5–7 bits at best**, dropping to 2–3 bits near the singularity, against an 8-bit minimum bar for inference. Per-cell trimming would be needed and that breaks the "stamp millions" model.
5. **Thermal coefficient ~0.3%/K on the computed function** — meaning a 10 K die hotspot makes the output of central T-cells drift by ~3% relative to edge T-cells. The function itself becomes spatially non-uniform across the die.
6. **The TENG-as-input scenario is the worst case for this circuit**: bipolar, bursty, ill-defined voltage source feeding directly into the input of a log amp. The "noise → T-cell → 1" intuition assumes well-conditioned signals the harvester does not produce.

**Most defensible use of T(x,y,z) in analog silicon**: implement it as a *small array operation* — pre-condition all inputs into the strict positive interior, factor the math into a translinear loop in current domain (where `exp` and `ln` are encoder/decoder, not stages), share a bandgap and PTAT bias across a tile, accept 6-bit precision, and route around the singularity in *software*. That gives you a T-tile of ~1000 transistors covering ~64–256 logical T evaluations time-multiplexed — useful, but not a primitive.

**Stronger recommendation**: if the goal is analog AI inference, choose a function family whose translinear realization *closes* — `(I_a · I_b)/I_c`, products of exponentials, sigmoidal `1/(1+exp(-x))`, or piecewise affine "ReLU-on-currents." These have NAND-like primitive status in analog. `exp(x)/ln(x) · ln(z)/exp(y)` does not, primarily because of (b) above: you cannot represent a single variable in two opposite encodings on the same wire without an out-of-band conversion stage, and that stage destroys the primitive framing.

---

*Constants used: V_t = kT/q = 25.85 mV at 300 K; bandgap V_ref ≈ 1.20 V; representative I_s ≈ 10⁻¹⁵ A for a small NPN; log-amp input noise ≈ 5 nA/√Hz; BJT mismatch σ(I_s) ≈ 5–10% un-trimmed.*
