#!/usr/bin/env python3
"""Extract, classify, and convert Claude export to SFT training data.

Mirrors the Grok pipeline (grok_extract_and_classify.py) but adapted
for Claude's export format.

Usage:
    python scripts/claude_export_extract_and_classify.py extract
    python scripts/claude_export_extract_and_classify.py classify
    python scripts/claude_export_extract_and_classify.py convert
    python scripts/claude_export_extract_and_classify.py all
"""

from __future__ import annotations

import json
import time
from pathlib import Path

# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------
REPO = Path(__file__).resolve().parent.parent
CLAUDE_JSON = REPO / "training" / "intake" / "claude_export" / "conversations.json"
CONV_DIR = REPO / "training" / "intake" / "claude_export" / "conversations"
INDEX_FILE = CONV_DIR / "_index.json"
CLASSIFIED_FILE = CONV_DIR / "_classified.json"

# Output SFT files
SFT_DIR = REPO / "training-data" / "sft"
SFT_FICTION = SFT_DIR / "claude_export_fiction_sft.jsonl"
SFT_TECHNICAL = SFT_DIR / "claude_export_technical_sft.jsonl"
SFT_CONLANG = SFT_DIR / "claude_export_conlang_sft.jsonl"
SFT_META = SFT_DIR / "claude_export_meta_sft.jsonl"
SFT_COMBINED = SFT_DIR / "claude_export_combined_sft.jsonl"

# -------------------------------------------------------------------
# Sacred Tongue detection keywords
# -------------------------------------------------------------------
TONGUE_KEYWORDS = {
    "KO": ["kor'aelin", "korath", "intent", "will", "drive", "purpose", "motivation", "desire", "command"],
    "AV": ["avali", "avion", "context", "awareness", "wisdom", "knowledge", "perception", "observation", "sanskrit"],
    "RU": ["runethic", "runik", "binding", "contract", "governance", "constraint", "rule", "law", "russian"],
    "CA": ["cassisivadan", "caleth", "implementation", "code", "compute", "construct", "execute", "function", "chinese"],
    "UM": ["umbroth", "umbral", "security", "shadow", "protect", "guard", "shield", "defense", "japanese"],
    "DR": ["draumric", "drath", "structure", "framework", "architecture", "foundation", "pattern", "german"],
}

CONLANG_MARKERS = [
    "tongue", "tongues", "sacred tongue", "conlang", "constructed language",
    "kor'aelin", "avali", "runethic", "cassisivadan", "umbroth", "draumric",
    "korath", "avion", "runik", "caleth", "umbral", "drath",
    "mal'kythric", "sacred particle", "cursed particle",
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
    "ame", "elven", "demon", "dragon", "sundering",
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
    "trust vector", "risk decision", "allow", "quarantine", "escalate", "deny",
    "polyhedral", "quasicrystal", "lattice", "friction",
]


def score_text(text: str, markers: list[str]) -> int:
    lower = text.lower()
    return sum(1 for m in markers if m in lower)


def detect_tongues(text: str) -> dict[str, float]:
    lower = text.lower()
    scores = {}
    for tongue, keywords in TONGUE_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in lower)
        scores[tongue] = round(hits / max(len(keywords), 1), 3)
    return scores


def detect_layers(text: str) -> list[int]:
    layers = set()
    lower = text.lower()
    layer_keywords = {
        1: ["context ingestion", "complex context", "layer 1", "l1"],
        2: ["realification", "layer 2", "l2", "real-valued"],
        3: ["weighted transform", "tongue weight", "phi-weight", "layer 3", "l3", "langues"],
        4: ["poincare", "embedding", "layer 4", "l4", "hyperbolic space"],
        5: ["hyperbolic distance", "arcosh", "layer 5", "l5", "d_h"],
        6: ["breathing", "layer 6", "l6", "oscillat"],
        7: ["mobius", "layer 7", "l7", "phase"],
        8: ["hamiltonian", "multi-well", "layer 8", "l8", "energy landscape"],
        9: ["spectral", "fft", "layer 9", "l9", "fourier"],
        10: ["spin coherence", "layer 10", "l10", "decoherence"],
        11: ["triadic", "temporal", "layer 11", "l11", "intent"],
        12: ["harmonic wall", "layer 12", "l12", "safety score", "h(d"],
        13: ["risk decision", "governance", "layer 13", "l13", "allow", "quarantine", "deny"],
        14: ["audio axis", "telemetry", "layer 14", "l14", "vacuum acoustic"],
    }
    for layer, keywords in layer_keywords.items():
        if any(kw in lower for kw in keywords):
            layers.add(layer)
    return sorted(layers) if layers else [0]


