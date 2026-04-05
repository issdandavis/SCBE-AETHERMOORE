# Direct Preference Optimization (DPO)

Authors: Rafael Rafailov, Archit Sharma, Eric Mitchell, Stefano Ermon, Christopher D. Manning, Chelsea Finn (2023). DPO replaces the complex RLHF pipeline with a simple classification loss that directly optimizes language model policy from human preferences.

## Problem with RLHF

Traditional RLHF involves a multi-stage process: first training a separate reward model from human preferences, then using reinforcement learning (PPO) to optimize the language model against that reward model. RLHF is a complex and often unstable procedure requiring careful hyperparameter tuning, reward model training, and RL optimization.

## Core Innovation

DPO introduces a new parameterization of the reward model in RLHF that enables extraction of the corresponding optimal policy in closed form. Instead of training a separate reward model and then optimizing against it with RL, DPO defines a loss function that directly optimizes the language model using preference data.

## Loss Function

The DPO loss is a simple binary cross-entropy classification loss over preference pairs. Given a prompt x, a preferred response y_w (winner) and a dispreferred response y_l (loser): L_DPO(π_θ; π_ref) = -E[log σ(β log(π_θ(y_w|x)/π_ref(y_w|x)) - β log(π_θ(y_l|x)/π_ref(y_l|x)))], where π_θ is the policy being optimized, π_ref is the reference policy (initial SFT model), β is a temperature parameter controlling deviation from the reference policy, and σ is the sigmoid function.

## Key Properties

The implicit reward is r(x,y) = β log(π_θ(y|x)/π_ref(y|x)) + β log Z(x), where Z(x) is the partition function. This means DPO implicitly learns a reward model while directly optimizing the policy.

No sampling from the LM during fine-tuning is required — unlike PPO which needs to generate samples from the current policy. This makes DPO computationally lightweight and eliminates a major source of instability.

## Advantages Over RLHF

Stable and performant compared to PPO-based RLHF. Computationally lightweight — no reward model training, no RL optimization loop. Eliminates the need for sampling from the LM during fine-tuning. Minimal hyperparameter tuning required (mainly β). Simple implementation — can be written in a few dozen lines of code.

## Results

DPO matches or exceeds PPO-based RLHF performance on sentiment control, summarization, and dialogue tasks while being substantially simpler to implement and train. On the TL;DR summarization task, DPO achieves similar win rates to PPO against human references. On Anthropic-HH dialogue, DPO produces responses rated as more helpful and less harmful.

## Variants

IPO (Identity Preference Optimization): Addresses overfitting to preference data by using a squared loss instead of log-sigmoid. KTO (Kahneman-Tversky Optimization): Uses unpaired preference data (just good/bad labels, not paired comparisons). ORPO (Odds Ratio Preference Optimization): Combines SFT and preference optimization into a single training phase. SimPO: Simplifies DPO further by removing the need for a reference model.
