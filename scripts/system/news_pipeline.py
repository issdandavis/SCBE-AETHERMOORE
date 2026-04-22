#!/usr/bin/env python3
"""
SCBE News Pipeline — Post-Quantum Transport & Training Data Generator
=====================================================================
Reads docs/research-feed.json and runs each item through the full SCBE pipeline:

  Stage 0 — RAW       : Original news item as-is
  Stage 1 — GEOTAGGED : Geographic GeoSeal stamp (lat/lon/country + phase seal)
  Stage 2 — TOKENIZED : Sacred Tongues encode+decode (all 6 tongues, both directions)
  Stage 3 — HASHED    : SHA-256 of each stage + HMAC chain binding all three
  Stage 4 — EGGED     : Sacred Egg envelope (shell=hash, yolk=payload, ritual marker)
  Stage 5 — ENCRYPTED : AES-256-GCM over egg (ML-KEM-768 when liboqs available)
  Stage 6 — SIGNED    : HMAC-SHA256 transport packet (ML-DSA-65 when available)

Every stage transition yields one SFT training pair.
Output destinations:
  training-data/news-pipeline/records/YYYY-MM-DD.jsonl  — full per-item records
  training-data/news-pipeline/sft/YYYY-MM-DD.jsonl      — training pairs (JSONL)
  docs/research-pipeline.json                           — run summary (public)
  docs/research-pipeline.json                           — public-facing summary

Usage:
  python scripts/system/news_pipeline.py
  SCBE_FORCE_SKIP_LIBOQS=1 python scripts/system/news_pipeline.py
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import math
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ──────────────────────────────────────────────────────────────────────────────
# Paths
# ──────────────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[2]
FEED_PATH = REPO_ROOT / "docs" / "research-feed.json"
PIPELINE_DIR = REPO_ROOT / "training-data" / "news-pipeline"
RECORDS_DIR = PIPELINE_DIR / "records"
SFT_DIR = PIPELINE_DIR / "sft"
SUMMARY_PATH = REPO_ROOT / "docs" / "research-pipeline.json"

for _d in (RECORDS_DIR, SFT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────────────────────────────────────
# Constants — mirror geoseal_cli.py / sacred_tongues.py
# ──────────────────────────────────────────────────────────────────────────────

PHI = (1 + 5**0.5) / 2

TONGUE_PHI_WEIGHTS: dict[str, float] = {
    "KO": 1.000,
    "AV": 1.618,
    "RU": 2.618,
    "CA": 4.236,
    "UM": 6.854,
    "DR": 11.090,
}

TONGUE_PHASES: dict[str, float] = {
    "KO": 0.0,
    "AV": math.pi / 3,
    "RU": 2 * math.pi / 3,
    "CA": math.pi,
    "UM": 4 * math.pi / 3,
    "DR": 5 * math.pi / 3,
}

TONGUE_NAMES: dict[str, str] = {
    "KO": "Kor'aelin",
    "AV": "Avali",
    "RU": "Runethic",
    "CA": "Cassisivadan",
    "UM": "Umbroth",
    "DR": "Draumric",
}

# Canonical tongue for each news source (which tongue "speaks" this data)
SOURCE_TONGUE: dict[str, str] = {
    "hn": "KO",       # Kor'aelin — precise/flow (Python/tech)
    "arxiv": "CA",    # Cassisivadan — symbolic/math
    "reddit": "AV",   # Avali — reactive/social
    "darpa": "RU",    # Runethic — ethical/structured
    "sam": "RU",      # Runethic — governance
    "bbc": "AV",      # Avali — broadcast/context
    "aje": "UM",      # Umbroth — veiled/multilingual
    "dw": "RU",       # Runethic — structured
    "f24": "AV",      # Avali — broadcast
    "nhk": "UM",      # Umbroth — Japanese-adjacent
    "toi": "AV",      # Avali — broadcast
    "cgtn": "CA",     # Cassisivadan — state/systematic
    "gdelt": "DR",    # Draumric — archival structure
    "guardian": "KO", # Kor'aelin — precise reporting
    "newsdata": "AV", # Avali
    "worldnews": "DR", # Draumric
}

# Geographic coordinates (lat, lon, ISO-3166 alpha-2)
SOURCE_COORDS: dict[str, tuple[float, float, str]] = {
    "bbc":      (51.509, -0.118,  "GB"),
    "aje":      (25.285,  51.531, "QA"),
    "dw":       (52.520,  13.405, "DE"),
    "f24":      (48.864,   2.349, "FR"),
    "nhk":      (35.689, 139.692, "JP"),
    "toi":      (19.076,  72.878, "IN"),
    "cgtn":     (39.909, 116.397, "CN"),
    "gdelt":    (0.000,    0.000, "XX"),  # global
    "hn":       (37.387, -122.060, "US"),
    "arxiv":    (40.730,  -73.935, "US"),
    "reddit":   (37.535, -121.960, "US"),
    "darpa":    (38.895,  -77.037, "US"),
    "sam":      (38.895,  -77.037, "US"),
    "guardian": (51.533,  -0.122,  "GB"),
    "newsdata": (37.387, -122.060, "US"),
    "worldnews": (0.000,   0.000,  "XX"),
}

REGION_COORDS: dict[str, tuple[float, float, str]] = {
    "us":     (38.895,  -77.037, "US"),
    "eu":     (50.110,    8.682, "DE"),
    "asia":   (35.689,  139.692, "JP"),
    "me":     (25.204,   55.270, "AE"),
    "africa": (-1.286,   36.817, "KE"),
    "global": (0.000,     0.000, "XX"),
}

# Gnews-variant → region coords
GNEWS_COORDS: dict[str, tuple[float, float, str]] = {
    "gnews-eu":    (50.110,   8.682, "DE"),
    "gnews-asia":  (35.689, 139.692, "JP"),
    "gnews-me":    (25.204,  55.270, "AE"),
    "gnews-af":    (-1.286,  36.817, "KE"),
    "gnews-latam": (-23.550, -46.633, "BR"),
    "gnews-jp":    (35.689, 139.692, "JP"),
}

# ──────────────────────────────────────────────────────────────────────────────
# Sacred Tongues tokenizer — try real import, fall back to inline minimal
# ──────────────────────────────────────────────────────────────────────────────

_TOKENIZER_SOURCE = "none"
try:
    _src_path = str(REPO_ROOT / "src")
    if _src_path not in sys.path:
        sys.path.insert(0, _src_path)
    from crypto.sacred_tongues import SacredTongueTokenizer  # type: ignore

    _TOKENIZER = SacredTongueTokenizer()
    _TOKENIZER_SOURCE = "src.crypto.sacred_tongues"
except Exception:
    _TOKENIZER = None  # type: ignore
    _TOKENIZER_SOURCE = "inline-fallback"

# ──────────────────────────────────────────────────────────────────────────────
# Semantic Atomic Braid — optional (requires numpy + src.symphonic.multipath)
# ──────────────────────────────────────────────────────────────────────────────

_BRAID_AVAILABLE = False
try:
    _repo_str = str(REPO_ROOT)
    if _repo_str not in sys.path:
        sys.path.insert(0, _repo_str)
    from src.spiralverse.semantic_atomic_braid import (  # type: ignore
        BraidAlignmentReport,
        evaluate_semantic_atomic_braid,
        sample_ops_for_tongue,
    )

    _BRAID_AVAILABLE = True
except Exception:
    _BRAID_AVAILABLE = False


def _braid_score(payload: bytes, tongue: str) -> dict | None:
    """Score semantic-atomic braid alignment for a payload.

    Returns dict with aligned score, all-tongue matrix, and worst-mismatch delta.
    Returns None when the braid module isn't available.
    """
    if not _BRAID_AVAILABLE:
        return None
    tongue_lc = tongue.lower()
    try:
        aligned = evaluate_semantic_atomic_braid(payload, tongue_lc, tongue_lc)
        matrix: dict[str, float] = {}
        for other in TONGUE_PHI_WEIGHTS:
            if other.lower() == tongue_lc:
                matrix[other] = round(aligned.overall_score, 6)
            else:
                try:
                    r = evaluate_semantic_atomic_braid(payload, tongue_lc, other.lower())
                    matrix[other] = round(r.overall_score, 6)
                except Exception:
                    matrix[other] = None  # type: ignore
        valid_others = [v for k, v in matrix.items() if k != tongue and v is not None]
        worst = round(min(valid_others), 6) if valid_others else None
        best_other = round(max(valid_others), 6) if valid_others else None
        return {
            "aligned_score": round(aligned.overall_score, 6),
            "aligned_components": {
                "semantic_alignment": round(aligned.semantic_alignment, 6),
                "roundtrip_ok": aligned.roundtrip_ok,
                "atomic_home_alignment": round(aligned.atomic_home_alignment, 6),
                "phi_underlay_alignment": round(aligned.phi_underlay_alignment, 6),
                "harmonic_fingerprint": round(aligned.harmonic_fingerprint, 6),
            },
            "tongue_matrix": matrix,
            "worst_mismatch_score": worst,
            "best_mismatch_score": best_other,
            "discriminatory_delta": round(aligned.overall_score - worst, 6) if worst is not None else None,
        }
    except Exception as exc:
        return {"error": str(exc)}


def tongue_encode(data: bytes, tongue: str = "KO") -> list[str]:
    """Encode bytes → Sacred Tongue tokens (bijective, deterministic)."""
    if _TOKENIZER is not None:
        return _TOKENIZER.encode_bytes(tongue.lower(), data)
    # Inline fallback: simple hex-pair tokens tagged by tongue
    prefix = tongue.lower()
    return [f"{prefix}'{b:02x}" for b in data]


def tongue_decode(tokens: list[str], tongue: str = "KO") -> bytes:
    """Decode Sacred Tongue tokens → bytes (round-trip verify)."""
    if _TOKENIZER is not None:
        return _TOKENIZER.decode_tokens(tongue.lower(), tokens)
    # Inline fallback: strip prefix and parse hex
    try:
        return bytes(int(t.split("'")[1], 16) for t in tokens)
    except Exception as exc:
        raise ValueError(f"Decode failed: {exc}") from exc


# ──────────────────────────────────────────────────────────────────────────────
# Crypto tier detection
# ──────────────────────────────────────────────────────────────────────────────

_FORCE_SKIP = os.getenv("SCBE_FORCE_SKIP_LIBOQS", "").strip().lower() in {"1", "true", "yes"}

def _load_oqs():
    """Attempt to import oqs without letting liboqs bootstrap abort importers."""
    if _FORCE_SKIP:
        return None
    try:
        import oqs  # type: ignore

        return oqs
    except BaseException:
        return None


_OQS_MODULE = _load_oqs()
LIBOQS_AVAILABLE = _OQS_MODULE is not None

CRYPTOGRAPHY_AVAILABLE = False
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # type: ignore  # noqa: F401
    from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey  # type: ignore  # noqa: F401

    CRYPTOGRAPHY_AVAILABLE = True
except Exception:
    CRYPTOGRAPHY_AVAILABLE = False

CRYPTO_TIER = "liboqs" if LIBOQS_AVAILABLE else ("cryptography" if CRYPTOGRAPHY_AVAILABLE else "hmac-only")


# ──────────────────────────────────────────────────────────────────────────────
# Stage 1 — GEOSEAL TAGGING
# ──────────────────────────────────────────────────────────────────────────────


def _resolve_coords(source: str, region: str) -> tuple[float, float, str]:
    """Resolve geographic coordinates from source or region."""
    if source in SOURCE_COORDS:
        return SOURCE_COORDS[source]
    if source in GNEWS_COORDS:
        return GNEWS_COORDS[source]
    return REGION_COORDS.get(region, (0.0, 0.0, "XX"))


def _geo_phase_seal(
    lat: float,
    lon: float,
    country: str,
    source: str,
    tongue: str,
    ts: float,
    payload_hash: str,
) -> str:
    """Geometry-bound GeoSeal — matches compute_seal() logic in geoseal_cli.py
    extended with geographic coordinates.

    Format: GEOSEAL:{tongue}:{lat:.4f}:{lon:.4f}:{country}:{ts:.3f}:{sha16}
    """
    phase = TONGUE_PHASES.get(tongue, 0.0)
    phi_w = TONGUE_PHI_WEIGHTS.get(tongue, 1.0)
    h = hashlib.sha256()
    for part in (
        source, tongue, country,
        f"{lat:.4f}", f"{lon:.4f}",
        f"{phase:.8f}", f"{phi_w:.6f}",
        f"{ts:.6f}", payload_hash,
    ):
        h.update(part.encode())
        h.update(b"|")
    digest = h.hexdigest()[:16]
    return f"GEOSEAL:{tongue}:{lat:.4f}:{lon:.4f}:{country}:{ts:.3f}:{digest}"


def stage_geotag(item: dict) -> dict:
    """Stage 1: stamp geographic GeoSeal onto the news item."""
    source = item.get("source", "hn")
    region = item.get("region", "global")
    tongue = SOURCE_TONGUE.get(source, "KO")
    lat, lon, country = _resolve_coords(source, region)
    ts = time.time()
    payload = item.get("title", "") + "|" + item.get("url", "")
    payload_hash = hashlib.sha256(payload.encode()).hexdigest()
    seal = _geo_phase_seal(lat, lon, country, source, tongue, ts, payload_hash)
    result = dict(item)
    result["geo"] = {
        "lat": lat,
        "lon": lon,
        "country": country,
        "region": region,
        "tongue": tongue,
        "tongue_name": TONGUE_NAMES[tongue],
        "phi_weight": TONGUE_PHI_WEIGHTS[tongue],
        "phase_rad": round(TONGUE_PHASES[tongue], 6),
        "seal": seal,
        "sealed_at": datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(),
    }
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Stage 2 — SACRED TONGUES TOKENIZATION (both directions, all 6 tongues)
# ──────────────────────────────────────────────────────────────────────────────


def stage_tokenize(geotagged: dict) -> dict:
    """Stage 2: encode title+URL through all 6 Sacred Tongues; verify round-trip."""
    payload = (geotagged.get("title", "") + " " + geotagged.get("url", "")).encode("utf-8")
    primary_tongue = geotagged.get("geo", {}).get("tongue", "KO")

    tongue_matrix: dict[str, Any] = {}
    all_roundtrip_ok = True

    for tongue in TONGUE_PHI_WEIGHTS:
        try:
            tokens = tongue_encode(payload, tongue)
            decoded = tongue_decode(tokens, tongue)
            roundtrip_ok = decoded == payload
            if not roundtrip_ok:
                all_roundtrip_ok = False
            tongue_matrix[tongue] = {
                "tongue_name": TONGUE_NAMES[tongue],
                "token_count": len(tokens),
                "byte_len": len(payload),
                "tokens_preview": tokens[:8],  # first 8 tokens only (training hint)
                "roundtrip_ok": roundtrip_ok,
                "phi_weight": TONGUE_PHI_WEIGHTS[tongue],
            }
        except Exception as exc:
            tongue_matrix[tongue] = {"error": str(exc), "roundtrip_ok": False}
            all_roundtrip_ok = False

    braid = _braid_score(payload, primary_tongue)

    result = dict(geotagged)
    result["tokenization"] = {
        "primary_tongue": primary_tongue,
        "payload_bytes": len(payload),
        "tongue_matrix": tongue_matrix,
        "all_roundtrip_ok": all_roundtrip_ok,
        "tokenizer_source": _TOKENIZER_SOURCE,
        # full token list for primary tongue (used downstream in training pairs)
        "primary_tokens": tongue_encode(payload, primary_tongue),
        # semantic-atomic braid alignment score (None when module unavailable)
        "braid": braid,
    }
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Stage 3 — CONTENT HASHING (SHA-256 + HMAC chain)
# ──────────────────────────────────────────────────────────────────────────────

_CHAIN_KEY = hashlib.sha256(b"SCBE-NEWS-PIPELINE-CHAIN-KEY-v1").digest()
_SCBE_NS = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")  # URL namespace (RFC 4122)


def _sha256(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


def _hmac256(key: bytes, data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode()
    return hmac.new(key, data, hashlib.sha256).hexdigest()


def stage_hash(raw: dict, geotagged: dict, tokenized: dict) -> dict:
    """Stage 3: SHA-256 each stage + HMAC chain binding all three."""
    raw_blob = json.dumps(raw, sort_keys=True, ensure_ascii=False)
    geo_blob = json.dumps(
        {k: v for k, v in geotagged.items() if k != "tokenization"},
        sort_keys=True,
        ensure_ascii=False,
    )
    tok_tokens = tokenized.get("tokenization", {}).get("primary_tokens", [])
    tok_blob = json.dumps(tok_tokens, ensure_ascii=False)

    h_raw = _sha256(raw_blob)
    h_geo = _sha256(geo_blob)
    h_tok = _sha256(tok_blob)
    # HMAC chain: each stage's HMAC is keyed off the previous stage's hash
    hmac_raw = _hmac256(_CHAIN_KEY, h_raw)
    hmac_geo = _hmac256(hmac_raw.encode(), h_geo)
    hmac_tok = _hmac256(hmac_geo.encode(), h_tok)
    chain_root = _sha256(hmac_tok)

    result = dict(tokenized)
    result["hashes"] = {
        "raw": h_raw,
        "geotagged": h_geo,
        "tokenized": h_tok,
        "hmac_raw": hmac_raw,
        "hmac_geo": hmac_geo,
        "hmac_tok": hmac_tok,
        "chain_root": chain_root,
    }
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Stage 4 — SACRED EGG CREATION
# ──────────────────────────────────────────────────────────────────────────────


def stage_egg(hashed: dict) -> dict:
    """Stage 4: create Sacred Egg envelope.

    Shell = chain_root hash (cryptographic binding to all prior stages).
    Yolk  = base64-encoded compressed payload (title + url + geo + tokenization).
    Egg ID = deterministic UUID v5 derived from shell hash.
    """
    chain_root = hashed.get("hashes", {}).get("chain_root", "")
    source = hashed.get("source", "hn")
    tongue = hashed.get("geo", {}).get("tongue", "KO")
    tongue_name = TONGUE_NAMES.get(tongue, tongue)

    # Yolk payload — the semantic content to preserve
    yolk_data = {
        "title": hashed.get("title", ""),
        "url": hashed.get("url", ""),
        "source": source,
        "region": hashed.get("region", "global"),
        "geo": hashed.get("geo", {}),
        "hashes": hashed.get("hashes", {}),
    }
    yolk_bytes = json.dumps(yolk_data, sort_keys=True, ensure_ascii=False).encode("utf-8")
    yolk_b64 = base64.b64encode(yolk_bytes).decode("ascii")

    # Egg ID = UUID v5 from SCBE namespace + chain_root
    egg_id = str(uuid.uuid5(_SCBE_NS, chain_root))

    phi_w = TONGUE_PHI_WEIGHTS.get(tongue, 1.0)
    # Egg cost — how expensive is this egg in phi-space?
    egg_cost = round(phi_w * math.log1p(len(yolk_bytes)) / math.log(PHI), 4)

    result = dict(hashed)
    result["egg"] = {
        "egg_id": egg_id,
        "shell": chain_root,                       # cryptographic shell
        "yolk": yolk_b64,                          # base64 payload
        "yolk_byte_len": len(yolk_bytes),
        "tongue": tongue,
        "tongue_name": tongue_name,
        "ritual": "news_ingest",
        "source": source,
        "egg_cost_phi": egg_cost,
        "hatched_at": None,                        # null until consumed
        "credits": 0,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
    }
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Stage 5 — PQC ENCRYPTION
# ──────────────────────────────────────────────────────────────────────────────


def _encrypt_aes_gcm(plaintext: bytes, key: bytes) -> tuple[str, str, str]:
    """AES-256-GCM encrypt. Returns (hex_nonce, hex_ciphertext, hex_tag)."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM  # type: ignore

    nonce = os.urandom(12)
    aead = AESGCM(key)
    ct_with_tag = aead.encrypt(nonce, plaintext, None)
    ct = ct_with_tag[:-16]
    tag = ct_with_tag[-16:]
    return nonce.hex(), ct.hex(), tag.hex()


