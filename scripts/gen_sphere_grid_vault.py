"""
Generate the Fractal Sphere Grid Vault for Obsidian.

Structure:
  notes/sphere-grid/           <- The Obsidian vault (outer shell)
    Agentic Sphere Grid.md     <- MOC (map of everything)
    geometry/                  <- Sacred Geometry flow definitions
    KO-Command/                <- TONGUE SPHERE
      KO-Domain.md
      T1-Task-Dispatch/        <- SKILL SPHERE (mini-vault)
        _sphere.md             <- Overview + metadata
        pattern.md             <- Core pattern to learn
        training-pairs.md      <- SFT data
        concepts.md            <- Key concepts
    AV-Transport/ ...
    RU-Entropy/ ...
    CA-Compute/ ...
    UM-Security/ ...
    DR-Structure/ ...
    hodge/                     <- Hodge dual combo spheres
    agents/                    <- Agent archetype vaults
"""

import math
import shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "notes" / "sphere-grid"
PHI = 1.618033988749895

# Clean existing
if BASE.exists():
    shutil.rmtree(BASE)
BASE.mkdir(parents=True)

TONGUES = {
    "KO": {
        "name": "Command",
        "weight": 1.0,
        "angle": 0,
        "desc": "Orchestration, coordination, task dispatch",
        "geometry": "Hexagonal: 6-fold symmetry, hub-spoke topology",
    },
    "AV": {
        "name": "Transport",
        "weight": PHI,
        "angle": 60,
        "desc": "Navigation, browsing, data movement",
        "geometry": "Spiral: phi-spiral paths, expanding search radius",
    },
    "RU": {
        "name": "Entropy",
        "weight": PHI**2,
        "angle": 120,
        "desc": "Research, chaos testing, exploration",
        "geometry": "Fractal: self-similar branching, Mandelbrot zoom",
    },
    "CA": {
        "name": "Compute",
        "weight": PHI**3,
        "angle": 180,
        "desc": "Code generation, training, execution",
        "geometry": "Cubic: 3D grid, structured build layers",
    },
    "UM": {
        "name": "Security",
        "weight": PHI**4,
        "angle": 240,
        "desc": "Scanning, auditing, governance enforcement",
        "geometry": "Icosahedral: 20 faces of defense, triangulated trust",
    },
    "DR": {
        "name": "Structure",
        "weight": PHI**5,
        "angle": 300,
        "desc": "Architecture, documentation, healing",
        "geometry": "Dodecahedral: 12 faces of design, pentagonal harmony",
    },
}

TONGUE_KEYS = list(TONGUES.keys())

