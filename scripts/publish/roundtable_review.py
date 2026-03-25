"""
Round Table Book Review System — Persistent Memory + Cross-Talk

Reads the book in chapter batches, deposits notes per chapter into a shared ledger,
then runs a round-table discussion where models read each other's notes.

Architecture:
  1. BATCH READ: Each model reads 3-5 chapters, deposits structured notes
  2. LEDGER: All notes stored in a JSONL file (persistent across runs)
  3. ROUND TABLE: Models receive OTHER models' notes and discuss/debate
  4. SYNTHESIS: Final summary combining all perspectives

Usage:
    python scripts/publish/roundtable_review.py --phase deposit --batch 1    # Read chapters 1-5
    python scripts/publish/roundtable_review.py --phase deposit --batch 2    # Read chapters 6-10
    python scripts/publish/roundtable_review.py --phase deposit --batch all  # Read all batches
    python scripts/publish/roundtable_review.py --phase roundtable           # Cross-talk discussion
    python scripts/publish/roundtable_review.py --phase synthesize           # Final summary
    python scripts/publish/roundtable_review.py --full                       # All phases
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime

REPO = Path(r"C:\Users\issda\SCBE-AETHERMOORE")
READER_DIR = REPO / "content" / "book" / "reader-edition"
LEDGER_PATH = REPO / "artifacts" / "book" / "roundtable_ledger.jsonl"
REPORT_DIR = REPO / "artifacts" / "book" / "roundtable-reports"

# Chapter batches for sequential reading
BATCHES = {
    1: ["ch01.md", "interlude-01-pollys-vigil.md", "ch02.md", "ch03.md", "ch04.md"],
    2: ["ch05.md", "interlude-06-jorren-records.md", "ch06.md", "ch07.md", "interlude-04-brams-report.md"],
    3: ["ch08.md", "interlude-09-tovak-hides.md", "ch09.md", "interlude-02-the-garden-before.md", "ch10.md"],
    4: ["interlude-03-sennas-morning.md", "ch11.md", "ch12.md", "ch13.md", "interlude-07-nadia-runs.md"],
    5: ["ch14.md", "ch15.md", "ch16.md", "ch16b-the-fizzlecress-incident.md"],
    6: ["ch17.md", "ch18.md", "ch19.md", "ch20.md", "interlude-10-arias-garden.md"],
    7: ["ch21.md", "ch21b-senna-after.md", "ch22.md", "ch23.md", "ch24.md"],
    8: [
        "interlude-08-the-pipe.md",
        "ch25.md",
        "interlude-05-alexanders-hold.md",
        "ch26.md",
        "ch27.md",
        "ch-rootlight.md",
    ],
}

MODELS = [
    ("meta-llama/Llama-3.3-70B-Instruct", "Llama-70B"),
    ("Qwen/Qwen2.5-72B-Instruct", "Qwen-72B"),
    ("google/gemma-3-27b-it", "Gemma-27B"),
]


def get_token():
    token = os.environ.get("HF_TOKEN", "")
    if not token:
        try:
            from dotenv import load_dotenv

            load_dotenv(str(REPO / "config" / "connector_oauth" / ".env.connector.oauth"))
            token = os.environ.get("HF_TOKEN", "")
        except ImportError:
            pass
    return token


def query_model(model_id, prompt, token, max_tokens=1500):
    from huggingface_hub import InferenceClient

    for attempt in range(3):
        try:
            client = InferenceClient(model=model_id, token=token)
            response = client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
            else:
                return f"ERROR: {e}"
    return None


def load_batch_text(batch_num):
    """Load chapter text for a batch, truncated to fit context."""
    files = BATCHES[batch_num]
    parts = []
    for fname in files:
        path = READER_DIR / fname
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            # Take first 40 lines of each chapter (enough for tone/voice/opening)
            excerpt = "".join(lines[:40]).strip()
            parts.append(f"--- {fname} ---\n{excerpt}\n")
    return "\n".join(parts)


def append_to_ledger(entry):
    """Append a note to the persistent JSONL ledger."""
    LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LEDGER_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def load_ledger():
    """Load all notes from the ledger."""
    if not LEDGER_PATH.exists():
        return []
    entries = []
    with open(LEDGER_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def phase_deposit(batch_num, token):
    """Phase 1: Models read a batch and deposit notes."""
    print(f"\n{'#'*60}")
    print(f"DEPOSIT PHASE — Batch {batch_num}")
    print(f"Chapters: {', '.join(BATCHES[batch_num])}")
    print("#" * 60)

    text = load_batch_text(batch_num)

    prompt = f"""You are reading "The Six Tongues Protocol" by Issac Davis, a portal fantasy novel (~135,000 words).
You are reading batch {batch_num} of 8. Deposit chapter-by-chapter notes.

For EACH chapter/interlude in this batch, write:
- CHAPTER: [filename]
- TONE: one word
- BEST_LINE: quote the single best line
- WORST_LINE: quote the weakest line (or "none")
- EMOTIONAL_PEAK: what moment hits hardest
- SENSORY_GAP: what sense is missing or weak
- PACING: too slow / just right / too fast
- THREAD_ADVANCED: which story threads move forward
- OPEN_QUESTION: one thing you want answered later
- SCORE: 1-10

Be specific. Quote actual text. These notes will be shared with other reviewers.