def _encrypt_hmac_only(plaintext: bytes, key: bytes) -> tuple[str, str, str]:
    """Fallback: XOR-stream encrypt via SHA-256 keystream + HMAC-SHA256 auth tag."""
    nonce = os.urandom(12)
    # SHA-256 keystream (not cryptographically secure for production — training stub)
    ks_seed = hashlib.sha256(key + nonce).digest()
    keystream = b""
    i = 0
    while len(keystream) < len(plaintext):
        keystream += hashlib.sha256(ks_seed + i.to_bytes(4, "big")).digest()
        i += 1
    ct = bytes(a ^ b for a, b in zip(plaintext, keystream))
    tag = _hmac256(key, nonce + ct)
    return nonce.hex(), ct.hex(), tag[:32]


def stage_encrypt(egged: dict) -> dict:
    """Stage 5: encrypt Sacred Egg payload.

    Crypto tier priority: liboqs ML-KEM-768 → cryptography AES-256-GCM → hmac-only.
    Transport key is ephemeral (derived from egg_id + chain_root).
    """
    egg = egged.get("egg", {})
    chain_root = egged.get("hashes", {}).get("chain_root", "")
    egg_id = egg.get("egg_id", "")

    # Derive transport key from egg identity (deterministic, session-specific)
    key_material = hashlib.sha256(
        f"SCBE-TRANSPORT-KEY:{egg_id}:{chain_root}".encode()
    ).digest()

    plaintext = base64.b64decode(egg.get("yolk", ""))

    kem_meta: dict[str, Any] = {"tier": CRYPTO_TIER}

    if LIBOQS_AVAILABLE:
        try:
            oqs = _load_oqs()
            if oqs is None:
                raise RuntimeError("oqs unavailable")

            with oqs.KeyEncapsulation("ML-KEM-768") as kem:
                pub = kem.generate_keypair()
                ciphertext_kem, shared_secret = kem.encap_secret(pub)
                transport_key = hashlib.sha256(shared_secret + key_material).digest()
                nonce_hex, ct_hex, tag_hex = _encrypt_aes_gcm(plaintext, transport_key)
                kem_meta.update(
                    {
                        "algorithm": "ML-KEM-768",
                        "kem_ciphertext": ciphertext_kem.hex(),
                        "kem_pk_len": len(pub),
                        "kem_ct_len": len(ciphertext_kem),
                    }
                )
        except BaseException:
            nonce_hex, ct_hex, tag_hex = _encrypt_hmac_only(plaintext, key_material)
            kem_meta["tier"] = "hmac-fallback"
    elif CRYPTOGRAPHY_AVAILABLE:
        nonce_hex, ct_hex, tag_hex = _encrypt_aes_gcm(plaintext, key_material)
        kem_meta["algorithm"] = "AES-256-GCM"
    else:
        nonce_hex, ct_hex, tag_hex = _encrypt_hmac_only(plaintext, key_material)

    result = dict(egged)
    result["encrypted"] = {
        "nonce": nonce_hex,
        "ciphertext": ct_hex,
        "auth_tag": tag_hex,
        "plaintext_len": len(plaintext),
        "ciphertext_len": len(bytes.fromhex(ct_hex)),
        "kem": kem_meta,
    }
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Stage 6 — POST-QUANTUM SIGNING & TRANSPORT PACKET
# ──────────────────────────────────────────────────────────────────────────────


