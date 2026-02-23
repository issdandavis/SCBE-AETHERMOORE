# Audio Security Threats: Comprehensive Reference

> **Purpose**: Practical reference for the SCBE audio axis (L14) and spectral coherence layers (L9-10).
> Covers historical audio exploits, modern attack vectors, and detection techniques.
>
> **Last updated**: 2026-02-22
> **SCBE Layers**: L9 (Spectral Coherence), L10 (Phase Alignment), L14 (Audio Axis)

---

## Table of Contents

1. [Historical: Phone Phreaking and Tone Exploitation](#1-historical-phone-phreaking-and-tone-exploitation)
2. [Modern Attack Surface: Taxonomy](#2-modern-attack-surface-taxonomy)
3. [Adversarial Audio Attacks on Voice Assistants](#3-adversarial-audio-attacks-on-voice-assistants)
4. [Audio Deepfakes and Voice Cloning Fraud](#4-audio-deepfakes-and-voice-cloning-fraud)
5. [Audio Steganography](#5-audio-steganography)
6. [Side-Channel Acoustic Attacks](#6-side-channel-acoustic-attacks)
7. [Malicious Audio File Payloads](#7-malicious-audio-file-payloads)
8. [VoIP and Modern Telephony Fraud](#8-voip-and-modern-telephony-fraud)
9. [Detection Techniques](#9-detection-techniques)
10. [SCBE Integration Points](#10-scbe-integration-points)
11. [References](#11-references)

---

## 1. Historical: Phone Phreaking and Tone Exploitation

### 1.1 The Core Vulnerability: In-Band Signaling

The entire phreaking era (roughly 1955-1990) exploited a single architectural flaw: **in-band signaling**. The AT&T long-distance network used the same audio channel for both voice traffic and control signals. Any device that could produce the right tones could hijack call routing.

The critical frequency was **2600 Hz**. When a trunk line carried a continuous 2600 Hz tone, the far-end switch interpreted it as an idle line. Dropping the tone "seized" the trunk, after which the phreaker could inject multi-frequency (MF) routing tones to place calls to any destination without billing.

### 1.2 Key Figures and Milestones

| Year | Event |
|------|-------|
| ~1957 | **Joe Engressia ("Joybubbles")**, blind with perfect pitch, discovers he can whistle 2600 Hz to manipulate phone switches |
| 1963 | Cap'n Crunch cereal includes a toy bosun whistle that happens to emit exactly 2600 Hz |
| ~1969 | **John Draper ("Captain Crunch")** learns of the whistle from a blind phreaker named Denny, begins experimenting |
| 1971 | *Esquire* magazine publishes Ron Rosenbaum's "Secrets of the Little Blue Box," bringing phreaking into public awareness |
| ~1972 | **Steve Wozniak and Steve Jobs** build and sell blue boxes at UC Berkeley before founding Apple |
| 1975 | Draper is arrested after bragging to an FBI informant about eavesdropping on FBI lines; convicted of toll fraud |
| 1980s | Transition to **SS7 (Signaling System 7)** begins, moving control signaling out-of-band |
| 1990s | SS7 deployment renders blue boxes obsolete in most of the developed world |

### 1.3 The Colored Boxes

Phreakers developed a taxonomy of devices, each targeting a different part of the telephone system:

**Blue Box** -- The iconic device. Generated 2600 Hz and the MF tones (combinations of 700, 900, 1100, 1300, 1500, 1700 Hz) used by AT&T for inter-office routing. Allowed free long-distance and international calls by seizing trunk lines and injecting routing instructions directly.

**Red Box** -- Simulated the tones produced when coins were deposited in a payphone. US payphones used specific tone patterns: a single 1700+2200 Hz tone for a nickel, two rapid tones for a dime, five rapid tones for a quarter. Red boxes typically used a modified Radio Shack tone dialer with a replaced crystal oscillator (from 3.579545 MHz to 6.5 MHz). Instructions were widely published in *2600 Magazine* in the early 1990s.

**Black Box** -- Manipulated the electrical characteristics of a home phone line to prevent the local switch from detecting an off-hook condition. Incoming calls could be received without the caller being billed. Worked by adding a resistor (typically 6.8k ohm) in series with the line to keep voltage above the billing threshold.

**Beige Box** -- A lineman's handset (or homemade equivalent) used to tap into telephone junction boxes and make calls on someone else's line.

**Silver Box** -- Generated DTMF (Dual Tone Multi-Frequency) tones, including the four "extra" column tones (A, B, C, D) that were reserved for military and internal telco use.

### 1.4 DTMF Exploitation

DTMF replaced rotary pulse dialing with a matrix of 8 frequencies (4 low group: 697, 770, 852, 941 Hz; 4 high group: 1209, 1336, 1477, 1633 Hz). Each key press sends a pair of tones, one from each group. The fourth column (1633 Hz paired with the low group) generated tones A, B, C, D which were used for:

- **A (697+1633)**: Flash/priority on military Autovon
- **B (770+1633)**: Flash override (highest military priority)
- **C (852+1633)**: Immediate priority
- **D (941+1633)**: Priority

Phreakers exploited DTMF in several ways:
- Generating tones to navigate IVR (Interactive Voice Response) systems
- Replaying recorded DTMF sequences to automate calling card fraud
- Using the A-D tones to access restricted telco functions
- Brute-forcing voicemail PINs by rapidly cycling DTMF combinations

### 1.5 Lessons for SCBE

The phreaking era established a fundamental security principle that directly maps to SCBE governance:

> **Never trust in-band control signals.** Any channel that mixes data and control is exploitable.

This principle is why SCBE separates governance signals from payload data across all layers, and why the L9-L10 spectral coherence checks exist: to detect when an audio channel carries signals that do not belong to the expected content profile.

---

## 2. Modern Attack Surface: Taxonomy

Modern audio-based security threats can be organized into five major categories:

```
Audio Security Threats
|
+-- Command Injection (inaudible/adversarial)
|   +-- Ultrasonic (DolphinAttack, NUIT, SurfingAttack)
|   +-- Adversarial ML examples (Carlini-Wagner, CommanderSong)
|   +-- Near-ultrasonic cross-device (NUIT-1, NUIT-2)
|
+-- Identity Fraud (deepfake/cloning)
|   +-- Text-to-speech synthesis
|   +-- Voice conversion/cloning
|   +-- Real-time voice morphing
|
+-- Data Exfiltration (steganography)
|   +-- LSB encoding in PCM
|   +-- Phase coding
|   +-- Spread spectrum
|   +-- Echo hiding
|
+-- Side-Channel Leakage (acoustic emanations)
|   +-- Keyboard acoustic analysis
|   +-- Cryptographic key extraction
|   +-- Optical-acoustic (LAMPHONE)
|   +-- Printer/HDD/fan emanations
|
+-- Payload Exploitation (malicious files)
|   +-- Buffer overflow via crafted headers
|   +-- Codec vulnerabilities
|   +-- Metadata injection
|
+-- Telephony Fraud (VoIP/SIP)
    +-- Toll fraud / IRSF
    +-- Caller ID spoofing
    +-- PBX compromise
```

---

## 3. Adversarial Audio Attacks on Voice Assistants

### 3.1 DolphinAttack (2017)

**Researchers**: Zhang et al., Zhejiang University
**Published**: ACM CCS 2017

**Mechanism**: Modulates voice commands onto an ultrasonic carrier (frequency > 20 kHz). The key insight is that microphone hardware has **nonlinear response characteristics**: when an ultrasonic signal hits the microphone diaphragm, the amplifier circuit's nonlinearity demodulates the baseband audio command. The microphone "hears" the command even though humans cannot.

**Affected systems**: Validated against Siri, Google Now, Samsung S Voice, Huawei HiVoice, Cortana, and Alexa.

**Attack range**: Effective at 1-2 meters with commodity hardware (ultrasonic transducer + amplifier).

**What it can do**:
- Initiate phone calls
- Open malicious websites
- Activate airplane mode (disabling cellular communication)
- Control IoT devices

### 3.2 SurfingAttack (2020)

**Researchers**: Yan et al., multiple US universities
**Published**: NDSS 2020

**Advancement over DolphinAttack**: Uses **ultrasonic guided waves transmitted through solid surfaces** (tables, desks). A small piezoelectric transducer attached to the underside of a table can send commands to a phone resting on top. This enables:
- **Interactive attacks**: The attacker can receive responses (e.g., SMS verification codes read aloud by the assistant) through a hidden microphone
- **Obstacle bypass**: Does not require line-of-sight
- **Covert operation**: The transducer is hidden beneath a solid surface

### 3.3 NUIT (Near-Ultrasound Inaudible Trojan, 2023)

**Researchers**: Chen et al., UTSA/UCCS
**Published**: USENIX Security 2023

**Key innovation**: Uses **near-ultrasound frequencies** (16-20 kHz) rather than true ultrasound. These frequencies can be played by **commodity speakers** (laptop speakers, TV speakers, smart speakers) unlike DolphinAttack which requires specialized ultrasonic transducers.

**Two attack variants**:
- **NUIT-1**: The attacking device IS the target. A malicious audio file (e.g., embedded in a YouTube video or podcast) contains near-ultrasonic commands that cause the device playing the audio to execute commands on its own voice assistant.
- **NUIT-2**: Cross-device attack. One device's speaker sends near-ultrasonic commands to a nearby device's voice assistant.

**Scope**: 15 of 17 tested smart devices were vulnerable to NUIT-2. Commands as short as **0.77 seconds** are sufficient.

### 3.4 Adversarial ML Audio Examples

**Carlini-Wagner Attack (2018)**: Demonstrated that given any audio waveform, it is possible to produce another waveform that is 99.9% similar but transcribes to any target phrase chosen by the attacker. Achieved nearly 100% success against DeepSpeech ASR. However, the original attack was not effective over-the-air (only worked on direct audio input).

**CommanderSong (2018)**: Embedded adversarial voice commands within music. A song plays normally to human listeners but causes speech recognition systems to execute hidden commands. Achieved nearly 100% attack success against the Kaldi ASR toolkit and was the **first adversarial audio attack demonstrated to work over-the-air** (played through speakers and captured by microphones).

**CommanderUAP (2024)**: Universal adversarial perturbation that works across multiple speech recognition models without needing to be tailored to specific inputs. Demonstrated transferability to commercial speech recognition APIs, making it a practical threat against production systems.

### 3.5 SCBE Relevance

These attacks directly threaten any SCBE-governed system that accepts audio input. The L14 Audio Axis must:
- Filter ultrasonic and near-ultrasonic frequencies before ASR processing
- Validate that audio input has spectral characteristics consistent with human speech
- Detect adversarial perturbation signatures (abnormal energy in specific frequency bands)
- Reject audio commands that arrive through non-standard channels (solid-surface guided waves)

---

## 4. Audio Deepfakes and Voice Cloning Fraud

### 4.1 Threat Scale

Audio deepfakes have become the most democratized form of synthetic media fraud:

- **McAfee (2024)**: 1 in 4 adults have encountered an AI voice scam; 1 in 10 have been personally targeted
- **Industry data (2025)**: Voice cloning for fraud increased by over **400%** year-over-year
- **Global losses**: Deepfake-enabled fraud exceeded **$200 million in Q1 2025 alone**
- **Minimum input**: As little as **3 seconds of audio** can produce an 85% voice match

### 4.2 High-Profile Incidents

| Incident | Loss | Method |
|----------|------|--------|
| UK energy firm CEO fraud (2019) | EUR 220,000 | AI-generated voice impersonating parent company CEO, phone call to bank manager |
| Arup engineering firm (2024) | $25 million | Multi-person deepfake video conference with AI-generated likenesses of CFO and executives |
| Hong Kong bank transfer (2024) | $35 million | Deepfake video call impersonating known business partner |
| Family emergency scams (ongoing) | Varies | Cloned voice of family member claiming kidnapping/emergency, demanding ransom |

### 4.3 Technical Pipeline

Modern voice cloning typically follows this pipeline:

```
Source Audio (3-30 sec) --> Speaker Embedding Extraction
                              |
                              v
Text Input -----------> TTS Synthesis Engine (e.g., VALL-E, XTTS, Bark)
                              |
                              v
                        Vocoder (WaveGlow, HiFi-GAN)
                              |
                              v
                        Post-processing (noise matching, channel simulation)
                              |
                              v
                        Deepfake Audio Output
```

**Key tools** (as of 2025-2026):
- **VALL-E** (Microsoft): Neural codec language model, 3 seconds of enrollment audio
- **XTTS** (Coqui): Open-source, multi-language, real-time capable
- **Bark** (Suno): Open-source, supports non-speech sounds (laughter, pauses)
- **RVC** (Retrieval-based Voice Conversion): Real-time voice conversion, widely used
- **ElevenLabs**: Commercial API, high quality, has been used in documented fraud cases

### 4.4 Detection Artifacts

Deepfake audio typically exhibits these detectable artifacts:

1. **Spectral smoothing**: Neural vocoders tend to over-smooth high-frequency harmonics, producing unnaturally "clean" spectral envelopes
2. **Phase discontinuities**: Frame-based synthesis creates subtle phase jumps at frame boundaries (typically every 10-25ms)
3. **Breathing pattern absence**: Synthetic speech often lacks natural respiratory patterns (inhales, micro-pauses)
4. **Formant transition anomalies**: Transitions between phonemes may be unnaturally smooth or exhibit micro-glitches
5. **Background consistency**: The acoustic environment (room tone, reverberation) may be inconsistent or artificially uniform
6. **Pitch contour regularity**: F0 (fundamental frequency) contours may lack the micro-variations present in natural speech
7. **Codec artifacts**: When deepfakes are transmitted over phone lines, the double-encoding (synthesis codec + channel codec) creates distinctive spectral signatures

### 4.5 SCBE Relevance

L9-L10 spectral coherence analysis is directly applicable to deepfake detection. The phase alignment checks in L10 can detect the frame-boundary phase discontinuities that are a hallmark of neural vocoder synthesis. L14 should implement multi-feature validation including MFCC analysis, phase coherence scoring, and breathing pattern detection.

---

## 5. Audio Steganography

### 5.1 Techniques

Audio steganography hides data within audio signals without perceptible alteration. The main techniques, ordered by sophistication:

**Temporal Domain Methods**:

- **LSB (Least Significant Bit)**: Replaces the least significant bits of PCM audio samples with payload data. At 1 bit per sample in 44.1 kHz 16-bit audio, this yields ~5.5 KB/sec of covert bandwidth. Detectable through statistical analysis of LSB distributions.

- **Echo Hiding**: Embeds data by introducing echoes with controlled delay, amplitude, and decay rate. A "0" bit might use a 0.5ms echo delay; a "1" bit might use a 1.0ms echo delay. More robust than LSB but lower capacity.

**Frequency Domain Methods**:

- **Phase Coding**: Replaces the phase components of selected DFT segments with phase values that encode data. Exploits the fact that the human auditory system is largely insensitive to absolute phase. More resistant to compression and noise.

- **Spread Spectrum**: Spreads the hidden message across the frequency spectrum using a pseudo-random sequence. The message is below the noise floor at any single frequency but recoverable with the spreading key. Very robust but low capacity.

- **Frequency Masking**: Hides data in frequency bands that are "masked" (rendered inaudible) by louder nearby frequencies. Exploits psychoacoustic masking models (similar to MP3 compression).

**Transform Domain Methods**:

- **Wavelet Domain**: Embeds data in wavelet coefficients, typically in high-frequency detail coefficients. Robust against common audio processing operations.

- **Cepstral Domain**: Manipulates cepstral coefficients (which represent the spectral envelope) to embed data. Particularly stealthy because changes are distributed across the signal.

### 5.2 Capacity vs. Detectability

| Technique | Capacity (bits/sec) | Robustness | Detectability |
|-----------|---------------------|------------|---------------|
| LSB | ~44,100 (at 1 bit/sample) | Low (destroyed by resampling/compression) | Medium (statistical tests) |
| Echo Hiding | ~50-100 | Medium | Medium |
| Phase Coding | ~100-500 | High | Low-Medium |
| Spread Spectrum | ~10-50 | Very High | Low |
| Frequency Masking | ~200-2000 | Medium-High | Low |
| Wavelet | ~100-1000 | High | Low |

### 5.3 Real-World Steganography Threats

- **Command-and-control channels**: Malware has been documented using audio steganography to receive C2 commands via streaming music services or podcasts
- **Data exfiltration**: Sensitive data encoded in audio files that pass through DLP (Data Loss Prevention) systems unchecked
- **Covert communication**: Embedding encrypted messages in audio posted to public platforms
- **Digital watermarking abuse**: Authorized watermarks can be removed or replaced to facilitate piracy or deniability

### 5.4 SCBE Relevance

The L9 spectral coherence layer should incorporate steganalysis as part of audio integrity verification. Any audio passing through SCBE governance should be analyzed for:
- LSB distribution anomalies (chi-squared tests on sample LSBs)
- Unexpected energy in psychoacoustically masked bands
- Phase regularity that suggests artificial encoding
- Statistical deviations from expected codec-specific distributions

---

## 6. Side-Channel Acoustic Attacks

### 6.1 Acoustic Cryptanalysis

**Genkin, Shamir, and Tromer (2014)**: Demonstrated extraction of full **4096-bit RSA decryption keys** from GnuPG by recording the acoustic emanations of a laptop during decryption. The attack exploits the fact that different CPU operations produce subtly different sounds due to vibrations in capacitors and inductors on the motherboard.

**Key facts**:
- Works with a **mobile phone placed next to the laptop** or a laboratory microphone at up to **4 meters**
- The relevant emanations are ultrasonic (10-150 kHz range)
- Attack requires the target to decrypt ~4,000 chosen ciphertexts (which can be sent via email)
- Total attack time: approximately **one hour**
- Later extended to **ECDH key extraction** using electromagnetic rather than acoustic emanations

**Countermeasures applied**: GnuPG (libgcrypt) added algorithmic blinding to make operations data-independent. NIST explicitly included side-channel resistance as an evaluation criterion in AES and SHA-3 competitions.

### 6.2 Keyboard Acoustic Side-Channel Attacks

Each key on a keyboard produces a slightly different sound due to its physical position, the angle of the keystroke, and the mechanical properties of the switch. These differences are sufficient to identify which key was pressed.

**Evolution of attacks**:

| Year | Method | Accuracy |
|------|--------|----------|
| 2004 | Asonov & Agrawal: FFT features + neural network | ~80% per keystroke |
| 2005 | Zhuang et al.: unsupervised learning (no labeled training data needed) | ~96% for English text |
| 2023 | Harrison et al.: deep learning (CoAtNet) on Zoom audio | **95%** accuracy on MacBook Pro keystrokes |
| 2024 | Multiple studies: improved CNN/transformer models, contact-type piezoelectric microphones | >93% on mechanical keyboards |

**Attack vectors**:
- **Nearby smartphone**: The microphone on a phone placed on the same desk
- **Video conferencing**: Zoom, Teams, and other VoIP software transmit keystroke audio to all participants
- **Malware-activated microphone**: Software that silently records audio from a compromised device's built-in microphone
- **Piezoelectric sensors**: Contact microphones hidden under a desk, nearly undetectable

**What can be recovered**:
- Passwords (even when not displayed on screen)
- Private messages
- Source code
- Financial data
- Any typed content

### 6.3 LAMPHONE: Optical-Acoustic Side Channel (2020)

**Researchers**: Nassi et al., Ben-Gurion University of the Negev
**Presented**: Black Hat USA 2020

A hanging light bulb acts as a **passive microphone**. Sound waves cause the bulb to vibrate by millidegrees, modulating the emitted light. An attacker with a telescope, electro-optical sensor, and analog-to-digital converter can recover speech from **25+ meters away** by observing these light fluctuations.

**Key properties**:
- **Completely passive**: No laser beam to detect (unlike laser microphone attacks)
- **Real-time**: Sound recovered in real time, not post-processed
- **Verified**: Shazam identified songs; Google Speech API transcribed human speech
- **Limitation**: Requires line-of-sight to a hanging bulb without a shade; defeated by curtains

### 6.4 Other Acoustic Emanation Vectors

- **HDD activity sounds**: Rotational hard drive seek patterns are acoustically distinguishable and can leak information about file access patterns
- **Printer sounds**: Dot-matrix and some inkjet printers produce sounds correlated with print content
- **Fan speed modulation**: Malware can exfiltrate data by modulating CPU load to control fan speed, encoding data in the resulting acoustic signal (the "Fansmitter" attack)
- **Coil whine**: GPU and CPU voltage regulator coil whine varies with computational load and can be analyzed similarly to acoustic cryptanalysis

### 6.5 SCBE Relevance

Side-channel acoustic attacks represent information leakage that bypasses all software-level security. For SCBE-governed environments:
- L9 should model expected acoustic profiles for hardware environments
- L10 phase alignment can detect anomalous periodic signals (like those produced by acoustic exfiltration malware)
- Physical security guidance should include acoustic shielding for high-security deployments
- Audio input validation should reject signals with characteristics of acoustic emanation captures (very low SNR, specific ultrasonic frequency profiles)

---

## 7. Malicious Audio File Payloads

### 7.1 Buffer Overflow via Crafted Audio Headers

Audio file formats (WAV, MP3, FLAC, OGG, etc.) have complex header structures that specify codec parameters, sample rates, channel counts, and metadata. Parsers that do not properly validate these fields are vulnerable to buffer overflow attacks.

**Notable CVEs**:

| CVE | Target | Type | Impact |
|-----|--------|------|--------|
| CVE-2015-7243 | Boxoft WAV to MP3 Converter | Stack buffer overflow via crafted WAV header | Remote code execution |
| CVE-2009-0004 | Apple QuickTime | Buffer overflow via malicious MP3 | Arbitrary code execution |
| CVE-2023-37734 | MP3 Audio Converter | Buffer overflow from inadequate bounds checking | Code execution or crash |
| CVE-2018-10536-10540 | WavPack 5.1.0 | Multiple out-of-bounds writes via crafted WAV/W64/CAF headers | Denial of service, potential code execution |
| CVE-2017-0381 | Android libopus | Buffer overflow in Opus codec | Remote code execution via crafted audio |
| CVE-2021-0674/0675 | Android MediaTek ALAC decoder | Out-of-bounds read/write | Local privilege escalation |

### 7.2 Attack Patterns

**Header manipulation**: Oversize or negative values in fields like `data chunk size`, `number of channels`, `bits per sample`, or `sample rate` can cause integer overflows or buffer overruns when the parser allocates memory or copies data.

**Metadata injection**: ID3 tags (MP3), Vorbis comments (OGG), and RIFF INFO chunks (WAV) can contain arbitrary data. Parsers that render metadata as HTML/rich text (e.g., media players showing album art) are vulnerable to XSS or script injection.

**Codec exploitation**: Decompression of compressed audio formats (MP3, AAC, Opus, FLAC) involves complex mathematical operations. Malformed compressed data can trigger:
- Division by zero
- Infinite loops (causing DoS)
- Heap corruption via malformed Huffman tables
- Stack overflow via deeply nested codec structures

**Polyglot files**: Files that are simultaneously valid audio files AND another format (e.g., a WAV file that is also valid JavaScript or HTML). These bypass content-type validation while delivering executable payloads.

### 7.3 SCBE Relevance

L14 Audio Axis must validate all audio file inputs before processing:
- Strict header validation against format specifications (reject any non-conformant values)
- Size and bounds checking on all variable-length fields
- Sandboxed codec execution (process audio decoding in an isolated environment)
- Content-type verification (ensure the file is genuinely audio, not a polyglot)
- Metadata sanitization (strip or escape all metadata before rendering)

---

## 8. VoIP and Modern Telephony Fraud

### 8.1 The Modern Phreaking: VoIP Toll Fraud

Phone phreaking did not die with SS7; it evolved. Modern VoIP systems present a vast attack surface:

**Scale**: The Communications Fraud Control Association (CFCA) reports **$28.3 billion in global telecom fraud losses** (2019 figures), with **$7.46 billion specifically from PBX/IP-PBX hacking**.

**IRSF (International Revenue Share Fraud)**: The dominant modern toll fraud technique:
1. Attacker sets up premium-rate numbers in countries with high carrier payouts
2. Attacker compromises a business VoIP system (PBX, SIP trunk, or SBC)
3. Automated calls are placed to the premium numbers, generating revenue for the attacker
4. The victim receives a massive phone bill (often $10,000-$100,000+ over a weekend)

### 8.2 VoIP Attack Vectors

**SIP Credential Brute-Force**: SIP typically runs on ports 5060 (unencrypted) and 5061 (TLS). Attackers scan for open SIP registrars and brute-force SIP account credentials. Default credentials on IP phones and PBX systems are a major vector.

**SIP Trunk Hijacking**: Compromising the SIP trunk (the connection between a PBX and the carrier) allows the attacker to make calls as if they were the business, bypassing most fraud detection.

**Caller ID Spoofing**: SIP allows the caller to set arbitrary values in the `From` header, enabling impersonation of any phone number. This enables:
- Vishing (voice phishing) campaigns
- Bypassing callback verification
- Impersonating banks, government agencies, or known contacts

**Audio Channel Manipulation**: Within an established VoIP call:
- DTMF injection to navigate IVR systems
- Audio replacement (man-in-the-middle substitution of audio streams)
- Recording injection (playing pre-recorded audio as if it were live speech)

### 8.3 SCBE Relevance

SCBE v4.0.0 (Telecommunications/Space Tor phase) should incorporate:
- SIP message integrity verification through governance layers
- STIR/SHAKEN integration for caller identity attestation
- Audio channel authenticity scoring (detecting injected/replaced audio in real-time)
- Rate limiting and anomaly detection for outbound call patterns

---

## 9. Detection Techniques

### 9.1 Spectral Analysis for Hidden Signals

**Purpose**: Detect ultrasonic commands, steganographic payloads, and anomalous frequency content.

**Method**: Compute the Short-Time Fourier Transform (STFT) or Mel-scaled spectrogram and analyze energy distribution across frequency bands.

**Key indicators**:
- **Ultrasonic energy** (>18 kHz): Legitimate audio from human speech or music rarely contains significant energy above 18 kHz. Sustained energy in this band suggests DolphinAttack, NUIT, or ultrasonic C2 channels.
- **Narrow-band energy spikes**: Steganographic spread-spectrum signals produce subtle but consistent energy across specific bands. Subtracting the expected spectral envelope from the actual spectrum reveals hidden narrowband signals.
- **Spectral flatness anomalies**: The Wiener entropy (spectral flatness) of each frame should match the expected range for the content type. Steganographic payloads tend to increase spectral flatness in specific sub-bands.
- **Harmonic structure validation**: Human speech has a clear harmonic structure (F0 + integer multiples). Adversarial perturbations often introduce energy at non-harmonic frequencies.

**Implementation for SCBE L9**:
```
Input: audio_signal, sample_rate
1. Compute STFT with frame_size=2048, hop=512
2. For each frame:
   a. Check ultrasonic band (18-22 kHz) energy vs. speech band (100-8000 Hz)
   b. If ultrasonic_ratio > threshold: FLAG_ULTRASONIC_COMMAND
   c. Compute spectral flatness per sub-band
   d. If any sub-band flatness deviates > 3 sigma from model: FLAG_STEGANOGRAPHY
3. Compute harmonic-to-noise ratio (HNR)
4. If HNR < expected_minimum for speech: FLAG_ADVERSARIAL
```

### 9.2 Frequency Band Anomaly Detection

**Purpose**: Identify signals that deviate from expected frequency profiles for their declared content type.

**Method**: Build reference models for expected spectral content and flag deviations.

**Reference profiles**:
| Content Type | Expected Band | Typical Energy Distribution |
|-------------|---------------|----------------------------|
| Human speech | 80-8000 Hz | Concentrated 100-4000 Hz, harmonics visible |
| Music | 20-20000 Hz | Broad, genre-dependent |
| VoIP speech (G.711) | 300-3400 Hz | Hard bandlimited by codec |
| VoIP speech (Opus) | 50-20000 Hz | Fullband but speech-shaped |
| DTMF tones | 697-1633 Hz | Exactly 2 discrete frequencies per event |

**Detection approach**:
- Compare input spectrum against the declared/expected profile
- Flag energy in unexpected bands (e.g., ultrasonic content in a telephone-quality audio stream)
- Detect codec inconsistencies (e.g., fullband energy in a stream declared as G.711)
- Monitor for sudden spectral changes that suggest audio splicing or injection

### 9.3 Phase Coherence Analysis (SCBE L9-L10)

**Purpose**: Detect deepfakes, audio splicing, and steganographic phase manipulation.

**Foundational concept**: Natural audio has coherent phase relationships across frequency bands and across time frames. Synthetic or manipulated audio often breaks this coherence.

**Techniques**:

**Inter-frame phase coherence**: In natural audio, the phase of each frequency bin evolves predictably between frames (based on the bin's center frequency and the hop size). Measuring the deviation from expected phase advancement reveals:
- Frame-boundary discontinuities in synthesized audio
- Splice points where two audio segments are joined
- Phase-coded steganographic payloads

```
Phase Deviation = |actual_phase[f,t] - (phase[f,t-1] + 2*pi*f*hop_size/sample_rate)|
```

Large deviations at consistent frame intervals suggest neural vocoder synthesis. Random large deviations suggest splicing.

**Cross-band phase coherence**: In harmonic signals (speech), the phases of harmonics (2*F0, 3*F0, etc.) are locked to the fundamental. Deepfakes often fail to preserve this relationship accurately.

**Group delay analysis**: The group delay (negative derivative of phase with respect to frequency) should be smooth for natural signals. Abrupt group delay changes indicate manipulation.

**Implementation for SCBE L10**:
```
Input: stft_complex (complex STFT matrix)
1. Compute instantaneous frequency: IF[f,t] = diff(angle(stft_complex[f,:])) * sr / (2*pi*hop)
2. Compute phase deviation: PD[f,t] = |IF[f,t] - f|
3. Compute cross-band coherence for detected harmonics
4. Score: phase_coherence = 1 - mean(PD) / max_expected_PD
5. If phase_coherence < threshold: FLAG_SYNTHETIC_OR_MANIPULATED
```

### 9.4 Temporal Pattern Analysis for Steganography

**Purpose**: Detect data hidden in temporal characteristics of audio.

**Techniques**:

**LSB statistical analysis**: In unmodified PCM audio, the least significant bit of each sample is approximately random but with slight statistical bias dependent on the audio content. Steganographic embedding makes the LSB distribution perfectly uniform (or nearly so).
- **Chi-squared test**: Compare observed LSB pair frequencies against expected frequencies. A p-value near 1.0 strongly indicates LSB steganography.
- **RS analysis** (Regular-Singular): Classify sample groups as Regular or Singular based on a smoothness function. The ratio changes predictably with LSB embedding rate.

**Echo detection**: Compute the autocorrelation function and look for unexpected echo patterns at delays corresponding to steganographic encoding (typically < 2ms).

**Timing analysis for VoIP steganography**: In compressed speech codecs (G.729, Opus), steganographic embedding in codec parameters alters the statistical distribution of:
- Line Spectral Pair (LSP) coefficients
- Adaptive codebook gains
- Fixed codebook indices

Measuring these distributions against clean codec output baselines reveals hidden data.

**Sample variance analysis**: Natural audio has predictable sample-to-sample variance patterns. Steganographic embedding, particularly LSB encoding, reduces this variance in a detectable way.

### 9.5 Deepfake Audio Detection Features

The current state-of-the-art in deepfake audio detection relies on multiple complementary feature sets:

**Spectral features**:
- **MFCC (Mel-Frequency Cepstral Coefficients)**: 13-40 coefficients + deltas. SVM classifiers on MFCCs achieve 97-98% accuracy on known deepfake datasets.
- **LFCC (Linear-Frequency Cepstral Coefficients)**: Better at capturing high-frequency artifacts than MFCC.
- **CQT (Constant-Q Transform)**: Provides logarithmic frequency resolution, useful for detecting pitch manipulation artifacts.
- **Mel spectrogram**: 2D representation amenable to CNN-based classification.

**Temporal features**:
- Zero-crossing rate
- Short-time energy
- Spectral flux (frame-to-frame spectral change)
- Pitch contour statistics (mean, variance, jitter, shimmer)

**Neural network architectures for detection**:
- **ResNet/ResNeXt on spectrograms**: Treat deepfake detection as image classification on mel spectrograms. ResNeXt-based architectures have shown strong results (2025).
- **Wav2Vec 2.0 + fine-tuning**: Use self-supervised speech representations as features. Strong generalization across deepfake methods.
- **AASIST** (Audio Anti-Spoofing using Integrated Spectro-Temporal features): Graph neural network approach, top performer in ASVspoof challenges.
- **Multi-scale attention transformers**: Capture both local artifacts (frame-level) and global patterns (utterance-level).

**Achieved performance** (ASVspoof challenge benchmarks):
- Best systems: Equal Error Rate (EER) < 1% on known attack types
- Unknown attack types: EER 5-15% (generalization remains a challenge)

### 9.6 Composite Detection Pipeline

For SCBE integration, a multi-stage detection pipeline is recommended:

```
Stage 1: File Integrity
  - Header validation (format compliance)
  - Polyglot detection (multi-format analysis)
  - Metadata sanitization

Stage 2: Spectral Screening
  - Ultrasonic band energy check
  - Frequency profile matching (expected vs. actual)
  - Harmonic structure validation

Stage 3: Phase Analysis
  - Inter-frame phase coherence scoring
  - Cross-band harmonic phase locking
  - Group delay smoothness check

Stage 4: Steganography Detection
  - LSB chi-squared test
  - RS analysis
  - Echo pattern scan
  - Spectral flatness deviation

Stage 5: Deepfake Scoring
  - MFCC/LFCC extraction + classifier
  - Breathing pattern detection
  - Pitch contour naturalness scoring
  - Background consistency check

Stage 6: Behavioral Context
  - Is this audio expected in this context?
  - Does the voice match the claimed identity?
  - Is the command consistent with the user's profile?

Final: H(d,pd) Governance Score
  - Aggregate threat indicators into SCBE safety score
  - Route: ALLOW / QUARANTINE / DENY
```

---

## 10. SCBE Integration Points

### 10.1 Layer Mapping

| SCBE Layer | Audio Security Function |
|-----------|----------------------|
| **L5 (Input Validation)** | File header validation, format compliance, metadata sanitization |
| **L7 (Behaviour Tree / DECIDE)** | Decision logic for audio threat response (allow/quarantine/deny) |
| **L8 (PID Controller / STEER)** | Dynamic threshold adjustment based on threat environment |
| **L9 (Spectral Coherence / SENSE)** | Primary spectral analysis: frequency profiling, ultrasonic detection, steganography screening, harmonic validation |
| **L10 (Phase Alignment)** | Phase coherence scoring, deepfake frame-boundary detection, splice detection, group delay analysis |
| **L12 (BFT Consensus / COORDINATE)** | Multi-sensor consensus for high-confidence threat classification (multiple microphones, multiple analysis methods must agree) |
| **L14 (Audio Axis)** | End-to-end audio security pipeline integrating all detection stages; codec security; real-time audio stream governance |

### 10.2 H(d,pd) Scoring for Audio Threats

The bounded safety score `H(d,pd) = 1/(1+d+2*pd)` can be applied to audio threats where:
- `d` = **detection confidence**: weighted sum of detection stage scores (0 = no threat indicators, higher = more indicators)
- `pd` = **prior danger**: base threat level for the audio context (e.g., untrusted network audio has higher pd than local microphone input)

**Example scoring**:
| Scenario | d | pd | H(d,pd) | Action |
|----------|---|-----|---------|--------|
| Clean speech, trusted local mic | 0.0 | 0.1 | 0.83 | ALLOW |
| Speech with minor spectral anomaly, trusted source | 0.3 | 0.1 | 0.63 | ALLOW (log) |
| Ultrasonic energy detected, untrusted source | 0.8 | 0.5 | 0.36 | QUARANTINE |
| Deepfake indicators + ultrasonic + splicing, untrusted | 2.0 | 0.8 | 0.22 | DENY |
| Confirmed adversarial payload, any source | 5.0 | 1.0 | 0.13 | DENY + ALERT |

### 10.3 Sacred Tongue Audio Encoding

The Six Tongues system intersects with audio security in tongue_transport:
- Audio content passing through Sacred Tongue encoding should be validated BEFORE encoding (threats encoded in a Sacred Tongue are still threats)
- GeoSeal wrapping of audio assets provides provenance and integrity verification
- Platform-specific audio validation (e.g., Twitter voice clips vs. podcast audio have different expected spectral profiles)

### 10.4 Concept Block Integration

The existing concept blocks can be leveraged for audio security:
- **SENSE (Kalman filter, L9)**: Track spectral features over time, using Kalman filtering to maintain expected-vs-observed models for each frequency band. Anomalies that persist across multiple frames with increasing confidence trigger alerts.
- **DECIDE (behaviour tree, L7)**: Audio threat response decision tree incorporating threat type, confidence, source trust level, and operational context.
- **STEER (PID controller, L8)**: Dynamically adjust detection sensitivity. In high-threat environments, lower thresholds (more false positives, fewer false negatives). In low-threat environments, raise thresholds to reduce alert fatigue.
- **COORDINATE (BFT consensus, L12)**: When multiple audio analysis modules disagree on threat classification, use Byzantine fault-tolerant voting to reach a governance decision.

---

## 11. References

### Historical Phreaking
- [Blue box - Wikipedia](https://en.wikipedia.org/wiki/Blue_box)
- [John Draper - Wikipedia](https://en.wikipedia.org/wiki/John_Draper)
- [Phreaking - Wikipedia](https://en.wikipedia.org/wiki/Phreaking)
- [Phreaking box - Wikipedia](https://en.wikipedia.org/wiki/Phreaking_box)
- [Cap'n Crunch Whistle and Secrets of the Little Blue Box - Telephone Museum](https://telephone-museum.org/telephone-collections/capn-crunch-bosun-whistle/)
- [Red box (phreaking) - Wikipedia](https://en.wikipedia.org/wiki/Red_box_(phreaking))
- [Black box (phreaking) - Wikipedia](https://en.wikipedia.org/wiki/Black_box_(phreaking))
- [The Shocking Tale of Phone Phreaks: 1955-1980 Odyssey](https://www.chaintech.network/blog/a-journey-from-1955-to-1980-the-intriguing-world-of-phone-phreaks/)
- [The History of Phone Phreaking: Dialing Into The Past](https://norzer.me/a-journey-through-the-history-of-phone-phreaking-dialing-into-the-past/)

### Ultrasonic and Adversarial Audio Attacks
- [DolphinAttack: Inaudible Voice Commands (CCS 2017)](https://acmccs.github.io/papers/p103-zhangAemb.pdf)
- [DolphinAttack - USSLab Project Page](https://www.usslab.org/projects/DolphinAttack/DolphinAttack.html)
- [DolphinAttack GitHub](https://github.com/USSLab/DolphinAttack)
- [EarArray: Defending against DolphinAttack via Acoustic Attenuation (NDSS 2021)](https://www.ndss-symposium.org/wp-content/uploads/ndss2021_5A-4_24551_paper.pdf)
- [NUIT Attack - Project Page](https://sites.google.com/view/nuitattack/home)
- [NUIT - USENIX Security 2023](https://dl.acm.org/doi/10.5555/3620237.3620494)
- [SurfingAttack (NDSS 2020)](https://www.ndss-symposium.org/ndss-paper/surfingattack-interactive-hidden-attack-on-voice-assistants-using-ultrasonic-guided-waves/)
- [Audio Adversarial Examples: Targeted Attacks on Speech-to-Text - Carlini & Wagner](https://arxiv.org/abs/1801.01944)
- [CommanderUAP: Universal Adversarial Attacks on Speech Recognition (2024)](https://cybersecurity.springeropen.com/articles/10.1186/s42400-024-00218-8)

### Voice Cloning and Deepfake Detection
- [The Rise of the AI-Cloned Voice Scam - American Bar Association](https://www.americanbar.org/groups/senior_lawyers/resources/voice-of-experience/2025-september/ai-cloned-voice-scam/)
- [Audio Deepfake Detection: What Has Been Achieved and What Lies Ahead (PMC)](https://pmc.ncbi.nlm.nih.gov/articles/PMC11991371/)
- [Deepfake Statistics 2025 - Deepstrike](https://deepstrike.io/blog/deepfake-statistics-2025)
- [Deepfake Statistics and Trends 2026 - Keepnet](https://keepnetlabs.com/blog/deepfake-statistics-and-trends)
- [FBI Warning AI Voice Phishing - BlackFog](https://www.blackfog.com/fbi-warning-ai-voice-phishing-how-to-stop-threat/)
- [Deepfake audio detection via MFCC features and mel-spectrogram (AIP)](https://pubs.aip.org/aip/acp/article/3264/1/030027/3338488/)
- [Deepfake audio detection with spectral features and ResNeXt-based architecture (2025)](https://www.sciencedirect.com/science/article/pii/S0950705125007725)

### Audio Steganography
- [Comparative study of digital audio steganography techniques (2012)](https://link.springer.com/article/10.1186/1687-4722-2012-25)
- [Digital audio steganography: Systematic review (Computer Science Review 2020)](https://dl.acm.org/doi/10.1016/j.cosrev.2020.100316)
- [Detecting fingerprints of audio steganography software](https://www.sciencedirect.com/science/article/pii/S2665910720300219)
- [A robust audio steganography technique based on image encryption using different chaotic maps (2024)](https://www.nature.com/articles/s41598-024-70940-3)
- [An Improved Phase Coding Audio Steganography Algorithm (2024)](https://arxiv.org/html/2408.13277v2)

### Side-Channel Acoustic Attacks
- [RSA Key Extraction via Low-Bandwidth Acoustic Cryptanalysis (Springer 2014)](https://link.springer.com/chapter/10.1007/978-3-662-44371-2_25)
- [Acoustic Cryptanalysis - Project Page (Tromer)](https://cs-people.bu.edu/tromer/acoustic/)
- [Acoustic Cryptanalysis (Journal of Cryptology 2015)](https://link.springer.com/article/10.1007/s00145-015-9224-2)
- [Improved CoAtNet for robust acoustic side-channel attack classification on keyboards (2025)](https://link.springer.com/article/10.1007/s10207-025-01194-x)
- [Acoustic Side Channel Attack on Keyboards Based on Typing Patterns (2024)](https://arxiv.org/html/2403.08740v1)
- [Lamphone: Real-Time Passive Sound Recovery from Light Bulb Vibrations](https://www.nassiben.com/lamphone)

### Malicious Audio Payloads
- [CVE-2015-7243 - Boxoft WAV to MP3 Buffer Overflow](https://www.cvedetails.com/cve/CVE-2015-7243/)
- [CVE-2023-37734 - MP3 Audio Converter Buffer Overflow](https://medium.com/@jraiv02/cve-2023-37734-buffer-overflow-in-mp3-audio-converter-318fd8271911)
- [CVE-2009-0004 - QuickTime MP3 Vulnerability](https://www.rapid7.com/db/vulnerabilities/quicktime-cve-2009-0004/)
- [WavPack Security Vulnerabilities](https://www.cvedetails.com/vulnerability-list/vendor_id-17637/product_id-43617/Wavpack-Wavpack.html)

### VoIP and Telephony Fraud
- [How to Identify and Prevent VoIP Fraud in 2025 - Cebod Telecom](https://www.cebodtelecom.com/prevent-voip-fraud-2025)
- [Toll Fraud: Protect Against Telecom and IRSF Attacks](https://kelleycreate.com/protect-business-from-voip-toll-fraud-irsf-and-ai-driven-telecom-attacks/)
- [VoIP Security: Vulnerabilities and Best Practices - Yeastar](https://www.yeastar.com/blog/voip-secuirty-best-practices/)
- [Analysis of a Real-World Toll Fraud Attack](https://blog.gonskicyber.com/a-real-world-analysis-of-security-risks-in-telephony-systems)

### Spectral Analysis and Detection
- [Audio-based anomaly detection on edge devices via self-supervision and spectral analysis (2023)](https://link.springer.com/article/10.1007/s10844-023-00792-2)
- [Exposing speech tampering via spectral phase analysis (2016)](https://www.sciencedirect.com/science/article/abs/pii/S1051200416301002)
- [Time and spectral analysis methods with ML for authentication of digital audio recordings](https://www.sciencedirect.com/science/article/abs/pii/S037907381300087X)
- [Side-Channel Attacks: Ten Years After (NIST)](https://csrc.nist.gov/csrc/media/events/physical-security-testing-workshop/documents/papers/physecpaper19.pdf)

---

*This document is part of the SCBE-AETHERMOORE project research corpus. It informs the design of audio governance in layers L9, L10, and L14 of the 14-layer AI safety framework.*
