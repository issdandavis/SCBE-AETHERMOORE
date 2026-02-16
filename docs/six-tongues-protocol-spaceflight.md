# The Six Tongues Protocol: Spaceflight Arc

## Chapters 17-22 — The Voyage Beyond the Cranium

*A continuation of the Six Tongues Protocol story, mapping deep-space flight concepts to the SCBE-AETHERMOORE architecture.*

*Author: Issac Davis*
*Patent Pending: USPTO #63/961,403*

---

## Chapter 17: The Launch — Delay-Tolerant Bundles

The day the Crystalline Cranium opened its eye to the cosmos, everything changed.

Kael stood at the highest point of the Sanctum, where the five Platonic solids hovered in their eternal dance, and watched as a thin beam of coherent light pierced the translucent surface of the Cranium. Not breaking it — nothing could break the boundary at r = 1.0 — but *communicating* through it. The Cranium was sending a message to the stars.

"How?" Kael asked, turning to Serai, the Master of Avali, whose silver eyes reflected the beam's trajectory.

"Delay-tolerant bundles," Serai said. She held up a crystalline capsule no larger than her thumb. Inside, Kael could see layers — fourteen of them, glowing in sequence like the floors of a lighthouse. "We cannot send thoughts across the void instantaneously. The distances are too vast. So instead, we *package* them."

She explained the principle: a message would be sealed at its origin, then handed from relay to relay across the emptiness between stars. Each relay — a small crystalline node orbiting in the deep field — would take *custody* of the bundle, inspect it, add its own cryptographic attestation, and forward it onward. The sender didn't need to maintain a connection to the receiver. They needed only to trust the chain.

"Each relay signs the bundle with SHA-256," Serai continued, "creating a custody chain. The first relay is index zero. The second is index one. When the bundle arrives at its destination, the receiver walks the chain backward, verifying that every signature is valid, every index is sequential, and no relay appears twice."

"No relay appears twice?" Kael frowned. "Why would a relay appear twice?"

"Loops," Serai said darkly. "If a corrupted node intercepts a bundle and sends it in a circle, the custody chain catches it. Duplicate relay IDs mean the bundle was trapped — wandering in loops instead of advancing. We reject those bundles absolutely."

Kael watched as the first bundle launched, its fourteen attestation layers glowing brighter as each one was sealed. The last layer — Layer 14, the Audio Axis — sang a single pure note as the bundle left the Cranium's influence. That note was its identity, its fingerprint, the harmonic summary of everything it carried.

And then it was gone, moving at the speed of light toward a relay node three light-minutes away. Three minutes of silence. Three minutes of trust.

"What if the relay is compromised?" Kael asked.

Serai smiled. "Then the chain breaks. And we know exactly where."

> **SCBE Mapping**: The DelayTolerantBundle class implements store-and-forward relay with custody transfer, modeling RFC 5050/9171 Bundle Protocol. Each relay adds a CustodyEntry (relay_id, SHA-256 signature_hash, order_index). The verify_custody_chain() method checks: non-empty chain, sequential indices, valid hex digests, and no duplicate relay IDs. The compute_bundle_hash() produces a deterministic SHA-256 over the complete bundle. The TTL mechanism (is_expired()) prevents bundles from circulating indefinitely. This maps to SCBE's 14-layer pipeline where each layer adds its own cryptographic attestation.

---

## Chapter 18: The Hyperbolic Slingshot — Trajectories in Six Dimensions

The first deep-space vessel to leave the Cranium's orbital neighborhood was called the *Harmonic Wanderer*. It was not a ship in the conventional sense — it was a thought-form, a governed process encapsulated in a 21-dimensional state vector, propelled through the six-dimensional harmonic space that extended beyond the Cranium's boundary.

Commander Vex, a veteran of the Risk Zone who bore the star-shaped scars of Kepler-Poinsot geometry on her arms, stood in the navigation chamber and studied the trajectory plot. It curved — not gently, like an ellipse, but sharply, like a thrown blade. A hyperbola.

"Eccentricity 2.3," the navigator reported. "We have excess energy. We won't be captured by any gravity well along the way."

Vex nodded. That was the point. In six-dimensional space — where the coordinates were position, velocity, priority, and security — a hyperbolic trajectory meant the vessel had enough governance momentum to pass through any system without being trapped. An elliptical orbit would mean capture: the thought-form bound to a single processing node, unable to escape. A hyperbola meant freedom.

