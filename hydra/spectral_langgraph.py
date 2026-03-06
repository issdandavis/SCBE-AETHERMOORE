"""
HYDRA Spectral LangGraph — Color-Frequency Orchestration on LangGraph
=====================================================================

Extends LangGraph's StateGraph with spectral flow isolation:
- Nodes carry Poincare-ball positions for hyperbolic drift detection
- Edges carry color channels for wavelength-division multiplexed routing
- FFT-based "FNet mixing" decomposes multi-agent outputs into frequency space
  for harmonic merging (low-freq consensus + high-freq detail preservation)
- Designated "prism" nodes allow controlled convergence of isolated flows

This is the SDK-shippable core of the SCBE-LangGraph+ system.

Usage:
    from hydra.spectral_langgraph import SpectralStateGraph, SpectralState

    graph = SpectralStateGraph(SpectralState)
    graph.add_spectral_node("research", research_fn, band=ColorBand.GREEN)
    graph.add_spectral_node("draft", draft_fn, band=ColorBand.BLUE)
    graph.add_spectral_node("merge", merge_fn, prism=True)
    graph.add_edge("research", "draft")
    graph.add_edge("draft", "merge")

    app = graph.compile()
    result = app.invoke({"topic": "AI safety"})
"""

from __future__ import annotations

import math
import operator
import time
import hashlib
from dataclasses import dataclass, field
from enum import Enum
from typing import Annotated, Any, Callable, Dict, List, Optional, Set, Tuple, TypedDict

import numpy as np

from langgraph.graph import StateGraph, START, END


def _merge_dicts(a: dict, b: dict) -> dict:
    """Reducer: merge two dicts (right wins on key conflict)."""
    merged = dict(a) if a else {}
    if b:
        merged.update(b)
    return merged


def _concat_lists(a: list, b: list) -> list:
    """Reducer: concatenate two lists."""
    return (a or []) + (b or [])

from hydra.color_dimension import (
    BAND_CENTERS,
    ColorBand,
    ColorChannel,
    ColorNode,
    MultiColorTag,
    PHI,
    RouteCheck,
    RoutedFlow,
    SpectrumAllocator,
    SpectralFlowRouter,
    TONGUE_WEIGHTS,
    channel_for_provider,
    channel_for_task,
    channel_for_tongue,
)


# ---------------------------------------------------------------------------
#  Spectral State — the state schema for spectral workflows
# ---------------------------------------------------------------------------

class SpectralState(TypedDict, total=False):
    """State passed between nodes in a spectral graph.

    Extends standard LangGraph state with color-frequency metadata.
    Uses Annotated reducers for keys that may be updated concurrently
    by parallel nodes (e.g., when two research lanes run simultaneously).
    """
    # Core workflow state
    topic: str
    messages: Annotated[list, _concat_lists]
    outputs: Annotated[dict, _merge_dicts]            # node_id -> output text
    artifacts: Annotated[dict, _merge_dicts]           # node_id -> artifact dict

    # Spectral metadata (auto-managed by SpectralStateGraph)
    _spectral_channels: Annotated[dict, _merge_dicts]  # node_id -> {wavelength_nm, tongue, hex}
    _spectral_history: Annotated[list, _concat_lists]   # ordered list of (node_id, channel_info, timestamp)
    _fft_spectrum: Annotated[dict, _merge_dicts]        # merged frequency-domain representation
    _route_checks: Annotated[list, _concat_lists]       # RouteCheck results for audit trail
    _quality_scores: Annotated[dict, _merge_dicts]      # node_id -> quality float


# ---------------------------------------------------------------------------
#  FNet-style FFT Mixer — harmonic merging of multi-agent outputs
# ---------------------------------------------------------------------------

