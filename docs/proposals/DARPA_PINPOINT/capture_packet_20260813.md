# PINPOINT Capture Packet — HR001126S0016

Date: 2026-08-13
Entity: Issac Davis dba SCBE AetherMoore
CAGE: 1EXD5
UEI: J4NXHM6N5F59
Decision owner: Issac

## 1. Opportunity Snapshot

- **Name:** Precision Inertial Navigation & Positioning On an Integrated Tesseract (PINPOINT)
- **Notice ID:** HR001126S0016
- **Source:** https://sam.gov/opp/a269e0efc8614bf5b9ea6628ae5f1ad7/view
- **Issuer:** DARPA Defense Sciences Office
- **Vehicle:** BAA. Awards may be procurement contracts, cooperative agreements, or OT for Prototype.
- **Contact:** PINPOINT@darpa.mil
- **Abstract due:** 2026-08-27 16:00 ET via BAAT. Mandatory. No conforming abstract = no full proposal.
- **Questions close:** 2026-09-15 16:00 ET
- **Full proposal due:** 2026-09-25 16:00 ET
- **Inactive:** 2026-10-25
- **This BAA buys:** Phase I only, 24 months. Phase II is planning-only (draft SOW + ROM).
- **NAICS / PSC:** 541715 / AC12
- **Proposers Day:** already happened (2026-07-27)

## 2. Mission Fit

**Government problem:** GPS-denied PNT. MEMS IMUs have sat on a noise/drift plateau for a decade. Strategic IMUs (RLG/FOG) are too big, hot, and expensive for tactical and unmanned platforms. Visual nav still needs a baseline IMU and fails in fog, blur, water, cloud, and desert.

**What they will actually buy:** a 6-DOF IMU whose *physics package* is new (levitated proof mass, nonlinear resonator, high-velocity tethered microsystem, or equally unorthodox), *co-designed* with a real-time adaptive controller and dynamic state estimator. Plus a Design Guide and PDK. Plus five packaged sensors.

**Why now:** HALOVS / NIMBUS / LeviTAS already pushed levitated and high-velocity vibratory systems. PINPOINT is the "make it an IMU" follow-on. The BAA literally tells proposers to stand on the public HALOVS portfolio.

**Why SCBE (solo, 2026-08-13):** Issac is the only performer. The bid is a ferrofluid-trapped 6-DOF IMU he designs and builds, with SCBE as the controller/estimator, not a teammate lane under a MEMS prime. Authority: `solo_approach_20260813.md`.

## 3. Capability Mapping

Map only what exists. Do not invent a MEMS lab.

| PINPOINT requirement | Existing artifact | Can we claim it? |
|---|---|---|
| Novel inertial *sensor physics* (levitated mass, nonlinear resonator, tethered high-velocity microsystem) | No IMU. Adjacent ferrofluid / magnetic-field work exists (see §3b). `physics_sim/core.py` is textbook Newtonian helpers. | **Not as a sensor. Yes as a coil-array control + ferrofluid-trap *hypothesis*.** |
| Real-time adaptive control of highly nonlinear dynamics | Lyapunov / CBF / port-Hamiltonian *language* in docs; executable L7 Lyapunov exponent in `symphonic_cipher/scbe_aethermoore_v2.1_production.py` and `src/symphonic_cipher/harmonic_scaling_law.py` | **Partial.** Demonstrated software-state stability behavior, not IMU closed-loop control. Patent file says the Lyapunov proof is a sketch. |
| Dynamic state estimator for 6-DOF | 9D state engine skill + Poincaré / phase / flux embeddings (`phdm-21d-embedding`, Layer-1 context tuple) | **Partial.** Geometric state, not an INS Kalman/MEKF on rate-table data. |
| "Integrated Tesseract" | `python/scbe/rubix_cubit.py` — 16-vertex 4D code-state with SHA receipts. File itself says: "software planning / governance primitive, not a physics claim." | **Name only.** Useful as a *control-state addressing* layer if a hardware prime already has 3 accel + 3 gyro channels. Do not imply the tesseract *is* the IMU. |
| Legal control path / fail-closed | TLCFI + fail-to-noise (patent-invariant core, 63/961,403 filed 2026-01-15, pending) | **Yes, as the controller safety layer.** Not as the sensor. |
| Design Guide + PDK (simulated design space, projected performance) | Loom / verifier-bench / receipted manifests; Deep Thoughts digital-engineering brief | **Yes, as the software PDK / evidence registry.** Not as a foundry PDK. |
| Month-12 lab demo: 3 accel + 3 gyro, rate table, shaker, Allan Deviation to 1,000 s | No lab, no rate table, no shaker, no ADEV harness | **No.** |
| Month-21/24: 3 then 5 packaged IMU prototypes + fabrication process | No fab, no packaging line | **No.** |
| GPS-denied navigation software story | `NASA_DARPA_ROBOTICS_COMPARISON.md` already records the missing pieces: calibrated dynamics, controller residuals, sim-to-real, online recovery | Honest. Use it as the gap list, not as proof. |
| Prior DARPA capture machinery | MATHBAC packet, CLARA volumes, Deep Thoughts brief, QBI IV&V triage | **Yes.** Process, not IMU evidence. |
| Federal posture | SAM active, CAGE `1EXD5`, UEI `J4NXHM6N5F59`, small-business sole prop | **Yes.** Confirm CMMC/SPRS before any procurement-contract path. |

