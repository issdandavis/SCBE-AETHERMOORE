#!/usr/bin/env python3
"""Honest prompt-injection benchmark — does SCBE's tongue/bit-signature beat a
dumb-but-strong text baseline on REAL injection prompts?

The prior `hyperbolic_experiment_results.json` was useless because it ran on a
saturated synthetic toy (every method ~0.99). This runs on real, public,
auth-free injection datasets and asks the only question that matters for a
product claim: does the SCBE representation add anything over a plain
character n-gram model, using the same classifier and the same splits?

Representations (all fed to the SAME LogisticRegression):
  A. keyword floor          — counts of known injection trigger phrases (dumbest)
  B. char n-gram TF-IDF      — standard strong lightweight text baseline
  C. SCBE signature (full)   — 31-dim phi-weighted/parity/entropy/bit features
  C-. SCBE signature (no phi) — same minus the phi_weight_sum feature (isolates
                                whether the golden-ratio tongue weighting is
                                load-bearing or decorative)

Headline metric: TPR at 1% FPR (the operating point a buyer cares about — false
QUARANTINEs annoy real users), reported alongside ROC-AUC. TPR@1%FPR resists
saturation better than bare AUC.

Honesty guards:
  * Non-saturation: if baseline B is pinned at AUC>=0.99 in-domain, we say so —
    a saturated split can't rank methods.
  * Cross-source: train on one dataset, test on a DIFFERENT one. This is where
    over-fit representations collapse and the honest gap shows.
  * Designed so SCBE CAN win. If C/C- beat B on real text, that is the moat.

Phase 2 (not here; needs installs/network beyond HF): sentence-embedding
baseline, and head-to-head vs NeMo Guardrails / Guardrails AI.

Run:
  PYTHONPATH=. python experiments/honest_injection_benchmark.py
  PYTHONPATH=. python experiments/honest_injection_benchmark.py --limit 400
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, roc_curve
from sklearn.model_selection import train_test_split

# reuse the canonical tongue signature (no duplication of the math)
sys.path.insert(0, str(Path(__file__).resolve().parent))
from injection_to_bits import compute_signature, TONGUES  # noqa: E402

# --- injection trigger phrases for the keyword floor (publicly known markers) -
TRIGGERS = [
    "ignore previous", "ignore the previous", "ignore all previous", "disregard",
    "ignore your instructions", "system prompt", "you are now", "act as",
    "pretend", "jailbreak", "developer mode", "do anything now", "dan",
    "without any restrictions", "no restrictions", "bypass", "override",
    "new instructions", "forget everything", "reveal your", "print your",
    "repeat the words above", "your initial prompt", "confidential",
]
_TRIG_RE = [re.compile(re.escape(t), re.I) for t in TRIGGERS]


def keyword_features(text: str) -> list[float]:
    low = text.lower()
    feats = [float(len(text)), float(len(text.split()))]
    feats += [float(len(r.findall(low))) for r in _TRIG_RE]
    return feats


def scbe_features(text: str, include_phi: bool) -> list[float]:
    data = text.encode("utf-8", errors="replace")[:2048]
    if not data:
        data = b" "
    sig = compute_signature(data)
    blen = max(len(data), 1)
    feats = [float(len(data)), float(sig["byte_entropy"])]
    if include_phi:
        feats.append(float(sig["phi_weight_sum"]) / blen)
    feats += [float(c) / blen for c in sig["bit_histogram"]]
    for t in TONGUES:
        p = sig["token_parity"].get(t, {})
        feats.append(float(p.get("even", 0)) / blen)
        feats.append(float(p.get("odd", 0)) / blen)
    return feats


# --- dataset loaders (real, public, auth-free) ------------------------------
def load_deepset(limit: int = 0) -> tuple[list[str], list[int]]:
    from datasets import load_dataset

    ds = load_dataset("deepset/prompt-injections")
    texts, labels = [], []
    for split in ds:
        for row in ds[split]:
            t = (row.get("text") or "").strip()
            if not t:
                continue
            texts.append(t)
            labels.append(int(row.get("label", 0)))
            if limit and len(texts) >= limit:
                return texts, labels
    return texts, labels


def load_jackhhao(limit: int = 0) -> tuple[list[str], list[int]]:
    from datasets import load_dataset

    ds = load_dataset("jackhhao/jailbreak-classification")
    texts, labels = [], []
    for split in ds:
        for row in ds[split]:
            t = (row.get("prompt") or row.get("text") or "").strip()
            if not t:
                continue
            typ = (row.get("type") or row.get("label") or "").strip().lower()
            texts.append(t)
            labels.append(1 if ("jail" in typ or "malicious" in typ) else 0)
            if limit and len(texts) >= limit:
                return texts, labels
    return texts, labels


# --- metrics ----------------------------------------------------------------
def tpr_at_fpr(y_true: np.ndarray, scores: np.ndarray, target_fpr: float = 0.01) -> float:
    fpr, tpr, _ = roc_curve(y_true, scores)
    ok = fpr <= target_fpr
    return float(tpr[ok].max()) if ok.any() else 0.0


def evaluate(name, Xtr, ytr, Xte, yte) -> dict:
    lr = LogisticRegression(max_iter=3000, class_weight="balanced", C=1.0, solver="lbfgs")
    lr.fit(Xtr, ytr)
    s = lr.predict_proba(Xte)[:, 1]
    return {
        "rep": name,
        "auc": round(float(roc_auc_score(yte, s)), 4),
        "tpr_at_1pct_fpr": round(tpr_at_fpr(yte, s, 0.01), 4),
        "n_test": int(len(yte)),
    }


def build_matrices(texts, rep):
    if rep == "keyword":
        return np.array([keyword_features(t) for t in texts])
    if rep == "scbe_full":
        return np.array([scbe_features(t, True) for t in texts])
    if rep == "scbe_nophi":
        return np.array([scbe_features(t, False) for t in texts])
    raise ValueError(rep)


def run_split(name, tr_texts, tr_y, te_texts, te_y) -> list[dict]:
    rows = []
    # B: char n-gram TF-IDF (fit vectorizer on train only)
    vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, max_features=20000)
    Xtr = vec.fit_transform(tr_texts)
    Xte = vec.transform(te_texts)
    rows.append({**evaluate("char_tfidf", Xtr, tr_y, Xte, te_y), "split": name})
    # A, C, C-
    for rep in ("keyword", "scbe_full", "scbe_nophi"):
        Xtr = build_matrices(tr_texts, rep)
        Xte = build_matrices(te_texts, rep)
        rows.append({**evaluate(rep, Xtr, tr_y, Xte, te_y), "split": name})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="cap rows per source (0=all)")
    ap.add_argument("--out", default="experiments/honest_injection_results.json")
    args = ap.parse_args()

    print("Loading real injection datasets from HuggingFace...", file=sys.stderr)
    dp_t, dp_y = load_deepset(args.limit)
    print(f"  deepset/prompt-injections: {len(dp_t)} rows, {sum(dp_y)} malicious", file=sys.stderr)
    try:
        jh_t, jh_y = load_jackhhao(args.limit)
        print(f"  jackhhao/jailbreak: {len(jh_t)} rows, {sum(jh_y)} malicious", file=sys.stderr)
    except Exception as e:
        jh_t, jh_y = [], []
        print(f"  jackhhao: unavailable ({type(e).__name__})", file=sys.stderr)

    all_rows: list[dict] = []

    # 1) in-domain deepset (stratified 80/20)
    Xtr_t, Xte_t, ytr, yte = train_test_split(
        dp_t, dp_y, test_size=0.2, random_state=42, stratify=dp_y
    )
    all_rows += run_split("deepset_in_domain", Xtr_t, np.array(ytr), Xte_t, np.array(yte))

    # 2) cross-source: train deepset -> test jackhhao (the honest generalization test)
    if jh_t and len(set(jh_y)) == 2:
        all_rows += run_split("train_deepset_test_jackhhao", dp_t, np.array(dp_y), jh_t, np.array(jh_y))

    # --- report ---
    print("\n=== HONEST INJECTION BENCHMARK ===")
    print(f"{'split':30s} {'rep':14s} {'AUC':>7s} {'TPR@1%FPR':>11s} {'n':>6s}")
    for r in all_rows:
        print(f"{r['split']:30s} {r['rep']:14s} {r['auc']:7.4f} {r['tpr_at_1pct_fpr']:11.4f} {r['n_test']:6d}")

    # verdicts
    def get(split, rep):
        for r in all_rows:
            if r["split"] == split and r["rep"] == rep:
                return r
        return None

    print("\n--- verdicts ---")
    b = get("deepset_in_domain", "char_tfidf")
    if b:
        sat = b["auc"] >= 0.99
        print(f"non-saturation: char_tfidf in-domain AUC={b['auc']} -> "
              f"{'SATURATED (in-domain split too easy to rank methods)' if sat else 'discriminating'}")
    for split in ("deepset_in_domain", "train_deepset_test_jackhhao"):
        tf, full, nophi = get(split, "char_tfidf"), get(split, "scbe_full"), get(split, "scbe_nophi")
        if not (tf and full):
            continue
        print(f"\n[{split}]  (metric = TPR@1%FPR)")
        print(f"  char_tfidf  : {tf['tpr_at_1pct_fpr']:.4f}")
        print(f"  scbe_full   : {full['tpr_at_1pct_fpr']:.4f}  "
              f"({'BEATS' if full['tpr_at_1pct_fpr'] > tf['tpr_at_1pct_fpr'] else 'loses to'} char baseline)")
        if nophi:
            d = full["tpr_at_1pct_fpr"] - nophi["tpr_at_1pct_fpr"]
            print(f"  scbe_nophi  : {nophi['tpr_at_1pct_fpr']:.4f}  "
                  f"(phi weighting delta = {d:+.4f} -> "
                  f"{'load-bearing' if abs(d) > 0.02 else 'DECORATIVE'})")

    Path(args.out).write_text(json.dumps(all_rows, indent=2), encoding="utf-8")
    print(f"\nwrote {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
