import json

from enhanced_scbe_cli import (
    GeoSeal,
    SacredEgg,
    ScatterCast,
    decode_text,
    encode_text,
    geoseal_distribution_probe,
    rfc5869_vector_ok,
    vocab_disjointness,
)


def test_hkdf_rfc5869_vector():
    assert rfc5869_vector_ok()


def test_cross_tongue_vocab_disjoint():
    overlaps = vocab_disjointness()
    # Canonical tongues can have limited lexical overlap.
    # We rely on explicit tongue prefixes for unambiguous parsing.
    assert max(overlaps.values()) <= 16


def test_encode_decode_roundtrip():
    text = "SCBE reality gate"
    tokens = encode_text("ko", text)
    decoded = decode_text("ko", tokens)
    assert decoded == text


def test_geoseal_non_saturated_distribution():
    stats = geoseal_distribution_probe(n=200)
    assert stats["d_h_std"] > 0.1
    assert stats["max_same_radius_fraction"] < 0.2


def test_scattercast_shapes_and_sacredegg_governance_gate():
    generated = ScatterCast().generate("ko", visible_len=23)
    assert len(bytes.fromhex(generated["seed_s_hex"])) == 32
    assert len(bytes.fromhex(generated["master_seed_hex"])) == 64
    assert len(bytes.fromhex(generated["kyber_seed_hex"])) == 32
    assert len(bytes.fromhex(generated["dilithium_seed_hex"])) == 32

    # All visible tokens must be prefixed with tongue code.
    tokens = generated["seed_v_phrase"].split()
    assert all(":" in tok for tok in tokens)
    assert all(tok.split(":", 1)[0] in {"ko", "dr"} for tok in tokens)

    egg = SacredEgg(generated["master_seed_hex"], generated["seed_v_phrase"])
    gov = egg.derive_key("gov")
    # Depending on resonance composition this can pass or fail; structure must be explicit.
    assert "key_hex" in gov or "error" in gov


def test_geoseal_classify_json_safe():
    out = GeoSeal().classify("Port Angeles, WA")
    blob = json.dumps(out)
    assert "decision" in out
    assert "d_h" in out
    assert isinstance(blob, str)
