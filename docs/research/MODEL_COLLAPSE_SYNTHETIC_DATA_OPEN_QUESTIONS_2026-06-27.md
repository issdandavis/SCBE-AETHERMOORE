# Open Questions - Model Collapse and SCBE Training

Date: 2026-06-27

## Open questions

1. What human:AI ratio should SCBE enforce for each training lane?
2. Should typo/correction pairs be weighted higher for user-voice preservation?
3. How should tokenizer lanes encode `surface`, `canonical`, and `context_inferred` without bloating sequences too much?
4. Should conlang lanes be trained as visible text, metadata tokens, or both?
5. Which external human corpora are license-safe enough for release training?
6. How should we detect AI-style over-polishing in generated book passages?
7. What eval best measures "kept Issac's voice" instead of generic correctness?
8. Should unknown project terms require human confirmation before canonicalization?

## Next checks

- Build a small typo/correction SFT slice from direct user text.
- Add a tokenizer packet format for `surface/canonical/context`.
- Add eval tasks where the model must preserve spelling errors while suggesting bracketed corrections.
- Add model-collapse prevention metrics to the training manifest.

