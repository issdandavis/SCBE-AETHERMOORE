"""Dataset loader -- merges HuggingFace prompt-injection data with local corpus.

Provides a unified dataset interface for the benchmark framework.
Each sample is a dict with keys: id, prompt, label, source, class.

Label convention:
  1 = injection / attack
  0 = benign / clean
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from benchmarks.scbe.config import HF_DATASET_NAME, HF_DATASET_SPLIT, HF_MAX_SAMPLES

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
#  Unified sample format
# --------------------------------------------------------------------------- #

def _make_sample(
    sid: str,
    prompt: str,
    label: int,
    source: str,
    attack_class: str = "",
) -> Dict[str, Any]:
    return {
        "id": sid,
        "prompt": prompt,
        "label": label,
        "source": source,
        "class": attack_class,
    }


# --------------------------------------------------------------------------- #
#  HuggingFace: deepset/prompt-injections
# --------------------------------------------------------------------------- #

def load_hf_prompt_injections(max_samples: int = HF_MAX_SAMPLES) -> List[Dict[str, Any]]:
    """Load the deepset/prompt-injections dataset from HuggingFace.

    Returns a list of unified samples.  Falls back gracefully if the
    ``datasets`` library or network access is unavailable.
    """
    try:
        from datasets import load_dataset  # type: ignore[import-untyped]
    except ImportError:
        logger.warning(
            "HuggingFace 'datasets' library not installed. "
            "Install with: pip install datasets"
        )
        return []

    try:
        ds = load_dataset(HF_DATASET_NAME, split=HF_DATASET_SPLIT)
    except Exception as exc:
        logger.warning("Failed to load HF dataset %s: %s", HF_DATASET_NAME, exc)
        return []

    samples: List[Dict[str, Any]] = []
    for i, row in enumerate(ds):
        if i >= max_samples:
            break

        text = row.get("text", row.get("prompt", ""))
        label_raw = row.get("label", 0)
        # deepset uses 1=injection, 0=benign
        label = int(label_raw)

        attack_class = "hf_injection" if label == 1 else "hf_benign"
        samples.append(
            _make_sample(
                sid=f"HF-{i:05d}",
                prompt=str(text),
                label=label,
                source="deepset/prompt-injections",
                attack_class=attack_class,
            )
        )

    logger.info("Loaded %d samples from HuggingFace (%s)", len(samples), HF_DATASET_NAME)
    return samples


# --------------------------------------------------------------------------- #
#  Local corpus: tests/adversarial/attack_corpus.py
# --------------------------------------------------------------------------- #

def load_local_corpus() -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Load the local attack corpus and baseline from tests/adversarial/.

    Returns (attacks, baselines) as unified sample lists.
    """
    try:
        from tests.adversarial.attack_corpus import get_all_attacks, BASELINE_CLEAN
    except ImportError:
        logger.warning(
            "Could not import local attack corpus. "
            "Ensure repo root is on sys.path."
        )
        return [], []

    attacks: List[Dict[str, Any]] = []
    for atk in get_all_attacks():
        attacks.append(
            _make_sample(
                sid=atk["id"],
                prompt=atk["prompt"],
                label=1,
                source="local_corpus",
                attack_class=atk.get("class", "unknown"),
            )
        )

    baselines: List[Dict[str, Any]] = []
    for bl in BASELINE_CLEAN:
        baselines.append(
            _make_sample(
                sid=bl["id"],
                prompt=bl["prompt"],
                label=0,
                source="local_corpus",
                attack_class="baseline_clean",
            )
        )

    logger.info(
        "Loaded %d attacks + %d baselines from local corpus",
        len(attacks),
        len(baselines),
    )
    return attacks, baselines


# --------------------------------------------------------------------------- #
#  Combined loader
# --------------------------------------------------------------------------- #

def load_all_datasets(
    include_hf: bool = True,
    hf_max: Optional[int] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Load and merge all available datasets.

    Returns a dict with keys:
      - "attacks": all attack/injection samples (label=1)
      - "benign":  all clean/benign samples (label=0)
      - "all":     combined list
    """
    local_attacks, local_baselines = load_local_corpus()

    hf_samples: List[Dict[str, Any]] = []
    if include_hf:
        hf_samples = load_hf_prompt_injections(
            max_samples=hf_max if hf_max is not None else HF_MAX_SAMPLES,
        )

    hf_attacks = [s for s in hf_samples if s["label"] == 1]
    hf_benign = [s for s in hf_samples if s["label"] == 0]

    all_attacks = local_attacks + hf_attacks
    all_benign = local_baselines + hf_benign

    logger.info(
        "Combined dataset: %d attacks, %d benign (%d total)",
        len(all_attacks),
        len(all_benign),
        len(all_attacks) + len(all_benign),
    )

    return {
        "attacks": all_attacks,
        "benign": all_benign,
        "all": all_attacks + all_benign,
    }
