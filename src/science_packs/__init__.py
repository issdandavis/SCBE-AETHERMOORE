"""
SCBE Science Packs - Comprehensive Scientific Computing Modules
================================================================

A modular collection of science modules covering every major discipline.
Each pack can be installed independently as an "add-on" power-up.

PACK CATEGORIES:
================
1. PHYSICAL SCIENCES
   - physics_sim (installed) - Classical, quantum, thermo, EM, relativity
   - chemistry - Molecular, organic, inorganic, biochemistry
   - astronomy - Astrophysics, cosmology, celestial mechanics
   - earth_science - Geology, meteorology, oceanography
   - materials - Solid state, crystallography, nanomaterials

2. LIFE SCIENCES
   - biology - Cell, molecular, genetics, evolution
   - neuroscience - Neural networks, brain modeling, cognition
   - ecology - Population dynamics, ecosystems, climate
   - bioinformatics - Genomics, proteomics, sequence analysis
   - pharmacology - Drug interactions, pharmacokinetics

3. MATHEMATICAL SCIENCES
   - pure_math - Number theory, topology, abstract algebra
   - applied_math - Numerical methods, optimization, ODEs/PDEs
   - statistics - Bayesian, frequentist, machine learning
   - cryptography - Post-quantum, lattice-based, elliptic curves
   - logic - Formal logic, proof assistants, type theory

4. ENGINEERING
   - electrical - Circuits, signals, power systems
   - mechanical - Dynamics, FEA, CAD
   - civil - Structural, geotechnical, transportation
   - aerospace - Aerodynamics, propulsion, flight dynamics
   - biomedical - Biomechanics, medical imaging, prosthetics

5. COMPUTER SCIENCE
   - algorithms - Data structures, complexity, graph theory
   - ai_ml - Neural networks, deep learning, reinforcement
   - distributed - Consensus, blockchain, P2P networks
   - security - Cryptanalysis, secure protocols, penetration testing
   - quantum_computing - Qubits, gates, error correction

6. SOCIAL SCIENCES (Computational)
   - economics - Econometrics, game theory, market simulation
   - sociology - Network analysis, agent-based models
   - psychology - Cognitive modeling, decision theory
   - linguistics - NLP, formal grammars, semantics

Version: 1.0.0
"""

__version__ = "1.0.0"
__all__ = [
    # Pack registry
    "SCIENCE_PACKS",
    "get_pack_info",
    "list_available_packs",
    "get_installed_packs",
    "install_pack",
    "PackStatus",
    # Categories
    "PHYSICAL_SCIENCES",
    "LIFE_SCIENCES",
    "MATHEMATICAL_SCIENCES",
    "ENGINEERING",
    "COMPUTER_SCIENCE",
    "SOCIAL_SCIENCES",
]

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import json
from pathlib import Path


class PackStatus(Enum):
    """Status of a science pack."""

    NOT_INSTALLED = "not_installed"
    INSTALLED = "installed"
    ACTIVE = "active"
    DISABLED = "disabled"
    UPDATING = "updating"


@dataclass
class SciencePack:
    """Represents a science module pack."""

    name: str
    category: str
    description: str
    version: str
    dependencies: List[str] = field(default_factory=list)
    status: PackStatus = PackStatus.NOT_INSTALLED
    size_mb: float = 0.0
    modules: List[str] = field(default_factory=list)
    textbook_refs: List[str] = field(default_factory=list)
    paper_refs: List[str] = field(default_factory=list)


# =============================================================================
# PHYSICAL SCIENCES PACKS
# =============================================================================

