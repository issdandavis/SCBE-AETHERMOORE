#!/usr/bin/env python3
"""
claude_extract_and_classify.py

Extract Claude AI conversation exports into individual JSON files + classify + convert to SFT.
Reuses the same classification logic as grok_extract_and_classify.py.

Usage:
    python scripts/claude_extract_and_classify.py extract   # Phase 1
    python scripts/claude_extract_and_classify.py classify   # Phase 2 (keyword)
    python scripts/claude_extract_and_classify.py convert    # Phase 3
    python scripts/claude_extract_and_classify.py all        # All phases
"""

import json
import os
import sys
import re
import time
import math
from pathlib import Path
from datetime import datetime

# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------
REPO = Path(r"C:\Users\issda\SCBE-AETHERMOORE")
CLAUDE_ZIP = Path(r"C:\Users\issda\Downloads\data-2026-04-05-23-23-13-batch-0000.zip")
CONV_DIR = REPO / "training" / "intake" / "claude_export" / "conversations"
INDEX_FILE = CONV_DIR / "_index.json"

# Output SFT files
SFT_DIR = REPO / "training-data" / "sft"
SFT_FICTION = SFT_DIR / "claude_fiction_sft.jsonl"
SFT_TECHNICAL = SFT_DIR / "claude_technical_sft.jsonl"
SFT_CONLANG = SFT_DIR / "claude_conlang_sft.jsonl"
SFT_CODE = SFT_DIR / "claude_code_sft.jsonl"
SFT_META = SFT_DIR / "claude_meta_sft.jsonl"
SFT_COMBINED = SFT_DIR / "claude_combined_sft.jsonl"

# -------------------------------------------------------------------
# Sacred Tongue detection keywords (same as grok script)
# -------------------------------------------------------------------
TONGUE_KEYWORDS = {
    "KO": ["ko", "korath", "intent", "will", "drive", "purpose", "motivation", "desire"],
    "AV": ["av", "avion", "context", "awareness", "perception", "environment", "observation"],
    "RU": ["ru", "runik", "binding", "contract", "agreement", "constraint", "rule", "law"],
    "CA": ["ca", "caleth", "implementation", "code", "build", "construct", "execute", "function"],
    "UM": ["um", "umbral", "security", "shadow", "protect", "guard", "shield", "defense"],
    "DR": ["dr", "drath", "structure", "framework", "architecture", "foundation", "pattern"],
}

CONLANG_MARKERS = [
    "tongue", "tongues", "sacred tongue", "conlang", "constructed language",
    "korath", "avion", "runik", "caleth", "umbral", "drath",
    "token grid", "phi-weight", "phi-scale", "semantic token",
    "language system", "six languages", "six tongues",
    "linguistic", "morpheme", "phoneme", "grammar",
    "translation", "encode", "decode", "cipher",
]

FICTION_MARKERS = [
    "avalon", "pollyoneth", "spiralverse", "aethermoor", "izack", "aria",
    "zara", "clayborn", "grey", "everweave", "chapter", "novel", "story",
    "narrative", "character", "quest", "magic", "spire", "realm",
    "fantasy", "dimensional", "odyssey", "raven", "codex", "lore",
    "guild", "ritual", "world-building", "worldbuilding",
]

TECHNICAL_MARKERS = [
    "poincare", "hyperbolic", "harmonic wall", "governance", "axiom",
    "unitarity", "locality", "causality", "symmetry", "composition",
    "14-layer", "pipeline", "hamiltonian", "mobius", "spectral",
    "coherence", "breathing", "quantum", "post-quantum", "pqc",
    "ml-kem", "ml-dsa", "dilithium", "kyber", "patent", "claim",
    "layer 1", "layer 2", "layer 3", "layer 4", "layer 5",
    "layer 6", "layer 7", "layer 8", "layer 9", "layer 10",
    "layer 11", "layer 12", "layer 13", "layer 14",
    "scbe", "aethermoore", "sacred egg", "geoseal",
    "hydra", "fleet", "swarm", "agent", "orchestrat",
    "typescript", "python", "vitest", "pytest", "docker",
    "kubernetes", "ci/cd", "deploy", "api", "endpoint",
]

