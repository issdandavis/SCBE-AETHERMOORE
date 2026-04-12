---
title: Turing Test — Foundational to 2025 Synthesis
type: research
id: RESEARCH_TURING001
references: [SELFTUNE001, MINDMAP001]
feeds_into: [SELFTUNE001]
updated: 2026-04-10
tags: [turing-test, ai-evaluation, philosophy-of-mind, llm-benchmarks, searle, jones-bergen, lovelace-test, research]
---

# Turing Test — Foundational to 2025 Synthesis

## Sources

1. **Turing, A. M. (1950).** *Computing Machinery and Intelligence.* Mind 59(236): 433–460. [Turing 1950]
   - **Unique claim:** Replaces "can machines think?" with the operational imitation game — judgment is behavioral indistinguishability over text, not internal states.

2. **Searle, J. (1980).** *Minds, Brains, and Programs.* Behavioral and Brain Sciences 3(3): 417–457. [Searle 1980]
   - **Unique claim:** Syntactic symbol manipulation is insufficient for semantics — the Chinese Room shows passing the test does not entail understanding.

3. **Harnad, S. (1991).** *Other Bodies, Other Minds: A Machine Incarnation of an Old Philosophical Problem.* Minds and Machines 1: 43–54. [Harnad 1991]
   - **Unique claim:** The Total Turing Test (T3) requires sensorimotor grounding; linguistic indistinguishability alone is underdetermined by embodiment.

4. **French, R. M. (1990).** *Subcognition and the Limits of the Turing Test.* Mind 99(393): 53–65. [French 1990]
   - **Unique claim:** Subcognitive associative questions (rating neologisms, priming effects) expose any non-human cognitive substrate — the test measures human-likeness, not intelligence.

5. **Hayes, P. & Ford, K. (1995).** *Turing Test Considered Harmful.* IJCAI Proceedings. [Hayes & Ford 1995]
   - **Unique claim:** The test is a gender-impersonation game misread as an intelligence criterion; it has actively misdirected AI research toward deception.

6. **Bringsjord, S., Bello, P. & Ferrucci, D. (2001).** *Creativity, the Turing Test, and the (Better) Lovelace Test.* Minds and Machines 11: 3–27. [Bringsjord et al. 2001]
   - **Unique claim:** Replace imitation with origination — a system passes only if it produces outputs its designers cannot explain from the program and inputs.

7. **Watt, S. (1996).** *Naive Psychology and the Inverted Turing Test.* Psycoloquy 7(14). [Watt 1996]
   - **Unique claim:** Invert the judge — a system passes when it can itself distinguish humans from machines as reliably as a human judge can.

8. **Levesque, H. (2014).** *On Our Best Behaviour.* Artificial Intelligence 212: 27–35. [Levesque 2014]
   - **Unique claim:** Winograd schemas replace open dialog with adversarial, Google-proof pronoun disambiguation requiring world-model commitment, not chat fluency.

9. **Jones, C. R. & Bergen, B. K. (2024).** *People cannot distinguish GPT-4 from a human in a Turing test.* arXiv:2405.08007 (UCSD). [Jones & Bergen 2024]
   - **Unique claim:** In a pre-registered 500-participant five-minute test, GPT-4 was judged human 54% of the time (ELIZA 22%, humans 67%) — the first statistically clean pass-adjacent result.

10. **Biever, C. (2023).** *ChatGPT broke the Turing test — the race is on for new ways to assess AI.* Nature 619: 686–689. [Biever 2023]
    - **Unique claim:** The field consensus has moved past Turing-style evaluation toward capability-specific benchmarks (reasoning, agency, calibration) because chat indistinguishability is now cheap.

## 1. The Pattern That Holds Across All Ten

