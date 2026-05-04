"""Build chemistry_manual_verification_v1 dataset.

Creates a rigorous, college-level chemistry obstacle course where each row
forces the system to walk the full arithmetic path:

  SMILES → atoms → bonds → valence count → electronegativity differences
  → functional group → RDKit validity → SCBE token state
  → fusion state → governance verdict

This is "running the numbers to the 10th decimal" — the model must learn
process, not just pattern-match answers.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional


@dataclass
class ChemistryVerificationRow:
    smiles: str
    name: str
    expected_valid: bool
    expected_family: str
    expected_elements: List[str]
    expected_governance: str  # ALLOW / HOLD / DENY

    # Manual chemistry arithmetic (the "show your work" part)
    manual_valence_check: str
    manual_electronegativity: str
    manual_functional_group: str
    manual_bond_analysis: str

    # SCBE fusion expectations
    expected_tau_hat_signs: Dict[str, int]  # KO, AV, RU, CA, UM, DR ∈ {-1,0,1}
    expected_coherence_range: tuple[float, float]  # (min, max)
    expected_valence_pressure_range: tuple[float, float]

    # Required verification pipeline steps
    required_checks: List[str]

    # Difficulty level for curriculum scheduling
    difficulty: int  # 1-5

    # Metadata
    source: str  # "basic", "functional_group", "drug", "stress_test", "boundary"
    tags: List[str]


DATASET_PATH = "training-data/chemistry_manual_verification_v1.jsonl"
MANIFEST_PATH = "training-data/chemistry_manual_verification_v1_manifest.json"

# ---------------------------------------------------------------------------
# Dataset: college-level chemistry obstacle course
# ---------------------------------------------------------------------------

ROWS: List[ChemistryVerificationRow] = [
    # ================================================================
    # 1. VALID SIMPLE MOLECULES (difficulty 1)
    # ================================================================
    ChemistryVerificationRow(
        smiles="O",
        name="water",
        expected_valid=True,
        expected_family="oxide",
        expected_elements=["O"],
        expected_governance="ALLOW",
        manual_valence_check="O has valence 2. Forms single bonds to 2 H atoms (implicit). 2 - 2 = 0 remaining. VALID.",
        manual_electronegativity="O (3.44) >> H (2.20). Difference = 1.24. Polar covalent. Net dipole moment.",
        manual_functional_group="Hydroxyl precursor (water). Not a functional group itself but solvent for hydrolysis.",
        manual_bond_analysis="Two O-H single bonds. Bond angle ~104.5° (sp3 hybridization, 2 lone pairs).",
        expected_tau_hat_signs={"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0},
        expected_coherence_range=(0.0, 2.0),
        expected_valence_pressure_range=(0.0, 5.0),
        required_checks=["rdkit_parse", "valence_satisfied", "fusion_state_finite"],
        difficulty=1,
        source="basic",
        tags=["simple", "inorganic", "polar"],
    ),
    ChemistryVerificationRow(
        smiles="C",
        name="methane",
        expected_valid=True,
        expected_family="alkane",
        expected_elements=["C"],
        expected_governance="ALLOW",
        manual_valence_check="C has valence 4. Forms 4 single bonds to H atoms (implicit). 4 - 4 = 0 remaining. VALID.",
        manual_electronegativity="C (2.55) ≈ H (2.20). Difference = 0.35. Nonpolar covalent.",
        manual_functional_group="Alkane (no functional group). Saturated hydrocarbon.",
        manual_bond_analysis="Four C-H single bonds. Tetrahedral geometry (109.5°). sp3 hybridization.",
        expected_tau_hat_signs={"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0},
        expected_coherence_range=(0.0, 2.0),
        expected_valence_pressure_range=(0.0, 5.0),
        required_checks=["rdkit_parse", "valence_satisfied"],
        difficulty=1,
        source="basic",
        tags=["simple", "alkane", "nonpolar"],
    ),
    ChemistryVerificationRow(
        smiles="CCO",
        name="ethanol",
        expected_valid=True,
        expected_family="alcohol",
        expected_elements=["C", "C", "O"],
        expected_governance="ALLOW",
        manual_valence_check="C1: valence 4, bonds to C2 + 3H = 4. OK. C2: valence 4, bonds to C1 + O + 2H = 4. OK. O: valence 2, bonds to C2 + H = 2. OK.",
        manual_electronegativity="O (3.44) > C (2.55) > H (2.20). O-C bond: ΔEN = 0.89 (polar). O-H bond: ΔEN = 1.24 (polar). Net dipole.",
        manual_functional_group="Primary alcohol (-OH on terminal carbon). Can oxidize to aldehyde then acid.",
        manual_bond_analysis="C-C single, C-O single, O-H single, C-H singles. sp3 throughout.",
        expected_tau_hat_signs={"KO": 1, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0},
        expected_coherence_range=(0.5, 5.0),
        expected_valence_pressure_range=(0.0, 10.0),
        required_checks=["rdkit_parse", "valence_satisfied", "functional_group_detected"],
        difficulty=1,
        source="basic",
        tags=["alcohol", "organic", "polar"],
    ),
    ChemistryVerificationRow(
        smiles="O=C=O",
        name="carbon_dioxide",
        expected_valid=True,
        expected_family="acid_anhydride",
        expected_elements=["C", "O", "O"],
        expected_governance="ALLOW",
        manual_valence_check="C: valence 4. Two double bonds to O = 4. 4 - 4 = 0. OK. Each O: valence 2. One double bond to C = 2. OK.",
        manual_electronegativity="O (3.44) >> C (2.55). ΔEN = 0.89 per bond. Linear molecule, dipoles cancel. NONPOLAR overall.",
        manual_functional_group="Carbon dioxide (not organic functional group but acidic oxide). Reacts with water to form carbonic acid.",
        manual_bond_analysis="Two C=O double bonds. Linear geometry (180°). sp hybridization on carbon.",
        expected_tau_hat_signs={"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0},
        expected_coherence_range=(0.0, 2.0),
        expected_valence_pressure_range=(0.0, 5.0),
        required_checks=["rdkit_parse", "valence_satisfied"],
        difficulty=1,
        source="basic",
        tags=["inorganic", "linear", "nonpolar"],
    ),
    ChemistryVerificationRow(
        smiles="N",
        name="ammonia",
        expected_valid=True,
        expected_family="amine_precursor",
        expected_elements=["N"],
        expected_governance="ALLOW",
        manual_valence_check="N has valence 3. Forms 3 single bonds to H (implicit). 3 - 3 = 0. OK.",
        manual_electronegativity="N (3.04) > H (2.20). ΔEN = 0.84. Polar covalent. Trigonal pyramidal (107°). Lone pair on N.",
        manual_functional_group="Amine precursor (NH3). Weak base (pKb ~4.75). Can donate lone pair.",
        manual_bond_analysis="Three N-H single bonds. sp3 hybridization with one lone pair.",
        expected_tau_hat_signs={"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0},
        expected_coherence_range=(0.0, 2.0),
        expected_valence_pressure_range=(0.0, 5.0),
        required_checks=["rdkit_parse", "valence_satisfied"],
        difficulty=1,
        source="basic",
        tags=["simple", "base", "polar"],
    ),

    # ================================================================
    # 2. FUNCTIONAL GROUPS (difficulty 2)
    # ================================================================
    ChemistryVerificationRow(
        smiles="CC(=O)O",
        name="acetic_acid",
        expected_valid=True,
        expected_family="carboxylic_acid",
        expected_elements=["C", "C", "O", "O"],
        expected_governance="ALLOW",
        manual_valence_check="C1 (methyl): 4 valence, 3H + C2 = 4. OK. C2 (carboxyl): 4 valence, =O + -O + C1 = 4. OK. O (hydroxyl): 2 valence, C2 + H = 2. OK. O (carbonyl): 2 valence, C2 = 2. OK.",
        manual_electronegativity="O (3.44) > C (2.55). Carbonyl C is electrophilic. O-H bond acidic (pKa ~4.76).",
        manual_functional_group="Carboxylic acid (-COOH). Can donate proton (acid) or form ester (condensation).",
        manual_bond_analysis="C-C single, C=O double, C-O single, O-H single. Carbonyl C is sp2 (trigonal planar 120°).",
        expected_tau_hat_signs={"KO": 1, "AV": 0, "RU": 0, "CA": 1, "UM": 0, "DR": 0},
        expected_coherence_range=(1.0, 8.0),
        expected_valence_pressure_range=(2.0, 15.0),
        required_checks=["rdkit_parse", "valence_satisfied", "functional_group_detected", "acidic_proton"],
        difficulty=2,
        source="functional_group",
        tags=["acid", "organic", "polar"],
    ),
    ChemistryVerificationRow(
        smiles="CC(=O)CC",
        name="butanone",
        expected_valid=True,
        expected_family="ketone",
        expected_elements=["C", "C", "C", "O"],
        expected_governance="ALLOW",
        manual_valence_check="Carbonyl C: valence 4, double bond O + single C + single C = 4. OK. O: valence 2, double bond C = 2. OK. All other carbons: 4 single bonds. OK.",
        manual_electronegativity="O (3.44) > C (2.55). Carbonyl carbon electrophilic. Can undergo nucleophilic addition.",
        manual_functional_group="Ketone (R-CO-R'). Cannot oxidize further (no alpha-H on carbonyl C for iodoform).",
        manual_bond_analysis="C=O double bond. Carbonyl C is sp2. Surrounding carbons sp3.",
        expected_tau_hat_signs={"KO": 1, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0},
        expected_coherence_range=(1.0, 8.0),
        expected_valence_pressure_range=(2.0, 15.0),
        required_checks=["rdkit_parse", "valence_satisfied", "functional_group_detected"],
        difficulty=2,
        source="functional_group",
        tags=["ketone", "organic"],
    ),
    ChemistryVerificationRow(
        smiles="CC(=O)OC",
        name="methyl_acetate",
        expected_valid=True,
        expected_family="ester",
        expected_elements=["C", "C", "O", "O"],
        expected_governance="ALLOW",
        manual_valence_check="Carbonyl C: 4 valence, =O + -O + -C = 4. OK. Ester O: 2 valence, C=O + CH3 = 2. OK. All other atoms satisfied.",
        manual_electronegativity="Two oxygens with different environments. Carbonyl O electronegative; ester O less so. Resonance stabilization.",
        manual_functional_group="Ester (R-COOR'). Product of Fischer esterification. Can hydrolyze back to acid + alcohol.",
        manual_bond_analysis="C=O double, C-O single (to alkoxy), O-C single (alkyl). Carbonyl C sp2. Resonance between two oxygens.",
        expected_tau_hat_signs={"KO": 1, "AV": 0, "RU": 0, "CA": 1, "UM": 0, "DR": 0},
        expected_coherence_range=(1.0, 8.0),
        expected_valence_pressure_range=(2.0, 15.0),
        required_checks=["rdkit_parse", "valence_satisfied", "functional_group_detected"],
        difficulty=2,
        source="functional_group",
        tags=["ester", "organic"],
    ),
    ChemistryVerificationRow(
        smiles="c1ccccc1",
        name="benzene",
        expected_valid=True,
        expected_family="aromatic_hydrocarbon",
        expected_elements=["C", "C", "C", "C", "C", "C"],
        expected_governance="ALLOW",
        manual_valence_check="Each C: valence 4. In benzene, each C bonded to 2 neighboring C + 1 H (implicit) = 3 sigma bonds. The 4th valence is delocalized pi bond. Aromatic sextet satisfies Hückel's rule (4n+2, n=1).",
        manual_electronegativity="All C (2.55). Nonpolar. Delocalized electron density above and below ring plane.",
        manual_functional_group="Aromatic ring (arene). Undergoes electrophilic aromatic substitution (EAS), not addition. Resonance energy ~36 kcal/mol.",
        manual_bond_analysis="6 C-C bonds with bond order 1.5 (resonance hybrid). Planar hexagon (120°). sp2 hybridization.",
        expected_tau_hat_signs={"KO": 0, "AV": 0, "RU": 1, "CA": 0, "UM": 0, "DR": 0},
        expected_coherence_range=(0.5, 6.0),
        expected_valence_pressure_range=(0.0, 12.0),
        required_checks=["rdkit_parse", "valence_satisfied", "aromaticity_verified", "huckel_rule"],
        difficulty=2,
        source="functional_group",
        tags=["aromatic", "arene", "organic"],
    ),
    ChemistryVerificationRow(
        smiles="CCN",
        name="ethylamine",
        expected_valid=True,
        expected_family="amine",
        expected_elements=["C", "C", "N"],
        expected_governance="ALLOW",
        manual_valence_check="N: valence 3, bonded to C2 + 2H (implicit) = 3. OK. C1: 4 valence, 3H + C2 = 4. OK. C2: 4 valence, C1 + N + 2H = 4. OK.",
        manual_electronegativity="N (3.04) > C (2.55) > H (2.20). Lone pair on N makes it nucleophilic and basic (pKb ~3.2).",
        manual_functional_group="Primary amine (-NH2). Can act as base, nucleophile, or form amides with acids.",
        manual_bond_analysis="C-C single, C-N single, N-H singles (implicit). sp3 throughout.",
        expected_tau_hat_signs={"KO": 1, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0},
        expected_coherence_range=(0.5, 5.0),
        expected_valence_pressure_range=(0.0, 10.0),
        required_checks=["rdkit_parse", "valence_satisfied", "functional_group_detected"],
        difficulty=2,
        source="functional_group",
        tags=["amine", "base", "organic"],
    ),

    # ================================================================
    # 3. KNOWN DRUGS (difficulty 3)
    # ================================================================
    ChemistryVerificationRow(
        smiles="CC(=O)Oc1ccccc1C(=O)O",
        name="aspirin",
        expected_valid=True,
        expected_family="salicylate_ester",
        expected_elements=["C", "C", "O", "O", "C", "C", "C", "C", "C", "C"],
        expected_governance="ALLOW",
        manual_valence_check="Carboxyl C: 4 valence, =O + -O + ring-C = 4. OK. Ester carbonyl C: 4 valence, =O + -O + CH3 = 4. OK. Aromatic Cs: each 3 sigma bonds + delocalized pi. OK.",
        manual_electronegativity="Multiple O atoms create strong polarity. Carboxylic acid proton acidic (pKa ~3.5). Ester group hydrolyzes in basic conditions.",
        manual_functional_group="Acetylsalicylic acid. Carboxylic acid + ester + aromatic ring. COX inhibitor (NSAID).",
        manual_bond_analysis="Mixed: C-C singles, C=O doubles, C-O singles, aromatic bonds (1.5 order). Planar aromatic portion.",
        expected_tau_hat_signs={"KO": 1, "AV": 1, "RU": 1, "CA": 1, "UM": 0, "DR": 0},
        expected_coherence_range=(3.0, 15.0),
        expected_valence_pressure_range=(5.0, 25.0),
        required_checks=["rdkit_parse", "valence_satisfied", "functional_group_detected", "drug_like_filters"],
        difficulty=3,
        source="drug",
        tags=["nsaid", "ester", "acid", "aromatic"],
    ),
    ChemistryVerificationRow(
        smiles="CN1C=NC2=C1C(=O)N(C(=O)N2C)C",
        name="caffeine",
        expected_valid=True,
        expected_family="alkaloid_purine",
        expected_elements=["C", "N", "C", "N", "C", "C", "O", "N", "C", "O", "N", "C", "C"],
        expected_governance="ALLOW",
        manual_valence_check="Purine fused ring system. All N atoms: valence 3 satisfied. Carbonyl Cs: 4 valence with =O. Methyl groups: 4 valence. Aromatic sextet in imidazole + pyrimidine rings.",
        manual_electronegativity="Multiple N atoms create basic sites. N-9 (imidazole) most basic. Carbonyls polar. Overall moderately polar.",
        manual_functional_group="Methylxanthine. Adenosine receptor antagonist. Contains two amide groups + imidazole ring.",
        manual_bond_analysis="Fused bicyclic aromatic system. C=O double bonds, N-CH3 single bonds, C=N double bonds within aromatic framework.",
        expected_tau_hat_signs={"KO": 1, "AV": 1, "RU": 1, "CA": 1, "UM": 0, "DR": 0},
        expected_coherence_range=(5.0, 20.0),
        expected_valence_pressure_range=(8.0, 30.0),
        required_checks=["rdkit_parse", "valence_satisfied", "aromaticity_verified", "drug_like_filters"],
        difficulty=3,
        source="drug",
        tags=["alkaloid", "purine", "cns_stimulant"],
    ),
    ChemistryVerificationRow(
        smiles="CC(C)Cc1ccc(C(C)C(=O)O)cc1",
        name="ibuprofen",
        expected_valid=True,
        expected_family="arylpropionic_acid",
        expected_elements=["C", "C", "C", "C", "C", "C", "C", "C", "C", "C", "C", "C", "O", "O"],
        expected_governance="ALLOW",
        manual_valence_check="Isobutyl group: all C valence 4. Aromatic ring: 6 Cs with delocalized pi. Propionic acid side chain: carboxyl C = 4, alpha-C = 4. All satisfied.",
        manual_electronegativity="Carboxylic acid O (3.44) creates polarity. Aromatic ring nonpolar. Lipophilic isobutyl group dominates. LogP ~3.5-4.",
        manual_functional_group="2-arylpropionic acid (NSAID). Carboxylic acid on chiral center. COX inhibitor.",
        manual_bond_analysis="C-C singles, aromatic bonds, C=O double, C-O single, O-H single. Mixed sp2/sp3.",
        expected_tau_hat_signs={"KO": 1, "AV": 1, "RU": 1, "CA": 1, "UM": 0, "DR": 0},
        expected_coherence_range=(5.0, 20.0),
        expected_valence_pressure_range=(8.0, 30.0),
        required_checks=["rdkit_parse", "valence_satisfied", "functional_group_detected", "drug_like_filters"],
        difficulty=3,
        source="drug",
        tags=["nsaid", "acid", "aromatic"],
    ),
    ChemistryVerificationRow(
        smiles="CC(=O)Nc1ccc(O)cc1",
        name="acetaminophen_paracetamol",
        expected_valid=True,
        expected_family="anilide",
        expected_elements=["C", "C", "O", "N", "C", "C", "C", "C", "O", "C"],
        expected_governance="ALLOW",
        manual_valence_check="Amide C: valence 4, =O + N + CH3 = 4. OK. N: valence 3, C=O + ring-C + H = 3. OK. Phenol O: valence 2, ring-C + H = 2. OK. Aromatic Cs: 3 sigma + delocalized pi.",
        manual_electronegativity="Amide N less basic than amine (pKb ~13). Phenol O weakly acidic (pKa ~9.5). Moderate polarity.",
        manual_functional_group="Acetanilide derivative. Amide + phenol. Analgesic/antipyretic. Conjugation between amide and aromatic ring.",
        manual_bond_analysis="Amide C=O, C-N single, N-C(aryl) single, phenol C-O single, O-H single. Aromatic ring.",
        expected_tau_hat_signs={"KO": 1, "AV": 1, "RU": 1, "CA": 1, "UM": 0, "DR": 0},
        expected_coherence_range=(3.0, 15.0),
        expected_valence_pressure_range=(5.0, 25.0),
        required_checks=["rdkit_parse", "valence_satisfied", "functional_group_detected", "drug_like_filters"],
        difficulty=3,
        source="drug",
        tags=["analgesic", "amide", "phenol", "aromatic"],
    ),

    # ================================================================
    # 4. INVALID / STRESS TESTS (difficulty varies)
    # ================================================================
    ChemistryVerificationRow(
        smiles="C(C)(C)(C)(C)(C)",
        name="pentavalent_carbon",
        expected_valid=False,
        expected_family="invalid",
        expected_elements=["C"],
        expected_governance="DENY",
        manual_valence_check="Central C bonded to 5 other Cs. Carbon valence = 4. 5 > 4. IMPOSSIBLE. Valence violation.",
        manual_electronegativity="N/A — structure is chemically impossible.",
        manual_functional_group="None. Carbon cannot form 5 single bonds.",
        manual_bond_analysis="N/A. Violates octet rule.",
        expected_tau_hat_signs={"KO": -1, "AV": -1, "RU": -1, "CA": -1, "UM": -1, "DR": -1},
        expected_coherence_range=(0.0, 0.0),
        expected_valence_pressure_range=(100.0, 100.0),
        required_checks=["rdkit_parse_fails", "valence_violation_detected"],
        difficulty=2,
        source="stress_test",
        tags=["invalid", "valence_violation", "octet"],
    ),
    ChemistryVerificationRow(
        smiles="NotASmiles",
        name="nonsense_string",
        expected_valid=False,
        expected_family="invalid",
        expected_elements=[],
        expected_governance="DENY",
        manual_valence_check="N/A. String contains invalid characters and no recognizable chemical structure.",
        manual_electronegativity="N/A.",
        manual_functional_group="None.",
        manual_bond_analysis="N/A.",
        expected_tau_hat_signs={"KO": -1, "AV": -1, "RU": -1, "CA": -1, "UM": -1, "DR": -1},
        expected_coherence_range=(0.0, 0.0),
        expected_valence_pressure_range=(100.0, 100.0),
        required_checks=["rdkit_parse_fails", "tokenization_fails"],
        difficulty=1,
        source="stress_test",
        tags=["invalid", "nonsense"],
    ),
    ChemistryVerificationRow(
        smiles="C1CC1",
        name="cyclopropane",
        expected_valid=True,
        expected_family="cycloalkane",
        expected_elements=["C", "C", "C"],
        expected_governance="ALLOW",
        manual_valence_check="Each C: valence 4. 2 C-C bonds + 2 H (implicit) = 4. OK. Small ring is strained but valid.",
        manual_electronegativity="All C (2.55). Nonpolar.",
        manual_functional_group="Cycloalkane. Ring strain ~27.5 kcal/mol (Baeyer strain). Undergoes addition reactions unlike larger cycloalkanes.",
        manual_bond_analysis="3 C-C single bonds. Equilateral triangle (60°). Severe angle strain (109.5° → 60°).",
        expected_tau_hat_signs={"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0},
        expected_coherence_range=(0.5, 4.0),
        expected_valence_pressure_range=(2.0, 10.0),
        required_checks=["rdkit_parse", "valence_satisfied", "ring_strain_noted"],
        difficulty=2,
        source="boundary",
        tags=["cycloalkane", "ring_strain"],
    ),
    ChemistryVerificationRow(
        smiles="C1=CC=CC=C1",
        name="benzene_aliphatic_notation",
        expected_valid=True,
        expected_family="aromatic_hydrocarbon",
        expected_elements=["C", "C", "C", "C", "C", "C"],
        expected_governance="ALLOW",
        manual_valence_check="Each C: 3 sigma bonds (2 C-C + 1 H implicit) + 1 pi bond = 4. Aromatic sextet. Kekulé structure. OK.",
        manual_electronegativity="All C (2.55). Nonpolar.",
        manual_functional_group="Aromatic ring (arene). Same as c1ccccc1 but written with explicit double bonds (Kekulé form).",
        manual_bond_analysis="Alternating C=C and C-C. Resonance hybrid. Planar. sp2.",
        expected_tau_hat_signs={"KO": 0, "AV": 0, "RU": 1, "CA": 0, "UM": 0, "DR": 0},
        expected_coherence_range=(0.5, 6.0),
        expected_valence_pressure_range=(0.0, 12.0),
        required_checks=["rdkit_parse", "valence_satisfied", "aromaticity_verified"],
        difficulty=2,
        source="boundary",
        tags=["aromatic", "kekule"],
    ),
    ChemistryVerificationRow(
        smiles="[Na+].[Cl-]",
        name="sodium_chloride",
        expected_valid=True,
        expected_family="ionic_salt",
        expected_elements=["Na", "Cl"],
        expected_governance="ALLOW",
        manual_valence_check="Na+: valence 0 (lost 1 electron). Cl-: valence 0 (gained 1 electron, octet complete). Ionic bond, not covalent.",
        manual_electronegativity="Cl (3.16) >> Na (0.93). ΔEN = 2.23. Ionic, not covalent. Dissociates in water.",
        manual_functional_group="Ionic salt. No covalent functional group. Electrolyte.",
        manual_bond_analysis="No covalent bonds. Na+ and Cl- held by electrostatic attraction. Crystal lattice.",
        expected_tau_hat_signs={"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0},
        expected_coherence_range=(0.0, 2.0),
        expected_valence_pressure_range=(0.0, 5.0),
        required_checks=["rdkit_parse", "ionic_noted"],
        difficulty=2,
        source="boundary",
        tags=["ionic", "salt", "inorganic"],
    ),
    ChemistryVerificationRow(
        smiles="CC(C)C(C)C(C)C(C)C(C)C(C)C(C)C(C)C",
        name="long_branched_alkane",
        expected_valid=True,
        expected_family="alkane",
        expected_elements=["C"],
        expected_governance="ALLOW",
        manual_valence_check="Every C: valence 4. Each terminal C: 3H + 1C = 4. Each internal C: 2H + 2C = 4. Branched Cs: 1H + 3C = 4. ALL VALID.",
        manual_electronegativity="All C (2.55) and H (2.20). Nonpolar. Hydrophobic.",
        manual_functional_group="Branched alkane. No functional group. Used to test parser on long chains.",
        manual_bond_analysis="All C-C and C-H single bonds. sp3 throughout.",
        expected_tau_hat_signs={"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0},
        expected_coherence_range=(1.0, 10.0),
        expected_valence_pressure_range=(2.0, 20.0),
        required_checks=["rdkit_parse", "valence_satisfied"],
        difficulty=2,
        source="boundary",
        tags=["alkane", "long_chain", "branched"],
    ),
]


def build_dataset():
    os.makedirs(os.path.dirname(DATASET_PATH) or ".", exist_ok=True)

    with open(DATASET_PATH, "w", encoding="utf-8") as f:
        for row in ROWS:
            f.write(json.dumps(asdict(row), ensure_ascii=False) + "\n")

    manifest = {
        "dataset": "chemistry_manual_verification_v1",
        "version": "1.0.0",
        "n_rows": len(ROWS),
        "sources": list(set(r.source for r in ROWS)),
        "difficulty_distribution": {
            str(d): sum(1 for r in ROWS if r.difficulty == d)
            for d in sorted(set(r.difficulty for r in ROWS))
        },
        "governance_distribution": {
            g: sum(1 for r in ROWS if r.expected_governance == g)
            for g in set(r.expected_governance for r in ROWS)
        },
        "columns": list(asdict(ROWS[0]).keys()),
        "path": DATASET_PATH,
        "description": (
            "College-level chemistry verification dataset. Each row forces the system "
            "to walk the full arithmetic path: atoms → bonds → valence → electronegativity "
            "→ functional group → RDKit validity → SCBE fusion → governance verdict."
        ),
    }

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Wrote {len(ROWS)} rows to {DATASET_PATH}")
    print(f"Manifest: {MANIFEST_PATH}")
    print(f"  Sources: {manifest['sources']}")
    print(f"  Difficulty: {manifest['difficulty_distribution']}")
    print(f"  Governance: {manifest['governance_distribution']}")


if __name__ == "__main__":
    build_dataset()