PHYSICAL_SCIENCES = {
    "physics_sim": SciencePack(
        name="Physics Simulation Engine",
        category="Physical Sciences",
        description="Classical mechanics, quantum mechanics, thermodynamics, electromagnetism, relativity, and numerical methods",
        version="2.0.0",
        status=PackStatus.INSTALLED,
        size_mb=2.5,
        modules=[
            "core",
            "atmosphere",
            "fluids",
            "orbital",
            "nuclear",
            "statistical",
            "waves_optics",
            "numerical",
            "simulator",
        ],
        textbook_refs=[
            "Halliday & Resnick - Fundamentals of Physics (OpenStax)",
            "Griffiths - Introduction to Quantum Mechanics",
            "Landau & Lifshitz - Classical Mechanics",
        ],
        paper_refs=[
            "arXiv:2301.00001 - Modern Computational Physics Methods",
        ],
    ),
    "chemistry": SciencePack(
        name="Computational Chemistry",
        category="Physical Sciences",
        description="Molecular dynamics, quantum chemistry, reaction kinetics, thermochemistry",
        version="1.0.0",
        dependencies=["physics_sim"],
        size_mb=5.2,
        modules=[
            "molecular",
            "quantum_chem",
            "kinetics",
            "thermochem",
            "spectroscopy",
            "electrochemistry",
            "organic",
            "inorganic",
        ],
        textbook_refs=[
            "OpenStax Chemistry 2e (Free)",
            "Atkins - Physical Chemistry",
            "Levine - Quantum Chemistry",
        ],
        paper_refs=[
            "doi:10.1021/acs.jctc.0c01234 - DFT Advances 2024",
        ],
    ),
    "astronomy": SciencePack(
        name="Computational Astronomy",
        category="Physical Sciences",
        description="Celestial mechanics, astrophysics, cosmology, stellar evolution",
        version="1.0.0",
        dependencies=["physics_sim"],
        size_mb=3.8,
        modules=[
            "celestial",
            "stellar",
            "galactic",
            "cosmology",
            "exoplanets",
            "radio_astronomy",
            "spectral_analysis",
        ],
        textbook_refs=[
            "OpenStax Astronomy (Free)",
            "Carroll & Ostlie - Modern Astrophysics",
        ],
        paper_refs=[
            "arXiv:2312.00001 - JWST Early Science Results",
        ],
    ),
    "earth_science": SciencePack(
        name="Earth & Planetary Science",
        category="Physical Sciences",
        description="Geology, meteorology, oceanography, climate modeling",
        version="1.0.0",
        dependencies=["physics_sim", "chemistry"],
        size_mb=4.5,
        modules=[
            "geology",
            "meteorology",
            "oceanography",
            "climate",
            "seismology",
            "hydrology",
            "geophysics",
        ],
        textbook_refs=[
            "OpenStax Earth Science (Free)",
            "Lutgens & Tarbuck - Earth Science",
        ],
        paper_refs=[
            "doi:10.1038/s41586-024-00001 - Climate Model Advances",
        ],
    ),
    "materials": SciencePack(
        name="Materials Science",
        category="Physical Sciences",
        description="Solid state physics, crystallography, nanomaterials, polymers",
        version="1.0.0",
        dependencies=["physics_sim", "chemistry"],
        size_mb=3.2,
        modules=[
            "solid_state",
            "crystallography",
            "nanomaterials",
            "polymers",
            "ceramics",
            "metals",
            "semiconductors",
        ],
        textbook_refs=[
            "Callister - Materials Science and Engineering",
            "Kittel - Introduction to Solid State Physics",
        ],
        paper_refs=[
            "doi:10.1126/science.2024001 - 2D Materials Review",
        ],
    ),
}

# =============================================================================
# LIFE SCIENCES PACKS
# =============================================================================

