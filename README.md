# Note Dancer

> ⚠️ **WARNING:** Work in progress

Real-time audio analysis and live visualization from audio streams. Analyzes incoming audio to detect notes, beats, and harmonic content, then visualizes them in real-time using multiple visualization modes.

## Purpose

Note Dancer aims to provide two things:

1. **A real-time audio analysis engine** that extracts musically meaningful features (beats, notes, spectral texture) from live audio streams with minimal latency (~21ms)
2. **A foundation for custom visualizations** — build your own visualizer in minutes by extending `AudioVisualizationBase` and receiving beat/note/energy data via UDP

The architecture is intentionally decoupled: engine and visualization communicate only via a simple UDP protocol. This makes it easy to:
- Swap visualizers without restarting the engine
- Build visualizations in Python, or any language that can speak UDP
- Use LLM tools to generate boilerplate visualization code from natural language descriptions
- Run on different machines if needed

See [ARCHITECTURE.md](ARCHITECTURE.md) for technical details and [AUDIO_THEORY.md](AUDIO_THEORY.md) for the design philosophy.

## System Requirements

- Python 3.12+
- Ubuntu/Linux (tested on Ubuntu 20.04+)
- PyAudio-compatible audio system (ALSA/PulseAudio)
- Pygame for visualization

## Installation

```bash
# Install system dependencies
sudo apt update
sudo apt install python3-dev libasound2-dev libportaudio2 pavucontrol

# Install Python package and dependencies (requires uv)
uv sync
```

## How to Run

Start the engine and visualizer together:

```bash
./run.sh
```

Individual commands:

```bash
# Start the audio engine (captures and analyzes audio)
uv run audio-engine

# Start a visualization (in another terminal)
uv run viz-radar          # Note attack radar
uv run viz-snake          # Snake-style visualization
uv run viz-monolith       # Monolithic display
uv run viz-simple         # Simple dashboard
uv run viz-cli            # Command-line output
```

Once the visulaization is running, press "H" to access the settings.

## Audio Routing

By default, the engine listens to your microphone. To visualize system audio (Spotify, YouTube, etc.):

1. Start the engine: `uv run audio-engine`
2. Open `pavucontrol` in another terminal
3. Go to the **Recording** tab
4. Select **Monitor of [Your Device]** for the Python process

See `TROUBLESHOOTING.md` for detailed configuration and troubleshooting.
