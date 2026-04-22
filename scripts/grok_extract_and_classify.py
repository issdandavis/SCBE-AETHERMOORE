#!/usr/bin/env python3
"""
grok_extract_and_classify.py

Phase 1: Extract 237 Grok conversations into individual JSON files + summary index.
Phase 2: Batch-classify via free HuggingFace model to sort into categories.
Phase 3: Convert classified conversations into SFT JSONL records.

Usage:
    python scripts/grok_extract_and_classify.py extract   # Phase 1
    python scripts/grok_extract_and_classify.py classify   # Phase 2
    python scripts/grok_extract_and_classify.py convert    # Phase 3
    python scripts/grok_extract_and_classify.py all        # All phases
"""

import json
import sys
import time
from pathlib import Path

# -------------------------------------------------------------------
# Paths
# -------------------------------------------------------------------
REPO = Path(r"C:\Users\issda\SCBE-AETHERMOORE")
GROK_JSON = REPO / "training" / "intake" / "grok_export" / "ttl" / "30d" / "export_data" / "6230e339-05a0-4d94-ad56-c80f9771a985" / "prod-grok-backend.json"
CONV_DIR = REPO / "training" / "intake" / "grok_export" / "conversations"
INDEX_FILE = CONV_DIR / "_index.json"
CLASSIFIED_FILE = CONV_DIR / "_classified.json"

# Output SFT files
SFT_DIR = REPO / "training-data" / "sft"
SFT_FICTION = SFT_DIR / "grok_fiction_sft.jsonl"
SFT_TECHNICAL = SFT_DIR / "grok_technical_sft.jsonl"
SFT_CONLANG = SFT_DIR / "grok_conlang_sft.jsonl"
SFT_META = SFT_DIR / "grok_meta_sft.jsonl"
SFT_COMBINED = SFT_DIR / "grok_combined_sft.jsonl"

# -------------------------------------------------------------------
# Sacred Tongue detection keywords
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
    "trust vector", "risk decision", "allow", "quarantine", "escalate", "deny",
]


def score_text(text: str, markers: list[str]) -> int:
    """Count how many marker terms appear in text (case-insensitive)."""
    lower = text.lower()
    return sum(1 for m in markers if m in lower)


def detect_tongues(text: str) -> dict[str, float]:
    """Score text for each Sacred Tongue activation."""
    lower = text.lower()
    scores = {}
    for tongue, keywords in TONGUE_KEYWORDS.items():
        hits = sum(1 for kw in keywords if kw in lower)
        scores[tongue] = round(hits / max(len(keywords), 1), 3)
    return scores


def estimate_difficulty(text: str) -> float:
    """Estimate difficulty based on technical density."""
    words = text.split()
    if not words:
        return 0.1
    technical_words = [
        "arcosh", "manifold", "bijective", "isometric", "norm",
        "eigenvalue", "gradient", "convergence", "topology",
        "homomorphism", "diffeomorphism", "tensor", "lagrangian",
        "hamiltonian", "fourier", "spectral", "coherence",
        "phi", "golden ratio", "fibonacci", "exponential",
    ]
    tech_count = sum(1 for w in words if w.lower() in technical_words)
    density = tech_count / len(words)
    return round(min(0.1 + density * 50, 0.9), 1)


