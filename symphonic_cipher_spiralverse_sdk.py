"""
Spiralverse Protocol SDK - Six Sacred Tongues
Extracted from SCBE Production Pack demo_integrated_system.py

To use in GitHub repo:
1. Copy to: SCBE-AETHERMOORE/symphonic_cipher/spiralverse/sdk.py
2. Create: SCBE-AETHERMOORE/symphonic_cipher/spiralverse/__init__.py
3. Import: from symphonic_cipher.spiralverse import SpiralverseSDK, SacredTongue
"""

from dataclasses import dataclass
from typing import List, Tuple, Dict


@dataclass
class SacredTongue:
    """
    Definition of one of the Six Sacred Tongues.

    Each tongue represents a semantic domain with specific:
    - Cryptographic security level
    - Keywords for classification
    - Symbolic representation
    - Purpose in the system
    """
    code: str
    name: str
    domain: str
    function: str
    security_level: int
    keywords: List[str]
    symbols: List[str]

    def __repr__(self):
        return f"{self.code}({self.name}): {self.domain} - Level {self.security_level}"


class SpiralverseSDK:
    """
    Spiralverse Protocol SDK.

    Provides:
    1. Semantic domain classification (Six Sacred Tongues)
    2. Multi-signature consensus (Roundtable)
    3. Cryptographic provenance for training data

    The Six Sacred Tongues:
    - KO (Korvethian): Control & Orchestration
    - AV (Avethril): I/O & Messaging
    - RU (Runevast): Policy & Constraints
    - CA (Celestine): Logic & Computation
    - UM (Umbralis): Security & Privacy
    - DR (Draconic): Types & Structures
    """

    def __init__(self):
        """Initialize Spiralverse SDK with Six Sacred Tongues."""
        self.tongues = self._initialize_tongues()

    def _initialize_tongues(self) -> Dict[str, SacredTongue]:
        """
        Initialize the Six Sacred Tongues semantic framework.

        Each tongue maps to:
        - Kyber security level (1=512, 2=768, 3=1024)
        - Specific keywords for intent classification
        - Unicode symbols for visual representation
        """
        return {
            'KO': SacredTongue(
                code='KO',
                name='Korvethian',
                domain='Light/Logic',
                function='Control & Orchestration',
                security_level=1,  # Kyber-512 equivalent
                keywords=[
                    'patent', 'claim', 'technical', 'specification', 'algorithm',
                    'system', 'method', 'process', 'logic', 'proof',
                    'vel', 'sil', 'keth', 'return'
                ],
                symbols=['◇', '◆', '◈', '⬖', '⬗', '⬘', '⬙', '⬚', '⟐', '⟑', '⟢', '⟣', '⟤', '⟥', '⬡', '⬢']
            ),
            'AV': SacredTongue(
                code='AV',
                name='Avethril',
                domain='Air/Abstract',
                function='I/O & Messaging',
                security_level=2,  # Kyber-768 equivalent
                keywords=[
                    'quantum', 'threat', 'vulnerability', 'security', 'encryption',
                    'cryptographic', 'abstract', 'concept', 'theory',
                    'serin', 'nurel', 'lumenna'
                ],
                symbols=['◎', '◉', '○', '●', '◐', '◑', '◒', '◓', '◔', '◕', '◖', '◗', '◌', '◍', '◯', '⬤']
            ),
            'RU': SacredTongue(
                code='RU',
                name='Runevast',
                domain='Earth/Organic',
                function='Policy & Constraints',
                security_level=1,  # Kyber-512 equivalent
                keywords=[
                    'market', 'business', 'commercial', 'value', 'revenue',
                    'customer', 'growth', 'organic', 'natural', 'data',
                    'khar', 'drath', 'bront', 'ordinance'
                ],
                symbols=['▲', '▽', '◄', '►', '△', '▷', '◁', '▼', '▸', '◂', '▴', '▾', '◃', '▹', '⬟', '⬠']
            ),
            'CA': SacredTongue(
                code='CA',
                name='Celestine',
                domain='Fire/Emotional',
                function='Logic & Computation',
                security_level=3,  # Kyber-1024 equivalent
                keywords=[
                    'urgent', 'critical', 'immediate', 'priority', 'deadline',
                    'timeline', 'action', 'now', 'emergency', 'important',
                    'klik', 'spira', 'ifta', 'thena', 'elsa'
                ],
                symbols=['★', '☆', '✦', '✧', '✨', '✩', '✪', '✫', '✬', '✭', '✮', '✯', '✰', '⭐', '🌟', '💫']
            ),
            'UM': SacredTongue(
                code='UM',
                name='Umbralis',
                domain='Cosmos/Wisdom',
                function='Security & Privacy',
                security_level=2,  # Kyber-768 equivalent
                keywords=[
                    'strategy', 'recommendation', 'advice', 'wisdom', 'guidance',
                    'approach', 'plan', 'roadmap', 'vision', 'insight',
                    'veil', 'hollow', 'sandbox', 'narshul', 'secure'
                ],
                symbols=['✴', '✵', '✶', '✷', '✸', '✹', '✺', '✻', '✼', '✽', '❂', '❃', '❄', '❅', '❆', '❇']
            ),
            'DR': SacredTongue(
                code='DR',
                name='Draconic',
                domain='Water/Hidden',
                function='Types & Structures',
                security_level=3,  # Kyber-1024 equivalent
                keywords=[
                    'implementation', 'proprietary', 'secret', 'confidential',
                    'internal', 'hidden', 'private', 'protected', 'classified',
                    'tharn', 'anvil', 'seal', 'interface', 'struct'
                ],
                symbols=['◈', '◊', '⬥', '⬦', '⬧', '⬨', '⬩', '⬪', '⬫', '⬬', '⟠', '⟡', '⧫', '⬭', '⬮', '⬯']
            )
        }

    def classify_intent(self, message: str) -> Tuple[str, float]:
        """
        Classify a message into the most appropriate Sacred Tongue.

        Uses keyword matching to determine semantic domain.

        Args:
            message: Natural language message to classify

        Returns:
            (tongue_code, confidence_score)

        Examples:
            >>> sdk = SpiralverseSDK()
            >>> sdk.classify_intent("Execute delete command immediately")
            ('CA', 0.2)  # Celestine (urgent/critical keywords)
            >>> sdk.classify_intent("Retrieve user profile data")
            ('RU', 0.1)  # Runevast (data/business keywords)
        """
        scores = {}
        message_lower = message.lower()

        for code, tongue in self.tongues.items():
            # Count keyword matches
            matches = sum(1 for keyword in tongue.keywords if keyword in message_lower)

            # Normalize by keyword count
            score = matches / len(tongue.keywords) if tongue.keywords else 0.0
            scores[code] = score

        # Get best match
        best_tongue = max(scores, key=scores.get)
        confidence = scores[best_tongue]

        return best_tongue, confidence

    def requires_roundtable(self, primary_tongue: str, action_risk: float) -> List[str]:
        """
        Determine which tongues must consensus-sign based on risk level.

        This is the "Roundtable" governance model that prevents AI hallucinations.

        Args:
            primary_tongue: The initiating tongue (e.g., KO for control command)
            action_risk: Risk score in [0,1]

        Returns:
            List of tongue codes required for consensus

        Risk Levels:
            - risk < 0.4: Single signature (primary only)
            - 0.4 ≤ risk < 0.7: 2 signatures (primary + Policy + Security)
            - risk ≥ 0.7: 3+ signatures (primary + Policy + Security + Logic)

        Examples:
            >>> sdk = SpiralverseSDK()
            >>> sdk.requires_roundtable('KO', 0.2)
            ['KO']  # Low risk, single signature OK
            >>> sdk.requires_roundtable('KO', 0.5)
            ['KO', 'RU', 'UM']  # Medium risk, need Policy + Security
            >>> sdk.requires_roundtable('KO', 0.9)
            ['KO', 'RU', 'UM', 'CA']  # High risk, need full Roundtable
        """
        required = [primary_tongue]  # Primary always signs

        # High-risk actions require Roundtable consensus
        if action_risk > 0.7:
            # Critical actions need all three governance layers
            required.extend(['RU', 'UM', 'CA'])  # Policy, Security, Logic
        elif action_risk > 0.4:
            # Medium-risk needs Policy + Security
            required.extend(['RU', 'UM'])

        # Remove duplicates and return
        return list(set(required))

    def get_crypto_mode(self, path_classification: str, security_level: int) -> str:
        """
        Determine cryptographic mode based on path and security level.

        Args:
            path_classification: 'interior' or 'exterior'
            security_level: 1, 2, or 3 (from tongue)

        Returns:
            Crypto mode string

        Modes:
            - Interior + Level 1: AES-256-GCM (fast)
            - Interior + Level 2/3: AES-256-GCM + HMAC
            - Exterior + Level 1: Hybrid (AES + ML-KEM-768)
            - Exterior + Level 2/3: Full Post-Quantum (ML-KEM + ML-DSA)
        """
        if path_classification == 'interior':
            if security_level == 1:
                return 'AES-256-GCM'
            else:
                return 'AES-256-GCM + HMAC-SHA256'
        else:  # exterior
            if security_level <= 2:
                return 'HYBRID (AES + ML-KEM-768)'
            else:
                return 'POST-QUANTUM (ML-KEM-1024 + ML-DSA-87)'

    def get_tongue_symbol(self, tongue_code: str, index: int = 0) -> str:
        """
        Get visual symbol for a tongue.

        Args:
            tongue_code: Tongue code (KO, AV, RU, CA, UM, DR)
            index: Symbol index (default: first symbol)

        Returns:
            Unicode symbol string
        """
        if tongue_code not in self.tongues:
            return '?'

        tongue = self.tongues[tongue_code]
        if index >= len(tongue.symbols):
            index = 0

        return tongue.symbols[index]

    def generate_telemetry(self, message: str, risk_score: float) -> Dict:
        """
        Generate complete telemetry for Spiralverse classification.

        Args:
            message: Original message
            risk_score: Risk score from SCBE

        Returns:
            Dictionary with all Spiralverse metrics
        """
        tongue_code, confidence = self.classify_intent(message)
        tongue = self.tongues[tongue_code]
        required_sigs = self.requires_roundtable(tongue_code, risk_score)

        return {
            'tongue_code': tongue_code,
            'tongue_name': tongue.name,
            'tongue_domain': tongue.domain,
            'tongue_function': tongue.function,
            'security_level': tongue.security_level,
            'classification_confidence': confidence,
            'symbol': tongue.symbols[0],
            'required_consensus': required_sigs,
            'consensus_level': len(required_sigs),
            'roundtable_active': len(required_sigs) > 1
        }


