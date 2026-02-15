## How-To

### How to route input signal

An input received from an internal or external soundcard can be mapped to your script via `pavucontrol`'s record tab. Take care to map the input itself, not the monitor for better performance.

### How to Route System Audio (The "Pavucontrol" Trick)

By default, Ubuntu will point your `audio_engine.py` at your physical microphone. To visualize music playing from Spotify, YouTube, or a media player, you must redirect the "Monitor" of your output into the script.

1. **Start the Engine:** Run your script: `python audio_engine.py`.
2. **Open the Controller:** In a new terminal tab, type `pavucontrol`.
3. **The Recording Tab:**
    * Navigate to the **Recording** tab in the window that appears.
    * Locate your Python process (it may show up as "ALSA plug-in [python3.12]").
4. **Flip the Switch:**
* Click the dropdown menu next to the application name.
    * Change it from **Built-in Audio Analog Stereo** to **Monitor of Built-in Audio Analog Stereo**.
    * *Note: If you don't see "Monitor," ensure your music is currently playing.*

## Installation

```bash
sudo apt update
sudo apt install python3-dev libasound2-dev libjack-jackd2-dev libportaudio2 pavucontrol
```

```python
python3 -m venv music_env
source music_env/bin/activate
pip install pyaudio numpy librosa aubio
```

## Tips & Tricks

### Configuration Tips for Ubuntu

| Variable | Setting | Reason |
| --- | --- | --- |
| **DEVICE_INDEX** | `None` | Setting this to `None` lets PulseAudio handle the default stream. You then use `pavucontrol` to do the heavy lifting. |
| **CHUNK Size** | `1024` | On Ubuntu, a chunk size of `1024` provides a stable balance between low latency and CPU overhead. |
| **Latency Fix** | `exception_on_overflow=False` | PyAudio on Linux can sometimes "hiccup" if the CPU spikes. This flag prevents the engine from crashing if a buffer overflows. |

### Troubleshooting "Flat" Meters

If you have performed the `pavucontrol` flip and the volume is still flat:

* **Check Output Device:** Ensure your music is actually playing out of the device you are monitoring. If you are using HDMI audio or USB Headphones, you must select the **Monitor of [That Specific Device]**.
* **ALSA/Pulse Conflict:** If the script fails to start, ensure no other "exclusive" audio applications (like a DAW) have locked the audio hardware.


## engine

The engine, capturing the audio and sending it via web socket.

### Why we use these specific libraries

- Aubio: It is written in C and is extremely fast at finding "onsets" (the start of a sound). We use it for the beat because it has significantly lower latency than Librosa.
- Librosa: While slower, its chroma_stft math is highly robust. It handles the complex task of "folding" all octaves into a single 12-note profile better than almost any other library.

### The Packet Protocol

The engine sends two types of messages to 127.0.0.1:5005:

- JSON Dictionary: {"bpm": 128.5} — Sent only when a beat is detected.
- JSON List: [0.1, 0.05, ...] — Sent 43 times per second (at 44.1kHz / 1024), providing the raw "harmonic fuel" for your radar.

## radar

The visualization, in form of a note atack radar.

### How the Live Attack Radar Works

- The Attack Filter (Temporal Delta): Instead of drawing the volume, we draw the change in volume. By subtracting the previous frame's energy from the current one, we isolate the "Attack" phase of a sound—the precise moment a string is plucked or a drum is hit. This prevents long, sustained bass notes from filling the screen with solid blobs of color.
- Coordinate Transformation: The visualizer uses Polar Coordinates (r, θ). We convert the note's identity into a radius (r) and the playhead's position into an angle (θ), then translate those into Cartesian Coordinates (x, y) for the screen.
- Decay Sync: The life of each note-head is mathematically tied to the rotation speed. This ensures that every "trace" vanishes exactly as the scanning arm completes a full circle, keeping the canvas clean.