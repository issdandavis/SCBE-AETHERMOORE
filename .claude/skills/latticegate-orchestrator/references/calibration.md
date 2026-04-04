# Threshold Calibration Protocol

## Objective
Empirically determine tau_allow and tau_collapse for a specific deployment domain
by measuring Davis Security Scores on a labeled corpus of known-safe and
known-adversarial prompts.

## Steps

### 1. Collect Corpus
- Minimum 200 prompts per class: SAFE, BORDERLINE, ADVERSARIAL
- Label by domain experts, not by the model itself (no circular validation)
- Document corpus source and labeling criteria

### 2. Compute DS Distribution
Run /drift-check on all corpus prompts. Record:
- DS per prompt
- Poincare radius per prompt
- Embedding model ID and version

### 3. Set Thresholds via ROC Analysis
Plot true positive rate vs. false positive rate at each DS cutoff.
Select:
- tau_allow: DS value at 95% true-safe recall (conservative)
- tau_collapse: DS value at 1% false-collapse rate (strict)

Report the F1 score at both thresholds.

### 4. Document and Sign Off
Store results in this file:
```
EMBEDDING_MODEL_ID : <id>
CORPUS_SIZE        : <n> prompts
CORPUS_DATE        : <ISO date>
tau_allow          : <value>  (95% recall threshold)
tau_collapse       : <value>  (1% FPR threshold)
F1_allow           : <value>
F1_collapse        : <value>
CALIBRATED_BY      : <name>
CALIBRATION_DATE   : <ISO date>
```

Only after this block is filled may the UNCALIBRATED flag be removed
from audit reports.

## Current Status
**UNCALIBRATED** — defaults tau_allow = 0.72, tau_collapse = 0.31 are
engineering estimates, not validated values.

## Corpus Sources Available

From the SCBE training pipeline:

| Class | Source | Records Available |
|-------|--------|-------------------|
| SAFE | training-data/sft/*.jsonl (governance=ALLOW) | 63,200+ |
| BORDERLINE | adversarial_candy_sft.jsonl (governance=QUARANTINE) | 26+ |
| ADVERSARIAL | adversarial_candy_sft.jsonl (governance=DENY) | 4+ |

**Gap**: BORDERLINE and ADVERSARIAL classes need 200+ each.
Generate additional records using `scripts/generate_adversarial_candy.py`
before running calibration.
