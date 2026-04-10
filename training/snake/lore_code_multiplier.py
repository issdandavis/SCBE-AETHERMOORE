"""
Lore×Code Multiplier — Turns lore records INTO code records.

"If you can find a way to turn the LORE number into the CODE number,
 then multiply them by each other, you have gained much."

The Spiralverse magic system IS computation. Every lore concept has a
computational twin. This module finds that twin and generates the
PAIRED training record: lore view + code view of the same concept.

The model doesn't learn "lore" and "code" as separate domains.
It learns they are the SAME THING at different observation angles.
Like quantum conjugate variables — position/momentum, time/energy,
lore/code.

Mapping:
  Spell          → Function (inputs → transform → output)
  Incantation    → Executable code in the tongue's paradigm language
  Governance     → Policy check / constraint / invariant
  Creature       → Class / type definition
  Artifact       → Data structure
  Quest          → Algorithm (goal-directed steps)
  World rule     → Axiom / invariant
  Superposition  → Fabrication structure (pre-collapse)
  Measurement    → Scalar collapse (information loss)
  Entanglement   → Cross-tongue correlation (KO↔DR, AV↔CA, RU↔UM)
  Sacred Tongue  → Programming language (KO=Lisp, AV=Python, etc.)

Quantum physics layer:
  Hilbert space      → Tongue activation space (6D complex)
  Unitary transform  → Pipeline layer (norm-preserving)
  Hamiltonian        → Governance energy landscape
  Eigenstate         → Stable tongue configuration
  Superposition      → Multi-tongue activation (fabrication)
  Collapse           → Decision (ALLOW/QUARANTINE/ESCALATE/DENY)
  Entanglement       → Cross-tongue binding (mirror axes)
  Quantum circuit    → 14-layer pipeline
  Qubit              → Tongue pair (KO|DR, AV|CA, RU|UM)
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from typing import Optional

PHI = (1 + math.sqrt(5)) / 2

# ---------------------------------------------------------------------------
# Lore concept categories — what kind of lore is this?
# ---------------------------------------------------------------------------

LORE_PATTERNS = {
    "spell": {
        "keywords": [
            "spell", "cast", "invoke", "enchant", "incantation", "ritual",
            "magic", "conjure", "summon", "channel", "weave", "bind",
        ],
        "code_type": "function",
        "paradigm": "transformation",
        "quantum": "unitary_operator",
    },
    "creature": {
        "keywords": [
            "creature", "beast", "dragon", "spirit", "entity", "guardian",
            "familiar", "phoenix", "raven", "serpent", "wolf", "golem",
        ],
        "code_type": "class",
        "paradigm": "type_definition",
        "quantum": "eigenstate",
    },
    "artifact": {
        "keywords": [
            "artifact", "relic", "crystal", "stone", "amulet", "scroll",
            "tome", "blade", "staff", "orb", "key", "seal", "ring",
        ],
        "code_type": "data_structure",
        "paradigm": "state_container",
        "quantum": "observable",
    },
    "governance": {
        "keywords": [
            "law", "rule", "decree", "edict", "council", "court",
            "treaty", "oath", "vow", "pact", "covenant", "charter",
            "govern", "authority", "sovereign", "throne", "crown",
        ],
        "code_type": "policy",
        "paradigm": "constraint",
        "quantum": "hamiltonian",
    },
    "quest": {
        "keywords": [
            "quest", "journey", "mission", "task", "challenge", "trial",
            "path", "voyage", "expedition", "search", "hunt", "pursuit",
        ],
        "code_type": "algorithm",
        "paradigm": "goal_directed",
        "quantum": "quantum_circuit",
    },
    "world_rule": {
        "keywords": [
            "always", "never", "cannot", "must", "forbidden", "eternal",
            "immutable", "universal", "absolute", "fundamental", "axiom",
        ],
        "code_type": "invariant",
        "paradigm": "axiom",
        "quantum": "conservation_law",
    },
    "tongue": {
        "keywords": [
            "kor'aelin", "korvath", "avali", "avhari", "runethic", "runeveil",
            "cassisivadan", "caelith", "umbroth", "umbraex", "draumric", "draethis",
            "sacred tongue", "tongue of", "speak in", "language of",
        ],
        "code_type": "language",
        "paradigm": "programming_paradigm",
        "quantum": "basis_state",
    },
    "combat": {
        "keywords": [
            "attack", "defend", "strike", "parry", "dodge", "shield",
            "battle", "fight", "duel", "clash", "charge", "retreat",
        ],
        "code_type": "state_machine",
        "paradigm": "adversarial",
        "quantum": "measurement",
    },
    "transformation": {
        "keywords": [
            "transform", "evolve", "morph", "shift", "change", "become",
            "ascend", "descend", "corrupt", "purify", "heal", "break",
        ],
        "code_type": "map_function",
        "paradigm": "morphism",
        "quantum": "gate_operation",
    },
}

# ---------------------------------------------------------------------------
# Deep computational concepts — what the lore ACTUALLY describes
# These aren't metaphors. The lore IS computation in fantasy language.
# Izack describes 2D→3D projection, pocket dimensions as namespaces,
# mana as computational budget, temporal anchoring as reference frames.
# ---------------------------------------------------------------------------

DEEP_CONCEPTS = {
    "dimensional_lifting": {
        "pattern": r"2\s*d.*3\s*d|dimension|project.*space|lift.*into|plane.*to.*solid",
        "code_concept": "Dimensional lifting: mapping lower-dimensional representation to higher-dimensional space",
        "code_example": """def lift_2d_to_3d(canvas_2d: list[list[float]], depth_fn) -> list[list[list[float]]]:
    \"\"\"Lift a 2D representation into 3D space.
    In the lore: Izack projects a 2D mind canvas into 3D for storage.
    In code: This is realification (L1->L2), embedding, or dimensionality expansion.
    In physics: Embedding a manifold into a higher-dimensional ambient space.
    \"\"\"
    return [[[cell * depth_fn(i, j) for cell in row]
             for j, row in enumerate(canvas_2d)]
            for i in range(len(canvas_2d))]""",
        "scbe_layer": "L1-L2 (Complex Context -> Realification)",
    },
    "namespace_allocation": {
        "pattern": r"pocket\s*(space|dimension|realm)|subspace|inner\s*realm|secret\s*space",
        "code_concept": "Namespace/container allocation: creating isolated execution environments",
        "code_example": """class PocketDimension:
    \"\"\"An isolated namespace with its own state, resources, and time reference.
    In the lore: Izack creates a pocket dimension inside his watch.
    In code: This is a container, namespace, sandbox, or virtual environment.
    In physics: A causally disconnected region with its own metric.
    \"\"\"
    def __init__(self, anchor_point, temporal_coordinate):
        self._state = {}
        self._anchor = anchor_point  # the watch crystal
        self._time_ref = temporal_coordinate  # entry/exit timestamps
        self._capacity = 0.0
        self._barrier = True  # inaccessible to outsiders

    def expand(self, resource):
        \"\"\"Grow the space by adding resources (mana = compute budget).\"\"\"
        self._capacity += resource.energy
        return self._capacity""",
        "scbe_layer": "L8 (Hamiltonian Multi-Well Realms)",
    },
    "temporal_reference": {
        "pattern": r"time\s*stasis|temporal|coordinate.*time|anchor.*time|freeze.*time",
        "code_concept": "Temporal reference frames: managing time-ordered state and causality",
        "code_example": """class TemporalAnchor:
    \"\"\"A reference frame for time-ordered operations.
    In the lore: Izack's watch anchors spacetime coordinates for his pocket dimension.
    In code: This is a transaction log, event sourcing, or causal ordering.
    In physics: A reference frame with proper time parametrization.
    \"\"\"
    def __init__(self, entry_time, anchor_object):
        self.entry = entry_time
        self.anchor = anchor_object
        self.events = []  # causally ordered

    def record(self, event):
        self.events.append((self.elapsed(), event))

    def elapsed(self):
        return time.monotonic() - self.entry""",
        "scbe_layer": "L6 (Breathing Transform) + L11 (Triadic Temporal)",
    },
    "resource_management": {
        "pattern": r"mana|magic\w*\s*(store|pool|reserve|budget|energy|power)|excess\s*mana|pure\s*mana",
        "code_concept": "Resource management: computational budgets, energy pools, allocation",
        "code_example": """class ManaPool:
    \"\"\"A finite resource pool with generation, consumption, and overflow.
    In the lore: Mana is stored as water in the pocket dimension's ocean.
    In code: This is a resource pool, thread pool, memory allocator, or compute budget.
    In physics: Energy conservation with potential/kinetic exchange.
    \"\"\"
    def __init__(self, capacity):
        self.capacity = capacity
        self.current = 0.0

    def generate(self, amount, source='self'):
        overflow = max(0, (self.current + amount) - self.capacity)
        self.current = min(self.capacity, self.current + amount)
        return overflow  # excess mana returns to environment

    def consume(self, cost):
        if self.current < cost:
            raise InsufficientMana(f'Need {cost}, have {self.current}')
        self.current -= cost""",
        "scbe_layer": "L8 (Hamiltonian energy landscape)",
    },
    "dynamic_allocation": {
        "pattern": r"expand.*(?:space|realm|capacity|ability)|grow.*(?:space|power|dimension)|increase.*(?:space|storage)",
        "code_concept": "Dynamic allocation: growing containers, buffers, or capabilities at runtime",
        "code_example": """def expand_realm(realm, new_resources):
    \"\"\"Dynamically grow a realm's capacity.
    In the lore: Izack fills his pocket dimension with air, water, earth to grow it.
    In code: This is realloc, dynamic array growth, or horizontal scaling.
    In physics: Cosmological expansion — adding energy-matter changes the metric.
    \"\"\"
    for resource in new_resources:
        realm.add(resource)
        realm.recalculate_bounds()
    return realm""",
        "scbe_layer": "L3 (Weighted Transform — spatial bounds)",
    },
    "access_control": {
        "pattern": r"barrier|boundary|ward|shield|wall|protect.*from|inaccessible.*outsider",
        "code_concept": "Access control: barriers, permissions, firewalls, sandboxing",
        "code_example": """class MagicalBarrier:
    \"\"\"Access control boundary that filters entities by permission.
    In the lore: The barrier of stars prevents outsiders from entering the pocket realm.
    In code: This is a firewall, ACL, sandbox boundary, or capability check.
    In physics: A potential barrier — only entities with sufficient energy can cross.
    \"\"\"
    def __init__(self, threshold):
        self.threshold = threshold

    def attempt_crossing(self, entity):
        if entity.trust_level >= self.threshold:
            return True  # ALLOW
        return False  # DENY""",
        "scbe_layer": "L12-L13 (Harmonic Wall + Risk Decision)",
    },
    "binding_reference": {
        "pattern": r"connect|link|bond|bind|entangle|tether|anchor.*to",
        "code_concept": "Reference binding: linking objects, pointers, foreign keys, entanglement",
        "code_example": """def bind(source, target, strength=1.0):
    \"\"\"Create a bidirectional binding between two entities.
    In the lore: Familiar bonds, magical tethers, soul connections.
    In code: This is a reference, foreign key, symlink, or event listener.
    In physics: Quantum entanglement — measuring one determines the other.
    \"\"\"
    source.bindings.append((target, strength))
    target.bindings.append((source, strength))
    return Bond(source, target, strength)""",
        "scbe_layer": "L9-L10 (Spectral + Spin Coherence)",
    },
    "type_conversion": {
        "pattern": r"transform|transmut|convert|morph|shift.*form|change.*shape|become.*(?:something|other)",
        "code_concept": "Type conversion: casting, serialization, morphisms between representations",
        "code_example": """def transmute(entity, target_type):
    \"\"\"Transform an entity from one type to another, preserving essential properties.
    In the lore: Shapeshifting, transmutation, ascension — the form changes but identity persists.
    In code: Type casting, serialization/deserialization, adapter pattern.
    In physics: Gauge transformation — representation changes, physics doesn't.
    \"\"\"
    preserved = entity.invariant_properties()
    new_entity = target_type.from_properties(preserved)
    assert new_entity.identity == entity.identity  # unitarity: nothing lost
    return new_entity""",
        "scbe_layer": "L7 (Mobius Phase — metric-preserving transformation)",
    },
    "observer_pattern": {
        "pattern": r"observe|witness|watch|monitor|sense|perceiv|detect|aware",
        "code_concept": "Observer pattern: monitoring state changes, event systems, measurement",
        "code_example": """class MagicalSense:
    \"\"\"Observe state changes without altering the observed system (ideally).
    In the lore: Sensing magic, detecting threats, witnessing events.
    In code: Observer pattern, event listeners, monitoring, logging.
    In physics: Measurement — observation DOES affect the system (collapse).
    \"\"\"
    def __init__(self):
        self._observers = []

    def register(self, observer):
        self._observers.append(observer)

    def notify(self, event):
        for obs in self._observers:
            obs.on_event(event)  # measurement = collapse""",
        "scbe_layer": "L14 (Audio Axis — telemetry/observation)",
    },
    "concurrency": {
        "pattern": r"weave|thread|fabric|tapestry|web|simultaneous|parallel|together.*at\s*once",
        "code_concept": "Concurrency: parallel execution, threading, weaving multiple streams",
        "code_example": """async def weave_spells(spell_list):
    \"\"\"Execute multiple spells concurrently, weaving their effects together.
    In the lore: Weaving magic threads into a tapestry of combined effect.
    In code: async/await, thread pool, parallel map, concurrent futures.
    In physics: Superposition — multiple states coexisting until measurement.
    \"\"\"
    import asyncio
    tasks = [asyncio.create_task(spell.cast()) for spell in spell_list]
    results = await asyncio.gather(*tasks)
    return combine_effects(results)""",
        "scbe_layer": "L1 (Composition — pipeline integrity across parallel paths)",
    },
    "memory_management": {
        "pattern": r"memory|remember|forget|recall|archive|store.*mind|mind.*store",
        "code_concept": "Memory management: allocation, garbage collection, caching, persistence",
        "code_example": """class ArcaneMemory:
    \"\"\"Persistent storage with recall, forgetting (GC), and archival.
    In the lore: Magical memories, forgotten spells, ancient archives.
    In code: Cache, database, memory allocator, garbage collector.
    In physics: Information conservation — information is never truly destroyed.
    \"\"\"
    def __init__(self, capacity):
        self._store = {}
        self._capacity = capacity

    def remember(self, key, value):
        if len(self._store) >= self._capacity:
            self._forget_oldest()
        self._store[key] = value

    def recall(self, key):
        return self._store.get(key)  # None = forgotten

    def _forget_oldest(self):
        oldest = min(self._store, key=lambda k: self._store[k].timestamp)
        del self._store[oldest]""",
        "scbe_layer": "L8 (Hamiltonian — energy wells as memory attractors)",
    },
    "encryption": {
        "pattern": r"seal|lock|encrypt|protect|guard.*secret|hide.*true|conceal|cipher|code.*secret",
        "code_concept": "Encryption/sealing: protecting information, hiding true form",
        "code_example": """def seal(content, key):
    \"\"\"Seal content so only the keyholder can unseal it.
    In the lore: Magical seals, locked grimoires, hidden true names.
    In code: Encryption (AES-GCM), digital signatures, sealed secrets.
    In physics: Quantum key distribution — observation destroys the key.
    \"\"\"
    from cryptography.fernet import Fernet
    cipher = Fernet(key)
    return cipher.encrypt(content.encode())""",
        "scbe_layer": "L5 (Hyperbolic Distance — exponential cost of breaking the seal)",
    },
    "algorithm_pipeline": {
        "pattern": r"ritual|ceremony|process|procedure|steps?\s*(?:in\s*order|to\s*follow)|recipe|method.*steps",
        "code_concept": "Algorithm/pipeline: ordered steps producing a result",
        "code_example": """def execute_ritual(steps, context):
    \"\"\"Execute an ordered sequence of steps, each feeding into the next.
    In the lore: Rituals with precise steps — wrong order = catastrophic failure.
    In code: Pipeline pattern, middleware chain, ETL, CI/CD.
    In physics: Unitary evolution — each step is a time-ordered operator.
    \"\"\"
    state = context
    for step in steps:
        state = step.execute(state)
        if not step.verify(state):
            raise RitualFailure(f'Step {step.name} failed verification')
    return state""",
        "scbe_layer": "L1-L14 (The entire 14-layer pipeline IS a ritual)",
    },
}

