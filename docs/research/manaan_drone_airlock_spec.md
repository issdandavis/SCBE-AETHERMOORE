# Manaan Drone Airlock Spec

Status: concept specification / prototype scaffold.
Claim boundary: this is not certified flight hardware, not a human airlock, and not a solved vacuum door. It is a bounded architecture for simulation and bench testing of a drone-scale pressure-interface idea.

## Objective

Build a drone-first pass-through interface that minimizes consumable loss while moving a small vehicle between a pressurized station volume and an external vacuum or low-pressure volume.

The system is not trying to create a perfect forcefield. It is trying to replace a briefly open gas hole with a controlled, recoverable displacement event:

1. Standby leak is handled by geometry and differential pumping.
2. Transit blowout is avoided by making the final interface a liquid plug instead of an open gas aperture.
3. Drag-out loss is recovered by wipers, wettability gradients, and a return loop.
4. The drone shape and speed are treated as part of the seal design, not as an afterthought.

## Non-Goals

- No crew passage.
- No doorway-scale membrane.
- No water-based mechanical fluid.
- No claim of full atmosphere hold across an unsupported large liquid span.
- No plasma window, laser gate, or energy-wall framing.
- No claim that ferrofluid, PFPE, or ionic liquid alone proves the integrated system.

## Baseline Architecture

The useful stack is a short tunnel with staged pressure control and one recoverable liquid boundary.

1. **Hard frame**
   - Rigid pressure-rated ring.
   - Replaceable insert cartridge for the liquid plug.
   - Mechanical hard-close shutter for fault isolation.

2. **Differential pumping staircase**
   - Two or more short cavities before the plug.
   - Each cavity has its own pressure sensor and pump path.
   - Purpose: reduce standby gas load and keep the liquid plug from being the only boundary.

3. **Liquid plug cartridge**
   - Candidate fluids: PFPE oil, compatible ionic liquid, or PFPE-carrier ferrofluid.
   - Water is excluded because vapor pressure, freezing, and contamination risks are wrong for vacuum service.
   - The plug must be replaceable because contamination is expected during early tests.

4. **Confinement field / capillary support**
   - Ferrofluid version: magnetic pole pieces or coils shape the plug and pull it back after displacement.
   - Nonmagnetic PFPE/ionic version: capillary mesh, wetting pattern, and mechanical lip geometry carry more of the load.
   - The field or mesh is not allowed to be the only closeout in a fault; the hard shutter remains the safety boundary.

5. **Recovery wiper loop**
   - Entry and exit wipers remove drag-out film from the drone body.
   - Wiper surface uses wettability gradients: hydrophobic/nonwetting where release matters, fluid-loving where return flow matters.
   - Collected fluid drains or wicks back into the cartridge reservoir.

6. **Drone interface geometry**
   - Slow dartfish-like body profile for liquid transit only.
   - Pointed entry reduces splash and plug rupture.
   - Long tapered tail reduces film pinch-off and droplet shedding.
   - External coating must be selected for low retained film with the chosen plug fluid.

## Operating States

### 0. Fault-Closed

Hard shutter closed. Plug cartridge isolated. Pumps may run only for recovery or cleanup.

Entry conditions:
- pressure sensor disagreement,
- excessive drag-out loss,
- plug-level sensor out of range,
- pump failure,
- field failure,
- unexpected object in tunnel.

### 1. Standby-Sealed

The liquid plug is formed, field or capillary confinement is active, and the differential cavities are held at target pressures.

Success criteria:
- pressure decay stays below the test threshold,
- plug level and shape are inside tolerance,
- no droplet shedding detected,
- recovery reservoir is not overfull.

### 2. Pre-Transit

Drone enters the inner guide and slows to transit speed. The staircase pressures are adjusted so the final differential across the plug is minimized for the moment of displacement.

