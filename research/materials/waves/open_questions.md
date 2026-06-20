# Waves Open Questions

Created: 2026-06-15

## Product Questions

1. Should `AI Waves Lab` be its own top-level product page, or should it ship as a room inside `AI Materials Bench` first?
2. Should the first visual be fiber/waveguide propagation, optical transistor bistability, or general interference/refraction?
3. Should the output target be education, engineering review, or AI-training packet generation?

## Technical Questions

1. Should the first backend be pure JavaScript for Vercel simplicity, or should it call the existing Python physics modules?
2. Which formulas from `waves_optics.py` should be treated as v1 stable?
3. What input validation envelope should be used for wavelength, refractive index, fiber length, attenuation, power, and frequency?
4. How should photonic accelerator route decisions be normalized with Materials Bench receipts?
5. Should the optical transistor simulator be exposed through a CLI wrapper first, then called by the web API?

## Research Questions

1. Which external photonics sources should be treated as primary references for v1 citations?
2. Are there measured provider profiles available for Q.ANT, Lightmatter, Intel photonics, or other photonic accelerators?
3. What is the cleanest public dataset for fiber impairment classification: chromatic dispersion, PMD, attenuation, Kerr nonlinearity, splice loss?
4. Can the Universal Propagation Grammar become a training schema for wave/fiber examples?

## Next Checks

1. Run the existing photonic accelerator tests.
2. Add direct tests for any JS formula port from `waves_optics.py`.
3. Compare a few formula outputs against a known physics reference before presenting them on the product page.
4. Add a source tag per calculation so receipts can say whether a result came from local formula, simulator, user input, or assumption.
