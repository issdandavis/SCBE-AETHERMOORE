"""Cube canvas — self-contained zoomable HTML of a program on the board."""
from python.scbe import board as BOARD
from python.scbe import canvas as CV
from python.scbe import polyglot as P


def test_build_html_is_a_complete_self_contained_page():
    html = CV.build_html("+ sqrt * inc")
    assert html.startswith("<!doctype html>") and html.rstrip().endswith("</html>")
    assert "<svg" in html and "<script>" in html              # inline, no external deps
    assert "http://" not in html and "https://" not in html   # truly self-contained
    assert "add sqrt mul inc" in html                          # the program is shown


def test_stones_sit_at_their_board_coordinates():
    # add = 0x00 -> board (0,0); the canvas should color it with board.rgb(0x00)
    html = CV.build_html("add")
    add = P.NAME_TO_BYTE["add"]
    r, g, b = BOARD.rgb(add)
    assert ("#%02x%02x%02x" % (r, g, b)) in html
    assert "#1 add  byte 0x00" in html                         # hover-info data present


def test_governance_verdict_in_header():
    html = CV.build_html("+ sqrt *")                           # diverges -> ESCALATE
    assert "ESCALATE" in html and "route_to_verifier" in html
    html2 = CV.build_html("+ mul inc")                         # exact -> ALLOW
    assert "ALLOW" in html2


def test_empty_program_renders():
    html = CV.build_html("")
    assert "<!doctype html>" in html and "(empty)" in html


def test_cli_writes_file(tmp_path):
    import subprocess
    import sys
    out = tmp_path / "c.html"
    rc = subprocess.run([sys.executable, "scbe.py", "canvas", "+", "sqrt", "*",
                         "--out", str(out)], capture_output=True, text=True)
    assert rc.returncode == 0 and out.exists()
    assert out.read_text(encoding="utf-8").startswith("<!doctype html>")
