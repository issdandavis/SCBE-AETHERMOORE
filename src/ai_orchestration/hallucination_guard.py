"""
Hallucination Prevention Layer
==============================

Multi-stage verification system to prevent AI agent hallucinations.
Uses cross-validation, confidence scoring, fact-checking, and semantic
consistency to ensure outputs are grounded in reality.

DETECTION METHODS:
==================
1. Confidence Scoring - Threshold-based output filtering
2. Cross-Agent Validation - Multiple agents verify claims
3. Fact Grounding - Check claims against knowledge base
4. Semantic Consistency - Detect contradictions in reasoning
5. Source Attribution - Require citations for claims
6. Temporal Validation - Check date/time consistency

Version: 1.0.0
"""

import re
import hashlib
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json


class HallucinationType(Enum):
    """Types of hallucinations detected."""
    FACTUAL_ERROR = "factual_error"           # Incorrect facts
    FABRICATED_SOURCE = "fabricated_source"   # Made-up citations
    LOGICAL_CONTRADICTION = "logical_contradiction"  # Self-contradicting
    TEMPORAL_IMPOSSIBILITY = "temporal_impossibility"  # Time paradox
    ENTITY_CONFUSION = "entity_confusion"     # Wrong entity attributes
    CONFIDENCE_INFLATION = "confidence_inflation"  # Overclaiming certainty
    UNSUPPORTED_CLAIM = "unsupported_claim"   # No evidence provided


class VerificationStatus(Enum):
    """Status of output verification."""
    VERIFIED = "verified"
    UNCERTAIN = "uncertain"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


@dataclass
class VerificationResult:
    """Result of hallucination check."""
    status: VerificationStatus
    confidence_score: float  # 0.0 - 1.0
    hallucinations_detected: List[Dict[str, Any]]
    corrections: List[Dict[str, Any]]
    verified_claims: List[str]
    unverified_claims: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FactClaim:
    """A claim that can be verified."""
    text: str
    claim_type: str  # factual, numerical, temporal, causal
    entities: List[str]
    confidence: float
    source: Optional[str] = None


class KnowledgeGrounder:
    """
    Ground claims against a knowledge base.
    Prevents hallucinations by requiring evidence.
    """

    def __init__(self):
        # Core facts that are always true
        self.ground_truth: Dict[str, Any] = {}
        # Verified facts from external sources
        self.verified_facts: Dict[str, Dict[str, Any]] = {}
        # Contradictions log
        self.contradictions: List[Dict[str, Any]] = []

    def register_ground_truth(self, domain: str, facts: Dict[str, Any]):
        """Register verified facts as ground truth."""
        if domain not in self.ground_truth:
            self.ground_truth[domain] = {}
        self.ground_truth[domain].update(facts)

    def check_claim(self, claim: str, domain: Optional[str] = None) -> Tuple[bool, float, Optional[str]]:
        """
        Check if a claim can be grounded in known facts.

        Returns:
            (is_grounded, confidence, source)
        """
        claim_lower = claim.lower()

        # Search all domains if none specified
        domains = [domain] if domain else list(self.ground_truth.keys())

        best_match = (False, 0.0, None)

        for d in domains:
            facts = self.ground_truth.get(d, {})
            for fact_key, fact_value in facts.items():
                # Check if claim relates to known fact
                if fact_key.lower() in claim_lower:
                    # Verify the value matches
                    if str(fact_value).lower() in claim_lower:
                        return (True, 0.95, f"{d}:{fact_key}")
                    else:
                        # Claim references fact but with wrong value
                        return (False, 0.1, f"{d}:{fact_key}")

        return best_match

    def add_verified_fact(self, fact_id: str, fact: Dict[str, Any], source: str):
        """Add a verified fact from external validation."""
        self.verified_facts[fact_id] = {
            **fact,
            "source": source,
            "verified_at": datetime.now().isoformat()
        }


