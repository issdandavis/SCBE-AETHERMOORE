# e-means boundary for Clay and the VQCC competition

Primary sources:

- [Meta FAISS `contrib/e_means`](https://github.com/facebookresearch/faiss/tree/main/contrib/e_means)
- [Bessa et al., *e-means: outperforming k-means (in one-tenth the epochs)*](https://arxiv.org/abs/2611.09501)

## What the linked implementation actually does

e-means is a mini-batch clustering algorithm, not an embedding model and not a
neural-weight optimizer.  For each cluster it maintains exponentially decayed
point counts and vector sums, then reads the centroid as their ratio.  It adds
automatic batch/step scaling laws, cosine step decay, dead-cluster revival,
and an exact closing mean.

The paper reports that it beats Lloyd k-means at 25 epochs after 1.4--2.6
epochs on its tested embedding datasets, with reported GPU wall-clock gains of
10--45x.  The FAISS README summarizes the ordinary use case as approximately
one-tenth the epochs and lower loss.  Those are authors' benchmark claims, not
yet measurements on Clay data.

## Good Clay uses

e-means is a strong candidate when Clay has a genuinely large vector bank:

- grouping byte-extension, token-family, or weight-drift vectors into sheets;
- assigning new token rows to an existing centroid catalog;
- compressing near-duplicate embedding regions before a controlled distillation;
- spherical clustering of normalized six-lane direction vectors;
- fast candidate partitioning before expensive source-disjoint evaluation.

It should preserve the canonical token deed outside the cluster label.  A
centroid ID is derived routing metadata, never a replacement for byte identity.

## Where it does not help yet

The current Clay action study has only 3,000 training vectors per arm.  FAISS
recommends GPUs when `n * k` exceeds roughly `10^10`; this experiment is many
orders of magnitude smaller.  Installing FAISS or replacing the fixed ridge
transport diagnostic with e-means would add machinery without addressing the
measured bottleneck: useful 37-value action geometry is being lost inside the
frozen byte-token recurrence.

For Google VQCC, e-means has no direct score value.  A submission improves only
when it reduces the task cost (qubits, Toffoli count, or permitted failure).
e-means could accelerate clustering/search over many candidate circuits, but a
cluster result is not a circuit optimization and must not be presented as one.

## Required A/B before adoption

On a large future token or weight catalog, compare e-means and Lloyd k-means
using identical vectors, initialization seeds, cluster counts, precision, and
compute limits.  Record:

1. wall time and passes;
2. final squared error or spherical objective;
3. empty/revived clusters and imbalance;
4. assignment stability across at least three seeds;
5. byte/token deed collision count;
6. downstream action accuracy and macro-F1;
7. memory and data-transfer cost.

Adopt it only if the speedup survives this local comparison without worsening
downstream behavior or identity receipts.
