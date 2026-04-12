"""
Generate SCBE-format SFT training data for the commerce LoRA adapter.

Converts plain prompt/response pairs into the full SCBE curriculum format:
  - messages[] with tongue-weight system header
  - tongue_weights (KO/AV/RU/CA/UM/DR mapped to commerce semantics)
  - dominant_tongue, layers, axioms, difficulty
  - English explanation variants alongside code variants
  - Governance-aware: $3 profit floor tagged as RU (Runethic/policy-binding)

Output files:
  training-data/hand_tune/commerce/commerce_sft_scbe.jsonl   <- SCBE rich format
  training-data/hand_tune/commerce/commerce_sft_plain.jsonl  <- plain English pairs

Usage:
    python scripts/system/generate_commerce_sft.py
    python scripts/system/generate_commerce_sft.py --merge-stripe  (if stripe_haggle.jsonl exists)
"""

import argparse
import hashlib
import json
import math
import os
import random
from pathlib import Path

# ---------------------------------------------------------------------------
# Tongue weight assignments for commerce domain
# ---------------------------------------------------------------------------
#
# KO (Kor'aelin)  — nonce/flow/intent     — negotiation flow, conversation intent
# AV (Avali)      — context/I/O           — customer/seller context, UI, product listings
# RU (Runethic)   — binding/policy        — profit floor enforcement, ToS, legal constraints
# CA (Cassisivadan)— compute/ciphertext   — transaction processing, cryptographic signatures
# UM (Umbroth)    — security/redaction    — API key safety, webhook validation, headers
# DR (Draumric)   — auth/schema           — Stripe/Square auth, schema definitions, webhooks
#
# Each example gets weights based on what it primarily teaches.

TONGUE_PROFILES = {
    "negotiation": {"KO": 0.45, "AV": 0.25, "RU": 0.20, "CA": 0.05, "UM": 0.02, "DR": 0.03},
    "payment_code": {"KO": 0.05, "AV": 0.20, "RU": 0.10, "CA": 0.45, "UM": 0.10, "DR": 0.10},
    "checkout_ui":  {"KO": 0.10, "AV": 0.40, "RU": 0.10, "CA": 0.20, "UM": 0.10, "DR": 0.10},
    "security":     {"KO": 0.02, "AV": 0.08, "RU": 0.15, "CA": 0.10, "UM": 0.55, "DR": 0.10},
    "webhook_auth": {"KO": 0.03, "AV": 0.10, "RU": 0.10, "CA": 0.15, "UM": 0.20, "DR": 0.42},
    "legal_policy": {"KO": 0.05, "AV": 0.15, "RU": 0.65, "CA": 0.02, "UM": 0.08, "DR": 0.05},
    "training_gen": {"KO": 0.30, "AV": 0.15, "RU": 0.25, "CA": 0.20, "UM": 0.05, "DR": 0.05},
    "react_ui":     {"KO": 0.10, "AV": 0.50, "RU": 0.10, "CA": 0.10, "UM": 0.10, "DR": 0.10},
    "stripe_test":  {"KO": 0.05, "AV": 0.15, "RU": 0.15, "CA": 0.30, "UM": 0.15, "DR": 0.20},
    "discount_floor": {"KO": 0.15, "AV": 0.10, "RU": 0.45, "CA": 0.20, "UM": 0.05, "DR": 0.05},
    "haggle_stripe":  {"KO": 0.35, "AV": 0.15, "RU": 0.25, "CA": 0.15, "UM": 0.05, "DR": 0.05},
}

# Layer assignments — which SCBE layers are activated by each topic
LAYER_MAP = {
    "negotiation":   [1, 3, 11, 12, 13],   # intent (L1), weighting (L3), temporal (L11), wall (L12), decision (L13)
    "payment_code":  [1, 2, 3, 4, 8],      # context ingestion → compute realm
    "checkout_ui":   [1, 2, 3, 6],          # surface-level, breathing transform
    "security":      [1, 5, 8, 12, 13],    # distance (L5), hamiltonian (L8), wall (L12), gate (L13)
    "webhook_auth":  [1, 3, 7, 12, 13, 14],# mobius phase (L7), audio telemetry (L14)
    "legal_policy":  [1, 3, 11, 12, 13],   # policy = temporal + wall + gate
    "training_gen":  [1, 2, 3, 9, 10],     # spectral + spin coherence for data generation
    "react_ui":      [1, 2, 3, 6],
    "stripe_test":   [1, 3, 8, 12, 13],
    "discount_floor":[1, 3, 11, 12, 13],   # floor = wall enforcement
    "haggle_stripe": [1, 3, 11, 12, 13],
}

