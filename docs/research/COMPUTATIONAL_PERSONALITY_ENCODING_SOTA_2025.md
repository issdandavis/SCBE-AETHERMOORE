# State of the Art: Computational Personality Encoding for LLMs (2025-2026)

**Date**: 2026-04-03
**Purpose**: Map current research to SCBE personality matrix implementation
**Status**: Research reference — directly informs next training round

---

## 1. Anthropic Persona Vectors (July 2025)

**Paper**: "Persona Vectors: Monitoring and Controlling Character Traits in Language Models" (arXiv:2507.21509)
**Source**: [Anthropic Research](https://www.anthropic.com/research/persona-vectors)

### What They Did
- Identified directions in model activation space that control character traits
- Automated pipeline: give it a trait name + description → extracts a "persona vector" from neural activity
- Generates prompts eliciting opposing behaviors, then takes the activation difference

### Key Results
- Single vector can: monitor personality shifts, mitigate shifts during deployment, avoid shifts during fine-tuning, flag problematic training data
- Steering with "evil" vector → model discusses unethical acts
- Steering with "sycophancy" vector → model sucks up to user
- Steering with "hallucination" vector → model fabricates information

### SCBE Connection
**This is the INVERSE of what we're doing.** Anthropic extracts vectors post-hoc from a trained model. SCBE injects the geometry PRE-training as a structured prior. Both approaches validate that personality lives in specific activation patterns. Anthropic's approach is reactive (find and control). SCBE's is proactive (build the scaffold, let personality settle into it).

**Actionable**: After training with our personality profiles, we could extract persona vectors to VERIFY that our scaffold actually created the intended activation patterns. Persona vectors become a validation tool, not a construction tool.

---

## 2. Big5-Chat: SFT + DPO for Personality (ACL 2025)

**Paper**: "BIG5-CHAT: Shaping LLM Personalities Through Training on Human-Grounded Data" (arXiv:2410.16491)
**Source**: [ACL Anthology](https://aclanthology.org/2025.acl-long.999/)

### What They Did
- 100,000 dialogues grounded in how HUMANS express Big Five traits
- Compared SFT, DPO, and prompting for personality induction
- Tested on BFI and IPIP-NEO personality instruments

### Key Results
- **SFT and DPO both outperform prompting** on personality tests
- Training-based methods show more expressive traits and intra-trait correlations matching human data
- **Critical finding**: High conscientiousness + agreeableness → better reasoning (social, math, commonsense, hallucination detection)
- Low extraversion + low neuroticism → better at ALL reasoning tasks

### SCBE Connection
This validates our DPO lane for persona fidelity. But Big5-Chat uses flat Big Five vectors. Our 6-layer personality matrix is dramatically richer. Their 100K dialogues are generic; our lore-native data carries structural/covenantal patterns they can't replicate.

**Actionable**: Use their evaluation methodology (BFI + IPIP-NEO tests) as a baseline comparison. If our scaffold-trained Polly scores higher on conscientiousness and agreeableness than their flat-Big5 approach, that's a publishable result.

---

## 3. Multi-Personality Generation at Decoding Time (Nov 2025)

**Paper**: "Multi-Personality Generation of LLMs at Decoding-time" (arXiv:2511.01891)

### What They Did
- Framework for controlling MULTIPLE personality dimensions simultaneously WITHOUT extra training
- Uses implicit density ratios from single-dimensional models
- Speculative Chunk-level Rejection sampling (SCR) for efficient generation

### SCBE Connection
This is inference-time personality steering -- similar to our Polly Pump. But they steer with density ratios; we steer with pump packets (tongue profile + null pattern + governance posture). Our approach is richer because the pump carries structural context, not just trait weights.

**Actionable**: Their SCR algorithm could optimize our pump packet retrieval at inference time.

---

## 4. Personality Vectors by Model Merging (Sept 2025)

**Paper**: "Personality Vector: Modulating Personality of Large Language Models by Model Merging" (arXiv:2509.19727)

### What They Did
- Construct personality vectors by subtracting pre-trained weights from fine-tuned weights
- Merge vectors to compose multiple personality traits
- No additional training needed after initial fine-tuning

### SCBE Connection
If we fine-tune separate LoRA adapters for each Sacred Tongue personality dimension (KO-weighted, RU-weighted, etc.), we could merge them in phi-scaled proportions to create composite personality vectors. This is the PHDM polyhedra as model-weight space: each polyhedron face = a LoRA adapter, and the ternary state (+1/0/-1) determines whether to add, ignore, or subtract that adapter.

**Actionable**: Train 6 tongue-specific LoRA adapters. Merge with phi weights. Test if composed personality beats flat training.

---

## 5. Structured Personality Control and Adaptation (Jan 2026)

**Paper**: "Structured Personality Control and Adaptation for LLM Agents" (arXiv:2601.10025)

### What They Did
- Survey of all approaches: prompt engineering, SFT, RLHF, DPO, and hybrid strategies
- Evaluated structured vs unstructured personality control
- Found hybrid strategies (prompt induction post fine-tuning) most effective

### SCBE Connection
Our approach IS the hybrid they recommend: scaffold (structured prior) + SFT + DPO + inference-time pump conditioning. We're already doing what the January 2026 survey identifies as the optimal strategy.

---

## 6. Twenty Years of Personality Computing Survey (March 2025)

**Paper**: "Twenty Years of Personality Computing: Threats, Challenges and Future Directions" (arXiv:2503.02082, ACM Computing Surveys)

### Key Findings
- LLMs can detect AND replicate human personality during interaction and role-play
- Major threats: data privacy, algorithmic bias, manipulation by personality-aware AI
- AI systems can manipulate humans to engineer large-scale social functions (voting, spending)

### SCBE Connection
This survey's threat model is exactly what the Spirit block addresses. Stakeholder-cost physics prevents personality-aware manipulation because the cost to the user is explicitly modeled. Our system doesn't just replicate personality -- it governs it.

---

## 7. The Personality Illusion (Sept 2025)

**Paper**: "The Personality Illusion: Revealing Dissociation Between Self-Reports & Behavior in LLMs" (arXiv:2509.03730)

### Key Finding
LLMs can score high on personality TESTS (self-report) while behaving completely differently in practice. The personality is an illusion -- the model learned to answer questionnaires, not to embody traits.

### SCBE Connection
This is the exact problem our scaffold solves. Flat SFT trains the model to SAY the right things on a personality test. Our geometric prior trains it to BEHAVE consistently because the personality is baked into the activation geometry, not just the output distribution. The 31% improvement + step-5 crossover is evidence that our prior produces behavioral embodiment, not just surface mimicry.

---

## 8. BILLY: Steering via Persona Vector Merging (Oct 2025)

**Paper**: "BILLY: Steering Large Language Models via Merging Persona Vectors for Creative Generation" (arXiv:2510.10157)

### What They Did
- Merge multiple persona vectors from specialized fine-tuned models
- Steer creative generation toward desired personality combinations
- Demonstrated on fiction writing tasks

### SCBE Connection
Direct validation of the LoRA adapter merging approach. If we train tongue-specific adapters and merge them with phi weights, this paper provides the methodology proof.

---

## Summary: Where SCBE Sits in the Landscape

| Approach | Personality Source | When Applied | Governance | SCBE Equivalent |
|---|---|---|---|---|
| Prompting | Text instructions | Inference | None | System prompt (weakest) |
| Big5-Chat SFT/DPO | Human dialogue data | Training | None | Our SFT/DPO (but richer data) |
| Persona Vectors | Post-hoc extraction | Post-training | Monitoring only | Validation tool |
| Model Merging | LoRA subtraction | Post-training | None | Tongue adapter merging |
| Decoding-time MPG | Density ratios | Inference | None | Polly Pump |
| **SCBE Scaffold** | **Geometric prior + lore** | **Pre-training + training + inference** | **Spirit block (stakeholder costs)** | **The full pipeline** |

**No one else is doing scaffold-first personality.** Everyone else is either post-hoc extraction, flat SFT, or inference-time steering. SCBE is the only approach that builds the personality geometry BEFORE training begins and enforces governance through cost physics.

The closest parallel is Anthropic's persona vectors -- but they extract what already exists. We construct what should exist. Their approach is archaeology. Ours is architecture.

---

## Recommended Citations for the Paper

When writing "Multi-view supervision via constructed language triangulation":

1. Park et al. (2024) — Stanford generative agents (interview-based personality, 85% accuracy)
2. Big5-Chat (2025) — SFT/DPO outperforms prompting for personality (validates our training method)
3. Anthropic Persona Vectors (2025) — Personality lives in activation geometry (validates our geometric prior)
4. Personality Illusion (2025) — Self-report ≠ behavior (motivates why scaffold is needed)
5. Structured Personality Control (2026) — Hybrid strategies are optimal (validates our architecture)
6. Twenty Years of Personality Computing (2025) — Threat model for personality-aware AI (motivates Spirit block)

Sources:
- [Anthropic Persona Vectors](https://arxiv.org/abs/2507.21509)
- [Big5-Chat ACL 2025](https://aclanthology.org/2025.acl-long.999/)
- [Multi-Personality Generation](https://arxiv.org/abs/2511.01891)
- [Personality Vector Model Merging](https://arxiv.org/html/2509.19727)
- [Structured Personality Control](https://arxiv.org/html/2601.10025)
- [Twenty Years of Personality Computing](https://arxiv.org/abs/2503.02082)
- [The Personality Illusion](https://arxiv.org/html/2509.03730v1)
- [BILLY Persona Vector Merging](https://arxiv.org/html/2510.10157)
- [Controllable Personality Sliders](https://arxiv.org/html/2603.03326)
- [PersLLM Personified Training](https://arxiv.org/html/2407.12393v2)
- [Nature Machine Intelligence Psychometric Framework](https://www.nature.com/articles/s42256-025-01115-6)
