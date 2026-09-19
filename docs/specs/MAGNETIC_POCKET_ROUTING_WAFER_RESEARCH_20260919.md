# Magnetic Pocket Routing and Wafer Prototype Boundary

**Status:** research specification; software evidence exists, physical device unbuilt

**Date:** 2026-09-19

**Scope:** magnetic pocket nodes, field-directed routing, fluid actuation, and the Clay wafer design

## Engineering interpretation

The useful form of the concept is a closed-loop physical state machine. A goal does not
directly move matter. Governance converts an explicit goal and measured state into a bounded
control vector; coils or electrodes create a field; physical nodes move or switch; sensors
measure the result; and the controller accepts, corrects, or rejects the transition.

| Design image | Engineering variable |
|---|---|
| pocket node | droplet trap, domain-wall site, nanomagnet, or skyrmion confinement region |
| subtle magnetic shift | bounded coil current, voltage pulse, or bias-field change |
| system intention | explicit goal vector plus policy constraints |
| lever or ball bearing | mobile droplet, domain wall, or other measured state carrier |
| dense/loose fluid | field-dependent flow or yield response; material must be specified |
| wafer neighborhood | graph edge implemented by a wire, field coupling, waveguide, or software route |

A minimal controller can be written as

\[
\mathbf B(\mathbf x,t)=\sum_i u_i(t)\,\mathbf b_i(\mathbf x),
\qquad
\mathbf u_t^*=\arg\min_{\mathbf u\in\mathcal U}
\left\|F(\mathbf s_t,\mathbf u)-\mathbf s_{goal}\right\|_Q^2
+\lambda\|\mathbf u\|_2^2,
\]

where `s_t` is the sensed physical state, `u` is a bounded actuator command, `F` is a
measured transition model, and `U` contains current, temperature, timing, and policy limits.
This formalizes "nodes drifting with intention" without giving an unmeasured internal state
direct control of hardware.

## What is already supported locally

1. `C:\dev\clay-wafer-net\clay_wafer_net\magnetic_logic.py` demonstrates the logical
   boundary of a threshold-coupled magnetic model. Three ferromagnetic inputs implement a
   monotone majority function. Antiferromagnetic coupling plus bias implements NAND and NOR.
   A single threshold node cannot implement XOR; a two-layer construction does so exactly.
   Clocking and fabrication remain outside that proof.
2. `C:\dev\ferro_field.py` maps a small command grammar into field surfaces and rejects an
   unknown operation. It is a control-language simulation, not a material or device result.
3. `C:\dev\ferrofluid_habitat_control_SPEC.md` already separates controllable magnet arrays
   and simulated surfaces from speculative integrated hardware.
4. `C:\dev\tongue-compiler\artifacts\wafer_nvidia_review_20260912\REVIEW.md` found a real
   64-expert/top-4 software router and later repair evidence found finite router/gate gradients.
   It found no CUDA kernel, RTL, physical layout, or device benchmark. The wafer is presently a
   neural routing architecture.

## What published experiments establish

- Rotating magnetic fields and patterned tracks have moved ferrofluid droplets through AND,
  OR, XOR, NOT, and NAND gates, fanout, a full adder, a flip-flop, and a finite-state machine.
  This strongly supports a tabletop routing demonstrator, but the reported platform operated
  at fluidic rather than processor-clock timescales.
- A water-based ferrofluid has experimentally shown memristive behavior, short- and long-term
  memory, and reservoir-computing classification with electrical programming and RF readout.
- Nanomagnetic logic chains have shown sub-nanosecond signal propagation under explicit
  clocking. Domain-wall prototypes have shown inversion, buffering, gain, fanout, and cascaded
  room-temperature operation.
- Geometrically confined magnetic skyrmions have performed physical reservoir computing. Their
  nonlinear trajectories and relaxation toward a stable region closely match the "pocket
  node" intuition, although the demonstrated systems require specialized thin films and
  readout hardware.

These are adjacent results. None demonstrates the full SCBE/Clay wafer.

## Material choice matters

Do not treat ferrofluid, magnetorheological fluid, and a spintronic thin film as interchangeable.

