"""
Choice Script Training Matrix (CSTM)
=====================================

AI training paradigm where agents develop unique personalities by playing
through interactive branching narratives.  Each agent in a "nursery" cohort
traverses the same story library but makes different choices, producing
distinct graduated personality kernels.

Modules
-------
- ``models``            — Core data structures (Scene, Choice, StoryGraph, etc.)
- ``story_engine``      — Parse ChoiceScript / Twee / JSON into StoryGraph DAGs
- ``player_agent``      — Autonomous agent with 21D personality vector
- ``nursery``           — Cohort management, curriculum, graduation
- ``kernel``            — Kernel extraction and export
- ``telemetry_bridge``  — Bridge game telemetry to SCBE concept blocks
- ``training_exporter`` — SFT/DPO training data generation from playthroughs
- ``mass_tester``       — Monte Carlo and exhaustive branch testing
"""

from .models import (
    Choice,
    Curriculum,
    CurriculumPhase,
    HistoryEntry,
    PhaseSpec,
    PlaythroughRecord,
    PlaythroughStep,
    Scene,
    StoryCategory,
    StoryGraph,
)
from .story_engine import (
    ConditionEvaluator,
    JSONParser,
    StoryEngine,
    TweeParser,
)
from .player_agent import (
    DecisionEngine,
    HistoryBuffer,
    PersonalityVector,
    PlayerAgent,
)
from .nursery import (
    AgentLifecycleState,
    AgentRecord,
    Cohort,
    GraduationCriteria,
    GraduationResult,
    NurseryManager,
)
from .kernel import (
    DecisionNode,
    DecisionTree,
    DriftAnalyzer,
    GraduatedKernel,
    KernelExtractor,
    PreferenceMatrix,
)
from .telemetry_bridge import (
    ConceptBlockActivation,
    HamiltonianTracker,
    TelemetryBridge,
    TelemetryEvent,
    TelemetryEventType,
)
from .training_exporter import (
    DPOTriple,
    SFTPair,
    TrainingExporter,
)
from .mass_tester import (
    CoverageReport,
    GraphAnalysis,
    Quicktest,
    Randomtest,
)

__all__ = [
    # Models
    "Choice", "Scene", "StoryGraph", "StoryCategory",
    "CurriculumPhase", "PhaseSpec", "Curriculum",
    "HistoryEntry", "PlaythroughRecord", "PlaythroughStep",
    # StoryEngine
    "StoryEngine", "JSONParser", "TweeParser", "ConditionEvaluator",
    # PlayerAgent
    "PlayerAgent", "PersonalityVector", "DecisionEngine", "HistoryBuffer",
    # Nursery
    "NurseryManager", "Cohort", "AgentRecord", "AgentLifecycleState",
    "GraduationCriteria", "GraduationResult",
    # Kernel
    "KernelExtractor", "GraduatedKernel", "DecisionTree",
    "DecisionNode", "DriftAnalyzer", "PreferenceMatrix",
    # TelemetryBridge
    "TelemetryBridge", "TelemetryEvent", "TelemetryEventType",
    "ConceptBlockActivation", "HamiltonianTracker",
    # TrainingExporter
    "TrainingExporter", "SFTPair", "DPOTriple",
    # MassTester
    "Randomtest", "Quicktest", "CoverageReport", "GraphAnalysis",
]
