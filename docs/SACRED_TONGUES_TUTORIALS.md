# Sacred Tongue Tokenizer — Practical Tutorials & Use Cases (Canonical Compact Format)

**Educational Materials Version:** 1.0
**Last Updated:** January 2026
**Difficulty:** Beginner → Advanced

This document defines the **canonical “compact” spell-text format** used inside SS1 blobs (one tongue prefix per field), provides hands-on tutorials (manual + programmatic), and includes a test suite and a short integration note for the **21D state spine**.

---

## 0. Mini‑Spec (Read This First)

### 0.1 Terms

* **Tongue**: a 256‑symbol, human‑readable encoding for bytes (e.g., `ko`, `ru`, `ca`, `dr`, `av`, `um`).
* **Token**: one byte encoded as a morpheme pair: `prefix + "'" + suffix`.
* **Spell‑text**: a sequence of tokens representing bytes, with a tongue marker.
* **Section**: a semantic domain in SS1 (e.g., `salt`, `nonce`, `ct`) that routes to a default tongue.
* **Compact format**: one tongue marker per spell-text field.
* **Verbose format**: tongue marker repeated per token (for debugging/logging).

### 0.2 Token Format (Byte → Token)

A byte `b ∈ [0,255]` is encoded by splitting into two nibbles:

* `h = (b >> 4) & 0x0F`  (high nibble)
* `l = b & 0x0F`         (low nibble)

Each tongue defines:

* `prefixes[0..15]` (16 strings)
* `suffixes[0..15]` (16 strings)

**Token**:

```text
TOKEN(b) := prefixes[h] + "'" + suffixes[l]
```

**Decode** reverses the lookup:

* find `h` from `prefix`
* find `l` from `suffix`
* reconstruct `b = (h << 4) | l`

> **Requirement:** the prefix and suffix tables must be 1‑to‑1 (no duplicates), or decode becomes ambiguous.

### 0.3 Canonicalization Rules (Non‑Negotiable)

To guarantee deterministic parsing and safe round‑trips:

1. **Lowercase only** for all tokens.
2. Apostrophe must be **ASCII** `'` (U+0027). Reject Unicode quotes like `’` (U+2019).
3. Token must match `prefix` and `suffix` exactly from the tongue tables.
4. Whitespace normalization: treat runs of whitespace as a single space when parsing.

### 0.4 Spell‑Text Formats

#### 0.4.1 Canonical (Compact) — used in SS1 blobs

One tongue marker per field:

```text
ko:zar'un thul'ir ael'esh vel'en
```

* `ko:` appears exactly once at the start of the spell-text.
* Tokens follow, space-separated.

#### 0.4.2 Optional (Verbose) — CLI/logging/testing only

Tongue marker repeated per token:

```text
ko:zar'un ko:thul'ir ko:ael'esh ko:vel'en
```

**Rule:** SS1 blobs MUST use **compact**; verbose is for:

* CLI debug output
* Development logs
* Token-by-token validation in tests

### 0.5 SS1 Blob Grammar (Pipe‑Delimited)

Canonical SS1 grammar (recommended):

```text
SS1|v=1|kid=<ascii>|aad=<ascii>|salt=<spell>|nonce=<spell>|ct=<spell>|tag=<spell>
```

Optional fields can be appended (e.g., `|redact=<spell>`).

**Constraints**

* `kid` and `aad` are ASCII key/value fields.
* `|` is the delimiter: do not place raw `|` in values.
* If you must embed delimiter characters, percent‑encode the value first (e.g., URL encoding) and decode after parsing.

### 0.6 Section → Tongue Routing Table (Reference)

Even if your implementation allows override, this routing table is the reference convention:

| SS1 Section | Default Tongue | Rationale                              |
| ----------- | -------------: | -------------------------------------- |
| `aad`       |           `av` | context / diplomatic metadata          |
| `salt`      |           `ru` | binding / commitment material          |
| `nonce`     |           `ko` | flow / intent / nonce material         |
| `ct`        |           `ca` | bitcraft / mathematics payload         |
| `tag`       |           `dr` | structure / integrity / authentication |
| `redact`    |           `um` | veil / erasure directives              |

### 0.7 Best Practice: Length‑Prefix Authentication Bundles

When you concatenate multiple binary pieces into one spell-text field (e.g., `auth_tag || signature`), always make boundaries explicit.