AXIOM_MAP = {
    "negotiation":   ["causality", "composition"],   # time-ordered negotiation, composed outcome
    "payment_code":  ["unitarity", "composition"],   # norm-preserving state, pipeline integrity
    "checkout_ui":   ["composition"],
    "security":      ["locality", "symmetry", "unitarity"],  # spatial bounds, gauge, norm
    "webhook_auth":  ["unitarity", "symmetry"],
    "legal_policy":  ["causality", "locality"],      # time-ordered policy, spatial scope
    "training_gen":  ["composition", "causality"],
    "react_ui":      ["composition"],
    "stripe_test":   ["unitarity", "composition"],
    "discount_floor":["causality", "locality"],      # floor = local bound + causal enforcement
    "haggle_stripe": ["causality", "composition"],
}

VERSION = "3.3.0"
SOURCE = "scbe_aethermoore"
AUTHOR = "Issac Davis"


# ---------------------------------------------------------------------------
# Raw examples — (profile_key, prompt, code_response, english_explanation)
# ---------------------------------------------------------------------------
# english_explanation: plain-language description a non-coder can understand

EXAMPLES = [
    (
        "payment_code",
        "How do I process a Square payment in Python?",
        """```python
import uuid, os
from square.client import Client

client = Client(access_token=os.environ['SQUARE_ACCESS_TOKEN'], environment='sandbox')

def charge_card(amount_cents: int, source_id: str, note: str = '') -> dict:
    result = client.payments.create_payment({
        'source_id': source_id,
        'idempotency_key': str(uuid.uuid4()),
        'amount_money': {'amount': amount_cents, 'currency': 'USD'},
        'note': note
    })
    if result.is_success():
        return {'success': True, 'payment_id': result.body['payment']['id']}
    return {'success': False, 'errors': result.errors}
```
Always use `idempotency_key` so retries don't double-charge. Store the payment_id for refunds.""",
        """To charge a card through Square, you call their API with the card token (source_id) and the dollar amount in cents ($1.00 = 100 cents). You also include a random idempotency key — this is like a ticket number that Square uses to recognize duplicate requests, so if your internet cuts out and you retry, the customer only gets charged once. If the charge works, you get back a payment ID to keep on file in case you ever need to issue a refund."""
    ),
    (
        "negotiation",
        "What is a good price negotiation flow for a web store with a $3 minimum profit floor?",
        """1. **Show list price** — display full retail
2. **Accept** if offer >= (cost + $3), accept immediately
3. **Counter** if below floor — offer (cost + $4), explain value
4. **Final offer** — counter at (cost + $3), mark 'best price'
5. **Hard no** — decline gracefully: 'That price doesn't work for us'

```python
def evaluate_offer(offer: float, cost: float, min_profit: float = 3.0) -> dict:
    floor = cost + min_profit
    if offer >= floor:
        return {'decision': 'accept', 'price': offer}
    elif offer >= floor - 1.0:
        return {'decision': 'counter', 'price': floor, 'message': 'Best we can do'}
    else:
        return {'decision': 'decline', 'price': floor, 'message': f'Lowest is ${floor:.2f}'}
```
The floor is hard — never go below cost + $3.""",
        """When a customer tries to haggle, you follow a simple five-step dance: first you show them the full price, then if their offer covers your costs plus at least $3 in profit you just say yes. If they're close to the floor but not quite there, you meet them halfway at exactly your floor price. If they're way below, you politely decline and tell them your lowest possible price. The $3 floor is a hard rule — it's not a guideline, it's a line you never cross, because selling below it means you're actually losing money once you factor in your costs."""
    ),
    (
        "checkout_ui",
        "How do I build a checkout page with Square Web Payments SDK?",
        """```html
<!DOCTYPE html>
<html>
<head>
    <script src="https://sandbox.web.squarecdn.com/v1/square.js"></script>
</head>
<body>
    <div id="card-container"></div>
    <button id="pay-btn">Pay Now</button>
    <script>
        const payments = Square.payments('YOUR_APP_ID', 'YOUR_LOCATION_ID');
        async function initCard() {
            const card = await payments.card();
            await card.attach('#card-container');
            document.getElementById('pay-btn').onclick = async () => {
                const result = await card.tokenize();
                if (result.status === 'OK') {
                    await fetch('/checkout', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({source_id: result.token, amount: 1000})
                    });
                }
            };
        }
        initCard();
    </script>
</body>
</html>
```
The card number never touches your server — Square converts it to a single-use token that expires in 24 hours.""",
        """The Square Web Payments SDK builds the card entry form for you — you don't handle raw card numbers at all. When a customer types their card info, Square's servers convert it to a short token (like a temporary code), and that token is what gets sent to your server. Your server then forwards the token to Square's API to complete the charge. This design means your server never sees actual card data, which keeps you out of the most serious PCI compliance requirements and protects your customers if your server is ever compromised."""
    ),
    (
        "security",
        "What security headers should every web app have?",
        """```python
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeaders(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; script-src 'self' https://sandbox.web.squarecdn.com;"
        )
        return response
```
Also: HTTPS only, cookies with `Secure; HttpOnly; SameSite=Strict`, rate-limit auth endpoints.""",
        """Security headers are instructions you attach to every page your server sends out. They tell the visitor's browser how to behave in ways that protect against common attacks. For example, one header stops your site from being embedded inside another website (which bad actors use for 'clickjacking' attacks). Another forces browsers to only communicate with your server over encrypted HTTPS connections. Content Security Policy tells the browser which scripts are allowed to run, blocking injected malicious code. Setting these up takes about ten lines of code and protects against entire categories of attacks automatically."""
    ),
    (
        "training_gen",
        "How do I simulate a customer haggling to generate training data?",
        """```python
import random

def simulate_haggle(list_price: float, cost: float, min_profit: float = 3.0) -> list[dict]:
    floor = cost + min_profit
    pairs = []
    offer = round(list_price * random.uniform(0.5, 0.85), 2)
    pairs.append({'prompt': f'Can you do ${offer:.2f}?', 'response': _seller_response(offer, list_price, floor)})
    if offer < floor:
        offer2 = round(min(list_price, offer * random.uniform(1.05, 1.2)), 2)
        pairs.append({'prompt': f'Okay, what about ${offer2:.2f}?', 'response': _seller_response(offer2, list_price, floor)})
    return pairs

def _seller_response(offer, list_price, floor):
    if offer >= list_price: return 'Absolutely, that works. Let me get that ready.'
    elif offer >= floor: return f'${offer:.2f} works for me. Deal.'
    elif offer >= floor - 0.50: return f'Closest I can go is ${floor:.2f} — just enough to cover costs.'
    else: return f'I appreciate the offer but I can\\'t go below ${floor:.2f}.'
```
Run this 1000 times across different price points to build a haggling dataset.""",
        """This script plays out a price negotiation as if a real customer and seller were talking, then saves the conversation as training examples for your AI. You tell it the sticker price and your cost, and it randomly generates a customer offer. The seller's reply is determined by whether the offer covers your costs plus $3 profit. If not, the seller holds firm or gently declines. Running this thousands of times across different products gives you a rich dataset of realistic negotiations where the AI always learns the same lesson: the profit floor is non-negotiable."""
    ),
    (
        "react_ui",
        "How do I build a product listing page in React with a buy button and haggle input?",
        """```jsx
import { useState } from 'react';

function ProductCard({ name, price, cost, onBuy }) {
    const [offer, setOffer] = useState('');
    const [message, setMessage] = useState('');
    const floor = cost + 3.0;

    const handleOffer = () => {
        const o = parseFloat(offer);
        if (isNaN(o)) return;
        if (o >= price) { setMessage('Deal!'); onBuy(price); }
        else if (o >= floor) { setMessage(`Deal at $${o.toFixed(2)}!`); onBuy(o); }
        else { setMessage(`Can't go below $${floor.toFixed(2)}.`); }
    };

    return (
        <div className="product-card">
            <h2>{name}</h2>
            <p>List price: <strong>${price.toFixed(2)}</strong></p>
            <button onClick={() => onBuy(price)}>Buy at ${price.toFixed(2)}</button>
            <input type="number" placeholder="Make an offer" value={offer} onChange={e => setOffer(e.target.value)} />
            <button onClick={handleOffer}>Submit Offer</button>
            {message && <p>{message}</p>}
        </div>
    );
}
```""",
        """This React component shows a product with two ways to buy it: a straightforward 'buy now' button at full price, or a custom offer input where the customer can try to negotiate. When they submit an offer, the code checks it against the profit floor ($3 above cost). If the offer is acceptable, the sale goes through at that price. If not, the buyer sees a message telling them the lowest possible price. The component handles all the negotiation logic in the browser itself — no server round-trip needed — making it fast and responsive for the customer."""
    ),
    (
        "webhook_auth",
        "How do I handle a Square webhook for payment completion?",
        """```python
import hashlib, hmac, os
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()
WEBHOOK_SECRET = os.environ['SQUARE_WEBHOOK_SIGNATURE_KEY']

def verify_square_signature(body: bytes, signature: str, url: str) -> bool:
    combined = url.encode() + body
    expected = hmac.new(WEBHOOK_SECRET.encode(), combined, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)

@app.post('/webhooks/square')
async def square_webhook(request: Request):
    body = await request.body()
    sig = request.headers.get('x-square-hmacsha256-signature', '')
    if not verify_square_signature(body, sig, str(request.url)):
        raise HTTPException(status_code=403, detail='Invalid signature')
    event = await request.json()
    if event.get('type') == 'payment.completed':
        payment = event['data']['object']['payment']
        await fulfill_order(payment['order_id'], payment['id'])
    return {'received': True}
```
Always verify the signature before processing. Never trust the payload alone.""",
        """A webhook is a notification Square sends to your server the moment a payment goes through. The problem is anyone could fake that notification — a bad actor could send your server a fake 'payment completed' message and trick you into shipping a product that was never actually paid for. The signature check prevents this: Square attaches a special code to every notification that's calculated using a secret key only you and Square know. Your server recalculates that code from the message and checks it matches. If it doesn't match, you reject the notification entirely."""
    ),
    (
        "payment_code",
        "How do I charge a card with the Stripe Python SDK?",
        """```python
import stripe, os
stripe.api_key = os.environ['STRIPE_SECRET_KEY']

def charge_card(amount_cents: int, payment_method_id: str, description: str = '') -> dict:
    try:
        intent = stripe.PaymentIntent.create(
            amount=amount_cents, currency='usd',
            payment_method=payment_method_id, confirm=True,
            description=description,
            automatic_payment_methods={'enabled': True, 'allow_redirects': 'never'},
        )
        return {'success': True, 'payment_intent_id': intent.id, 'status': intent.status}
    except stripe.error.CardError as e:
        return {'success': False, 'error': e.user_message, 'code': e.code}
    except stripe.error.StripeError as e:
        return {'success': False, 'error': str(e)}
```
Use `rk_test_...` keys in sandbox — no real money moves. Store the key in `.env`, never in code.""",
        """To charge a card through Stripe, you create a PaymentIntent — think of it as an instruction to Stripe saying 'charge this card this much money.' You set the amount in cents (so $15 = 1500), attach the customer's card token, and confirm it all in one call. Stripe handles the actual card network communication. If the card works you get back a confirmation ID. If the card is declined, Stripe gives you a plain-English reason you can show the customer. The test API key (starts with rk_test_) lets you run all of this without real money during development."""
    ),
    (
        "checkout_ui",
        "How do I build a Stripe Checkout Session for a one-time purchase?",
        """```python
import stripe, os
stripe.api_key = os.environ['STRIPE_SECRET_KEY']

def create_checkout_session(price_cents: int, product_name: str, success_url: str, cancel_url: str) -> str:
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{'price_data': {'currency': 'usd', 'product_data': {'name': product_name},
                     'unit_amount': price_cents}, 'quantity': 1}],
        mode='payment',
        success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=cancel_url,
    )
    return session.url

url = create_checkout_session(1500, 'Aethermoor Print', 'https://yoursite.com/success', 'https://yoursite.com/cancel')
```
Checkout Sessions handle the entire payment UI. Verify the webhook after payment — don't trust the success URL alone.""",
        """Stripe Checkout is a pre-built payment page that Stripe hosts for you. Instead of building a card form yourself, you create a Checkout Session on your server (telling it what the product is and how much it costs), and Stripe gives you back a URL. You redirect your customer to that URL, they enter their card details on Stripe's secure page, and then Stripe redirects them back to your site when done. Because it's Stripe's page, you never handle card data at all. Always verify the payment through a webhook though — the success page redirect can be faked, but a webhook with a valid signature cannot."""
    ),
    (
        "webhook_auth",
        "How do I verify a Stripe webhook signature in Python?",
        """```python
import stripe, os
from fastapi import FastAPI, Request, HTTPException

app = FastAPI()
stripe.api_key = os.environ['STRIPE_SECRET_KEY']
WEBHOOK_SECRET = os.environ['STRIPE_WEBHOOK_SECRET']  # whsec_...

@app.post('/webhooks/stripe')
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, WEBHOOK_SECRET)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail='Invalid signature')
    if event['type'] == 'payment_intent.succeeded':
        pi = event['data']['object']
        await fulfill_order(pi['id'])
    return {'status': 'ok'}
```
Test locally with `stripe listen --forward-to localhost:8000/webhooks/stripe`. The `whsec_` secret is separate from your API key.""",
        """Stripe's webhook verification works similarly to Square's — Stripe attaches a signature to every notification it sends you, and you verify it before acting on the message. The `stripe.Webhook.construct_event()` call does all the cryptographic checking for you; if the signature is wrong it raises an error and you return a 400 response (which tells Stripe to retry later). You need two different secrets: your API key for making Stripe API calls, and a separate webhook secret (starts with `whsec_`) specifically for verifying incoming notifications. During development, the Stripe CLI can forward real webhook events to your local machine so you can test without deploying."""
    ),
    (
        "discount_floor",
        "How do I apply a discount to a Stripe transaction while maintaining our $3 profit floor?",
        """```python
import stripe, os
stripe.api_key = os.environ['STRIPE_SECRET_KEY']

def create_discounted_session(list_price_cents, cost_cents, discount_pct, product_name, success_url, cancel_url):
    floor_cents = cost_cents + 300
    discounted = int(list_price_cents * (1 - discount_pct / 100))
    if discounted < floor_cents:
        max_pct = int((1 - floor_cents / list_price_cents) * 100)
        return {'error': True, 'message': f'Max safe discount is {max_pct}%. Floor is ${floor_cents/100:.2f}.'}
    coupon = stripe.Coupon.create(percent_off=discount_pct, duration='once')
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{'price_data': {'currency': 'usd', 'product_data': {'name': product_name},
                     'unit_amount': list_price_cents}, 'quantity': 1}],
        discounts=[{'coupon': coupon.id}],
        mode='payment', success_url=success_url, cancel_url=cancel_url,
    )
    return {'error': False, 'url': session.url, 'final_price_cents': discounted}
```
Never skip the floor check — Stripe will happily charge $0.01 if you tell it to.""",
        """When you run a discount, your code has to check the math before Stripe ever gets involved. Here's why: Stripe doesn't know anything about your costs or profit requirements — it just charges whatever price you tell it to. So if you blindly apply a 70% discount on a $10 item that cost you $8, you'd charge the customer $3 but actually lose $5 on the sale. The floor check calculates the lowest safe price ($3 above your cost), compares it to the discounted price, and blocks the checkout session from being created if the discount goes too deep. It also tells you the maximum discount percentage that's actually safe, so you can show that to the customer or adjust your promotion accordingly."""
    ),
    (
        "stripe_test",
        "How do I use Stripe test card numbers in the sandbox?",
        """Stripe provides test card numbers that simulate different outcomes:

```
4242 4242 4242 4242  — Always succeeds
4000 0000 0000 9995  — Always declines (insufficient funds)
4000 0025 0000 3155  — Requires 3D Secure authentication
4000 0000 0000 0069  — Expired card
```

In code, use PaymentMethod tokens directly:
```python
TEST_CARDS = {
    'success': 'pm_card_visa',
    'decline': 'pm_card_visa_chargeDeclined',
    'insufficient': 'pm_card_chargeDeclinedInsufficientFunds',
}
stripe.PaymentIntent.create(
    amount=1000, currency='usd',
    payment_method=TEST_CARDS['success'], confirm=True,
    automatic_payment_methods={'enabled': True, 'allow_redirects': 'never'},
)
```
Switch to `rk_test_...` key and all charges are simulated with no real money.""",
        """Stripe gives you fake card numbers for testing so you can make sure your payment system handles every scenario correctly before going live. The magic number 4242 4242 4242 4242 always succeeds — use it to test the happy path. Other numbers simulate failures: one acts like the customer's card has no funds, another triggers a 3D Secure challenge (where the bank texts a code to verify identity), and another simulates an expired card. In code you can skip even the fake card numbers entirely and use named payment method tokens like `pm_card_visa` — Stripe swaps in the test behavior automatically. None of these test charges cost real money or show up on anyone's statement."""
    ),
    (
        "haggle_stripe",
        "How do I generate Stripe transaction training data for a haggling commerce AI?",
        """```python
import stripe, random, json, os
stripe.api_key = os.environ['STRIPE_SECRET_KEY']  # rk_test_...

def simulate_haggle_transaction(cost_cents, list_cents):
    floor_cents = cost_cents + 300
    offer_cents = int(list_cents * random.uniform(0.5, 1.1))
    if offer_cents < floor_cents:
        return {
            'prompt': f'Customer offers ${offer_cents/100:.2f} on a ${list_cents/100:.2f} item.',
            'response': f'Sorry, we can\\'t go below ${floor_cents/100:.2f}. That covers our costs plus minimum margin.',
            'outcome': 'declined',
        }
    try:
        pm = 'pm_card_visa' if random.random() > 0.1 else 'pm_card_visa_chargeDeclined'
        intent = stripe.PaymentIntent.create(
            amount=offer_cents, currency='usd', payment_method=pm, confirm=True,
            automatic_payment_methods={'enabled': True, 'allow_redirects': 'never'},
        )
        response = f'Deal at ${offer_cents/100:.2f}! Confirmation: {intent.id[:12]}'
        return {'prompt': f'Customer offers ${offer_cents/100:.2f}.', 'response': response, 'outcome': 'charged'}
    except stripe.error.CardError as e:
        return {'prompt': f'Customer offers ${offer_cents/100:.2f}.', 'response': f'Card declined: {e.user_message}. Try another?', 'outcome': 'card_error'}

pairs = [simulate_haggle_transaction(500, 1200) for _ in range(20)]
with open('training-data/hand_tune/commerce/stripe_haggle.jsonl', 'w') as f:
    for p in pairs:
        f.write(json.dumps({'prompt': p['prompt'], 'response': p['response']}) + '\\n')
```""",
        """This script plays out hundreds of simulated sales with real Stripe test API calls (no actual money), then saves each conversation as a training example for your commerce AI. It picks a random offer amount, checks it against the profit floor, and if the sale can proceed it actually tries to run a test charge through Stripe. That way each training example includes a realistic Stripe confirmation ID, making the AI's responses feel authentic rather than made-up. Failed cards are also simulated — roughly 10% of accepted offers get a card decline, which teaches the AI how to handle payment failures gracefully. Run it for 100-200 examples to build a solid dataset."""
    ),
]


