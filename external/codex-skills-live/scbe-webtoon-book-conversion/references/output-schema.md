# Output Schema

Every storyboard packet should contain:

## Required fields

- `episode_id`
- `section_title`
- `section_type`
- `source_markdown`
- `key_script`
- `target_panel_min`
- `target_panel_max`
- `status`

## Required content blocks

1. `Episode intent`
   One short paragraph describing what changes by the end of the episode.

2. `Panel list`
   Ordered list of panels with one line each:
   - panel number
   - panel type
   - visual beat
   - emotional or story job

3. `Visual anchors`
   Short list of recurring objects, colors, symbols, and environment rules.

4. `Prompt lane notes`
   Only the details an image model needs:
   - character state
   - camera bias
   - lighting
   - sacred color requirements
   - forbidden drift

5. `Continuity notes`
   Anything that later panels or chapters must preserve.
