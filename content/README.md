# content/

Published and publishable writing. No code.

| Folder | Contents |
|--------|----------|
| `articles/` | 87 dated technical and marketing articles |
| `articles/platforms/` | Per-platform rewrites (Bluesky, Dev.to, LinkedIn, Medium, Reddit, Substack, Hugging Face, and others), including two generated research-campaign batches |
| `book/` | Fiction manuscripts; `book/reader-edition/` is the chapter set consumed by the audiobook narrator |
| `marketing/` | Marketing copy |

`scripts/publish/post_all.py` selects files from `articles/` by filename prefix, and `scripts/audiobook/narrator_voice_system.py` reads every `.md` in `book/reader-edition/`. Do not add stray Markdown files to those two folders.

---

Every file in this directory is listed with a one-line description in [`docs/file-index/content.md`](../docs/file-index/content.md).
