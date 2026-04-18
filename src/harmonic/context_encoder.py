"""
SCBE Context Encoder (Layers 1-4)
=================================
Bridge RWP v3 Sacred Tongue tokens into SCBE hyperbolic embeddings.
"""

from typing import Dict, List

import numpy as np

from crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER, TONGUES


class SCBEContextEncoder:
    """
    Layer 1-4 bridge: Sacred Tongue tokens -> complex context -> Poincare ball.
    """

    def __init__(self):
        self.tokenizer = SACRED_TONGUE_TOKENIZER
        self.tongues = TONGUES

    def tokens_to_complex_context(
        self,
        section_tokens: Dict[str, List[str]],
        dimension: int = 6,
    ) -> np.ndarray:
        """
        Convert Sacred Tongue tokens to a 6D complex context vector (Layer 1).

        Dimensions map to the six tongues:
        0: Kor'aelin (nonce), 1: Avali (aad), 2: Runethic (salt),
        3: Cassisivadan (ct), 4: Umbroth (redact), 5: Draumric (tag).
        """
        context = np.zeros(dimension, dtype=complex)

        tongue_map = ["ko", "av", "ru", "ca", "um", "dr"]
        section_map = {
            "nonce": 0,
            "aad": 1,
            "salt": 2,
            "ct": 3,
            "redact": 4,
            "tag": 5,
        }

        for section, tokens in section_tokens.items():
            if not tokens or section not in section_map:
                continue

            idx = section_map[section]
            tongue_code = tongue_map[idx]

            amplitude = len(tokens) / 256.0
            phase = self.tokenizer.compute_harmonic_fingerprint(tongue_code, tokens)
            phase = (phase % (2 * np.pi)) - np.pi

            context[idx] = amplitude * np.exp(1j * phase)

        return context

    def complex_to_real_embedding(self, c: np.ndarray) -> np.ndarray:
        """
        Layer 2: Realification c in C^D -> x in R^(2D).
        """
        return np.concatenate([np.real(c), np.imag(c)])

    def apply_langues_weighting(self, x: np.ndarray) -> np.ndarray:
        """
        Layer 3: Apply Langues metric weighting (diagonal approximation).
        Weights follow the phi-scaled tongue hierarchy: KO=φ^0 … DR=φ^5.
        Each tongue's real and imaginary components carry equal weight.
        """
        _phi = 1.618033988749895
        # KO=1.00, AV=1.618, RU=2.618, CA=4.236, UM=6.854, DR=11.090
        tongue_weights = np.array([_phi**i for i in range(6)])
        # 12D: real parts first (6), then imaginary parts (6)
        weights = np.concatenate([tongue_weights, tongue_weights])
        return weights[: len(x)] * x

    def embed_to_poincare_ball(self, x_weighted: np.ndarray, alpha: float = 1.5) -> np.ndarray:
        """
        Layer 4: Embed into Poincare ball.
        """
        norm = np.linalg.norm(x_weighted)
        if norm < 1e-10:
            return x_weighted

        scale = np.tanh(alpha * norm) / norm
        u = scale * x_weighted

        u_norm = np.linalg.norm(u)
        if u_norm >= 0.9999:
            u = u / u_norm * 0.9999

        return u

    def full_pipeline(self, envelope_dict: Dict[str, List[str]]) -> np.ndarray:
        """
        Complete Layer 1-4 pipeline: RWP envelope -> Poincare ball embedding.
        """
        section_tokens = {
            k: v for k, v in envelope_dict.items() if k in ["aad", "salt", "nonce", "ct", "tag", "redact"]
        }

        if "redact" not in section_tokens and envelope_dict.get("ml_kem_ct"):
            section_tokens["redact"] = envelope_dict["ml_kem_ct"]

        c = self.tokens_to_complex_context(section_tokens)
        x = self.complex_to_real_embedding(c)
        x_weighted = self.apply_langues_weighting(x)
        return self.embed_to_poincare_ball(x_weighted)
