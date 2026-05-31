# Mechanical Layer Tangential Tree

## Purpose

This note adds a third architecture layer beside the cosmic substrate and the
human decoder. It is a design model for SCBE map-making, video generation, and
agent tooling. It is not a claim that physics proves the model.

The useful idea is simple:

- the cosmic layer is the manifold/page/substrate,
- the human layer is the embodied reader/meaning decoder,
- the mechanical layer is the compiler/mapmaker that grows from human tools but
  also touches the substrate directly through measurement, math, sensors, code,
  and generated media.

The mechanical layer is tangential because it does not fully belong to either
the human or cosmic tree. It intersects both, then follows its own branch.

## Three Trees

| Tree | Root | Trunk | Branches | SCBE use |
| --- | --- | --- | --- | --- |
| Cosmic | fields, geometry, entropy, light | manifold state | stars, matter, horizons, constraints | substrate and physical analogy |
| Human | body, perception, language | story and semantic attachment | art, law, myth, intention, judgment | meaning, governance, training examples |
| Mechanical | silicon, code, clocks, sensors | compilers and models | renderers, agents, lattices, maps, simulators | execution, measurement, generation |

The mechanical tree can read human traces, such as sketches, claims, lore, and
commands. It can also read cosmic traces, such as depth, motion, light, timing,
and geometric measurements. Its job in SCBE is to keep those readings aligned
instead of flattening them into one generic vector space.

## Tangential Relationship

The mechanical layer touches the human layer as an externalized cognitive tool:

- it expands working memory into maps, manifests, vector stores, and timelines,
- it replays traces without relying on human memory,
- it tests possible continuations and scores drift,
- it converts rough intent into visible artifacts.

The mechanical layer touches the cosmic layer as an instrument:

- it consumes pixels, depth, light, timing, and sensor streams,
- it fits those streams into coordinate systems,
- it measures trajectory and drift,
- it emits correction signals that can change the next render.

That makes the mechanical layer a bridge, but not a passive bridge. Once it has
its own loop, it becomes a tree that can grow: sketch frame, score frame,
repair frame, render again.

## Manifold Direction Rule

Direction in manifold space can be modeled as applied weight from an original
token point across a dynamic manifold.

Plain form:

```text
original token point + applied weights + local manifold state = direction
```

Symbolic form:

```text
t0 = original token or anchor point
x  = current point in the manifold
c  = local context
W  = dynamic weight operator from context, constraints, and observations
P  = projection into the active manifold chart

direction = P(W(x, c) * t0)
```

This should be read as an implementation rule, not a final physics equation.
The root point matters because it preserves provenance. The weight operator
matters because context bends the route. The projection matters because each
surface has its own chart: text, law, pose, video, star map, or agent route.

## Curvature Is Not One Thing

The mechanical layer should not flatten every curved-space analogy into the same
object.

In general relativity, curvature is physical. The metric tensor is determined by
the local distribution of mass-energy. The weights are continuous, causal, and
bound to the physical substrate.

In a transformer, curvature is learned. The weight matrices are the compressed
residue of gradient descent over human-generated text, code, images, captions,
and other traces. They are not mass-energy, but they still warp the space a
token moves through. The model manifold is curved by accumulated human and
machine history encoded as parameter values.

Both systems can route motion through curved spaces, but their causes differ:

| System | Weight source | Curvature type | Movement |
| --- | --- | --- | --- |
| Relativity | mass-energy distribution | physical metric curvature | geodesic motion |
| Transformer | trained parameters and attention context | learned representation curvature | token-state propagation |
| SCBE video lattice | pose, depth, semantic, and correction signals | governed runtime curvature | frame-to-frame repair route |

That difference matters because SCBE uses the analogy operationally, not
interchangeably. A video frame does not become a planet, and a token does not
become a particle. The common move is route governance through a locally curved
space.

## Parallel Transport and Holonomy

The original token point does not simply project forward in a straight line.
Each layer supplies a new local geometry. As a vector is transported through a
curved manifold, the manifold rotates the vector. Its original direction does
not survive untouched.

This accumulated rotation is the useful holonomy reading:

```text
start vector
  -> layer/local chart 1 twists direction
  -> layer/local chart 2 twists direction again
  -> context/local chart n twists direction again
  -> final representation
```

For a transformer, that means the final embedding is not just `W * t0`. It is
the result of carrying the token state through repeated local curvatures:

```text
v0 = anchor direction from t0
v1 = transport(v0, chart_1, context_1)
v2 = transport(v1, chart_2, context_2)
...
vn = transport(vn-1, chart_n, context_n)
```