# Skills: (tier_id, name, desc, pattern_summary, training_pairs, concepts)
SKILLS = {
    "KO": [
        (
            "T1",
            "Task Dispatch",
            "Route tasks to appropriate agents",
            "Match intent to capability, phi-weighted priority",
            [
                ("Route code review to right agent", "Match to builder (CA), check activation >= 0.3"),
                ("Distribute 5 tasks across 3 agents", "Load-balance by AP bank and activation coverage"),
            ],
            ["Parse intent structure", "Capability matching algorithm", "Priority queue with tongue weights"],
        ),
        (
            "T2",
            "Formation Swap",
            "Reorganize fleet mid-task without state loss",
            "Checkpoint-swap-restore for zero-downtime rotation",
            [
                ("Code review found security issues", "Swap builder for guardian, preserve context"),
                ("Research hit dead end", "Swap researcher for scout, hand off queries"),
            ],
            ["State checkpointing", "Role reassignment protocol", "Zero-downtime rotation"],
        ),
        (
            "T3",
            "Rally Coordination",
            "Boost fleet performance by 15%",
            "Amplified adjacency ripple across all fleet members",
            [
                ("Fleet behind on deadline", "Rally all agents, 15% boost, focus bottleneck"),
                ("Three agents coordinating", "Rally + formation swap for max coherence"),
            ],
            ["Fleet-wide broadcast", "Performance multiplier stacking", "Hodge combo amplification"],
        ),
        (
            "T4",
            "Sovereign Command",
            "Full fleet orchestration authority",
            "Atomic fleet commands with governance gate approval",
            [
                ("Full codebase refactor", "Scout maps, builder refactors, guardian audits, teacher docs"),
                ("Production incident", "Healer diagnoses, builder patches, guardian monitors"),
            ],
            ["Governance approval flow", "Atomic fleet execution", "Rollback on partial failure"],
        ),
    ],
    "AV": [
        (
            "T1",
            "Web Search",
            "Find and retrieve web content with governance",
            "Every search result governance-scanned before return",
            [
                ("Search transformer papers", "Query arxiv + semantic scholar, scan results"),
                ("Find library docs", "Official docs first, community second, scan for injection"),
            ],
            ["Governed search pipeline", "Source ranking", "Injection detection"],
        ),
        (
            "T2",
            "Navigation",
            "Multi-step browser traversal with state tracking",
            "SENSE-PLAN-STEER-DECIDE loop",
            [
                ("Navigate to settings page", "SENSE structure, PLAN clicks, STEER, DECIDE"),
                ("Multi-step form fill", "Track state across pages, validate before submit"),
            ],
            ["State machine navigation", "Backtracking on failure", "Session persistence"],
        ),
        (
            "T3",
            "Site Mapping",
            "Map full site structure and extract content",
            "BFS crawl with governance scanning per page",
            [
                ("Map documentation site", "BFS from root, extract API docs, build graph"),
                ("Inventory blog posts", "Map /blog path, extract metadata, return catalog"),
            ],
            ["BFS/DFS crawl strategies", "Content extraction", "Link graph analysis"],
        ),
        (
            "T4",
            "Fleet Transport",
            "Move data between agents and systems at scale",
            "Spiral Seal encrypted transport with tongue routing",
            [
                ("Ship training data to HuggingFace", "Scan, seal with RU+CA, push via API"),
                ("Sync agent state across fleet", "Checkpoint, transport via bus, verify"),
            ],
            ["Sealed transport protocol", "Tongue-routed delivery", "Integrity verification"],
        ),
    ],
    "RU": [
        (
            "T1",
            "Hypothesis Generation",
            "Generate testable claims from patterns",
            "Turn observations into ranked testable hypotheses",
            [
                ("Attention clusters at phi=0.5", "Hypothesis: resonance point in phase tunnel"),
                ("Loss plateaus at epoch 50", "Hypothesis: LR schedule needs warmup"),
            ],
            ["Knowledge gap detection", "Prior probability estimation", "Testability ranking"],
        ),
        (
            "T2",
            "Data Collection",
            "Gather and structure data from diverse sources",
            "Schema-driven multi-source extraction with dedup",
            [
                ("Collect SCBE mentions in papers", "Search arxiv/scholar, extract citations"),
                ("Gather training from game logs", "Parse Everweave logs, structure as SFT"),
            ],
            ["Collection schema design", "Multi-source extraction", "Deduplication"],
        ),
        (
            "T3",
            "Chaos Testing",
            "Stress-test with randomized inputs and faults",
            "Controlled destruction for resilience discovery",
            [
                ("Chaos test governance gate", "Inject malformed 9D vectors, verify DENY"),
                ("Stress test fleet transport", "Simultaneous sends, verify no data loss"),
            ],
            ["Adversarial input generation", "Fault injection", "Resilience scoring"],
        ),
        (
            "T4",
            "Entropy Oracle",
            "Predict failures from entropy patterns",
            "Ornstein-Uhlenbeck analysis on system entropy history",
            [
                ("Entropy spiking in layer 7", "Check OU params, alert if diverging"),
                ("Predict next bottleneck", "Analyze entropy trends across 14 layers"),
            ],
            ["OU process analysis", "Anomaly detection (spectral)", "Failure prediction"],
        ),
    ],
    "CA": [
        (
            "T1",
            "Code Generation",
            "Write functional tested code from specs",
            "Read existing patterns, write implementation, write tests",
            [
                ("Implement Poincare distance", "Write function with arcosh, add property test"),
                ("Add Sacred Tongue to tokenizer", "Follow existing pattern, update TONGUE_KEYS"),
            ],
            ["Pattern-following implementation", "Test-first development", "Convention adherence"],
        ),
        (
            "T2",
            "Test Writing",
            "Comprehensive test suites with property testing",
            "Property tests prove correctness across ALL inputs",
            [
                ("Test governance gate", "L2: unit verdicts, L4: random 9D vectors, L5: bypass"),
                ("Test fleet transport", "L3: end-to-end delivery, L6: payload injection"),
            ],
            ["Tiered testing (L1-L6)", "Property-based testing", "Adversarial test design"],
        ),
        (
            "T3",
            "Training Pipeline",
            "Full ML pipeline from data to deployment",
            "Data prep, governance scan, train, eval, push to HF",
            [
                ("Train on Sacred Tongue corpus", "SFT from tokenizer data, LoRA, eval accuracy"),
                ("Fine-tune governance classifier", "ALLOW/DENY as labels, DPO training"),
            ],
            ["SFT/DPO/GRPO training", "Quality gate scanning", "HuggingFace integration"],
        ),
        (
            "T4",
            "Model Deployment",
            "Deploy models with health monitoring",
            "Blue-green canary deploy with rollback",
            [
                ("Deploy new tokenizer model", "Canary to staging, monitor accuracy, promote"),
                ("Rollback broken deployment", "Identify regression, activate rollback"),
            ],
            ["Canary deployment", "Health monitoring", "Automated rollback"],
        ),
    ],
    "UM": [
        (
            "T1",
            "Governance Scan",
            "Check content against SCBE governance rules",
            "9D state vector risk computation on every piece of content",
            [
                ("Scan web content for injection", "Check script tags, SQL patterns, prompt injection"),
                ("Validate training data", "Scan for duplicates, toxic content, poisoning"),
            ],
            ["9D risk computation", "Content classification", "Threshold tuning"],
        ),
        (
            "T2",
            "Threat Detection",
            "Detect adversarial patterns before they succeed",
            "Pattern matching + anomaly detection + behavioral analysis",
            [
                ("Unusual API access pattern", "Compare to immune memory, check credential stuffing"),
                ("Agent behavior diverging", "Compute drift distance, quarantine if threshold"),
            ],
            ["Immune memory matching", "Anomaly detection", "Drift measurement"],
        ),
        (
            "T3",
            "Audit Trail",
            "Verifiable audit records with hash chains",
            "Immutable hash-chained governance-stamped records",
            [
                ("Audit trail for deployment", "Record every step, hash-chain all"),
                ("Verify trail integrity", "Walk hash chain, verify each record"),
            ],
            ["Hash chain construction", "Governance stamping", "Tamper detection"],
        ),
        (
            "T4",
            "Seal Enforcement",
            "Sacred Seal cryptographic proofs on all actions",
            "Argon2id + XChaCha20 + 6-tongue cross-threading",
            [
                ("Seal governance decision", "KDF from tongue seed, encrypt, cross-thread, anchor"),
                ("Verify sealed artifact", "Decode AEAD, verify threading, check chain"),
            ],
            ["Argon2id KDF", "XChaCha20-Poly1305 AEAD", "Cross-tongue threading"],
        ),
    ],
    "DR": [
        (
            "T1",
            "Documentation",
            "Generate structured docs from code and systems",
            "Translate code to human understanding with cross-links",
            [
                ("Document sphere grid API", "Overview, reference, examples, gotchas"),
                ("Write agent onboarding", "Archetype selection, AP system, first unlock"),
            ],
            ["Audience-aware writing", "Structure patterns", "Cross-linking"],
        ),
        (
            "T2",
            "Debugging",
            "Systematic diagnosis and fix of system issues",
            "Reproduce, isolate, trace, fix, verify",
            [
                ("AssertionError in tests", "Read assertion, check expected vs actual, trace"),
                ("Governance returning DENY", "Check 9D vector, verify bounds, log path"),
            ],
            ["Reproduction methods", "Root cause analysis", "Minimal fix principle"],
        ),
        (
            "T3",
            "Self Healing",
            "Automatic error recovery without human intervention",
            "Monitor-diagnose-fix loop with governance approval",
            [
                ("Agent crashed mid-task", "Restore from checkpoint, retry, log recovery"),
                ("Memory pressure warning", "Compact L0, archive L1 to L2, continue"),
            ],
            ["Checkpoint/restore", "Graduated response", "Recovery verification"],
        ),
        (
            "T4",
            "Architecture",
            "Design and validate system architecture at scale",
            "Constraints, primitives, composition, validation, docs",
            [
                ("Design fleet comms", "Sacred Tongue transport, governance scanning, audit"),
                ("Architect training pipeline", "Data funnel, gate, train, eval, deploy cycle"),
            ],
            ["Constraint analysis", "Primitive selection", "Composition validation"],
        ),
    ],
}

