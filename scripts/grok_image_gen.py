#!/usr/bin/env python3
"""
SCBE Image Generator — Multi-backend router that actually works.

Backends (in priority order):
  1. Google Imagen 4.0 (Standard/Ultra) — best quality, needs GEMINI_API_KEY
  2. HuggingFace Inference API — FLUX.1-schnell remote, needs HF_TOKEN
  3. HuggingFace Z-Image Turbo — fast, needs HF_TOKEN
  4. Local SDXL Turbo — only if CUDA available with enough VRAM (8GB+)

Usage:
    python scripts/grok_image_gen.py --prompt "manhwa panel..." -o panel.png
    python scripts/grok_image_gen.py --prompt "..." --backend imagen-ultra -o hero.png
    python scripts/grok_image_gen.py --prompt "..." --backend hf -o panel.png
    python scripts/grok_image_gen.py --prompt "..." --reference ref.png --backend imagen -o panel.png
    python scripts/grok_image_gen.py --list-backends
    python scripts/grok_image_gen.py --check
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _imagen_config_kwargs(types_module, aspect: str, *, include_people: bool = True) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "number_of_images": 1,
        "aspect_ratio": aspect,
    }
    person_generation = getattr(types_module, "PersonGeneration", None)
    if include_people and person_generation is not None:
        kwargs["person_generation"] = getattr(person_generation, "ALLOW_ADULT", "ALLOW_ADULT")
    return kwargs


def _is_person_generation_error(exc: Exception) -> bool:
    text = str(exc)
    return "PersonGeneration" in text or "ALLOW_ALL" in text or "ALLOW_ADULT" in text


def _merge_prompt_avoidances(prompt: str, negative_prompt: str | None) -> str:
    if not negative_prompt:
        return prompt
    return f"{prompt} Do not include: {negative_prompt}."


# ── Backend: Google Imagen ──────────────────────────────────────
def gen_imagen(
    prompt: str,
    output: str,
    model: str = "imagen-4.0-generate-001",
    aspect: str = "3:4",
    reference: str | None = None,
    negative_prompt: str | None = None,
) -> str:
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        sys.exit("google-genai not installed: pip install google-genai")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("GEMINI_API_KEY not set. Get one at https://aistudio.google.com/apikey")

    client = genai.Client(api_key=api_key)

    if reference:
        sys.exit("Reference-image routing is not implemented for the Imagen backend in this script yet.")

    imagen_prompt = _merge_prompt_avoidances(prompt, negative_prompt)
    config_kwargs = _imagen_config_kwargs(types, aspect, include_people=True)
    config = types.GenerateImagesConfig(**config_kwargs)
    try:
        result = client.models.generate_images(model=model, prompt=imagen_prompt, config=config)
    except Exception as exc:
        if not _is_person_generation_error(exc):
            raise
        fallback_kwargs = _imagen_config_kwargs(types, aspect, include_people=False)
        fallback_config = types.GenerateImagesConfig(**fallback_kwargs)
        result = client.models.generate_images(model=model, prompt=imagen_prompt, config=fallback_config)

    if not result.generated_images:
        raise RuntimeError("Imagen returned no images — prompt may have been filtered")

    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    with open(output, "wb") as f:
        f.write(result.generated_images[0].image.image_bytes)
    return output


# ── Backend: HuggingFace Inference API ──────────────────────────
def gen_hf_inference(
    prompt: str,
    output: str,
    model: str = "black-forest-labs/FLUX.1-schnell",
    negative_prompt: str | None = None,
    width: int | None = None,
    height: int | None = None,
) -> str:
    import requests

    token = os.environ.get("HF_TOKEN")
    if not token:
        sys.exit("HF_TOKEN not set. Get one at https://huggingface.co/settings/tokens")

    url = f"https://router.huggingface.co/hf-inference/models/{model}"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"inputs": prompt}
    parameters = {}
    if negative_prompt:
        parameters["negative_prompt"] = negative_prompt
    if width:
        parameters["width"] = int(width)
    if height:
        parameters["height"] = int(height)
    if parameters:
        payload["parameters"] = parameters

    for attempt in range(3):
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        if resp.status_code == 200:
            os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
            with open(output, "wb") as f:
                f.write(resp.content)
            return output
        elif resp.status_code == 429:
            wait = 30 * (attempt + 1)
            print(f"  Rate limited, waiting {wait}s...")
            time.sleep(wait)
        elif resp.status_code == 503:
            print(f"  Model loading, waiting 30s...")
            time.sleep(30)
        else:
            raise RuntimeError(f"HF API error {resp.status_code}: {resp.text[:200]}")

    raise RuntimeError("HF API failed after 3 attempts")


# ── Backend: HuggingFace Z-Image Turbo (MCP) ───────────────────
def gen_zimage(
    prompt: str, output: str, negative_prompt: str | None = None, width: int | None = None, height: int | None = None
) -> str:
    """Uses the HF Z-Image Turbo endpoint if available."""
    import requests

    token = os.environ.get("HF_TOKEN")
    if not token:
        sys.exit("HF_TOKEN not set")

    url = "https://router.huggingface.co/hf-inference/models/stabilityai/sdxl-turbo"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"inputs": prompt}
    parameters = {}
    if negative_prompt:
        parameters["negative_prompt"] = negative_prompt
    if width:
        parameters["width"] = int(width)
    if height:
        parameters["height"] = int(height)
    if parameters:
        payload["parameters"] = parameters

    resp = requests.post(url, headers=headers, json=payload, timeout=120)
    if resp.status_code == 200:
        os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
        with open(output, "wb") as f:
            f.write(resp.content)
        return output
    raise RuntimeError(f"Z-Image error {resp.status_code}: {resp.text[:200]}")


# ── Backend detection ───────────────────────────────────────────
BACKENDS = {
    "imagen": {"name": "Google Imagen 4.0 Standard", "env": "GEMINI_API_KEY", "quality": "good", "speed": "fast"},
    "imagen-ultra": {"name": "Google Imagen 4.0 Ultra", "env": "GEMINI_API_KEY", "quality": "best", "speed": "slow"},
    "hf": {"name": "HuggingFace FLUX.1-schnell (remote)", "env": "HF_TOKEN", "quality": "good", "speed": "fast"},
    "zimage": {"name": "HuggingFace SDXL Turbo (remote)", "env": "HF_TOKEN", "quality": "ok", "speed": "fastest"},
}


def check_backends() -> dict[str, bool]:
    """Check which backends are available."""
    status = {}
    for key, info in BACKENDS.items():
        env_var = info["env"]
        has_key = bool(os.environ.get(env_var))
        status[key] = has_key
    return status


def pick_best_backend(preference: str | None = None) -> str:
    """Pick the best available backend."""
    if preference:
        if preference in BACKENDS:
            env_var = BACKENDS[preference]["env"]
            if os.environ.get(env_var):
                return preference
            else:
                sys.exit(f"Backend '{preference}' requires {env_var} to be set")
        else:
            sys.exit(f"Unknown backend: {preference}. Available: {', '.join(BACKENDS.keys())}")

    # Auto-pick best available
    priority = ["imagen-ultra", "imagen", "hf", "zimage"]
    for backend in priority:
        env_var = BACKENDS[backend]["env"]
        if os.environ.get(env_var):
            return backend

    sys.exit("No image generation backend available. Set GEMINI_API_KEY or HF_TOKEN.")


def generate(
    backend: str,
    prompt: str,
    output: str,
    aspect: str = "3:4",
    reference: str | None = None,
    negative_prompt: str | None = None,
    width: int | None = None,
    height: int | None = None,
) -> str:
    """Route to the correct backend."""
    if reference and backend not in {"imagen", "imagen-ultra"}:
        sys.exit(f"--reference is not implemented for backend '{backend}'")
    if backend == "imagen":
        return gen_imagen(
            prompt,
            output,
            model="imagen-4.0-generate-001",
            aspect=aspect,
            reference=reference,
            negative_prompt=negative_prompt,
        )
    elif backend == "imagen-ultra":
        return gen_imagen(
            prompt,
            output,
            model="imagen-4.0-ultra-generate-001",
            aspect=aspect,
            reference=reference,
            negative_prompt=negative_prompt,
        )
    elif backend == "hf":
        return gen_hf_inference(prompt, output, negative_prompt=negative_prompt, width=width, height=height)
    elif backend == "zimage":
        return gen_zimage(prompt, output, negative_prompt=negative_prompt, width=width, height=height)
    else:
        sys.exit(f"Unknown backend: {backend}")


def main():
    parser = argparse.ArgumentParser(description="SCBE Image Generator — multi-backend router")
    parser.add_argument("--prompt", help="Text prompt for generation")
    parser.add_argument("--output", "-o", default="artifacts/generated_image.png", help="Output file path")
    parser.add_argument("--backend", "-b", choices=list(BACKENDS.keys()), help="Force a specific backend")
    parser.add_argument("--aspect", default="3:4", help="Aspect ratio (default: 3:4)")
    parser.add_argument("--reference", "-r", help="Reference image path (Imagen only)")
    parser.add_argument("--check", action="store_true", help="Check which backends are available")
    parser.add_argument("--list-backends", action="store_true", help="List all backends")
    args = parser.parse_args()

    if args.check:
        status = check_backends()
        print("Backend availability:")
        for key, available in status.items():
            info = BACKENDS[key]
            mark = "OK" if available else "MISSING " + info["env"]
            color = "" if available else " <--"
            print(f"  {key:15s}  {info['name']:40s}  [{mark}]{color}")
        return

    if args.list_backends:
        print("Available backends:")
        for key, info in BACKENDS.items():
            print(f"  {key:15s}  {info['name']:40s}  quality={info['quality']}  speed={info['speed']}")
        return

    if not args.prompt:
        parser.print_help()
        return

    backend = pick_best_backend(args.backend)
    print(f"Using backend: {BACKENDS[backend]['name']}")

    t0 = time.time()
    output = generate(backend, args.prompt, args.output, aspect=args.aspect, reference=args.reference)
    elapsed = time.time() - t0
    print(f"Generated: {output} ({elapsed:.1f}s)")


if __name__ == "__main__":
    main()