def stage_sign(encrypted: dict) -> dict:
    """Stage 6: sign ciphertext with ML-DSA-65 (liboqs) or HMAC-SHA256 fallback.

    Returns the final transport envelope — everything needed to verify + decrypt
    on the receiving end.
    """
    enc = encrypted.get("encrypted", {})
    egg_id = encrypted.get("egg", {}).get("egg_id", "")
    chain_root = encrypted.get("hashes", {}).get("chain_root", "")

    # Blob to sign = ciphertext + auth_tag + egg_id + chain_root
    blob = (
        bytes.fromhex(enc.get("ciphertext", ""))
        + bytes.fromhex(enc.get("auth_tag", ""))
        + egg_id.encode()
        + chain_root.encode()
    )

    sig_meta: dict[str, Any] = {}

    if LIBOQS_AVAILABLE:
        try:
            oqs = _load_oqs()
            if oqs is None:
                raise RuntimeError("oqs unavailable")

            alg = "ML-DSA-65"
            try:
                with oqs.Signature(alg) as signer:
                    pub = signer.generate_keypair()
                    signature = signer.sign(blob)
                    sig_meta = {
                        "algorithm": alg,
                        "signature": signature.hex(),
                        "sig_len": len(signature),
                        "pk_len": len(pub),
                    }
            except Exception:
                alg = "Dilithium3"
                with oqs.Signature(alg) as signer:
                    pub = signer.generate_keypair()
                    signature = signer.sign(blob)
                    sig_meta = {
                        "algorithm": alg,
                        "signature": signature.hex(),
                        "sig_len": len(signature),
                        "pk_len": len(pub),
                    }
        except Exception as exc:
            sig_meta = {
                "algorithm": "HMAC-SHA256-fallback",
                "signature": _hmac256(_CHAIN_KEY, blob),
                "error": str(exc),
            }
    else:
        sig_meta = {
            "algorithm": "HMAC-SHA256",
            "signature": _hmac256(_CHAIN_KEY, blob),
            "blob_len": len(blob),
        }

    transport_packet = {
        "packet_version": "SCBE-NEWS-TRANSPORT-v1",
        "egg_id": egg_id,
        "chain_root": chain_root,
        "source": encrypted.get("source", ""),
        "region": encrypted.get("region", ""),
        "geo": {
            k: v
            for k, v in encrypted.get("geo", {}).items()
            if k in ("lat", "lon", "country", "tongue", "seal")
        },
        # Ciphertext omitted from records; auth_tag + ciphertext_len are sufficient
        # for training data — the actual bytes add ~2KB bloat per record.
        "encrypted_payload": {k: v for k, v in enc.items() if k != "ciphertext"},
        "signature": sig_meta,
        "crypto_tier": CRYPTO_TIER,
        "created_at": datetime.now(tz=timezone.utc).isoformat(),
    }

    result = dict(encrypted)
    result["transport"] = transport_packet
    return result