def estimate_difficulty(text: str, category: str = "meta") -> float:
    """Estimate difficulty based on application depth, not vocabulary."""
    words = text.split()
    if not words:
        return 0.1

    lower = text.lower()

    # Count cross-domain bridges (connecting lore to math, code to theory, etc.)
    bridge_pairs = [
        ("tongue", "harmonic"), ("lore", "axiom"), ("narrative", "geometry"),
        ("character", "pipeline"), ("magic", "crypto"), ("story", "security"),
        ("conlang", "embedding"), ("fiction", "math"), ("ritual", "protocol"),
        ("spell", "algorithm"), ("realm", "layer"), ("guild", "governance"),
    ]
    bridges = sum(1 for a, b in bridge_pairs if a in lower and b in lower)

    # Count application verbs (doing, not describing)
    apply_verbs = [
        "implement", "build", "design", "compute", "derive", "prove",
        "construct", "synthesize", "integrate", "validate", "enforce",
        "translate", "convert", "transform", "map", "route",
    ]
    applications = sum(1 for v in apply_verbs if v in lower)

    # Multi-tongue activation (using multiple tongues = harder)
    tongue_hits = sum(1 for kw_list in TONGUE_KEYWORDS.values()
                      for kw in kw_list if kw in lower)

    # Base difficulty by category
    base = {"fiction": 0.2, "conlang": 0.4, "technical": 0.5, "meta": 0.1}.get(category, 0.1)

    # Scale up for bridges, applications, and multi-tongue
    score = base + bridges * 0.1 + applications * 0.05 + min(tongue_hits * 0.02, 0.2)
    return round(min(max(score, 0.1), 0.9), 1)


