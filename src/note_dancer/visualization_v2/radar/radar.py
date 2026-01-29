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

        # --- 1. HUD Scene Controls (Top-Left) ---
        self.show_rings = self.hud.register(BooleanParameter("Show Rings", True, category="local"))
        self.max_node_size = self.hud.register(NumericParameter("Node Size", 60.0, 5.0, 150.0, 5.0, category="local"))
        self.inner_radius = self.hud.register(
            NumericParameter("Inner Rad", 150.0, 50.0, 400.0, 10.0, category="local")
        )
        self.lag_comp = self.hud.register(NumericParameter("Lag Comp", 0.0, -30.0, 30.0, 1.0, category="local"))

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
        # 1 Rotation every 8 beats
        bps = events["bpm"] / 60.0
        degrees_per_frame = (360.0 * bps) / (60.0 * 8)
        self.scanning_angle = (self.scanning_angle + degrees_per_frame) % 360

        # Decay rate ensures notes disappear just before the radar hits them again
        decay_rate = 255.0 / (360.0 / max(0.01, degrees_per_frame))

        # 3. Background: Flash on Impact (Flux Threshold)
        bg_flash = 25 if events["impact"] else 0
        screen.fill((10 + bg_flash, 10 + bg_flash, 18 + bg_flash))

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
