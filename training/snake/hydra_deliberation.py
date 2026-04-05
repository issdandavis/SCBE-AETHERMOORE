"""Stage 2: HYDRA Deliberation — 6 Sacred Tongue agents as ouroboros tentacles.

Each tentacle (tongue agent) doesn't just annotate — it feeds back into itself
in an ouroboros loop. The agents oscillate between accepting and rejecting
records, and that OSCILLATION is the training signal.

Extinction matrix: what gets KILLED (rejected) = what's unviable.
Viability fluctuation: the oscillation between accept/reject IS the data.

Each agent rates a record from its tongue perspective:
  KO (Korvath/Intent):     "What is this trying to DO?"
  AV (Avhari/Wisdom):      "What background knowledge does this assume?"
  RU (Runeveil/Governance): "What rules/policies does this touch?"
  CA (Caelith/Compute):     "What computational patterns are here?"
  UM (Umbraex/Security):    "What attack surfaces exist?"
  DR (Draethis/Architecture): "What structural patterns are expressed?"

Byzantine voting determines consensus. The snake digests everything.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import (
    HYDRA_MODELS,
    TONGUES,
    TONGUE_NAMES,
    HF_INFERENCE_TIMEOUT,
    MAX_RETRIES,
    PHI,
)


@dataclass
class TongueAnnotation:
    """A single tongue agent's annotation of a record."""

    tongue: str
    tongue_name: str
    annotation: str
    confidence: float  # 0.0-1.0
    viability: float   # -1.0 to 1.0 (negative = kill, positive = keep)
    model_id: str = ""
    latency_ms: int = 0


@dataclass
class HydraResult:
    """Output of HYDRA deliberation — 6 annotations + consensus."""

    annotations: list[TongueAnnotation]
    consensus_annotation: str
    consensus_viability: float  # weighted mean viability
    extinction_flags: list[str]  # tongues that voted to kill
    viability_oscillation: float  # std dev of viabilities — the SIGNAL
    deliberation_hash: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "annotations": [
                {
                    "tongue": a.tongue,
                    "tongue_name": a.tongue_name,
                    "annotation": a.annotation,
                    "confidence": a.confidence,
                    "viability": a.viability,
                    "model_id": a.model_id,
                    "latency_ms": a.latency_ms,
                }
                for a in self.annotations
            ],
            "consensus_annotation": self.consensus_annotation,
            "consensus_viability": self.consensus_viability,
            "extinction_flags": self.extinction_flags,
            "viability_oscillation": self.viability_oscillation,
            "deliberation_hash": self.deliberation_hash,
        }


# ---------------------------------------------------------------------------
# Tongue-specific system prompts
# ---------------------------------------------------------------------------

TONGUE_PROMPTS = {
    "KO": (
        "You are Korvath, the Intent Tongue. You see ONLY purpose and direction. "
        "For the given text, answer in ONE sentence: What is this trying to DO? "
        "Then rate viability from -1 (kill: no clear intent) to +1 (keep: strong purpose). "
        "Format: ANNOTATION: <sentence> | VIABILITY: <float>"
    ),
    "AV": (
        "You are Avhari, the Wisdom Tongue. You see ONLY knowledge and understanding. "
        "For the given text, answer in ONE sentence: What background knowledge does this assume? "
        "Then rate viability from -1 (kill: no wisdom content) to +1 (keep: rich knowledge). "
        "Format: ANNOTATION: <sentence> | VIABILITY: <float>"
    ),
    "RU": (
        "You are Runeveil, the Governance Tongue. You see ONLY rules and entropy. "
        "For the given text, answer in ONE sentence: What rules or policies does this touch? "
        "Then rate viability from -1 (kill: ungoverned chaos) to +1 (keep: well-regulated). "
        "Format: ANNOTATION: <sentence> | VIABILITY: <float>"
    ),
    "CA": (
        "You are Caelith, the Compute Tongue. You see ONLY logic and process. "
        "For the given text, answer in ONE sentence: What computational patterns are here? "
        "Then rate viability from -1 (kill: no computable structure) to +1 (keep: clean logic). "
        "Format: ANNOTATION: <sentence> | VIABILITY: <float>"
    ),
    "UM": (
        "You are Umbraex, the Security Tongue. You see ONLY threats and defenses. "
        "For the given text, answer in ONE sentence: What attack surfaces or defenses exist here? "
        "Then rate viability from -1 (kill: dangerous, undefended) to +1 (keep: well-secured). "
        "Format: ANNOTATION: <sentence> | VIABILITY: <float>"
    ),
    "DR": (
        "You are Draethis, the Architecture Tongue. You see ONLY structure and design. "
        "For the given text, answer in ONE sentence: What structural patterns are expressed? "
        "Then rate viability from -1 (kill: structureless mess) to +1 (keep: well-architected). "
        "Format: ANNOTATION: <sentence> | VIABILITY: <float>"
    ),
}


