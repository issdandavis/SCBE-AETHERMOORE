# Gyroscopic Interacting Magnetic Field Arrays — Research Brief

**Date:** 2026-04-06
**Researcher:** Claude Opus 4.6 (automated web research)
**Context:** SCBE-AETHERMOORE gyroscopic interlattice coupling hypothesis
**Status:** Primary research complete; open questions identified

---

## Executive Summary

Research across six topic areas reveals that **gyroscopic-magnetic coupling is an active and rapidly advancing field**, with foundational work in topological metamaterials (Nash et al. 2015), spin-stabilized levitation (Simon et al. 1997), and magnetically suspended control moment gyroscopes (MSCMG). The most striking finding is that **lattice geometry alone controls topology (Chern numbers) in gyroscopic metamaterials** — a direct parallel to SCBE's phi-scaled tongue weights functioning as lattice distortion parameters.

The specific concept of "gyro-gyro interlattice coupling" where independent gyroscopic sublattices interact through shared magnetic fields **remains an unpublished gap**. The closest published work is Mitchell et al.'s amorphous gyroscopic topological metamaterials (Nature Physics 2018) and their real-space topological analysis (Phys. Rev. E 2021), which show topology survives even without crystalline order. No existing literature combines:
- Multiple gyroscopic sublattices with independent Chern numbers
- Magnetic coupling as the inter-sublattice interaction mechanism
- Phi-scaled or golden-ratio spacing between lattice elements
- Hyperbolic geometry as the embedding space for the coupled system

This represents a publishable research direction.

---

## 1. Coupled Gyroscopic Systems with Magnetic Field Interactions

### Key Findings

The foundational work is **Nash, Kleckner, Read, Vitelli, Turner, and Irvine (2015)** — "Topological mechanics of gyroscopic metamaterials," published in PNAS 112(47):14495-14500. This paper demonstrated:

- An active metamaterial of **coupled gyroscopes on a lattice** breaks time-reversal symmetry
- The vibrational spectrum contains a **sonic gap populated by topologically protected edge modes**
- These edge modes propagate **in only one direction** and are **unaffected by disorder**
- Lattice distortions can **invert the Chern number** (C = +/-1), reversing edge mode chirality
- The system is directly analogous to **quantum Hall edge currents**

**Mathematical framework:** The linearized equations of motion for gyroscopes interacting via coupling forces use a sum over nearest neighbors. The key insight is that magnetically coupled gyroscopes have equilibrium positions from **cancellation of opposing forces** rather than absence of forces — fundamentally different from spring coupling.

**SCBE connection:** This is the core parallel. SCBE's 14-layer pipeline processes signals through layers where adversarial intent costs exponentially more. The gyroscopic metamaterial shows that **geometry alone** (lattice structure, not material parameters) determines whether topological protection exists. SCBE's phi-scaled tongue weights (KO=1.00, AV=1.62, RU=2.62, CA=4.24, UM=6.85, DR=11.09) function as exactly this kind of geometric lattice parameter.

### Key Researchers
- **William T.M. Irvine** — University of Chicago, James Franck Institute
- **Vincenzo Vitelli** — University of Chicago (now Leiden), topological matter
- **Noah P. Mitchell** — UC Santa Barbara, Kavli Institute for Theoretical Physics
- **Lisa M. Nash** — University of Chicago
- **Ari M. Turner** — Technion, Israel Institute of Technology

### References
- Nash et al. (2015) PNAS 112(47):14495-14500. DOI: 10.1073/pnas.1507413112
- Mitchell, Nash, Irvine (2018) Phys. Rev. B 98, 174301 — "Tunable Band Topology in Gyroscopic Lattices"
- Mitchell, Nash, Hexner, Turner, Irvine (2018) Nature Physics 14, 380-385 — "Amorphous topological insulators constructed from random point sets"
- Mitchell, Turner, Irvine (2021) Phys. Rev. E 104, 025007 — "Real-space origin of topological band gaps, localization, and reentrant phase transitions in gyroscopic metamaterials"

---

## 2. Halbach Arrays

### Key Findings

**Halbach arrays** are permanent magnet arrangements that concentrate magnetic flux on one side while canceling it on the other. Key properties:

