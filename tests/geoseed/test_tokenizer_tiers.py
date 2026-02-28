from src.geoseed.tokenizer_tiers import GeoSeedTokenizerTiers, TokenizerTier


def test_tier_f1_dispatch_for_training_bytes():
    tiers = GeoSeedTokenizerTiers()
    result = tiers.encode(TokenizerTier.F1, data=b"\x41")

    assert result.item_count == 8
    assert result.metadata["layer_path"] == [1, 2, 3, 4, 5]


def test_tier_f2_dispatch_for_public_tokens():
    tiers = GeoSeedTokenizerTiers()
    result = tiers.encode(
        TokenizerTier.F2,
        tokens_by_tongue={"KO": ["alpha", "beta"], "ca": ["gamma"]},
        run_id="f2-test",
    )

    assert result.item_count == 3
    assert result.metadata["run_id"] == "f2-test"

    tongues = sorted({bit.tongue for bit in result.payload})
    assert tongues == ["CA", "KO"]


def test_tier_f3_identity_genesis_verification():
    tiers = GeoSeedTokenizerTiers()
    result = tiers.encode(
        TokenizerTier.F3,
        agent_name="agent-geoseed",
        payload=b"genesis-payload",
        requested_tongues=["UM", "KO"],
    )

    identity = result.payload
    assert result.item_count == 1
    assert identity.origin_tongue == "UM"
    assert tiers.identity_genesis.verify_identity(identity) is True
