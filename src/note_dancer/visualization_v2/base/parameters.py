import json
import socket

import pygame

from note_dancer.visualization_v2.base.hud import NumericParameter


class EngineParameter(NumericParameter):
    """Extends your NumericParameter to send updates back to the Audio Engine."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.cmd_addr = ("127.0.0.1", 5006)

    def handle(self, key: int) -> bool:
        changed = super().handle(key)
        if changed:
            # Automatic mapping: "Low Gain" -> "low_gain"
            engine_key = self.name.lower().replace(" ", "_")

            # Manual override for specific naming differences
            if engine_key == "flux_thr":
                engine_key = "flux_sens"

            msg = json.dumps({engine_key: float(self.value)})
            self.cmd_sock.sendto(msg.encode(), self.cmd_addr)
        return changed


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


class ADRenderParameter(NumericParameter):
    """
    Visualizes the 'weight' of the animation.
    Automatically switches between Low/Mid/High based on its name.
    """

    def draw_visual(self, surf: pygame.Surface, data: dict) -> None:
        w, h = surf.get_size()

        # 1. Determine which band we are tracking
        # If the parameter name contains "Mid" or "High", use those keys
        name_lower = self.name.lower()
        key_suffix = "mid" if "mid" in name_lower else "high" if "high" in name_lower else "low"

        smooth_val = data.get(key_suffix, 0.0)
        raw_val = data.get(f"raw_{key_suffix}", 0.0)

        # Color based on band (matching your Dashboard colors)
        bar_color = (255, 50, 50) if key_suffix == "low" else (50, 255, 50) if key_suffix == "mid" else (50, 100, 255)
        # De-saturate the bar color slightly for the "trail" look
        trail_color = [max(0, c - 100) for c in bar_color]

        # Draw Background
        surf.fill((20, 20, 25))

        # 2. Draw the Smoothed 'Decay' Bar
        trail_w = int(w * max(0, min(1.0, smooth_val)))
        if trail_w > 0:
            pygame.draw.rect(surf, trail_color, (0, 0, trail_w, h))

        # 3. Draw the Raw 'Attack' Spark
        hit_x = int(w * max(0, min(1.0, raw_val)))
        if hit_x > 0:
            pygame.draw.rect(surf, (255, 255, 255), (hit_x - 1, 0, 3, h))