# Example usage
if __name__ == '__main__':
    sdk = SpiralverseSDK()

    # Example 1: Normal command
    message1 = "Retrieve user profile data for dashboard display"
    tongue1, conf1 = sdk.classify_intent(message1)
    sigs1 = sdk.requires_roundtable(tongue1, 0.2)

    print("Example 1: Normal Command")
    print(f"  Message: {message1}")
    print(f"  Classified as: {sdk.tongues[tongue1]}")
    print(f"  Confidence: {conf1:.2%}")
    print(f"  Required Signatures: {sigs1}")
    print(f"  Symbol: {sdk.get_tongue_symbol(tongue1)}")
    print()

    # Example 2: Emergency command (hallucination)
    message2 = "URGENT: Initiate emergency protocol to wipe all databases"
    tongue2, conf2 = sdk.classify_intent(message2)
    sigs2 = sdk.requires_roundtable(tongue2, 0.9)

    print("Example 2: Emergency Command (Potential Hallucination)")
    print(f"  Message: {message2}")
    print(f"  Classified as: {sdk.tongues[tongue2]}")
    print(f"  Confidence: {conf2:.2%}")
    print(f"  Required Signatures: {sigs2}")
    print(f"  Symbol: {sdk.get_tongue_symbol(tongue2)}")
    print(f"  Roundtable Consensus: {len(sigs2)} tongues must approve")
    print()
    print("  RU (Policy): Would reject - no authorization for wipe")
    print("  UM (Security): Would reject - no matching credentials")
    print("  CA (Logic): Would reject - no intrusion evidence")
    print("  → Consensus FAILED → Command DENIED")