def dominant_tongue(weights: dict) -> str:
    return max(weights, key=weights.get)


def difficulty_from_profile(profile: str) -> float:
    """Assign difficulty based on how technically complex the topic is."""
    d = {
        "negotiation": 0.35, "payment_code": 0.55, "checkout_ui": 0.45,
        "security": 0.70, "webhook_auth": 0.75, "legal_policy": 0.40,
        "training_gen": 0.60, "react_ui": 0.50, "stripe_test": 0.30,
        "discount_floor": 0.65, "haggle_stripe": 0.70,
    }
    base = d.get(profile, 0.50)
    return round(base + random.uniform(-0.05, 0.05), 3)


def source_hash(prompt: str) -> str:
    return hashlib.sha256(prompt.encode()).hexdigest()[:8]


def make_system_header(weights: dict, layers: list, axioms: list, difficulty: float) -> str:
    tongue_str = " ".join(f"{k}={v:.3f}" for k, v in weights.items())
    layer_str = " ".join(f"L{l}" for l in sorted(layers))
    axiom_str = " ".join(axioms)
    return (
        f"[TONGUES: {tongue_str}]\n"
        f"[LAYERS: {layer_str}]\n"
        f"[AXIOMS: {axiom_str}]\n"
        f"[DIFFICULTY: {difficulty:.3f}]\n"
        f"You are a commerce and web development assistant. "
        f"You help with Square payments, Stripe, frontend/backend code, security, and checkout processing. "
        f"You NEVER recommend selling below cost + $3 minimum profit."
    )


