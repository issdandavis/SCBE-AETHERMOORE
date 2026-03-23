# Anchor Sheet Spec

Use this file when creating or revising character anchor sheets or environment swatch sheets.

## Character Anchor Sheet

Create one sheet per character.

Required fields:

- `Character`: canonical name
- `Story Role`: why this character matters in the active arc
- `Visual Center`: one sentence for the immediate read
- `Silhouette and Posture`: body read, stance, motion logic, habitual stillness or tension
- `Face Read`: age impression, expression baseline, emotional readability
- `Hair and Distinctive Features`: hair behavior, eyes, scars, companion marks, other recognition anchors
- `Costume Locks`: items that must survive across panels
- `Props and Companion Logic`: tools, books, animals, sigils, carried objects
- `Palette`: dominant colors, accent colors, light logic
- `Expression Range`: 3-5 approved expression lanes
- `No-Drift Rules`: things the renderer must not change
- `Panel Flex`: allowed compression or exaggeration modes and why
- `Reference Sources`: manuscript lines, storyboard packets, or canon notes

Use this template:

```md
## Character: <Name>

- Story Role:
- Visual Center:
- Silhouette and Posture:
- Face Read:
- Hair and Distinctive Features:
- Costume Locks:
- Props and Companion Logic:
- Palette:
- Expression Range:
- No-Drift Rules:
- Panel Flex:
- Reference Sources:
```

## Environment Swatch Sheet

Create one sheet per continuity-critical location.

Required fields:

- `Environment`: canonical location name
- `Story Use`: what beats this location supports
- `Visual Center`: immediate read
- `Palette`: dominant, secondary, and accent colors
- `Materials`: stone, crystal, iron, wood, fog, foliage, etc.
- `Lighting Logic`: daylight, ambient glow, warning lights, weather, or magical illumination
- `Geometry and Scale`: room height, verticality, crowding, openness, platforms, thresholds
- `Operational Details`: interfaces, sigils, tools, signage, cable logic, policy architecture
- `Atmosphere`: scent, weather, pulse, hum, stillness, dust, particles
- `Recurring Props`: objects that should recur in multiple panels
- `No-Drift Rules`: what must not change
- `Linked Characters`: who is most associated with this place
- `Reference Sources`: manuscript lines, episode packets, or approved art

Use this template:

```md
## Environment: <Name>

- Story Use:
- Visual Center:
- Palette:
- Materials:
- Lighting Logic:
- Geometry and Scale:
- Operational Details:
- Atmosphere:
- Recurring Props:
- No-Drift Rules:
- Linked Characters:
- Reference Sources:
```

## Practical Rules

- Prefer one strong visual center over a long style paragraph.
- Keep the sheet readable enough to paste into prompt work.
- Separate canon from mood. Mood can flex; canon should not.
- Put specific nouns before aesthetic adjectives.
- If a detail appears only once and is not narratively load-bearing, keep it out of the lock list.
- If a detail appears in dialogue, action, and environment together, it probably belongs in the lock list.

## Minimum Deliverable

For a new arc, do not proceed to full panel generation without:

- `3` character anchor sheets for the dominant cast
- `2-4` environment swatch sheets for the dominant spaces
- at least one cited source line per sheet