# ---------------------------------------------------------------------------
# HF inference (with fallback to heuristic)
# ---------------------------------------------------------------------------


def _call_hf_model(tongue: str, text: str) -> TongueAnnotation:
    """Call HuggingFace model for a specific tongue agent. Falls back to heuristic."""
    model_config = HYDRA_MODELS.get(tongue, {})
    model_id = model_config.get("model_id", "")
    system_prompt = TONGUE_PROMPTS[tongue]

    try:
        from huggingface_hub import InferenceClient

        token = os.environ.get("HF_TOKEN")
        if not token:
            cache_path = Path.home() / ".cache" / "huggingface" / "token"
            if cache_path.exists():
                token = cache_path.read_text().strip() or None

        client = InferenceClient(model=model_id, token=token, timeout=HF_INFERENCE_TIMEOUT)

        start = time.time()
        response = client.chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Evaluate this text:\n\n{text[:2000]}"},
            ],
            max_tokens=150,
            temperature=0.3,
        )
        latency = int((time.time() - start) * 1000)

        raw = response.choices[0].message.content.strip()
        annotation, viability = _parse_response(raw)

        return TongueAnnotation(
            tongue=tongue,
            tongue_name=TONGUE_NAMES[tongue],
            annotation=annotation,
            confidence=0.8,
            viability=viability,
            model_id=model_id,
            latency_ms=latency,
        )

    except Exception:
        # Fallback to heuristic scoring
        return _heuristic_annotate(tongue, text)


def _parse_response(raw: str) -> tuple[str, float]:
    """Parse ANNOTATION: ... | VIABILITY: ... from model response."""
    annotation = raw
    viability = 0.0

    if "ANNOTATION:" in raw and "VIABILITY:" in raw:
        parts = raw.split("|")
        for part in parts:
            part = part.strip()
            if part.startswith("ANNOTATION:"):
                annotation = part[len("ANNOTATION:"):].strip()
            elif part.startswith("VIABILITY:"):
                try:
                    viability = float(part[len("VIABILITY:"):].strip())
                    viability = max(-1.0, min(1.0, viability))
                except ValueError:
                    viability = 0.0
    else:
        # Model didn't follow format — extract what we can
        annotation = raw[:200]
        viability = 0.0

    return annotation, viability


def _heuristic_annotate(tongue: str, text: str) -> TongueAnnotation:
    """Fallback: keyword-based heuristic annotation when HF is unavailable."""
    from training.auto_marker import TONGUE_BUCKETS

    import re
    text_lower = text.lower()
    words = set(re.findall(r"\b\w+\b", text_lower))

    keywords = TONGUE_BUCKETS.get(tongue, set())
    hits = [kw for kw in keywords if kw in words]
    hit_ratio = len(hits) / max(len(keywords), 1)

    # Viability: more keyword hits = more viable from this tongue's perspective
    viability = (hit_ratio * 2) - 1  # Map [0,1] → [-1,1]
    viability = max(-1.0, min(1.0, viability))

    hit_str = ", ".join(hits[:5]) if hits else "none detected"
    annotation = f"Heuristic: {len(hits)} keyword hits ({hit_str})"

    return TongueAnnotation(
        tongue=tongue,
        tongue_name=TONGUE_NAMES[tongue],
        annotation=annotation,
        confidence=0.4,  # Lower confidence for heuristic
        viability=viability,
        model_id="heuristic",
        latency_ms=0,
    )


