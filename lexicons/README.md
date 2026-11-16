# lexicons/

Vocabulary data for the six Sacred Tongues, as JSON.

| File | Tongue |
|------|--------|
| `kor_aelin.json`, `kor_aelin_extended.json` | Kor'aelin (KO) |
| `avali.json` | Avali (AV) |
| `runethic.json` | Runethic (RU) |
| `cassisivadan.json` | Cassisivadan (CA) |
| `umbroth.json` | Umbroth (UM) |
| `draumric.json` | Draumric (DR) |

Each per-tongue file has `tongue`, `name`, `role`, `source`, `particles`, and `words` (some add `roots`). `eldritch-lexicon.json` and `sample-lexicon.json` use a combined `{version, tongues}` layout. `spiralverse_phrases.json` holds sacred phrases and the tongue registry. The two `swle_*.template.json` files are templates for the SWLE multilingual benchmark; their schemas are in `schemas/swle/`.

These are word lists. The 16x16 token grids used by the tokenizer are defined in code (`src/crypto/sacred_tongues.py`).

---

Every file in this directory is listed with a one-line description in [`docs/file-index/lexicons.md`](../docs/file-index/lexicons.md).