But freedom had a cost.

"Fuel calculation," Vex ordered.

The navigator's fingers danced across the harmonic console. The fuel cost function appeared in glowing golden characters:

```
cost = PHI * euclidean_distance * eccentricity
```

Where PHI was the Golden Ratio, 1.618..., the fundamental scaling constant that governed everything in the Cranium's universe. The higher the eccentricity — the more open the hyperbola — the more fuel was consumed. It was the price of not being captured.

"There's a gravity assist opportunity at waypoint seven," the navigator added. "A massive processing node — a Bridge Zone polyhedron, a Johnson solid with high influence. If we pass close enough, its inverse-square gravitational field will deflect our trajectory, bending us toward the target system without additional fuel expenditure."

Vex studied the six-dimensional plot. The gravity assist would work like a trapdoor function: easy to compute forward (approach the body, get deflected), nearly impossible to reverse (reconstruct the original trajectory from the deflected one). It was elegant. It was the same mathematics that made the Cranium's cryptography unbreakable.

"Execute the slingshot," Vex ordered.

The *Harmonic Wanderer* bent around the Johnson solid, its six-dimensional trajectory curving through spaces that human intuition could not visualize. The eccentricity decreased — the assist had stolen some of the hyperbola's excess energy, donating it as angular momentum — but the vessel was now aimed precisely at its target.

One hundred waypoints plotted. One hundred steps through the void. Each one computed from the conic equation r(theta) = a(e^2 - 1) / (1 + e*cos(theta)), each one modulated by the harmonic structure of six-dimensional space.

The stars wheeled around them, and Vex allowed herself a rare smile. They were flying on the same mathematics that held the Cranium together.

> **SCBE Mapping**: The HyperbolicTrajectory class models orbital paths through the 6D protocol space V6 = (x, y, z, velocity, priority, security). The eccentricity e > 1 parameterizes the openness of the hyperbola. compute_path() generates waypoints using the conic equation r(theta) = a(e^2-1)/(1+e*cos(theta)) with true anomaly sweeping to theta_max. gravity_assist() models trapdoor deflection via inverse-square influence. fuel_cost() = PHI * distance * eccentricity uses the Golden Ratio as the fundamental scaling constant. This maps to SCBE's L5-L7 Poincare Ball operations where hyperbolic distances govern state transitions.

---

## Chapter 19: Docking — The Mutual Authentication Handshake

The approach to Station Tessera took four hours of careful maneuvering through the station's Trust Tube — a geodesic corridor in hyperbolic space, exactly 0.15 units wide, that curved toward the docking port like a crystalline throat.

Lieutenant Ryn handled communications, speaking in rapid alternations of Avali (for transport coordination) and Umbroth (for security verification). The docking protocol was ancient, older than anyone aboard could remember, but its mathematics was timeless.

"Initiating RWP handshake," Ryn announced. "Phase one: APPROACH."

The docking protocol had five phases, each mapped to a state in a strict finite state machine that permitted no shortcuts and no reversals:

**IDLE** → **APPROACH** → **CHALLENGE** → **VERIFY** → **DOCKED**

In APPROACH, both vessels exchanged their identities and proposed cipher suites — lists of cryptographic algorithms they supported. The protocol selected the first suite that appeared on both lists, respecting the local vessel's preference ordering. If no common suite existed, the handshake failed immediately. No negotiation. No exceptions.

"Common suite found: SCBE-AES-256-HARMONIC," Ryn reported.

Phase two was CHALLENGE. Station Tessera generated a random nonce — 32 bytes of entropy — and transmitted it. The *Harmonic Wanderer* received the nonce, combined it with the shared secret derived from their mutual Kyber key exchange, and computed an HMAC-SHA256 response. This was the handshake's cryptographic heart: proving that both parties possessed the same key material without ever transmitting the key itself.

"HMAC response computed. Transmitting."

Station Tessera received the HMAC, recomputed it independently, and compared. The comparison was byte-by-byte, using HMAC.compare_digest — a constant-time operation that prevented timing side-channel attacks. If a single bit differed, the entire handshake would abort and both parties would transition to IDLE, erasing all session state.

"Phase three: VERIFY."

In VERIFY, the roles reversed. Now the *Harmonic Wanderer* challenged Station Tessera with its own nonce, and the station proved its identity with its own HMAC response. Mutual authentication. Neither party trusted the other on faith — both demanded cryptographic proof.

