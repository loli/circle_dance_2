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
    def __init__(self, name: str, atk: EngineParameter, dcy: EngineParameter, category: str = "physics"):
        super().__init__(name, category=category)
        self.atk = atk
        self.dcy = dcy

    def handle(self, key: int) -> bool:
        """Pass the key to both children; return True if either changed."""
        # We use a bitwise OR here so both have a chance to process the key
        return self.atk.handle(key) | self.dcy.handle(key)

    def __str__(self) -> str:
        """Consolidated key-map and value string."""
        k1, k2 = self.atk.keys
        k3, k4 = self.dcy.keys
        # Shortening key names for space: [T/G|U/J]
        k_str = (
            f"[{pygame.key.name(k1).upper()}/{pygame.key.name(k2).upper()}|"
            f"{pygame.key.name(k3).upper()}/{pygame.key.name(k4).upper()}]"
        )
        return f"{k_str:<12} {self.name}: A{self.atk.value:.2f} D{self.dcy.value:.2f}"

    def draw_visual(self, surf: pygame.Surface, data: dict):
        """The combined 'Needle + Bar' visualization."""
        w, h = surf.get_size()
        key = self.name.lower()

        # Get physics data from engine state
        smooth_val = data.get(key, 0.0)
        raw_val = data.get(f"raw_{key}", 0.0)

        # Draw Background
        surf.fill((20, 20, 25))

        # 1. The 'Decay' Body (Colored Bar)
        color = (255, 50, 50) if key == "low" else (50, 255, 50) if key == "mid" else (50, 100, 255)
        pygame.draw.rect(surf, color, (0, 0, int(w * smooth_val), h))

        # 2. The 'Attack' Spark (White Needle)
        hit_x = int(w * raw_val)
        pygame.draw.line(surf, (255, 255, 255), (hit_x, 0), (hit_x, h), 2)
