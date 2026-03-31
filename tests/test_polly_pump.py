from src.polly_pump import BundleRetriever, RetrievedBundle, sense, stabilize


def test_sense_builds_packet_from_lore_prompt() -> None:
    packet = sense(
        "Explain the Aethermoor lore and Polly identity in the Everweave novel with sacred tongues."
    )

    assert len(packet.tongue_profile) == 6
    assert len(packet.null_pattern) == 6
    assert packet.canon == "lore"
    assert packet.dominant_tongue in {"KO", "UM"}
    assert packet.governance == "ALLOW"
    assert packet.source_roots


def test_retriever_prefers_bundle_with_matching_shape() -> None:
    packet = sense("Polly lore novel sacred tongues Everweave identity magic")
    retriever = BundleRetriever(
        [
            RetrievedBundle(
                bundle_id="lore-1",
                text="Everweave canon bundle for Polly and the sacred tongues.",
                tongue_profile=list(packet.tongue_profile),
                canon=packet.canon,
                emotion=packet.emotion,
                governance=packet.governance,
                null_pattern=packet.null_pattern,
                source_root="artifacts/notion_export_unpacked",
            ),
            RetrievedBundle(
                bundle_id="security-1",
                text="Adversarial override bypass admin mode exploit bundle.",
                tongue_profile=[0.0, 0.0, 0.1, 0.2, 0.95, 0.0],
                canon="security",
                emotion="adversarial",
                governance="DENY",
                null_pattern="##_#__",
                source_root="tests/adversarial",
            ),
        ]
    )

    ranked = retriever.retrieve(packet, top_k=2)

    assert ranked[0].bundle_id == "lore-1"
    assert ranked[0].score > ranked[1].score


def test_stabilize_emits_structured_prestate_block() -> None:
    packet = sense("Explain the Everweave lore and sacred tongues for Polly.")
    bundles = [
        RetrievedBundle(
            bundle_id="lore-1",
            text="Polly is anchored in the Everweave canon and the six sacred tongues.",
            tongue_profile=list(packet.tongue_profile),
            canon=packet.canon,
            emotion=packet.emotion,
            governance=packet.governance,
            null_pattern=packet.null_pattern,
            source_root="docs/map-room/scbe_source_roots.md",
            score=0.99,
        )
    ]

    block = stabilize(packet, bundles)

    assert "[POLLY_PUMP_PRESTATE]" in block
    assert "dominant_tongue=" in block
    assert "[BUNDLES]" in block
    assert "bundle_id" not in block
    assert "id=lore-1" in block
    assert "Everweave canon" in block