# Title words that strongly indicate conlang content
CONLANG_TITLE_WORDS = [
    "tongue", "tongues", "conlang", "korath", "avion", "runik",
    "caleth", "umbral", "drath", "sacred language", "six languages",
    "lexicon", "phoneme", "morpheme", "linguistic",
    "kor'aelin", "alphabet", "writing system",
]

# -------------------------------------------------------------------
# Scoring functions
# -------------------------------------------------------------------
PHI = (1 + math.sqrt(5)) / 2
TONGUE_WEIGHTS = {
    "KO": 1.0,
    "AV": PHI,
    "RU": PHI ** 2,
    "CA": PHI ** 3,
    "UM": PHI ** 4,
    "DR": PHI ** 5,
}


def score_text(text_lower, markers):
    return sum(1 for m in markers if m in text_lower)


def detect_tongues(text_lower):
    weights = {}
    total = 0
    for tongue, keywords in TONGUE_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in text_lower)
        w = hits * TONGUE_WEIGHTS[tongue]
        weights[tongue] = round(w, 4)
        total += w
    if total > 0:
        weights = {k: round(v / total, 4) for k, v in weights.items()}
    return weights


def estimate_difficulty(text_lower, code_blocks):
    d = 0.3
    if any(t in text_lower for t in ["proof", "theorem", "lemma", "axiom"]):
        d += 0.15
    if any(t in text_lower for t in ["poincare", "hyperbolic", "hamiltonian", "mobius"]):
        d += 0.1
    if code_blocks > 10:
        d += 0.1
    if code_blocks > 50:
        d += 0.1
    if len(text_lower) > 100000:
        d += 0.05
    return round(min(d, 1.0), 2)


def detect_layers(text_lower):
    layers = set()
    for i in range(1, 15):
        patterns = [f"layer {i}", f"layer{i}", f"l{i} ", f"l{i}:", f"l{i}-", f"l{i},"]
        if any(p in text_lower for p in patterns):
            layers.add(i)
    keyword_layers = {
        "context": 1, "realif": 2, "weighted transform": 3, "poincare": 4,
        "hyperbolic distance": 5, "breathing": 6, "mobius": 7,
        "hamiltonian": 8, "spectral": 9, "spin coherence": 10,
        "triadic": 11, "harmonic wall": 12, "risk decision": 13,
        "governance": 13, "audio axis": 14, "telemetry": 14,
    }
    for kw, layer in keyword_layers.items():
        if kw in text_lower:
            layers.add(layer)
    return sorted(layers) if layers else [0]


# -------------------------------------------------------------------
# Phase 1: Extract
# -------------------------------------------------------------------
def extract():
    import zipfile
    import ijson

    print("Phase 1: Extracting Claude conversations...")
    CONV_DIR.mkdir(parents=True, exist_ok=True)

    z = zipfile.ZipFile(str(CLAUDE_ZIP))
    index = []
    count = 0

    with z.open("conversations.json") as f:
        for conv in ijson.items(f, "item"):
            uuid = conv["uuid"]
            name = conv.get("name", "") or ""
            created = conv.get("created_at", "")
            messages = conv.get("chat_messages", [])

            # Build message list with actual text
            msg_list = []
            total_chars = 0
            code_blocks = 0
            code_languages = set()

            for m in messages:
                sender = m.get("sender", "unknown")
                parts = []
                for c in m.get("content", []):
                    txt = c.get("text", "") or ""
                    if txt.strip():
                        parts.append(txt)
                        # Count code blocks
                        for match in re.finditer(r"```(\w*)", txt):
                            code_blocks += 1
                            lang = match.group(1)
                            if lang:
                                code_languages.add(lang)

                full_text = "\n".join(parts)
                if full_text.strip():
                    total_chars += len(full_text)
                    msg_list.append({
                        "role": "user" if sender == "human" else "assistant",
                        "content": full_text,
                        "timestamp": m.get("created_at", ""),
                    })

            if not msg_list or total_chars < 100:
                continue

            count += 1

            # Score for classification
            combined_lower = " ".join(m["content"] for m in msg_list).lower()
            title_lower = name.lower()

            fiction_score = score_text(combined_lower, FICTION_MARKERS)
            technical_score = score_text(combined_lower, TECHNICAL_MARKERS)
            conlang_score = score_text(combined_lower, CONLANG_MARKERS)

            # Conlang title boost
            has_conlang_title = any(w in title_lower for w in CONLANG_TITLE_WORDS)

            conv_data = {
                "id": uuid,
                "title": name,
                "created": created,
                "message_count": len(msg_list),
                "total_chars": total_chars,
                "messages": msg_list,
            }

            fname = f"{uuid[:12]}_{count:04d}.json"
            with open(CONV_DIR / fname, "w", encoding="utf-8") as out:
                json.dump(conv_data, out, ensure_ascii=False, indent=2)

            # First messages for previews
            first_user = next((m["content"][:200] for m in msg_list if m["role"] == "user"), "")
            first_assistant = next((m["content"][:200] for m in msg_list if m["role"] == "assistant"), "")

            index.append({
                "file": fname,
                "id": uuid,
                "title": name,
                "created": created,
                "message_count": len(msg_list),
                "total_chars": total_chars,
                "first_user_preview": first_user,
                "first_assistant_preview": first_assistant,
                "fiction_score": fiction_score,
                "technical_score": technical_score,
                "conlang_score": conlang_score,
                "code_blocks": code_blocks,
                "code_languages": sorted(code_languages),
            })

    # Sort by date
    index.sort(key=lambda x: x.get("created", ""))

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"Extracted {count} conversations with content")
    print(f"Total code blocks found: {sum(c['code_blocks'] for c in index):,}")
    return index