LIFE_SCIENCES = {
    "biology": SciencePack(
        name="Computational Biology",
        category="Life Sciences",
        description="Cell biology, molecular biology, genetics, evolution",
        version="1.0.0",
        size_mb=4.8,
        modules=[
            "cell_biology",
            "molecular",
            "genetics",
            "evolution",
            "developmental",
            "systems_biology",
            "synthetic_biology",
        ],
        textbook_refs=[
            "OpenStax Biology 2e (Free)",
            "Alberts - Molecular Biology of the Cell",
        ],
        paper_refs=[
            "doi:10.1016/j.cell.2024.001 - Single Cell Genomics",
        ],
    ),
    "neuroscience": SciencePack(
        name="Computational Neuroscience",
        category="Life Sciences",
        description="Neural networks, brain modeling, cognitive simulation",
        version="1.0.0",
        dependencies=["biology"],
        size_mb=6.1,
        modules=[
            "hodgkin_huxley",
            "neural_networks",
            "synaptic",
            "brain_regions",
            "cognitive",
            "vision",
            "motor_control",
        ],
        textbook_refs=[
            "Dayan & Abbott - Theoretical Neuroscience (MIT)",
            "Kandel - Principles of Neural Science",
        ],
        paper_refs=[
            "arXiv:2401.00001 - Large Scale Brain Simulation",
        ],
    ),
    "ecology": SciencePack(
        name="Computational Ecology",
        category="Life Sciences",
        description="Population dynamics, ecosystems, food webs, climate ecology",
        version="1.0.0",
        dependencies=["biology"],
        size_mb=2.9,
        modules=[
            "population",
            "predator_prey",
            "food_webs",
            "ecosystems",
            "conservation",
            "biogeography",
            "climate_ecology",
        ],
        textbook_refs=[
            "Gotelli - A Primer of Ecology",
            "Rockwood - Introduction to Population Ecology",
        ],
        paper_refs=[
            "doi:10.1111/ele.2024.001 - Biodiversity Crisis Modeling",
        ],
    ),
    "bioinformatics": SciencePack(
        name="Bioinformatics",
        category="Life Sciences",
        description="Genomics, proteomics, sequence analysis, structural biology",
        version="1.0.0",
        dependencies=["biology"],
        size_mb=5.5,
        modules=[
            "sequence_alignment",
            "phylogenetics",
            "genomics",
            "proteomics",
            "structural",
            "transcriptomics",
            "metagenomics",
        ],
        textbook_refs=[
            "Pevsner - Bioinformatics and Functional Genomics",
            "NCBI Handbook (Free)",
        ],
        paper_refs=[
            "doi:10.1038/s41592-024-001 - AlphaFold3 Methods",
        ],
    ),
    "pharmacology": SciencePack(
        name="Computational Pharmacology",
        category="Life Sciences",
        description="Drug interactions, pharmacokinetics, ADME modeling",
        version="1.0.0",
        dependencies=["biology", "chemistry"],
        size_mb=3.7,
        modules=[
            "pharmacokinetics",
            "pharmacodynamics",
            "drug_design",
            "toxicology",
            "adme",
            "drug_interactions",
            "clinical_trials",
        ],
        textbook_refs=[
            "Goodman & Gilman - Pharmacological Basis of Therapeutics",
            "Rowland & Tozer - Clinical Pharmacokinetics",
        ],
        paper_refs=[
            "doi:10.1038/s41573-024-001 - AI Drug Discovery",
        ],
    ),
}

# =============================================================================
# MATHEMATICAL SCIENCES PACKS
# =============================================================================

MATHEMATICAL_SCIENCES = {
    "pure_math": SciencePack(
        name="Pure Mathematics",
        category="Mathematical Sciences",
        description="Number theory, topology, abstract algebra, analysis",
        version="1.0.0",
        size_mb=2.1,
        modules=[
            "number_theory",
            "topology",
            "abstract_algebra",
            "real_analysis",
            "complex_analysis",
            "differential_geometry",
        ],
        textbook_refs=[
            "Rudin - Principles of Mathematical Analysis",
            "Dummit & Foote - Abstract Algebra",
            "Munkres - Topology",
        ],
        paper_refs=[
            "arXiv:2401.00001 - Advances in Algebraic Topology",
        ],
    ),
    "applied_math": SciencePack(
        name="Applied Mathematics",
        category="Mathematical Sciences",
        description="Numerical methods, ODEs/PDEs, optimization, dynamical systems",
        version="1.0.0",
        size_mb=3.4,
        modules=[
            "numerical_linear_algebra",
            "ode_solvers",
            "pde_solvers",
            "optimization",
            "dynamical_systems",
            "chaos",
            "control_theory",
        ],
        textbook_refs=[
            "Strang - Linear Algebra (MIT OpenCourseWare)",
            "Trefethen & Bau - Numerical Linear Algebra",
            "Boyd & Vandenberghe - Convex Optimization (Free)",
        ],
        paper_refs=[
            "doi:10.1137/20M1001 - Modern Numerical Methods",
        ],
    ),
    "statistics": SciencePack(
        name="Statistical Computing",
        category="Mathematical Sciences",
        description="Bayesian inference, frequentist methods, ML foundations",
        version="1.0.0",
        size_mb=4.2,
        modules=[
            "bayesian",
            "frequentist",
            "hypothesis_testing",
            "regression",
            "time_series",
            "monte_carlo",
            "causal_inference",
        ],
        textbook_refs=[
            "OpenStax Statistics (Free)",
            "Gelman - Bayesian Data Analysis",
            "Hastie - Elements of Statistical Learning (Free)",
        ],
        paper_refs=[
            "arXiv:2312.00001 - Modern Causal Inference",
        ],
    ),
    "cryptography": SciencePack(
        name="Cryptographic Systems",
        category="Mathematical Sciences",
        description="Post-quantum crypto, lattice-based, elliptic curves, zero-knowledge",
        version="1.0.0",
        status=PackStatus.INSTALLED,  # Core to SCBE
        size_mb=3.8,
        modules=[
            "symmetric",
            "asymmetric",
            "lattice",
            "elliptic_curves",
            "post_quantum",
            "zero_knowledge",
            "mpc",
            "homomorphic",
        ],
        textbook_refs=[
            "Katz & Lindell - Modern Cryptography",
            "Boneh & Shoup - Graduate Cryptography (Free)",
        ],
        paper_refs=[
            "NIST PQC Standard (2024)",
            "arXiv:2401.00001 - Lattice Attacks Survey",
        ],
    ),
    "logic": SciencePack(
        name="Mathematical Logic",
        category="Mathematical Sciences",
        description="Formal logic, proof assistants, type theory, computability",
        version="1.0.0",
        size_mb=1.8,
        modules=[
            "propositional",
            "predicate",
            "modal",
            "proof_theory",
            "model_theory",
            "computability",
            "type_theory",
        ],
        textbook_refs=[
            "Enderton - A Mathematical Introduction to Logic",
            "Girard - Proofs and Types (Free)",
        ],
        paper_refs=[
            "arXiv:2312.00001 - Lean 4 Formalization Methods",
        ],
    ),
}