CHAPTERS:
{text}"""

    for model_id, name in MODELS:
        print(f"  [{name}] reading batch {batch_num}...", end=" ", flush=True)
        response = query_model(model_id, prompt, token, max_tokens=2000)
        if response.startswith("ERROR"):
            print("FAILED")
        else:
            print(f"OK ({len(response)} chars)")
            entry = {
                "timestamp": datetime.now().isoformat(),
                "phase": "deposit",
                "batch": batch_num,
                "model": name,
                "chapters": BATCHES[batch_num],
                "notes": response,
            }
            append_to_ledger(entry)
        time.sleep(2)


def phase_roundtable(token):
    """Phase 2: Models read each other's notes and discuss."""
    print(f"\n{'#'*60}")
    print("ROUND TABLE PHASE — Cross-Talk Discussion")
    print("#" * 60)

    ledger = load_ledger()
    deposits = [e for e in ledger if e["phase"] == "deposit"]

    if len(deposits) < 3:
        print("Need at least 3 deposit entries for round table. Run more batches first.")
        return

    # Build a summary of all notes by model
    notes_by_model = {}
    for entry in deposits:
        model = entry["model"]
        if model not in notes_by_model:
            notes_by_model[model] = []
        notes_by_model[model].append(f"Batch {entry['batch']}:\n{entry['notes'][:800]}")

    for model_id, name in MODELS:
        # Give this model everyone ELSE's notes
        other_notes = []
        for other_model, notes_list in notes_by_model.items():
            if other_model != name:
                other_notes.append(f"\n=== {other_model}'s NOTES ===\n" + "\n".join(notes_list[:3]))

        prompt = f"""You are on a book review round table for "The Six Tongues Protocol."
Other reviewers have deposited their chapter-by-chapter notes. Read their notes and respond.

{chr(10).join(other_notes)}

YOUR TASK:
1. Where do you AGREE with the other reviewers? Quote their observations you support.
2. Where do you DISAGREE? What did they miss or get wrong?
3. What patterns do you see across ALL the notes that no single reviewer mentioned?
4. What is the book's BIGGEST STRENGTH based on the collective notes?
5. What is the book's BIGGEST WEAKNESS based on the collective notes?
6. CONSENSUS RATING: Based on all notes combined, what score does the book deserve? (1-10)"""

        print(f"  [{name}] reviewing others' notes...", end=" ", flush=True)
        response = query_model(model_id, prompt, token, max_tokens=1500)
        if response.startswith("ERROR"):
            print("FAILED")
        else:
            print(f"OK ({len(response)} chars)")
            entry = {
                "timestamp": datetime.now().isoformat(),
                "phase": "roundtable",
                "model": name,
                "notes": response,
            }
            append_to_ledger(entry)
        time.sleep(2)


def phase_synthesize(token):
    """Phase 3: Final synthesis from all round table discussion."""
    print(f"\n{'#'*60}")
    print("SYNTHESIS PHASE — Final Verdict")
    print("#" * 60)

    ledger = load_ledger()
    roundtable = [e for e in ledger if e["phase"] == "roundtable"]

    if not roundtable:
        print("No round table entries. Run --phase roundtable first.")
        return

    all_discussion = "\n\n".join(
        [f"=== {e['model']} ===\n{e['notes'][:1000]}" for e in roundtable[-6:]]  # Last 6 entries
    )

    prompt = f"""You are the chair of a book review panel. Read the round table discussion below and produce a FINAL SYNTHESIS.

{all_discussion}

PRODUCE:
1. CONSENSUS SCORE (1-10) with justification
2. TOP 3 STRENGTHS (with quotes from the discussion)
3. TOP 3 WEAKNESSES (with quotes from the discussion)
4. PUBLICATION RECOMMENDATION: Ready / Needs revision / Not ready
5. ONE-SENTENCE REVIEW for the back cover
6. COMP TITLES the panel agrees on"""

    # Use the largest model for synthesis
    model_id, name = MODELS[0]
    print(f"  [{name}] synthesizing...", end=" ", flush=True)
    response = query_model(model_id, prompt, token, max_tokens=2000)
    if response.startswith("ERROR"):
        print("FAILED")
    else:
        print(f"OK")
        entry = {
            "timestamp": datetime.now().isoformat(),
            "phase": "synthesis",
            "model": name,
            "notes": response,
        }
        append_to_ledger(entry)

        # Save final report
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%dT%H%M%S")
        report_path = REPORT_DIR / f"{ts}_final_synthesis.md"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"# Round Table Final Synthesis\n\n")
            f.write(f"Generated: {ts}\n\n")
            f.write(response)
        print(f"\n  Report: {report_path}")

    print(f"\n  Ledger: {LEDGER_PATH}")
    print(f"  Total entries: {len(load_ledger())}")


def main():
    parser = argparse.ArgumentParser(description="Round Table Book Review System")
    parser.add_argument("--phase", choices=["deposit", "roundtable", "synthesize"], help="Which phase to run")
    parser.add_argument("--batch", default="1", help="Batch number (1-8) or 'all'")
    parser.add_argument("--full", action="store_true", help="Run all phases end-to-end")
    parser.add_argument("--clear-ledger", action="store_true", help="Clear the ledger and start fresh")

    args = parser.parse_args()
    token = get_token()

    if not token:
        print("ERROR: No HF_TOKEN found.")
        sys.exit(1)

    if args.clear_ledger:
        if LEDGER_PATH.exists():
            LEDGER_PATH.unlink()
        print("Ledger cleared.")
        if not args.phase and not args.full:
            return

    if args.full:
        # Run all batches then roundtable then synthesis
        for batch in range(1, 9):
            phase_deposit(batch, token)
        phase_roundtable(token)
        phase_synthesize(token)
        return

    if args.phase == "deposit":
        if args.batch == "all":
            for batch in range(1, 9):
                phase_deposit(batch, token)
        else:
            phase_deposit(int(args.batch), token)
    elif args.phase == "roundtable":
        phase_roundtable(token)
    elif args.phase == "synthesize":
        phase_synthesize(token)


if __name__ == "__main__":
    main()
