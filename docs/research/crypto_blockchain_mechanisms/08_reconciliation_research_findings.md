# 08 — Reconciliation Research Findings

Condensed from the lost `SCBE_Research_Document.md` (666 lines, 48 sections, 12
sources). That document's DOI/arXiv list did not survive. The sources below were
re-checked or are clearly marked.

| Finding | Source / status |
|---|---|
| **Client order ID is the golden thread.** In FIX, `ClOrdID` is **tag 11** and is assigned by the client so it can correlate its own orders. | FIX Protocol standard (fixtrading.org), tag 11 `ClOrdID`, verified as well-known |
| **Hyperliquid partial-fill silence**: some partial fills may not come with the update you expect, so you have to poll fills and not trust order-status streams alone. | ⚠ Session note — verify against Hyperliquid API docs |
| **Dedupe** on venue + coin + time + trade ID. Trade ID is the primary key, and time is a sanity check. | Design consensus from the session; implemented |
| **Scaled integers, not floats**, because 0.1 + 0.2 ≠ 0.3 in IEEE-754. | Standard practice; tested in `test_scaled_integers_avoid_float_drift` |
| **Ethereum finality** is about 2 epochs, roughly **12.8–16 min** (session said ~13–16 min). | ⚠ Session note; consistent with ethereum.org's "Gasper finality ~2 epochs" |
| **Solana Alpenglow**: about **150 ms target**, **202 ms** in a single early dashboard reading. Live on mainnet from epoch 1064 (**Oct 21, 2026**), replacing TowerBFT's ~12.8 s. | **Verified**: [solana.com/upgrades/alpenglow](https://solana.com/upgrades/alpenglow); [FinanceFeeds](https://financefeeds.com/solana-after-alpenglow-202ms-observed-against-a-150ms-target-on-day-one/). Note: another same-day report showed 6.6 s, so 150 ms is a target, not a constant. |
| **NautilusTrader** reconciles against authoritative venue position/order reports at startup and treats unresolved state cautiously. | ⚠ Session note — check nautilustrader.io docs ("execution reconciliation") |
| **Fail closed; no-data ≠ flat** is the most dangerous confusion in the stack. | See 09 |
| **Daily-close discipline**: month-end reconciliation is archaeology. | Session principle |
| **Classify breaks by type** so each type has a playbook. | Implemented in `BreakType` |

**Implication for finality:** a fill isn't final until the chain is. For on-chain
venues, a reconcile should mark fills `pending_finality` until the chain-specific
threshold passes. That threshold went from about 15 min on Ethereum to about 0.2 s on
post-Alpenglow Solana. (Not yet implemented in the stubs — **open item**.)
