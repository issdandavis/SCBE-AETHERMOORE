"""
Stripe sandbox transaction simulator — generates JSONL training pairs.

Runs real Stripe test API calls (no real money) and wraps results as
SFT prompt/response pairs for the commerce LoRA adapter.

Usage:
    python scripts/system/stripe_simulator.py --count 50
    python scripts/system/stripe_simulator.py --count 200 --output training-data/hand_tune/commerce/stripe_haggle.jsonl
    python scripts/system/stripe_simulator.py --dry-run --count 5

Requires:
    STRIPE_SECRET_KEY=rk_test_... in .env or environment
    pip install stripe python-dotenv
"""

import argparse
import json
import os
import random
import sys
from pathlib import Path

# Load .env from repo root
_env_path = Path(__file__).resolve().parents[2] / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            # Use .env value over any stale environment variable
            os.environ[k.strip()] = v.strip()

import stripe  # noqa: E402

STRIPE_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
if not STRIPE_KEY:
    print("ERROR: STRIPE_SECRET_KEY not set.")
    print("Add it to your .env file:  STRIPE_SECRET_KEY=rk_test_...")
    sys.exit(1)

if not STRIPE_KEY.startswith("rk_test_") and not STRIPE_KEY.startswith("sk_test_"):
    print("ERROR: STRIPE_SECRET_KEY looks like a live key. Use a test key (rk_test_... or sk_test_...).")
    sys.exit(1)

stripe.api_key = STRIPE_KEY

# Stripe test PaymentMethod tokens — no real card needed
TEST_PM = {
    "success": "pm_card_visa",
    "decline_generic": "pm_card_visa_chargeDeclined",
    "decline_insufficient": "pm_card_chargeDeclinedInsufficientFunds",
    "decline_expired": "pm_card_chargeDeclinedExpiredCard",
    "auth_required": "pm_card_authenticationRequired",
}

# Realistic product catalog: (name, cost_cents, list_cents)
PRODUCTS = [
    ("Aethermoor Print — 8x10", 350, 1200),
    ("Aethermoor Print — 11x14", 500, 1800),
    ("Spiralverse Zine Vol. 1", 200, 800),
    ("Spiralverse Zine Bundle (3)", 550, 2000),
    ("Sacred Tongue Sticker Sheet", 100, 500),
    ("Character Enamel Pin", 250, 1400),
    ("Canvas Tote — Branded", 600, 2200),
    ("Digital Wallpaper Pack", 50, 400),
    ("Governance Starter Kit PDF", 200, 4900),
    ("Commission Slot — Sketch", 1500, 8000),
]

MIN_PROFIT_CENTS = 300  # $3.00 hard floor


def _charge(amount_cents: int, pm_token: str) -> dict:
    """Hit Stripe test API. Returns outcome dict."""
    try:
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency="usd",
            payment_method=pm_token,
            confirm=True,
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
        )
        return {"ok": True, "id": intent.id, "status": intent.status}
    except stripe.error.CardError as e:
        return {"ok": False, "code": e.code, "message": e.user_message}
    except stripe.error.StripeError as e:
        return {"ok": False, "code": "stripe_error", "message": str(e)}


def _seller_reply(offer_cents: int, floor_cents: int, list_cents: int, charge_result: dict | None) -> str:
    """Build a realistic seller response string."""
    if offer_cents < floor_cents:
        if offer_cents >= floor_cents - 100:  # within $1 of floor
            return (
                f"I appreciate the offer! Closest I can do is ${floor_cents/100:.2f} — "
                f"that's my floor with costs factored in. Deal at that?"
            )
        return (
            f"I can't go below ${floor_cents/100:.2f} on this one — that's our hard floor. "
            f"I'd actually lose money otherwise. Let me know if that works."
        )

    # Offer accepted — attempt charge
    if charge_result and charge_result["ok"]:
        return (
            f"${offer_cents/100:.2f} works! Payment went through — "
            f"confirmation {charge_result['id'][:16]}. I'll get your order ready."
        )
    elif charge_result and not charge_result["ok"]:
        if charge_result["code"] in ("card_declined", "insufficient_funds"):
            return (
                f"The deal is on at ${offer_cents/100:.2f}, but your card was declined "
                f"({charge_result['message']}). Try another card?"
            )
        return (
            f"Deal at ${offer_cents/100:.2f}! Had a payment issue though — "
            f"{charge_result['message']}. Can you retry with a different method?"
        )
    return f"${offer_cents/100:.2f} works for me — deal!"


