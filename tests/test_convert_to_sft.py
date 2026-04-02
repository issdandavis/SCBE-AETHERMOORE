import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "spiralverse" / "convert_to_sft.py"
SPEC = importlib.util.spec_from_file_location("convert_to_sft", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ConvertToSFTTests(unittest.TestCase):
    def test_convert_record_keeps_page_like_input_working(self):
        raw = {
            "id": "page-1",
            "title": "Governance Gate",
            "text": (
                "The governance gate evaluates layered signals before producing an ALLOW, "
                "QUARANTINE, or DENY decision across the SCBE runtime."
            ),
        }

        converted = MODULE.convert_record(raw, 1)

        self.assertIsNotNone(converted)
        assert converted is not None
        self.assertEqual(converted["id"], "sft-0001")
        self.assertIn("Governance Gate", converted["instruction"])
        self.assertEqual(converted["metadata"]["source_type"], "notion_page")

    def test_normalize_sft_record_accepts_prompt_response_rows(self):
        raw = {
            "prompt": "Explain the harmonic wall.",
            "response": "It increases cost with radial drift.",
            "metadata": json.dumps({"category_hint": "governance"}),
        }

        normalized = MODULE.normalize_sft_record(raw, 7)

        self.assertEqual(normalized["instruction"], raw["prompt"])
        self.assertEqual(normalized["response"], raw["response"])
        self.assertEqual(normalized["metadata"]["source_type"], "flat_sft")
        self.assertIn("track", normalized["metadata"])

    def test_load_records_accepts_spiralverse_generator_export(self):
        payload = {
            "version": "1.0",
            "protocol": "Spiralverse",
            "generated_at": "2026-04-02T00:00:00",
            "total_conversations": 1,
            "conversations": [
                {
                    "id": "convo-1",
                    "starting_topic": "astronomy",
                    "metadata": {"num_pivots": 1, "languages_used": ["EMBER"], "topic_journey": ["astronomy", "physics"]},
                    "turns": [
                        {
                            "turn": 1,
                            "topic": "astronomy",
                            "message": (
                                "Discussion about astronomy: studying stellar evolution and cosmic phenomena "
                                "across the universe with governance-aware narration."
                            ),
                            "encoded": "◇◆◈",
                            "language": "EMBER",
                            "language_domain": "emotional",
                            "signature_hash": "abc123",
                        }
                    ],
                }
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            source = Path(temp_dir) / "spiralverse_demo_data.json"
            source.write_text(json.dumps(payload), encoding="utf-8")

            records = MODULE.load_records(str(source))

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["id"], "convo-1")
        self.assertEqual(records[0]["turns"][0]["language"], "EMBER")

    def test_convert_spiralverse_turn_emits_sft_with_provenance(self):
        conversation = {
            "id": "convo-2",
            "starting_topic": "music",
            "metadata": {"num_pivots": 2, "topic_journey": ["music", "mathematics", "physics_of_sound"]},
        }
        turn_data = {
            "turn": 3,
            "topic": "physics_of_sound",
            "message": (
                "Discussion about physics_of_sound: how sound waves are created, propagate, and are perceived "
                "through harmonic structures and governed telemetry."
            ),
            "encoded": "◎◉○",
            "language": "AETHERIC",
            "language_domain": "abstract",
            "signature_hash": "def456",
        }

        converted = MODULE.convert_spiralverse_turn(conversation, turn_data, 12)

        self.assertIsNotNone(converted)
        assert converted is not None
        self.assertEqual(converted["id"], "sft-0012")
        self.assertIn("AETHERIC sacred language alignment", converted["instruction"])
        self.assertEqual(converted["metadata"]["source_type"], "spiralverse_generator_turn")
        self.assertEqual(converted["metadata"]["conversation_id"], "convo-2")
        self.assertEqual(converted["metadata"]["topic_journey"], ["music", "mathematics", "physics_of_sound"])


if __name__ == "__main__":
    unittest.main()
