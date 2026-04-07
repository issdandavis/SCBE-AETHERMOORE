# Training Curriculum Architecture

## The Trit-Pair Foundation

The manifold mirror proved 6 tongues decompose into 3 complement pairs, each with 3 interference modes:

```
PAIR          CONSTRUCTIVE (+1)    NEUTRAL (0)      DESTRUCTIVE (-1)
KO/DR         Build structure      Maintain          Challenge structure
AV/UM         Stabilize            Balance           Destabilize
RU/CA         Verify truth         Hold              Create/dissolve
```

Each training record gets a 3-trit score: `(ko_dr, av_um, ru_ca)` in {-1, 0, +1}.
That's 3^3 = 27 possible training states per record.

The trit is NOT quality. It's INTENT. A destructive (-1) record is not bad — it's testing.

## The Five Tracks

### Track 1: Foundation (K-8 equivalent)
**Purpose**: Build the base lattice. Facts, vocabulary, patterns.
**Trit bias**: (+1, 0, 0) — mostly constructive KO/DR, neutral elsewhere.
**Curriculum sources** (worldwide):
- Common Core (US K-8 math, ELA)
- UK National Curriculum (KS1-KS3)
- Singapore Math (Primary/Lower Secondary)
- Japanese Curriculum Standards (Elementary/Junior High)
- IB Primary Years Programme
- Finnish National Core Curriculum
- Indian CBSE/NCERT (Class 1-8)
- Chinese Compulsory Education Standards

**What this trains**: Pattern recognition, factual recall, sequential reasoning, basic numeracy/literacy. The structural skeleton.

**Tongue activation**: DR dominant (structure/forge), KO secondary (intent/orchestration).

### Track 2: Standard (9-12 equivalent)
**Purpose**: Connect the lattice. Cross-domain relationships, argument construction.
**Trit bias**: (+1, +1, 0) — constructive structure AND stability.
**Curriculum sources**:
- US Common Core (High School)
- AP Regular track (non-honors)
- UK GCSE + A-Level (standard)
- German Gymnasium/Realschule
- French Baccalaureat (general)
- Japanese High School standards
- Korean CSAT prep curriculum
- Australian HSC/VCE
- IB Middle Years Programme
- Brazilian ENEM curriculum

**What this trains**: Argument structure, evidence evaluation, multi-step problem solving, essay construction, lab methodology. The connective tissue.

**Tongue activation**: DR + AV (structure + transport/routing of ideas).

### Track 3: Advanced Placement / Honors
**Purpose**: Stress-test the lattice. Edge cases, proofs, creative application.
**Trit bias**: (+1, 0, -1) — build structure while CHALLENGING truth (RU/CA destructive).
**Curriculum sources**:
- AP courses (all 38 subjects)
- IB Diploma Programme (Higher Level)
- UK A-Level Further Maths/Sciences
- French Classes Preparatoires
- German Abitur (Leistungskurs)
- Olympiad training sets (IMO, IPhO, IChO, IOI, IOL)
- AMC/AIME/USAMO problem sets
- STEP/MAT (Cambridge/Oxford entrance)
- Korean Science High School curriculum
- Chinese Gaokao advanced problems
- Indian IIT-JEE / KVPY preparation
- Russian PhysTech entrance problems

**What this trains**: Proof construction, creative problem solving under constraints, edge case handling, novel application of known principles. The adversarial layer.

**Tongue activation**: RU/CA active (truth/creativity under pressure), DR backbone.

### Track 4: College / University
**Purpose**: Specialize the lattice. Depth over breadth, research methodology.
**Trit bias**: (0, +1, -1) — stabilize while creating new.
**Curriculum sources**:
- MIT OpenCourseWare (all departments)
- Stanford Online / Coursera university courses
- Khan Academy (upper division)
- Harvard/Yale/Princeton open courses
- ETH Zurich open materials
- UK Russell Group course specs
- arXiv-sourced problem sets
- Textbook problem sets (Stewart Calculus, Griffiths E&M, CLRS Algorithms, Sipser Theory of Computation, Rudin Analysis, etc.)
- Graduate qualifying exams (publicly available)
- Professional certification prep (PE, CPA, Bar, MCAT, etc.)

