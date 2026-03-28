"""Tests for hydra/color_dimension.py — Frequency-Based Flow Isolation."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hydra.color_dimension import (
    BAND_CENTERS,
    ColorBand,
    ColorChannel,
    ColorNode,
    MultiColorTag,
    PHI,
    PROVIDER_BANDS,
    SpectralFlowRouter,
    SPEED_OF_LIGHT_NM_THZ,
    SpectrumAllocator,
    TONGUE_AUDIO_HZ,
    TONGUE_INTERVALS,
    TONGUE_PHASES,
    TONGUE_WAVELENGTHS,
    TONGUE_WEIGHTS,
    channel_for_provider,
    channel_for_task,
    channel_for_tongue,
    group_by_color_band,
    sort_by_disorganized_order,
)

# ── ColorChannel ──────────────────────────────────────────────────


class TestColorChannel:
    def test_frequency_from_wavelength(self):
        ch = ColorChannel(wavelength_nm=500.0)
        expected = SPEED_OF_LIGHT_NM_THZ / 500.0
        assert abs(ch.frequency_thz - expected) < 0.01

    def test_frequency_zero_wavelength(self):
        ch = ColorChannel(wavelength_nm=0)
        assert ch.frequency_thz == 0.0

    def test_hue_violet(self):
        ch = ColorChannel(wavelength_nm=380.0)
        assert ch.hue_degrees == 270.0

    def test_hue_red(self):
        ch = ColorChannel(wavelength_nm=780.0)
        assert ch.hue_degrees == 0.0

    def test_tongue_weight_default(self):
        ch = ColorChannel(wavelength_nm=500.0)  # default tongue="KO"
        assert ch.tongue_weight == 1.0

    def test_tongue_weight_dr(self):
        ch = ColorChannel(wavelength_nm=500.0, tongue="DR")
        assert abs(ch.tongue_weight - PHI**5) < 0.01

    def test_composite_frequency(self):
        ch = ColorChannel(wavelength_nm=500.0, tongue="AV")
        expected = (SPEED_OF_LIGHT_NM_THZ / 500.0) * PHI
        assert abs(ch.composite_frequency - expected) < 0.01

    def test_spectral_distance_same_tongue(self):
        a = ColorChannel(wavelength_nm=400.0)
        b = ColorChannel(wavelength_nm=700.0)
        dist = a.spectral_distance(b)
        assert abs(dist - 300.0 / 400.0) < 0.01

    def test_spectral_distance_identical(self):
        a = ColorChannel(wavelength_nm=500.0, tongue="RU")
        assert a.spectral_distance(a) == 0.0

    def test_spectral_distance_cross_tongue(self):
        a = ColorChannel(wavelength_nm=500.0, tongue="KO")
        b = ColorChannel(wavelength_nm=500.0, tongue="DR")
        # Same wavelength but different tongue -> nonzero composite distance
        assert a.spectral_distance(b) > 0.5

    def test_tag_overlap_identical(self):
        tags = frozenset({"a", "b"})
        a = ColorChannel(wavelength_nm=400.0, tags=tags)
        b = ColorChannel(wavelength_nm=500.0, tags=tags)
        assert a.tag_overlap(b) == 1.0

    def test_tag_overlap_disjoint(self):
        a = ColorChannel(wavelength_nm=400.0, tags=frozenset({"a"}))
        b = ColorChannel(wavelength_nm=500.0, tags=frozenset({"b"}))
        assert a.tag_overlap(b) == 0.0

    def test_tag_overlap_empty(self):
        a = ColorChannel(wavelength_nm=400.0)
        b = ColorChannel(wavelength_nm=500.0)
        assert a.tag_overlap(b) == 0.0

    def test_to_rgb_violet(self):
        ch = ColorChannel(wavelength_nm=400.0)
        r, g, b = ch.to_rgb()
        assert r > 0 and b > 0 and g == 0  # violet = R+B, no green

    def test_to_rgb_green(self):
        ch = ColorChannel(wavelength_nm=540.0)
        r, g, b = ch.to_rgb()
        assert g > r and g > b  # green dominant

    def test_hex_color_format(self):
        ch = ColorChannel(wavelength_nm=500.0)
        hex_str = ch.hex_color()
        assert hex_str.startswith("#")
        assert len(hex_str) == 7


# ── ColorBand & Lookups ──────────────────────────────────────────


class TestColorBands:
    def test_all_bands_have_centers(self):
        for band in ColorBand:
            assert band in BAND_CENTERS

    def test_centers_monotonically_increasing(self):
        wls = [BAND_CENTERS[b] for b in ColorBand]
        assert wls == sorted(wls)

    def test_all_providers_mapped(self):
        for provider in ["claude", "gpt", "gemini", "grok", "hf", "local"]:
            assert provider in PROVIDER_BANDS

    def test_channel_for_provider(self):
        ch = channel_for_provider("claude", tongue="RU", tags={"test"})
        assert ch.wavelength_nm == BAND_CENTERS[ColorBand.VIOLET]
        assert ch.tongue == "RU"
        assert "test" in ch.tags

    def test_channel_for_task(self):
        ch = channel_for_task("research")
        assert ch.wavelength_nm == BAND_CENTERS[ColorBand.CYAN]

    def test_channel_for_unknown_provider(self):
        ch = channel_for_provider("unknown_model")
        assert ch.wavelength_nm == BAND_CENTERS[ColorBand.CYAN]  # default


# ── MultiColorTag ─────────────────────────────────────────────────


class TestMultiColorTag:
    def test_empty_tag(self):
        tag = MultiColorTag()
        assert tag.dominant_channel is None
        assert tag.all_tags == frozenset()
        assert tag.average_wavelength == 550.0

    def test_add_channels(self):
        tag = MultiColorTag()
        tag.add_channel(channel_for_provider("claude"))
        tag.add_channel(channel_for_provider("gpt"))
        assert len(tag.channels) == 2
        assert "claude" in tag.all_tags
        assert "gpt" in tag.all_tags

    def test_dominant_channel(self):
        tag = MultiColorTag(
            [
                channel_for_provider("claude"),  # 400nm, highest freq
                channel_for_provider("hf"),  # 700nm, lowest freq
            ]
        )
        dom = tag.dominant_channel
        assert dom is not None
        assert dom.wavelength_nm == 400.0  # shortest wl = highest freq

    def test_average_wavelength_weighted(self):
        tag = MultiColorTag(
            [
                ColorChannel(wavelength_nm=400.0, tongue="KO"),  # weight 1.0
                ColorChannel(wavelength_nm=700.0, tongue="KO"),  # weight 1.0
            ]
        )
        assert abs(tag.average_wavelength - 550.0) < 1.0  # simple average

    def test_composite_rgb(self):
        tag = MultiColorTag([channel_for_provider("claude")])
        r, g, b = tag.composite_rgb
        assert 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255

    def test_is_visible_on_same_channel(self):
        ch = channel_for_provider("claude")
        tag = MultiColorTag([ch])
        assert tag.is_visible_on(ch)

    def test_not_visible_on_distant_channel(self):
        tag = MultiColorTag([channel_for_provider("claude")])  # 400nm
        far = channel_for_provider("hf")  # 700nm
        assert not tag.is_visible_on(far, threshold=0.05)


# ── ColorNode ─────────────────────────────────────────────────────


class TestColorNode:
    def test_empty_node_accepts(self):
        node = ColorNode("test")
        assert node.can_accept_flow("a", channel_for_provider("claude"))

    def test_white_node_accepts_all(self):
        node = ColorNode("white", white=True)
        ch = channel_for_provider("claude")
        node.enter_flow("a", ch)
        # Even identical channel is accepted on white node
        assert node.can_accept_flow("b", ch)

    def test_different_providers_can_share_node(self):
        """Claude (400nm) and GPT (455nm) should be far enough apart."""
        node = ColorNode("shared")
        claude = channel_for_provider("claude")
        gpt = channel_for_provider("gpt")
        node.enter_flow("a", claude)
        assert node.can_accept_flow("b", gpt)

    def test_close_channels_collide(self):
        node = ColorNode("narrow")
        ch_a = ColorChannel(wavelength_nm=400.0)
        ch_b = ColorChannel(wavelength_nm=405.0)  # only 5nm apart
        node.enter_flow("a", ch_a)
        assert not node.can_accept_flow("b", ch_b, isolation_threshold=0.05)

    def test_exit_flow_frees_slot(self):
        node = ColorNode("test")
        ch_a = ColorChannel(wavelength_nm=400.0)
        ch_b = ColorChannel(wavelength_nm=405.0)
        node.enter_flow("a", ch_a)
        assert not node.can_accept_flow("b", ch_b, isolation_threshold=0.05)
        node.exit_flow("a")
        assert node.can_accept_flow("b", ch_b, isolation_threshold=0.05)

    def test_allowed_bands_filter(self):
        node = ColorNode("restricted", allowed_bands={ColorBand.VIOLET, ColorBand.BLUE})
        assert node.can_accept_flow("a", channel_for_provider("claude"))  # VIOLET
        assert not node.can_accept_flow("b", channel_for_provider("hf"))  # RED

    def test_same_flow_no_collision(self):
        node = ColorNode("test")
        ch = ColorChannel(wavelength_nm=400.0)
        node.enter_flow("a", ch)
        assert node.can_accept_flow("a", ch)  # same flow_id = no collision


# ── SpectrumAllocator ─────────────────────────────────────────────


class TestSpectrumAllocator:
    def test_allocate_preferred(self):
        alloc = SpectrumAllocator()
        ch = alloc.allocate("f1", preferred_band=ColorBand.GREEN)
        assert ch.wavelength_nm == BAND_CENTERS[ColorBand.GREEN]

    def test_no_duplicate_allocation(self):
        alloc = SpectrumAllocator()
        ch1 = alloc.allocate("f1", preferred_band=ColorBand.GREEN)
        ch2 = alloc.allocate("f1", preferred_band=ColorBand.RED)
        assert ch1 is ch2  # same flow_id returns cached channel

    def test_nearby_allocation_shifts(self):
        alloc = SpectrumAllocator(min_separation_nm=30)
        ch1 = alloc.allocate("f1", preferred_band=ColorBand.GREEN)  # 540nm
        ch2 = alloc.allocate("f2", preferred_band=ColorBand.GREEN)  # should shift
        assert abs(ch1.wavelength_nm - ch2.wavelength_nm) >= 30

    def test_deallocate(self):
        alloc = SpectrumAllocator()
        alloc.allocate("f1", preferred_band=ColorBand.GREEN)
        assert "f1" in alloc.allocated
        alloc.deallocate("f1")
        assert "f1" not in alloc.allocated

    def test_utilization(self):
        alloc = SpectrumAllocator(min_separation_nm=20)
        assert alloc.utilization() == 0.0
        alloc.allocate("f1")
        assert alloc.utilization() > 0.0

    def test_many_allocations(self):
        alloc = SpectrumAllocator(min_separation_nm=10)
        channels = []
        for i in range(20):
            ch = alloc.allocate(f"flow_{i}")
            channels.append(ch)
        # All channels should be unique
        wavelengths = [ch.wavelength_nm for ch in channels]
        assert len(set(wavelengths)) == 20


# ── Sorting & Grouping ───────────────────────────────────────────


class TestSortingGrouping:
    def test_disorganized_order_monotonic(self):
        items = [
            MultiColorTag([channel_for_task("debate")]),  # 617nm
            MultiColorTag([channel_for_task("research")]),  # 500nm
            MultiColorTag([channel_for_task("draft")]),  # 455nm
            MultiColorTag([channel_for_task("govern")]),  # 400nm
        ]
        sorted_items = sort_by_disorganized_order(items)
        wavelengths = [it.average_wavelength for it in sorted_items]
        assert wavelengths == sorted(wavelengths)

    def test_group_by_color_band(self):
        items = [
            MultiColorTag([channel_for_task("research")]),  # cyan
            MultiColorTag([channel_for_task("draft")]),  # blue
            MultiColorTag([channel_for_task("embed")]),  # red
        ]
        groups = group_by_color_band(items)
        assert len(groups["cyan"]) == 1
        assert len(groups["blue"]) == 1
        assert len(groups["red"]) == 1
        assert len(groups["green"]) == 0

    def test_empty_sort(self):
        assert sort_by_disorganized_order([]) == []

    def test_empty_group(self):
        groups = group_by_color_band([])
        assert all(len(v) == 0 for v in groups.values())


# ── Sacred Tongue Weights ─────────────────────────────────────────


class TestTongueWeights:
    def test_phi_scaling(self):
        weights = list(TONGUE_WEIGHTS.values())
        for i in range(1, len(weights)):
            ratio = weights[i] / weights[i - 1]
            assert abs(ratio - PHI) < 0.001

    def test_ko_is_one(self):
        assert TONGUE_WEIGHTS["KO"] == 1.0

    def test_six_tongues(self):
        assert len(TONGUE_WEIGHTS) == 6
        assert set(TONGUE_WEIGHTS.keys()) == {"KO", "AV", "RU", "CA", "UM", "DR"}


# ── Audio-to-Visible Bridge ──────────────────────────────────────


class TestAudioVisibleBridge:
    def test_tongue_wavelengths_in_visible_range(self):
        for tongue, wl in TONGUE_WAVELENGTHS.items():
            assert 380 <= wl <= 680, f"{tongue} wavelength {wl} out of visible range"

    def test_ko_at_violet_dr_at_red(self):
        assert TONGUE_WAVELENGTHS["KO"] == 380.0
        assert TONGUE_WAVELENGTHS["DR"] == 680.0

    def test_wavelengths_monotonically_increase(self):
        tongues = ["KO", "AV", "RU", "CA", "UM", "DR"]
        wls = [TONGUE_WAVELENGTHS[t] for t in tongues]
        assert wls == sorted(wls)

    def test_musical_intervals_match_spec(self):
        assert TONGUE_INTERVALS["KO"] == 1.0
        assert TONGUE_INTERVALS["AV"] == 9 / 8
        assert TONGUE_INTERVALS["UM"] == 3 / 2

    def test_audio_hz_phi_scaled(self):
        assert abs(TONGUE_AUDIO_HZ["KO"] - 440.0) < 0.01
        assert abs(TONGUE_AUDIO_HZ["AV"] - 440.0 * PHI) < 0.01

    def test_tongue_phases_60_degree_separation(self):
        assert TONGUE_PHASES["KO"] == 0.0
        assert TONGUE_PHASES["AV"] == 60.0
        assert TONGUE_PHASES["DR"] == 300.0

    def test_channel_for_tongue(self):
        ch = channel_for_tongue("RU", tags={"security"})
        assert ch.tongue == "RU"
        assert abs(ch.wavelength_nm - TONGUE_WAVELENGTHS["RU"]) < 0.01
        assert "security" in ch.tags

    def test_tongue_channels_spectrally_separated(self):
        ko = channel_for_tongue("KO")
        dr = channel_for_tongue("DR")
        dist = ko.spectral_distance(dr)
        # KO=380nm, DR=680nm, cross-tongue with different tongue strings
        # -> composite frequency distance; ~0.49 normalized
        assert dist > 0.4  # well separated across the spectrum


# ── Spectral Flow Router ─────────────────────────────────────────


class TestSpectralFlowRouter:
    @staticmethod
    def _build_router() -> SpectralFlowRouter:
        router = SpectralFlowRouter(
            isolation_threshold=0.1, hyperbolic_min_separation=0.3
        )
        router.add_node("a", (0.00, 0.00))
        router.add_node("b", (0.20, 0.00))
        router.add_node("c", (0.40, 0.00))
        router.add_node("m", (0.10, 0.10), designated_merge=True)  # explicit merge node
        router.add_node("n", (0.12, 0.11))  # near m for hyperbolic-proximity checks
        router.add_node("x", (-0.40, -0.20))
        router.add_node("y", (0.45, 0.25))

        router.add_edge("a", "b")
        router.add_edge("b", "c")
        router.add_edge("a", "m")
        router.add_edge("m", "c")
        router.add_edge("a", "n")
        router.add_edge("n", "c")
        router.add_edge("x", "m")
        router.add_edge("m", "y")
        return router

    def test_overlap_rejected_on_non_merge_node(self):
        router = self._build_router()
        close_a = ColorChannel(wavelength_nm=400.0)
        close_b = ColorChannel(wavelength_nm=405.0)  # spectrally close

        assert router.route("f1", ["a", "b", "c"], close_a).allowed
        denied = router.route("f2", ["a", "b", "c"], close_b)
        assert not denied.allowed
        assert any(reason.startswith("node_overlap:") for reason in denied.reasons)

    def test_overlap_allowed_at_designated_merge_node(self):
        router = self._build_router()
        close_a = ColorChannel(wavelength_nm=400.0)
        close_b = ColorChannel(wavelength_nm=405.0)

        assert router.route("f1", ["a", "m", "c"], close_a).allowed
        # Shared node is only m, which is designated merge
        allowed = router.route("f2", ["x", "m", "y"], close_b)
        assert allowed.allowed

    def test_far_spectral_channels_can_share_non_merge_path(self):
        router = self._build_router()
        violet = ColorChannel(wavelength_nm=400.0)
        red = ColorChannel(wavelength_nm=700.0)

        assert router.route("f1", ["a", "b", "c"], violet).allowed
        allowed = router.route("f2", ["a", "b", "c"], red)
        assert allowed.allowed

    def test_hyperbolic_proximity_blocks_near_parallel_paths(self):
        router = self._build_router()
        close_a = ColorChannel(wavelength_nm=400.0)
        close_b = ColorChannel(wavelength_nm=405.0)

        assert router.route("f1", ["a", "m", "c"], close_a).allowed
        denied = router.route("f2", ["a", "n", "c"], close_b)
        assert not denied.allowed
        assert any(
            reason.startswith("hyperbolic_proximity:") for reason in denied.reasons
        )

    def test_disconnected_path_rejected(self):
        router = self._build_router()
        channel = ColorChannel(wavelength_nm=500.0)
        check = router.can_route("f1", ["a", "c"], channel)  # no direct edge
        assert not check.allowed
        assert "disconnected_or_unknown_path" in check.reasons

    def test_unroute_frees_path(self):
        router = self._build_router()
        close_a = ColorChannel(wavelength_nm=400.0)
        close_b = ColorChannel(wavelength_nm=405.0)

        assert router.route("f1", ["a", "b", "c"], close_a).allowed
        assert not router.route("f2", ["a", "b", "c"], close_b).allowed
        router.unroute("f1")
        assert router.route("f2", ["a", "b", "c"], close_b).allowed

    def test_poincare_distance_positive(self):
        d = SpectralFlowRouter.poincare_distance((0.0, 0.0), (0.2, 0.0))
        assert d > 0.0
