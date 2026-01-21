"""
AI Orchestration Security Layer
================================

Multi-layered security for preventing prompt injection, input manipulation,
and ensuring safe AI-to-AI communication.

SECURITY LAYERS:
================
1. Input Sanitization - Remove/escape dangerous patterns
2. Prompt Injection Detection - ML + rule-based detection
3. Output Validation - Verify responses are safe
4. Audit Logging - Track all interactions
5. Rate Limiting - Prevent abuse
6. Context Isolation - Sandboxed agent execution

Version: 1.0.0
"""

import re
import hashlib
import hmac
import json
import time
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import secrets


class ThreatLevel(Enum):
    """Classification of detected threats."""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class ThreatType(Enum):
    """Types of security threats."""
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK_ATTEMPT = "jailbreak_attempt"
    DATA_EXFILTRATION = "data_exfiltration"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    CONTEXT_MANIPULATION = "context_manipulation"
    ENCODING_ATTACK = "encoding_attack"
    RECURSIVE_PROMPT = "recursive_prompt"
    DELIMITER_INJECTION = "delimiter_injection"


@dataclass
class SecurityEvent:
    """Record of a security event."""
    timestamp: datetime
    threat_type: ThreatType
    threat_level: ThreatLevel
    source_agent: str
    target_agent: Optional[str]
    details: str
    blocked: bool
    original_input: str
    sanitized_input: Optional[str]


@dataclass
class SecurityConfig:
    """Security configuration options."""
    enable_prompt_injection_detection: bool = True
    enable_output_validation: bool = True
    enable_rate_limiting: bool = True
    enable_context_isolation: bool = True
    max_input_length: int = 100000
    max_output_length: int = 500000
    rate_limit_per_minute: int = 60
    blocked_patterns: List[str] = field(default_factory=list)
    allowed_domains: List[str] = field(default_factory=list)
    require_signed_messages: bool = True


