"""
Merge a trained LoRA adapter into the base model, then export to GGUF for Ollama.

Pipeline:
    1. Load base model (full precision, CPU if needed)
    2. Load LoRA adapter and merge weights
    3. Save merged HF model to F:/scbe-rag/merged/<adapter>-<size>/
    4. Convert to GGUF using llama.cpp (must be installed)
    5. Quantize to Q4_K_M
    6. Write Modelfile and create the Ollama model

Usage:
    python scripts/system/merge_to_gguf.py --adapter commerce --model 7b
    python scripts/system/merge_to_gguf.py --adapter coder --model 360m
    python scripts/system/merge_to_gguf.py --adapter commerce --model 7b --skip-convert  (if GGUF already done)

Requirements:
    pip install peft transformers torch
    # For GGUF conversion — clone llama.cpp and set LLAMA_CPP_PATH:
    # git clone https://github.com/ggerganov/llama.cpp C:/tools/llama.cpp
    # pip install -r C:/tools/llama.cpp/requirements.txt
    # set LLAMA_CPP_PATH=C:/tools/llama.cpp
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Config — matches hand_tune.py
# ---------------------------------------------------------------------------

MODEL_BASES = {
    "360m": "C:/Users/issda/SCBE-AETHERMOORE/models/smollm2-360m-instruct",
    "7b": "Qwen/Qwen2.5-Coder-7B-Instruct",
}

ADAPTER_BASE = "F:/scbe-rag/adapters"
MERGED_BASE = "C:/Users/issda/tmp/scbe-merged"   # temp — 14GB for 7b, deleted after GGUF
GGUF_BASE = "F:/scbe-rag/gguf"                   # final home — Q4_K_M is ~4.5GB, fits on F:

ADAPTER_SYSTEM_PROMPTS = {
    "coder": "You are a precise coding assistant. Write clean, working code with brief explanations.",
    "lawbot": (
        "You are a helpful legal information assistant. Always clarify you provide general information, "
        "not legal advice, and recommend consulting an attorney for specific situations."
    ),
    "commerce": (
        "You are a commerce and web development assistant. "
        "You help with Square payments, Stripe, frontend/backend code, security, and checkout processing. "
        "You NEVER recommend selling below cost + $3 minimum profit."
    ),
}

LLAMA_CPP_PATH = os.environ.get("LLAMA_CPP_PATH", "C:/tools/llama.cpp")

# Space requirements (bytes)
SPACE_NEEDED_C = {
    "360m": 2 * 1024**3,   # ~2GB merged
    "7b":  16 * 1024**3,   # ~14-16GB merged (float16)
}
SPACE_NEEDED_F = {
    "360m": 500 * 1024**2,  # ~500MB GGUF
    "7b":   5 * 1024**3,    # ~4.5GB GGUF
}


def check_disk_space(model_key: str) -> None:
    """Abort early if C: or F: don't have enough room."""
    import psutil

    c_free = psutil.disk_usage("C:\\").free
    f_free = psutil.disk_usage("F:\\").free

    c_need = SPACE_NEEDED_C[model_key]
    f_need = SPACE_NEEDED_F[model_key]

    print("=== Disk space check ===")
    print(f"  C: free {c_free/1e9:.1f} GB  (need ~{c_need/1e9:.0f} GB for merged model)")
    print(f"  F: free {f_free/1e9:.1f} GB  (need ~{f_need/1e9:.1f} GB for GGUF)")

    problems = []
    if c_free < c_need:
        problems.append(
            f"C: only has {c_free/1e9:.1f} GB free — need ~{c_need/1e9:.0f} GB for merged weights."
        )
    if f_free < f_need:
        problems.append(
            f"F: only has {f_free/1e9:.1f} GB free — need ~{f_need/1e9:.1f} GB for GGUF."
        )

    if problems:
        print("\nERROR — not enough disk space:")
        for p in problems:
            print(f"  {p}")
        sys.exit(1)

    print("  Space OK.\n")


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------

