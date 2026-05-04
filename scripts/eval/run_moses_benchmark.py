"""Real MOSES-style benchmark for molecular generation.

Trains a simple character-level Markov baseline on the MOSES training set,
generates molecules, and evaluates them with RDKit.

Metrics computed:
  - Validity     : % parseable by RDKit
  - Uniqueness   : % unique among valid
  - Novelty      : % not present in training set
  - Filters      : % passing basic drug-likeness filters
  - Diversity    : average pairwise Tanimoto distance (Morgan fingerprints)
  - SNN          : mean similarity to nearest neighbor in training set

Run:
    python scripts/eval/run_moses_benchmark.py
"""

from __future__ import annotations

import csv
import os
import random
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple

import numpy as np
from rdkit import Chem, rdBase
from rdkit.Chem import Descriptors, AllChem, DataStructs

# Suppress RDKit warnings
rdBase.DisableLog("rdApp.error")
rdBase.DisableLog("rdApp.warning")

RANDOM_SEED = 42
random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

TRAIN_PATH = "training-data/moses/train.csv"
N_TRAIN_FOR_MODEL = 50_000  # Subsample for fast Markov training
N_GENERATE = 10_000
MARKOV_ORDER = 5


# ---------------------------------------------------------------------------
# Character-level Markov model
# ---------------------------------------------------------------------------
class MarkovModel:
    """Character-level Markov chain for SMILES generation."""

    def __init__(self, order: int = 5):
        self.order = order
        self.transitions: Dict[str, Counter] = defaultdict(Counter)
        self.starts: List[str] = []

    def fit(self, smiles_list: List[str]):
        for smi in smiles_list:
            padded = "^" * self.order + smi + "$"
            self.starts.append(padded[: self.order])
            for i in range(len(padded) - self.order):
                context = padded[i : i + self.order]
                next_char = padded[i + self.order]
                self.transitions[context][next_char] += 1

    def _sample(self, context: str) -> str:
        counter = self.transitions.get(context)
        if not counter:
            return "$"
        chars, counts = zip(*counter.items())
        total = sum(counts)
        probs = [c / total for c in counts]
        return np.random.choice(chars, p=probs)

    def generate(self, max_length: int = 120) -> str:
        context = random.choice(self.starts)
        result = []
        for _ in range(max_length):
            nxt = self._sample(context)
            if nxt == "$":
                break
            result.append(nxt)
            context = (context + nxt)[-self.order :]
        return "".join(result)


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------
@dataclass
class BenchmarkResult:
    n_generated: int
    n_valid: int
    n_unique: int
    n_novel: int
    n_filtered: int
    validity: float
    uniqueness: float
    novelty: float
    filters: float
    diversity: float
    snn: float
    mean_mw: float
    mean_logp: float

    def print_report(self):
        print("\n" + "=" * 60)
        print("MOSES-STYLE BENCHMARK RESULTS")
        print("=" * 60)
        print(f"  Generated           : {self.n_generated}")
        print(f"  Valid               : {self.n_valid}")
        print(f"  Unique (of valid)   : {self.n_unique}")
        print(f"  Novel (of valid)    : {self.n_novel}")
        print(f"  Filtered (of valid) : {self.n_filtered}")
        print("-" * 60)
        print(f"  Validity   : {self.validity:.2f}%")
        print(f"  Uniqueness : {self.uniqueness:.2f}%")
        print(f"  Novelty    : {self.novelty:.2f}%")
        print(f"  Filters    : {self.filters:.2f}%")
        print(f"  Diversity  : {self.diversity:.4f}")
        print(f"  SNN        : {self.snn:.4f}")
        print(f"  Mean MW    : {self.mean_mw:.2f}")
        print(f"  Mean logP  : {self.mean_logp:.2f}")
        print("=" * 60)
        print("\nLeaderboard comparison (published baselines):")
        print("  JT-VAE     : Validity 100.0%, Novelty 99.9%, FCD 81.8")
        print("  MOLER      : Validity 100.0%, FCD 85.2")
        print("  NSGGM      : Validity 100.0%, Novelty 94.4%, FCD 82.3")
        print("  LSTM       : Validity 95.9%, Novelty 91.2%, FCD 91.3 (GuacaMol)")
        print("  Our Markov : " + f"Validity {self.validity:.1f}%, "
              f"Novelty {self.novelty:.1f}%")
        print("=" * 60)


def mol_from_smiles(smi: str):
    try:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            return None
        # Sanitize to catch edge cases
        Chem.SanitizeMol(mol)
        return mol
    except Exception:
        return None


def passes_filters(mol) -> bool:
    """Basic drug-likeness filters (simplified MOSES filters)."""
    if mol is None:
        return False
    mw = Descriptors.MolWt(mol)
    logp = Descriptors.MolLogP(mol)
    hbd = Descriptors.NumHDonors(mol)
    hba = Descriptors.NumHAcceptors(mol)
    tpsa = Descriptors.TPSA(mol)
    return (
        0 < mw <= 500
        and -10 <= logp <= 10
        and hbd <= 5
        and hba <= 10
        and tpsa < 150
    )


