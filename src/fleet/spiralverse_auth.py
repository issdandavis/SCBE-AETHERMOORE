"""
SpiralverseAuthenticator — Multi-layer AI-to-AI authentication SaaS.

Provides cryptographic verification for agent-to-agent communication
using 4 signature layers aligned with Sacred Tongue encoding.

Sellable as:
  - API SaaS ($99-499/mo per organization)
  - Enterprise on-prem ($5K-25K/yr)
  - Open-source core + premium features
"""

import hashlib
import hmac
import json
import math
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Phi-weighted keys for Sacred Tongues
PHI = (1 + math.sqrt(5)) / 2
TONGUE_PHI_WEIGHTS = {
    "KO": 1.0,
    "AV": PHI,
    "RU": PHI ** 2,
    "CA": PHI ** 3,
    "UM": PHI ** 4,
    "DR": PHI ** 5,
}
TONGUE_HMAC_SEEDS = {
    tongue: hashlib.sha256(f"SCBE-{tongue}-{w:.6f}".encode()).hexdigest()
    for tongue, w in TONGUE_PHI_WEIGHTS.items()
}


@dataclass
class AgentIdentity:
    agent_id: str
    name: str
    tongue: str  # primary Sacred Tongue alignment
    public_key_hash: str  # SHA-256 of agent's public key
    registered_at: float = field(default_factory=time.time)
    trust_score: float = 0.5  # [0, 1] — starts neutral
    interaction_count: int = 0
    last_active: float = 0.0


@dataclass
class SignedMessage:
    message_id: str
    content: str
    sender_id: str
    timestamp: float
    signatures: Dict[str, str]  # layer_name -> signature_hex
    tongue: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class SpiralverseAuthenticator:
    """Multi-layer authentication for AI-to-AI communication."""

    def __init__(self, master_seed: str = "SCBE-AETHERMOORE-SPIRALVERSE"):
        self.master_seed = master_seed
        self.agents: Dict[str, AgentIdentity] = {}
        self.message_log: List[Dict[str, Any]] = []
        self._master_key = hashlib.sha256(master_seed.encode()).hexdigest()

    def register_agent(self, name: str, tongue: str = "DR", public_key_hash: str = "") -> AgentIdentity:
        agent_id = f"agent-{uuid.uuid4().hex[:12]}"
        if not public_key_hash:
            public_key_hash = hashlib.sha256(f"{name}-{time.time()}".encode()).hexdigest()
        identity = AgentIdentity(
            agent_id=agent_id,
            name=name,
            tongue=tongue,
            public_key_hash=public_key_hash,
        )
        self.agents[agent_id] = identity
        return identity

    def sign_message(self, sender_id: str, content: str, tongue: str = "", metadata: Optional[Dict] = None) -> SignedMessage:
        agent = self.agents.get(sender_id)
        if not agent:
            raise ValueError(f"Unknown agent: {sender_id}")

        tongue = tongue or agent.tongue
        ts = time.time()
        msg_id = f"msg-{uuid.uuid4().hex[:12]}"

        # Layer 1: Content signature
        content_sig = hashlib.sha256(content.encode()).hexdigest()

        # Layer 2: Identity signature
        identity_payload = f"{sender_id}:{content_sig}:{ts}"
        identity_sig = hmac.new(
            agent.public_key_hash.encode(),
            identity_payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        # Layer 3: Roundtable signature (collective)
        roundtable_payload = f"{identity_sig}:{len(self.agents)}:{self._master_key}"
        roundtable_sig = hashlib.sha256(roundtable_payload.encode()).hexdigest()

        # Layer 4: Sacred Language encoding
        tongue_seed = TONGUE_HMAC_SEEDS.get(tongue, TONGUE_HMAC_SEEDS["DR"])
        tongue_payload = f"{roundtable_sig}:{tongue}:{TONGUE_PHI_WEIGHTS.get(tongue, 1.0):.6f}"
        tongue_sig = hmac.new(
            tongue_seed.encode(),
            tongue_payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        signatures = {
            "content": content_sig,
            "identity": identity_sig,
            "roundtable": roundtable_sig,
            "sacred_tongue": tongue_sig,
        }

        # Update agent stats
        agent.interaction_count += 1
        agent.last_active = ts
        agent.trust_score = min(1.0, agent.trust_score + 0.01)  # trust grows slowly

        msg = SignedMessage(
            message_id=msg_id,
            content=content,
            sender_id=sender_id,
            timestamp=ts,
            signatures=signatures,
            tongue=tongue,
            metadata=metadata or {},
        )

        self.message_log.append({
            "message_id": msg_id,
            "sender_id": sender_id,
            "tongue": tongue,
            "timestamp": ts,
            "verified": True,
        })
        if len(self.message_log) > 1000:
            self.message_log = self.message_log[-1000:]

        return msg

    def verify_message(self, msg: SignedMessage) -> Dict[str, Any]:
        results = {"message_id": msg.message_id, "layers": {}, "valid": True, "trust_score": 0.0}

        # Layer 1: Content
        expected_content = hashlib.sha256(msg.content.encode()).hexdigest()
        l1_valid = msg.signatures.get("content") == expected_content
        results["layers"]["content"] = {"valid": l1_valid, "layer": 1}

        # Layer 2: Identity
        agent = self.agents.get(msg.sender_id)
        if agent:
            identity_payload = f"{msg.sender_id}:{expected_content}:{msg.timestamp}"
            expected_identity = hmac.new(
                agent.public_key_hash.encode(),
                identity_payload.encode(),
                hashlib.sha256,
            ).hexdigest()
            l2_valid = msg.signatures.get("identity") == expected_identity
            results["trust_score"] = agent.trust_score
        else:
            l2_valid = False
        results["layers"]["identity"] = {"valid": l2_valid, "layer": 2}

        # Layer 3: Roundtable
        roundtable_payload = f"{msg.signatures.get('identity', '')}:{len(self.agents)}:{self._master_key}"
        expected_roundtable = hashlib.sha256(roundtable_payload.encode()).hexdigest()
        l3_valid = msg.signatures.get("roundtable") == expected_roundtable
        results["layers"]["roundtable"] = {"valid": l3_valid, "layer": 3}

        # Layer 4: Sacred Language
        tongue_seed = TONGUE_HMAC_SEEDS.get(msg.tongue, TONGUE_HMAC_SEEDS["DR"])
        tongue_payload = f"{msg.signatures.get('roundtable', '')}:{msg.tongue}:{TONGUE_PHI_WEIGHTS.get(msg.tongue, 1.0):.6f}"
        expected_tongue = hmac.new(
            tongue_seed.encode(),
            tongue_payload.encode(),
            hashlib.sha256,
        ).hexdigest()
        l4_valid = msg.signatures.get("sacred_tongue") == expected_tongue
        results["layers"]["sacred_tongue"] = {"valid": l4_valid, "layer": 4}

        results["valid"] = all([l1_valid, l2_valid, l3_valid, l4_valid])
        return results

    def get_trust_scores(self) -> Dict[str, Dict[str, Any]]:
        return {
            aid: {
                "name": a.name,
                "tongue": a.tongue,
                "trust_score": round(a.trust_score, 4),
                "interactions": a.interaction_count,
                "last_active": a.last_active,
            }
            for aid, a in self.agents.items()
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "registered_agents": len(self.agents),
            "total_messages": len(self.message_log),
            "tongues_active": list(set(a.tongue for a in self.agents.values())),
            "avg_trust": round(sum(a.trust_score for a in self.agents.values()) / max(1, len(self.agents)), 4),
        }