### 3b. Ferrofluid and GitHub research (found 2026-08-13, first pass missed it)

First `have_it` query was `PINPOINT IMU inertial tesseract` and returned zero. That was the wrong string. `ferrofluid` is all over GitHub and the farm. The files already bound themselves; do not tighten or loosen those bounds in the abstract.

| Artifact | Where | What it actually is | PINPOINT use |
|---|---|---|---|
| `ferro_field.py` | `C:\dev\ferro_field.py`, also `issdandavis/loom` and `issdandavis/dev-workspace` | Grammar: language → legal field op → electromagnet current map → *simulated* Rosensweig surface. Hardware not built. | **Load-bearing for the control half of a magnetically trapped proof mass.** The current-map transfers to a real coil array. The fluid height map does not. |
| `ferrofluid_habitat_control_SPEC.md` | `C:\dev\` and `issdandavis/dev-workspace` | 2026-06-28 honest spec. Habitat thermal/actuation/energy fusion is speculative. TRL: control software runnable; terrestrial surface-shaping 3–4 (others); space-habitat surface 1. | Cite the one-sentence claim. Do not cite habitat fusion. |
| M-TEF cell packet | `SCBE-AETHERMOORE/research/mtef-cell/`, `docs/research/mtef_research_compendium_2026-06-17.md`, `issdandavis/ideas`, `issdandavis/idea-vault` | Literature-backed hybrid EM + TENG harvester. Ferrofluid is a *magnetic control layer*, deliberately not a miracle conductive fluid. Integrated system TRL 1–2. | Adjacent materials, not an IMU. Do not claim energy-harvesting as inertial sensing. |
| Drone-a-rang veins | `C:\dev\clay_home\folds\drone_a_rang\BUILD.md` (also `dev-workspace`) | Computed ferrofluid vs 98 g centrifugal. Replaces mercury. 50–800 T/m field gradient vs 1,492 kN/m³ centrifugal. Toroidal hub required. Tesla-valve geometry, zero moving parts. Secondary/trim on a spinning airfoil, not a sensor. | Closest *inertial* arithmetic on the farm. Mass-routing under high-g, not a 6-DOF IMU. Useful as a high-g working-fluid calculation if a prime is doing Table 1. |
| Magnetic-sheathed fiber tether | `issdandavis/SCBE-research` `docs/research/magnetic_sheathed_fiber_optic_space_tether_2026-06-01.md` | Ferrofluid as tunable hydrodynamic working medium in *side channels*. Fiber path stays sealed. | BAA "tethered microsystem" is a MEMS resonator, not this orbital tether. Do not conflate. |
| Permeable dock plug | `C:\Users\issda\drone_permeable_interface_sim.py` | PFPE/ferrofluid liquid-plug loss model (choked flow, capillary number). | Docking, not inertial. |
| Thermomagnetic wafer roadmap | `issdandavis/college-peninsula` scholarship packet | Ferrofluid loop as coolant / field-positioned working fluid for a neural wafer. | Thermal, not IMU. |
| 2026-06 COMPLETION_LEDGER cut | `issdandavis/dev-workspace` | "park all space/magnetic/ferrofluid HARDWARE" | Still the right hardware cut. Software control stays. |

**The one new sentence the ferrofluid docs buy:**

> A magnetically trapped ferrofluid droplet is a legitimate *species* of the BAA's "electromagnetically levitated proof mass," and we already have a fail-closed coil-array controller (`ferro_field.py`) plus a computed high-g ferrofluid routing model (`drone_a_rang`). We do not have a measured accelerometer or gyroscope.

That sentence is fundable as a teammate physics story. It is **not** a month-12 six-axis lab demo. Rosensweig spikes in a 9×22 ASCII heatmap are not Allan Deviation.

Literature that a prime or a later abstract could stand on (not ours): ferrofluid accelerometers and magnetic-trap droplet proof masses exist in the published MEMS literature. Cite those papers if, and only if, someone on the team has read them. Do not imply we built them.

### What the title coincidence is, and is not

PINPOINT's "tesseract" is DSO naming for an integrated 6-DOF inertial package (and, in the HALOVS lineage, a 4-axis design space). SCBE's tesseract is a 4D permission/code cube. The overlap is rhetorical, not physical. An abstract that leads with "we already built the tesseract" will be read as non-conforming wordplay. An abstract that says "hardware prime supplies the six sensing channels; SCBE supplies a 4D control-state cube, Lyapunov-bounded adaptive law, and receipted estimator" is the honest sentence.

### Patent language (do not drift)

- Cite **63/961,403, filed 2026-01-15**, sole inventor Issac Daniel Davis.
- Application **19/691,526** may be named without calling it a nonprovisional conversion.
- Say **filed** and **pending**. Never patented, granted, or patent holder.
- Lyapunov is a claimed *stability behavior*, not a finished proof.
- Hyperbolic `d_H` did **not** beat cosine on trust AUC. Do not put that number, or any superiority claim, in a PINPOINT abstract.

## 4. Delivery Shape

**Solo.** Issac is PI, builder, and author. See `solo_approach_20260813.md`.

| Work package | Months 1–12 | Months 13–24 |
|---|---|---|
| Ferrofluid trap + Rosensweig resonator (the sensor) | One-axis bench → six channels | Three then five packaged IMUs |
| Coil-array controller (`ferro_field` extended) | Month-3 ferrohydrodynamic sim | Closed-loop on the bench |
| 6-DOF estimator + 4D state cube | Simulated ADEV | Hardware-in-the-loop vs rented rate table |
| Design Guide / software PDK | Parameter registry | Transition package |
| Lab IV&V | Rented rate-table + shaker days | Government lab on delivered units |

Use case: **Table 2 UAV / Persistent Autonomy only.** Not munitions.

Instrument: **OT for Prototype.** Vendors (Ferrotec, coil shops, rate-table rental) are procurement. Nobody else is on the cover sheet.

Compliance: ACA still shares *program-generated* data with other PINPOINT performers. Background IP (63/961,403, Rubix, ferro_field grammar) is listed as background and stays out of the share set.

## 5. Economics

- Award size: **not stated**. Multiple awards.
- Solo Phase I ROM: **~$400k–$575k** (1.0 FTE PI + bench materials + rented test days + PI-meeting travel). Details in `solo_approach_20260813.md`.
- IIP: no.
- Do not write a foundry budget. Do not write a $3M team budget.

## 6. Risk Register

| Risk | Severity | Mitigation |
|---|---|---|
| Software-only abstract deemed non-conforming | Fatal | Abstract must propose *building* six physical channels. |
| Claiming measured ADEV I do not have | Fatal | Propose Table 2; do not report it as done. |
| Title-tesseract overclaim | Fatal to credibility | Rubix is control-state geometry only. |
| Lyapunov-as-proof | High | Bounded-update stabilizer, not a theorem. |
| No in-house rate table | High | Rent days. Book at month 10. |
| One-person critical path | High | Named in the risk section. |
| Ferrofluid colloid / tempco / Brownian noise | High | Two fluids, sealed cartridge, temperature in the estimator. |
| ACA shares program data | Medium | Background-IP list before submit. |
| CMMC if they force a procurement contract | Medium | Bid OT first. |

## 7. Go / No-Go

**GO to write a solo abstract** on the ferrofluid-trap IMU in `solo_approach_20260813.md`.

**NO-GO** if the abstract does not commit Issac to building six physical channels, or if it claims any ADEV number as already measured.

Teaming is off. Kill date for *partners* is deleted. New kill: if the plant paragraph is still software-only on 2026-08-24, do not file.

## 8. 14-Day Clock

| Date | Action |
|---|---|
| 2026-08-13 | Solo path locked. Teaming dropped. |
| 2026-08-14–20 | Draft Att B abstract + Att A slide. Open BAAT account. Price the Ferrotec + lock-in + rate-table rental so the ROM is not invented. |
| 2026-08-21–24 | Issac reads the draft. Cut any sentence that claims a measured IMU. |
| 2026-08-25–26 | PDF the abstract. Submit dry-run in BAAT. |
| 2026-08-27 16:00 ET | Abstract in BAAT. Not Grants.gov. |
| 2026-09-15 | Last day for questions. |
| 2026-09-25 | Full proposal only if the abstract was conforming. |

## 9. Teaming Targets (hardware first)

These are HALOVS / adjacent device groups the BAA told everyone to stand on. Ranked by how directly their published HALOVS work is already an IMU precursor.

1. **Andrei Shkel / Camilo Velez Cuervo** — Untethered micro-HRG (u2-HRG). Closest thing to a gyroscope product on the HALOVS list.
2. **Jeffrey DeNatale / Rob Candler** — n-LUMOS (nonlinear ultra-fast magnetically operated microsystems). Control-of-nonlinear is the exact co-design sentence.
3. **Cristian Cassella, Northeastern** — higher scale-factor gyros via interface states.
4. **Mingyo "Leen" Park, Penn State** — HORCREX nonlinear MEMS frequency-comb inertial sensors, $2M DARPA, cleanroom already running.
5. **Honeywell MEMS IMU lineage** (prior PRIGM / thermally stabilized munition IMUs). Only if a small-business/university team needs a transition partner, not a first email.

Do **not** lead with MATHBAC AI/geometry people (Aalyria, UW-Madison, SIFT). Wrong plant. Collin / Hoags / DAVA is firmware and is not a MEMS foundry.

## 10. Outreach Draft (one paragraph, reuse the Deep Thoughts tone)

Subject: PINPOINT (HR001126S0016) — nonlinear control / 6-DOF estimator teammate lane

Hello <Name>,

I run a small U.S. performer (Issac Davis dba SCBE AetherMoore, CAGE 1EXD5, UEI J4NXHM6N5F59) that builds Lyapunov-bounded adaptive control, a 4D control-state cube, and receipted state estimators. I am **not** bidding PINPOINT as a sensor prime. If you are taking a HALOVS/NIMBUS/LeviTAS device into the PINPOINT 6-DOF IMU, I can cover the controller + dynamic estimator + Design Guide / software PDK work package so your team hits the month-3 math/sim gate and the month-12 closed-loop ADEV story without growing a separate controls staff. UAV / persistent-autonomy (Table 2) is the use case I would support. Happy to send a one-page split and join a 20-minute call before the 27 August abstract.

Issac Davis
issdandavis7795@gmail.com
CAGE 1EXD5 | UEI J4NXHM6N5F59

## 11. Abstract Skeleton (only fill this after a prime is named)

Mandatory: Attachment A slide + Attachment B, ≤5 pages body, 12-pt, 1-inch margins, unclassified. Cover sheet, ToC, optional 2-page bibliography, optional ≤3 technical papers do not count.

1. **Goals and Impact** — Prime's sensor physics in the first sentence. SCBE in the second: stabilize and estimate that nonlinear plant in real time so Table 2 Phase I ADEV is reachable. Quantitative target is the prime's number, not ours.
2. **Technical Approach** — Today's MEMS linear-regime plateau. New: device in nonlinear/levitated regime + adaptive law that keeps a Lyapunov function non-increasing + 4D state cube addressing the six channels + fail-closed estimator. Month-3 / 12 / 21 / 24 milestones copied from the BAA, with owner tags.
3. **Capabilities** — Prime: fab, packaging, rate table. SCBE: control, estimator, PDK software. PI is almost certainly the hardware PI.
4. **Cost and Schedule** — Prime's ROM. SCBE as a line, not the total.

## 12. Existing Docs To Reuse, Not Rewrite

- `docs/proposals/DEEP_THOUGHTS_26_05_CAPABILITY_BRIEF.md` — entity block, teammate posture, compliance boundaries.
- `docs/proposals/DEEP_THOUGHTS_26_05_OUTREACH_EMAILS.md` — email tone.
- `docs/proposals/DARPA_QBI_IVV/capture_triage_2026-05-01.md` — same go/no-go shape.
- `docs/proposals/DARPA_MATHBAC/ip_carveout_v1.md` + teaming agreement drafts — ACA / background IP.
- `python/scbe/rubix_cubit.py` — the only honest tesseract cite.
- `symphonic_cipher/scbe_aethermoore_v2.1_production.py` L7 — the only honest Lyapunov cite.
- `C:\dev\clay\lightning_rescue_20260806\clay_vault\training\v4\NASA_DARPA_ROBOTICS_COMPARISON.md` — already lists the physical gaps. Keep that list in the abstract's risk paragraph.

Do not recycle MATHBAC 24/24, DAVA `phi_beacon`, or Clay counting-score numbers into this BAA. Wrong metric.

## 13. Sources

- Local BAA PDF: `C:\Users\issda\Downloads\_pinpoint_extract\HR001126S0016.pdf`
- Attachments A–I in the same folder (abstract slide, abstract template, Volume I/II, cost sheet, model OT, ACA, milestone schedule)
- HALOVS portfolio PDF referenced by the BAA: https://www.darpa.mil/sites/default/files/attachment/2026-06/program-halovs-portfolio.pdf
- HALOVS program page: https://www.darpa.mil/research/programs/halovs