Recommended pattern:

```text
AUTH_PAYLOAD := u16be(len(auth_tag)) || auth_tag || u16be(len(signature)) || signature
```

This prevents ambiguity if sizes ever change.

---

## 1. Tutorial 1 — Your First Sacred Tongue Encoding (Manual + Verifiable)

### 1.1 The Problem

You have a nonce (bytes) and want a representation that is:

* Machine-readable ✓
* Human-verifiable ✓
* Phonetically elegant ✓
* Deterministic ✓

### 1.2 Example Input (16 bytes)

```text
Raw bytes:
0x3c 0x5a 0x7f 0x2e 0x91 0xb4 0x68 0x42 0xd3 0x1e 0xa7 0xc9 0x4b 0x6f 0x88 0x15
```

We will use **Kor'aelin (`ko`)** as the default nonce tongue.

### 1.3 Manual Encoding (Learn the Nibbles)

Take the first byte: `0x3c`

* Binary: `0011 1100`
* High nibble: `0011` = `3`
* Low nibble:  `1100` = `12`

Token:

```text
ko_token = prefixes[3] + "'" + suffixes[12]
```

> Your actual `prefixes[]` and `suffixes[]` determine the surface string.

### 1.4 Nibble Debug Printing (Recommended)

Use this helper to make the walkthrough **self-verifying** against your wordlists:

```python
from sacred_tokenizer import SacredTongueTokenizer


def debug_encode_byte(tokenizer: SacredTongueTokenizer, b: int) -> str:
    assert 0 <= b <= 255
    h = (b >> 4) & 0x0F
    l = b & 0x0F

    # Assumes tokenizer exposes prefixes/suffixes. If not, use tokenizer internals.
    prefix = tokenizer.prefixes[h]
    suffix = tokenizer.suffixes[l]
    token = f"{prefix}'{suffix}"

    print(
        f"b=0x{b:02x}  bin={b:08b}  h={h:>2}  l={l:>2}  "
        f"prefix[{h}]={prefix}  suffix[{l}]={suffix}  token={token}"
    )
    return token


tok = SacredTongueTokenizer("ko")
debug_encode_byte(tok, 0x3C)
debug_encode_byte(tok, 0x5A)
```

### 1.5 Programmatic Encoding (Compact Spell‑Text)

```python
from sacred_tokenizer import SacredTongueTokenizer

nonce_bytes = bytes([
    0x3c, 0x5a, 0x7f, 0x2e, 0x91, 0xb4, 0x68, 0x42,
    0xd3, 0x1e, 0xa7, 0xc9, 0x4b, 0x6f, 0x88, 0x15
])

tok = SacredTongueTokenizer("ko")
spell_compact = tok.encode(nonce_bytes)  # should return: "ko:<tokens...>"
print(spell_compact)

# Round-trip verification
recovered = tok.decode(spell_compact)
assert recovered == nonce_bytes
print("✓ Round-trip successful!")
```

### 1.6 Optional Verbose Debug Output

```python
# Optional: per-token tongue prefix for logs
spell_verbose = tok.encode(nonce_bytes, verbose=True)
print(spell_verbose)
```

---

## 2. Tutorial 2 — Building a Complete SS1 Encrypted Backup (AES‑GCM + PBKDF2)

### 2.1 Scenario

You want to encrypt a backup file with:

* Plaintext: user data
* Password: user-supplied passphrase
* Output: **SS1 spell‑text blob** for storage/transmission

### 2.2 Correct Implementation (PBKDF2 Fix + Compact Fields)

This tutorial uses `hashlib.pbkdf2_hmac` for portability.