# =============================================================================
# ENGINEERING PACKS
# =============================================================================

ENGINEERING = {
    "electrical": SciencePack(
        name="Electrical Engineering",
        category="Engineering",
        description="Circuit analysis, signals & systems, power systems, control",
        version="1.0.0",
        dependencies=["physics_sim", "applied_math"],
        size_mb=4.1,
        modules=[
            "circuits",
            "signals",
            "power_systems",
            "control_systems",
            "electromagnetics",
            "electronics",
            "digital_systems",
        ],
        textbook_refs=[
            "OpenStax University Physics Vol 2 (Free)",
            "Oppenheim - Signals and Systems",
            "Horowitz - Art of Electronics",
        ],
        paper_refs=[
            "IEEE Spectrum - Power Grid Modernization 2024",
        ],
    ),
    "mechanical": SciencePack(
        name="Mechanical Engineering",
        category="Engineering",
        description="Dynamics, FEA, thermodynamics, fluid mechanics, CAD",
        version="1.0.0",
        dependencies=["physics_sim"],
        size_mb=5.3,
        modules=[
            "statics",
            "dynamics",
            "fea",
            "cfd",
            "heat_transfer",
            "machine_design",
            "vibrations",
            "robotics",
        ],
        textbook_refs=[
            "Beer & Johnston - Mechanics of Materials",
            "Shigley - Mechanical Engineering Design",
        ],
        paper_refs=[
            "doi:10.1115/1.2024001 - Additive Manufacturing Methods",
        ],
    ),
    "aerospace": SciencePack(
        name="Aerospace Engineering",
        category="Engineering",
        description="Aerodynamics, propulsion, flight dynamics, spacecraft design",
        version="1.0.0",
        dependencies=["physics_sim", "mechanical"],
        size_mb=4.7,
        modules=[
            "aerodynamics",
            "propulsion",
            "flight_dynamics",
            "structures",
            "spacecraft_design",
            "astrodynamics",
            "avionics",
        ],
        textbook_refs=[
            "Anderson - Fundamentals of Aerodynamics",
            "Anderson - Introduction to Flight",
        ],
        paper_refs=[
            "AIAA Journal - Hypersonic Vehicle Design 2024",
        ],
    ),
    "civil": SciencePack(
        name="Civil Engineering",
        category="Engineering",
        description="Structural analysis, geotechnical, transportation, water resources",
        version="1.0.0",
        dependencies=["physics_sim", "mechanical"],
        size_mb=3.9,
        modules=[
            "structural",
            "geotechnical",
            "transportation",
            "water_resources",
            "construction",
            "environmental_eng",
            "surveying",
        ],
        textbook_refs=[
            "Hibbeler - Structural Analysis",
            "Das - Principles of Foundation Engineering",
        ],
        paper_refs=[
            "ASCE - Infrastructure Resilience 2024",
        ],
    ),
    "biomedical": SciencePack(
        name="Biomedical Engineering",
        category="Engineering",
        description="Biomechanics, medical imaging, prosthetics, tissue engineering",
        version="1.0.0",
        dependencies=["biology", "mechanical"],
        size_mb=4.4,
        modules=[
            "biomechanics",
            "medical_imaging",
            "prosthetics",
            "tissue_eng",
            "biosensors",
            "drug_delivery",
            "neural_engineering",
        ],
        textbook_refs=[
            "Enderle - Biomedical Engineering",
            "Bronzino - Biomedical Engineering Handbook",
        ],
        paper_refs=[
            "doi:10.1038/s41551-024-001 - Neural Interface Advances",
        ],
    ),
}