Control targets:
- align drone centerline,
- confirm drone coating ID / allowed geometry,
- reduce relative pressure jump where practical,
- pre-wet or condition the wiper if the test recipe calls for it.

### 3. Plug Displacement

The drone nose contacts and displaces the liquid plug. The system should behave like a self-healing wet seal, not an open door.

Critical rule:
There must not be a free gas annulus from station air to vacuum. If the plug opens into a gas gap, the architecture has failed into an ordinary orifice.

### 4. Film Recovery

As the drone exits, the tapered tail and wiper recover fluid. This state is where the main consumable loss is measured.

Primary metric:
- milligrams or microliters of plug fluid lost per transit.

Secondary metrics:
- external contamination on the drone,
- droplet count,
- reseal time,
- pressure transient amplitude.

### 5. Reseal / Verify

The plug reforms under field, capillary, and reservoir action. Pumps restore the staircase to standby pressures.

The system does not return to Standby-Sealed until:
- pressure trend stabilizes,
- plug imaging or level signal confirms continuity,
- no free droplets are detected,
- recovered-fluid mass balance is inside tolerance.

## Physics Ledger

| Term | What It Controls | Design Lever | Failure Mode |
| --- | --- | --- | --- |
| Conductance | Standby leakage through gaps and staged apertures | smaller apertures, more stages, higher pump speed | pumps cannot keep up |
| Choked flow | Catastrophic leak through an open gas aperture | avoid free gas annulus; keep liquid plug continuous | transit becomes ordinary venting |
| Vapor pressure | Fluid loss to vacuum | PFPE / ionic liquid selection, temperature control | fluid evaporates or contaminates surfaces |
| Capillary number | Film thickness dragged out by moving drone | slow transit, low-viscosity compatible fluid, coating choice | thick film leaves with drone |
| Weber number | Splashing and droplet ejection | slow entry, pointed nose, smooth acceleration | plug ruptures into droplets |
| Magnetic pressure | Ferrofluid plug hold and return force | pole geometry, field strength, carrier fluid | field cannot reseal at scale |
| Wetting hysteresis | Whether fluid sticks or releases | surface chemistry, microtexture, wiper material | film remains on drone |
| Microgravity capillarity | Plug shape and droplet behavior | cartridge lip geometry, mesh, return wick | plug balls up or detaches |

## Materials Shortlist

### Candidate Plug Fluids

- PFPE oil: strong first candidate for low vapor pressure and vacuum compatibility.
- PFPE-carrier ferrofluid: candidate when magnetic confinement is required.
- Ionic liquid: candidate when vapor pressure dominates, with special attention to viscosity, toxicity, and surface cleanup.

### Excluded For First Prototype

- Water: wrong vapor pressure and phase behavior.
- Ordinary hydrocarbon oils: higher contamination and outgassing risk.
- Unbounded aerogel membrane: useful as insulation or support material, not as the primary seal.

### Supporting Materials

- Aerogel or multilayer insulation around cold coils or thermal-control zones.
- Superhydrophobic / oleophobic coatings on drone regions where release is required.
- Fluid-loving wick paths where recovery is required.
- Replaceable sacrificial wiper lips for early contamination testing.

## Drone Requirements

Minimum drone assumptions for the first simulated and bench-scale program:

- rigid axisymmetric or near-axisymmetric body,
- no exposed cavities that trap plug fluid,
- slow controlled transit,
- known surface coating,
- guide-compatible nose and tail geometry,
- machine-readable ID before entry,
- post-transit contamination inspection.

Recommended body features:

- tapered nose for low-disturbance entry,
- long tapered tail for clean film closure,
- removable witness coupons on the skin,
- alignment fiducials for optical tracking,
- no spinning during plug transit unless explicitly tested.

## Control And Sensor Model

Minimum sensor set:

- pressure sensor per staircase cavity,
- plug reservoir level,
- plug cartridge temperature,
- magnetic coil current and temperature if used,
- optical or capacitive plug-continuity sensor,
- drone position and velocity,
- recovered-fluid mass or level,
- droplet / contamination witness sensor near the exit.

