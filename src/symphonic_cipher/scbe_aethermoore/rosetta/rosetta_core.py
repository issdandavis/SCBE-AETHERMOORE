"""Rosetta Core — Concept Mapping Engine.

Maps concepts across natural languages (EN, ZH, JA, KO), conlangs
(Toki Pona, Esperanto, Lojban), and Sacred Tongues using NSM semantic
primes as the universal concept base.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass, field
from typing import Optional

from .seed_data import (
    NSM_PRIMES,
    CJK_COGNATES,
    TOKIPONA_MAP,
    ESPERANTO_MAP,
    LOJBAN_MAP,
    SACRED_TONGUE_PRIMES,
    TAM_PROFILES,
    LANGUAGE_METADATA,
)

PHI = 1.618033988749895


@dataclass
class LanguageSystem:
    """Describes a language system in the Rosetta graph."""

    code: str           # "EN", "ZH", "JA", "KO", "KO_ST", "TOKIPONA"
    name: str           # "English", "Kor'aelin"
    family: str         # "germanic", "sinitic", "sacred", "conlang"
    script: str         # "latin", "cjk", "hangul", "sacred_token"
    vocab_size: int     # 256 (Sacred), 120 (Toki Pona), ~50000 (natural)

    @property
    def tam_type(self) -> str:
        """TAM prominence type from profile."""
        profile = TAM_PROFILES.get(self.code, {})
        return profile.get("prominence", "unknown")


@dataclass
class RosettaConcept:
    """A single concept mapped across languages."""

    concept_id: str                             # NSM prime name: "GOOD", "MOVE", "WANT"
    nsm_prime: bool = True                      # True for the 65 universal primes
    embedding_6d: list[float] = field(default_factory=lambda: [0.0] * 6)
    surfaces: dict[str, list[str]] = field(default_factory=dict)
    sacred_tokens: dict[str, list[str]] = field(default_factory=dict)
    tam_profile: dict = field(default_factory=dict)
    drift_log: list[dict] = field(default_factory=list)

    def add_surface(self, lang_code: str, forms: list[str]) -> None:
        self.surfaces[lang_code] = forms

    def add_sacred(self, tongue_code: str, tokens: list[str]) -> None:
        self.sacred_tokens[tongue_code] = tokens

    def log_drift(self, lang_a: str, lang_b: str, drift: float, note: str = "") -> None:
        self.drift_log.append({
            "lang_a": lang_a, "lang_b": lang_b,
            "drift": drift, "note": note,
            "timestamp": time.time(),
        })


class RosettaStone:
    """Core concept mapping engine.

    Loads seed data and provides lookup, translation, embedding, and
    drift scoring across all registered language systems.
    """

    def __init__(self) -> None:
        self._languages: dict[str, LanguageSystem] = {}
        self._concepts: dict[str, RosettaConcept] = {}
        self._conlang_maps: dict[str, dict[str, str]] = {
            "TOKIPONA": TOKIPONA_MAP,
            "ESPERANTO": ESPERANTO_MAP,
            "LOJBAN": LOJBAN_MAP,
        }
        self._load_languages()
        self._load_nsm_primes()

    # ── Bootstrap ──────────────────────────────────────────

    def _load_languages(self) -> None:
        for code, meta in LANGUAGE_METADATA.items():
            self._languages[code] = LanguageSystem(
                code=code,
                name=meta["name"],
                family=meta["family"],
                script=meta["script"],
                vocab_size=meta["vocab_size"],
            )

    def _load_nsm_primes(self) -> None:
        for concept_id, lang_surfaces in NSM_PRIMES.items():
            concept = RosettaConcept(
                concept_id=concept_id,
                nsm_prime=True,
                embedding_6d=self._concept_embedding(concept_id),
            )
            # Natural language surfaces
            for lang, forms in lang_surfaces.items():
                concept.add_surface(lang, forms)

            # Conlang surfaces
            for conlang, mapping in self._conlang_maps.items():
                if concept_id in mapping:
                    concept.add_surface(conlang, [mapping[concept_id]])

            # Sacred Tongue tokens
            if concept_id in SACRED_TONGUE_PRIMES:
                for tongue, token in SACRED_TONGUE_PRIMES[concept_id].items():
                    st_code = f"{tongue}_ST"
                    concept.add_sacred(tongue, [token])
                    concept.add_surface(st_code, [token])

            # TAM info
            concept.tam_profile = {
                lang: TAM_PROFILES.get(lang, {})
                for lang in concept.surfaces
                if lang in TAM_PROFILES
            }

            self._concepts[concept_id] = concept

    def _concept_embedding(self, concept_id: str) -> list[float]:
        """Generate a deterministic 6D Poincare ball embedding from concept ID.

        Uses hash-based projection into the unit ball (norm < 1).
        """
        h = hashlib.sha256(concept_id.encode()).digest()
        raw = [int.from_bytes(h[i*4:(i+1)*4], "little") / (2**32) for i in range(6)]
        # Scale into Poincare ball (norm < 0.95)
        norm = math.sqrt(sum(x**2 for x in raw))
        if norm == 0:
            return [0.0] * 6
        scale = 0.9 / norm
        return [x * scale for x in raw]

    # ── Public API ─────────────────────────────────────────

    def add_language(self, lang: LanguageSystem) -> None:
        self._languages[lang.code] = lang

    def add_concept(self, concept: RosettaConcept) -> None:
        self._concepts[concept.concept_id] = concept

    def add_mapping(self, concept_id: str, lang_code: str, forms: list[str]) -> bool:
        """Add surface forms for a concept in a language. Returns True if concept exists."""
        if concept_id not in self._concepts:
            return False
        self._concepts[concept_id].add_surface(lang_code, forms)
        return True

    def get_languages(self) -> list[LanguageSystem]:
        return list(self._languages.values())

    def get_language(self, code: str) -> Optional[LanguageSystem]:
        return self._languages.get(code)

    def get_concept(self, concept_id: str) -> Optional[RosettaConcept]:
        return self._concepts.get(concept_id)

    def list_concepts(self) -> list[str]:
        return sorted(self._concepts.keys())

    def lookup(self, concept_id: str, lang_code: str) -> list[str]:
        """Look up surface forms for a concept in a specific language."""
        concept = self._concepts.get(concept_id)
        if concept is None:
            return []
        return concept.surfaces.get(lang_code, [])

    def translate(self, concept_id: str, src: str, dst: str) -> dict:
        """Translate a concept between two languages.

        Returns dict with src_forms, dst_forms, drift_score, and tam_info.
        """
        concept = self._concepts.get(concept_id)
        if concept is None:
            return {"error": f"Unknown concept: {concept_id}"}

        src_forms = concept.surfaces.get(src, [])
        dst_forms = concept.surfaces.get(dst, [])
        drift = self.drift_score(concept_id, src, dst)

        return {
            "concept_id": concept_id,
            "src": src,
            "dst": dst,
            "src_forms": src_forms,
            "dst_forms": dst_forms,
            "drift_score": drift,
            "tam_src": TAM_PROFILES.get(src, {}),
            "tam_dst": TAM_PROFILES.get(dst, {}),
        }

    def find_cognates(self, word: str, src_lang: str) -> list[RosettaConcept]:
        """Find concepts that contain the given word as a surface form."""
        results = []
        word_lower = word.lower()
        for concept in self._concepts.values():
            forms = concept.surfaces.get(src_lang, [])
            for f in forms:
                if word_lower in f.lower():
                    results.append(concept)
                    break
        return results

    def find_cjk_cognate(self, character: str) -> Optional[dict]:
        """Look up a CJK cognate entry by character."""
        return CJK_COGNATES.get(character)

    def embed(self, concept_id: str) -> list[float]:
        """Get the 6D Poincare ball embedding for a concept."""
        concept = self._concepts.get(concept_id)
        if concept is None:
            return [0.0] * 6
        return concept.embedding_6d

    def drift_score(self, concept_id: str, lang_a: str, lang_b: str) -> float:
        """Compute semantic drift score between two languages for a concept.

        Uses a simple heuristic based on:
        - Family distance (same family = low drift)
        - Script overlap
        - Surface form count mismatch
        Returns a float in [0, 1] where 1 = maximum drift.
        """
        concept = self._concepts.get(concept_id)
        if concept is None:
            return 1.0

        la = self._languages.get(lang_a)
        lb = self._languages.get(lang_b)
        if la is None or lb is None:
            return 1.0

        score = 0.0

        # Family distance
        if la.family == lb.family:
            score += 0.0
        elif {la.family, lb.family} & {"sacred", "conlang"}:
            score += 0.3
        else:
            score += 0.2

        # Script mismatch
        if la.script != lb.script:
            score += 0.15

        # Surface form count divergence
        forms_a = concept.surfaces.get(lang_a, [])
        forms_b = concept.surfaces.get(lang_b, [])
        if forms_a and forms_b:
            ratio = abs(len(forms_a) - len(forms_b)) / max(len(forms_a), len(forms_b))
            score += ratio * 0.15
        elif not forms_a or not forms_b:
            score += 0.3  # One side missing

        # TAM mismatch
        tam_a = TAM_PROFILES.get(lang_a, {}).get("prominence", "")
        tam_b = TAM_PROFILES.get(lang_b, {}).get("prominence", "")
        if tam_a and tam_b and tam_a != tam_b:
            score += 0.1

        return min(score, 1.0)

    def tam_profile(self, lang_code: str) -> dict:
        """Get the TAM (Tense/Aspect/Mood) profile for a language."""
        return TAM_PROFILES.get(lang_code, {})

    def export_sft(self, format: str = "jsonl") -> str:
        """Export all concept mappings as SFT training data.

        Each concept becomes one training record.
        """
        records = []
        for cid, concept in sorted(self._concepts.items()):
            record = {
                "id": f"rosetta-{cid.lower()}-001",
                "category": "rosetta-concept",
                "instruction": f"What are the surface forms for the concept '{cid}' across all registered languages?",
                "response": json.dumps({
                    "concept_id": cid,
                    "nsm_prime": concept.nsm_prime,
                    "surfaces": concept.surfaces,
                    "sacred_tokens": concept.sacred_tokens,
                }, ensure_ascii=False),
                "metadata": {
                    "source": "scbe_aethermoore",
                    "version": "4.0.0",
                    "type": "concept_mapping",
                },
            }
            records.append(record)

        # Add CJK cognate records
        for char, data in sorted(CJK_COGNATES.items()):
            record = {
                "id": f"rosetta-cjk-{hashlib.md5(char.encode()).hexdigest()[:6]}",
                "category": "rosetta-cognate",
                "instruction": f"What are the readings of the CJK character '{char}' across Chinese, Japanese, and Korean?",
                "response": json.dumps(data, ensure_ascii=False),
                "metadata": {
                    "source": "scbe_aethermoore",
                    "version": "4.0.0",
                    "type": "cognate_mapping",
                },
            }
            records.append(record)

        if format == "json":
            return json.dumps(records, indent=2, ensure_ascii=False)

        # JSONL
        lines = [json.dumps(r, ensure_ascii=False) for r in records]
        return "\n".join(lines)
