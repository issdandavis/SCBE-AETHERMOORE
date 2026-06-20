# Audio Field Observable Bridge

Date: 2026-05-31

## Claim Boundary

Audio is a wave-observation lane. This bridge does **not** claim that arbitrary
sound can reveal an arbitrary magnetic field. It extracts acoustic observables
and only emits magnetic or field-coupling proxies when a physical context is
declared.

## Research Basis

- SCBE already has Layer 14 Audio Axis telemetry: frame energy, spectral
  centroid, spectral flux, high-frequency ratio, and audio stability.
- Magnetoelastic research gives a real bridge between strain/acoustic phonons
  and magnetization in magnetic materials.
- Magnetosonic plasma waves give a real bridge between compressibility, sound
  speed, Alfven speed, propagation angle, and magnetic pressure.
- NASA plasma-wave communication is usually sonification of electric/magnetic
  field measurements, not ordinary air sound in vacuum.

## Product Use

The implementation lives in `python/scbe/audio_field_observables.py`.

It extracts:

- `energy_log`
- `spectral_centroid_hz`
- `spectral_bandwidth_hz`
- `high_frequency_ratio`
- `stability`
- `dispersion_proxy`
- `reverberation_decay_s`
- `modal_count`
- `phase_wrap_count`
- `field_coupling_proxy`, only for declared `magnetoelastic` or
  `magnetosonic` models

This can later be inserted into reaction packets as an observable relation lane:

```text
audio frame
-> acoustic observables
-> declared model-bound field proxy
-> quasi-integer recoupling
-> reaction packet receipt
```

## Safe Interpretation

- Generic audio: acoustic observation only.
- Magnetoelastic model: bounded proxy for strain-magnetization coupling.
- Magnetosonic model: bounded proxy for compressibility-magnetic-pressure
  coupling using declared sound and Alfven speeds.

## Sources

- Yi Li et al., "Advances in coherent coupling between magnons and acoustic
  phonons," APL Materials 9, 060902 (2021).
  https://pubs.aip.org/aip/apm/article/9/6/060902/123131/Advances-in-coherent-coupling-between-magnons-and
- Y. Chen et al., "Resonance zones for interactions of magnetosonic waves with
  radiation belt electrons and protons," Geoscience Letters (2017).
  https://link.springer.com/article/10.1186/s40562-017-0086-3
- NASA, "Eavesdropping in Space: How NASA records eerie sounds around Earth."
  https://science.nasa.gov/blogs/the-sun-spot/2018/12/11/eavesdropping-in-space-how-nasa-records-eerie-sounds-around-earth/
- NASA, "In Solar System's Symphony, Earth's Magnetic Field Drops the Beat."
  https://www.nasa.gov/solar-system/in-solar-systems-symphony-earths-magnetic-field-drops-the-beat/
