# 09 — The No-Data State

| State | What you know | Sizing |
|---|---|---|
| **Confirmed flat** | Position = 0, from an authoritative report | A known zero, so you can size normally |
| **No data** | Position ∈ {flat, long, short}, unknown | Every decision is a guess |

**Rule: fail closed.** Uncertainty blocks new risk.

**Asymmetry argument (session):**
- Worst case if you *block* during no-data: you **miss a move**. That costs you
  opportunity and is bounded.
- Worst case if you *trade through* no-data: you **double up on a position you didn't
  know about**. That costs real loss, can compound, and can end up at liquidation.

Bounded regret beats unbounded regret, so block.

Implementation: `VenueReport.position = None` → `PositionState.NO_DATA` →
`may_trade() == False` (test: `test_no_data_is_not_flat_and_fails_closed`).

Precept 9 tie-in (01): this is fault tolerance applied to knowledge. Treat silence
as a fault, not as zero.