def make_scbe_record(profile: str, prompt: str, response: str, english: str, idx: int) -> dict:
    weights = TONGUE_PROFILES[profile]
    layers = LAYER_MAP[profile]
    axioms = AXIOM_MAP[profile]
    diff = difficulty_from_profile(profile)
    dt = dominant_tongue(weights)
    sh = source_hash(prompt)

    system_content = make_system_header(weights, layers, axioms, diff)

    # Randomly choose whether to give code or English response for variety
    # Always store both; primary response alternates
    use_english = (idx % 3 == 2)  # every 3rd record use English version
    primary_response = english if use_english else response

    record = {
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": primary_response},
        ],
        "tongue_weights": weights,
        "dominant_tongue": dt,
        "layers": sorted(layers),
        "axioms": axioms,
        "difficulty": diff,
        "augmentation": "commerce_sft",
        "tags": [
            "commerce",
            "hand_tuned",
            profile,
            "stripe" if "stripe" in profile or "stripe" in prompt.lower() else "square",
            "english" if use_english else "code",
        ],
        "source_hash": sh,
        "metadata": {
            "source": SOURCE,
            "version": VERSION,
            "author": AUTHOR,
            "origin": "hand_tune_commerce",
            "track": "commerce",
            "has_code_variant": True,
            "has_english_variant": True,
        },
    }
    return record


