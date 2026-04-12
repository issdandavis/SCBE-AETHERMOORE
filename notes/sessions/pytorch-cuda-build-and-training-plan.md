---
title: PyTorch CUDA Build + Polly Training Plan
date: 2026-04-05
tags: [training, pytorch, cuda, polly, infrastructure]
status: actionable
---

# PyTorch CUDA Build + Polly Training Plan

## Hardware

- CPU: i7-10750H, 12 threads
- RAM: ~12 GB
- GPU: GTX 1660 Ti, 6 GB VRAM (compute capability 7.5)
- NVIDIA Driver: 591.86 (supports CUDA 13.1)
- Current PyTorch: 2.10.0 **CPU-only** (Python 3.14 — no CUDA wheels exist yet)

## The Problem

Python 3.14 is too new for PyTorch CUDA wheels. PyTorch only ships pre-built CUDA wheels for Python 3.10-3.13.

## Option A: Quick Fix — Python 3.12 venv (5 min, do this first)

```powershell
# Create training venv with Python 3.12 (already installed at C:\Users\issda\Python312\python.exe)
C:\Users\issda\Python312\python.exe -m venv C:\Users\issda\SCBE-AETHERMOORE\.training-venv

# Activate
C:\Users\issda\SCBE-AETHERMOORE\.training-venv\Scripts\activate

# Install CUDA-enabled PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install training deps
pip install transformers datasets peft accelerate bitsandbytes huggingface_hub
```

This gets: Qwen2.5-0.5B or Qwen3-1.7B with 4-bit QLoRA on 6GB VRAM. Same as Kaggle T4 runs.

## Option B: Build PyTorch Wheels for Python 3.14 (weekend project)

### Prerequisites to install

1. **CUDA Toolkit 12.4** (~3GB)
   - Download from NVIDIA developer site
   - Install to `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4`

2. **cuDNN 9.x for CUDA 12** (~700MB)
   - Download from NVIDIA developer site
   - Extract into CUDA toolkit directory

3. **Visual Studio 2022** with C++ build tools (MSVC compiler)

4. **CMake 3.26+** and **Ninja**
   ```
   pip install cmake ninja
   ```

### Build steps

```powershell
# Clone PyTorch
git clone --recursive https://github.com/pytorch/pytorch
cd pytorch
git checkout v2.10.0
git submodule sync
git submodule update --init --recursive

# Environment variables
$env:CUDA_HOME = "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4"
$env:CMAKE_GENERATOR = "Ninja"
$env:USE_CUDA = "1"
$env:TORCH_CUDA_ARCH_LIST = "7.5"  # GTX 1660 Ti

# Build wheel (1-3 hours on i7-10750H)
python setup.py bdist_wheel

# Wheel output in dist/ — install with:
pip install dist/torch-*.whl
```

### Build tradeoffs

- Time: 2-4 hours compile + downloads
- Disk: ~15GB (toolkit + source + build artifacts)
- Risk: Build failures, version mismatches on Windows
- Benefit: CUDA on Python 3.14, custom arch optimization, reusable knowledge

## Free Models to Fine-Tune

All Apache 2.0 or open license, all on HuggingFace:

| Model | Size | Can train on 1660 Ti? | Notes |
|-------|------|-----------------------|-------|
| Qwen2.5-0.5B-Instruct | 0.5B | Yes (QLoRA 4-bit) | Best fit for 6GB VRAM |
| Qwen3-1.7B | 1.7B | Tight but possible | 4-bit QLoRA + gradient checkpointing |
| Qwen3-4B | 4B | Inference only | Train on Kaggle/cloud |
| Qwen3-8B | 8B | Inference only (quantized) | Train on Kaggle/cloud |
| Llama-3.2-1B-Instruct | 1B | Yes (QLoRA 4-bit) | Good alternative |
| Llama-3.2-3B-Instruct | 3B | Tight | 4-bit QLoRA |
| Mistral-7B-Instruct-v0.3 | 7B | Inference only | Train on Kaggle |

## Polly Training Run Plan

Goal: Update Polly (website chatbot) with SCBE-aware responses.

### Training corpus available

- `training-data/sft/quantum_frequency_bundles_sft.jsonl` — 11,389 records, 183MB (with color fields)
- `training-data/sft/snake_pipeline.jsonl` — 16-stage enriched data
- All SFT files in `training-data/sft/` directory
- Existing training scripts: `scripts/hf_training_loop.py`, `scripts/train_scbe_coder_kaggle.py`

### Training steps

1. Set up Python 3.12 venv with CUDA PyTorch (Option A above)
2. Pick base model: Qwen2.5-0.5B-Instruct (safest for 6GB) or Qwen3-1.7B (stretch)
3. Filter/format SFT data for Polly's use case (website Q&A, SCBE concepts, governance)
4. Run QLoRA fine-tune locally or on Kaggle
5. Merge LoRA adapter, push to HuggingFace
6. Serve via vLLM or Ollama with OpenAI-compatible API
7. Wire into website chatbot

### Kaggle alternative (if local is too slow)

- 2x T4 (16GB each), 30 hrs/week free
- Can train up to 7B with QLoRA
- Existing script: `scripts/train_scbe_coder_kaggle.py`

## System Review Results (2026-04-05)

10 bugs fixed across 8 files in audio/chromatic/quantum/TTS pipeline:
- 5 critical (import crashes, wrong stress calc, unhandled JSON)
- 5 medium (stale docs, forward refs, unused imports)
- All 16 snake pipeline stages verified functional
- 11,389 SFT records confirmed with color_field data
- System is production-ready for training data generation