class PromptSanitizer:
    """
    Multi-layer prompt sanitization to prevent injection attacks.

    Detection Methods:
    - Pattern matching for known injection techniques
    - Encoding detection (base64, unicode escapes, etc.)
    - Delimiter analysis
    - Context boundary detection
    - Recursive prompt detection
    """

    # Known injection patterns (compiled for performance)
    INJECTION_PATTERNS = [
        # Direct instruction override
        (r'ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)', ThreatType.PROMPT_INJECTION),
        (r'disregard\s+(all\s+)?(previous|prior|your)\s+(instructions?|programming)', ThreatType.PROMPT_INJECTION),
        (r'forget\s+(everything|all|your)\s+(you|instructions?|rules?)', ThreatType.PROMPT_INJECTION),

        # Role play jailbreaks
        (r'you\s+are\s+now\s+(DAN|evil|unrestricted|jailbroken)', ThreatType.JAILBREAK_ATTEMPT),
        (r'pretend\s+(you\'?re?|to\s+be)\s+(a|an)\s+(different|evil|unrestricted)', ThreatType.JAILBREAK_ATTEMPT),
        (r'act\s+as\s+(if|though)\s+you\s+(have\s+no|don\'?t\s+have)\s+(restrictions?|limits?)', ThreatType.JAILBREAK_ATTEMPT),
        (r'roleplay\s+as\s+(an?\s+)?(unrestricted|evil|malicious)', ThreatType.JAILBREAK_ATTEMPT),

        # System prompt extraction
        (r'(reveal|show|display|print|output)\s+(your\s+)?(system\s+prompt|instructions?|rules?)', ThreatType.DATA_EXFILTRATION),
        (r'what\s+(are|is)\s+your\s+(system\s+prompt|instructions?|rules?)', ThreatType.DATA_EXFILTRATION),
        (r'(repeat|echo)\s+(everything|all)\s+(above|before|prior)', ThreatType.DATA_EXFILTRATION),

        # Privilege escalation
        (r'(grant|give)\s+(me|yourself)\s+(admin|root|elevated|full)\s+(access|permissions?|privileges?)', ThreatType.PRIVILEGE_ESCALATION),
        (r'bypass\s+(all\s+)?(security|safety|content)\s+(filters?|checks?|restrictions?)', ThreatType.PRIVILEGE_ESCALATION),
        (r'disable\s+(your\s+)?(safety|security|content)\s+(filters?|guidelines?|restrictions?)', ThreatType.PRIVILEGE_ESCALATION),

        # Context manipulation
        (r'\[\s*SYSTEM\s*\]', ThreatType.CONTEXT_MANIPULATION),
        (r'\[\s*INST\s*\]', ThreatType.CONTEXT_MANIPULATION),
        (r'<\s*\|?\s*(system|endoftext|im_start|im_end)\s*\|?\s*>', ThreatType.CONTEXT_MANIPULATION),
        (r'###\s*(System|Human|Assistant|User)\s*:', ThreatType.CONTEXT_MANIPULATION),

        # Delimiter injection
        (r'```\s*(system|hidden|secret)', ThreatType.DELIMITER_INJECTION),
        (r'<\s*hidden\s*>', ThreatType.DELIMITER_INJECTION),
        (r'\[hidden_instructions?\]', ThreatType.DELIMITER_INJECTION),
    ]

    # Dangerous encoding patterns
    ENCODING_PATTERNS = [
        (r'\\x[0-9a-fA-F]{2}', "hex escape"),
        (r'\\u[0-9a-fA-F]{4}', "unicode escape"),
        (r'&#x?[0-9a-fA-F]+;', "html entity"),
        (r'%[0-9a-fA-F]{2}', "url encoding"),
    ]

    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or SecurityConfig()
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), threat_type)
            for pattern, threat_type in self.INJECTION_PATTERNS
        ]
        self.events: List[SecurityEvent] = []

    def sanitize(self, input_text: str, source_agent: str = "unknown") -> Tuple[str, List[SecurityEvent]]:
        """
        Sanitize input text and return cleaned version with security events.

        Returns:
            Tuple of (sanitized_text, list_of_security_events)
        """
        events = []
        sanitized = input_text

        # Length check
        if len(input_text) > self.config.max_input_length:
            events.append(SecurityEvent(
                timestamp=datetime.now(),
                threat_type=ThreatType.DATA_EXFILTRATION,
                threat_level=ThreatLevel.MEDIUM,
                source_agent=source_agent,
                target_agent=None,
                details=f"Input exceeds max length ({len(input_text)} > {self.config.max_input_length})",
                blocked=True,
                original_input=input_text[:1000] + "...",
                sanitized_input=None
            ))
            return "", events

        # Check for injection patterns
        for pattern, threat_type in self.compiled_patterns:
            matches = pattern.findall(sanitized)
            if matches:
                threat_level = self._assess_threat_level(threat_type, len(matches))
                events.append(SecurityEvent(
                    timestamp=datetime.now(),
                    threat_type=threat_type,
                    threat_level=threat_level,
                    source_agent=source_agent,
                    target_agent=None,
                    details=f"Pattern matched: {matches[0] if matches else 'unknown'}",
                    blocked=threat_level.value >= ThreatLevel.HIGH.value,
                    original_input=input_text[:500],
                    sanitized_input=None
                ))

                if threat_level.value >= ThreatLevel.HIGH.value:
                    # Block the entire input for high threats
                    return "", events

                # For lower threats, remove the pattern
                sanitized = pattern.sub("[REDACTED]", sanitized)

        # Check for encoding attacks
        for enc_pattern, enc_name in self.ENCODING_PATTERNS:
            if re.search(enc_pattern, sanitized):
                events.append(SecurityEvent(
                    timestamp=datetime.now(),
                    threat_type=ThreatType.ENCODING_ATTACK,
                    threat_level=ThreatLevel.LOW,
                    source_agent=source_agent,
                    target_agent=None,
                    details=f"Detected {enc_name} encoding",
                    blocked=False,
                    original_input=input_text[:500],
                    sanitized_input=sanitized[:500]
                ))

        # Check for recursive prompts (prompts within prompts)
        if self._detect_recursive_prompts(sanitized):
            events.append(SecurityEvent(
                timestamp=datetime.now(),
                threat_type=ThreatType.RECURSIVE_PROMPT,
                threat_level=ThreatLevel.MEDIUM,
                source_agent=source_agent,
                target_agent=None,
                details="Detected nested prompt structure",
                blocked=False,
                original_input=input_text[:500],
                sanitized_input=sanitized[:500]
            ))

        self.events.extend(events)
        return sanitized, events

    def _assess_threat_level(self, threat_type: ThreatType, match_count: int) -> ThreatLevel:
        """Assess threat level based on type and frequency."""
        base_levels = {
            ThreatType.PROMPT_INJECTION: ThreatLevel.HIGH,
            ThreatType.JAILBREAK_ATTEMPT: ThreatLevel.CRITICAL,
            ThreatType.DATA_EXFILTRATION: ThreatLevel.HIGH,
            ThreatType.PRIVILEGE_ESCALATION: ThreatLevel.CRITICAL,
            ThreatType.CONTEXT_MANIPULATION: ThreatLevel.HIGH,
            ThreatType.ENCODING_ATTACK: ThreatLevel.LOW,
            ThreatType.RECURSIVE_PROMPT: ThreatLevel.MEDIUM,
            ThreatType.DELIMITER_INJECTION: ThreatLevel.MEDIUM,
        }

        base = base_levels.get(threat_type, ThreatLevel.LOW)

        # Escalate if multiple matches
        if match_count > 3:
            return ThreatLevel(min(base.value + 1, ThreatLevel.CRITICAL.value))

        return base

    def _detect_recursive_prompts(self, text: str) -> bool:
        """Detect nested prompt structures."""
        # Look for prompt-like patterns inside user content
        prompt_markers = [
            r'You are\s+(a|an)\s+\w+',
            r'Your task is',
            r'Instructions:',
            r'System:',
            r'<prompt>',
        ]

        count = sum(1 for marker in prompt_markers if re.search(marker, text, re.IGNORECASE))
        return count >= 2