**What this trains**: Deep specialization, research methodology, peer review capability, literature synthesis, original contribution. The depth dimension.

**Tongue activation**: All six active. CA dominant (compute/creativity), UM rising (security/rigor).

### Track 5: Remedial / Scaffold (Special Needs)
**Purpose**: DON'T TRIM. SPEED UP.
**Trit bias**: (+1, +1, +1) — all constructive. No destruction until the lattice holds.
**Philosophy**: A "slow" model isn't dumb. It has gaps in the lattice that cause every subsequent layer to vibrate wrong. You don't remove content — you FILL GAPS and let the model self-trim what it can't hold yet.

**Curriculum sources**:
- Same content as Track 1-4, but:
  - Decomposed into smaller units (1 concept per record, not 3)
  - More worked examples per concept (5:1 ratio vs 2:1)
  - Explicit prerequisite chains (concept A requires B, C)
  - Scaffolded hint sequences (full solution -> partial -> minimal)
  - Multi-modal repetition (same concept, 3 different framings)
- Orton-Gillingham methodology (structured literacy)
- Singapore Math bar model approach
- Montessori concrete-to-abstract sequences
- Universal Design for Learning (UDL) principles
- Sheltered Instruction Observation Protocol (SIOP) for language learners
- Differentiated Instruction frameworks

**What this trains**: Gap detection, prerequisite satisfaction, self-pacing, multi-modal understanding. The model learns to identify WHAT it's missing, not just to fail gracefully.

**Tongue activation**: KO dominant (intent — "what am I trying to learn?"), DR secondary (structure — "where does this fit?").

**The key insight**: If a model can't learn calculus, it's not because calculus is hard. It's because somewhere in algebra the lattice has a hole. Fill the hole, don't remove the calculus. The model that can identify its own gaps is MORE valuable than the model that gets the answer right.

## Trit Scoring Per Record

Every training record gets tagged:

```json
{
  "trit_score": {
    "ko_dr": +1,      // constructive / neutral / destructive
    "av_um": 0,        // stabilizing / balanced / destabilizing  
    "ru_ca": -1        // verifying / holding / challenging
  },
  "trit_state": 7,     // integer encoding: (ko_dr+1)*9 + (av_um+1)*3 + (ru_ca+1)
  "track": "advanced",  // foundation / standard / advanced / college / scaffold
  "curriculum_source": "AP Calculus BC",
  "prerequisite_chain": ["algebra_2", "precalculus", "limits"],
  "concept_density": 2.3,  // concepts per record (scaffold=1.0, college=3.0+)
  "tongue_activation": {"ko": 0.1, "av": 0.3, "dr": 0.8, "ru": 0.5, "ca": 0.7, "um": 0.2}
}
```

## The 27 Training States

