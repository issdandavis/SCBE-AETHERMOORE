# Human Noise and Correction Tagging

Date: 2026-06-27
Status: draft training policy

## Purpose

Preserve human-origin messiness while still teaching likely corrections.

Instead of silently converting:

```text
wiht -> with
```

Store:

```text
wiht(with)
```

or when uncertain:

```text
aethredesk(AetherDesk?)
```

## Why

Human spelling errors, unusual spacing, raw phrasing, and invented terms are part of the real distribution. If we erase them before training, the model learns polished AI prose instead of Issac's actual working style.

## Tags

| Tag | Use |
|---|---|
| `human_typo` | Surface form appears to be a typo. |
| `human_style` | Surface form is part of voice/style, not a typo. |
| `correction_pair` | Surface and correction are stored together. |
| `uncertain_correction` | Correction is likely but not confirmed. |
| `canonical_project_term` | Preferred project spelling. |
| `unknown_word` | Token not known yet. |
| `context_inferred` | Correction inferred from context. |
| `preserve_surface` | Do not overwrite the original. |

## Packet example

```json
{
  "schema": "scbe.human_noise.v1",
  "surface": "trainging",
  "correction": "training",
  "notation": "trainging(training)",
  "tags": ["user_original", "human_typo", "correction_pair", "preserve_surface"],
  "context": "AI model training workflow",
  "confidence": "high"
}
```

## Unknown project term example

```json
{
  "schema": "scbe.human_noise.v1",
  "surface": "aethredesk",
  "correction": "AetherDesk",
  "notation": "aethredesk(AetherDesk?)",
  "tags": ["user_original", "unknown_word", "context_inferred", "preserve_surface"],
  "context": "browser, terminal, AI workbench, home screen",
  "confidence": "medium"
}
```

## Training rule

Keep both:

1. the raw user surface form
2. the likely/canonical correction

Do not train only on the correction.

## Tokenizer role

Tokenizer packet:

```json
{
  "surface": "wiht",
  "canonical": "with",
  "source": "user_original",
  "confidence": "high",
  "lane": ["human_noise", "correction_pair"]
}
```

Conlang/coding lanes can then add:

```json
{
  "draumric": "structure/build context",
  "velmari": "signal/language context",
  "binary": "surface bytes",
  "hex": "transport representation"
}
```

## SFT pattern

Prompt:

```text
Tag this user text while preserving spelling: "we are trainging ai to use aethredesk"
```

Response:

```json
{
  "plain_text": "we are trainging ai to use aethredesk",
  "corrections": [
    {"surface": "trainging", "correction": "training", "notation": "trainging(training)"},
    {"surface": "aethredesk", "correction": "AetherDesk", "notation": "aethredesk(AetherDesk?)"}
  ]
}
```

## Release rule

Official text may use corrected spelling, but training and provenance archives must keep the raw user original.