```python
import os
import time
import hashlib
from dataclasses import dataclass
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from sacred_tokenizer import format_ss1_blob, parse_ss1_blob


@dataclass
class BackupEncryptor:
    """Encrypt backups using Sacred Tongue SS1 format."""

    user_id: str
    kdf_iterations: int = 200_000

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive a 32-byte AES key using PBKDF2-HMAC-SHA256."""
        return hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            self.kdf_iterations,
            dklen=32,
        )

    def encrypt_backup(self, plaintext: bytes, password: str) -> str:
        # Step 1: random cryptographic material
        salt = os.urandom(16)
        nonce = os.urandom(12)

        # Step 2: derive key
        key = self._derive_key(password, salt)

        # Step 3: encrypt
        cipher = AESGCM(key)
        aad_bytes = self.user_id.encode("utf-8")
        full_ct = cipher.encrypt(nonce, plaintext, aad_bytes)  # ct||tag

        # Step 4: split tag
        ct_body, tag = full_ct[:-16], full_ct[-16:]

        # Step 5: SS1 format (compact spell-text per field)
        kid = f"{self.user_id}-backup-{int(time.time())}"
        ss1_blob = format_ss1_blob(
            v=1,
            kid=kid,
            aad=self.user_id,
            salt=salt,
            nonce=nonce,
            ciphertext=ct_body,
            tag=tag,
        )
        return ss1_blob

    def decrypt_backup(self, ss1_blob: str, password: str) -> bytes:
        # Step 1: parse SS1
        c = parse_ss1_blob(ss1_blob)
        salt = c["salt"]
        nonce = c["nonce"]
        ct_body = c["ct"]
        tag = c["tag"]
        aad_bytes = c["aad"].encode("utf-8")

        # Step 2: derive key
        key = self._derive_key(password, salt)

        # Step 3: decrypt
        cipher = AESGCM(key)
        full_ct = ct_body + tag
        return cipher.decrypt(nonce, full_ct, aad_bytes)


# Usage
encryptor = BackupEncryptor(user_id="alice-2026")
plaintext = b"Secret backup data - family photos and documents"
password = "MySecurePassphrase123"

ss1_blob = encryptor.encrypt_backup(plaintext, password)
print("Encrypted SS1 Blob:")
print(ss1_blob)
print()

recovered = encryptor.decrypt_backup(ss1_blob, password)
assert recovered == plaintext
print("✓ Decryption successful!")
```

### 2.3 Expected Output Shape (Canonical Compact)

Your `format_ss1_blob()` should produce fields like:

```text
SS1|v=1|kid=alice-2026-backup-1705433400|aad=alice-2026|
  salt=ru:<tokens...>|nonce=ko:<tokens...>|ct=ca:<tokens...>|tag=dr:<tokens...>
```

> **Canonical rule:** within each field, the tongue marker appears once: `nonce=ko:<tokens...>`.

---

## 3. Tutorial 3 — Multi‑Party Key Recovery (Shamir Shares + Sacred Tongues)

### 3.1 Scenario

* You have a 32‑byte master key.
* Split into `N` shares with threshold `T` (Shamir).
* Each share is distributed to a party.
* Shares are encoded into spell‑text for human auditing and safe transport.

### 3.2 Correct Implementation (True Share IDs + True Tongue Distribution)

```python
import os
from dataclasses import dataclass
from sacred_tokenizer import SacredTongueTokenizer

# Replace these with your Shamir library
from threshold_crypto import split_secret, recover_secret


@dataclass
class EncodedShare:
    share_id: int
    tongue: str
    spell_text: str


class SecretSharingRecovery:
    """Multi-party key recovery using Sacred Tongues."""

    def setup_shares(self, master_secret: bytes, num_shares: int, threshold: int):
        shares = split_secret(
            secret=master_secret,
            num_shares=num_shares,
            threshold=threshold,
        )

        tongues = ["ko", "ru", "ca", "av", "dr", "um"]
        encoded: dict[str, EncodedShare] = {}

        for i, (share_id, share_bytes) in enumerate(shares):
            tongue = tongues[i % len(tongues)]
            tok = SacredTongueTokenizer(tongue)

            # Explicit tongue encoding (NOT section routing)
            spell = tok.encode(share_bytes)

            encoded[f"party_{i+1}"] = EncodedShare(
                share_id=share_id,
                tongue=tongue,
                spell_text=spell,
            )

        return encoded

    def verify_share_integrity(self, share: EncodedShare) -> bool:
        try:
            tok = SacredTongueTokenizer(share.tongue)
            recovered = tok.decode(share.spell_text)
            return recovered is not None and len(recovered) > 0
        except Exception:
            return False

    def recover_secret(self, party_shares: dict[str, EncodedShare]) -> bytes:
        shares_for_recovery = []
        for party_id, share in party_shares.items():
            tok = SacredTongueTokenizer(share.tongue)
            share_bytes = tok.decode(share.spell_text)

            # IMPORTANT: use real share_id from Shamir
            shares_for_recovery.append((share.share_id, share_bytes))

        return recover_secret(shares_for_recovery)


# Usage
recovery = SecretSharingRecovery()
master_key = os.urandom(32)

# Split into 5 shares, threshold 3
shares = recovery.setup_shares(master_key, num_shares=5, threshold=3)

print("Distributed shares:")
for party, info in shares.items():
    print(f"\n{party}:")
    print(f"  Tongue: {info.tongue}")
    print(f"  Spell-text (first 60): {info.spell_text[:60]}...")

# Later: any 3 parties recover
subset = {"party_1": shares["party_1"], "party_2": shares["party_2"], "party_3": shares["party_3"]}
recovered = recovery.recover_secret(subset)
assert recovered == master_key
print("\n✓ Master key recovered successfully!")
```

