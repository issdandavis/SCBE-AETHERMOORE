"""Tests for hydra/spectral_langgraph.py — Spectral LangGraph integration."""

import sys
import os

import numpy as np
import pytest

pytest.importorskip("langgraph", reason="langgraph not installed")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hydra.spectral_langgraph import (
    SpectralMixer,
    SpectralState,
    SpectralStateGraph,
    build_article_graph,
    build_research_graph,
)
from hydra.color_dimension import ColorBand


# ── SpectralMixer (FNet) ─────────────────────────────────────────


class TestSpectralMixer:
    def test_text_to_signal_length(self):
        sig = SpectralMixer.text_to_signal("hello world", length=64)
        assert sig.shape == (64,)

    def test_text_to_signal_padding(self):
        sig = SpectralMixer.text_to_signal("hi", length=16)
        assert sig[0] > 0  # 'h' has nonzero ordinal
        assert sig[10] == 0.0  # padded

    def test_roundtrip_fft(self):
        sig = SpectralMixer.text_to_signal("test signal for FFT roundtrip", length=128)
        spec = SpectralMixer.signal_to_spectrum(sig)
        recovered = SpectralMixer.spectrum_to_signal(spec, length=128)
        np.testing.assert_allclose(sig, recovered, atol=1e-10)

    def test_spectral_energy_sums_to_one(self):
        sig = SpectralMixer.text_to_signal("energy test signal", length=64)
        spec = SpectralMixer.signal_to_spectrum(sig)
        energy = SpectralMixer.spectral_energy(spec)
        assert abs(energy["low"] + energy["mid"] + energy["high"] - 1.0) < 0.01

    def test_spectral_energy_empty(self):
        spec = np.zeros(32, dtype=np.complex128)
        energy = SpectralMixer.spectral_energy(spec)
        assert energy["total"] == 0.0

    def test_merge_spectra_preserves_structure(self):
        s1 = SpectralMixer.signal_to_spectrum(SpectralMixer.text_to_signal("alpha", 64))
        s2 = SpectralMixer.signal_to_spectrum(SpectralMixer.text_to_signal("beta", 64))
        merged = SpectralMixer.merge_spectra({"a": s1, "b": s2})
        assert merged.shape == s1.shape

    def test_merge_spectra_empty(self):
        result = SpectralMixer.merge_spectra({})
        assert len(result) == 0

    def test_mix_outputs_basic(self):
        outputs = {"agent1": "Hello world", "agent2": "World hello"}
        result = SpectralMixer.mix_outputs(outputs, signal_length=64)
        assert result["agent_count"] == 2
        assert "agent1" in result["per_agent_energy"]
        assert "merged_energy" in result

    def test_mix_outputs_with_tongue_weights(self):
        outputs = {"claude": "Architecture analysis", "gpt": "Draft content"}
        result = SpectralMixer.mix_outputs(
            outputs,
            tongue_weights={"claude": "DR", "gpt": "AV"},
            signal_length=64,
        )
        assert result["agent_count"] == 2
        # DR weight >> AV weight, so merged should lean toward claude's spectrum
        assert "merged_energy" in result

    def test_parseval_theorem(self):
        """Time-domain energy should equal frequency-domain energy (rfft normalization)."""
        n = 128
        sig = SpectralMixer.text_to_signal("Parseval test signal", length=n)
        time_energy = float(np.sum(sig**2))
        # Use full FFT for clean Parseval check
        spec_full = np.fft.fft(sig)
        freq_energy = float(np.sum(np.abs(spec_full) ** 2)) / n
        assert abs(time_energy - freq_energy) < 1e-6


# ── SpectralStateGraph ────────────────────────────────────────────


