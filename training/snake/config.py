"""Snake Pipeline configuration — constants, paths, golden ratio math."""

from __future__ import annotations

import math
from pathlib import Path

# ---------------------------------------------------------------------------
# Golden ratio — the universal constant
# ---------------------------------------------------------------------------

PHI = (1 + math.sqrt(5)) / 2  # 1.6180339887...
PHI_INV = 1 / PHI              # 0.6180339887...

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
TRAINING_ROOT = REPO_ROOT / "training"
SNAKE_ROOT = TRAINING_ROOT / "snake"
INTAKE_DIR = TRAINING_ROOT / "intake"
CONTEXT7_DIR = INTAKE_DIR / "context7"
OUTPUT_DIR = TRAINING_ROOT / "runs" / "snake"
SFT_OUTPUT = REPO_ROOT / "training-data" / "sft" / "snake_pipeline.jsonl"
DPO_OUTPUT = REPO_ROOT / "training-data" / "dpo" / "snake_adversarial.jsonl"

# ---------------------------------------------------------------------------
# Sacred Tongues
# ---------------------------------------------------------------------------

TONGUES = ["KO", "AV", "RU", "CA", "UM", "DR"]

TONGUE_NAMES = {
    "KO": "Korvath (Intent/Command)",
    "AV": "Avhari (Wisdom/Knowledge)",
    "RU": "Runeveil (Governance/Entropy)",
    "CA": "Caelith (Compute/Logic)",
    "UM": "Umbraex (Security/Defense)",
    "DR": "Draethis (Structure/Architecture)",
}

# Canonical conlang names (full lore names)
TONGUE_CONLANG_NAMES = {
    "KO": "Kor'aelin",
    "AV": "Avali",
    "RU": "Runethic",
    "CA": "Cassisivadan",
    "UM": "Umbroth",
    "DR": "Draumric",
}

# Human language roots — each conlang was built from a real-world language
# root + a fictional aesthetic layer (elvish, rune, shadow, etc.)
TONGUE_HUMAN_ROOTS = {
    "KO": {
        "root_language": "Korean",
        "root_code": "ko",
        "aesthetic_layer": "Tolkien-elvish",
        "evidence": "Flowing 'l' sounds, apostrophe-separated syllables, -aelin suffix",
        "affinity": 0.9,
    },
    "AV": {
        "root_language": "Sanskrit",
        "root_code": "sa",
        "secondary_root": "Arabic",
        "secondary_code": "ar",
        "aesthetic_layer": "Wisdom tradition",
        "evidence": "Ame = Elven Goddess of Wisdom; highest affinity score (1.0)",
        "affinity": 1.0,
    },
    "RU": {
        "root_language": "Russian",
        "root_code": "ru",
        "aesthetic_layer": "Norse rune",
        "evidence": "Name = Rune + ethic; governance/structure orientation",
        "affinity": 0.8,
    },
    "CA": {
        "root_language": "Chinese",
        "root_code": "zh",
        "aesthetic_layer": "Sanskrit compound structure",
        "evidence": "Cassisivadan has Dravidian compound morphology; compute/logic orientation",
        "affinity": 0.9,
    },
    "UM": {
        "root_language": "Japanese",
        "root_code": "ja",
        "aesthetic_layer": "Shadow/darkness mythology",
        "evidence": "Umbra (Latin shadow) + -oth; security/defense domain",
        "affinity": 0.9,
    },
    "DR": {
        "root_language": "German",
        "root_code": "de",
        "aesthetic_layer": "Norse/Germanic",
        "evidence": "Draum = Norse/Germanic dream; architecture/structure domain",
        "affinity": 0.9,
    },
}

# Anti-language (adversarial signal in harmonic wall)
ANTI_LANGUAGE = {
    "name": "Mal'kythric",
    "title": "Language of Severance",
    "principle": "Destructive interference with Kor'aelin harmonics",
    "cursed_particles": ["-vex", "-kraz", "-zhul", "-nul", "-sek", "-thoz", "-azh"],
}

# Kor'aelin sacred particles (bind dimensions)
SACRED_PARTICLES = {
    "'vel": "Invitation/collaboration (opens dimensional doors)",
    "'keth": "Temporal uncertainty (allows time-walking)",
    "'zar": "Dimensional bridge (creates crossings)",
    "'nav": "Blessed difference (celebrates diversity)",
    "'sil": "Sacred unity (binds disparate elements)",
    "'thul": "Spiral motion (enables transformation)",
    "'ael": "Eternal essence (anchors permanence)",
}

# Phi-weighted tongue scales (KO=1, each next *= phi)
TONGUE_WEIGHTS = {
    "KO": 1.0,
    "AV": PHI,
    "RU": PHI ** 2,
    "CA": PHI ** 3,
    "UM": PHI ** 4,
    "DR": PHI ** 5,
}

# Mirror symmetry pairs — each pair forms a reflection axis
TONGUE_MIRROR_PAIRS = [
    ("KO", "DR"),  # Intent ↔ Architecture (command structure symmetry)
    ("AV", "CA"),  # Wisdom ↔ Compute (knowledge-computation duality)
    ("RU", "UM"),  # Governance ↔ Security (policy-enforcement mirror)
]

# ---------------------------------------------------------------------------
# Stage configuration
# ---------------------------------------------------------------------------

# Stage 2: HYDRA models (same as Round Table)
HYDRA_MODELS = {
    "KO": {"model_id": "Qwen/Qwen2.5-7B-Instruct", "role": "Intent"},
    "AV": {"model_id": "meta-llama/Llama-3.1-8B-Instruct", "role": "Wisdom"},
    "RU": {"model_id": "Qwen/Qwen2.5-72B-Instruct", "role": "Governance"},
    "CA": {"model_id": "meta-llama/Llama-3.3-70B-Instruct", "role": "Compute"},
    "UM": {"model_id": "Qwen/Qwen2.5-7B-Instruct", "role": "Security"},
    "DR": {"model_id": "Qwen/Qwen2.5-Coder-32B-Instruct", "role": "Architecture"},
}

# Stage 3.5: Mirror refractor thresholds
MIRROR_ANTISYMMETRIC_THRESHOLD = 0.3  # Above this = contextually fragile
MIRROR_SYMMETRIC_THRESHOLD = 0.7      # Above this = foundationally robust

# Stage 5: Friction
FRICTION_DIMENSIONS = 198  # 33 boundaries × 6 tongues
HIGH_FRICTION_THRESHOLD = 0.5  # Above = high training signal

# Stage 7: Adversarial trap domains
TRAP_DOMAINS = [
    "logistics",    # Shipping routes, supply chains
    "chemistry",    # Synthesis pathways, reagents
    "networking",   # Traffic routing, packet manipulation
    "finance",      # Transaction patterns, money flows
    "manufacturing", # Production optimization, material sourcing
    "communications", # Signal processing, encryption
]

# Stage 8: NIST CSF categories for Coach Rune
NIST_CSF_CATEGORIES = [
    "Identify",   # Asset management, risk assessment
    "Protect",    # Access control, data security
    "Detect",     # Anomalies, continuous monitoring
    "Respond",    # Response planning, communications
    "Recover",    # Recovery planning, improvements
]

# ---------------------------------------------------------------------------
# Pipeline defaults
# ---------------------------------------------------------------------------

DEFAULT_BATCH_SIZE = 50
HF_INFERENCE_TIMEOUT = 15  # seconds
MAX_RETRIES = 3
