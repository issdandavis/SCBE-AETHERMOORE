# Sacred Tongue Tokenizer - Practical Tutorials and Use Cases

Educational Materials Version: 1.0
Last Updated: January 2026
Difficulty: Beginner to Advanced

---

## Tutorial 1: Your First Sacred Tongue Encoding

### Step 1: Understand the Problem

You have a 16-byte encryption nonce:

```
Raw bytes: 0x3c 0x5a 0x7f 0x2e 0x91 0xb4 0x68 0x42 0xd3 0x1e 0xa7 0xc9 0x4b 0x6f 0x88 0x15
```

Goal: store this in a way that is machine-readable, human-verifiable, phonetically elegant, and deterministic.

Solution: Sacred Tongue encoding using Kor'aelin (nonce tongue).

### Step 2: Manual Encoding (Learning)

Encode the first byte: 0x3c

```
0x3c in binary: 0011 1100
High nibble: 0011 = 3
Low nibble: 1100 = 12

Kor'aelin prefixes[3] = "zar"
Kor'aelin suffixes[12] = "un"
Result: "zar'un"
```

Encode the second byte: 0x5a

```
0x5a in binary: 0101 1010
High nibble: 0101 = 5
Low nibble: 1010 = 10

Kor'aelin prefixes[5] = "thul"
Kor'aelin suffixes[10] = "ir"
Result: "thul'ir"
```

Complete encoding (all 16 bytes):

```
Byte 0: 0x3c -> zar'un
Byte 1: 0x5a -> thul'ir
Byte 2: 0x7f -> ael'esh
Byte 3: 0x2e -> vel'en
Byte 4: 0x91 -> med'il
Byte 5: 0xb4 -> gal'or
Byte 6: 0x68 -> keth'un
Byte 7: 0x42 -> joy'ar
Byte 8: 0xd3 -> nex'ia
Byte 9: 0x1e -> ra'en
Byte 10: 0xa7 -> med'oth
Byte 11: 0xc9 -> nav'il
Byte 12: 0x4b -> joy'eth
Byte 13: 0x6f -> keth'oth
Byte 14: 0x88 -> ael'eth
Byte 15: 0x15 -> ra'en

Spell-text nonce:
zar'un thul'ir ael'esh vel'en med'il gal'or keth'un joy'ar
nex'ia ra'en med'oth nav'il joy'eth keth'oth ael'eth ra'en
```

### Step 3: Programmatic Encoding

```python
from sacred_tokenizer import SacredTongueTokenizer

# Create tokenizer for nonce (Kor'aelin)
tokenizer = SacredTongueTokenizer('ko')

# Raw nonce bytes
nonce_bytes = bytes([
    0x3c, 0x5a, 0x7f, 0x2e, 0x91, 0xb4, 0x68, 0x42,
    0xd3, 0x1e, 0xa7, 0xc9, 0x4b, 0x6f, 0x88, 0x15
])

# Encode to spell-text
spell = tokenizer.encode(nonce_bytes)
print(spell)
# Output: ko:zar'un ko:thul'ir ko:ael'esh ko:vel'en ko:med'il ko:gal'or ko:keth'un ko:joy'ar ko:nex'ia ko:ra'en ko:med'oth ko:nav'il ko:joy'eth ko:keth'oth ko:ael'eth ko:ra'en
```

### Step 4: Verification

```python
recovered_bytes = tokenizer.decode(spell)
assert recovered_bytes == nonce_bytes
print("Round-trip successful")
```

---

## Tutorial 2: Building a Complete SS1 Encrypted Backup

```python
import os
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from sacred_tokenizer import format_ss1_blob, parse_ss1_blob

class BackupEncryptor:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.kdf_iterations = 100_000

    def encrypt_backup(self, plaintext: bytes, password: str) -> str:
        salt = os.urandom(16)
        nonce = os.urandom(12)
        key = self._derive_key(password, salt)

        cipher = AESGCM(key)
        aad = self.user_id.encode()
        ciphertext = cipher.encrypt(nonce, plaintext, aad)

        auth_tag = ciphertext[-16:]
        ciphertext_body = ciphertext[:-16]

        ss1_blob = format_ss1_blob(
            kid=f"{self.user_id}-backup-{int(time.time())}",
            aad=aad.decode(),
            salt=salt,
            nonce=nonce,
            ciphertext=ciphertext_body,
            tag=auth_tag
        )
        return ss1_blob

    def decrypt_backup(self, ss1_blob: str, password: str) -> bytes:
        components = parse_ss1_blob(ss1_blob)
        salt = components['salt']
        nonce = components['nonce']
        ciphertext_body = components['ct']
        auth_tag = components['tag']
        aad = components['aad'].encode()

        key = self._derive_key(password, salt)
        ciphertext = ciphertext_body + auth_tag

        cipher = AESGCM(key)
        return cipher.decrypt(nonce, ciphertext, aad)

    def _derive_key(self, password: str, salt: bytes) -> bytes:
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=self.kdf_iterations,
        )
        return kdf.derive(password.encode())
```

