#!/usr/bin/env python3
"""
Symphonic Cipher Demo

Demonstrates the complete intent-modulated conlang + harmonic verification system:
1. Conlang phrase tokenization
2. Feistel permutation (key-driven)
3. Harmonic synthesis with modality-specific overtone masks
4. Full DSP pipeline (gain, EQ, compression, reverb, panning)
5. RWP v3 envelope creation and verification
6. AI-based feature extraction and classification

Run with: python demo.py
"""

import sys
import numpy as np
import json
from pathlib import Path

# Add package to path if running from repo root
sys.path.insert(0, str(Path(__file__).parent))

from symphonic_cipher.core import (
    SymphonicCipher,
    ConlangDictionary,
    ModalityEncoder,
    Modality,
    FeistelPermutation,
    HarmonicSynthesizer,
    RWPEnvelope,
    derive_msg_key,
    generate_nonce,
    generate_master_key,
    BASE_FREQ,
    FREQ_STEP,
    SAMPLE_RATE,
)
from symphonic_cipher.dsp import (
    GainStage,
    ParametricEQ,
    DynamicCompressor,
    ConvolutionReverb,
    StereoPanner,
    DSPChain,
)
from symphonic_cipher.ai_verifier import (
    FeatureExtractor,
    HarmonicVerifier,
    IntentClassifier,
    VerificationResult,
)


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70)


def print_dict(d: dict, indent: int = 2) -> None:
    """Print dictionary with formatting."""
    for key, value in d.items():
        if isinstance(value, dict):
            print(" " * indent + f"{key}:")
            print_dict(value, indent + 2)
        elif isinstance(value, (list, np.ndarray)):
            if len(value) > 5:
                print(" " * indent + f"{key}: [{value[0]}, {value[1]}, ..., {value[-1]}] (len={len(value)})")
            else:
                print(" " * indent + f"{key}: {list(value)}")
        else:
            print(" " * indent + f"{key}: {value}")


def demo_dictionary():
    """Demonstrate conlang dictionary functionality."""
    print_header("1. CONLANG DICTIONARY")

    # Default dictionary
    d = ConlangDictionary()
    print("\nDefault vocabulary:")
    for token, id_val in sorted(d.vocab.items(), key=lambda x: x[1]):
        freq = BASE_FREQ + id_val * FREQ_STEP
        print(f"  '{token}' -> ID {id_val} -> {freq} Hz")

    # Tokenization
    phrase = "korah aelin dahru"
    ids = d.tokenize(phrase)
    print(f"\nTokenization: '{phrase}' -> {ids.tolist()}")

    # Extended dictionary with negative IDs
    extended = ConlangDictionary(ConlangDictionary.EXTENDED_VOCAB)
    print("\nExtended vocabulary (with negative IDs):")
    for token, id_val in sorted(extended.vocab.items(), key=lambda x: x[1]):
        freq = BASE_FREQ + id_val * FREQ_STEP
        print(f"  '{token}' -> ID {id_val} -> {freq} Hz")


def demo_modality():
    """Demonstrate modality encoding."""
    print_header("2. MODALITY ENCODING")

    encoder = ModalityEncoder(h_max=5)
    print("\nOvertone masks M(M):")
    for modality in Modality:
        mask = encoder.get_mask(modality)
        print(f"  {modality.value:10} -> {sorted(mask)}")

    print("\nModality interpretation:")
    print("  STRICT   = Binary intent (odd harmonics) - robotic/precise")
    print("  ADAPTIVE = Non-binary intent (full series) - biological/organic")
    print("  PROBE    = Minimal (fundamental only) - diagnostic mode")


def demo_feistel():
    """Demonstrate Feistel permutation."""
    print_header("3. FEISTEL PERMUTATION")

    feistel = FeistelPermutation(rounds=4)
    ids = np.array([0, 1, 2, 3, 4, 5], dtype=np.int64)

    # Two different keys
    key1 = generate_master_key()
    key2 = generate_master_key()

    perm1 = feistel.permute(ids, key1)
    perm2 = feistel.permute(ids, key2)

    print(f"\nOriginal IDs: {ids.tolist()}")
    print(f"Key 1 permutation: {perm1.tolist()}")
    print(f"Key 2 permutation: {perm2.tolist()}")
    print(f"\nNote: Same input, different keys -> different output")
    print("The permutation is deterministic and invertible.")


