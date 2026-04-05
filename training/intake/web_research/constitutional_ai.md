# Constitutional AI: Harmlessness from AI Feedback

Authors: Yuntao Bai, Saurav Kadavath, Sandipan Kundu, Amanda Askell, et al. (Anthropic, 2022). Introduces a method for training AI systems to be helpful, harmless, and honest through self-improvement rather than human-labeled harmful outputs.

## Core Idea

Instead of relying on human annotators to label harmful outputs (which is expensive, psychologically harmful to annotators, and difficult to scale), Constitutional AI uses a set of written principles (the "constitution") to guide the model's self-improvement. The constitution is a list of rules or principles that define what constitutes helpful and harmless behavior.

## Two-Phase Training

### Phase 1: Supervised Learning (SL-CAI)

The model generates responses to potentially harmful prompts. It then critiques its own responses using the constitutional principles. Based on self-critique, it generates revised responses that better follow the principles. The original model is fine-tuned on these improved (critique, revision) pairs. This creates a model that has learned to self-correct without any human labeling of harmful content.

### Phase 2: Reinforcement Learning from AI Feedback (RLAIF)

The model generates pairs of responses to prompts. An AI evaluator (using the constitutional principles) judges which response is better. These AI-generated preferences are used to train a reward model. The SL-CAI model is then fine-tuned using RL (PPO) against this AI-trained reward model. This replaces human feedback (RLHF) with AI feedback (RLAIF).

## The Constitution

The constitution includes principles like: Choose the response that is most helpful while being harmless and honest. Choose the response that sounds most similar to what a peaceful, ethical person would say. Choose the response that is least likely to be used to cause harm. Choose the response that most supports human autonomy and freedom.

## Key Results

The method produces a harmless but non-evasive AI assistant that engages with harmful queries by explaining its objections rather than simply refusing. Chain-of-thought reasoning enhances both performance and decision-making transparency. The approach enables more precise behavioral control with significantly fewer human labels. RLAIF achieves comparable performance to RLHF while being more scalable.

## Significance for AI Safety

Reduces the cost and psychological burden of safety training by minimizing human exposure to harmful content. Makes safety training more scalable through automation. The constitutional approach allows precise specification of desired behavior through explicit principles. Demonstrates that AI systems can meaningfully contribute to their own alignment through guided self-improvement.