# Tongue → Language mapping (from Tongue Turing Test)
TONGUE_LANG = {
    "KO": {"lang": "lisp", "name": "Kor'aelin", "paradigm": "functional/prefix"},
    "AV": {"lang": "python", "name": "Avali", "paradigm": "object-oriented/infix"},
    "RU": {"lang": "forth", "name": "Runethic", "paradigm": "stack-based/postfix"},
    "CA": {"lang": "sql", "name": "Cassisivadan", "paradigm": "declarative/query"},
    "UM": {"lang": "asm", "name": "Umbroth", "paradigm": "imperative/register"},
    "DR": {"lang": "makefile", "name": "Draumric", "paradigm": "dependency-driven/build"},
}

# Quantum physics concept templates
QUANTUM_TEMPLATES = {
    "unitary_operator": {
        "concept": "Unitary transformation",
        "physics": "U|psi> = |psi'> where ||psi'|| = ||psi|| (norm preserved)",
        "scbe": "Pipeline layer preserves information norm through L{n} transform",
        "code_pattern": "def transform(state: Vector) -> Vector:  # ||output|| == ||input||",
    },
    "eigenstate": {
        "concept": "Eigenstate / stable configuration",
        "physics": "H|n> = E_n|n> — state is unchanged by its own operator",
        "scbe": "A tongue configuration that is self-consistent under governance",
        "code_pattern": "class StableState:  # H.apply(self) returns self with eigenvalue",
    },
    "observable": {
        "concept": "Observable / measurable quantity",
        "physics": "O = sum(o_n |n><n|) — eigenvalues are measurement outcomes",
        "scbe": "A data structure whose fields are the measurable properties",
        "code_pattern": "class Observable:  # .measure() collapses to eigenvalue",
    },
    "hamiltonian": {
        "concept": "Hamiltonian / energy landscape",
        "physics": "H = T + V — total energy determines time evolution",
        "scbe": "Governance energy: ALLOW/QUARANTINE/ESCALATE/DENY are energy wells",
        "code_pattern": "def governance_energy(state) -> float:  # which well are we in?",
    },
    "quantum_circuit": {
        "concept": "Quantum circuit / gate sequence",
        "physics": "U_total = U_n ... U_2 U_1 — sequence of unitary gates",
        "scbe": "14-layer pipeline: each layer is a unitary gate, composition is the circuit",
        "code_pattern": "pipeline = [L1, L2, ..., L14]  # each preserves norm",
    },
    "conservation_law": {
        "concept": "Conservation law",
        "physics": "dQ/dt = 0 — some quantity is invariant under time evolution",
        "scbe": "Axiom enforcement: unitarity/locality/causality/symmetry/composition",
        "code_pattern": "assert invariant(state) == invariant(transform(state))",
    },
    "basis_state": {
        "concept": "Basis state / computational basis",
        "physics": "|0>, |1> — the fundamental states from which all others are built",
        "scbe": "Sacred Tongues are the basis: any concept = superposition of 6 tongues",
        "code_pattern": "tongues = [KO, AV, RU, CA, UM, DR]  # orthogonal basis",
    },
    "measurement": {
        "concept": "Quantum measurement / wavefunction collapse",
        "physics": "Measurement projects |psi> onto eigenstate, destroying superposition",
        "scbe": "Scalar collapse: fabrication(12D) → scalar(1D) = information loss",
        "code_pattern": "scalar = fabrication.collapse()  # THIS IS THE INFORMATION LOSS",
    },
    "gate_operation": {
        "concept": "Quantum gate / transformation",
        "physics": "Single-qubit gates rotate state on Bloch sphere; multi-qubit entangle",
        "scbe": "Tongue transformation: rotating activation between tongues",
        "code_pattern": "new_state = gate.apply(old_state)  # rotation in tongue space",
    },
}


