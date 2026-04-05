# LoRA: Low-Rank Adaptation of Large Language Models

Authors: Edward J. Hu, Yelong Shen, Phillip Wallis, Zeyuan Allen-Zhu, Yuanzhi Li, Shean Wang, Lu Wang, Weizhu Chen (2021). Introduces a parameter-efficient fine-tuning method that dramatically reduces the trainable parameters needed to adapt large language models.

## Core Method

LoRA freezes the pre-trained model weights and injects trainable rank decomposition matrices into each layer of the Transformer architecture. For a pre-trained weight matrix W₀ ∈ R^(d×k), the update is constrained by representing it with a low-rank decomposition: W₀ + ΔW = W₀ + BA, where B ∈ R^(d×r) and A ∈ R^(r×k), with rank r << min(d, k).

During training, W₀ is frozen and does not receive gradient updates, while A and B are trainable parameters. For h = W₀x, the modified forward pass becomes h = W₀x + BAx. A is initialized with random Gaussian, B is initialized to zero, so ΔW = BA is zero at the beginning of training. The update is scaled by α/r, where α is a constant.

## Key Properties

No additional inference latency: At deployment, ΔW = BA can be merged into the original weights W₀ + BA, so there is no additional computational cost during inference, unlike adapter-based methods which add latency.

Rank as the key hyperparameter: The rank r controls the expressiveness of the adaptation. Surprisingly low ranks (r = 1, 2, 4, 8) work well in practice, suggesting that the weight updates during adaptation have very low intrinsic rank.

Task switching: Different LoRA modules can be swapped at deployment by subtracting one BA and adding another, enabling efficient task switching without full model copies.

## Parameter Efficiency

Compared to full fine-tuning of GPT-3 175B: 10,000x fewer trainable parameters. 3x reduction in GPU memory requirements. Higher training throughput. No additional inference latency (unlike adapters).

For GPT-3 175B with r = 4: trainable parameters drop from 175B to ~4.7M per task. Total checkpoint storage is ~35MB per task instead of ~350GB.

## Rank-Deficiency Investigation

The paper provides an empirical investigation into rank-deficiency in language model adaptation, showing that weight update matrices ΔW have very low intrinsic rank. This finding suggests that pre-trained models are significantly over-parameterized for specific downstream tasks, and the adaptation landscape is surprisingly low-dimensional.

## Results

Evaluated on RoBERTa, DeBERTa, GPT-2, and GPT-3 across GLUE benchmark tasks. Achieves on-par or better quality compared to full fine-tuning despite having far fewer trainable parameters. On GPT-3 175B, LoRA matches or exceeds fine-tuning performance on several benchmarks while being dramatically more efficient.

## Variants and Extensions

QLoRA: Combines LoRA with 4-bit quantization of the base model, enabling fine-tuning of 65B parameter models on a single 48GB GPU. The base model is quantized to 4-bit NormalFloat, while LoRA adapters remain in higher precision (bfloat16). Double quantization reduces memory further by quantizing the quantization constants.

AdaLoRA: Adaptive rank allocation that distributes the parameter budget across weight matrices based on importance scores, allowing critical layers to have higher rank while less important ones use lower rank.
