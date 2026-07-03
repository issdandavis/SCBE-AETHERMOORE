# Iridescent Book and Training Workflow

Date: 2026-06-27
Status: draft workflow

## Goal

Build a Bible-style AI writing/training system where colored lettering distinguishes:

- Issac's direct words
- Issac's voice guides
- saved user text
- user-originated ideas
- AI output
- human-authored external research
- verified AI output
- unverified claims
- facts
- feelings
- cutting-edge discovery
- established proven knowledge
- established but unproven knowledge
- code/test/production/tool contexts
- SCBE conlang and coding-language lanes

## Workflow

1. Capture text.
2. Preserve original user words.
3. Segment into spans.
4. Tag each span with source/confidence/function/project/conlang.
5. Render colored/iridescent book view.
6. Export machine-readable packet.
7. Convert approved packets into training data.
8. Use verifier to flag unsupported claims.

## Data lanes

| Lane | Durable? | Training use |
|---|---:|---|
| raw chat trace | temporary | no, curate first |
| user original text | yes | high-value voice/source anchor |
| AI draft | yes, marked | useful if tagged as AI |
| verified AI | yes | high-value if receipt-backed |
| external human research | yes, license/source tracked | anti-collapse anchor |
| unverified research | temporary/draft | eval/negative examples |
| final book passage | yes | publication/export |

## Example packet

```json
{
  "schema": "scbe.iridescent_text.v1",
  "id": "book_training_example_001",
  "plain_text": "Use Colab as compute, not truth.",
  "segments": [
    {
      "start": 0,
      "end": 26,
      "tags": {
        "source": ["user_idea", "ai_edited_user"],
        "confidence": ["verified_ai"],
        "function": ["instruction", "constraint"],
        "project": ["colab", "tool"],
        "runtime": ["draft"]
      },
      "render": {
        "mode": "iridescent_span",
        "palette": ["teal", "violet", "emerald", "red", "orange", "gray-blue"]
      }
    }
  ],
  "metadata": {
    "created_by": "aetherdesk",
    "provenance": "user_concept_plus_ai_spec",
    "validated": false
  }
}
```

## Training row shape

```json
{
  "messages": [
    {
      "role": "system",
      "content": "Tag text for SCBE iridescent provenance. Output only JSON."
    },
    {
      "role": "user",
      "content": "Text: Use Colab as compute, not truth. Context: Issac idea, AI drafted wording, Colab tool boundary."
    },
    {
      "role": "assistant",
      "content": "{...scbe.iridescent_text.v1 packet...}"
    }
  ],
  "metadata": {
    "source_type": "iridescent_text_training",
    "validated": false
  }
}
```

## Rendering modes

| Mode | Use |
|---|---|
| `plain` | No visible color; metadata still exists. |
| `span_color` | Whole span has one dominant color. |
| `iridescent_span` | Span gradient encodes multiple layers. |
| `glyph_stripe` | Each letter carries a different context layer. |
| `underline_only` | Use when accessibility/readability matters. |

## Book export targets

- HTML with `<span data-tags="">`
- Markdown with sidecar JSON
- PDF later
- SFT JSONL for training
- adventure/code assignment sheets

## Important constraints

- Do not make color the only carrier of meaning.
- Do not overwrite user-original text.
- Do not erase spelling errors before training; store likely corrections as bracketed pairs.
- Do not mark AI text as user text.
- Do not mark unverified research as fact.
- Do not train on research snippets without source/license review.
- Do not keep all raw traces forever.

## Human typo/correction workflow

Example:

```text
raw:    "we are trainging ai to use aethredesk"
tagged: "we are trainging(training) ai to use aethredesk(AetherDesk?)"
```

Rules:

- raw user text remains immutable
- correction is metadata, not replacement
- `?` marks uncertain correction
- tokenizer stores both `surface` and `canonical`
- conlang/coding lanes can attach project context

## Next implementation

1. Build a tiny packet-to-HTML renderer.
2. Add a book editor panel in AetherDesk.
3. Add a tag palette.
4. Add export to SFT JSONL.
5. Add verifier checks:
   - source missing
   - unsupported fact
   - unverified claim colored as proven
   - AI output mislabeled as user original
