# Source Model

## Goal

Keep one canonical manuscript and derive every publication artifact from it.
Do not let the upload copy become the editorial source of truth.

## Recommended Layout

```text
project/
├── manuscript/
│   ├── source.md
│   ├── metadata.yaml
│   └── sections/
├── outputs/
│   ├── epub/
│   ├── pdf/
│   ├── docx/
│   └── preview/
├── review/
│   ├── audits/
│   ├── persona-notes/
│   └── device-checks/
├── art/
│   ├── prompts/
│   ├── candidates/
│   └── final/
└── publish/
    ├── packets/
    ├── pricing/
    └── metadata/
```

## Canonical Inputs

- `source manuscript`
  - One markdown or document source that the author edits directly.

- `metadata`
  - Title, subtitle, author, series, trim targets, audience, keywords, rights, release intent.

- `art brief`
  - Cover direction, motifs, must-include, must-avoid, output sizes.

## Conversion Matrix

Treat the matrix as explicit data:

| Source | Target | Purpose |
|---|---|---|
| markdown | EPUB | Kindle and reflowable review |
| markdown | PDF | print interior proof |
| markdown | DOCX | editor or collaborator review |
| metadata + art brief | cover prompt pack | AI art generation |
| outputs + metadata | publish packet | upload-ready bundle |

## Rules

1. Edit the source, not the compiled output.
2. Keep generated artifacts disposable and reproducible.
3. Store review notes outside the manuscript unless they are accepted edits.
4. Freeze text before running broad art and upload work.
