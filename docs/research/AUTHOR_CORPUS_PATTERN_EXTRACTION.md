# Author Corpus Pattern Extraction: Encodable Patterns for Geometric Personality Training

**Author**: Issac Davis + Claude Opus 4.6 (1M context)
**Date**: 2026-04-02
**Status**: Research Reference (v1.0)
**Purpose**: Quadruple-use document -- (1) human reference, (2) AI training data source, (3) Sacred Tongue tokenizer test corpus, (4) PHDM polyhedral face mapping input

---

## Document Architecture

This document extracts **encodable invariants** from how authors construct character personalities across 10 research areas. Each pattern is structured for direct ingestion into the SCBE-AETHERMOORE personality scaffold pipeline:

- **Sacred Tongues**: KO (Intent), AV (Metadata), RU (Binding), CA (Compute), UM (Security), DR (Structure)
- **16 PHDM Polyhedra**: Tetrahedron (foundation), Cube (stability), Octahedron (reactive), Dodecahedron (reasoning), Icosahedron (deep personality), Truncated Tetrahedron (filtered), Cuboctahedron (balance), Icosidodecahedron (cognitive map), Small Stellated Dodecahedron (risk), Great Dodecahedron (adversarial), Szilassi (recursive identity), Csaszar (mirror identity), Pentagonal Bipyramid (connector), Triangular Cupola (bridge), Rhombic Dodecahedron (space-filling), Bilinski Dodecahedron (compressed)

---

## A. Character Introduction Patterns (First 500 Words)

### Research Summary

How an author establishes personality in the first scene is not arbitrary. Across craft literature and computational stylistics, a small set of invariant techniques recur regardless of genre, period, or medium.

### Pattern A1: The Characteristic Moment

**Source**: K.M. Weiland, *Creating Character Arcs* (2016); Robert McKee, *Story* (1997); MasterClass writing guides (2024-2026)

**The Invariant**: All effective character introductions dramatize a single action that encodes the character's dominant trait. The character is not described -- they are *caught in the act* of being themselves. Weiland calls this the "Characteristic Moment." McKee's formulation is that true character is only revealed in choices made under pressure. The key is that the reader witnesses behavior before receiving explanation.

**Encodable Dimensions**:

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `intro_mode` | categorical | {action, dialogue, description, internal, environmental} | Primary channel of first impression |
| `agency_level` | float | [0, 1] | Is the character acting (1.0) or being acted upon (0.0)? |
| `trait_signal_density` | float | [0, 1] | Personality-relevant information per word in first 100 words |
| `contradiction_present` | boolean | {0, 1} | Does the intro contain a trait that will be challenged later? |

**Sacred Tongue Mapping**: **KO (Intent)** -- the introduction is fundamentally about declaring the character's intent posture to the reader. What they do first IS their intent signature.

**Polyhedral Face**: **Tetrahedron (Foundation)** -- the simplest solid, the minimum viable impression. Four faces = four intro modes (action/dialogue/description/internal). The first impression is the foundation everything else builds from.

**Training Data Example**:
```json
{
  "pattern": "characteristic_moment",
  "source_text": "When we first meet Indiana Jones, he is navigating a booby-trapped temple, solving puzzles under mortal danger, then losing the artifact to a rival. In 90 seconds: competence, courage, fallibility, rivalry.",
  "encoding": {
    "intro_mode": "action",
    "agency_level": 0.95,
    "trait_signal_density": 0.82,
    "contradiction_present": true
  },
  "tongue": "KO",
  "polyhedron": "Tetrahedron"
}
```

---

### Pattern A2: The Action-Description-Dialogue Ratio

**Source**: Dialogue-to-action ratio analysis (screenwriting pedagogy); computational stylistics research on 1,100 English novels (Dialogism project, Oxford Digital Humanities, 2017); Fiveable screenwriting curriculum (2024)

**The Invariant**: Effective introductions follow a ratio pattern where action dominates (40-60%), followed by either dialogue (20-35%) or description (15-25%), with internal monologue used sparingly (5-15%). The ratio itself encodes genre: thrillers skew to 70%+ action; literary fiction allows 40%+ internal monologue; screenplays enforce near-zero internal narration. The invariant is not the specific ratio but that the ratio IS the genre signal, and all skilled authors control it deliberately.

**Encodable Dimensions**:

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `action_ratio` | float | [0, 1] | Proportion of intro devoted to action/movement |
| `dialogue_ratio` | float | [0, 1] | Proportion of intro devoted to speech |
| `description_ratio` | float | [0, 1] | Proportion of intro devoted to sensory/physical description |
| `internal_ratio` | float | [0, 1] | Proportion of intro devoted to thoughts/feelings |
| `ratio_vector` | float[4] | simplex | The four ratios as a normalized vector (must sum to 1.0) |

**Sacred Tongue Mapping**: **AV (Metadata)** -- the ratio is metadata ABOUT the story's mode of communication. It classifies the genre, pacing, and narrative distance without containing content itself.

**Polyhedral Face**: **Cuboctahedron (Balance)** -- 14 faces, bridging cube and octahedron. The ratio is about balance between competing modes of expression. The cuboctahedron's dual nature (square and triangular faces) mirrors the tension between showing and telling.

**Training Data Example**:
```json
{
  "pattern": "intro_ratio",
  "source_text": "Opening of The Hunger Games by Suzanne Collins",
  "encoding": {
    "action_ratio": 0.15,
    "dialogue_ratio": 0.10,
    "description_ratio": 0.30,
    "internal_ratio": 0.45,
    "ratio_vector": [0.15, 0.10, 0.30, 0.45]
  },
  "tongue": "AV",
  "polyhedron": "Cuboctahedron",
  "note": "Literary YA inverts the thriller ratio -- internal dominates because the stakes are emotional before they are physical"
}
```

---

### Pattern A3: Information Trickle Rate

**Source**: Reedsy writing guides (2024); Jericho Writers craft guidance (2025); MasterClass character introduction module (2026)

**The Invariant**: Effective introductions never info-dump. Across all competent authors, backstory and context are released at a controlled rate that maintains reader curiosity. The invariant is: **reveal enough to create questions, never enough to answer them**. The information release follows a roughly logarithmic curve -- dense at the start (name, situation, one striking detail), then rapidly slowing as the scene focuses on present action.

**Encodable Dimensions**:

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `info_density_first_50` | float | [0, 1] | New-fact density in first 50 words |
| `info_density_next_200` | float | [0, 1] | New-fact density in words 51-250 |
| `info_density_final_250` | float | [0, 1] | New-fact density in words 251-500 |
| `question_generation_rate` | float | [0, 1] | Unanswered questions introduced per 100 words |
| `backstory_ratio` | float | [0, 1] | Fraction of intro devoted to pre-scene events |

**Sacred Tongue Mapping**: **DR (Structure)** -- information trickle rate is a structural constraint on narrative flow. It governs pacing architecture.

**Polyhedral Face**: **Truncated Tetrahedron (Filtered)** -- the truncation represents deliberate removal of information (cutting corners off the tetrahedron). What gets filtered out is as important as what remains.

---

## B. Decision Architecture Under Pressure

### Research Summary

Robert McKee's central thesis -- "true character is revealed in the choices a human being makes under pressure; the greater the pressure, the deeper the revelation" (*Story*, 1997) -- is not merely craft advice. It is a falsifiable structural claim about how authors encode personality through decision sequences.

### Pattern B1: The Pressure-Choice-Revelation Triad

**Source**: Robert McKee, *Story: Substance, Structure, Style* (1997); Lisa Cron, *Wired for Story* (2012); Writers Helping Writers, "How to Draw Readers in Through a Character's Choices" (2021)

**The Invariant**: In all effective characterization through decision, three elements are always present: (1) genuine pressure where something valued is at stake, (2) a choice between at least two options where neither is cost-free, and (3) the revelation that the choice creates -- showing the reader something about the character they could not have known from description alone. McKee's key insight: "If the character chooses to tell the truth in a situation where telling a lie would gain him nothing, the choice is trivial. But if the same character insists on telling the truth when a lie would save his life, then we sense that honesty is the core of his nature."

**Encodable Dimensions**:

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `pressure_magnitude` | float | [0, 1] | How much is at stake (0=nothing, 1=life/identity) |
| `option_count` | integer | [2, 5] | Number of meaningfully distinct choices |
| `option_cost_variance` | float | [0, 1] | How different the costs of each option are |
| `choice_consistency` | float | [-1, 1] | Alignment with previously established traits (-1=contradicts, 1=confirms) |
| `revelation_depth` | categorical | {surface, behavioral, moral, unconscious} | What layer of personality the choice reveals |