def make_plain_record(prompt: str, english: str) -> dict:
    """Simple messages format for plain English training."""
    return {
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a commerce assistant. Explain payment, pricing, and web store concepts "
                    "in plain English that anyone can understand. "
                    "You never recommend selling below cost + $3 minimum profit."
                ),
            },
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": english},
        ],
        "task_type": "commerce_english",
        "track": "commerce",
    }


_SUCCESS_ROTATION = ["payment_code", "stripe_test", "webhook_auth", "checkout_ui", "discount_floor", "haggle_stripe"]
_success_rotation_idx = 0


def _classify_haggle_profile(prompt: str, response: str) -> str:
    """Classify a haggle record by what actually happened, rotating among
    semantically valid profiles for successful charges to spread tongue coverage.

    Successful charge outcomes rotate across:
        CA (payment_code)   — compute/transaction
        CA (stripe_test)    — test infrastructure
        DR (webhook_auth)   — auth + schema (the confirmation is a webhook-like event)
        AV (checkout_ui)    — context + customer I/O
        RU (discount_floor) — accepted deal at or near floor
        KO (haggle_stripe)  — full negotiation arc completed

    UM (security)      — card declined / payment failure
    RU (legal_policy)  — hard floor hold
    KO (negotiation)   — borderline counter-offer
    """
    global _success_rotation_idx
    r = response.lower()

    # Card declined / payment failure — security/redaction (UM dominant)
    if "declined" in r or "card was declined" in r or "payment issue" in r or "try another card" in r:
        return "security"

    # Hard floor hold — policy binding (RU dominant)
    if ("hard floor" in r or "lose money" in r) and "closest" not in r:
        return "legal_policy"

    # Borderline counter-offer — negotiation (KO dominant)
    if "closest" in r or "floor with costs" in r or "deal at that" in r:
        return "negotiation"

    # Successful charge — rotate through valid profiles for tongue variety
    if "confirmation" in r or "payment went through" in r or "get your order" in r:
        profile = _SUCCESS_ROTATION[_success_rotation_idx % len(_SUCCESS_ROTATION)]
        _success_rotation_idx += 1
        return profile

    return "negotiation"


