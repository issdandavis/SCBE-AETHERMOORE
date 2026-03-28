"""
Sacred Eggs ritual reference implementation.

This module exposes a small ritual API compatible with the SCBE test harness:
- `solitary_incubation`
- `triadic_binding` / `manifold_binding`
- `verify_binding`
- `ring_descent`
- `fail_to_noise`
- `invoke_ritual` dispatcher
"""

from __future__ import annotations

import base64
import hashlib
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional, Tuple

_GOOD_NOISE = b"fail-to-noise"


def _safe_bytes(payload: Any) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, bytearray):
        return bytes(payload)
    if payload is None:
        return b""
    return str(payload).encode("utf-8", errors="ignore")


def _distinct(values: Iterable[str]) -> bool:
    items = list(values)
    return len(items) == len(set(items))


def _valid_manifold(manifold: Any) -> bool:
    if not isinstance(manifold, (list, tuple)) or len(manifold) != 6:
        return False
    total = 0.0
    for x in manifold:
        if not isinstance(x, (int, float)):
            return False
        if x != x:  # nan
            return False
        if x == float("inf") or x == float("-inf"):
            return False
        total += float(x) ** 2
    # Open Poincare ball: ||x|| < 1
    return total < 1.0


def _binding_token(
    participants: Iterable[str],
    threshold: int,
    payload: bytes,
    manifold: Tuple[float, ...],
) -> str:
    material = "|".join(sorted(participants)).encode("utf-8")
    material += b"::" + str(int(threshold)).encode("utf-8")
    material += b"::" + payload
    material += b"::" + ",".join(f"{float(v):.12f}" for v in manifold).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