count = 0


def write_note(path, content):
    global count
    path.write_text(content.strip(), encoding="utf-8")
    count += 1


# ============================================================
# Generate tongue domains + skill spheres
# ============================================================

for tongue_code, tongue_info in TONGUES.items():
    tname = tongue_info["name"]
    tdir = BASE / f"{tongue_code}-{tname}"
    tdir.mkdir(parents=True, exist_ok=True)

    # Tongue domain note
    skill_links = []
    for s in SKILLS[tongue_code]:
        safe = s[1].replace(" ", "-")
        skill_links.append(f"- [[{tongue_code}-{tname}/{s[0]}-{safe}/_sphere|{s[0]} {s[1]}]] -- {s[2]}")
    skill_links_str = "\n".join(skill_links)

    adj_cw = TONGUE_KEYS[(TONGUE_KEYS.index(tongue_code) + 1) % 6]
    adj_ccw = TONGUE_KEYS[(TONGUE_KEYS.index(tongue_code) - 1) % 6]

    write_note(
        tdir / f"{tongue_code}-Domain.md",
        f"""---
type: tongue-sphere
tongue: "{tongue_code}"
name: "{tname}"
weight: {tongue_info["weight"]:.2f}
angle: {tongue_info["angle"]}
sacred_geometry: "{tongue_info["geometry"]}"
---

# {tongue_code} -- {tname}

> {tongue_info["desc"]}

**Weight:** {tongue_info["weight"]:.2f} | **Angle:** {tongue_info["angle"]} deg
**Sacred Geometry:** {tongue_info["geometry"]}

## Skill Spheres

{skill_links_str}

## Flow Geometry

The {tname} domain uses **{tongue_info["geometry"].split(":")[0]}** geometry:
{tongue_info["geometry"].split(":")[1].strip()}

Adjacent domains:
- Clockwise: [[{adj_cw}-{TONGUES[adj_cw]["name"]}/{adj_cw}-Domain|{adj_cw}]]
- Counter-clockwise: [[{adj_ccw}-{TONGUES[adj_ccw]["name"]}/{adj_ccw}-Domain|{adj_ccw}]]

#sphere-grid #tongue #{tongue_code}
""",
    )

    # Skill spheres (mini-vaults)
    for tier_id, name, desc, pattern_summary, pairs, concepts in SKILLS[tongue_code]:
        safe_name = name.replace(" ", "-")
        sdir = tdir / f"{tier_id}-{safe_name}"
        sdir.mkdir(parents=True, exist_ok=True)

        tier_num = int(tier_id[1])
        cost = tier_num * 8.0 * tongue_info["weight"]
        phi = (tier_num - 1) * 0.4

        # Previous and next tier references
        prev_skills = [s for s in SKILLS[tongue_code] if int(s[0][1]) == tier_num - 1]
        next_skills = [s for s in SKILLS[tongue_code] if int(s[0][1]) == tier_num + 1]

        prereq_str = "None (entry point)"
        if prev_skills:
            ps = prev_skills[0]
            prereq_str = f'[[{tongue_code}-{tname}/{ps[0]}-{ps[1].replace(" ", "-")}/_sphere|{ps[0]} {ps[1]}]]'

        unlock_str = "Hodge combo eligibility"
        if next_skills:
            ns = next_skills[0]
            unlock_str = f'[[{tongue_code}-{tname}/{ns[0]}-{ns[1].replace(" ", "-")}/_sphere|{ns[0]} {ns[1]}]]'

        # Relative links for notes within this sphere
        rel_prefix = f"{tongue_code}-{tname}/{tier_id}-{safe_name}"

        # _sphere.md
        write_note(
            sdir / "_sphere.md",
            f"""---
type: skill-sphere
tongue: "{tongue_code}"
tier: {tier_num}
name: "{name}"
cost: {cost:.1f}
phi: {phi:.2f}
---

# {name}

> {desc}

**Domain:** [[{tongue_code}-{tname}/{tongue_code}-Domain|{tongue_code} ({tname})]]
**Tier:** {tier_num} | **Cost:** {cost:.1f} AP | **Phi:** {phi:+.2f}

## Inside This Sphere

- [[{rel_prefix}/pattern|Core Pattern]] -- {pattern_summary}
- [[{rel_prefix}/training-pairs|Training Pairs]] -- SFT data for this skill
- [[{rel_prefix}/concepts|Key Concepts]] -- What to learn

## Activation

| Level | Range | Meaning |
|-------|-------|---------|
| DORMANT | 0.00-0.09 | Cannot use |
| LATENT | 0.10-0.29 | Aware, cannot invoke |
| **PARTIAL** | **0.30-0.59** | **Usable (degraded)** |
| CAPABLE | 0.60-0.89 | Fully functional |
| MASTERED | 0.90-1.00 | Peak, can teach |

## Connections

- **Prereq:** {prereq_str}
- **Unlocks:** {unlock_str}
- [[adjacency-ripple]] bleeds growth to adjacent spheres
- [[computational-necessity]] can ACCELERATE this sphere

#sphere-grid #{tongue_code} #tier-{tier_num}
""",
        )

        # pattern.md
        concept_list = "\n".join(f"- {c}" for c in concepts)
        write_note(
            sdir / "pattern.md",
            f"""---
type: pattern
parent: "{name}"
tongue: "{tongue_code}"
---

# Pattern: {name}

> {pattern_summary}

## Core Approach

An agent at PARTIAL (0.30) executes this with degraded performance.
An agent at MASTERED (0.90+) executes optimally and can [[teach]] it.

## Key Concepts

{concept_list}

## Integration

- Uses [[{tongue_code}-{tname}/{tongue_code}-Domain|{tongue_code}]] primitives
- Governed by [[governance-scan]] at every step
- Results feed into [[{rel_prefix}/training-pairs|training pairs]]

#sphere-grid #pattern #{tongue_code}
""",
        )

        # training-pairs.md
        pair_rows = "\n".join(f"| {instr} | {resp} |" for instr, resp in pairs)
        write_note(
            sdir / "training-pairs.md",
            f"""---
type: training-data
parent: "{name}"
tongue: "{tongue_code}"
format: "sft"
---

# Training Pairs: {name}

> SFT pairs for teaching agents this skill.

| Instruction | Response |
|-------------|----------|
{pair_rows}

## How These Are Used

1. Agent fails at task requiring {name}
2. [[computational-necessity]] detects the need
3. These pairs feed the agent fine-tune
4. Activation increases -> agent improves

## Generating More Pairs

- Successful completions by MASTERED agents
- Supervised corrections by operators
- [[chaos-testing]] outcomes

#sphere-grid #training-data #{tongue_code}
""",
        )

        # concepts.md
        concept_sections = "\n\n".join(
            f"### {i+1}. {c}\n\nEssential for {name} at tier {tier_num}." for i, c in enumerate(concepts)
        )
        write_note(
            sdir / "concepts.md",
            f"""---
type: concepts
parent: "{name}"
tongue: "{tongue_code}"
---

# Concepts: {name}

{concept_sections}

## Learning Path

1. Start with concept 1 (foundational)
2. At PARTIAL (0.30): concepts 1-2 solid
3. At CAPABLE (0.60): all understood
4. At MASTERED (0.90): can teach and generate examples

#sphere-grid #concepts #{tongue_code}
""",
        )


