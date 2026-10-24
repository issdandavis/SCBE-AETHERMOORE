# 15 — Low-Budget Test Plan (zero dollars)

## Venues
- **Coinbase sandbox**: sandbox order-entry environment (session: "real order book,
  fake dollars." ⚠ Verify current sandbox behavior. Coinbase's Advanced Trade/Exchange
  sandbox data may be synthetic.)
- **Binance Spot Testnet** (testnet.binance.vision): free test funds and its own
  test matching engine.
- Run **both at once** to get a **two-venue reconciliation surface** at no cost.
- Kraken has a demo/paper option, but its API is thinner and fussier, so it's
  deprioritized.

## Why Coinbase + Binance
- Enough liquidity, or simulated liquidity, for realistic fills.
- **Different architectures**, which exercise dedupe and the golden thread (07–08) in
  real conditions.

## Watch-outs
- Testnet feeds go **stale or thin off-hours**. Log **`feed_ts_ms` next to every
  fill** (the field already exists in `Fill`).
- If slow-instance divergence lines up with a dead feed, that is a **data problem,
  not a system problem**. Exclude it, or label it as such.

## Next concrete step (agreed)
Pick **one market** (e.g. BTC-USD / BTCUSDT) and **one venue pair** (Coinbase sandbox +
Binance testnet). Run the **two-speed diff** (12) over a weekend off from Wendy's.

## Done when
- Both adapters (06) pass `place / cancel / get_fills / get_position` against testnets.
- A weekend run produces two hash-chained logs and a break report with no
  UNKNOWN_ORDER or PHANTOM_FILL entries that stay unexplained.