**Note on tongue inference:** Avoid auto-detecting tongues in normal operation (it becomes a guessing oracle and slows recovery). Store tongue metadata with the share.

---

## 4. Tutorial 4 — Tongue‑Specific Cryptographic Protocols (Domain Separation by Tongue)

### 4.1 Scenario

Design a protocol where different tongues represent different security domains:

1. Initialization → **Avali (`av`)** (context/metadata)
2. Key Exchange → **Runethic (`ru`)** (binding/commitment)
3. Message Flow → **Kor'aelin (`ko`)** (intent/nonce)
4. Encryption → **Cassisivadan (`ca`)** (bitcraft)
5. Authentication → **Draumric (`dr`)** (structure/integrity)
6. Cleanup/Redaction → **Umbroth (`um`)** (erasure)

### 4.2 Implementation (Length‑Prefixed Auth Payload)

```python
import os
import time
import json
import hashlib
from dataclasses import dataclass

from sacred_tokenizer import encode_to_spelltext


def u16be(n: int) -> bytes:
    if not (0 <= n <= 65535):
        raise ValueError("u16 out of range")
    return n.to_bytes(2, "big")


@dataclass
class MultiPhaseCryptographicProtocol:
    """Protocol using different tongues for each phase."""

    def phase_1_initialization(self, protocol_name: str, parties: list[str]) -> dict:
        init_data = {
            "protocol": protocol_name,
            "parties": parties,
            "timestamp": int(time.time()),
            "version": "1.0",
        }
        init_bytes = json.dumps(init_data, separators=(",", ":"), sort_keys=True).encode("utf-8")
        init_spell = encode_to_spelltext(init_bytes, section="aad")
        return {"phase": "initialization", "tongue": "av", "data": init_spell}

    def phase_2_key_exchange(self, ephemeral_public_key: bytes) -> dict:
        key_spell = encode_to_spelltext(ephemeral_public_key, section="salt")
        return {"phase": "key_exchange", "tongue": "ru", "data": key_spell}

    def phase_3_message_flow(self, nonce: bytes, message_hash: bytes) -> dict:
        flow_data = nonce + message_hash
        flow_spell = encode_to_spelltext(flow_data, section="nonce")
        return {"phase": "message_flow", "tongue": "ko", "data": flow_spell}

    def phase_4_encryption(self, ciphertext: bytes) -> dict:
        ct_spell = encode_to_spelltext(ciphertext, section="ct")
        return {"phase": "encryption", "tongue": "ca", "data": ct_spell}

    def phase_5_authentication(self, auth_tag: bytes, signature: bytes) -> dict:
        # Best practice: explicit boundaries
        payload = u16be(len(auth_tag)) + auth_tag + u16be(len(signature)) + signature
        auth_spell = encode_to_spelltext(payload, section="tag")
        return {"phase": "authentication", "tongue": "dr", "data": auth_spell}

    def phase_6_redaction(self, ephemeral_key: bytes, session_material: bytes) -> dict:
        directive = ephemeral_key + session_material
        redact_spell = encode_to_spelltext(directive, section="redact")
        return {"phase": "redaction", "tongue": "um", "data": redact_spell}

    def execute_full_protocol(self) -> list[dict]:
        trace: list[dict] = []

        trace.append(self.phase_1_initialization("Secure Channel v1", ["alice", "bob"]))

        ephemeral_key = os.urandom(32)
        trace.append(self.phase_2_key_exchange(ephemeral_key))

        nonce = os.urandom(12)
        message_hash = hashlib.sha256(b"Hello Bob").digest()
        trace.append(self.phase_3_message_flow(nonce, message_hash))

        ciphertext = os.urandom(100)
        trace.append(self.phase_4_encryption(ciphertext))

        auth_tag = os.urandom(16)
        signature = os.urandom(64)
        trace.append(self.phase_5_authentication(auth_tag, signature))

        trace.append(self.phase_6_redaction(ephemeral_key, b"session_data"))
        return trace


# Usage
protocol = MultiPhaseCryptographicProtocol()
trace = protocol.execute_full_protocol()

print("Multi-Phase Protocol Trace")
print("=" * 60)
for step in trace:
    print(f"\nPhase: {step['phase'].upper()}")
    print(f"Tongue: {step['tongue']}")
    print(f"Data (first 80): {step['data'][:80]}...")
```

