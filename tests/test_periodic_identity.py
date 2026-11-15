from python.scbe.atomic_tokenization import (
    chemical_element,
    chemical_identity,
    parse_formula,
)
from python.scbe.periodic_identity import (
    PERIODIC_IDENTITIES,
    SYMBOLS_BY_ATOMIC_NUMBER,
    periodic_identity_manifest,
)


def test_periodic_identity_covers_all_118_atomic_numbers_once() -> None:
    assert len(PERIODIC_IDENTITIES) == 118
    assert len(SYMBOLS_BY_ATOMIC_NUMBER) == 118
    assert [PERIODIC_IDENTITIES[symbol].atomic_number for symbol in SYMBOLS_BY_ATOMIC_NUMBER] == list(range(1, 119))


def test_femoco_elements_have_real_periodic_coordinates() -> None:
    assert chemical_identity("Fe").as_dict() == {
        "symbol": "Fe",
        "atomic_number": 26,
        "period": 4,
        "group": 8,
        "block": "d",
    }
    assert chemical_identity("mo").as_dict() == {
        "symbol": "Mo",
        "atomic_number": 42,
        "period": 5,
        "group": 6,
        "block": "d",
    }
    assert chemical_identity("S").atomic_number == 16


def test_atomic_material_surface_recognizes_femoco_formula() -> None:
    assert parse_formula("Fe7MoS9") == {"Fe": 7, "Mo": 1, "S": 9}
    assert chemical_element("Mo").Z == 42
    assert chemical_element("Mo").feature_source == "curated"


def test_identity_only_rows_are_addressable_without_invented_features() -> None:
    assert chemical_element("Og") is None
    og = chemical_identity("Og")
    assert og is not None
    assert og.atomic_number == 118
    assert og.period == 7
    assert og.group == 18
    assert og.block == "p"


def test_manifest_is_atomic_number_ordered_and_records_group_three_boundary() -> None:
    manifest = periodic_identity_manifest()
    assert manifest["schema"] == "scbe.periodic-identity.v1"
    assert [row["atomic_number"] for row in manifest["elements"]] == list(range(1, 119))
    assert "address convention" in manifest["group_three_boundary"]
