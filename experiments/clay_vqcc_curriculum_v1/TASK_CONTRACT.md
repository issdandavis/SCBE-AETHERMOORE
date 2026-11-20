# VQCC cost-comparison capability contract

## Capability

Given two **already valid** 32-opcode Kickmix fragments, choose the fragment
with fewer Toffoli-class operations (`30`, `31`, `32`, `b0`, `b1`, `b2`), or
return `T` when they tie. This is a circuit-search resource discriminator. It
does not assert that one fragment can replace the other.

This is specifically an **input-access sanity task**: it measures whether the
new path can bind opcode evidence to an exact cost relation on unseen families.
It is not yet the findings-ranking capability and is not a circuit optimizer.

```text
public.gate_count rows + external circuit-family sidecar
  -> independently recount each opcode window
  -> family-disjoint train/holdout split
  -> balanced fixed-length A/B/T comparisons
  -> Clay candidate and four matched controls
  -> exact, macro-balanced, and Toffoli-regret evaluation
```

## Exact interface

- Input windows contain exactly 32 opcode bytes each.
- Prompt encoding is `TASK=COST_COMPARE_V1`, followed by fixed-width `A=` and
  `B=` hexadecimal rows.
- Output is exactly one character: `A`, `B`, or `T`. All targets therefore have
  equal length.
- The answer is recomputed from the opcodes; a conflicting corpus answer is a
  hard error.
- Every stored count is recomputed from its opcode bytes, and every comparison
  identity binds both record IDs, families, opcode bytes, and recomputed counts.
- Family IDs are required from the separately sealed split sidecar. The broad
  `public-vqcc-opcode-windows` corpus group is not accepted as proof of family
  separation.
- Evaluation records are used once. A and B examples use prespecified count-gap
  strata with identical gap distributions.

## Controls

Run at least three aligned seeds:

1. `candidate`: VQCC examples with intact input/target bindings.
2. `no_intervention`: unchanged frozen parent without the new trainable path.
3. `equal_parameter`: identical trainable parameter count and update count,
   trained on a token-matched ordinary corpus.
4. `shuffled_binding`: identical VQCC occurrence pool with a one-to-one target
   derangement that preserves exact A/B/T marginals.
5. `zero_update`: candidate architecture and initialization with zero updates.

All trained arms begin from bit-identical trainable tensors. The candidate,
equal-parameter, shuffled-binding, and zero-update arms have identical
trainable parameter counts; the first three have identical update counts.
The `ArmSpec` declarations are only preregistration metadata. The runner must
independently count and hash actual trainable tensors before any update; the
metadata itself is not proof that capacity is equal.

## Evaluation and promotion

- Holdout circuit/notebook families and record IDs must be absent from train.
- A/B/T labels are exactly balanced and prompts are constant length, fixing the
  majority baseline at 1/3.
- Primary metric: macro-balanced exact accuracy.
- Secondary metrics: exact accuracy, parse coverage, per-label recall, and mean
  extra Toffoli cost selected relative to the cheaper fragment.
- A second once-paired, record-unique evaluation preserves natural A/B/T
  prevalence and reports natural exact accuracy separately. It cannot be
  replaced by the balanced diagnostic.
- Every result reports unique-record count, unique-family count, maximum record
  reuse, and count-gap distributions.
- The candidate must beat **every** control by more than both 0.02 absolute and
  two pooled standard deviations, while retaining the sealed dyadic behavior
  exactly. Each aligned score carries an explicit unique seed ID; NaN, infinity,
  out-of-range scores, or repeated seeds are rejected. Otherwise report
  `UNDERPOWERED` or `REJECT`; never call it a win.

## Explicit non-claims

Passing this task does not prove semantic equivalence, verifier acceptance,
Kaggle score improvement, findings ranking, proposal quality, or the ability to
synthesize a circuit. It only proves input access to a family-generalizing
resource-count relation. Any use in search remains downstream of a separate
equivalence/verifier gate.

## Public-finding binding task

`findings_task.py` adds a separate diagnostic. It parses only the pinned
`public.experimental_findings` grammar and asks which of two measured
limitations belongs to a public experiment description.

- Pairing is within task and answer-length buckets.
- Paired questions reuse the same two answers, once with `A` correct and once
  with `B` correct.
- Every retained answer source is therefore correct once and a distractor
  once; answer length and writing style cannot determine the label.
- Questions and answers retain source-family identities from the sealed split
  sidecar, and train/holdout families must be disjoint.
- The training control deranges answers one-to-one inside the same task/length
  stratum without changing answer-source marginals.
- Evaluation reports coverage, exact accuracy, task-macro accuracy, per-task
  accuracy, and conditional correct-answer log-score margin.

Passing this task shows experiment-result binding on unseen public source
families. It does not show that Clay can rank new circuit proposals, prove
equivalence, or improve the Kaggle score.