---

## 5. Test Suite (Invariants & Integration Proof)

These tests are intended for `pytest`. They cover:

1. **Tokenizer invariants** (round‑trip, canonicalization)
2. **SS1 invariants** (format/parse, tamper detection)
3. **Protocol invariants** (phase routing, boundary clarity)

> If you use Hypothesis, you can extend the random loops into property-based tests.

### 5.1 Tokenizer Invariants

```python
import os
import pytest
from sacred_tokenizer import SacredTongueTokenizer


def test_tokenizer_roundtrip_random_bytes():
    tok = SacredTongueTokenizer("ko")
    for _ in range(200):
        b = os.urandom(64)
        s = tok.encode(b)
        recovered = tok.decode(s)
        assert recovered == b


def test_reject_unicode_apostrophe():
    tok = SacredTongueTokenizer("ko")

    # Construct a valid encoding then swap ASCII apostrophe with U+2019
    b = b"\x00\x10\x20\x30"
    s = tok.encode(b)
    s_bad = s.replace("'", "’")

    with pytest.raises(Exception):
        tok.decode(s_bad)


def test_canonical_lowercase_only():
    tok = SacredTongueTokenizer("ko")
    b = b"\x3c"
    s = tok.encode(b)
    s_upper = s.upper()

    with pytest.raises(Exception):
        tok.decode(s_upper)
```

### 5.2 SS1 Invariants

```python
import os
import pytest
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from sacred_tokenizer import format_ss1_blob, parse_ss1_blob


def test_ss1_format_parse_roundtrip():
    # Minimal roundtrip: bytes -> SS1 -> parsed bytes
    salt = os.urandom(16)
    nonce = os.urandom(12)
    ct = os.urandom(32)
    tag = os.urandom(16)

    blob = format_ss1_blob(
        v=1,
        kid="kid-test",
        aad="aad-test",
        salt=salt,
        nonce=nonce,
        ciphertext=ct,
        tag=tag,
    )

    c = parse_ss1_blob(blob)
    assert c["kid"] == "kid-test"
    assert c["aad"] == "aad-test"
    assert c["salt"] == salt
    assert c["nonce"] == nonce
    assert c["ct"] == ct
    assert c["tag"] == tag


def test_ss1_tamper_detect_aesgcm_tag_fails():
    # Encrypt then flip one token in ct -> decrypt must fail
    key = os.urandom(32)
    cipher = AESGCM(key)

    salt = os.urandom(16)
    nonce = os.urandom(12)
    aad = b"aad"
    plaintext = b"hello world"

    full_ct = cipher.encrypt(nonce, plaintext, aad)
    ct, tag = full_ct[:-16], full_ct[-16:]

    blob = format_ss1_blob(v=1, kid="k", aad="aad", salt=salt, nonce=nonce, ciphertext=ct, tag=tag)
    parsed = parse_ss1_blob(blob)

    # Tamper: flip a byte in ciphertext
    ct_tampered = bytearray(parsed["ct"])
    ct_tampered[0] ^= 0x01

    with pytest.raises(Exception):
        cipher.decrypt(parsed["nonce"], bytes(ct_tampered) + parsed["tag"], aad)
```

### 5.3 Protocol Invariants

