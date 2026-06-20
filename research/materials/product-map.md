# Materials Research Product Map

This maps the research folder into sellable product surfaces.

## Primary Product

### AI Materials Bench

What it sells:

- A visual, receipt-producing workbench for materials concepts.
- Human-readable assumptions.
- Backend math checks.
- Diagrams for field geometry, fiber/optics, thermal paths, and material stacks.

Core rooms:

- `fiber-optics` - waveguide, optical channel, attenuation, group delay.
- `field-geometry` - coils, magnetic guides, orientation, coupling.
- `thermal-vacuum` - reflection, insulation, thermal cycling, material failure.
- `space-materials` - vacuum, microgravity, deployment constraints, maintenance burden.
- `chemistry-bridge` - safe formulas, balancing, properties, receipts, and toolchain links.

## Secondary Product

### AI Chemistry Set

What it sells:

- Equation balancing.
- Structured explanations.
- Safe chemistry education.
- Visual experiment cards.
- Receipts for assumptions and outputs.

Materials connection:

- Converts chemistry notes into product-safe educational and design-review outputs.
- Can feed material compatibility, environmental constraints, and reaction-class summaries without exposing hazardous procedural instructions.

## Backend Direction

Short-term:

- Keep current JavaScript API handlers for fast Vercel deployment.
- Add scenario presets from this folder.
- Return consistent JSON receipts with assumptions, numbers, limits, and source tags.

Medium-term:

- Bridge selected formulas from `src\physics_sim`.
- Add RDKit / Open Babel / ASE as optional local or worker-backed adapters.
- Add source citations from `research\materials\source-inventory.md`.

Long-term:

- Build a terminal room around materials work:
  - chat mode for non-coders
  - input mode for coders
  - projector/stage mode for diagrams
  - command preflight for dangerous operations

## UI Direction

The interface should feel like a serious lab console, not a legal claims page.

Required surfaces:

- visual diagram canvas
- assumptions panel
- calculated metrics panel
- receipt output
- scenario selector
- source note link
- command/export button

Do not lead with:

- patent language
- governance claims
- military framing
- unverified performance claims
- procedural chemical synthesis instructions
