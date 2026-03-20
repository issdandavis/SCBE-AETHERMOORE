"""Cash App Monthly Expense Tracker.

Parses Cash App CSV exports and auto-categorizes transactions for Schedule C tax tracking.
Run weekly or monthly to keep your expense ledger up to date.

Usage:
    python scripts/cashapp_expense_tracker.py --csv path/to/cashapp_report.csv
    python scripts/cashapp_expense_tracker.py --csv path/to/cashapp_report.csv --since 2026-01-01
    python scripts/cashapp_expense_tracker.py --csv path/to/cashapp_report.csv --month 2026-03
"""
import argparse
import csv
import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Business expense categories and their Schedule C lines
BUSINESS_VENDORS = {
    # AI Subscriptions (Line 27a)
    "anthropic": ("AI Subscription", "27a"),
    "claude": ("AI Subscription", "27a"),
    "openai": ("AI Subscription", "27a"),
    "chatgpt": ("AI Subscription", "27a"),
    "xai": ("AI Subscription", "27a"),
    "grok": ("AI Subscription", "27a"),
    "perplexity": ("AI Subscription", "27a"),
    "midjourney": ("AI Subscription", "27a"),
    "colab": ("AI Subscription", "27a"),
    # Dev Tools (Line 27a)
    "github": ("Dev Tools", "27a"),
    "copilot": ("Dev Tools", "27a"),
    "replit": ("Dev Tools", "27a"),
    "cursor": ("Dev Tools", "27a"),
    "notion": ("Dev Tools", "27a"),
    "slack": ("Dev Tools", "27a"),
    "zapier": ("Dev Tools", "27a"),
    "canva": ("Dev Tools", "27a"),
    "figma": ("Dev Tools", "27a"),
    "adobe": ("Dev Tools", "27a"),
    "docker": ("Dev Tools", "27a"),
    "discord": ("Dev Tools", "27a"),
    "npm": ("Dev Tools", "27a"),
    # Hosting / Cloud (Line 25)
    "vercel": ("Hosting/Cloud", "25"),
    "hetzner": ("Hosting/Cloud", "25"),
    "digitalocean": ("Hosting/Cloud", "25"),
    "cloudflare": ("Hosting/Cloud", "25"),
    "netlify": ("Hosting/Cloud", "25"),
    "heroku": ("Hosting/Cloud", "25"),
    "railway": ("Hosting/Cloud", "25"),
    "render": ("Hosting/Cloud", "25"),
    "supabase": ("Hosting/Cloud", "25"),
    "firebase": ("Hosting/Cloud", "25"),
    # Cloud Storage (Line 27a)
    "google one": ("Cloud Storage", "27a"),
    "google storage": ("Cloud Storage", "27a"),
    # Business Services (Line 27a)
    "shopify": ("Business Services", "27a"),
    "stripe": ("Business Services", "27a"),
    "gumroad": ("Business Services", "27a"),
    "paypal *shopify": ("Business Services", "27a"),
    # Legal / IP (Line 17)
    "patent": ("Legal/IP", "17"),
    "uspto": ("Legal/IP", "17"),
    # AI/ML Tools (Line 27a)
    "huggingface": ("AI/ML Tools", "27a"),
    "hugging": ("AI/ML Tools", "27a"),
    "kaggle": ("AI/ML Tools", "27a"),
}


def classify_transaction(notes, name):
    """Classify a transaction as business or personal."""
    combined = (notes + " " + name).lower()
    for keyword, (category, line) in BUSINESS_VENDORS.items():
        if keyword in combined:
            return category, line, keyword
    return None, None, None


def parse_cashapp_csv(csv_path, since=None, month=None):
    """Parse Cash App CSV and return categorized transactions."""
    transactions = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_str = row.get("Date", "")
            if not date_str:
                continue

            # Parse date
            try:
                dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
            except ValueError:
                continue

            # Filter by date range
            if since and dt < since:
                continue
            if month and not date_str.startswith(month):
                continue

            notes = row.get("Notes", "") or ""
            name = row.get("Name of sender/receiver", "") or ""
            amt_str = row.get("Amount", "").replace("$", "").replace(",", "")
            try:
                amount = float(amt_str)
            except (ValueError, TypeError):
                continue

            category, sched_c_line, matched_keyword = classify_transaction(notes, name)

            transactions.append({
                "date": date_str[:10],
                "amount": amount,
                "notes": notes.strip()[:60],
                "name": name.strip(),
                "category": category,
                "schedule_c_line": sched_c_line,
                "matched_keyword": matched_keyword,
                "is_business": category is not None,
                "type": row.get("Transaction Type", ""),
            })

    return transactions