def simulate_transaction(dry_run: bool = False) -> dict:
    """Simulate one haggle → charge flow. Returns {prompt, response, meta}."""
    name, cost_cents, list_cents = random.choice(PRODUCTS)
    floor_cents = cost_cents + MIN_PROFIT_CENTS

    # Customer opens with offer (50% to 110% of list)
    offer_fraction = random.uniform(0.50, 1.10)
    offer_cents = int(list_cents * offer_fraction)

    prompt = f"I want to buy the {name} (listed at ${list_cents/100:.2f}). Can you do ${offer_cents/100:.2f}?"

    charge_result = None
    if offer_cents >= floor_cents and not dry_run:
        # Pick a payment method — 88% success, 12% various failures
        roll = random.random()
        if roll < 0.88:
            pm = TEST_PM["success"]
        elif roll < 0.93:
            pm = TEST_PM["decline_insufficient"]
        elif roll < 0.96:
            pm = TEST_PM["decline_generic"]
        else:
            pm = TEST_PM["decline_expired"]
        charge_result = _charge(offer_cents, pm)
    elif offer_cents >= floor_cents and dry_run:
        charge_result = {"ok": True, "id": "pi_DRY_RUN_SIMULATED_000", "status": "succeeded"}

    response = _seller_reply(offer_cents, floor_cents, list_cents, charge_result)

    return {
        "prompt": prompt,
        "response": response,
        "_meta": {
            "product": name,
            "cost_cents": cost_cents,
            "list_cents": list_cents,
            "floor_cents": floor_cents,
            "offer_cents": offer_cents,
            "accepted": offer_cents >= floor_cents,
            "charge": charge_result,
        },
    }


def run(count: int, output: str, dry_run: bool, verbose: bool) -> None:
    print(f"Stripe simulator — {'DRY RUN' if dry_run else 'LIVE TEST API'} — generating {count} pairs")
    print(f"Output: {output}\n")

    results = []
    accepted = declined = card_errors = 0

    for i in range(count):
        r = simulate_transaction(dry_run=dry_run)
        results.append(r)
        m = r["_meta"]
        if not m["accepted"]:
            declined += 1
        elif m["charge"] and not m["charge"]["ok"]:
            card_errors += 1
        else:
            accepted += 1

        if verbose:
            status = "ACCEPT" if m["accepted"] else "FLOOR"
            print(f"  [{i+1:3d}] {status:6s}  offer=${m['offer_cents']/100:.2f}  floor=${m['floor_cents']/100:.2f}  {m['product']}")

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w") as f:
        for r in results:
            f.write(json.dumps({"prompt": r["prompt"], "response": r["response"]}) + "\n")

    print(f"\nDone. {count} pairs written to {output}")
    print(f"  Accepted (charged):  {accepted}")
    print(f"  Floor holds:         {declined}")
    print(f"  Card errors:         {card_errors}")
    if not dry_run:
        print(f"\nAll charges were on Stripe TEST API — no real money moved.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Stripe sandbox haggle simulator")
    parser.add_argument("--count", type=int, default=50, help="Number of transactions to simulate")
    parser.add_argument(
        "--output",
        default="training-data/hand_tune/commerce/stripe_haggle.jsonl",
        help="Output JSONL path",
    )
    parser.add_argument("--dry-run", action="store_true", help="Skip real Stripe calls")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print each transaction")
    args = parser.parse_args()
    run(args.count, args.output, args.dry_run, args.verbose)


if __name__ == "__main__":
    main()
