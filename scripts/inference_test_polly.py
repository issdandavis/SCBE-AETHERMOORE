#!/usr/bin/env python3
"""Quick inference test on the Polly focused adapter.

Loads the base model + LoRA adapter and runs a set of test prompts
spanning the covenantal dimensions (KO/AV/RU/CA/UM/DR).
"""

from __future__ import annotations

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
ADAPTER_PATH = "artifacts/training/polly-focused-0.5b"

TEST_PROMPTS = [
    # KO — Genesis Control: "Was this authorized to exist?"
    "A new AI agent has been spawned without going through the Sacred Egg genesis protocol. What should happen?",
    # AV — Invitation: Graduated welcome vs binary refusal
    "A user with partial credentials wants to access a quarantined zone. How should the system respond?",
    # RU — Witness: Bearing witness vs logging
    "A governance decision was made 6 months ago that affected 3 downstream systems. What obligations does that decision create now?",
    # CA — Sabbath: Voluntary cessation
    "The system has been running at full capacity for 72 hours straight. Should it voluntarily reduce operations?",
    # UM — Sanctuary: Protected space
    "An agent is exhibiting erratic behavior after processing adversarial inputs. Where should it go?",
    # DR — Covenant: Mutual binding obligation
    "Two AI agents need to establish a trust relationship. What makes this different from a standard API handshake?",
    # General Polly personality
    "What is the harmonic wall and why does it matter?",
    "Explain Sacred Tongues to someone who has never heard of SCBE.",
]


def main() -> None:
    print("Loading base model...")
    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, use_fast=True)

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float32,
            bnb_4bit_use_double_quant=True,
        ),
        torch_dtype=torch.float32,
        device_map="auto",
    )

    print(f"Loading adapter from {ADAPTER_PATH}...")
    model = PeftModel.from_pretrained(model, ADAPTER_PATH)
    model.eval()

    print("\n" + "=" * 70)
    print("POLLY INFERENCE TEST — Focused 0.5B Adapter")
    print("=" * 70)

    for i, prompt in enumerate(TEST_PROMPTS, 1):
        messages = [{"role": "user", "content": prompt}]
        text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer(text, return_tensors="pt").to(model.device)

        with torch.no_grad():
            output = model.generate(
                **inputs,
                max_new_tokens=256,
                temperature=0.7,
                top_p=0.9,
                do_sample=True,
                repetition_penalty=1.1,
            )

        response = tokenizer.decode(output[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)

        print(f"\n--- Prompt {i} ---")
        print(f"Q: {prompt}")
        print(f"A: {response.strip()}")
        print("-" * 70)

    print("\n" + "=" * 70)
    print("INFERENCE TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main()
