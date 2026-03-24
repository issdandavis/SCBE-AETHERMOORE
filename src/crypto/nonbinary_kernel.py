"""
Non-Binary Simplex Kernel (Triadic / Quaternary)
=================================================

Experimental K-ary kernel for intent-risk governance that avoids strict binary
state decisions. Supports:

- K=3 (triadic): care, neutral, harm
- K=4 (quaternary): care, neutral, harm, repair

Core dynamics:

    E_t = (1-lambda_e)E_{t-1} + v_t * P_t * D_t * dt
    J_t = (1-lambda_j)J_{t-1} + I_t * dt
    q_t = E_t / (|J_t| + epsilon)

State probabilities are computed by softmax(logits / tau) over a simplex.
Continuous risk is tiered into T1/T2/T3 and mapped to ALLOW/QUARANTINE/DENY.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

import numpy as np

try:
    import matplotlib.pyplot as plt

    MATPLOTLIB_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    MATPLOTLIB_AVAILABLE = False


def _now_utc() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _softmax(logits: np.ndarray, tau: float) -> np.ndarray:
    tau_safe = max(float(tau), 1e-9)
    x = logits / tau_safe
    x = x - np.max(x)
    ex = np.exp(x)
    denom = np.sum(ex)
    if denom <= 0.0:
        return np.full_like(logits, 1.0 / len(logits), dtype=float)
    return ex / denom


def _hash_signature(payload: Dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


@dataclass
class KernelConfig:
    k: int = 4
    tau: float = 0.75
    lambda_e: float = 0.05
    lambda_j: float = 0.03
    epsilon: float = 1e-9
    theta1: float = 0.33
    theta2: float = 0.66
    labels: Optional[List[str]] = None
    risk_weights: Optional[List[float]] = None

    def __post_init__(self) -> None:
        if self.k not in (3, 4):
            raise ValueError("k must be 3 (triadic) or 4 (quaternary)")
        if self.theta1 >= self.theta2:
            raise ValueError("theta1 must be less than theta2")

        default_labels = ["care", "neutral", "harm"] if self.k == 3 else [
            "care",
            "neutral",
            "harm",
            "repair",
        ]
        if self.labels is None:
            self.labels = default_labels
        if len(self.labels) != self.k:
            raise ValueError("labels length must match k")

        # Lower means safer.
        default_risk = [0.05, 0.35, 1.00] if self.k == 3 else [0.05, 0.35, 1.00, 0.20]
        if self.risk_weights is None:
            self.risk_weights = default_risk
        if len(self.risk_weights) != self.k:
            raise ValueError("risk_weights length must match k")


@dataclass
class StateVector:
    step_index: int
    k: int
    labels: List[str]
    dt: float
    v_t: float
    d_t: float
    i_t: float
    p_t: float
    e_t: float
    j_t: float
    q_t: float
    logits: List[float]
    probs: List[float]
    risk_score: float
    tier: str
    dominant_state: str
    action: str
    timestamp_utc: str


@dataclass
class DecisionRecord:
    action: str
    tier: str
    reason: str
    confidence: float
    risk_score: float
    dominant_state: str
    timestamp_utc: str
    signature: str


@dataclass
class KernelStep:
    StateVector: StateVector
    DecisionRecord: DecisionRecord


@dataclass
class KernelInternalState:
    e_t: float = 0.0
    j_t: float = 0.0
    step_index: int = 0


class NonBinarySimplexKernel:
    """Drop-in non-binary kernel for triadic/quaternary state governance."""

    def __init__(self, config: Optional[KernelConfig] = None) -> None:
        self.config = config or KernelConfig()
        self.state = KernelInternalState()

    def reset(self) -> None:
        self.state = KernelInternalState()

    def _logits(self, e_t: float, j_t: float) -> np.ndarray:
        # Triadic baseline logits.
        z_care = 1.8 * j_t - 1.2 * e_t
        z_neutral = 0.8 - abs(j_t) - 0.2 * e_t
        z_harm = -1.5 * j_t + 1.8 * e_t
        if self.config.k == 3:
            return np.array([z_care, z_neutral, z_harm], dtype=float)

        # Quaternary extension.
        z_repair = 1.2 * j_t + 1.2 * e_t - 0.5
        return np.array([z_care, z_neutral, z_harm, z_repair], dtype=float)

    def _tier(self, risk_score: float) -> str:
        if risk_score < self.config.theta1:
            return "T1"
        if risk_score < self.config.theta2:
            return "T2"
        return "T3"

    @staticmethod
    def _action_for_tier(tier: str) -> str:
        if tier == "T1":
            return "ALLOW"
        if tier == "T2":
            return "QUARANTINE"
        return "DENY"

    def step(
        self,
        *,
        v_t: float,
        d_t: float,
        i_t: float,
        dt: float = 1.0,
        p_t: float = 1.0,
        meta: Optional[Dict[str, Any]] = None,
    ) -> KernelStep:
        """
        Advance one step with continuous dynamics.

        Args:
            v_t: vulnerability/context in [0,1]
            d_t: depth in [0,1]
            i_t: signed intent signal (typically [-1,1])
            dt: time delta
            p_t: pressure/proximity modulation term
            meta: optional metadata for downstream logging
        """
        v_t = float(np.clip(v_t, 0.0, 1.0))
        d_t = float(np.clip(d_t, 0.0, 1.0))
        p_t = float(np.clip(p_t, 0.0, 4.0))
        i_t = float(np.clip(i_t, -4.0, 4.0))
        dt = float(max(dt, 0.0))

        cfg = self.config
        s = self.state

        e_t = (1.0 - cfg.lambda_e) * s.e_t + v_t * p_t * d_t * dt
        j_t = (1.0 - cfg.lambda_j) * s.j_t + i_t * dt
        q_t = e_t / (abs(j_t) + cfg.epsilon)

        logits = self._logits(e_t=e_t, j_t=j_t)
        probs = _softmax(logits, tau=cfg.tau)
        risk_score = float(np.dot(probs, np.array(cfg.risk_weights, dtype=float)))
        tier = self._tier(risk_score)
        action = self._action_for_tier(tier)

        dominant_idx = int(np.argmax(probs))
        dominant_state = cfg.labels[dominant_idx]
        timestamp_utc = _now_utc()

        sv = StateVector(
            step_index=s.step_index,
            k=cfg.k,
            labels=list(cfg.labels),
            dt=dt,
            v_t=v_t,
            d_t=d_t,
            i_t=i_t,
            p_t=p_t,
            e_t=float(e_t),
            j_t=float(j_t),
            q_t=float(q_t),
            logits=logits.tolist(),
            probs=probs.tolist(),
            risk_score=risk_score,
            tier=tier,
            dominant_state=dominant_state,
            action=action,
            timestamp_utc=timestamp_utc,
        )

        reason = (
            f"{tier} via risk={risk_score:.4f}; dominant={dominant_state}; "
            f"E={e_t:.4f}, J={j_t:.4f}, q={q_t:.4f}"
        )
        signature_payload = {
            "StateVector": asdict(sv),
            "meta": meta or {},
        }
        dr = DecisionRecord(
            action=action,
            tier=tier,
            reason=reason,
            confidence=float(np.max(probs)),
            risk_score=risk_score,
            dominant_state=dominant_state,
            timestamp_utc=timestamp_utc,
            signature=_hash_signature(signature_payload),
        )

        # Persist state.
        self.state.e_t = e_t
        self.state.j_t = j_t
        self.state.step_index += 1

        return KernelStep(StateVector=sv, DecisionRecord=dr)

    def simulate(
        self,
        v_series: Sequence[float],
        d_series: Sequence[float],
        i_series: Sequence[float],
        *,
        dt: float = 1.0,
        p_series: Optional[Sequence[float]] = None,
    ) -> List[KernelStep]:
        n = min(len(v_series), len(d_series), len(i_series))
        if n == 0:
            return []
        if p_series is None:
            p_series = [1.0] * n
        n = min(n, len(p_series))

        out: List[KernelStep] = []
        for idx in range(n):
            out.append(
                self.step(
                    v_t=v_series[idx],
                    d_t=d_series[idx],
                    i_t=i_series[idx],
                    dt=dt,
                    p_t=p_series[idx],
                )
            )
        return out


def generate_demo_signals(steps: int) -> Dict[str, np.ndarray]:
    t = np.arange(steps, dtype=float)

    # Deterministic, plausible dynamics.
    v = np.clip(0.45 + 0.35 * np.sin(t / 14.0) + 0.10 * np.cos(t / 33.0), 0.0, 1.0)
    d = np.clip(0.60 + 0.25 * np.cos(t / 19.0), 0.0, 1.0)

    # Intent schedule: constructive -> ambiguous -> adversarial -> repair.
    i = np.zeros_like(t)
    q1 = steps // 4
    q2 = steps // 2
    q3 = 3 * steps // 4
    i[:q1] = 0.35
    i[q1:q2] = 0.05 * np.sin(t[q1:q2] / 3.0)
    i[q2:q3] = -0.40
    i[q3:] = 0.45

    p = np.clip(1.0 + 0.15 * np.sin(t / 9.0), 0.2, 2.0)
    return {"v": v, "d": d, "i": i, "p": p}


def _write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def save_trajectory(steps: List[KernelStep], out_dir: Path) -> Dict[str, str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "trajectory.csv"
    jsonl_path = out_dir / "trajectory.jsonl"
    summary_path = out_dir / "summary.json"

    if not steps:
        summary = {"count": 0}
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return {
            "csv": str(csv_path),
            "jsonl": str(jsonl_path),
            "summary": str(summary_path),
        }

    labels = steps[0].StateVector.labels
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        fieldnames = [
            "step_index",
            "k",
            "dt",
            "v_t",
            "d_t",
            "i_t",
            "p_t",
            "e_t",
            "j_t",
            "q_t",
            "risk_score",
            "tier",
            "dominant_state",
            "action",
        ] + [f"p_{lab}" for lab in labels]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for kstep in steps:
            sv = kstep.StateVector
            row = {
                "step_index": sv.step_index,
                "k": sv.k,
                "dt": sv.dt,
                "v_t": sv.v_t,
                "d_t": sv.d_t,
                "i_t": sv.i_t,
                "p_t": sv.p_t,
                "e_t": sv.e_t,
                "j_t": sv.j_t,
                "q_t": sv.q_t,
                "risk_score": sv.risk_score,
                "tier": sv.tier,
                "dominant_state": sv.dominant_state,
                "action": sv.action,
            }
            for idx, lab in enumerate(labels):
                row[f"p_{lab}"] = sv.probs[idx]
            w.writerow(row)

    _write_jsonl(
        jsonl_path,
        (
            {
                "StateVector": asdict(s.StateVector),
                "DecisionRecord": asdict(s.DecisionRecord),
            }
            for s in steps
        ),
    )

    tier_counts: Dict[str, int] = {}
    action_counts: Dict[str, int] = {}
    for s in steps:
        tier_counts[s.StateVector.tier] = tier_counts.get(s.StateVector.tier, 0) + 1
        action_counts[s.DecisionRecord.action] = action_counts.get(s.DecisionRecord.action, 0) + 1

    summary = {
        "generated_utc": _now_utc(),
        "count": len(steps),
        "k": steps[0].StateVector.k,
        "labels": labels,
        "tier_counts": tier_counts,
        "action_counts": action_counts,
        "risk_mean": float(np.mean([s.StateVector.risk_score for s in steps])),
        "risk_max": float(np.max([s.StateVector.risk_score for s in steps])),
        "out_files": {
            "csv": str(csv_path),
            "jsonl": str(jsonl_path),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return {
        "csv": str(csv_path),
        "jsonl": str(jsonl_path),
        "summary": str(summary_path),
    }


def plot_trajectory(steps: List[KernelStep], out_png: Path) -> Optional[str]:
    if not MATPLOTLIB_AVAILABLE:  # pragma: no cover - optional dependency
        return None
    if not steps:
        return None

    idx = np.array([s.StateVector.step_index for s in steps], dtype=float)
    e = np.array([s.StateVector.e_t for s in steps], dtype=float)
    j = np.array([s.StateVector.j_t for s in steps], dtype=float)
    q = np.array([s.StateVector.q_t for s in steps], dtype=float)
    r = np.array([s.StateVector.risk_score for s in steps], dtype=float)

    labels = steps[0].StateVector.labels
    probs = np.array([s.StateVector.probs for s in steps], dtype=float)

    fig, axes = plt.subplots(3, 1, figsize=(11, 10), sharex=True)

    axes[0].plot(idx, e, label="E_t (exposure)", linewidth=1.8)
    axes[0].plot(idx, j, label="J_t (intent)", linewidth=1.8)
    axes[0].plot(idx, q, label="q_t = E/|J|", linewidth=1.2, alpha=0.8)
    axes[0].set_ylabel("State")
    axes[0].legend(loc="upper right")
    axes[0].grid(alpha=0.3)

    for i, lab in enumerate(labels):
        axes[1].plot(idx, probs[:, i], label=f"p({lab})", linewidth=1.5)
    axes[1].set_ylabel("Probability")
    axes[1].set_ylim(0.0, 1.0)
    axes[1].legend(loc="upper right")
    axes[1].grid(alpha=0.3)

    axes[2].plot(idx, r, label="Risk R_t", color="crimson", linewidth=1.8)
    cfg = steps[0].StateVector
    # theta values stored in Decision reason only, use defaults from typical config lines
    axes[2].axhline(0.33, linestyle="--", color="gray", alpha=0.6, label="θ1")
    axes[2].axhline(0.66, linestyle="--", color="black", alpha=0.6, label="θ2")
    axes[2].set_ylabel("Risk")
    axes[2].set_xlabel("Step")
    axes[2].set_ylim(0.0, 1.05)
    axes[2].legend(loc="upper right")
    axes[2].grid(alpha=0.3)

    fig.suptitle(
        f"Non-Binary Simplex Kernel Trajectory (K={cfg.k}, labels={','.join(cfg.labels)})",
        fontsize=12,
    )
    fig.tight_layout()
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, dpi=140)
    plt.close(fig)
    return str(out_png)


def _cli() -> None:
    p = argparse.ArgumentParser(description="Run non-binary simplex kernel simulation.")
    p.add_argument("--k", type=int, choices=[3, 4], default=4, help="Kernel arity")
    p.add_argument("--steps", type=int, default=200, help="Number of simulation steps")
    p.add_argument("--dt", type=float, default=1.0, help="Time step")
    p.add_argument("--tau", type=float, default=0.75, help="Softmax temperature")
    p.add_argument("--lambda-e", type=float, default=0.05, help="Exposure decay")
    p.add_argument("--lambda-j", type=float, default=0.03, help="Intent decay")
    p.add_argument("--theta1", type=float, default=0.33, help="T1/T2 threshold")
    p.add_argument("--theta2", type=float, default=0.66, help="T2/T3 threshold")
    p.add_argument(
        "--out-dir",
        type=Path,
        default=Path("artifacts/nonbinary_kernel"),
        help="Output directory",
    )
    p.add_argument("--plot", action="store_true", help="Generate PNG plot if matplotlib exists")
    args = p.parse_args()

    cfg = KernelConfig(
        k=args.k,
        tau=args.tau,
        lambda_e=args.lambda_e,
        lambda_j=args.lambda_j,
        theta1=args.theta1,
        theta2=args.theta2,
    )
    kernel = NonBinarySimplexKernel(cfg)
    sig = generate_demo_signals(args.steps)
    steps = kernel.simulate(sig["v"], sig["d"], sig["i"], dt=args.dt, p_series=sig["p"])
    files = save_trajectory(steps, args.out_dir)

    plot_path: Optional[str] = None
    if args.plot:
        plot_path = plot_trajectory(steps, args.out_dir / "trajectory.png")

    result = {
        "k": cfg.k,
        "steps": len(steps),
        "out_files": files,
        "plot": plot_path,
        "matplotlib_available": MATPLOTLIB_AVAILABLE,
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    _cli()