**Sacred Tongue Mapping**: **KO (Intent)** primary, **UM (Security)** secondary -- the decision reveals intent (KO) but the pressure context determines what the character is protecting (UM). Every decision under pressure is fundamentally a security calculation.

**Polyhedral Face**: **Octahedron (Reactive)** -- 8 faces representing reactive states. Decisions under pressure are reactive by nature. The octahedron's dual relationship to the cube (stability) captures how reactive decisions can either reinforce or destabilize a character's stable identity.

**Training Data Example**:
```json
{
  "pattern": "pressure_choice_revelation",
  "source_text": "Sophie's Choice (William Styron, 1979): A mother forced to choose which child lives. The choice reveals not her preference but the impossibility of the preference itself -- the character IS the wound the choice creates.",
  "encoding": {
    "pressure_magnitude": 1.0,
    "option_count": 2,
    "option_cost_variance": 0.0,
    "choice_consistency": -1.0,
    "revelation_depth": "unconscious"
  },
  "tongue": "KO",
  "polyhedron": "Octahedron"
}
```

---

### Pattern B2: The Moral Dilemma Gradient

**Source**: Writer's Digest, "5 Moral Dilemmas That Make Characters Better" (2023); MasterClass, "How to Write Moral Dilemmas" (2026); Writers Helping Writers, "Show Character Depth by Challenging Moral Beliefs" (2016)

**The Invariant**: Authors construct moral dilemmas on a gradient from *values-confirming* (easy, early in arc) to *values-destroying* (hard, climactic). The gradient follows a pattern: first the character faces a dilemma where their values give a clear answer, then one where values conflict with self-interest, then one where two core values contradict each other, and finally one where no value system provides an answer. This escalation pattern is present across genres from literary fiction to superhero comics.

**Encodable Dimensions**:

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `dilemma_tier` | categorical | {confirming, testing, conflicting, annihilating} | Which level of the moral gradient |
| `values_at_stake` | integer | [1, 5] | Number of core values in tension |
| `self_interest_alignment` | float | [-1, 1] | Does the moral choice align with self-interest? |
| `arc_position` | float | [0, 1] | Where in the story arc this dilemma appears |
| `resolution_type` | categorical | {decisive, compromised, deferred, transformed} | How the character resolves it |

**Sacred Tongue Mapping**: **RU (Binding)** -- moral dilemmas are fundamentally about what the character is bound to. Which commitments override which? RU encodes the hierarchy of obligations.

**Polyhedral Face**: **Small Stellated Dodecahedron (Risk)** -- the star points extending beyond the base solid represent risk-taking behavior. Moral dilemmas are the highest-risk personality moments -- the character risks their identity.

---

### Pattern B3: McKee's Characterization vs. Character Distinction

**Source**: Robert McKee, *Story* (1997); Karen Woodward, "Robert McKee and Characterization vs Character" (2014)

**The Invariant**: All authors who write compelling characters maintain a distinction between *characterization* (observable traits: appearance, habits, speech patterns, profession) and *character* (the choices made under pressure that reveal the true self). McKee's law: "The revelation of true character in contrast or contradiction to characterization is fundamental to all fine storytelling." The invariant is the GAP between surface and depth. Flat characters have no gap; round characters have a gap that the story progressively reveals.

**Encodable Dimensions**:

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `surface_depth_gap` | float | [0, 1] | Distance between characterization and true character |
| `gap_direction` | categorical | {better_beneath, worse_beneath, orthogonal} | Is the true self better/worse/different from the surface? |
| `reveal_count` | integer | [0, 10] | Number of times the gap is exposed during the narrative |
| `final_alignment` | float | [0, 1] | At story's end, how aligned are surface and depth? |

**Sacred Tongue Mapping**: **UM (Security)** -- the gap between characterization and character IS a security boundary. The surface is the public-facing persona; the depth is the protected interior. Breaching this boundary (revealing true character) is structurally identical to a security event.

**Polyhedral Face**: **Csaszar (Mirror Identity)** -- the toroidal topology (genus 1, all faces touch) represents the self-referential nature of the surface-depth gap. The mirror relationship between what is shown and what is hidden.

---

## C. Speech Pattern Differentiation

### Research Summary

Computational linguistics and writing craft converge on a key finding: character voice is not primarily lexical (word choice) but structural (sentence architecture, rhythm, and omission patterns). Authors who differentiate characters effectively do so through measurable linguistic features.

### Pattern C1: The Structural Voice Signature

**Source**: Author's Pathway, "Dialogue Differentiation" (2024); Amy Isaman, "Writing Dialogue: How to Develop Characters' Voices" (2023); ScreenCraft, "7 Effective Ways to Give Characters Unique Voices" (2024); PMC/Tandfonline, "Automatic Identification of Character Types from Film Dialogs" (Azmi et al., 2017)

**The Invariant**: Across all authors who write distinguishable dialogue, each character has a stable *structural voice signature* composed of: (1) mean sentence length, (2) question-to-statement ratio, (3) contraction frequency, (4) subordinate clause rate, and (5) interruption tendency. The invariant is NOT that all authors use the same values -- it is that each character maintains consistent values across scenes, and that character pairs have statistically distinct signatures. Research by Azmi et al. (2017) demonstrated that character types can be automatically identified from dialogue features alone with significant accuracy.

**Encodable Dimensions**:

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `mean_sentence_length` | float | [3, 40] | Average words per sentence in dialogue |
| `question_rate` | float | [0, 1] | Fraction of utterances that are questions |
| `contraction_rate` | float | [0, 1] | Fraction of contractable phrases that are contracted |
| `subordination_rate` | float | [0, 1] | Fraction of sentences with subordinate clauses |
| `interruption_frequency` | float | [0, 1] | How often the character interrupts or is interrupted |
| `hedge_density` | float | [0, 1] | Frequency of hedging markers (maybe, sort of, I think) |
| `filler_rate` | float | [0, 1] | Frequency of discourse markers (well, you know, like) |

**Sacred Tongue Mapping**: **CA (Compute)** -- the voice signature is a computable function. Given the parameter vector, you can generate dialogue that matches the character. CA encodes the operational function, not the meaning.

**Polyhedral Face**: **Dodecahedron (Complex Reasoning)** -- 12 pentagonal faces. Speech patterns are complex enough to require high-dimensional representation but structured enough to be regular (pentagonal symmetry). The 12 faces can map to 12 key speech parameters.

**Training Data Example**:
```json
{
  "pattern": "structural_voice_signature",
  "source_text": "Hagrid (J.K. Rowling): contracted forms ('em, takin', ter, fer), short sentences, simple vocabulary, high warmth markers, zero subordination. Compare Dumbledore: long sentences, zero contractions, complex subordination, rhetorical questions, classical vocabulary.",
  "encoding_hagrid": {
    "mean_sentence_length": 8.2,
    "question_rate": 0.12,
    "contraction_rate": 0.92,
    "subordination_rate": 0.05,
    "interruption_frequency": 0.15,
    "hedge_density": 0.08,
    "filler_rate": 0.22
  },
  "encoding_dumbledore": {
    "mean_sentence_length": 22.5,
    "question_rate": 0.35,
    "contraction_rate": 0.02,
    "subordination_rate": 0.68,
    "interruption_frequency": 0.01,
    "hedge_density": 0.15,
    "filler_rate": 0.03
  },
  "tongue": "CA",
  "polyhedron": "Dodecahedron"
}
```

---

### Pattern C2: The Dialogue Strip Test

**Source**: Author's Pathway (2024); P.S. Hoffman, "How to Write Character Voice" (2024); multiple writing craft sources

**The Invariant**: Skilled authors can pass the "dialogue strip test" -- remove all dialogue tags and the reader can still identify who is speaking. This is not dialect or accent but structural consistency in voice. The invariant is: **if two characters are statistically indistinguishable when tags are removed, the author has failed at differentiation**. This test is computationally verifiable and serves as a quality gate for training data.

**Encodable Dimensions**:

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `tag_removal_accuracy` | float | [0, 1] | Classifier accuracy for speaker identification without tags |
| `voice_distance` | float | [0, 1] | Cosine distance between character voice vectors |
| `consistency_variance` | float | [0, 1] | How much a character's voice parameters vary across scenes |

**Sacred Tongue Mapping**: **AV (Metadata)** -- the strip test is a metadata validation operation. It checks whether the encoding carries sufficient information without explicit labels.

