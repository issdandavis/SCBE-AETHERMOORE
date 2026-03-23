"""
Automated Test Reader Panel for The Six Tongues Protocol.

Sends book excerpts to multiple HuggingFace LLM models for review.
Scales reader count without overloading local compute (all inference is remote).

Usage:
    python scripts/publish/test_readers.py                    # Default: 3 models, kiss scene
    python scripts/publish/test_readers.py --scene opening    # Test a specific scene
    python scripts/publish/test_readers.py --scene all        # Test all scenes
    python scripts/publish/test_readers.py --readers 5        # Scale up reader count
    python scripts/publish/test_readers.py --list-scenes      # Show available scenes
    python scripts/publish/test_readers.py --list-models      # Show available models
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime

# ── Config ────────────────────────────────────────────────────
REPO = Path(r"C:\Users\issda\SCBE-AETHERMOORE")
READER_DIR = REPO / "content" / "book" / "reader-edition"
OUTPUT_DIR = REPO / "artifacts" / "book" / "test-reader-reports"

# Free HF Inference API models (no local compute, all remote)
MODELS = [
    # Tier 1: Large (best quality, may have queue)
    ("meta-llama/Llama-3.3-70B-Instruct", "Llama-70B", "large"),
    ("Qwen/Qwen2.5-72B-Instruct", "Qwen-72B", "large"),
    ("google/gemma-3-27b-it", "Gemma-27B", "medium"),
    # Tier 2: Medium (good quality, faster)
    ("meta-llama/Llama-3.1-8B-Instruct", "Llama-8B", "small"),
    ("Qwen/Qwen2.5-7B-Instruct", "Qwen-7B", "small"),
    ("google/gemma-3-4b-it", "Gemma-4B", "small"),
    # Tier 3: Small (fast, good for volume testing)
    ("microsoft/Phi-3.5-mini-instruct", "Phi-3.5", "small"),
]

# Scene definitions: (file, start_line, end_line, description)
SCENES = {
    "opening": {
        "file": "ch01.md",
        "start": 0, "end": 60,
        "desc": "Chapter 1: Marcus at 3AM, the warm breeze, Bryce's photo, the white void, Polly appears",
    },
    "polly_vigil": {
        "file": "interlude-01-pollys-vigil.md",
        "start": 0, "end": 50,
        "desc": "Polly watches Marcus sleep, remembers Izack, the sleep-caw",
    },
    "swarm": {
        "file": "ch04.md",
        "start": 120, "end": 200,
        "desc": "The routing basement, SOS mesh, Bram with wrench, HELP packets",
    },
    "kiss": {
        "file": "ch13.md",
        "start": 370, "end": 500,
        "desc": "Senna's breakdown, the cuff off, circles on her back, the confession, the kiss",
    },
    "fizzle": {
        "file": "ch16b-the-fizzlecress-incident.md",
        "start": 0, "end": 60,
        "desc": "Drunk on a roof, missing Earth, Dax calls him out about Senna",
    },
    "fizzle_globe": {
        "file": "ch16b-the-fizzlecress-incident.md",
        "start": 110, "end": 200,
        "desc": "Waking up 4 inches tall in Fizzle's globe, Coff-three, living coffee",
    },
    "memory_tithe": {
        "file": "ch19.md",
        "start": 120, "end": 180,
        "desc": "The forest takes grandmother's kitchen, sesame oil fading",
    },
    "moonflower": {
        "file": "ch11.md",
        "start": 180, "end": 220,
        "desc": "Tovak's moonflower spirit, bass-drum hit, the Void Seed aftermath",
    },
    "rootlight": {
        "file": "ch-rootlight.md",
        "start": 210, "end": 300,
        "desc": "Festival food, blue soup, grief pastry, Senna laughing, the walk home",
    },
    "wardrobe": {
        "file": "ch12.md",
        "start": 398, "end": 420,
        "desc": "Marcus gets Aethermoor clothes after the Binding, keeps the hoodie",
    },
    "age_joke": {
        "file": "ch14.md",
        "start": 204, "end": 260,
        "desc": "Marcus asks Senna's age at Ravencrest garden, she's 146, printing press joke",
    },
    "senna_after": {
        "file": "ch21b-senna-after.md",
        "start": 0, "end": 200,
        "desc": "Senna's perspective lying on Marcus's chest, implicit magic, two heartbeats",
    },
    "pregnancy": {
        "file": "ch-rootlight.md",
        "start": 377, "end": 460,
        "desc": "Pregnancy announcement under World Tree, three heartbeats, tree blooms",
    },
}

# Review prompts by type
PROMPTS = {
    "sensory": """You are a book reviewer focused on SENSORY WRITING. Read this scene and rate:
1. TASTE — Can you taste anything? What? (1-10)
2. SMELL — Does the scene have its own scent, not borrowed from another scene? (1-10)
3. SOUND — Can you hear the scene? Breathing, footsteps, silence? (1-10)
4. TOUCH — Can you feel textures, temperatures, contact? (1-10)
5. What single sensory detail is BEST? Quote it.
6. What sensory detail is MISSING that should be there?
Overall sensory score 1-10.""",

    "emotional": """You are a book reviewer focused on EMOTIONAL AUTHENTICITY. Read this scene and rate:
1. Do the characters feel like real people? (1-10)
2. Does the scene TRY TOO HARD to be emotional, or does it let the moment breathe? (1-10, where 10 = perfect restraint)
3. Is there a line that OVER-EXPLAINS what the reader already felt? Quote it.
4. Is there a line that is PERFECT — shows not tells? Quote it.
5. Would a real person behave this way in this situation? (1-10)
Overall emotional authenticity 1-10.""",

    "general": """You are a professional book reviewer. Read this scene from a portal fantasy novel and rate:
