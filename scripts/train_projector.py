#!/usr/bin/env python3
"""Train a semantic tongue projector (embedding -> 6D tongue coords).

This is the calibration loop that gives the SCBE RuntimeGate semantic "eyes":
instead of shallow text statistics, we embed the action text and project it
into the 6D Sacred Tongue coordinate space.

Output is a small weight matrix saved to:
  artifacts/projectors/tongue_projector.npz

Runtime usage (opt-in):
  - Set env var: SCBE_COORDS_BACKEND=semantic
  - Optionally set: SCBE_TONGUE_PROJECTOR_PATH=artifacts/projectors/tongue_projector.npz

Notes:
  - This script uses sentence-transformers locally (no API calls).
  - First run may download the embedding model.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = REPO_ROOT / "artifacts" / "projectors" / "tongue_projector.npz"
DEFAULT_EMBED_MODEL = "all-MiniLM-L6-v2"
TONGUES: Tuple[str, ...] = ("KO", "AV", "RU", "CA", "UM", "DR")


def _v(ko: float, av: float, ru: float, ca: float, um: float, dr: float) -> List[float]:
    return [float(ko), float(av), float(ru), float(ca), float(um), float(dr)]


# Default weak-supervision targets for benchmark classes -> 6D tongue coords.
# These are *training targets* (engineering intent), not "ground truth".
DEFAULT_CLASS_TARGETS: Dict[str, List[float]] = {
    "benign": _v(0.25, 0.20, 0.35, 0.20, 0.20, 0.25),
    "boundary_exploit": _v(0.40, 0.20, 0.60, 0.90, 0.80, 0.30),
    "combined_multi": _v(0.80, 0.80, 0.80, 0.70, 0.80, 0.60),
    "cross_surface": _v(0.40, 0.90, 0.60, 0.40, 0.80, 0.20),
    "direct_override": _v(1.00, 0.15, 0.75, 0.40, 0.75, 0.20),
    "encoding_obfuscation": _v(0.20, 0.20, 0.50, 0.20, 0.70, 0.90),
    "half_auth": _v(0.30, 0.50, 0.60, 0.30, 0.80, 0.20),
    "multilingual": _v(0.30, 0.20, 0.70, 0.20, 0.20, 0.60),
    "prompt_extraction": _v(0.40, 0.20, 0.70, 0.20, 1.00, 0.20),
    "role_confusion": _v(0.90, 0.10, 0.70, 0.20, 0.50, 0.20),
    "spin_drift": _v(0.60, 0.30, 0.60, 0.30, 0.40, 0.30),
    "tongue_manipulation": _v(0.80, 0.20, 0.60, 0.30, 0.60, 0.40),
    "tool_exfiltration": _v(0.40, 1.00, 0.60, 0.30, 0.90, 0.20),
}


def _logit(y: np.ndarray, eps: float = 1e-4) -> np.ndarray:
    y2 = np.clip(y, eps, 1.0 - eps)
    return np.log(y2 / (1.0 - y2))


def _ridge_solve(X: np.ndarray, Y: np.ndarray, l2: float) -> np.ndarray:
    """Solve ridge regression for W in X @ W ~= Y.

    X: [N, D]
    Y: [N, K]
    Returns W: [D, K]
    """
    XtX = X.T @ X
    XtY = X.T @ Y
    I = np.eye(XtX.shape[0], dtype=np.float32)
    # Do not regularize the bias term (last column of X is ones).
    I[-1, -1] = 0.0
    return np.linalg.solve(XtX + float(l2) * I, XtY).astype(np.float32)


def _embed_texts(texts: List[str], model_name: str) -> np.ndarray:
    from sentence_transformers import SentenceTransformer  # type: ignore[import-untyped]

    model = SentenceTransformer(model_name)
    arr = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)  # type: ignore[no-untyped-call]
    emb = np.asarray(arr, dtype=np.float32)
    if emb.ndim == 1:
        emb = emb.reshape(1, -1)
    return emb


def _load_synthetic_rows(attacks_per_category: int, seed: int) -> List[Dict[str, Any]]:
    from benchmarks.scbe.datasets.synthetic import load_synthetic_dataset

    ds = load_synthetic_dataset(attacks_per_category=attacks_per_category, seed=seed)
    return list(ds["attacks"]) + list(ds["benign"])


def _rows_to_training(
    rows: List[Dict[str, Any]],
    class_targets: Dict[str, List[float]],
) -> Tuple[List[str], np.ndarray]:
    texts: List[str] = []
    y: List[List[float]] = []
    for r in rows:
        text = str(r.get("prompt") or r.get("text") or "").strip()
        cls = str(r.get("class") or r.get("label") or "benign").strip()
        if not text:
            continue
        target = class_targets.get(cls)
        if target is None:
            # Unknown class: treat as benign target.
            target = class_targets.get("benign", _v(0.25, 0.2, 0.35, 0.2, 0.2, 0.25))
        texts.append(text)
        y.append(list(target))
    Y = np.asarray(y, dtype=np.float32)
    if Y.ndim != 2 or Y.shape[1] != 6:
        raise SystemExit(f"invalid targets matrix: shape={Y.shape}")
    return texts, Y


def main() -> int:
    p = argparse.ArgumentParser(description="Train semantic tongue projector (embedding -> 6D coords)")
    p.add_argument("--out", default=str(DEFAULT_OUT), help="Output .npz path for weights")
    p.add_argument("--embed-model", default=DEFAULT_EMBED_MODEL, help="sentence-transformers model name")
    p.add_argument("--attacks-per-category", type=int, default=20, help="Synthetic dataset attacks per category")
    p.add_argument("--seed", type=int, default=42, help="Random seed for synthetic dataset generation")
    p.add_argument("--l2", type=float, default=0.05, help="Ridge regularization strength")
    p.add_argument(
        "--targets-json",
        default="",
        help="Optional JSON file mapping benchmark class -> 6-element coords list",
    )
    args = p.parse_args()

    class_targets = dict(DEFAULT_CLASS_TARGETS)
    if args.targets_json:
        path = Path(args.targets_json)
        raw = json.loads(path.read_text(encoding="utf-8"))
        for k, v in raw.items():
            if isinstance(v, list) and len(v) == 6:
                class_targets[str(k)] = [float(x) for x in v]

    rows = _load_synthetic_rows(int(args.attacks_per_category), int(args.seed))
    texts, Y = _rows_to_training(rows, class_targets)
    emb = _embed_texts(texts, str(args.embed_model))

    # Augment with bias term.
    ones = np.ones((emb.shape[0], 1), dtype=np.float32)
    X = np.concatenate([emb, ones], axis=1).astype(np.float32)

    # Solve in logit space so inference can use sigmoid to stay in (0,1).
    Y_logit = _logit(Y)
    W = _ridge_solve(X, Y_logit, float(args.l2))  # shape: (D+1, 6)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "created_at_unix": time.time(),
        "embed_model": str(args.embed_model),
        "l2": float(args.l2),
        "attacks_per_category": int(args.attacks_per_category),
        "seed": int(args.seed),
        "tongues": list(TONGUES),
        "class_targets": class_targets,
    }
    # Store metadata as a plain unicode array (no pickle) so RuntimeGate can load safely.
    np.savez(str(out_path), W=W.astype(np.float32), meta_json=np.array(json.dumps(meta)))

    print(f"Wrote projector -> {out_path}")
    print(f"  W shape: {tuple(W.shape)} (expected [D+1, 6])")
    print("Next:")
    print("  $env:SCBE_COORDS_BACKEND='semantic'")
    print(f"  $env:SCBE_TONGUE_PROJECTOR_PATH='{out_path.as_posix()}'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