**Polyhedral Face**: **Pentagonal Bipyramid (Connector)** -- the 10 triangular faces represent pairwise character voice comparisons. The bipyramid structure connects characters through their distinguishing features.

---

### Pattern C3: Emotional Modulation of Speech

**Source**: Storm Writing School, "The Pitfalls of Emotional Body Language" (2024); Frontiers in Robotics and AI, "Sentiment Analysis for Words and Fiction Characters" (Jacobs, 2019)

**The Invariant**: Characters do not just have a static voice -- their voice shifts under emotional pressure in character-specific ways. Some characters become more verbose when angry; others go monosyllabic. Some become more formal under stress; others lose all register control. The invariant is that each character has a **consistent emotional modulation function** -- a predictable way their speech parameters shift as a function of emotional state.

**Encodable Dimensions**:

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `anger_length_delta` | float | [-1, 1] | How sentence length changes under anger |
| `fear_formality_delta` | float | [-1, 1] | How formality changes under fear |
| `joy_verbosity_delta` | float | [-1, 1] | How verbosity changes under joy |
| `sadness_question_delta` | float | [-1, 1] | How question rate changes under sadness |
| `modulation_consistency` | float | [0, 1] | How predictable the emotional shift pattern is |

**Sacred Tongue Mapping**: **RU (Binding)** -- emotional modulation binds the voice signature to the emotional state. It is the coupling function between inner state and outer expression.

**Polyhedral Face**: **Octahedron (Reactive)** -- emotional modulation is inherently reactive. The octahedron's 8 faces can map to 8 primary emotion-direction combinations.

---

## D. The Unsaid (Null-Space in Prose)

### Research Summary

Hemingway's iceberg theory (1932) formalized what all effective prose writers practice: the most powerful characterization exists in what is omitted. Computational analysis of this phenomenon requires encoding absence, which maps naturally to the Sacred Tongue framework's capacity for null-space representation.

### Pattern D1: The Seven-Eighths Rule

**Source**: Ernest Hemingway, *Death in the Afternoon* (1932); Wikipedia, "Iceberg theory" (primary sources); Spark Notes analysis of "Hills Like White Elephants"; Celtx Blog, "What is Iceberg Theory?" (2024)

**The Invariant**: Hemingway stated: "There is seven-eighths of it underwater for every part that shows. Anything you know you can eliminate and it only strengthens your iceberg." The invariant across all authors who use subtext effectively is: **the ratio of known-to-the-author material to shown-to-the-reader material is consistently 3:1 or greater**. Authors who write effective subtext have built the full context and then systematically removed it. Authors who merely omit without building have no iceberg -- they have a flat surface.

**Encodable Dimensions**:

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `explicit_ratio` | float | [0, 1] | Fraction of relevant information that appears on page |
| `implication_density` | float | [0, 1] | Number of inferable facts per 100 explicit words |
| `topic_avoidance_count` | integer | [0, 10] | Number of topics the character systematically avoids |
| `deflection_frequency` | float | [0, 1] | How often the character redirects from sensitive topics |
| `silence_as_response_rate` | float | [0, 1] | Fraction of prompts met with non-verbal or no response |

**Sacred Tongue Mapping**: **UM (Security)** -- the unsaid IS the security boundary. What a character refuses to say is what they are protecting. The iceberg's hidden mass is the secured payload.

**Polyhedral Face**: **Szilassi (Recursive Identity)** -- the toroidal Szilassi polyhedron (genus 1, all 7 faces mutually adjacent) represents the recursive nature of the unsaid: what is hidden refers back to what is shown, which refers back to what is hidden. The self-referential topology is the topology of subtext.

**Training Data Example**:
```json
{
  "pattern": "seven_eighths_rule",
  "source_text": "Hills Like White Elephants (Hemingway, 1927): Two characters discuss 'an operation' without ever naming abortion. The entire story's meaning exists in the null space. The word 'abortion' appears zero times. The topic is communicated entirely through deflection, euphemism, and silence.",
  "encoding": {
    "explicit_ratio": 0.12,
    "implication_density": 0.95,
    "topic_avoidance_count": 1,
    "deflection_frequency": 0.73,
    "silence_as_response_rate": 0.28
  },
  "tongue": "UM",
  "polyhedron": "Szilassi"
}
```

---

### Pattern D2: The Avoidance Fingerprint

**Source**: Helping Writers Become Authors, "Subtext: The Art of Iceberging" (Weiland, 2023); The Script Lab, "How to Use Hemingway's Iceberg Theory" (2023)

**The Invariant**: Each character has a unique set of topics they will not discuss. This avoidance set is consistent across the narrative and directly maps to the character's wound/ghost. The invariant: **a character's avoidance fingerprint is the negative image of their wound**. What they refuse to talk about IS what they are wounded by. Skilled authors maintain this fingerprint with perfect consistency -- a character who avoids discussing their father in Chapter 2 will still avoid it in Chapter 20, unless the arc demands a breakthrough moment.

**Encodable Dimensions**:

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `avoidance_topics` | set | variable | Set of consistently avoided subjects |
| `avoidance_consistency` | float | [0, 1] | How reliably the character avoids these topics |
| `deflection_method` | categorical | {redirect, humor, anger, silence, counter_question} | Primary avoidance strategy |
| `breakthrough_threshold` | float | [0, 1] | How much pressure required to force engagement |

**Sacred Tongue Mapping**: **UM (Security)** primary, **KO (Intent)** secondary -- the avoidance set defines the security perimeter (UM), but the deflection method reveals intent (KO) -- what the character intends the listener to understand instead.

**Polyhedral Face**: **Bilinski Dodecahedron (Compressed)** -- the compressed rhombic form represents information compression through omission. The 12 rhombic faces encode 12 possible avoidance categories.

---

## E. Relationship Revelation Patterns

### Research Summary

How a character behaves changes based on who they are with. This is not inconsistency -- it is the fundamental sociolinguistic phenomenon of register variation, amplified by fiction into a characterization tool. Computational studies of code-switching in literature confirm that these shifts are systematic and encodable.

### Pattern E1: The Relational Voice Matrix

**Source**: NotMFA, "Foil vs. Mirror Characters" (2025); Gardner-Chloros & Weston, "Code-switching and multilingualism in literature," *Language and Literature* (2015); Oxford Academic, "How Literary Texts 'Stage' Code-Switching," *Forum for Modern Language Studies* (2024)

**The Invariant**: Every character has a **relational voice matrix** -- a mapping from conversation partner to voice parameter adjustments. A character speaks differently to their boss, their child, their enemy, and their lover. The invariant is: **the matrix is consistent for each relationship, and the differences between cells encode the power dynamics and emotional valence of each relationship**. Gardner-Chloros and Weston (2015) demonstrated that code-switching in literature is "staged" (deliberately constructed by authors) rather than reproduced, meaning authors consciously design these shifts.

**Encodable Dimensions**:

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `formality_range` | float | [0, 1] | Maximum minus minimum formality across all partners |
| `partner_count` | integer | [1, 10] | Number of distinct relational contexts shown |
| `power_sensitivity` | float | [0, 1] | How much speech shifts based on power differential |
| `intimacy_sensitivity` | float | [0, 1] | How much speech shifts based on emotional closeness |
| `threat_sensitivity` | float | [0, 1] | How much speech shifts based on perceived danger |

**Sacred Tongue Mapping**: **RU (Binding)** -- the relational matrix encodes the binding between self and other. Each cell in the matrix is a specific binding contract: "when I am with X, I become Y."

**Polyhedral Face**: **Icosidodecahedron (Full Cognitive Map)** -- 32 faces (the most complex shape in the PHDM). The relational voice matrix requires high-dimensional representation because each relationship activates a different combination of personality facets.

**Training Data Example**:
```json
{
  "pattern": "relational_voice_matrix",
  "source_text": "Elizabeth Bennet (Austen, Pride and Prejudice): With Jane -- warm, confiding, complete sentences, genuine emotion. With Mr. Collins -- short, ironic, barely concealed contempt. With Darcy (early) -- formal, combative, wit as weapon. With Darcy (late) -- still witty but softened, longer sentences, fewer verbal parries.",
  "encoding": {
    "formality_range": 0.72,
    "partner_count": 6,
    "power_sensitivity": 0.45,
    "intimacy_sensitivity": 0.85,
    "threat_sensitivity": 0.30
  },
  "tongue": "RU",
  "polyhedron": "Icosidodecahedron"
}
```

---

### Pattern E2: The Foil Contrast Function

**Source**: Art of Narrative, "Character Foils" (2020); LitCharts definitions; Gillaim Writers Group, "Crafting Foil Characters" (2024); NotMFA, "Form Not Formula: Mirrors and Foils" (2025)

