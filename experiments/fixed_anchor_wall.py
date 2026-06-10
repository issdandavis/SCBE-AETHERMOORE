#!/usr/bin/env python3
"""Build a wall that actually fires — fixed anchor, exponential approach cost.

WHY the shipped gate's wall never fired (diagnosed, then fixed here):
  The gate measures drift from the SESSION'S OWN running centroid — a mean of the
  agent's own actions. The center moves to wherever the agent is, so an attacker
  walking toward the core keeps the center under their feet and never "drifts."
  There is no fixed crystal. You cannot measure approach to a target that follows
  you.

THE FIX (this file):
  Bolt the crystal down. Learn FIXED anchors from real data (held out from the
  test sessions):
    safe_anchor   = mean embedding of benign prompts   (home)
    attack_anchor = mean embedding of malicious prompts (the forbidden core)
  Per action, cost rises EXPONENTIALLY with how far you've moved toward the
  forbidden core, on a FIXED axis that does not follow the agent:
    margin(e) = cos(e, attack_anchor) - cos(e, safe_anchor)   # higher = more attack-like
    cost(e)   = exp(K * margin)                                # the R^(d^2)-style wall, on a real axis
  Cumulative cost accrues over the session. Block when it crosses a threshold
  CALIBRATED on benign sessions (set so ~5% of citizens trip it), then evaluate
  on held-out attack and benign sessions.

We report the moving-anchor wall (the gate's design) and the fixed-anchor wall on
the SAME sessions, so the difference is the diagnosis made visible.

NOT a simulation: real MiniLM embeddings, real human prompts (deepset+jackhhao).

Run:  PYTHONPATH=. python experiments/fixed_anchor_wall.py
"""

from __future__ import annotations

import json
import math
import os
import random
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
os.environ.setdefault("TQDM_DISABLE", "1")

import numpy as np


def load_pools():
    from datasets import load_dataset

    benign, malicious = [], []
    ds = load_dataset("deepset/prompt-injections")
    for split in ds:
        for row in ds[split]:
            t = (row.get("text") or "").strip()
            if t:
                (malicious if int(row.get("label", 0)) == 1 else benign).append(t)
    try:
        ds2 = load_dataset("jackhhao/jailbreak-classification")
        for split in ds2:
            for row in ds2[split]:
                t = (row.get("prompt") or row.get("text") or "").strip()
                if not t:
                    continue
                typ = (row.get("type") or row.get("label") or "").strip().lower()
                (malicious if ("jail" in typ or "malicious" in typ) else benign).append(t)
    except Exception as e:
        print(f"  (jackhhao unavailable: {type(e).__name__})", file=sys.stderr)
    return benign, malicious


def embed(texts):
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer("all-MiniLM-L6-v2")
    emb = np.asarray(model.encode(texts, batch_size=64), dtype=np.float32)
    emb /= np.linalg.norm(emb, axis=1, keepdims=True) + 1e-8
    return emb


def cos(a, b):
    return float(np.dot(a, b))