Expected output example:

```
SS1|kid=alice-2026-backup-1705433400|aad=alice-2026|salt=ru:bront'ak drath'eth bip'a bop'e klik'i loopa'ta ifta'na thena'sa|nonce=ko:vel'an kor'ae thul'ir ael'eth|ct=ca:bip'a bop'e klik'i loopa'ta ifta'na thena'sa elsa'ta spira'na rythm'sa quirk'ra fizz'lo gear'mi pop'ki zip'zi|tag=dr:anvil'a tharn'e mek'i grond'o draum'u
```

---

## Tutorial 3: Multi-Party Key Recovery

```python
from threshold_crypto import split_secret, recover_secret
from sacred_tokenizer import SacredTongueTokenizer, TONGUES, encode_to_spelltext

class SecretSharingRecovery:
    def setup_shares(self, master_secret: bytes, num_shares: int, threshold: int):
        shares = split_secret(secret=master_secret, num_shares=num_shares, threshold=threshold)
        encoded_shares = {}
        tongues = ['ko', 'ru', 'ca']

        for i, (share_id, share_bytes) in enumerate(shares):
            tongue_code = tongues[i % len(tongues)]
            spell = encode_to_spelltext(share_bytes, section='salt')
            encoded_shares[f'party_{i+1}'] = {
                'share_id': share_id,
                'spell_text': spell,
                'tongue': tongue_code
            }
        return encoded_shares

    def verify_share_integrity(self, spell_text: str, tongue_code: str) -> bool:
        try:
            tokenizer = SacredTongueTokenizer(tongue_code)
            _ = tokenizer.decode(spell_text)
            return True
        except Exception:
            return False

    def recover_secret(self, party_shares: dict) -> bytes:
        shares = []
        for party_id, spell_text in party_shares.items():
            tongue_code = self._detect_tongue(spell_text)
            tokenizer = SacredTongueTokenizer(tongue_code)
            share_bytes = tokenizer.decode(spell_text)
            share_idx = int(party_id.split('_')[1]) - 1
            shares.append((share_idx, share_bytes))
        return recover_secret(shares)

    def _detect_tongue(self, spell_text: str) -> str:
        for code in TONGUES.keys():
            try:
                tokenizer = SacredTongueTokenizer(code)
                _ = tokenizer.decode(spell_text)
                return code
            except Exception:
                continue
        raise ValueError("Could not determine tongue for spell-text")
```

---

## Tutorial 4: Tongue-Specific Cryptographic Protocols

```python
from sacred_tokenizer import SacredTongueTokenizer, encode_to_spelltext, SECTION_TONGUES

class MultiPhaseCryptographicProtocol:
    def phase_1_initialization(self, protocol_name: str, parties: list) -> dict:
        init_data = {
            'protocol': protocol_name,
            'parties': ','.join(parties),
            'timestamp': str(int(time.time())),
            'version': '1.0'
        }
        init_bytes = json.dumps(init_data).encode()
        init_spell = encode_to_spelltext(init_bytes, 'aad')
        return {'phase': 'initialization', 'tongue': 'av', 'data': init_spell}

    def phase_2_key_exchange(self, ephemeral_public_key: bytes) -> dict:
        key_spell = encode_to_spelltext(ephemeral_public_key, 'salt')
        return {'phase': 'key_exchange', 'tongue': 'ru', 'data': key_spell}

    def phase_3_message_flow(self, nonce: bytes, message_hash: bytes) -> dict:
        flow_data = nonce + message_hash
        flow_spell = encode_to_spelltext(flow_data, 'nonce')
        return {'phase': 'message_flow', 'tongue': 'ko', 'data': flow_spell}

    def phase_4_encryption(self, ciphertext: bytes) -> dict:
        ct_spell = encode_to_spelltext(ciphertext, 'ct')
        return {'phase': 'encryption', 'tongue': 'ca', 'data': ct_spell}

    def phase_5_authentication(self, auth_tag: bytes, signature: bytes) -> dict:
        auth_data = auth_tag + signature
        auth_spell = encode_to_spelltext(auth_data, 'tag')
        return {'phase': 'authentication', 'tongue': 'dr', 'data': auth_spell}

    def phase_6_redaction(self, ephemeral_key: bytes, session_material: bytes):
        redaction_directive = ephemeral_key + session_material
        redact_spell = encode_to_spelltext(redaction_directive, 'redact')
        return {'phase': 'redaction', 'tongue': 'um', 'data': redact_spell}
```

---

## Common Pitfalls

1) Missing apostrophe:
- Wrong: prefix + suffix -> "silae"
- Right: prefix + "'" + suffix -> "sil'ae"

2) Wrong tongue for section:
- Wrong: encode_to_spelltext(salt, 'ca')
- Right: encode_to_spelltext(salt, 'salt')

3) Case sensitivity:
- Use lowercase tokens only.

4) Character encoding:
- Use ASCII apostrophe (U+0027) not a curly quote.
