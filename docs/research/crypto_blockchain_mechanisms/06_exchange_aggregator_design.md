# 06 — Exchange Aggregator Design

Reconstructed from the session artifacts `exchange_adapter_interfaces.md`,
`SCBE_Exchange_Adapter_Review.md` and `SCBE_Cheat_Sheet.md`, which were lost on the box.

## Thesis (Issac)
This is **not** a way around regulation. It is an **aggregator/middleman apparatus**:
- like **YouTube** (content ↔ viewer) or **Cash App** (market ↔ market),
- a **one-click front end** that ties together each exchange's own auth flows (OAuth,
  API keys, rate limits) so non-technical users never handle any of that,
- with every venue's KYC, custody and compliance staying with that venue.

## Architecture

```
[ UI: portfolio view + single order ticket ]
                 │
        [ Router / fan-out ]────► [ Hashed decision log ] ──► SCBE governance
                 │
   ┌─────────────┼──────────────┐
[Adapter A]  [Adapter B]   [Adapter C]      one module per venue
   │             │              │
 venue API     venue API      venue API
                 ▲
        [ Encrypted auth vault ]  (per-user keys/tokens; never logged)
```

## Canonical adapter interface

Each venue module translates its own quirks into **one canonical format**.

```python
class ExchangeAdapter(Protocol):
    venue: str
    def place_order(self, req: OrderRequest) -> OrderAck: ...   # requires client_order_id
    def cancel_order(self, client_order_id: str) -> CancelAck: ...
    def get_balances(self) -> list[Balance]: ...
    def get_fills(self, since_ms: int) -> list[Fill]: ...        # paginated, idempotent
    def get_position(self, symbol: str) -> Position | None: ...  # None = NO DATA (see 09)
    def rate_limit_state(self) -> RateLimit: ...
```

Canonical types use **scaled integers** for quantity and price (see 08). Every order
carries a client-generated `client_order_id`, which is the golden thread across all
venues.

## Quirks the adapters must absorb (examples)
- Different symbol formats (`BTC-USD` vs `BTCUSDT`).
- Different precision and lot-size rules.
- Partial-fill reporting gaps (see Hyperliquid in 08).
- Different rate-limit models: request weight versus requests per second.
- Testnet versus production base URLs (15).

## Auth vault
- Encrypted at rest, scoped per user and per venue, with least-privilege keys
  (**trade-only, never withdrawal**).
- Secrets never appear in logs. The decision log records *that* a key was used, not
  the key itself.

## Decision log → SCBE
Every routing decision is appended to a hash-chained log (implemented in
`prototype/reconciliation/scbe_reconciliation_stubs.py::DecisionLog`). SCBE can then
audit it later, and the dwell gate (13) can block actions read-only.

## Review notes (from the lost `SCBE_Exchange_Adapter_Review.md`, summarized)
- The biggest risk is not placing orders. It is **knowing what actually happened**
  after you placed them. That is why 07–09 exist.
- Fanning one ticket out to several venues needs per-venue client IDs that come from
  one parent ID, so a partial failure stays traceable.