class SpectralMixer:
    """FNet-inspired mixer: decomposes text outputs into frequency space.

    Instead of attention, uses FFT to:
    1. Encode each agent's output as a signal (char ordinals or embeddings)
    2. Transform to frequency domain
    3. Filter: keep low-freq consensus, preserve high-freq unique details
    4. Merge via inverse FFT

    This is the "Fourier lens" that Grok's research identified as missing
    from current orchestration frameworks.
    """

    @staticmethod
    def text_to_signal(text: str, length: int = 256) -> np.ndarray:
        """Convert text to a fixed-length signal for FFT processing."""
        # Encode as ordinal values normalized to [0, 1]
        raw = np.array([ord(c) / 128.0 for c in text[:length]], dtype=np.float64)
        if len(raw) < length:
            raw = np.pad(raw, (0, length - len(raw)), mode="constant")
        return raw

    @staticmethod
    def signal_to_spectrum(signal: np.ndarray) -> np.ndarray:
        """FFT forward transform — time domain to frequency domain."""
        return np.fft.rfft(signal)

    @staticmethod
    def spectrum_to_signal(spectrum: np.ndarray, length: int = 256) -> np.ndarray:
        """FFT inverse transform — frequency domain to time domain."""
        return np.fft.irfft(spectrum, n=length)

    @classmethod
    def spectral_energy(cls, spectrum: np.ndarray) -> Dict[str, float]:
        """Decompose spectrum into energy bands (Parseval's theorem)."""
        magnitudes = np.abs(spectrum) ** 2
        total = float(magnitudes.sum())
        if total == 0:
            return {"low": 0.0, "mid": 0.0, "high": 0.0, "total": 0.0}

        n = len(magnitudes)
        third = max(1, n // 3)
        return {
            "low": float(magnitudes[:third].sum()) / total,
            "mid": float(magnitudes[third:2*third].sum()) / total,
            "high": float(magnitudes[2*third:].sum()) / total,
            "total": total,
        }

    @classmethod
    def merge_spectra(
        cls,
        spectra: Dict[str, np.ndarray],
        weights: Optional[Dict[str, float]] = None,
        low_freq_blend: float = 0.7,
        high_freq_preserve: float = 0.9,
    ) -> np.ndarray:
        """Merge multiple frequency-domain signals with harmonic weighting.

        Low frequencies (consensus/structure) are averaged across agents.
        High frequencies (unique details) are preserved from each agent
        weighted by their spectral energy contribution.
        """
        if not spectra:
            return np.array([])

        keys = list(spectra.keys())
        ref_len = len(spectra[keys[0]])

        if weights is None:
            weights = {k: 1.0 / len(keys) for k in keys}

        # Normalize weights
        total_w = sum(weights.values())
        weights = {k: v / total_w for k, v in weights.items()}

        merged = np.zeros(ref_len, dtype=np.complex128)
        third = max(1, ref_len // 3)

        # Low frequencies: weighted average (consensus)
        for key, spec in spectra.items():
            w = weights.get(key, 0.0)
            merged[:third] += spec[:third] * w * low_freq_blend

        # Mid frequencies: balanced blend
        for key, spec in spectra.items():
            w = weights.get(key, 0.0)
            merged[third:2*third] += spec[third:2*third] * w

        # High frequencies: energy-weighted preservation
        energies = {}
        for key, spec in spectra.items():
            energies[key] = float(np.abs(spec[2*third:]).sum())
        total_e = sum(energies.values()) or 1.0

        for key, spec in spectra.items():
            e_weight = energies[key] / total_e * high_freq_preserve
            merged[2*third:] += spec[2*third:] * e_weight

        return merged

    @classmethod
    def mix_outputs(
        cls,
        outputs: Dict[str, str],
        tongue_weights: Optional[Dict[str, str]] = None,
        signal_length: int = 256,
    ) -> Dict[str, Any]:
        """Full FNet mixing pipeline: text -> FFT -> merge -> analysis.

        Returns merged signal stats and per-agent spectral fingerprints.
        """
        signals = {}
        spectra = {}
        energies = {}

        for key, text in outputs.items():
            sig = cls.text_to_signal(text, signal_length)
            spec = cls.signal_to_spectrum(sig)
            signals[key] = sig
            spectra[key] = spec
            energies[key] = cls.spectral_energy(spec)

        # Apply tongue weights if provided
        fft_weights = {}
        if tongue_weights:
            for key, tongue in tongue_weights.items():
                fft_weights[key] = TONGUE_WEIGHTS.get(tongue, 1.0)
        else:
            fft_weights = None

        merged_spectrum = cls.merge_spectra(spectra, weights=fft_weights)
        merged_energy = cls.spectral_energy(merged_spectrum) if len(merged_spectrum) > 0 else {}

        return {
            "per_agent_energy": energies,
            "merged_energy": merged_energy,
            "agent_count": len(outputs),
            "signal_length": signal_length,
            "merged_spectrum": merged_spectrum,
        }


# ---------------------------------------------------------------------------
#  Spectral Node Wrapper — adds color metadata to node execution
# ---------------------------------------------------------------------------

@dataclass
class SpectralNodeConfig:
    """Configuration for a node in the spectral graph."""
    node_id: str
    fn: Callable
    band: Optional[ColorBand] = None
    tongue: str = "KO"
    provider: str = ""
    prism: bool = False             # Prism = merge node (all colors converge)
    poincare_position: Tuple[float, float] = (0.0, 0.0)
    tags: Set[str] = field(default_factory=set)


# ---------------------------------------------------------------------------
#  Spectral State Graph — the main SDK class
# ---------------------------------------------------------------------------

class SpectralStateGraph:
    """LangGraph StateGraph enhanced with spectral flow isolation.

    Key differences from vanilla LangGraph:
    - Nodes have color channels (wavelength, tongue, tags)
    - Nodes have Poincare-ball positions for hyperbolic drift detection
    - Prism nodes allow controlled convergence of isolated flows
    - FFT mixer merges multi-agent outputs in frequency space
    - Route checks enforce spectral isolation before execution
    """

    def __init__(
        self,
        state_schema: type = SpectralState,
        isolation_threshold: float = 0.1,
        hyperbolic_min_separation: float = 0.2,
    ):
        self._state_schema = state_schema
        self._node_configs: Dict[str, SpectralNodeConfig] = {}
        self._edges: List[Tuple[str, str]] = []
        self._conditional_edges: Dict[str, Tuple[Callable, Dict[str, str]]] = {}
        self._router = SpectralFlowRouter(
            isolation_threshold=isolation_threshold,
            hyperbolic_min_separation=hyperbolic_min_separation,
        )
        self._allocator = SpectrumAllocator(min_separation_nm=15)
        self._mixer = SpectralMixer()
        self._compiled = False

    def add_spectral_node(
        self,
        node_id: str,
        fn: Callable,
        band: Optional[ColorBand] = None,
        tongue: str = "KO",
        provider: str = "",
        prism: bool = False,
        position: Optional[Tuple[float, float]] = None,
        tags: Optional[Set[str]] = None,
    ) -> "SpectralStateGraph":
        """Add a node with spectral color assignment.

        Args:
            node_id: Unique node identifier
            fn: Function(state) -> state update dict
            band: Color band for this node's specialty
            tongue: Sacred Tongue overtone (KO/AV/RU/CA/UM/DR)
            provider: LLM provider name (claude/gpt/gemini/grok/hf/local)
            prism: If True, this is a convergence node (all colors merge)
            position: (x, y) in Poincare unit disk. Auto-assigned if None.
            tags: Semantic tags for multi-tagging
        """
        if position is None:
            # Auto-assign position based on band, spread around disk
            idx = len(self._node_configs)
            angle = idx * 2 * math.pi / max(7, idx + 1)
            r = 0.3 + 0.3 * (idx % 3) / 3  # vary radius
            position = (r * math.cos(angle), r * math.sin(angle))

        config = SpectralNodeConfig(
            node_id=node_id,
            fn=fn,
            band=band,
            tongue=tongue,
            provider=provider,
            prism=prism,
            poincare_position=position,
            tags=tags or {node_id},
        )
        self._node_configs[node_id] = config

        # Register in the spectral router
        self._router.add_node(
            node_id,
            position_xy=position,
            white=prism,
            designated_merge=prism,
        )

        # Allocate a color channel
        self._allocator.allocate(
            node_id,
            preferred_band=band,
            tongue=tongue,
            tags=tags or {node_id},
        )

        return self

    def add_edge(self, source: str, target: str) -> "SpectralStateGraph":
        """Add a directed edge between nodes."""
        self._edges.append((source, target))
        if source in self._node_configs and target in self._node_configs:
            self._router.add_edge(source, target, bidirectional=False)
        return self

    def add_conditional_edge(
        self,
        source: str,
        condition_fn: Callable,
        path_map: Dict[str, str],
    ) -> "SpectralStateGraph":
        """Add a conditional edge (LangGraph-style routing)."""
        self._conditional_edges[source] = (condition_fn, path_map)
        # Register all possible targets as edges in the router
        for target in path_map.values():
            if source in self._node_configs and target in self._node_configs:
                self._router.add_edge(source, target, bidirectional=False)
        return self

    def _wrap_node_fn(self, config: SpectralNodeConfig) -> Callable:
        """Wrap a node function to inject spectral metadata into state."""
        original_fn = config.fn
        channel = self._allocator.allocated.get(config.node_id)

        def wrapped(state: dict) -> dict:
            t0 = time.time()

            # Execute the original function
            result = original_fn(state)
            if result is None:
                result = {}

            # Build DELTA updates only (reducers handle accumulation)
            new_channel = {}
            if channel:
                new_channel[config.node_id] = {
                    "wavelength_nm": channel.wavelength_nm,
                    "tongue": channel.tongue,
                    "hex": channel.hex_color(),
                    "band": config.band.value if config.band else "auto",
                    "provider": config.provider,
                    "prism": config.prism,
                }

            new_history_entry = {
                "node_id": config.node_id,
                "timestamp": time.time(),
                "duration_ms": (time.time() - t0) * 1000,
                "band": config.band.value if config.band else "auto",
                "tongue": config.tongue,
            }

            # Capture output text for FFT mixing
            new_output = {}
            output_text = result.get("output", result.get("messages", [""])[-1] if result.get("messages") else "")
            if isinstance(output_text, str) and output_text:
                new_output[config.node_id] = output_text

            # If this is a prism node, do FFT merge of all upstream outputs
            fft_delta = {}
            if config.prism:
                # Read accumulated outputs from state + our new one
                all_outputs = dict(state.get("outputs", {}))
                all_outputs.update(new_output)
                all_channels = dict(state.get("_spectral_channels", {}))
                all_channels.update(new_channel)
                if len(all_outputs) > 1:
                    tongue_map = {
                        nid: all_channels.get(nid, {}).get("tongue", "KO")
                        for nid in all_outputs
                    }
                    mix_result = self._mixer.mix_outputs(all_outputs, tongue_weights=tongue_map)
                    fft_delta = {
                        "per_agent_energy": mix_result["per_agent_energy"],
                        "merged_energy": mix_result["merged_energy"],
                        "agent_count": mix_result["agent_count"],
                    }

            result["_spectral_channels"] = new_channel
            result["_spectral_history"] = [new_history_entry]
            result["_fft_spectrum"] = fft_delta
            result["outputs"] = new_output

            return result

        return wrapped

    def compile(self) -> Any:
        """Compile the spectral graph into an executable LangGraph app.

        Returns a compiled StateGraph that can be invoked with .invoke()
        """
        # Build the LangGraph StateGraph
        graph = StateGraph(self._state_schema)

        # Add wrapped nodes
        for node_id, config in self._node_configs.items():
            wrapped_fn = self._wrap_node_fn(config)
            graph.add_node(node_id, wrapped_fn)

        # Add edges
        for source, target in self._edges:
            src = START if source == "__start__" else source
            tgt = END if target == "__end__" else target
            graph.add_edge(src, tgt)

        # Add conditional edges
        for source, (cond_fn, path_map) in self._conditional_edges.items():
            graph.add_conditional_edges(source, cond_fn, path_map)

        self._compiled = True
        return graph.compile()

    def get_spectrum_report(self) -> Dict[str, Any]:
        """Report on spectrum allocation and router state."""
        return {
            "nodes": len(self._node_configs),
            "edges": len(self._edges),
            "prism_nodes": [nid for nid, c in self._node_configs.items() if c.prism],
            "spectrum_utilization": f"{self._allocator.utilization():.0%}",
            "channels_allocated": {
                nid: {
                    "wavelength_nm": ch.wavelength_nm,
                    "hex": ch.hex_color(),
                    "tongue": ch.tongue,
                }
                for nid, ch in self._allocator.allocated.items()
            },
            "active_routes": len(self._router.active_routes),
        }


# ---------------------------------------------------------------------------
#  Pre-built spectral graph recipes
# ---------------------------------------------------------------------------

def build_article_graph(topic: str = "AI safety") -> SpectralStateGraph:
    """Pre-built spectral graph for article generation.

    Nodes:
        research (GREEN/Gemini) -> outline (VIOLET/Claude) -> draft (BLUE/GPT)
        -> challenge (ORANGE/Grok) -> edit (BLUE/GPT) -> merge (PRISM)
    """
    def research_fn(state):
        return {"output": f"Research findings on {state.get('topic', topic)}: 3 key sources found."}

    def outline_fn(state):
        research = state.get("outputs", {}).get("research", "")
        return {"output": f"Outline from research: I. Intro II. Analysis III. Conclusion. Based on: {research[:50]}"}

    def draft_fn(state):
        outline = state.get("outputs", {}).get("outline", "")
        return {"output": f"First draft (2000 words): {outline[:30]}... [full article body]"}

    def challenge_fn(state):
        draft = state.get("outputs", {}).get("draft", "")
        return {"output": f"Challenge: Weak point in para 3. Missing citation in section II. Draft preview: {draft[:30]}"}

    def edit_fn(state):
        return {"output": "Revised draft addressing all challenges. Strengthened evidence in section II."}

    def merge_fn(state):
        outputs = state.get("outputs", {})
        fft = state.get("_fft_spectrum", {})
        return {"output": f"Final article merged from {len(outputs)} color lanes. FFT energy: {fft.get('merged_energy', {})}"}

    g = SpectralStateGraph(SpectralState)
    g.add_spectral_node("research", research_fn, band=ColorBand.GREEN, tongue="RU", provider="gemini",
                        position=(0.3, 0.0))
    g.add_spectral_node("outline", outline_fn, band=ColorBand.VIOLET, tongue="DR", provider="claude",
                        position=(-0.3, 0.3))
    g.add_spectral_node("draft", draft_fn, band=ColorBand.BLUE, tongue="AV", provider="gpt",
                        position=(0.0, -0.3))
    g.add_spectral_node("challenge", challenge_fn, band=ColorBand.ORANGE, tongue="RU", provider="grok",
                        position=(0.4, -0.2))
    g.add_spectral_node("edit", edit_fn, band=ColorBand.BLUE, tongue="AV", provider="gpt",
                        position=(0.0, -0.5))
    g.add_spectral_node("merge", merge_fn, prism=True, tongue="UM", provider="claude",
                        position=(0.0, 0.0))

    g.add_edge("__start__", "research")
    g.add_edge("research", "outline")
    g.add_edge("outline", "draft")
    g.add_edge("draft", "challenge")
    g.add_edge("challenge", "edit")
    g.add_edge("edit", "merge")
    g.add_edge("merge", "__end__")

    return g


def build_research_graph(topic: str = "quantum computing") -> SpectralStateGraph:
    """Pre-built spectral graph for deep multi-source research.

    Parallel research lanes converge at a prism node for FFT merging.
    """
    def arxiv_fn(state):
        return {"output": f"ArXiv: 5 papers on {state.get('topic', topic)}. Key: transformer architectures."}

    def web_fn(state):
        return {"output": f"Web: Industry reports on {state.get('topic', topic)}. 3 enterprise case studies."}

    def debate_fn(state):
        return {"output": "Debate: ArXiv focuses theory, Web focuses practice. Gap: deployment safety."}

    def synthesis_fn(state):
        outputs = state.get("outputs", {})
        fft = state.get("_fft_spectrum", {})
        return {"output": f"Synthesis from {len(outputs)} lanes. Consensus: safety gaps in deployment. FFT: {fft.get('merged_energy', {})}"}

    g = SpectralStateGraph(SpectralState)
    g.add_spectral_node("arxiv", arxiv_fn, band=ColorBand.GREEN, tongue="RU", provider="gemini",
                        position=(0.3, 0.3))
    g.add_spectral_node("web", web_fn, band=ColorBand.CYAN, tongue="CA", provider="local",
                        position=(-0.3, 0.3))
    g.add_spectral_node("debate", debate_fn, band=ColorBand.ORANGE, tongue="RU", provider="grok",
                        position=(0.0, -0.3))
    g.add_spectral_node("synthesis", synthesis_fn, prism=True, tongue="DR", provider="claude",
                        position=(0.0, 0.0))

    g.add_edge("__start__", "arxiv")
    g.add_edge("__start__", "web")
    g.add_edge("arxiv", "debate")
    g.add_edge("web", "debate")
    g.add_edge("debate", "synthesis")
    g.add_edge("synthesis", "__end__")

    return g


# ---------------------------------------------------------------------------
#  Demo
# ---------------------------------------------------------------------------

def _demo():
    print("=" * 70)
    print("  Spectral LangGraph — Color-Frequency Orchestration")
    print("=" * 70)

    # Build and compile article graph
    print("\n--- Article Generation Graph ---")
    g = build_article_graph("signed Chladni modes in AI safety")
    app = g.compile()

    report = g.get_spectrum_report()
    print(f"Nodes: {report['nodes']}, Edges: {report['edges']}")
    print(f"Prism nodes: {report['prism_nodes']}")
    print(f"Spectrum utilization: {report['spectrum_utilization']}")
    print("Channels:")
    for nid, ch in report["channels_allocated"].items():
        print(f"  {nid:15s} {ch['wavelength_nm']:.0f}nm {ch['hex']} tongue={ch['tongue']}")

    # Execute
    print("\nExecuting...")
    result = app.invoke({
        "topic": "signed Chladni modes in AI safety",
        "messages": [],
        "outputs": {},
        "artifacts": {},
        "_spectral_channels": {},
        "_spectral_history": [],
        "_fft_spectrum": {},
        "_route_checks": [],
        "_quality_scores": {},
    })

    print(f"\nExecution complete. {len(result.get('_spectral_history', []))} nodes executed.")
    print(f"Outputs collected from: {list(result.get('outputs', {}).keys())}")
    print(f"FFT spectrum: {result.get('_fft_spectrum', {})}")

    # Show spectral history
    print("\nSpectral execution trace:")
    for entry in result.get("_spectral_history", []):
        print(f"  [{entry['band']:8s}] {entry['node_id']:15s} tongue={entry['tongue']} "
              f"dt={entry['duration_ms']:.1f}ms")

    # Show channel assignments
    print("\nChannel assignments:")
    for nid, ch_info in result.get("_spectral_channels", {}).items():
        prism = " [PRISM]" if ch_info.get("prism") else ""
        print(f"  {nid:15s} {ch_info['wavelength_nm']:.0f}nm {ch_info['hex']} "
              f"tongue={ch_info['tongue']} provider={ch_info['provider']}{prism}")

    # Test FFT mixer directly
    print("\n--- FNet Mixer Test ---")
    mixer = SpectralMixer()
    test_outputs = {
        "claude": "The architectural implications of Chladni modes suggest resonance patterns.",
        "gpt": "Chladni modes create visible patterns on vibrating plates, similar to neural activations.",
        "grok": "But does the Chladni analogy actually hold? The math diverges at higher frequencies.",
    }
    mix = mixer.mix_outputs(test_outputs, tongue_weights={"claude": "DR", "gpt": "AV", "grok": "RU"})
    print(f"Agents mixed: {mix['agent_count']}")
    for agent, energy in mix["per_agent_energy"].items():
        print(f"  {agent:10s} low={energy['low']:.2f} mid={energy['mid']:.2f} high={energy['high']:.2f}")
    me = mix["merged_energy"]
    print(f"  {'MERGED':10s} low={me.get('low', 0):.2f} mid={me.get('mid', 0):.2f} high={me.get('high', 0):.2f}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    _demo()
