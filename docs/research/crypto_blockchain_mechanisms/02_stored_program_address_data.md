# 02 — Precept 6: The Address–Constants Distinction, and "Data = Concept + Identity + Location + Methods"

## The stored-program insight (paraphrase)

In a stored-program machine (EDVAC report, 1945; IAS design, 1946), instructions and
data sit in the **same memory** as plain numbers. A number in a cell might be:

- a **constant** (a value to compute with),
- an **address** (a pointer to some other cell), or
- an **instruction** (an operation code plus an address).

The hardware does not label which is which. **Interpretation decides.** Denning &
Tedre treat this as a precept: you have to keep track of whether a number means "this
value" or "the place where the value lives." (**⚠ session note — precept numbering to verify.**)

## Issac's house / mailbox analogy

A street address is a number, and so is the amount of money in an envelope inside
that house's mailbox. "123" can mean the house (location), the person known by it
(identity), or what's in the box (content or concept). Mixing these up is the bug.
Telling them apart is the skill. Using one as the other on purpose (pointer
arithmetic, indirection) is the power.

## Why it unlocked compilers and self-modifying code

- Programs are data, so **a program can write another program**. This makes
  assemblers, compilers, loaders and interpreters possible.
- Early machines changed their own instructions' address fields to step through
  arrays, before index registers existed. This is **self-modifying code**.
- The flip side is a security hazard. Treating data as code is the root of
  code-injection attacks. That is why modern systems mark memory pages
  non-executable and why SCBE keeps its decision logs read-only and hash-chained.

## Issac's synthesis: Data = Concept + Identity + Location + Methods

> Everything is numbers, grabbed by location, treated as identity or concept, and changed by a small set of methods.

| Part | Machine meaning | Market / ledger meaning |
|---|---|---|
| **Location** | Memory address | Venue + account + symbol |
| **Identity** | Which object this is | Client order ID / trade ID (the golden thread) |
| **Concept** | What the bits mean | Position, price, fill, balance |
| **Methods** | Small instruction set | place / cancel / get balance / get fills |

There is no separate hardware type for instructions versus data. In the same way,
there is no separate "kind" of money between a bank ledger, an exchange book and a
blockchain. They are all numbers at locations, with identities, changed by a small set
of methods. This is the root of the quote in the README and of the adapter interface
in 06.