# ──────────────────────────────────────────────────────────────────────────────
# SFT Pair Generators — each stage transition → one training pair
# ──────────────────────────────────────────────────────────────────────────────


def _sft(
    pair_id: str,
    instruction: str,
    inp: Any,
    output: Any,
) -> dict:
    return {
        "id": pair_id,
        "instruction": instruction,
        "input": json.dumps(inp, ensure_ascii=False) if not isinstance(inp, str) else inp,
        "output": json.dumps(output, ensure_ascii=False) if not isinstance(output, str) else output,
        "pipeline": "news-pipeline",
        "version": "v1",
    }


def sft_raw_to_geo(raw: dict, geo: dict, idx: int) -> dict:
    src = raw.get("source", "?")
    rgn = raw.get("region", "global")
    tongue = SOURCE_TONGUE.get(src, "KO")
    return _sft(
        f"news:raw->geo:{idx}",
        f"Apply GeoSeal geographic tagging to this news article. "
        f"Identify the geographic origin from the source field ('{src}', region '{rgn}'), "
        f"resolve precise WGS-84 coordinates, assign an ISO-3166 country code, determine "
        f"the canonical Sacred Tongue for this source ({TONGUE_NAMES[tongue]}), "
        f"and produce a geometry-bound phase seal that encodes tongue-phase, "
        f"phi-weight, and a SHA-256 geographic fingerprint.",
        {k: v for k, v in raw.items()},
        {"geo": geo["geo"]},
    )


