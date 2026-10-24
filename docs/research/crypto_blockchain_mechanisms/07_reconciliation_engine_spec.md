# 07 — Reconciliation Engine Spec

Reconstructed from the session artifact `scbe_reconciliation_module.md`. The code is at
`prototype/reconciliation/scbe_reconciliation_stubs.py`, with 9 tests in
`tests/research/test_scbe_reconciliation_stubs.py`. **All 9 tests pass** (2026-10-24).

## Sync vs reconcile
- **Sync** is a continuous stream: apply fills and order updates as they arrive.
- **Reconcile** is periodic: compare our ledger against the venue's **authoritative**
  report and classify the differences ("breaks").

Sync keeps you fast. Reconcile keeps you honest. Never use one as a stand-in for the
other.

## Data model
- `Fill(venue, symbol, trade_id, client_order_id, qty, price, ts_ms, feed_ts_ms)`.
  qty and price are scaled integers at 1e-8.
- Dedupe key: `(venue, symbol, trade_id)`. Recording a fill is idempotent.
- `VenueReport(position=None)` means **NO_DATA**, which is different from `position=0`
  (confirmed flat).

## Break taxonomy
| Break | Meaning | Default action |
|---|---|---|
| MISSING_FILL | Venue has a fill we don't | Ingest, re-check position |
| PHANTOM_FILL | We have a fill the venue doesn't | Freeze the symbol, investigate |
| QTY_MISMATCH / PRICE_MISMATCH | Same trade, different numbers | Venue wins, log the correction |
| POSITION_MISMATCH | Totals disagree | Block new risk until resolved |
| UNKNOWN_ORDER | Client ID we never issued | Security alert (possible key misuse) |
| NO_DATA | Venue silent | **Fail closed** (09) |

## Gate
`may_trade(report, breaks)` returns True only if the position state is KNOWN **and**
no breaks remain open.

## Discipline
- Run a **daily close** reconcile. Leaving it to month-end turns the job into
  archaeology.
- Every reconcile writes to the hash-chained `DecisionLog`.
