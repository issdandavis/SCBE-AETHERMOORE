# Fizzle Pocket Worlds Research

## Canon Anchor

Fizzle Brightcog is the clearest pocket-world builder in the current Aethermoor
lore.

In `content/book/reader-edition/ch16b-the-fizzlecress-incident.md`, Fizzle's
Workshop Globe is a pocket-dimension prototype: a glass sphere containing a
miniature island, local weather, warm sand, a palm tree, tiny furniture, and a
spatial-compression entry/exit rule. Marcus wakes inside it at small scale, not
as a symbolic metaphor but as an actual bounded world with its own local
physics.

The globe matters because it is small enough to understand. Marcus can inspect
the whole world, sit in it, draw on the table, test Coff-three, and leave by
declaring intent. It is a classroom, workshop, simulator, recovery room, and
comedy stage at the same time.

## Fizzle's Function

Fizzle is not only comic relief. He is the CA-tongue experimental engineer who
turns emotional mess into testable apparatus.

His pattern:

1. Start with a human need.
2. Build a bounded local world around that need.
3. Let chaos happen safely inside the boundary.
4. Preserve the useful trace.
5. Improve the next version.

Coff-three follows the same rule. It is reverse engineered from Marcus's
metabolic trace, tuned by local ingredients and classified minerals, then tested
inside a contained environment. The result is not just coffee. It is a tool that
reveals what Marcus's hands and feelings were already doing.

That line is the key:

> the best tools are the ones that show you what your hands were already doing

For our renderer, that means the system should not start by pretending it can
draw perfectly. It should reveal the child's current motion, correct it gently,
and make the next attempt easier to understand.

## Pocket World Definition

A Fizzle-style pocket world has five properties:

| Property | Lore Form | System Form |
| --- | --- | --- |
| Boundary | Glass globe, seventeen-tongue lock | Explicit world size and rules |
| Scale shift | Marcus becomes small | Low-resolution symbolic state |
| Local physics | Breeze, sand, island, compression | Tile/sprite/entity rules |
| Trace surface | Driftwood table with equations | SVG sketch, JSON state, log |
| Exit rule | Declare intent to leave | Save/export/advance frame |

This maps directly to `src/video_lattice/tiny_engine.py`: tile IDs, sprites,
entity positions, rules, JSON state, and SVG rendering. The engine is already
the code version of Fizzle's globe.

## Why This Helps A Child Learn To Draw

The goal is not "make an AI draw everything." The better goal is:

Teach a small learner to draw with nothing but:

- keyboard keys,
- command-line steps,
- a small readable world,
- repeated traces,
- and willingness to follow instructions.

The pocket world gives the learner one small frame at a time. The child does not
need a full art program. They can type commands like:

```text
draw hand open
curl finger index 0.4
move thumb left
show skeleton
show polygon
compare last
save frame
```

The system renders a simple control sketch, scores it, and explains the next
one small correction.

This is Fizzle's globe translated into teaching:

- The whole problem fits in view.
- Mistakes stay contained.
- Every attempt leaves a trace.
- The trace becomes the lesson.

## Animation Process Connection

This also answers the animation-process issue: you learn by tracing the process,
not by copying the finished style.

The Fizzle loop is:

1. Rough intent.
2. Small bounded test.
3. Visible failure.
4. Preserved trace.
5. Repair.
6. Next version.

That is the same production shape as rough keys, pencil tests, cleanup, and
final paint. The pocket world is the pencil-test box.

## Video Lattice Use

For video generation, a Fizzle pocket world should produce these artifacts per
frame or beat:

1. `world.json` - bounded symbolic state.
2. `control.svg` - visible child-readable sketch.
3. `pose.json` - hand/body landmarks or simple polygon chains.
4. `trace.json` - what changed since the last frame.
5. `score.json` - anatomy, drift, undefined-space, and continuity scores.
6. `repair.md` - one instruction for the next attempt.

The renderer can be upgraded later. The teaching loop does not depend on a huge
video model.

## Canon-Safe Prompt Template

```text
Fizzle Brightcog's pocket-world lesson:
Build a tiny bounded workshop globe for [skill].
The world has [3-5 objects], [1 actor], and [1 rule].
Show the rough trace first.
Show the correction second.
Do not hide the failed attempt.
Make the tool reveal what the hands were already doing.
```

Example:

```text
Fizzle Brightcog's pocket-world lesson:
Build a tiny bounded workshop globe for drawing an open hand.
The world has a wrist dot, palm polygon, four finger chains, one thumb chain,
and one chalk table.
Show the rough trace first.
Show the correction second.
Do not hide the failed attempt.
Make the tool reveal what the hands were already doing.
```

## Implementation Direction

The next practical build is a command-line "pocket drawing tutor":

```powershell
python scripts/video_lattice/pocket_drawing_tutor.py hand open
python scripts/video_lattice/pocket_drawing_tutor.py hand fist --compare-last
python scripts/video_lattice/pocket_drawing_tutor.py body walk --frames 6
```

It should use existing pieces:

- `TinyWorld` for the bounded pocket.
- `SketchPad` for SVG/PNG control drawings.
- `pose_polygons` for hands and bodies.
- `TemporalTracker` for frame-to-frame drift.
- `LocalVectorIndex` later for searching old attempts.

This keeps the system small, readable, and teachable before plugging it into
heavier video generation.

