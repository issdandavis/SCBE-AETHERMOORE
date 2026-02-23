#!/usr/bin/env python3
"""
SCBE-AETHERMOORE Coder — Gradio Demo for HuggingFace Spaces.

Serves the fine-tuned Qwen2.5-Coder-1.5B model as an interactive chatbot
that understands the SCBE-AETHERMOORE architecture, governance, and code.

Deploy to HuggingFace Spaces:
    1. Create a new Space (Gradio SDK)
    2. Upload this file as app.py
    3. Set HF_MODEL_ID env var to your model repo
    4. The Space will auto-install requirements and launch

Local usage:
    pip install gradio transformers torch
    python scripts/gradio_demo.py

Author: Issac Davis
Date: 2026-02-22
Part of SCBE-AETHERMOORE (USPTO #63/961,403)
"""

from __future__ import annotations

import os

import gradio as gr

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

MODEL_ID = os.environ.get("HF_MODEL_ID", "issdandavis/scbe-aethermoore-coder-1.5b")
MAX_NEW_TOKENS = 1024
TEMPERATURE = 0.7
TOP_P = 0.9
REPETITION_PENALTY = 1.1

SYSTEM_PROMPT = (
    "You are SCBE-AETHERMOORE Coder, an AI assistant specialized in the "
    "SCBE-AETHERMOORE 14-layer AI safety and governance framework. You understand "
    "hyperbolic geometry (Poincare Ball containment), post-quantum cryptography "
    "(ML-KEM, ML-DSA, Spiral Seal), the Six Sacred Tongues (Kor'aelin, Avali, "
    "Runethic, Cassisivadan, Draumric, Umbroth), governance gates (FSGS, BFT "
    "consensus), cognitive polyhedra, and the full 14-layer pipeline. You can "
    "generate, explain, and refactor code following SCBE conventions. Answer "
    "accurately and precisely."
)

EXAMPLE_PROMPTS = [
    "Explain the 14-layer SCBE-AETHERMOORE pipeline in detail.",
    "Generate a new SCBE concept block that implements a rate limiter.",
    "What are the Six Sacred Tongues and their programming paradigm mappings?",
    "Refactor this function to follow Sacred Tongue boundaries:\ndef process(data): return transform(data)",
    "How does the Poincare Ball containment field enforce trust rings?",
    "Explain the Spiral Seal post-quantum encryption protocol.",
    "What is the Grand Unified Governance function G(xi, i, poly)?",
    "Write a SemanticAntivirus scanner for prompt injection detection.",
]

CSS = """
.gradio-container {
    max-width: 900px !important;
    margin: auto !important;
}
.disclaimer {
    font-size: 0.85em;
    color: #666;
    text-align: center;
    margin-top: 1em;
}
"""

# ---------------------------------------------------------------------------
# Model loading (lazy, cached)
# ---------------------------------------------------------------------------

_model = None
_tokenizer = None


def get_model_and_tokenizer():
    """Lazy-load model and tokenizer."""
    global _model, _tokenizer
    if _model is not None:
        return _model, _tokenizer

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    print(f"Loading model: {MODEL_ID}")

    _tokenizer = AutoTokenizer.from_pretrained(
        MODEL_ID,
        trust_remote_code=True,
    )

    # Detect device
    if torch.cuda.is_available():
        device_map = "auto"
        dtype = torch.float16
    else:
        device_map = "cpu"
        dtype = torch.float32

    _model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype=dtype,
        device_map=device_map,
        trust_remote_code=True,
    )

    print(f"Model loaded on {device_map} with dtype {dtype}")
    return _model, _tokenizer


def generate_response(message: str, history: list[dict]) -> str:
    """Generate a response given user message and chat history."""
    model, tokenizer = get_model_and_tokenizer()

    # Build messages list
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add history
    for turn in history:
        messages.append({"role": turn["role"], "content": turn["content"]})

    # Add current message
    messages.append({"role": "user", "content": message})

    # Apply chat template
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    import torch

    inputs = tokenizer(text, return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            repetition_penalty=REPETITION_PENALTY,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )

    # Decode only the new tokens
    response = tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[1]:],
        skip_special_tokens=True,
    )

    return response.strip()


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

def build_demo() -> gr.Blocks:
    """Build the Gradio demo interface."""
    with gr.Blocks(css=CSS, title="SCBE-AETHERMOORE Coder") as demo:
        gr.Markdown(
            "# SCBE-AETHERMOORE Coder\n"
            "### AI Architecture Assistant — 14-Layer Safety & Governance Framework\n\n"
            "Ask about the architecture, generate code following SCBE conventions, "
            "or explore the mathematical foundations."
        )

        chatbot = gr.ChatInterface(
            fn=generate_response,
            type="messages",
            examples=EXAMPLE_PROMPTS,
            cache_examples=False,
            title=None,
            description=None,
        )

        gr.Markdown(
            '<div class="disclaimer">'
            "Powered by Qwen2.5-Coder-1.5B fine-tuned on SCBE-AETHERMOORE | "
            "USPTO Patent #63/961,403 | "
            '<a href="https://github.com/issdandavis/SCBE-AETHERMOORE">GitHub</a>'
            "</div>"
        )

    return demo


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    demo = build_demo()
    demo.launch(
        server_name="0.0.0.0",
        server_port=int(os.environ.get("PORT", 7860)),
        share=False,
    )
