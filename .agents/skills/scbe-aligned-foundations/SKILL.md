---
name: scbe-aligned-foundations
description: >-
  Use when building, extending, or auditing the SCBE multi-representation
  training program that aligns mathematics, English, Sacred Tongues lane
  naming, binary transport framing, chemistry packets, and coding primaries
  into one staged curriculum. Trigger this skill for tokenizer-native language
  lanes, chemistry-as-structure training, coding-primaries alignment, aligned
  foundation dataset generation, or transfer-eval planning across those lanes.

---

Use this skill when the task is to keep the SCBE token substrate aligned across
multiple representations instead of treating each dataset as an isolated fine-tune.

## Core rule

Preserve one concept across multiple synchronized forms:

- mathematics
- plain English
- Sacred Tongues abbreviation and full-name lane
- binary or packet framing
- domain lane instantiation such as chemistry or coding

Do not collapse those into one flat corpus if the alignment can be preserved.

## Workflow

1. Build or refresh the aligned foundations set:
   - `python scripts/build_aligned_foundations_sft.py`
2. Build or refresh the chemistry lane:
   - `python scripts/build_chemistry_primary_sft.py`
3. Treat local coding corpora as first-class:
   - `training-data/sft/bijective_codeflow_v1_*.sft.jsonl`
   - `training-data/sft/drill_langues_full_*.sft.jsonl`
4. Use the combined profile when the goal is shared substrate learning:
   - `config/model_training/aligned-foundations-qwen-primary.json`
5. Use the chemistry-only profile when isolating stability or conservation:
   - `config/model_training/chemistry-qwen-primary.json`

## What to check before training

- Full tongue names and abbreviations co-occur often enough
- Layer numbers and names co-occur for `L10` through `L14`
- Risk tiers are taught as a full set: `ALLOW`, `QUARANTINE`, `ESCALATE`, `DENY`
- Chemistry records state why a reaction is stable or unstable
- Coding records preserve slot alignment and bijective mappings

## Evaluation priorities

Judge success by structure, not just loss:

- token meaning stability
- cross-lane semantic preservation
- packet format compliance
- chemistry conservation and stability correctness
- coding slot and algorithm preservation
- transfer between chemistry, coding, and governance language

## References

Read these when shaping or auditing the lane:

- [program.md](references/program.md)
- [notes/theory/atomic-tokenizer-chemistry-unified.md](../../../notes/theory/atomic-tokenizer-chemistry-unified.md)
