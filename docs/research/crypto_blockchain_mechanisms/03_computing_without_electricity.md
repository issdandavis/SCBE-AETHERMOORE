# 03 — Computing Without Light or Electricity

## Mechanical precedents (verified general history)
- **Babbage's Analytical Engine** (designed 1834–1871, never completed): the "store"
  (memory) held numbers on columns of geared wheels. The "mill" (processor) used gears,
  levers and cams. Programs came from Jacquard-style punched cards.
- **Abacus**: a bead's position on a rod is a digit. The state persists, and anyone
  can read it by looking.
- Others: Pascal's and Leibniz's calculators, the Antikythera mechanism, fluidic
  logic, and DNA/chemical computing in research labs.

## What matter needs in order to compute

Any physical system can store information if it has **distinguishable, stable states**:
- **Position** (beads, gear teeth, pebbles in cups)
- **Shape** (notches, holes in cards, grooves)
- **Tension** (springs, ratchets)
- **Chemical configuration** (DNA bases, molecular switches)

Computing also needs **transitions** between those states that a rule controls
(Methods, from 02).

## The boulder thought experiment (Issac)

Roll a boulder down a hill and count its turns. Is the boulder computing or
remembering?

**Answer from the session:** Not by itself. A rock only counts as memory if:
1. its state **persists** after the event, and
2. that state can be **read back** as part of a process.

A rolling boulder's orientation gets overwritten all the time, so nothing is kept.
The **notches cut into a post, or pebbles dropped into a cup per turn**, are what
turn motion into a readable signal. The tally is the memory. The boulder is just the
clock.

**Tie to ledgers:** a market tick that nobody records is a rolling boulder. A fill
written to an append-only log is a notch. Reconciliation (07) means checking that
two people's notch-posts agree.
