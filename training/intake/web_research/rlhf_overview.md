# Reinforcement Learning from Human Feedback (RLHF)

RLHF is a technique to align language models with human values by optimizing them using human preferences as a reward signal. Rather than using traditional loss functions, RLHF leverages human feedback to directly optimize model behavior for subjective qualities like helpfulness, harmlessness, and honesty. Famously used in training ChatGPT and has become a key technique for state-of-the-art language models.

## Three-Stage Training Process

### Stage 1: Pretraining

The pipeline begins with a pretrained language model trained on large-scale text data using standard next-token prediction. Models range from 10M to 280B+ parameters. Optional fine-tuning on human-generated preferred text can improve initial quality.

### Stage 2: Reward Model Training

The reward model learns to predict human preferences and assign scalar rewards to generated text. Process: sample prompts from a dataset, generate multiple outputs per prompt, have human annotators rank outputs via pairwise comparisons. Use Elo rating system for head-to-head matchups. The reward model can be a fine-tuned LM or trained from scratch. Input: sequence of text. Output: scalar reward value. Typical scale: ~50k labeled preference samples.

### Stage 3: Fine-tuning with PPO

The language model is fine-tuned using Proximal Policy Optimization to maximize reward model scores. The RL formulation: Policy = language model (prompt → text), Action space = vocabulary tokens (~50k), Reward = preference model score - KL divergence penalty.

The reward function: r = r_θ - λ * r_KL, where r_θ is the preference model score and r_KL is the KL divergence penalty between RL policy and initial model. The KL penalty prevents reward hacking (generating gibberish that fools the reward model) and ensures coherent output.

## Key Challenges

Data collection is expensive (human annotators). Annotators disagree, adding variance. Models can still output harmful or inaccurate text. PPO is relatively old; alternatives like DPO, ILQL show promise. Optimal reward model size relative to LM is an open question. High VRAM requirements for full fine-tuning — LoRA helps significantly.

## Open Source Tools

TRL (Transformers Reinforcement Learning): General purpose RLHF integrated with Hugging Face. TRLX: Production-ready for models up to 33B parameters, supports PPO and ILQL. RL4LMs: Flexible building blocks supporting PPO, NLPO, A2C, TRPO.