# ============================================================
# Geometry notes
# ============================================================
(BASE / "geometry").mkdir(exist_ok=True)

write_note(
    BASE / "geometry" / "sacred-flows.md",
    """---
type: sacred-geometry
---

# Sacred Flows

> How information flows between spheres.

## The Six Geometries

| Tongue | Geometry | Pattern |
|--------|----------|---------|
| **KO** | Hexagonal | 6-fold symmetry, hub-spoke command |
| **AV** | Spiral | Phi-spiral paths, expanding search |
| **RU** | Fractal | Self-similar branching |
| **CA** | Cubic | 3D grid, structured layers |
| **UM** | Icosahedral | 20 faces of defense |
| **DR** | Dodecahedral | 12 faces of design |

## Flow Types

### 1. Prerequisite (vertical)
Lower tier -> Higher tier. Must complete T1 before T2.

### 2. Adjacency Ripple (horizontal)
Same tongue, adjacent tier: 10% growth bleed.

### 3. Hodge Resonance (diagonal)
Cross-tongue duals share resonance. Both CAPABLE -> combo emerges.

## Phi Spiral Ordering

Spheres positioned along phi spiral within each tongue:
T1 at 0, T2 at phi, T3 at 2*phi, T4 at 3*phi.
Natural spacing matches governance cost scaling.

#sphere-grid #geometry
""",
)

