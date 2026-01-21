"""
Spectral Identity System - Rainbow Chromatic Fingerprinting

Maps multi-dimensional trust/context vectors to unique color signatures.
Like light through a prism - each entity gets a unique spectral fingerprint
that humans can visually verify.

Color Mapping to SCBE Layers:
- Red (620-750nm)    → Layer 1-2: Context/Metric (danger/identity)
- Orange (590-620nm) → Layer 3-4: Breath/Phase (temporal)
- Yellow (570-590nm) → Layer 5-6: Potential/Spectral (energy)
- Green (495-570nm)  → Layer 7-8: Spin/Triadic (verification)
- Blue (450-495nm)   → Layer 9-10: Harmonic/Decision (trust)
- Indigo (420-450nm) → Layer 11-12: Audio/Quantum (deep security)
- Violet (380-420nm) → Layer 13-14: Anti-Fragile/CFI (integrity)

Sacred Tongue Color Associations:
- Koraelin (KO)     → Deep Red (#8B0000)
- Avali (AV)        → Amber (#FFBF00)
- Runethic (RU)     → Emerald (#50C878)
- Cassisivadan (CA) → Sapphire (#0F52BA)
- Umbroth (UM)      → Amethyst (#9966CC)
- Draumric (DR)     → Obsidian (#3D3D3D)

@module harmonic/spectral_identity
"""

from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
import math
import time


@dataclass
class RGB:
    """RGB color representation"""
    r: int  # 0-255
    g: int  # 0-255
    b: int  # 0-255
    
    def to_hex(self) -> str:
        """Convert to hex string"""
        return f"#{self.r:02X}{self.g:02X}{self.b:02X}"


@dataclass
class HSL:
    """HSL color representation"""
    h: float  # 0-360 (hue)
    s: float  # 0-100 (saturation)
    l: float  # 0-100 (lightness)


@dataclass
class SpectralBand:
    """Spectral band definition"""
    name: str
    wavelength_min: float  # nm
    wavelength_max: float  # nm
    hue_min: float         # degrees
    hue_max: float         # degrees
    layers: List[int]      # Associated SCBE layers
    sacred_tongue: Optional[str] = None  # Associated Sacred Tongue


@dataclass
class SpectralIdentity:
    """Complete spectral identity"""
    entity_id: str
    primary_color: RGB
    secondary_color: RGB
    spectrum: List[float]  # 7-band intensities
    tongue_signature: List[RGB]  # 6-tongue colors
    hex_code: str
    color_name: str
    spectral_hash: str
    confidence: str  # 'HIGH', 'MEDIUM', 'LOW'
    timestamp: float


# The 7 spectral bands (ROYGBIV)
SPECTRAL_BANDS: List[SpectralBand] = [
    SpectralBand('Red',    620, 750, 0,   15,  [1, 2],   'KO'),
    SpectralBand('Orange', 590, 620, 15,  45,  [3, 4],   'AV'),
    SpectralBand('Yellow', 570, 590, 45,  65,  [5, 6],   'RU'),
    SpectralBand('Green',  495, 570, 65,  165, [7, 8],   'CA'),
    SpectralBand('Blue',   450, 495, 165, 250, [9, 10],  'UM'),
    SpectralBand('Indigo', 420, 450, 250, 275, [11, 12], 'DR'),
    SpectralBand('Violet', 380, 420, 275, 300, [13, 14], None),
]

# Sacred Tongue base colors
TONGUE_COLORS: Dict[str, RGB] = {
    'KO': RGB(139, 0,   0),    # Deep Red
    'AV': RGB(255, 191, 0),    # Amber
    'RU': RGB(80,  200, 120),  # Emerald
    'CA': RGB(15,  82,  186),  # Sapphire
    'UM': RGB(153, 102, 204),  # Amethyst
    'DR': RGB(61,  61,  61),   # Obsidian
}


