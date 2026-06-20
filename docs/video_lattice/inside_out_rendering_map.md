# Inside-Out Rendering Map

## Core Model

The video lattice treats generation as exploration through a bounded space.

- The circle or sphere is the current rendered state.
- The surface is what the viewer sees.
- Height is abstraction, style, camera intention, and confidence.
- Depth is evidence, geometry, occlusion, and uncertainty.
- Digging deeper means inspecting landmarks, polygons, depth estimates, and
  multi-view disagreement.
- Climbing higher means composing style, prompt intent, scene logic, and
  cinematic direction.

The generator should not start with final pixels. It should start with the
inside structure and climb outward:

1. Real-time eyes and input.
2. Multi-view landmark observations.
3. Undefined-space scoring.
4. Body and hand skeletons.
5. Polygons and joint chains.
6. Perspective/depth projection.
7. Temporal lattice drift.
8. Correction signals.
9. Control-frame manifest.
10. Style and renderer-specific output.

## Overbuild Strategy

We intentionally overbuild the representation, then test what matters.

The system can carry more signals than a first renderer needs:

- body landmarks
- hand landmarks
- finger chains
- palm and torso polygons
- depth confidence
- multi-view disparity
- user input events
- lattice drift
- correction severity
- renderer-neutral control assets

Signals that do not improve output can be reduced later. Signals that catch
real failures become part of the stable generation contract.

## Undefined Space

Undefined space is not an error. It is a state.

If only one view sees a body part, or if depth is weak, the system should mark
that region as uncertain instead of inventing certainty. A renderer can then:

- request another view,
- preserve the prior pose,
- lower style aggression,
- re-render the frame,
- ask for human input,
- or quarantine the frame as unstable.

## Current Local Implementation

- `src/video_lattice/realtime_perception.py`
  - multi-view camera observations
  - fused landmarks
  - undefined-space score
  - perception vector for lattice input
- `src/video_lattice/pose_polygons.py`
  - 21-point hands
  - 33-point body pose
  - palm and torso polygons
  - finger curl and body geometry vectors
- `src/video_lattice/sketch_pad.py`
  - SVG/PNG control sketch generation
- `scripts/video_lattice/synthetic_video_lattice_demo.py`
  - demo report
  - control-frame manifest
  - sketch assets
- `src/video_lattice/tiny_engine.py`
  - compact pocket-dimension world state
  - tile/sprite/entity rules
  - SVG and symbolic grid rendering

## Pocket Dimensions

The tiny engine treats a world as a pocket dimension: a bounded space with
local rules, reusable symbols, actors, memory, and a render surface. This is
closer to old game-engine thinking than raw video generation.

Instead of storing every future pixel, it stores:

- tile IDs,
- sprite IDs,
- entity positions,
- local rules,
- palette hints,
- and state deltas.

An AI can learn to operate inside that pocket by choosing actions and observing
how the compact world changes. The renderer can then turn the pocket state into
sketches, frames, or styled video.

## Test Rule

Every added representation should answer one of these questions:

1. Does it help preserve anatomy?
2. Does it detect temporal drift?
3. Does it reduce undefined space?
4. Does it give the renderer a better correction signal?
5. Does it make human review easier?

If not, it stays experimental.
