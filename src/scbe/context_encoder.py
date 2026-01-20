"""
SCBE Context Encoder - Layer 1-4 Integration
=============================================
Bridge between RWP v3.0 Sacred Tongues and SCBE 14-layer governance

Last Updated: January 18, 2026
Version: 3.0.0

Flow:
1. RWP tokens → Spectral fingerprint (FFT of token frequencies)
2. Fingerprint → Complex amplitude/phase
3. Complex → Real (Layer 2 realification)
4. Real → Weighted (Layer 3 Langues metric)
5. Weighted → Poincaré ball (Layer 4 hyperbolic embedding)

Integration: Enables SCBE governance validation of RWP v3.0 envelopes
"""

import numpy as np
from typing import List, Dict, Optional
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crypto.sacred_tongues import SACRED_TONGUE_TOKENIZER, TONGUES


class SCBEContextEncoder:
    """
    Layer 1-4: Sacred Tongue tokens → Complex context vector → Hyperbolic embedding.
    
    Flow:
    1. RWP tokens → Spectral fingerprint (FFT of token frequencies)
    2. Fingerprint → Complex amplitude/phase
    3. Complex → Real (Layer 2 realification)
    4. Real → Weighted (Layer 3)
    5. Weighted → Poincaré ball (Layer 4)
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
        Convert Sacred Tongue tokens to 6D complex context vector (Layer 1).
        
        Each dimension corresponds to a Sacred Tongue's spectral signature:
        c[0] = Kor'aelin (nonce/intent)
        c[1] = Avali (aad/metadata)
        c[2] = Runethic (salt/binding)
        c[3] = Cassisivadan (ct/entropy)
        c[4] = Umbroth (redaction/veil)
        c[5] = Draumric (tag/integrity)
        
        Returns: Complex vector c ∈ ℂ^6 where c[i] = A[i] * exp(j*φ[i])
        """
        context = np.zeros(dimension, dtype=complex)
        
        tongue_map = ['ko', 'av', 'ru', 'ca', 'um', 'dr']
        section_map = {
            'nonce': 0, 'aad': 1, 'salt': 2, 
            'ct': 3, 'redact': 4, 'tag': 5
        }
        
        for section, tokens in section_tokens.items():
            if section not in section_map:
                continue
            
            idx = section_map[section]
            tongue_code = tongue_map[idx]
            
            # Compute amplitude from token count
            amplitude = len(tokens) / 256.0  # Normalize by max expected
            
            # Compute phase from harmonic fingerprint
            phase = self.tokenizer.compute_harmonic_fingerprint(tongue_code, tokens)
            phase = (phase % (2 * np.pi)) - np.pi  # Wrap to [-π, π]
            
            context[idx] = amplitude * np.exp(1j * phase)
        
        return context
    
    def complex_to_real_embedding(self, c: np.ndarray) -> np.ndarray:
        """
        Layer 2: Realification c ∈ ℂ^D → x ∈ ℝ^{2D}
        x = [Re(c[0]), Im(c[0]), Re(c[1]), Im(c[1]), ...]
        """
        real = np.real(c)
        imag = np.imag(c)
        return np.concatenate([real, imag])
    
    def apply_langues_weighting(self, x: np.ndarray) -> np.ndarray:
        """
        Layer 3: Apply Langues metric weighting.
        L(x,t) = Σ w_l * exp(β_l * d_l * sin(ω_l*t + φ_l))
        
        For now, simplified to diagonal weighting G = diag(w_1, ..., w_6)
        """
        # Default weights (can be derived from current threat level)
        weights = np.array([1.0, 1.1, 1.25, 1.33, 1.5, 1.66] * 2)  # 2D → 12D
        return weights[:len(x)] * x
    
    def embed_to_poincare_ball(self, x_weighted: np.ndarray, alpha: float = 1.5) -> np.ndarray:
        """
        Layer 4: Embed into Poincaré ball.
        u = tanh(α||x||) * x/||x||
        """
        norm = np.linalg.norm(x_weighted)
        if norm < 1e-10:
            return x_weighted  # Already at origin
        
        scale = np.tanh(alpha * norm) / norm
        u = scale * x_weighted
        
        # Clamp to ball boundary (safety)
        u_norm = np.linalg.norm(u)
        if u_norm >= 0.9999:
            u = u / u_norm * 0.9999
        
        return u
    
    def full_pipeline(self, envelope_dict: Dict) -> np.ndarray:
        """
        Complete Layer 1-4 pipeline: RWP envelope → Poincaré ball embedding.
        """
        # Extract tokens
        section_tokens = {
            k: v for k, v in envelope_dict.items()
            if k in ['aad', 'salt', 'nonce', 'ct', 'tag', 'redact']
        }
        
        # Layer 1: Tokens → Complex context
        c = self.tokens_to_complex_context(section_tokens)
        
        # Layer 2: Complex → Real
        x = self.complex_to_real_embedding(c)
        
        # Layer 3: Apply Langues weighting
        x_weighted = self.apply_langues_weighting(x)
        
        # Layer 4: Embed to Poincaré ball
        u = self.embed_to_poincare_ball(x_weighted)
        
        return u


# Singleton instance for global use
SCBE_CONTEXT_ENCODER = SCBEContextEncoder()
