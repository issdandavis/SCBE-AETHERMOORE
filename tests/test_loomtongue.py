"""loomtongue: a FULL program (loop) written in the conlang, run + verified across faces.

The bridge between the tokenizer and loomflow's control flow. Opcode-word coherence with the
scalar tokenizer, the conlang->program translation, the bijective read-back, and the python
reference are checked unconditionally; js/rust agreement runs only when the toolchain is present.
"""

import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from python.scbe import loomflow as L  # noqa: E402
from python.scbe.loomtongue import (  # noqa: E402
    CONLANG_EXAMPLES,
    OP_FOR_WORD,
    WORD_FOR_OP,
    from_tongue,
    to_tongue,
    verify_tongue,
)

_HAVE_NODE = shutil.which("node") is not None
_HAVE_RUST = shutil.which("rustc") is not None


def test_lexicon_is_bijective_and_coherent_with_scalar_tokenizer():
    assert len(WORD_FOR_OP) == 19  # every loomflow opcode has a word
    assert len(OP_FOR_WORD) == 19  # ... and they are all distinct
    assert WORD_FOR_OP["add"] == "bip'a"  # matches the scalar note-mode tokenizer
    assert WORD_FOR_OP["mul"] == "bip'i"
    assert WORD_FOR_OP["brz"] == "bop'u"  # control flow on the unused band


def test_conlang_program_translates_and_runs():
    prog = from_tongue(CONLANG_EXAMPLES["sum_1_to_5"])
    assert L.interpret(prog)[-1] == 15.0
    assert L.interpret(from_tongue(CONLANG_EXAMPLES["factorial_5"]))[-1] == 120.0


def test_read_back_is_bijective():
    for src in CONLANG_EXAMPLES.values():
        assert to_tongue(from_tongue(src)) == src  # the song reads back out exactly


def test_unknown_conlang_opcode_raises():
    with pytest.raises(ValueError, match="unknown conlang opcode"):
        from_tongue("zzz acc 0")


def test_python_face_runs_the_conlang_loop_unconditionally():
    r = verify_tongue(CONLANG_EXAMPLES["sum_1_to_5"], faces=("python",))
    assert r["reference"] == 15.0
    assert r["results"]["python"]["status"] == "AGREE"
    assert r["bijective"] is True


@pytest.mark.skipif(not _HAVE_NODE, reason="node not installed")
def test_javascript_runs_the_conlang_loop():
    r = verify_tongue(CONLANG_EXAMPLES["factorial_5"], faces=("javascript",))
    assert r["results"]["javascript"] == {"status": "AGREE", "value": 120.0}


@pytest.mark.skipif(not _HAVE_RUST, reason="rustc not installed")
def test_rust_runs_the_conlang_loop():
    r = verify_tongue(CONLANG_EXAMPLES["sum_1_to_5"], faces=("rust",))
    assert r["results"]["rust"] == {"status": "AGREE", "value": 15.0}
