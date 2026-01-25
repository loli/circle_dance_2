1. The Strategy

- Engine Script (audio_engine.py): Runs in the background. It does the HPS/Chroma math and "blasts" the 12 energy levels out over a local network port (UDP).
- Visualizer Script (visualizer.py): Listens to that port. It only cares about drawing whatever data it receives.