1. Prose quality (1-10)
2. Character voice distinctiveness (1-10)
3. Would you keep reading? (yes/no)
4. One sentence review.
5. Best line. Worst line.
Overall rating 1-10.""",
}


def get_token():
    """Get HF token from environment."""
    token = os.environ.get('HF_TOKEN', '')
    if not token:
        try:
            from dotenv import load_dotenv
            load_dotenv(str(REPO / 'config' / 'connector_oauth' / '.env.connector.oauth'))
            token = os.environ.get('HF_TOKEN', '')
        except ImportError:
            pass
    return token


def load_scene(scene_name):
    """Load a scene excerpt from the chapter files."""
    if scene_name not in SCENES:
        print(f"Unknown scene: {scene_name}")
        print(f"Available: {', '.join(SCENES.keys())}")
        sys.exit(1)

    cfg = SCENES[scene_name]
    path = READER_DIR / cfg["file"]
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    excerpt = ''.join(lines[cfg["start"]:cfg["end"]]).strip()
    return excerpt, cfg["desc"]


def query_model(model_id, prompt, token, max_retries=2):
    """Query a single HF model with retry logic."""
    from huggingface_hub import InferenceClient

    for attempt in range(max_retries + 1):
        try:
            client = InferenceClient(model=model_id, token=token)
            response = client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1200,
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            if attempt < max_retries:
                wait = 5 * (attempt + 1)
                print(f"    Retry in {wait}s... ({e})")
                time.sleep(wait)
            else:
                return f"ERROR: {e}"


def run_panel(scene_name, prompt_type, num_readers, token):
    """Run a panel of readers on a single scene."""
    excerpt, desc = load_scene(scene_name)
    prompt_template = PROMPTS.get(prompt_type, PROMPTS["general"])

    full_prompt = f"""{prompt_template}

CONTEXT: This is from "The Six Tongues Protocol" — a portal fantasy where a burnt-out security engineer falls into a world where magic is cryptographic protocol architecture. ~132,000 words.

SCENE ({desc}):
{excerpt}"""

    # Select models based on reader count
    selected = MODELS[:min(num_readers, len(MODELS))]

    results = []
    for model_id, name, tier in selected:
        print(f"  [{name}] querying...", end=" ", flush=True)
        response = query_model(model_id, full_prompt, token)
        if response.startswith("ERROR"):
            print(f"FAILED")
        else:
            print(f"OK ({len(response)} chars)")
        results.append({
            "model": name,
            "model_id": model_id,
            "tier": tier,
            "response": response,
        })
        # Small delay to avoid rate limits
        time.sleep(1)

    return results


def save_report(scene_name, prompt_type, results):
    """Save results to a timestamped report."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    filename = f"{timestamp}_{scene_name}_{prompt_type}.json"
    path = OUTPUT_DIR / filename

    report = {
        "timestamp": timestamp,
        "scene": scene_name,
        "prompt_type": prompt_type,
        "scene_desc": SCENES[scene_name]["desc"],
        "num_readers": len(results),
        "results": results,
    }

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    return path


def print_summary(results):
    """Print a quick summary table."""
    print(f"\n{'='*60}")
    print("PANEL SUMMARY")
    print('='*60)
    for r in results:
        status = "OK" if not r["response"].startswith("ERROR") else "FAIL"
        # Try to extract a rating from the response
        rating = "?"
        for line in r["response"].split('\n'):
            if 'overall' in line.lower() and '/10' in line.lower():
                # Extract number before /10
                import re
                match = re.search(r'(\d+\.?\d*)\s*/\s*10', line)
                if match:
                    rating = match.group(1)
                    break
            elif line.strip().startswith(('Overall', 'Rating', 'Score')):
                match = re.search(r'(\d+\.?\d*)', line)
                if match:
                    rating = match.group(1)
                    break
        print(f"  [{r['model']:12s}] [{r['tier']:6s}] {status:4s}  Rating: {rating}/10")


def main():
    parser = argparse.ArgumentParser(description="Automated Test Reader Panel")
    parser.add_argument("--scene", default="kiss",
                        help="Scene to test (or 'all')")
    parser.add_argument("--prompt", default="emotional",
                        choices=["sensory", "emotional", "general"],
                        help="Review prompt type")
    parser.add_argument("--readers", type=int, default=3,
                        help="Number of reader models (1-7)")
    parser.add_argument("--list-scenes", action="store_true",
                        help="List available scenes")
    parser.add_argument("--list-models", action="store_true",
                        help="List available models")

    args = parser.parse_args()

    if args.list_scenes:
        print("\nAvailable scenes:")
        for name, cfg in SCENES.items():
            print(f"  {name:20s} — {cfg['desc']}")
        return

    if args.list_models:
        print("\nAvailable models:")
        for model_id, name, tier in MODELS:
            print(f"  {name:12s} [{tier:6s}]  {model_id}")
        return

    token = get_token()
    if not token:
        print("ERROR: No HF_TOKEN found. Set HF_TOKEN environment variable.")
        sys.exit(1)

    scenes_to_test = list(SCENES.keys()) if args.scene == "all" else [args.scene]

    for scene in scenes_to_test:
        print(f"\n{'#'*60}")
        print(f"SCENE: {scene} ({SCENES[scene]['desc']})")
        print(f"PROMPT: {args.prompt} | READERS: {args.readers}")
        print('#'*60)

        results = run_panel(scene, args.prompt, args.readers, token)
        report_path = save_report(scene, args.prompt, results)
        print_summary(results)
        print(f"\nReport saved: {report_path}")


if __name__ == "__main__":
    main()