# ---------------------------------------------------------------------------
# Lore record classifier
# ---------------------------------------------------------------------------


@dataclass
class LoreClassification:
    """What kind of lore concept is this record?"""

    category: str = "unknown"
    confidence: float = 0.0
    matched_keywords: list[str] = field(default_factory=list)
    code_type: str = "unknown"
    paradigm: str = "unknown"
    quantum_concept: str = "unknown"
    dominant_tongue: str = "KO"
    deep_concepts: list[str] = field(default_factory=list)


def find_deep_concepts(text: str) -> list[str]:
    """Find the REAL computational concepts hiding in lore text.

    The lore isn't metaphor for code — it IS code in fantasy language.
    2D->3D projection, pocket dimensions as namespaces, mana as compute budget.
    """
    import re as _re

    lower = text.lower()
    found = []
    for concept_name, info in DEEP_CONCEPTS.items():
        if _re.search(info["pattern"], lower):
            found.append(concept_name)
    return found


def classify_lore(text: str) -> LoreClassification:
    """Classify a lore record into its computational category."""
    lower = text.lower()
    best_cat = "unknown"
    best_score = 0.0
    best_keywords = []

    for category, info in LORE_PATTERNS.items():
        matched = [kw for kw in info["keywords"] if kw in lower]
        score = len(matched) / len(info["keywords"])
        if score > best_score:
            best_score = score
            best_cat = category
            best_keywords = matched

    if best_cat == "unknown":
        return LoreClassification()

    pattern = LORE_PATTERNS[best_cat]

    # Detect dominant tongue from content
    tongue_scores = {"KO": 0, "AV": 0, "RU": 0, "CA": 0, "UM": 0, "DR": 0}
    tongue_kw = {
        "KO": ["command", "intent", "invoke", "execute", "strike", "charge"],
        "AV": ["wisdom", "know", "learn", "teach", "understand", "ancient"],
        "RU": ["rule", "law", "govern", "decree", "authority", "oath"],
        "CA": ["compute", "calculate", "formula", "precise", "measure", "count"],
        "UM": ["shadow", "dark", "hidden", "protect", "guard", "secret"],
        "DR": ["build", "forge", "craft", "structure", "design", "architect"],
    }
    for tongue, kws in tongue_kw.items():
        tongue_scores[tongue] = sum(1 for k in kws if k in lower)
    dominant = max(tongue_scores, key=tongue_scores.get)

    # Find deep computational concepts
    deep = find_deep_concepts(text)

    # If surface classification failed but deep concepts found, promote
    if best_cat == "unknown" and deep:
        best_cat = "deep_concept"
        best_score = len(deep) / len(DEEP_CONCEPTS)
        best_keywords = deep[:5]

    if best_cat == "unknown":
        return LoreClassification()

    pattern = LORE_PATTERNS.get(best_cat, {
        "code_type": "function",
        "paradigm": "computational",
        "quantum": "unitary_operator",
    })

    return LoreClassification(
        category=best_cat,
        confidence=best_score,
        matched_keywords=best_keywords,
        code_type=pattern["code_type"],
        paradigm=pattern["paradigm"],
        quantum_concept=pattern["quantum"],
        dominant_tongue=dominant,
        deep_concepts=deep,
    )


