"""Specific parameter that come with built-in visualizations."""

import pygame

from note_dancer.visualization_v2.base.hud import NumericParameter
from note_dancer.visualization_v2.base.parameters_base import EngineParameter, ParameterContainer


# Parameters with built-in visualizations
class FluxImpactParameter(EngineParameter):
    """Visualizes the Spectral Flux (Transients) against a threshold."""

    def draw_visual(self, surf: pygame.Surface, data: dict) -> None:
        history = data.get("flux_history", [])
        if not history:
            return

        w, h = surf.get_size()
        # Draw the Flux Sparkline
        points = []
        for i, val in enumerate(history):
            x = (i / len(history)) * w
            # Normalize flux: we'll assume 0-8 is a standard display range
            y = h - min(h, int((val / 8.0) * h))
            points.append((x, y))

        if len(points) > 1:
            pygame.draw.lines(surf, (200, 100, 255), False, points, 1)

        # Draw the Threshold Line (the 'Flux Thr' slider value)
        line_y = h - min(h, int((self.value / 8.0) * h))
        color = (255, 255, 255) if (history[-1] > self.value) else (150, 50, 200)
        pygame.draw.line(surf, color, (0, line_y), (w, line_y), 2)


class ChromaSensitivityParameter(NumericParameter):
    """Visualizes the 12 Chroma notes and the relative sensitivity gate."""

    def draw_visual(self, surf: pygame.Surface, data: dict):
        notes = data.get("prev_energies", [0.0] * 12)
        w, h = surf.get_size()

        peak = max(notes) if any(notes) else 1.0
        threshold_val = peak * self.value
        bar_w = w / 12

        for i, energy in enumerate(notes):
            bar_h = int((energy / peak) * h)
            color = (0, 255, 150) if energy >= threshold_val else (40, 60, 50)
            pygame.draw.rect(surf, color, (i * bar_w + 1, h - bar_h, bar_w - 2, bar_h))

        # Relative threshold line
        line_y = h - int(self.value * h)
        pygame.draw.line(surf, (255, 255, 0), (0, line_y), (w, line_y), 1)


class SpectrumGainParameter(EngineParameter):
    """Shows a live mini-meter next to the Gain sliders."""

    def draw_visual(self, surf: pygame.Surface, data: dict) -> None:
        w, h = surf.get_size()
        # Determine which band this specific slider represents
        band_key = "low" if "Low" in self.name else "mid" if "Mid" in self.name else "high"
        val = data.get(band_key, 0.0)

        # Color mapping
        color = (255, 50, 50) if band_key == "low" else (50, 255, 50) if band_key == "mid" else (50, 100, 255)

        # Draw meter background
        pygame.draw.rect(surf, (30, 30, 35), (0, 0, w, h))
        # Draw fill (clamped 0.0 to 1.0)
        fill_w = int(w * max(0, min(1.0, val)))
        pygame.draw.rect(surf, color, (0, 0, fill_w, h))
        # Draw a 'clipping' warning if the signal is hitting max
        if val >= 1.0:
            pygame.draw.rect(surf, (255, 255, 255), (w - 5, 0, 5, h))


# Containers of parameters for grouped displaying
class Envelope(ParameterContainer):
    """
    A strictly coupled container for Attack and Decay physics.
    It manages two internal NumericParameters and shares a unified visual.
    """

    def __init__(self, name: str, atk: NumericParameter, dcy: NumericParameter, category: str = "physics"):
        # Pass the parameters up to the base class as a list
        super().__init__(name, [atk, dcy], category=category)

        # Keep named references for internal logic
        self.atk = atk
        self.dcy = dcy

    def draw_visual(self, surf: pygame.Surface, data: dict):
        """
        Renders the unified high-density 'Needle + Bar' graph.
        Shared by both Attack and Decay rows.
        """
        w, h = surf.get_size()

        # Fetch live audio data (e.g., 'low' and 'raw_low')
        key = self.name.lower()
        smooth_val = data.get(key, 0.0)
        raw_val = data.get(f"raw_{key}", 0.0)

        # Draw Background
        surf.fill((20, 20, 25))

        # 1. The 'Decay' Body (Band-specific colors)
        color = (255, 50, 50) if key == "low" else (50, 255, 50) if key == "mid" else (50, 100, 255)

        fill_w = int(w * max(0.0, min(1.0, smooth_val)))
        if fill_w > 0:
            pygame.draw.rect(surf, color, (0, 0, fill_w, h))

        # 2. The 'Attack' Spark (White Needle for instant hits)
        hit_x = int(w * max(0.0, min(1.0, raw_val)))
        pygame.draw.line(surf, (255, 255, 255), (hit_x, 0), (hit_x, h), 2)

    def __str__(self) -> str:
        return f"Envelope: {self.name}"
