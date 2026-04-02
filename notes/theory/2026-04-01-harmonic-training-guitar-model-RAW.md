# Harmonic Training — Guitar Model

Status: RAW INTUITION (unvalidated — research pending)
Source: Issac Davis, April 1, 2026
Method: "L7 deep dive" — raw thoughts first, research second

---

## The Raw Idea

What if you treat multi-method AI training like playing a guitar?

### Six Strings = Six Tongues = Six Training Methods

Each Sacred Tongue maps to a training method. They're not run sequentially — they're played as CHORDS. All methods active simultaneously with phi-weighted mixing.

| String | Tongue | Training Method | What It Teaches |
|--------|--------|----------------|-----------------|
| 1 (low E) | KO (Intent) | SFT | "What to say" |
| 2 (A) | AV (Transport) | Distillation | "How good models talk" |
| 3 (D) | RU (Policy) | Constitutional AI | "What NOT to say" |
| 4 (G) | CA (Compute) | DPO | "Which answer humans prefer" |
| 5 (B) | UM (Security) | GRPO | "Rank without reward model" |
| 6 (high E) | DR (Structure) | RLHF | "Optimize against reward signal" |

### Chords = Training Mixtures

A chord is a specific combination of string activations. In training:

```
C_major = weighted mix of [SFT high, DPO medium, CAI low]
Am      = weighted mix of [CAI high, GRPO medium, SFT low]
```

Different "songs" (training curricula) use different chord progressions.

### Modes = Training Personalities

Musical modes start on different scale degrees but use the same notes. In training:

- **Ionian (major)** = balanced, general-purpose training
- **Dorian** = slightly darker, more policy-heavy
- **Phrygian** = aggressive, security-focused
- **Lydian** = bright, creative, exploration-heavy
- **Mixolydian** = dominant, assertive responses
- **Aeolian (minor)** = conservative, safety-first
- **Locrian** = unstable, adversarial training (red team)

Same training methods, different emphasis patterns. The MODE determines the personality of the resulting model.

### Harmonics = Multi-View Triangulation

When you pluck a guitar string, you don't just get the fundamental frequency. You get the entire overtone series: f, 2f, 3f, 4f...

In training:
- The fundamental = L3 (expression, surface text)
- 2nd harmonic = L2 (governance, what should this do?)
- 3rd harmonic = L1 (tongue encoding, cross-representation)
- 4th harmonic = L0 (byte substrate, raw structure)

Multi-view training IS the overtone series. You're not just training on the fundamental — you're training on the full harmonic spectrum of each example.

### Sympathetic Resonance = Cross-Method Transfer

On a guitar, when you pluck the low E string, the high E string vibrates too (sympathetic resonance) because they share frequency relationships.

In training: when SFT improves the model's ability to generate text, DPO's preference signal becomes more effective because there's a better base distribution to choose from. They RESONATE.

The 14% improvement from multi-view training might be measuring this sympathetic resonance between training views.

### Scales Across the Fretboard = Layers Across the Pipeline

Same string (method), different fret position (layer). Playing SFT at L0 sounds different from SFT at L3:

- SFT at L0: learn byte-level patterns of good code
- SFT at L1: learn tongue-tokenized representations of good code
- SFT at L2: learn governance decisions on good code
- SFT at L3: learn to generate good code directly

Same method, different view. The fretboard IS the layer stack.

### The Phi Connection

Guitar tuning uses frequency ratios. Standard tuning is based on perfect fourths (4:3 ratio) and a major third (5:4).

The Sacred Tongues use phi ratios: 1, φ, φ², φ³, φ⁴, φ⁵.

Question: what if phi-ratio tuning produces better training "harmony" than equal-weighted mixing? The 14% result might be evidence that phi-weighted mixing IS the natural tuning system for multi-method training.

### What This Predicts

1. Running all 6 methods as a phi-weighted chord should beat any single method
2. Different "modes" (emphasis patterns) should produce measurably different model personalities
3. The overtone series (multi-view) should amplify the chord effect
4. Sympathetic resonance means improving one method improves adjacent methods
5. There should be an optimal "tuning" — the phi ratios might be it

### Open Questions

- What's the musical equivalent of the harmonic wall function?
- Do modes map to the personality matrix axes?
- Is there a "key change" operation that transforms one training personality into another?
- What does "dissonance" mean in training? Is it useful (adversarial) or harmful (conflicting gradients)?
- Can you "transpose" a trained model — shift its personality without retraining?

---

## Method Note

This is "L7" style thinking: raw intuition from physical analogy, no references, no validation. The research agent is running now to find the real music theory math. After that, we see what survives contact with reality.

The pattern: D&D campaign → security framework. Manhwa → orientation. DNA → trainable absence. Guitar → multi-method training. The analogy comes first. The math confirms or kills it.
