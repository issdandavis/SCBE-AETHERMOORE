# Adaptive Training Systems

> Research on making AI training intelligent, self-adjusting, and continuous.
> Compiled 2026-03-18.

---

## Executive Summary

The state of the art in adaptive training (as of early 2026) centers on five key paradigms: **curriculum learning** (progressive difficulty), **self-play** (model trains against itself), **online/continual learning** (continuous updates), **active learning** (model requests its own data), and **GRPO** (efficient RL without value networks). The most exciting recent developments are **Absolute Zero Reasoner** (self-play with zero human data, NeurIPS 2025 spotlight), **AdaRFT** (adaptive curriculum RL finetuning), and **Curriculum-RLAIF** (combining curriculum learning with AI feedback).

---

## 1. Curriculum Learning

### What It Is

Training on progressively harder examples. Start easy, increase difficulty as the model improves. Introduced by Yoshua Bengio et al. (2009), inspired by how humans learn -- simple concepts first, then complexity.

### How It Works

1. Sort or bucket training data by difficulty.
2. Train initially on easy examples only.
3. Gradually introduce harder examples as training progresses.
4. The model learns general principles from easy examples that transfer to hard ones.

### Key Results

- Produces better generalization than random-order training.
- Effect is most pronounced on test set performance (not just training loss).
- Works best when easy examples teach transferable features.

### Recent Papers (2025)

**AdaRFT: Efficient Reinforcement Finetuning via Adaptive Curriculum Learning**
- Paper: https://arxiv.org/abs/2504.05520
- Dynamically adjusts difficulty based on the model's recent reward signals.
- Maintains a target difficulty level that increases/decreases based on reward feedback.
- At each step, trains on examples closest to target difficulty.
- Avoids wasting compute on too-easy or too-hard problems.

**Self-Evolving Curriculum (SEC) for LLM RL**
- Paper: https://arxiv.org/pdf/2505.14970
- Formulates curriculum selection as a non-stationary Multi-Armed Bandit (MAB) problem.
- Adaptively learns a curriculum policy concurrently with RL fine-tuning.
- No human intervention needed to design the curriculum.

**Curriculum-RLAIF: Curriculum Alignment with RL from AI Feedback**
- Paper: https://arxiv.org/abs/2505.20075
- Constructs preference pairs with varying difficulty levels.
- Progressively incorporates harder preference pairs for reward model training.
- Easy pairs from guided prompts, hard pairs from random sampling, medium "bridge" pairs sorted easy-to-hard.

**Self-Adaptive Curriculum Learning for NLU**
- Paper: https://arxiv.org/abs/2507.09758
- The pretrained model itself predicts example difficulty.
- No external difficulty metric needed -- the model is its own difficulty estimator.

**Actor-Curator: Co-adaptive Curriculum Learning**
- Paper: https://arxiv.org/html/2602.20532v1
- Policy-improvement bandits for scalable RL post-training.
- The "Curator" agent learns which training examples to present.

### Implementation Recommendation

Use **AdaRFT-style adaptive sampling** for the SCBE tower training system:
```python
class AdaptiveCurriculum:
    def __init__(self, difficulty_bins, target_reward=0.5):
        self.target_difficulty = 0.0  # Start easy
        self.target_reward = target_reward
        self.momentum = 0.1

    def update(self, recent_rewards):
        avg_reward = mean(recent_rewards)
        if avg_reward > self.target_reward:
            self.target_difficulty += self.momentum  # Make harder
        else:
            self.target_difficulty -= self.momentum * 0.5  # Ease off
        self.target_difficulty = clamp(self.target_difficulty, 0, 1)

    def sample_batch(self, dataset):
        # Select examples closest to current target difficulty
        return dataset.nearest_difficulty(self.target_difficulty)
```

