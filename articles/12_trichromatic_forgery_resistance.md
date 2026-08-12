---
title: "Detection Dimensions Are Not Security Bits: Splitting an AI Governance Overlay in Two"
published: false
description: "We counted 63 spectral channels as 504 bits of security. They aren't. Here's the separation that fixes it: a 63-dimensional detection overlay, and a 256-bit authenticated replay-resistant state chain."
tags: ai, security, cryptography, machinelearning
canonical_url: https://aethermoore.com/research/negative-tongue-lattice.html
---

## The mistake worth publishing

An earlier draft of this article claimed a "504-bit state space", `10^71` times larger than the
number of atoms in the observable universe, and "5 out of 5 forgeries caught."

Every one of those numbers was produced by code that could not have produced a different answer.
That is the interesting part, so it goes first.

**The state space was counted, not measured.** We had 6 governance dimensions × 3 spectral bands,
plus 15 cross-dimension bridges × 3 bands = 63 channels, and multiplied by 8 bits each to get 504.
But the 15 bridges are *computed from* the 6 dimensions. They are deterministic functions of
values already counted. Of 63 channels, **45 carry no independent information**. Multiplying
channel count by bit depth gives you a number; it does not give you entropy.

**The forgery test had no failing input.** The "attacker" was constructed by copying the visible
band and drawing the two hidden bands from `np.random.RandomState(42)` — a *fixed seed, inside the
function*, so all five attacks received identical forged values. It was n=1 reported five times.
Detection was declared when fewer than 6 dimensions matched on all three bands. Per dimension, the
chance that two uniform draws both land within the 0.15 tolerance is 0.0772; for all six at once,
about 2×10⁻⁷. In 200,000 simulated trials it never happened. The test could only ever print
"caught."

**The bridges were hardcoded out.** The loop that checked them read `bridge_matches += 0`, with
the comment "Forged bridges almost certainly don't match," and the reported rate was the literal
constant `0.0`. The 45 channels the headline counted contributed nothing to the verdict.

**And the seal was not a seal.** State integrity used `blake2s(state, digest_size=16)` — *unkeyed*,
128-bit. Anyone holding the state can recompute it. That is a checksum against corruption, not a
tag against an adversary.

## The separation

Detection and authentication are different jobs measured in different units, and the original
design spent one as the other. So they are now two layers that never borrow each other's numbers.

| Layer | What it does | Correct unit |
|---|---|---|
| **Trichromatic overlay** | 63 values: 6 dimensions × 3 bands + 15 bridges × 3 bands | **dimensions** |
| **State chain** | keyed 256-bit BLAKE2s tag over the canonical state | **bits of security** |

The overlay keeps its job, which it does honestly: infrared carries slow state (trust history,
session depth, centroid drift), ultraviolet carries fast state (spike detection, null-space
anomaly, cost harmonics), and visible carries the current activations an attacker can also see.
Hidden state is genuinely useful for anomaly detection — an attacker who has not lived the
session cannot reproduce its trajectory. That is a real signal. It is **not** a key, and the
number of channels it spans is **not** a security parameter.

## What the chain actually binds

Each state is authenticated with a 256-bit keyed BLAKE2s tag over a length-prefixed encoding of:

```
tag = BLAKE2s-256(
    key      = HKDF(master, "chain" | session_id),
    message  = session_id ‖ counter ‖ nonce ‖ state_digest ‖ previous_tag ‖ tongue ‖ orientation
)
```

Length-prefixing matters more than it looks: plain concatenation lets `("ab","c")` and
`("a","bc")` produce identical bytes, so a tag over one would be a valid tag over the other.
Every field carries an 8-byte big-endian length.

The **previous tag** is what makes this a chain rather than a pile of signatures. Combined with a
strictly monotonic counter and a fresh random nonce, it blocks replay, reordering, splicing, and
dropped-entry attacks — each of which is a separate test that fails when the corresponding binding
is removed.

## Six keys, still 256 bits

Six dimension-specific keys plus a chain key are derived from one 256-bit master via HKDF-SHA256
with distinct `info` labels. This buys **domain separation**: a tag minted for one dimension will
not verify as another.

It buys **no additional entropy**. Total security remains 256 bits, bounded by the master key.
Seven derived keys is not 7 × 256 = 1792 bits, and the code says so in a field rather than leaving
it to prose:

```python
"security_bits": 256,
"claimed_security_bits_if_naively_summed": 1792,
"naive_sum_is_false": True,
"derived_keys_add_entropy": False,
```

## Orientation: discrete direction, unchanged value

Alongside the value, each entry may carry a **multi-sign orientation** — one sign per axis from
`{+, 0, −}`, written `+-+` or `+0-+-0`. It says which dimensions are rising, falling, or flat,
concurrently, without touching a single measured value.

Over three axes the pure orientations close into four antipodal pairs under negation:

```
+++ / ---      +-+ / -+-      ++- / --+      +-- / -++
```

The natural width here is six — one sign per governance dimension — giving `3^6 = 729`
orientations. The orientation is bound *under the tag* but deliberately kept *out of the state
digest*. So re-orienting a reading changes the tag and leaves the value provably identical; that
is the tested property, not a description of intent.

And `729` orientations is ~9.51 bits of **label space**. It is not added to the 256. The same
discipline that refuses to call 63 channels 504 bits refuses to bank orientation as security.

## Tests that can fail

The lesson from the original forgery check is that a passing test proves nothing unless some input
would have failed it. So the suite includes a positive control (the untampered chain verifies), and
each negative test changes exactly one thing:

- all **256 single-bit flips** of the tag are rejected — exhaustive, not sampled
- modified state, digest, or nonce rejected
- replay of an earlier entry, reordering, and a dropped middle entry all rejected
- a valid *prefix* still verifies, so the suite is not simply rejecting everything
- wrong master key, wrong session id, and cross-dimension relabelling all rejected
- the repo's HKDF is cross-checked against `pyca/cryptography`'s implementation

Then the implementation is deliberately broken three ways to confirm the guards are load-bearing:
unbind the orientation and the orientation test collapses; unbind the previous tag and a tag over a
fabricated history verifies; drop the key and an attacker holding the wrong key verifies fine —
reproducing the original unkeyed failure exactly.

## The claim

> **63-dimensional trichromatic detection overlay with a 256-bit authenticated,
> replay-resistant state chain.**

Smaller than "10^71 times the atoms in the universe." It has the advantage of being true, and of
naming which half is which.

---

*Built by Issac Daniel Davis. The six governance dimensions are Kor'aelin, Avali, Runethic,
Cassisivadan, Umbroth, and Draumric — coordination, transport, policy, computation, security, and
verification channels inside the SCBE-AETHERMOORE system.*