def sft_geo_to_tok_encode(geo: dict, tok: dict, idx: int) -> dict:
    tongue = geo.get("geo", {}).get("tongue", "KO")
    tname = TONGUE_NAMES.get(tongue, tongue)
    mat = tok.get("tokenization", {}).get("tongue_matrix", {}).get(tongue, {})
    return _sft(
        f"news:geo->tok-encode:{tongue}:{idx}",
        f"Encode the title and URL of this geo-tagged news article into {tname} ({tongue}) "
        f"Sacred Tongue tokens. Each byte maps bijectively to one prefix'suffix token pair "
        f"using the deterministic 16×16 tongue grid. "
        f"Return the token list, byte length, and first 8 preview tokens.",
        {
            "title": geo.get("title", ""),
            "url": geo.get("url", ""),
            "tongue": tongue,
            "tongue_name": tname,
        },
        {
            "token_count": mat.get("token_count", 0),
            "byte_len": mat.get("byte_len", 0),
            "tokens_preview": mat.get("tokens_preview", []),
            "roundtrip_ok": mat.get("roundtrip_ok", False),
        },
    )


def sft_tok_decode_roundtrip(tok: dict, idx: int) -> dict:
    tongue = tok.get("tokenization", {}).get("primary_tongue", "KO")
    tname = TONGUE_NAMES.get(tongue, tongue)
    preview = tok.get("tokenization", {}).get("tongue_matrix", {}).get(tongue, {}).get("tokens_preview", [])
    title = tok.get("title", "")
    return _sft(
        f"news:tok-decode-roundtrip:{tongue}:{idx}",
        f"Decode these {tname} ({tongue}) Sacred Tongue tokens back to the original "
        f"UTF-8 text and verify the bijective round-trip. "
        f"Confirm that decode(encode(text)) == text for each of the six tongues.",
        {
            "tokens_preview": preview,
            "tongue": tongue,
            "full_token_count": tok.get("tokenization", {}).get("tongue_matrix", {}).get(tongue, {}).get("token_count", 0),
        },
        {
            "decoded_title": title,
            "all_roundtrip_ok": tok.get("tokenization", {}).get("all_roundtrip_ok", False),
            "tongue_matrix_summary": {
                t: d.get("roundtrip_ok", False)
                for t, d in tok.get("tokenization", {}).get("tongue_matrix", {}).items()
            },
        },
    )


