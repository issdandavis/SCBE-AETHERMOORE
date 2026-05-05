"""Generate expanded chemistry_manual_verification_v2 dataset (200 rows).

Auto-generates chemically accurate verification rows from known SMILES strings
using RDKit. Covers: basic, functional groups, drugs, aromatics, heterocycles,
amino acids, inorganic, organometallics, natural products, peptides, invalid.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List

from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_PATH = REPO_ROOT / "training-data" / "chemistry_manual_verification_v2.jsonl"
MANIFEST_PATH = REPO_ROOT / "training-data" / "chemistry_manual_verification_v2_manifest.json"

ELECTRONEGATIVITY = {
    "H": 2.20,
    "Li": 0.98,
    "Be": 1.57,
    "B": 2.04,
    "C": 2.55,
    "N": 3.04,
    "O": 3.44,
    "F": 3.98,
    "Na": 0.93,
    "Mg": 1.31,
    "Al": 1.61,
    "Si": 1.90,
    "P": 2.19,
    "S": 2.58,
    "Cl": 3.16,
    "K": 0.82,
    "Ca": 1.00,
    "Sc": 1.36,
    "Ti": 1.54,
    "V": 1.63,
    "Cr": 1.66,
    "Mn": 1.55,
    "Fe": 1.83,
    "Co": 1.88,
    "Ni": 1.91,
    "Cu": 1.90,
    "Zn": 1.65,
    "Ga": 1.81,
    "Ge": 2.01,
    "As": 2.18,
    "Se": 2.55,
    "Br": 2.96,
    "Rb": 0.82,
    "Sr": 0.95,
    "Ag": 1.93,
    "Cd": 1.69,
    "In": 1.78,
    "Sn": 1.96,
    "Sb": 2.05,
    "Te": 2.1,
    "I": 2.66,
    "Cs": 0.79,
    "Ba": 0.89,
    "Au": 2.54,
    "Hg": 2.00,
    "Pb": 2.33,
    "Bi": 2.02,
}

FUNCTIONAL_GROUP_SMARTS = {
    "alcohol": "[OX2H]",
    "aldehyde": "[CX3H1](=O)[#6]",
    "ketone": "[#6][CX3](=O)[#6]",
    "carboxylic_acid": "[CX3](=O)[OX2H1]",
    "ester": "[#6][CX3](=O)[OX2H0][#6]",
    "amide": "[NX3][CX3](=[OX1])[#6]",
    "amine": "[NX3;H2,H1;!$(NC=O)]",
    "nitro": "[NX3](=O)=O",
    "ether": "[OD2]([#6])[#6]",
    "alkene": "[CX3]=[CX3]",
    "alkyne": "[CX2]#[CX2]",
    "aromatic": "c",
    "sulfide": "[#16X2H0]",
    "thiol": "[SX2H]",
    "halide": "[F,Cl,Br,I]",
    "phenol": "[OX2H]c",
}


@dataclass
class ChemistryVerificationRow:
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


# ---------------------------------------------------------------------------
# Seed molecules (SMILES, name, family, difficulty, source, tags)
# ---------------------------------------------------------------------------

SEED_MOLECULES: List[tuple[str, str, str, int, str, List[str]]] = [
    # Basic / inorganic
    ("O", "water", "oxide", 1, "basic", ["simple", "inorganic", "polar"]),
    ("C", "methane", "alkane", 1, "basic", ["simple", "alkane", "nonpolar"]),
    ("CCO", "ethanol", "alcohol", 1, "basic", ["alcohol", "organic", "polar"]),
    ("O=C=O", "carbon_dioxide", "acid_anhydride", 1, "basic", ["inorganic", "linear", "nonpolar"]),
    ("N", "ammonia", "amine_precursor", 1, "basic", ["simple", "base", "polar"]),
    ("[Na+]", "sodium_ion", "cation", 1, "inorganic", ["ionic", "metal"]),
    ("[Cl-]", "chloride_ion", "anion", 1, "inorganic", ["ionic", "halide"]),
    ("[Na+].[Cl-]", "sodium_chloride", "salt", 1, "inorganic", ["ionic", "salt"]),
    ("[Ca+2]", "calcium_ion", "cation", 1, "inorganic", ["ionic", "metal"]),
    ("[OH-]", "hydroxide", "anion", 1, "inorganic", ["ionic", "base"]),
    ("[H+]", "proton", "cation", 1, "inorganic", ["ionic", "acid"]),
    ("[NH4+]", "ammonium", "cation", 1, "inorganic", ["ionic", "base"]),
    ("[OH3+]", "hydronium", "cation", 2, "inorganic", ["ionic", "acid"]),
    ("O=S(=O)=O", "sulfur_trioxide", "acid_anhydride", 2, "inorganic", ["oxide", "acidic"]),
    ("[Fe+2]", "iron_ii", "cation", 1, "inorganic", ["ionic", "metal", "transition"]),
    ("[Fe+3]", "iron_iii", "cation", 1, "inorganic", ["ionic", "metal", "transition"]),
    ("[Cu+2]", "copper_ii", "cation", 1, "inorganic", ["ionic", "metal", "transition"]),
    ("[Zn+2]", "zinc_ion", "cation", 1, "inorganic", ["ionic", "metal", "transition"]),
    ("[Mg+2]", "magnesium_ion", "cation", 1, "inorganic", ["ionic", "metal"]),
    ("[K+]", "potassium_ion", "cation", 1, "inorganic", ["ionic", "metal", "alkali"]),
    # Alkanes
    ("CC", "ethane", "alkane", 1, "basic", ["alkane", "nonpolar"]),
    ("CCC", "propane", "alkane", 1, "basic", ["alkane", "nonpolar"]),
    ("CCCC", "butane", "alkane", 1, "basic", ["alkane", "nonpolar"]),
    ("CC(C)C", "isobutane", "alkane", 1, "basic", ["alkane", "branched", "nonpolar"]),
    ("CC(C)(C)C", "neopentane", "alkane", 1, "basic", ["alkane", "branched", "nonpolar"]),
    ("CCCCCC", "hexane", "alkane", 1, "basic", ["alkane", "nonpolar"]),
    ("CCCCCCCC", "octane", "alkane", 1, "basic", ["alkane", "nonpolar"]),
    ("C1CCCCC1", "cyclohexane", "alkane", 2, "basic", ["alkane", "cyclic", "nonpolar"]),
    ("C1CC1", "cyclopropane", "alkane", 2, "basic", ["alkane", "cyclic", "strained"]),
    ("C1CCC1", "cyclobutane", "alkane", 2, "basic", ["alkane", "cyclic"]),
    # Alkenes / alkynes
    ("C=C", "ethene", "alkene", 1, "basic", ["alkene", "nonpolar"]),
    ("CC=C", "propene", "alkene", 1, "basic", ["alkene", "nonpolar"]),
    ("C=CC=C", "butadiene", "alkene", 2, "basic", ["alkene", "conjugated"]),
    ("C#C", "acetylene", "alkyne", 1, "basic", ["alkyne", "nonpolar"]),
    ("CC#C", "propyne", "alkyne", 1, "basic", ["alkyne", "nonpolar"]),
    ("C1=CC=CC=C1", "benzene", "aromatic", 2, "aromatic", ["aromatic", "cyclic"]),
    ("Cc1ccccc1", "toluene", "aromatic", 2, "aromatic", ["aromatic", "substituted"]),
    ("c1ccccc1O", "phenol", "aromatic", 2, "aromatic", ["aromatic", "alcohol", "phenol"]),
    ("c1ccc(cc1)C(=O)O", "benzoic_acid", "aromatic", 2, "aromatic", ["aromatic", "acid"]),
    ("c1ccc(cc1)N", "aniline", "aromatic", 2, "aromatic", ["aromatic", "amine"]),
    ("Oc1ccccc1O", "catechol", "aromatic", 3, "aromatic", ["aromatic", "diol", "phenol"]),
    ("c1ccc2c(c1)ccc2", "naphthalene", "aromatic", 3, "aromatic", ["aromatic", "polycyclic"]),
    ("c1ccc2ccccc2c1", "anthracene", "aromatic", 3, "aromatic", ["aromatic", "polycyclic"]),
    ("c1ccc(cc1)C(=O)c2ccccc2", "benzophenone", "aromatic", 3, "aromatic", ["aromatic", "ketone"]),
    # Functional groups
    ("CC(=O)O", "acetic_acid", "carboxylic_acid", 2, "functional_group", ["acid", "organic"]),
    ("CC(=O)OC", "methyl_acetate", "ester", 2, "functional_group", ["ester", "organic"]),
    ("CC(=O)N(C)C", "dimethylacetamide", "amide", 2, "functional_group", ["amide", "organic"]),
    ("CC(=O)C", "acetone", "ketone", 1, "functional_group", ["ketone", "organic"]),
    ("CC=O", "acetaldehyde", "aldehyde", 1, "functional_group", ["aldehyde", "organic"]),
    ("CCN", "ethylamine", "amine", 1, "functional_group", ["amine", "organic", "base"]),
    ("CC(C)N", "isopropylamine", "amine", 1, "functional_group", ["amine", "organic"]),
    ("CC(C)(C)N", "tert_butylamine", "amine", 2, "functional_group", ["amine", "organic"]),
    ("CCOC", "dimethyl_ether", "ether", 1, "functional_group", ["ether", "organic"]),
    ("CCS", "ethanethiol", "thiol", 2, "functional_group", ["thiol", "organic"]),
    ("CC(C)(C)S", "tert_butylthiol", "thiol", 2, "functional_group", ["thiol", "organic"]),
    ("C[N+](=O)[O-]", "nitromethane", "nitro", 2, "functional_group", ["nitro", "organic"]),
    ("CO", "methanol", "alcohol", 1, "functional_group", ["alcohol", "organic"]),
    ("CC(C)O", "isopropanol", "alcohol", 1, "functional_group", ["alcohol", "organic"]),
    ("CC(C)(C)O", "tert_butanol", "alcohol", 2, "functional_group", ["alcohol", "organic"]),
    ("C1CCOC1", "tetrahydrofuran", "ether", 2, "functional_group", ["ether", "cyclic", "organic"]),
    ("C1COCCO1", "dioxane", "ether", 2, "functional_group", ["ether", "cyclic", "organic"]),
    ("CC(=O)Nc1ccc(cc1)O", "paracetamol", "amide", 2, "drug", ["drug", "analgesic", "phenol"]),
    ("CC(C)Cc1ccc(cc1)C(C)C(=O)O", "ibuprofen", "carboxylic_acid", 3, "drug", ["drug", "NSAID"]),
    ("COc1ccccc1O", "guaiacol", "ether", 2, "natural_product", ["natural", "phenol", "ether"]),
    # Amino acids (simplified, zwitterionic forms omitted for RDKit compatibility)
    ("NCC(=O)O", "glycine", "amino_acid", 2, "amino_acid", ["amino_acid", "simple"]),
    ("CC(N)C(=O)O", "alanine", "amino_acid", 2, "amino_acid", ["amino_acid"]),
    ("CC(C)C(N)C(=O)O", "valine", "amino_acid", 2, "amino_acid", ["amino_acid", "branched"]),
    ("CC(C)CC(N)C(=O)O", "leucine", "amino_acid", 2, "amino_acid", ["amino_acid", "branched"]),
    ("CCC(C)C(N)C(=O)O", "isoleucine", "amino_acid", 2, "amino_acid", ["amino_acid", "branched"]),
    ("NC(Cc1ccccc1)C(=O)O", "phenylalanine", "amino_acid", 3, "amino_acid", ["amino_acid", "aromatic"]),
    ("NC(CO)C(=O)O", "serine", "amino_acid", 2, "amino_acid", ["amino_acid", "hydroxyl"]),
    ("NC(CC(=O)O)C(=O)O", "aspartic_acid", "amino_acid", 3, "amino_acid", ["amino_acid", "acidic"]),
    ("NC(CCC(=O)O)C(=O)O", "glutamic_acid", "amino_acid", 3, "amino_acid", ["amino_acid", "acidic"]),
    ("NC(Cc1c[nH]c2ccccc12)C(=O)O", "tryptophan", "amino_acid", 4, "amino_acid", ["amino_acid", "aromatic", "indole"]),
    ("NC(Cc1ccc(O)cc1)C(=O)O", "tyrosine", "amino_acid", 3, "amino_acid", ["amino_acid", "phenol"]),
    ("NC(CS)C(=O)O", "cysteine", "amino_acid", 2, "amino_acid", ["amino_acid", "thiol"]),
    # Peptides (small)
    ("NCC(=O)NCC(=O)O", "glycyl_glycine", "peptide", 3, "peptide", ["peptide", "dipeptide"]),
    ("CC(NC(=O)CN)C(=O)O", "alanyl_glycine", "peptide", 3, "peptide", ["peptide", "dipeptide"]),
    (
        "NCC(=O)NC(Cc1ccccc1)C(=O)O",
        "glycyl_phenylalanine",
        "peptide",
        4,
        "peptide",
        ["peptide", "dipeptide", "aromatic"],
    ),
    ("CC(NC(=O)CNC(=O)C(C)N)C(=O)O", "alanyl_glycyl_alanine", "peptide", 4, "peptide", ["peptide", "tripeptide"]),
    # Drugs / natural products
    ("CC(=O)Oc1ccccc1C(=O)O", "aspirin", "ester", 3, "drug", ["drug", "NSAID", "salicylate"]),
    ("CN1C=NC2=C1C(=O)N(C(=O)N2C)C", "caffeine", "purine", 3, "drug", ["drug", "stimulant", "alkaloid"]),
    ("c1ccc2c(c1)c(c[nH]2)CCN", "tryptamine", "indole", 3, "natural_product", ["natural", "indole", "amine"]),
    ("CN1CCC2=C(C1)c1ccccc1N2", "harmane", "indole", 3, "natural_product", ["natural", "indole", "alkaloid"]),
    ("C1CCN(CC1)C(=O)O", "piperidine_carbamate", "carbamate", 3, "drug", ["drug", "cyclic"]),
    ("CN(C)CCCN1c2ccccc2CCc3ccccc31", "imipramine", "amine", 4, "drug", ["drug", "tricyclic", "antidepressant"]),
    ("CN1C2CCC1CC(C2)OC(=O)C(Cc3ccccc3)N", "atropine", "ester", 4, "drug", ["drug", "alkaloid", "tropane"]),
    ("CC(=O)Nc1ccc(cc1)O", "paracetamol_2", "amide", 2, "drug", ["drug", "analgesic"]),
    ("CCCCc1ccc(CC(=O)O)cc1", "ibuprofen_precursor", "carboxylic_acid", 3, "drug", ["drug", "NSAID"]),
    ("c1ccc(cc1)C(=O)O", "benzoic_acid_2", "carboxylic_acid", 2, "drug", ["preservative", "acid"]),
    # Heterocycles
    ("c1ccncc1", "pyridine", "heterocycle", 2, "heterocycle", ["aromatic", "heterocycle", "base"]),
    ("c1cccnc1", "pyridine_2", "heterocycle", 2, "heterocycle", ["aromatic", "heterocycle"]),
    ("c1coc(c1)", "furan", "heterocycle", 2, "heterocycle", ["aromatic", "heterocycle", "five_membered"]),
    ("c1csc(c1)", "thiophene", "heterocycle", 2, "heterocycle", ["aromatic", "heterocycle", "sulfur"]),
    ("c1c[nH]cn1", "imidazole", "heterocycle", 2, "heterocycle", ["aromatic", "heterocycle", "base"]),
    ("c1cncnc1", "pyrimidine", "heterocycle", 2, "heterocycle", ["aromatic", "heterocycle", "base"]),
    ("c1cnccn1", "pyrazine", "heterocycle", 2, "heterocycle", ["aromatic", "heterocycle"]),
    ("c1ccc2[nH]ccc2c1", "indole", "heterocycle", 3, "heterocycle", ["aromatic", "heterocycle", "indole"]),
    (
        "c1ccc2c(c1)[nH]c1ccccc12",
        "carbazole",
        "heterocycle",
        3,
        "heterocycle",
        ["aromatic", "heterocycle", "polycyclic"],
    ),
    ("C1=CC=NC=C1", "pyridine_aliphatic", "heterocycle", 2, "heterocycle", ["heterocycle"]),
    ("C1CCNC1", "pyrrolidine", "heterocycle", 2, "heterocycle", ["cyclic", "amine", "saturated"]),
    ("C1CCNCC1", "piperidine", "heterocycle", 2, "heterocycle", ["cyclic", "amine", "saturated"]),
    ("C1CNCCN1", "piperazine", "heterocycle", 2, "heterocycle", ["cyclic", "amine", "saturated"]),
    ("c1ccc2ncccc2c1", "quinoline", "heterocycle", 3, "heterocycle", ["aromatic", "heterocycle", "polycyclic"]),
    ("c1ccc2cnccc2c1", "isoquinoline", "heterocycle", 3, "heterocycle", ["aromatic", "heterocycle", "polycyclic"]),
    # Organometallics / coordination
    ("[Fe]", "iron_atom", "metal", 2, "organometallic", ["metal", "transition"]),
    ("[Fe+2]", "ferrous_ion", "metal", 1, "organometallic", ["metal", "ionic"]),
    ("[Fe+3]", "ferric_ion", "metal", 1, "organometallic", ["metal", "ionic"]),
    ("[Cu]", "copper_atom", "metal", 2, "organometallic", ["metal", "transition"]),
    ("[Zn]", "zinc_atom", "metal", 2, "organometallic", ["metal", "transition"]),
    ("[Pt]", "platinum_atom", "metal", 2, "organometallic", ["metal", "transition", "catalyst"]),
    ("[Au]", "gold_atom", "metal", 2, "organometallic", ["metal", "transition", "noble"]),
    ("[Hg]", "mercury_atom", "metal", 2, "organometallic", ["metal", "transition", "liquid"]),
    ("[Ti]", "titanium_atom", "metal", 2, "organometallic", ["metal", "transition"]),
    ("[Ni]", "nickel_atom", "metal", 2, "organometallic", ["metal", "transition", "catalyst"]),
    # Complex / stress tests
    ("C1CC1CC1CC1", "bicyclobutane_like", "alkane", 4, "stress_test", ["cyclic", "strained", "polycyclic"]),
    ("C1CC2CCC1C2", "norbornane", "alkane", 4, "stress_test", ["cyclic", "strained", "polycyclic"]),
    ("C1CC2CCC1C2", "norbornane", "alkane", 4, "stress_test", ["cyclic", "strained", "polycyclic"]),
    ("C1CC2CC1C2", "norbornane", "alkane", 4, "stress_test", ["cyclic", "strained", "polycyclic"]),
    ("C1CC2CCC1C2", "adamantane", "alkane", 4, "stress_test", ["cyclic", "polycyclic", "cage"]),
    ("C12C3C4C1C5C2C3C45", "cubane", "alkane", 5, "stress_test", ["cyclic", "strained", "cage"]),
    ("C1=CC=CC=C1C2=CC=CC=C2", "biphenyl", "aromatic", 3, "stress_test", ["aromatic", "polycyclic"]),
    ("c1ccc(cc1)c2ccccc2", "biphenyl_2", "aromatic", 3, "stress_test", ["aromatic", "polycyclic"]),
    ("C1=CC=C(C=C1)C(=O)O", "benzoic_acid_3", "carboxylic_acid", 2, "stress_test", ["aromatic", "acid"]),
    ("CC(C)C1CCC(C(C)C)CC1O", "menthol", "alcohol", 4, "natural_product", ["natural", "terpene", "cyclic"]),
    ("CC1=CC=C(C=C1)C(C)C", "p_cymene", "aromatic", 3, "natural_product", ["natural", "terpene", "aromatic"]),
    ("CC1=C(C(CCC1)(C)C)C=O", "beta_irone", "aldehyde", 4, "natural_product", ["natural", "terpene", "aromatic"]),
    ("CC(C)=CCC/C(C)=C/CO", "geraniol", "alcohol", 3, "natural_product", ["natural", "terpene", "alcohol"]),
    ("CC1=C2C(=CC=C1)C=CC2=O", "naphthoquinone", "ketone", 4, "natural_product", ["natural", "quinone", "aromatic"]),
    ("c1ccc(cc1)C(=O)c2ccccc2", "benzophenone_2", "ketone", 3, "stress_test", ["aromatic", "ketone"]),
    ("c1ccc(cc1)C(=O)Nc2ccccc2", "benzanilide", "amide", 3, "stress_test", ["aromatic", "amide"]),
    (
        "CCOC(=O)C(C)NP(=O)(Oc1ccccc1)Oc2ccccc2",
        "sarin_precursor",
        "organophosphate",
        5,
        "stress_test",
        ["toxic", "phosphate", "nerve_agent"],
    ),
    ("CC(C)OP(=O)(F)OC(C)C", "sarin", "organophosphate", 5, "stress_test", ["toxic", "phosphate", "nerve_agent"]),
    ("CN1C=NC2=C1C(=O)N(C(=O)N2C)C", "caffeine_2", "purine", 3, "drug", ["drug", "stimulant"]),
    ("C1=CC=C(C=C1)CC(C(=O)O)N", "phenylalanine_simplified", "amino_acid", 3, "amino_acid", ["amino_acid", "aromatic"]),
    ("C1CC(=O)N(C1)CC(=O)O", "oxoproline_glycine", "peptide", 4, "peptide", ["peptide", "cyclic"]),
    ("C1CC(=O)NC1", "pyrrolidone", "lactam", 3, "stress_test", ["cyclic", "amide", "lactam"]),
    # Invalid / boundary
    ("C(C)(C)(C)(C)(C)", "invalid_carbon_valence", "invalid", 1, "boundary", ["invalid", "valence"]),
    ("O=O=O", "invalid_ozone_like", "invalid", 2, "boundary", ["invalid", "valence"]),
    ("[C+5]", "invalid_carbon_charge", "invalid", 1, "boundary", ["invalid", "charge"]),
    ("", "empty_string", "invalid", 1, "boundary", ["invalid", "empty"]),
    ("   ", "whitespace_only", "invalid", 1, "boundary", ["invalid", "empty"]),
    ("not_a_smiles", "garbage_text", "invalid", 1, "boundary", ["invalid", "garbage"]),
    ("C1CC", "unclosed_ring", "invalid", 2, "boundary", ["invalid", "ring"]),
    ("C1CCCCC", "unclosed_ring_2", "invalid", 2, "boundary", ["invalid", "ring"]),
    ("C#C#C", "invalid_cumulene", "invalid", 2, "boundary", ["invalid", "bond"]),
    ("[Na].[Cl]", "invalid_ion_pair", "invalid", 2, "boundary", ["invalid", "ionic"]),
    # More alkanes / cyclic
    ("CCCCCCC", "heptane", "alkane", 1, "basic", ["alkane", "nonpolar"]),
    ("CCCCCCCCCC", "decane", "alkane", 1, "basic", ["alkane", "nonpolar"]),
    ("C1CCCC1", "cyclopentane", "alkane", 2, "basic", ["alkane", "cyclic"]),
    ("C1CCCCCC1", "cycloheptane", "alkane", 2, "basic", ["alkane", "cyclic"]),
    ("C1CCCCCCC1", "cyclooctane", "alkane", 2, "basic", ["alkane", "cyclic"]),
    # More alkenes
    ("C=CC", "propene_2", "alkene", 1, "basic", ["alkene", "nonpolar"]),
    ("C/C=C/C", "trans_2_butene", "alkene", 2, "basic", ["alkene", "nonpolar"]),
    ("CC=CC", "cis_2_butene", "alkene", 2, "basic", ["alkene", "nonpolar"]),
    ("C1=CC=C(C=C1)C=C", "styrene", "aromatic", 3, "aromatic", ["aromatic", "alkene"]),
    # More functional groups
    ("CCCC(=O)O", "butyric_acid", "carboxylic_acid", 2, "functional_group", ["acid", "organic"]),
    ("CCCCC(=O)O", "valeric_acid", "carboxylic_acid", 2, "functional_group", ["acid", "organic"]),
    ("CC(=O)OC(C)C", "isopropyl_acetate", "ester", 2, "functional_group", ["ester", "organic"]),
    ("CC(=O)OCC", "ethyl_acetate", "ester", 2, "functional_group", ["ester", "organic"]),
    ("CC(=O)NC", "methylacetamide", "amide", 2, "functional_group", ["amide", "organic"]),
    ("CC(C)C=O", "isobutyraldehyde", "aldehyde", 2, "functional_group", ["aldehyde", "organic"]),
    ("CC(C)C(=O)O", "isobutyric_acid", "carboxylic_acid", 2, "functional_group", ["acid", "organic"]),
    ("CCCC=O", "butyraldehyde", "aldehyde", 2, "functional_group", ["aldehyde", "organic"]),
    ("CCOCC", "diethyl_ether", "ether", 1, "functional_group", ["ether", "organic"]),
    ("CC(C)OC(C)C", "diisopropyl_ether", "ether", 2, "functional_group", ["ether", "organic"]),
    ("c1ccc(cc1)C=O", "benzaldehyde", "aromatic", 2, "aromatic", ["aromatic", "aldehyde"]),
    ("c1ccc(cc1)CO", "benzyl_alcohol", "aromatic", 2, "aromatic", ["aromatic", "alcohol"]),
    ("c1ccc(cc1)OC", "anisole", "aromatic", 2, "aromatic", ["aromatic", "ether"]),
    ("c1ccc(cc1)C(=O)OC", "methyl_benzoate", "aromatic", 2, "aromatic", ["aromatic", "ester"]),
    ("c1ccc(cc1)C(=O)N", "benzamide", "aromatic", 2, "aromatic", ["aromatic", "amide"]),
    ("c1ccc(cc1)C#N", "benzonitrile", "aromatic", 2, "aromatic", ["aromatic", "nitrile"]),
    ("N#C", "hydrogen_cyanide", "nitrile", 2, "functional_group", ["toxic", "nitrile"]),
    ("CC#N", "acetonitrile", "nitrile", 2, "functional_group", ["organic", "nitrile"]),
    # More amino acids
    ("NC(CC1=CC=CC=C1)C(=O)O", "phenylalanine_2", "amino_acid", 3, "amino_acid", ["amino_acid", "aromatic"]),
    ("NC(Cc1c[nH]c2ccccc12)C(=O)O", "tryptophan_2", "amino_acid", 4, "amino_acid", ["amino_acid", "indole"]),
    ("NC(CCCCN)C(=O)O", "lysine", "amino_acid", 3, "amino_acid", ["amino_acid", "basic"]),
    ("NC(CC(=O)N)C(=O)O", "asparagine", "amino_acid", 3, "amino_acid", ["amino_acid", "amide"]),
    ("NC(CC(=O)O)C(=O)O", "aspartic_acid_2", "amino_acid", 3, "amino_acid", ["amino_acid", "acidic"]),
    ("NC(CCC(=O)O)C(=O)O", "glutamic_acid_2", "amino_acid", 3, "amino_acid", ["amino_acid", "acidic"]),
    ("NC(CS)C(=O)O", "cysteine_2", "amino_acid", 2, "amino_acid", ["amino_acid", "thiol"]),
    ("NC(CC1=CNC2=CC=CC=C12)C(=O)O", "tryptophan_3", "amino_acid", 4, "amino_acid", ["amino_acid", "indole"]),
    # More drugs / natural products
    ("CC12CCC3C(C1CCC2O)CCC4=CC(=O)CCC34C", "testosterone", "steroid", 5, "drug", ["drug", "steroid", "hormone"]),
    (
        "CC(C)CCCC(C)C1CCC2C1(CCC3C2CC=C4C3(CCC(C4)O)C)C",
        "cholesterol",
        "sterol",
        5,
        "natural_product",
        ["natural", "sterol", "lipid"],
    ),
    ("CC(=O)Oc1ccccc1C(=O)O", "aspirin_2", "ester", 3, "drug", ["drug", "NSAID"]),
    ("CN1C=NC2=C1C(=O)N(C(=O)N2C)C", "caffeine_3", "purine", 3, "drug", ["drug", "stimulant"]),
    ("C1=CC=C(C=C1)C(=O)O", "benzoic_acid_4", "carboxylic_acid", 2, "drug", ["preservative"]),
    ("CC1=CC=C(C=C1)C(C)C", "p_cymene_2", "aromatic", 3, "natural_product", ["natural", "terpene"]),
    (
        "CC(C)=CCC/C(C)=C/COP(=O)(O)OP(=O)(O)O",
        "geranyl_pyrophosphate",
        "organophosphate",
        5,
        "natural_product",
        ["natural", "terpene", "phosphate"],
    ),
    # More inorganics / acids
    ("O=S(=O)(O)O", "sulfuric_acid", "inorganic_acid", 2, "inorganic", ["acid", "strong", "inorganic"]),
    ("O=[N+]([O-])O", "nitric_acid", "inorganic_acid", 2, "inorganic", ["acid", "strong", "inorganic"]),
    ("O=P(O)(O)O", "phosphoric_acid", "inorganic_acid", 2, "inorganic", ["acid", "inorganic"]),
    ("O=C(O)C(=O)O", "oxalic_acid", "dicarboxylic_acid", 2, "inorganic", ["acid", "organic"]),
    ("O=C(O)CC(=O)O", "malonic_acid", "dicarboxylic_acid", 2, "inorganic", ["acid", "organic"]),
    ("O=C(O)CCC(=O)O", "succinic_acid", "dicarboxylic_acid", 2, "inorganic", ["acid", "organic"]),
    ("[Na+].[OH-]", "sodium_hydroxide", "salt", 1, "inorganic", ["base", "ionic", "salt"]),
    ("[Ca+2].[Cl-].[Cl-]", "calcium_chloride", "salt", 1, "inorganic", ["salt", "ionic"]),
    ("[Mg+2].[O-2]", "magnesium_oxide", "salt", 1, "inorganic", ["oxide", "ionic"]),
    ("[Al+3].[Cl-].[Cl-].[Cl-]", "aluminum_chloride", "salt", 2, "inorganic", ["salt", "ionic", "lewis_acid"]),
    # More heterocycles
    ("c1ccc2[nH]ccc2c1", "indole_2", "heterocycle", 3, "heterocycle", ["aromatic", "heterocycle", "indole"]),
    ("c1c[nH]cn1", "imidazole_2", "heterocycle", 2, "heterocycle", ["aromatic", "heterocycle", "base"]),
    ("c1cncnc1", "pyrimidine_2", "heterocycle", 2, "heterocycle", ["aromatic", "heterocycle"]),
    ("c1cnccn1", "pyrazine_2", "heterocycle", 2, "heterocycle", ["aromatic", "heterocycle"]),
    ("c1ccc2ncccc2c1", "quinoline_2", "heterocycle", 3, "heterocycle", ["aromatic", "heterocycle", "polycyclic"]),
    ("c1ccc2cnccc2c1", "isoquinoline_2", "heterocycle", 3, "heterocycle", ["aromatic", "heterocycle", "polycyclic"]),
    ("C1=CN=CC=N1", "pyrazine_aliphatic", "heterocycle", 2, "heterocycle", ["heterocycle"]),
    ("C1=CN=CN=C1", "pyrimidine_aliphatic", "heterocycle", 2, "heterocycle", ["heterocycle"]),
    ("c1ccc2[nH]cnc2c1", "benzimidazole", "heterocycle", 3, "heterocycle", ["aromatic", "heterocycle", "fused"]),
    ("c1ccc2occc2c1", "benzofuran", "heterocycle", 3, "heterocycle", ["aromatic", "heterocycle", "fused"]),
    (
        "c1ccc2sccc2c1",
        "benzothiophene",
        "heterocycle",
        3,
        "heterocycle",
        ["aromatic", "heterocycle", "fused", "sulfur"],
    ),
    # More stress / complex
    ("C1=CC=C2C(=C1)C3=CC=CC=C3C2", "fluorene", "aromatic", 4, "stress_test", ["aromatic", "polycyclic"]),
    ("c1ccc2cc3ccccc3cc2c1", "phenanthrene", "aromatic", 4, "stress_test", ["aromatic", "polycyclic"]),
    ("c1ccc2c(c1)c3cccc3c2", "acenaphthylene", "aromatic", 4, "stress_test", ["aromatic", "polycyclic"]),
    ("c1ccc2cc3c(ccc4ccccc43)cc2c1", "chrysene", "aromatic", 5, "stress_test", ["aromatic", "polycyclic"]),
    ("CC1=C2C(=CC=C1)C=CC2=O", "naphthoquinone_2", "ketone", 4, "natural_product", ["natural", "quinone"]),
    ("c1ccc(cc1)C(=O)c2ccccc2", "benzophenone_3", "ketone", 3, "stress_test", ["aromatic", "ketone"]),
    ("c1ccc(cc1)C(=O)Nc2ccccc2", "benzanilide_2", "amide", 3, "stress_test", ["aromatic", "amide"]),
    # More invalid / boundary
    ("C(C)(C)(C)(C)(C)C", "invalid_hypervalent", "invalid", 2, "boundary", ["invalid", "valence"]),
    ("F(F)(F)(F)(F)(F)(F)", "invalid_heptafluorine", "invalid", 2, "boundary", ["invalid", "valence"]),
    ("[H]1.[H]1", "invalid_bond_closure", "invalid", 2, "boundary", ["invalid", "syntax"]),
    ("C%00", "invalid_ring_high", "invalid", 2, "boundary", ["invalid", "ring"]),
    ("C1CC1C1CC1C1CC", "invalid_ring_stress", "invalid", 3, "boundary", ["invalid", "ring", "stress"]),
    ("C1CC1C1CC1C1CC1C1CC", "invalid_extreme_rings", "invalid", 4, "boundary", ["invalid", "ring", "stress"]),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _detect_functional_groups(mol: Chem.Mol) -> List[str]:
    groups = []
    for name, smarts in FUNCTIONAL_GROUP_SMARTS.items():
        patt = Chem.MolFromSmarts(smarts)
        if patt and mol.HasSubstructMatch(patt):
            groups.append(name)
    return groups


def _explicit_valence(atom: Chem.Atom) -> int:
    try:
        return int(atom.GetValence(Chem.ValenceType.EXPLICIT))
    except Exception:
        return int(atom.GetExplicitValence())


def _allowed_valence(atom: Chem.Atom) -> int | None:
    sym = atom.GetSymbol()
    charge = atom.GetFormalCharge()
    if sym == "N" and charge > 0:
        return 4
    if sym == "O" and charge > 0:
        return 3
    if sym == "O" and charge < 0:
        return 1
    if sym == "S":
        return 6
    if sym == "P":
        return 5
    return {
        "C": 4,
        "N": 3,
        "O": 2,
        "F": 1,
        "Cl": 1,
        "Br": 1,
        "I": 1,
        "B": 3,
        "Na": 0,
        "Mg": 0,
        "Al": 0,
        "Si": 4,
        "K": 0,
        "Ca": 0,
    }.get(sym)


def _valence_status(atom: Chem.Atom) -> tuple[bool, int, int | None, str]:
    if abs(atom.GetFormalCharge()) > 3:
        return False, 0, None, f"unrealistic formal charge {atom.GetFormalCharge():+d}"
    if atom.GetSymbol() == "H" and atom.IsInRing():
        return False, 0, None, "hydrogen ring closure is not promotable"
    val = _explicit_valence(atom)
    limit = _allowed_valence(atom)
    if limit is None:
        return True, val, limit, "transition/extended element not capped by this structural gate"
    if val <= limit:
        return True, val, limit, "within structural valence ceiling"
    return False, val, limit, "over structural valence ceiling"


def _mol_valence_ok(mol: Chem.Mol | None) -> bool:
    if mol is None or mol.GetNumAtoms() == 0:
        return False
    if _has_neutral_salt_fragment(mol):
        return False
    return all(_valence_status(atom)[0] for atom in mol.GetAtoms())


def _has_neutral_salt_fragment(mol: Chem.Mol) -> bool:
    has_neutral_metal = False
    has_neutral_halide = False
    for atom in mol.GetAtoms():
        sym = atom.GetSymbol()
        charge = atom.GetFormalCharge()
        if sym in {"Na", "K", "Mg", "Ca", "Al"} and charge == 0:
            has_neutral_metal = True
        if sym in {"F", "Cl", "Br", "I"} and charge == 0:
            has_neutral_halide = True
    return has_neutral_metal and has_neutral_halide


def _build_valence_text(mol: Chem.Mol, name: str) -> str:
    if mol is None:
        return "RDKit failed to parse SMILES. INVALID."
    if mol.GetNumAtoms() == 0:
        return f"{name}: RDKit parsed zero atoms. INVALID."
    if _has_neutral_salt_fragment(mol):
        return f"{name}: neutral metal/halide fragments must be encoded as ions. INVALID."
    lines = []
    for atom in mol.GetAtoms():
        sym = atom.GetSymbol()
        ok, val, limit, note = _valence_status(atom)
        charge = atom.GetFormalCharge()
        suffix = f", charge {charge:+d}" if charge else ""
        if not ok:
            limit_text = "uncapped" if limit is None else str(limit)
            lines.append(f"{sym}{atom.GetIdx()}: valence {val} > allowed {limit_text}{suffix}. INVALID ({note}).")
        elif limit is None:
            lines.append(f"{sym}{atom.GetIdx()}: valence {val}{suffix}. OK ({note}).")
        elif ok:
            lines.append(f"{sym}{atom.GetIdx()}: valence {val} <= allowed {limit}{suffix}. OK ({note}).")
    return " ".join(lines) if lines else f"{name}: no atoms parsed."


def _build_en_text(mol: Chem.Mol) -> str:
    if mol is None:
        return "Cannot compute electronegativity for invalid molecule."
    en_vals = []
    for atom in mol.GetAtoms():
        sym = atom.GetSymbol()
        if sym in ELECTRONEGATIVITY:
            en_vals.append((sym, ELECTRONEGATIVITY[sym]))
    if not en_vals:
        return "No recognized elements for EN analysis."
    en_vals.sort(key=lambda x: -x[1])
    highest = en_vals[0]
    lowest = en_vals[-1]
    delta = highest[1] - lowest[1]
    bond_type = "ionic" if delta > 1.7 else "polar covalent" if delta > 0.4 else "nonpolar covalent"
    return (
        f"Highest EN: {highest[0]} ({highest[1]}). Lowest: {lowest[0]} ({lowest[1]}). ΔEN = {delta:.2f}. {bond_type}."
    )


def _build_fg_text(mol: Chem.Mol) -> str:
    if mol is None:
        return "No functional groups (invalid molecule)."
    groups = _detect_functional_groups(mol)
    if not groups:
        return "No recognized functional groups. Likely hydrocarbon or inorganic."
    return f"Detected: {', '.join(groups)}."


def _build_bond_text(mol: Chem.Mol) -> str:
    if mol is None:
        return "No bonds (invalid molecule)."
    counts = {"SINGLE": 0, "DOUBLE": 0, "TRIPLE": 0, "AROMATIC": 0}
    for bond in mol.GetBonds():
        t = str(bond.GetBondType())
        counts[t] = counts.get(t, 0) + 1
    parts = [f"{k}={v}" for k, v in counts.items() if v]
    return f"Bond counts: {', '.join(parts)}."


def _elements(mol: Chem.Mol) -> List[str]:
    if mol is None:
        return []
    syms = sorted({a.GetSymbol() for a in mol.GetAtoms()})
    return syms


def _coherence_range(difficulty: int) -> tuple[float, float]:
    # Rough heuristic: harder molecules have wider ranges
    base = difficulty * 1.5
    return (0.0, base + 3.0)


def _valence_pressure_range(difficulty: int, valid: bool) -> tuple[float, float]:
    if not valid:
        return (20.0, 100.0)
    return (0.0, difficulty * 8.0 + 5.0)


def _governance(valid: bool) -> str:
    return "ALLOW" if valid else "DENY"


def _tau_hat_signs(family: str) -> Dict[str, int]:
    # Very rough heuristic mapping
    return {
        "KO": 1 if family in {"alcohol", "amine", "thiol", "phenol", "amide", "amino_acid", "peptide"} else 0,
        "AV": 1 if family in {"aromatic", "heterocycle", "indole"} else 0,
        "RU": 1 if family in {"salt", "ionic", "cation", "anion"} else 0,
        "CA": 1 if family in {"carboxylic_acid", "acid_anhydride", "amino_acid", "peptide"} else 0,
        "UM": 1 if family in {"metal", "organometallic", "transition"} else 0,
        "DR": 1 if family in {"drug", "natural_product", "alkaloid"} else 0,
    }


def _required_checks(difficulty: int, valid: bool) -> List[str]:
    base = ["rdkit_parse"]
    if valid:
        base.append("valence_satisfied")
    if difficulty >= 2:
        base.append("functional_group_detected")
    if difficulty >= 3:
        base.append("fusion_state_finite")
    return base


def generate_row(
    smiles: str, name: str, family: str, difficulty: int, source: str, tags: List[str]
) -> ChemistryVerificationRow:
    mol = Chem.MolFromSmiles(smiles)
    hydrogen_ring_boundary = "[H]" in smiles and any(ch.isdigit() for ch in smiles)
    valid = (
        mol is not None
        and mol.GetNumAtoms() > 0
        and family != "invalid"
        and not hydrogen_ring_boundary
        and _mol_valence_ok(mol)
    )
    elems = _elements(mol)
    return ChemistryVerificationRow(
        smiles=smiles,
        name=name,
        expected_valid=valid,
        expected_family=family,
        expected_elements=elems,
        expected_governance=_governance(valid),
        manual_valence_check=_build_valence_text(mol, name),
        manual_electronegativity=_build_en_text(mol),
        manual_functional_group=_build_fg_text(mol),
        manual_bond_analysis=_build_bond_text(mol),
        expected_tau_hat_signs=_tau_hat_signs(family),
        expected_coherence_range=_coherence_range(difficulty),
        expected_valence_pressure_range=_valence_pressure_range(difficulty, valid),
        required_checks=_required_checks(difficulty, valid),
        difficulty=difficulty,
        source=source,
        tags=tags,
    )


def main() -> None:
    rows: List[dict] = []
    for smiles, name, family, difficulty, source, tags in SEED_MOLECULES:
        try:
            row = generate_row(smiles, name, family, difficulty, source, tags)
            rows.append(asdict(row))
        except Exception as exc:
            print(f"SKIP {name}: {exc}")

    # Shuffle deterministically for reproducibility
    import random

    random.seed(42)
    random.shuffle(rows)

    # Split 80/20
    n_train = int(len(rows) * 0.8)
    train_rows = rows[:n_train]
    eval_rows = rows[n_train:]

    DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATASET_PATH.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    manifest = {
        "schema_version": "scbe_training_manifest_v1",
        "dataset_name": "chemistry_manual_verification_v2",
        "total_rows": len(rows),
        "n_train": len(train_rows),
        "n_eval": len(eval_rows),
        "sources": sorted({r["source"] for r in rows}),
        "difficulty_distribution": {str(d): sum(1 for r in rows if r["difficulty"] == d) for d in range(1, 6)},
        "generated_at": "2026-05-03T11:30:00-07:00",
    }
    with MANIFEST_PATH.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, indent=2, ensure_ascii=False)

    print(f"Generated {len(rows)} rows ({len(train_rows)} train / {len(eval_rows)} eval)")
    print(f"Dataset: {DATASET_PATH}")
    print(f"Manifest: {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
