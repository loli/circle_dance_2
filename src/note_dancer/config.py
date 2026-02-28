import pyaudio

# ============================================================================
# AUDIO STREAM CONFIGURATION
# ============================================================================

CHUNK = 1024
"""
Number of audio samples per frame (single processing unit).

Impact on Latency:
  - Latency (ms) = CHUNK / RATE * 1000
  - 1024 @ 48kHz = 21.3ms latency (good balance)
  - 512 @ 48kHz = 10.7ms (lower latency, higher CPU)
  - 2048 @ 48kHz = 42.6ms (higher latency, lower CPU)

Impact on CPU & Stability:
  - Smaller chunks = more frequent processing = higher CPU
  - Larger chunks = more data per frame = smoother but slower response
  - Best range for real-time: 512-2048

Watch Out For:
  - Audio device may not support all chunk sizes
  - Very small chunks (<512) can cause Xruns (buffer underruns)
  - Very large chunks (>2048) feel sluggish for beat sync
  - If you hear pops/clicks, try increasing CHUNK
"""

FORMAT = pyaudio.paFloat32
"""
Audio data format: 32-bit floating point.
- paFloat32: Best quality, handles normalized [-1, 1] range
- paInt16: Lower CPU, less dynamic range
- Recommendation: Keep paFloat32 for analysis accuracy
"""

WINDOW_CHUNKS = 6
"""
Number of CHUNK units to keep in history buffer for spectral analysis.

Buffer Size = WINDOW_CHUNKS * CHUNK samples
- WINDOW_CHUNKS=6 @ 1024 chunks = 6144 samples @ 48kHz = 128ms history

Impact on Spectral Resolution:
  - More history = finer frequency resolution in FFT
  - WINDOW_CHUNKS=6: ~47 Hz resolution (good for music)
  - WINDOW_CHUNKS=4: ~71 Hz resolution (coarser, less accurate note detection)
  - WINDOW_CHUNKS=8: ~35 Hz resolution (overkill, diminishing returns)

Watch Out For:
  - Larger buffers = longer latency (6 chunks = 128ms)
  - If you need < 50ms latency, reduce to 4 (at cost of resolution)
  - Spectral features (chroma, peak tracking) depend on this; small = noise
"""

# ============================================================================
# SAMPLE RATE CONFIGURATION
# ============================================================================

RATE = 48000
"""
Sample rate in Hz (samples per second).

Standard Options:
  - 44100 Hz: CD quality, common for generic audio interfaces
  - 48000 Hz: Professional standard, used by Behringer & video gear
  - 96000 Hz: Only benefit is marginal; costs 2× CPU & latency

Nyquist Frequency (max analyzable):
  - @ 44.1 kHz: up to 22.05 kHz (plenty for human hearing ~20 kHz)
  - @ 48 kHz: up to 24 kHz (slight headroom above 20 kHz)

Which to Use:
  - Generic microphone / Spotify → 44100
  - Behringer U-Phoria / external soundcard → 48000
  - USB headphones / HDMI audio → Check device specs (often 48000)

Watch Out For:
  - Mismatch between config and device default causes silent input or distortion
  - Check via: pactl list sources | grep -A 5 "rate"
  - If analysis seems "off", verify RATE matches device actual rate
"""

# ============================================================================
# NETWORK CONFIGURATION
# ============================================================================

UDP_IP = "127.0.0.1"
"""
IP address where engine listens for connections.

Default: 127.0.0.1 (localhost)
  - Engine and Viz on same machine (normal setup)
  - Fast, secure, no network latency

Remote Setup:
  - Change to 0.0.0.0 to listen on all interfaces
  - Then point viz to your-machine-ip:5005
  - Added latency: ~1-5ms over LAN (acceptable)
  - Watch out: Network packet loss = dropped audio frames

Watch Out For:
  - Firewalls may block UDP 5005/5006
  - VPNs add jitter (make visuals stutter)
  - Wireless connections unreliable for real-time
"""

UDP_PORT_ENGINE = 5005
"""
Port where engine sends audio analysis data (Engine → Visualization).

Data sent: 19 floats (brightness, flux, low/mid/high, bpm, beat, 12 notes)
Frequency: ~47 times per second (every CHUNK)
Size: 76 bytes per packet

Watch Out For:
  - May conflict if another app uses port 5005
  - Check via: lsof -i :5005
  - Firewall rules block non-localhost UDP by default
"""

UDP_PORT_COMMANDS = 5006
"""
Port where visualization sends parameter updates (Visualization → Engine).

Commands sent: JSON-formatted parameter changes (gains, thresholds, etc.)
Frequency: Only on slider changes (< 10 Hz typical)

Watch Out For:
  - Both ports must be available (5005 & 5006)
  - Engine won't start if either port is in use
"""