def compute_diversity(mols: List, sample_size: int = 500) -> float:
    """Average pairwise Tanimoto distance using Morgan fingerprints."""
    if len(mols) < 2:
        return 0.0
    sampled = random.sample(mols, min(sample_size, len(mols)))
    fps = [AllChem.GetMorganFingerprintAsBitVect(m, 2, nBits=2048) for m in sampled]
    distances = []
    for i in range(len(fps)):
        for j in range(i + 1, len(fps)):
            sim = DataStructs.TanimotoSimilarity(fps[i], fps[j])
            distances.append(1.0 - sim)
    return float(np.mean(distances)) if distances else 0.0


def compute_snn(generated_fps, train_fps, sample_size: int = 500) -> float:
    """Mean similarity to nearest neighbor in training set."""
    if not generated_fps or not train_fps:
        return 0.0
    sampled = random.sample(generated_fps, min(sample_size, len(generated_fps)))
    sims = []
    for g_fp in sampled:
        max_sim = max(DataStructs.TanimotoSimilarity(g_fp, t_fp) for t_fp in train_fps)
        sims.append(max_sim)
    return float(np.mean(sims))


def run_benchmark(
    train_path: str = TRAIN_PATH,
    n_train: int = N_TRAIN_FOR_MODEL,
    n_generate: int = N_GENERATE,
    order: int = MARKOV_ORDER,
) -> BenchmarkResult:
    # 1. Load training data
    print(f"Loading training data from {train_path} ...")
    train_smiles: List[str] = []
    with open(train_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            train_smiles.append(row["SMILES"].strip())
    print(f"  Total training molecules: {len(train_smiles)}")

    # Subsample for fast Markov training
    model_smiles = random.sample(train_smiles, min(n_train, len(train_smiles)))
    train_set = set(train_smiles)
    print(f"  Using {len(model_smiles)} for model training")

    # 2. Train Markov model
    print(f"\nTraining order-{order} Markov model ...")
    model = MarkovModel(order=order)
    model.fit(model_smiles)
    print(f"  Context states: {len(model.transitions)}")

    # 3. Generate molecules
    print(f"\nGenerating {n_generate} molecules ...")
    generated_smiles: List[str] = []
    while len(generated_smiles) < n_generate:
        smi = model.generate()
        if smi:
            generated_smiles.append(smi)
        if len(generated_smiles) % 1000 == 0 and len(generated_smiles) > 0:
            print(f"  ... {len(generated_smiles)} generated")

    # 4. Validate with RDKit
    print("\nValidating with RDKit ...")
    valid_mols = []
    valid_smiles_set: Set[str] = set()
    for smi in generated_smiles:
        mol = mol_from_smiles(smi)
        if mol is not None:
            # Canonicalize for uniqueness
            canon = Chem.MolToSmiles(mol, canonical=True)
            if canon not in valid_smiles_set:
                valid_mols.append(mol)
                valid_smiles_set.add(canon)

    n_valid = len(valid_smiles_set)
    n_unique = len(valid_smiles_set)  # already deduplicated
    n_novel = len(valid_smiles_set - train_set)
    n_filtered = sum(1 for m in valid_mols if passes_filters(m))

    validity = 100.0 * n_valid / n_generate
    uniqueness = 100.0 * n_unique / max(1, n_valid)
    novelty = 100.0 * n_novel / max(1, n_valid)
    filters = 100.0 * n_filtered / max(1, n_valid)

    # 5. Compute diversity and SNN
    print("Computing fingerprints ...")
    valid_fps = [
        AllChem.GetMorganFingerprintAsBitVect(m, 2, nBits=2048)
        for m in valid_mols
    ]
    train_mols = [mol_from_smiles(s) for s in random.sample(train_smiles, 5000)]
    train_fps = [
        AllChem.GetMorganFingerprintAsBitVect(m, 2, nBits=2048)
        for m in train_mols
        if m is not None
    ]

    print("Computing diversity ...")
    diversity = compute_diversity(valid_mols, sample_size=500)

    print("Computing SNN ...")
    snn = compute_snn(valid_fps, train_fps, sample_size=500)

    mean_mw = float(np.mean([Descriptors.MolWt(m) for m in valid_mols])) if valid_mols else 0.0
    mean_logp = float(np.mean([Descriptors.MolLogP(m) for m in valid_mols])) if valid_mols else 0.0

    return BenchmarkResult(
        n_generated=n_generate,
        n_valid=n_valid,
        n_unique=n_unique,
        n_novel=n_novel,
        n_filtered=n_filtered,
        validity=validity,
        uniqueness=uniqueness,
        novelty=novelty,
        filters=filters,
        diversity=diversity,
        snn=snn,
        mean_mw=mean_mw,
        mean_logp=mean_logp,
    )


if __name__ == "__main__":
    if not os.path.exists(TRAIN_PATH):
        print(f"ERROR: Training data not found at {TRAIN_PATH}")
        print("Download it first:")
        print("  https://media.githubusercontent.com/media/molecularsets/moses/master/data/train.csv")
        sys.exit(1)

    result = run_benchmark()
    result.print_report()
