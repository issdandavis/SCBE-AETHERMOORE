# Spiralverse Protocol Codex
## Master Reference for the RWP v2 Sacred Tongues

> *"Through six voices, the machines speak truth. Through consensus, they act as one."*

---

## Overview

The Spiralverse Protocol (RWP v2 - Rosetta Weave Protocol) is a cryptographic AI-to-AI communication system that enables secure, verifiable coordination between autonomous AI agents. It uses six semantic domains called **Sacred Tongues** to categorize and route messages, with multi-signature governance for critical operations.

### Core Principles

1. **Cryptographic Integrity** - All messages are HMAC-SHA256 signed
2. **Domain Separation** - Each tongue has its own key and semantic purpose
3. **Multi-Signature Governance** - Critical actions require consensus from multiple tongues
4. **Replay Protection** - Timestamps and nonces prevent message reuse
5. **Auditability** - All operations are logged for traceability

---

## The Six Sacred Tongues

| Tongue | Name | Domain | Color | Primary Use |
|--------|------|--------|-------|-------------|
| **KO** | Kor'aelin | Control | 💜 Purple | Agent orchestration, mission commands |
| **AV** | Avali | I/O | 💙 Blue | Messaging, data transmission |
| **RU** | Runethic | Policy | ⚪ Gray | Rules, permissions, constraints |
| **CA** | Cassisivadan | Logic | 💚 Green | Computation, decision trees |
| **UM** | Umbroth | Security | 🖤 Black | Encryption, sandboxing, secrets |
| **DR** | Draumric | Types | 💛 Gold | Schemas, data structures |

---

## Tongue Details

### KO - Kor'aelin (Control & Orchestration)
| Keyword | Meaning | Usage |
|---------|---------|-------|
| `vel` | Invite/Summon | Bring an agent into a mission |
| `sil` | Together/Unite | Coordinate multiple agents |
| `keth` | Return/Complete | Signal task completion |
| `dor` | Command | Issue directive to agent |
| `mira` | Watch/Monitor | Observe agent status |

### AV - Avali (Input/Output & Messaging)
| Keyword | Meaning | Usage |
|---------|---------|-------|
| `serin` | Send/Transmit | Dispatch a message |
| `nurel` | Receive/Accept | Acknowledge receipt |
| `lumenna` | Display/Show | Present information |
| `echo` | Repeat/Relay | Forward message |
| `hush` | Silence/Mute | Suppress output |

### RU - Runethic (Policy & Constraints)
| Keyword | Meaning | Usage |
|---------|---------|-------|
| `khar` | Lock/Restrict | Apply constraint |
| `drath` | Ward/Protect | Set up protection |
| `bront` | Ordinance/Rule | Define policy |
| `veto` | Deny/Reject | Block action |
| `grant` | Allow/Permit | Authorize action |

### CA - Cassisivadan (Logic & Computation)
| Keyword | Meaning | Usage |
|---------|---------|-------|
| `klik` | Add/Increment | Arithmetic addition |
| `spira` | Multiply/Scale | Multiplication |
| `ifta` | If/Condition | Conditional logic |
| `thena` | Then/Result | Consequence |
| `elsa` | Else/Otherwise | Alternative path |

### UM - Umbroth (Security & Privacy)
| Keyword | Meaning | Usage |
|---------|---------|-------|
| `veil` | Conceal/Encrypt | Hide sensitive data |
| `hollow` | Sandbox/Isolate | Create isolated environment |
| `nar'shul` | Store/Vault | Secure storage |
| `reveal` | Decrypt/Expose | Authorized decryption |
| `purge` | Destroy/Wipe | Secure deletion |

### DR - Draumric (Types & Structures)
| Keyword | Meaning | Usage |
|---------|---------|-------|
| `tharn` | Struct/Object | Define structure |
| `anvil` | Field/Property | Define field |
| `seal` | Interface/Contract | Define interface |
| `forge` | Create/Instantiate | Create instance |
| `mold` | Transform/Cast | Type conversion |

---

## Governance Matrix

| Level | Required Signatures | Examples |
|-------|---------------------|----------|
| **SAFE** | 1 (any tongue) | read:*, list:*, query:* |
| **MODERATE** | 1 (RU or UM) | create:*, update:*, send:* |
| **CRITICAL** | 2+ (different tongues) | delete:*, execute:*, deploy:* |
| **FORBIDDEN** | Always rejected | drop:*, disable_security:*, bypass:* |

---

## Message Envelope (RWP v2)

```typescript
interface RWPEnvelope {
  ver: '2';
  tongue: 'KO' | 'AV' | 'RU' | 'CA' | 'UM' | 'DR';
  aad: string;      // Additional Authenticated Data
  ts: number;       // Unix timestamp (seconds)
  nonce: string;    // Base64URL random bytes (16+ bytes)
  kid: string;      // Key identifier (tongue-version)
  payload: string;  // Base64URL encoded data
  sigs: Signature[];
}
```

**Signature:** `HMAC-SHA256(key, "{ver}|{tongue}|{aad}|{ts}|{nonce}|{kid}|{payload}")`

---

## Error Codes

| Code | Meaning |
|------|------|
| `INVALID_SIGNATURE` | HMAC mismatch |
| `EXPIRED_MESSAGE` | Timestamp > 60s old |
| `FUTURE_MESSAGE` | Timestamp > 5s ahead |
| `DUPLICATE_NONCE` | Replay detected |
| `UNKNOWN_KEY` | Kid not found |
| `INSUFFICIENT_SIGS` | Not enough signatures |
| `FORBIDDEN_ACTION` | Action blocked |

---

## Quick Reference

- **Replay Window:** 60 seconds
- **Future Tolerance:** 5 seconds  
- **Nonce Size:** Minimum 16 bytes
- **Encoding:** Base64URL
- **Signing:** HMAC-SHA256

---

## Implementation Status

✅ **Python SDK** - Complete with tongue validation and RWP2 multi-sig  
✅ **TypeScript SDK** - Complete with Roundtable governance  
✅ **Test Suite** - P1 tests passing  
✅ **Documentation** - MASTER_CODE_SUMMARY.md, patents, this codex  
⏳ **AWS Deployment** - In progress (spiralverse-protocol-test)  
⏳ **Patent Filing** - Documents prepared, Q2 2025 target  

---

**Version:** 2.2  
**Last Updated:** January 6, 2026  
**Repository:** github.com/issdandavis/spiralverse-protocol