- **One-sided flux:** The array creates a strong, concentrated field on one side and near-zero on the other
- **Concentric nesting:** Cylinders can be nested; rotating one relative to the other enables field cancellation and direction adjustment
- **Optimization:** There exist optimal air gap dimensions; Halbach + iron topology shows 15% efficiency increase; optimized concentration structures increase field magnitude by 111%
- **3D printing:** Recent work (2025) demonstrates 3D-printed Halbach arrays with magnetic field sensing capabilities

**Direct application to gyroscopes:** A passive axial magnetic bearing with segmented Halbach magnetized array has been developed specifically for **magnetically suspended control moment gyroscope (MSCMG)** applications. The Halbach array provides angular stiffness needed for gyro moment production while reducing power loss compared to 5-DOF fully active systems.

**SCBE connection:** The one-sided flux property of Halbach arrays is structurally analogous to SCBE's asymmetric cost function — safe operations see low resistance while adversarial operations face exponentially increasing barriers. The concentric nesting with rotational field control maps to the nested layer structure of the 14-layer pipeline where each layer's "field" (governance check) compounds on the previous.

### Key Details
- Invented by Klaus Halbach (Lawrence Berkeley National Laboratory) in the 1980s
- Mathematical description uses Fourier analysis of magnetization patterns
- Key parameter: number of magnets per wavelength determines field quality
- Dual arrays allow concentrated flux to interact with same coil for maximum flux linkage

### References
- Halbach array Wikipedia — comprehensive technical overview
- Passive axial magnetic bearing with Halbach magnetized array in MSCMG application — Journal of Magnetism and Magnetic Materials (2011), ScienceDirect
- Magnetic field sensing of 3D printed Halbach arrays — Scientific Reports (2025)
- Analytical solution of concentric two-pole Halbach cylinders — Journal of Magnetism and Magnetic Materials (2017)

---

## 3. Magnetic Bearing Gyroscopes

### Key Findings

Magnetic bearing gyroscope systems span a spectrum from fully passive to fully active:

