# /// script
# dependencies = ["transformers", "datasets", "trl", "peft", "accelerate", "torch", "safetensors"]
# ///
import os
import random
import inspect
from datasets import Dataset
from trl import SFTTrainer, SFTConfig
from transformers import AutoModelForCausalLM, AutoTokenizer

seed = 1337
random.seed(seed)

samples = [
    "User: What is Hyperbolic Geometry?\nAssistant: Hyperbolic geometry uses a curved space with constant negative curvature.\n",
    "User: How do you secure multi-agent systems?\nAssistant: Add governance gates and traceable packets before every tool call.\n",
    "User: What is a Sacred Tongue?\nAssistant: A domain-separated semantic channel for protocol intent and safety policy.\n",
    "User: Explain quickly the SCBE idea.\nAssistant: Layered deterministic geometry, strict trust gates, and policy-aware routing.\n",
    "User: Give one line profit plan.\nAssistant: Pick one high-intent product, automate publishing, and track conversion daily.\n",
]

train_texts = [
    s + "\n" for s in samples * 4
]

# tiny synthetic dataset
raw = [{"text": t} for t in train_texts]

dataset = Dataset.from_list(raw)
train_test = dataset.train_test_split(test_size=0.2, seed=seed)

# tiny public model to keep job cheap
model_id = "hf-internal-testing/tiny-random-GPT2"
max_steps = int(os.getenv("SCBE_SMOKE_MAX_STEPS", "6"))
use_cpu = os.getenv("SCBE_SMOKE_USE_CPU", "1") not in ("0", "false", "False")

trainer_cfg_kwargs = dict(
    output_dir="artifacts",
    num_train_epochs=1,
    per_device_train_batch_size=1,
    per_device_eval_batch_size=1,
    learning_rate=2e-4,
    max_steps=max_steps,
    logging_steps=1,
    eval_strategy="steps",
    eval_steps=2,
    save_steps=4,
    report_to="none",
    fp16=False,
    bf16=False,
)

if use_cpu:
    # Transformers >=4.45 uses use_cpu for CPU-only training in trainer args.
    if "use_cpu" in inspect.signature(SFTConfig).parameters:
        trainer_cfg_kwargs["use_cpu"] = True
    # Keep deterministic/low-resource behavior on non-GPU runs.
    trainer_cfg_kwargs["dataloader_num_workers"] = 0

# tokenizer init
tokenizer = AutoTokenizer.from_pretrained(model_id)
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

model = AutoModelForCausalLM.from_pretrained(model_id)

trainer = SFTTrainer(
    model=model,
    processing_class=tokenizer,
    train_dataset=train_test["train"],
    eval_dataset=train_test["test"],
    args=SFTConfig(**trainer_cfg_kwargs),
)

train_result = trainer.train()
print("TRAIN_RESULT", train_result.metrics)

# persist minimal artifact locally in container
final = model.save_pretrained("artifacts/final_model")
# tokenizer save for compatibility
tokenizer.save_pretrained("artifacts/final_model")

print("SMOKE_TRAIN_DONE", final)
