from __future__ import annotations

import json

from src.geoseal_cli import main


def test_arc_cards_builds_default_tokens_and_routes_upstream_schema(capsys, tmp_path):
    package = tmp_path / "arc_prize_2026"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "arc_token_batch.py").write_text(
        """
import argparse, json
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--challenges')
p.add_argument('--output',type=Path)
p.add_argument('--json',action='store_true')
a=p.parse_args()
a.output.parent.mkdir(parents=True,exist_ok=True)
a.output.write_text('{}\\n',encoding='ascii')
print(json.dumps({'task_count':1,'bytes':3,'output':str(a.output)}))
""".lstrip(),
        encoding="utf-8",
    )
    (package / "arc_flashcards.py").write_text(
        """
import argparse, json
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--tokens')
p.add_argument('--output',type=Path)
p.add_argument('--index',type=Path)
p.add_argument('--stages',nargs='*')
p.add_argument('--json',action='store_true')
a=p.parse_args()
card={
    'schema':'arc-flashcard/1',
    'stage':a.stages[0] if a.stages else 'ASSERT',
    'prompt':{'instruction':'No identifiers here'},
}
a.output.parent.mkdir(parents=True,exist_ok=True)
a.output.write_text(json.dumps(card)+'\\n',encoding='ascii')
summary={
    'schema':'arc-flashcard-index/1',
    'task_count':1,
    'card_count':1,
    'stage_counts':{card['stage']:1},
    'bytes':a.output.stat().st_size,
    'task_ids_in_prompts':False,
    'hidden_test_answers':0,
}
a.index.write_text(json.dumps(summary)+'\\n',encoding='ascii')
print(json.dumps(summary))
""".lstrip(),
        encoding="utf-8",
    )
    data = tmp_path / "data"
    data.mkdir()
    (data / "arc-agi_test_challenges.json").write_text("{}", encoding="utf-8")

    code = main(
        [
            "arc-cards",
            "--collection",
            "arc-test",
            "--arc-root",
            str(tmp_path),
            "--stages",
            "ASSERT_TO_COST",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    assert code == 0
    assert captured.err == ""
    payload = json.loads(captured.out)
    assert payload["schema_version"] == "geoseal_arc_flashcards_v1"
    assert payload["generated_tokens"] is True
    assert payload["generation"]["task_ids_in_prompts"] is False
    assert payload["generation"]["stage_counts"] == {"ASSERT_TO_COST": 1}
    assert payload["routing"]["stage_phases"] == {"ASSERT_TO_COST": ["ASSERT", "ACT", "MEM"]}
    assert payload["routing"]["faces"] == ["KO", "AV", "RU", "CA", "UM", "DR", "ARC_ATOMIC"]
    assert payload["routing"]["opcode_registry"] == "python.scbe.ca_opcode_table.OP_TABLE"
    card = json.loads((tmp_path / ".scratch" / "geoseal_arc_flashcards" / "arc-test" / "cards.jsonl").read_text())
    assert card["schema"] == "arc-flashcard/1"
    assert card["prompt"] == {"instruction": "No identifiers here"}
