"""
SpiralSeal SS1 Convenience Functions

One-shot seal/unseal operations for simple use cases.
"""

from typing import Optional


def seal(plaintext: bytes, master_secret: bytes, aad: str = "",
         kid: Optional[str] = None) -> str:
    """Seal (encrypt) data in one shot.

    Args:
        plaintext: Data to encrypt
        master_secret: 32-byte master secret
        aad: Associated authenticated data string
        kid: Key ID (auto-generated if not provided)

    Returns:
        SS1 formatted string
    """
    from .spiral_seal import SpiralSeal

    seal_instance = SpiralSeal(
        master_key=master_secret,
        key_id=kid.encode() if kid else None
    )
    result = seal_instance.seal(plaintext, aad=aad.encode() if aad else None)
    return result.to_ss1_string()


def unseal(blob: str, master_secret: bytes, aad: str = "") -> bytes:
    """Unseal (decrypt) data in one shot.

    Args:
        blob: SS1 formatted string
        master_secret: 32-byte master secret
        aad: Associated authenticated data string (must match seal)

    Returns:
        Decrypted plaintext bytes

    Raises:
        ValueError: If authentication fails or AAD mismatch
    """
    from .spiral_seal import SpiralSeal
    from .sacred_tongues import parse_ss1_blob

    # Parse the blob to extract AAD
    parsed = parse_ss1_blob(blob)

    # Check AAD matches
    if parsed.get("aad", "") != aad:
        raise ValueError(f"AAD mismatch: expected '{aad}', got '{parsed.get('aad', '')}'")

    seal_instance = SpiralSeal(master_key=master_secret)
    return seal_instance.unseal(
        salt=parsed["salt"],
        nonce=parsed["nonce"],
        ciphertext=parsed["ct"],
        tag=parsed["tag"],
        aad=aad.encode() if aad else b""
    )
