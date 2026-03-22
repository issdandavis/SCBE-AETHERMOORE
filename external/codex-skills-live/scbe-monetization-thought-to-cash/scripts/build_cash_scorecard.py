#!/usr/bin/env python3
"""
Build a daily cash scorecard markdown node for Obsidian.

Usage:
  python scripts/build_cash_scorecard.py --cash-today 249.50 --orders 3 --top-offer "SCBE Governance Toolkit"
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_VAULT_ROOT = Path.home() / "OneDrive" / "Documents" / "DOCCUMENTS" / "A follder"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def build_note(
    *,
    run_id: str,
    cash_today: float,
    orders: int,
    new_customers: int,
    top_offer: str,
    blocker: str,
    next_action: str,
) -> str:
    ts = utc_now().isoformat()
    return (
        f"---\n"
        f"node_id: cash-scorecard-{run_id}\n"
        f"created_at: {ts}\n"
        f"tags: [cash, monetization, execution]\n"
        f"---\n\n"
        f"# Cash Scorecard {run_id}\n\n"
        f"- cash_today_usd: {cash_today:.2f}\n"
        f"- orders: {orders}\n"
        f"- new_customers: {new_customers}\n"
        f"- top_offer: {top_offer}\n"
        f"- blocker: {blocker}\n"
        f"- next_24h_action: {next_action}\n"
    )


def append_index(index_path: Path, run_id: str, note_rel: str, cash_today: float, orders: int) -> None:
    if not index_path.exists():
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text("# Cash Index\n\n", encoding="utf-8")

    line = f"- [[{note_rel}|{run_id}]] | cash=${cash_today:.2f} | orders={orders}\n"
    with index_path.open("a", encoding="utf-8") as handle:
        handle.write(line)


def main() -> int:
    parser = argparse.ArgumentParser(description="Write daily cash scorecard node to Obsidian.")
    parser.add_argument("--cash-today", type=float, required=True)
    parser.add_argument("--orders", type=int, default=0)
    parser.add_argument("--new-customers", type=int, default=0)
    parser.add_argument("--top-offer", default="(unset)")
    parser.add_argument("--blocker", default="(none)")
    parser.add_argument("--next-action", default="Ship one direct revenue action now.")
    parser.add_argument("--vault-root", default=str(DEFAULT_VAULT_ROOT))
    args = parser.parse_args()

    run_id = utc_now().strftime("%Y%m%dT%H%M%SZ")
    vault_root = Path(args.vault_root).resolve()
    workspace = vault_root / "AI Workspace"
    day_key = run_id[:8]

    node_dir = workspace / "Nodal Network" / day_key
    node_dir.mkdir(parents=True, exist_ok=True)
    note_path = node_dir / f"cash-scorecard-{run_id}.md"

    note = build_note(
        run_id=run_id,
        cash_today=float(args.cash_today),
        orders=int(args.orders),
        new_customers=int(args.new_customers),
        top_offer=str(args.top_offer),
        blocker=str(args.blocker),
        next_action=str(args.next_action),
    )
    note_path.write_text(note, encoding="utf-8")

    index_path = workspace / "Nodal Network" / "Cash Index.md"
    note_rel = f"Nodal Network/{day_key}/cash-scorecard-{run_id}"
    append_index(index_path, run_id, note_rel, float(args.cash_today), int(args.orders))

    print(f"note={note_path}")
    print(f"index={index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
