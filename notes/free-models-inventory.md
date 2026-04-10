---
title: "Free Open-Weight Model Inventory"
date: 2026-04-05
tags: [models, training, infrastructure, hydra]
status: actionable
tongue_profile: [CA, AV]
---

# Free Open-Weight Models for SCBE Training + Deployment

GPT Pro budget exhausted 2026-04-05. These are the replacements.

## Can Train Locally (GTX 1660 Ti, 6GB VRAM, QLoRA 4-bit)

| Model | Params | License | Downloads | HF Link |
|-------|--------|---------|-----------|---------|
| Qwen2.5-0.5B-Instruct | 0.5B | Apache 2.0 | 6.2M | hf.co/Qwen/Qwen2.5-0.5B-Instruct |
| Qwen3-1.7B | 1.7B | Apache 2.0 | 7.5M | hf.co/Qwen/Qwen3-1.7B |
| Llama-3.2-1B-Instruct | 1B | Llama 3.2 | 4.1M | hf.co/meta-llama/Llama-3.2-1B-Instruct |

## Can Train on Kaggle Free Tier (2x T4 16GB)

| Model | Params | License | Downloads | HF Link |
|-------|--------|---------|-----------|---------|
| Qwen3-4B | 4B | Apache 2.0 | 8.7M | hf.co/Qwen/Qwen3-4B |
| Qwen3-8B | 8B | Apache 2.0 | 9.3M | hf.co/Qwen/Qwen3-8B |
| Qwen2.5-7B-Instruct | 7B | Apache 2.0 | 13.5M | hf.co/Qwen/Qwen2.5-7B-Instruct |
| Llama-3.1-8B-Instruct | 8B | Llama 3.1 | 8.5M | hf.co/meta-llama/Llama-3.1-8B-Instruct |
| Mistral-7B-Instruct-v0.3 | 7B | Apache 2.0 | 2.2M | hf.co/mistralai/Mistral-7B-Instruct-v0.3 |
| Llama-3.2-3B-Instruct | 3B | Llama 3.2 | 5.9M | hf.co/meta-llama/Llama-3.2-3B-Instruct |

## Need Cloud (A100/A10G) or Heavy Quantization

| Model | Params | License | Downloads | HF Link |
|-------|--------|---------|-----------|---------|
| Llama-3.1-70B-Instruct | 70B | Llama 3.1 | 1.0M | hf.co/meta-llama/Llama-3.1-70B-Instruct |
| Mixtral-8x7B-Instruct | 8x7B MoE | Apache 2.0 | 433K | hf.co/mistralai/Mixtral-8x7B-Instruct-v0.1 |
| Mistral-Small-3.2-24B | 24B | Apache 2.0 | 742K | hf.co/mistralai/Mistral-Small-3.2-24B-Instruct-2506 |

## Free Speech/Audio Models

| Model | Type | License | HF Link |
|-------|------|---------|---------|
| Voxtral-Mini-3B-2507 | ASR (13 langs) | Apache 2.0 | hf.co/mistralai/Voxtral-Mini-3B-2507 |
| Voxtral-Mini-4B-Realtime | Real-time ASR | Apache 2.0 | hf.co/mistralai/Voxtral-Mini-4B-Realtime-2602 |

## HYDRA Round Table Agent Mapping

| Tongue | Role | Recommended Model | Why |
|--------|------|-------------------|-----|
| KO (Intent) | What is this trying to DO? | Qwen3-4B | Fast, good at intent classification |
| AV (Wisdom) | What knowledge assumed? | Qwen2.5-7B-Instruct | Strong knowledge, Apache 2.0 |
| RU (Governance) | What rules touched? | Mistral-7B-Instruct-v0.3 | Good at structured reasoning |
| CA (Compute) | What patterns here? | Qwen3-8B | Best reasoning at this size |
| UM (Security) | What attack surfaces? | Llama-3.1-8B-Instruct | Meta's safety training |
| DR (Architecture) | What structure expressed? | Llama-3.2-3B-Instruct | Efficient, structural analysis |

## How to Run Locally

### Ollama (easiest)
```bash
# Install from ollama.com, then:
ollama pull qwen3:8b
ollama pull llama3.1:8b
ollama pull mistral:7b

# OpenAI-compatible API at localhost:11434
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen3:8b","messages":[{"role":"user","content":"hello"}]}'
```

### HuggingFace Transformers
```python
from transformers import AutoModelForCausalLM, AutoTokenizer
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-8B", device_map="auto")
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-8B")
```

### vLLM (production serving)
```bash
pip install vllm
vllm serve Qwen/Qwen3-8B --port 8000
# OpenAI-compatible API at localhost:8000
```

## Training Corpus Available

- `training-data/sft/quantum_frequency_bundles_sft.jsonl` — 11,389 records, 183MB
- `training-data/sft/snake_pipeline.jsonl` — 16-stage enriched
- All files in `training-data/sft/` directory
- Scripts: `scripts/hf_training_loop.py`, `scripts/train_scbe_coder_kaggle.py`

## PyTorch CUDA Setup Required

Python 3.14 has no CUDA wheels. Use Python 3.12 venv:
```powershell
C:\Users\issda\Python312\python.exe -m venv .training-venv
.training-venv\Scripts\activate
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install transformers datasets peft accelerate bitsandbytes huggingface_hub
```

See `notes/pytorch-cuda-build-and-training-plan.md` for full details including building wheels from source.