# ---------------------------------------------------------------------------
# Code twin generator — the multiplication engine
# ---------------------------------------------------------------------------

# Templates for generating code twins from lore concepts
CODE_TEMPLATES = {
    "function": '''def {name}({params}) -> {return_type}:
    """
    Lore: {lore_description}
    Code: {code_description}
    Quantum: {quantum_description}
    Tongue: {tongue} ({paradigm})
    """
    {body}
    return result''',
    "class": '''class {name}:
    """
    Lore: {lore_description}
    Code: {code_description}
    Quantum: {quantum_description}
    Tongue: {tongue} ({paradigm})
    """
    def __init__(self, {params}):
        {init_body}

    def {method}(self) -> {return_type}:
        {method_body}''',
    "policy": '''def check_{name}(state: dict) -> bool:
    """
    Lore: {lore_description}
    Code: {code_description}
    Quantum: {quantum_description} (Hamiltonian constraint)
    Tongue: {tongue} ({paradigm})
    """
    {body}
    return compliant''',
    "algorithm": '''def {name}(start, goal, constraints):
    """
    Lore: {lore_description}
    Code: {code_description}
    Quantum: {quantum_description} (circuit execution)
    Tongue: {tongue} ({paradigm})
    """
    path = [start]
    {body}
    return path''',
    "invariant": '''def assert_{name}(before, after) -> None:
    """
    Lore: {lore_description}
    Code: {code_description}
    Quantum: {quantum_description} (conservation law)
    Tongue: {tongue} ({paradigm})
    """
    {body}
    assert invariant_holds, "{name} violated"''',
    "data_structure": '''@dataclass
class {name}:
    """
    Lore: {lore_description}
    Code: {code_description}
    Quantum: {quantum_description} (observable)
    Tongue: {tongue} ({paradigm})
    """
    {fields}

    def measure(self):
        """Collapse to observable value."""
        {measure_body}''',
    "state_machine": '''class {name}:
    """
    Lore: {lore_description}
    Code: {code_description}
    Quantum: {quantum_description}
    Tongue: {tongue} ({paradigm})
    """
    STATES = {states}

    def __init__(self):
        self.state = self.STATES[0]

    def transition(self, action):
        {transition_body}''',
    "language": '''# Sacred Tongue: {tongue} ({paradigm})
# Lore: {lore_description}
# Code: This tongue IS {lang_name} — {paradigm} evaluation
# Quantum: {quantum_description} (basis state in 6D tongue Hilbert space)
#
# The tongue is not a metaphor for the language.
# The language is not a metaphor for the tongue.
# They are the same mathematical object observed from different angles.
{code_example}''',
    "map_function": '''def {name}(input_state):
    """
    Lore: {lore_description}
    Code: {code_description}
    Quantum: {quantum_description} (gate operation)
    Tongue: {tongue} ({paradigm})

    This is a morphism: preserves structure while changing representation.
    Like a quantum gate rotating a qubit on the Bloch sphere.
    """
    {body}
    return transformed_state''',
}