write_note(
    BASE / "geometry" / "phi-spiral.md",
    f"""---
type: sacred-geometry
---

# Phi Spiral

> The golden ratio governs sphere placement and cost.

phi = {PHI:.15f}

## Tongue Weights (powers of phi)

| Tongue | Power | Weight |
|--------|-------|--------|
| KO | phi^0 | 1.00 |
| AV | phi^1 | 1.62 |
| RU | phi^2 | 2.62 |
| CA | phi^3 | 4.24 |
| UM | phi^4 | 6.85 |
| DR | phi^5 | 11.09 |

## Why Phi

Optimal packing: spheres never overlap, cost curve is smooth.
30 total nodes = edges of an icosahedron.

#sphere-grid #geometry #phi
""",
)


# ============================================================
# Concept notes
# ============================================================
for cname, cdesc in [
    (
        "computational-necessity",
        "The system discovers what it needs by trying and failing.\n\n"
        "Need pressure accumulates on missing skills (+0.15 per failure).\n"
        "At pressure >= 0.5, governance reviews: ACCELERATE if genuine need, DENY if risky.\n"
        "Growth is organic and non-optimal -- agents develop what they USE.",
    ),
    (
        "adjacency-ripple",
        "When a skill activates, adjacent skills get 10% free boost.\n\n"
        "Adjacent = same tongue within 1 tier, or Hodge partner tongue.\n"
        "Creates organic growth bleed -- mastering code gen makes testing slightly easier.",
    ),
    (
        "teach",
        "MASTERED (0.90+) agents share knowledge with the fleet.\n\n"
        "Student gets 20% of remaining gap for free.\n"
        "Teacher earns 7 AP. No cost to student.\n"
        "Cooperative fleet growth -- specialists bootstrap others.",
    ),
    (
        "fleet-coverage",
        "The fleet as a whole has capabilities no single agent has.\n\n"
        "Coverage = % of skills at PARTIAL+ across all agents per tongue.\n"
        "6 archetypes cover ~70% naturally. 100% requires sustained cooperative work.",
    ),
]:
    write_note(
        BASE / f"{cname}.md",
        f"""---
type: concept
---

# {cname.replace("-", " ").title()}

{cdesc}

#sphere-grid #concept
""",
    )