Minimum control outputs:

- pump speed or valve state per cavity,
- hard shutter open/close,
- magnetic confinement current if used,
- wiper engagement pressure,
- drone go/no-go signal,
- fault lockout.

## First Prototype Ladder

### Prototype A: No Vacuum, Visible Fluid Bench

Purpose: learn film drag-out and wiper recovery before adding pressure risk.

Setup:
- clear cartridge,
- surrogate low-volatility oil,
- scaled dart body,
- camera,
- mass before/after.

Pass condition:
- repeatable plug displacement and reseal,
- measured recovered fraction,
- no uncontrolled droplet shedding at target speed.

Kill condition:
- body routinely carries unrecoverable fluid slugs,
- plug breaks into droplets instead of reforming,
- wiper adds more contamination than it recovers.

### Prototype B: Low Differential Pressure

Purpose: add pressure and pump dynamics without full atmosphere-to-vacuum risk.

Setup:
- small pressure difference,
- one pump cavity,
- hard-close shutter,
- same body and fluid measurement as Prototype A.

Pass condition:
- pressure transient is bounded,
- plug stays continuous,
- recovery mass balance remains measurable.

Kill condition:
- leak behaves like an open orifice,
- pump load dominates,
- reseal time is inconsistent.

### Prototype C: Vacuum-Compatible Materials

Purpose: test the actual fluid/coating/wiper stack in a controlled vacuum chamber.

Setup:
- PFPE or ionic candidate,
- real coating coupons,
- vacuum witness plates,
- residual contamination check.

Pass condition:
- low mass loss,
- acceptable contamination,
- no material incompatibility.

Kill condition:
- fluid migrates to unacceptable surfaces,
- coating degrades,
- outgassing or residue invalidates the chamber.

### Prototype D: Ferrofluid Variant

Purpose: determine whether magnetic confinement beats passive capillary/mechanical confinement.

Gate:
The ferrofluid version must reduce reseal time, loss, or plug instability enough to justify field hardware and contamination risk.

Kill condition:
If the passive PFPE/ionic cartridge performs similarly, do not keep magnetic complexity.

## Success Metrics

Primary:

- gas lost per transit,
- plug fluid lost per transit,
- reseal time,
- number of safe repeated transits before cartridge service.

Secondary:

- pump energy per transit,
- coil energy per transit if magnetic,
- recovered-fluid fraction,
- drone contamination mass,
- failure-to-hard-close time,
- cleaning and cartridge replacement time.

## Main Risks

1. Large-span confinement does not scale.
2. Drone exits contaminated enough to make the design operationally poor.
3. Plug sheds droplets in microgravity.
4. Wiper recovery is worse than a normal mini-airlock.
5. Field hardware is heavier and more failure-prone than a mechanical cartridge.
6. Differential pumping cavities do not reduce the load enough for the added complexity.
7. Surface coatings work in bench fluid but fail after repeated exposure.

## Honest Comparison Baselines

The Manaan interface only earns a build path if it beats at least one simpler baseline:

- small conventional cycling airlock,
- capture canister that docks around the drone,
- mechanical iris plus purge/repressurize cycle,
- tethered exterior bay with no pass-through,
- disposable contamination sleeve.

The first comparison should be against a small cycling airlock, because that is the obvious practical competitor.

## Next Work

1. Define a toy model for gas lost per transit versus a small cycling airlock.
2. Define a film-loss model using body speed, fluid viscosity, surface tension, and effective tail radius.
3. Build a bench recipe for Prototype A with a nonhazardous surrogate fluid.
4. Add a state-machine sketch for Standby, Pre-Transit, Displacement, Recovery, Reseal, and Fault-Closed.
5. Decide whether the first branch is passive PFPE/ionic cartridge or ferrofluid cartridge.