# ===================================================================
# Phase 1: Extract
# ===================================================================
def extract():
    """Stream-parse the Claude JSON into individual conversation files."""
    import ijson

    print(f"Extracting conversations from {CLAUDE_JSON}")
    print(f"Output directory: {CONV_DIR}")

    CONV_DIR.mkdir(parents=True, exist_ok=True)
    index = []
    conv_count = 0
    skipped = 0

    with open(CLAUDE_JSON, "rb") as f:
        for item in ijson.items(f, "item"):
            conv_count += 1
            conv_id = item.get("uuid", f"unknown_{conv_count}")
            name = item.get("name", "")
            created = item.get("created_at", "")[:10]
            chat_messages = item.get("chat_messages", [])

            if not chat_messages:
                skipped += 1
                continue

            # Build message list
            messages = []
            total_chars = 0
            for msg in chat_messages:
                text = msg.get("text", "") or ""
                sender = msg.get("sender", "unknown")
                msg_time = msg.get("created_at", "")
                if text.strip():
                    messages.append({
                        "role": "assistant" if sender == "assistant" else "user",
                        "content": text,
                        "timestamp": msg_time,
                    })
                    total_chars += len(text)

            if not messages:
                skipped += 1
                continue

            # Save conversation file
            conv_file = CONV_DIR / f"{created}_{conv_id[:8]}.json"
            conv_data = {
                "id": conv_id,
                "title": name or "Untitled",
                "created": created,
                "message_count": len(messages),
                "total_chars": total_chars,
                "messages": messages,
            }
            with open(conv_file, "w", encoding="utf-8") as cf:
                json.dump(conv_data, cf, ensure_ascii=False)

            # Build index entry
            first_user = next((m["content"][:300] for m in messages if m["role"] == "user"), "")
            first_asst = next((m["content"][:300] for m in messages if m["role"] == "assistant"), "")

            # Combine text for scoring (first 10 messages)
            all_text = (name or "") + " " + " ".join(m["content"] for m in messages[:10])

            index.append({
                "file": conv_file.name,
                "id": conv_id,
                "title": name or "Untitled",
                "created": created,
                "message_count": len(messages),
                "total_chars": total_chars,
                "first_user_preview": first_user,
                "first_assistant_preview": first_asst,
                "fiction_score": score_text(all_text, FICTION_MARKERS),
                "technical_score": score_text(all_text, TECHNICAL_MARKERS),
                "conlang_score": score_text(all_text, CONLANG_MARKERS),
            })

            if conv_count % 100 == 0:
                print(f"  ... processed {conv_count} conversations")

    # Save index
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Processed {conv_count} conversations ({skipped} empty, {len(index)} with content)")
    print(f"Index: {INDEX_FILE}")

    # Category distribution
    fiction = sum(1 for e in index if e["fiction_score"] > e["technical_score"] and e["fiction_score"] > e["conlang_score"])
    technical = sum(1 for e in index if e["technical_score"] > e["fiction_score"] and e["technical_score"] > e["conlang_score"])
    conlang = sum(1 for e in index if e["conlang_score"] > e["fiction_score"] and e["conlang_score"] > e["technical_score"])
    mixed = len(index) - fiction - technical - conlang
    print(f"\nPreliminary keyword classification:")
    print(f"  Fiction/Lore: {fiction}")
    print(f"  Technical/SCBE: {technical}")
    print(f"  Conlang/Tongues: {conlang}")
    print(f"  Mixed/Unclear: {mixed}")

    return index


# ===================================================================
# Phase 2: Classify (keyword-based, no HF dependency)
# ===================================================================
def classify():
    """Classify conversations using keyword scoring."""
    if not INDEX_FILE.exists():
        print("ERROR: No index file. Run 'extract' first.")
        return []

    with open(INDEX_FILE, encoding="utf-8") as f:
        index = json.load(f)

    print(f"Classifying {len(index)} conversations...")

    classified = []
    for entry in index:
        kw_scores = {
            "fiction": entry.get("fiction_score", 0),
            "technical": entry.get("technical_score", 0),
            "conlang": entry.get("conlang_score", 0),
        }
        top = max(kw_scores, key=kw_scores.get)
        top_score = kw_scores[top]

        # If no markers hit, it's meta
        if top_score == 0:
            category = "meta"
        # If conlang and fiction are close, prefer conlang (rarer, more valuable)
        elif kw_scores["conlang"] > 0 and kw_scores["conlang"] >= kw_scores["fiction"] * 0.7:
            category = "conlang"
        else:
            category = top

        entry["category"] = category
        entry["classification_method"] = "keyword"
        classified.append(entry)

    with open(CLASSIFIED_FILE, "w", encoding="utf-8") as f:
        json.dump(classified, f, indent=2, ensure_ascii=False)

    cats = {}
    for e in classified:
        cat = e["category"]
        cats[cat] = cats.get(cat, 0) + 1

    print(f"\nClassification results:")
    for cat, count in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")
    print(f"\nSaved: {CLASSIFIED_FILE}")

    return classified


