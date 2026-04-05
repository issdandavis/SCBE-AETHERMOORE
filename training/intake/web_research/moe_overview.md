# Mixture of Experts (MoE)

Mixture of Experts is a transformer architecture enabling models to be pretrained with significantly less compute by using conditional computation — selectively activating different expert networks based on input rather than processing all inputs through every parameter.

## Architecture

A MoE consists of two main components: Sparse MoE layers replace dense feed-forward network layers with multiple experts (typically 8, ranging from 2 to 2048), where each expert is a neural network (usually an FFN). A gate network (router) with learned parameters routes tokens to appropriate experts, determining which tokens go to which experts.

The output: y = Σ(i=1 to n) G(x)_i * E_i(x), where G(x) is the gating function and E_i(x) is expert i output. If G(x)_i = 0, expert i computation is skipped entirely.

## Gating Functions

Simple softmax gating: G_σ(x) = Softmax(x · W_g). Noisy top-k gating adds noise for load balancing: H(x)_i = (x · W_g)_i + StandardNormal() · Softplus((x · W_noise)_i), then keep top-k and apply softmax.

## Load Balancing

An auxiliary loss encourages uniform expert utilization, penalizing imbalanced routing. Expert capacity = (tokens_per_batch / number_of_experts) × capacity_factor. Switch Transformers found optimal capacity factor of 1.0-1.25.

## Switch Transformers

Routes each token to exactly ONE expert (vs. top-2). Key innovations: reduced router computation, better batch sizes per expert, lower communication costs. Achieved 4x speedup over T5-XXL. Used selective precision: bfloat16 for experts, full precision for router.

## Expert Specialization

Encoder experts specialize in token groups (punctuation, proper nouns). Decoder experts show less specialization with more distributed knowledge. In multilingual models, NO language-specific experts emerge due to load balancing.

## Fine-tuning Challenges

MoEs are more prone to overfitting on small tasks. They perform worse on reasoning tasks (SuperGLUE) but excel on knowledge tasks (TriviaQA). Solutions: higher learning rates, smaller batch sizes, higher dropout in experts, freeze non-MoE parameters. MoEs benefit disproportionately from instruction tuning compared to dense models.

## Serving

Mixtral 8x7B requires 47B parameter VRAM (shared non-expert layers) despite having 56B raw parameters, with compute equivalent to ~12B dense model (top-2 routing). Optimization techniques: distillation to dense models, expert aggregation, quantization (QMoE achieves <1 bit per parameter).

## Key Metrics

4x speedup in pretraining over dense baselines. More experts = improved sample efficiency with diminishing gains after 256-512 experts. Faster inference per parameter but higher memory footprint.
