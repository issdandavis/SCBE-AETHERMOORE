from pathlib import Path
import tempfile


def test_repo_temporary_directory_is_writable_and_recyclable():
    with tempfile.TemporaryDirectory() as td:
        temp_dir = Path(td)
        payload = temp_dir / "probe.txt"
        payload.write_text("ok", encoding="utf-8")
        assert payload.read_text(encoding="utf-8") == "ok"
    assert not temp_dir.exists()