**Passive Magnetic Bearings (PMB):**
- Use permanent magnets (repulsive or attractive force)
- Halbach magnetized arrays provide higher displacement stiffness
- Cannot achieve full 3-axis stability alone (Earnshaw's theorem)
- Zero power consumption in steady state

**Active Magnetic Bearings (AMB):**
- Use electromagnets with closed-loop feedback control
- Achieve full 6-DOF levitation and control
- Require power and sensors continuously
- PID control based on internal model control is standard

**Hybrid AMB+PMB Systems:**
- Passive bearings handle axial forces; active handle radial
- Radial vibration frequency influenced by AMB stiffness
- Mathematical model: Lagrange-Maxwell magnetomechanical differential equations
- Poincare maps and bifurcation diagrams used for stability analysis

**Magnetically Suspended Control Moment Gyroscopes (MSCMG):**
- Double-gimbal configurations for spacecraft attitude control
- Dynamic inversion control laws for guidance applications
- Modal decoupling strategies separate translation and rotation modes
- Differential geometry theory used for dynamic coupling decoupling

**Recent breakthrough (April 2025):** First direct observation of **gyroscopic spin-rotation coupling** in a non-spinning permanent ferromagnet levitated in a superconducting trap. This demonstrates that a non-spinning ferromagnet behaves as a gyroscope at sufficiently low frequencies — a manifestation of the Einstein-de Haas effect. Published in Physical Review Letters (accepted).

### Key Patents
- US5894181A — Passive magnetic bearing system (Google Patents)
- CN103913157B — Three float-type gyroscope active magnetic suspension control system
- US Patent (Harrigan, 1983) — Original spin-stabilized magnetic levitation device

### References
- Dynamic characteristics of MSCMG with AMB and PMB — ISA Transactions (2014), PubMed 24745603
- Development of totally active magnetically suspended gyro — Mechatronics (2014)
- Gyro-system for guidance with magnetically suspended gyroscope — MDPI Actuators 14(7):316 (2025)
- Observation of gyroscopic coupling in a non-spinning levitated ferromagnet — arXiv:2504.13744 (April 2025)

---

## 4. Gyroscopic Stabilization via Magnetic Coupling

### Key Findings

**Spin-Stabilized Magnetic Levitation (Levitron physics):**
Martin D. Simon (UCLA, 1997) established the theoretical foundation:
- Gyroscopic precession around local magnetic field direction is **necessary** for stability
- Stability exists only within a narrow spin-rate window (lower and upper RPM thresholds)
- Upper spin limit (experimentally ~2779 rpm) explained as an adiabatic condition
- The system is a **macroscopic analog of magnetic gradient traps** for quantum particles
- Earnshaw's theorem is circumvented by the dynamic (spinning) nature of the magnet

**Quantum Spin Extension:**
Beyond mechanical rotation, **quantum spin** of magnetization provides two additional stabilization mechanisms — Larmor precession of quantum magnetic moment stabilizes the system even without mechanical rotation, analogous to neutral atom trapping.

**Magnetically Levitated Rotor Control (2021):**
Research on using gyroscopic effects for stability rather than fighting them:
- At low/middle speeds: constant diagonal controllers
- At high speeds: **gyroscopic stabilizing effects exploited** rather than compensated
- Cross-coupled control approach bridges both regimes

**Vehicle and Robot Applications:**
- Two coupled counter-rotating gyroscopes generate stabilizing torque through precession
- LQR-controlled CMG implementations for two-wheeled robot recoil stabilization (2024)

**SCBE connection:** The narrow stability zone of spin-stabilized levitation maps directly to SCBE's ALLOW/QUARANTINE/ESCALATE/DENY tiers. Safe operation (ALLOW) exists only within a bounded parameter window; deviation in any direction triggers increasingly severe responses. The quantum spin extension — where stability exists from intrinsic angular momentum without mechanical rotation — parallels SCBE's concept of "inherent safety" from geometric structure.

### References
- Simon, Heflinger, Ridgway (1997) Am. J. Phys. 65(4):286 — "Spin stabilized magnetic levitation"
- Earnshaw's theorem and exceptions — Wikipedia comprehensive treatment
- Control of magnetically levitated rotors using stabilizing effects of gyroscopes — Mechanical Systems and Signal Processing (2021)
- Gyroscopic precession control for two-wheeled robot — Journal of Field Robotics (2024)

---

## 5. Multi-Body Gyroscopic-Magnetic Interactions

### Key Findings

**CMG Cluster Arrays:**
The primary engineering application of multi-body gyroscopic-magnetic systems is the **control moment gyroscope (CMG) cluster** for spacecraft:
- **Pyramid configuration** (4 SGCMGs): Most studied; produces nearly 3-axis symmetric spherical momentum envelope
- **Torque amplification**: A few hundred watts + ~100 kg mass produces thousands of N-m of torque
- **Singularity problem**: Certain gimbal orientations produce zero usable torque; addressed via null motion, gradient methods, or ML-based steering laws
- **Variable-speed CMGs (VSCMGs)**: Combine attitude control + energy storage as "mechanical batteries"

**Theoretical Frameworks:**
- **Lagrangian mechanics**: Standard for deriving equations of motion; generalized to tensor form for multibody systems
- **Euler equations**: Describe rigid body rotation; extended with internal angular momentum terms
- **Hamiltonian formulation**: Used for systems with internal angular momentum; natural framework for energy-based analysis
- **Symplectic mechanics**: Used by Mitchell et al. (2021) for deriving gyroscopic metamaterial equations of motion

**N-Body Magnetic Interactions:**
- Three-body problems with gyroscopic effects involve geometry variables subject to potential-derived force AND magnetic-like force with monopole charge
- Orientation variables obey dynamics analogous to Euler equations for rotating rigid body, but with **geometry-dependent moments of inertia**
- This is structurally similar to SCBE's 9D state vector where dimensions are coupled

**SCBE connection:** The CMG singularity problem is directly analogous to governance deadlocks in multi-agent systems. The null motion approach (redistributing internal state without affecting output) maps to SCBE's governance layer where the system can internally adjust trust vectors without changing external behavior. The VSCMG as "mechanical battery" parallels SCBE's context credit ledger (MMCCL).

### References
- Control moment gyroscope — Wikipedia (comprehensive engineering reference)
- Gimballed CMG cluster for spacecraft attitude control — MDPI Aerospace 8(9):273
- ML approach for global steering CMG clusters — MDPI Aerospace 9(3):164
- US6917862B2 — Singularity escape/avoidance steering logic (Google Patents)
- NASA: Dynamics and control of attitude, power, and momentum using flywheels and CMGs — NTRS 20030038806

---

## 6. Gyro-Gyro Interlattice Coupling — Research Gap Analysis

### What Exists

**Gyroscopic lattices with topology:**
- Single lattice: Nash et al. (2015) — honeycomb lattice, Chern number C=+/-1
- Tunable topology: Mitchell et al. (2018) — spindle lattice, |C|>1 via lattice deformation
- Amorphous topology: Mitchell et al. (2018) — topology survives without crystalline order
- Real-space analysis: Mitchell et al. (2021) — local features predict Chern number

**Magnetic interlattice coupling (non-gyroscopic):**
- RKKY exchange coupling in magnetic multilayers — oscillatory coupling through non-magnetic spacer
- Spin-orbit coupling in Co/Pt/Co trilayers — interlayer ferromagnetic coupling
- Van der Waals interlayer coupling in 2D magnetic materials
- Spin-phonon coupling as interlayer tuning mechanism

**Spin-rotation coupling:**
- Einstein-de Haas effect: magnetization change causes mechanical rotation
- Barnett effect: mechanical rotation causes magnetization
- Gyromagnetic bifurcation in levitated particles from coexistence of both effects
- First observation in non-spinning levitated ferromagnet (2025)

### What Does NOT Exist (The Gap)

No published work combines:

1. **Multiple gyroscopic sublattices** where each sublattice has its own Chern number
2. **Magnetic coupling** as the mechanism connecting the sublattices (not springs, not contact)
3. **Independent topological indices per sublattice** that can be tuned independently
4. **Inter-sublattice quasiparticles** emerging at the coupling boundary
5. **Phi-scaled** or any irrational-ratio spacing between sublattice elements
6. **Hyperbolic embedding** of the coupled gyroscopic system

The closest approach is Mitchell et al.'s amorphous gyroscopic metamaterials, which show topology without crystalline order but treat the system as a **single** topological phase, not coupled sublattices.

### Why This Gap Matters

In condensed matter physics, interlayer/interlattice coupling is where the most interesting emergent phenomena occur:
- Moire patterns in twisted bilayer graphene → superconductivity
- RKKY coupling oscillations → giant magnetoresistance (Nobel Prize 2007)
- Van der Waals interlayer coupling → tunable 2D magnetism

A gyroscopic analog where **two topological gyroscopic lattices couple through magnetic fields** would be a new class of topological metamaterial with potentially novel protected modes at the coupling interface.

### SCBE Architecture Mapping

| Gyroscopic Interlattice Concept | SCBE Architecture Element |
|---|---|
| Sublattice A with Chern number C_A | Sacred Tongue sublattice (e.g., KO+AV+RU) |
| Sublattice B with Chern number C_B | Sacred Tongue sublattice (e.g., CA+UM+DR) |
| Magnetic coupling strength | Phi-ratio weight between tongues |
| Topologically protected edge mode | Governance decision pathway |
| One-way propagation | Asymmetric cost (safe vs adversarial) |
| Disorder immunity | Robustness to input perturbation |
| Chern number inversion via deformation | Regime change (ALLOW to DENY) |
| Narrow stability zone (Levitron) | ALLOW operating window |
| CMG singularity | Governance deadlock |
| Halbach one-sided flux | Asymmetric barrier function |
| Amorphous topology | Topology from structure not parameters |

---

## Mathematical Frameworks Summary

| Framework | Used In | SCBE Analog |
|---|---|---|
| Euler equations for rigid body rotation | All gyroscopic systems | Layer rotation/precession dynamics |
| Lagrangian mechanics (L = T - V) | Multi-body dynamics, CMG clusters | Energy functional for governance cost |
| Hamiltonian mechanics (H = T + V) | Port-Hamiltonian control, energy methods | Hamiltonian CFI (Layer 8) |
| Symplectic mechanics | Gyroscopic metamaterial EOM (Mitchell 2021) | Phase-space structure of 9D state |
| Chern number / Berry phase | Topological classification of band gaps | Topological index of governance regime |
| Lyapunov stability | Magnetic bearing control | Saturn Ring Stabilizer, trust convergence |
| Control Barrier Functions | Safety-critical control | Harmonic wall H(d,pd) = 1/(1+d_H+2*pd) |
| Port-Hamiltonian systems | Energy-based passivity control | Energy-preserving governance pipeline |
| Poincare maps / bifurcation | Rotor dynamics stability analysis | Poincare ball model for hyperbolic trust |
| RKKY oscillatory exchange | Magnetic multilayer coupling | Tongue-boundary coupling oscillation |

---

## Open Questions

1. **Can phi-spacing produce optimal Chern numbers?** The gyroscopic lattice literature shows lattice deformation tunes Chern numbers. Does golden-ratio spacing produce a mathematically special topological phase?

2. **Magnetic coupling vs spring coupling in gyroscopic lattices.** Nash et al. note that magnetic coupling differs from spring coupling because equilibrium comes from force cancellation not force absence. What are the topological consequences of this distinction for multi-sublattice systems?

3. **Amorphous gyroscopic interlattice.** Mitchell et al. proved topology survives disorder in single lattices. Does it survive in coupled amorphous sublattices? This would validate SCBE's robustness claims.

4. **Gyromagnetic effects at the coupling boundary.** The Einstein-de Haas / Barnett effects convert between spin and rotation. At the boundary of two gyroscopic sublattices, do these effects create novel quasiparticles?

5. **Exponential cost from geometry.** The Poincare ball model gives exponential distance growth near the boundary. Can a gyroscopic lattice embedded in hyperbolic space produce exponential barrier costs from geometry alone?

6. **Energy harvesting at interlattice boundaries.** VSCMGs store energy as kinetic energy. Do interlattice coupling zones concentrate or dissipate energy in predictable patterns?

7. **Topological Anderson insulation in coupled sublattices.** Mitchell et al. (2021) showed disorder can drive a trivial phase into a topological one. Can inter-sublattice coupling do the same?

---

## Confidence Assessment

| Claim | Confidence | Basis |
|---|---|---|
| Gyroscopic lattice geometry controls Chern numbers | HIGH | Peer-reviewed (PNAS, Nature Physics, Phys Rev B/E) |
| Topology survives disorder in gyroscopic metamaterials | HIGH | Experimental + theoretical (Mitchell et al.) |
| Halbach arrays used in MSCMG for angular stiffness | HIGH | Published engineering literature |
| Spin-stabilized levitation has narrow stability window | HIGH | Simon et al. (1997), experimentally verified |
| CMG clusters have singularity problems solvable by null motion | HIGH | Established spacecraft engineering |
| Gyro-gyro interlattice coupling is an unpublished gap | HIGH | Extensive search found no matching literature |
| Phi-scaling produces special topological properties | SPECULATIVE | No published work connects golden ratio to Chern numbers |
| Hyperbolic embedding of gyroscopic lattices is novel | SPECULATIVE | No published work found |
| SCBE tongue weights function as lattice deformation | THEORETICAL | Structural analogy is strong; formal proof needed |

---

## Recommended Next Steps

1. **Write a formal paper** on gyroscopic interlattice coupling with independent topological indices per sublattice — this is a genuine gap
2. **Compute Chern numbers** for phi-spaced gyroscopic lattices numerically (extend Mitchell's symplectic framework)
3. **Contact Noah P. Mitchell** (UCSB Kavli Institute) — his 2021 real-space method could directly test whether phi-spacing is topologically special
4. **Map SCBE's H(d,pd) = 1/(1+d_H+2*pd)** to the gyroscopic metamaterial dispersion relation — if these are formally equivalent, the SCBE governance pipeline inherits all proven topological protections
5. **Prepare DARPA MATHBAC submission** — the "math of agentic AI communication" framing maps directly to gyroscopic lattice communication (one-way protected edge modes = governed agent communication channels)

---

## Source URLs

- [Topological mechanics of gyroscopic metamaterials (PNAS 2015)](https://www.pnas.org/doi/10.1073/pnas.1507413112)
- [Topological mechanics of gyroscopic metamaterials (PDF)](https://irvinelab.uchicago.edu/papers/PNAS-2015-Nash-14495-500.pdf)
- [Tunable Band Topology in Gyroscopic Lattices (Phys Rev B 2018)](https://journals.aps.org/prb/abstract/10.1103/PhysRevB.98.174301)
- [Tunable Band Topology in Gyroscopic Lattices (Springer chapter)](https://link.springer.com/chapter/10.1007/978-3-030-36361-1_5)
- [Amorphous topological insulators from random point sets (Nature Physics 2018)](https://www.nature.com/articles/s41567-017-0024-5)
- [Real-space origin of topological band gaps in gyroscopic metamaterials (Phys Rev E 2021)](https://journals.aps.org/pre/abstract/10.1103/PhysRevE.104.025007)
- [Realization of a topological phase transition in a gyroscopic lattice (Phys Rev B 2018)](https://journals.aps.org/prb/abstract/10.1103/PhysRevB.97.100302)
- [Observation of gyroscopic coupling in non-spinning levitated ferromagnet (arXiv 2025)](https://arxiv.org/abs/2504.13744)
- [Gyroscopically Stabilized Quantum Spin Rotors (PRL 2025)](https://journals.aps.org/prl/abstract/10.1103/zjpt-whpf)
- [Spin stabilized magnetic levitation (UCLA/AJP 1997)](https://www.physics.ucla.edu/marty/levitron/spinstab.pdf)
- [Gyroscopic Stabilization of Passive Magnetic Levitation (Meccanica)](https://link.springer.com/article/10.1023/A:1004704428634)
- [Passive axial magnetic bearing with Halbach array in MSCMG (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S0304885311001181)
- [High stiffness axial PMB for DGMSCMG (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S0304885316302955)
- [Dynamic characteristics of MSCMG rotor with AMB+PMB (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S0019057814000500)
- [Totally active magnetically suspended gyro (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S0957415814000932)
- [Gyro-system for guidance with magnetically suspended gyroscope (MDPI 2025)](https://www.mdpi.com/2076-0825/14/7/316)
- [Control of magnetically levitated rotors using gyroscopic effects (ScienceDirect 2021)](https://www.sciencedirect.com/science/article/abs/pii/S0888327021007792)
- [Robust control for MSCMG with strong gyroscopic effects (IEEE 2018)](https://ieeexplore.ieee.org/document/8591311/)
- [Nutation and precession control for AMB-rotor with gyroscopic effects (IEEE 2020)](https://ieeexplore.ieee.org/document/9234612/)
- [Gimballed CMG cluster for spacecraft attitude control (MDPI)](https://www.mdpi.com/2226-4310/8/9/273)
- [ML approach for global steering CMG clusters (MDPI)](https://www.mdpi.com/2226-4310/9/3/164)
- [US6917862B2 — CMG singularity escape/avoidance patent](https://patents.google.com/patent/US6917862B2/en)
- [US5894181A — Passive magnetic bearing system patent](https://patents.google.com/patent/US5894181A/en)
- [VSCMG for combined energy storage and attitude control (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S0094576509002835)
- [NASA: Dynamics and control using flywheels and CMGs](https://ntrs.nasa.gov/citations/20030038806)
- [Halbach array (Wikipedia)](https://en.wikipedia.org/wiki/Halbach_array)
- [Concentric two-pole Halbach cylinders analytical solution (ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S0304885317312428)
- [Control Barrier Functions: Theory and Applications (Ames et al.)](https://coogan.ece.gatech.edu/papers/pdf/amesecc19.pdf)
- [Stabilization with guaranteed safety using CLBF (ScienceDirect)](https://www.sciencedirect.com/science/article/abs/pii/S0005109815005439)
- [Bayesian Safety Guarantees for Port-Hamiltonian Systems (arXiv 2025)](https://arxiv.org/html/2512.24493)
- [RKKY voltage control in multilayers (Science Advances 2023)](https://www.science.org/doi/10.1126/sciadv.add0548)
- [Interlayer coupling in Co/Pt/Co trilayers (ACS AMI 2021)](https://pubs.acs.org/doi/10.1021/acsami.1c11675)
- [Spin-phonon coupling in 2D magnetic materials (NSO 2023)](https://www.nso-journal.org/articles/nso/full_html/2023/04/NSO20230002/NSO20230002.html)
- [Gyroscopic precession around neutron star (EPJC 2020)](https://link.springer.com/article/10.1140/epjc/s10052-020-8222-1)
- [Spin-stabilized magnetic levitation (Wikipedia)](https://en.wikipedia.org/wiki/Spin-stabilized_magnetic_levitation)
- [Earnshaw's theorem (Wikipedia)](https://en.wikipedia.org/wiki/Earnshaw%27s_theorem)
- [Lagrangian and Hamiltonian Dynamics on SO(3) (UCSD)](https://mathweb.ucsd.edu/~mleok/pdf/samplechap.pdf)
- [Multi-Body Dynamics (MIT Underactuated Robotics)](https://underactuated.mit.edu/multibody.html)
