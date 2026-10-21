# Multiview perspective reasoning benchmark

This experiment tests the neural use of the six-tongue codec without equating
reversibility with intelligence. The exact byte is the conserved event. Its six
Sacred Tongue encodings are six transport forms of that event. A separate set
of six evidence lenses supplies semantic interpretations.

Each evidence lens omits one of six signed evidence components. The benchmark
therefore knows all three of these independently:

1. the invariant result computed from all evidence;
2. what each partial lens concludes; and
3. which omitted component explains a disagreement.

Twenty-two of the 64 synthetic events are majority traps: the plurality of the
six partial interpretations differs from the invariant result. This prevents a
model from treating popularity as truth.

## Tasks

- leave-one-tongue-out identity recovery;
- residual recovery of the original tongue after the semantic core is aligned;
- held-out one-step forward and inverse transitions;
- two-to-five-step forward and backward composition;
- four-way parallel path selection;
- rollback after a wrong path and continuation from the recovered state;
- held-out invariant truth;
- all six perspective stances;
- the evidence axis responsible for disagreement; and
- minority-view preservation.

Activation snapshots retain same-event core and residual cosine matrices,
per-lens output distributions, lane predictions, the four attention-head paths
for the invariant query and every lens query, and one stepwise forward-path
trace. The six forms remain separate attention nodes instead of being averaged
before the read. These are bounded synthetic measurements, not private
chain-of-thought.

## Arms and controls

All arms use exactly the same neural architecture and parameter count.

- `aligned_identity_only`: reversible identity and byte retention without a
  transition or interpretation objective;
- `aligned_relational`: aligned tongues plus transition and interpretation
  objectives;
- `aligned_relational_cycle`: adds an explicit inverse/cycle objective;
- `aligned_cycle_no_residual`: removes the tongue-residue objective while
  keeping the parameters;
- `shuffled_relational_cycle`: independently permutes each tongue's binding;
- `ordinary_relational_cycle`: equal-width ordinary numeric features carrying
  the same byte and lane information; and
- `random_relational_cycle`: equal-width fixed random codes.

Three seeds are required. A tokenizer-specific claim requires the aligned
cycle arm to beat both the shuffled and ordinary controls on both the reasoning
floor and interpretation floor, with every paired seed positive and the mean
effect greater than twice pooled standard deviation. The floor is the minimum
component score, so a strong aggregate cannot hide a failed direction.

The cycle objective and split residual have separate registered gates. No arm
is promoted automatically.

Preflight disables fused CUDA attention in favor of the deterministic math
kernel and trains the same arm twice from the same seed. The full matrix is
refused unless the two resulting state hashes match exactly.

## Scope

This is a synthetic mechanism test. It can show whether exact identities,
surface residues, partial interpretations, causes of disagreement, and
reversible paths coexist in a learned state. It cannot establish sound judgment
about religion, history, ethics, or any other open domain. Those require
sourced records, explicit provenance, and evaluators that do not define truth
by majority vote.

Run:

```powershell
python -B scripts/experiments/multiview_perspective_reasoning.py --preflight-only
python -B scripts/experiments/multiview_perspective_reasoning.py --steps 600 --seeds 11,23,37
```