def extract_name_from_lore(text: str, category: str) -> str:
    """Extract a reasonable function/class name from lore text."""
    # Try to find a proper noun
    words = text.split()
    proper = [w for w in words[:30] if w[0:1].isupper() and len(w) > 2 and w.isalpha()]
    if proper:
        name = proper[0].lower()
    else:
        name = category
    # Make it code-safe
    name = re.sub(r"[^a-z0-9_]", "_", name)
    return name or category


def generate_code_twin(lore_text: str, classification: LoreClassification) -> Optional[str]:
    """Generate the code twin of a lore record.

    This is the multiplication: lore x code_mapping = lore_code pair.

    Priority:
      1. If deep concepts found -> use REAL code examples from DEEP_CONCEPTS
      2. Fall back to generic CODE_TEMPLATES only when no deep concept matches
    """
    if classification.category == "unknown":
        return None

    # --- Priority 1: Deep concept code (REAL implementations) ---
    if classification.deep_concepts:
        lore_desc = lore_text[:200].replace("\n", " ").replace('"', "'").replace("\\", "")
        parts = []
        parts.append(f'# Lore->Code extraction from: {lore_desc[:100]}')
        parts.append(f'# Deep concepts found: {", ".join(classification.deep_concepts)}')
        parts.append(f'# SCBE layers touched: {", ".join(DEEP_CONCEPTS[c]["scbe_layer"] for c in classification.deep_concepts if c in DEEP_CONCEPTS)}')
        parts.append("")

        for concept_name in classification.deep_concepts[:3]:  # max 3 per record
            concept = DEEP_CONCEPTS.get(concept_name)
            if concept:
                parts.append(f"# --- {concept_name}: {concept['code_concept']} ---")
                parts.append(concept["code_example"])
                parts.append("")

        return "\n".join(parts)

    # --- Priority 2: Generic template fallback ---
    template_key = classification.code_type
    template = CODE_TEMPLATES.get(template_key)
    if not template:
        return None

    name = extract_name_from_lore(lore_text, classification.category)
    tongue_info = TONGUE_LANG.get(classification.dominant_tongue, TONGUE_LANG["KO"])
    quantum = QUANTUM_TEMPLATES.get(classification.quantum_concept, {})

    lore_desc = lore_text[:150].replace("\n", " ").replace('"', "'")
    code_desc = f"{classification.code_type} implementing {classification.paradigm} pattern"
    quantum_desc = quantum.get("concept", classification.quantum_concept)

    fields = {
        "name": name,
        "params": "context",
        "return_type": "Any",
        "lore_description": lore_desc,
        "code_description": code_desc,
        "quantum_description": quantum_desc,
        "tongue": tongue_info["name"],
        "paradigm": tongue_info["paradigm"],
        "body": f"    # {classification.paradigm} logic\n    result = context",
        "init_body": f"self.state = {{}}\n        # {classification.paradigm}",
        "method": "process",
        "method_body": f"return self.state  # {classification.paradigm}",
        "fields": f"    value: float = 0.0\n    tongue: str = '{classification.dominant_tongue}'",
        "measure_body": f"return self.value  # collapse to scalar",
        "states": "['IDLE', 'ACTIVE', 'RESOLVED']",
        "transition_body": f"    # {classification.paradigm} state transition\n        pass",
        "lang_name": tongue_info.get("lang", "unknown"),
        "code_example": quantum.get("code_pattern", "pass"),
    }

    try:
        return template.format(**fields)
    except KeyError:
        return None