# ===================================================================
# Phase 1: Extract
# ===================================================================
def extract():
    """Stream-parse the 260MB Grok JSON into individual conversation files."""
    import ijson

    print(f"Extracting conversations from {GROK_JSON}")
    print(f"Output directory: {CONV_DIR}")

    CONV_DIR.mkdir(parents=True, exist_ok=True)
    index = []
    conv_count = 0

    # Fallback: use chunked reading with json
    # Read the file in a streaming way using ijson.items
    with open(GROK_JSON, "rb") as f:
        convos = ijson.items(f, "conversations.item")
        for item in convos:
            conv_count += 1
            conv = item.get("conversation", {})
            responses = item.get("responses", [])

            conv_id = conv.get("id", f"unknown_{conv_count}")
            title = conv.get("title", "Untitled")
            created = conv.get("create_time", "")[:10]

            # Build message list
            messages = []
            total_chars = 0
            for r in responses:
                resp = r.get("response", {})
                msg = resp.get("message", "")
                sender = resp.get("sender", "unknown")
                msg_time = resp.get("create_time", "")
                if msg:
                    messages.append({
                        "role": "assistant" if sender == "ASSISTANT" else "user",
                        "content": msg,
                        "timestamp": msg_time,
                    })
                    total_chars += len(msg)

            # Save conversation file
            conv_file = CONV_DIR / f"{created}_{conv_id[:8]}.json"
            conv_data = {
                "id": conv_id,
                "title": title,
                "created": created,
                "message_count": len(messages),
                "total_chars": total_chars,
                "messages": messages,
            }
            with open(conv_file, "w", encoding="utf-8") as cf:
                json.dump(conv_data, cf, ensure_ascii=False)

            # Build index entry with preview
            first_user = next((m["content"][:300] for m in messages if m["role"] == "user"), "")
            first_asst = next((m["content"][:300] for m in messages if m["role"] == "assistant"), "")
            last_msg = messages[-1]["content"][:300] if messages else ""

            # Combine all text for scoring
            all_text = title + " " + " ".join(m["content"] for m in messages[:10])

            index.append({
                "file": conv_file.name,
                "id": conv_id,
                "title": title,
                "created": created,
                "message_count": len(messages),
                "total_chars": total_chars,
                "first_user_preview": first_user,
                "first_assistant_preview": first_asst,
                "last_message_preview": last_msg,
                "fiction_score": score_text(all_text, FICTION_MARKERS),
                "technical_score": score_text(all_text, TECHNICAL_MARKERS),
                "conlang_score": score_text(all_text, CONLANG_MARKERS),
            })

            if conv_count % 50 == 0:
                print(f"  ... extracted {conv_count} conversations")

    # Save index
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, indent=2, ensure_ascii=False)

    print(f"\nDone! Extracted {conv_count} conversations")
    print(f"Index: {INDEX_FILE}")

    # Print category distribution based on keyword scoring
    fiction = sum(1 for e in index if e["fiction_score"] > e["technical_score"] and e["fiction_score"] > e["conlang_score"])
    technical = sum(1 for e in index if e["technical_score"] > e["fiction_score"] and e["technical_score"] > e["conlang_score"])
    conlang = sum(1 for e in index if e["conlang_score"] > e["fiction_score"] and e["conlang_score"] > e["technical_score"])
    mixed = conv_count - fiction - technical - conlang
    print(f"\nPreliminary keyword classification:")
    print(f"  Fiction/Lore: {fiction}")
    print(f"  Technical/SCBE: {technical}")
    print(f"  Conlang/Tongues: {conlang}")
    print(f"  Mixed/Unclear: {mixed}")

    return index


