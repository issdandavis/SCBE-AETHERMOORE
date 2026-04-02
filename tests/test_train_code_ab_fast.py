import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "research" / "train_code_ab_fast.py"
SPEC = importlib.util.spec_from_file_location("train_code_ab_fast", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class TrainCodeABFastTests(unittest.TestCase):
    def test_extract_text_prefers_messages(self):
        record = {
            "messages": [
                {"role": "system", "content": "sys"},
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "world"},
            ]
        }
        text = MODULE.extract_text(record)
        self.assertIn("<|im_start|>system", text)
        self.assertIn("hello", text)
        self.assertIn("world", text)

    def test_clamp_records_respects_token_budget(self):
        records = [
            {"text": "a" * 40, "estimated_tokens": 10, "row_index": 0},
            {"text": "b" * 40, "estimated_tokens": 10, "row_index": 1},
            {"text": "c" * 40, "estimated_tokens": 10, "row_index": 2},
        ]
        kept = MODULE.clamp_records(records, target_tokens=20, max_records=None, seed=42)
        self.assertGreaterEqual(len(kept), 1)
        self.assertLessEqual(sum(r["estimated_tokens"] for r in kept), 20)

    def test_prepare_benchmark_writes_manifest_and_jsonl(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            baseline = temp / "baseline.jsonl"
            triangulated = temp / "triangulated.jsonl"
            artifact_dir = temp / "artifacts"

            baseline_rows = [
                {"messages": [{"role": "user", "content": "baseline alpha"}]},
                {"messages": [{"role": "assistant", "content": "baseline beta"}]},
            ]
            triangulated_rows = [
                {"messages": [{"role": "user", "content": "triangulated alpha long enough to count"}]},
                {"messages": [{"role": "assistant", "content": "triangulated beta long enough to count"}]},
                {"messages": [{"role": "user", "content": "triangulated gamma long enough to count"}]},
            ]

            baseline.write_text("\n".join(json.dumps(row) for row in baseline_rows), encoding="utf-8")
            triangulated.write_text("\n".join(json.dumps(row) for row in triangulated_rows), encoding="utf-8")

            manifest = MODULE.prepare_benchmark(
                baseline_path=baseline,
                triangulated_path=triangulated,
                artifact_dir=artifact_dir,
                max_baseline_rows=2,
                seed=42,
            )

            self.assertTrue((artifact_dir / "manifest.json").exists())
            self.assertTrue((artifact_dir / "baseline_matched.jsonl").exists())
            self.assertTrue((artifact_dir / "triangulated_matched.jsonl").exists())
            self.assertIn("prepared", manifest)
            self.assertEqual(manifest["prepared"]["baseline"]["rows"], 2)
            self.assertLessEqual(
                manifest["prepared"]["triangulated"]["estimated_tokens"],
                manifest["target_token_budget"],
            )


if __name__ == "__main__":
    unittest.main()
