# SCBE Aligned Foundations Program

This skill supports a staged curriculum where the same concept is taught in several synchronized forms and then reused across domain lanes.

## Program stages

1. Primitive substrate
   - alphabet
   - numbers
   - binary transport framing
   - Sacred Tongues lane names and full names
2. Governance substrate
   - `L10` through `L14`
   - `ALLOW`, `QUARANTINE`, `ESCALATE`, `DENY`
3. Chemistry lane
   - reaction class
   - atom conservation
   - stability and instability
   - reason for verdict
4. Coding lane
   - bijective codeflow
   - language-family slot preservation
   - Sacred-Tongues code primaries
5. Transfer lane
   - same concept preserved across chemistry, code, governance, and transport

## Current local corpus anchors

- `training-data/sft/aligned_foundations_train.sft.jsonl`
- `training-data/sft/aligned_foundations_holdout.sft.jsonl`
- `training-data/sft/chemistry_primary_train.sft.jsonl`
- `training-data/sft/chemistry_primary_holdout.sft.jsonl`
- `training-data/sft/bijective_codeflow_v1_train.sft.jsonl`
- `training-data/sft/bijective_codeflow_v1_holdout.sft.jsonl`
- `training-data/sft/drill_langues_full_train.sft.jsonl`
- `training-data/sft/drill_langues_full_holdout.sft.jsonl`

## Active profiles

- `config/model_training/chemistry-qwen-primary.json`
- `config/model_training/aligned-foundations-qwen-primary.json`
- `config/model_training/coder-qwen-code-primaries.json`

## High-signal failure modes

- abbreviations appear without full names
- layer numbers appear without layer names
- `ESCALATE` is missing from tier data
- chemistry is present as packet syntax but not as explanatory understanding
- coding corpora drift away from the shared lane vocabulary
- training loss improves while structural metrics stay flat

## Minimum expectations for new data

Every new shard should answer:

- what is the concept
- what is its mathematical form
- what is the plain-English form
- what is the lane or tongue mapping
- what is the packet or binary framing
- what is the verdict and why