def demo_harmonic_synthesis():
    """Demonstrate harmonic synthesis."""
    print_header("4. HARMONIC SYNTHESIS")

    synth = HarmonicSynthesizer()
    ids = np.array([0, 1, 2])  # Three tokens

    print(f"\nSynthesizing audio for token IDs: {ids.tolist()}")
    print(f"  Sample rate: {SAMPLE_RATE} Hz")
    print(f"  Duration: {synth.duration} seconds")
    print(f"  Samples: {synth.n_samples}")

    for modality in [Modality.STRICT, Modality.ADAPTIVE, Modality.PROBE]:
        waveform = synth.synthesize(ids, modality)
        rms = np.sqrt(np.mean(waveform ** 2))
        peak = np.max(np.abs(waveform))
        print(f"\n  {modality.value}:")
        print(f"    RMS: {rms:.4f}")
        print(f"    Peak: {peak:.4f}")
        print(f"    Waveform shape: {waveform.shape}")


def demo_dsp_chain():
    """Demonstrate DSP processing chain."""
    print_header("5. DSP PROCESSING CHAIN")

    # Generate input signal
    synth = HarmonicSynthesizer()
    mono_signal = synth.synthesize(np.array([0, 1, 2]), Modality.ADAPTIVE)

    print("\nSignal flow:")
    print("  Input -> Gain -> EQ -> Compression -> Reverb -> Stereo Panning -> Output")

    # Initialize DSP chain
    dsp = DSPChain(sample_rate=SAMPLE_RATE)

    # Configure stages
    dsp.gain_stage.set_gain_db(3.0)  # +3 dB boost
    dsp.configure_eq(center_freq=1000, gain_db=2.0, q=2.0)  # Mild boost at 1kHz
    dsp.configure_compressor(threshold_db=-20, ratio=4.0)
    dsp.configure_reverb(wet_mix=0.2, decay_time=0.3)
    dsp.configure_panning(pan_position=0.3)  # Slightly right

    print("\nDSP Configuration:")
    print(f"  Gain: +{dsp.gain_stage.gain_db} dB")
    print(f"  EQ: Peak at 1000 Hz, +2 dB, Q=2")
    print(f"  Compressor: Threshold -20 dB, Ratio 4:1")
    print(f"  Reverb: 20% wet, 0.3s decay")
    print(f"  Pan: 0.3 (slightly right)")

    # Process
    stereo_output = dsp.process(mono_signal)

    print("\nProcessing results:")
    print(f"  Input: mono {mono_signal.shape}")
    print(f"  Output: stereo {stereo_output.shape}")

    left_rms = np.sqrt(np.mean(stereo_output[0] ** 2))
    right_rms = np.sqrt(np.mean(stereo_output[1] ** 2))
    print(f"  Left RMS: {left_rms:.4f}")
    print(f"  Right RMS: {right_rms:.4f}")
    print(f"  (Right is louder due to pan position)")


def demo_envelope():
    """Demonstrate RWP v3 envelope creation and verification."""
    print_header("6. RWP v3 ENVELOPE")

    # Create cipher
    master_key = generate_master_key()
    cipher = SymphonicCipher(master_key=master_key)

    # Encode a phrase
    phrase = "korah aelin dahru"
    envelope, components = cipher.encode(
        phrase,
        modality=Modality.ADAPTIVE,
        tongue="KO",
        return_components=True
    )

    print(f"\nEncoding phrase: '{phrase}'")
    print(f"Modality: ADAPTIVE")
    print(f"Tongue (domain): KO")

    print("\nComponents:")
    print_dict(components)

    print("\nEnvelope structure:")
    print(f"  header.ver: {envelope['header']['ver']}")
    print(f"  header.tongue: {envelope['header']['tongue']}")
    print(f"  header.aad: {envelope['header']['aad']}")
    print(f"  header.ts: {envelope['header']['ts']}")
    print(f"  header.nonce: {envelope['header']['nonce'][:20]}...")
    print(f"  payload: {envelope['payload'][:50]}... (length: {len(envelope['payload'])})")
    print(f"  sig: {envelope['sig'][:32]}...")

    # Verify
    print("\nVerification:")
    success, message = cipher.verify(envelope)
    print(f"  Result: {'PASS' if success else 'FAIL'}")
    print(f"  Message: {message}")

    # Demonstrate rejection
    print("\nTamper detection test:")
    tampered = envelope.copy()
    tampered["sig"] = "invalid_signature"
    success, message = cipher.verify(tampered)
    print(f"  Tampered envelope: {'PASS' if success else 'FAIL'}")
    print(f"  Message: {message}")