def generate_report(transactions, output_dir, label=""):
    """Generate expense report from transactions."""
    os.makedirs(output_dir, exist_ok=True)

    biz = [t for t in transactions if t["is_business"] and t["amount"] < 0]
    refunds = [t for t in transactions if t["is_business"] and t["amount"] > 0]

    # Category totals
    cat_totals = defaultdict(float)
    vendor_totals = defaultdict(float)
    for t in biz:
        cat_totals[t["category"]] += abs(t["amount"])
        vendor_totals[t["matched_keyword"].upper()] += abs(t["amount"])
    for t in refunds:
        cat_totals[t["category"]] -= abs(t["amount"])

    total_expenses = sum(cat_totals.values())

    # Print report
    print("=" * 60)
    print(f"  CASH APP EXPENSE REPORT {label}")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    print(f"\n  Business transactions: {len(biz)} expenses, {len(refunds)} refunds")
    print(f"  Total deductible:      ${total_expenses:,.2f}")
    print()

    print("  BY CATEGORY:")
    for cat, total in sorted(cat_totals.items(), key=lambda x: -x[1]):
        print(f"    {cat:<25} ${total:>10,.2f}")

    print()
    print("  BY VENDOR:")
    for v, total in sorted(vendor_totals.items(), key=lambda x: -x[1]):
        print(f"    {v:<25} ${total:>10,.2f}")

    print()
    print("  RECENT TRANSACTIONS:")
    for t in sorted(biz, key=lambda x: x["date"], reverse=True)[:15]:
        print(f"    {t['date']}  ${abs(t['amount']):>8,.2f}  {t['notes'][:40]}")

    # Save CSV
    csv_path = os.path.join(output_dir, f"expense_tracker_{label or 'latest'}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "date", "amount", "notes", "category", "schedule_c_line", "type"
        ])
        writer.writeheader()
        for t in sorted(biz + refunds, key=lambda x: x["date"]):
            writer.writerow({
                "date": t["date"],
                "amount": abs(t["amount"]) if t["amount"] < 0 else -abs(t["amount"]),
                "notes": t["notes"],
                "category": t["category"],
                "schedule_c_line": t["schedule_c_line"],
                "type": "Expense" if t["amount"] < 0 else "Refund",
            })

    # Save JSON summary
    summary = {
        "generated": datetime.now().isoformat(),
        "label": label,
        "total_transactions": len(transactions),
        "business_expenses": len(biz),
        "business_refunds": len(refunds),
        "total_deductible": round(total_expenses, 2),
        "by_category": {k: round(v, 2) for k, v in sorted(cat_totals.items(), key=lambda x: -x[1])},
        "by_vendor": {k: round(v, 2) for k, v in sorted(vendor_totals.items(), key=lambda x: -x[1])},
    }
    json_path = os.path.join(output_dir, f"expense_summary_{label or 'latest'}.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print(f"\n  Saved: {csv_path}")
    print(f"  Saved: {json_path}")
    print("=" * 60)

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Cash App Monthly Expense Tracker for Schedule C"
    )
    parser.add_argument("--csv", required=True, help="Path to Cash App CSV export")
    parser.add_argument("--since", help="Only include transactions after this date (YYYY-MM-DD)")
    parser.add_argument("--month", help="Only include transactions from this month (YYYY-MM)")
    parser.add_argument("--output", default="artifacts/tax/monthly", help="Output directory")

    args = parser.parse_args()

    since = datetime.strptime(args.since, "%Y-%m-%d") if args.since else None
    label = args.month or (args.since or "all")

    transactions = parse_cashapp_csv(args.csv, since=since, month=args.month)
    generate_report(transactions, args.output, label=label)


if __name__ == "__main__":
    main()
