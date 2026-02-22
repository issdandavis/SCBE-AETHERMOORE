"""Sacred Egg Integrator — Ritual-Based Secret Distribution (Chapter 7)

Bridges GeoSeal context-bound encryption with Sacred Tongue tokenization
and ritual-gated access control. A Sacred Egg unlocks only when specific
geometric, linguistic, and temporal conditions align.

Three ritual modes:
  - solitary:     Agent's tongue must match egg's primary_tongue
  - triadic:      3+ tongues with combined phi-weight >= threshold
  - ring_descent: Agent must have traversed rings monotonically inward

On failure, returns noise tokens of identical length (fail-to-noise).

Integrates:
  - cli_toolkit: CrossTokenizer, ConcentricRingPolicy, geoseal_encrypt/decrypt
  - sacred_eggs.py: predicate-gated AEAD foundation
  - sacred_eggs_ref.py: patent-hardened decrypt-or-noise semantics

@layer Layer 12, Layer 13
@component Sacred Egg Integrator
@version 1.0.0
@patent USPTO #63/961,403
"""

from __future__ import annotations

import base64
import copy
import dataclasses
import hashlib
import json
import math
import os
from typing import Dict, List, Optional, Tuple

# Import from cli_toolkit (the canonical Six-Tongues + GeoSeal module)
from src.symphonic_cipher.scbe_aethermoore.cli_toolkit import (
    CrossTokenizer,
    ConcentricRingPolicy,
    TongueTokenizer,
    Lexicons,
    XlateAttestation,
    geoseal_encrypt,
    geoseal_decrypt,
    project_to_sphere,
    project_to_cube,
    healpix_id,
    morton_id,
    potentials,
    classify,
    TONGUES,
)

# Ring ordering for ring_descent validation
_RING_ORDER: Dict[str, int] = {
    "core": 0,
    "inner": 1,
    "middle": 2,
    "outer": 3,
    "edge": 4,
}


# =============================================================================
# Data Structures
# =============================================================================


@dataclasses.dataclass(frozen=True)
class SacredEgg:
    """A GeoSeal-encrypted payload with ritual access conditions.

    Biological egg anatomy:
        shell:   Public identifier (egg_id + glyph) — safe to share, reveals nothing
        yolk:    The encrypted secret payload (yolk_ct.ct_spec) — the core
        white:   Context-derived key material (yolk_ct.ct_k + attest) — the albumen
        whole:   The complete egg structure — all parts bound by GeoSeal signature

    Attributes:
        egg_id:          SHA-256 of envelope (first 16 hex chars) — the SHELL hash
        primary_tongue:  Required tongue for solitary hatch (KO/AV/RU/CA/UM/DR)
        glyph:           Visual symbol for the egg — SHELL decoration
        hatch_condition: Ritual requirements dict:
                          - ring: required trust ring name
                          - path: required geometric classification ("interior"/"exterior")
                          - min_tongues: minimum tongue count for triadic
                          - min_weight: minimum cumulative phi-weight for triadic
        yolk_ct:         GeoSeal envelope dict (ct_k, ct_spec, attest, sig)
    """
    egg_id: str
    primary_tongue: str
    glyph: str
    hatch_condition: dict
    yolk_ct: dict

    # --- Biological anatomy accessors ---

    @property
    def shell(self) -> dict:
        """The SHELL: public-safe identifier. Can be shared without leaking secrets."""
        return {
            "egg_id": self.egg_id,
            "glyph": self.glyph,
            "primary_tongue": self.primary_tongue,
            "hatch_condition": self.hatch_condition,
        }

    @property
    def yolk(self) -> bytes:
        """The YOLK: encrypted secret payload (ciphertext). Meaningless without keys."""
        ct_spec = self.yolk_ct.get("ct_spec", "")
        return base64.b64decode(ct_spec) if ct_spec else b""

    @property
    def white(self) -> dict:
        """The WHITE (albumen): context-derived key material and geometric attestation."""
        return {
            "ct_k": self.yolk_ct.get("ct_k", ""),
            "attest": self.yolk_ct.get("attest", {}),
        }

    @property
    def whole(self) -> dict:
        """The WHOLE egg: complete structure with all parts and signature."""
        return {
            "shell": self.shell,
            "yolk": base64.b64encode(self.yolk).decode(),
            "white": self.white,
            "sig": self.yolk_ct.get("sig", ""),
        }


@dataclasses.dataclass(frozen=True)
class HatchResult:
    """Result of attempting to hatch a Sacred Egg.

    On success: tokens contain the decoded payload in the agent's tongue.
    On failure: tokens contain noise of identical length (fail-to-noise).
    The reason field is always either "hatched" or "sealed" — no specifics
    about which condition failed (oracle safety).
    """
    success: bool
    tokens: Optional[List[str]]
    attestation: Optional[dict]
    reason: str  # "sealed" or "hatched" — never reveals which predicate failed