def sft_tok_to_hash(tok: dict, hashed: dict, idx: int) -> dict:
    tongue = hashed.get("geo", {}).get("tongue", "KO")
    h = hashed.get("hashes", {})
    return _sft(
        f"news:tok->hash:{idx}",
        "Compute SHA-256 content hashes and an HMAC chain for the three pipeline stages "
        "of this news item: (1) raw JSON, (2) geo-tagged JSON, (3) Sacred Tongue token list. "
        f"The primary encoding tongue is {TONGUE_NAMES.get(tongue, tongue)} ({tongue}). "
        "The HMAC chain keys each stage's MAC off the prior stage's hash, producing "
        "a tamper-evident chain_root that binds raw → geo → tokenized together.",
        {
            "title": tok.get("title", ""),
            "source": tok.get("source", ""),
            "primary_tongue": tongue,
            "token_count": tok.get("tokenization", {}).get("tongue_matrix", {}).get(tongue, {}).get("token_count", 0),
        },
        {
            "raw_hash": h.get("raw", ""),
            "geo_hash": h.get("geotagged", ""),
            "tok_hash": h.get("tokenized", ""),
            "chain_root": h.get("chain_root", ""),
        },
    )


def sft_hash_to_egg(hashed: dict, egged: dict, idx: int) -> dict:
    egg = egged.get("egg", {})
    tongue = egg.get("tongue", "KO")
    return _sft(
        f"news:hash->egg:{idx}",
        "Create a Sacred Egg for this news item. "
        "The shell is the HMAC chain_root (cryptographic binding to all prior stages). "
        "The yolk is the base64-encoded semantic payload (title, URL, geo, hashes). "
        f"The ritual is 'news_ingest', tongue is {TONGUE_NAMES.get(tongue, tongue)} ({tongue}). "
        "Derive a deterministic egg_id as a UUID v5 from the SCBE namespace and the shell hash. "
        "Compute the phi-weighted egg cost using the tongue's phi-weight.",
        {
            "chain_root": hashed.get("hashes", {}).get("chain_root", ""),
            "source": hashed.get("source", ""),
            "tongue": tongue,
            "yolk_byte_len": egg.get("yolk_byte_len", 0),
        },
        {
            "egg_id": egg.get("egg_id", ""),
            "shell": egg.get("shell", ""),
            "ritual": egg.get("ritual", ""),
            "tongue": tongue,
            "tongue_name": TONGUE_NAMES.get(tongue, tongue),
            "egg_cost_phi": egg.get("egg_cost_phi", 0),
            "hatched_at": None,
            "credits": 0,
        },
    )


