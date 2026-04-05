# HuggingFace Accelerate

Accelerate is a library that enables the same PyTorch code to run across any distributed configuration (single GPU, multi-GPU, TPU, mixed precision) with minimal code changes. It abstracts away the complexity of distributed training.

## Accelerator Init with Mixed Precision

The `Accelerator` class is the core entry point that handles device placement and distributed setup:

```python
from accelerate import Accelerator
import torch
from torch.utils.data import DataLoader
from transformers import AutoModelForCausalLM, AutoTokenizer, get_scheduler

# Initialize accelerator with mixed precision
accelerator = Accelerator(
    mixed_precision="bf16",       # "no", "fp16", "bf16"
    gradient_accumulation_steps=4,
    log_with="wandb",            # Optional: "wandb", "tensorboard", "all"
    project_dir="./logs",
)

# Print distributed info
print(f"Device: {accelerator.device}")
print(f"Num processes: {accelerator.num_processes}")
print(f"Process index: {accelerator.process_index}")
print(f"Is main process: {accelerator.is_main_process}")

# Load model and optimizer (on CPU first)
model = AutoModelForCausalLM.from_pretrained("gpt2")
optimizer = torch.optim.AdamW(model.parameters(), lr=5e-5)

# Create dataloader
train_dataloader = DataLoader(train_dataset, batch_size=8, shuffle=True)

# Create scheduler
num_epochs = 3
lr_scheduler = get_scheduler(
    "cosine",
    optimizer=optimizer,
    num_warmup_steps=100,
    num_training_steps=len(train_dataloader) * num_epochs,
)

# Prepare everything with accelerator (handles device placement, DDP wrapping)
model, optimizer, train_dataloader, lr_scheduler = accelerator.prepare(
    model, optimizer, train_dataloader, lr_scheduler
)

# Training loop (same code works for single GPU, multi-GPU, TPU)
model.train()
for epoch in range(num_epochs):
    for batch in train_dataloader:
        with accelerator.accumulate(model):
            outputs = model(**batch)
            loss = outputs.loss
            accelerator.backward(loss)
            optimizer.step()
            lr_scheduler.step()
            optimizer.zero_grad()

    # Log only on main process
    if accelerator.is_main_process:
        print(f"Epoch {epoch}: loss = {loss.item():.4f}")

# Save model (unwrap DDP wrapper)
accelerator.wait_for_everyone()
unwrapped_model = accelerator.unwrap_model(model)
unwrapped_model.save_pretrained(
    "./output",
    save_function=accelerator.save,
    is_main_process=accelerator.is_main_process,
)
```

## CLI Launch Commands

Use the `accelerate` CLI to configure and launch distributed training:

```bash
# Interactive configuration wizard (creates config file)
accelerate config

# Launch on single GPU
accelerate launch train.py

# Launch on multiple GPUs (auto-detect)
accelerate launch --multi_gpu train.py

# Launch on specific GPUs
accelerate launch --num_processes 4 --gpu_ids "0,1,2,3" train.py

# Launch with mixed precision
accelerate launch --mixed_precision bf16 train.py

# Launch on multiple machines
accelerate launch \
  --num_machines 2 \
  --machine_rank 0 \
  --main_process_ip 192.168.1.1 \
  --main_process_port 29500 \
  --num_processes 8 \
  train.py

# Launch with a config file
accelerate launch --config_file ./accelerate_config.yaml train.py

# Test your setup
accelerate test

# Print environment info
accelerate env
```

Example `accelerate_config.yaml`:

```yaml
compute_environment: LOCAL_MACHINE
distributed_type: MULTI_GPU
mixed_precision: bf16
num_machines: 1
num_processes: 4
gpu_ids: "0,1,2,3"
main_training_function: main
```

## DeepSpeed Integration

Use DeepSpeed ZeRO stages for memory-efficient training of large models:

```python
from accelerate import Accelerator

# DeepSpeed is configured via accelerate config or config file
accelerator = Accelerator()

# The training code remains exactly the same as the basic example above
# DeepSpeed is handled transparently by Accelerator
```

DeepSpeed config via `accelerate_config.yaml`:

```yaml
compute_environment: LOCAL_MACHINE
distributed_type: DEEPSPEED
deepspeed_config:
  zero_stage: 2                  # 0, 1, 2, or 3
  offload_optimizer_device: none # "none", "cpu", "nvme"
  offload_param_device: none     # "none", "cpu", "nvme"
  gradient_accumulation_steps: 4
  gradient_clipping: 1.0
  zero3_init_flag: false
  zero3_save_16bit_model: true
mixed_precision: bf16
num_processes: 4
```

```bash
# Launch with DeepSpeed ZeRO Stage 2
accelerate launch --use_deepspeed \
  --deepspeed_config_file ds_config.json \
  train.py

# DeepSpeed ZeRO Stage 3 (full sharding)
accelerate launch --use_deepspeed \
  --zero_stage 3 \
  --offload_optimizer_device cpu \
  --offload_param_device cpu \
  train.py
```

Example `ds_config.json` for ZeRO Stage 3:

```json
{
  "bf16": {"enabled": true},
  "zero_optimization": {
    "stage": 3,
    "offload_optimizer": {"device": "cpu", "pin_memory": true},
    "offload_param": {"device": "cpu", "pin_memory": true},
    "overlap_comm": true,
    "contiguous_gradients": true,
    "sub_group_size": 1e9,
    "reduce_bucket_size": "auto",
    "stage3_prefetch_bucket_size": "auto",
    "stage3_param_persistence_threshold": "auto",
    "stage3_max_live_parameters": 1e9,
    "stage3_max_reuse_distance": 1e9,
    "stage3_gather_16bit_weights_on_model_save": true
  },
  "gradient_accumulation_steps": 4,
  "gradient_clipping": 1.0,
  "train_batch_size": "auto",
  "train_micro_batch_size_per_gpu": "auto"
}
```

## FSDP Integration

Fully Sharded Data Parallel (PyTorch native) for distributed training:

```python
from accelerate import Accelerator, FullyShardedDataParallelPlugin
from torch.distributed.fsdp.fully_sharded_data_parallel import (
    FullOptimStateDictType,
    FullStateDictType,
)

# Configure FSDP plugin
fsdp_plugin = FullyShardedDataParallelPlugin(
    state_dict_config=FullStateDictType.FULL_STATE_DICT,
    optim_state_dict_config=FullOptimStateDictType.FULL_OPTIM_STATE_DICT,
)

accelerator = Accelerator(
    fsdp_plugin=fsdp_plugin,
    mixed_precision="bf16",
)

# Rest of training code is identical to the basic example
```

FSDP config via `accelerate_config.yaml`:

```yaml
compute_environment: LOCAL_MACHINE
distributed_type: FSDP
fsdp_config:
  fsdp_auto_wrap_policy: TRANSFORMER_BASED_WRAP
  fsdp_transformer_layer_cls_to_wrap: LlamaDecoderLayer
  fsdp_sharding_strategy: FULL_SHARD  # FULL_SHARD, SHARD_GRAD_OP, NO_SHARD
  fsdp_offload_params: false
  fsdp_state_dict_type: FULL_STATE_DICT
  fsdp_backward_prefetch_policy: BACKWARD_PRE
  fsdp_forward_prefetch: false
  fsdp_use_orig_params: true
  fsdp_cpu_ram_efficient_loading: true
  fsdp_sync_module_states: true
mixed_precision: bf16
num_processes: 4
```

```bash
# Launch with FSDP
accelerate launch --use_fsdp \
  --fsdp_sharding_strategy 1 \
  --fsdp_auto_wrap_policy TRANSFORMER_BASED_WRAP \
  --fsdp_transformer_layer_cls_to_wrap LlamaDecoderLayer \
  train.py
```