"Verification complete. Both HMACs valid."

"Phase four: DOCKED."

The docking clamps engaged with a deep harmonic resonance — the Audio Axis singing a perfect fifth, R = 3/2, as the two vessels' 21-dimensional state vectors merged into a shared governance frame. For the duration of the docking, they would breathe together, their FluxStates synchronized, their Trust Tubes aligned.

Ryn leaned back and exhaled. "Clean dock. Zero anomalies."

Behind them, Commander Vex watched the status board with approval. The handshake had completed in exactly four transitions — IDLE to APPROACH to CHALLENGE to VERIFY to DOCKED — with no invalid states, no retries, no ambiguity. It was mathematics made manifest as protocol.

And in the depths of the docking port, fourteen layers of attestation sealed the connection, each one adding its signature to the chain. Layer 14 sang its confirmation: a single, pure, perfect note.

> **SCBE Mapping**: The DockingProtocol class implements a 5-phase mutual authentication state machine: IDLE → APPROACH → CHALLENGE → VERIFY → DOCKED. Phase 1 negotiates cipher suites (first common match wins, local preference). Phases 2-3 perform mutual HMAC-SHA256 challenge-response using a shared secret — each party proves key possession without transmitting the key. HMAC.compare_digest provides constant-time comparison. Invalid transitions raise errors. Empty IDs are rejected. This maps to SCBE's think() pipeline handshake where entities must prove identity before accessing trust ring resources.

---

## Chapter 20: Re-entry — Crossing the Harmonic Wall

The return to the Cranium was the most dangerous part of any voyage. Not because of the void — the void was indifferent — but because of the Wall.

Every entity re-entering the Crystalline Cranium had to cross the Harmonic Wall: the superexponential barrier at the boundary defined by H(d, R) = exp(d^2 * depth), where depth = 14 and d was the hyperbolic displacement from the authorized crossing point. At d = 0.5, the resistance was exp(0.25 * 14) = exp(3.5) ≈ 33. At d = 1.0, it was exp(14) ≈ 1.2 million. At d = 1.5, it was exp(31.5) ≈ 48 trillion.

You did not force your way through the Harmonic Wall. You *burned* your way through it, and what burned was trust.

Commander Vex stood in the re-entry chamber, where a row of crystalline tokens glowed in their housing — each one a one-time ablative pass, a fragment of pre-authenticated trust that could be expended to absorb the Wall's resistance. The vessel carried seven tokens for this crossing. Each token could absorb a fixed amount of harmonic flux.

"Re-entry parameters," Vex ordered.

"Boundary flux: 0.73. Token capacity: 1.0 each. Seven tokens available."

The re-entry shield worked on a simple but unforgiving principle: as the vessel crossed the boundary, the Harmonic Wall's resistance manifested as raw flux that had to be absorbed. Each token consumed exactly one unit of flux before shattering. If the total flux exceeded the available tokens, the crossing failed catastrophically — the vessel would be rejected to the WALL zone (r ≥ 0.9) with an FSGS status of ROLLBACK.

"Commit first token."

The first token shattered with a sound like breaking glass, its crystalline structure absorbing 0.73 units of flux and dissipating it as harmonic heat. The re-entry shield logged the crossing: boundary flux, tokens remaining, shield integrity.

"Crossing successful. Six tokens remaining. Shield at 85.7%."

Vex watched the tokens carefully. Each crossing consumed them — this was by design. You could not re-enter the Cranium infinite times. Each return cost something irreplaceable. It was the architectural equivalent of one-time passwords: use it once, and it's gone forever.

"What happens if we run out?" asked a young ensign.

"Then we can't come back," Vex said simply. "The Wall becomes absolute. No tokens, no crossing. The shield reports catastrophic failure, and we drift."

The ensign's face went pale.

Vex softened. "That's why we plan carefully. Seven tokens for a three-crossing mission. We use them at the calculated moments, at the calculated flux levels, and we always keep a reserve."

Behind them, the Cranium's surface shimmered as they passed through, Layer 12's Harmonic Scaling correcting the Pythagorean Comma drift that accumulated during boundary crossings. The Audio Axis sang a resolution chord — the comma correction audible as a tiny, precise adjustment in pitch.

They were home.