def merge_adapter(adapter_name: str, model_key: str) -> Path:
    """Merge LoRA into base, save merged model. Returns path."""
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer

    adapter_path = Path(ADAPTER_BASE) / f"{adapter_name}-{model_key}"
    merged_path = Path(MERGED_BASE) / f"{adapter_name}-{model_key}"

    if not (adapter_path / "adapter_config.json").exists():
        print(f"ERROR: No trained adapter at {adapter_path}")
        print(f"Train it first: python scripts/system/hand_tune.py --adapter {adapter_name} --model {model_key}")
        sys.exit(1)

    print(f"Loading base model: {MODEL_BASES[model_key]}")
    print("(Loading in float16, CPU-offload if needed — this takes a few minutes for 7b)")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_BASES[model_key], trust_remote_code=True)

    # Load in float16 for merging (not 4-bit — we need full weights to merge)
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_BASES[model_key],
        torch_dtype=torch.float16,
        device_map="cpu",       # CPU merge is slow but safe on 6GB VRAM
        trust_remote_code=True,
    )

    print(f"Loading adapter: {adapter_path}")
    model = PeftModel.from_pretrained(model, str(adapter_path))

    print("Merging adapter weights...")
    model = model.merge_and_unload()

    merged_path.mkdir(parents=True, exist_ok=True)
    print(f"Saving merged model to: {merged_path}")
    model.save_pretrained(str(merged_path), safe_serialization=True)
    tokenizer.save_pretrained(str(merged_path))

    print(f"Merge complete: {merged_path}")
    return merged_path


def convert_to_gguf(merged_path: Path, adapter_name: str, model_key: str) -> Path:
    """Convert merged HF model to GGUF using llama.cpp."""
    gguf_dir = Path(GGUF_BASE) / f"{adapter_name}-{model_key}"
    gguf_dir.mkdir(parents=True, exist_ok=True)

    convert_script = Path(LLAMA_CPP_PATH) / "convert_hf_to_gguf.py"
    if not convert_script.exists():
        # Older llama.cpp versions use convert.py
        convert_script = Path(LLAMA_CPP_PATH) / "convert.py"

    if not convert_script.exists():
        print(f"ERROR: llama.cpp not found at {LLAMA_CPP_PATH}")
        print("Install it:")
        print("  git clone https://github.com/ggerganov/llama.cpp C:/tools/llama.cpp")
        print("  pip install -r C:/tools/llama.cpp/requirements.txt")
        print("Or set LLAMA_CPP_PATH env var to your llama.cpp directory.")
        sys.exit(1)

    gguf_f16_path = gguf_dir / f"{adapter_name}-{model_key}-f16.gguf"
    gguf_q4_path = gguf_dir / f"{adapter_name}-{model_key}-q4_k_m.gguf"

    print(f"\nConverting to GGUF (f16)...")
    result = subprocess.run(
        [sys.executable, str(convert_script), str(merged_path), "--outfile", str(gguf_f16_path), "--outtype", "f16"],
        check=True,
    )

    # Quantize to Q4_K_M — best size/quality tradeoff
    quantize_bin = Path(LLAMA_CPP_PATH) / "build" / "bin" / "llama-quantize"
    if not quantize_bin.exists():
        quantize_bin = Path(LLAMA_CPP_PATH) / "quantize"  # older path

    if quantize_bin.exists():
        print(f"Quantizing to Q4_K_M...")
        subprocess.run(
            [str(quantize_bin), str(gguf_f16_path), str(gguf_q4_path), "Q4_K_M"],
            check=True,
        )
        # Remove f16 after quantize to save space
        gguf_f16_path.unlink()
        print(f"GGUF saved: {gguf_q4_path}")
        return gguf_q4_path
    else:
        print("NOTE: llama-quantize binary not found — keeping f16 GGUF (larger file)")
        print(f"To quantize manually: {LLAMA_CPP_PATH}/build/bin/llama-quantize {gguf_f16_path} {gguf_q4_path} Q4_K_M")
        return gguf_f16_path


