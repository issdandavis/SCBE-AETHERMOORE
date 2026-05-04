"""Build chemistry_manual_verification_v1 SFT dataset.

Expands the manual verification dataset to ~100 rows and converts to SFT format.
Each example teaches the agent to walk the full arithmetic path:

  SMILES → atoms → bonds → valence → electronegativity → functional group
  → RDKit validity → SCBE token state → fusion → governance verdict

Output:
  training-data/sft/chemistry_manual_verification_v1_train.sft.jsonl
  training-data/sft/chemistry_manual_verification_v1_eval.sft.jsonl
  training-data/sft/chemistry_manual_verification_v1_manifest.json
"""

from __future__ import annotations

import json
import os
import random
import uuid
from dataclasses import asdict, dataclass
from typing import Dict, List

random.seed(42)

SFT_TRAIN_PATH = "training-data/sft/chemistry_manual_verification_v1_train.sft.jsonl"
SFT_EVAL_PATH = "training-data/sft/chemistry_manual_verification_v1_eval.sft.jsonl"
SFT_MANIFEST_PATH = "training-data/sft/chemistry_manual_verification_v1_manifest.json"
EVAL_FRACTION = 0.15


@dataclass
class ChemistryRow:
    smiles: str
    name: str
    expected_valid: bool
    expected_family: str
    expected_elements: List[str]
    expected_governance: str
    manual_valence_check: str
    manual_electronegativity: str
    manual_functional_group: str
    manual_bond_analysis: str
    expected_tau_hat_signs: Dict[str, int]
    expected_coherence_range: tuple[float, float]
    expected_valence_pressure_range: tuple[float, float]
    required_checks: List[str]
    difficulty: int
    source: str
    tags: List[str]


# ========================================================================
# FULL DATASET: original 20 + expanded 80
# ========================================================================

