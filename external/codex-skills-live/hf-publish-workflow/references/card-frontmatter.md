# Hugging Face Card Frontmatter

Use the smallest valid block that matches the repo type.

## Model Card

```yaml
---
language:
  - en
license: mit
pipeline_tag: text-generation
library_name: transformers
tags:
  - scbe
  - aethermoore
  - governance
  - cryptography
  - hyperbolic-geometry
  - safety
  - reproducible
---
```

## Dataset Card

```yaml
---
language:
  - en
license: mit
task_categories:
  - text-generation
pretty_name: SCBE AetherMoore Dataset
tags:
  - scbe
  - aethermoore
  - governance
  - cryptography
  - hyperbolic-geometry
  - safety
  - structured-data
---
```

## Space README Frontmatter

```yaml
---
title: SCBE AetherMoore Demo
emoji: "🧭"
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: "5.0.0"
app_file: app.py
pinned: false
tags:
  - scbe
  - aethermoore
  - governance
  - cryptography
  - hyperbolic-geometry
  - safety
---
```

## Notes

- Replace placeholder values (`license`, `pipeline_tag`, `sdk_version`, `app_file`) with real project values.
- Keep tags stable across repos to improve cross-repo discoverability.
- Add `datasets:` and `base_model:` keys when those relationships are known.