# ============================================================
# Hodge combos
# ============================================================
(BASE / "hodge").mkdir(exist_ok=True)

for hname, ta, tb, hdesc in [
    ("Architectural Command", "KO", "DR", "Structure + Command = system design"),
    ("Chaotic Research", "RU", "AV", "Entropy + Transport = deep exploration"),
    ("Secure Computation", "CA", "UM", "Compute + Security = safe execution"),
    ("Command Transport", "KO", "AV", "Command + Transport = fleet dispatch"),
    ("Structural Entropy", "DR", "RU", "Structure + Entropy = stress testing"),
    ("Compute Command", "CA", "KO", "Compute + Command = sovereign automation"),
]:
    fname = hname.lower().replace(" ", "-")
    write_note(
        BASE / "hodge" / f"{fname}.md",
        f"""---
type: hodge-combo
tongue_a: "{ta}"
tongue_b: "{tb}"
multiplier: 1.3
---

# {hname}

> {hdesc}

**Tongues:** [[{ta}-{TONGUES[ta]["name"]}/{ta}-Domain|{ta}]] + [[{tb}-{TONGUES[tb]["name"]}/{tb}-Domain|{tb}]]
**Bonus:** 1.3x (Hodge dual pair)

Emerges when both domains have T3 skills at CAPABLE (0.60+).

#sphere-grid #hodge #{ta} #{tb}
""",
    )


# ============================================================
# Agent archetypes
# ============================================================
(BASE / "agents").mkdir(exist_ok=True)

