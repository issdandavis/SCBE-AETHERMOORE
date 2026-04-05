# cryptography (Python)

`cryptography` is a comprehensive Python package that provides cryptographic recipes and primitives for Python developers. It serves as a "cryptographic standard library" supporting Python 3.8+ and PyPy3 7.3.11+. The library includes both high-level recipes for common use cases (like Fernet for symmetric encryption) and low-level interfaces to cryptographic algorithms including symmetric ciphers, asymmetric encryption, message digests, key derivation functions, and X.509 certificate handling.

The library is built on top of OpenSSL (3.0.0+ required) with Rust bindings for performance-critical operations. It provides a safe, well-audited API that handles cryptographic best practices automatically while still allowing advanced users access to lower-level primitives through the "hazmat" (hazardous materials) module. Key features include AES encryption, RSA/EC key operations, SHA-2/SHA-3 hashing, PBKDF2/Scrypt/Argon2 key derivation, X.509 certificate creation and verification, and PKCS#12 handling.

## Encrypt and Decrypt Data with Fernet

Provides functionalities for encrypting and decrypting data using symmetric encryption. This is crucial for securing data at rest and in transit. It requires a key for both operations.

```python
from cryptography.fernet import Fernet

def encrypt_data(key, data):
    f = Fernet(key)
    encrypted_data = f.encrypt(data.encode())
    return encrypted_data

def decrypt_data(key, encrypted_data):
    f = Fernet(key)
    decrypted_data = f.decrypt(encrypted_data)
    return decrypted_data.decode()

# Example usage:
key = Fernet.generate_key()
original_data = "This is a secret message."

encrypted = encrypt_data(key, original_data)
print(f"Encrypted: {encrypted}")

decrypted = decrypt_data(key, encrypted)
print(f"Decrypted: {decrypted}")
```

## Symmetric Encryption with Fernet

Demonstrates how to use the Fernet symmetric encryption recipe from the cryptography library. This includes generating a key, initializing the Fernet cipher, encrypting a message, and decrypting it. The key must be kept secure.

```python
from cryptography.fernet import Fernet

key = Fernet.generate_key()
f = Fernet(key)

message = b"A really secret message. Not for prying eyes."
token = f.encrypt(message)

decrypted_message = f.decrypt(token)
print(decrypted_message)
```

## RSA Key Management and Encryption

Generate RSA key pairs, perform encryption with OAEP padding, and handle key serialization.

```python
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes

# Generate RSA key pair
private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()

# Encrypt with public key
message = b"Secret data for RSA encryption"
ciphertext = public_key.encrypt(
    message,
    padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None
    )
)

# Decrypt with private key
plaintext = private_key.decrypt(
    ciphertext,
    padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None
    )
)
print(plaintext)
```

## Public-Key Cryptography (Asymmetric)

Cryptographic operations where encryption and decryption use different keys. There are separate encryption and decryption keys. Typically encryption is performed using a public key, and it can then be decrypted using a private key. Asymmetric cryptography can also be used to create signatures, which can be generated with a private key and verified with a public key.
