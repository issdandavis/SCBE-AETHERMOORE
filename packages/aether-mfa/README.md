# Aether MFA

An **owned** multi-factor library you can use across your website and your own systems, built only on
**standard cryptographic primitives** — no rolled crypto. Two layers:

| Layer | What it is | Crypto | Interop |
|---|---|---|---|
| **1. TOTP / HOTP** | The classic 6-digit second factor | `hmac` + `hashlib` (stdlib) | RFC 6238 / RFC 4226 — works with Google/Microsoft/Aegis Authenticator |
| **2. Push approval** | "AI MFA": agent requests a specific action → ping on your phone → you approve | Ed25519 via `cryptography` | Challenge/response, action-bound |

Layer 2 is the part you described: *agents send you a ping on your phone like an MFA app; you get a
match-number, you verify it, the action proceeds.* It is **L13 ESCALATE made concrete** — a governed
agent action that needs a human's cryptographic *yes* before it runs.

## Why these primitives (the "good, not toy" rationale)

You don't roll your own crypto for real security — so this doesn't. It composes well-reviewed,
standard pieces:

- **TOTP/HOTP** are the published IETF standards. Our codes match the RFC test vectors exactly
  (`test_aether_mfa.py`), which is the proof that any authenticator app will interoperate.
- **Ed25519** signatures (via the `cryptography` library, which wraps OpenSSL/`libsodium`-grade code)
  give asymmetric push approval: the **device holds the private key, the server stores only the public
  key.** A server breach cannot forge an approval.

The only thing "designed" here is the *protocol around* those primitives, and it follows the same
shape real push-MFA (Duo, Okta Verify) uses:

- **Action-binding** — the signature covers `challenge_id | action | nonce | match_number`, so a *yes*
  for "read logs" cannot be replayed as a *yes* for "delete logs".
- **Number-matching** — a code shown on the requesting surface must be echoed from the phone. Defeats
  blind-approval fatigue and push-phishing (the modern attack on plain "tap to approve").
- **Single-use + expiry** — each challenge is consumed on the first verdict and dies after its TTL, so
  a captured approval can't be replayed.
- **Constant-time comparisons** on every secret-bearing check.

## Quick start

```bash
pip install cryptography      # layer 2 only; layer 1 is stdlib
python demo_agent_mfa.py      # watch the full agent-approval story
pytest test_aether_mfa.py     # 12 tests: RFC vectors + attack cases
```

### Layer 1 — TOTP second factor

```python
import aether_mfa as mfa

secret = mfa.generate_secret()                       # base32, store per-user
uri = mfa.provisioning_uri(secret, account="issac@scbe", issuer="SCBE")
# render `uri` as a QR; the user's authenticator app scans it
mfa.verify_totp(secret, user_entered_code)           # True/False, drift-tolerant
```

### Layer 2 — push approval for an agent action

```python
verifier = mfa.PushVerifier(ttl_seconds=120)

# one-time enrollment (on the phone): keypair generated, server gets only the public key
device_id, phone_private_key, device = mfa.enroll_device(label="my phone")
verifier.register_device(device)

# an agent wants to do something sensitive
ch = verifier.create_challenge(device_id, action="publish dataset X to Hugging Face")
# -> push `ch` to the phone; show `ch.match_number` on the agent surface

# on the phone: the human confirms the number they see, device signs
sig = mfa.approve(ch, phone_private_key, entered_match_number=ch.match_number)

# server verifies
verdict = verifier.verify_approval(ch.challenge_id, sig, ch.match_number)
if verdict.allow:
    ...  # agent proceeds, bound to verdict.action
```

## Where it goes next (roadmap)

This package is the transport-agnostic core. To make it the real cross-platform system you own:

1. **Web** — drop `PushVerifier` behind a FastAPI/Flask endpoint (`/challenge`, `/approve`,
   `/verify`); serve the TOTP QR on account setup. The library is already stateless per call.
2. **Mobile push** — replace "show match_number on screen" with a real notification (APNs / FCM, or a
   self-hosted ntfy/MQTT topic). The phone app holds the Ed25519 private key in the secure enclave /
   Keystore.