class TestSpectralStateGraph:
    def test_add_node(self):
        g = SpectralStateGraph(SpectralState)
        g.add_spectral_node("test", lambda s: {"output": "ok"}, band=ColorBand.GREEN)
        assert "test" in g._node_configs
        assert "test" in g._allocator.allocated

    def test_add_edge(self):
        g = SpectralStateGraph(SpectralState)
        g.add_spectral_node("a", lambda s: {})
        g.add_spectral_node("b", lambda s: {})
        g.add_edge("a", "b")
        assert ("a", "b") in g._edges

    def test_prism_node_registered_as_merge(self):
        g = SpectralStateGraph(SpectralState)
        g.add_spectral_node("hub", lambda s: {}, prism=True)
        assert "hub" in g._router.designated_merge_nodes

    def test_auto_position(self):
        g = SpectralStateGraph(SpectralState)
        g.add_spectral_node("a", lambda s: {})
        g.add_spectral_node("b", lambda s: {})
        pos_a = g._node_configs["a"].poincare_position
        pos_b = g._node_configs["b"].poincare_position
        # Different positions
        assert pos_a != pos_b
        # Inside unit disk
        assert pos_a[0] ** 2 + pos_a[1] ** 2 < 1.0
        assert pos_b[0] ** 2 + pos_b[1] ** 2 < 1.0

    def test_spectrum_report(self):
        g = SpectralStateGraph(SpectralState)
        g.add_spectral_node("a", lambda s: {}, band=ColorBand.VIOLET)
        g.add_spectral_node("b", lambda s: {}, band=ColorBand.RED, prism=True)
        g.add_edge("a", "b")
        report = g.get_spectrum_report()
        assert report["nodes"] == 2
        assert report["edges"] == 1
        assert "b" in report["prism_nodes"]
        assert "a" in report["channels_allocated"]

    def test_tongue_assignment_persists(self):
        g = SpectralStateGraph(SpectralState)
        g.add_spectral_node("gov", lambda s: {}, tongue="UM", band=ColorBand.VIOLET)
        ch = g._allocator.allocated["gov"]
        assert ch.tongue == "UM"


# ── End-to-End Execution ──────────────────────────────────────────


class TestEndToEnd:
    @staticmethod
    def _initial_state(topic="test"):
        return {
            "topic": topic,
            "messages": [],
            "outputs": {},
            "artifacts": {},
            "_spectral_channels": {},
            "_spectral_history": [],
            "_fft_spectrum": {},
            "_route_checks": [],
            "_quality_scores": {},
        }

    def test_article_graph_executes(self):
        g = build_article_graph("AI safety")
        app = g.compile()
        result = app.invoke(self._initial_state("AI safety"))
        assert len(result["_spectral_history"]) == 6
        assert "merge" in result["outputs"]
        assert result["_fft_spectrum"].get("agent_count", 0) > 0

    def test_research_graph_executes(self):
        g = build_research_graph("quantum computing")
        app = g.compile()
        result = app.invoke(self._initial_state("quantum computing"))
        assert len(result["_spectral_history"]) == 4
        assert "synthesis" in result["outputs"]

    def test_spectral_channels_populated(self):
        g = build_article_graph("test")
        app = g.compile()
        result = app.invoke(self._initial_state("test"))
        channels = result["_spectral_channels"]
        assert len(channels) >= 5  # research, outline, draft, challenge, edit, merge
        # Each channel has wavelength
        for nid, ch_info in channels.items():
            assert "wavelength_nm" in ch_info
            assert 380 <= ch_info["wavelength_nm"] <= 780

    def test_prism_triggers_fft_merge(self):
        g = build_article_graph("test")
        app = g.compile()
        result = app.invoke(self._initial_state("test"))
        fft = result["_fft_spectrum"]
        assert "merged_energy" in fft
        assert fft["agent_count"] > 1

    def test_custom_graph_with_conditional_edge(self):
        g = SpectralStateGraph(SpectralState)

        def node_a(state):
            return {"output": "from A", "_quality_scores": {"a": 0.8}}

        def node_b(state):
            return {"output": "from B (good path)"}

        def node_c(state):
            return {"output": "from C (fallback)"}

        def router(state):
            scores = state.get("_quality_scores", {})
            return "good" if scores.get("a", 0) > 0.5 else "fallback"

        g.add_spectral_node("a", node_a, band=ColorBand.VIOLET, position=(0.2, 0.0))
        g.add_spectral_node("b", node_b, band=ColorBand.GREEN, position=(-0.2, 0.3))
        g.add_spectral_node("c", node_c, band=ColorBand.ORANGE, position=(-0.2, -0.3))

        g.add_edge("__start__", "a")
        g.add_conditional_edge("a", router, {"good": "b", "fallback": "c"})
        g.add_edge("b", "__end__")
        g.add_edge("c", "__end__")

        app = g.compile()
        result = app.invoke(self._initial_state("conditional test"))
        assert "b" in result["outputs"]  # should take "good" path
        assert "c" not in result["outputs"]