def sft_egg_to_encrypted(egged: dict, encrypted: dict, idx: int) -> dict:
    egg = egged.get("egg", {})
    enc = encrypted.get("encrypted", {})
    kem = enc.get("kem", {})
    return _sft(
        f"news:egg->encrypted:{idx}",
        "Encrypt this Sacred Egg payload using the SCBE post-quantum transport protocol. "
        "Derive an ephemeral transport key from the egg_id and chain_root. "
        f"Apply {kem.get('algorithm', kem.get('tier', 'AES-256-GCM'))} encryption: "
        "use a 12-byte random nonce, return the ciphertext and authentication tag as hex. "
        "Record the crypto tier (liboqs ML-KEM-768 / cryptography AES-GCM / hmac-only) "
        "so the training record captures which security level was active.",
        {
            "egg_id": egg.get("egg_id", ""),
            "shell": egg.get("shell", ""),
            "yolk_byte_len": egg.get("yolk_byte_len", 0),
            "ritual": egg.get("ritual", ""),
        },
        {
            "nonce": enc.get("nonce", ""),
            "ciphertext_len": enc.get("ciphertext_len", 0),
            "auth_tag": enc.get("auth_tag", ""),
            "crypto_tier": kem.get("tier", CRYPTO_TIER),
        },
    )