@dataclass
class SacredEgg:
    egg_id: str = "egg"
    payload: bytes = b""
    manifold: Tuple[float, ...] = field(
        default_factory=lambda: (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    )
    participants: Tuple[str, ...] = field(default_factory=tuple)
    threshold: int = 3
    latest_binding: Optional[str] = None

    def __init__(self, **kwargs: Any) -> None:
        self.egg_id = str(kwargs.get("egg_id", kwargs.get("id", "egg")))
        self.payload = _safe_bytes(kwargs.get("payload", b""))
        m = kwargs.get("manifold", (0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
        if isinstance(m, (list, tuple)) and len(m) == 6:
            self.manifold = tuple(float(x) for x in m)
        else:
            self.manifold = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        p = kwargs.get("participants", ())
        self.participants = (
            tuple(str(x) for x in p) if isinstance(p, (list, tuple)) else tuple()
        )
        self.threshold = int(kwargs.get("threshold", 3))
        self.latest_binding = None

    def invoke_ritual(self, ritual: str, **kwargs: Any) -> Dict[str, Any]:
        r = (ritual or "").strip().lower()
        if r in {
            "solitary_incubation",
            "begin_solitary_incubation",
            "incubate_solitary",
            "incubate",
        }:
            return self.solitary_incubation(**kwargs)
        if r in {
            "triadic_binding",
            "perform_triadic_binding",
            "triadic_bind",
            "bind_triad",
            "triad_bind",
        }:
            return self.triadic_binding(**kwargs)
        if r in {
            "manifold_binding",
            "bind_manifold",
            "bind_to_manifold",
            "manifold_bind",
            "lock_to_manifold",
        }:
            return self.manifold_binding(**kwargs)
        if r in {"ring_descent", "perform_ring_descent", "descend_ring", "descent"}:
            return self.ring_descent(**kwargs)
        if r in {
            "fail_to_noise",
            "noise_failover",
            "zeroize_to_noise",
            "obscure_to_noise",
        }:
            return self.fail_to_noise(**kwargs)
        return {"ok": False, "status": "rejected", "error": "unknown_ritual"}

    def solitary_incubation(
        self,
        actor: Optional[str] = None,
        participants: Optional[Iterable[str]] = None,
        **_: Any,
    ) -> Dict[str, Any]:
        member_list = (
            list(participants)
            if participants is not None
            else ([actor] if actor else [])
        )
        if len(member_list) != 1:
            return {"ok": False, "status": "rejected", "error": "requires_one_invoker"}
        return {
            "ok": True,
            "status": "accepted",
            "mode": "solitary_incubation",
            "actor": str(member_list[0]),
        }

    def triadic_binding(
        self,
        participants: Optional[Iterable[str]] = None,
        threshold: int = 3,
        payload: Any = None,
        manifold: Any = None,
        **_: Any,
    ) -> Dict[str, Any]:
        parts = tuple(str(x) for x in (participants or self.participants))
        k = int(threshold if threshold is not None else self.threshold)
        if k <= 0 or len(parts) < k:
            return {
                "ok": False,
                "status": "rejected",
                "error": "insufficient_participants",
            }
        if not _distinct(parts):
            return {
                "ok": False,
                "status": "rejected",
                "error": "participants_not_distinct",
            }

        manifold_point = manifold if manifold is not None else self.manifold
        if not _valid_manifold(manifold_point):
            return {"ok": False, "status": "rejected", "error": "invalid_manifold"}

        raw_payload = _safe_bytes(payload if payload is not None else self.payload)
        token = _binding_token(
            parts, k, raw_payload, tuple(float(x) for x in manifold_point)
        )
        self.latest_binding = token
        return {
            "ok": True,
            "status": "bound",
            "binding": token,
            "threshold": k,
            "participants": list(parts),
        }

    def manifold_binding(self, **kwargs: Any) -> Dict[str, Any]:
        return self.triadic_binding(**kwargs)

    def verify_binding(
        self,
        binding: Any = None,
        participants: Optional[Iterable[str]] = None,
        threshold: int = 3,
        payload: Any = None,
        manifold: Any = None,
        **_: Any,
    ) -> Dict[str, Any]:
        token = binding
        if isinstance(binding, dict):
            token = binding.get("binding")
        if token is None:
            return {"ok": False, "status": "rejected", "error": "missing_binding"}

        parts = tuple(str(x) for x in (participants or self.participants))
        k = int(threshold if threshold is not None else self.threshold)
        manifold_point = manifold if manifold is not None else self.manifold
        if not _valid_manifold(manifold_point):
            return {"ok": False, "status": "rejected", "error": "invalid_manifold"}
        if k <= 0 or len(parts) < k or not _distinct(parts):
            return {"ok": False, "status": "rejected", "error": "invalid_participants"}

        raw_payload = _safe_bytes(payload if payload is not None else self.payload)
        expected = _binding_token(
            parts, k, raw_payload, tuple(float(x) for x in manifold_point)
        )
        if str(token) != expected:
            return {"ok": False, "status": "rejected", "error": "binding_mismatch"}
        return {"ok": True, "status": "verified", "binding": expected}

    def ring_descent(
        self, ring: int = 0, source_ring: int = 0, target_ring: int = 0, **_: Any
    ) -> Dict[str, Any]:
        try:
            current = int(source_ring if source_ring is not None else ring)
            nxt = int(target_ring if target_ring is not None else ring)
        except Exception:
            return {"ok": False, "status": "rejected", "error": "invalid_ring"}
        if current < 0 or nxt < 0:
            return {"ok": False, "status": "rejected", "error": "negative_ring"}
        return {
            "ok": True,
            "status": "accepted",
            "source_ring": current,
            "target_ring": nxt,
        }

    def fail_to_noise(self, **_: Any) -> Dict[str, Any]:
        # Do not leak payload in any error surface.
        noise = base64.urlsafe_b64encode(
            hashlib.sha256(_GOOD_NOISE + os.urandom(16)).digest()
        ).decode("ascii")
        return {"ok": False, "status": "rejected", "noise": noise}


def create_sacred_egg(**kwargs: Any) -> SacredEgg:
    return SacredEgg(**kwargs)


def invoke_ritual(ritual: str, **kwargs: Any) -> Dict[str, Any]:
    egg = kwargs.get("egg")
    if isinstance(egg, SacredEgg):
        return egg.invoke_ritual(ritual, **kwargs)
    return SacredEgg(**kwargs).invoke_ritual(ritual, **kwargs)


def solitary_incubation(**kwargs: Any) -> Dict[str, Any]:
    return invoke_ritual("solitary_incubation", **kwargs)


def triadic_binding(**kwargs: Any) -> Dict[str, Any]:
    return invoke_ritual("triadic_binding", **kwargs)


def manifold_binding(**kwargs: Any) -> Dict[str, Any]:
    return invoke_ritual("manifold_binding", **kwargs)


def verify_binding(**kwargs: Any) -> Dict[str, Any]:
    egg = kwargs.get("egg")
    if isinstance(egg, SacredEgg):
        return egg.verify_binding(**kwargs)
    return SacredEgg(**kwargs).verify_binding(**kwargs)


def ring_descent(**kwargs: Any) -> Dict[str, Any]:
    return invoke_ritual("ring_descent", **kwargs)


def fail_to_noise(**kwargs: Any) -> Dict[str, Any]:
    return invoke_ritual("fail_to_noise", **kwargs)