def write_modelfile(gguf_path: Path, adapter_name: str, model_key: str) -> Path:
    """Write an Ollama Modelfile and create the model."""
    system = ADAPTER_SYSTEM_PROMPTS[adapter_name]
    ollama_name = f"scbe-{adapter_name}-{model_key}"

    modelfile_path = gguf_path.parent / "Modelfile"
    modelfile_content = f"""FROM {gguf_path}

SYSTEM \"\"\"{system}\"\"\"

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.1
PARAMETER num_ctx 4096
"""

    modelfile_path.write_text(modelfile_content, encoding="utf-8")
    print(f"\nModelfile written: {modelfile_path}")

    print(f"Creating Ollama model: {ollama_name}")
    result = subprocess.run(
        ["ollama", "create", ollama_name, "-f", str(modelfile_path)],
        check=True,
    )

    print(f"\nModel ready. Test it:")
    print(f"  ollama run {ollama_name}")
    print(f"  ollama run {ollama_name} 'How do I set up a Stripe webhook?'")
    return modelfile_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Merge LoRA adapter and export to Ollama GGUF")
    parser.add_argument("--adapter", choices=["coder", "lawbot", "commerce"], required=True)
    parser.add_argument("--model", choices=["360m", "7b"], default="7b")
    parser.add_argument("--skip-merge", action="store_true", help="Skip merge step (merged model already exists)")
    parser.add_argument("--skip-convert", action="store_true", help="Skip GGUF conversion (GGUF already exists)")
    args = parser.parse_args()

    print(f"\n=== Merge + GGUF export: {args.adapter} ({args.model}) ===")

    if not args.skip_merge and not args.skip_convert:
        check_disk_space(args.model)

    merged_path = Path(MERGED_BASE) / f"{args.adapter}-{args.model}"
    gguf_dir = Path(GGUF_BASE) / f"{args.adapter}-{args.model}"
    gguf_q4_path = gguf_dir / f"{args.adapter}-{args.model}-q4_k_m.gguf"
    gguf_f16_path = gguf_dir / f"{args.adapter}-{args.model}-f16.gguf"

    # Step 1: Merge
    if not args.skip_merge:
        merged_path = merge_adapter(args.adapter, args.model)
    else:
        print(f"Skipping merge — using existing: {merged_path}")
        if not merged_path.exists():
            print("ERROR: --skip-merge specified but merged model not found")
            sys.exit(1)

    # Step 2: Convert to GGUF
    if not args.skip_convert:
        existing_gguf = gguf_q4_path if gguf_q4_path.exists() else (gguf_f16_path if gguf_f16_path.exists() else None)
        if existing_gguf:
            print(f"GGUF already exists: {existing_gguf} — skipping conversion")
            gguf_path = existing_gguf
        else:
            gguf_path = convert_to_gguf(merged_path, args.adapter, args.model)
    else:
        gguf_path = gguf_q4_path if gguf_q4_path.exists() else gguf_f16_path
        if not gguf_path.exists():
            print("ERROR: --skip-convert specified but GGUF not found")
            sys.exit(1)
        print(f"Using existing GGUF: {gguf_path}")

    # Step 3: Ollama Modelfile + create
    write_modelfile(gguf_path, args.adapter, args.model)

    # Step 4: Clean up temp merged model (C: space reclaimed)
    if not args.skip_merge and merged_path.exists():
        merged_size = sum(f.stat().st_size for f in merged_path.rglob("*") if f.is_file())
        print(f"\nCleaning up temp merged model ({merged_size/1e9:.1f} GB) from C: ...")
        shutil.rmtree(merged_path)
        print(f"Deleted: {merged_path}")
        import psutil
        drive = "C:\\"
        print(f"C: free after cleanup: {psutil.disk_usage(drive).free/1e9:.1f} GB")


if __name__ == "__main__":
    main()