| Medium | Best fit here | Main limitation |
|---|---|---|
| ferrofluid droplets | visible routing, logic, memory experiments, education | slow, surface/flow variation, bulky sensing |
| magnetorheological fluid or elastomer | variable damping, stiffness, clutching, and actuation | thermal and mechanical response is far slower than digital logic |
| nanomagnets/domain walls | nonvolatile Boolean logic and memory | clocking, fabrication variation, write current, fanout |
| skyrmions/spin waves | nonlinear reservoirs and wave/phase routing | specialized materials, noise, readout, integration maturity |
| CMOS/GPU | controller, sensing, optimization, and high-throughput arithmetic | does not itself test the physical-field hypothesis |

For the user's "loosen and densify" actuator, magnetorheological material is the closer
engineering category. For mobile information packets, ferrofluid droplets are closer. For an
eventual chip, spintronic films are the relevant scale.

## Buildable hybrid prototype

The first physical machine should be a peripheral coprocessor, not a replacement PC.

```mermaid
flowchart LR
    G[Verified goal and policy] --> C[Bounded controller]
    C --> D[Coil or electrode drivers]
    D --> P[Magnetic pocket array]
    P --> S[Camera, Hall, resistance, or RF readout]
    S --> E[State estimator]
    E --> C
    E --> R[Signed transition receipt]
    R --> G
```

The host PC performs policy, optimization, logging, and training. The physical array supplies
nonlinearity, hysteresis, memory, routing, or actuation. This division lets the idea be tested
without pretending a fluid board can match a GPU.

## Acceptance ladder

1. **Simulation:** predict each transition, include hysteresis/noise, and reproduce NAND, NOR,
   XOR-through-depth, reset, and HOLD states. Compare against a size-matched digital control.
2. **Macroscopic pocket board:** demonstrate closed-loop routing for at least 1,000 transitions;
   publish transition error, settling time, energy, temperature, and cross-talk. Repeat across
   at least three runs and devices.
3. **Computation:** demonstrate universal gates, fanout of at least two, state retention, reset,
   and cascaded operation. A successful gate in isolation is insufficient.
4. **Reservoir task:** use a fixed physical reservoir plus trained linear readout. Beat both a
   no-reservoir baseline and a parameter-matched software control by more than two pooled
   standard deviations; otherwise report `UNDERPOWERED` or `NO_LIFT`.
5. **Chip path:** supply a device model, SPICE or micromagnetic co-simulation, clock network,
   I/O circuit, PDK-compatible layout, timing/power analysis, and fabrication partner.
6. **Wafer performance:** only claim an accelerator after a compiled kernel beats the matched
   dense/sparse baseline in wall time, energy, memory traffic, and task quality on the same
   hardware.

## Wafer relationship to current NVIDIA systems

The shared problem is routing useful work and data among many compute units. NVIDIA's current
platforms solve this through extreme codesign of GPUs, CPUs, switches, networking, memory, and
software. The Clay wafer's current 64-cell/top-4 expert router is a software model of task
placement. A graph coordinate is not a physical wire, six readout views are not six processors,
and signed trits do not reduce storage unless an implemented encoding and kernel prove it.

The near-term research claim is therefore:

> SCBE can use a governed control language to address a simulated or tabletop magnetic state
> array, while the wafer router can be evaluated as a sparse software scheduler. Physical
> acceleration remains an experimental hypothesis.

## Primary sources

- Katsikis, Cybulski, and Prakash, [Synchronous universal droplet logic and control](https://www.nature.com/articles/nphys3341), *Nature Physics* 11 (2015).
- Crepaldi et al., [Experimental Demonstration of In-Memory Computing in a Ferrofluid System](https://pubmed.ncbi.nlm.nih.gov/36919899/), *Advanced Materials* 35 (2023), DOI 10.1002/adma.202211406.
- Colci et al., [Sub-nanosecond signal propagation in anisotropy-engineered nanomagnetic logic chains](https://www.nature.com/articles/ncomms7466), *Nature Communications* 6 (2015).
- Currivan-Incorvia et al., [Logic circuit prototypes for three-terminal magnetic tunnel junctions with mobile domain walls](https://www.nature.com/articles/ncomms10275), *Nature Communications* 7 (2016).
- Beneke et al., [Gesture recognition with Brownian reservoir computing using geometrically confined skyrmion dynamics](https://www.nature.com/articles/s41467-024-52345-y), *Nature Communications* 15 (2024).
- NVIDIA, [Vera Rubin platform production announcement](https://nvidianews.nvidia.com/news/vera-rubin-full-production-agentic-ai-factory) (2026).

This specification records engineering connections and disconfirming tests. It is not evidence
that the integrated device has been built and is not a patent-novelty determination.
