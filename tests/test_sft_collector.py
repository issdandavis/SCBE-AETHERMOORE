"""
Tests for SCBE SFT Training Data Collector
============================================

Validates:
- JSONL capture and file writing
- Record format integrity
- Auto-rotation at size threshold
- Statistics tracking
- Thread-safe concurrent writes
- HuggingFace export format
"""

import json
import os
import tempfile
import threading
import time

import pytest

# ---------------------------------------------------------------------------
#  Path setup
# ---------------------------------------------------------------------------
import sys

_project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from src.api.sft_collector import SFTCollector


# ---------------------------------------------------------------------------
#  Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_dir():
    """Provide a temporary directory for test output."""
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def collector(tmp_dir):
    """Create an SFTCollector writing to a temp directory."""
    return SFTCollector(
        output_dir=tmp_dir,
        filename="test_sft.jsonl",
        max_size_bytes=1024,  # 1 KB for easy rotation testing
    )


# ---------------------------------------------------------------------------
#  Tests
# ---------------------------------------------------------------------------

class TestCapture:
    """Test basic capture functionality."""

    def test_capture_creates_file(self, collector, tmp_dir):
        collector.capture("Do X", "Did X", category="test")
        assert os.path.exists(collector.filepath)

    def test_capture_returns_record(self, collector):
        rec = collector.capture("Navigate to example.com", "Navigated OK", category="browser")
        assert rec["category"] == "browser"
        assert rec["instruction"] == "Navigate to example.com"
        assert rec["response"] == "Navigated OK"
        assert rec["id"].startswith("sft-browser-")
        assert "timestamp" in rec["metadata"]

    def test_capture_appends_jsonl(self, collector):
        collector.capture("Inst 1", "Resp 1", category="a")
        collector.capture("Inst 2", "Resp 2", category="b")

        with open(collector.filepath, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]

        assert len(lines) == 2
        r1 = json.loads(lines[0])
        r2 = json.loads(lines[1])
        assert r1["instruction"] == "Inst 1"
        assert r2["instruction"] == "Inst 2"


class TestJSONLIntegrity:
    """Test that every line is valid JSON."""

    def test_all_lines_are_valid_json(self, collector):
        for i in range(20):
            collector.capture(f"Instruction {i}", f"Response {i}", category="integrity")

        with open(collector.filepath, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    pytest.fail(f"Line {line_num} is not valid JSON: {line!r}")
                assert "id" in obj
                assert "instruction" in obj
                assert "response" in obj
                assert "category" in obj

    def test_metadata_includes_custom_fields(self, collector):
        rec = collector.capture(
            "Test", "OK", category="meta",
            metadata={"tenant": "acme", "session_id": "s-123"},
        )
        assert rec["metadata"]["tenant"] == "acme"
        assert rec["metadata"]["session_id"] == "s-123"
        assert rec["metadata"]["source"] == "sft_collector"


class TestAutoRotation:
    """Test file rotation when size threshold is exceeded."""

    def test_rotation_creates_new_file(self, collector, tmp_dir):
        # Write enough data to exceed 1 KB threshold
        big_text = "X" * 200
        for _ in range(20):
            collector.capture(big_text, big_text, category="rotation")

        files = [f for f in os.listdir(tmp_dir) if f.endswith(".jsonl")]
        # Should have the current file plus at least one rotated file
        assert len(files) >= 2, f"Expected rotation, got files: {files}"

    def test_rotation_preserves_old_data(self, collector, tmp_dir):
        big_text = "Y" * 200
        for _ in range(20):
            collector.capture(big_text, big_text, category="preserve")

        # Read all JSONL files and count total records
        total = 0
        for fname in os.listdir(tmp_dir):
            if fname.endswith(".jsonl"):
                path = os.path.join(tmp_dir, fname)
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            total += 1

        assert total == 20


class TestStats:
    """Test statistics tracking."""

    def test_stats_initial(self, collector):
        stats = collector.stats()
        assert stats["total_records"] == 0
        assert stats["by_category"] == {}
        assert stats["file_size_bytes"] == 0

    def test_stats_after_captures(self, collector):
        collector.capture("A", "B", category="cat1")
        collector.capture("C", "D", category="cat1")
        collector.capture("E", "F", category="cat2")

        stats = collector.stats()
        assert stats["total_records"] == 3
        assert stats["by_category"]["cat1"] == 2
        assert stats["by_category"]["cat2"] == 1
        assert stats["file_size_bytes"] > 0


class TestExport:
    """Test export functionality."""

    def test_export_jsonl(self, collector):
        collector.capture("I", "R", category="export")
        path = collector.export(fmt="jsonl")
        assert path == collector.filepath
        assert os.path.exists(path)

    def test_export_hf(self, collector, tmp_dir):
        collector.capture("Instruction 1", "Response 1", category="hf_test")
        collector.capture("Instruction 2", "Response 2", category="hf_test")

        hf_path = collector.export(fmt="hf")
        assert os.path.exists(hf_path)
        assert hf_path.endswith("_hf.jsonl")

        with open(hf_path, "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f if l.strip()]

        assert len(lines) == 2
        rec = json.loads(lines[0])
        assert "instruction" in rec
        assert "output" in rec
        assert "category" in rec
        # HF format should NOT have metadata
        assert "metadata" not in rec

    def test_export_invalid_format(self, collector):
        with pytest.raises(ValueError, match="Unsupported export format"):
            collector.export(fmt="csv")


class TestConcurrentWrites:
    """Test thread safety of concurrent captures."""

    def test_concurrent_writes(self, collector):
        errors = []
        barrier = threading.Barrier(10)

        def writer(thread_id: int):
            try:
                barrier.wait(timeout=5)
                for i in range(50):
                    collector.capture(
                        f"Thread {thread_id} instruction {i}",
                        f"Thread {thread_id} response {i}",
                        category=f"thread-{thread_id}",
                    )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(t,)) for t in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)

        assert not errors, f"Thread errors: {errors}"

        stats = collector.stats()
        assert stats["total_records"] == 500  # 10 threads * 50 records

        # Verify all records are valid JSON (across all files including rotated)
        total_on_disk = 0
        for fname in os.listdir(collector._output_dir):
            if fname.endswith(".jsonl"):
                path = os.path.join(collector._output_dir, fname)
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            json.loads(line)  # Will raise if invalid
                            total_on_disk += 1

        assert total_on_disk == 500
