# The Raven Who Cried Shadow-Hound

*Based on: The Boy Who Cried Wolf*
*Sacred Tongue: KO (Kor'aelin/Korvath) — Intent & Command*
*Ages: 5-8*

---

## The Story

In the early days of Avalon Academy, before the wards were strong, a young messenger raven named Pip was given an important job. Every morning, Pip flew a patrol circle around the outer islands — the Floating Meadows, the Singing Shale Cliffs, the Flame Deserts — and if he spotted shadow-hounds from Varn'ka'zul, he was to cry out in Kor'aelin: *"Vekk-ala! Vekk-ala!"* — which means "Threat approaching! Threat approaching!"

The cry would activate the golem sentinels, wake Grey's garrison, and seal the sky-bridges.

But Pip was bored. The shadow-hounds hadn't come in months.

On a warm Tuesday, Pip dove toward the Floating Meadows and screamed: *"Vekk-ala! Vekk-ala!"*

Twelve golems mobilized. Grey drew his sword. Three professors abandoned mid-lecture. Fizzle Brightcog dropped a beaker of volatile alchemical solution (it exploded, singeing his eyebrows for the fourth time that year).

They found nothing. Pip giggled from a rooftop.

"Just testing the system!" he chirped.

Grey stared at him. "The system worked. That means every person who responded just burned energy, attention, and trust. Those don't refill for free."

Pip did it again on Thursday. Same response, slightly slower. Fizzle didn't drop his beaker this time — he just sighed.

Pip did it a third time on Saturday. This time, only two golems moved. Grey didn't draw his sword. The professors kept teaching.

On Sunday, three shadow-hounds actually came.

They slipped through the gap between the Singing Shale Cliffs and the Flame Deserts — exactly the patrol route Pip was supposed to be watching. But Pip was napping on the Spiral Spire, dreaming of pranks.

When he finally saw them — lean, dark things that hunted fear, not flesh — he screamed: *"Vekk-ala! Vekk-ala!"*

Nobody came.

Polly came. She always came. She was older than the academy, older than the wards, older than Pip's entire family line. She dove at the shadow-hounds with talons spread, buying time. She couldn't fight them — she was a scribe, not a warrior — but she could slow them until someone believed.

It was Alexander Thorne, Izack's firstborn, who heard Polly's wingbeats and looked up. He was seven years old. He ran to Grey and said, very calmly: "Polly is fighting. That means it's real."

Grey mobilized. The hounds were driven back. No one was hurt.

But Pip lost his patrol route. He spent the next year cataloging feathers in the Archive — Polly's assignment, because Polly believed that tedium was the best teacher of attention.

"You used Kor'aelin to say something you didn't mean," Polly told him, adjusting her monocle. "The Control Tongue controls because it carries INTENT. When you fill it with lies, you dilute its power. Every false alarm made the real alarm weaker. The words didn't change. The trust behind them did."

---

## The Song

*(Rhythmic chant — think jump-rope cadence)*

**Pattern: ABAB rhyme, repetitive with a BROKEN pattern on the last verse**

> Pip the raven, sharp and keen,
> Flew the cliffs at half past nine.
> Saw no shadow-hounds between —
> Cried *Vekk-ala!* — "All is fine!"
>
> Golems marched and Grey drew steel,
> Professors dropped their scrolls and chalk.
> Pip laughed loud: "It wasn't real!"
> Grey said: "Trust is not a joke to walk."
>
> Pip the raven, twice he lied,
> Twice the golems came and found just air.
> By the third, they barely tried —
> Pip called out, but no one cared.
>
> Then the shadow-hounds crept in,
> Dark as ink on midnight stone.
> Pip screamed true — but trust was thin,
> And the raven cried alone.
>
> *(spoken, not sung):*
> *Who came? Polly came.*
> *Because Polly always comes.*
> *Not because she heard the word —*
> *Because she knew the difference.*

**Phonetic focus:** The repeated *"Vekk-ala"* trains the hard K sounds of Kor'aelin. The broken pattern in the last verse (spoken instead of sung) mirrors the lesson — the pattern of trust, once broken, doesn't rhyme anymore.

---

## The AI Safety Lesson

**Principle: Signal integrity determines system reliability.**

In AI systems, false positives degrade response to true positives. This is **signal detection theory**: every false alarm raises the threshold for the next alarm. After enough false alerts, the system stops responding — not because the sensor broke, but because the *credibility channel* degraded.

This maps to **Layer 13 (Risk Decision Gate)**: ALLOW/QUARANTINE/ESCALATE/DENY. If the system cries ESCALATE too often on benign inputs, operators learn to ignore escalations. When a real threat arrives, the DENY signal is treated like noise.

**Long-term thinking:** Pip's first false alarm had zero immediate cost to him but depleted a shared resource (trust/attention) that took months to rebuild. In AI safety, this is the **base rate problem**: if 99% of flagged items are false positives, humans stop reviewing the 1% that are real threats.

---

## Real-World Math

- **Signal detection theory (SDT)**: Every detection system has four outcomes: true positive (real threat, detected), false positive (no threat, alarm anyway), true negative (no threat, no alarm), false negative (real threat, missed). Pip's pranks were false positives. They shifted the decision criterion — the responders needed MORE evidence to believe future alarms.
- **Bayesian updating**: P(real threat | alarm) = P(alarm | real threat) * P(real threat) / P(alarm). After three false alarms, P(alarm | real threat) stayed the same but P(alarm) increased (because alarms happen even without threats), so P(real threat | alarm) *decreased*. The math literally says: more false alarms = less belief in real alarms.
- **The boy who cried wolf as a probability problem**: If 3 out of 4 alarms are false, the probability of any given alarm being real is 25%. Would you mobilize 12 golems for a 25% chance? A 10% chance? Where's the threshold?

## Real-World History

- **The Challenger disaster (1986)**: NASA engineers had raised concerns about O-ring failures in cold weather multiple times before the January 28 launch. Each previous concern was reviewed and the launch proceeded safely — creating a normalization of deviance. When engineers raised the alarm one final time before the fatal launch, managers had learned to discount it. Seven astronauts died. The alarm was real. The trust was thin.
- **Radar in WWII**: Early radar systems had enormous false positive rates. Operators stared at screens for hours seeing phantom blips. When real aircraft appeared, tired operators sometimes missed them or dismissed them. The solution was better filtering (reducing false positives) rather than just telling operators to "pay more attention." The system had to earn trust back through accuracy.
