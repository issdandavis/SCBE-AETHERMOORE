"""Quick MOSES-style benchmark for molecular generation.

Uses a small subset of the MOSES training set for fast baseline validation.
Metrics: validity, uniqueness, novelty, filters, diversity, SNN.
"""

from __future__ import annotations

import csv
import os
import random
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, List, Set

import numpy as np
from rdkit import Chem, rdBase
from rdkit.Chem import AllChem, DataStructs, Descriptors

rdBase.DisableLog("rdApp.error")
rdBase.DisableLog("rdApp.warning")

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

TRAIN_PATH = "training-data/moses/train.csv"
N_TRAIN_FOR_MODEL = 5_000
N_GENERATE = 1_000
MARKOV_ORDER = 5


class MarkovModel:
    def __init__(self, order: int = 5):
        self.order = order
        self.transitions: Dict[str, List[str]] = defaultdict(list)

    def fit(self, smiles_list: List[str]) -> None:
        for smi in smiles_list:
            padded = "~" * self.order + smi + "$"
            for i in range(len(padded) - self.order):
                ctx = padded[i : i + self.order]
                nxt = padded[i + self.order]
                self.transitions[ctx].append(nxt)

    def generate(self, max_len: int = 100) -> str:
        ctx = "~" * self.order
        out = []
        for _ in range(max_len):
            choices = self.transitions.get(ctx, [])
            if not choices:
                break
            nxt = random.choice(choices)
            if nxt == "$":
                break
            out.append(nxt)
            ctx = (ctx + nxt)[-self.order :]
        return "".join(out)


def load_smiles(path: str, n: int) -> List[str]:
    smiles = []
    with open(path, "r", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        for row in reader:
            if not row:
                continue
            s = row[0].strip()
            if s and s != "SMILES":
                smiles.append(s)
            if len(smiles) >= n:
                break
    return smiles


def evaluate(smiles_list: List[str], train_set: Set[str]) -> Dict[str, float]:
    valid = []
    for smi in smiles_list:
        mol = Chem.MolFromSmiles(smi)
        if mol is not None:
            valid.append((smi, mol))

    validity = len(valid) / len(smiles_list) if smiles_list else 0.0
    unique_valid = {}
    for smi, mol in valid:
        unique_valid[smi] = mol
    uniqueness = len(unique_valid) / len(valid) if valid else 0.0

    novel = [smi for smi in unique_valid if smi not in train_set]
    novelty = len(novel) / len(unique_valid) if unique_valid else 0.0

    # Filters: basic drug-likeness (MolWt < 500, LogP < 5)
    passed = 0
    for mol in unique_valid.values():
        mw = Descriptors.MolWt(mol)
        logp = Descriptors.MolLogP(mol)
        if mw < 500 and logp < 5:
            passed += 1
    filters = passed / len(unique_valid) if unique_valid else 0.0

    # Diversity: average pairwise Tanimoto (sample subset for speed)
    fps = []
    for mol in unique_valid.values():
        fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
        fps.append(fp)

    if len(fps) > 1:
        n_sample = min(200, len(fps))
        idx = np.random.choice(len(fps), n_sample, replace=False)
        sample_fps = [fps[i] for i in idx]
        sims = []
        for i in range(len(sample_fps)):
            for j in range(i + 1, len(sample_fps)):
                sims.append(DataStructs.TanimotoSimilarity(sample_fps[i], sample_fps[j]))
        diversity = 1.0 - (np.mean(sims) if sims else 0.0)
    else:
        diversity = 0.0

    # SNN: mean similarity to nearest neighbor in training set
    train_fps = []
    for smi in list(train_set)[:2000]:
        mol = Chem.MolFromSmiles(smi)
        if mol:
            train_fps.append(AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048))

    if fps and train_fps:
        nn_sims = []
        for fp in fps[:200]:
            best = max(DataStructs.TanimotoSimilarity(fp, tfp) for tfp in train_fps)
            nn_sims.append(best)
        snn = np.mean(nn_sims)
    else:
        snn = 0.0

    return {
        "validity": round(validity, 4),
        "uniqueness": round(uniqueness, 4),
        "novelty": round(novelty, 4),
        "filters": round(filters, 4),
        "diversity": round(diversity, 4),
        "snn": round(snn, 4),
        "n_generated": len(smiles_list),
        "n_valid": len(valid),
        "n_unique": len(unique_valid),
    }


def main() -> int:
    if not os.path.exists(TRAIN_PATH):
        print(f"Missing {TRAIN_PATH}")
        return 1

    print("Loading training set...")
    train_smiles = load_smiles(TRAIN_PATH, N_TRAIN_FOR_MODEL)
    print(f"Loaded {len(train_smiles)} training SMILES")

    print("Fitting Markov model...")
    model = MarkovModel(order=MARKOV_ORDER)
    model.fit(train_smiles)

    print("Generating molecules...")
    generated = []
    for _ in range(N_GENERATE):
        smi = model.generate()
        if smi:
            generated.append(smi)

    print(f"Generated {len(generated)} molecules")

    print("Evaluating...")
    train_set = set(train_smiles)
    metrics = evaluate(generated, train_set)

    print("\n=== MOSES Baseline Results ===")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

    # Save
    import json
    from pathlib import Path

    out_path = Path("artifacts/moses_baseline_quick.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(metrics, fh, indent=2)
    print(f"\nSaved to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