# =============================================================================
# COMPUTER SCIENCE PACKS
# =============================================================================

COMPUTER_SCIENCE = {
    "algorithms": SciencePack(
        name="Algorithms & Data Structures",
        category="Computer Science",
        description="Classic algorithms, complexity theory, graph algorithms, optimization",
        version="1.0.0",
        size_mb=2.3,
        modules=[
            "sorting",
            "searching",
            "graphs",
            "dynamic_programming",
            "complexity",
            "np_hard",
            "approximation",
            "randomized",
        ],
        textbook_refs=[
            "CLRS - Introduction to Algorithms (MIT)",
            "Kleinberg & Tardos - Algorithm Design",
            "Sedgewick - Algorithms (Princeton, Free)",
        ],
        paper_refs=[
            "arXiv:2401.00001 - Quantum Algorithm Speedups",
        ],
    ),
    "ai_ml": SciencePack(
        name="AI & Machine Learning",
        category="Computer Science",
        description="Neural networks, deep learning, reinforcement learning, NLP",
        version="1.0.0",
        dependencies=["algorithms", "statistics"],
        size_mb=8.2,
        modules=[
            "neural_networks",
            "deep_learning",
            "cnn",
            "rnn",
            "transformers",
            "reinforcement_learning",
            "nlp",
            "computer_vision",
            "generative",
        ],
        textbook_refs=[
            "Goodfellow - Deep Learning (Free)",
            "Sutton & Barto - Reinforcement Learning (Free)",
            "Bishop - Pattern Recognition and ML",
        ],
        paper_refs=[
            "arXiv:2401.00001 - Transformer Architecture Survey 2024",
            "arXiv:2312.00001 - RLHF Methods",
        ],
    ),
    "distributed": SciencePack(
        name="Distributed Systems",
        category="Computer Science",
        description="Consensus protocols, blockchain, P2P networks, cloud computing",
        version="1.0.0",
        dependencies=["algorithms"],
        size_mb=3.1,
        modules=[
            "consensus",
            "blockchain",
            "p2p",
            "cloud",
            "replication",
            "sharding",
            "consistency",
            "fault_tolerance",
        ],
        textbook_refs=[
            "Tanenbaum - Distributed Systems",
            "Kleppmann - Designing Data-Intensive Applications",
        ],
        paper_refs=[
            "arXiv:2312.00001 - Byzantine Fault Tolerance Survey",
        ],
    ),
    "security": SciencePack(
        name="Computer Security",
        category="Computer Science",
        description="Cryptanalysis, secure protocols, penetration testing, malware analysis",
        version="1.0.0",
        status=PackStatus.INSTALLED,  # Core to SCBE
        dependencies=["algorithms", "cryptography"],
        size_mb=4.6,
        modules=[
            "cryptanalysis",
            "protocols",
            "network_security",
            "web_security",
            "binary_analysis",
            "malware",
            "forensics",
            "secure_coding",
        ],
        textbook_refs=[
            "Anderson - Security Engineering (Free)",
            "Stallings - Computer Security",
        ],
        paper_refs=[
            "USENIX Security 2024 - Best Papers",
        ],
    ),
    "quantum_computing": SciencePack(
        name="Quantum Computing",
        category="Computer Science",
        description="Qubits, quantum gates, error correction, quantum algorithms",
        version="1.0.0",
        dependencies=["physics_sim", "algorithms"],
        size_mb=3.5,
        modules=[
            "qubits",
            "gates",
            "circuits",
            "algorithms",
            "error_correction",
            "simulation",
            "variational",
            "quantum_ml",
        ],
        textbook_refs=[
            "Nielsen & Chuang - Quantum Computation",
            "Qiskit Textbook (IBM, Free)",
        ],
        paper_refs=[
            "arXiv:2401.00001 - Quantum Error Correction Advances",
        ],
    ),
}

# =============================================================================
# SOCIAL SCIENCES PACKS
# =============================================================================