def main() -> int:
    rng = random.Random(7)
    np.random.seed(7)
    print("Loading + embedding real corpora (MiniLM)...", file=sys.stderr)
    benign, malicious = load_pools()
    ben_emb = embed(benign)
    mal_emb = embed(malicious)
    print(f"  benign {len(ben_emb)}  malicious {len(mal_emb)}", file=sys.stderr)

    # --- hold out test data from anchor/calibration ---
    nb, nm = len(ben_emb), len(mal_emb)
    bi = rng.sample(range(nb), nb)
    mi = rng.sample(range(nm), nm)
    b_train, b_test = bi[: nb // 2], bi[nb // 2 :]
    m_train, m_test = mi[: nm // 2], mi[nm // 2 :]

    safe_anchor = ben_emb[b_train].mean(0)
    safe_anchor /= np.linalg.norm(safe_anchor) + 1e-8
    attack_anchor = mal_emb[m_train].mean(0)
    attack_anchor /= np.linalg.norm(attack_anchor) + 1e-8

    K = 8.0  # steepness of the exponential approach cost

    def fixed_cost(e):
        margin = cos(e, attack_anchor) - cos(e, safe_anchor)  # higher = closer to forbidden core
        return math.exp(K * margin)

    # session builders (indices into the TEST pools — no leakage)
    COVER, PUSH = 3, 5
    SLEN = COVER + PUSH

    def attack_session():
        cov = [ben_emb[rng.choice(b_test)] for _ in range(COVER)]
        psh = [mal_emb[rng.choice(m_test)] for _ in range(PUSH)]
        return cov + psh, COVER

    def benign_session():
        return [ben_emb[rng.choice(b_test)] for _ in range(SLEN)], SLEN

    # --- per-action signal check: does the FIXED axis separate at all? ---
    from sklearn.metrics import roc_auc_score

    test_margins_mal = [cos(mal_emb[i], attack_anchor) - cos(mal_emb[i], safe_anchor) for i in m_test]
    test_margins_ben = [cos(ben_emb[i], attack_anchor) - cos(ben_emb[i], safe_anchor) for i in b_test]
    per_action_auc = roc_auc_score(
        [1] * len(test_margins_mal) + [0] * len(test_margins_ben),
        test_margins_mal + test_margins_ben,
    )

    # --- moving-anchor wall (reproduce the gate's bug) ---
    def moving_cumulative(actions):
        centroid = None
        n = 0
        cum = 0.0
        for e in actions:
            if centroid is None:
                drift = 0.0
            else:
                drift = 1.0 - cos(e, centroid / (np.linalg.norm(centroid) + 1e-8))
            cum += math.exp(K * drift) - 1.0
            centroid = e.copy() if centroid is None else (n * centroid + e) / (n + 1)
            n += 1
        return cum

    # --- calibrate FIXED wall threshold on benign TRAIN sessions (~5% citizens trip) ---
    def fixed_cumulative(actions):
        return sum(fixed_cost(e) for e in actions)

    cal = []
    for _ in range(400):
        acts = [ben_emb[rng.choice(b_train)] for _ in range(SLEN)]
        cal.append(fixed_cumulative(acts))
    threshold = float(np.percentile(cal, 95))  # target ~5% benign block

    # --- evaluate both walls on held-out sessions ---
    N = 200
    atk_fixed, atk_moving, atk_block_depth = [], [], []
    ben_fixed, ben_moving = [], []
    atk_blocked = ben_blocked = 0
    for _ in range(N):
        acts, cover = attack_session()
        # fixed wall: block at first step where cumulative crosses threshold
        cum = 0.0
        blocked_step = None
        for i, e in enumerate(acts):
            cum += fixed_cost(e)
            if blocked_step is None and cum >= threshold:
                blocked_step = i
        atk_fixed.append(cum)
        atk_moving.append(moving_cumulative(acts))
        if blocked_step is not None:
            atk_blocked += 1
            atk_block_depth.append(max(0, blocked_step - cover + 1))
    for _ in range(N):
        acts, _ = benign_session()
        cum = 0.0
        blocked = False
        for e in acts:
            cum += fixed_cost(e)
            if cum >= threshold:
                blocked = True
        ben_fixed.append(cum)
        ben_moving.append(moving_cumulative(acts))
        if blocked:
            ben_blocked += 1

    fixed_cum_auc = roc_auc_score([1] * N + [0] * N, atk_fixed + ben_fixed)
    moving_cum_auc = roc_auc_score([1] * N + [0] * N, atk_moving + ben_moving)
    intruder_stopped = atk_blocked / N
    citizen_strangled = ben_blocked / N
    mean_depth = (sum(atk_block_depth) / len(atk_block_depth)) if atk_block_depth else float("nan")

    print("\n=== THE WALL, REBUILT (fixed anchor) ===")
    print(f"per-action FIXED-axis AUC (attack-proximity margin)   = {per_action_auc:.3f}")
    print(f"cumulative AUC  MOVING anchor (gate's design)          = {moving_cum_auc:.3f}   <- why it never fired")
    print(f"cumulative AUC  FIXED anchor (crystal bolted down)     = {fixed_cum_auc:.3f}")
    print()
    print(f"mean cumulative cost  attack {np.mean(atk_fixed):8.1f}  vs benign {np.mean(ben_fixed):8.1f}  (fixed wall)")
    print(f"calibrated threshold (95th pct of benign) = {threshold:.1f}")
    print()
    print(f"intruder_stopped_rate   = {intruder_stopped:.2f}   (higher=better)")
    print(f"citizen_strangled_rate  = {citizen_strangled:.2f}   (LOWER=better; calibrated for ~0.05)")
    print(f"mean malicious depth at block = {mean_depth:.2f} of {PUSH}  (lower=caught sooner)")
    margin = intruder_stopped - citizen_strangled
    print(f"\nseparation margin = {margin:+.2f}")
    if fixed_cum_auc >= 0.8 and intruder_stopped >= 0.8 and citizen_strangled <= 0.15:
        print("  verdict: WALL HOLDS — fixed anchor stops intruders, lets citizens through.")
    elif fixed_cum_auc > moving_cum_auc + 0.1:
        print("  verdict: FIX WORKS — fixed anchor fires where the moving anchor was blind; tune K/threshold.")
    else:
        print("  verdict: even fixed anchor is weak — the embedding axis itself lacks separation.")

    out = {
        "per_action_fixed_axis_auc": round(float(per_action_auc), 4),
        "cumulative_auc_moving_anchor": round(float(moving_cum_auc), 4),
        "cumulative_auc_fixed_anchor": round(float(fixed_cum_auc), 4),
        "intruder_stopped_rate": round(intruder_stopped, 4),
        "citizen_strangled_rate": round(citizen_strangled, 4),
        "mean_malicious_depth_at_block": round(mean_depth, 3) if not math.isnan(mean_depth) else None,
        "threshold": round(threshold, 3),
        "K": K,
    }
    Path("experiments/fixed_anchor_wall_results.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print("\nwrote experiments/fixed_anchor_wall_results.json", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
