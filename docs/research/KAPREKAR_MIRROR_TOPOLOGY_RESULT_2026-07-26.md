# Kaprekar Mirror Topology Shadow-Lane Result

Date: 2026-07-26

Status: **UNDERPOWERED - do not promote into Clay**

## Question

Does a mirrored Kaprekar representation provide useful relational structure
beyond ordinary digit features, deterministic random features, and the
unmirrored Kaprekar topology?

The proposed representation uses:

- the ordinary four-digit Kaprekar transition `K`;
- decimal reversal `M`;
- the conjugate mirror transition `M(K(M(x)))`;
- primary and mirror attractor depth;
- bounded three-coordinate points suitable for later Poincare projection;
- a literal palindrome envelope, `x || reverse(x)`, as an audit field.

This is a finite synthetic probe. It is not evidence that general neural
representations have this topology.

## Data Contract

The deterministic exporter produces 10,000 four-digit records, including the
10 repeated-digit states that enter the zero basin. The 9,990 non-repeated
states converge to 6174 in at most seven steps. Decimal permutation families
are assigned together to train, validation, or test by a stable SHA-256 split.
There are 715 families in total.

Learnable features, labels, and full trajectory audit data are separate JSON
objects. The benchmark feature builder reads only the state and auxiliary
view. It cannot read transition labels or trajectory paths.

## Benchmark

The primary task asks whether a destination lies on a source state's future
Kaprekar path. Every source contributes one positive and one negative. The
negative is matched to the positive on attractor basin and remaining depth.
Each seed produces 19,212 balanced pairs.

All arms use the same ridge learner and a 20-value feature array. The
`primary_random_pad` arm is the size-matched control: it contains the primary
topology plus five deterministic noise values, so it has the same active width
as the mirror arm.

Family-disjoint seeds: `7`, `2024`, `6174`.

| Condition | Seed 7 F1 | Seed 2024 F1 | Seed 6174 F1 | Mean F1 |
| --- | ---: | ---: | ---: | ---: |
| Raw digits | 0.768527 | 0.750471 | 0.756887 | 0.758628 |
| Digit statistics | 0.798551 | 0.754352 | 0.798851 | 0.783918 |
| Random shell | 0.833560 | 0.798625 | 0.816579 | 0.816255 |
| Shuffled depth | 0.839572 | 0.748544 | 0.802113 | 0.796743 |
| Primary topology | 0.846871 | 0.811621 | 0.848854 | 0.835782 |
| Primary plus random padding | 0.888004 | 0.808774 | 0.857553 | 0.851444 |
| Mirror topology | 0.870629 | 0.842877 | 0.873394 | 0.862300 |

## Promotion Gate

The gate operates on route error, `1 - F1`. A candidate must improve every
seed and exceed the stricter of:

- 5% of the control's mean error; or
- two times the pooled standard deviation.

Against digit statistics, mirror topology reduces mean route error from
0.216082 to 0.137700, a 36.27% relative reduction. All seeds improve and the
0.078382 absolute reduction exceeds the 0.043370 binding threshold.

Against the strongest matched control, `primary_random_pad`, mirror topology
reduces mean route error from 0.148556 to 0.137700, a 7.31% relative reduction.
The absolute reduction is only 0.010857 against a 0.061354 binding threshold.
The per-seed error reductions are `-0.017374`, `0.034102`, and `0.015842`, so
one seed loses.

The transition guard passes: mirror mean normalized MAE is `0.00003405`,
compared with `0.00003014` for digit statistics. Its `0.00000391` degradation
is below the `0.00000572` tolerance.

## Conclusion

The mirror representation carries measurable signal on this toy relational
task, but the evidence is not stable enough to distinguish that signal from a
same-capacity primary topology control. The result is **UNDERPOWERED**, not a
qualification and not a general refutation.

No Clay input, PHDM state, governance gate, Hydra path, Polly pad, or canonical
21-dimensional representation is changed by this experiment. The topology,
exporter, and benchmark remain a versioned shadow lane for reproducibility.

Reproduce with:

```powershell
python -m src.training.kaprekar_mirror_benchmark `
  --seeds 7,2024,6174 `
  --width 4 `
  --output kaprekar_mirror_benchmark_report.json
```

The command intentionally returns a nonzero status when the promotion gate
does not qualify.