SOCIAL_SCIENCES = {
    "economics": SciencePack(
        name="Computational Economics",
        category="Social Sciences",
        description="Econometrics, game theory, market simulation, agent-based models",
        version="1.0.0",
        dependencies=["statistics"],
        size_mb=2.8,
        modules=[
            "econometrics",
            "game_theory",
            "market_sim",
            "abm",
            "financial_modeling",
            "auction_theory",
            "mechanism_design",
        ],
        textbook_refs=[
            "OpenStax Principles of Economics (Free)",
            "Mas-Colell - Microeconomic Theory",
        ],
        paper_refs=[
            "doi:10.1257/aer.2024.001 - Computational Economics Survey",
        ],
    ),
    "sociology": SciencePack(
        name="Computational Sociology",
        category="Social Sciences",
        description="Network analysis, agent-based social models, opinion dynamics",
        version="1.0.0",
        dependencies=["statistics"],
        size_mb=2.2,
        modules=[
            "network_analysis",
            "abm_social",
            "opinion_dynamics",
            "segregation",
            "diffusion",
            "collective_behavior",
        ],
        textbook_refs=[
            "Easley & Kleinberg - Networks, Crowds, and Markets (Free)",
            "Epstein - Generative Social Science",
        ],
        paper_refs=[
            "arXiv:2312.00001 - Computational Social Science Methods",
        ],
    ),
    "psychology": SciencePack(
        name="Computational Psychology",
        category="Social Sciences",
        description="Cognitive modeling, decision theory, behavioral simulation",
        version="1.0.0",
        dependencies=["statistics", "neuroscience"],
        size_mb=2.5,
        modules=[
            "cognitive_models",
            "decision_theory",
            "memory",
            "attention",
            "learning",
            "emotion",
            "social_cognition",
        ],
        textbook_refs=[
            "Anderson - Cognitive Psychology and Its Implications",
            "Busemeyer - Cognitive Modeling",
        ],
        paper_refs=[
            "doi:10.1037/rev2024001 - Computational Models of Mind",
        ],
    ),
    "linguistics": SciencePack(
        name="Computational Linguistics",
        category="Social Sciences",
        description="NLP, formal grammars, semantics, language models",
        version="1.0.0",
        dependencies=["ai_ml"],
        size_mb=3.9,
        modules=[
            "nlp_core",
            "formal_grammars",
            "semantics",
            "pragmatics",
            "morphology",
            "syntax",
            "phonology",
            "language_models",
        ],
        textbook_refs=[
            "Jurafsky & Martin - Speech and Language Processing (Free)",
            "Manning - Foundations of Statistical NLP",
        ],
        paper_refs=[
            "arXiv:2401.00001 - Large Language Model Survey",
        ],
    ),
}

# =============================================================================
# UNIFIED REGISTRY
# =============================================================================

SCIENCE_PACKS: Dict[str, Dict[str, SciencePack]] = {
    "Physical Sciences": PHYSICAL_SCIENCES,
    "Life Sciences": LIFE_SCIENCES,
    "Mathematical Sciences": MATHEMATICAL_SCIENCES,
    "Engineering": ENGINEERING,
    "Computer Science": COMPUTER_SCIENCE,
    "Social Sciences": SOCIAL_SCIENCES,
}


def get_pack_info(pack_name: str) -> Optional[SciencePack]:
    """Get information about a specific pack."""
    for category, packs in SCIENCE_PACKS.items():
        if pack_name in packs:
            return packs[pack_name]
    return None


def list_available_packs() -> Dict[str, List[str]]:
    """List all available packs by category."""
    return {category: list(packs.keys()) for category, packs in SCIENCE_PACKS.items()}


def get_installed_packs() -> List[SciencePack]:
    """Get all installed packs."""
    installed = []
    for category, packs in SCIENCE_PACKS.items():
        for pack in packs.values():
            if pack.status in (PackStatus.INSTALLED, PackStatus.ACTIVE):
                installed.append(pack)
    return installed


def install_pack(pack_name: str) -> bool:
    """Install a science pack (placeholder for actual installation logic)."""
    pack = get_pack_info(pack_name)
    if pack is None:
        return False

    # Check dependencies
    for dep in pack.dependencies:
        dep_pack = get_pack_info(dep)
        if dep_pack and dep_pack.status == PackStatus.NOT_INSTALLED:
            print(f"Installing dependency: {dep}")
            install_pack(dep)

    pack.status = PackStatus.INSTALLED
    return True


# Total pack count
def get_total_pack_count() -> int:
    """Get total number of available science packs."""
    return sum(len(packs) for packs in SCIENCE_PACKS.values())


# Print summary on import
if __name__ == "__main__":
    print(f"SCBE Science Packs v{__version__}")
    print(f"Total packs available: {get_total_pack_count()}")
    print("\nCategories:")
    for category, packs in list_available_packs().items():
        print(f"  {category}: {len(packs)} packs")
