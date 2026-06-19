"""free_generator: code-stripping, the model->verify integration (mocked endpoint),
and honest failure handling -- proven without needing a live model running."""

from python.helm import free_generator as fg
from python.helm.public_bench import load_fixture, run_public_bench


def test_strip_to_code_handles_fences_and_bare():
    assert fg.strip_to_code("```python\ndef f():\n    return 1\n```") == "def f():\n    return 1"
    assert fg.strip_to_code("def g():\n    return 2") == "def g():\n    return 2"


def test_generator_with_mocked_correct_model(monkeypatch):
    probs = load_fixture()

    def fake_chat(messages, **kw):
        prompt = messages[0]["content"]
        for p in probs:
            if p["prompt"] in prompt:  # full prompt is unique (24-char prefixes collide)
                return "```python\n" + p["code"] + "\n```"
        return "def x():\n    return None\n"

    monkeypatch.setattr(fg, "_chat", fake_chat)
    s = run_public_bench(probs, generator=fg.make_generator(), public_k=1)
    assert s["attempted"] > 0
    assert s["verified"] == s["attempted"]  # a (mocked) correct model -> all pass public+hidden


def test_endpoint_failure_fails_verification_not_silently_wrong(monkeypatch):
    probs = load_fixture()

    def boom(messages, **kw):
        raise ConnectionError("no model running")

    monkeypatch.setattr(fg, "_chat", boom)
    s = run_public_bench(probs, generator=fg.make_generator(), public_k=1)
    assert s["verified"] == 0  # a dead endpoint yields a stub that FAILS -- never ships wrong code