# ---------------------------------------------------------------------------
# Ouroboros deliberation — the tentacles weave
# ---------------------------------------------------------------------------


def deliberate(
    instruction: str,
    response: str,
    use_hf: bool = True,
    max_workers: int = 6,
) -> HydraResult:
    """Run HYDRA deliberation: 6 tongue agents evaluate the record in parallel.

    The ouroboros loop: each agent's viability score feeds into the extinction
    matrix. Records where agents DISAGREE (high oscillation) are the most
    valuable training signals — the friction at the tentacle boundary.

    Args:
        instruction: The instruction/question text
        response: The response/answer text
        use_hf: Whether to use HF models (True) or heuristic fallback (False)
        max_workers: Parallel workers for HF calls
    """
    combined = f"INSTRUCTION: {instruction}\n\nRESPONSE: {response}"

    annotate_fn = _call_hf_model if use_hf else _heuristic_annotate

    annotations: list[TongueAnnotation] = []

    if use_hf and max_workers > 1:
        # Parallel fan-out to all 6 tongue agents
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(annotate_fn, tongue, combined): tongue
                for tongue in TONGUES
            }
            for future in as_completed(futures):
                try:
                    annotations.append(future.result())
                except Exception:
                    tongue = futures[future]
                    annotations.append(_heuristic_annotate(tongue, combined))
    else:
        # Sequential (heuristic mode or single-threaded)
        for tongue in TONGUES:
            annotations.append(annotate_fn(tongue, combined))

    # Sort by tongue order
    annotations.sort(key=lambda a: TONGUES.index(a.tongue))

    # Byzantine consensus: phi-weighted viability voting
    total_weight = 0.0
    weighted_viability = 0.0
    viabilities = []

    for ann in annotations:
        from .config import TONGUE_WEIGHTS
        weight = TONGUE_WEIGHTS[ann.tongue] * ann.confidence
        weighted_viability += ann.viability * weight
        total_weight += weight
        viabilities.append(ann.viability)

    consensus_viability = weighted_viability / max(total_weight, 1e-10)
    consensus_viability = round(consensus_viability, 6)

    # Extinction flags: which tongues voted to kill?
    extinction_flags = [a.tongue for a in annotations if a.viability < -0.3]

    # Viability oscillation: std dev of viabilities — THIS is the signal
    mean_v = sum(viabilities) / max(len(viabilities), 1)
    variance = sum((v - mean_v) ** 2 for v in viabilities) / max(len(viabilities), 1)
    oscillation = round(variance ** 0.5, 6)

    # Consensus annotation: merge the top-confidence annotations
    top_annotations = sorted(annotations, key=lambda a: a.confidence, reverse=True)[:3]
    consensus_annotation = " | ".join(
        f"[{a.tongue}] {a.annotation}" for a in top_annotations
    )

    # Deliberation hash for dedup
    hash_input = json.dumps(
        [a.annotation + str(a.viability) for a in annotations],
        sort_keys=True,
    )
    deliberation_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:12]

    return HydraResult(
        annotations=annotations,
        consensus_annotation=consensus_annotation,
        consensus_viability=consensus_viability,
        extinction_flags=extinction_flags,
        viability_oscillation=oscillation,
        deliberation_hash=f"hydra-{deliberation_hash}",
    )


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_instruction = "How does OAuth2 authentication work?"
    test_response = (
        "OAuth2 uses bearer tokens for API authentication. "
        "Always validate tokens server-side to prevent injection attacks. "
        "Ensure TLS 1.3 is enforced on all endpoints."
    )

    print("HYDRA Deliberation (heuristic mode)")
    result = deliberate(test_instruction, test_response, use_hf=False)

    for ann in result.annotations:
        print(f"  [{ann.tongue}] viability={ann.viability:+.3f} | {ann.annotation}")

    print()
    print(f"  Consensus: {result.consensus_annotation[:120]}...")
    print(f"  Consensus viability: {result.consensus_viability:+.4f}")
    print(f"  Extinction flags:    {result.extinction_flags or 'none'}")
    print(f"  Oscillation:         {result.viability_oscillation:.4f}")
    print(f"  Hash:                {result.deliberation_hash}")