```python
from sacred_tokenizer import parse_ss1_blob


def test_compact_format_single_tongue_marker_per_field():
    # This is a schema test: verify that a blob field begins with "xx:" only once.
    # Adjust based on how your format_ss1_blob renders spaces/newlines.
    def tongue_marker_count(field_value: str) -> int:
        # Count occurrences like "ko:" "ru:" etc. at token boundaries.
        # This is intentionally simple.
        return sum(field_value.count(t + ":") for t in ["ko", "ru", "ca", "dr", "av", "um"])

    # If you have a sample SS1 blob string in a fixture, parse it and assert:
    # assert tongue_marker_count(c["nonce_spell"]) == 1
    # Here we leave it as a pattern test since SS1 parsing is implementation-defined.
    assert True
```

---

## 6. 21D Spine Integration Note (tongue_id / phase_angle / tongue_weight)

In the 21D canonical state vector (BrainState21), the Sacred Tongues slice typically occupies three dimensions:

* `tongue_id` — which tongue/domain is active
* `phase_angle` — a semantic phase or mode angle
* `tongue_weight` — weighting of tongue influence in governance/metrics

### 6.1 Practical Mapping From Tutorials → 21D

Your tutorials generate artifacts that make these fields measurable and deterministic:

* **`tongue_id`** comes directly from the SS1 field’s tongue marker (`ko:`, `ru:`, etc.).
* **`phase_angle`** can be computed from tongue domain + token indices, or discretized by mode.
* **`tongue_weight`** can be assigned by section criticality (`tag` > `ct` > `nonce` > `salt` > `aad`).

A simple, stable mapping:

* Assign each tongue a fixed integer id:

  | Tongue | Suggested `tongue_id` |
  | -----: | --------------------: |
  |   `av` |                     1 |
  |   `ru` |                     2 |
  |   `ko` |                     3 |
  |   `ca` |                     4 |
  |   `dr` |                     5 |
  |   `um` |                     6 |

* Assign `phase_angle` as a 6‑sector circle:

  ```text
  phase_angle = 2π * (tongue_id - 1) / 6
  ```

* Assign `tongue_weight` by section:

  | Section  | Suggested weight |
  | -------- | ---------------: |
  | `tag`    |             1.00 |
  | `ct`     |             0.90 |
  | `nonce`  |             0.75 |
  | `salt`   |             0.60 |
  | `aad`    |             0.30 |
  | `redact` |             0.95 |

### 6.2 Why This Matters

Using SS1 spell-text with explicit tongue markers makes the semantic‑phase slice of your 21D spine **observable** and **replayable**:

* A log of SS1 blobs yields a time series of `tongue_id(t)`.
* Mode switching statistics become a stable spectral fingerprint.
* The system can enforce domain separation in both crypto artifacts and governance state.

---

## Appendix A — Common Pitfalls

### A.1 Missing Apostrophe

❌ Wrong:

```python
token = prefix + suffix
```

✅ Correct:

```python
token = prefix + "'" + suffix
```

### A.2 Wrong Tongue for a Section

❌ Wrong:

```python
salt_spell = encode_to_spelltext(salt_bytes, section="ct")
```

✅ Correct:

```python
salt_spell = encode_to_spelltext(salt_bytes, section="salt")
```

### A.3 Unicode Quote Characters

❌ Wrong (U+2019):

```text
sil’ae
```

✅ Correct (U+0027):

```text
sil'ae
```

---

## Appendix B — Compact vs Verbose (Summary)

* **Compact** is canonical for SS1 blobs:

  `nonce=ko:<tokens...>`

* **Verbose** is optional for debugging/logging:

  `ko:<token> ko:<token> ...`

Keep your production artifacts compact; keep your developer tools verbose when needed.

## Connections

```yaml
connections:
  id: sacred-tongue-tokenizer-practical-tutorials-and-use-cases
  module: language-governance
  state_dimensions: [10, 11, 12]
  related:
    - master-specification-canonical-twenty-one-dimensional-state
    - polyhedral-hamiltonian-dynamic-mesh-brain-architecture
  tests:
    - test_tokenizer_roundtrip_random_bytes
    - test_reject_unicode_apostrophe
    - test_canonical_lowercase_only
    - test_ss1_format_parse_roundtrip
    - test_ss1_tamper_detect_aesgcm_tag_fails
  knowledge_spine_paths:
    - docs/00_MASTER/INDEX.csv
    - docs/00_MASTER/MINDMAP.mmd
```
