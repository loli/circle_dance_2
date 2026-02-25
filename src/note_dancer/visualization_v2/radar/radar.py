import math

import pygame

from note_dancer.visualization_v2.base.audioviz import AudioVisualizationBase
from note_dancer.visualization_v2.base.hud import BooleanParameter, NumericParameter
from note_dancer.visualization_v2.radar.note_trace import NoteTrace

NEON_PALETTE = [
    (255, 0, 180),  # Magenta
    (255, 170, 0),  # Amber
    (14, 255, 178),  # Electric Mint (Colder than Phosphor Green)
    (0, 180, 255),  # Deep Azure (More saturated than standard Cyan)
    (255, 230, 0),  # Radioactive Lemon (Piercing, better than Amber)
    (180, 50, 255),  # Hyper-Violet (Deep, moody alternative to Magenta)
    (255, 60, 110),  # Crimson Neon (A "hot" pink/red that cuts through black)
    (220, 240, 255),  # Glacier Blue (A high-luma 'White' with a blue soul)
]


class RadarVisualizer(AudioVisualizationBase):
    def __init__(self):
        # Pass dimensions to Base for window creation
        super().__init__()

        # --- Radar Specific Defaults ---
        self.low_gain.value = 0.8
        self.low_atk.value = 0.85
        self.low_dcy.value = 0.10
        self.mid_gain.value = 0.8
        self.mid_atk.value = 0.60
        self.mid_dcy.value = 0.20
        self.high_gain.value = 0.8
        self.high_atk.value = 0.75
        self.high_dcy.value = 0.26
        self.flux_thr.value = 6.30
        self.note_sens.value = 0.96

        # --- Scene Controls ---
        self.note_style = self.hud.register(NumericParameter("Note Style", 0, 0, 3, 1, category="local"))
        self.color_schema = self.hud.register(NumericParameter("Color Schema", 0, 0, 2, 1, category="local"))
        self.neon_hue_idx = self.hud.register(
            NumericParameter("Neon Hue", 0, 0, len(NEON_PALETTE) - 1, 1, category="local")
        )
        self.show_rings = self.hud.register(BooleanParameter("Show Rings", True, category="local"))
        self.enable_flash = self.hud.register(BooleanParameter("Flash Base", False, category="local"))
        self.half_rotation_speed = self.hud.register(BooleanParameter("Half Rotation Speed", False, category="local"))
        self.max_node_size = self.hud.register(NumericParameter("Node Size", 20.0, 5.0, 150.0, 5.0, category="local"))
        self.lag_comp = self.hud.register(NumericParameter("Lag Comp", 2.0, -30.0, 30.0, 1.0, category="local"))
        self.inner_radius = self.hud.register(
            NumericParameter("Inner Rad", 150.0, 50.0, 400.0, 10.0, category="hidden")
        )

        # --- State ---
        self.scanning_angle = 0.0
        self.active_traces = []
        self.ring_spacing = 22.0

    def render_visualization(self, screen, font):
        events = self.process_audio_frame()
        if not events:
            return

        # 1. Apply Responsive Scaling
        sf = self.scale_factor
        scaled_inner_r = self.inner_radius.value * sf
        scaled_spacing = self.ring_spacing * sf
        scaled_node_size = self.max_node_size.value * sf

        # 2. Rotational Physics (Unchanged)
        rotation_every_n_beats = 16 if self.half_rotation_speed.value else 8
        bps = events["bpm"] / 60.0
        degrees_per_frame = (360.0 * bps) / (60.0 * rotation_every_n_beats)
        self.scanning_angle = (self.scanning_angle + degrees_per_frame) % 360

        decay_rate = 255.0 / ((360.0 - 15.0) / max(0.01, degrees_per_frame))

        # --- 3. Background: Fill and optional Flash ---
        # Base luminance (10 is a deep, dark grey-blue)
        base_color = 10

        # Calculate flash: pulses brighter when 'impact' (flux threshold) is triggered
        flash_amt = 25 if (self.enable_flash.value and events["impact"]) else 0
        total_v = base_color + flash_amt

        # Fill with a slight blue-shift in the Blue channel (+8) for that radar look
        screen.fill((total_v, total_v, total_v + 8))

        # 4. Spawn Notes (Now using scaled values)
        for note_idx in events["active_notes"]:
            self.active_traces.append(
                NoteTrace(
                    note_idx,
                    self.scanning_angle,
                    self.notes[note_idx],  # 'energy' here is now a perfect logarithmic 0.0 to 1.0
                    decay_rate,
                    scaled_inner_r,
                    scaled_spacing,
                    scaled_node_size,
                )
            )

        # 5. Draw Rings (Now using scaled values)
        if self.show_rings.value:
            duck = events["low"] * (30.0 * sf)  # Scale the movement too!
            for i in range(12):
                r = scaled_inner_r + (i * scaled_spacing) - duck
                ring_bright = 40 + int(events["mid"] * 50)
                # Thicker rings on larger screens
                thickness = max(1, int(1 * sf))
                pygame.draw.circle(
                    screen, (ring_bright, ring_bright, ring_bright + 15), self.center, int(r), thickness
                )

        # 6. Update and Draw Particles
        self.active_traces = [t for t in self.active_traces if t.update()]
        current_neon_color = NEON_PALETTE[int(self.neon_hue_idx.value)]
        for t in self.active_traces:
            t.draw(
                screen,
                self.center,
                events["low"],
                self.lag_comp.value,
                self.note_style.value,
                self.color_schema.value,
                current_neon_color,
            )

        # 7. Sweep Line (Scaled length)
        rad = math.radians(self.scanning_angle - 90)
        line_len = scaled_inner_r + (12 * scaled_spacing)
        end_pos = (self.center[0] + line_len * math.cos(rad), self.center[1] + line_len * math.sin(rad))

        line_color = (255, 255, 255) if events["beat"] else (120, 150, 255)
        pygame.draw.line(screen, line_color, self.center, end_pos, max(1, int(2 * sf)))

        # 8. Store metrics for debug overlay
        self._active_traces_count = len(self.active_traces)
        self._cache_size = len(NoteTrace._glowing_orb_cache)

    def run(self):
        """Now calling the centralized run in Base class."""
        print("Radar Visualizer Started.")
        print("F: Toggle Fullscreen | ESC: Quit | H: Toggle HUD")
        super().run(title="V2 Radar Visualizer - Note Dancer")


def run():
    RadarVisualizer().run()


if __name__ == "__main__":
    run()
