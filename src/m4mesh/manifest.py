from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import hashlib
import json


@dataclass(frozen=True)
class FluxManifest:
    # CVL
    alpha_C: float
    alpha_K: float
    alpha_T: float
    activation: str = "relu"
    shared_dim: Optional[int] = None

    # TIE-KB
    top_k: int = 8
    temperature: float = 0.2
    query_map: str = "Q_fixed_v1"

    # Geometry
    curvature_c: float = 1.0
    projection: str = "tanh_ball_v1"

    # Wave
    wave_alpha: float = 0.15
    wave_gamma: float = 0.25
    wave_steps: int = 6
    wave_init: str = "z_minus_1_equals_z0"

    # Gates
    visibility_gate: str = "block_keep_CK_hide_T"
    physics_gate: str = "in_loop_block_keep_CK_hide_T"

    # SMEAR
    smear_enabled: bool = True
    smear_J: int = 2
    smear_betas: List[float] = field(default_factory=lambda: [0.6, 0.3, 0.1])

    # Metrics
    epsilon_leak: float = 0.05
    rho_max: float = 0.15

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cvl": {
                "weights": {
                    "alpha_C": self.alpha_C,
                    "alpha_K": self.alpha_K,
                    "alpha_T": self.alpha_T,
                },
                "activation": self.activation,
                "projections": {"shared_dim": self.shared_dim},
            },
            "tie_kb": {
                "top_k": self.top_k,
                "temperature": self.temperature,
                "query_map": self.query_map,
            },
            "geometry": {
                "curvature_c": self.curvature_c,
                "projection": self.projection,
            },
            "wave": {
                "alpha": self.wave_alpha,
                "gamma": self.wave_gamma,
                "steps": self.wave_steps,
                "init": self.wave_init,
            },
            "gates": {
                "visibility": self.visibility_gate,
                "physics": self.physics_gate,
            },
            "smear": {
                "enabled": self.smear_enabled,
                "J": self.smear_J,
                "betas": self.smear_betas,
            },
            "metrics": {
                "epsilon_leak": self.epsilon_leak,
                "rho_max": self.rho_max,
            },
        }

    def hash(self) -> str:
        blob = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
        return hashlib.sha256(blob).hexdigest()

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "FluxManifest":
        cvl = data["cvl"]
        tie = data["tie_kb"]
        geo = data["geometry"]
        wave = data["wave"]
        gates = data["gates"]
        smear = data["smear"]
        metrics = data["metrics"]
        return FluxManifest(
            alpha_C=float(cvl["weights"]["alpha_C"]),
            alpha_K=float(cvl["weights"]["alpha_K"]),
            alpha_T=float(cvl["weights"]["alpha_T"]),
            activation=str(cvl.get("activation", "relu")),
            shared_dim=cvl.get("projections", {}).get("shared_dim", None),
            top_k=int(tie.get("top_k", 8)),
            temperature=float(tie.get("temperature", 0.2)),
            query_map=str(tie.get("query_map", "Q_fixed_v1")),
            curvature_c=float(geo.get("curvature_c", 1.0)),
            projection=str(geo.get("projection", "tanh_ball_v1")),
            wave_alpha=float(wave.get("alpha", 0.15)),
            wave_gamma=float(wave.get("gamma", 0.25)),
            wave_steps=int(wave.get("steps", 6)),
            wave_init=str(wave.get("init", "z_minus_1_equals_z0")),
            visibility_gate=str(gates.get("visibility", "block_keep_CK_hide_T")),
            physics_gate=str(gates.get("physics", "in_loop_block_keep_CK_hide_T")),
            smear_enabled=bool(smear.get("enabled", True)),
            smear_J=int(smear.get("J", 2)),
            smear_betas=list(smear.get("betas", [0.6, 0.3, 0.1])),
            epsilon_leak=float(metrics.get("epsilon_leak", 0.05)),
            rho_max=float(metrics.get("rho_max", 0.15)),
        )