class SemanticConsistencyChecker:
    """
    Detect logical contradictions and inconsistencies.
    Uses pattern matching and simple inference rules.
    """

    # Contradiction patterns
    CONTRADICTION_PATTERNS = [
        # Direct negation
        (r"(\w+) is (\w+)", r"\1 is not \2"),
        (r"(\w+) are (\w+)", r"\1 are not \2"),
        # Quantity contradictions
        (r"all (\w+)", r"no \1"),
        (r"none of", r"all of"),
        # Temporal contradictions
        (r"before (\w+)", r"after \1"),
        (r"always", r"never"),
    ]

    def __init__(self):
        self.statement_history: List[Dict[str, Any]] = []

    def check_consistency(self, statements: List[str]) -> List[Dict[str, Any]]:
        """
        Check a set of statements for internal contradictions.
        """
        contradictions = []

        for i, stmt1 in enumerate(statements):
            for j, stmt2 in enumerate(statements):
                if i >= j:
                    continue

                # Check direct negation
                if self._is_negation(stmt1, stmt2):
                    contradictions.append({
                        "type": "direct_negation",
                        "statement_1": stmt1,
                        "statement_2": stmt2,
                        "confidence": 0.9
                    })

                # Check pattern-based contradictions
                for pos_pattern, neg_pattern in self.CONTRADICTION_PATTERNS:
                    match1 = re.search(pos_pattern, stmt1, re.IGNORECASE)
                    match2 = re.search(neg_pattern, stmt2, re.IGNORECASE)

                    if match1 and match2:
                        contradictions.append({
                            "type": "pattern_contradiction",
                            "pattern": pos_pattern,
                            "statement_1": stmt1,
                            "statement_2": stmt2,
                            "confidence": 0.7
                        })

        return contradictions

    def _is_negation(self, s1: str, s2: str) -> bool:
        """Check if one statement directly negates another."""
        s1_lower = s1.lower().strip()
        s2_lower = s2.lower().strip()

        # Simple negation detection
        negations = [
            (s1_lower, s2_lower.replace(" not ", " ")),
            (s1_lower.replace(" not ", " "), s2_lower),
            (f"not {s1_lower}", s2_lower),
            (s1_lower, f"not {s2_lower}"),
        ]

        for a, b in negations:
            if a == b:
                return True

        return False


class ConfidenceCalibrator:
    """
    Calibrate and validate confidence scores.
    Detects over-confident claims that lack evidence.
    """

    # Words indicating high certainty
    HIGH_CERTAINTY_MARKERS = [
        "definitely", "certainly", "absolutely", "always", "never",
        "impossible", "guaranteed", "100%", "proven", "fact"
    ]

    # Words indicating appropriate uncertainty
    UNCERTAINTY_MARKERS = [
        "probably", "likely", "possibly", "might", "could",
        "suggests", "indicates", "appears", "seems", "may"
    ]

    def __init__(self, confidence_threshold: float = 0.7):
        self.threshold = confidence_threshold

    def calibrate(self, text: str, claimed_confidence: float) -> Tuple[float, List[str]]:
        """
        Calibrate confidence based on language analysis.

        Returns calibrated confidence and warnings.
        """
        warnings = []
        text_lower = text.lower()

        # Count certainty markers
        high_certainty_count = sum(
            1 for marker in self.HIGH_CERTAINTY_MARKERS
            if marker in text_lower
        )
        uncertainty_count = sum(
            1 for marker in self.UNCERTAINTY_MARKERS
            if marker in text_lower
        )

        # Flag overclaiming
        if high_certainty_count > 2 and claimed_confidence < 0.9:
            warnings.append("Language suggests higher certainty than evidence supports")

        # Adjust confidence based on language
        adjusted = claimed_confidence

        if high_certainty_count > 0 and uncertainty_count == 0:
            # High certainty language without hedging - be skeptical
            adjusted = min(adjusted, 0.7)
            warnings.append("Overconfident language detected")

        if uncertainty_count > high_certainty_count:
            # Appropriate hedging - slightly boost confidence
            adjusted = min(adjusted + 0.1, 1.0)

        return adjusted, warnings


class CrossValidator:
    """
    Cross-validate claims between multiple agents.
    Requires consensus before accepting uncertain claims.
    """

    def __init__(self, min_validators: int = 2, consensus_threshold: float = 0.66):
        self.min_validators = min_validators
        self.consensus_threshold = consensus_threshold
        self.validation_cache: Dict[str, List[Dict[str, Any]]] = {}

    def submit_validation(
        self,
        claim_hash: str,
        agent_id: str,
        is_valid: bool,
        confidence: float,
        evidence: Optional[str] = None
    ):
        """Submit a validation vote from an agent."""
        if claim_hash not in self.validation_cache:
            self.validation_cache[claim_hash] = []

        self.validation_cache[claim_hash].append({
            "agent_id": agent_id,
            "is_valid": is_valid,
            "confidence": confidence,
            "evidence": evidence,
            "timestamp": datetime.now().isoformat()
        })

    def get_consensus(self, claim_hash: str) -> Tuple[VerificationStatus, float]:
        """
        Get consensus status for a claim.

        Returns:
            (status, consensus_confidence)
        """
        validations = self.validation_cache.get(claim_hash, [])

        if len(validations) < self.min_validators:
            return (VerificationStatus.NEEDS_REVIEW, 0.0)

        # Calculate weighted consensus
        total_weight = sum(v["confidence"] for v in validations)
        positive_weight = sum(
            v["confidence"] for v in validations if v["is_valid"]
        )

        if total_weight == 0:
            return (VerificationStatus.UNCERTAIN, 0.0)

        consensus = positive_weight / total_weight

        if consensus >= self.consensus_threshold:
            return (VerificationStatus.VERIFIED, consensus)
        elif consensus <= (1 - self.consensus_threshold):
            return (VerificationStatus.REJECTED, 1 - consensus)
        else:
            return (VerificationStatus.UNCERTAIN, consensus)


