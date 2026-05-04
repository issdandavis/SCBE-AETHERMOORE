# Open-Source AI Detection Integration

Date: 2026-05-03

## Goal

Add an AI-likelihood lane to the SCBE fiction-quality benchmark without confusing three different questions:

1. Is the passage good writing?
2. Does the passage look machine-generated?
3. Is the passage useful for training or revision?

Those are separate axes. A detector can call good human prose "AI" by mistake, and a high-quality AI passage can look human after editing. The benchmark must show those failure modes instead of hiding them.

## Open-Source References

### RAID

RAID is the current benchmark lane to watch for robust machine-generated text detection. Its repository describes it as a large benchmark for evaluating AI-generated text detectors, and the associated paper emphasizes that many detectors fail under adversarial attacks, varied sampling strategies, and unseen generators.

Use RAID for later public validation, not as a lightweight local dependency.

Source: https://github.com/liamdugan/raid

### Binoculars

Binoculars is the best next detector shape for a serious local implementation. It is a zero-shot detector that contrasts two language models and reports strong performance with very low false positive rate in the paper's evaluation.

Why it matters here: it is aligned with the user's goal of asking "does this look AI-generated?" while keeping false positives on human text visible.

Source: https://arxiv.org/abs/2401.12070

### GLTR

GLTR is useful as the human-readable explanation model. It uses statistical artifacts from language-model probabilities and was designed to help non-experts review generated text. The paper reports that GLTR-style annotation improved human detection in a study from 54 percent to 72 percent.

Why it matters here: SCBE needs readable reasons, not just a hidden classifier score.

Source: https://arxiv.org/abs/1906.04043

### Beemo

Beemo is useful because it tests mixed authorship and edited AI text. It explicitly covers human-written, machine-generated, expert-edited, and LLM-edited text.

Why it matters here: the user's actual question is not just "AI or human?" It is "how do people react to generated work, edited work, famous human work, and my own book side by side?"

Source: https://toloka.ai/ai-detection-benchmark

### SuperAnnotate Generated Text Detector

This is a practical open-source service path. It uses a fine-tuned RoBERTa Large model and exposes an HTTP service. It also points to model variants optimized for low false positive rate and high overall accuracy.

Why it matters here: this is a likely external detector adapter once we are ready to run a heavier model or service.

Source: https://github.com/superannotateai/generated_text_detector

## What Was Added Now

The local benchmark now emits:

```json
"ai_detection": {
  "schema_version": "scbe_local_ai_likelihood_v1",
  "detector_family": "transparent_stylometric_gltr_inspired",
  "ai_likelihood_score": 0,
  "label": "likely_human_or_human_edited"
}
```

This is a local heuristic lane. It is not proof of authorship.

Signals:

- generic-generation markers
- assistant-style disclaimer markers
- synthetic fiction pressure markers
- vague filler
- lexical diversity
- sentence-length variance
- missing null-space anchors
- thought-track coverage
- over-smoothness

## Current Blind-Round Behavior

Latest local run:

- Public-domain famous human average AI-likelihood: 23.002
- Own book excerpt AI-likelihood: 27.208
- Known AI control average AI-likelihood: 47.958
- Generic AI fantasy control: 86.916, `likely_ai_generated`
- Grounded AI control: 9.0, `likely_human_or_human_edited`

Interpretation:

The detector catches low-quality generic AI writing. It does not catch strong or grounded AI writing. That is useful because it proves the benchmark should never claim "AI detector solved." Instead, it should report false positives and false negatives as first-class evidence.

## Package Direction

Keep the public CLI verbs stable:

```powershell
scbe-fiction-quality score --json
scbe-fiction-quality blind-round --json
```

Later add:

```powershell
scbe-fiction-quality detect --detector local
scbe-fiction-quality detect --detector binoculars
scbe-fiction-quality detect --detector superannotate-http --url http://127.0.0.1:8080/detect
```

The default should remain local and transparent. Heavier detectors should be optional adapters.

## Next Hardening Step

Build a detector adapter contract:

```json
{
  "schema_version": "scbe_ai_detection_adapter_v1",
  "detector": "binoculars|superannotate|local",
  "ai_likelihood_score": 0,
  "label": "likely_human_or_human_edited|mixed_or_uncertain|likely_ai_generated",
  "confidence": 0,
  "evidence": {}
}
```

Then add one optional external detector first. Recommended order:

1. SuperAnnotate HTTP adapter for practical service testing.
2. Binoculars adapter for stronger zero-shot local research.
3. RAID/Beemo eval pack for public benchmark comparison.