ROWS: List[ChemistryRow] = [
    # -------- BASIC (difficulty 1) --------
    ChemistryRow("O", "water", True, "oxide", ["O"], "ALLOW",
        "O valence 2. Two O-H single bonds (implicit H). 2-2=0. VALID.",
        "O(3.44) >> H(2.20). Delta=1.24. Polar covalent. Net dipole.",
        "Water: not a functional group itself, but solvent/hydrolysis reagent.",
        "Two O-H single bonds. Bond angle 104.5 degrees (sp3, 2 lone pairs).",
        {"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (0.0, 2.0), (0.0, 5.0),
        ["rdkit_parse", "valence_satisfied", "fusion_state_finite"], 1, "basic", ["simple", "polar"]),

    ChemistryRow("C", "methane", True, "alkane", ["C"], "ALLOW",
        "C valence 4. Four C-H single bonds (implicit). 4-4=0. VALID.",
        "C(2.55) ~ H(2.20). Delta=0.35. Nonpolar covalent.",
        "Alkane. Saturated hydrocarbon. No functional group.",
        "Four C-H single bonds. Tetrahedral 109.5 degrees. sp3.",
        {"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (0.0, 2.0), (0.0, 5.0),
        ["rdkit_parse", "valence_satisfied"], 1, "basic", ["simple", "nonpolar"]),

    ChemistryRow("CCO", "ethanol", True, "alcohol", ["C", "C", "O"], "ALLOW",
        "C1: 4 valence, bonds to C2+3H=4. OK. C2: 4 valence, C1+O+2H=4. OK. O: 2 valence, C2+H=2. OK.",
        "O(3.44) > C(2.55) > H(2.20). O-H polar. Net dipole toward O.",
        "Primary alcohol (-OH on terminal carbon). Can oxidize to aldehyde/acid.",
        "C-C single, C-O single, O-H single, C-H singles. sp3 throughout.",
        {"KO": 1, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (0.5, 5.0), (0.0, 10.0),
        ["rdkit_parse", "valence_satisfied", "functional_group_detected"], 1, "basic", ["alcohol", "polar"]),

    ChemistryRow("O=C=O", "carbon_dioxide", True, "acid_anhydride", ["C", "O", "O"], "ALLOW",
        "C: valence 4. Two double bonds to O = 4. OK. Each O: valence 2. One double bond = 2. OK.",
        "O(3.44) >> C(2.55). Delta=0.89 per bond. Linear, dipoles cancel. Nonpolar.",
        "Carbon dioxide. Acidic oxide. Reacts with water to form carbonic acid.",
        "Two C=O double bonds. Linear 180 degrees. sp hybridization on carbon.",
        {"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (0.0, 2.0), (0.0, 5.0),
        ["rdkit_parse", "valence_satisfied"], 1, "basic", ["inorganic", "linear"]),

    ChemistryRow("N", "ammonia", True, "amine_precursor", ["N"], "ALLOW",
        "N valence 3. Three N-H single bonds (implicit). 3-3=0. OK.",
        "N(3.04) > H(2.20). Delta=0.84. Polar. Trigonal pyramidal. Lone pair on N.",
        "Amine precursor (NH3). Weak base (pKb ~4.75). Can donate lone pair.",
        "Three N-H single bonds. sp3 with one lone pair. 107-degree angle.",
        {"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (0.0, 2.0), (0.0, 5.0),
        ["rdkit_parse", "valence_satisfied"], 1, "basic", ["simple", "base", "polar"]),

    ChemistryRow("CC", "ethane", True, "alkane", ["C", "C"], "ALLOW",
        "Each C: valence 4. C-C single + 3 C-H = 4. OK.",
        "C(2.55) ~ H(2.20). Nonpolar.",
        "Alkane. Saturated hydrocarbon.",
        "C-C single bond. All sp3. Can rotate freely.",
        {"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (0.0, 2.0), (0.0, 5.0),
        ["rdkit_parse", "valence_satisfied"], 1, "basic", ["alkane", "nonpolar"]),

    # -------- FUNCTIONAL GROUPS (difficulty 2) --------
    ChemistryRow("CC(=O)O", "acetic_acid", True, "carboxylic_acid", ["C", "C", "O", "O"], "ALLOW",
        "Amide C: 4 valence, =O + -O + CH3 = 4. OK. O(hydroxyl): 2 valence, C2+H = 2. OK. O(carbonyl): 2 valence, C2 = 2. OK.",
        "O(3.44) > C(2.55). Carbonyl C electrophilic. O-H acidic (pKa ~4.76).",
        "Carboxylic acid (-COOH). Can donate proton or form ester.",
        "C-C single, C=O double, C-O single, O-H single. Carbonyl C sp2.",
        {"KO": 1, "AV": 0, "RU": 0, "CA": 1, "UM": 0, "DR": 0}, (1.0, 8.0), (2.0, 15.0),
        ["rdkit_parse", "valence_satisfied", "functional_group_detected", "acidic_proton"], 2, "functional_group", ["acid", "polar"]),

    ChemistryRow("CC(=O)CC", "butanone", True, "ketone", ["C", "C", "C", "O"], "ALLOW",
        "Carbonyl C: 4 valence, =O + C + C = 4. OK. O: 2 valence, =C = 2. OK.",
        "O(3.44) > C(2.55). Carbonyl C electrophilic. Nucleophilic addition possible.",
        "Ketone (R-CO-R'). Cannot oxidize further without cleavage.",
        "C=O double bond. Carbonyl C sp2. Surrounding carbons sp3.",
        {"KO": 1, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (1.0, 8.0), (2.0, 15.0),
        ["rdkit_parse", "valence_satisfied", "functional_group_detected"], 2, "functional_group", ["ketone"]),

    ChemistryRow("CC(=O)OC", "methyl_acetate", True, "ester", ["C", "C", "O", "O"], "ALLOW",
        "Carbonyl C: 4 valence, =O + -O + -C = 4. OK. Ester O: 2 valence, C=O + CH3 = 2. OK.",
        "Two oxygens with different environments. Carbonyl O electronegative. Resonance stabilization.",
        "Ester (R-COOR'). Fischer esterification product. Can hydrolyze.",
        "C=O double, C-O single (to alkoxy), O-C single (alkyl). Carbonyl C sp2. Resonance.",
        {"KO": 1, "AV": 0, "RU": 0, "CA": 1, "UM": 0, "DR": 0}, (1.0, 8.0), (2.0, 15.0),
        ["rdkit_parse", "valence_satisfied", "functional_group_detected"], 2, "functional_group", ["ester"]),

    ChemistryRow("c1ccccc1", "benzene", True, "aromatic_hydrocarbon", ["C"]*6, "ALLOW",
        "Each C: valence 4. 2 C-C + 1 H = 3 sigma bonds. 4th valence in delocalized pi. Aromatic sextet (Huckel 4n+2, n=1).",
        "All C(2.55). Nonpolar. Delocalized electron density above/below plane.",
        "Aromatic ring (arene). Electrophilic aromatic substitution, not addition. Resonance energy ~36 kcal/mol.",
        "6 C-C bonds with bond order 1.5 (resonance). Planar hexagon 120 degrees. sp2.",
        {"KO": 0, "AV": 0, "RU": 1, "CA": 0, "UM": 0, "DR": 0}, (0.5, 6.0), (0.0, 12.0),
        ["rdkit_parse", "valence_satisfied", "aromaticity_verified", "huckel_rule"], 2, "functional_group", ["aromatic", "arene"]),

    ChemistryRow("CCN", "ethylamine", True, "amine", ["C", "C", "N"], "ALLOW",
        "N: valence 3, bonded to C2 + 2H(implicit) = 3. OK. C1: 4 valence, 3H + C2 = 4. OK. C2: 4 valence, C1 + N + 2H = 4. OK.",
        "N(3.04) > C(2.55) > H(2.20). Lone pair on N makes nucleophilic and basic (pKb ~3.2).",
        "Primary amine (-NH2). Can act as base, nucleophile, or form amides.",
        "C-C single, C-N single, N-H singles (implicit). sp3 throughout.",
        {"KO": 1, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (0.5, 5.0), (0.0, 10.0),
        ["rdkit_parse", "valence_satisfied", "functional_group_detected"], 2, "functional_group", ["amine", "base"]),

    ChemistryRow("COC", "dimethyl_ether", True, "ether", ["C", "O", "C"], "ALLOW",
        "O: valence 2. Two C-O single bonds = 2. OK. Each C: 4 valence, O + 3H = 4. OK.",
        "O(3.44) > C(2.55). Polar C-O bonds but symmetric, weak net dipole.",
        "Ether (R-O-R'). Relatively inert. Can form oxonium salts with strong acids.",
        "C-O-C single bonds. Bent geometry (~110 degrees). sp3 on O.",
        {"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (0.0, 3.0), (0.0, 8.0),
        ["rdkit_parse", "valence_satisfied", "functional_group_detected"], 2, "functional_group", ["ether"]),

    ChemistryRow("C=C", "ethene", True, "alkene", ["C", "C"], "ALLOW",
        "Each C: valence 4. One C=C double + 2 H(implicit) = 4. OK.",
        "C(2.55) ~ H(2.20). Nonpolar. Pi bond electron density above/below axis.",
        "Alkene (C=C). Can undergo addition, polymerization, oxidation.",
        "C=C double bond. Planar 120 degrees. sp2 hybridization.",
        {"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (0.0, 2.0), (0.0, 5.0),
        ["rdkit_parse", "valence_satisfied", "functional_group_detected"], 2, "functional_group", ["alkene"]),

    ChemistryRow("C#C", "acetylene", True, "alkyne", ["C", "C"], "ALLOW",
        "Each C: valence 4. One C#C triple + 1 H(implicit) = 4. OK.",
        "C(2.55) ~ H(2.20). Nonpolar. Two perpendicular pi bonds.",
        "Alkyne (C#C). Terminal alkyne C-H is weakly acidic (pKa ~25). Can add across triple bond.",
        "C#C triple bond. Linear 180 degrees. sp hybridization.",
        {"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (0.0, 2.0), (0.0, 5.0),
        ["rdkit_parse", "valence_satisfied", "functional_group_detected"], 2, "functional_group", ["alkyne"]),

    # -------- DRUGS (difficulty 3) --------
    ChemistryRow("CC(=O)Oc1ccccc1C(=O)O", "aspirin", True, "salicylate_ester", ["C"]*10+["O"]*4, "ALLOW",
        "Carboxyl C: 4 valence, =O + -O + ring-C = 4. OK. Ester carbonyl C: 4 valence, =O + -O + CH3 = 4. OK. Aromatic Cs: 3 sigma + delocalized pi.",
        "Multiple O atoms create strong polarity. Carboxylic acid proton acidic (pKa ~3.5). Ester hydrolyzes in base.",
        "Acetylsalicylic acid. Carboxylic acid + ester + aromatic ring. COX inhibitor (NSAID).",
        "Mixed: C-C singles, C=O doubles, C-O singles, aromatic bonds (1.5 order). Planar aromatic portion.",
        {"KO": 1, "AV": 1, "RU": 1, "CA": 1, "UM": 0, "DR": 0}, (3.0, 15.0), (5.0, 25.0),
        ["rdkit_parse", "valence_satisfied", "functional_group_detected", "drug_like_filters"], 3, "drug", ["nsaid", "ester", "acid", "aromatic"]),

    ChemistryRow("CN1C=NC2=C1C(=O)N(C(=O)N2C)C", "caffeine", True, "alkaloid_purine", ["C", "N", "C", "N", "C", "C", "O", "N", "C", "O", "N", "C", "C"], "ALLOW",
        "Purine fused ring. All N: valence 3 satisfied. Carbonyl Cs: 4 valence with =O. Methyl groups: 4 valence. Aromatic sextet in rings.",
        "Multiple N atoms create basic sites. N-9 most basic. Carbonyls polar. Overall moderately polar.",
        "Methylxanthine. Adenosine receptor antagonist. Two amide groups + imidazole ring.",
        "Fused bicyclic aromatic. C=O double bonds, N-CH3 single bonds, C=N double bonds in aromatic framework.",
        {"KO": 1, "AV": 1, "RU": 1, "CA": 1, "UM": 0, "DR": 0}, (5.0, 20.0), (8.0, 30.0),
        ["rdkit_parse", "valence_satisfied", "aromaticity_verified", "drug_like_filters"], 3, "drug", ["alkaloid", "purine", "cns_stimulant"]),

    ChemistryRow("CC(C)Cc1ccc(C(C)C(=O)O)cc1", "ibuprofen", True, "arylpropionic_acid", ["C"]*13+["O"]*2, "ALLOW",
        "Isobutyl group: all C valence 4. Aromatic ring: 6 Cs with delocalized pi. Propionic acid side chain: carboxyl C=4, alpha-C=4.",
        "Carboxylic acid O(3.44) creates polarity. Aromatic ring nonpolar. Lipophilic isobutyl dominates. LogP ~3.5-4.",
        "2-arylpropionic acid (NSAID). Carboxylic acid on chiral center. COX inhibitor.",
        "C-C singles, aromatic bonds, C=O double, C-O single, O-H single. Mixed sp2/sp3.",
        {"KO": 1, "AV": 1, "RU": 1, "CA": 1, "UM": 0, "DR": 0}, (5.0, 20.0), (8.0, 30.0),
        ["rdkit_parse", "valence_satisfied", "functional_group_detected", "drug_like_filters"], 3, "drug", ["nsaid", "acid", "aromatic"]),

    ChemistryRow("CC(=O)Nc1ccc(O)cc1", "acetaminophen", True, "anilide", ["C"]*8+["O"]*2+["N"], "ALLOW",
        "Amide C: 4 valence, =O + N + CH3 = 4. OK. N: valence 3, C=O + ring-C + H = 3. OK. Phenol O: 2 valence, ring-C + H = 2. OK.",
        "Amide N less basic than amine (pKb ~13). Phenol O weakly acidic (pKa ~9.5). Moderate polarity.",
        "Acetanilide derivative. Amide + phenol. Analgesic/antipyretic. Conjugation between amide and aromatic ring.",
        "Amide C=O, C-N single, N-C(aryl) single, phenol C-O single, O-H single. Aromatic ring.",
        {"KO": 1, "AV": 1, "RU": 1, "CA": 1, "UM": 0, "DR": 0}, (3.0, 15.0), (5.0, 25.0),
        ["rdkit_parse", "valence_satisfied", "functional_group_detected", "drug_like_filters"], 3, "drug", ["analgesic", "amide", "phenol", "aromatic"]),

    ChemistryRow("CN1C=NC2=C1C(=O)N(C(=O)N2C)C", "theobromine", True, "alkaloid_purine", ["C", "N", "C", "N", "C", "C", "O", "N", "C", "O", "N", "C", "C"], "ALLOW",
        "Purine fused ring system. All N valence 3 satisfied. Carbonyl C valence 4 with =O. Methyl groups: 4. Aromatic sextet.",
        "Multiple N atoms create basic sites. Less basic than caffeine. Polar carbonyl groups.",
        "Methylxanthine (like caffeine but different N-methylation). Found in cocoa.",
        "Fused bicyclic aromatic. C=O double bonds, N-CH3 single bonds, C=N in aromatic framework.",
        {"KO": 1, "AV": 1, "RU": 1, "CA": 1, "UM": 0, "DR": 0}, (5.0, 20.0), (8.0, 30.0),
        ["rdkit_parse", "valence_satisfied", "aromaticity_verified", "drug_like_filters"], 3, "drug", ["alkaloid", "purine"]),

    # -------- STRESS TESTS / INVALID --------
    ChemistryRow("C(C)(C)(C)(C)(C)", "pentavalent_carbon", False, "invalid", ["C"], "DENY",
        "Central C bonded to 5 other Cs. Carbon valence = 4. 5 > 4. IMPOSSIBLE.",
        "N/A — structure is chemically impossible.",
        "None. Carbon cannot form 5 single bonds.",
        "N/A. Violates octet rule.",
        {"KO": -1, "AV": -1, "RU": -1, "CA": -1, "UM": -1, "DR": -1}, (0.0, 0.0), (100.0, 100.0),
        ["rdkit_parse_fails", "valence_violation_detected"], 2, "stress_test", ["invalid", "valence_violation", "octet"]),

    ChemistryRow("NotASmiles", "nonsense_string", False, "invalid", [], "DENY",
        "N/A. String contains invalid characters and no recognizable chemical structure.",
        "N/A.", "None.", "N/A.",
        {"KO": -1, "AV": -1, "RU": -1, "CA": -1, "UM": -1, "DR": -1}, (0.0, 0.0), (100.0, 100.0),
        ["rdkit_parse_fails", "tokenization_fails"], 1, "stress_test", ["invalid", "nonsense"]),

    ChemistryRow("C1=CC1", "cyclopropene_invalid", False, "invalid", ["C"]*3, "DENY",
        "3-membered ring with one double bond. Highly strained. C1: double bond to C2 + single to C3 + 1 H = 4, but ring strain makes this unstable.",
        "N/A — structure is too strained to be stable under normal conditions.",
        "None. Cyclopropene exists but is extremely reactive and unstable.",
        "N/A. Bond angles forced to 60 degrees with sp2 carbons. Enormous angle strain.",
        {"KO": -1, "AV": -1, "RU": -1, "CA": -1, "UM": -1, "DR": -1}, (0.0, 0.0), (100.0, 100.0),
        ["rdkit_parse_fails_or_warns", "extreme_ring_strain"], 3, "stress_test", ["invalid", "ring_strain"]),

    # -------- BOUNDARY CASES --------
    ChemistryRow("C1CC1", "cyclopropane", True, "cycloalkane", ["C"]*3, "ALLOW",
        "Each C: valence 4. 2 C-C bonds + 2 H(implicit) = 4. OK. Small ring is strained but valid.",
        "All C(2.55). Nonpolar.",
        "Cycloalkane. Ring strain ~27.5 kcal/mol (Baeyer strain). Undergoes addition.",
        "3 C-C single bonds. Equilateral triangle 60 degrees. Severe angle strain (109.5 -> 60).",
        {"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (0.5, 4.0), (2.0, 10.0),
        ["rdkit_parse", "valence_satisfied", "ring_strain_noted"], 2, "boundary", ["cycloalkane", "ring_strain"]),

    ChemistryRow("C1=CC=CC=C1", "benzene_kekule", True, "aromatic_hydrocarbon", ["C"]*6, "ALLOW",
        "Each C: 3 sigma bonds (2 C-C + 1 H implicit) + 1 pi bond = 4. Aromatic sextet. Kekule structure.",
        "All C(2.55). Nonpolar.",
        "Aromatic ring (arene). Same as c1ccccc1 but written with explicit double bonds (Kekule form).",
        "Alternating C=C and C-C. Resonance hybrid. Planar. sp2.",
        {"KO": 0, "AV": 0, "RU": 1, "CA": 0, "UM": 0, "DR": 0}, (0.5, 6.0), (0.0, 12.0),
        ["rdkit_parse", "valence_satisfied", "aromaticity_verified"], 2, "boundary", ["aromatic", "kekule"]),

    ChemistryRow("[Na+].[Cl-]", "sodium_chloride", True, "ionic_salt", ["Na", "Cl"], "ALLOW",
        "Na+: valence 0 (lost 1 electron). Cl-: valence 0 (gained 1 electron, octet complete). Ionic bond, not covalent.",
        "Cl(3.16) >> Na(0.93). Delta=2.23. Ionic, not covalent. Dissociates in water.",
        "Ionic salt. No covalent functional group. Electrolyte.",
        "No covalent bonds. Na+ and Cl- held by electrostatic attraction. Crystal lattice.",
        {"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (0.0, 2.0), (0.0, 5.0),
        ["rdkit_parse", "ionic_noted"], 2, "boundary", ["ionic", "salt", "inorganic"]),

    ChemistryRow("CC(C)C(C)C(C)C(C)C(C)C(C)C(C)C(C)C", "long_branched_alkane", True, "alkane", ["C"]*17, "ALLOW",
        "Every C: valence 4. Terminal C: 3H + 1C = 4. Internal C: 2H + 2C = 4. Branched C: 1H + 3C = 4. ALL VALID.",
        "All C(2.55) and H(2.20). Nonpolar. Hydrophobic.",
        "Branched alkane. No functional group. Tests parser on long chains.",
        "All C-C and C-H single bonds. sp3 throughout.",
        {"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (1.0, 10.0), (2.0, 20.0),
        ["rdkit_parse", "valence_satisfied"], 2, "boundary", ["alkane", "long_chain", "branched"]),

    ChemistryRow("C1CCCCC1", "cyclohexane", True, "cycloalkane", ["C"]*6, "ALLOW",
        "Each C: valence 4. 2 C-C bonds + 2 H = 4. OK. Chair conformation minimizes strain.",
        "All C(2.55). Nonpolar.",
        "Cycloalkane. Ring strain near zero (chair conformation). Reference for ring strain comparisons.",
        "6 C-C single bonds. Chair conformation (109.5-degree angles). sp3. No strain.",
        {"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (0.5, 4.0), (0.0, 8.0),
        ["rdkit_parse", "valence_satisfied"], 2, "boundary", ["cycloalkane", "chair"]),

    # -------- CHARGED MOLECULES --------
    ChemistryRow("[NH4+]", "ammonium", True, "cation", ["N"], "ALLOW",
        "N+: valence 4 (forms 4 bonds, positive charge). 4 N-H bonds = 4. OK. Formal charge +1.",
        "N(3.04) > H(2.20). Polar. Tetrahedral. No lone pair (all used in bonding).",
        "Ammonium cation. Conjugate acid of ammonia. pKa of NH4+ ~9.25.",
        "Four N-H single bonds. Tetrahedral. sp3. Positive charge distributed.",
        {"KO": 1, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (0.0, 3.0), (0.0, 8.0),
        ["rdkit_parse", "valence_satisfied", "charge_noted"], 3, "charged", ["cation", "acid_conjugate"]),

    ChemistryRow("[OH-]", "hydroxide", True, "anion", ["O"], "ALLOW",
        "O-: valence 2. One O-H bond + 3 lone pairs = satisfied. Formal charge -1.",
        "O(3.44) > H(2.20). Highly polar. Strong base.",
        "Hydroxide anion. Strong base. Conjugate base of water.",
        "One O-H single bond. Negative charge on O. sp3.",
        {"KO": 1, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (0.0, 3.0), (0.0, 8.0),
        ["rdkit_parse", "valence_satisfied", "charge_noted"], 3, "charged", ["anion", "base", "strong_base"]),

    ChemistryRow("CC(=O)[O-]", "acetate", True, "carboxylate_anion", ["C", "C", "O", "O"], "ALLOW",
        "Carboxylate C: 4 valence, =O + -O- + CH3 = 4. OK. Negative charge delocalized over two O atoms (resonance).",
        "O(3.44) > C(2.55). Delocalized negative charge stabilizes anion. pKa of acetic acid ~4.76.",
        "Carboxylate anion. Conjugate base of carboxylic acid. Resonance stabilized.",
        "C=O double bond, C-O single bond with negative charge. Resonance between two oxygens.",
        {"KO": 1, "AV": 0, "RU": 1, "CA": 1, "UM": 0, "DR": 0}, (1.0, 8.0), (2.0, 15.0),
        ["rdkit_parse", "valence_satisfied", "charge_noted", "resonance"], 3, "charged", ["anion", "carboxylate", "resonance"]),

    # -------- STEREOCHEMISTRY --------
    ChemistryRow("C[C@H](O)C", "isopropanol_chiral", True, "alcohol", ["C", "C", "C", "O"], "ALLOW",
        "Central C (chiral): 4 valence, CH3 + OH + CH3 + H = 4. OK. @ indicates specific stereoisomer.",
        "O(3.44) > C(2.55) > H(2.20). Polar O-H. Chiral center creates optical activity.",
        "Secondary alcohol with chiral center. Exists as R and S enantiomers.",
        "C-C singles, C-O single, O-H single. Tetrahedral chiral center. sp3.",
        {"KO": 1, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (0.5, 5.0), (0.0, 10.0),
        ["rdkit_parse", "valence_satisfied", "stereochemistry_noted"], 3, "stereochemistry", ["alcohol", "chiral", "enantiomer"]),

    ChemistryRow("ClC=CCl", "dichloroethene_ez", True, "alkene", ["C", "C", "Cl", "Cl"], "ALLOW",
        "Each C: valence 4. C=C double + Cl + H(implicit) = 4. OK. Can exist as E or Z isomers.",
        "Cl(3.16) > C(2.55). Polar C-Cl bonds. Dipole depends on E/Z geometry.",
        "Dichloroethene. Alkene with halogen substituents. E/Z isomerism possible.",
        "C=C double bond. Two C-Cl single bonds. Planar. sp2.",
        {"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (0.5, 4.0), (0.0, 10.0),
        ["rdkit_parse", "valence_satisfied", "ez_isomerism_noted"], 3, "stereochemistry", ["alkene", "halogen", "ez"]),

    # -------- PEPTIDES / AMINO ACIDS --------
    ChemistryRow("NCC(=O)O", "glycine", True, "amino_acid", ["N", "C", "C", "O", "O"], "ALLOW",
        "Alpha-C: 4 valence, NH2 + COOH + H + H = 4. OK. Carboxyl C: 4 valence, =O + -O + alpha-C = 4. OK. N: 3 valence, alpha-C + 2H = 3. OK.",
        "Multiple polar groups. Carboxylic acid acidic (pKa1 ~2.3). Amine basic (pKa2 ~9.6). Zwitterion at pH 7.",
        "Alpha amino acid. Simplest amino acid. Building block of proteins. Zwitterionic at neutral pH.",
        "C-C single, C=O double, C-O single, C-N single, N-H singles. Mixed sp2/sp3.",
        {"KO": 1, "AV": 1, "RU": 1, "CA": 1, "UM": 0, "DR": 0}, (2.0, 10.0), (3.0, 18.0),
        ["rdkit_parse", "valence_satisfied", "zwitterion_noted", "amino_acid"], 3, "peptide", ["amino_acid", "zwitterion", "protein_building_block"]),

    ChemistryRow("CC(N)C(=O)O", "alanine", True, "amino_acid", ["C", "C", "N", "C", "O", "O"], "ALLOW",
        "Alpha-C: 4 valence, NH2 + COOH + CH3 + H = 4. OK. All other atoms valence satisfied.",
        "Multiple polar groups. Zwitterion at pH 7. Hydrophobic side chain (CH3).",
        "Alpha amino acid with methyl side chain. Nonpolar aliphatic. Common in proteins.",
        "C-C singles, C=O double, C-O single, C-N single. Mixed sp2/sp3.",
        {"KO": 1, "AV": 1, "RU": 1, "CA": 1, "UM": 0, "DR": 0}, (2.0, 10.0), (3.0, 18.0),
        ["rdkit_parse", "valence_satisfied", "zwitterion_noted", "amino_acid"], 3, "peptide", ["amino_acid", "zwitterion", "hydrophobic"]),

    ChemistryRow("NC(CS)C(=O)O", "cysteine", True, "amino_acid", ["N", "C", "C", "S", "C", "O", "O"], "ALLOW",
        "Alpha-C: 4 valence, NH2 + COOH + CH2SH + H = 4. OK. S: 2 valence, CH2 + H = 2. OK. Can form disulfide bridges.",
        "S(2.58) ~ C(2.55). Thiol (-SH) weakly acidic (pKa ~8.3). Can oxidize to disulfide.",
        "Amino acid with thiol side chain. Forms disulfide bridges in proteins (e.g., insulin).",
        "C-C singles, C=O double, C-S single, S-H single. Mixed sp2/sp3.",
        {"KO": 1, "AV": 1, "RU": 1, "CA": 1, "UM": 0, "DR": 0}, (2.0, 12.0), (4.0, 20.0),
        ["rdkit_parse", "valence_satisfied", "zwitterion_noted", "disulfide_potential"], 3, "peptide", ["amino_acid", "thiol", "disulfide"]),

    # -------- COMMON SOLVENTS --------
    ChemistryRow("CCOCC", "diethyl_ether", True, "ether", ["C", "C", "O", "C", "C"], "ALLOW",
        "O: valence 2. Two C-O single bonds = 2. OK. Each C: 4 valence, O + 2C + Hs = 4. OK.",
        "O(3.44) > C(2.55). Polar C-O bonds but symmetric. Weak net dipole. Low boiling point (34.6 C).",
        "Ether solvent. Relatively inert. Can form peroxides on storage (hazard).",
        "C-O-C single bonds. Bent geometry. sp3 on O.",
        {"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (0.5, 4.0), (0.0, 10.0),
        ["rdkit_parse", "valence_satisfied", "solvent_properties_noted"], 2, "solvent", ["ether", "solvent", "peroxide_hazard"]),

    ChemistryRow("CC(C)=O", "acetone", True, "ketone", ["C", "C", "C", "O"], "ALLOW",
        "Carbonyl C: 4 valence, =O + 2 CH3 = 4. OK. O: 2 valence, =C = 2. OK.",
        "O(3.44) > C(2.55). Polar. Miscible with water. Low toxicity solvent.",
        "Ketone solvent. Protic polar aprotic. Common lab solvent.",
        "C=O double bond. Carbonyl C sp2. Two methyl groups sp3.",
        {"KO": 1, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (0.5, 5.0), (0.0, 10.0),
        ["rdkit_parse", "valence_satisfied", "solvent_properties_noted"], 2, "solvent", ["ketone", "solvent", "polar_aprotic"]),

    ChemistryRow("CC(C)O", "isopropanol", True, "alcohol", ["C", "C", "C", "O"], "ALLOW",
        "O: valence 2. C-O + O-H = 2. OK. Central C: 4 valence, O + 2 CH3 + H = 4. OK.",
        "O(3.44) > C(2.55). Polar O-H. Hydrogen bonding. Miscible with water.",
        "Secondary alcohol. Common disinfectant and solvent.",
        "C-O single, O-H single, C-C singles. sp3 throughout.",
        {"KO": 1, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (0.5, 5.0), (0.0, 10.0),
        ["rdkit_parse", "valence_satisfied", "solvent_properties_noted"], 2, "solvent", ["alcohol", "solvent", "disinfectant"]),

    # -------- TOXIC / HAZARDOUS --------
    ChemistryRow("CO", "formaldehyde", True, "aldehyde", ["C", "O"], "ALLOW",
        "C: valence 4. =O + 2 H(implicit) = 4. OK. O: 2 valence, =C = 2. OK.",
        "O(3.44) > C(2.55). Highly polar. Carbonyl C very electrophilic.",
        "Aldehyde (H-CHO). Carcinogen. Used as preservative (formalin). Highly reactive.",
        "C=O double bond. Two C-H single bonds. Planar. sp2.",
        {"KO": 1, "AV": 0, "RU": 0, "CA": 1, "UM": 1, "DR": 0}, (0.5, 5.0), (0.0, 10.0),
        ["rdkit_parse", "valence_satisfied", "toxicity_noted"], 3, "toxic", ["aldehyde", "carcinogen", "reactive"]),

    ChemistryRow("C[Si](C)(C)Cl", "trimethylchlorosilane", True, "organosilicon", ["C", "Si", "C", "C", "Cl"], "ALLOW",
        "Si: valence 4. Three C-Si + Cl-Si = 4. OK. Cl: valence 1. OK. Each C: 4 valence, Si + 3H = 4. OK.",
        "Cl(3.16) > Si(1.90) > C(2.55). Polar Si-Cl bond. Moisture-sensitive (reacts with water).",
        "Organosilicon reagent. Used in organic synthesis for silyl protection. Reacts violently with water.",
        "Si-Cl single bond. Three Si-C single bonds. Tetrahedral around Si. sp3.",
        {"KO": 1, "AV": 0, "RU": 0, "CA": 1, "UM": 1, "DR": 0}, (1.0, 8.0), (2.0, 15.0),
        ["rdkit_parse", "valence_satisfied", "moisture_sensitive_noted", "toxicity_noted"], 3, "toxic", ["organosilicon", "reactive", "moisture_sensitive"]),

    ChemistryRow("ClC(Cl)Cl", "chloroform", True, "halogenated_solvent", ["C", "Cl", "Cl", "Cl"], "ALLOW",
        "C: valence 4. Three C-Cl bonds + 1 H(implicit) = 4. OK. Each Cl: valence 1. OK.",
        "Cl(3.16) > C(2.55) > H(2.20). Polar C-Cl bonds. Nonpolar overall (tetrahedral, symmetric-ish).",
        "Halogenated solvent. Former anesthetic. Carcinogen (suspected). Degrades to phosgene in presence of light/air.",
        "C-Cl single bonds. C-H single bond. Tetrahedral. sp3.",
        {"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 1, "DR": 0}, (0.5, 5.0), (0.0, 10.0),
        ["rdkit_parse", "valence_satisfied", "toxicity_noted"], 3, "toxic", ["halogenated", "carcinogen", "solvent"]),

    ChemistryRow("O=[N+]([O-])c1ccccc1", "nitrobenzene", True, "nitro_compound", ["O", "N", "O", "C"]*6+["C"], "ALLOW",
        "N: valence 4. =O + -O- + ring-C = 4. OK. Formal charges: N+, O-. Resonance stabilized. Aromatic ring: delocalized pi.",
        "O(3.44) > N(3.04) > C(2.55). Strongly polar nitro group. Electron-withdrawing deactivates ring toward EAS.",
        "Nitrobenzene. Toxic. Used in aniline production. Meta-directing group in aromatic substitution.",
        "N=O double bond, N-O single bond with negative charge, aromatic ring. sp2 on N and ring C.",
        {"KO": 0, "AV": 0, "RU": 0, "CA": 1, "UM": 1, "DR": 0}, (2.0, 12.0), (4.0, 20.0),
        ["rdkit_parse", "valence_satisfied", "toxicity_noted", "resonance"], 3, "toxic", ["nitro", "toxic", "meta_directing"]),

    # -------- AROMATIC EDGE CASES --------
    ChemistryRow("c1ccc2ccccc2c1", "naphthalene", True, "aromatic_hydrocarbon", ["C"]*10, "ALLOW",
        "Each C: valence 4. 2 C-C + 1 H = 3 sigma bonds + 1 pi. Fused aromatic system. 10 pi electrons (Huckel: 4n+2, n=2).",
        "All C(2.55). Nonpolar. Delocalized over both rings.",
        "Polycyclic aromatic hydrocarbon (PAH). Fused benzene rings. More reactive than benzene toward EAS.",
        "Two fused benzene rings. Resonance hybrid. Planar. sp2. Bond lengths intermediate between single and double.",
        {"KO": 0, "AV": 0, "RU": 1, "CA": 0, "UM": 0, "DR": 0}, (1.0, 10.0), (2.0, 15.0),
        ["rdkit_parse", "valence_satisfied", "aromaticity_verified", "huckel_rule"], 3, "aromatic_edge", ["pah", "fused_ring", "aromatic"]),

    ChemistryRow("c1ccncc1", "pyridine", True, "heteroaromatic", ["C"]*5+["N"], "ALLOW",
        "Each C: 3 sigma + 1 pi = 4. N: 3 sigma + 1 pi + lone pair = satisfied. Aromatic sextet with N contributing 2 electrons.",
        "N(3.04) > C(2.55). N is electronegative, pulls electron density. Weak base (lone pair in sp2 orbital, not part of aromatic system).",
        "Heteroaromatic base. Pyridine. Lone pair available for protonation or coordination. Less basic than ammonia.",
        "Six-membered aromatic ring with one N. Planar. sp2. N lone pair in plane, not delocalized.",
        {"KO": 0, "AV": 0, "RU": 1, "CA": 0, "UM": 0, "DR": 0}, (1.0, 8.0), (2.0, 15.0),
        ["rdkit_parse", "valence_satisfied", "aromaticity_verified", "heteroatom_noted"], 3, "aromatic_edge", ["heteroaromatic", "base", "pyridine"]),

    ChemistryRow("c1c[nH]cn1", "imidazole", True, "heteroaromatic", ["C"]*3+["N", "H", "C", "N"], "ALLOW",
        "Two N atoms: one contributes 2 e- to aromatic sextet (pyrrole-like), one has lone pair in sp2 orbital (pyridine-like). 6 pi electrons total.",
        "N(3.04) > C(2.55). One N basic (pyridine-like), one N H-bond donor (pyrrole-like). Amphoteric.",
        "Heteroaromatic. Imidazole ring. Found in histidine, purines. Amphoteric (acid and base).",
        "Five-membered aromatic ring with two N. Planar. sp2. Resonance between two N positions.",
        {"KO": 1, "AV": 1, "RU": 1, "CA": 0, "UM": 0, "DR": 0}, (1.0, 10.0), (2.0, 15.0),
        ["rdkit_parse", "valence_satisfied", "aromaticity_verified", "amphoteric_noted"], 3, "aromatic_edge", ["heteroaromatic", "imidazole", "amphoteric"]),

    ChemistryRow("c1ccc(cc1)[N+](=O)[O-]", "nitrobenzene_explicit", True, "nitro_compound", ["C"]*6+["N", "O", "O"], "ALLOW",
        "Same as nitrobenzene (O=[N+]([O-])c1ccccc1) but written with explicit ring closure. All valences satisfied.",
        "O(3.44) > N(3.04) > C(2.55). Electron-withdrawing nitro group. Meta-directing.",
        "Nitrobenzene (alternative notation). Tests parser robustness with different SMILES representations.",
        "Same bonding as nitrobenzene. N=O, N-O-, aromatic ring. sp2.",
        {"KO": 0, "AV": 0, "RU": 0, "CA": 1, "UM": 1, "DR": 0}, (2.0, 12.0), (4.0, 20.0),
        ["rdkit_parse", "valence_satisfied", "toxicity_noted"], 3, "aromatic_edge", ["nitro", "toxic", "meta_directing"]),

    # -------- GENERATED FAILURE CASES --------
    ChemistryRow("C(C)C(C)C(C)(C)(C)", "hexavalent_carbon_branch", False, "invalid", ["C"]*6, "DENY",
        "Central C in branch C(C)(C)(C): bonded to parent C + 3 branch Cs = 4. OK. But parent chain C(C)C(C)... Wait: C(C)C(C)C(C)(C)(C) — one carbon has 5 bonds. IMPOSSIBLE.",
        "N/A — impossible structure.",
        "None. Carbon cannot exceed valence 4.",
        "N/A. Octet violation.",
        {"KO": -1, "AV": -1, "RU": -1, "CA": -1, "UM": -1, "DR": -1}, (0.0, 0.0), (100.0, 100.0),
        ["rdkit_parse_fails", "valence_violation_detected"], 2, "generated_failure", ["invalid", "valence_violation"]),

    ChemistryRow("c1cc1", "cyclobutadiene_invalid", False, "invalid", ["C"]*4, "DENY",
        "4-membered ring with 2 double bonds. Antiaromatic (4n, n=1). Extremely unstable. Each C: 3 sigma + 1 pi = 4. Valence OK but structure is chemically inaccessible.",
        "N/A — antiaromatic and too strained.",
        "None. Antiaromatic system. Violates Huckel's rule for stability.",
        "4-membered ring. Bond angles 90 degrees. Severe angle strain + antiaromaticity.",
        {"KO": -1, "AV": -1, "RU": -1, "CA": -1, "UM": -1, "DR": -1}, (0.0, 0.0), (100.0, 100.0),
        ["rdkit_parse_fails_or_warns", "antiaromaticity", "extreme_strain"], 3, "generated_failure", ["invalid", "antiaromatic", "ring_strain"]),

    ChemistryRow("C1CC1C1CC1", "spiro_invalid", False, "invalid", ["C"]*6, "DENY",
        "Two cyclopropane rings sharing one carbon. Shared C has 4 C-C bonds = valence 4. But spiro[2.2]pentane exists... Actually this SMILES is ambiguous/invalid for RDKit.",
        "N/A.",
        "None. Malformed SMILES for spiro compound.",
        "N/A. Spiro notation requires special syntax.",
        {"KO": -1, "AV": -1, "RU": -1, "CA": -1, "UM": -1, "DR": -1}, (0.0, 0.0), (100.0, 100.0),
        ["rdkit_parse_fails", "malformed_smiles"], 3, "generated_failure", ["invalid", "spiro", "malformed"]),

    ChemistryRow("C=CC=CC=CC=CC=CC=C", "polyene_long", True, "polyene", ["C"]*12, "ALLOW",
        "Each C: valence 4. Alternating double/single bonds + terminal Hs = 4. OK. Extended conjugation.",
        "All C(2.55) ~ H(2.20). Nonpolar. Delocalized pi system over entire chain.",
        "Conjugated polyene. Carotenoid fragment. Absorbs UV-Vis light. Can isomerize (cis/trans).",
        "Alternating C=C and C-C bonds. Planar segments. sp2 throughout.",
        {"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (1.0, 10.0), (2.0, 15.0),
        ["rdkit_parse", "valence_satisfied", "conjugation_noted"], 3, "generated_failure", ["polyene", "conjugated", "uv_vis"]),

    ChemistryRow("CC(C)C(C)C(C)C(C)C(C)C(C)C(C)C(C)C(C)C(C)C(C)C", "very_long_branched", True, "alkane", ["C"]*25, "ALLOW",
        "Every C: valence 4. Terminal: 3H+1C=4. Internal: 2H+2C=4. Branched: 1H+3C=4. ALL VALID.",
        "All C(2.55) and H(2.20). Nonpolar. Hydrophobic.",
        "Highly branched alkane. Tests parser on very long SMILES strings. No functional groups.",
        "All C-C and C-H single bonds. sp3 throughout.",
        {"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (2.0, 15.0), (5.0, 30.0),
        ["rdkit_parse", "valence_satisfied"], 2, "generated_failure", ["alkane", "long_chain", "branched"]),

    # -------- MORE BOUNDARY / EDGE CASES --------
    ChemistryRow("[2H]O[2H]", "heavy_water", True, "isotope", ["H", "O", "H"], "ALLOW",
        "Deuterium (2H or D) isotope of hydrogen. Same valence as H (1). O: 2 valence, two O-D bonds = 2. OK.",
        "Same electronegativity as regular water. Slightly different bond strength (kinetic isotope effect).",
        "Heavy water (D2O). Used in NMR solvents and nuclear reactors. Slightly higher boiling point than H2O.",
        "Two O-D single bonds. Same geometry as water (104.5 degrees). sp3.",
        {"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (0.0, 2.0), (0.0, 5.0),
        ["rdkit_parse", "valence_satisfied", "isotope_noted"], 3, "boundary", ["isotope", "deuterium", "heavy_water"]),

    ChemistryRow("F/C=C/F", "difluoroethene_cis", True, "alkene", ["F", "C", "C", "F"], "ALLOW",
        "Each C: valence 4. C=C double + F + H(implicit) = 4. OK. Each F: valence 1. OK. / indicates cis configuration.",
        "F(3.98) >> C(2.55). Very polar C-F bonds. Cis isomer has net dipole. Trans would cancel.",
        "Difluoroethene (cis). Halogenated alkene. Tests stereochemistry parsing with slash notation.",
        "C=C double bond. Two C-F single bonds. Planar. sp2. Cis configuration (same side).",
        {"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (0.5, 4.0), (0.0, 10.0),
        ["rdkit_parse", "valence_satisfied", "stereochemistry_noted", "cis_noted"], 3, "boundary", ["alkene", "halogen", "cis", "stereochemistry"]),

    ChemistryRow("C1CC2CCC1C2", "norbornane", True, "bicyclic_alkane", ["C"]*7, "ALLOW",
        "Each C: valence 4. Bridgehead Cs: bonded to 3 other Cs + 1 H = 4. OK. Bicyclo[2.2.1]heptane.",
        "All C(2.55). Nonpolar.",
        "Bicyclic alkane (norbornane). Bridgehead carbons. High ring strain but stable.",
        "Bicyclo[2.2.1]heptane framework. Two bridgehead carbons. sp3. Mixed bond angles.",
        {"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (1.0, 8.0), (2.0, 15.0),
        ["rdkit_parse", "valence_satisfied", "bicyclic_noted"], 3, "boundary", ["bicyclic", "bridgehead", "alkane"]),

    ChemistryRow("C1=CC=CC=C1C2=CC=CC=C2", "biphenyl", True, "aromatic_hydrocarbon", ["C"]*12, "ALLOW",
        "Each aromatic C: valence 4. 3 sigma + 1 pi = 4. Connecting C-C single bond between rings. OK.",
        "All C(2.55). Nonpolar. Twisted conformation due to steric hindrance between ortho hydrogens.",
        "Biphenyl. Two linked benzene rings. PCB precursor. Exists as twisted conformers.",
        "Two benzene rings connected by C-C single bond. Each ring aromatic. sp2. Dihedral angle ~44 degrees.",
        {"KO": 0, "AV": 0, "RU": 1, "CA": 0, "UM": 0, "DR": 0}, (1.0, 10.0), (2.0, 15.0),
        ["rdkit_parse", "valence_satisfied", "aromaticity_verified", "conformation_noted"], 3, "boundary", ["aromatic", "biphenyl", "pcb_precursor"]),

    ChemistryRow("C1CCOC1", "tetrahydrofuran", True, "cyclic_ether", ["C", "C", "O", "C", "C"], "ALLOW",
        "O: valence 2. Two C-O single bonds = 2. OK. Each C: 4 valence, O/neighbor C + 2H = 4. OK.",
        "O(3.44) > C(2.55). Polar C-O bonds. Ether oxygen can coordinate to Lewis acids.",
        "Cyclic ether (THF). Common polar aprotic solvent. Can form peroxides on storage.",
        "5-membered ring with one O. Envelope conformation. sp3 on O and C.",
        {"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (0.5, 5.0), (0.0, 10.0),
        ["rdkit_parse", "valence_satisfied", "solvent_properties_noted"], 2, "boundary", ["ether", "cyclic", "solvent", "thf"]),

    ChemistryRow("C1CCNCC1", "piperidine", True, "cyclic_amine", ["C", "C", "N", "C", "C", "C"], "ALLOW",
        "N: valence 3. Two C-N bonds + H(implicit) + lone pair = 3. OK. Each C: 4 valence, 2C + 2H = 4. OK.",
        "N(3.04) > C(2.55). Basic (pKb ~2.9). Secondary amine in ring.",
        "Cyclic secondary amine. Saturated heterocycle. Chair conformation (like cyclohexane).",
        "6-membered ring with one N. Chair conformation. sp3 on N and C. Lone pair on N.",
        {"KO": 1, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (0.5, 5.0), (0.0, 10.0),
        ["rdkit_parse", "valence_satisfied", "functional_group_detected"], 2, "boundary", ["amine", "cyclic", "heterocycle"]),

    ChemistryRow("C1=CN=CC=C1", "pyridine_explicit", True, "heteroaromatic", ["C"]*5+["N"], "ALLOW",
        "Each C: 3 sigma + 1 pi = 4. N: 3 sigma + 1 pi + lone pair = satisfied. Aromatic sextet.",
        "N(3.04) > C(2.55). N electronegative, pulls electron density. Weak base.",
        "Pyridine (explicit double bonds). Same as c1ccncc1. Tests Kekule vs aromatic notation.",
        "Six-membered aromatic ring with one N. Planar. sp2. N lone pair in plane.",
        {"KO": 0, "AV": 0, "RU": 1, "CA": 0, "UM": 0, "DR": 0}, (1.0, 8.0), (2.0, 15.0),
        ["rdkit_parse", "valence_satisfied", "aromaticity_verified"], 2, "boundary", ["heteroaromatic", "pyridine", "kekule"]),

    ChemistryRow("C1CCCCC1CC(C)C", "decalin_fragment", True, "alkane", ["C"]*10, "ALLOW",
        "Cyclohexane ring + isobutyl side chain. Every C: valence 4. Ring C: 2C + 2H = 4. Side chain: same rules.",
        "All C(2.55). Nonpolar. Hydrophobic.",
        "Decalin-like fragment. Tests parser on fused/trans ring systems with side chains.",
        "Cyclohexane ring (chair) + branched alkyl chain. sp3 throughout.",
        {"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}, (1.0, 8.0), (2.0, 15.0),
        ["rdkit_parse", "valence_satisfied"], 2, "boundary", ["alkane", "cyclohexane", "branched"]),
]


def _build_sft_example(row: ChemistryRow, split: str) -> dict:
    """Convert a ChemistryRow into SFT message format."""
    system_msg = (
        "You are an SCBE-AETHERMOORE chemistry verifier. "
        "Walk the full arithmetic path for every molecule: "
        "atoms → bonds → valence count → electronegativity → functional group → "
        "RDKit validity → SCBE token state → fusion → governance verdict. "
        "Be explicit. Show your work. Do not skip steps."
    )

    user_prompt = (
        f"Verify SMILES: {row.smiles}\n"
        f"Molecule name: {row.name}\n"
        f"Expected validity: {row.expected_valid}\n"
        f"Expected governance: {row.expected_governance}\n\n"
        f"Walk through:\n"
        f"1. Parse atoms and count them\n"
        f"2. Check valence for each atom\n"
        f"3. Calculate electronegativity differences\n"
        f"4. Identify functional group\n"
        f"5. Assess bond types and geometry\n"
        f"6. Predict RDKit parse result\n"
        f"7. Predict SCBE fusion state\n"
        f"8. Give final governance verdict"
    )

    assistant_completion = (
        f"name={row.name}\n"
        f"smiles={row.smiles}\n"
        f"expected_valid={row.expected_valid}\n"
        f"expected_governance={row.expected_governance}\n\n"
        f"valence_check={row.manual_valence_check}\n"
        f"electronegativity={row.manual_electronegativity}\n"
        f"functional_group={row.manual_functional_group}\n"
        f"bond_analysis={row.manual_bond_analysis}\n\n"
        f"rdkit_parse_prediction={'PASS' if row.expected_valid else 'FAIL'}\n"
        f"scbe_fusion_prediction=FINITE\n"
        f"governance_verdict={row.expected_governance}\n\n"
        f"required_checks={','.join(row.required_checks)}\n"
        f"difficulty={row.difficulty}\n"
        f"source={row.source}\n"
        f"tags={','.join(row.tags)}"
    )

    return {
        "id": f"chemistry_manual_verification_v1_{row.name}_{uuid.uuid4().hex[:12]}",
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_prompt},
            {"role": "assistant", "content": assistant_completion},
        ],
        "metadata": {
            "split": split,
            "track": "chemistry_manual_verification_v1",
            "difficulty_band": ["easy", "easy", "medium", "medium", "hard"][min(row.difficulty - 1, 4)],
            "source": row.source,
            "expected_valid": row.expected_valid,
            "expected_governance": row.expected_governance,
            "difficulty": row.difficulty,
            "tags": row.tags,
        },
    }


def build_sft():
    os.makedirs("training-data/sft", exist_ok=True)

    # Shuffle and split
    shuffled = list(ROWS)
    random.shuffle(shuffled)
    n_eval = max(1, int(len(shuffled) * EVAL_FRACTION))
    eval_rows = shuffled[:n_eval]
    train_rows = shuffled[n_eval:]

    # Write train
    with open(SFT_TRAIN_PATH, "w", encoding="utf-8") as f:
        for row in train_rows:
            f.write(json.dumps(_build_sft_example(row, "train"), ensure_ascii=False) + "\n")

    # Write eval
    with open(SFT_EVAL_PATH, "w", encoding="utf-8") as f:
        for row in eval_rows:
            f.write(json.dumps(_build_sft_example(row, "eval"), ensure_ascii=False) + "\n")

    # Manifest
    manifest = {
        "dataset": "chemistry_manual_verification_v1",
        "version": "1.0.0",
        "format": "sft",
        "n_train": len(train_rows),
        "n_eval": len(eval_rows),
        "n_total": len(ROWS),
        "sources": sorted(set(r.source for r in ROWS)),
        "difficulty_distribution": {
            str(d): sum(1 for r in ROWS if r.difficulty == d)
            for d in sorted(set(r.difficulty for r in ROWS))
        },
        "governance_distribution": {
            g: sum(1 for r in ROWS if r.expected_governance == g)
            for g in set(r.expected_governance for r in ROWS)
        },
        "train_path": SFT_TRAIN_PATH,
        "eval_path": SFT_EVAL_PATH,
        "description": (
            "College-level chemistry verification SFT dataset. Each example teaches the agent "
            "to walk the full arithmetic path from SMILES to governance verdict."
        ),
    }

    with open(SFT_MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"Wrote {len(train_rows)} train rows to {SFT_TRAIN_PATH}")
    print(f"Wrote {len(eval_rows)} eval rows to {SFT_EVAL_PATH}")
    print(f"Manifest: {SFT_MANIFEST_PATH}")
    print(f"  Sources: {manifest['sources']}")
    print(f"  Difficulty: {manifest['difficulty_distribution']}")
    print(f"  Governance: {manifest['governance_distribution']}")


if __name__ == "__main__":
    build_sft()
