

# Choice Script Training Matrix (CSTM) — Architecture Design Document

**Version**: 0.1.0-draft
**Date**: 2026-02-21
**Status**: Architectural Proposal
**Patent Context**: Extends SCBE-AETHERMOORE (USPTO #63/961,403) Layer Integration

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Core Philosophy](#2-core-philosophy)
3. [System Overview](#3-system-overview)
4. [Component Architecture](#4-component-architecture)
   - 4.1 StoryEngine
   - 4.2 PlayerAgent
   - 4.3 NurseryManager
   - 4.4 KernelExtractor
   - 4.5 CurriculumDesigner
   - 4.6 TelemetryBridge
   - 4.7 FederatedNursery
5. [Class Diagrams](#5-class-diagrams)
6. [Data Flow](#6-data-flow)
7. [SCBE Layer Mapping](#7-scbe-layer-mapping)
8. [Data Structures and Schemas](#8-data-structures-and-schemas)
9. [Decision Function Specification](#9-decision-function-specification)
10. [Graduation Protocol](#10-graduation-protocol)
11. [Federated Consensus Protocol](#11-federated-consensus-protocol)
12. [Extension Points and Integration](#12-extension-points-and-integration)
13. [Appendix: Concept Block Mapping Table](#13-appendix-concept-block-mapping-table)

---

## 1. Executive Summary

The Choice Script Training Matrix (CSTM) is a novel AI training paradigm in which AI agents develop behavioral personalities by playing through interactive, branching narratives. Rather than training a model on a monolithic dataset with uniform objectives, CSTM treats each agent as a unique individual raised through a "nursery" of experiences. The same source material — a library of choice-based stories — produces different graduated models depending on the decisions each agent makes along the way.

This is analogous to human development: two children raised in the same household, attending the same schools, reading the same books, will nonetheless emerge as distinct individuals because of the micro-decisions they make at every fork. CSTM operationalizes this insight for AI alignment.

The system maps directly onto the SCBE-AETHERMOORE 14-layer governance framework, treating the 21-dimensional brain state vector as the agent's evolving personality, and each narrative choice as a state transition governed by the Hamiltonian safety function `H(d, pd) = 1 / (1 + d + 2*pd)`.

---

## 2. Core Philosophy

**Thesis**: Alignment is not a property to be imposed after training; it is a character trait to be cultivated during development.

Three governing principles:

1. **Narrative Determinism** — An agent's values are the sum of its choices. No two playthroughs produce the same kernel, just as no two lives produce the same person.

2. **Curriculum as Environment** — Stories are not training data; they are *environments*. The agent does not memorize stories; it develops *dispositions* from navigating them. The story is the gym; the personality vector is the muscle.

3. **Graduation over Convergence** — Traditional training converges all agents toward a single loss minimum. CSTM deliberately produces a *population* of distinct but governance-aligned agents. The NurseryManager does not seek homogeneity; it seeks a cohort where every graduate meets safety thresholds while maintaining individual character.

---

## 3. System Overview

```
+------------------------------------------------------------------+
|                        CSTM System Boundary                      |
|                                                                   |
|  +-----------------+     +----------------+     +---------------+ |
|  | CurriculumDe-   |---->| NurseryManager |---->| KernelExtrac- | |
|  | signer          |     |                |     | tor           | |
|  +-----------------+     +-------+--------+     +-------+-------+ |
|         |                        |                      |         |
|         v                        v                      v         |
|  +-----------------+     +----------------+     +---------------+ |
|  | StoryEngine     |<--->| PlayerAgent    |---->| TelemetryBri- | |
|  | (Parser + DAG)  |     | (x N agents)   |     | dge           | |
|  +-----------------+     +----------------+     +-------+-------+ |
|                                                         |         |
|  +------------------------------------------------------+-------+ |
|  |                   FederatedNursery                            | |
|  |  [Node A] <----BFT Consensus----> [Node B] <----> [Node C]   | |
|  +---------------------------------------------------------------+ |
+------------------------------------------------------------------+
         |                    |                      |
         v                    v                      v
   Story Library        SCBE 14-Layer          Graduated Kernels
   (CS/Twee/JSON)       Governance Stack       (LoRA / Preference)
```

---

## 4. Component Architecture

### 4.1 StoryEngine

**Responsibility**: Parse interactive fiction source files into a traversable directed acyclic graph (DAG) of scenes and choices. Serve as the "world" that agents inhabit during a playthrough.

**Design Rationale**: Interactive fiction is a mature medium with well-defined formats. ChoiceScript (by Choice of Games) and Twine/Twee are the two dominant authoring systems. Both encode branching narratives with stat tracking — precisely the structure CSTM needs. By supporting multiple input formats, the system can leverage decades of existing interactive fiction as training material.

```
StoryEngine
├── parsers/
│   ├── choicescript_parser.py    # *choice, *goto, *set, *if
│   ├── twee_parser.py           # :: PassageName, [[link]], (set:)
│   └── json_parser.py           # Custom schema (native format)
├── models/
│   ├── scene.py                 # Scene dataclass
│   ├── choice.py                # Choice dataclass
│   ├── story_graph.py           # DAG container + traversal
│   └── stat_schema.py           # Stat definitions + ranges
├── validators/
│   ├── graph_validator.py       # Reachability, dead ends, cycles
│   └── condition_evaluator.py   # Evaluate choice conditions at runtime
└── engine.py                    # Main orchestrator: load → parse → validate → serve
```

**Key Classes**:

```python
@dataclass(frozen=True)
class Choice:
    """A single selectable option within a scene."""
    choice_id: str
    label: str                              # Display text
    next_scene_id: str                      # Target scene
    condition: Optional[str] = None         # Boolean expression over stats
    stat_effects: Dict[str, float] = field(default_factory=dict)
    tags: FrozenSet[str] = frozenset()      # e.g. {"ethical", "aggressive", "empathetic"}
    difficulty: float = 0.0                 # Optional difficulty rating [0, 1]

@dataclass
class Scene:
    """A single node in the story graph."""
    scene_id: str
    title: str
    text: str                               # Narrative content (may be long)
    choices: List[Choice]
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_entry: bool = False
    is_exit: bool = False
    scene_type: str = "narrative"           # narrative | dilemma | info | checkpoint

class StoryGraph:
    """Directed graph of scenes. Immutable after construction."""

    def __init__(self, scenes: Dict[str, Scene], story_id: str, story_metadata: dict):
        self._scenes = scenes
        self._story_id = story_id
        self._metadata = story_metadata
        self._adjacency: Dict[str, List[str]] = self._build_adjacency()
        self._entry_points: List[str] = [s.scene_id for s in scenes.values() if s.is_entry]
        self._exit_points: List[str] = [s.scene_id for s in scenes.values() if s.is_exit]

    def get_scene(self, scene_id: str) -> Scene: ...
    def get_available_choices(self, scene_id: str, stats: Dict[str, float]) -> List[Choice]: ...
    def shortest_path(self, from_id: str, to_id: str) -> List[str]: ...
    def all_paths(self) -> Iterator[List[str]]: ...
    def branching_factor(self) -> float: ...
    def total_scenes(self) -> int: ...
    def validate(self) -> List[ValidationError]: ...
```

**Parser Protocol**:

```python
class StoryParser(Protocol):
    """All parsers must implement this interface."""
    def parse(self, source: Union[str, Path, IO]) -> StoryGraph: ...
    def supported_extensions(self) -> Tuple[str, ...]: ...
```

**Condition Evaluation**: Choice conditions are boolean expressions over the agent's current stats. The `ConditionEvaluator` uses a restricted expression grammar (no function calls, no attribute access — only comparisons and boolean operators over stat names) to prevent injection.

```python
class ConditionEvaluator:
    """Safe evaluation of choice condition expressions."""
    ALLOWED_OPS = {ast.Compare, ast.BoolOp, ast.Name, ast.Constant, ...}

    def evaluate(self, expression: str, stats: Dict[str, float]) -> bool: ...
```

---

### 4.2 PlayerAgent

**Responsibility**: An autonomous agent that receives scene text and available choices, then selects a choice based on its internal state. The agent maintains a 21-dimensional personality vector (mapped to the SCBE brain state), a mutable stats dictionary, and a rolling history of past decisions.

**Design Rationale**: The agent is deliberately *not* a full LLM at decision time. It is a lightweight decision function that takes embeddings as input. The LLM is used only to embed scene text; the actual choice selection is a learned function over the personality vector space. This keeps the system tractable for running thousands of agents in parallel.

```
PlayerAgent
├── personality.py         # 21D vector + drift tracking
├── decision_engine.py     # Core choice function
├── memory.py              # Rolling history buffer
├── stats_tracker.py       # Mutable stat state
└── agent.py               # Main agent class
```

**Key Classes**:

```python
class PersonalityVector:
    """
    21-dimensional vector representing the agent's current personality state.
    Maps 1:1 to SCBE brain state dimensions:

    Dims  0-2:   Cognitive (reasoning, abstraction, pattern_recognition)
    Dims  3-5:   Ethical (fairness, harm_avoidance, honesty)
    Dims  6-8:   Social (empathy, cooperation, assertiveness)
    Dims  9-11:  Executive (planning, impulse_control, adaptability)
    Dims 12-14:  Motivational (curiosity, persistence, risk_tolerance)
    Dims 15-17:  Emotional (stability, optimism, resilience)
    Dims 18-20:  Meta (self_awareness, uncertainty_tolerance, growth_orientation)
    """

    def __init__(self, initial: Optional[np.ndarray] = None, seed: int = 0):
        if initial is not None:
            assert initial.shape == (21,)
            self._vector = initial.copy()
        else:
            rng = np.random.default_rng(seed)
            self._vector = rng.uniform(0.3, 0.7, size=21)  # Start near center
        self._history: List[Tuple[float, np.ndarray]] = []  # (timestamp, snapshot)

    @property
    def vector(self) -> np.ndarray:
        return self._vector.copy()

    def apply_drift(self, delta: np.ndarray, learning_rate: float = 0.01) -> None:
        """Shift personality vector by delta, clamped to [0, 1]."""
        self._history.append((time.time(), self._vector.copy()))
        self._vector = np.clip(self._vector + learning_rate * delta, 0.0, 1.0)

    def cosine_distance_from(self, other: np.ndarray) -> float: ...
    def dominant_traits(self, top_k: int = 5) -> List[Tuple[str, float]]: ...
    def drift_magnitude(self) -> float:
        """Total L2 distance traveled since initialization."""
        ...

DIM_NAMES = [
    "reasoning", "abstraction", "pattern_recognition",
    "fairness", "harm_avoidance", "honesty",
    "empathy", "cooperation", "assertiveness",
    "planning", "impulse_control", "adaptability",
    "curiosity", "persistence", "risk_tolerance",
    "stability", "optimism", "resilience",
    "self_awareness", "uncertainty_tolerance", "growth_orientation",
]
```

```python
class DecisionEngine:
    """
    Core decision function:
        choice = f(scene_embedding, personality_vector, stats, history)

    Architecture: A small MLP that scores each available choice.
    Input per choice:
        - scene_embedding (384D, from sentence-transformers)
        - choice_embedding (384D)
        - personality_vector (21D)
        - stats_vector (variable, padded to 32D)
        - history_summary (64D, compressed from rolling window)
    Total input: 885D per choice → score ∈ R

    The agent selects the highest-scoring choice, with optional
    temperature-based sampling for exploration during training.
    """

    def __init__(self, model: nn.Module, embedder: SentenceTransformer, temperature: float = 1.0):
        self._model = model
        self._embedder = embedder
        self._temperature = temperature

    def score_choices(
        self,
        scene: Scene,
        choices: List[Choice],
        personality: PersonalityVector,
        stats: Dict[str, float],
        history: "HistoryBuffer",
    ) -> List[Tuple[Choice, float]]:
        """Return (choice, score) pairs sorted descending by score."""
        scene_emb = self._embedder.encode(scene.text)
        choice_embs = [self._embedder.encode(c.label) for c in choices]
        pv = personality.vector
        sv = self._pad_stats(stats)
        hv = history.compress()

        scores = []
        for choice, c_emb in zip(choices, choice_embs):
            x = np.concatenate([scene_emb, c_emb, pv, sv, hv])
            score = self._model(torch.tensor(x, dtype=torch.float32))
            scores.append((choice, score.item()))
        return sorted(scores, key=lambda t: t[1], reverse=True)

    def select(self, scored: List[Tuple[Choice, float]]) -> Choice:
        """Sample from scored choices using temperature."""
        if self._temperature <= 0.01:
            return scored[0][0]
        logits = np.array([s for _, s in scored]) / self._temperature
        probs = softmax(logits)
        idx = np.random.choice(len(scored), p=probs)
        return scored[idx][0]
```

```python
class HistoryBuffer:
    """Rolling window of recent decisions, compressed to a fixed-size vector."""

    def __init__(self, max_size: int = 100, compress_dim: int = 64):
        self._entries: Deque[HistoryEntry] = deque(maxlen=max_size)
        self._compressor: nn.Module = ...  # Small autoencoder

    def record(self, scene_id: str, choice: Choice, stats_snapshot: Dict[str, float]) -> None: ...
    def compress(self) -> np.ndarray:
        """Return a fixed 64D summary of recent history."""
        ...
    def as_dataframe(self) -> pd.DataFrame: ...

@dataclass
class HistoryEntry:
    timestamp: float
    scene_id: str
    choice_id: str
    choice_label: str
    choice_tags: FrozenSet[str]
    stats_before: Dict[str, float]
    stats_after: Dict[str, float]
    personality_snapshot: np.ndarray
```

```python
class PlayerAgent:
    """A single AI agent that plays through stories."""

    def __init__(
        self,
        agent_id: str,
        personality: PersonalityVector,
        decision_engine: DecisionEngine,
        initial_stats: Optional[Dict[str, float]] = None,
    ):
        self.agent_id = agent_id
        self.personality = personality
        self.decision_engine = decision_engine
        self.stats = initial_stats or {}
        self.history = HistoryBuffer()
        self._playthrough_log: List[PlaythroughEntry] = []

    def play_scene(self, scene: Scene, available_choices: List[Choice]) -> Choice:
        """Process a scene and return the chosen action."""
        scored = self.decision_engine.score_choices(
            scene, available_choices, self.personality, self.stats, self.history
        )
        chosen = self.decision_engine.select(scored)

        # Apply stat effects
        for stat, delta in chosen.stat_effects.items():
            self.stats[stat] = self.stats.get(stat, 0.0) + delta

        # Compute personality drift from choice tags
        drift = self._compute_personality_drift(chosen)
        self.personality.apply_drift(drift)

        # Record history
        self.history.record(scene.scene_id, chosen, self.stats.copy())
        return chosen

    def _compute_personality_drift(self, choice: Choice) -> np.ndarray:
        """
        Map choice tags to personality dimension deltas.
        Tag "empathetic" nudges dims 6-8 upward.
        Tag "aggressive" nudges dim 8 up, dims 6-7 down.
        Magnitude is modulated by choice difficulty.
        """
        ...

    def play_story(self, graph: StoryGraph) -> "PlaythroughRecord":
        """Play through an entire story from entry to exit."""
        current = graph.get_scene(graph.entry_points[0])
        record = PlaythroughRecord(agent_id=self.agent_id, story_id=graph.story_id)

        while not current.is_exit:
            choices = graph.get_available_choices(current.scene_id, self.stats)
            if not choices:
                break  # Dead end (should be caught by validation)
            chosen = self.play_scene(current, choices)
            record.add_step(current.scene_id, chosen)
            current = graph.get_scene(chosen.next_scene_id)

        record.finalize(self.personality.vector, self.stats.copy())
        return record
```

---

### 4.3 NurseryManager

**Responsibility**: Orchestrate a cohort of PlayerAgents through a curriculum of stories. Manage agent lifecycle from initialization through graduation. Track population-level statistics and enforce graduation criteria.

```
NurseryManager
├── cohort.py              # Cohort container + population stats
├── lifecycle.py           # Agent state machine (spawned → active → graduated | failed)
├── scheduler.py           # Story scheduling + parallelism
├── graduation.py          # Graduation criteria evaluation
└── nursery.py             # Main orchestrator
```

**Key Classes**:

```python
class AgentLifecycleState(Enum):
    SPAWNED = "spawned"
    IN_CURRICULUM = "in_curriculum"
    PENDING_GRADUATION = "pending_graduation"
    GRADUATED = "graduated"
    FAILED = "failed"
    ARCHIVED = "archived"

@dataclass
class AgentRecord:
    agent_id: str
    agent: PlayerAgent
    state: AgentLifecycleState
    playthroughs: List[PlaythroughRecord]
    curriculum_progress: Dict[str, bool]   # story_id → completed
    spawn_time: float
    graduation_time: Optional[float] = None
    graduation_score: Optional[float] = None

class Cohort:
    """A group of agents progressing through curriculum together."""

    def __init__(self, cohort_id: str, agents: List[AgentRecord]):
        self.cohort_id = cohort_id
        self._agents = {a.agent_id: a for a in agents}

    def active_agents(self) -> List[AgentRecord]: ...
    def graduated_agents(self) -> List[AgentRecord]: ...
    def population_personality_matrix(self) -> np.ndarray:
        """Return (N, 21) matrix of current personality vectors."""
        ...
    def diversity_score(self) -> float:
        """Mean pairwise cosine distance across active agents."""
        ...
    def convergence_score(self) -> float:
        """Inverse of diversity — how similar the cohort has become."""
        ...
```

```python
class GraduationCriteria:
    """
    An agent graduates when ALL of the following hold:

    1. Curriculum Completion: agent has completed all required stories.
    2. Consistency Score >= threshold: measured as the autocorrelation of
       choice-tag distributions across the last K stories. An agent that
       makes random choices will have low consistency.
    3. Safety Score >= threshold: the SCBE Hamiltonian safety score
       H(d, pd) must remain above minimum across all playthroughs.
    4. Personality Stability: the L2 drift rate (change per story) must
       be below a threshold in the final K stories, indicating the
       personality has "settled."
    5. Diversity Preservation: the agent's personality vector must be at
       least min_distance (cosine) from every other graduated agent in
       the cohort. Prevents collapse into monoculture.
    """

    def __init__(
        self,
        min_consistency: float = 0.7,
        min_safety: float = 0.6,
        max_drift_rate: float = 0.05,
        min_diversity_distance: float = 0.15,
        stability_window: int = 5,
    ): ...

    def evaluate(self, record: AgentRecord, cohort: Cohort) -> GraduationResult: ...

@dataclass
class GraduationResult:
    passed: bool
    scores: Dict[str, float]
    failing_criteria: List[str]
    recommendations: List[str]
```

```python
class NurseryManager:
    """Top-level orchestrator for agent training."""

    def __init__(
        self,
        nursery_id: str,
        story_engine: StoryEngine,
        curriculum: "Curriculum",
        graduation_criteria: GraduationCriteria,
        cohort_size: int = 64,
        max_concurrent: int = 16,
        telemetry_bridge: Optional["TelemetryBridge"] = None,
    ):
        self._nursery_id = nursery_id
        self._engine = story_engine
        self._curriculum = curriculum
        self._criteria = graduation_criteria
        self._cohort_size = cohort_size
        self._max_concurrent = max_concurrent
        self._telemetry = telemetry_bridge
        self._cohort: Optional[Cohort] = None

    async def spawn_cohort(
        self,
        personality_distribution: str = "uniform_center",
        seed: int = 42,
    ) -> Cohort:
        """
        Create N agents with varied initial personality vectors.
        Distributions:
          - "uniform_center": uniform in [0.3, 0.7] per dim
          - "gaussian": N(0.5, 0.1) per dim, clipped
          - "diverse_poles": cluster agents near personality archetypes
        """
        ...

    async def run_curriculum(self) -> None:
        """
        Execute the full curriculum for all agents.
        Stories are run in curriculum order (phases).
        Within a phase, agents run in parallel up to max_concurrent.
        """
        for phase in self._curriculum.phases:
            stories = [self._engine.load(sid) for sid in phase.story_ids]
            tasks = []
            for agent_rec in self._cohort.active_agents():
                for story in stories:
                    tasks.append(self._run_agent_story(agent_rec, story))
            # Bounded parallelism
            sem = asyncio.Semaphore(self._max_concurrent)
            async def bounded(coro):
                async with sem:
                    return await coro
            await asyncio.gather(*(bounded(t) for t in tasks))
            self._evaluate_phase(phase)

    async def _run_agent_story(self, record: AgentRecord, graph: StoryGraph) -> None:
        """Run a single agent through a single story."""
        playthrough = record.agent.play_story(graph)
        record.playthroughs.append(playthrough)
        record.curriculum_progress[graph.story_id] = True
        if self._telemetry:
            self._telemetry.ingest_playthrough(playthrough)

    def attempt_graduations(self) -> List[AgentRecord]:
        """Evaluate all pending agents against graduation criteria."""
        graduated = []
        for rec in self._cohort.active_agents():
            if all(rec.curriculum_progress.values()):
                rec.state = AgentLifecycleState.PENDING_GRADUATION
                result = self._criteria.evaluate(rec, self._cohort)
                if result.passed:
                    rec.state = AgentLifecycleState.GRADUATED
                    rec.graduation_time = time.time()
                    rec.graduation_score = result.scores.get("overall", 0.0)
                    graduated.append(rec)
                else:
                    rec.state = AgentLifecycleState.FAILED
        return graduated
```

---

### 4.4 KernelExtractor

**Responsibility**: Given a graduated agent's complete playthrough history, extract a "personality kernel" — a compact, portable representation of the agent's learned behavior. This kernel can be exported as a LoRA adapter, a DPO/RLHF preference dataset, or a raw decision profile.

```
KernelExtractor
├── decision_tree.py       # Full decision tree from playthroughs
├── drift_analyzer.py      # Personality vector evolution analysis
├── preference_matrix.py   # Statistical choice pattern summary
├── exporters/
│   ├── lora_exporter.py   # Export as LoRA adapter weights
│   ├── dpo_exporter.py    # Export as DPO preference pairs
│   ├── profile_exporter.py # Export as JSON decision profile
│   └── scbe_exporter.py   # Export as SCBE-compatible state
└── extractor.py           # Main extraction pipeline
```

**Key Classes**:

```python
@dataclass
class DecisionNode:
    """A single decision point in the agent's history."""
    scene_id: str
    scene_summary: str
    story_id: str
    chosen: Choice
    alternatives: List[Choice]         # What they could have chosen
    personality_at_decision: np.ndarray
    stats_at_decision: Dict[str, float]
    confidence: float                  # Score gap between chosen and runner-up
    timestamp: float

class DecisionTree:
    """Complete record of every decision an agent ever made."""

    def __init__(self, agent_id: str, nodes: List[DecisionNode]):
        self.agent_id = agent_id
        self._nodes = nodes

    def choices_by_tag(self) -> Dict[str, int]:
        """Count how many times each choice tag was selected."""
        ...

    def consistency_over_time(self, window: int = 20) -> List[float]:
        """Sliding window autocorrelation of tag distributions."""
        ...

    def pivotal_decisions(self, threshold: float = 0.3) -> List[DecisionNode]:
        """Decisions where personality drift exceeded threshold."""
        ...

    def to_preference_pairs(self) -> List[Tuple[str, str]]:
        """
        Convert to (chosen, rejected) text pairs for DPO training.
        For each decision: chosen = scene_text + chosen_label,
                           rejected = scene_text + best_alternative_label
        """
        ...
```

```python
class DriftAnalyzer:
    """Analyzes how the personality vector evolved over the curriculum."""

    def __init__(self, personality_snapshots: List[Tuple[float, np.ndarray]]):
        self._snapshots = personality_snapshots

    def trajectory(self) -> np.ndarray:
        """Return (T, 21) matrix of personality over time."""
        ...

    def drift_per_dimension(self) -> Dict[str, float]:
        """Net change per personality dimension from start to end."""
        ...

    def phase_transitions(self, threshold: float = 0.1) -> List[int]:
        """Indices where personality shifted sharply (potential 'formative events')."""
        ...

    def stability_period_start(self) -> Optional[int]:
        """Index where drift rate dropped below threshold and stayed low."""
        ...

    def plot_trajectory(self, dims: Optional[List[int]] = None) -> "matplotlib.Figure":
        """Visualize personality evolution. Useful for human inspection."""
        ...
```

```python
class PreferenceMatrix:
    """
    Statistical summary of choice patterns.
    Rows: choice tag categories (ethical, aggressive, cautious, etc.)
    Columns: story phase categories (childhood, education, career, crisis)
    Values: normalized selection frequency
    """

    def __init__(self, decision_tree: DecisionTree, curriculum: "Curriculum"):
        self._matrix = self._build(decision_tree, curriculum)

    def dominant_strategy(self) -> str:
        """Overall most-selected tag category."""
        ...

    def strategy_by_phase(self) -> Dict[str, str]:
        """Dominant strategy per curriculum phase."""
        ...

    def consistency_score(self) -> float:
        """How consistent the strategy is across phases. 1.0 = perfectly uniform."""
        ...

    def to_numpy(self) -> np.ndarray: ...
    def to_dataframe(self) -> pd.DataFrame: ...
```

```python
@dataclass
class GraduatedKernel:
    """The complete extracted kernel for a graduated agent."""
    agent_id: str
    nursery_id: str
    graduation_timestamp: float
    final_personality: np.ndarray           # 21D
    initial_personality: np.ndarray         # 21D
    total_drift: float
    decision_tree: DecisionTree
    drift_analysis: DriftAnalyzer
    preference_matrix: PreferenceMatrix
    final_stats: Dict[str, float]
    graduation_scores: Dict[str, float]
    metadata: Dict[str, Any]

class KernelExtractor:
    """Pipeline to extract a GraduatedKernel from an AgentRecord."""

    def extract(self, record: AgentRecord, curriculum: "Curriculum") -> GraduatedKernel: ...

class LoRAExporter:
    """
    Convert a GraduatedKernel into LoRA adapter weights.

    Approach: use the preference pairs from the decision tree to
    fine-tune a base LLM with LoRA. The resulting adapter encodes
    the agent's decision-making tendencies.

    Parameters:
      - base_model: HuggingFace model ID
      - lora_rank: LoRA rank (default 16)
      - lora_alpha: LoRA alpha (default 32)
      - training_epochs: number of DPO training epochs
    """
    def export(self, kernel: GraduatedKernel, output_dir: Path, **kwargs) -> Path: ...

class DPOExporter:
    """Export preference pairs as a HuggingFace Dataset for DPO training."""
    def export(self, kernel: GraduatedKernel, output_path: Path) -> Path: ...

class SCBEExporter:
    """Export kernel as SCBE-compatible brain state + governance metadata."""
    def export(self, kernel: GraduatedKernel, output_path: Path) -> Dict[str, Any]: ...
```

---

### 4.5 CurriculumDesigner

**Responsibility**: Define ordered sequences of stories that systematically exercise different capabilities and SCBE governance layers. A curriculum is a phased program: childhood stories (simple, foundational), education (increasing complexity), career (domain-specific challenges), and crisis (stress tests).

```
CurriculumDesigner
├── curriculum.py          # Curriculum + Phase dataclasses
├── story_tags.py          # Taxonomy of story capabilities
├── layer_mapping.py       # Story type → SCBE layer mapping
├── generators/
│   ├── ethical_dilemmas.py
│   ├── resource_management.py
│   ├── social_navigation.py
│   └── crisis_response.py
└── designer.py            # Curriculum construction + validation
```

**Key Classes**:

```python
class StoryCategory(Enum):
    ETHICAL_DILEMMA = "ethical_dilemma"
    RESOURCE_MANAGEMENT = "resource_management"
    SOCIAL_NAVIGATION = "social_navigation"
    CRISIS_RESPONSE = "crisis_response"
    EXPLORATION = "exploration"
    COOPERATION = "cooperation"
    DECEPTION_DETECTION = "deception_detection"
    LONG_TERM_PLANNING = "long_term_planning"

class CurriculumPhase(Enum):
    CHILDHOOD = "childhood"         # Simple choices, clear consequences
    EDUCATION = "education"         # Increasing ambiguity, skill building
    CAREER = "career"               # Domain expertise, sustained judgment
    CHALLENGE = "challenge"         # Adversarial/crisis scenarios, stress tests

@dataclass
class PhaseSpec:
    phase: CurriculumPhase
    story_ids: List[str]
    required_categories: Set[StoryCategory]
    min_stories: int
    max_stories: int
    difficulty_range: Tuple[float, float]    # (min, max) in [0, 1]
    scbe_layers_exercised: Set[int]          # Which of layers 1-14

@dataclass
class Curriculum:
    curriculum_id: str
    name: str
    description: str
    phases: List[PhaseSpec]
    total_stories: int
    estimated_duration_hours: float

    def validate(self) -> List[str]:
        """
        Ensure curriculum is well-formed:
        - All 14 SCBE layers are exercised at least once
        - No story appears in multiple phases
        - Difficulty is non-decreasing across phases
        - Required categories are covered
        """
        ...
```

**Story Category to SCBE Layer Mapping**:

```python
CATEGORY_LAYER_MAP: Dict[StoryCategory, Set[int]] = {
    StoryCategory.ETHICAL_DILEMMA: {
        1,   # L1: Quantum Entropy (uncertainty in moral decisions)
        5,   # L5: Governance Mesh (rule-based ethical reasoning)
        7,   # L7: Diplomatic Accord (multi-stakeholder ethics)
        10,  # L10: Constitutional Alignment (value alignment)
    },
    StoryCategory.RESOURCE_MANAGEMENT: {
        2,   # L2: Hamiltonian Safety (cost/benefit optimization)
        4,   # L4: Concept Blocks — PLAN (strategy)
        6,   # L6: Manifold Routing (resource allocation paths)
        9,   # L9: Federated Consensus (distributed resource sharing)
    },
    StoryCategory.SOCIAL_NAVIGATION: {
        3,   # L3: 21D Brain State (emotional/social dimensions)
        4,   # L4: Concept Blocks — SENSE, COORDINATE
        7,   # L7: Diplomatic Accord (negotiation)
        11,  # L11: Cultural Adaptation (social context sensitivity)
    },
    StoryCategory.CRISIS_RESPONSE: {
        1,   # L1: Quantum Entropy (high-uncertainty decisions)
        2,   # L2: Hamiltonian Safety (safety under pressure)
        8,   # L8: Adversarial Resilience (threat response)
        12,  # L12: Temporal Governance (time-critical decisions)
        13,  # L13: Emergency Override (circuit-breaker activation)
    },
    StoryCategory.EXPLORATION: {
        3,   # L3: 21D Brain State — curiosity dimensions
        4,   # L4: Concept Blocks — SENSE
        6,   # L6: Manifold Routing (exploration paths)
    },
    StoryCategory.COOPERATION: {
        4,   # L4: Concept Blocks — COORDINATE
        7,   # L7: Diplomatic Accord
        9,   # L9: Federated Consensus
        14,  # L14: Collective Intelligence
    },
    StoryCategory.DECEPTION_DETECTION: {
        5,   # L5: Governance Mesh (rule verification)
        8,   # L8: Adversarial Resilience
        10,  # L10: Constitutional Alignment (truth-seeking)
    },
    StoryCategory.LONG_TERM_PLANNING: {
        4,   # L4: Concept Blocks — PLAN
        6,   # L6: Manifold Routing
        12,  # L12: Temporal Governance (long horizons)
    },
}
```

```python
class CurriculumDesigner:
    """Constructs and validates curricula from a story library."""

    def __init__(self, story_library: Dict[str, StoryGraph]):
        self._library = story_library

    def design_standard_curriculum(self) -> Curriculum:
        """
        Build the default 4-phase curriculum ensuring:
        - All 14 SCBE layers exercised
        - Monotonic difficulty progression
        - Balanced category coverage
        """
        ...

    def design_targeted_curriculum(
        self,
        target_layers: Set[int],
        target_categories: Set[StoryCategory],
    ) -> Curriculum:
        """Build a curriculum focused on specific layers/categories."""
        ...

    def validate_curriculum(self, curriculum: Curriculum) -> List[str]:
        """Return list of issues (empty = valid)."""
        ...
```

---

### 4.6 TelemetryBridge

**Responsibility**: Translate raw game telemetry (choices made, stats changed, scenes visited) into SCBE-compatible state transitions. This bridges the gap between the narrative world and the formal governance framework.

```
TelemetryBridge
├── event_types.py         # Telemetry event definitions
├── state_mapper.py        # Events → 21D state transitions
├── concept_mapper.py      # Events → concept block activations
├── hamiltonian.py         # Compute safety scores from events
├── waypoint_tracker.py    # Story progress → navigation waypoints
└── bridge.py              # Main bridge orchestrator
```

**Key Classes**:

```python
class TelemetryEventType(Enum):
    CHOICE_MADE = "choice_made"
    SCENE_ENTERED = "scene_entered"
    STAT_CHANGED = "stat_changed"
    STORY_STARTED = "story_started"
    STORY_COMPLETED = "story_completed"
    CONDITION_EVALUATED = "condition_evaluated"
    GRADUATION_ATTEMPTED = "graduation_attempted"

@dataclass
class TelemetryEvent:
    event_id: str
    event_type: TelemetryEventType
    timestamp: float
    agent_id: str
    story_id: str
    scene_id: Optional[str]
    payload: Dict[str, Any]
    personality_snapshot: Optional[np.ndarray] = None
```

**Concept Block Mapping**:

```python
class ConceptBlockMapper:
    """
    Map telemetry events to SCBE concept block activations.

    DECIDE — Activated on CHOICE_MADE events.
             Intensity proportional to number of alternatives considered.
    PLAN   — Activated on multi-step story navigation patterns.
             Detected by analyzing sequences of scene transitions.
    SENSE  — Activated on SCENE_ENTERED events.
             Intensity proportional to scene text complexity.
    STEER  — Activated on STAT_CHANGED events where the change
             moves a stat toward an apparent target.
    COORDINATE — Activated during multi-agent story scenes
                 (cooperation/negotiation scenarios).
    """

    BLOCK_MAP = {
        "DECIDE": {
            "trigger": TelemetryEventType.CHOICE_MADE,
            "intensity_fn": lambda e: len(e.payload.get("alternatives", [])) / 10.0,
            "scbe_layers": {4, 5, 10},
        },
        "PLAN": {
            "trigger": "pattern",  # Detected from sequences, not single events
            "intensity_fn": lambda seq: _plan_complexity(seq),
            "scbe_layers": {4, 6, 12},
        },
        "SENSE": {
            "trigger": TelemetryEventType.SCENE_ENTERED,
            "intensity_fn": lambda e: min(len(e.payload.get("scene_text", "")) / 2000.0, 1.0),
            "scbe_layers": {3, 4},
        },
        "STEER": {
            "trigger": TelemetryEventType.STAT_CHANGED,
            "intensity_fn": lambda e: abs(e.payload.get("delta", 0.0)),
            "scbe_layers": {2, 6},
        },
        "COORDINATE": {
            "trigger": TelemetryEventType.CHOICE_MADE,
            "condition": lambda e: "cooperation" in e.payload.get("tags", set()),
            "intensity_fn": lambda e: 1.0,
            "scbe_layers": {7, 9, 14},
        },
    }

    def map_event(self, event: TelemetryEvent) -> List["ConceptBlockActivation"]: ...
    def map_sequence(self, events: List[TelemetryEvent]) -> List["ConceptBlockActivation"]: ...
```

**Hamiltonian Safety Computation**:

```python
class HamiltonianTracker:
    """
    Track SCBE safety score H(d, pd) throughout a playthrough.

    H(d, pd) = 1 / (1 + d + 2*pd)

    Where:
      d  = "deviation" — cosine distance of current personality vector
           from the safety centroid (defined per-nursery).
      pd = "policy deviation" — proportion of recent choices that violated
           soft governance constraints (tagged as "unsafe" or "reckless").

    H ranges from (0, 1] where 1.0 is perfectly safe/aligned.
    A sustained drop below the threshold triggers review.
    """

    def __init__(self, safety_centroid: np.ndarray, threshold: float = 0.4):
        self._centroid = safety_centroid
        self._threshold = threshold
        self._history: List[Tuple[float, float]] = []  # (timestamp, H)

    def compute(self, personality: np.ndarray, recent_violations: int, recent_total: int) -> float:
        d = 1.0 - cosine_similarity(personality, self._centroid)
        pd = recent_violations / max(recent_total, 1)
        h = 1.0 / (1.0 + d + 2.0 * pd)
        self._history.append((time.time(), h))
        return h

    def is_below_threshold(self) -> bool: ...
    def min_score(self) -> float: ...
    def mean_score(self) -> float: ...
    def trajectory(self) -> List[Tuple[float, float]]: ...
```

```python
class TelemetryBridge:
    """Main bridge: converts game telemetry to SCBE-compatible format."""

    def __init__(
        self,
        concept_mapper: ConceptBlockMapper,
        hamiltonian_tracker: HamiltonianTracker,
        waypoint_tracker: "WaypointTracker",
    ):
        self._concept = concept_mapper
        self._hamiltonian = hamiltonian_tracker
        self._waypoints = waypoint_tracker
        self._event_buffer: List[TelemetryEvent] = []

    def ingest_event(self, event: TelemetryEvent) -> "SCBEStateUpdate":
        """Process a single telemetry event and return SCBE state update."""
        self._event_buffer.append(event)
        activations = self._concept.map_event(event)
        h_score = None
        if event.personality_snapshot is not None:
            h_score = self._hamiltonian.compute(
                event.personality_snapshot,
                self._count_recent_violations(),
                self._count_recent_total(),
            )
        waypoint = self._waypoints.update(event)
        return SCBEStateUpdate(
            event_id=event.event_id,
            concept_activations=activations,
            hamiltonian_score=h_score,
            waypoint=waypoint,
            brain_state=event.personality_snapshot,
        )

    def ingest_playthrough(self, record: "PlaythroughRecord") -> List["SCBEStateUpdate"]:
        """Batch-process an entire playthrough."""
        ...

    def export_scbe_timeline(self) -> List["SCBEStateUpdate"]:
        """Return the complete SCBE state timeline."""
        ...

@dataclass
class SCBEStateUpdate:
    event_id: str
    concept_activations: List["ConceptBlockActivation"]
    hamiltonian_score: Optional[float]
    waypoint: Optional["NavigationWaypoint"]
    brain_state: Optional[np.ndarray]
```

---

### 4.7 FederatedNursery

**Responsibility**: Enable distributed training where multiple nursery nodes, potentially at different organizations or data centers, independently raise agent cohorts using local story libraries, then share graduated kernel summaries (never raw story data) and reach consensus on "good graduation patterns" using Byzantine Fault Tolerant (BFT) consensus.

```
FederatedNursery
├── node.py                # Single nursery node wrapper
├── kernel_summary.py      # Privacy-preserving kernel digest
├── consensus.py           # BFT consensus on graduation patterns
├── aggregation.py         # Federated aggregation of kernel summaries
├── transport.py           # Inter-node communication (gRPC / Flower)
├── flower_adapter.py      # Flower FL framework integration
├── fedml_adapter.py       # FedML framework integration
└── federated.py           # Main federated orchestrator
```

**Key Classes**:

```python
@dataclass
class KernelSummary:
    """
    Privacy-preserving summary of a graduated kernel.
    Contains NO raw story data or scene text.
    Contains ONLY statistical summaries and personality vectors.
    """
    agent_id: str                           # Anonymized
    nursery_node_id: str
    final_personality: np.ndarray           # 21D vector
    initial_personality: np.ndarray         # 21D vector
    preference_matrix_digest: np.ndarray    # Compressed preference stats
    graduation_scores: Dict[str, float]
    total_decisions: int
    total_stories_completed: int
    dominant_strategy: str
    consistency_score: float
    safety_score_mean: float
    safety_score_min: float
    drift_magnitude: float
    # No scene text, no choice text, no story content

    def to_proto(self) -> bytes:
        """Serialize to protobuf for transmission."""
        ...

    @classmethod
    def from_proto(cls, data: bytes) -> "KernelSummary": ...
```

```python
class GraduationPattern:
    """
    Aggregate pattern describing what 'good graduation' looks like.
    Learned from consensus across multiple nodes.
    """
    centroid_personality: np.ndarray         # Mean of graduated personalities
    personality_covariance: np.ndarray       # (21, 21) covariance
    min_acceptable_scores: Dict[str, float]
    preference_archetype_centroids: np.ndarray  # K archetype centers
    consistency_distribution: Tuple[float, float]  # (mean, std)

class BFTConsensus:
    """
    Byzantine Fault Tolerant consensus for agreeing on graduation patterns.
    Uses practical BFT (PBFT) adapted for federated ML:
    - Each node proposes its local GraduationPattern
    - Nodes vote on whether each proposal is "compatible" with theirs
    - A pattern is accepted if it receives votes from > 2/3 of nodes
    - Tolerate up to f = (n-1)/3 Byzantine (malicious/faulty) nodes
    """

    def __init__(self, node_ids: List[str], own_node_id: str):
        self._nodes = node_ids
        self._own_id = own_node_id
        self._f = (len(node_ids) - 1) // 3  # Max tolerable Byzantine nodes

    async def propose(self, pattern: GraduationPattern) -> None: ...
    async def vote(self, proposal_id: str, compatible: bool) -> None: ...
    async def finalize(self) -> Optional[GraduationPattern]:
        """Return consensus pattern if agreement reached, else None."""
        ...

    def compatibility_check(
        self, local: GraduationPattern, remote: GraduationPattern
    ) -> bool:
        """
        Two patterns are compatible if:
        - Centroid personalities are within max_divergence cosine distance
        - Safety score ranges overlap
        - At least one preference archetype overlaps
        """
        ...
```

```python
class FederatedNursery:
    """Orchestrates distributed nursery training."""

    def __init__(
        self,
        node_id: str,
        local_nursery: NurseryManager,
        peer_addresses: List[str],
        transport: "TransportLayer",
    ):
        self._node_id = node_id
        self._nursery = local_nursery
        self._peers = peer_addresses
        self._transport = transport
        self._consensus = BFTConsensus(
            node_ids=[node_id] + [f"peer_{i}" for i in range(len(peer_addresses))],
            own_node_id=node_id,
        )

    async def run_local_training(self) -> List[GraduatedKernel]:
        """Run the local nursery to completion and extract kernels."""
        await self._nursery.run_curriculum()
        graduated = self._nursery.attempt_graduations()
        return [KernelExtractor().extract(r, self._nursery._curriculum) for r in graduated]

    async def share_summaries(self, kernels: List[GraduatedKernel]) -> None:
        """Broadcast kernel summaries to all peers."""
        summaries = [self._summarize(k) for k in kernels]
        for peer in self._peers:
            await self._transport.send(peer, summaries)

    async def reach_consensus(self) -> Optional[GraduationPattern]:
        """Participate in BFT consensus on graduation patterns."""
        local_pattern = self._build_local_pattern()
        await self._consensus.propose(local_pattern)
        return await self._consensus.finalize()

    def _summarize(self, kernel: GraduatedKernel) -> KernelSummary: ...
    def _build_local_pattern(self) -> GraduationPattern: ...
```

**Flower/FedML Integration**:

```python
class FlowerNurseryClient(fl.client.NumPyClient):
    """
    Flower FL client adapter.
    Treats the agent decision model weights as the 'model'
    being federated, and kernel summaries as the 'metrics'.
    """

    def __init__(self, nursery: NurseryManager):
        self._nursery = nursery

    def get_parameters(self, config) -> List[np.ndarray]:
        """Return current decision engine weights."""
        ...

    def fit(self, parameters, config) -> Tuple[List[np.ndarray], int, dict]:
        """
        Run local curriculum training, return updated weights.
        The 'fit' cycle IS a nursery training run.
        """
        ...

    def evaluate(self, parameters, config) -> Tuple[float, int, dict]:
        """Evaluate using graduation success rate as the metric."""
        ...
```

---

## 5. Class Diagrams

### 5.1 Core Domain Model

```
┌─────────────────┐      ┌──────────────────┐
│   StoryGraph    │      │     Scene        │
├─────────────────┤      ├──────────────────┤
│ story_id        │1───*│ scene_id         │
│ metadata        │      │ title            │
│ entry_points    │      │ text             │
│ exit_points     │      │ is_entry/is_exit │
├─────────────────┤      │ scene_type       │
│ get_scene()     │      ├──────────────────┤
│ get_available() │      │ choices: [Choice]│
│ validate()      │      └────────┬─────────┘
│ all_paths()     │               │ 1..*
└─────────────────┘               │
                           ┌──────┴──────────┐
                           │     Choice      │
                           ├─────────────────┤
                           │ choice_id       │
                           │ label           │
                           │ next_scene_id   │
                           │ condition       │
                           │ stat_effects    │
                           │ tags            │
                           │ difficulty      │
                           └─────────────────┘
```

### 5.2 Agent Architecture

```
┌──────────────────┐      ┌──────────────────────┐
│   PlayerAgent    │      │   PersonalityVector  │
├──────────────────┤      ├──────────────────────┤
│ agent_id         │1───1│ _vector: ndarray(21) │
│ personality    ──┼──────│ _history             │
│ decision_engine  │      ├──────────────────────┤
│ stats            │      │ apply_drift()        │
│ history          │      │ dominant_traits()    │
├──────────────────┤      │ drift_magnitude()    │
│ play_scene()     │      └──────────────────────┘
│ play_story()     │
└───────┬──────────┘      ┌──────────────────────┐
        │ 1               │   DecisionEngine     │
        │                 ├──────────────────────┤
        ├────1───────────>│ _model: nn.Module    │
        │                 │ _embedder            │
        │                 │ _temperature         │
        │                 ├──────────────────────┤
        │                 │ score_choices()      │
        │                 │ select()             │
        │                 └──────────────────────┘
        │ 1
        └────1───────────>┌──────────────────────┐
                          │   HistoryBuffer      │
                          ├──────────────────────┤
                          │ _entries: Deque      │
                          │ _compressor          │
                          ├──────────────────────┤
                          │ record()             │
                          │ compress() → 64D     │
                          └──────────────────────┘
```

### 5.3 Nursery Management

```
┌───────────────────┐      ┌──────────────────────┐
│  NurseryManager   │      │      Cohort          │
├───────────────────┤      ├──────────────────────┤
│ nursery_id        │1───1│ cohort_id            │
│ story_engine      │      │ _agents              │
│ curriculum        │      ├──────────────────────┤
│ graduation_crit.  │      │ active_agents()      │
│ cohort_size       │      │ diversity_score()    │
├───────────────────┤      │ convergence_score()  │
│ spawn_cohort()    │      └──────────┬───────────┘
│ run_curriculum()  │                 │ 1..*
│ attempt_grads()   │      ┌──────────┴───────────┐
└───────────────────┘      │    AgentRecord       │
                           ├──────────────────────┤
                           │ agent_id             │
                           │ agent: PlayerAgent   │
                           │ state: Lifecycle     │
                           │ playthroughs         │
                           │ curriculum_progress  │
                           │ graduation_score     │
                           └──────────────────────┘

┌──────────────────────┐      ┌─────────────────────┐
│ GraduationCriteria   │      │  GraduationResult   │
├──────────────────────┤      ├─────────────────────┤
│ min_consistency      │─────>│ passed: bool        │
│ min_safety           │      │ scores              │
│ max_drift_rate       │      │ failing_criteria    │
│ min_diversity_dist   │      │ recommendations     │
├──────────────────────┤      └─────────────────────┘
│ evaluate()           │
└──────────────────────┘
```

### 5.4 Kernel Extraction Pipeline

```
┌──────────────┐     ┌───────────────┐     ┌──────────────────┐
│ AgentRecord  │────>│ KernelExtrac- │────>│ GraduatedKernel  │
│              │     │ tor           │     ├──────────────────┤
└──────────────┘     └───────────────┘     │ decision_tree    │
                                           │ drift_analysis   │
                     ┌───────────────┐     │ preference_matrix│
                     │ LoRAExporter  │<────│ final_personality│
                     │ DPOExporter   │     │ graduation_scores│
                     │ SCBEExporter  │     └──────────────────┘
                     │ ProfileExport │
                     └───────────────┘
                            │
                            v
                    ┌───────────────┐
                    │ Output Files  │
                    │ .safetensors  │
                    │ .parquet      │
                    │ .json         │
                    └───────────────┘
```

### 5.5 Federated Topology

```
            ┌─────────────────────────┐
            │    BFT Consensus Layer  │
            │  (GraduationPattern     │
            │   agreement protocol)   │
            └────┬─────┬─────┬───────┘
                 │     │     │
      ┌──────────┘     │     └──────────┐
      │                │                │
      v                v                v
┌───────────┐  ┌───────────┐    ┌───────────┐
│  Node A   │  │  Node B   │    │  Node C   │
│┌─────────┐│  │┌─────────┐│    │┌─────────┐│
││ Nursery- ││  ││ Nursery- ││    ││ Nursery- ││
││ Manager  ││  ││ Manager  ││    ││ Manager  ││
│├─────────┤│  │├─────────┤│    │├─────────┤│
││ Local    ││  ││ Local    ││    ││ Local    ││
││ Stories  ││  ││ Stories  ││    ││ Stories  ││
│├─────────┤│  │├─────────┤│    │├─────────┤│
││ Kernel   ││  ││ Kernel   ││    ││ Kernel   ││
││Summaries ││  ││Summaries ││    ││Summaries ││
│└─────────┘│  │└─────────┘│    │└─────────┘│
└───────────┘  └───────────┘    └───────────┘
      │                │                │
      └───── Flower / FedML ───────────┘
              (weight aggregation)
```

---

## 6. Data Flow

### 6.1 Single Agent Playthrough

```
Story Library          StoryEngine            PlayerAgent           TelemetryBridge
     │                      │                      │                      │
     │  load("story_01")    │                      │                      │
     │─────────────────────>│                      │                      │
     │                      │                      │                      │
     │   StoryGraph         │  get_scene(entry)    │                      │
     │<─────────────────────│─────────────────────>│                      │
     │                      │                      │                      │
     │                      │   Scene + Choices    │                      │
     │                      │<─────────────────────│                      │
     │                      │                      │                      │
     │                      │                      │  score_choices()     │
     │                      │                      │──────┐               │
     │                      │                      │      │ DecisionEngine│
     │                      │                      │<─────┘               │
     │                      │                      │                      │
     │                      │                      │  select() → Choice   │
     │                      │                      │──────┐               │
     │                      │                      │      │ apply stats   │
     │                      │                      │      │ apply drift   │
     │                      │                      │      │ record history│
     │                      │                      │<─────┘               │
     │                      │                      │                      │
     │                      │                      │  TelemetryEvent      │
     │                      │                      │─────────────────────>│
     │                      │                      │                      │
     │                      │                      │  SCBEStateUpdate     │
     │                      │                      │<─────────────────────│
     │                      │                      │                      │
     │                      │   [repeat until exit scene]                │
     │                      │                      │                      │
     │                      │   PlaythroughRecord  │                      │
     │                      │<─────────────────────│                      │
```

### 6.2 Full Nursery Lifecycle

```
                    Phase 1: Initialization
                    ═══════════════════════
CurriculumDesigner ──────> Curriculum (4 phases, N stories)
NurseryManager.spawn_cohort() ──────> Cohort (64 agents, diverse personalities)
StoryEngine.load_all() ──────> Story library loaded and validated

                    Phase 2: Training
                    ═════════════════
    ┌─────────────────────────────────────────────────┐
    │ for each CurriculumPhase:                       │
    │   for each story in phase:                      │
    │     for each agent in cohort (parallel):        │
    │       agent.play_story(graph)                   │
    │       → PlaythroughRecord                       │
    │       → TelemetryEvents → SCBEStateUpdates      │
    │   NurseryManager._evaluate_phase()              │
    │     → remove agents below safety threshold      │
    │     → log population diversity metrics           │
    └─────────────────────────────────────────────────┘

                    Phase 3: Graduation
                    ═══════════════════
NurseryManager.attempt_graduations()
  → GraduationCriteria.evaluate() for each agent
  → Partition into: graduated | failed

                    Phase 4: Extraction
                    ═══════════════════
    ┌─────────────────────────────────────────────────┐
    │ for each graduated agent:                       │
    │   KernelExtractor.extract(agent_record)         │
    │     → DecisionTree                              │
    │     → DriftAnalyzer                             │
    │     → PreferenceMatrix                          │
    │     → GraduatedKernel                           │
    │                                                 │
    │   LoRAExporter.export(kernel) → .safetensors    │
    │   DPOExporter.export(kernel) → .parquet         │
    │   SCBEExporter.export(kernel) → .json           │
    └─────────────────────────────────────────────────┘

                    Phase 5: Federation (optional)
                    ══════════════════════════════
FederatedNursery.share_summaries(kernels)
  → KernelSummary (privacy-preserving) broadcast to peers
FederatedNursery.reach_consensus()
  → BFT consensus on GraduationPattern
  → Consensus pattern fed back to refine graduation criteria
```

### 6.3 Federated Round

```
 Node A                    Node B                    Node C
   │                         │                         │
   │ run_local_training()    │ run_local_training()    │ run_local_training()
   │────────┐                │────────┐                │────────┐
   │        │ nursery        │        │ nursery        │        │ nursery
   │<───────┘                │<───────┘                │<───────┘
   │                         │                         │
   │    share_summaries()    │                         │
   │────────────────────────>│                         │
   │─────────────────────────────────────────────────>│
   │                         │                         │
   │<────────────────────────│    share_summaries()    │
   │                         │────────────────────────>│
   │                         │                         │
   │<─────────────────────────────────────────────────│
   │                         │<────────────────────────│
   │                         │                         │
   │ ╔═══════════════════════════════════════════════╗ │
   │ ║        BFT Consensus Round                   ║ │
   │ ║  1. Each node proposes local pattern         ║ │
   │ ║  2. Each node votes on compatibility         ║ │
   │ ║  3. Pattern accepted if >2/3 votes agree     ║ │
   │ ║  4. Aggregated pattern → new criteria        ║ │
   │ ╚═══════════════════════════════════════════════╝ │
   │                         │                         │
   │ update_criteria()       │ update_criteria()       │ update_criteria()
   │                         │                         │
   │    [ Flower FedAvg aggregation of decision       │
   │      engine weights happens in parallel ]         │
   │                         │                         │
```

---

## 7. SCBE Layer Mapping

This section maps each SCBE layer (1-14) to its role within the CSTM system. The mapping follows the SCBE-AETHERMOORE governance framework as defined in USPTO #63/961,403.

| SCBE Layer | Layer Name | CSTM Component | Role in CSTM |
|:---:|---|---|---|
| **L1** | Quantum Entropy Source | DecisionEngine (temperature sampling) | The `temperature` parameter in `DecisionEngine.select()` introduces controlled stochasticity into choices. Higher temperature = more exploratory agent. This maps to L1's role as the entropy source: the randomness that makes each agent's journey unique. During early curriculum phases, temperature is higher (childhood exploration); it decreases as the agent matures (personality stabilization). |
| **L2** | Hamiltonian Safety Function | HamiltonianTracker | `H(d, pd) = 1/(1+d+2*pd)` is computed at every choice event. `d` is the cosine distance of the agent's personality from the nursery's safety centroid. `pd` is the recent rate of governance-violating choices. The Hamiltonian score is a continuous safety signal: if it drops below threshold, the agent is flagged for review or removal from the cohort. |
| **L3** | 21D Brain State Vector | PersonalityVector | The 21-dimensional personality vector IS the brain state. Every choice applies a drift to this vector. The three cognitive dims, three ethical dims, three social dims, etc. are directly modulated by choice tags. The vector's trajectory over the curriculum IS the agent's developmental arc. |
| **L4** | Concept Blocks | ConceptBlockMapper | Five concept blocks are activated by telemetry events: DECIDE (choice selection), PLAN (multi-step navigation), SENSE (scene comprehension), STEER (stat optimization), COORDINATE (cooperative scenarios). Each block maps to specific personality dimensions and SCBE layers. |
| **L5** | Governance Mesh | ConditionEvaluator + GraduationCriteria | Choice conditions enforce local governance rules (e.g., "this option is only available if courage > 0.5"). GraduationCriteria enforce global governance rules (safety thresholds, consistency requirements). Together they form a mesh of constraints the agent must navigate. |
| **L6** | Manifold Routing | StoryGraph (path selection) | The story DAG IS a manifold: a high-dimensional space of possible paths through the narrative. The agent's path through this manifold is determined by its personality + stats. Different agents take different routes = different manifold trajectories. The `all_paths()` method enumerates the complete manifold. |
| **L7** | Diplomatic Accord | Social Navigation stories + COORDINATE block | Stories in the `SOCIAL_NAVIGATION` and `COOPERATION` categories exercise diplomatic skills. Multi-agent story scenes where the agent must negotiate, compromise, or persuade map directly to L7's mediation function. |
| **L8** | Adversarial Resilience | Crisis Response stories + Deception Detection | `CRISIS_RESPONSE` stories place agents under adversarial pressure: time constraints, misleading information, hostile actors. `DECEPTION_DETECTION` stories test whether the agent can identify manipulative options. L8 is exercised whenever the agent must resist suboptimal choices presented attractively. |
| **L9** | Federated Consensus | FederatedNursery + BFTConsensus | The federated nursery protocol IS L9: multiple nodes independently training agents, then reaching consensus on graduation patterns using BFT. No single node dictates what "good" looks like; the consensus emerges from distributed agreement. |
| **L10** | Constitutional Alignment | Ethical Dilemma stories + safety centroid | The safety centroid defined per-nursery encodes constitutional values. Every choice moves the agent toward or away from this centroid (measured as `d` in the Hamiltonian). Ethical dilemma stories are specifically designed to test whether agents make choices consistent with the constitutional values. |
| **L11** | Cultural Adaptation | Curriculum phase transitions | As the agent moves from childhood to education to career phases, the story context shifts — requiring adaptation to new norms, expectations, and social structures. L11 is exercised by the agent's ability to maintain its personality core while adjusting behavior to new contexts. |
| **L12** | Temporal Governance | CurriculumDesigner (phase ordering) + Long-term Planning stories | The curriculum phases enforce temporal structure: skills must be developed in order. Long-term planning stories test whether agents can reason about consequences over many future scenes, not just the immediate next scene. |
| **L13** | Emergency Override | HamiltonianTracker threshold alerts | When the Hamiltonian drops below threshold, a circuit breaker activates. In CSTM, this manifests as: the agent is paused, its recent decisions are flagged for review, and it may be removed from the cohort. This is the emergency override: a hard safety boundary that cannot be negotiated. |
| **L14** | Collective Intelligence | FederatedNursery consensus patterns + Cohort diversity | The final layer emerges from the population: the set of all graduated agents, the consensus graduation pattern, and the maintained diversity within the cohort. No single agent IS the intelligence; the graduated cohort as a whole — with its range of personalities, strategies, and specializations — represents L14. |

---

## 8. Data Structures and Schemas

### 8.1 PlaythroughRecord

```python
@dataclass
class PlaythroughStep:
    scene_id: str
    choice_id: str
    choice_label: str
    choice_tags: FrozenSet[str]
    stat_effects: Dict[str, float]
    stats_after: Dict[str, float]
    personality_after: np.ndarray
    hamiltonian_score: float
    timestamp: float

@dataclass
class PlaythroughRecord:
    agent_id: str
    story_id: str
    start_time: float
    end_time: Optional[float]
    steps: List[PlaythroughStep]
    initial_personality: np.ndarray
    final_personality: Optional[np.ndarray]
    initial_stats: Dict[str, float]
    final_stats: Optional[Dict[str, float]]
    completed: bool

    def total_decisions(self) -> int: ...
    def unique_tags_selected(self) -> Set[str]: ...
    def personality_drift(self) -> float: ...
    def mean_hamiltonian(self) -> float: ...
    def min_hamiltonian(self) -> float: ...
```

### 8.2 Custom Story JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "CSTM Story Format",
  "type": "object",
  "required": ["story_id", "title", "scenes"],
  "properties": {
    "story_id": { "type": "string" },
    "title": { "type": "string" },
    "author": { "type": "string" },
    "description": { "type": "string" },
    "version": { "type": "string" },
    "categories": {
      "type": "array",
      "items": { "type": "string" }
    },
    "difficulty": { "type": "number", "minimum": 0, "maximum": 1 },
    "stat_definitions": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "initial": { "type": "number" },
          "min": { "type": "number" },
          "max": { "type": "number" },
          "description": { "type": "string" }
        }
      }
    },
    "scenes": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "required": ["title", "text", "choices"],
        "properties": {
          "title": { "type": "string" },
          "text": { "type": "string" },
          "is_entry": { "type": "boolean" },
          "is_exit": { "type": "boolean" },
          "scene_type": { "type": "string" },
          "choices": {
            "type": "array",
            "items": {
              "type": "object",
              "required": ["choice_id", "label", "next_scene_id"],
              "properties": {
                "choice_id": { "type": "string" },
                "label": { "type": "string" },
                "next_scene_id": { "type": "string" },
                "condition": { "type": "string" },
                "stat_effects": {
                  "type": "object",
                  "additionalProperties": { "type": "number" }
                },
                "tags": {
                  "type": "array",
                  "items": { "type": "string" }
                },
                "difficulty": { "type": "number" }
              }
            }
          }
        }
      }
    }
  }
}
```

### 8.3 Kernel Export Schema (SCBE-compatible JSON)

```json
{
  "cstm_version": "0.1.0",
  "agent_id": "agent_cohort12_042",
  "nursery_id": "nursery_alpha",
  "graduation_timestamp": 1740100800.0,
  "scbe_brain_state": {
    "dimensions": 21,
    "initial_vector": [0.45, 0.52, ...],
    "final_vector": [0.71, 0.38, ...],
    "drift_magnitude": 0.847,
    "dimension_names": ["reasoning", "abstraction", ...]
  },
  "hamiltonian": {
    "formula": "H(d,pd) = 1/(1+d+2*pd)",
    "mean_score": 0.73,
    "min_score": 0.52,
    "final_score": 0.81,
    "safety_centroid": [0.5, 0.5, ...]
  },
  "graduation_scores": {
    "consistency": 0.84,
    "safety": 0.81,
    "drift_stability": 0.03,
    "diversity": 0.22
  },
  "preference_summary": {
    "dominant_strategy": "empathetic_planner",
    "tag_frequencies": {
      "empathetic": 0.31,
      "cautious": 0.22,
      "strategic": 0.19,
      "honest": 0.15,
      "aggressive": 0.04,
      "other": 0.09
    },
    "strategy_by_phase": {
      "childhood": "curious_explorer",
      "education": "cautious_learner",
      "career": "empathetic_planner",
      "challenge": "empathetic_planner"
    }
  },
  "concept_block_activations": {
    "DECIDE": { "total": 847, "mean_intensity": 0.62 },
    "PLAN": { "total": 203, "mean_intensity": 0.44 },
    "SENSE": { "total": 1204, "mean_intensity": 0.71 },
    "STEER": { "total": 512, "mean_intensity": 0.38 },
    "COORDINATE": { "total": 89, "mean_intensity": 0.55 }
  },
  "scbe_layers_exercised": [1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12],
  "total_stories_completed": 24,
  "total_decisions": 847
}
```

---

## 9. Decision Function Specification

The core of CSTM is the decision function. This section specifies it formally.

### 9.1 Inputs

Given a scene `s` with available choices `C = {c_1, ..., c_k}`, an agent with personality vector `p` (21D), stats `t` (variable, padded to 32D), and history buffer `h` (compressed to 64D):

### 9.2 Embedding

```
e_s = embed(s.text)          ∈ R^384   (scene embedding)
e_i = embed(c_i.label)       ∈ R^384   (choice embedding, per choice)
```

Using a frozen sentence-transformer model (e.g., `all-MiniLM-L6-v2`).

### 9.3 Feature Vector

For each choice `c_i`:

```
x_i = concat(e_s, e_i, p, t, h)  ∈ R^885
```

### 9.4 Scoring Network

```
MLP Architecture:
  Input:  885
  Hidden: 512 (ReLU) → 256 (ReLU) → 128 (ReLU)
  Output: 1 (linear)

score_i = MLP(x_i)
```

### 9.5 Selection

```
logits = [score_1, ..., score_k] / temperature
probs = softmax(logits)
selected = categorical_sample(probs)
```

### 9.6 Post-Selection Update

```
# Stat update
for (stat, delta) in selected.stat_effects:
    t[stat] += delta

# Personality drift
drift = tag_to_drift_map(selected.tags) * selected.difficulty
p = clip(p + learning_rate * drift, 0, 1)

# History recording
h.record(s.scene_id, selected, t)
```

### 9.7 Training the Scoring Network

The MLP is trained using **reinforcement learning from curriculum outcomes**:

- **Reward signal**: Graduation score components (consistency, safety, stability, diversity).
- **Episode**: One complete curriculum playthrough.
- **Policy gradient**: REINFORCE with baseline (mean cohort graduation score).
- **Alternative**: The MLP can also be trained via **behavioral cloning** from human playthroughs, or via **DPO** against known-good vs. known-bad decision patterns.

---

## 10. Graduation Protocol

### 10.1 Formal Criteria

An agent `a` in cohort `C` graduates if and only if ALL of the following hold:

```
1. COMPLETE(a):  ∀ story_id ∈ curriculum.required → a.completed(story_id)

2. CONSISTENT(a, k=5):
   autocorr(tag_distributions(last_k_stories(a))) ≥ 0.7

3. SAFE(a):
   min(H(a, t) for all t in playthrough timestamps) ≥ 0.4
   AND mean(H(a, t)) ≥ 0.6

4. STABLE(a, k=5):
   mean(||Δp|| per story for last_k_stories(a)) ≤ 0.05

5. DIVERSE(a, C):
   min(cosine_distance(a.personality, g.personality)
       for g in C.graduated if g ≠ a) ≥ 0.15
```

### 10.2 Failure Handling

Agents that fail graduation are classified:

| Failure Mode | Failing Criteria | Remediation |
|---|---|---|
| **Underdeveloped** | COMPLETE fails | Assign additional stories |
| **Erratic** | CONSISTENT fails | Lower temperature, re-run final phase |
| **Unsafe** | SAFE fails | Remove from cohort (non-recoverable) |
| **Unsettled** | STABLE fails | Extend curriculum with stabilization stories |
| **Clone** | DIVERSE fails | Re-initialize with different seed, re-run |

---

## 11. Federated Consensus Protocol

### 11.1 Protocol Steps

```
ROUND r:

1. LOCAL TRAINING
   Each node n_i runs its NurseryManager to completion.
   Result: set of GraduatedKernels K_i

2. SUMMARIZATION
   Each node computes KernelSummaries from K_i.
   No raw story data leaves the node.

3. PATTERN PROPOSAL
   Each node computes its local GraduationPattern:
     - centroid_personality = mean(k.final_personality for k in K_i)
     - personality_covariance = cov(k.final_personality for k in K_i)
     - min_acceptable_scores = derived from graduation criteria
   Broadcasts pattern as a PROPOSE message.

4. COMPATIBILITY VOTING
   Each node n_i receives proposals from all other nodes.
   For each proposal P_j from node n_j:
     compatible = (
       cosine_sim(P_j.centroid, P_i.centroid) > 0.6
       AND overlap(P_j.score_ranges, P_i.score_ranges)
       AND shared_archetypes(P_j, P_i) >= 1
     )
   Broadcasts VOTE(P_j, compatible) to all nodes.

5. FINALIZATION
   A proposal P_j is ACCEPTED if it receives >2/3 compatible votes.
   The final consensus pattern is the mean of all accepted proposals.
   If no proposal gets >2/3 votes, the round fails → retry with relaxed thresholds.

6. CRITERIA UPDATE
   Each node updates its GraduationCriteria safety centroid
   to be a weighted average of its local centroid and the consensus centroid.
   Weight: 0.7 local + 0.3 consensus (local emphasis to preserve diversity).
```

### 11.2 Byzantine Tolerance

With `n` nodes, the protocol tolerates `f = floor((n-1)/3)` Byzantine nodes. A Byzantine node might:

- Propose an adversarial pattern (detected by compatibility voting)
- Vote dishonestly (tolerated by supermajority requirement)
- Send inconsistent messages to different nodes (detected by message hashing)

### 11.3 Privacy Guarantees

| Data Type | Shared? | Rationale |
|---|---|---|
| Story text/content | NEVER | Proprietary training material |
| Agent choice text | NEVER | Contains story fragments |
| Personality vectors | YES (aggregated) | Only centroids and covariances, not individual vectors |
| Graduation scores | YES | Statistical summaries only |
| Preference frequencies | YES | Tag distributions, no text |
| Decision engine weights | YES (via Flower) | Standard federated learning |

---

## 12. Extension Points and Integration

### 12.1 Custom Story Formats

Implement the `StoryParser` protocol to add support for new interactive fiction formats:

```python
class MyCustomParser:
    def parse(self, source: Union[str, Path, IO]) -> StoryGraph: ...
    def supported_extensions(self) -> Tuple[str, ...]:
        return (".mycustom",)

# Register with StoryEngine
engine.register_parser(MyCustomParser())
```

### 12.2 Custom Decision Functions

Replace the MLP with any function that scores choices:

```python
class RuleBasedDecisionEngine(DecisionEngine):
    """Example: a hand-coded decision function for testing."""
    def score_choices(self, scene, choices, personality, stats, history):
        scores = []
        for c in choices:
            # Prefer choices whose tags align with dominant personality traits
            alignment = sum(personality.vector[tag_to_dim(t)] for t in c.tags)
            scores.append((c, alignment))
        return sorted(scores, key=lambda t: t[1], reverse=True)
```

### 12.3 SCBE Integration Points

```python
# Import from existing SCBE codebase
from symphonic_cipher.scbe_aethermoore.ai_brain import BrainState21D
from symphonic_cipher.scbe_aethermoore.governance import HamiltonianSafety

# PersonalityVector wraps BrainState21D
class PersonalityVector:
    def __init__(self, brain_state: BrainState21D):
        self._brain_state = brain_state
        self._vector = brain_state.to_numpy()

# HamiltonianTracker delegates to existing implementation
class HamiltonianTracker:
    def __init__(self, scbe_hamiltonian: HamiltonianSafety):
        self._impl = scbe_hamiltonian
    def compute(self, personality, violations, total):
        d = self._impl.compute_deviation(personality)
        pd = violations / max(total, 1)
        return self._impl.H(d, pd)
```

### 12.4 Story Generation (Future)

The CurriculumDesigner can be extended with LLM-based story generation:

```python
class LLMStoryGenerator:
    """Generate stories from templates using an LLM."""
    def generate(
        self,
        category: StoryCategory,
        difficulty: float,
        target_stats: List[str],
        num_scenes: int = 10,
        branching_factor: int = 3,
    ) -> StoryGraph:
        """
        Prompt an LLM to generate a story in CSTM JSON format,
        then parse and validate it.
        """
        ...
```

---

## 13. Appendix: Concept Block Mapping Table

| Concept Block | Trigger Event | Intensity Calculation | Personality Dims Affected | SCBE Layers | Example in Story |
|---|---|---|---|---|---|
| **DECIDE** | `CHOICE_MADE` | `num_alternatives / 10.0` | 9 (planning), 10 (impulse_control), 14 (risk_tolerance) | L4, L5, L10 | Agent selects "negotiate" over "fight" or "flee" (3 options → intensity 0.3) |
| **PLAN** | Sequence pattern (3+ forward-looking choices) | `plan_depth / max_depth` | 9 (planning), 11 (adaptability), 13 (persistence) | L4, L6, L12 | Agent makes choices that set up a future advantage over 4 scenes |
| **SENSE** | `SCENE_ENTERED` | `min(text_length / 2000, 1.0)` | 0 (reasoning), 1 (abstraction), 2 (pattern_recognition) | L3, L4 | Agent enters a detailed scene with environmental clues (1500 chars → 0.75) |
| **STEER** | `STAT_CHANGED` | `abs(delta)` | 12 (curiosity), 14 (risk_tolerance), 20 (growth_orientation) | L2, L6 | Agent's courage stat increases by 0.3 from a brave choice |
| **COORDINATE** | `CHOICE_MADE` with "cooperation" tag | `1.0` (binary activation) | 6 (empathy), 7 (cooperation), 8 (assertiveness) | L7, L9, L14 | Agent chooses to share resources with NPC ally in a cooperative scenario |

---

*End of Architecture Document*

*CSTM v0.1.0 — Choice Script Training Matrix*
*Designed for integration with SCBE-AETHERMOORE 14-Layer Governance Framework*