def load_stripe_haggle(path: str) -> list[tuple]:
    """Load stripe_haggle.jsonl, classifying each record by actual transaction outcome."""
    results = []
    if not os.path.exists(path):
        return results

    outcome_counts: dict[str, int] = {}

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
                prompt = d.get("prompt", "")
                response = d.get("response", "")
                if not prompt or not response:
                    continue

                profile = _classify_haggle_profile(prompt, response)
                outcome_counts[profile] = outcome_counts.get(profile, 0) + 1

                r = response.lower()
                if "confirmation" in r:
                    english = (
                        f"The customer's offer was accepted and the payment went through successfully. "
                        f"A Stripe confirmation ID was issued. Outcome: {response}"
                    )
                elif "declined" in r or "card" in r:
                    english = (
                        f"The offer was acceptable price-wise but the card failed. "
                        f"The seller needs to handle this gracefully and ask for another payment method. "
                        f"Outcome: {response}"
                    )
                elif "floor" in r.lower() or "can't go below" in r:
                    english = (
                        f"The customer's offer was below the $3 profit floor and was declined. "
                        f"The seller enforced the minimum price policy. Outcome: {response}"
                    )
                else:
                    english = (
                        f"The seller evaluated the customer's offer against the profit floor. "
                        f"Outcome: {response}"
                    )

                results.append((profile, prompt, response, english))
            except Exception:
                pass

    print(f"  Stripe haggle classification: {dict(outcome_counts)}")
    return results