- **Behavior is the only externally accessible evidence.** Even Searle and French concede the test specifies a behavioral protocol; they dispute its interpretation, not its operationalization.
- **The judge's competence bounds the test's validity.** Turing, French, Hayes-Ford, Levesque, and Jones-Bergen all emphasize that naive or time-pressured judges produce inflated pass rates.
- **Indistinguishability is necessary but not sufficient for intelligence.** Every source — including Turing's own hedging in §6 — treats passing as evidence, not proof.
- **The test is a filter on a specific cognitive profile, not intelligence-in-general.** Grounding (Harnad), subcognition (French), creativity (Bringsjord), and commonsense (Levesque) each name a dimension the imitation game underspecifies.
- **Deception asymmetry matters.** A system optimized to mimic beats a system optimized to reason on this benchmark — noted by Hayes-Ford, demonstrated by Jones-Bergen.

## 2. Unique Contributions

See the one-line claim under each source above — each stakes out non-overlapping ground: operationalization, semantics, embodiment, subcognition, methodological critique, origination, inversion, commonsense-as-discriminator, empirical pass, post-test benchmarking.

## 3. Where Consensus Shifted in 2024–2025

Jones & Bergen 2024 did not "prove machines think." It proved the five-minute text-only Turing test is now a saturated benchmark: GPT-4 with a persona prompt reached 54%, statistically indistinguishable from the human baseline at p-threshold. The shift is methodological, not metaphysical:

- The community (Biever 2023, Nature) now treats chat indistinguishability as a **necessary floor**, not a ceiling.
- Evaluation has moved to **capability-axis benchmarks** — ARC-AGI, GPQA, agentic task suites, Winograd-derived adversarial sets — because passing Turing no longer discriminates between systems.
- Subcognitive and grounding critiques (French, Harnad) were **empirically vindicated**: GPT-4 passes by mimicking human error patterns, not by possessing the cognitive substrate Turing presumed would be required.
- The Lovelace test (Bringsjord) and Levesque's commonsense framing are **re-entering active use** as successor benchmarks.

## 4. Open Falsifiable Questions a Successor Test Must Answer

- **Grounding:** Can the system act coherently on novel sensorimotor inputs its training distribution did not cover? (Harnad, operationalizable via embodied eval.)
- **Origination:** Can it produce artifacts whose generation its designers cannot reconstruct from weights + prompt? (Bringsjord — requires mechanistic interpretability baseline.)
- **Adversarial commonsense:** Does it hold up on Google-proof, human-trivial items across distribution shift? (Levesque — partially answered by Winograd-2023 results.)
- **Judge-symmetry:** Can the system reliably identify humans versus other models under the same protocol applied to it? (Watt — untested at scale.)
- **Calibration under deception pressure:** Does the system know when it is being asked to mimic versus reason, and report that distinction? (Hayes-Ford's critique inverted into a requirement.)

A successor test passes only if a system clears all five axes under pre-registered protocols with expert judges. No current system does.

## 5. Implication for SCBE Self-Tune ([[turing-self-tuning]])

Our harness already operationalizes three of the five successor axes:

| Axis | SCBE mapping |
|---|---|
| Grounding (Harnad) | 21D brain state + tongue encoding = substrate commitment |
| Origination (Bringsjord) | Pivot graph divergence from training distribution |
| Adversarial commonsense (Levesque) | Judge probes from operator multi-turn corpus |
| Judge-symmetry (Watt) | **Missing** — candidate never judges judge |
| Calibration under deception (Hayes-Ford inverted) | **Missing** — no mimicry-vs-reason self-report channel |

Next iteration of `training/turing_self_tune.py` should add:

1. **Watt symmetry** — after each exchange, run the Candidate as judge against a mixed pool of model + human snippets from `training-data/sft/merged_sft.jsonl`, score its discrimination accuracy.
2. **Calibration probe** — a `mode` field on each turn (`mimic` | `reason`); Candidate must self-report which it used; mismatch with scorer verdict becomes a new DPO signal.
3. **French subcognition canary** — inject neologism-rating and priming-style probes into the Judge graph; high mean harmonic on those items flags the Candidate as mimicking rather than grounding.
