# PEFT (Parameter-Efficient Fine-Tuning)

PEFT provides methods for efficiently adapting large pretrained models to downstream tasks by only training a small number of additional parameters. Supports LoRA, QLoRA, prefix tuning, prompt tuning, and adapter methods.

## LoRA Configuration

Low-Rank Adaptation adds trainable rank-decomposition matrices to transformer layers:

```python
from peft import LoraConfig, get_peft_model, TaskType
from transformers import AutoModelForCausalLM

# Load base model
model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-3.1-8B")

# Configure LoRA
lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=16,                          # Rank of the update matrices
    lora_alpha=32,                 # Scaling factor (alpha/r)
    lora_dropout=0.05,             # Dropout on LoRA layers
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    bias="none",                   # "none", "all", or "lora_only"
    modules_to_save=None,          # Additional modules to save
)

# Apply LoRA to model
model = get_peft_model(model, lora_config)

# Print trainable parameters
model.print_trainable_parameters()
# trainable params: 6,553,600 || all params: 8,036,163,584 || trainable%: 0.0816

# Save LoRA adapter (only saves the small adapter weights)
model.save_pretrained("./lora-adapter")

# Load LoRA adapter
from peft import PeftModel
base_model = AutoModelForCausalLM.from_pretrained("meta-llama/Llama-3.1-8B")
model = PeftModel.from_pretrained(base_model, "./lora-adapter")
```

## QLoRA 4-Bit Quantized Training

Combine 4-bit quantization with LoRA for memory-efficient fine-tuning:

```python
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datasets import load_dataset

# 4-bit quantization config
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

# Load quantized model
model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.1-8B",
    quantization_config=bnb_config,
    device_map="auto",
)

tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B")
tokenizer.pad_token = tokenizer.eos_token

# Prepare model for k-bit training (freeze, cast norms to float32)
model = prepare_model_for_kbit_training(model)

# Apply LoRA
lora_config = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    bias="none",
    task_type="CAUSAL_LM",
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

# Load dataset
dataset = load_dataset("json", data_files="train.jsonl", split="train")

def tokenize(example):
    return tokenizer(example["text"], truncation=True, max_length=512, padding="max_length")

dataset = dataset.map(tokenize, batched=True, remove_columns=dataset.column_names)

# Train
training_args = TrainingArguments(
    output_dir="./qlora-output",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    learning_rate=2e-4,
    bf16=True,
    logging_steps=10,
    optim="paged_adamw_8bit",
    warmup_ratio=0.03,
    lr_scheduler_type="cosine",
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset,
    data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
)

trainer.train()
model.save_pretrained("./qlora-adapter")
```

## merge_and_unload

Merge LoRA weights back into the base model for deployment:

```python
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# Load base model
base_model = AutoModelForCausalLM.from_pretrained(
    "meta-llama/Llama-3.1-8B",
    torch_dtype=torch.bfloat16,
    device_map="auto",
)

# Load adapter on top of base
model = PeftModel.from_pretrained(base_model, "./qlora-adapter")

# Merge LoRA weights into base model and remove adapter overhead
merged_model = model.merge_and_unload()

# Save the merged full model
merged_model.save_pretrained("./merged-model")
tokenizer = AutoTokenizer.from_pretrained("meta-llama/Llama-3.1-8B")
tokenizer.save_pretrained("./merged-model")

# Push merged model to Hub
merged_model.push_to_hub("username/my-merged-model")
tokenizer.push_to_hub("username/my-merged-model")
```

## AutoPeftModel Load, Merge, and Save

Convenience class that auto-detects the PEFT method and loads accordingly:

```python
from peft import AutoPeftModelForCausalLM
from transformers import AutoTokenizer
import torch

# Load adapter model directly (auto-detects base model from adapter config)
model = AutoPeftModelForCausalLM.from_pretrained(
    "./qlora-adapter",
    torch_dtype=torch.bfloat16,
    device_map="auto",
)

# Load from Hub
model = AutoPeftModelForCausalLM.from_pretrained(
    "username/my-lora-adapter",
    torch_dtype=torch.bfloat16,
    device_map="auto",
)

# Merge and save in one step
merged = model.merge_and_unload()
merged.save_pretrained("./production-model")

# Generate with adapter model (works without merging)
tokenizer = AutoTokenizer.from_pretrained("./qlora-adapter")
inputs = tokenizer("Hello, my name is", return_tensors="pt").to(model.device)
outputs = model.generate(**inputs, max_new_tokens=50)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))
```

## LoRA-FA Optimizer

LoRA-FA (Frozen-A) freezes the A matrix after initialization and only trains B, reducing memory further:

```python
from peft import LoraConfig, get_peft_model

# LoRA-FA: freeze the down-projection (A) matrix
lora_fa_config = LoraConfig(
    r=16,
    lora_alpha=32,
    lora_dropout=0.05,
    target_modules=["q_proj", "v_proj"],
    use_rslora=True,         # Rank-stabilized LoRA scaling
    bias="none",
    task_type="CAUSAL_LM",
)

# Standard LoRA: A is random init (Kaiming), B is zero init
# LoRA-FA: A is random init and frozen, only B is trained
# This halves the trainable parameters and optimizer states

from transformers import AutoModelForCausalLM
model = AutoModelForCausalLM.from_pretrained("gpt2")
model = get_peft_model(model, lora_fa_config)
model.print_trainable_parameters()

# rsLoRA uses alpha/sqrt(r) scaling instead of alpha/r
# This stabilizes training across different rank values
```
