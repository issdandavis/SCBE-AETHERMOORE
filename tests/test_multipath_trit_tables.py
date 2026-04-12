"""All 6 Sacred Tongue trit tables must satisfy A1-A5 axioms."""

from __future__ import annotations

import pytest

from src.symphonic.multipath import (
    KO_TABLE,
    AV_TABLE,
    RU_TABLE,
    UM_TABLE,
    DR_TABLE,
    TRIT_TABLES,
)
from src.symphonic.multipath import trit_table_CA as ca_module

NEW_TABLES = [
    ("KO", KO_TABLE, 0),
    ("AV", AV_TABLE, 1),
    ("RU", RU_TABLE, 2),
    ("UM", UM_TABLE, 4),
    ("DR", DR_TABLE, 5),
]


@pytest.mark.parametrize("name,table,tongue_id", NEW_TABLES)
def test_axioms_pass(name, table, tongue_id):
    results = table.validate()
    assert results["all_pass"], f"{name} failed axioms: {results}"


@pytest.mark.parametrize("name,table,tongue_id", NEW_TABLES)
def test_shape(name, table, tongue_id):
    assert table.tongue == name
    assert table.tongue_id == tongue_id
    assert len(table.ops) == 64
    assert len(table.bands) == 4
    assert table.trit_matrix.shape == (64, 6)
    assert table.feat_matrix.shape == (64, 8)


@pytest.mark.parametrize("name,table,tongue_id", NEW_TABLES)
def test_home_channel_unitarity(name, table, tongue_id):
    assert (table.trit_matrix[:, tongue_id] == 1).all()


@pytest.mark.parametrize("name,table,tongue_id", NEW_TABLES)
def test_unique_ops(name, table, tongue_id):
    assert len(set(table.ops)) == 64


def test_ca_axioms_pass():
    results = ca_module.validate()
    assert results.get("all_pass") or all(
        v for k, v in results.items() if k != "all_pass"
    ), f"CA failed axioms: {results}"


def test_all_six_tongues_registered():
    assert set(TRIT_TABLES.keys()) == {"KO", "AV", "RU", "CA", "UM", "DR"}