def demo_feature_extraction():
    """Demonstrate AI feature extraction."""
    print_header("7. AI FEATURE EXTRACTION")

    # Generate signals with different modalities
    synth = HarmonicSynthesizer()
    ids = np.array([0, 1, 2])

    extractor = FeatureExtractor(sample_rate=SAMPLE_RATE)

    print("\nExtracting features from different modalities:")

    for modality in [Modality.STRICT, Modality.ADAPTIVE]:
        waveform = synth.synthesize(ids, modality)
        features = extractor.extract(waveform)

        print(f"\n  {modality.value}:")
        print(f"    RMS: {features.rms:.4f}")
        print(f"    Spectral Centroid: {features.spectral_centroid:.1f} Hz")
        print(f"    Spectral Flatness: {features.spectral_flatness:.4f}")
        print(f"    Harmonic Mask: {features.harmonic_mask.tolist()}")
        print(f"    Jitter: {features.jitter:.4f}")
        print(f"    Shimmer: {features.shimmer:.4f}")
        print(f"    Sideband Ratio: {features.sideband_energy_ratio:.4f}")
        print(f"    Phase Coherence: {features.phase_coherence:.4f}")
        print(f"    Feature Vector Dimension: {features.dimension}")


def demo_harmonic_verification():
    """Demonstrate harmonic verification."""
    print_header("8. HARMONIC VERIFICATION")

    synth = HarmonicSynthesizer()
    verifier = HarmonicVerifier(sample_rate=SAMPLE_RATE)

    print("\nTesting harmonic verification for different modalities:")

    for modality in [Modality.STRICT, Modality.ADAPTIVE, Modality.PROBE]:
        waveform = synth.synthesize(np.array([0]), modality)
        report = verifier.verify(waveform, modality.value)

        print(f"\n  {modality.value}:")
        print(f"    Result: {report.result.value}")
        print(f"    Confidence: {report.confidence:.2f}")
        print(f"    Harmonic Match: {report.harmonic_match}")
        print(f"    Sideband Check: {report.sideband_check}")
        print(f"    Phase Check: {report.phase_check}")
        print(f"    Jitter Check: {report.jitter_check}")
        print(f"    Message: {report.message}")


def demo_intent_classifier():
    """Demonstrate neural network intent classifier."""
    print_header("9. INTENT CLASSIFIER (Neural Network)")

    classifier = IntentClassifier(input_dim=30)
    extractor = FeatureExtractor(sample_rate=SAMPLE_RATE)
    synth = HarmonicSynthesizer()

    print("\nNeural Network Architecture:")
    print("  Input: 30-dimensional feature vector")
    print("  Hidden 1: 64 neurons, ReLU")
    print("  Hidden 2: 32 neurons, ReLU")
    print("  Output: 1 neuron, Sigmoid (binary classification)")
    print("  Threshold: 0.85")

    print("\nClassifying audio samples:")

    for modality in [Modality.STRICT, Modality.ADAPTIVE]:
        waveform = synth.synthesize(np.array([0, 1, 2]), modality)
        features = extractor.extract(waveform)
        is_authentic, confidence = classifier.classify(features)

        print(f"\n  {modality.value}:")
        print(f"    Authentic: {is_authentic}")
        print(f"    Confidence: {confidence:.4f}")