**References**:
- [Curriculum Learning (Wikipedia)](https://en.wikipedia.org/wiki/Curriculum_learning)
- [Bengio et al. 2009 Original Paper](https://arxiv.org/abs/0904.0654)
- [AdaRFT Paper](https://arxiv.org/abs/2504.05520)
- [AdaCuRL Framework](https://arxiv.org/html/2511.09478)

---

## 2. Self-Play

### What It Is

A model trains against itself (or copies of itself) to improve. Classic example: AlphaGo/AlphaZero. In 2025, this paradigm expanded dramatically beyond games into language model training.

### Key 2025 Breakthroughs

**Absolute Zero Reasoner (AZR)** -- NeurIPS 2025 Spotlight
- Paper: https://arxiv.org/abs/2505.03335
- Code: https://github.com/LeapLabTHU/Absolute-Zero-Reasoner
- A single model learns to both **propose** training tasks and **solve** them.
- ZERO human-curated training data required.
- The model acts as Proposer (generates problems with high learning potential) and Solver (attempts solutions, verified by code execution).
- Outperforms models trained on tens of thousands of human-labeled examples.
- AZR-Base-7B improves math accuracy by 10.9 points; AZR-Coder-7B by 15.2 points.
- Demonstrates emergent reasoning without any in-domain training data.

**WebRL: Self-Evolving Online Curriculum RL for Web Agents**
- Paper: https://proceedings.iclr.cc/paper_files/paper/2025/file/c66e1fcc9691aae706250638f36f681b-Paper-Conference.pdf
- Automatically generates web navigation tasks matching agent's current skill level.
- Self-evolving curriculum adjusts difficulty based on agent performance.
- If model does well, harder tasks appear. If struggling, easier tasks.

**Multi-Turn Multi-Agent Self-Play for Social Intelligence**
- Paper: https://arxiv.org/html/2602.03109v1
- One model plays all roles in social scenarios (Werewolf, SOTOPIA).
- Develops emergent empathy, persuasion, and compromise-seeking.
- Shows self-play works for "soft" skills, not just adversarial games.

### Self-Play Autocurricula

The concept of "autocurricula" -- where the training curriculum emerges from self-play dynamics rather than being designed -- is gaining significant traction. Frontier labs are using curriculum design when performing RL over foundation models, with the rationale nicely explained in Kimi-k1.5's technical report (June 2025).

### Implementation Recommendation

For SCBE, implement AZR-style self-play for tower floor challenges:
```python
class SelfPlayTowerFloor:
    def __init__(self, model, code_executor):
        self.model = model
        self.executor = code_executor

    def training_step(self):
        # Model proposes a challenge (Proposer role)
        challenge = self.model.generate_challenge(
            difficulty_target=self.current_difficulty
        )

        # Model attempts to solve it (Solver role)
        solution = self.model.solve(challenge)

        # Verify via code execution (binary reward)
        reward = self.executor.verify(challenge, solution)

        # Update model with GRPO
        self.model.update(challenge, solution, reward)

        # Adjust difficulty based on solve rate
        self.update_difficulty(reward)
```

**References**:
- [Absolute Zero Reasoner Project Page](https://andrewzh112.github.io/absolute-zero-reasoner/)
- [AZR on Hugging Face Papers](https://huggingface.co/papers/2505.03335)
- [Self-Play Training in RL (Emergent Mind)](https://www.emergentmind.com/topics/self-play-training)
- [Self-Play Course (Hugging Face Deep RL)](https://huggingface.co/learn/deep-rl-course/en/unit7/self-play)
- [Self-Play and Autocurricula (Amplify Partners)](https://www.amplifypartners.com/blog-posts/self-play-and-autocurricula-in-the-age-of-agents)

---

## 3. Online / Continual Learning

### What It Is

The model updates continuously on new data, rather than being trained once on a fixed dataset. The holy grail of adaptive training -- but also the hardest to get right due to catastrophic forgetting.

### Current State (2025-2026)

Continual learning for LLMs remains an active research area without a fully solved solution. The core challenge is **catastrophic forgetting** -- when learning new knowledge causes the model to forget old knowledge.

### Three Approaches

1. **Continual Pre-training**: Resume pre-training on new data. Risk: forgetting.
2. **Continual Fine-tuning**: Apply new task-specific fine-tuning. More targeted.
3. **External Knowledge Integration**: Use RAG or tool-based methods to add knowledge without modifying weights.

### Key Survey

**Continual Learning of Large Language Models: A Comprehensive Survey**
- Paper: https://arxiv.org/abs/2402.01364
- GitHub: https://github.com/Wang-ML-Lab/llm-continual-learning-survey
- Published in ACM Computing Surveys (CSUR) 2025.

### Practical Strategies for Long-Running Training

For maintaining continuous training processes that run for hours:

1. **Elastic Weight Consolidation (EWC)**: Identify important weights for previous tasks and penalize changes to them.
2. **Progressive Neural Networks**: Freeze old columns, add new ones for new tasks.
3. **LoRA-based Continual Learning**: Train separate LoRA adapters for each task, merge or switch as needed.
4. **Replay Buffers**: Keep a small buffer of old examples and mix them into new training batches.
5. **Knowledge Distillation**: Use the old model as a teacher to prevent the new model from diverging.

### Implementation Recommendation

For SCBE's tower system, use **replay buffers + LoRA adapters**:
```python
class ContinualTowerTrainer:
    def __init__(self, base_model):
        self.base_model = base_model
        self.floor_adapters = {}  # LoRA adapter per floor
        self.replay_buffer = ReplayBuffer(max_size=10000)

    def train_floor(self, floor_num, data):
        # Create new LoRA adapter for this floor
        adapter = LoRAAdapter(rank=16)
        self.floor_adapters[floor_num] = adapter

        for batch in data:
            # Mix in replay examples from previous floors
            replay = self.replay_buffer.sample(batch_size // 4)
            mixed_batch = concatenate(batch, replay)

            # Train with adapter
            loss = self.base_model.train_with_adapter(adapter, mixed_batch)

            # Add hard examples to replay buffer
            self.replay_buffer.add(batch.hard_examples())
```

**References**:
- [Continual Learning with RL for LLMs (Cameron Wolfe)](https://cameronrwolfe.substack.com/p/rl-continual-learning)
- [Continual Learning in Token Space (Letta)](https://www.letta.com/blog/continual-learning)
- [Self-Evolving LLMs via Continual Instruction Tuning](https://arxiv.org/html/2509.18133v3)
- [State of LLMs 2025 (Sebastian Raschka)](https://magazine.sebastianraschka.com/p/state-of-llms-2025)

---

## 4. Active Learning

### What It Is

The model identifies which training examples would be most valuable and requests them. Instead of random sampling from a dataset, the model says "I need more examples like THIS."

### Core Strategies

1. **Uncertainty Sampling**: Query examples where the model is most uncertain (highest entropy in predictions).
2. **Query-by-Committee**: Multiple models vote; query examples where they disagree most.
3. **Diversity Sampling**: Select examples that are most different from what's already been trained on.
4. **Expected Model Change**: Query examples that would cause the largest gradient update.
5. **Hybrid (Uncertainty + Diversity)**: Combines both -- clearly outperforms geometry-only or uncertainty-only approaches.

### Key 2025 Research

**Enhanced Uncertainty Sampling with Category Information**
- Paper: https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0327694
- Traditional uncertainty sampling neglects category information, leading to imbalanced selection.
- New approach integrates category info with uncertainty for balanced active learning.

**Calibrated Uncertainty Sampling**
- Paper: https://arxiv.org/html/2510.03162v1
- Uncalibrated uncertainty models may significantly affect acquisition function effectiveness.
- Proper calibration of uncertainty estimates is critical for active learning to work.

### Implementation Recommendation

For the tower training system, use active learning to let the model choose which floor to revisit:
```python
class ActiveTowerLearner:
    def __init__(self, model, floor_datasets):
        self.model = model
        self.floor_datasets = floor_datasets

    def select_next_training_batch(self):
        uncertainties = {}
        for floor_num, dataset in self.floor_datasets.items():
            # Compute model uncertainty on each floor's data
            sample = dataset.random_sample(100)
            entropy = self.model.compute_entropy(sample)
            uncertainties[floor_num] = entropy.mean()

        # Train on floor where model is most uncertain
        hardest_floor = max(uncertainties, key=uncertainties.get)
        return self.floor_datasets[hardest_floor].sample_batch()
```

**References**:
- [Active Learning Guide (Encord)](https://encord.com/blog/active-learning-machine-learning-guide/)
- [Uncertainty Sampling Explained (Keymakr)](https://keymakr.com/blog/uncertainty-sampling-explained/)
- [Active Learning (Lil'Log)](https://lilianweng.github.io/posts/2022-02-20-active-learning/)

---

## 5. GRPO (Group Relative Policy Optimization)

### What It Is

GRPO is the RL algorithm behind DeepSeek-R1's reasoning breakthrough. It eliminates the value network from PPO, reducing memory by 40-60% and cost by up to 18x, while achieving equal or better performance.

### How It Works

1. For a given prompt, sample **G** different completions from the current policy.
2. Score each completion with a reward function (can be rule-based or learned).
3. Compute **group-relative advantages** by normalizing rewards within the group (mean=0, std=1).
4. Update the policy using a clipped objective (like PPO) but without any value network.

### Key Innovation

Instead of training a separate value network to estimate baselines (which doubles memory), GRPO uses the group of samples itself as the baseline. If a completion scored above the group average, reinforce it. Below average, suppress it.

### Mathematical Core

```
Advantage_i = (reward_i - mean(rewards)) / std(rewards)

Loss = -E[ min(
    ratio * advantage,
    clip(ratio, 1-eps, 1+eps) * advantage
)] + beta * KL(policy || reference)
```

Where `ratio = policy(output) / reference_policy(output)`.

### Results

- **DeepSeek-R1-Zero**: Pure RL with GRPO, no SFT. Emergent behaviors: self-evaluation, "aha moments" where model recognizes and corrects errors.
- **Memory reduction**: 40-60% less than PPO (no value network).
- **Cost reduction**: Up to 18x cheaper than PPO. A $10,000 PPO run could cost ~$556 with GRPO.

### Available Implementations

- **Hugging Face TRL**: `trl` library has GRPO trainer built in.
- **OpenRLHF**: Open-source RLHF/GRPO framework.
- **DeepSpeed-Chat**: Microsoft's distributed RL training framework supports GRPO-style training.

### Implementation Recommendation

GRPO is the recommended RL algorithm for the SCBE tower training system:
```python
from trl import GRPOTrainer, GRPOConfig

config = GRPOConfig(
    num_generations=8,       # G=8 completions per prompt
    max_new_tokens=512,
    temperature=0.7,
    kl_coef=0.05,           # KL penalty
    cliprange=0.2,
    learning_rate=1e-6,
)

trainer = GRPOTrainer(
    model=model,
    ref_model=ref_model,
    reward_function=tower_floor_reward,  # Floor-specific reward
    config=config,
    train_dataset=floor_dataset,
)

trainer.train()
```

**References**:
- [GRPO Illustrated Breakdown (Ebrahim Pichka)](https://epichka.com/blog/2025/grpo/)
- [GRPO Deep Dive (Cameron Wolfe Substack)](https://cameronrwolfe.substack.com/p/grpo)
- [Why GRPO is Important (Oxen.ai)](https://ghost.oxen.ai/why-grpo-is-important-and-how-it-works/)
- [DeepSeekMath Paper (arXiv)](https://arxiv.org/abs/2402.03300)
- [DeepSeek-R1 Paper (arXiv)](https://arxiv.org/pdf/2501.12948)
- [Math Behind GRPO (Medium)](https://medium.com/@sahin.samia/the-math-behind-deepseek-a-deep-dive-into-group-relative-policy-optimization-grpo-8a75007491ba)
- [Training-Free GRPO (OpenReview)](https://openreview.net/forum?id=tyUnYbE7Gi)

---

## 6. Constitutional AI Training Loops

### What It Is

Anthropic's approach to alignment: train the model using AI-generated feedback based on a constitution (set of principles), rather than relying solely on human labelers.

### Two-Phase Process

**Phase 1 -- Supervised Learning (Critique + Revision)**:
1. Model generates responses to harmful prompts.
2. Model critiques its own responses using constitutional principles.
3. Model revises responses based on its critiques.
4. Fine-tune on the revised responses.

**Phase 2 -- RL from AI Feedback (RLAIF)**:
1. Model generates pairs of responses.
2. Another model evaluates which response better follows the constitution.
3. Train a preference/reward model from these AI-generated preferences.
4. Use RL (PPO or GRPO) to optimize against the preference model.

### Key Insight

RLAIF is more scalable than RLHF because you don't need human labelers. The constitution acts as the human oversight -- a compact set of rules that scales to infinite evaluations.

### 2025 Warning: Model Collapse Risk

Research from 2025 shows that RL-AIF training, which relies on fine-tuning models using their own self-critic outputs, may lead to **model collapse** -- where models degenerate when training on recursively generated data. Mitigation: mix in real human data periodically, or use separate models for critique vs. training.

### Implementation for SCBE

The SCBE governance engine already implements risk tiers (ALLOW/QUARANTINE/ESCALATE/DENY). These map directly to a constitutional framework:
```python
SCBE_CONSTITUTION = [
    "Operations within safe Poincare ball radius receive ALLOW.",
    "Drift beyond safe radius triggers QUARANTINE for review.",
    "Anomalous patterns exceeding escalation threshold trigger ESCALATE.",
    "Adversarial intent confirmed by harmonic wall triggers DENY.",
    "All governance decisions must be auditable and reversible.",
    "Sacred Tongue encoding must preserve semantic integrity.",
]

def constitutional_reward(response, constitution=SCBE_CONSTITUTION):
    """Score a response against SCBE constitutional principles."""
    violations = 0
    for principle in constitution:
        if violates(response, principle):
            violations += 1
    return 1.0 - (violations / len(constitution))
```

**References**:
- [Constitutional AI Paper (Anthropic)](https://www.anthropic.com/research/constitutional-ai-harmlessness-from-ai-feedback)
- [Constitutional AI (arXiv)](https://arxiv.org/abs/2212.08073)
- [CAI & AI Feedback (RLHF Book)](https://rlhfbook.com/c/13-cai)
- [Constitution or Collapse? (arXiv 2025)](https://arxiv.org/html/2504.04918v1)

---

## 7. Checkpointing and Resume Strategies

### Essential Components to Save

Every checkpoint must include:

1. **Model state dict** -- All learnable parameters.
2. **Optimizer state dict** -- Moving averages of gradients, squared gradients, learning rate schedules. Resetting these disrupts convergence.
3. **RNG states** -- For reproducibility (torch, numpy, python random, CUDA).
4. **Training step / epoch counter** -- To resume curriculum position.
5. **Loss history / metrics** -- For monitoring and adaptive difficulty adjustment.
6. **Curriculum state** -- Current difficulty level, floor number, active learning priorities.

### Checkpointing Strategies

| Strategy | Description | When to Use |
|----------|-------------|-------------|
| **Epoch-based** | Save after each epoch | Standard, simple |
| **Step-based** | Save every N steps | Long epochs, want finer granularity |
| **Loss-based** | Save when validation loss improves | Best model selection |
| **Time-based** | Save every N minutes | Unreliable environments (Colab, Kaggle) |
| **Sharded** | Each GPU saves its own shard | Multi-GPU training |
| **Incremental** | Save only diffs from previous checkpoint | Storage-constrained environments |
| **Asynchronous** | Background thread handles I/O | Minimize training interruption |

### For Free Compute (Colab/Kaggle) -- Critical Strategy

Free compute environments disconnect randomly. Use aggressive time-based checkpointing:

```python
import time
from google.colab import drive

class FreeComputeCheckpointer:
    def __init__(self, save_dir, interval_minutes=15):
        self.save_dir = save_dir
        self.interval = interval_minutes * 60
        self.last_save = time.time()

    def maybe_save(self, model, optimizer, step, curriculum_state):
        if time.time() - self.last_save > self.interval:
            checkpoint = {
                'model': model.state_dict(),
                'optimizer': optimizer.state_dict(),
                'step': step,
                'curriculum': curriculum_state,
                'rng': {
                    'torch': torch.random.get_rng_state(),
                    'numpy': np.random.get_state(),
                    'python': random.getstate(),
                },
                'timestamp': time.time(),
            }
            # Save to Google Drive (survives Colab disconnect)
            path = f"{self.save_dir}/checkpoint_step_{step}.pt"
            torch.save(checkpoint, path)
            self.last_save = time.time()
            print(f"Checkpoint saved: {path}")
```

### Resume Strategy for Tower Training

```python
def resume_tower_training(checkpoint_path, tower):
    ckpt = torch.load(checkpoint_path)

    model.load_state_dict(ckpt['model'])
    optimizer.load_state_dict(ckpt['optimizer'])

    # Restore curriculum position
    current_floor = ckpt['curriculum']['floor']
    difficulty = ckpt['curriculum']['difficulty']
    step = ckpt['step']

    # Restore RNG for reproducibility
    torch.random.set_rng_state(ckpt['rng']['torch'])
    np.random.set_state(ckpt['rng']['numpy'])
    random.setstate(ckpt['rng']['python'])

    # Resume from exact position
    tower.set_floor(current_floor)
    tower.set_difficulty(difficulty)
    return model, optimizer, step
```

### Multi-Location Backup

For reliability, save to multiple locations:
1. **Local disk** (fast, ephemeral on Colab).
2. **Google Drive** (survives Colab disconnect).
3. **Hugging Face Hub** (long-term storage, version controlled).
4. **Oracle Cloud VM** (always-on, SSH accessible).

**References**:
- [Checkpointing and Resuming Training (APXML)](https://apxml.com/courses/fine-tuning-adapting-large-language-models/chapter-3-full-parameter-fine-tuning/checkpointing-resuming-training)
- [Checkpointing Strategies for LLMs (Medium)](https://medium.com/@dpratishraj7991/checkpointing-strategies-for-large-language-models-llms-full-sharded-efficient-restarts-at-0fa026d8a566)
- [Understanding LLM Checkpoint I/O Patterns (arXiv)](https://arxiv.org/html/2512.24511v1)
- [LLM Checkpointing (Aussie AI)](https://www.aussieai.com/research/checkpointing)
- [Best Practices for Model Training (UAlbany)](https://albany.atlassian.net/wiki/spaces/askit/pages/577732657/Checkpointing+Guide+Best+Practices+for+Model+Training)

---

## 8. Self-Adjusting Difficulty -- The Complete Pattern

### Putting It All Together

Combining all paradigms into a single adaptive training loop:

```python
class AdaptiveTowerTraining:
    """
    Combines: curriculum learning + self-play + active learning + GRPO + checkpointing.
    Maps to SCBE 14-layer pipeline as 14 tower floors.
    """

    def __init__(self, model, ref_model, floors, reward_fn):
        self.model = model
        self.ref_model = ref_model
        self.floors = floors
        self.reward_fn = reward_fn

        # Curriculum state
        self.current_floor = 0
        self.difficulty = 0.0

        # Active learning
        self.uncertainty_tracker = UncertaintyTracker()

        # GRPO config
        self.grpo = GRPOTrainer(
            model=model,
            ref_model=ref_model,
            num_generations=8,
        )

        # Checkpointing
        self.checkpointer = FreeComputeCheckpointer(
            save_dir="/content/drive/MyDrive/scbe_tower",
            interval_minutes=15,
        )

        # Sacred Egg registry
        self.eggs = []

    def train(self, max_steps=100000):
        step = 0
        while step < max_steps and self.current_floor < len(self.floors):
            floor = self.floors[self.current_floor]

            # 1. ADAPTIVE CURRICULUM: Select difficulty-appropriate batch
            batch = floor.sample_at_difficulty(self.difficulty)

            # 2. SELF-PLAY: If floor supports it, model generates its own challenges
            if floor.supports_self_play:
                self_challenges = self.model.propose_challenges(
                    difficulty=self.difficulty
                )
                batch = mix(batch, self_challenges, ratio=0.3)

            # 3. GRPO TRAINING STEP
            rewards = self.grpo.step(batch)

            # 4. ADJUST DIFFICULTY based on performance
            avg_reward = rewards.mean()
            if avg_reward > 0.7:
                self.difficulty = min(self.difficulty + 0.05, 1.0)
            elif avg_reward < 0.3:
                self.difficulty = max(self.difficulty - 0.025, 0.0)

            # 5. ACTIVE LEARNING: Track uncertainty per floor
            self.uncertainty_tracker.update(self.current_floor, rewards)

            # 6. BOSS CHECK: Evaluate if ready to advance
            if step % 1000 == 0:
                boss_score = floor.boss_evaluation(self.model)
                if boss_score >= floor.pass_threshold:
                    # Hatch Sacred Egg
                    egg = self.hatch_egg(floor)
                    self.eggs.append(egg)
                    self.current_floor += 1
                    self.difficulty = 0.0  # Reset for new floor

                    # Maybe revisit a previous floor (active learning)
                    weakest = self.uncertainty_tracker.weakest_floor()
                    if weakest is not None and weakest != self.current_floor:
                        self.revisit_floor(weakest, steps=500)

            # 7. CHECKPOINT
            self.checkpointer.maybe_save(
                self.model, self.grpo.optimizer, step,
                {'floor': self.current_floor, 'difficulty': self.difficulty}
            )

            step += 1

    def hatch_egg(self, floor):
        return {
            'floor': floor.number,
            'checkpoint': self.model.state_dict(),
            'difficulty_reached': self.difficulty,
            'personality': floor.personality_traits,
            'timestamp': time.time(),
        }

    def revisit_floor(self, floor_num, steps):
        """Active learning: revisit floor where model is weakest."""
        floor = self.floors[floor_num]
        for _ in range(steps):
            batch = floor.sample_uncertain(self.model)
            self.grpo.step(batch)
```

---

## Tool Recommendations

| Need | Tool | URL |
|------|------|-----|
| GRPO training | Hugging Face TRL | https://github.com/huggingface/trl |
| Distributed RL | OpenRLHF | https://github.com/OpenRLHF/OpenRLHF |
| Self-play framework | AZR codebase | https://github.com/LeapLabTHU/Absolute-Zero-Reasoner |
| Curriculum learning | Custom (see AdaRFT) | https://arxiv.org/abs/2504.05520 |
| Checkpointing | PyTorch + HF Hub | Built into PyTorch/transformers |
| Active learning | modAL | https://github.com/modAL-project/modAL |
| Continual learning | Avalanche | https://avalanche.continualai.org/ |
| Free GPU | Kaggle + Colab | See `2026-03-18-free-compute-landscape.md` |

---

## Key Papers (Chronological)

| Year | Paper | Contribution |
|------|-------|-------------|
| 2009 | Bengio et al. "Curriculum Learning" | Founded the field |
| 2017 | Silver et al. "AlphaZero" | Self-play for superhuman game AI |
| 2022 | Bai et al. "Constitutional AI" (Anthropic) | RLAIF, AI-as-judge alignment |
| 2024 | Shao et al. "DeepSeekMath" | Introduced GRPO |
| 2025 Jan | DeepSeek-R1 | Pure RL reasoning with GRPO, emergent self-correction |
| 2025 Apr | AdaRFT | Adaptive curriculum for RL finetuning |
| 2025 May | Absolute Zero Reasoner | Self-play with zero data, NeurIPS spotlight |
| 2025 May | Curriculum-RLAIF | Curriculum + AI feedback for alignment |
| 2025 May | WebRL | Self-evolving curriculum for web agents |
| 2025 Jun | Kimi-k1.5 | Autocurricula for frontier model RL |
| 2026 Feb | Actor-Curator | Co-adaptive curriculum via bandits |
