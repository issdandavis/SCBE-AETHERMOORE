# Prompt for Colab Gemini — Llama-7B PhaseTunnelGate Validation

Paste this into the Colab AI chat:

---

I need you to run a PhaseTunnelGate experiment on a 7B parameter model to validate findings from DistilBERT. Here's what we found on DistilBERT and need to confirm at scale:

## Prior Results (DistilBERT — confirmed)
- Q weights are spectrally structured (4.52x noise floor)
- K weights are spectrally flat (1.05x noise floor)
- V weights are intermediate
- Natural tunnel frequencies: Q=-36°, K=118°, V=87° (154° Q-K separation)
- PhaseTunnelGate classified 4/18 heads as commit-permitted (tunnel+attenuate)
- Null hypothesis CONFIRMED: trained > random at 107.8% vs 102.4%

## What to run on Llama-7B (or Mistral-7B if Llama needs auth)

### Step 1: Load model (quantized for T4 GPU)
Load `mistralai/Mistral-7B-v0.1` (or `meta-llama/Llama-2-7b-hf` if you have the token) in 4-bit quantization using bitsandbytes. We only need the weight matrices, not inference.

### Step 2: FFT Spectral Density Probe
For layers 0, 4, 8, 12, 16, 20, 24, 28, 31:
- Extract Q, K, V weight matrices from the self-attention
- Compute 2D FFT, get power spectrum
- Calculate spectral density ratio = mean(high_freq) / mean(low_freq)
- Compare Q vs K vs V density ratios across layers
- Plot: x=layer, y=spectral_density, three lines (Q, K, V)

### Step 3: PhaseTunnelGate
For each extracted weight matrix:
- Compute FFT, find dominant mode (peak frequency bin)
- Extract phase angle of dominant mode: B_phase = angle(FFT[peak])
- Compute transmission coefficient: T = cos²((B_phase - phi_wall) / 2) where phi_wall = 0
- Classify: TUNNEL (T>0.7), ATTENUATE (0.3-0.7), REFLECT (0.05-0.3), COLLAPSE (T≤0.05)

### Step 4: Resonance Sweep
For each weight type (Q, K, V) at the deepest layer:
- Sweep phi_wall from -π to π in 360 steps
- At each phi_wall, compute T
- Find the peak T and its phi_wall angle
- Report: natural tunnel frequency for Q, K, V
- Calculate Q-K angular separation

### Step 5: Null Hypothesis
- Generate random matrices same shape as Q, K, V weights
- Run Steps 2-4 on random matrices
- Compare spectral density and tunnel frequencies: trained vs random

### Step 6: Summary Document
Write a markdown document with:
- Model name and size
- All results in tables
- Comparison to DistilBERT findings
- Whether Q-K phase separation holds at scale
- Whether the PhaseTunnelGate classification is consistent
- Save to /content/llama7b_phase_tunnel_results.md

Use torch, numpy, matplotlib. Print results after each step. Make the plots clear with titles and legends. This is for a research paper — be precise with numbers.
