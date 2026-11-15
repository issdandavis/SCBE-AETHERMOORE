# FAISS e-means applicability to SCBE and Clay

Date: 2026-11-15  
Status: researched candidate; not inserted into an active evaluator or training run.

## Correction and measured claim

The linked FAISS module is **e-means**, not ordinary k-means. Meta FAIR describes
e-means as a mini-batch, exponential-moving-average specialization for the
k-means objective. Its paper/reproduction material reports reaching lower loss
than Lloyd k-means in roughly one-tenth the epochs, without adding a tuning
hyperparameter.

The speed claim must retain its comparison and hardware context. FAISS's current
H100 reproduction reports about `9.5x` to `36.1x` wall-clock speedups when
e-means is stopped at the first epoch budget matching Flash-KMeans 0.3.1 after
25 iterations. The exact value varies with dataset size, dimension, input type,
and centroid count. It is not a universal constant and it is not evidence of
better downstream model reasoning by itself.

Primary sources:

- <https://github.com/facebookresearch/faiss/tree/main/contrib/e_means>
- <https://github.com/facebookresearch/faiss/blob/main/benchs/e_means/README.md>
- <https://arxiv.org/abs/2611.09501>

## Where it could help

E-means is relevant where SCBE or Clay already clusters many fixed embeddings:

- offline token-family or six-lane centroid discovery;
- routing-table initialization and centroid refresh;
- large embedding-corpus distillation before a controlled model run;
- replacing expensive exploratory k-means++ passes in experiments where only
  the partition/objective matters.

It does not replace attention, tokenization, the prime sieve, source-disjoint
evaluation, or weight training. It changes how centroids are estimated.

## Existing SCBE boundary

SCBE already has a hash-sealed result claiming bit-identical trajectory-key
partitions after k-means++ refits under five random Poincare isometries. That
result makes e-means a test candidate, not an automatic replacement: an EMA
update order can change centroid trajectories even when final objective values
are similar.

The first useful bake-off is therefore:

1. Use the same frozen embedding rows, preprocessing, centroid count, and seed
   set as the current k-means++ result.
2. Compare e-means, FAISS k-means++, and a shuffled-input control.
3. Report wall time, epochs, train/test distortion, empty clusters, imbalance,
   assignment agreement, centroid drift, and peak memory.
4. Repeat every Poincare isometry and test whether the final trajectory-key
   partition remains bit-identical after centroid correspondence is solved.
5. Require at least three seeds and the existing two-pooled-SD rule for any
   downstream quality claim.

## Promotion boundary

Promote e-means only if it is materially faster while preserving or improving
the frozen objective **and** the downstream partition/route invariants. A speed
win with changed assignments is a different model condition, not a drop-in
optimization. The current Clay run and E92 prospective gate remain untouched.