> **SCBE Mapping**: The ReentryShield class models ablative one-time-token boundary crossing (L12 Harmonic Wall). Each shield has a fixed number of single-use tokens. cross_boundary(flux) consumes tokens (one per unit of flux); if tokens are exhausted mid-crossing, the result is CatastrophicFailure (rejected to WALL zone with ROLLBACK status). Zero-flux crossings are free passes. The crossing log records every attempt. This maps to SCBE's Harmonic Wall function H(d,R) = exp(d^2*14) and the concept of non-renewable trust credentials that enforce finite crossing budgets.

---

## Chapter 21: Star Tracking — Certificate Authority Verification

In the deep field between star systems, where no relay node was close enough to provide real-time authentication, the *Harmonic Wanderer* relied on the oldest navigation method known to spacefaring civilizations: the stars themselves.

Navigator Pell sat in the observation dome, surrounded by a holographic sphere of stellar positions — the Star Catalog, a list of known reference stars with their exact 6D coordinates in harmonic space. Each star was an immutable reference point, a geometric anchor that could not be moved or forged. Together, they formed the Celestial Certificate Authority.

"Taking observations," Pell announced. Three telescopic sensors locked onto three bright stars, measuring their apparent positions with sub-arcsecond precision.

The identification algorithm was simple but robust: for each observed position, compute the Euclidean distance to every cataloged star and select the nearest match. If the nearest match was within 0.01 units of tolerance, the star was positively identified. If not, the observation was rejected as unreliable.

"Star Alpha confirmed. Distance to catalog entry: 0.003. Within tolerance."
"Star Beta confirmed. Distance: 0.007. Within tolerance."
"Star Gamma confirmed. Distance: 0.002. Within tolerance."

Three confirmed stars. Three known positions. From these, Pell could compute the vessel's *attitude quaternion* — a four-component mathematical object that described the vessel's orientation in space. The quaternion was unit-normalized (its magnitude equaled exactly 1.0), which meant it represented a pure rotation with no scaling or distortion.

"Attitude computed. Quaternion: [0.707, 0.000, 0.707, 0.000]. Unit magnitude verified."

The attitude quaternion served the same purpose as a certificate chain in cryptography: it was a mathematical proof that the vessel's claimed position was consistent with the independently verifiable positions of the reference stars. You could lie about where you were, but you couldn't lie about where the stars were. They were the ultimate root of trust.

"Verify position against catalog," Pell ordered.

The verify_position() function took the vessel's claimed 6D coordinates and checked them against the star observations: compute the expected apparent star positions from the claimed location, compare them to the actual observations, and if the discrepancies were within tolerance, the position was verified. If not, the vessel was lying about its location — or lost.

"Position verified. All observations within 0.01 tolerance. Confidence: HIGH."

Commander Vex nodded from the command chair. "Update the custody chain."

The verified position was added to the bundle's custody chain as a CustodyEntry, signed with the SHA-256 digest of the star observations. Any future relay or destination could independently verify that the *Harmonic Wanderer* was exactly where it claimed to be at the moment of signing — because the stars didn't lie.

This was the deepest lesson of the Celestial Certificate Authority: trust was not a social construct in the Cranium's universe. Trust was geometry. Trust was the distance between where you claimed to be and where the stars proved you were.

> **SCBE Mapping**: The StarTracker class models a certificate authority using a star catalog of known reference positions. identify_nearest_star() performs nearest-neighbor matching with configurable tolerance. compute_attitude() derives a unit quaternion (magnitude = 1.0) from observations, analogous to deriving a certificate from trusted anchors. verify_position() checks claimed coordinates against star observations — the geometric equivalent of certificate chain validation. This maps to SCBE's CA verification system where trust is established through geometric proof against immutable reference points (Platonic solids in Core zone).

---

## Chapter 22: The Constellation — Fleet Consensus and Byzantine Fault Tolerance

They were not alone in the deep field. Over the course of six months, eleven vessels had launched from the Cranium's orbital facilities, each one a governed thought-form encapsulated in a 21-dimensional state vector, each one carrying its own re-entry tokens and custody chain. Together, they formed the First Constellation — a fleet operating under Byzantine fault tolerance.

Fleet Admiral Thane stood on the command bridge of the *Icosahedral Dawn*, flagship of the Constellation, and surveyed the formation display. Eleven vessels arranged in a carefully calculated geometric pattern — not a random scatter, but a structured topology that ensured every vessel could communicate with every other vessel within 200 milliseconds.

