# Architecture & Design

## Overview

Note Dancer is a real-time audio analysis and visualization engine designed for electronic music. It separates audio processing (backend "engine") from visualization (frontend), communicating via UDP on localhost. The system emphasizes low latency, robust beat/note detection, and adaptive normalization.

## Core Principles

### 1. Low-Latency Design
- Chunk-based processing: 1024 samples at 48kHz = **21.3ms latency per frame**
- Non-blocking UDP for visualization updates (drops stale packets, never queues)
- Engine processes at ~47 FPS for smooth real-time feedback

### 2. Adaptive Normalization
**Problem:** Audio volume varies dramatically within songs (quiet verses vs. loud choruses).

**Solution:** `AutoGain` class—a percentile-based peak tracker:
- Tracks the 90th percentile of recent peaks
- Decays slowly (15-20 second half-life) to maintain visual "ceiling" during breakdowns
- Attacks quickly (0.1 seconds) to respond to sudden volume spikes
- Per-band tracking (Low, Mid, High) for independent normalization

### 3. Electronic Music Focus
Optimized for beat-driven, harmonically rich music:
- **Beat Detection:** Aubio tempo detection (fast, C-based onset detection)
- **Note Extraction:** Librosa chroma_stft (12-semitone energy profile, robust to octave folding)
- **Transient Isolation:** HPSS (Harmonic-Percussive Source Separation) for clean attack detection
- **Spectral Envelope:** Triple-band RMS (Low, Mid, High) for visual physics feedback

## Physical Connection

### Network Topology
```
[AudioStream] → [AudioAnalyzer] → [NetworkTransmitter]
     ↓              ↓                    ↓
  PyAudio      DSP Filters          UDP Port 5005
  (Microphone   + Feature              (Engine)
   or System)    Extraction            
                                   ← UDP Port 5006 (Commands)
                                        ↑
                      [AudioReceiver] ← [Visualization]
                      (PyGame)
```

### Packet Format
**Engine → Visualization** (every frame, ~21.3ms):
- **19 floats** (76 bytes) packed as `!19f`:
  - `brightness` (float): Spectral centroid [0, 1]
  - `flux` (float): Transient energy, normalized by recent history
  - `low`, `mid`, `high` (floats): Band energies [0, 1]
  - `bpm` (float): Detected beats per minute
  - `is_beat` (float): 1.0 if beat detected, 0.0 otherwise
  - `notes` (12 floats): Chroma energies for C, C#, D, D#, E, F, F#, G, G#, A, A#, B

**Visualization → Engine** (on-demand, commands):
- Parameter updates sent as JSON via UDP port 5006
- Thread-safe: Engine locks params dict before reading

## Sound Features

### Beat Detection
- **Library:** Aubio tempo detector
- **Input:** Raw audio stream
- **Output:** Boolean `is_beat` + continuous `bpm` value
- **Tuning:** Fixed kernel size (automatic, minimal latency)

### Note Detection (Chroma)
- **Library:** Librosa `chroma_stft` (magnitude-only, no phase)
- **Method:** STFT → Harmonic magnitude (median filter, kernel 31) → chroma fold
- **Output:** 12 semitone energies
- **Why:** Handles polyphonic music, octave-invariant (all C's sound like one note)

### Spectral Features
| Feature | Formula | Use Case |
|---------|---------|----------|
| **RMS per Band** | √(mean(filtered²)) | "Volume" of bass/mid/high |
| **Spectral Centroid** | weighted_mean(frequency bins) | "Brightness" of the sound |
| **Flux (Transients)** | sum(max(0, current - previous)) | Detects attacks, drum hits |

### Normalization Modes
Three strategies to map raw energies to [0, 1]:

1. **Statistical** (default)
   - Per-band AutoGain (90th percentile tracker)
   - Decays over song duration, adapts to overall loudness
   - Best for: General music with volume dynamics

2. **Competitive** (spotlight)
   - Divides energy by the brightest note
   - Makes weak notes visible, strong notes dominate
   - Best for: Melodic music, emphasizing note contrast

3. **Fixed Scale** (VU meter)
   - Maps absolute dB levels (-40 to 0) to [0, 1]
   - Ignores song history
   - Best for: Consistent loudness across tracks

### Silence Gating
- **Threshold:** -40 dB (removes background noise)
- **Implementation:** Zeros out energies below ~0.01 amplitude
- **Purpose:** Prevents noise from creating false note detections

## Implementation Details

### DSP Pipeline (Per Frame)
```
Raw Audio (1024 samples)
  ↓
[Butterworth Filters] - Low (<150 Hz), Mid (150-4k Hz), High (>4k Hz)
  ├→ RMS → AutoGain → User Gain → Clipped [0, 1]
  ↓
[Librosa STFT] (2048 FFT, 1024 hop)
  ├→ HPSS decomposition (harmonic + percussive)
  ├→ Harmonic → Chroma (12 notes)
  ├→ Percussive → Flux (transients)
  └→ Magnitude → Spectral Centroid (brightness)
  ↓
[Network Transmit] - 19 floats via UDP
```

### Thread Safety
- **Locks:** `threading.Lock` on `analyzer.params` dict
- **Pattern:** CommandListener acquires lock before updating parameters
- **Free Operations:** Reading from `latest_data` in receiver is non-blocking

### Hardware Requirements
- **Sample Rate:** 44.1 kHz (generic audio) or 48 kHz (Behringer soundcard)
- **Chunk Size:** 1024 samples (configurable in `config.py`)
- **Channels:** Stereo input, mixed to mono (averaged)
- **Latency Options:** `PULSE_LATENCY_MSEC` environment variable
  - 20ms: Minimum (tight kernel buffer, USB devices may struggle)
  - 42ms: Balanced (two chunks, stable on older hardware)
  - 60-100ms: Maximum (laggy but super stable)

## Configuration

Edit `src/note_dancer/config.py`:
```python
CHUNK = 1024          # Samples per frame
RATE = 48000          # Hz (44100 for generic, 48000 for Behringer)
WINDOW_CHUNKS = 6     # History depth (6 × 1024 samples for spectral analysis)
UDP_IP = "127.0.0.1"  # Change if visualizer on different machine
UDP_PORT_ENGINE = 5005
UDP_PORT_COMMANDS = 5006
```

## Visualization Parameters (Real-Time Control)

Users can adjust **gains, attack/decay envelopes, and thresholds** while running:
- **Gains:** Low/Mid/High gain multipliers [0.1 to 2.0]
- **Flux Threshold:** Transient sensitivity [0.0 to 10.0]
- **Note Sensitivity:** Chroma spotlight intensity [0.5 to 0.98]
- **Envelopes:** Per-band attack/decay times (smoothing factors)
- **Normalization Mode:** Switch between statistical, competitive, fixed

See `visualization/base/parameters.py` for parameter definitions.

## Why These Choices?

| Choice | Reason |
|--------|--------|
| **Aubio for BPM** | Written in C, extremely fast onset detection, low latency (#1 priority for drums) |
| **Librosa for Chroma** | Robust 12-semitone folding, handles polyphonic music better than alternatives |
| **HPSS** | Separates sustained notes from drum attacks, cleaner feature extraction |
| **AutoGain** | Electronic music has extreme dynamics (quiet synth pads → loud drop); single scale won't work |
| **UDP** | Connectionless, non-blocking, perfect for "send latest frame" paradigm |
| **48 kHz** | High enough for accurate high-frequency features, lower CPU than 96 kHz |
