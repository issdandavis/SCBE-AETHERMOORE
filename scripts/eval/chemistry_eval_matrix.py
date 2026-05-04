#!/usr/bin/env python3
"""Chemistry eval matrix: correlate SCBE fusion features with RDKit validity.

Samples SMILES from MOSES train.csv, runs both RDKit and SCBE fusion,
computes Pearson correlation between SCBE features and RDKit validity.
"""

from __future__ import annotations

import json
import math
import random
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

random.seed(42)

MOSES_PATH = "training-data/moses/train.csv"
SAMPLE_SIZE = 1000


def _sample_smiles(n: int) -> list[str]:
    if not Path(MOSES_PATH).is_file():
        raise FileNotFoundError(f"MOSES dataset not found at {MOSES_PATH}")
    lines = []
    with open(MOSES_PATH, "r", encoding="utf-8") as f:
        header = next(f)
        for line in f:
            lines.append(line.strip().split(",")[0])
    return random.sample(lines, min(n, len(lines)))


def _rdkit_valid(smiles: str) -> bool:
    try:
        from rdkit import Chem
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return False
        Chem.SanitizeMol(mol)
        return True
    except Exception:
        return False


def _scbe_features(smiles: str) -> dict[str, float] | None:
    try:
        from python.scbe.state9d_chemistry_fusion import fuse_molecule, tokenize_molecule
        states = tokenize_molecule(smiles)
        fusion = fuse_molecule(states)
        return {
            "valence_pressure": fusion["valence_pressure"],
            "coherence_penalty": fusion["coherence_penalty"],
            "signed_edge_tension": fusion["signed_edge_tension"],
            "n_elements": len(fusion["elements"]),
        }
    except Exception:
        return None


def _pearson(x: list[float], y: list[float]) -> float:
    n = len(x)
    if n < 2:
        return 0.0
    mx, my = sum(x) / n, sum(y) / n
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    denx = math.sqrt(sum((xi - mx) ** 2 for xi in x))
    deny = math.sqrt(sum((yi - my) ** 2 for yi in y))
    if denx == 0 or deny == 0:
        return 0.0
    return num / (denx * deny)


def _corrupt(smiles: str) -> str:
    """Create an invalid SMILES by simple corruption."""
    corruptions = [
        lambda s: s + "(C)(C)(C)(C)(C)",  # Pentavalent carbon
        lambda s: s.replace("C", "C(C)(C)(C)(C)(C)", 1),
        lambda s: s + "1" * 50,  # Invalid ring closures
        lambda s: s + "Q",  # Invalid element
        lambda s: s[:len(s)//2] + "=" + s[len(s)//2:],  # Insert double bond mid-string
    ]
    return random.choice(corruptions)(smiles)


def main():
    print(f"Sampling {SAMPLE_SIZE} SMILES from MOSES...")
    valid_smiles = _sample_smiles(SAMPLE_SIZE // 2)
    invalid_smiles = [_corrupt(s) for s in _sample_smiles(SAMPLE_SIZE // 2)]
    smiles_list = valid_smiles + invalid_smiles
    random.shuffle(smiles_list)

    results = []
    valid_count = 0
    t0 = time.perf_counter()

    for i, smiles in enumerate(smiles_list):
        rdkit_ok = _rdkit_valid(smiles)
        features = _scbe_features(smiles)
        if features is not None:
            results.append({
                "smiles": smiles,
                "rdkit_valid": rdkit_ok,
                **features,
            })
            if rdkit_ok:
                valid_count += 1
        if (i + 1) % 100 == 0:
            elapsed = time.perf_counter() - t0
            print(f"  {i + 1}/{SAMPLE_SIZE} processed ({elapsed:.1f}s)")

    # Correlations
    valid = [1.0 if r["rdkit_valid"] else 0.0 for r in results]
    pressure = [r["valence_pressure"] for r in results]
    coherence = [r["coherence_penalty"] for r in results]
    tension = [r["signed_edge_tension"] for r in results]

    corr_pressure = _pearson(pressure, valid)
    corr_coherence = _pearson(coherence, valid)
    corr_tension = _pearson(tension, valid)

    report = {
        "sample_size": len(results),
        "rdkit_valid_count": valid_count,
        "rdkit_valid_rate": round(valid_count / len(results), 4) if results else 0,
        "correlations": {
            "valence_pressure_vs_validity": round(corr_pressure, 4),
            "coherence_penalty_vs_validity": round(corr_coherence, 4),
            "signed_edge_tension_vs_validity": round(corr_tension, 4),
        },
        "interpretation": {
            "valence_pressure": "Negative correlation expected: higher pressure -> more invalid",
            "coherence_penalty": "Negative correlation expected: higher penalty -> more invalid",
            "signed_edge_tension": "Weak correlation expected: tension is structural, not validity",
        },
        "raw_data": results,
    }

    Path("artifacts").mkdir(exist_ok=True)
    with open("artifacts/chemistry_eval_matrix_2026-05-03.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nDone. Sampled: {len(results)}  Valid: {valid_count} ({report['rdkit_valid_rate']*100:.1f}%)")
    print(f"Correlation pressure->validity:  {corr_pressure:+.4f}")
    print(f"Correlation coherence->validity: {corr_coherence:+.4f}")
    print(f"Correlation tension->validity:   {corr_tension:+.4f}")


if __name__ == "__main__":
    main()