class SpectralIdentityGenerator:
    """
    Spectral Identity Generator
    
    Creates unique chromatic fingerprints from multi-dimensional vectors.
    """
    
    GOLDEN_RATIO = 1.618033988749895
    
    def generate_identity(
        self,
        entity_id: str,
        trust_vector: List[float],
        layer_scores: Optional[List[float]] = None
    ) -> SpectralIdentity:
        """
        Generate spectral identity from a 6D trust vector.
        
        Args:
            entity_id: Unique entity identifier
            trust_vector: 6D trust vector (one per Sacred Tongue)
            layer_scores: Optional 14-layer scores
            
        Returns:
            Complete spectral identity
        """
        if len(trust_vector) != 6:
            raise ValueError('Trust vector must have 6 dimensions (one per Sacred Tongue)')
        
        # Normalize trust vector to [0, 1]
        normalized = [max(0.0, min(1.0, v)) for v in trust_vector]
        
        # Generate 7-band spectrum from trust vector + layer scores
        spectrum = self._generate_spectrum(normalized, layer_scores)
        
        # Generate tongue-specific colors
        tongue_signature = self._generate_tongue_signature(normalized)
        
        # Compute primary and secondary colors
        primary, secondary = self._compute_dominant_colors(spectrum)
        
        # Generate combined color
        combined = self._blend_colors(tongue_signature, normalized)
        
        # Generate spectral hash
        spectral_hash = self._generate_spectral_hash(entity_id, normalized, spectrum)
        
        # Determine confidence based on vector variance
        confidence = self._compute_confidence(normalized)
        
        return SpectralIdentity(
            entity_id=entity_id,
            primary_color=primary,
            secondary_color=secondary,
            spectrum=spectrum,
            tongue_signature=tongue_signature,
            hex_code=combined.to_hex(),
            color_name=self._generate_color_name(combined, spectrum),
            spectral_hash=spectral_hash,
            confidence=confidence,
            timestamp=time.time()
        )
    
    def _generate_spectrum(
        self,
        trust_vector: List[float],
        layer_scores: Optional[List[float]] = None
    ) -> List[float]:
        """Generate 7-band spectrum from trust vector"""
        spectrum: List[float] = []
        
        for band in range(7):
            if band < 6:
                # First 6 bands map to Sacred Tongues
                intensity = trust_vector[band]
            else:
                # 7th band (Violet) is average of all
                intensity = sum(trust_vector) / 6
            
            # Modulate with layer scores if available
            if layer_scores and len(layer_scores) >= 14:
                band_layers = SPECTRAL_BANDS[band].layers
                layer_avg = sum(layer_scores[l - 1] for l in band_layers) / len(band_layers)
                intensity = (intensity + layer_avg) / 2
            
            # Apply golden ratio modulation for uniqueness
            intensity = intensity * (1 + 0.1 * math.sin(band * self.GOLDEN_RATIO * math.pi))
            
            spectrum.append(max(0.0, min(1.0, intensity)))
        
        return spectrum
    
    def _generate_tongue_signature(self, trust_vector: List[float]) -> List[RGB]:
        """Generate Sacred Tongue color signature"""
        tongues = ['KO', 'AV', 'RU', 'CA', 'UM', 'DR']
        signature: List[RGB] = []
        
        for i, tongue in enumerate(tongues):
            base = TONGUE_COLORS[tongue]
            intensity = trust_vector[i]
            
            # Modulate base color by trust intensity
            signature.append(RGB(
                r=round(base.r * (0.3 + 0.7 * intensity)),
                g=round(base.g * (0.3 + 0.7 * intensity)),
                b=round(base.b * (0.3 + 0.7 * intensity))
            ))
        
        return signature
    
    def _compute_dominant_colors(self, spectrum: List[float]) -> Tuple[RGB, RGB]:
        """Compute dominant colors from spectrum"""
        # Find top 2 bands
        indexed = [(v, i) for i, v in enumerate(spectrum)]
        indexed.sort(key=lambda x: x[0], reverse=True)
        
        primary_band = SPECTRAL_BANDS[indexed[0][1]]
        secondary_band = SPECTRAL_BANDS[indexed[1][1]]
        
        return (
            self._band_to_rgb(primary_band, indexed[0][0]),
            self._band_to_rgb(secondary_band, indexed[1][0])
        )
    
    def _band_to_rgb(self, band: SpectralBand, intensity: float) -> RGB:
        """Convert spectral band to RGB"""
        hue = (band.hue_min + band.hue_max) / 2
        saturation = 70 + 30 * intensity
        lightness = 30 + 40 * intensity
        
        return self._hsl_to_rgb(HSL(hue, saturation, lightness))
    
    def _blend_colors(self, tongue_signature: List[RGB], weights: List[float]) -> RGB:
        """Blend tongue colors weighted by trust vector"""
        r, g, b = 0.0, 0.0, 0.0
        total_weight = 0.0
        
        for i in range(6):
            weight = weights[i] + 0.1  # Minimum weight to include all tongues
            r += tongue_signature[i].r * weight
            g += tongue_signature[i].g * weight
            b += tongue_signature[i].b * weight
            total_weight += weight
        
        return RGB(
            r=round(r / total_weight),
            g=round(g / total_weight),
            b=round(b / total_weight)
        )
    
    def _generate_spectral_hash(
        self,
        entity_id: str,
        trust_vector: List[float],
        spectrum: List[float]
    ) -> str:
        """Generate unique spectral hash"""
        # Create deterministic hash from all inputs
        data = ':'.join([
            entity_id,
            *[f'{v:.6f}' for v in trust_vector],
            *[f'{v:.6f}' for v in spectrum]
        ])
        
        # Simple hash function
        hash_val = 0
        for char in data:
            hash_val = ((hash_val << 5) - hash_val) + ord(char)
            hash_val = hash_val & 0xFFFFFFFF  # Keep as 32-bit
        
        # Convert to hex and format
        hex_hash = f'{hash_val:08x}'
        return f'SP-{hex_hash[:4].upper()}-{hex_hash[4:8].upper()}'
    
    def _compute_confidence(self, trust_vector: List[float]) -> str:
        """Compute confidence based on vector variance"""
        mean = sum(trust_vector) / 6
        variance = sum((v - mean) ** 2 for v in trust_vector) / 6
        
        # Higher variance = more distinct = higher confidence
        if variance > 0.1:
            return 'HIGH'
        if variance > 0.05:
            return 'MEDIUM'
        return 'LOW'
    
    def _generate_color_name(self, color: RGB, spectrum: List[float]) -> str:
        """Generate human-readable color name"""
        # Find dominant band
        max_index = spectrum.index(max(spectrum))
        band_name = SPECTRAL_BANDS[max_index].name
        
        # Determine intensity modifier
        brightness = (color.r + color.g + color.b) / 3
        modifier = ''
        if brightness > 200:
            modifier = 'Bright '
        elif brightness > 150:
            modifier = 'Light '
        elif brightness < 80:
            modifier = 'Dark '
        elif brightness < 120:
            modifier = 'Deep '
        
        # Determine saturation modifier
        max_c = max(color.r, color.g, color.b)
        min_c = min(color.r, color.g, color.b)
        saturation = 0 if max_c == 0 else (max_c - min_c) / max_c
        
        if saturation < 0.2:
            return f'{modifier}Gray-{band_name}'
        if saturation > 0.8:
            return f'{modifier}Vivid {band_name}'
        
        return f'{modifier}{band_name}'
    
    def _hsl_to_rgb(self, hsl: HSL) -> RGB:
        """Convert HSL to RGB"""
        h = hsl.h / 360
        s = hsl.s / 100
        l = hsl.l / 100
        
        if s == 0:
            r = g = b = l
        else:
            def hue2rgb(p: float, q: float, t: float) -> float:
                if t < 0:
                    t += 1
                if t > 1:
                    t -= 1
                if t < 1/6:
                    return p + (q - p) * 6 * t
                if t < 1/2:
                    return q
                if t < 2/3:
                    return p + (q - p) * (2/3 - t) * 6
                return p
            
            q = l * (1 + s) if l < 0.5 else l + s - l * s
            p = 2 * l - q
            r = hue2rgb(p, q, h + 1/3)
            g = hue2rgb(p, q, h)
            b = hue2rgb(p, q, h - 1/3)
        
        return RGB(
            r=round(r * 255),
            g=round(g * 255),
            b=round(b * 255)
        )
    
    def compare_identities(self, a: SpectralIdentity, b: SpectralIdentity) -> float:
        """
        Compare two spectral identities for similarity.
        
        Returns:
            Similarity score 0-1 (1 = identical)
        """
        # Compare spectrums
        spectrum_diff = sum(abs(a.spectrum[i] - b.spectrum[i]) for i in range(7))
        spectrum_similarity = 1 - (spectrum_diff / 7)
        
        # Compare tongue signatures
        tongue_diff = 0.0
        for i in range(6):
            color_diff = (
                abs(a.tongue_signature[i].r - b.tongue_signature[i].r) +
                abs(a.tongue_signature[i].g - b.tongue_signature[i].g) +
                abs(a.tongue_signature[i].b - b.tongue_signature[i].b)
            ) / (255 * 3)
            tongue_diff += color_diff
        tongue_similarity = 1 - (tongue_diff / 6)
        
        # Weighted average
        return 0.6 * spectrum_similarity + 0.4 * tongue_similarity
    
    def generate_visual(self, identity: SpectralIdentity) -> str:
        """Generate visual representation (ASCII art)"""
        bars = []
        for i, intensity in enumerate(identity.spectrum):
            band = SPECTRAL_BANDS[i]
            bar_length = round(intensity * 20)
            bar = '█' * bar_length + '░' * (20 - bar_length)
            bars.append(f'{band.name:<7} {bar} {intensity * 100:.1f}%')
        
        lines = [
            '╔══════════════════════════════════════════╗',
            f'║  SPECTRAL IDENTITY: {identity.entity_id[:18]:<18} ║',
            '╠══════════════════════════════════════════╣',
            f'║  Color: {identity.hex_code} ({identity.color_name[:20]:<20}) ║',
            f'║  Hash:  {identity.spectral_hash:<30} ║',
            f'║  Confidence: {identity.confidence:<26} ║',
            '╠══════════════════════════════════════════╣',
            *[f'║  {b:<38} ║' for b in bars],
            '╚══════════════════════════════════════════╝'
        ]
        
        return '\n'.join(lines)


# Singleton instance
spectral_generator = SpectralIdentityGenerator()


# Convenience functions
def generate_spectral_identity(
    entity_id: str,
    trust_vector: List[float],
    layer_scores: Optional[List[float]] = None
) -> SpectralIdentity:
    """Generate spectral identity from trust vector"""
    return spectral_generator.generate_identity(entity_id, trust_vector, layer_scores)


def compare_spectral_identities(a: SpectralIdentity, b: SpectralIdentity) -> float:
    """Compare two spectral identities"""
    return spectral_generator.compare_identities(a, b)


def visualize_spectral_identity(identity: SpectralIdentity) -> str:
    """Generate ASCII visualization"""
    return spectral_generator.generate_visual(identity)