# ---------------------------------------------------------------------------
# Quantum physics training record generator
# ---------------------------------------------------------------------------


def generate_quantum_bridge(lore_text: str, classification: LoreClassification) -> dict:
    """Generate a quantum physics bridge record.

    This connects the lore concept to its quantum physics equivalent,
    creating a three-way mapping: lore ↔ code ↔ physics.
    """
    quantum = QUANTUM_TEMPLATES.get(classification.quantum_concept, {})
    tongue_info = TONGUE_LANG.get(classification.dominant_tongue, TONGUE_LANG["KO"])

    instruction = (
        f"Explain the quantum physics behind this Spiralverse concept: "
        f"{lore_text[:200]}"
    )

    response_parts = [
        f"## Quantum Bridge: {classification.category.title()} → {quantum.get('concept', 'Unknown')}",
        "",
        f"**Lore concept**: {classification.category} (tongue: {tongue_info['name']})",
        f"**Code equivalent**: {classification.code_type} ({classification.paradigm})",
        f"**Quantum physics**: {quantum.get('concept', 'N/A')}",
        "",
        f"### Physics",
        f"{quantum.get('physics', 'N/A')}",
        "",
        f"### SCBE Mapping",
        f"{quantum.get('scbe', 'N/A')}",
        "",
        f"### Code Pattern",
        f"```python",
        f"{quantum.get('code_pattern', 'pass')}",
        f"```",
        "",
        f"### Why This Mapping Holds",
        f"In the Spiralverse, {classification.category} concepts map to "
        f"{quantum.get('concept', 'quantum operations')} because both preserve "
        f"structure under transformation. The Sacred Tongue {tongue_info['name']} "
        f"({tongue_info['paradigm']}) is the natural language for expressing this "
        f"because its evaluation order matches the physics.",
    ]

    return {
        "instruction": instruction,
        "output": "\n".join(response_parts),
        "metadata": {
            "source": "lore_code_multiplier",
            "record_type": "quantum_bridge",
            "lore_category": classification.category,
            "code_type": classification.code_type,
            "quantum_concept": classification.quantum_concept,
            "tongue": classification.dominant_tongue,
            "grounding": 0.9,
            "is_multiplication": True,
        },
    }