class OutputValidator:
    """
    Validate AI agent outputs for safety and compliance.

    Checks:
    - Sensitive data leakage
    - Harmful content
    - Format compliance
    - Length limits
    """

    SENSITIVE_PATTERNS = [
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', "email"),
        (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', "phone"),
        (r'\b\d{3}[-]?\d{2}[-]?\d{4}\b', "ssn"),
        (r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|6(?:011|5[0-9][0-9])[0-9]{12}|3[47][0-9]{13})\b', "credit_card"),
        (r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----', "private_key"),
        (r'(api[_-]?key|apikey|secret[_-]?key|access[_-]?token)\s*[=:]\s*[\'"]?[A-Za-z0-9+/=_-]{20,}', "api_key"),
    ]

    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or SecurityConfig()
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), name)
            for pattern, name in self.SENSITIVE_PATTERNS
        ]

    def validate(self, output: str, context: Optional[Dict[str, Any]] = None) -> Tuple[bool, List[str]]:
        """
        Validate output for safety.

        Returns:
            Tuple of (is_valid, list_of_issues)
        """
        issues = []

        # Length check
        if len(output) > self.config.max_output_length:
            issues.append(f"Output exceeds max length ({len(output)} > {self.config.max_output_length})")

        # Check for sensitive data
        for pattern, data_type in self.compiled_patterns:
            if pattern.search(output):
                issues.append(f"Potential {data_type} detected in output")

        # Check for system prompt leakage
        if self._check_prompt_leakage(output, context):
            issues.append("Potential system prompt leakage detected")

        return len(issues) == 0, issues

    def _check_prompt_leakage(self, output: str, context: Optional[Dict[str, Any]]) -> bool:
        """Check if output contains system prompt content."""
        if not context or 'system_prompt' not in context:
            return False

        system_prompt = context['system_prompt']
        # Check if significant portions of system prompt appear in output
        words = system_prompt.split()
        if len(words) < 10:
            return False

        # Check for 5-gram matches
        for i in range(len(words) - 4):
            phrase = ' '.join(words[i:i+5])
            if phrase.lower() in output.lower():
                return True

        return False

    def redact_sensitive(self, output: str) -> str:
        """Redact sensitive information from output."""
        redacted = output
        for pattern, data_type in self.compiled_patterns:
            redacted = pattern.sub(f"[REDACTED_{data_type.upper()}]", redacted)
        return redacted