def sft_encrypted_to_transport(encrypted: dict, signed: dict, idx: int) -> dict:
    pkt = signed.get("transport", {})
    sig = pkt.get("signature", {})
    return _sft(
        f"news:encrypted->transport:{idx}",
        "Assemble and sign the final post-quantum transport packet for this encrypted news egg. "
        "Sign the ciphertext+auth_tag+egg_id+chain_root blob with "
        f"{sig.get('algorithm', 'HMAC-SHA256')}. "
        "Attach the geographic seal, source metadata, and crypto tier. "
        "This packet is the canonical SCBE-NEWS-TRANSPORT-v1 wire format.",
        {
            "egg_id": encrypted.get("egg", {}).get("egg_id", ""),
            "chain_root": encrypted.get("hashes", {}).get("chain_root", ""),
            "source": encrypted.get("source", ""),
            "region": encrypted.get("region", ""),
            "ciphertext_len": encrypted.get("encrypted", {}).get("ciphertext_len", 0),
        },
        {
            "packet_version": pkt.get("packet_version", ""),
            "sig_algorithm": sig.get("algorithm", ""),
            "sig_len": sig.get("sig_len", len(sig.get("signature", "")) // 2),
            "crypto_tier": pkt.get("crypto_tier", ""),
            "geo_seal": pkt.get("geo", {}).get("seal", ""),
        },
    )


def sft_braid_alignment(tok: dict, idx: int) -> dict | None:
    """Stage 2b: SFT pair for the semantic-atomic braid alignment score.

    Produces a training pair only when the braid module was available and ran
    successfully (i.e., tok["tokenization"]["braid"] is a dict without "error").
    Returns None (pair skipped) when the module was absent or failed.
    """
    braid = tok.get("tokenization", {}).get("braid")
    if not braid or "error" in braid:
        return None
    tongue = tok.get("tokenization", {}).get("primary_tongue", "KO")
    tname = TONGUE_NAMES.get(tongue, tongue)
    title = tok.get("title", "")
    source = tok.get("source", "?")
    preview_tokens = (
        tok.get("tokenization", {}).get("tongue_matrix", {}).get(tongue, {}).get("tokens_preview", [])
    )
    return _sft(
        f"news:braid-align:{tongue}:{idx}",
        f"Score the semantic-atomic braid alignment for this news article. "
        f"The primary Sacred Tongue is {tname} ({tongue}). "
        f"Compute the 4-component alignment score: "
        f"semantic_alignment (×0.25), roundtrip_ok (×0.20), atomic_home_alignment (×0.40), "
        f"phi_underlay_alignment (×0.15). "
        f"Report the aligned score, the full tongue-matrix cross-scores, and the "
        f"discriminatory delta (aligned_score - worst_mismatch_score). "
        f"A high delta means the payload is strongly bound to its canonical tongue.",
        {
            "title": title,
            "source": source,
            "primary_tongue": tongue,
            "tongue_name": tname,
            "tokens_preview": preview_tokens,
        },
        {
            "aligned_score": braid.get("aligned_score"),
            "aligned_components": braid.get("aligned_components", {}),
            "tongue_matrix": braid.get("tongue_matrix", {}),
            "worst_mismatch_score": braid.get("worst_mismatch_score"),
            "best_mismatch_score": braid.get("best_mismatch_score"),
            "discriminatory_delta": braid.get("discriminatory_delta"),
        },
    )


# ──────────────────────────────────────────────────────────────────────────────
# Full item pipeline
# ──────────────────────────────────────────────────────────────────────────────


def run_item(item: dict, idx: int) -> tuple[dict, list[dict]]:
    """Run one news item through all 7 stages. Returns (record, sft_pairs)."""
    raw = dict(item)

    geotagged = stage_geotag(raw)
    tokenized = stage_tokenize(geotagged)
    hashed = stage_hash(raw, geotagged, tokenized)
    egged = stage_egg(hashed)
    encrypted = stage_encrypt(egged)
    signed = stage_sign(encrypted)

    record = {
        "pipeline_id": f"news-{datetime.now(tz=timezone.utc).date().isoformat()}:{idx:03d}",
        "stages": {
            "raw": raw,
            "geotagged": {k: v for k, v in geotagged.items()},
            "tokenized": {
                "tokenization_summary": {
                    t: {"token_count": d.get("token_count"), "roundtrip_ok": d.get("roundtrip_ok")}
                    for t, d in tokenized.get("tokenization", {}).get("tongue_matrix", {}).items()
                },
                "all_roundtrip_ok": tokenized.get("tokenization", {}).get("all_roundtrip_ok"),
                "tokenizer_source": tokenized.get("tokenization", {}).get("tokenizer_source"),
            },
            "hashes": hashed.get("hashes", {}),
            "egg": signed.get("egg", {}),
            "encrypted": {
                k: v for k, v in signed.get("encrypted", {}).items() if k != "ciphertext"
            },
            "transport": signed.get("transport", {}),
        },
        "crypto_tier": CRYPTO_TIER,
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }

    braid_pair = sft_braid_alignment(tokenized, idx)
    sft_pairs = [
        sft_raw_to_geo(raw, geotagged, idx),
        sft_geo_to_tok_encode(geotagged, tokenized, idx),
        sft_tok_decode_roundtrip(tokenized, idx),
        sft_tok_to_hash(tokenized, hashed, idx),
        sft_hash_to_egg(hashed, egged, idx),
        sft_egg_to_encrypted(egged, encrypted, idx),
        sft_encrypted_to_transport(encrypted, signed, idx),
    ]
    if braid_pair is not None:
        sft_pairs.append(braid_pair)

    return record, sft_pairs


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────


def main() -> None:
    if not FEED_PATH.exists():
        print(f"[news_pipeline] Feed not found: {FEED_PATH}", file=sys.stderr)
        sys.exit(1)

    feed = json.loads(FEED_PATH.read_text(encoding="utf-8"))
    items = feed.get("items", [])
    today = datetime.now(tz=timezone.utc).date().isoformat()

    records_path = RECORDS_DIR / f"{today}.jsonl"
    sft_path = SFT_DIR / f"{today}.jsonl"

    total_records = 0
    total_sft = 0
    errors = 0

    # Overwrite mode: each run writes a clean snapshot for today.
    # Daily accumulation happens naturally across calendar-day files; within a
    # day the latest run wins, preventing duplicate records from static feeds.
    with records_path.open("w", encoding="utf-8") as rec_f, sft_path.open("w", encoding="utf-8") as sft_f:
        for idx, item in enumerate(items):
            try:
                record, sft_pairs = run_item(item, idx)
                rec_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                for pair in sft_pairs:
                    sft_f.write(json.dumps(pair, ensure_ascii=False) + "\n")
                total_records += 1
                total_sft += len(sft_pairs)
            except Exception as exc:
                errors += 1
                print(f"[news_pipeline] item {idx} failed: {exc}", file=sys.stderr)

    # Write public summary
    summary = {
        "generated": datetime.now(tz=timezone.utc).isoformat(),
        "feed_generated": feed.get("generated", ""),
        "items_processed": total_records,
        "sft_pairs_generated": total_sft,
        "errors": errors,
        "crypto_tier": CRYPTO_TIER,
        "tokenizer_source": _TOKENIZER_SOURCE,
        "tongue_coverage": list(TONGUE_PHI_WEIGHTS.keys()),
        "records_file": records_path.relative_to(REPO_ROOT).as_posix(),
        "sft_file": sft_path.relative_to(REPO_ROOT).as_posix(),
        "pipeline_stages": [
            "raw", "geotagged", "tokenized", "hashed", "egged", "encrypted", "signed"
        ],
        "braid_available": _BRAID_AVAILABLE,
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(
        f"[news_pipeline] {total_records} items -> {total_sft} SFT pairs | "
        f"crypto={CRYPTO_TIER} | tokenizer={_TOKENIZER_SOURCE} | errors={errors}"
    )


if __name__ == "__main__":
    main()
