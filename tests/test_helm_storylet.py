"""Storylet engine: derived-factor gating and salience selection."""

from python.helm import Step, Storylet, flag, run_storylets


def test_salience_picks_the_more_salient_first():
    order = []

    def make_storylet(name, salience):
        def action(objective, context):
            order.append(name)
            return {"v": 1}

        return Storylet(Step(name, "x", action), salience=lambda factors, value=salience: value)

    run = run_storylets("x", [make_storylet("a", 2.0), make_storylet("b", 1.0)])
    assert run.approved == 2
    assert order == ["a", "b"]


def test_derived_factor_gates_a_storylet():
    seed = Storylet(Step("seed", "x", lambda objective, context: {"ok": True}))
    gate = Storylet(Step("gate", "x", lambda objective, context: {"done": True}, criteria=(flag("threshold_met"),)))

    def derive(ctx):
        return {"threshold_met": len(ctx["results"]) >= 1}

    run = run_storylets("x", [seed, gate], derive=derive)
    assert run.approved == 2 and run.fully_autonomous
    order = [receipt.step for receipt in run.receipts]
    assert order.index("seed") < order.index("gate")


def test_unreachable_storylet_is_denied():
    gate = Storylet(Step("gate", "x", lambda objective, context: 1, criteria=(flag("never"),)))
    run = run_storylets("x", [gate])
    assert run.denied_count == 1 and run.approved == 0


def test_storylet_run_is_deterministic():
    def make_storylets():
        return [
            Storylet(Step("a", "x", lambda objective, context: {"v": 1}), salience=lambda factors: 1.0),
            Storylet(Step("b", "x", lambda objective, context: {"v": 2}), salience=lambda factors: 2.0),
        ]

    assert run_storylets("s", make_storylets()).chain_digest == run_storylets("s", make_storylets()).chain_digest
