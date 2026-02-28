# Creating Your Own Visualization

## Using an LLM (Recommended for Rapid Prototyping)

This project is designed to be LLM-friendly. Here's the fastest way to generate a custom visualization:

### Steps

1. **Provide context to the LLM**
   - Attach or point it to: `src/note_dancer/visualization/base/audioviz.py` (the base class)
   - Attach: `AUDIO_THEORY.md` and `ARCHITECTURE.md` (for understanding the data)
   - Optionally, one existing example like `src/note_dancer/visualization/snake/snake.py` or `src/note_dancer/visualization/radar/radar.py`
   - Ask it to analyze the structure

2. **Create a folder** for your visualization:
   ```bash
   mkdir -p src/note_dancer/visualization/my_visualization
   touch src/note_dancer/visualization/my_visualization/__init__.py
   ```

3. **Show the LLM an example**
   - Tell it to examine one of the existing visualizers (snake, radar, monolith, etc.)
   - Ask it to understand how `AudioVisualizationBase` works and what data is available

4. **Describe your idea and let it generate**
   - Example prompt:
     ```
     Create a visualization that:
     - Draws a rotating waveform in the center
     - Colors rotate through the spectrum based on detected notes (12 chroma values)
     - Size pulses with the transient (flux) energy
     - Background brightness follows the spectral centroid (brightness)
     - Add a parameter to control rotation speed with the BPM
     ```
   - The LLM will generate the complete `my_visualization.py` file

5. **Add entry point to `pyproject.toml`**
   ```toml
   my-vis = "note_dancer.visualization.my_visualization.my_visualization:main"
   ```

6. **Run it**:
   ```bash
   uv sync
   uv run my-vis
   ```

**Why this works:** The engine exposes clean, well-documented data (beat, bpm, notes, bands, flux, brightness). The base class handles screen setup, HUD parameters, and event loops. An LLM can infer the patterns from one example and generate syntactically correct code.

---

## Quick Start

1. **Create a new file** in `src/note_dancer/visualization/` (e.g., `myvis/myvis.py`)

2. **Extend AudioVisualizationBase**
```python
import pygame
from note_dancer.visualization.base.audioviz import AudioVisualizationBase

class MyVisualizer(AudioVisualizationBase):
    def __init__(self):
        super().__init__()
        # Your custom setup here
        self.my_value = 0.0

    def render_visualization(self, screen: pygame.Surface, font: pygame.font.Font) -> None:
        # Get latest audio data from engine
        events = self.process_audio_frame()
        if not events:
            return
        
        # events contains: beat, bpm, low, mid, high, notes (12), flux, brightness
        low = events.get("low", 0.0)
        mid = events.get("mid", 0.0)
        high = events.get("high", 0.0)
        notes = events.get("notes", [0.0] * 12)
        is_beat = events.get("beat", False)
        
        # Draw your visualization
        screen.fill((0, 0, 0))  # black background
        # ... your pygame drawing code ...

def main():
    viz = MyVisualizer()
    viz.run()

if __name__ == "__main__":
    main()
```

3. **Add an entry point** in `pyproject.toml`:
```toml
[project.scripts]
my-viz = "note_dancer.visualization.myvis.myvis:main"
```

4. **Run it**:
```bash
uv sync  # Update dependencies
uv run my-viz
```

## Available Audio Data

From `process_audio_frame()`:
- `beat` (bool): True if beat detected this frame
- `bpm` (float): Detected tempo
- `low`, `mid`, `high` (float): Band energies [0, 1]
- `notes` (list[12]): Chroma energies (C, C#, D, ..., B) [0, 1]
- `flux` (float): Transient/attack strength
- `brightness` (float): Spectral centroid [0, 1]

## Built-in Features (From Parent Class)

- **Screen management:** `self.screen`, `self.width`, `self.height`
- **Pygame setup:** `self.clock` for FPS, `pygame.display.set_mode()` called
- **HUD (Parameters):** Register sliders with `self.hud.register(NumericParameter(...))`
- **Event handling:** `F` for fullscreen, `Ctrl+C` to quit
- **Debug overlay:** `self.debug_overlay` (opt-in)

See [snake.py](visualization/snake/snake.py) or [radar.py](visualization/radar/radar.py) for full examples.

## Tips

- Keep `render_visualization()` under 16ms (60 FPS = ~16.6ms/frame)
- Use `self.hud.register()` to add tunable sliders (saved across sessions)
- Call `super().handle_base_events()` if you extend event handling
- Notes are ordered: C=0, C#=1, D=2, D#=3, E=4, F=5, F#=6, G=7, G#=8, A=9, A#=10, B=11