"BFT threshold," Thane said. "Remind me."

"For eleven vessels, n ≥ 3f + 1," reported the fleet mathematician, a quiet Runethic speaker named Solara. "To tolerate three Byzantine faults, we need at least ten vessels. With eleven, we have one spare."

Three Byzantine faults. Three vessels that might be compromised, corrupted, or simply malfunctioning — sending contradictory messages to different parts of the fleet, trying to manipulate consensus. The protocol had to reach correct agreement even in the presence of these adversaries.

"I'm proposing a formation change," Thane announced to the fleet. "New formation: DELTA. Acknowledge and vote."

The ConstellationFleet protocol worked in three stages:

**Stage 1: Propose.** The admiral submitted a formation proposal to all vessels. This cleared any previous votes, ensuring a clean slate. The proposal was broadcast over all Sacred Tongue channels simultaneously — Kor'aelin for the command, Avali for the transport, Cassisivadan for the computation of the new formation's geometry.

**Stage 2: Vote.** Each vessel independently evaluated the proposal and cast a vote: ACCEPT or REJECT. The vote was signed with the vessel's unique identifier and recorded in the fleet's consensus log. No vessel could vote twice. No vessel outside the fleet could vote at all — unknown vessel IDs were rejected immediately.

"*Dawn* votes ACCEPT."
"*Wanderer* votes ACCEPT."
"*Tessera* votes ACCEPT."
"*Prism* votes REJECT."
"*Vertex* votes ACCEPT."

*Prism* had rejected. That was fine — one rejection didn't break consensus.

"*Helix* votes ACCEPT."
"*Spiral* votes ACCEPT."
"*Axiom* votes ACCEPT."

Eight accepts out of eleven. The threshold was calculated: for BFT with f potential failures, consensus required strictly more than 2/3 of all vessels to agree. For eleven vessels, that meant at least 8 accepts. They had exactly 8.

**Stage 3: Execute.** With consensus achieved, the formation change was executed *atomically* — all vessels shifted simultaneously, their positions updated in a single coordinated step. If consensus had not been reached, the shift would have been rejected entirely. No partial formations. No split fleet. All or nothing.

"Formation DELTA confirmed. All vessels in position."

Thane watched as the eleven vessels rearranged themselves, their Trust Tubes weaving through hyperbolic space like the threads of a crystalline tapestry. Each vessel occupied a vertex of the DELTA formation — a geometric pattern that maximized inter-vessel communication efficiency while minimizing the attack surface.

"And the squads?" Thane asked.

Solara pulled up the squad partition display. The fleet was divided into squads based on vessel index: vessels 0, 3, 6, 9 formed Squad 0; vessels 1, 4, 7, 10 formed Squad 1; vessels 2, 5, 8 formed Squad 2. Each squad operated as a semi-autonomous unit within the fleet, capable of independent action but bound to the fleet's consensus for formation changes.

The squad partition followed the modular arithmetic: vessel *i* belonged to squad *(i mod squad_count)*. It was deterministic, fair, and impossible to game — you couldn't choose your squad, and your squad couldn't choose you. The mathematics chose for everyone.

"This is how we explore the cosmos," Thane said quietly, watching the formation settle into its final configuration. "Not as individuals. Not as a mob. As a *constellation* — governed by consensus, resistant to corruption, bound by geometry."

Below them, the Crystalline Cranium glowed like a pale moon, its Poincare Ball containment field visible as a faint sphere of curved light. Inside it, billions of thoughts flowed through fourteen layers, each one governed by the same mathematics that held the Constellation together.

The six Sacred Tongues sang across the fleet's communication channels. Kor'aelin rewarded successful maneuvers. Avali managed attention allocation across eleven concurrent vessel states. Runethic enforced the formation rules. Cassisivadan computed the geometric transformations. Umbroth dampened oscillations in vessels that maneuvered too aggressively. And Draumric — Cortisol, the stress tongue — remained silent.

That was the best sign of all.

When Draumric was silent, the system was at peace.