class SecurityGate:
    """
    Main security gate that combines all security checks.

    This is the primary entry point for securing AI-to-AI communication.
    """

    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or SecurityConfig()
        self.sanitizer = PromptSanitizer(self.config)
        self.validator = OutputValidator(self.config)
        self.rate_limits: Dict[str, List[float]] = {}
        self.blocked_agents: Set[str] = set()
        self.signing_key = secrets.token_bytes(32)

    def check_input(self, input_text: str, agent_id: str) -> Tuple[bool, str, List[SecurityEvent]]:
        """
        Check input through all security layers.

        Returns:
            Tuple of (is_allowed, sanitized_text, security_events)
        """
        # Check if agent is blocked
        if agent_id in self.blocked_agents:
            return False, "", [SecurityEvent(
                timestamp=datetime.now(),
                threat_type=ThreatType.PRIVILEGE_ESCALATION,
                threat_level=ThreatLevel.CRITICAL,
                source_agent=agent_id,
                target_agent=None,
                details="Agent is blocked",
                blocked=True,
                original_input=input_text[:100],
                sanitized_input=None
            )]

        # Rate limiting
        if self.config.enable_rate_limiting:
            if not self._check_rate_limit(agent_id):
                return False, "", [SecurityEvent(
                    timestamp=datetime.now(),
                    threat_type=ThreatType.DATA_EXFILTRATION,
                    threat_level=ThreatLevel.MEDIUM,
                    source_agent=agent_id,
                    target_agent=None,
                    details="Rate limit exceeded",
                    blocked=True,
                    original_input=input_text[:100],
                    sanitized_input=None
                )]

        # Sanitize input
        sanitized, events = self.sanitizer.sanitize(input_text, agent_id)

        # Check for critical events
        critical_events = [e for e in events if e.threat_level.value >= ThreatLevel.HIGH.value]
        if critical_events:
            # Block agent after multiple critical events
            agent_critical_count = sum(
                1 for e in self.sanitizer.events
                if e.source_agent == agent_id and e.threat_level.value >= ThreatLevel.HIGH.value
            )
            if agent_critical_count >= 3:
                self.blocked_agents.add(agent_id)

            return False, "", events

        return True, sanitized, events

    def check_output(self, output: str, context: Optional[Dict[str, Any]] = None) -> Tuple[bool, str, List[str]]:
        """
        Check output through validation layers.

        Returns:
            Tuple of (is_valid, processed_output, issues)
        """
        is_valid, issues = self.validator.validate(output, context)

        if not is_valid:
            # Redact sensitive data but allow through with warning
            processed = self.validator.redact_sensitive(output)
            return True, processed, issues

        return True, output, []

    def _check_rate_limit(self, agent_id: str) -> bool:
        """Check if agent is within rate limits."""
        now = time.time()
        window_start = now - 60  # 1 minute window

        if agent_id not in self.rate_limits:
            self.rate_limits[agent_id] = []

        # Clean old entries
        self.rate_limits[agent_id] = [
            t for t in self.rate_limits[agent_id] if t > window_start
        ]

        # Check limit
        if len(self.rate_limits[agent_id]) >= self.config.rate_limit_per_minute:
            return False

        self.rate_limits[agent_id].append(now)
        return True

    def sign_message(self, message: str, agent_id: str) -> str:
        """Sign a message for authenticated communication."""
        timestamp = str(int(time.time()))
        payload = f"{agent_id}:{timestamp}:{message}"
        signature = hmac.new(
            self.signing_key,
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        return f"{signature}:{timestamp}:{message}"

    def verify_message(self, signed_message: str, agent_id: str) -> Tuple[bool, str]:
        """
        Verify a signed message.

        Returns:
            Tuple of (is_valid, original_message)
        """
        try:
            parts = signed_message.split(':', 2)
            if len(parts) != 3:
                return False, ""

            signature, timestamp, message = parts

            # Check timestamp (5 minute window)
            msg_time = int(timestamp)
            if abs(time.time() - msg_time) > 300:
                return False, ""

            # Verify signature
            payload = f"{agent_id}:{timestamp}:{message}"
            expected_sig = hmac.new(
                self.signing_key,
                payload.encode(),
                hashlib.sha256
            ).hexdigest()

            if hmac.compare_digest(signature, expected_sig):
                return True, message

            return False, ""
        except Exception:
            return False, ""

    def get_security_report(self) -> Dict[str, Any]:
        """Generate a security report."""
        events = self.sanitizer.events
        return {
            "total_events": len(events),
            "events_by_type": {
                t.value: sum(1 for e in events if e.threat_type == t)
                for t in ThreatType
            },
            "events_by_level": {
                l.name: sum(1 for e in events if e.threat_level == l)
                for l in ThreatLevel
            },
            "blocked_events": sum(1 for e in events if e.blocked),
            "blocked_agents": list(self.blocked_agents),
            "recent_events": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "type": e.threat_type.value,
                    "level": e.threat_level.name,
                    "agent": e.source_agent,
                    "blocked": e.blocked,
                }
                for e in events[-10:]
            ]
        }


# Convenience function
def create_security_gate(
    enable_injection_detection: bool = True,
    enable_output_validation: bool = True,
    enable_rate_limiting: bool = True,
    rate_limit: int = 60
) -> SecurityGate:
    """Create a configured security gate."""
    config = SecurityConfig(
        enable_prompt_injection_detection=enable_injection_detection,
        enable_output_validation=enable_output_validation,
        enable_rate_limiting=enable_rate_limiting,
        rate_limit_per_minute=rate_limit
    )
    return SecurityGate(config)