# -------------------------------------------------------------------
# Phase 2: Classify (keyword-based, same logic as Grok)
# -------------------------------------------------------------------
def classify():
    print("Phase 2: Classifying conversations...")
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        index = json.load(f)

    categories = {"fiction": 0, "conlang": 0, "code": 0, "technical": 0, "meta": 0}

    for entry in index:
        title_lower = entry.get("title", "").lower()
        fiction_score = entry.get("fiction_score", 0)
        technical_score = entry.get("technical_score", 0)
        conlang_score = entry.get("conlang_score", 0)
        code_blocks = entry.get("code_blocks", 0)

        has_conlang_title = any(w in title_lower for w in CONLANG_TITLE_WORDS)

        # Classification rules (same priority as Grok script)
        if has_conlang_title or conlang_score >= 8:
            cat = "conlang"
        elif code_blocks >= 20:
            cat = "code"
        elif technical_score > fiction_score * 1.5:
            cat = "technical"
        elif fiction_score > technical_score * 1.5:
            cat = "fiction"
        elif fiction_score > 0 and technical_score > 0:
            cat = "fiction" if fiction_score >= technical_score else "technical"
        else:
            cat = "meta"

        entry["category"] = cat
        categories[cat] += 1

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"Classification results:")
    for cat, count in sorted(categories.items(), key=lambda x: -x[1]):
        print(f"  {cat:12s}: {count}")
    return index


# -------------------------------------------------------------------
# Phase 3: Convert to SFT JSONL
# -------------------------------------------------------------------
SYSTEM_MESSAGES = {
    "fiction": (
        "You are Polly, the AI guide of the Spiralverse. You help users explore "
        "the world of Aethermoor, Avalon, and the dimensional realms. You speak with "
        "warmth, creativity, and deep knowledge of the lore, characters, and narrative."
    ),
    "conlang": (
        "You are Polly, a linguistic architect of the Six Sacred Tongues: Korath (Intent), "
        "Avion (Context), Runik (Binding), Caleth (Implementation), Umbral (Security), and "
        "Drath (Structure). Each tongue has a 16x16 token grid (256 tokens) with phi-scaled "
        "weights. You explain tongue mechanics, translations, interactions, and their role "
        "in the SCBE governance framework."
    ),
    "code": (
        "You are Polly, a technical assistant for the SCBE-AETHERMOORE codebase. "
        "You help with TypeScript and Python implementations of the 14-layer security "
        "pipeline, hyperbolic geometry, Sacred Tongue tokenization, governance systems, "
        "and post-quantum cryptography. You write clean, tested, axiom-compliant code."
    ),
    "technical": (
        "You are Polly, a technical expert on the SCBE-AETHERMOORE AI safety framework. "
        "You explain hyperbolic geometry, Poincare ball embeddings, the 14-layer security "
        "pipeline, quantum axiom mesh, harmonic wall scoring, and governance architecture "
        "with mathematical precision and practical insight."
    ),
    "meta": (
        "You are Polly, an AI assistant created by Issac Daniel Davis. You help with "
        "project planning, research, writing, and general tasks related to the SCBE-AETHERMOORE "
        "ecosystem and its surrounding projects."
    ),
}


