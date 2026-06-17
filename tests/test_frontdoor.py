"""Front door — token stream -> opcode object -> rendered code (the keyboard layer)."""
import pytest

from python.scbe import frontdoor as F
from python.scbe import polyglot as P


def test_symbols_names_hex_all_map():
    names, prog = F.tokens_to_program("+ sqrt * 0x0b /")
    assert names == ["add", "sqrt", "mul", "inc", "div"]
    assert prog == P.program_bytes(*names)


def test_aliases_and_commas():
    names, _ = F.tokens_to_program("power, root, maximum")
    assert names == ["pow", "sqrt", "max"]


def test_unknown_token_hints():
    with pytest.raises(ValueError) as e:
        F.tokens_to_program("add sqrtt mul")
    assert "sqrt" in str(e.value)            # did-you-mean suggestion present


def test_non_core_hex_rejected():
    with pytest.raises(ValueError):
        F.tokens_to_program("0xff")          # not a v1 scalar-core opcode


def test_render_is_verified_and_clean():
    out = F.render("+ sqrt * inc /", ("python", "rust"), color=False)
    assert "SCBE · cube code" in out
    assert "18/18 faces" in out and "seekable" in out and "sealed" in out
    assert "def tongue_fn" in out and "fn tongue_fn" in out
    # the rendered object decodes back to exactly what we typed (bijection holds)
    _, prog = F.tokens_to_program("+ sqrt * inc /")
    from python.scbe import bijective_dna as DNA
    assert DNA.decode_from_source(P.emit(prog, "rust")) == prog


def test_empty_program_renders():
    out = F.render("", ("python",), color=False)
    assert "0 op" in out or "(empty)" in out


def test_geoseal_signature_is_nonzero_and_stable():
    a = F.render("+ * sqrt", ("python",), color=False)
    b = F.render("+ * sqrt", ("python",), color=False)
    assert a == b                            # deterministic
    sig = [ln for ln in a.splitlines() if "geoseal" in ln][0]
    assert "0000000000000000" not in sig     # XOR-fold fixed the splitmix64(0) artifact
