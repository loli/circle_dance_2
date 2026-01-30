import math
import sys

import pygame

from note_dancer.visualization_v2.base.audioviz import AudioVisualizationBase
from note_dancer.visualization_v2.base.hud import BooleanParameter, NumericParameter
from note_dancer.visualization_v2.radar.note_trace import NoteTrace


class RadarVisualizer(AudioVisualizationBase):
    def __init__(self, width=900, height=900):
        super().__init__()
        self.width, self.height = width, height
        self.center = (width // 2, height // 2)

        # --- Override Engine Defaults for this specific Viz ---
        self.low_gain.value = 5.0
        self.low_atk.value = 0.85
        self.low_dcy.value = 0.10

        self.mid_gain.value = 12.0
        self.mid_atk.value = 0.60
        self.mid_dcy.value = 0.20

        self.high_gain.value = 26.0
        self.high_atk.value = 0.75
        self.high_dcy.value = 0.26

        self.flux_thr.value = 6.30  # Higher threshold for cleaner snaps
        self.note_sens.value = 0.95  # Only very high (relative) note energies result in notes appearing

        # --- Scene Controls ---
        self.show_rings = self.hud.register(BooleanParameter("Show Rings", True, category="local"))
        self.enable_flash = self.hud.register(BooleanParameter("Flash Base", False, category="local"))
        self.half_rotation_speed = self.hud.register(BooleanParameter("Half Rotation Speed", False, category="local"))
        self.max_node_size = self.hud.register(NumericParameter("Node Size", 20.0, 5.0, 150.0, 5.0, category="local"))
        self.lag_comp = self.hud.register(NumericParameter("Lag Comp", 2.0, -30.0, 30.0, 1.0, category="local"))

        # --- Hidden Parameters (can be made visible if deemed required) ---
        self.inner_radius = self.hud.register(
            NumericParameter("Inner Rad", 150.0, 50.0, 400.0, 10.0, category="hidden")
        )

        # --- 2. State ---
        self.scanning_angle = 0.0
        self.active_traces = []
        self.ring_spacing = 22.0

    def render_visualization(self, screen, font):
        # 1. Process Audio Physics
        events = self.process_audio_frame()
        if not events:
            return

        # 2. Rotational Physics (Synced to Smoothed BPM)
        # default: 1 Rotation every 8 beats
        rotation_every_n_beats = 16 if self.half_rotation_speed.value else 8
        bps = events["bpm"] / 60.0
        degrees_per_frame = (360.0 * bps) / (60.0 * rotation_every_n_beats)
        self.scanning_angle = (self.scanning_angle + degrees_per_frame) % 360

        # Decay rate ensures notes disappear just before the radar hits them again
        clearance_gap = 15.0  # degree
        effective_degrees = 360.0 - clearance_gap
        decay_rate = 255.0 / (effective_degrees / max(0.01, degrees_per_frame))

        # 3. Background: Fill and optional Flash (on Impact, flux threshold crossing)
        # Base color is always there to "clear" the previous frame
        base_color = 10
        flash_amt = 25 if (self.enable_flash.value and events["impact"]) else 0
        total_v = base_color + flash_amt
        screen.fill((total_v, total_v, total_v + 8))  # +8 gives it that slight "Radar Blue" tint

        # 4. Spawn New Note Traces
        for note_idx in events["active_notes"]:
            energy = self.notes[note_idx]
            self.active_traces.append(
                NoteTrace(
                    note_idx,
                    self.scanning_angle,
                    energy,
                    decay_rate,
                    self.inner_radius.value,
                    self.ring_spacing,
                    self.max_node_size.value,
                )
            )

        # 5. Draw the Staff (Concentric Rings)
        if self.show_rings.value:
            # Ducking driven by smoothed Lows (Attack/Decay applied)
            duck = events["low"] * 30.0
            for i in range(12):
                r = self.inner_radius.value + (i * self.ring_spacing) - duck
                # Mids brighten the rings
                ring_bright = 40 + int(events["mid"] * 50)
                pygame.draw.circle(screen, (ring_bright, ring_bright, ring_bright + 15), self.center, int(r), 1)

        # 6. Update and Draw Particles
        self.active_traces = [t for t in self.active_traces if t.update()]
        for t in self.active_traces:
            t.draw(screen, self.center, events["low"], self.lag_comp.value)

        # 7. Radar Sweep Line
        rad = math.radians(self.scanning_angle - 90)
        line_len = self.inner_radius.value + (12 * self.ring_spacing)
        end_pos = (self.center[0] + line_len * math.cos(rad), self.center[1] + line_len * math.sin(rad))
        # Pulse white on the rhythmic beat
        line_color = (255, 255, 255) if events["beat"] else (120, 150, 255)
        pygame.draw.line(screen, line_color, self.center, end_pos, 2)

    def run(self):
        """Main Pygame execution loop."""
        pygame.init()
        screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("V2 Radar Visualizer - Note Dancer")
        clock = pygame.time.Clock()
        # High-contrast monospace font for the HUD
        font = pygame.font.SysFont("monospace", 16, bold=True)

        print("Radar Visualizer Started.")
        print("Press 'H' to toggle the Tuning HUD.")

        running = True
        while running:
            # 1. Event Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    # Pass keys to the HUD for parameter tuning
                    self.handle_keys(event.key)

            # 2. Drawing (The Base class calls render_visualization + HUD draw)
            # We don't need to call update() separately; process_audio_frame handles it.
            self.draw(screen, font)

            # 3. Finalize Frame
            pygame.display.flip()
            clock.tick(60)

        pygame.quit()
        sys.exit()


def run():
    """Standalone function to run the Radar Visualizer."""
    viz = RadarVisualizer()
    viz.run()


if __name__ == "__main__":
    run()
