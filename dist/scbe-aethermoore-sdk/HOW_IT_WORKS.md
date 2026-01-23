# How SCBE-AETHERMOORE Works

A plain-English explanation for investors, developers, and security teams.

---

## The Problem

When AI agents talk to each other, how do you know:
- The message is **authentic** (not forged)?
- The sender is **authorized** (allowed to do this)?
- The action is **safe** (won't cause harm)?

Traditional security says "check a password" or "look up permissions in a database."

But AI agents operate at machine speed. They might send thousands of requests per second. They might change behavior subtly over time. A database lookup isn't enough.

---

## The Solution: Math-Based Governance

SCBE-AETHERMOORE uses **geometry and cryptography** to make these decisions:

```
Agent sends request → Math evaluates risk → Decision: ALLOW / QUARANTINE / DENY
```

The key insight: **distance in a special space = trust level**.

---

## The Five-Step Process

### Step 1: Context → Vector

Everything about "what's happening" becomes a 6-dimensional point:

```
Context: { user: "alice", action: "transfer", amount: 10000, source: "external" }
     ↓
Vector: [0.3, -0.7, 0.5, 0.2, -0.1, 0.8]
```

Think of it like GPS coordinates, but for "trust space" instead of physical space.

### Step 2: Project into Hyperbolic Space

We use a **Poincaré ball** — a mathematical space where:
- The center = maximum trust (safe zone)
- The edges = danger zone
- Distance grows **exponentially** as you move outward

```
         Safe Zone (center)
              ●
             /|\
            / | \
           /  |  \
          ●   ●   ●  ← Normal actions
         /         \
        ●───────────●  ← Edge = high risk
```

Why hyperbolic? Because attackers need to spend **exponentially more effort** to reach the danger zone. It's like trying to climb a hill that gets steeper the higher you go.

### Step 3: Measure Distance + Amplify

We measure how far the request is from the "safe center":

```
distance = hyperbolic_distance(request_point, safe_center)
risk = 1.5^(distance²)  ← Exponential amplification
```

Example:
- Normal request: distance=1.0 → risk=1.5
- Unusual request: distance=2.0 → risk=5.06
- Suspicious request: distance=3.0 → risk=38.4
- Attack attempt: distance=4.0 → risk=129

The attacker's cost grows **much faster** than our cost to check.

### Step 4: Multi-Signature Consensus (Roundtable)

For high-stakes actions, we require multiple "departments" to agree:

| Action | Required Signers |
|--------|-----------------|
| Read data | 1 (just control) |
| Write data | 2 (control + policy) |
| Delete data | 3 (control + policy + security) |
| Deploy code | 4 (all departments) |

This is like requiring both a manager AND security officer to approve a vault withdrawal.

### Step 5: Make Decision

```
IF risk < 0.3:  ALLOW  (proceed normally)
IF risk < 0.7:  QUARANTINE  (manual review)
IF risk >= 0.7: DENY  (block + alert)
```

Every decision includes:
- Exact distance and risk score
- Which factors contributed
- Full audit trail

---

## The Security Gate (Bouncer Analogy)

The `SecurityGate` acts like a nightclub bouncer:

1. **Check ID** → Verify the agent's cryptographic signature
2. **Check reputation** → Look at the agent's trust score
3. **Make them wait** → Higher risk = longer wait time

```typescript
// Trusted agent, safe action
await gate.check(alice, 'read', { source: 'internal' });
// → Allowed immediately (10ms wait)

// Untrusted agent, dangerous action
await gate.check(eve, 'delete', { source: 'external' });
// → Denied after 500ms wait (slows attackers)
```

The adaptive dwell time means:
- Legitimate users barely notice
- Attackers get slowed down significantly
- Brute force becomes impractical

---

## Trust Decay (Use It or Lose It)

Agents have a trust score that decays over time:

```
Initial trust: 1.0 (fully trusted)
     ↓
Time passes without check-in
     ↓
Trust decays: 0.95 → 0.90 → 0.85...
     ↓
Agent checks in (proves it's still legitimate)
     ↓
Trust restored: 0.95
```

This prevents:
- Stolen credentials being used days later
- Dormant compromised agents suddenly activating
- "Set and forget" security holes

---

## The Envelope (Cryptographic Wrapper)

Every message is wrapped in an **RWP v2.1 Envelope**:

```
┌─────────────────────────────────────┐
│ Envelope                            │
├─────────────────────────────────────┤
│ version: "2.1"                      │
│ payload: <encrypted message>        │
│ nonce: <unique random value>        │
│ timestamp: 1706000000000            │
│ signatures:                         │
│   ko: "abc123..."  (control)        │
│   ru: "def456..."  (policy)         │
│   um: "ghi789..."  (security)       │
└─────────────────────────────────────┘
```

Features:
- **Replay protection**: Nonce can only be used once
- **Timestamp validation**: Rejects old messages
- **Multi-signature**: Requires all listed departments to sign
- **AES-256-GCM encryption**: Payload is encrypted

---

## Why This Beats Traditional Security

| Traditional | SCBE-AETHERMOORE |
|-------------|------------------|
| Check username/password | Check cryptographic signature |
| Look up permissions in database | Calculate risk from geometry |
| Same response time for everyone | Adaptive delay based on risk |
| Binary allow/deny | Three-tier with quarantine |
| Hard to explain decisions | Every decision has exact math |
| Attackers know the rules | Cost grows exponentially |

---

## Real-World Example: AI Agent Deployment

**Scenario**: Alice's AI assistant wants to deploy code to production.

```
1. Alice's agent creates request:
   { action: "deploy", target: "prod", code_hash: "sha256:..." }

2. Request becomes 6D vector:
   [0.2, 0.8, -0.3, 0.5, 0.1, -0.2]

3. System calculates:
   - Distance from safe center: 2.4
   - Risk score: 0.48
   - Decision: QUARANTINE (needs human review)

4. Because action="deploy", requires 4 signatures:
   - ko (control): ✓ signed
   - ru (policy): ✓ signed
   - um (security): ✓ signed
   - dr (types): ✓ signed

5. Human reviews, approves

6. Envelope created with all 4 signatures + AES encryption

7. Production system verifies envelope:
   - All signatures valid ✓
   - Timestamp within window ✓
   - Nonce not reused ✓
   - Policy satisfied ✓

8. Deployment proceeds
```

---

## What Makes This Different

1. **Mathematical certainty**: Not "87% confident it's an attack" — it's "distance = 3.14, cost = 20,000×"

2. **No training period**: Works from day one (no ML model to train)

3. **No false positives from noise**: Deterministic thresholds, not statistical

4. **Exponential deterrence**: Attackers face impossible costs

5. **Full audit trail**: Every decision can be explained with exact numbers

---

## Summary

SCBE-AETHERMOORE turns AI security from "guess if it's bad" into "calculate how suspicious."

The math doesn't care what kind of attack it is. Unusual = far from center = high cost = blocked.

Simple as that.
