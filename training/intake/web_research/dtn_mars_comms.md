# Delay-Tolerant Networking (DTN) — Mars Comms Applied to AI Thought Routing

## Source
NASA/IETF DTN Architecture (RFC 4838, RFC 5050), adapted for AI cognitive architecture

## Core Concept: Bundle Protocol for AI Thoughts

Delay-Tolerant Networking (DTN) was developed for deep-space communication where real-time connectivity is impossible. The Bundle Protocol wraps data into self-contained "bundles" that can survive long delays, disruptions, and route changes. Applied to AI thought routing, each cognitive operation becomes a bundle that can tolerate delays, store itself during occlusion, and self-correct through forward error correction.

### Key DTN Principles

1. **Store-and-Forward**: Unlike TCP/IP which requires end-to-end connectivity, DTN nodes store bundles until a forwarding opportunity arises. In AI terms: thoughts don't need immediate resolution. A partial computation can be stored at an intermediate layer and forwarded when the next processing stage is ready.

2. **Bundle Protocol**: Each bundle is self-contained with:
   - Source endpoint ID (which cognitive module originated the thought)
   - Destination endpoint ID (target processing layer)
   - Creation timestamp (temporal ordering for causality)
   - Lifetime/TTL (how long the thought remains valid before expiry)
   - Payload (the actual cognitive content — embeddings, decisions, signals)
   - Extension blocks (metadata: tongue assignment, governance stamps, axiom tags)

3. **Context Occlusion**: In Mars communications, the planet literally goes behind the Sun for weeks — total signal blackout. The system must handle this gracefully. In AI routing:
   - A processing layer may be overloaded, unavailable, or deliberately paused
   - Thoughts queued during occlusion don't die — they persist and deliver when the path clears
   - This maps directly to SCBE's QUARANTINE state: not rejected, just held
   - Occlusion is a feature, not a failure — it creates natural batching windows

4. **Forward Error Correction (FEC)**: Deep-space signals degrade. FEC adds redundant information so the receiver can reconstruct the original even with partial loss. In AI thought routing:
   - Each thought bundle carries redundant representations (multi-tongue encoding)
   - If one encoding path is corrupted or misclassified, others survive
   - The 6-tongue system IS forward error correction — same concept encoded through KO/AV/RU/CA/UM/DR provides 6 parallel channels
   - Polyhedral structure adds geometric redundancy on top of linguistic redundancy

5. **Convergence Layers**: DTN uses convergence layers to adapt to different underlying transports (TCP, UDP, LTP for space). In SCBE:
   - L1-L4 (input processing) = different convergence layers for different data types
   - L5-L7 (hyperbolic/Mobius) = the deep-space link layer (high-latency, high-value)
   - L8-L12 (Hamiltonian/spectral/harmonic) = the orbital mechanics layer
   - L13-L14 (decision/audio) = the ground station layer (final delivery)

### Custody Transfer

DTN's custody transfer protocol means each node along the route takes responsibility for the bundle. If a node accepts custody, the sender can release its copy. In AI routing:
- Each pipeline layer that accepts a thought takes custody
- The previous layer is freed to process new inputs
- If the receiving layer fails, custody reverts and the bundle seeks an alternate route
- This prevents the pipeline from stalling on a single blocked layer

### Contact Graphs and Scheduled Links

In space, communication windows are predictable — you know when Mars will be visible from Earth. DTN uses contact graphs to schedule transmissions. In AI:
- Processing capacity varies by load, time, and resource availability
- A contact graph for the 14-layer pipeline predicts which layers will have capacity
- Batch scheduling becomes Mars-style: queue thoughts for optimal delivery windows
- Training data generation (like the Training Pad) operates on scheduled contact windows

### Fragmentary Delivery

Large bundles can be fragmented and reassembled. In AI:
- Complex thoughts that span multiple concepts can be fragmented across layers
- Each fragment carries enough metadata to reassemble at the destination
- Partial delivery is still valuable — some fragments may arrive first and begin processing
- The multi-turn SFT records in the Training Pad are already fragmentary: write → fail → feedback → fix → pass, each fragment is independently valuable but the full assembly tells the complete story

## Application to SCBE Training Pipeline

### Thought Bundles as Training Records
Each SFT record IS a thought bundle:
- Source: the generator (web_research, context7, training_pad, manual)
- Destination: the model layer it trains (L0-L3)
- Payload: instruction + response
- Extension blocks: tongue_profile, category, null_pattern, axiom_tags
- Lifetime: records don't expire but can be superseded by better examples
- FEC: multiple records covering the same concept from different angles

### Occlusion-Tolerant Curriculum
Training doesn't happen continuously — it happens in windows:
- Data collection phase (store bundles)
- Curation phase (route bundles to correct curriculum slots)
- Training phase (deliver bundles to model)
- Evaluation phase (verify bundle delivery — did the model learn?)
- Each phase can tolerate delays and interruptions without data loss

### Mars Distance as Cognitive Latency
The 4-24 minute one-way light delay to Mars maps to:
- L0 (binary substrate): 0 latency — immediate bit-level operations
- L1 (structural): low latency — pattern recognition
- L2 (semantic): medium latency — meaning extraction requires more processing
- L3 (governance): high latency — full pipeline traversal, like a round-trip to Mars
- The deeper the processing, the higher the "cognitive latency" — and DTN handles this naturally

### Store-and-Forward for Incomplete Training
Not all training data arrives complete. Some records are:
- Partial (a write event without a subsequent run)
- Ambiguous (tongue classification is uncertain)
- Contradictory (two records with conflicting governance signals)
DTN's store-and-forward model says: don't discard these. Store them. A future processing pass may resolve the ambiguity, complete the partial, or reconcile the contradiction.

## Mathematical Connections

### Bundle Lifetime and Harmonic Decay
Bundle TTL maps to the harmonic scaling function:
- `H(d, pd) = 1/(1 + φ*d_H + 2*pd)` defines how quickly influence decays with distance
- A thought bundle's effective lifetime decreases as it moves further from its origin in hyperbolic space
- Bundles near the center (safe operations) have long lifetimes
- Bundles near the boundary (adversarial territory) decay rapidly — they expire before delivery

### Custody Transfer and Layer Ownership
Each axiom group takes custody of thoughts that pass through its domain:
- Unitarity (L2, L4, L7): ensures norm preservation during transfer
- Locality (L3, L8): bounds the spatial extent of custody
- Causality (L6, L11, L13): enforces temporal ordering of custody transfers
- Symmetry (L5, L9, L10, L12): ensures gauge invariance across custody boundaries
- Composition (L1, L14): verifies pipeline integrity from source to destination

### Contact Graph as Training Schedule
The optimal training schedule IS a contact graph:
- Windows when GPU is available = contact windows
- Data batch sizes = bundle fragment sizes
- Layer-specific training passes = link-specific transmissions
- The whole curriculum plan is a multi-hop route through cognitive space
