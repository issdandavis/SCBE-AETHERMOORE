# TRL (Transformer Reinforcement Learning)

TRL is a library for training language models with reinforcement learning techniques including Supervised Fine-Tuning (SFT), Direct Preference Optimization (DPO), Reward Modeling, and PPO. It builds on top of Transformers and PEFT.

## TRL Training Overview

TRL provides specialized trainers for each stage of the RLHF pipeline:

```
1. SFT (Supervised Fine-Tuning)  → Teach the model a task format
2. Reward Modeling                → Train a reward signal from human preferences
3. DPO / PPO                     → Align the model using preference data or reward model
```

```python
from trl import (
    SFTTrainer, SFTConfig,
    DPOTrainer, DPOConfig,
    RewardTrainer, RewardConfig,
)
```

## SFT Configuration with DFT Loss

Supervised Fine-Tuning with data-formatting and loss configuration:

```python
from trl import SFTTrainer, SFTConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from datasets import load_dataset
from peft import LoraConfig

model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-0.5B")
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-0.5B")
tokenizer.pad_token = tokenizer.eos_token

# Conversational format: {"messages": [{"role": "user", "content": "..."}, ...]}
dataset = load_dataset("json", data_files="sft_data.jsonl", split="train")

peft_config = LoraConfig(
    r=16, lora_alpha=32, lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    task_type="CAUSAL_LM",
)

sft_config = SFTConfig(
    output_dir="./sft-output",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    bf16=True,
    logging_steps=10,
    save_strategy="steps",
    save_steps=500,
    max_seq_length=2048,
    packing=True,
    dataset_text_field=None,
    optim="paged_adamw_8bit",
    warmup_ratio=0.03,
    lr_scheduler_type="cosine",
)

trainer = SFTTrainer(
    model=model, args=sft_config,
    train_dataset=dataset, tokenizer=tokenizer,
    peft_config=peft_config,
)
trainer.train()
trainer.save_model("./sft-adapter")

# Plain text format: {"text": "### Instruction: ...\n### Response: ..."}
text_dataset = load_dataset("json", data_files="text_data.jsonl", split="train")
text_config = SFTConfig(
    output_dir="./sft-text-output",
    dataset_text_field="text",
    max_seq_length=1024,
    num_train_epochs=3,
    per_device_train_batch_size=4,
)
trainer = SFTTrainer(model=model, args=text_config, train_dataset=text_dataset, tokenizer=tokenizer)
trainer.train()
```

## DPO Trainer with Preference Data

Direct Preference Optimization trains from preference pairs without a separate reward model:

```python
from trl import DPOTrainer, DPOConfig
from transformers import AutoModelForCausalLM, AutoTokenizer
from datasets import load_dataset
from peft import LoraConfig
import torch

model = AutoModelForCausalLM.from_pretrained(
    "./sft-adapter-merged", torch_dtype=torch.bfloat16, device_map="auto",
)
tokenizer = AutoTokenizer.from_pretrained("./sft-adapter-merged")
tokenizer.pad_token = tokenizer.eos_token

# DPO dataset: {"prompt": "...", "chosen": "...", "rejected": "..."}
# Or conversational: {"chosen": [messages...], "rejected": [messages...]}
dataset = load_dataset("json", data_files="dpo_data.jsonl", split="train")

peft_config = LoraConfig(
    r=8, lora_alpha=16, lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    task_type="CAUSAL_LM",
)

dpo_config = DPOConfig(
    output_dir="./dpo-output",
    num_train_epochs=1,
    per_device_train_batch_size=2,
    gradient_accumulation_steps=8,
    learning_rate=5e-5,
    beta=0.1,
    max_length=1024,
    max_prompt_length=512,
    bf16=True,
    logging_steps=10,
    save_strategy="steps",
    save_steps=200,
    optim="paged_adamw_8bit",
    warmup_ratio=0.1,
    loss_type="sigmoid",
)

trainer = DPOTrainer(
    model=model, args=dpo_config,
    train_dataset=dataset, tokenizer=tokenizer,
    peft_config=peft_config,
)
trainer.train()
trainer.save_model("./dpo-adapter")
metrics = trainer.evaluate()
print(f"Eval loss: {metrics['eval_loss']:.4f}")
```

## Reward Model Training

Train a reward model from human preference data to score responses:

```python
from trl import RewardTrainer, RewardConfig
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from datasets import load_dataset
import torch

model = AutoModelForSequenceClassification.from_pretrained("Qwen/Qwen2.5-0.5B", num_labels=1)
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-0.5B")
tokenizer.pad_token = tokenizer.eos_token
model.config.pad_token_id = tokenizer.pad_token_id

# Format: {"chosen": "Good response", "rejected": "Bad response"}
dataset = load_dataset("json", data_files="reward_data.jsonl", split="train")

reward_config = RewardConfig(
    output_dir="./reward-model",
    num_train_epochs=1,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    learning_rate=1e-5,
    bf16=True,
    logging_steps=10,
    max_length=512,
)

trainer = RewardTrainer(model=model, args=reward_config, train_dataset=dataset, tokenizer=tokenizer)
trainer.train()
trainer.save_model("./reward-model")

# Score a response
inputs = tokenizer("What is AI? AI is artificial intelligence.", return_tensors="pt")
with torch.no_grad():
    reward_score = model(**inputs).logits[0].item()
print(f"Reward score: {reward_score:.4f}")
```

## Reward Model Replacement with DPO

DPO eliminates the need for a separate reward model by directly optimizing from preference data:

```python
# Traditional RLHF: SFT -> Train Reward Model -> PPO with Reward Model
# DPO pipeline:     SFT -> DPO with preference data (no reward model)

# DPO implicitly defines a reward: r(x,y) = beta * log(pi(y|x) / pi_ref(y|x))

# DPO advantages:
# - No separate reward model to train and serve
# - No RL instability (reward hacking, KL divergence)
# - Simpler training loop (cross-entropy-like loss)
# - Lower memory footprint

# When to still use a reward model:
# - Best-of-N sampling at inference time
# - Online RLHF with data generated during training
# - When you need an explicit scoring function
```
