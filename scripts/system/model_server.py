"""
Local model server — loads SmolLM2-360M once, swaps LoRA adapters per request.

Usage:
    python scripts/system/model_server.py
    python scripts/system/model_server.py --port 8010

Endpoints:
    POST /generate   {"adapter": "coder|lawbot|commerce", "prompt": "...", "max_tokens": 256}
    GET  /adapters   list available adapters
    GET  /health     status
"""

import argparse
import os
import time
# BASE_MODELS and _build_adapter_configs defined below after os import
from pathlib import Path

import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from peft import PeftModel
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

import argparse as _argparse

# Detect which model size to serve (set via --model flag or MODEL_SIZE env var)
_MODEL_SIZE = os.environ.get("MODEL_SIZE", "360m")

BASE_MODELS = {
    "360m": "C:/Users/issda/SCBE-AETHERMOORE/models/smollm2-360m-instruct",
    "7b": "Qwen/Qwen2.5-Coder-7B-Instruct",
}
ADAPTER_BASE = "F:/scbe-rag/adapters"

_SYSTEMS = {
    "coder": "You are a precise coding assistant. Write clean, working code with brief explanations.",
    "lawbot": "You are a helpful legal information assistant. Always clarify you provide general information, not legal advice, and recommend consulting an attorney for specific situations.",
    "commerce": (
        "You are a commerce and web development assistant. "
        "You help with Square payments, Stripe, frontend/backend code, security, and checkout processing. "
        "You NEVER recommend selling below cost + $3 minimum profit."
    ),
    "base": "You are a helpful assistant.",
}

def _build_adapter_configs(model_size: str) -> dict:
    return {
        "coder": {"path": f"{ADAPTER_BASE}/coder-{model_size}", "system": _SYSTEMS["coder"]},
        "lawbot": {"path": f"{ADAPTER_BASE}/lawbot-{model_size}", "system": _SYSTEMS["lawbot"]},
        "commerce": {"path": f"{ADAPTER_BASE}/commerce-{model_size}", "system": _SYSTEMS["commerce"]},
        "base": {"path": None, "system": _SYSTEMS["base"]},
    }

BASE_MODEL = BASE_MODELS[_MODEL_SIZE]
ADAPTER_CONFIGS = _build_adapter_configs(_MODEL_SIZE)

app = FastAPI(title="SCBE Model Server")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Global state
_base_model = None
_tokenizer = None
_active_adapter = None
_model_with_adapter = None


def get_available_adapters() -> list[str]:
    available = ["base"]
    for name, cfg in ADAPTER_CONFIGS.items():
        if name == "base":
            continue
        if cfg["path"] and Path(cfg["path"]).exists():
            # Check if adapter_config.json is there (trained)
            if (Path(cfg["path"]) / "adapter_config.json").exists():
                available.append(name)
    return available


def load_base():
    global _base_model, _tokenizer
    if _base_model is not None:
        return

    print("Loading tokenizer...")
    _tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    _tokenizer.pad_token = _tokenizer.eos_token

    print("Loading base model in 4-bit...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )
    _base_model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb_config,
        device_map="auto",
    )
    _base_model.eval()
    print("Base model loaded.")


def load_adapter(adapter_name: str):
    global _active_adapter, _model_with_adapter, _base_model

    if adapter_name == _active_adapter:
        return  # Already loaded

    cfg = ADAPTER_CONFIGS.get(adapter_name)
    if not cfg:
        raise ValueError(f"Unknown adapter: {adapter_name}")

    if adapter_name == "base" or not cfg["path"]:
        _model_with_adapter = _base_model
        _active_adapter = "base"
        return

    adapter_path = cfg["path"]
    if not (Path(adapter_path) / "adapter_config.json").exists():
        raise ValueError(f"Adapter '{adapter_name}' not trained yet. Run: python scripts/system/hand_tune.py --adapter {adapter_name}")

    print(f"Loading adapter: {adapter_name}")
    _model_with_adapter = PeftModel.from_pretrained(_base_model, adapter_path)
    _model_with_adapter.eval()
    _active_adapter = adapter_name
    print(f"Adapter '{adapter_name}' active.")


def generate(adapter_name: str, prompt: str, max_tokens: int = 256) -> str:
    cfg = ADAPTER_CONFIGS[adapter_name]
    system = cfg["system"]

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": prompt},
    ]

    text = _tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = _tokenizer(text, return_tensors="pt").to(_model_with_adapter.device)

    with torch.no_grad():
        output = _model_with_adapter.generate(
            **inputs,
            max_new_tokens=max_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
            pad_token_id=_tokenizer.eos_token_id,
        )

    new_tokens = output[0][inputs["input_ids"].shape[1]:]
    return _tokenizer.decode(new_tokens, skip_special_tokens=True).strip()


class GenerateRequest(BaseModel):
    adapter: str = "base"
    prompt: str
    max_tokens: int = 256


@app.on_event("startup")
async def startup():
    load_base()
    # Pre-load first available trained adapter
    available = get_available_adapters()
    if len(available) > 1:
        load_adapter(available[1])
    else:
        load_adapter("base")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "active_adapter": _active_adapter,
        "available_adapters": get_available_adapters(),
        "model_loaded": _base_model is not None,
    }


@app.get("/adapters")
def list_adapters():
    result = {}
    for name in get_available_adapters():
        result[name] = {"system": ADAPTER_CONFIGS[name]["system"]}
    return result


@app.post("/generate")
def generate_endpoint(req: GenerateRequest):
    if req.adapter not in ADAPTER_CONFIGS:
        raise HTTPException(400, f"Unknown adapter '{req.adapter}'. Available: {get_available_adapters()}")

    if req.adapter not in get_available_adapters():
        raise HTTPException(400, f"Adapter '{req.adapter}' not trained yet. Run hand_tune.py --adapter {req.adapter}")

    t0 = time.time()
    load_adapter(req.adapter)
    response = generate(req.adapter, req.prompt, req.max_tokens)
    elapsed = round(time.time() - t0, 2)

    return {
        "adapter": req.adapter,
        "prompt": req.prompt,
        "response": response,
        "elapsed_s": elapsed,
    }


def main():
    global BASE_MODEL, ADAPTER_CONFIGS, _MODEL_SIZE
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8010)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--model", choices=["360m", "7b"], default=_MODEL_SIZE,
                        help="Which base model to serve (default: 360m)")
    args = parser.parse_args()

    if args.model != _MODEL_SIZE:
        _MODEL_SIZE = args.model
        os.environ["MODEL_SIZE"] = args.model
        BASE_MODEL = BASE_MODELS[args.model]
        ADAPTER_CONFIGS = _build_adapter_configs(args.model)

    print(f"Starting model server on {args.host}:{args.port} (model: {args.model})")
    print(f"Base: {BASE_MODEL}")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