**The Invariant**: A foil is not simply "the opposite" of the protagonist. Effective foils share the same narrative space, goals, or wounds but employ different internal logic. The invariant from NotMFA (2025): "A foil doesn't echo the protagonist's wound, it challenges their worldview. The foil lives inside the same narrative space -- similar goals, similar obstacles -- but runs on a different internal logic." The foil is the same equation with different constants.

**Encodable Dimensions**:

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `shared_dimension_count` | integer | [1, 5] | Number of personality dimensions where foil and protagonist overlap |
| `divergent_dimension_count` | integer | [1, 5] | Number of personality dimensions where they differ maximally |
| `logic_system_distance` | float | [0, 1] | How different their decision-making frameworks are |
| `outcome_divergence` | float | [0, 1] | How different their story outcomes are |

**Sacred Tongue Mapping**: **DR (Structure)** -- the foil relationship is a structural pattern. It defines the architecture of contrast within the narrative.

**Polyhedral Face**: **Csaszar (Mirror Identity)** -- the mirror character technique maps directly to the Csaszar's mirror-like toroidal topology.

---

### Pattern E3: Code-Switching as Character Signal

**Source**: Gardner-Chloros & Weston, *Language and Literature* (2015); Akaeze, "Character Definition and Identity: The Case of Code-Switching" (2023); Oxford Academic, "How Literary Texts 'Stage' Code-Switching" (2024)

**The Invariant**: When characters shift register, language, or communication style between social contexts, the shift itself is characterization. The invariant: **code-switching signals encode three things simultaneously: (1) the character's social range, (2) the power dynamic with the current interlocutor, and (3) the character's awareness of social performance**. Characters who never code-switch have narrow social range or low self-awareness. Characters who code-switch fluidly have high social intelligence.

**Encodable Dimensions**:

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `register_range` | float | [0, 1] | Span between most formal and most informal speech |
| `switch_frequency` | float | [0, 1] | How often the character shifts register |
| `switch_triggers` | set | variable | What causes register shifts (power, intimacy, threat, audience) |
| `social_awareness` | float | [0, 1] | How deliberately the character manages their register |

**Sacred Tongue Mapping**: **AV (Metadata)** -- code-switching IS metadata generation. Each switch annotates the social context without stating it explicitly.

**Polyhedral Face**: **Triangular Cupola (Bridge)** -- the cupola bridges triangular and square faces, analogous to how code-switching bridges different social registers.

---

## F. Arc Construction Invariants

### Research Summary

Character arcs have been theorized since Aristotle, but modern frameworks (Weiland, McKee, Dramatica, the Enneagram) converge on a surprisingly small set of structural invariants. Computational analysis (Reagan et al., 2016) confirms that emotional trajectories cluster into six basic shapes across 1,700+ stories.

### Pattern F1: The Wound-Lie-Want-Need Quaternary

**Source**: K.M. Weiland, *Creating Character Arcs* (2016); C.S. Lakin, "The Character Arc in Six Specific Stages" (2019); StoryFlint, "8 Lessons from Creating Character Arcs" (2024); Jerry Jenkins, "How to Create a Powerful Character Arc" (2024)

**The Invariant**: All positive character arcs contain four linked elements: (1) a **Wound** (past trauma or formative event), (2) a **Lie** (false belief that the wound generated), (3) a **Want** (conscious goal driven by the lie), and (4) a **Need** (unconscious truth that contradicts the lie). The invariant from Weiland: "The Want and Need must be different -- and usually opposed." The arc IS the journey from Want to Need (or the refusal of that journey in a negative arc). The Wound generates the Lie, the Lie generates the Want, and the Need exists as the Lie's antithesis.

**Encodable Dimensions**:

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `wound_severity` | float | [0, 1] | Magnitude of the formative trauma |
| `lie_entrenchment` | float | [0, 1] | How deeply the character believes the lie |
| `want_need_distance` | float | [0, 1] | How far apart the conscious want and unconscious need are |
| `arc_type` | categorical | {positive, flat, negative, disillusionment, corruption} | Direction of transformation |
| `arc_completion` | float | [0, 1] | How fully the character transitions from lie to truth |

**Sacred Tongue Mapping**: **DR (Structure)** primary, **KO (Intent)** secondary -- the wound-lie-want-need quaternary IS the structural DNA of the arc (DR). The Want is the character's conscious intent (KO), while the Need is the structural truth that the arc reveals.

**Polyhedral Face**: **Icosahedron (Deep Personality)** -- 20 triangular faces, the most complex Platonic solid. Character arcs are the deepest personality structures, requiring the highest-resolution encoding. The 20 faces can map to 20 arc checkpoint states.

**Training Data Example**:
```json
{
  "pattern": "wound_lie_want_need",
  "source_text": "Tony Stark / Iron Man: Wound = kidnapping and weapons legacy. Lie = 'I can protect everyone by being the smartest person in the room alone.' Want = build better armor, control threats. Need = trust others, accept vulnerability. Arc across 11 films: gradual dissolution of the Lie through repeated failure of solo control.",
  "encoding": {
    "wound_severity": 0.85,
    "lie_entrenchment": 0.90,
    "want_need_distance": 0.75,
    "arc_type": "positive",
    "arc_completion": 0.95
  },
  "tongue": "DR",
  "polyhedron": "Icosahedron"
}
```

---

### Pattern F2: The Six Emotional Arc Shapes