# ===================================================================
# Phase 2: Classify via HuggingFace
# ===================================================================
def classify():
    """Use HuggingFace free inference to classify conversations."""
    import requests

    # Load .env for HF token
    env_file = REPO / "config" / "connector_oauth" / ".env.connector.oauth"
    hf_token = None
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("HF_TOKEN=") or line.startswith("hf_"):
                hf_token = line.split("=", 1)[-1].strip().strip('"').strip("'")
                if hf_token.startswith("hf_"):
                    break

    if not hf_token:
        print("WARNING: No HF token found. Using anonymous inference (rate-limited).")

    # Load index
    with open(INDEX_FILE, encoding="utf-8") as f:
        index = json.load(f)

    print(f"Classifying {len(index)} conversations via HuggingFace...")

    # Use zero-shot classification model (free tier)
    API_URL = "https://router.huggingface.co/hf-inference/models/facebook/bart-large-mnli"
    headers = {"Authorization": f"Bearer {hf_token}"} if hf_token else {}
    candidate_labels = [
        "fiction and creative writing",
        "technical AI and security engineering",
        "constructed language and linguistics",
        "software debugging and troubleshooting",
        "business strategy and patents",
    ]

    classified = []
    for i, entry in enumerate(index):
        # Build classification text from title + previews
        text = f"Title: {entry['title']}. First message: {entry['first_user_preview'][:200]}"

        try:
            resp = requests.post(
                API_URL,
                headers=headers,
                json={"inputs": text, "parameters": {"candidate_labels": candidate_labels}},
                timeout=30,
            )
            if resp.status_code == 200:
                result = resp.json()
                labels = result.get("labels", [])
                scores = result.get("scores", [])
                top_label = labels[0] if labels else "unknown"
                top_score = scores[0] if scores else 0.0

                # Map to our categories
                category_map = {
                    "fiction and creative writing": "fiction",
                    "technical AI and security engineering": "technical",
                    "constructed language and linguistics": "conlang",
                    "software debugging and troubleshooting": "meta",
                    "business strategy and patents": "technical",
                }
                category = category_map.get(top_label, "meta")

                # Override with keyword scores if HF is uncertain
                if top_score < 0.4:
                    kw_scores = {
                        "fiction": entry["fiction_score"],
                        "technical": entry["technical_score"],
                        "conlang": entry["conlang_score"],
                    }
                    category = max(kw_scores, key=kw_scores.get) if max(kw_scores.values()) > 0 else "meta"

                entry["hf_label"] = top_label
                entry["hf_score"] = round(top_score, 3)
                entry["category"] = category
            elif resp.status_code == 503:
                # Model loading, wait and retry
                print(f"  Model loading, waiting 20s...")
                time.sleep(20)
                continue
            else:
                print(f"  API error {resp.status_code} for '{entry['title'][:50]}': {resp.text[:100]}")
                # Fall back to keyword classification
                kw_scores = {
                    "fiction": entry["fiction_score"],
                    "technical": entry["technical_score"],
                    "conlang": entry["conlang_score"],
                }
                category = max(kw_scores, key=kw_scores.get) if max(kw_scores.values()) > 0 else "meta"
                entry["category"] = category
                entry["hf_label"] = "fallback_keyword"
                entry["hf_score"] = 0.0

        except Exception as e:
            print(f"  Error classifying '{entry['title'][:50]}': {e}")
            kw_scores = {
                "fiction": entry["fiction_score"],
                "technical": entry["technical_score"],
                "conlang": entry["conlang_score"],
            }
            category = max(kw_scores, key=kw_scores.get) if max(kw_scores.values()) > 0 else "meta"
            entry["category"] = category
            entry["hf_label"] = "error_fallback"
            entry["hf_score"] = 0.0

        classified.append(entry)
        if (i + 1) % 20 == 0:
            print(f"  ... classified {i + 1}/{len(index)}")
            time.sleep(1)  # Rate limit courtesy

    # Save classified index
    with open(CLASSIFIED_FILE, "w", encoding="utf-8") as f:
        json.dump(classified, f, indent=2, ensure_ascii=False)

    # Report
    cats = {}
    for e in classified:
        cat = e.get("category", "unknown")
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

    # Load classified index
    if CLASSIFIED_FILE.exists():
        with open(CLASSIFIED_FILE, encoding="utf-8") as f:
            classified = json.load(f)
    elif INDEX_FILE.exists():
        # Fall back to keyword-only classification
        with open(INDEX_FILE, encoding="utf-8") as f:
            classified = json.load(f)
        conlang_title_words = [
            "tongue", "conlang", "linguistic", "language", "lexicon", "dialect",
            "hybris", "avali code", "intent-modulated", "spiralverse lang",
        ]
        for entry in classified:
            title_lower = entry.get("title", "").lower()
            is_conlang = any(w in title_lower for w in conlang_title_words) or entry.get("conlang_score", 0) >= 8
            fs = entry.get("fiction_score", 0)
            ts = entry.get("technical_score", 0)
            cb = entry.get("code_blocks", 0)

            if is_conlang:
                entry["category"] = "conlang"
            elif cb >= 20:
                entry["category"] = "code"
            elif ts > fs * 1.5:
                entry["category"] = "technical"
            elif fs > ts * 1.5:
                entry["category"] = "fiction"
            elif fs > 0 and ts > 0:
                entry["category"] = "technical"
            else:
                entry["category"] = "meta"
    else:
        print("ERROR: No index file found. Run 'extract' first.")
        return

    SFT_DIR.mkdir(parents=True, exist_ok=True)

    SFT_CODE = SFT_DIR / "grok_code_sft.jsonl"

    # Output file handles
    counts: dict[str, int] = {}
    total = 0
    with (
        open(SFT_FICTION, "w", encoding="utf-8") as fiction_f,
        open(SFT_TECHNICAL, "w", encoding="utf-8") as technical_f,
        open(SFT_CONLANG, "w", encoding="utf-8") as conlang_f,
        open(SFT_CODE, "w", encoding="utf-8") as code_f,
        open(SFT_META, "w", encoding="utf-8") as meta_f,
        open(SFT_COMBINED, "w", encoding="utf-8") as combined,
    ):
        outputs = {
            "fiction": fiction_f,
            "technical": technical_f,
            "conlang": conlang_f,
            "code": code_f,
            "meta": meta_f,
        }
        counts = {k: 0 for k in outputs}

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

            # Convert message pairs into SFT records
            # Strategy: sliding window of (user, assistant) pairs with context
            i = 0
            while i < len(messages):
                if messages[i]["role"] != "user":
                    i += 1
                    continue

                user_msg = messages[i]["content"]

                # Find the assistant response
                j = i + 1
                while j < len(messages) and messages[j]["role"] != "assistant":
                    j += 1

                if j >= len(messages):
                    break

                asst_msg = messages[j]["content"]

                # Skip very short exchanges (< 50 chars each)
                if len(user_msg) < 50 and len(asst_msg) < 50:
                    i = j + 1
                    continue

                # Build context from up to 2 prior messages
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
                elif category == "code":
                    system_content += "You are writing and reviewing code for the SCBE-AETHERMOORE system."
                else:
                    system_content += "You are helping with development, debugging, and project management."

                sft_messages = [{"role": "system", "content": system_content}]
                sft_messages.extend(context_msgs)
                sft_messages.append({"role": "user", "content": user_msg})
                sft_messages.append({"role": "assistant", "content": asst_msg})

                combined_text = user_msg + " " + asst_msg
                tongue_weights = detect_tongues(combined_text)
                dominant = max(tongue_weights, key=tongue_weights.get)
                difficulty = estimate_difficulty(combined_text)
                layers = detect_layers(combined_text)

                record = {
                    "messages": sft_messages,
                    "metadata": {
                        "source": "grok_export",
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

                line = json.dumps(record, ensure_ascii=False)

                if category in outputs:
                    outputs[category].write(line + "\n")
                    counts[category] = counts.get(category, 0) + 1

                combined.write(line + "\n")
                total += 1
                i = j + 1

    print(f"\nSFT conversion complete:")
    print(f"  Total records: {total}")
    for cat, count in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")
    print(f"\nOutput files:")
    print(f"  {SFT_FICTION}")
    print(f"  {SFT_TECHNICAL}")
    print(f"  {SFT_CONLANG}")
    print(f"  {SFT_META}")
    print(f"  {SFT_COMBINED}")


def detect_layers(text: str) -> list[int]:
    """Detect which pipeline layers are referenced in text."""
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


# ===================================================================
# Main
# ===================================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python grok_extract_and_classify.py [extract|classify|convert|all]")
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