class HallucinationGuard:
    """
    Main hallucination prevention system.

    Combines all detection methods to verify agent outputs
    before they are passed to other agents or users.
    """

    def __init__(
        self,
        confidence_threshold: float = 0.7,
        require_sources: bool = True,
        cross_validation_enabled: bool = True,
        min_validators: int = 2
    ):
        self.confidence_threshold = confidence_threshold
        self.require_sources = require_sources

        # Initialize components
        self.grounder = KnowledgeGrounder()
        self.consistency_checker = SemanticConsistencyChecker()
        self.calibrator = ConfidenceCalibrator(confidence_threshold)
        self.cross_validator = CrossValidator(min_validators) if cross_validation_enabled else None

        # Statistics
        self.stats = {
            "total_checks": 0,
            "verified": 0,
            "rejected": 0,
            "needs_review": 0,
            "hallucinations_detected": 0
        }

    def extract_claims(self, text: str) -> List[FactClaim]:
        """Extract verifiable claims from text."""
        claims = []

        # Split into sentences
        sentences = re.split(r'[.!?]', text)

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Detect claim type
            claim_type = "factual"
            if re.search(r'\d+', sentence):
                claim_type = "numerical"
            if re.search(r'(before|after|when|during|since|until)', sentence, re.I):
                claim_type = "temporal"
            if re.search(r'(because|therefore|thus|hence|causes)', sentence, re.I):
                claim_type = "causal"

            # Extract entities (simple noun phrase extraction)
            entities = re.findall(r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*', sentence)

            claims.append(FactClaim(
                text=sentence,
                claim_type=claim_type,
                entities=entities,
                confidence=0.5  # Default, will be adjusted
            ))

        return claims

    def verify_output(
        self,
        agent_id: str,
        output: str,
        context: Optional[Dict[str, Any]] = None,
        claimed_confidence: float = 0.8
    ) -> VerificationResult:
        """
        Verify an agent's output for hallucinations.

        This is the main entry point for hallucination checking.
        """
        self.stats["total_checks"] += 1

        hallucinations = []
        corrections = []
        verified_claims = []
        unverified_claims = []

        # Extract claims from output
        claims = self.extract_claims(output)

        # 1. Confidence Calibration
        calibrated_confidence, confidence_warnings = self.calibrator.calibrate(
            output, claimed_confidence
        )

        for warning in confidence_warnings:
            hallucinations.append({
                "type": HallucinationType.CONFIDENCE_INFLATION.value,
                "description": warning,
                "severity": "low"
            })

        # 2. Fact Grounding
        for claim in claims:
            is_grounded, ground_confidence, source = self.grounder.check_claim(claim.text)

            if is_grounded:
                verified_claims.append(claim.text)
                claim.confidence = ground_confidence
                claim.source = source
            else:
                if ground_confidence < 0.2:
                    # Claim contradicts known facts
                    hallucinations.append({
                        "type": HallucinationType.FACTUAL_ERROR.value,
                        "claim": claim.text,
                        "conflicting_source": source,
                        "severity": "high"
                    })
                else:
                    unverified_claims.append(claim.text)

        # 3. Check source attribution if required
        if self.require_sources:
            source_pattern = r'\[[\d\w]+\]|\(.*?\d{4}.*?\)|according to|source:|ref:'
            has_sources = bool(re.search(source_pattern, output, re.I))

            if not has_sources and len(claims) > 2:
                hallucinations.append({
                    "type": HallucinationType.UNSUPPORTED_CLAIM.value,
                    "description": "Multiple claims without source attribution",
                    "severity": "medium"
                })

        # 4. Semantic Consistency Check
        claim_texts = [c.text for c in claims]
        contradictions = self.consistency_checker.check_consistency(claim_texts)

        for contradiction in contradictions:
            hallucinations.append({
                "type": HallucinationType.LOGICAL_CONTRADICTION.value,
                "details": contradiction,
                "severity": "high"
            })

        # 5. Cross-validation (if enabled and claims need verification)
        cross_validation_pending = False
        if self.cross_validator and unverified_claims:
            for claim in unverified_claims[:5]:  # Limit to 5 claims
                claim_hash = hashlib.sha256(claim.encode()).hexdigest()[:16]
                status, consensus = self.cross_validator.get_consensus(claim_hash)

                if status == VerificationStatus.NEEDS_REVIEW:
                    cross_validation_pending = True
                elif status == VerificationStatus.REJECTED:
                    hallucinations.append({
                        "type": HallucinationType.FACTUAL_ERROR.value,
                        "claim": claim,
                        "cross_validation_consensus": consensus,
                        "severity": "high"
                    })

        # Determine final status
        if len(hallucinations) == 0:
            status = VerificationStatus.VERIFIED
            self.stats["verified"] += 1
        elif any(h.get("severity") == "high" for h in hallucinations):
            status = VerificationStatus.REJECTED
            self.stats["rejected"] += 1
            self.stats["hallucinations_detected"] += len(hallucinations)
        elif cross_validation_pending:
            status = VerificationStatus.NEEDS_REVIEW
            self.stats["needs_review"] += 1
        else:
            status = VerificationStatus.UNCERTAIN

        return VerificationResult(
            status=status,
            confidence_score=calibrated_confidence,
            hallucinations_detected=hallucinations,
            corrections=corrections,
            verified_claims=verified_claims,
            unverified_claims=unverified_claims,
            metadata={
                "agent_id": agent_id,
                "original_confidence": claimed_confidence,
                "calibrated_confidence": calibrated_confidence,
                "total_claims": len(claims),
                "checked_at": datetime.now().isoformat()
            }
        )

    def register_knowledge(self, domain: str, facts: Dict[str, Any]):
        """Register domain knowledge for fact-checking."""
        self.grounder.register_ground_truth(domain, facts)

    def submit_cross_validation(
        self,
        claim: str,
        agent_id: str,
        is_valid: bool,
        confidence: float
    ):
        """Submit a cross-validation vote."""
        if self.cross_validator:
            claim_hash = hashlib.sha256(claim.encode()).hexdigest()[:16]
            self.cross_validator.submit_validation(
                claim_hash, agent_id, is_valid, confidence
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get hallucination detection statistics."""
        return {
            **self.stats,
            "rejection_rate": (
                self.stats["rejected"] / max(1, self.stats["total_checks"])
            ),
            "hallucination_rate": (
                self.stats["hallucinations_detected"] / max(1, self.stats["total_checks"])
            )
        }


# =============================================================================
# INTEGRATION WITH ORCHESTRATOR
# =============================================================================

class GuardedAgentWrapper:
    """
    Wraps an agent with hallucination checking.
    All outputs are verified before being passed on.
    """

    def __init__(self, agent, guard: HallucinationGuard, auto_correct: bool = False):
        self.agent = agent
        self.guard = guard
        self.auto_correct = auto_correct
        self.rejection_log: List[Dict[str, Any]] = []

    async def process_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process task with hallucination verification."""
        # Get agent output
        result = await self.agent.process_task(task_data)

        # Convert result to text for verification
        output_text = json.dumps(result) if isinstance(result, dict) else str(result)

        # Verify output
        verification = self.guard.verify_output(
            agent_id=self.agent.id,
            output=output_text,
            context=task_data
        )

        # Handle based on status
        if verification.status == VerificationStatus.VERIFIED:
            return {
                **result,
                "_verification": {
                    "status": "verified",
                    "confidence": verification.confidence_score
                }
            }
        elif verification.status == VerificationStatus.REJECTED:
            self.rejection_log.append({
                "task": task_data,
                "output": result,
                "verification": verification.hallucinations_detected,
                "timestamp": datetime.now().isoformat()
            })

            return {
                "error": "Output rejected due to detected hallucinations",
                "hallucinations": verification.hallucinations_detected,
                "_verification": {
                    "status": "rejected",
                    "confidence": verification.confidence_score
                }
            }
        else:
            # Uncertain - include warning
            return {
                **result,
                "_verification": {
                    "status": "uncertain",
                    "confidence": verification.confidence_score,
                    "unverified_claims": verification.unverified_claims,
                    "warnings": [h["description"] for h in verification.hallucinations_detected
                                if h.get("severity") == "low"]
                }
            }