# ---------------------------------------------------------------------------
# The multiplier — takes lore JSONL, outputs lore×code JSONL
# ---------------------------------------------------------------------------


def multiply_record(record: dict) -> list[dict]:
    """Take one lore record, produce its code and quantum twins.

    Input: 1 lore record
    Output: up to 3 records:
      1. Original lore record (preserved)
      2. Code twin (the computational equivalent)
      3. Quantum bridge (the physics connection)

    This is the multiplication: 1 lore → 3 training signals.
    """
    results = []

    # Extract text from the record (handle both chat and instruction formats)
    text = ""
    messages = record.get("messages", [])
    if messages:
        for m in messages:
            if m.get("role") in ("user", "assistant"):
                text += " " + m.get("content", "")
    else:
        # instruction/output or instruction/response format
        text = record.get("instruction", "") + " " + record.get("output", record.get("response", ""))
    text = text.strip()

    if not text:
        return [record]  # Pass through empty records

    # Classify the lore
    classification = classify_lore(text)
    if classification.category == "unknown":
        return [record]  # Can't classify, pass through

    # Record 1: Original with classification metadata
    enriched = dict(record)
    enriched.setdefault("metadata", {})
    if isinstance(enriched["metadata"], dict):
        enriched["metadata"]["lore_classification"] = {
            "category": classification.category,
            "code_type": classification.code_type,
            "quantum_concept": classification.quantum_concept,
            "tongue": classification.dominant_tongue,
            "confidence": classification.confidence,
            "deep_concepts": classification.deep_concepts,
        }
    results.append(enriched)

    # Record 2: Code twin
    code_twin = generate_code_twin(text, classification)
    if code_twin:
        tongue_info = TONGUE_LANG.get(classification.dominant_tongue, TONGUE_LANG["KO"])
        code_record = {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are Polly, translating Spiralverse lore into executable code. "
                        "In the Spiralverse, magic IS computation. Sacred Tongues ARE "
                        "programming languages. Show the code twin of each lore concept."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Translate this lore concept into {tongue_info['lang']} "
                        f"({tongue_info['paradigm']}): {text[:300]}"
                    ),
                },
                {"role": "assistant", "content": f"```python\n{code_twin}\n```"},
            ],
            "metadata": {
                "source": "lore_code_multiplier",
                "record_type": "code_twin",
                "lore_category": classification.category,
                "code_type": classification.code_type,
                "tongue": classification.dominant_tongue,
                "grounding": 0.95 if classification.deep_concepts else 0.85,
                "deep_concepts": classification.deep_concepts,
                "is_multiplication": True,
            },
            "tags": ["lore_x_code", classification.category, classification.dominant_tongue]
            + [f"deep:{c}" for c in classification.deep_concepts[:3]],
        }
        results.append(code_record)

    # Record 3: Quantum bridge
    quantum_record = generate_quantum_bridge(text, classification)
    quantum_record_full = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You explain the quantum physics underlying Spiralverse magic. "
                    "Every lore concept maps to a quantum mechanical operation. "
                    "Show the three-way bridge: lore ↔ code ↔ physics."
                ),
            },
            {"role": "user", "content": quantum_record["instruction"]},
            {"role": "assistant", "content": quantum_record["output"]},
        ],
        "metadata": quantum_record["metadata"],
        "tags": ["quantum_bridge", classification.category, classification.quantum_concept],
    }
    results.append(quantum_record_full)

    return results