# =============================================================================
# Helpers
# =============================================================================


def context_radius(ctx: List[float]) -> float:
    """Deterministic proxy radius derived from context vector, clamped to [0, 1).

    Uses the cube projection (tanh normalization) averaged across dimensions
    to produce a stable scalar in [0, 1).
    """
    v = project_to_cube(ctx, m=6)
    r = sum(v) / len(v)
    return min(0.999999, max(0.0, float(r)))


def _sealed_noise_tokens(
    xt: CrossTokenizer, tongue: str, nbytes: int
) -> List[str]:
    """Generate random noise tokens of exact byte-length.

    The output is indistinguishable from real token output to an observer
    who doesn't hold the decryption key.
    """
    noise = os.urandom(max(1, nbytes))
    return xt.tok.encode_bytes(tongue, noise)


# =============================================================================
# SacredEggIntegrator
# =============================================================================


class SacredEggIntegrator:
    """Bridges GeoSeal encryption with Sacred Tongue tokenization and rituals.

    Usage:
        lex = Lexicons()
        tok = TongueTokenizer(lex)
        xt = CrossTokenizer(tok)
        integrator = SacredEggIntegrator(xt)

        # Create
        egg = integrator.create_egg(payload, "KO", "diamond",
                                     {"ring": "inner", "path": "interior"},
                                     context, pk_kem_b64, sk_dsa_b64)

        # Hatch
        result = integrator.hatch_egg(egg, context, "KO", sk_kem_b64, pk_dsa_b64)
    """

    def __init__(self, xt: CrossTokenizer):
        self.xt = xt
        self.ring_policy = ConcentricRingPolicy()

    def create_egg(
        self,
        payload: bytes,
        primary_tongue: str,
        glyph: str,
        hatch_condition: dict,
        context: List[float],
        pk_kem_b64: str,
        sk_dsa_b64: str,
    ) -> SacredEgg:
        """Encrypt payload with GeoSeal and bind to ritual conditions.

        Args:
            payload:         Raw bytes to encrypt
            primary_tongue:  Tongue identity bound to this egg (KO/AV/RU/CA/UM/DR)
            glyph:           Visual symbol for display
            hatch_condition: Dict with optional keys: ring, path, min_tongues, min_weight
            context:         6D float vector for GeoSeal context binding
            pk_kem_b64:      Base64-encoded KEM public key
            sk_dsa_b64:      Base64-encoded DSA signing key

        Returns:
            A sealed SacredEgg
        """
        if primary_tongue not in TONGUES:
            raise ValueError(f"Unknown tongue: {primary_tongue}")

        pt_b64 = base64.b64encode(payload).decode()
        env = geoseal_encrypt(pt_b64, context, pk_kem_b64, sk_dsa_b64)
        egg_id = hashlib.sha256(
            json.dumps(env, sort_keys=True).encode()
        ).hexdigest()[:16]

        return SacredEgg(
            egg_id=egg_id,
            primary_tongue=primary_tongue,
            glyph=glyph,
            hatch_condition=dict(hatch_condition),
            yolk_ct=env,
        )

    def hatch_egg(
        self,
        egg: SacredEgg,
        current_context: List[float],
        agent_tongue: str,
        sk_kem_b64: str,
        pk_dsa_b64: str,
        ritual_mode: str = "solitary",
        additional_tongues: Optional[List[str]] = None,
        path_history: Optional[List[dict]] = None,
    ) -> HatchResult:
        """Attempt to hatch a Sacred Egg under ritual conditions.

        All failure modes return identical-format HatchResult with noise tokens.
        No information leaks about which condition failed (Theorem 7.1).

        Args:
            egg:                The Sacred Egg to hatch
            current_context:    Agent's current 6D context vector
            agent_tongue:       Agent's active Sacred Tongue
            sk_kem_b64:         Base64-encoded KEM secret key
            pk_dsa_b64:         Base64-encoded DSA verification key
            ritual_mode:        "solitary", "triadic", or "ring_descent"
            additional_tongues: Extra tongues for triadic mode
            path_history:       Ring traversal history for ring_descent mode

        Returns:
            HatchResult — success=True with real tokens, or success=False with noise
        """
        # Compute geometric classification from context
        r = context_radius(current_context)
        ring_info = self.ring_policy.classify(r)
        current_ring = ring_info.get("ring", "beyond")

        u = project_to_sphere(current_context)
        v = project_to_cube(current_context)
        h = healpix_id(u, 2)
        z = morton_id(v, 2)
        P, margin = potentials(u, v)
        path = classify(h, z, P, margin)

        # Pre-compute noise output length for consistent fail-to-noise
        ct_spec_b64 = egg.yolk_ct.get("ct_spec", "")
        ct_spec_len = len(base64.b64decode(ct_spec_b64)) if ct_spec_b64 else 16
        fail_tokens = _sealed_noise_tokens(self.xt, agent_tongue, nbytes=ct_spec_len)

        # --- Enforce hatch conditions (geometric) ---

        required_path = egg.hatch_condition.get("path")
        if required_path is not None and path != required_path:
            return HatchResult(False, fail_tokens, None, "sealed")

        required_ring = egg.hatch_condition.get("ring")
        if required_ring is not None and current_ring != required_ring:
            return HatchResult(False, fail_tokens, None, "sealed")

        # --- Enforce ritual predicates ---

        if ritual_mode == "solitary":
            if agent_tongue != egg.primary_tongue:
                return HatchResult(False, fail_tokens, None, "sealed")

        elif ritual_mode == "triadic":
            tongues = [egg.primary_tongue] + (additional_tongues or [])
            min_tongues = int(egg.hatch_condition.get("min_tongues", 3))
            if len(tongues) < min_tongues:
                return HatchResult(False, fail_tokens, None, "sealed")
            weight_sum = sum(
                self.xt.WEIGHT.get(t, 0.0) for t in tongues
            )
            min_weight = float(egg.hatch_condition.get("min_weight", 10.0))
            if weight_sum < min_weight:
                return HatchResult(False, fail_tokens, None, "sealed")

        elif ritual_mode == "ring_descent":
            history = path_history or []
            if len(history) < 1:
                return HatchResult(False, fail_tokens, None, "sealed")
            try:
                for i in range(len(history) - 1):
                    cur_ord = _RING_ORDER.get(history[i]["ring"], 99)
                    nxt_ord = _RING_ORDER.get(history[i + 1]["ring"], 99)
                    if cur_ord <= nxt_ord:
                        # Not monotonically inward
                        return HatchResult(False, fail_tokens, None, "sealed")
            except (KeyError, TypeError):
                return HatchResult(False, fail_tokens, None, "sealed")
            if current_ring != "core":
                return HatchResult(False, fail_tokens, None, "sealed")

        else:
            # Unknown ritual mode
            return HatchResult(False, fail_tokens, None, "sealed")

        # --- Context-bound GeoSeal decrypt ---

        ok, yolk_bytes = geoseal_decrypt(
            egg.yolk_ct, current_context, sk_kem_b64, pk_dsa_b64
        )
        if not ok or yolk_bytes is None:
            return HatchResult(False, fail_tokens, None, "sealed")

        # --- Tokenize in primary tongue ---

        tokens_primary = self.xt.tok.encode_bytes(egg.primary_tongue, yolk_bytes)
        attest_out = copy.deepcopy(egg.yolk_ct["attest"])

        # --- Cross-tokenize if agent tongue differs ---

        if agent_tongue != egg.primary_tongue:
            token_text = " ".join(tokens_primary)
            tokens_dst, xlate_attest = self.xt.retokenize(
                egg.primary_tongue, agent_tongue, token_text
            )
            attest_out["xlate"] = dataclasses.asdict(xlate_attest)
            return HatchResult(True, tokens_dst, attest_out, "hatched")

        return HatchResult(True, tokens_primary, attest_out, "hatched")

    @staticmethod
    def paint_egg(
        egg: SacredEgg,
        glyph: Optional[str] = None,
        hatch_condition: Optional[dict] = None,
    ) -> SacredEgg:
        """Paint an egg — customize the shell while keeping the yolk intact.

        Like painting an Easter egg: the outside changes, the inside stays
        exactly the same. The egg_id (derived from yolk_ct) doesn't change.

        Args:
            egg:              The egg to paint
            glyph:            New visual symbol (None = keep current)
            hatch_condition:  New hatch conditions (None = keep current)

        Returns:
            A new SacredEgg with the updated shell
        """
        return SacredEgg(
            egg_id=egg.egg_id,
            primary_tongue=egg.primary_tongue,
            glyph=glyph if glyph is not None else egg.glyph,
            hatch_condition=(
                dict(hatch_condition) if hatch_condition is not None
                else dict(egg.hatch_condition)
            ),
            yolk_ct=egg.yolk_ct,
        )

    def to_json(self, egg: SacredEgg) -> str:
        """Serialize a Sacred Egg to JSON."""
        return json.dumps(dataclasses.asdict(egg), indent=2, sort_keys=True)

    def from_json(self, data: str) -> SacredEgg:
        """Deserialize a Sacred Egg from JSON."""
        d = json.loads(data)
        return SacredEgg(**d)