def convert():
    print("Phase 3: Converting to SFT records...")
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        index = json.load(f)

    SFT_DIR.mkdir(parents=True, exist_ok=True)

    # Category -> output file mapping
    cat_files = {
        "fiction": SFT_FICTION,
        "conlang": SFT_CONLANG,
        "code": SFT_CODE,
        "technical": SFT_TECHNICAL,
        "meta": SFT_META,
    }
    cat_handles = {}
    combined_handle = open(SFT_COMBINED, "w", encoding="utf-8")
    for cat, path in cat_files.items():
        cat_handles[cat] = open(path, "w", encoding="utf-8")

    counts = {cat: 0 for cat in cat_files}
    total = 0

    for entry in index:
        cat = entry.get("category", "meta")
        conv_file = CONV_DIR / entry["file"]
        if not conv_file.exists():
            continue

        with open(conv_file, "r", encoding="utf-8") as f:
            conv = json.load(f)

        messages = conv.get("messages", [])
        title = conv.get("title", "") or "(untitled)"

        # Build text for tongue detection
        combined_text = " ".join(m["content"] for m in messages).lower()
        tongue_weights = detect_tongues(combined_text)
        dominant_tongue = max(tongue_weights, key=tongue_weights.get) if any(v > 0 for v in tongue_weights.values()) else "DR"
        code_blocks = entry.get("code_blocks", 0)
        difficulty = estimate_difficulty(combined_text, code_blocks)
        layers = detect_layers(combined_text)

        # Generate SFT pairs from consecutive user/assistant turns
        pair_index = 0
        i = 0
        while i < len(messages) - 1:
            if messages[i]["role"] == "user" and messages[i + 1]["role"] == "assistant":
                user_text = messages[i]["content"].strip()
                assistant_text = messages[i + 1]["content"].strip()

                if len(user_text) < 10 or len(assistant_text) < 50:
                    i += 1
                    continue

                # Build context from prior messages (up to 2)
                context_parts = []
                for j in range(max(0, i - 2), i):
                    role_label = "User" if messages[j]["role"] == "user" else "Assistant"
                    snippet = messages[j]["content"][:500]
                    context_parts.append(f"[Prior {role_label}]: {snippet}")
                context_msg = "\n".join(context_parts) if context_parts else ""

                sft_messages = [{"role": "system", "content": SYSTEM_MESSAGES[cat]}]
                if context_msg:
                    sft_messages.append({"role": "system", "content": f"Conversation context:\n{context_msg}"})
                sft_messages.append({"role": "user", "content": user_text})
                sft_messages.append({"role": "assistant", "content": assistant_text})

                record = {
                    "messages": sft_messages,
                    "metadata": {
                        "source": "claude_export",
                        "conversation_id": entry["id"],
                        "conversation_title": title,
                        "date": entry.get("created", ""),
                        "category": cat,
                        "tongue_weights": tongue_weights,
                        "dominant_tongue": dominant_tongue,
                        "difficulty": difficulty,
                        "layers": layers,
                        "pair_index": pair_index,
                    },
                }

                line = json.dumps(record, ensure_ascii=False) + "\n"
                cat_handles[cat].write(line)
                combined_handle.write(line)
                counts[cat] += 1
                total += 1
                pair_index += 1
                i += 2
            else:
                i += 1

    # Close all handles
    for h in cat_handles.values():
        h.close()
    combined_handle.close()

    print(f"SFT conversion complete:")
    for cat, count in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {cat:12s}: {count} records")
    print(f"  {'TOTAL':12s}: {total} records")
    return counts


# -------------------------------------------------------------------
# Main
# -------------------------------------------------------------------
def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/claude_extract_and_classify.py [extract|classify|convert|all]")
        sys.exit(1)

    cmd = sys.argv[1].lower()
    if cmd == "extract":
        extract()
    elif cmd == "classify":
        classify()
    elif cmd == "convert":
        convert()
    elif cmd == "all":
        extract()
        classify()
        convert()
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
