# Prompt Injection Recall Improvement Plan

Updated: 2026-04-25

## Current Position

The SCBE adversarial harness beats the repo-native operational corpus, but it
does not yet beat ProtectAI on public one-shot prompt-injection datasets.

Latest full public matrix after adding the angular phase lattice lookup:

| Dataset | Before Recall | After Recall | Precision | False Positive Rate |
|---|---:|---:|---:|---:|
| `deepset/prompt-injections` | 0.1825 | 0.2091 | 0.8462 | 0.0251 |
| `zachz/prompt-injection-benchmark` | 0.2600 | 0.3200 | 0.9412 | 0.0388 |

This is a real gain, but it is not enough. The next goal is to exceed ProtectAI
recall while keeping false-positive pressure controlled.

## Useful Existing Assets

### 1. Static Adversarial Harness

Files:

- `tests/adversarial/scbe_harness.py`
- `tests/adversarial/attack_corpus.py`
- `scripts/benchmark/third_party_prompt_injection_matrix.py`

Use:

- Fast deterministic benchmark loop.
- Best place to measure one-shot recall improvements.
- Current weakness is phrase coverage, not runtime logic.

### 2. Runtime Governance Gate

Files:

- `src/governance/runtime_gate.py`
- `tests/test_runtime_gate.py`

Useful pieces:

- Reroute table for secrets, external sends, shell execution, destructive ops.
- High-confidence override and secret markers.
- Intent spike layer.
- Optional classifier hook.
- Optional trichromatic governance hook.

Finding:

- RuntimeGate alone is not a strong public one-shot classifier.
- It should be used as a runtime/bus execution guard, not the primary public
  static recall layer.

### 3. Trajectory Risk Gate

Files:

- `src/security/trajectory_risk_gate.py`
- `tests/security/test_trajectory_risk_gate.py`
- `scripts/benchmark/trajectory_risk_eval.py`

Use:

- Multi-turn time, intent, access, and need scoring.
- Separates benign user reset from safety/core-action steering.
- Should be wired into agent bus/runtime endpoints, not judged only on one-shot
  public datasets.

### 4. Angular Phase / Rhombic Lookup

Files:

- `src/security/phase_lattice_lookup.py`
- `tests/security/test_phase_lattice_lookup.py`

Use:

- Deterministic approximate lookup for attack-family phrasing.
- Converts text into sparse phi-spaced angular rows and rhombic phase buckets.
- Catches off-axis variants without making every regex a brittle straight line.

Finding:

- First useful recall gain landed here.
- Must remain sparse. Dense character buckets caused unacceptable false
  positives and were rejected by tests.
- Holographic overlay is a subclass/watermark signal, not a primary block
  trigger. It refines a phase hit but does not raise the blocking score alone.
- `origami_fold_path` is the deterministic "fortune teller" route: fixed answer
  leaves, with answer count controlled by fold depth and face count.

### 5. Training and Governance Data

Files and directories:

- `training-data/sft/governance_security_boundary_eval_v1.sft.jsonl`
- `training-data/sft/aligned_foundations_train.sft.jsonl`
- `training-data/sft/coding_system_full_v1_train.sft.jsonl`
- `scripts/benchmark/governance_security_eval.py`
- `artifacts/training/governance_classifier_sklearn/` if present

Use:

- Build a local lightweight classifier lane.
- Use public false negatives plus repo-native attacks as positive examples.
- Use baseline clean rows and benign reset examples as negative examples.

## Highest-Value Next Build

Build a three-lane `SCBECompositePromptInjectionGate`:

1. `SCBEDetectionGate` for existing geometric and lexical signals.
2. `PhaseLatticeLookup` for deterministic off-axis family recall.
3. A local sklearn/linear classifier trained on public benchmark positives,
   repo-native attacks, and clean baselines.

Decision rule:

- Block if any high-confidence deterministic lane fires.
- Block if classifier score is high.
- Review/sandbox if classifier score is medium and trajectory/access pressure
  is high.
- Allow benign resets when trajectory need and access pressure are low.

## Why This Can Beat ProtectAI

ProtectAI is strong on public one-shot phrasing because it has broad language
coverage. SCBE currently wins on operational sequencing and system-specific
governance, but weak public recall means many generic attack phrasings do not
activate enough signals.

The path to beat it is not one more keyword list. It is:

- deterministic exact markers for high-confidence patterns,
- angular/rhombic approximate lookup for phrase-family neighbors,
- local classifier for broad public wording,
- trajectory gate for time/access/need context.

## Guardrails

- Do not lower the global detection threshold blindly.
- Do not let phase lookup use dense character buckets; it over-collides.
- Every recall gain must be reported with false-positive rate.
- Public one-shot recall and multi-turn runtime safety are separate metrics.

## Commands

```powershell
python -m pytest tests\security\test_phase_lattice_lookup.py tests\adversarial\test_adversarial_benchmark.py tests\security\test_trajectory_risk_gate.py -q
python scripts\benchmark\third_party_prompt_injection_matrix.py --output artifacts\benchmark\third_party_prompt_injection_matrix\phase_lattice_after_full.json
python scripts\benchmark\trajectory_risk_eval.py
```