def demo_end_to_end():
    """Demonstrate complete end-to-end flow."""
    print_header("10. END-TO-END DEMO")

    print("\n[SENDER SIDE]")
    print("-" * 40)

    # Initialize
    master_key = generate_master_key()
    cipher = SymphonicCipher(master_key=master_key)
    dsp = DSPChain(sample_rate=SAMPLE_RATE)

    # Configure DSP (studio engineering stages)
    dsp.configure_compressor(threshold_db=-15, ratio=3.0)
    dsp.configure_reverb(wet_mix=0.15)
    dsp.enable_stage('eq', False)  # Skip EQ for this demo

    # Encode
    phrase = "korah aelin dahru melik"
    print(f"1. Input phrase: '{phrase}'")
    print(f"2. Modality: ADAPTIVE (intent-rich)")

    envelope, components = cipher.encode(
        phrase,
        modality=Modality.ADAPTIVE,
        return_components=True
    )

    print(f"3. Token IDs: {components['original_ids']}")
    print(f"4. Permuted IDs: {components['permuted_ids']}")
    print(f"5. Waveform RMS: {components['waveform_rms']:.4f}")
    print(f"6. Envelope created (sig: {envelope['sig'][:16]}...)")

    # Simulate DSP processing on the audio
    import base64
    payload_bytes = base64.urlsafe_b64decode(envelope['payload'] + '==')
    audio = np.frombuffer(payload_bytes, dtype=np.float32)
    processed = dsp.process(audio)
    print(f"7. Audio processed through DSP chain")
    print(f"   Stereo output shape: {processed.shape}")

    print("\n[RECEIVER SIDE]")
    print("-" * 40)

    # Create receiver with same key
    receiver_cipher = SymphonicCipher(master_key=master_key)

    # Verify envelope
    print("1. Received envelope")
    success, message = receiver_cipher.verify(envelope)
    print(f"2. MAC verification: {'PASS' if success else 'FAIL'}")

    # Harmonic verification
    verifier = HarmonicVerifier(sample_rate=SAMPLE_RATE)
    report = verifier.verify(audio, "ADAPTIVE")
    print(f"3. Harmonic verification: {report.result.value}")
    print(f"   Confidence: {report.confidence:.2f}")

    # Feature extraction
    extractor = FeatureExtractor(sample_rate=SAMPLE_RATE)
    features = extractor.extract(audio)
    print(f"4. Feature extraction complete (dim={features.dimension})")

    # AI classification
    classifier = IntentClassifier()
    is_authentic, confidence = classifier.classify(features)
    print(f"5. AI classification: {'AUTHENTIC' if is_authentic else 'SUSPICIOUS'}")
    print(f"   Confidence: {confidence:.4f}")

    print("\n[RESULT]")
    print("-" * 40)
    if success and report.result == VerificationResult.PASS:
        print("Command AUTHORIZED")
    else:
        print("Command REJECTED")


def main():
    """Run all demos."""
    print("\n")
    print("=" * 70)
    print(" SYMPHONIC CIPHER DEMONSTRATION")
    print(" Intent-Modulated Conlang + Harmonic Verification System")
    print("=" * 70)
    print("\nThis demo showcases all mathematical components of the system.")

    demo_dictionary()
    demo_modality()
    demo_feistel()
    demo_harmonic_synthesis()
    demo_dsp_chain()
    demo_envelope()
    demo_feature_extraction()
    demo_harmonic_verification()
    demo_intent_classifier()
    demo_end_to_end()

    print("\n")
    print("=" * 70)
    print(" DEMO COMPLETE")
    print("=" * 70)
    print("\nAll mathematical components have been demonstrated:")
    print("  - Dictionary mapping (Section 2)")
    print("  - Modality encoding (Section 3)")
    print("  - Per-message secret derivation (Section 4)")
    print("  - Feistel permutation (Section 5)")
    print("  - Harmonic synthesis operator H (Section 6)")
    print("  - RWP v3 envelope (Section 7)")
    print("  - Verification procedure (Section 8)")
    print("  - DSP pipeline (Sections 3.2-3.10)")
    print("  - AI feature extraction and classification (Section 4.1-4.2)")
    print()


if __name__ == "__main__":
    main()
