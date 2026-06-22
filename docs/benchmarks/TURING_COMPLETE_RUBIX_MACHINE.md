# Turing Complete Rubix Machine

A standard physical 3x3 Rubik's Cube is finite, so it is not Turing complete by
itself. The SCBE version is a virtual Rubix machine:

- cube moves are the instruction surface
- `python.scbe.bit_spine` owns the Brainfuck-class tape/loop runtime
- conlang faces label the instruction lanes
- receipts prove state after execution

This gives us a clean bridge:

`cube turns -> executable program -> conlang projection -> benchmark action route`

## Display Faces

The fixed faces can also act like a tiny multi-panel screen. In that layout the
cube is not only a command surface:

- turns are controller inputs
- face panels are live views
- the spine runtime is the executable core
- shell, CLI, browser, game, and benchmark tools are attached behind the panels
- receipts show what changed after each action

That makes the cube closer to a portable console for an AI agent: one compact
object with visible state, legal actions, and tool outputs. A face can show a
terminal, another can show task state, another can show benchmark score or
contracts, and another can show the next legal moves. The AI does not need to
imagine the hidden machine; it can read the panels and choose the next turn.

For AetherDesk, this suggests a practical interface:

`Rubix face -> app tile -> shell/browser/tool -> receipt -> face update`

The cube remains finite as a visual object. The attached runtime and tools are
where real computation and product work happen.

The current CLI returns this as `display_faces`:

| Face | Panel | Purpose |
| --- | --- | --- |
| `R` / `KO` | `terminal` | program, pointer, and step count |
| `L` / `AV` | `tools` | attached spine, CLI, and display ports |
| `U` / `RU` | `task_state` | move count, last move, active lane |
| `D` / `CA` | `output` | bytes, text, and tape cells |
| `F` / `UM` | `legal_moves` | available controller moves |
| `B` / `DR` | `receipt` | schema and runtime proof |

This keeps the UI contract small: each face has `tongue`, `app`, `title`, and
`lines`. A frontend can render those lines as panels now, then later replace a
panel with a richer terminal, browser, graph, or game view without changing the
machine receipt.

## Atomic And Field Mapping

The face mapping is tied back to the existing chemistry/physics notes instead of
being a separate metaphor.

From `Langues and Related Fields`:

| Face | Tongue | Field | Phi Weight |
| --- | --- | --- | --- |
| `R` | `KO` | authority / control / flow start | `1.00` |
| `L` | `AV` | transport / messaging / context carriage | `1.62` |
| `U` | `RU` | policy / constraints / binding | `2.62` |
| `D` | `CA` | compute / transform / ciphertext | `4.24` |
| `F` | `UM` | security / secrets / sensitive pressure | `6.85` |
| `B` | `DR` | schema / integrity / authentication | `11.09` |

From `Atomic Op Features - 8 Vector`, every face atom also carries:

`[op_id + 1, group, period, valence, chi, band, tongue_id, 0.0]`

The `atomic_faces` receipt uses `python.scbe.atomic_tokenization` to fill the
element, trit vector, band, resilience, adaptivity, and trust fields. This makes
the Rubix display a combined field surface: cube command, tongue field, atomic
state, and executable spine receipt all stay aligned.

## Instruction Mapping

| Move | Instruction | Meaning | Face Tongue |
| --- | --- | --- | --- |
| `R` | `>` | pointer right | `KO` |
| `R'` | `<` | pointer left | `KO` |
| `U` | `+` | increment cell | `RU` |
| `U'` | `-` | decrement cell | `RU` |
| `D` | `.` | emit cell | `CA` |
| `D'` | `,` | read input | `CA` |
| `F` | `[` | loop open | `UM` |
| `F'` | `]` | loop close | `UM` |
| `B` | `!` | seal checkpoint | `DR` |
| `B'` | `#` | receipt checkpoint | `DR` |
| `L` | `@` | tongue rotate | `AV` |
| `L'` | `~` | tongue rotate back | `AV` |

The executable subset is Brainfuck-equivalent: `> < + - . , [ ]`.
With unbounded tape and unbounded execution time, that is Turing complete.
The Turing-complete claim lives in the bit-spine runtime, not in the finite cube
notation. The cube is the keyboard/control surface.

## Why This Helps The Benchmark

The model does not need to invent arbitrary code. It can choose legal cube
turns from a tiny menu:

- move pointer
- mutate cell
- open/close loop
- emit/read
- rotate conlang lane
- seal receipt

The backend can substitute those turns into benchmark actions:

- `R/R'` route between contract slots
- `U/U'` adjust state counters or confidence
- `F/F'` enter/exit repair loops
- `D` emit a verified artifact
- `B` seal a receipt

The same easy operator surface can run different backend wires.

## Runnable Surface

Use:

```powershell
python -m python.scbe.turing_rubix "U U U D" --json
```

That compiles cube moves into a tiny program, runs it, and returns the conlang
projection plus final tape/output receipt from `bit_spine.run_ops_receipt`.