3. **Durable store** — swap the in-memory `ChallengeStore` for Redis or a DB (same method surface:
   `put_device`/`get_device`/`put_challenge`/`get_challenge`). **Not a drop-in for correctness:** the
   single-use guarantee requires the "still pending? → consume" step to be **atomic**. A real backend
   must use a compare-and-set (`UPDATE … SET status='consumed' WHERE id=? AND status='pending'` and
   check rows-affected, or Redis WATCH/Lua) — otherwise two concurrent identical approvals can both
   pass and double-approve. The in-memory store only gets this for free by being single-threaded.
4. **SCBE governance hook** — ✅ built, see next section.
5. **Rate-limit + audit** — cap challenges per device per minute; append every verdict to the SCBE
   ledger so approvals are accountable.

## SCBE L13 escalation bridge (built — `scbe_escalation.py`)

The "AI MFA" hook is wired: `scbe_escalation.EscalationGate` turns an SCBE governance verdict that
says "hold for a human" into a real push approval.

```python
import scbe_escalation as esc

gate = esc.EscalationGate()                 # default hold-tiers: {QUARANTINE, REVIEW}
gate.register_device(my_phone)

result = runtime_gate.evaluate(action_text, tool_name)   # SCBE RuntimeGate, unchanged
out = gate.guard(action_text, result, device_id)
if out.released:
    proceed_if(out.decision == "ALLOW")     # ALLOW/DENY/REROUTE are final now
else:
    # out.challenge was pushed to the phone; the human approves out of band:
    final = gate.resolve(out.challenge.challenge_id, signature, match_number)
    proceed_if(final == "ALLOW")
```

**Tier choice (the part that's easy to get wrong).** Canonical L13 `ESCALATE` maps to RuntimeGate's
`Decision.REVIEW` — but `REVIEW` only fires when council/trichromatic **overlays are enabled**. A
*base* `RuntimeGate()` council returns ALLOW / **QUARANTINE** / DENY, so QUARANTINE is the tier that
actually asks for a human by default. The bridge therefore holds on **both** `{QUARANTINE, REVIEW}` by
default (constructor-overridable), so it isn't a dead gate in the common config.

**Honest scope:** this is a *bridge that consumes* `GateResult` (duck-typed — no import of the
2400-line `runtime_gate.py`, no heavy deps, no collision with that hot file). It does **not** yet make
`runtime_gate.evaluate()`'s callers route through MFA — that live insertion is a separate edit, and
needs `aether-mfa` importable from `src/` first. `demo_scbe_escalation.py` + `test_scbe_escalation.py`
prove the round-trip (ALLOW passes, DENY blocks, QUARANTINE → push → signed approve → ALLOW, replay → DENY).

## Files

- `aether_mfa.py` — the library (layer 1 + layer 2).
- `test_aether_mfa.py` — RFC 4226/6238 interop vectors + push attack cases (wrong-match, expired,
  replay, action-binding, nonce-binding, forged signature, unknown device). **13 passing.**
- `demo_agent_mfa.py` — end-to-end narration of the agent-approval flow, including a denied phishing
  attempt.
- `scbe_escalation.py` — the SCBE L13 bridge: routes QUARANTINE/REVIEW verdicts to MFA approval.
- `test_scbe_escalation.py` — tier routing + the hold-tier approval round-trip. **9 passing.**
- `demo_scbe_escalation.py` — gate verdict → push → human approval, end to end.

## Threat model (what it does and does NOT cover)

**Covers:** stolen server DB (no private keys to steal), push-phishing / approval-fatigue (number
match), replay (single-use + nonce), action redirection (binding), forged approvals (Ed25519).

**The one assumption everything rests on — enrollment integrity.** `register_device` accepts any
public key; Ed25519 only proves "whoever enrolled this key approved." If an attacker enrolls *their*
device key against your account, they approve everything. So enrollment **must** happen inside an
already-authenticated session with out-of-band confirmation (the classic MFA bootstrap problem). The
push layer is exactly as strong as that step.

**Out of scope (you provide):** the transport's own TLS; secure key storage on the device (use the OS
secure enclave / Keystore in a real app); rate-limiting and lockout policy; the human actually reading
the action text before approving. TOTP secrets must be stored encrypted at rest server-side. TOTP has
no within-window replay guard (a code re-entered inside its 30 s period re-validates — standard TOTP
behavior); add a per-user last-used-counter if you need strict single-use codes.