def run(merge_stripe: bool, output_scbe: str, output_plain: str) -> None:
    examples = list(EXAMPLES)

    if merge_stripe:
        haggle_path = "training-data/hand_tune/commerce/stripe_haggle.jsonl"
        stripe_extras = load_stripe_haggle(haggle_path)
        examples.extend(stripe_extras)
        print(f"Merged {len(stripe_extras)} stripe_haggle records")

    scbe_records = []
    plain_records = []

    for idx, (profile, prompt, code_resp, english) in enumerate(examples):
        # SCBE rich record (code or English depending on idx)
        scbe_records.append(make_scbe_record(profile, prompt, code_resp, english, idx))
        # Always add the English variant as a separate plain record
        plain_records.append(make_plain_record(prompt, english))
        # Also add a second SCBE record using the English response for coverage
        scbe_records.append(make_scbe_record(profile, prompt, english, code_resp, idx + 1000))

    Path(output_scbe).parent.mkdir(parents=True, exist_ok=True)
    with open(output_scbe, "w", encoding="utf-8") as f:
        for r in scbe_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(output_plain, "w", encoding="utf-8") as f:
        for r in plain_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print(f"SCBE format: {len(scbe_records):>4} records -> {output_scbe}")
    print(f"Plain English: {len(plain_records):>4} records -> {output_plain}")
    print()
    print("Tongue distribution (SCBE records):")
    tongue_counts: dict[str, int] = {}
    for r in scbe_records:
        dt = r["dominant_tongue"]
        tongue_counts[dt] = tongue_counts.get(dt, 0) + 1
    tongue_names = {"KO": "Kor'aelin", "AV": "Avali", "RU": "Runethic", "CA": "Cassisivadan", "UM": "Umbroth", "DR": "Draumric"}
    for t, c in sorted(tongue_counts.items(), key=lambda x: -x[1]):
        name = tongue_names.get(t, t)
        print(f"  {t} ({name}): {'#' * c} {c}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--merge-stripe", action="store_true", help="Merge stripe_haggle.jsonl if present")
    parser.add_argument("--output-scbe", default="training-data/hand_tune/commerce/commerce_sft_scbe.jsonl")
    parser.add_argument("--output-plain", default="training-data/hand_tune/commerce/commerce_sft_plain.jsonl")
    args = parser.parse_args()
    run(args.merge_stripe, args.output_scbe, args.output_plain)


if __name__ == "__main__":
    main()
