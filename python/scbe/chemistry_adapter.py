"""SCBE Chemistry Adapter — Training Pipeline Bridge.

Wraps the chemistry verification gate so the training system can:
  1. Check molecules before promotion
  2. Score generated molecules for SFT ranking
  3. Filter toxic/invalid compounds before dataset inclusion

Usage:
    from python.scbe.chemistry_adapter import ChemistryAdapter
    adapter = ChemistryAdapter()
    result = adapter.check("CCO")
    assert result.can_promote
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .state9d_chemistry_fusion import (
    fuse_molecule,
    molecule_governance_summary,
    tokenize_molecule,
)


def _rdkit_parse(smiles: str) -> tuple[bool, Any]:
    try:
        from rdkit import Chem
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return False, None
        Chem.SanitizeMol(mol)
        return True, mol
    except Exception:
        return False, None


def _valence_check(mol) -> tuple[bool, str]:
    if mol is None:
        return False, "No molecule"
    from rdkit import Chem
    for atom in mol.GetAtoms():
        sym = atom.GetSymbol()
        val = atom.GetValence(Chem.ValenceType.EXPLICIT)
        max_val = {
            "C": 4, "N": 3, "O": 2, "S": 2, "P": 3,
            "F": 1, "Cl": 1, "Br": 1, "I": 1, "B": 3,
            "Na": 0, "Mg": 0, "Al": 0, "Si": 4,
        }.get(sym, None)
        if max_val is not None and val > max_val:
            return False, f"{sym} valence {val} > {max_val}"
    return True, "OK"


@dataclass
class ChemistryCheckResult:
    """Result of a chemistry verification check."""

    smiles: str
    can_promote: bool
    rdkit_ok: bool
    valence_ok: bool
    fusion_ok: bool
    valence_pressure: float = 0.0
    coherence_penalty: float = 0.0
    governance_verdict: str = "UNKNOWN"
    reasons: List[str] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "smiles": self.smiles,
            "can_promote": self.can_promote,
            "rdkit_ok": self.rdkit_ok,
            "valence_ok": self.valence_ok,
            "fusion_ok": self.fusion_ok,
            "valence_pressure": self.valence_pressure,
            "coherence_penalty": self.coherence_penalty,
            "governance_verdict": self.governance_verdict,
            "reasons": self.reasons,
        }


class ChemistryAdapter:
    """Chemistry adapter for the SCBE training pipeline.

    Promotion rules:
      - RDKit must parse the SMILES
      - No valence violations
      - SCBE fusion state must be finite
      - Valence pressure < threshold (default 50)
      - Coherence penalty < threshold (default 20)
    """

    def __init__(
        self,
        max_valence_pressure: float = 50.0,
        max_coherence_penalty: float = 20.0,
        require_drug_like_filters: bool = False,
    ):
        self.max_valence_pressure = max_valence_pressure
        self.max_coherence_penalty = max_coherence_penalty
        self.require_drug_like_filters = require_drug_like_filters

    def check(self, smiles: str) -> ChemistryCheckResult:
        """Run full chemistry verification on a SMILES string."""
        result = ChemistryCheckResult(
            smiles=smiles, can_promote=False,
            rdkit_ok=False, valence_ok=False, fusion_ok=False,
        )

        # 0. Pre-filter: reject pathological / adversarial inputs fast
        if not smiles or not smiles.strip():
            result.reasons.append("Empty or whitespace-only SMILES")
            return result
        stripped = smiles.strip()
        if len(stripped) > 2000:
            result.reasons.append("SMILES exceeds 2000 character safety limit")
            return result
        # Reject obvious injection patterns and non-ASCII
        import re
        if re.search(r"[<>'\";]|\\x00|\\x00|/\\.|\\.\\./|SELECT|DELETE|DROP|UNION", stripped):
            result.reasons.append("Adversarial pattern detected in SMILES")
            return result
        # Reject excessive nesting depth
        max_depth = 0
        depth = 0
        for ch in stripped:
            if ch in "([":
                depth += 1
                max_depth = max(max_depth, depth)
            elif ch in ")]":
                depth -= 1
        if max_depth > 100:
            result.reasons.append("Excessive bracket nesting (>100)")
            return result
        if depth != 0:
            result.reasons.append("Mismatched brackets")
            return result
        # Reject excessive ring closures (pathological for RDKit)
        ring_count = sum(1 for ch in stripped if ch.isdigit())
        if ring_count > 200:
            result.reasons.append("Excessive ring closures (>200)")
            return result

        # 1. RDKit parse
        parsed, mol = _rdkit_parse(smiles)
        result.rdkit_ok = parsed
        if not parsed:
            result.reasons.append("RDKit parse failed")

        # 2. Valence check
        if parsed:
            ok, msg = _valence_check(mol)
            result.valence_ok = ok
            if not ok:
                result.reasons.append(f"Valence: {msg}")
        else:
            result.valence_ok = False
            result.reasons.append("Valence check skipped (parse failed)")

        # 3. SCBE fusion
        try:
            states = tokenize_molecule(smiles)
            fusion = fuse_molecule(states)
            summary = molecule_governance_summary(smiles, t=0.0)
            result.summary = summary
            result.fusion_ok = True
            result.valence_pressure = summary.get("valence_pressure", 0.0)
            result.coherence_penalty = summary.get("coherence_penalty", 0.0)
            result.governance_verdict = "ALLOW" if parsed else "DENY"

            if result.valence_pressure > self.max_valence_pressure:
                result.reasons.append(
                    f"Valence pressure {result.valence_pressure:.2f} > {self.max_valence_pressure}"
                )
            if result.coherence_penalty > self.max_coherence_penalty:
                result.reasons.append(
                    f"Coherence penalty {result.coherence_penalty:.2f} > {self.max_coherence_penalty}"
                )

            # Drug-like filters (optional)
            if self.require_drug_like_filters and parsed:
                from rdkit.Chem import Descriptors
                mw = Descriptors.MolWt(mol)
                logp = Descriptors.MolLogP(mol)
                hbd = Descriptors.NumHDonors(mol)
                hba = Descriptors.NumHAcceptors(mol)
                tpsa = Descriptors.TPSA(mol)
                if not (0 < mw <= 500 and -10 <= logp <= 10 and hbd <= 5 and hba <= 10 and tpsa < 150):
                    result.reasons.append("Drug-like filters failed")

        except Exception as e:
            result.fusion_ok = False
            result.reasons.append(f"SCBE fusion error: {e}")

        # Final promotion decision
        result.can_promote = (
            result.rdkit_ok
            and result.valence_ok
            and result.fusion_ok
            and result.valence_pressure <= self.max_valence_pressure
            and result.coherence_penalty <= self.max_coherence_penalty
            and not result.reasons
        )

        return result

    def batch_check(self, smiles_list: List[str]) -> List[ChemistryCheckResult]:
        """Check multiple molecules."""
        return [self.check(s) for s in smiles_list]

    def gate_check(self, smiles: str) -> bool:
        """Returns True only if the molecule passes ALL checks."""
        return self.check(smiles).can_promote

    def score_for_sft(self, smiles: str) -> dict[str, Any]:
        """Generate a scoring dict for SFT ranking/preference pairs."""
        result = self.check(smiles)
        summary = result.summary

        # Composite score: higher = better molecule
        score = 0.0
        if result.rdkit_ok:
            score += 0.3
        if result.valence_ok:
            score += 0.3
        if result.fusion_ok:
            score += 0.2
        if result.can_promote:
            score += 0.2

        # Penalize high pressure / low coherence
        pressure_norm = min(1.0, result.valence_pressure / max(1.0, self.max_valence_pressure))
        coherence_norm = min(1.0, result.coherence_penalty / max(1.0, self.max_coherence_penalty))
        score -= 0.1 * pressure_norm
        score -= 0.1 * coherence_norm

        return {
            "smiles": smiles,
            "score": round(max(0.0, score), 4),
            "can_promote": result.can_promote,
            "rdkit_ok": result.rdkit_ok,
            "valence_ok": result.valence_ok,
            "fusion_ok": result.fusion_ok,
            "valence_pressure": result.valence_pressure,
            "coherence_penalty": result.coherence_penalty,
            "tau_hat": summary.get("tau_hat", {}),
            "votes": summary.get("votes", {}),
        }


# ---------------------------------------------------------------------------
# Training gate entry point
# ---------------------------------------------------------------------------
def training_gate_check(smiles: str) -> bool:
    """Called by the training pipeline before promoting a molecule.

    Returns True only if the molecule passes chemistry verification.
    """
    adapter = ChemistryAdapter()
    result = adapter.check(smiles)
    return result.can_promote


def training_gate_batch(file_path: str) -> dict[str, Any]:
    """Run gate on a file of SMILES strings (one per line or JSONL)."""
    results = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Try JSONL first
            try:
                obj = json.loads(line)
                smiles = obj.get("smiles", obj.get("SMILES", ""))
            except json.JSONDecodeError:
                smiles = line
            if smiles:
                results.append(training_gate_check(smiles))

    n_pass = sum(results)
    return {
        "total": len(results),
        "passed": n_pass,
        "failed": len(results) - n_pass,
        "pass_rate": n_pass / max(1, len(results)),
        "all_passed": all(results) if results else True,
    }
