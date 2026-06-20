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


def test_repair_generator_uses_execution_feedback_to_fix(monkeypatch):
    # bad code first -> public fails -> repair prompt includes the failure -> good code -> passes.
    # proves the loop FIRES and acts on execution feedback (not a no-op).
    calls = []

    def fake_chat(messages, **kw):
        calls.append(messages[0]["content"])
        return "def f():\n    return 0" if len(calls) == 1 else "def add(a, b):\n    return a + b"

    monkeypatch.setattr(fg, "_chat", fake_chat)
    gen = fg.make_repair_generator(model="mock", rounds=2)
    out = gen({"prompt": "add a and b", "test_list": ["assert add(1,2)==3", "assert add(5,5)==10"], "test_imports": []})
    assert len(calls) == 2  # the loop retried after the public failure
    assert "FAILED" in calls[1]  # the retry prompt carried the execution feedback
    assert "def add" in out  # and the repaired code is what's returned


def test_repair_generator_only_sees_public_not_hidden(monkeypatch):
    # the repair loop must never receive the hidden tests -- honest lift, not leakage
    seen = []

    def fake_chat(messages, **kw):
        seen.append(messages[0]["content"])
        return "def f():\n    return 1"  # always wrong -> forces every repair round to run

    monkeypatch.setattr(fg, "_chat", fake_chat)
    gen = fg.make_repair_generator(model="mock", rounds=2, public_k=1)
    gen({"prompt": "p", "test_list": ["assert f()==1", "assert f()==2  # HIDDEN"], "test_imports": []})
    assert not any("HIDDEN" in s for s in seen)  # the hidden assert never reached the model


def test_stuck_prior_detector_escalates_to_restructure(monkeypatch):
    # model returns the SAME failing code on retry -> detector fires -> next prompt says STUCK and
    # demands a different approach; when the model finally complies, the fix lands.
    calls = []

    def fake_chat(messages, **kw):
        content = messages[0]["content"]
        calls.append(content)
        if "STUCK" in content:
            return "def add(a, b):\n    return a + b"  # the restructured (correct) attempt
        return "def add(a, b):\n    return a - b"  # the stuck prior: same wrong code, repeated

    monkeypatch.setattr(fg, "_chat", fake_chat)
    gen = fg.make_repair_generator(model="mock", rounds=4)
    out = gen({"prompt": "add a and b", "test_list": ["assert add(1,2)==3", "assert add(2,2)==4"], "test_imports": []})
    assert any("STUCK" in c for c in calls)  # the detector escalated after the repeated failure
    assert "a + b" in out  # and the restructure broke the loop


def test_norm_code_ignores_cosmetic_differences():
    a = "def f(x):\n    return x + 1\n"
    b = "def f(x):\n\n    # a comment\n    return x + 1\n"
    assert fg._norm_code(a) == fg._norm_code(b)