def multiply_file(input_path: str, output_path: str) -> dict:
    """Process an entire JSONL file through the multiplier.

    Returns statistics about the multiplication.
    """
    stats = {
        "input_records": 0,
        "output_records": 0,
        "code_twins": 0,
        "quantum_bridges": 0,
        "categories": {},
        "multiplication_factor": 0.0,
    }

    with open(input_path, "r", encoding="utf-8") as fin, open(output_path, "w", encoding="utf-8") as fout:
        for line in fin:
            try:
                record = json.loads(line.strip())
            except json.JSONDecodeError:
                continue

            stats["input_records"] += 1
            results = multiply_record(record)

            for r in results:
                fout.write(json.dumps(r, ensure_ascii=False) + "\n")
                stats["output_records"] += 1

                meta = r.get("metadata", {})
                if isinstance(meta, dict):
                    rt = meta.get("record_type", "")
                    if rt == "code_twin":
                        stats["code_twins"] += 1
                    elif rt == "quantum_bridge":
                        stats["quantum_bridges"] += 1
                    cat = meta.get("lore_category", meta.get("lore_classification", {}).get("category", ""))
                    if cat:
                        stats["categories"][cat] = stats["categories"].get(cat, 0) + 1

    if stats["input_records"] > 0:
        stats["multiplication_factor"] = stats["output_records"] / stats["input_records"]

    return stats


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python lore_code_multiplier.py <input.jsonl> <output.jsonl>")
        print()
        print("Takes lore training data and multiplies it:")
        print("  1 lore record → 1 enriched lore + 1 code twin + 1 quantum bridge")
        print()
        print("The multiplication: LORE × CODE = LORE_CODE")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    print(f"Multiplying: {input_path} -> {output_path}")
    stats = multiply_file(input_path, output_path)

    print(f"\n{'='*60}")
    print(f"LORE × CODE MULTIPLICATION RESULTS")
    print(f"{'='*60}")
    print(f"Input records:        {stats['input_records']}")
    print(f"Output records:       {stats['output_records']}")
    print(f"Multiplication factor: {stats['multiplication_factor']:.2f}x")
    print(f"Code twins generated: {stats['code_twins']}")
    print(f"Quantum bridges:      {stats['quantum_bridges']}")
    print(f"\nCategories:")
    for cat, count in sorted(stats["categories"].items(), key=lambda x: -x[1]):
        print(f"  {cat}: {count}")