for arch, atongue, adesc in [
    ("researcher", "RU", "Deep exploration and hypothesis generation"),
    ("builder", "CA", "Code generation and deployment"),
    ("guardian", "UM", "Security scanning and governance"),
    ("scout", "AV", "Navigation and web traversal"),
    ("teacher", "KO", "Knowledge transfer and documentation"),
    ("healer", "DR", "Debugging and self-healing"),
]:
    write_note(
        BASE / "agents" / f"{arch}.md",
        f"""---
type: agent-archetype
archetype: "{arch}"
tongue: "{atongue}"
---

# {arch.title()} Archetype

> {adesc}

**Dominant Tongue:** [[{atongue}-{TONGUES[atongue]["name"]}/{atongue}-Domain|{atongue} ({TONGUES[atongue]["name"]})]]

Starts with pre-filled skills in the {TONGUES[atongue]["name"]} domain.
Specialization emerges from usage -- not from the archetype.
Can [[teach]] skills once they reach MASTERED (0.90+).

#sphere-grid #archetype #{arch}
""",
    )


# ============================================================
# MOC -- Map of Content (vault front door)
# ============================================================

tongue_links = "\n".join(
    f"- [[{t}-{TONGUES[t]['name']}/{t}-Domain|{t} ({TONGUES[t]['name']})]] -- "
    f"{TONGUES[t]['geometry'].split(':')[0]} geometry, weight {TONGUES[t]['weight']:.2f}"
    for t in TONGUE_KEYS
)

write_note(
    BASE / "Agentic Sphere Grid.md",
    f"""---
type: moc
---

# Agentic Sphere Grid

> An Obsidian vault containing a sphere grid. Each sphere is a mini-vault.
> Sacred geometry organizes the flows. Agents learn by traversing spheres.

## Structure

```
This Vault
  |-- Tongue Spheres (6 domains, each with its sacred geometry)
  |     |-- Skill Spheres (4 tiers per tongue = 24 mini-vaults)
  |           |-- _sphere.md      (overview + metadata)
  |           |-- pattern.md      (core pattern to learn)
  |           |-- training-pairs.md (SFT data)
  |           |-- concepts.md     (key concepts)
  |-- Hodge Combos (6 dual-tongue synergies)
  |-- Agent Archetypes (6 starting positions)
  |-- Geometry (sacred flow definitions)
```

## Tongue Domains

{tongue_links}

## Core Concepts

- [[computational-necessity]] -- Growth through failure
- [[adjacency-ripple]] -- Organic skill bleed
- [[teach]] -- Cooperative transfer
- [[fleet-coverage]] -- Emergent fleet capability

## Sacred Geometry

- [[geometry/sacred-flows]] -- How spheres connect
- [[geometry/phi-spiral]] -- Golden ratio organization

## Agent Archetypes

- [[agents/researcher]] (RU) | [[agents/builder]] (CA) | [[agents/guardian]] (UM)
- [[agents/scout]] (AV) | [[agents/teacher]] (KO) | [[agents/healer]] (DR)

## Hodge Combos

- [[hodge/architectural-command]] (KO+DR) | [[hodge/chaotic-research]] (RU+AV)
- [[hodge/secure-computation]] (CA+UM) | [[hodge/command-transport]] (KO+AV)
- [[hodge/structural-entropy]] (DR+RU) | [[hodge/compute-command]] (CA+KO)

## How Agents Learn

```
Do work --> Earn AP --> Enter sphere --> Read notes --> Activation grows
                                              |
                        Pattern + Training Pairs = the curriculum
                                              |
Fail --> Need pressure --> Governance ACCELERATEs --> Sphere unlocks
                                              |
MASTERED --> Teach others --> Fleet grows cooperatively
```

#sphere-grid #moc
""",
)

# ============================================================
# Report
# ============================================================
total = sum(1 for _ in BASE.rglob("*.md"))
dirs = sum(1 for _ in BASE.rglob("*") if _.is_dir())
print(f"SPHERE GRID VAULT GENERATED")
print(f"  Location: {BASE}")
print(f"  Total notes: {total}")
print(f"  Directories: {dirs}")
print(f"  Tongue domains: 6")
print(f"  Skill spheres: 24 (4 notes each = 96 training notes)")
print(f"  Hodge combos: 6")
print(f"  Agent archetypes: 6")
print(f"  Geometry notes: 2")
print(f"  Concept notes: 4")
print(f"  MOC index: 1")