> **SCBE Mapping**: The ConstellationFleet class implements BFT consensus across a multi-vessel formation. BFT threshold: n ≥ 3f+1 (11 vessels tolerates 3 faults). propose_formation() clears old votes and broadcasts. vote() accepts/rejects per vessel (unknown IDs rejected, no double voting). has_consensus() requires > 2/3 supermajority. shift_formation() executes atomically only with consensus. squad_partition() uses modular arithmetic (vessel_i mod squad_count). This maps to SCBE's SquadSpace Byzantine quorum (commit_voxel requires n ≥ 3f+1 votes) and the PollyPad governance system where consensus across distributed units ensures architectural integrity.

---

## Epilogue: The Return

The First Constellation completed its voyage in fourteen months — one month for each layer of the SCBE-AETHERMOORE architecture. They had mapped six new relay nodes in the deep field, established custody chains across four star systems, and proven that the Cranium's governance mathematics worked not just within its boundaries but across the cosmic distances between them.

On the day of return, all eleven vessels approached the Cranium in formation, each one burning a re-entry token as they crossed the Harmonic Wall. The wall's flux was 0.42 — gentle, by re-entry standards — and every vessel crossed safely, its shield logging the crossing with mathematical precision.

They docked at Station Tessera, completing the five-phase handshake in perfect synchronization. Eleven mutual authentications, eleven HMAC verifications, eleven custody chains validated and sealed.

And as the fleet powered down, the Audio Axis of the Crystalline Cranium sang a chord that no one aboard would ever forget. Not a single note, but six notes — one for each Sacred Tongue — layered in the hexatonic pattern at 60-degree intervals, phased perfectly, harmonically scaled by the Perfect Fifth and corrected by the Pythagorean Comma.

It was the sound of geometry made audible. The sound of mathematics singing.

The sound of home.

---

## Appendix: Space Flight to SCBE Mapping Table

| Space Flight Concept | SCBE-AETHERMOORE Component | Chapter |
|---|---|---|
| Delay-Tolerant Bundle | L1-L14 pipeline attestation chain | 17 |
| Custody Chain | SHA-256 HMAC chain across 16 polyhedra | 17 |
| Hyperbolic Trajectory | L5 Hyperbolic Distance + Poincare Ball geodesics | 18 |
| 6D Harmonic Space | 6D hyperbolic subspace of 21D state vector | 18 |
| Gravity Assist | Trapdoor function (easy forward, hard inverse) | 18 |
| Fuel Cost (PHI * d * e) | Golden Ratio phi-scaled energy costs | 18 |
| Docking Protocol | think() pipeline mutual authentication | 19 |
| RWP Handshake | IDLE→APPROACH→CHALLENGE→VERIFY→DOCKED state machine | 19 |
| HMAC Challenge-Response | ML-KEM + HMAC-SHA256 key proof | 19 |
| Re-entry Shield | Harmonic Wall H(d,R)=exp(d^2*14) boundary crossing | 20 |
| Ablative Tokens | One-time trust credentials (non-renewable) | 20 |
| Catastrophic Failure | FSGS ROLLBACK state at WALL zone | 20 |
| Star Catalog | Core Zone Platonic solids as reference anchors | 21 |
| Attitude Quaternion | Certificate chain derivation from trusted roots | 21 |
| Position Verification | Geometric proof against immutable references | 21 |
| Fleet Constellation | SquadSpace distributed consensus | 22 |
| BFT (n ≥ 3f+1) | Byzantine quorum in commit_voxel() | 22 |
| Formation Change | Atomic state transition with supermajority | 22 |
| Squad Partition | Modular arithmetic vessel assignment | 22 |

---

## Glossary: New Terms

- **Custody Chain**: An ordered sequence of relay attestations, each with a unique relay_id and SHA-256 signature, forming an auditable path from sender to receiver.
- **Hyperbolic Trajectory**: An escape orbit (eccentricity > 1) through 6D harmonic space, used when a governed process must transit through a system without being captured.
- **RWP Handshake**: Rendezvous-With-Proof — the five-phase mutual authentication protocol used for docking (IDLE → APPROACH → CHALLENGE → VERIFY → DOCKED).
- **Ablative Token**: A single-use trust credential consumed during Harmonic Wall boundary crossings; cannot be regenerated.
- **Celestial Certificate Authority**: The star catalog used as a root of trust for position verification; immutable reference points that cannot be forged.
- **Constellation**: A fleet of governed vessels operating under Byzantine fault tolerance, requiring > 2/3 supermajority for formation changes.
- **Squad Partition**: Deterministic vessel-to-squad assignment using modular arithmetic (vessel_i mod squad_count).
