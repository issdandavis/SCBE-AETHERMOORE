# vLLM

vLLM is a high-throughput, memory-efficient inference engine for large language models. It uses PagedAttention to manage KV cache memory dynamically, enabling significantly higher throughput than naive implementations.

## PagedAttention Overview

PagedAttention is vLLM's core innovation. It partitions the KV cache into fixed-size blocks (pages) that are allocated on demand, similar to virtual memory in operating systems:

```
Traditional attention:
- Pre-allocates contiguous memory for max sequence length per request
- Wastes 60-80% of KV cache memory due to fragmentation and over-allocation

PagedAttention:
- Allocates KV cache in non-contiguous blocks (pages)
- Pages are mapped via a block table (like a page table in virtual memory)
- Memory is allocated only as tokens are generated
- Enables memory sharing across sequences (e.g., beam search, parallel sampling)
- Achieves near-zero waste of KV cache memory

Benefits:
- 2-4x higher throughput than HuggingFace Transformers
- Supports longer sequences within the same GPU memory
- Efficient batching of requests with different lengths
- Copy-on-write for shared prefixes (prompt caching)
```

## LLM Class Batch Interface

The `LLM` class provides a simple Python API for offline batch inference:

```python
from vllm import LLM, SamplingParams

# Initialize the LLM
llm = LLM(
    model="meta-llama/Llama-3.1-8B-Instruct",
    dtype="bfloat16",
    tensor_parallel_size=1,     # Number of GPUs for tensor parallelism
    gpu_memory_utilization=0.90, # Fraction of GPU memory to use
    max_model_len=4096,          # Maximum sequence length
)

# Define sampling parameters
sampling_params = SamplingParams(
    temperature=0.7,
    top_p=0.9,
    top_k=50,
    max_tokens=256,
    stop=["\n\n", "###"],
    presence_penalty=0.0,
    frequency_penalty=0.0,
)

# Batch inference with multiple prompts
prompts = [
    "Explain quantum computing in simple terms.",
    "Write a Python function to sort a list.",
    "What are the benefits of exercise?",
    "Summarize the theory of relativity.",
]

outputs = llm.generate(prompts, sampling_params)

for output in outputs:
    prompt = output.prompt
    generated = output.outputs[0].text
    print(f"Prompt: {prompt[:50]}...")
    print(f"Output: {generated[:200]}")
    print(f"Tokens: {len(output.outputs[0].token_ids)}")
    print("---")

# Chat-style inference with message format
llm = LLM(model="meta-llama/Llama-3.1-8B-Instruct")

conversations = [
    [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is machine learning?"},
    ],
    [
        {"role": "user", "content": "Write a haiku about coding."},
    ],
]

outputs = llm.chat(conversations, SamplingParams(max_tokens=256, temperature=0.8))

for output in outputs:
    print(output.outputs[0].text)

# Greedy decoding (deterministic)
greedy_params = SamplingParams(temperature=0, max_tokens=128)
outputs = llm.generate(["The capital of France is"], greedy_params)
```

## Batch Inference with Ray Data

Scale batch inference across multiple GPUs or nodes using Ray Data:

```python
import ray
from vllm import LLM, SamplingParams

# Initialize Ray
ray.init()

# Define the inference function
class VLLMPredictor:
    def __init__(self):
        self.llm = LLM(
            model="meta-llama/Llama-3.1-8B-Instruct",
            dtype="bfloat16",
            gpu_memory_utilization=0.90,
        )
        self.sampling_params = SamplingParams(
            temperature=0.7,
            max_tokens=256,
        )

    def __call__(self, batch):
        prompts = batch["prompt"].tolist()
        outputs = self.llm.generate(prompts, self.sampling_params)
        batch["response"] = [out.outputs[0].text for out in outputs]
        batch["num_tokens"] = [len(out.outputs[0].token_ids) for out in outputs]
        return batch

# Create Ray dataset
ds = ray.data.read_json("prompts.jsonl")

# Run batch inference with GPU workers
results = ds.map_batches(
    VLLMPredictor,
    concurrency=2,               # Number of parallel workers
    num_gpus=1,                  # GPUs per worker
    batch_size=64,               # Batch size per worker
)

# Collect results
for row in results.iter_rows():
    print(f"Prompt: {row['prompt'][:50]}...")
    print(f"Response: {row['response'][:100]}...")

# Save results
results.write_json("outputs/")

# Multi-GPU tensor parallelism with Ray
class MultiGPUPredictor:
    def __init__(self):
        self.llm = LLM(
            model="meta-llama/Llama-3.1-70B-Instruct",
            dtype="bfloat16",
            tensor_parallel_size=4,
        )
        self.params = SamplingParams(temperature=0.7, max_tokens=512)

    def __call__(self, batch):
        outputs = self.llm.generate(batch["prompt"].tolist(), self.params)
        batch["response"] = [out.outputs[0].text for out in outputs]
        return batch

results = ds.map_batches(MultiGPUPredictor, concurrency=1, num_gpus=4, batch_size=32)
```

## Prompt Embedding Inference

Pass pre-computed token IDs or multi-modal inputs directly instead of text prompts:

```python
from vllm import LLM, SamplingParams

# Initialize LLM
llm = LLM(
    model="meta-llama/Llama-3.1-8B-Instruct",
    dtype="bfloat16",
)

# Method 1: Token IDs directly
token_ids = [1, 15043, 29892, 590, 1024, 338]  # "Hello, my name is"
sampling_params = SamplingParams(max_tokens=50, temperature=0.7)

outputs = llm.generate(
    [{"prompt_token_ids": token_ids}],
    sampling_params,
)
print(outputs[0].outputs[0].text)

# Method 2: Multi-modal inputs with embeddings
# For models that support multi-modal inputs (e.g., vision-language models)
outputs = llm.generate(
    [{
        "prompt": "Describe this image:",
        "multi_modal_data": {
            "image": image_data,  # PIL Image or tensor
        },
    }],
    sampling_params,
)

# Serving with OpenAI-compatible API
# Start server: python -m vllm.entrypoints.openai.api_server \
#   --model meta-llama/Llama-3.1-8B-Instruct --port 8000

# Then use the OpenAI client:
from openai import OpenAI

client = OpenAI(base_url="http://localhost:8000/v1", api_key="unused")
response = client.chat.completions.create(
    model="meta-llama/Llama-3.1-8B-Instruct",
    messages=[{"role": "user", "content": "Hello!"}],
    max_tokens=100,
    temperature=0.7,
)
print(response.choices[0].message.content)
```
