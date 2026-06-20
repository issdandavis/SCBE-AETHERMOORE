import numpy as np
import pytest

from python.scbe import frontdoor as F
from python.scbe import polyglot as P
from python.scbe.phdm_embedding import PHDMEmbedder


def test_geometric_address_round_trips_opcode_token_from_candidate_table():
    embedder = PHDMEmbedder()
    candidates = sorted(P.SCALAR_OPS)
    address = embedder.geometric_address("sqrt")

    inverse = embedder.inverse_geometric_address(address, candidates, top_k=3)

    assert inverse["schema_version"] == "scbe_poincare_token_inverse_v1"
    assert inverse["match"]["token"] == "sqrt"
    assert inverse["match"]["rank"] == 1
    assert inverse["match"]["exact"] is True
    assert inverse["match"]["distance"] == pytest.approx(0.0, abs=1e-12)
    assert len(inverse["matches"]) == 3


def test_geometric_address_round_trips_sacred_tongue_keyboard_token():
    embedder = PHDMEmbedder()
    _, prog = F.tokens_to_program("add mul sqrt inc")
    tongue_tokens = F.tongue_spell(prog, "ko").split()
    address = embedder.geometric_address(tongue_tokens[2])

    match = embedder.inverse_embedding(address["position"], tongue_tokens)[0]

    assert tongue_tokens[2] == "sil'eth"
    assert match.token == "sil'eth"
    assert match.exact is True


def test_inverse_embedding_reports_nearest_for_perturbed_position():
    embedder = PHDMEmbedder()
    candidates = ["add", "mul", "sqrt", "inc"]
    address = embedder.geometric_address("mul")
    point = np.asarray(address["position"], dtype=float)
    point[0] += 1e-5

    match = embedder.inverse_embedding(point, candidates)[0]

    assert match.token == "mul"
    assert match.exact is False
    assert match.distance > 0.0


def test_inverse_embedding_rejects_out_of_ball_position():
    embedder = PHDMEmbedder()
    with pytest.raises(ValueError, match="outside the open Poincare ball"):
        embedder.inverse_embedding(np.ones(6), ["add"])


def test_inverse_embedding_requires_bounded_candidate_table():
    embedder = PHDMEmbedder()
    address = embedder.geometric_address("add")
    with pytest.raises(ValueError, match="candidates"):
        embedder.inverse_embedding(address["position"], [])
