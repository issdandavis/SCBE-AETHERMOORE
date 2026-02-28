from src.geoseed.bit_dresser import BitDresserF1


def test_f1_dress_byte_returns_8_fingerprints():
    dresser = BitDresserF1()
    fingerprints = dresser.dress_byte(0xA5, byte_index=0)

    assert len(fingerprints) == 8
    assert all(fp.layer_path == [1, 2, 3, 4, 5] for fp in fingerprints)
    assert all(len(fp.poincare_pos) == 12 for fp in fingerprints)
    assert all(fp.hyperbolic_distance >= 0.0 for fp in fingerprints)


def test_f1_dressing_is_deterministic():
    dresser = BitDresserF1()
    first = [fp.fingerprint_id for fp in dresser.dress_byte(0x42, byte_index=2)]
    second = [fp.fingerprint_id for fp in dresser.dress_byte(0x42, byte_index=2)]

    assert first == second


def test_f1_hello_world_reports_unique_fingerprints():
    report = BitDresserF1().hello_world(byte_value=0x42)

    assert report["fingerprint_count"] == 8
    assert report["unique_fingerprint_count"] == 8
    assert report["deterministic_repeat"] is True
