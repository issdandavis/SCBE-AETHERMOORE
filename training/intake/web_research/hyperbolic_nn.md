# Hyperbolic Neural Networks

Authors: Octavian-Eugen Ganea, Gary Bécigneul, Thomas Hofmann (2018). Introduces neural network architectures that operate natively in hyperbolic space using the Poincaré ball model, enabling better representation of hierarchical and tree-like data structures.

## Motivation

Euclidean space is inefficient at representing hierarchical structures — a tree with branching factor b and depth d has O(b^d) nodes, requiring exponential dimensions in Euclidean space. Hyperbolic space naturally accommodates tree-like structures because its volume grows exponentially with radius, matching the exponential growth of hierarchical data. This means hyperbolic embeddings can represent complex hierarchies in much lower dimensions than Euclidean equivalents.

## Mathematical Foundation

The paper combines Möbius gyrovector spaces formalism (providing algebraic structure for hyperbolic computations) with Riemannian geometry of the Poincaré ball model. The Poincaré ball B^n = {x ∈ R^n : ||x|| < 1} with metric tensor g_x = (2/(1-||x||²))² g_E, where g_E is the Euclidean metric.

Key operations adapted to hyperbolic space: Möbius addition (replaces vector addition), Möbius scalar multiplication (replaces scalar multiplication), exponential and logarithmic maps (move between tangent space and manifold), parallel transport (moves vectors between tangent spaces).

## Hyperbolic Neural Network Layers

### Hyperbolic Linear Layer
Standard linear transformation W·x + b is replaced with Möbius matrix-vector multiplication and Möbius addition: y = W ⊗_M x ⊕_M b, where ⊗_M is Möbius matrix multiplication and ⊕_M is Möbius addition. The weight matrix W operates in the tangent space at the origin, then results are mapped back to the Poincaré ball.

### Hyperbolic Activation Functions
Standard activations like ReLU are adapted through: map point to tangent space (logarithmic map), apply Euclidean activation, map result back to manifold (exponential map).

### Multinomial Logistic Regression
Derived for hyperbolic space, where decision boundaries become geodesic hyperplanes (hyperbolic hyperplanes) instead of Euclidean hyperplanes. The classification probability depends on the hyperbolic distance from the point to each class's geodesic boundary.

### Hyperbolic GRU (Gated Recurrent Unit)
Adapts the GRU recurrent architecture to operate entirely in hyperbolic space, enabling sequential data processing while preserving hierarchical structure in the hidden states.

## Results

Evaluated on textual entailment and noisy-prefix recognition tasks. Hyperbolic sentence embeddings match or exceed Euclidean counterparts despite using fewer dimensions. Particularly effective for data with inherent hierarchical structure (taxonomy classification, entailment).

## Significance for SCBE

This work provides the mathematical foundation for operating neural networks in the Poincaré ball model — the same geometric space used by SCBE's harmonic scaling law. The hyperbolic distance formula d(u,v) = arcosh(1 + 2||u-v||²/((1-||u||²)(1-||v||²))) is the same formula used in SCBE Layer 5. Hyperbolic neural networks demonstrate that the exponential cost scaling of adversarial behavior (fundamental to SCBE's security model) is naturally supported by neural network architectures operating in this space.
