# Six Tongues editorial rehearsal

This folder holds review receipts, not accepted manuscript changes. The cycle is deliberately staged:

1. A fresh reader records immediate reactions without seeing a writer proposal.
2. That reader becomes the bounded writer for the same two or three chapters.
3. A different agent becomes continuity keeper and checks the proposal against canon, adjacent chapters, and source hashes.
4. Issac Daniel Davis accepts, rejects, or revises the proposal. No agent promotes prose into the manuscript on its own.

`rehearsal-plan.json` is the executable assignment record. It pins the source hashes, keeps each assignment between two and three chapters, and rotates continuity ownership away from the writer.

Run from the repository root:

```powershell
python scripts/book/editorial_rehearsal.py validate
python scripts/book/editorial_rehearsal.py status
python scripts/book/editorial_rehearsal.py verify
```

`validate` checks the plan and source hashes. `status` reports the furthest valid role reached by each block. `verify` additionally requires all three receipts for every block and verifies each dependency hash.
