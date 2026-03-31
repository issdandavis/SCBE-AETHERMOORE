#!/usr/bin/env python3
"""Polly Chat — interactive chat with pump-oriented Polly.

Loads a trained Polly LoRA adapter and the pump aquifer,
then runs an interactive chat loop where every query gets:
1. Pump packet (tongue profile, null pattern, governance)
2. Aquifer retrieval (nearest bundles)
3. Stabilized system prompt (pre-state orientation)
4. Model generation (expression from oriented state)

Usage:
    python scripts/polly_chat.py
    python scripts/polly_chat.py --model issdandavis/scbe-polly-stacklite-v1
    python scripts/polly_chat.py --model ./local-lora-adapter
    python scripts/polly_chat.py --no-pump  # baseline mode, no orientation
"""

import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')
REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / 'src'))

from polly_pump.packet import sense, TONGUE_CODES, TONGUE_NAMES
from polly_pump.retriever import BundleRetriever, RetrievedBundle
from polly_pump.stabilizer import stabilize


def load_aquifer(path=None):
    """Load the pump aquifer from JSONL."""
    if path is None:
        path = REPO / 'artifacts' / 'pump_aquifer.jsonl'

    bundles = []
    with open(path, encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            bundles.append(RetrievedBundle(
                bundle_id=rec.get('bundle_id', ''),
                text=rec.get('text', ''),
                tongue_profile=rec.get('tongue_profile', [0]*6),
                canon=rec.get('canon', 'general'),
                emotion=rec.get('emotion', 'neutral'),
                governance=rec.get('governance', 'ALLOW'),
                null_pattern=rec.get('null_pattern', '######'),
                source_root=rec.get('source_root', ''),
                tags=rec.get('tags', []),
            ))
    return bundles


def build_system_prompt(user_text, retriever, use_pump=True):
    """Build the full system prompt with pump orientation."""
    if not use_pump:
        return (
            "You are Polly -- Polymnia Aetheris, Polydimensional Manifestation "
            "of Accumulated Wisdom and Occasional Sarcasm. You chronicle the "
            "Spiralverse and know the Six Sacred Tongues, the 14-layer "
            "architecture, and the lore of Avalon Academy."
        )

    # Sense
    packet = sense(user_text)

    # Locate + Lift
    bundles = retriever.retrieve(packet, top_k=3)

    # Compose
    prestate = stabilize(packet, bundles)

    # Add Polly personality on top of the prestate
    personality = (
        "You are Polly -- Polymnia Aetheris. Respond with warmth, accuracy, "
        "and your characteristic blend of wisdom and occasional sarcasm."
    )

    return f"{personality}\n\n{prestate}"


def main():
    parser = argparse.ArgumentParser(description='Chat with pump-oriented Polly')
    parser.add_argument('--model', default=None,
                        help='HF model repo or local path (omit for prompt-only mode)')
    parser.add_argument('--aquifer', default=None,
                        help='Path to pump aquifer JSONL')
    parser.add_argument('--no-pump', action='store_true',
                        help='Disable pump orientation (baseline mode)')
    parser.add_argument('--show-state', action='store_true',
                        help='Show pump state before each response')
    args = parser.parse_args()

    # Load aquifer
    if not args.no_pump:
        print("Loading pump aquifer...")
        aquifer = load_aquifer(args.aquifer)
        retriever = BundleRetriever(aquifer)
        print(f"  {len(aquifer)} bundles loaded")
    else:
        retriever = None
        print("Pump disabled (baseline mode)")

    # Load model if specified
    pipe = None
    if args.model:
        print(f"Loading model: {args.model}")
        try:
            from transformers import pipeline as hf_pipeline
            pipe = hf_pipeline(
                "text-generation",
                model=args.model,
                max_new_tokens=512,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
            )
            print("Model loaded")
        except Exception as e:
            print(f"Could not load model: {e}")
            print("Running in prompt-only mode (shows system prompt, no generation)")

    # Chat loop
    print(f"\n{'='*50}")
    print("POLLY CHAT" + (" (with pump)" if not args.no_pump else " (baseline)"))
    print(f"{'='*50}")
    print("Type your message. 'quit' to exit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input or user_input.lower() in ('quit', 'exit', 'q'):
            break

        # Build system prompt
        system_prompt = build_system_prompt(
            user_input, retriever, use_pump=not args.no_pump
        )

        if args.show_state:
            packet = sense(user_input)
            print(f"\n  [PUMP] {packet.summary_line()}")

        if pipe:
            # Generate with model
            prompt = (
                f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
                f"<|im_start|>user\n{user_input}<|im_end|>\n"
                f"<|im_start|>assistant\n"
            )
            output = pipe(prompt)[0]["generated_text"]
            response = output.split("<|im_start|>assistant\n")[-1].split("<|im_end|>")[0]
            print(f"\nPolly: {response.strip()}\n")
        else:
            # Prompt-only mode
            print(f"\n  [System prompt ({len(system_prompt)} chars)]")
            if args.show_state:
                print(f"  {system_prompt[:300]}...")
            print(f"  (No model loaded -- showing pump state only)\n")


if __name__ == '__main__':
    main()
