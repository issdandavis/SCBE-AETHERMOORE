# Waves Research Brief

Created: 2026-06-15

Question: What are the next build steps for SCBE wave, optics, fiber, and photonic materials work?

## Short Answer

Build a product-facing `AI Waves Lab` as the next module beside AI Materials Bench and AI Chemistry Set.

The useful scope is:

1. Fiber / waveguide propagation.
2. Optical and acoustic wave visualization.
3. Photonic accelerator routing.
4. Optical-transistor simulation mode.
5. Source-backed receipts that show formulas, assumptions, and limits.

Do not lead with hardware claims. Lead with working calculations, diagrams, scenario presets, and verified receipts.

## What Already Exists Locally

### Wave and Optics Formula Base

Source:

`src\physics_sim\waves_optics.py`

Existing useful functions include:

- wave velocity
- wavelength / frequency transforms
- angular frequency
- wave number
- phase velocity
- group velocity
- two-source interference
- thin-film interference
- diffraction
- Snell's law
- critical angle
- Brewster angle
- numerical aperture
- Doppler shift
- beat frequency

Next step:

Expose these through an API handler and visual page, not as isolated Python utilities.

### Optical Transistor Simulator

Source:

`src\physics_sim\optical_transistor.py`

Existing useful models include:

- nonlinear cavity round-trip map
- bistability checks
- fixed point stability
- Adler injection locking
- multi-beam gain competition
- cascadability verdict
- null-gate controls
- material-regime reporting

Next step:

Make this an "Optical Switch Room" inside the Waves Lab. The user changes gain, absorber, detuning, and pump values; the UI shows whether the system is bistable, locked, cascadable, or invalid.

### Photonic Accelerator Lane

Source:

`docs\specs\PHOTONIC_ACCELERATOR_LANE.md`

Implementation:

`src\tokenizer\accelerator_routing.py`

Tests:

`tests\tokenizer\test_accelerator_routing.py`

Existing useful behavior:

- routes packets to `PHOTONIC_NPU`, `PHOTONIC_NPU_WITH_VERIFY`, `GPU`, `CPU`, `HOLD`, or fallback
- reports fit score
- reports precision mismatch
- reports branching / memory / latency / energy failure modes
- marks hardware claim as simulated

Next step:

Wire this into the Waves Lab as a "Photonic Route Receipt" panel. It should stay provider-neutral unless measured provider data exists.

### Universal Propagation Grammar

Source:

`C:\Users\issda\Documents\Avalon Files\System Library\Repository Mirror\docs\specs\UNIVERSAL_PROPAGATION_GRAMMAR.md`

Useful fiber optics fields:

- carrier: fiber core / waveguide mode / optical channel
- excitation: laser launch / modulation / amplifier stage
- distortion: chromatic dispersion, PMD, Kerr effects, attenuation
- coupling: cross-phase modulation / amplifier-chain interactions
- observables: OTDR-like traces, BER/Q trajectory, group delay, polarization state

Next step:

Use this as the scenario schema for the Waves Lab. It turns fiber and wave demos into structured packets an AI can reason over.

## External Grounding

External research supports three product-safe directions:

1. Integrated photonics is a real field, especially thin-film lithium niobate and silicon photonics.
2. Photonic neural networks are actively researched, but practical deployment depends on precision, calibration, nonlinearity, memory movement, and system integration.
3. Fiber sensing and waveguide telemetry are strong near-term software products because they can be visualized, simulated, and receipt-checked without needing exotic hardware access.

## Product Direction

### AI Waves Lab

Sellable surface:

- "Describe a wave, fiber, photonic, or optical-switch concept. Get a diagram, calculations, assumptions, failure modes, and a receipt."

Primary rooms:

- `fiber-room`
- `interference-room`
- `optical-switch-room`
- `photonic-route-room`
- `audio-wave-room`

Backend endpoints:

- `api/agent/ai-waves-lab.js`
- `api/agent/ai-waves-lab-page.js`

Frontend:

- `docs/ai-waves-lab.html`

Core receipt fields:

- `scenario`
- `inputs`
- `assumed`
- `calculations`
- `diagram`
- `failure_modes`
- `source_tags`
- `validity`

## Build Order

1. Add an API route that wraps a small safe subset of `waves_optics.py` formulas in JavaScript.
2. Add scenario presets: fiber link, two-source interference, prism/refraction, optical switch, photonic route.
3. Add a visual canvas with wavefronts, path rays, and signal panels.
4. Add a receipt panel with assumptions and validity limits.
5. Bridge the existing Python optical transistor simulator through CLI or subprocess only after the simple JS route works.
6. Add tests for formula correctness and invalid/extreme input handling.
7. Add a product page card linking Materials Bench, Chemistry Set, and Waves Lab as the "AI Science Set."

## Hard Boundaries For Product Copy

Use:

- formulas
- calculations
- diagrams
- assumptions
- educational scenarios
- receipt-backed reasoning

Avoid:

- unverified performance claims
- real-hardware claims without measurements
- procedure-like chemistry or fabrication instructions
- military framing
- "physical security as proven hardware" claims unless measured

## Immediate Next Commit

Recommended next commit:

`feat(waves): add AI Waves Lab research packet and route plan`

Then implementation commit:

`feat(waves): ship AI Waves Lab page and calculator endpoint`