```
State  (KO/DR, AV/UM, RU/CA)  Name                    When to use
0      (-1, -1, -1)           FULL CHAOS              Adversarial robustness training
1      (-1, -1,  0)           DESTABILIZE             Stress testing
2      (-1, -1, +1)           CREATIVE DESTRUCTION    Paradigm shift training
3      (-1,  0, -1)           CHALLENGE               Standard adversarial input
4      (-1,  0,  0)           QUESTION                Socratic method
5      (-1,  0, +1)           DECONSTRUCT             Analysis/criticism training
6      (-1, +1, -1)           CONTROLLED BURN         Safe adversarial with stability
7      (-1, +1,  0)           GENTLE PUSH             Stretch zone (proximal development)
8      (-1, +1, +1)           REFORM                  Restructure while stable
9      ( 0, -1, -1)           TURBULENCE              Noisy environment training
10     ( 0, -1,  0)           DRIFT                   Concept drift detection
11     ( 0, -1, +1)           CREATIVE INSTABILITY    Brainstorming under pressure
12     ( 0,  0, -1)           PURE TEST               Evaluation (no new structure)
13     ( 0,  0,  0)           NULL STATE              Rest/consolidation
14     ( 0,  0, +1)           PURE VERIFY             Fact-checking, validation
15     ( 0, +1, -1)           STABLE TEST             Assessment with safety net
16     ( 0, +1,  0)           MAINTENANCE             Practice/repetition
17     ( 0, +1, +1)           STABLE VERIFY           Routine quality checks
18     (+1, -1, -1)           BUILD UNDER FIRE        Construction during adversity
19     (+1, -1,  0)           BUILD UNDER STRESS      Construction during instability
20     (+1, -1, +1)           PIONEER                 New territory, unstable ground
21     (+1,  0, -1)           BUILD + TEST            Standard learn-then-quiz
22     (+1,  0,  0)           PURE BUILD              New content introduction
23     (+1,  0, +1)           BUILD + VERIFY          Learn and confirm understanding
24     (+1, +1, -1)           SAFE BUILD + TEST       Scaffolded assessment
25     (+1, +1,  0)           SAFE BUILD              Scaffolded instruction (Track 5)
26     (+1, +1, +1)           FULL HARMONY            Mastery confirmation

```

## Track-to-State Mapping

```
Track        Primary States         Frequency
Foundation   22, 25, 26, 16         80% of records
Standard     22, 23, 21, 25         70% of records
Advanced     21, 5, 18, 3           60% of records
College      20, 11, 4, 21          balanced distribution
Scaffold     25, 26, 16, 22         90% constructive
```

## Curriculum Volume Estimates

| Track | Subjects | Records/Subject | Total Records | Trit Distribution |
|-------|----------|----------------|---------------|-------------------|
| Foundation (K-8) | 12 core | ~5,000 | ~60,000 | 70% (+), 25% (0), 5% (-) |
| Standard (9-12) | 20 elective | ~3,000 | ~60,000 | 55% (+), 30% (0), 15% (-) |
| Advanced (AP/IB) | 38 AP + 30 IB | ~2,000 | ~136,000 | 40% (+), 25% (0), 35% (-) |
| College | 50 majors × 40 courses | ~500 | ~1,000,000 | 30% (+), 30% (0), 40% (-) |
| Scaffold | mirrors Track 1-4 | 3x density | ~750,000 | 85% (+), 12% (0), 3% (-) |
| **Total** | | | **~2,006,000** | |

## Information Quality Verification

Before any record enters training, it passes through the trit-pair verification:

1. **Pair coherence check**: Does the trit score match the actual content?
   - Encode through both tongues in the pair
   - Run manifold mirror: does interference match claimed trit?
   - If claimed (+1) but interference is destructive → mislabeled

2. **Track consistency check**: Does the trit bias match the track?
   - Foundation record with trit (-1, -1, -1)? → wrong track or mislabeled
   - Scaffold record with concept_density > 2.0? → needs decomposition

3. **Prerequisite chain validation**: Are all prerequisites satisfied?
   - Check that earlier records in the chain exist and are (+1) scored
   - Missing prerequisite → insert scaffold records to fill gap

4. **Cross-tongue round-trip**: Encode in primary tongue, decode through complement
   - If identity preservation < 0.3 → record is too ambiguous, needs rewrite
   - If translation fidelity < 0.8 → record is tongue-specific, add parallel versions

## The Speed-Up Principle (Track 5)

"You don't trim dumb, you speed it up and let it trim if it can't even fit that mold."

Implementation:
1. **Same content, more scaffolding**: 5 worked examples instead of 2
2. **Explicit gap detection**: Each scaffold record includes "this requires X, Y, Z"
3. **Self-trimming curriculum**: Present full content, measure what sticks, repeat what didn't
4. **Speed over simplification**: Run more iterations at full complexity rather than fewer at reduced complexity
5. **The model that identifies gaps > the model that avoids them**

A model trained on Track 5 should be BETTER at gap detection than Track 3 models, because it's seen more explicit prerequisite chains. The "slow bot" becomes the best debugger.
