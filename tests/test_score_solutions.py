"""score_solutions: a file-backed model generator scores correct solutions as pass,
wrong ones as fail, and missing ones as fail (no silent pass) -- proven on the fixture."""

import json

from python.helm.public_bench import func_name, load_fixture, run_public_bench
from python.helm.score_solutions import solutions_generator


def _write(tmp_path, name, obj):
    p = tmp_path / name
    p.write_text(json.dumps(obj), encoding="utf-8")
    return str(p)


def test_correct_solutions_verify_and_wrong_fail(tmp_path):
    probs = load_fixture()
    correct = {str(p["task_id"]): p["code"] for p in probs}
    wrong = {str(p["task_id"]): "def %s(*a, **k):\n    return None\n" % func_name(p) for p in probs}

    cs = run_public_bench(probs, generator=solutions_generator(_write(tmp_path, "ok.json", correct)), public_k=1)
    ws = run_public_bench(probs, generator=solutions_generator(_write(tmp_path, "bad.json", wrong)), public_k=1)

    assert cs["attempted"] > 0
    assert cs["verified"] == cs["attempted"]  # correct solutions -> all pass public+hidden
    assert ws["verified"] == 0  # wrong stubs -> none pass (the floor)


def test_list_form_and_missing_falls_back_to_floor(tmp_path):
    probs = load_fixture()
    # list form, and one task_id deliberately absent -> that one must fail, not silently pass
    listed = [{"task_id": probs[0]["task_id"], "code": probs[0]["code"]}]
    s = run_public_bench(probs, generator=solutions_generator(_write(tmp_path, "list.json", listed)), public_k=1)
    assert s["verified"] == 1  # only the one provided (and correct) verifies; the rest fall to the floor
