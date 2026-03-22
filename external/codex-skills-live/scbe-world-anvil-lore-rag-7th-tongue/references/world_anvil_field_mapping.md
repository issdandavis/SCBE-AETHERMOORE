# World Anvil Field Mapping

Use this reference when normalizing World Anvil export JSON into the local lore index.

## Canonical Record Fields

- `title`: display title for retrieval and citation
- `content`: primary text body used for chunking and embedding
- `source_path`: absolute or repo-relative file path
- `source_type`: parser type (`world_anvil_json`, `md`, `txt`, `rst`)
- `url`: canonical World Anvil URL if present
- `tags`: normalized list of tags
- `category`: article/category/type grouping

## Input Key Priority (Current Parser)

- Title priority:
  - `title`
  - `name`
  - `slug`
  - `_id`
  - fallback: filename stem

- Content/body priority:
  - `content`
  - `body`
  - `text`
  - `description`
  - `excerpt`
  - `markdown`
  - fallback: full JSON object (serialized)

- URL priority:
  - `url`
  - `permalink`

- Tags priority:
  - `tags` (list)
  - `tag` (string or list)
  - string tags are split by comma

- Category priority:
  - `category`
  - `type`

## Typical World Anvil Object Shapes

- Article-like:
  - `id`, `title`, `content`, `slug`, `url`, `tags`, `category`

- Timeline/event-like:
  - `title`, `description`, `content`, `date`, `timeline`, `tags`

- Map marker/location-like:
  - `name`, `description`, `content`, `map`, `coordinates`, `tags`

- Character/NPC-like:
  - `name`, `title`, `description`, `content`, `relations`, `tags`

## Normalization Notes

- Keep raw language and lore terms unchanged; do not rewrite names during indexing.
- Preserve unicode text from exports.
- Strip markdown decoration from text chunks but keep semantic text.
- Deduplicate by `(title, first 120 chars of content)` to avoid repeated nested objects.

## Retrieval and Citation Contract

- Citation format:
  - `<title> [<filename>#chunk<index>]`
- Prefer records with real `url` values when tie-breaking equal-ranked results.
- Use World Anvil records as primary canon source; repo docs are fallback context.
