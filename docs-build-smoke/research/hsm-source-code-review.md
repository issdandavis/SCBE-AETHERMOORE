# Open Source HSM Source Code Review

**Date**: 2026-03-24
**Repos forked**: wolfHSM, NetHSM, Pico HSM
**Purpose**: Understand HSM internals for SCBE PQC integration

---

## 1. wolfHSM (wolfSSL) — Pure C, GPL-3.0

**Repo**: github.com/issdandavis/wolfHSM

### Architecture
- Strict **client-server RPC model** for automotive HSMs
- Server runs in trusted enclave, client in application domain
- wolfCrypt callback interception transparently routes crypto to HSM
- Transport abstraction: shared memory, TCP, TLS

### Crypto Primitives
| Category | Algorithms |
|----------|-----------|
| Symmetric | AES-ECB/CBC/CTR/GCM |
| MAC | CMAC, HMAC |
| Hash | SHA-256, SHA-512 |
| Asymmetric | RSA, ECC (P-256/384/521), Curve25519, Ed25519 |
| **Post-Quantum** | **ML-DSA / Dilithium** (keygen, sign, verify) |
| KDF | HKDF, CMAC-KDF |

### Key Storage (3 tiers)
1. **RAM Cache**: 8 regular + 1 big slot, LRU eviction, per-client isolation
2. **NVM**: Dual-partition atomic writes, crash recovery
3. **Key IDs**: 16-bit `[TYPE:4][USER:4][ID:8]` with per-key policy flags

### SCBE Takeaways
- wolfHSM **already has ML-DSA** — validates SCBE's Dilithium3 -> ML-DSA-65 migration
- Per-key usage flags (ENCRYPT/DECRYPT/SIGN/VERIFY/WRAP) — SCBE should adopt
- Crypto callback interception pattern — route all ops through governance layer
- No ML-KEM yet — SCBE is ahead here

---

## 2. NetHSM (Nitrokey) — OCaml/MirageOS, Open Source

**Repo**: github.com/issdandavis/nethsm

### Architecture
- MirageOS unikernel — single-purpose OS with minimal attack surface
- Muen separation kernel (Ada/SPARK, formally verified) enforces hardware isolation
- 3 isolated subjects: S-Net-External (network bridge), S-Platform (TPM/disk), S-Keyfender (crypto core)

### Crypto
- RSA, EC (P-256/384/521/secp256k1/Brainpool), Ed25519, AES-CBC
- No PQC at all
- AES-256-GCM for all at-rest encryption
- Fortuna CSPRNG with 32 pools

### Key Hierarchy (3 layers)
1. **Device Key** — TPM-sealed, hardware-bound
2. **Domain Key** — Encrypts all stores, two unlock modes (attended/unattended)
3. **Per-value encryption** — Individual AES-256-GCM per key-value pair

### Access Control (5 roles)
- **Administrator**: Create/import keys, CANNOT use them
- **Operator**: Use keys (sign/decrypt), CANNOT create/delete
- **Metrics/Backup/Public**: Read-only

### SCBE Takeaways
- Admin can't use keys, Operator can't create them — separation of concerns
- Tag-based key restrictions map to Sacred Tongues (6 tags = 6 tongues)
- Namespace multi-tenancy for M5 Mesh Foundry customers
- No PQC — SCBE + NetHSM bridge could add PQC envelope
- Verified boot chain with RSA-4096 signature

---

## 3. Pico HSM — C/mbedTLS, AGPL-3.0, $4-8 hardware

**Repo**: github.com/issdandavis/pico-hsm

### Hardware Targets
- Raspberry Pi Pico (RP2040) — $4
- Raspberry Pi Pico 2 (RP2350) — $8, adds OTP + secure boot
- ESP32-S3 — adds flash encryption

### Crypto (most complete of the three)
- RSA up to 4096-bit, ECDSA (all standard curves), EdDSA (Ed25519, Ed448)
- ECDH (X25519, X448), AES all modes including GCM/CCM
- ChaCha20-Poly1305 AEAD
- BIP32/SLIP10 HD key derivation (crypto wallet compatible)
- HKDF, PBKDF2

### Key Protection
1. **MKEK**: Master key in OTP fuses (RP2350/ESP32-S3) — hardware non-extractable
2. **DKEK**: Device key with n-of-m Shamir threshold sharing
3. **PIN**: Double-salted, never stored plaintext, retry lockout

### Physical Security
- **BOOTSEL button = press-to-confirm** for every private key operation
- Keys in RAM only during operations, then zeroed
- Secure boot prevents unauthorized firmware
- Secure lock disables debug access permanently

### PKCS#11 Compliance
- Full PKCS#11 via USB CCID smart card interface
- Works with OpenSC, pkcs11-tool, standard enterprise tooling
- Compatible with Nitrokey HSM ecosystem

### SCBE Integration Path
1. Use Pico HSM (RP2350) as **L13 governance signing key** root-of-trust
2. HD key derivation generates per-tongue (KO/AV/RU/CA/UM/DR) signing keys
3. Press-to-confirm maps to SCBE ESCALATE tier
4. PKCS#11 bridge via OpenSC — no custom driver needed
5. $8 hardware root > $0 software-only security

### Gaps
- No PQC on-device — ML-KEM/ML-DSA must stay in SCBE software layer
- RSA-4096 signing is 15 seconds — use Ed25519 for speed
- RP2040 (original) lacks OTP — use RP2350 or ESP32-S3 only

---

## Comparison Matrix

| Feature | wolfHSM | NetHSM | Pico HSM | SCBE |
|---------|---------|--------|----------|------|
| ML-DSA (Dilithium) | Yes | No | No | Yes |
| ML-KEM (Kyber) | No | No | No | Yes |
| AES-256-GCM | Yes | Yes | Yes | Yes |
| Hardware key isolation | Via MCU ports | Muen/TPM | OTP fuses | Software only |
| PKCS#11 | No (custom RPC) | REST API | Yes | No |
| Governance/risk scoring | No | Binary RBAC | No | 14-layer pipeline |
| Cost | Automotive MCU | $1000+ appliance | $4-8 | Free |
| Press-to-confirm | No | No | Yes | N/A |
| BIP32 HD keys | No | No | Yes | No |
| Multi-tenant | No | Namespaces | Key domains | Planned |

## Conclusion

SCBE's PQC software stack is the most advanced of the four in terms of post-quantum crypto (ML-KEM-768 + ML-DSA-65 + AES-256-GCM). What it lacks vs these HSMs:
1. **Hardware key isolation** — Pico HSM at $8 closes this gap
2. **Per-key usage policies** — wolfHSM's pattern should be adopted
3. **Role separation** — NetHSM's "admin can't use, operator can't create" principle
4. **Physical attestation** — Pico's press-to-confirm for ESCALATE tier

The recommended integration: **Pico HSM (RP2350)** as hardware root for Sacred Vault MKEK, with SCBE providing the PQC envelope, governance pipeline, and risk scoring that none of the HSMs implement.