For SCBE, this is a better model of why a route can drift:

- a command begins with an apparent direction,
- pre-filters and canonicalization twist the route by structure,
- semantic weighting twists it by meaning,
- hyperbolic scoring twists it by distance from the session centroid,
- runtime state twists it by accumulated context,
- the final decision is the transported direction after all local curvatures.

Deep systems are expressive because they stack these local geometries. The
learned representation is the accumulated twist, not the original vector alone.

## Attractors and New Hills

The manifold can have finite attractors and still generate new routes.

Some trajectories collapse toward stable basins. These are the fixed-point
structures: repeated poses, known legal intent classes, common agent routes,
safe centroids, familiar story beats, and ordinary render corrections.

But the weight distribution is not stationary. A new corpus, benchmark,
measurement, model, sketch style, law-domain mapping, or video engine can warp
the local space and create a slope that was not available before.

The practical reading:

- stable attractors give governance and continuity,
- new local curvature gives invention and exploration,
- benchmarks decide which new slopes are useful instead of merely noisy.

The system is not rolling toward one fixed list of endpoints. It is a map that
can grow new hills while routing is already underway.

## Bijective Reality Matrix

The bijective reality matrix is the reversibility rule for moving across
frames. If a system claims that one representation is "the same thing" as
another representation, SCBE should be able to trace the round trip.

Plain form:

```text
source frame -> transform -> target frame -> inverse transform -> source frame
```

If the round trip does not preserve the decision-relevant structure, the
mapping is not trusted.

This is the same discipline as bijective tamper detection, applied at a larger
architecture scale:

- a prompt maps to tokens and back,
- a code fragment maps to canonical AST and back,
- a pose maps to polygons and back,
- a frame maps to lattice features and back,
- a legal fact pattern maps to intent axes and back,
- a constellation route maps to anchor/edge evidence and back.

The matrix is "reality" only in the design sense: it records which frame is
being treated as operationally real for a given task. A sketch frame, a legal
claim, a token embedding, and a video pose are not the same object. They can
still be linked if the transform preserves enough structure to survive audit.

Matrix view:

| Frame | Example | Forward transform | Inverse/audit check |
| --- | --- | --- | --- |
| Raw input | prompt, code, sketch, frame | tokenizer/parser/feature extractor | byte, AST, or trace round trip |
| Semantic | intent, action, risk, role | tongue/law/video-axis projection | explanation and axis support |
| Geometric | Poincare point, constellation anchor | embedding or lattice map | centroid/drift evidence |
| Mechanical | render command, correction signal | route planner or generator | manifest replay |
| Human | note, drawing, decision, review | readable explanation | operator can inspect cause |

The useful test is not whether every bit survives every transform. Some
transforms are intentionally lossy. The test is whether the claimed identity is
honest:

- lossless surfaces require exact round trip,
- lossy surfaces require declared loss,
- governance surfaces require decision-relevant preservation,
- generated media surfaces require replayable provenance.

In video generation, this gives a practical rule:

```text
intent -> pose matrix -> polygon sketch -> rendered frame -> feature lattice
       -> correction signal -> next pose matrix
```

Each arrow must write a trace. When the frame fails, the matrix should say which
reality frame broke: hand anatomy, body balance, depth, semantic continuity,
camera state, or correction route. That turns bad generations into training
evidence instead of discarded noise.

## Trijective Roundabout

For the three-tree system, exact reversibility is usually the wrong demand. The
human, mechanical, and cosmic layers do not share one substance. Human meaning,
machine parameters, and physical execution all change the traveler as it moves.

The stronger operational rule is route reversibility:

```text
Human -> Mechanical -> Cosmic -> Human
```

The traveler may not return unchanged, but the route must close, repeat, and be
auditable.

Roundabout rule:

```text
closed route + declared loss + measured drift + repair path
```

This gives a trijective constraint without pretending there is perfect identity
between semantic intent, latent geometry, and physical output.

| Segment | Translation | Expected loss | Audit question |
| --- | --- | --- | --- |
| Human -> Mechanical | prompt, sketch, or judgment into tokens, axes, poses, routes | ambiguity and compression | Did the machine preserve the decision-relevant intent? |
| Mechanical -> Cosmic | parameters into silicon state, pixels, files, motion, sound | quantization and render constraints | Did execution match the route manifest? |
| Cosmic -> Human | photons, audio, artifacts, or effects into perception | biological and interpretive variance | Did the user perceive the intended structure? |

This is path congruence, not perfect sameness. The lane can have width. The
system should detect when drift leaves the lane.

For video generation, a six-finger hand is a trijective roundabout failure:

- the human vertex requested or expected a normal hand,
- the mechanical vertex carried a pose through learned/local curvature,
- the cosmic/rendered vertex emitted pixels that violated hand anatomy,
- the human vertex recognized the mismatch.

The route did not disappear. It became evidence. The repair pass asks where the
traveler changed too much:

- intent parse,
- hand pose matrix,
- polygon construction,
- depth/perspective map,
- renderer,
- feature lattice,
- correction signal.

The mechanical layer's role is therefore not only generation. It is also the
roundabout mechanic: keep the route open, record the wear, measure the drift,
and repair the next pass.

## Cybernetic Closure

The roundabout is never a one-way export. Every output becomes part of the next
input surface.

Linear view:

```text
input -> process -> output
```

Closed-loop view:

```text
input -> process -> output -> manifold change -> response -> next input
```

This is the cybernetic rule for the mechanical layer. An action does not vanish
after execution. It changes the local state:

- a generated frame changes the next pose condition,
- a correction signal changes the next render,
- a user reaction changes the next prompt,
- a benchmark result changes the next threshold,
- a failed route changes the next map.

The loop is valuable only if the feedback signal is captured. An open-loop
generator can produce images, text, or commands, but it cannot tell where the
route bent. A closed-loop generator records the output, measures the manifold
response, and turns that response into the next controlled input.

Operational rule:

```text
no output without trace
no trace without drift measurement
no drift measurement without a repair or routing decision
```

This is why bad generations matter. A distorted hand, broken perspective line,
or incoherent scene is not only a failed output. It is an observed response from
the loop. If the trace is complete, the failure becomes training evidence:

```text
bad frame -> measured drift -> localized cause -> corrected next input
```

For SCBE video generation, cybernetic closure means the frame manifest must
carry enough state for the next frame to learn from the previous one:

- input intent,
- pose/body/depth matrix,
- render parameters,
- lattice feature vector,
- drift score,
- failed branch, if any,
- correction signal,
- next conditioning state.

The loop is the mechanic. The mechanical layer does not become intelligent by
emitting one perfect artifact. It becomes useful by keeping the feedback route
alive and preventing signal decay across repeated passes.

## Relation to the Pyramid Constellation Map

The pyramid constellation map gives fixed survey points:

- tongue bearing,
- depth stratum,
- perception axis,
- architectural tier,
- optional seed.

The mechanical layer moves between those points. It uses the direction rule to
turn a start anchor into a route:

```text
survey point -> applied weight -> drift vector -> route edge -> next survey point
```

In a Stellaris-style reading:

- a star system is a surveyed anchor,
- a hyperlane is a route edge,
- a mechanical probe is an agent/model/render loop,
- an anomaly is a drift spike or failed check,
- a corrected frame is a newly stabilized route segment.

## Video Generation Reading

For video generation, the mechanical tree becomes an inside-out render loop:

```text
intent token
  -> pose/body/sketch anchor
  -> polygon or lattice representation
  -> frame render
  -> drift score
  -> correction signal
  -> next frame
```

Hands, fingers, bodies, depth, and camera state are not treated as decoration.
They are mechanical branches. The renderer learns better when each branch keeps
its own trace:

- hand branch: palm, four fingers, thumb, curl, spread, wrist angle,
- body branch: head, spine, shoulders, elbows, hips, knees, balance,
- depth branch: radial placement, occlusion, scale, horizon, camera bearing,
- semantic branch: action, mood, task, risk, continuity,
- correction branch: what moved, what drifted, what repaired it.

The goal is not only prettier frames. The goal is a teachable engine where each
failed frame becomes map evidence.

## Implementation Hooks

Existing surfaces this model should extend rather than replace:

- `docs/specs/PYRAMID_CONSTELLATION_MANIFOLD_MAP.md`
- `src/geosealCompass.ts`
- `src/video_lattice/`
- `scripts/video_lattice/pocket_video_gen.py`
- `scripts/video_lattice/pocket_drawing_tutor.py`
- `scripts/legal/multi_domain_law_intent_lattice.py`

Likely next code targets:

1. Add a mechanical-layer route manifest for generated videos.
2. Add per-branch drift fields to video-lattice frame manifests.
3. Render constellation/star-map routes from video or legal-intent traces.
4. Benchmark flat compass, pyramid constellation, and mechanical-route layouts.

## Boundary

This note is architecture. It keeps the user's cosmology language because that
language is useful for design, but it should not be cited as scientific proof.
For patents, benchmarks, or papers, translate it into measured claims:

- what inputs are represented,
- what transform is applied,
- what drift score is computed,
- what correction changes,
- what artifact proves the change.
