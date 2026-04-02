import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "research" / "train_code_ab_kaggle_safe.py"
SPEC = importlib.util.spec_from_file_location("train_code_ab_kaggle_safe", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class TrainCodeABKaggleSafeTests(unittest.TestCase):
    def test_build_runtime_plan_prefers_t4_full_run(self):
        plan = MODULE.build_runtime_plan("Tesla T4", allow_cpu_smoke=False)
        self.assertEqual(plan["mode"], "gpu_full")
        self.assertEqual(plan["max_steps"], 75)
        self.assertEqual(plan["max_seq_length"], 512)
        self.assertTrue(plan["quantized"])

    def test_build_runtime_plan_rejects_cpu_without_opt_in(self):
        with self.assertRaises(RuntimeError):
            MODULE.build_runtime_plan("CPU", allow_cpu_smoke=False)

    def test_build_runtime_plan_allows_cpu_smoke_when_requested(self):
        plan = MODULE.build_runtime_plan("CPU", allow_cpu_smoke=True)
        self.assertEqual(plan["mode"], "cpu_smoke")
        self.assertEqual(plan["max_steps"], 4)
        self.assertFalse(plan["quantized"])

    def test_summarize_delta_reports_winner(self):
        summary = MODULE.summarize_delta(2.0, 1.5)
        self.assertEqual(summary["winner"], "triangulated")
        self.assertEqual(summary["delta_loss"], -0.5)
        self.assertEqual(summary["relative_improvement_pct"], 25.0)


if __name__ == "__main__":
    unittest.main()
