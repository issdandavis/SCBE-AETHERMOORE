# 01 — Denning & Tedre: Precepts of Computational Thinking from Early Machines

Source: Peter J. Denning and Matti Tedre, *Computational Thinking* (MIT Press
Essential Knowledge series, 2019), Chapter 3, "Computing Machines."

> **Note on quotations:** We did not have the book text open when writing this. The
> chapter's list of nine precepts, and their numbering, come from the session
> (**⚠ session note — verify against the book**). All descriptions below are
> **paraphrase** unless marked as a quote from a primary source we could confirm.

The chapter's argument (paraphrase): computational thinking did not arrive fully
formed. It was built up from practical lessons learned while building and running
early machines. Each lesson became a lasting "precept" for how we think about
computation.

## Issac's four chosen precepts

### Precept 2 — Boolean Algebra and Circuit Design
- Claude Shannon's MIT master's thesis, *A Symbolic Analysis of Relay and Switching
  Circuits* (1937, published in *Transactions of the AIEE* 57(12), 1938), showed that
  George Boole's algebra could describe and simplify relay circuits.
- Why it matters (paraphrase): logic stops being only philosophy and becomes
  something you can wire. A designer can reason about a circuit symbolically before
  building it.
- The session cited a Herman Goldstine remark that praises the thesis's importance.
  We could not confirm the exact wording, so it is **paraphrased**: Goldstine
  credited the thesis with turning circuit design from an art into a science.
  (Goldstine, *The Computer from Pascal to von Neumann*, Princeton UP, 1972 — **verify page**.)

### Precept 4 — Control Flow
- Babbage's Analytical Engine design (1830s) had conditional branching, meaning the
  next operation could depend on a result. Ada Lovelace's 1843 Notes on Menabrea's
  paper spell out how operation cards would direct the machine.
- Burks, Goldstine & von Neumann, *Preliminary Discussion of the Logical Design of an
  Electronic Computing Instrument* (Institute for Advanced Study, 1946), made
  conditional and unconditional transfer of control a basic part of the
  stored-program design.
- Paraphrase: a program is not just a list of steps. It is a path through those steps,
  chosen by the data.

### Precept 5 — Loops
- Babbage planned for the Engine to repeat a group of operation cards ("backing" the
  cards) instead of punching the same sequence over and over.
- Lovelace's **Note G** sets out a step-by-step procedure for computing Bernoulli
  numbers with the Engine. It is widely called the first published computer program,
  and it reuses operations across iterations.
- A quote from Lovelace we could confirm (Note A, 1843): *"the Analytical Engine weaves
  algebraical patterns just as the Jacquard-loom weaves flowers and leaves."*

### Precept 7 — Subprograms
- David Wheeler's **"Wheeler Jump"** on Cambridge's EDSAC (operational 1949) was a
  way to call a reusable subroutine and return to the caller. The caller's address
  was planted into the subroutine's final jump.
- M. V. Wilkes, D. J. Wheeler & S. Gill, *The Preparation of Programs for an
  Electronic Digital Computer* (Addison-Wesley, 1951), was the first textbook on
  programming. It described a subroutine library.
- Paraphrase: solve something once, name it, and call it from anywhere. Every
  function, library and API comes from this idea.

## Deep dive — Precept 9: Fault Tolerance and Data Protections

**Origin story.** ENIAC (1945–46) used about 17,000+ vacuum tubes. Tube failures were
a daily operating reality. Running filaments continuously and at reduced voltage
lowered the failure rate. Engineers learned to find failures quickly and swap the
failed units. (Commonly reported; **verify exact figures** in Ceruzzi or the
*IEEE Annals* histories.)

**The precept (paraphrase):** Assume parts will fail and data will get corrupted.
Design so that errors are *detected*, *contained*, and *recovered from*, instead of
assuming hardware is perfect.

| Early technique | Idea | Modern descendant |
|---|---|---|
| Redundancy / duplicate runs | Compute twice and compare | Triple modular redundancy, replicas, consensus |
| Parity bits | One extra bit catches single-bit flips | ECC memory (Hamming/SECDED codes) |
| Checksums | Short summary of a block | CRC, SHA hashes, Merkle roots |
| Isolation and recovery | Contain the failure and restart from a known point | Transactions (ACID), checkpoints, write-ahead logs |
| Physical measures | Cooling, power conditioning, shielding | Data-center engineering, RAID across disks |

**Why it is computational thinking and not just engineering:** it changes how you
*write the program*. You plan for checkpoints, validate inputs, and make operations
idempotent. Every later file in this folder applies Precept 9 to markets:
reconciliation is a parity check between two ledgers (07–09), and a blockchain is a
checksummed, replicated, append-only log.