# ===================================================================
# Phase 3: Convert to SFT
# ===================================================================
def convert():
    """Convert classified conversations into SFT JSONL records."""
    if CLASSIFIED_FILE.exists():
        with open(CLASSIFIED_FILE, encoding="utf-8") as f:
            classified = json.load(f)
    elif INDEX_FILE.exists():
        with open(INDEX_FILE, encoding="utf-8") as f:
            classified = json.load(f)
        for entry in classified:
            kw_scores = {
                "fiction": entry.get("fiction_score", 0),
                "technical": entry.get("technical_score", 0),
                "conlang": entry.get("conlang_score", 0),
            }
            entry["category"] = max(kw_scores, key=kw_scores.get) if max(kw_scores.values()) > 0 else "meta"
    else:
        print("ERROR: No index file found. Run 'extract' first.")
        return

    SFT_DIR.mkdir(parents=True, exist_ok=True)

    output_paths = {
        "fiction": SFT_FICTION,
        "technical": SFT_TECHNICAL,
        "conlang": SFT_CONLANG,
        "meta": SFT_META,
    }
    for path in [*output_paths.values(), SFT_COMBINED]:
        path.write_text("", encoding="utf-8")

    counts: dict[str, int] = {k: 0 for k in output_paths}
    total = 0

    for entry in classified:
        conv_file = CONV_DIR / entry["file"]
        if not conv_file.exists():
            continue

        with open(conv_file, encoding="utf-8") as f:
            conv_data = json.load(f)

        messages = conv_data.get("messages", [])
        category = entry.get("category", "meta")
        title = entry.get("title", "Untitled")
        created = entry.get("created", "")

        i = 0
        while i < len(messages):
            if messages[i]["role"] != "user":
                i += 1
                continue

            user_msg = messages[i]["content"]
            j = i + 1
            while j < len(messages) and messages[j]["role"] != "assistant":
                j += 1

            if j >= len(messages):
                break

            asst_msg = messages[j]["content"]
            if len(user_msg) < 30 and len(asst_msg) < 30:
                i = j + 1
                continue

            context_msgs = []
            for k in range(max(0, i - 2), i):
                role = messages[k]["role"]
                content = messages[k]["content"][:500]
                context_msgs.append({"role": role, "content": content})

            system_content = "You are Polly, the SCBE-AETHERMOORE AI assistant. "
            if category == "fiction":
                system_content += "You are discussing Spiralverse lore, worldbuilding, and creative writing."
            elif category == "conlang":
                system_content += "You are discussing the Six Sacred Tongues constructed language system and its applications."
            elif category == "technical":
                system_content += "You are discussing SCBE technical architecture, hyperbolic geometry, and AI safety."
            else:
                system_content += "You are helping with development, debugging, and project management."

            sft_messages = [{"role": "system", "content": system_content}]
            sft_messages.extend(context_msgs)
            sft_messages.append({"role": "user", "content": user_msg})
            sft_messages.append({"role": "assistant", "content": asst_msg})

            combined_text = user_msg + " " + asst_msg
            tongue_weights = detect_tongues(combined_text)
            dominant = max(tongue_weights, key=tongue_weights.get)
            difficulty = estimate_difficulty(combined_text, category)
            layers = detect_layers(combined_text)

            record = {
                "messages": sft_messages,
                "metadata": {
                    "source": "claude_export",
                    "conversation_id": entry.get("id", ""),
                    "conversation_title": title,
                    "date": created,
                    "category": category,
                    "tongue_weights": tongue_weights,
                    "dominant_tongue": dominant,
                    "difficulty": difficulty,
                    "layers": layers,
                    "pair_index": counts.get(category, 0),
                },
            }

            line = json.dumps(record, ensure_ascii=False) + "\n"

            if category in output_paths:
                with open(output_paths[category], "a", encoding="utf-8") as out_f:
                    out_f.write(line)
                counts[category] = counts.get(category, 0) + 1

            with open(SFT_COMBINED, "a", encoding="utf-8") as combined_f:
                combined_f.write(line)
            total += 1
            i = j + 1

    print(f"\nSFT conversion complete:")
    print(f"  Total records: {total}")
    for cat, count in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")
    print(f"\nOutput files:")
    for name, path in [("fiction", SFT_FICTION), ("technical", SFT_TECHNICAL),
                        ("conlang", SFT_CONLANG), ("meta", SFT_META), ("combined", SFT_COMBINED)]:
        if path.exists():
            size = path.stat().st_size / 1024 / 1024
            print(f"  {name}: {path.name} ({size:.1f} MB)")


# ===================================================================
# Main
# ===================================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/claude_export_extract_and_classify.py [extract|classify|convert|all]")
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