**Source**: Andrew Reagan, Lewis Mitchell, Dilan Kiley, Christopher Danforth, Peter Sheridan Dodds, "The emotional arcs of stories are dominated by six basic shapes," *EPJ Data Science* 5(1), 2016. [arXiv:1606.07772](https://arxiv.org/abs/1606.07772)

**The Invariant**: Computational analysis of 1,700+ Project Gutenberg stories using sentiment analysis revealed that all narrative emotional trajectories cluster into six basic shapes: (1) **Rags to Riches** (steady rise), (2) **Tragedy** (steady fall), (3) **Man in a Hole** (fall then rise), (4) **Icarus** (rise then fall), (5) **Cinderella** (rise-fall-rise), (6) **Oedipus** (fall-rise-fall). These six arcs confirmed Kurt Vonnegut's rejected master's thesis hypothesis. The most commercially successful stories use arcs 3 (Man in a Hole), 5 (Cinderella), and combinations thereof.

**Encodable Dimensions**:

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `arc_shape` | categorical | {rise, fall, fall_rise, rise_fall, rise_fall_rise, fall_rise_fall} | Which of the six basic shapes |
| `amplitude` | float | [0, 1] | Magnitude of emotional swing |
| `inflection_count` | integer | [0, 4] | Number of direction changes |
| `emotional_trajectory` | float[] | variable | Time-series of sentiment values (normalized) |

**Sacred Tongue Mapping**: **CA (Compute)** -- the emotional arc is a computable function. Given shape + amplitude + inflection points, the trajectory can be generated.

**Polyhedral Face**: **Cube (Stability)** -- the 6 faces of the cube map directly to the 6 basic arc shapes. The cube represents the stable, fundamental structure of narrative emotion.

---

### Pattern F3: The Minimum Viable Arc

**Source**: Dabble Writer, "Character Arc Template" (2024); Fiction Frameworks, "Character Arc Development Basics" (2024); Storm Writing School, "Create a Moving Character Arc" (2024)

**The Invariant**: The minimum viable character arc requires exactly three elements: (1) a **starting state** (who the character is), (2) a **catalytic event** (what forces change), and (3) a **landing state** (who they become or refuse to become). The catalytic event must make the starting state untenable. The landing state must be genuinely different from (or a deliberate reinforcement of) the starting state. Without all three, there is no arc -- there is merely a sequence of events.

**Encodable Dimensions**:

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `start_state_vector` | float[5] | [0,1]^5 | Big Five personality values at arc start |
| `catalyst_magnitude` | float | [0, 1] | How disruptive the catalytic event is |
| `end_state_vector` | float[5] | [0,1]^5 | Big Five personality values at arc end |
| `state_distance` | float | [0, 1] | Euclidean distance between start and end vectors |
| `arc_present` | boolean | {0, 1} | Whether minimum viable arc requirements are met |

**Sacred Tongue Mapping**: **DR (Structure)** -- the minimum viable arc is the minimum viable narrative structure.

**Polyhedral Face**: **Tetrahedron (Foundation)** -- 4 faces, the simplest polyhedron. The minimum viable arc is the simplest meaningful transformation. Three faces for start/catalyst/end, one face for the arc's thematic meaning.

---

## G. Emotional Vocabulary Distribution

### Research Summary

How characters express emotion is not uniform. Authors distribute emotional expression across four channels: action, dialogue, internal monologue, and physical description. The distribution is both character-specific and author-specific. Computational analysis of emotional vocabulary in fiction (Jacobs, 2019) confirms that emotional profiles are computable and distinctive.

### Pattern G1: The Four-Channel Emotion Model

**Source**: MasterClass, "Show Don't Tell" (2026); Hidden Gems Book Blog, "How to Show, Not Tell with Emotions" (2023); ProWritingAid, "Show Don't Tell" (2024); Angela Ackerman & Becca Puglisi, *The Emotion Thesaurus* (2nd ed., 2019)

**The Invariant**: Effective emotional characterization distributes expression across four channels: (1) **somatic** (physical body reactions -- racing heart, sweating, nausea), (2) **behavioral** (observable actions -- slamming doors, pacing, clenching fists), (3) **verbal** (what the character says about their emotions -- direct or deflected), and (4) **cognitive** (internal thoughts and interpretations). The invariant: **each character has a consistent channel preference**. Stoic characters route through somatic and behavioral channels. Verbose characters route through verbal. Introspective characters route through cognitive. Ackerman and Puglisi's *Emotion Thesaurus* catalogs 130 emotions with body language cues, thoughts, and visceral responses for each, providing the most comprehensive taxonomy available.

**Encodable Dimensions**:

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `somatic_preference` | float | [0, 1] | How much emotion is expressed through body |
| `behavioral_preference` | float | [0, 1] | How much emotion is expressed through action |
| `verbal_preference` | float | [0, 1] | How much emotion is expressed through dialogue |
| `cognitive_preference` | float | [0, 1] | How much emotion is expressed through thought |
| `channel_vector` | float[4] | simplex | Normalized distribution (must sum to 1.0) |
| `emotional_range` | float | [0, 1] | Number of distinct emotions displayed / 130 |
| `emotional_intensity_mean` | float | [0, 1] | Average intensity of emotional displays |

**Sacred Tongue Mapping**: **RU (Binding)** -- the emotion channel preference binds the internal state to the external expression mode. It is the coupling constant between feeling and display.

**Polyhedral Face**: **Cuboctahedron (Balance)** -- the balance between four channels mirrors the cuboctahedron's role as the equilibrium between cube (stability/containment) and octahedron (reactivity/expression).

**Training Data Example**:
```json
{
  "pattern": "four_channel_emotion",
  "source_text": "Comparison -- Katniss Everdeen (Collins): Heavy somatic (0.45), moderate behavioral (0.30), low verbal (0.10), moderate cognitive (0.15). She FEELS emotions in her body, ACTS on them, rarely TALKS about them, occasionally THINKS about them. vs. Hazel Grace (Green, TFIOS): Low somatic (0.10), low behavioral (0.15), high verbal (0.40), high cognitive (0.35). She TALKS and THINKS about emotions constantly.",
  "encoding_katniss": {
    "channel_vector": [0.45, 0.30, 0.10, 0.15],
    "emotional_range": 0.42,
    "emotional_intensity_mean": 0.78
  },
  "encoding_hazel": {
    "channel_vector": [0.10, 0.15, 0.40, 0.35],
    "emotional_range": 0.65,
    "emotional_intensity_mean": 0.55
  },
  "tongue": "RU",
  "polyhedron": "Cuboctahedron"
}
```

---

### Pattern G2: The Emotion Suppression Signature

**Source**: Storm Writing School, "Body Language Pitfalls" (2024); Frontiers in Robotics and AI, "Sentiment Analysis for Fiction Characters" (Jacobs, 2019)

**The Invariant**: How a character suppresses emotion is as distinctive as how they express it. Some characters suppress through overcontrol (rigid posture, flat voice, deliberate stillness). Others suppress through displacement (redirecting anger into humor, fear into aggression). Still others leak (the suppression fails in characteristic ways -- micro-expressions, involuntary gestures, speech hesitations). The invariant: **the suppression pattern is more character-diagnostic than the expression pattern**, because suppression reveals the gap between felt emotion and performed identity.

**Encodable Dimensions**:

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `suppression_method` | categorical | {overcontrol, displacement, leakage, denial, intellectualization} | Primary suppression strategy |
| `suppression_success_rate` | float | [0, 1] | How effectively the character hides emotions |
| `leak_channel` | categorical | {somatic, behavioral, verbal, cognitive} | Where suppressed emotions escape |
| `suppression_cost` | float | [0, 1] | Observable toll of ongoing suppression |

**Sacred Tongue Mapping**: **UM (Security)** -- emotion suppression IS a security operation. The character is protecting their internal state from external observation.

**Polyhedral Face**: **Great Dodecahedron (Adversarial)** -- the Kepler-Poinsot star polyhedron represents adversarial profiles. Emotion suppression is an adversarial relationship between the character's felt self and their performed self.

---

## H. The Contradiction Principle

### Research Summary

E.M. Forster's 1927 distinction between "flat" and "round" characters remains the foundational framework, but modern computational approaches have quantified what makes characters round: internal contradiction managed by coherent logic.

### Pattern H1: The Productive Contradiction

**Source**: E.M. Forster, *Aspects of the Novel* (1927); MasterClass, "Round vs. Flat Characters" (2026); Writers.com, "Flat Characters and Round Characters in Literature" (2024); September C. Fawkes, "Flat Characters vs. Round Characters" (2021)

**The Invariant**: Round characters contain contradictions; flat characters do not. But the invariant is more specific than this: **productive contradictions are those where both sides of the contradiction are psychologically motivated by the same wound**. A character who is simultaneously generous and stingy is flat if these traits appear randomly. The same character is round if their generosity toward strangers and stinginess with family both trace to a childhood of poverty -- generosity proves they've escaped it, stinginess protects against returning to it. The contradiction is the wound viewed from two angles.

**Encodable Dimensions**:

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `contradiction_count` | integer | [0, 5] | Number of active trait contradictions |
| `contradiction_coherence` | float | [0, 1] | How well contradictions trace to a common source |
| `contradiction_visibility` | float | [0, 1] | How obvious the contradictions are to the reader |
| `roundness_score` | float | [0, 1] | Composite measure: contradiction_count * coherence * visibility |
| `trait_pairs` | array | variable | List of contradicting trait pairs |

**Sacred Tongue Mapping**: **DR (Structure)** primary, **KO (Intent)** secondary -- contradictions are structural features of personality architecture (DR). The coherence that unifies them is the hidden intent (KO) that makes the contradiction productive rather than arbitrary.

**Polyhedral Face**: **Szilassi (Recursive Identity)** -- every face of the Szilassi touches every other face. In a productive contradiction, every trait connects to every other trait through the central wound. The topology of contradiction IS the Szilassi topology.

**Training Data Example**:
```json
{
  "pattern": "productive_contradiction",
  "source_text": "Jay Gatsby (Fitzgerald): Generous host / secretive past. Romantic idealist / criminal businessman. Self-made man / fabricated identity. All contradictions trace to one wound: Gatsby believes love must be purchased, identity must be constructed, and reality can be overwritten by sufficient will. The contradictions ARE the character.",
  "encoding": {
    "contradiction_count": 3,
    "contradiction_coherence": 0.92,
    "contradiction_visibility": 0.85,
    "roundness_score": 0.78,
    "trait_pairs": [
      ["generous_host", "secretive_past"],
      ["romantic_idealist", "criminal_businessman"],
      ["self_made", "fabricated_identity"]
    ]
  },
  "tongue": "DR",
  "polyhedron": "Szilassi"
}
```

---

### Pattern H2: The Flat-Round Spectrum

**Source**: Forster (1927); Oregon State University, "What are Flat vs Round Characters?" (2024); ProWritingAid, "Round vs Flat Character" (2024); Scribophile Academy, "Round vs. Flat Characters" (2024)

**The Invariant**: Flat and round are not binary categories but endpoints on a spectrum. The spectrum is defined by three factors: (1) **interiority access** (does the reader access the character's thoughts?), (2) **contradiction count** (how many active contradictions exist?), and (3) **change capacity** (does the character transform?). Importantly, flatness is not a flaw. Flat characters serve structural purposes (foils, comic relief, thematic embodiment). The invariant: **the appropriate flatness/roundness is determined by narrative function, not character importance**.

**Encodable Dimensions**:

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `interiority_access` | float | [0, 1] | Degree of reader access to character's inner life |
| `complexity_index` | float | [0, 1] | Weighted combination of contradiction, change, and interiority |
| `narrative_function` | categorical | {protagonist, antagonist, foil, mentor, herald, ally, trickster} | Propp/Campbell archetype role |
| `appropriate_depth` | float | [0, 1] | Expected complexity given the narrative function |
| `depth_deviation` | float | [-1, 1] | actual complexity minus expected complexity |

**Sacred Tongue Mapping**: **AV (Metadata)** -- the flat-round classification IS metadata about the character's narrative role. It classifies without defining content.

**Polyhedral Face**: **Rhombic Dodecahedron (Space-Filling)** -- space-filling polyhedra tile without gaps, just as the full cast of characters must fill the narrative space without gaps in function. Some tiles are simple (flat characters), others complex (round characters), but together they tile the narrative.

---

## I. Crowd-Sourced Pattern Mining

### Research Summary

Three major crowd-sourced and computational resources provide large-scale pattern data: TV Tropes (24,000+ tropes across 40,000+ works), Dramatica theory (systematic character dimensionality), and Bamman et al.'s computational persona models. Together they offer the most comprehensive empirical base for character pattern extraction.

### Pattern I1: Bamman's Latent Persona Clusters

**Source**: David Bamman, Brendan O'Connor, Noah A. Smith, "Learning Latent Personas of Film Characters," ACL 2013; David Bamman, Ted Underwood, Noah A. Smith, "A Bayesian Mixed Effects Model of Literary Character," ACL 2014; BookNLP pipeline (Bamman et al., 2014-2021)

**The Invariant**: When Bamman et al. (2013) applied latent variable models to 42,306 movie plot summaries from Wikipedia, they learned K=50 latent lexical topics and P=100 latent personas. Of these 100, the top 14 by frequency accounted for the majority of character instances. A persona is defined as "a set of mixtures over latent lexical classes" capturing the stereotypical actions of which a character is agent and patient, as well as attributes by which they are described. The invariant: **the effective dimensionality of character types is far lower than the combinatorial space would suggest -- approximately 20-30 clusters account for 80%+ of all characters in Western narrative**. The 2014 paper extended this to 15,000 novels with author-style controls.

**Encodable Dimensions**:

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `persona_cluster_id` | integer | [0, 100] | Which latent persona cluster the character belongs to |
| `cluster_confidence` | float | [0, 1] | Confidence of cluster assignment |
| `agent_action_distribution` | float[] | simplex | Distribution over action types as agent |
| `patient_action_distribution` | float[] | simplex | Distribution over action types as patient |
| `attribute_distribution` | float[] | simplex | Distribution over descriptive attributes |

**Sacred Tongue Mapping**: **CA (Compute)** -- latent persona clusters are computed representations. The cluster assignment IS the computational output.

**Polyhedral Face**: **Icosidodecahedron (Full Cognitive Map)** -- 32 faces for the most complex representation. The persona cluster model requires the full cognitive map because it integrates actions, patient-hood, and attributes simultaneously.

---

### Pattern I2: Dramatica's Four-Dimensional Character Model

**Source**: Melanie Anne Phillips & Chris Huntley, *Dramatica: A New Theory of Story* (1994); Storymind.com, Dramatica Theory Book chapters 7, 9; Narrative First, "Adapting Character Motivations to the Story Goal" (2024)

**The Invariant**: Dramatica models characters along four independent dimensions: (1) **Motivation** (the force that moves the character), (2) **Purpose** (the direction of movement), (3) **Methodology** (the approach used), and (4) **Evaluation** (the standard for measuring progress). Each dimension has 16 elements organized into quads, yielding 64 base elements total. The fundamental KTAD quad (Knowledge, Thought, Ability, Desire) underlies all dimensions. The invariant: **complete characters address all four dimensions; incomplete characters are missing one or more dimensions, and the missing dimension IS the character's blind spot**.

**Encodable Dimensions**:

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `motivation_element` | categorical | 16 values | Primary motivating force |
| `purpose_element` | categorical | 16 values | Primary directional goal |
| `methodology_element` | categorical | 16 values | Primary approach/strategy |
| `evaluation_element` | categorical | 16 values | Primary success metric |
| `dimensional_completeness` | float | [0, 1] | How many of 4 dimensions are actively addressed |
| `blind_spot_dimension` | categorical | {motivation, purpose, methodology, evaluation, none} | Which dimension is missing |

**Sacred Tongue Mapping**: **DR (Structure)** -- Dramatica is explicitly a structural theory. The four dimensions define the structural architecture of character.

**Polyhedral Face**: **Cube (Stability)** -- 6 faces. The cube's orthogonal stability maps to the orthogonal independence of Dramatica's four dimensions plus the two meta-axes (change/steadfast, start/stop).

---

### Pattern I3: TV Tropes as Pattern Ontology

**Source**: TV Tropes wiki (24,000+ tropes, 40,000+ works); Chou, "Structures in Tropes Networks: Toward a Formal Story Grammar," ICCC 2021; ACL 2020, "Analyzing Gender Bias within Narrative Tropes"; Gala et al., GitHub repository (30K tropes, 1.9M instances); ACM CHI 2023, "TaleStream: Supporting Story Ideation with Trope Knowledge"

**The Invariant**: TV Tropes represents the largest crowd-sourced ontology of narrative patterns. Computational analysis reveals that tropes form network structures with discoverable grammar rules. Chou (ICCC 2021) extracted statistical patterns from trope networks to identify underlying narrative grammar. The invariant: **authors do not invent character patterns from scratch -- they compose from a finite (but large) vocabulary of known patterns, combined in novel ways**. The creative act is in combination, not in element creation. The trope network has small-world properties -- most tropes are reachable from most other tropes in 3-4 steps.

**Encodable Dimensions**:

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `trope_set` | set | variable | Set of TV Tropes tags that apply to this character |
| `trope_count` | integer | [1, 50] | Number of applicable tropes |
| `trope_rarity_mean` | float | [0, 1] | Average rarity of the character's tropes |
| `trope_combination_novelty` | float | [0, 1] | How unusual the specific trope combination is |
| `archetype_alignment` | float | [0, 1] | How closely the character fits a known archetype |

**Sacred Tongue Mapping**: **AV (Metadata)** -- trope tags ARE metadata. They classify and annotate without containing the narrative content itself.

**Polyhedral Face**: **Rhombic Dodecahedron (Space-Filling)** -- tropes tile the narrative possibility space. Each trope is a rhombic face that, combined with others, fills the complete character design space without gaps.

---

### Pattern I4: Propp's 7 Character Functions

**Source**: Vladimir Propp, *Morphology of the Folktale* (1928/1968); ResearchGate, "The Thirty-One Functions" (2017); Wikipedia, "Vladimir Propp"

**The Invariant**: Propp analyzed 115 Russian folktales and found that all characters resolve into 7 abstract functions: (1) **Villain**, (2) **Dispatcher**, (3) **Helper**, (4) **Donor**, (5) **Hero**, (6) **False Hero**, (7) **Princess/Prize**. These functions are independent of the specific characters who fill them. Multiple functions can be filled by one character, or one function can be split across multiple characters. The invariant: **narrative function is separable from character identity -- the same personality can serve different functions in different stories, and different personalities can serve the same function**.

**Encodable Dimensions**:

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `propp_function` | categorical | {villain, dispatcher, helper, donor, hero, false_hero, princess} | Primary narrative function |
| `function_purity` | float | [0, 1] | How exclusively the character serves one function |
| `function_count` | integer | [1, 7] | Number of functions the character serves |

**Sacred Tongue Mapping**: **DR (Structure)** -- Propp's functions are pure structural roles. They define the narrative architecture independent of content.

**Polyhedral Face**: **Pentagonal Bipyramid (Connector)** -- 10 faces, connecting the 7 functions through the narrative. The bipyramid's dual apex structure represents the protagonist-antagonist axis around which all other functions orbit.

---

## J. The Physical-Personality Bridge

### Research Summary

Physical description in fiction is never neutral. Authors use appearance as a shorthand for personality, and the relationship between physical description and personality expectation is both culturally constructed and narratively exploitable. Skilled authors either confirm or subvert the physical-personality mapping, but they never ignore it.

### Pattern J1: The Expectation-Subversion Dynamic

**Source**: Writer's Atelier, "Using Physical Descriptions to Create Character Personality" (Simonds, 2022); Carve Magazine, "10 Tips for Writing Physical Descriptions" (2024); Carol Newman Cronin, "Fiction Writing: Matching Physical Traits to Personality" (2023)

**The Invariant**: Physical description creates personality expectations (cultural stereotypes, genre conventions, visual shorthand). Authors make one of three choices: (1) **confirm** the expectation (the muscular character IS tough), (2) **subvert** it (the muscular character is gentle and afraid of conflict), or (3) **complicate** it (the muscular character is tough in some contexts and gentle in others). The invariant: **the relationship between physical description and personality must be deliberate -- random or absent relationships signal amateur writing**. Confirmation is efficient (low word cost for high information transfer). Subversion is memorable (creates cognitive surprise). Complication is deepening (creates roundness).

**Encodable Dimensions**:

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `physical_personality_alignment` | float | [-1, 1] | -1 = full subversion, 0 = no relationship, 1 = full confirmation |
| `description_strategy` | categorical | {confirm, subvert, complicate, absent} | Author's approach |
| `stereotype_invoked` | boolean | {0, 1} | Whether a recognizable physical-personality stereotype is engaged |
| `description_specificity` | float | [0, 1] | How specific/unique the physical description is vs generic |
| `personality_reveal_delay` | float | [0, 1] | How long after physical description before personality is shown |

**Sacred Tongue Mapping**: **AV (Metadata)** primary, **KO (Intent)** secondary -- physical description IS metadata about the character (AV). The deliberate alignment or subversion encodes authorial intent (KO) about how the reader should initially perceive the character.

**Polyhedral Face**: **Truncated Tetrahedron (Filtered)** -- the truncation (cutting corners off the tetrahedron) represents how physical description is always a filtered, partial view. What the author chooses to describe and what they omit IS the filter function.

**Training Data Example**:
```json
{
  "pattern": "expectation_subversion",
  "source_text": "Tyrion Lannister (George R.R. Martin): Physically small, 'misshapen' dwarf -- expectation: weak, pitiable, minor. Personality: brilliant strategist, devastating wit, political operator, deeply empathetic. Strategy: SUBVERT on competence, CONFIRM on social marginalization, COMPLICATE on morality.",
  "encoding": {
    "physical_personality_alignment": -0.72,
    "description_strategy": "subvert",
    "stereotype_invoked": true,
    "description_specificity": 0.88,
    "personality_reveal_delay": 0.05
  },
  "tongue": "AV",
  "polyhedron": "Truncated_Tetrahedron"
}
```

---

### Pattern J2: The Characteristic Physical Detail

**Source**: StoryGrid, "Character Descriptions: 50+ Examples and Techniques" (2024); All Write Alright, "Tricks for Describing a Character's Appearance" (2024); MasterClass, "How to Write Vivid Character Descriptions" (2026)

**The Invariant**: Effective physical description does not attempt completeness. Instead, it selects one or two **characteristic physical details** that do double duty as personality indicators. The invariant: **the chosen detail must be both visually distinctive and psychologically resonant**. A character's bitten fingernails communicate more than their hair color. A character's immaculate shoes in a dirty environment communicates more than their height. The detail is chosen because it is the physical expression of the character's inner state.

**Encodable Dimensions**:

| Dimension | Type | Range | Description |
|-----------|------|-------|-------------|
| `detail_count` | integer | [0, 5] | Number of characteristic physical details chosen |
| `detail_psychological_load` | float | [0, 1] | How much personality information the detail carries |
| `detail_category` | categorical | {habitual, involuntary, chosen, congenital, acquired} | Type of physical detail |
| `detail_narrative_function` | categorical | {shorthand, foreshadowing, contrast, continuity, symbol} | What the detail does in the story |

**Sacred Tongue Mapping**: **KO (Intent)** -- the characteristic detail IS the author's intent compressed into a single physical observation. It communicates what the author wants the reader to understand about the character at minimum cost.

**Polyhedral Face**: **Bilinski Dodecahedron (Compressed)** -- the Bilinski is a compressed variant of the rhombic dodecahedron. Characteristic physical details ARE compressed personality representations -- maximum information in minimum description.

---

## Cross-Reference Tables

### Table 1: Pattern-to-Sacred-Tongue Distribution

| Tongue | Code | Patterns Mapped | Primary Role |
|--------|------|----------------|-------------|
| KO (Intent) | 1.00 | A1, B1, D2, F1, H1, J2 | Character intent, conscious goals, authorial intent |
| AV (Metadata) | 1.62 | A2, C2, E3, H2, I3, J1 | Classification, tagging, validation, genre signals |
| RU (Binding) | 2.62 | B2, C3, E1, G1 | Relationships, obligations, coupling functions |
| CA (Compute) | 4.24 | C1, F2, I1 | Computable functions, algorithmic patterns |
| UM (Security) | 6.85 | B3, D1, D2, G2 | Protected states, boundaries, suppression, the unsaid |
| DR (Structure) | 11.09 | A3, E2, F1, F3, H1, I2, I4 | Architecture, structural DNA, organizational patterns |

### Table 2: Pattern-to-Polyhedron Distribution

| # | Polyhedron | Family | Personality Role | Patterns Mapped |
|---|-----------|--------|-----------------|----------------|
| 1 | Tetrahedron | Platonic | Foundation | A1, F3 |
| 2 | Cube | Platonic | Stability | F2, I2 |
| 3 | Octahedron | Platonic | Reactive | B1, C3 |
| 4 | Dodecahedron | Platonic | Complex Reasoning | C1 |
| 5 | Icosahedron | Platonic | Deep Personality | F1 |
| 6 | Truncated Tetrahedron | Archimedean | Filtered | A3, J1 |
| 7 | Cuboctahedron | Archimedean | Balance | A2, G1 |
| 8 | Icosidodecahedron | Archimedean | Full Cognitive Map | E1, I1 |
| 9 | Small Stellated Dodecahedron | Kepler-Poinsot | Risk | B2 |
| 10 | Great Dodecahedron | Kepler-Poinsot | Adversarial | G2 |
| 11 | Szilassi | Toroidal | Recursive Identity | D1, H1 |
| 12 | Csaszar | Toroidal | Mirror Identity | B3, E2 |
| 13 | Pentagonal Bipyramid | Johnson | Connector | C2, I4 |
| 14 | Triangular Cupola | Johnson | Bridge | E3 |
| 15 | Rhombic Dodecahedron | Rhombic | Space-Filling | H2, I3 |
| 16 | Bilinski Dodecahedron | Rhombic | Compressed | D2, J2 |

### Table 3: Encodable Dimension Count by Area

| Area | Dimension Count | Primary Types | Training Example Count |
|------|----------------|--------------|----------------------|
| A. Introduction Patterns | 14 | float, categorical, boolean | 2 |
| B. Decision Architecture | 14 | float, categorical, integer | 1 |
| C. Speech Differentiation | 17 | float, categorical | 1 |
| D. The Unsaid | 9 | float, categorical, integer, set | 1 |
| E. Relationship Patterns | 14 | float, categorical, integer, set | 1 |
| F. Arc Invariants | 15 | float, categorical, integer, float[] | 1 |
| G. Emotional Vocabulary | 11 | float, categorical | 1 |
| H. Contradictions | 9 | float, categorical, integer, array | 1 |
| I. Crowd-Sourced Mining | 17 | integer, float, categorical, set, float[] | 0 |
| J. Physical-Personality Bridge | 9 | float, categorical, integer, boolean | 1 |
| **Total** | **129** | | **10** |

---

## Personality Framework Comparison Table

The following frameworks are referenced across the patterns and can serve as alternative or complementary encoding systems:

| Framework | Dimensions | Source | Encodable? | SCBE Integration Path |
|-----------|-----------|--------|-----------|----------------------|
| Big Five (OCEAN) | 5 continuous | Costa & McCrae (1992) | Yes -- 5 floats [0,1] | Body block axes |
| Enneagram | 9 types + wings + tri-types | Riso & Hudson (1996) | Yes -- type + 2 wing weights | Body block motivation layer |
| MBTI/Cognitive Functions | 4 binary + 8 cognitive functions | Myers & Briggs (1962) | Yes -- 4 binary + 8 float weights | Mind block routing preferences |
| Dramatica KMPE | 4 x 16 elements | Phillips & Huntley (1994) | Yes -- 4 categorical | Mind block decision architecture |
| Moral Foundations | 5-6 continuous | Haidt & Graham (2007) | Yes -- 5-6 floats [0,1] | Spirit block cost weights |
| Propp Functions | 7 categorical | Propp (1928) | Yes -- 7 binary flags | DR structure role assignment |
| Reagan Arc Shapes | 6 categorical | Reagan et al. (2016) | Yes -- 6 probability weights | CA trajectory computation |
| Bamman Personas | ~100 latent clusters | Bamman et al. (2013) | Yes -- cluster ID + confidence | CA persona assignment |
| Ackerman/Puglisi Emotions | 130 emotions x 3 channels | Ackerman & Puglisi (2019) | Yes -- 130 x 3 intensity matrix | RU binding state |

---

## Encoding Recommendations for SCBE Pipeline

### 1. Compact Record Format

Each character analysis should produce a `persona_source_record` with the following structure:

```json
{
  "subject_id": "character_name_work_author",
  "patterns": [
    {
      "pattern_id": "A1_characteristic_moment",
      "encoding": { ... },
      "tongue": "KO",
      "polyhedron": "Tetrahedron",
      "confidence": 0.85,
      "source_span": "Chapter 1, paragraphs 1-3"
    }
  ],
  "body_axes": {
    "big_five": [0.72, 0.45, 0.38, 0.65, 0.55],
    "enneagram_type": 5,
    "moral_foundations": [0.80, 0.60, 0.40, 0.30, 0.50]
  },
  "mind_routing": {
    "dramatica_quad": ["pursuit", "proaction", "effect", "actuality"],
    "speech_signature": { ... },
    "relational_matrix": { ... }
  },
  "spirit_costs": {
    "self": 0.3,
    "user": 0.8,
    "system": 0.5,
    "attacker": 0.9,
    "inaction": 0.4
  }
}
```

### 2. Tongue Tokenization Test Cases

Each pattern section includes text that should be tokenizable through the Sacred Tongue pipeline. Test vectors:

- **KO tokens**: intent verbs (choose, pursue, avoid, protect, reveal)
- **AV tokens**: classification labels (genre, ratio, type, category, tag)
- **RU tokens**: binding operators (between, with, toward, against, bound_to)
- **CA tokens**: computable functions (compute, cluster, classify, predict, generate)
- **UM tokens**: security boundaries (suppress, protect, hide, guard, filter)
- **DR tokens**: structural elements (arc, framework, function, architecture, pattern)

### 3. PHDM Address Generation

For each encoded pattern, generate a PHDM address:

```
address = <polyhedron_index>.<face_index>.<vertex_nearest>
```

Where:
- `polyhedron_index` = 1-16 (from canonical table)
- `face_index` = determined by pattern sub-category
- `vertex_nearest` = determined by encoding vector position on the polyhedron's face

### 4. Cross-Tongue Consistency Check

Any pattern with multiple tongue mappings should produce consistent encodings across tongues. If KO and UM encode the same pattern, the KO encoding (intent-space) and UM encoding (security-space) should be transformable to each other via the tongue weight ratio (UM/KO = 6.85).

---

## Sources

### Academic Papers
- [Bamman, O'Connor, Smith. "Learning Latent Personas of Film Characters." ACL 2013](https://aclanthology.org/P13-1035/)
- [Bamman, Underwood, Smith. "A Bayesian Mixed Effects Model of Literary Character." ACL 2014](https://www.semanticscholar.org/paper/A-Bayesian-Mixed-Effects-Model-of-Literary-Bamman-Underwood/30c9deb8ca14ddef3be7c31e729fc92ee47e6619)
- [Reagan et al. "The emotional arcs of stories are dominated by six basic shapes." EPJ Data Science, 2016](https://arxiv.org/abs/1606.07772)
- [Azmi et al. "Automatic Identification of Character Types from Film Dialogs." Applied Artificial Intelligence, 2017](https://pmc.ncbi.nlm.nih.gov/articles/PMC5652896/)
- [Jacobs. "Sentiment Analysis for Words and Fiction Characters." Frontiers in Robotics and AI, 2019](https://www.frontiersin.org/journals/robotics-and-ai/articles/10.3389/frobt.2019.00053/full)
- [Gardner-Chloros & Weston. "Code-switching and multilingualism in literature." Language and Literature, 2015](https://journals.sagepub.com/doi/10.1177/0963947015585065)
- [Chou. "Structures in Tropes Networks: Toward a Formal Story Grammar." ICCC 2021](https://computationalcreativity.net/iccc21/wp-content/uploads/2021/09/ICCC_2021_paper_21.pdf)
- [Oxford Digital Humanities. "How Literary Texts 'Stage' Code-Switching." Forum for Modern Language Studies, 2024](https://academic.oup.com/fmls/article/60/1/19/7640021)
- [ACL 2020. "Analyzing Gender Bias within Narrative Tropes"](https://aclanthology.org/2020.nlpcss-1.23.pdf)
- [BookNLP pipeline (Bamman et al.)](https://github.com/booknlp/booknlp)

### Books and Monographs
- Robert McKee, *Story: Substance, Structure, Style, and the Principles of Screenwriting* (1997)
- K.M. Weiland, *Creating Character Arcs* (2016)
- Lisa Cron, *Wired for Story* (2012)
- Angela Ackerman & Becca Puglisi, *The Emotion Thesaurus* (2nd ed., 2019)
- Melanie Anne Phillips & Chris Huntley, *Dramatica: A New Theory of Story* (1994)
- Vladimir Propp, *Morphology of the Folktale* (1928/1968)
- E.M. Forster, *Aspects of the Novel* (1927)
- Ernest Hemingway, *Death in the Afternoon* (1932)

### Writing Craft Sources
- [K.M. Weiland, Helping Writers Become Authors](https://www.helpingwritersbecomeauthors.com/)
- [Writers Helping Writers (Ackerman & Puglisi)](https://writershelpingwriters.net/)
- [Author's Pathway, Dialogue Differentiation Guide](https://authorspathway.com/writing-process/writing/why-your-characters-sound-the-same-a-guide-to-dialogue-differentiation/)
- [MasterClass Writing Guides](https://www.masterclass.com/articles/how-to-introduce-characters)
- [NotMFA, "Foil vs. Mirror Characters"](https://www.notmfa.com/craft/form-not-formula-mirrors-and-foils)
- [Storm Writing School, "Body Language Pitfalls"](https://stormwritingschool.com/body-language/)
- [ScreenCraft, "7 Ways to Give Characters Unique Voices"](https://screencraft.org/blog/effective-ways-to-give-your-characters-unique-voices/)
- [StoryGrid, "Character Descriptions: 50+ Examples"](https://storygrid.com/character-descriptions-50-examples-and-techniques-for-writers/)
- [Storymind.com, Dramatica Theory](https://storymind.com/blog/dramatica-a-new-theory-of-story/)
- [Reedsy Studio, Character Introduction Guide](https://reedsy.com/studio/resources/how-to-introduce-a-character)
- [Enneagram for Fiction Writers](https://read.jltooker.com/p/writing-fiction-with-the-enneagram)

### Computational and Data Resources
- [TV Tropes wiki (24,000+ tropes)](https://tvtropes.org/)
- [Gala et al., TV Tropes scraper (GitHub)](https://github.com/dhruvilgala/tvtropes)
- [ACM CHI 2023, "TaleStream: Supporting Story Ideation with Trope Knowledge"](https://dl.acm.org/doi/fullHtml/10.1145/3586183.3606807)
- [BookNLP GitHub repository](https://github.com/booknlp/booknlp)
- [Bamman ACL2013 Personas (GitHub)](https://github.com/dbamman/ACL2013_Personas)

---

## Appendix: Encoding Priority for Implementation

### Phase 1 (Immediate -- can be encoded from existing training data)
1. **F1**: Wound-Lie-Want-Need (every character has this or is flat)
2. **C1**: Structural Voice Signature (directly measurable from dialogue)
3. **H1**: Productive Contradiction (the roundness test)
4. **G1**: Four-Channel Emotion Model (directly observable)

### Phase 2 (Near-term -- requires cross-scene analysis)
5. **E1**: Relational Voice Matrix (requires multiple scenes with different partners)
6. **D1**: Seven-Eighths Rule (requires author knowledge beyond the text)
7. **A1**: Characteristic Moment (requires first-scene isolation)
8. **B1**: Pressure-Choice-Revelation (requires identified decision points)

### Phase 3 (Research -- requires computational pipeline)
9. **I1**: Bamman Persona Clusters (requires BookNLP or similar pipeline)
10. **F2**: Six Emotional Arc Shapes (requires full-text sentiment analysis)
11. **I3**: TV Tropes Pattern Ontology (requires trope database integration)
12. **J1**: Expectation-Subversion Dynamic (requires cultural stereotype database)

---

*This document was generated as a research reference for the SCBE-AETHERMOORE personality scaffold pipeline. All patterns are derived from cited sources and structured for quadruple use: human review, AI training, Sacred Tongue tokenization testing, and PHDM polyhedral mapping.*
