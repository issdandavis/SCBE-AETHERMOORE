from src.crypto.binary_lambda import BLCTerm, blc_to_surfaces, decode_blc, encode_blc, placements


def test_identity_round_trip_and_placement():
    term = BLCTerm.lam(BLCTerm.var(1))
    bits = encode_blc(term)

    assert bits == "0010"
    assert decode_blc(bits).to_source() == "(lambda 1)"

    spans = placements(bits)
    assert [(p.bits, p.role, p.start, p.end) for p in spans] == [
        ("00", "binder", 0, 2),
        ("10", "reference", 2, 4),
    ]


def test_application_round_trip_and_surfaces():
    identity = BLCTerm.lam(BLCTerm.var(1))
    term = BLCTerm.app(identity, identity)
    surfaces = blc_to_surfaces(term)

    assert surfaces["blc_bits"] == "0100100010"
    assert surfaces["round_trip"] is True
    assert surfaces["binary"] == "01001000 10000000"
    assert surfaces["hex"] == "48.80"
    assert [p["role"] for p in surfaces["placements"]] == ["branch", "binder", "reference", "binder", "reference"]


def test_invalid_variable_reference_rejected():
    try:
        decode_blc("111")
    except ValueError as exc:
        assert "Unterminated" in str(exc)
    else:
        raise AssertionError("unterminated variable reference should fail")

