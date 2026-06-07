from src.aetherbrowser.corridor_atlas import build_corridor_graph


def test_corridor_atlas_ranks_goal_relevant_low_risk_link() -> None:
    graph = build_corridor_graph(
        url="https://example.com",
        title="Example Home",
        text="Welcome to the product site.",
        goal="find contact page",
        links=[
            {"text": "Pricing", "href": "/pricing", "selector": "a.pricing"},
            {"text": "Contact", "href": "/contact", "selector": "a.contact"},
        ],
        buttons=[{"text": "Buy now", "selector": "button.buy"}],
    )

    payload = graph.to_dict()
    chosen = payload["chosen_corridor"]
    assert payload["schema_version"] == "aetherbrowser_corridor_atlas_v1"
    assert payload["safety_contract"] == "read_only_map_no_clicks_no_form_submission"
    assert chosen["visible_label"] == "Contact"
    assert chosen["risk_level"] == "low"
    assert chosen["target_hint"] == "https://example.com/contact"
    assert chosen["factor_address"]["encoding"] == "prime_factor_address_v1"
    assert chosen["factor_address"]["product"] == 2 * 17 * 43
    assert (
        chosen["factor_address"]["score_participation"]
        == "not_used_for_ranking_audit_label_only"
    )
    assert payload["ranker_contract"]["status"] == "HEURISTIC_SMOKE_TESTED"
    assert (
        payload["ranker_contract"]["factor_address_score_participation"]
        == "not_used_for_ranking_audit_label_only"
    )


def test_corridor_atlas_marks_payment_button_high_risk() -> None:
    graph = build_corridor_graph(
        url="https://shop.example/cart",
        title="Cart",
        text="Review your order before payment.",
        goal="review order",
        buttons=[
            {"text": "Checkout", "selector": "button.checkout"},
            {"text": "Continue shopping", "selector": "button.continue"},
        ],
    )

    edges = graph.to_dict()["edges"]
    checkout = next(edge for edge in edges if edge["visible_label"] == "Checkout")
    assert checkout["risk_level"] == "high"
    assert checkout["risk_penalty"] > 0
    assert graph.to_dict()["chosen_corridor"]["visible_label"] == "Continue shopping"


def test_corridor_atlas_token_overlap_does_not_claim_synonym_semantics() -> None:
    graph = build_corridor_graph(
        url="https://example.com",
        title="Fixture",
        goal="find contact page",
        links=[
            {"text": "Contact our team", "href": "/team", "selector": "x-node"},
            {"text": "Message the team", "href": "/support", "selector": "x-node"},
        ],
    )

    payload = graph.to_dict()
    assert payload["ranker_contract"]["goal_relevance_version"] == "token_overlap_v1"
    assert payload["chosen_corridor"]["visible_label"] == "Contact our team"
    keyword = next(
        edge for edge in payload["edges"] if edge["visible_label"] == "Contact our team"
    )
    synonym = next(
        edge for edge in payload["edges"] if edge["visible_label"] == "Message the team"
    )
    assert keyword["goal_relevance"] > synonym["goal_relevance"]


def test_corridor_atlas_rejects_zero_edges_limit() -> None:
    try:
        build_corridor_graph(url="https://example.com", title="Example", max_edges=0)
    except ValueError as exc:
        assert "max_edges" in str(exc)
    else:
        raise AssertionError("expected max_edges validation error")


def test_corridor_ranker_beats_risk_only_and_random_smoke_baselines() -> None:
    """Small labeled smoke: the corridor score must beat trivial routing baselines.

    This does not claim production generalization. It only prevents the read-only
    atlas from asserting "ranked safe move" without clearing a minimal baseline:
    risk-only first-safe choice and random choice over the same candidate set.
    """
    fixtures = [
        {
            "goal": "find contact page",
            "links": [
                {"text": "Pricing", "href": "/pricing", "selector": "a.pricing"},
                {"text": "Contact", "href": "/contact", "selector": "a.contact"},
                {"text": "Docs", "href": "/docs", "selector": "a.docs"},
            ],
            "buttons": [{"text": "Buy now", "selector": "button.buy"}],
            "expected": "Contact",
        },
        {
            "goal": "open api docs",
            "links": [
                {"text": "Blog", "href": "/blog", "selector": "a.blog"},
                {"text": "API Docs", "href": "/docs/api", "selector": "a.api"},
                {"text": "Status", "href": "/status", "selector": "a.status"},
            ],
            "buttons": [],
            "expected": "API Docs",
        },
        {
            "goal": "open security settings",
            "links": [],
            "buttons": [],
            "tabs": [
                {"text": "Profile", "selector": "[role='tab'][data-tab='profile']"},
                {"text": "Security", "selector": "[role='tab'][data-tab='security']"},
                {"text": "Billing", "selector": "[role='tab'][data-tab='billing']"},
            ],
            "expected": "Security",
        },
        {
            "goal": "find shipping help",
            "links": [
                {"text": "Returns", "href": "/help/returns", "selector": "a.returns"},
                {
                    "text": "Shipping Help",
                    "href": "/help/shipping",
                    "selector": "a.shipping",
                },
                {"text": "Account", "href": "/account", "selector": "a.account"},
            ],
            "buttons": [{"text": "Checkout", "selector": "button.checkout"}],
            "expected": "Shipping Help",
        },
    ]

    ranker_hits = 0
    risk_only_hits = 0
    random_expected_hits = 0.0
    for fixture in fixtures:
        graph = build_corridor_graph(
            url="https://example.com",
            title="Fixture",
            goal=fixture["goal"],
            links=fixture.get("links", []),
            buttons=fixture.get("buttons", []),
            tabs=fixture.get("tabs", []),
        )
        payload = graph.to_dict()
        assert payload["ranker_contract"]["status"] == "HEURISTIC_SMOKE_TESTED"
        edge_by_label = {edge["visible_label"]: edge for edge in payload["edges"]}
        candidate_labels = [
            item["text"]
            for bucket in ("links", "buttons", "tabs")
            for item in fixture.get(bucket, [])
            if item["text"] in edge_by_label
        ]
        first_safe = next(
            (
                label
                for label in candidate_labels
                if edge_by_label[label]["risk_level"] == "low"
            ),
            candidate_labels[0],
        )

        ranker_hits += (
            payload["chosen_corridor"]["visible_label"] == fixture["expected"]
        )
        risk_only_hits += first_safe == fixture["expected"]
        random_expected_hits += 1.0 / len(candidate_labels)

    assert ranker_hits == len(fixtures)
    assert risk_only_hits < ranker_hits
    assert random_expected_hits < ranker_hits
