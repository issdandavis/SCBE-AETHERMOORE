"""The Instrument: play a token-song -> verified code in any language face, song read back out.

Verifies by execution (the python face actually runs), not by assertion: a song computes the
right value, the song is recovered from the emitted code (bijective), one song manifests in all
18 faces, and the multi-sensory key (note + instrument + colour) keeps all 64 ops distinct so
the scale can't run out. The conlang-keys path is checked when the sixtongues codec is present.
"""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe.instrument import (  # noqa: E402
    emit_all,
    faces,
    keyspace,
    play,
)


def test_play_runs_verified_and_is_bijective():
    r = play("C E", face="python", args=(10, 3, 2))  # add, mul: (10+3)*... wait stack: see value
    assert r["ops"] == ["add", "mul"]
    assert r["value"] == 50  # verified by executing the python face
    assert r["song_back"] == "C E"
    assert r["bijective"] is True


def test_second_song_computes_and_round_trips():
    r = play("C C", face="python", args=(2, 3, 4))  # add, add over [2,3,4] -> (3+4)+2 = 9
    assert r["value"] == 9
    assert r["bijective"] is True


def test_one_song_manifests_in_all_18_faces():
    out = emit_all("C E", args=(2, 3, 4))
    assert len(out) == 18
    assert sorted(faces()) == sorted(out)
    errors = {f: v for f, v in out.items() if v.startswith("ERROR")}
    assert errors == {}


def test_keyspace_chord_never_runs_out_of_keys():
    # op_id = 12*band + note, so (note, instrument) alone uniquely keys all 64 ops -- the
    # 12-note scale recycles but the instrument band disambiguates; colour is a third axis.
    keys = {(keyspace(i)["note"], keyspace(i)["instrument"]) for i in range(64)}
    assert len(keys) == 64
    assert keyspace(0)["instrument"] != keyspace(12)["instrument"]  # same note name, new timbre
    assert keyspace(0)["light_nm"] != keyspace(40)["light_nm"]  # built in wavelengths


def _have_sixtongues() -> bool:
    try:
        from python.scbe.instrument import _sixtongues

        _sixtongues()
        return True
    except Exception:
        return False


@pytest.mark.skipif(not _have_sixtongues(), reason="sixtongues conlang codec not available")
def test_play_in_the_conlang():
    from python.scbe.instrument import play_tongue

    t = play_tongue("sil'a sil'ei", tongue="ko", face="python", args=(10, 3, 2))
    assert t["ops"] == ["add", "mul"]
    assert t["value"] == 50
    assert t["bijective"] is True  # encode_bytes reads the song back out of the ops
