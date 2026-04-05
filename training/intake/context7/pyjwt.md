# PyJWT

PyJWT is a Python library for encoding and decoding JSON Web Tokens (JWT). It supports HMAC, RSA, ECDSA, and EdDSA algorithms for token signing and verification.

## Decode and Verify

Decode a JWT and verify its signature. Always specify the `algorithms` parameter to prevent algorithm confusion attacks:

```python
import jwt

# Decode and verify with HMAC
payload = jwt.decode(
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U",
    "secret",
    algorithms=["HS256"]
)
print(payload)  # {'sub': '1234567890'}

# Decode without verification (UNSAFE - only for inspection)
payload = jwt.decode(
    token,
    options={"verify_signature": False}
)

# Decode with audience verification
payload = jwt.decode(
    token,
    "secret",
    algorithms=["HS256"],
    audience="urn:my-api"
)

# Decode with issuer verification
payload = jwt.decode(
    token,
    "secret",
    algorithms=["HS256"],
    issuer="urn:my-issuer"
)

# Decode with required claims
payload = jwt.decode(
    token,
    "secret",
    algorithms=["HS256"],
    options={"require": ["exp", "iss", "sub"]}
)
```

## Encode with Datetime Claims

Create tokens with standard registered claims including expiration:

```python
import jwt
from datetime import datetime, timedelta, timezone

# Encode with expiration
payload = {
    "sub": "1234567890",
    "name": "John Doe",
    "iat": datetime.now(tz=timezone.utc),
    "exp": datetime.now(tz=timezone.utc) + timedelta(hours=1),
    "nbf": datetime.now(tz=timezone.utc),
    "iss": "my-auth-server",
    "aud": "my-api"
}

token = jwt.encode(payload, "secret", algorithm="HS256")
print(token)

# Encode with custom headers
token = jwt.encode(
    payload,
    "secret",
    algorithm="HS256",
    headers={"kid": "key-id-001"}
)

# Token will raise ExpiredSignatureError if decoded after expiration
try:
    decoded = jwt.decode(token, "secret", algorithms=["HS256"])
except jwt.ExpiredSignatureError:
    print("Token has expired")
except jwt.InvalidTokenError as e:
    print(f"Invalid token: {e}")
```

## RSA Encoding and Decoding

Use RSA key pairs for asymmetric token signing:

```python
import jwt

# Load RSA keys
with open("private_key.pem", "r") as f:
    private_key = f.read()

with open("public_key.pem", "r") as f:
    public_key = f.read()

# Encode with RSA private key
token = jwt.encode(
    {"sub": "user123", "role": "admin"},
    private_key,
    algorithm="RS256"
)

# Decode with RSA public key
payload = jwt.decode(
    token,
    public_key,
    algorithms=["RS256"]
)
print(payload)  # {'sub': 'user123', 'role': 'admin'}

# Using cryptography library key objects directly
from cryptography.hazmat.primitives import serialization

with open("private_key.pem", "rb") as f:
    private_key_obj = serialization.load_pem_private_key(f.read(), password=None)

with open("public_key.pem", "rb") as f:
    public_key_obj = serialization.load_pem_public_key(f.read())

token = jwt.encode({"sub": "user123"}, private_key_obj, algorithm="RS256")
payload = jwt.decode(token, public_key_obj, algorithms=["RS256"])
```

## API Reference: jwt.decode

```python
jwt.decode(
    jwt,                    # str or bytes - The JWT to decode
    key="",                 # str or key object - Verification key
    algorithms=None,        # list[str] - Allowed algorithms (REQUIRED for security)
    options=None,           # dict - Decoding options
    audience=None,          # str or list - Expected audience claim
    issuer=None,            # str - Expected issuer claim
    leeway=0,               # int or timedelta - Clock skew tolerance in seconds
    required=None,          # list[str] - Claims that must be present (deprecated, use options)
)
```

Options dictionary keys:

```python
options = {
    "verify_signature": True,    # Verify the token signature
    "verify_exp": True,          # Verify expiration claim
    "verify_nbf": True,          # Verify not-before claim
    "verify_iat": True,          # Verify issued-at claim
    "verify_aud": True,          # Verify audience claim
    "verify_iss": True,          # Verify issuer claim
    "require": ["exp", "sub"],   # List of required claims
}
```

Common exceptions:

```python
import jwt

# jwt.ExpiredSignatureError - Token has expired (exp claim)
# jwt.ImmatureSignatureError - Token not yet valid (nbf claim)
# jwt.InvalidAudienceError - Audience mismatch
# jwt.InvalidIssuerError - Issuer mismatch
# jwt.InvalidSignatureError - Signature verification failed
# jwt.DecodeError - Token cannot be decoded
# jwt.InvalidTokenError - Base class for all token errors
# jwt.MissingRequiredClaimError - Required claim not present
```
