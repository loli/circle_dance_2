import colorsys
import math

import pygame

from note_dancer.visualization.base.audioviz import AudioVisualizationBase
from note_dancer.visualization.base.hud import BooleanParameter, NumericParameter

# --- Setup ---
WIDTH, HEIGHT = 900, 900
CENTER = (WIDTH // 2, HEIGHT // 2)


class NoteTrace:
    def __init__(
        self,
        note_index: int,
        angle: float,
        energy: float,
        decay_rate: float,
        inner_r: float,
        spacing: float,
        max_size: float,
    ) -> None:
        self.note_index = note_index
        self.angle = angle
        self.energy = energy
        self.life = 255.0
        self.decay_rate = decay_rate
        self.inner_r = inner_r
        self.spacing = spacing
        self.max_size = max_size
        rgb = colorsys.hsv_to_rgb(note_index / 12.0, 0.8, 1.0)
        self.color = (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))

    def update(self) -> None:
        self.life -= self.decay_rate

    def draw(
        self,
        surface: pygame.Surface,
        current_boost: float,
        lag_comp: float,
        global_brightness: float,
    ) -> None:
        # 1. Color Shift (Brightness logic)
        white_mix = global_brightness * 255
        current_color = (
            min(255, int(self.color[0] + white_mix)),
            min(255, int(self.color[1] + white_mix)),
            min(255, int(self.color[2] + white_mix)),
        )

        # 2. Dynamic Alpha
        alpha = max(0, min(255, int(self.life + (global_brightness * 100))))

        # 3. Sidechain Movement (The "Duck")
        duck_factor = current_boost * 20.0
        visual_angle = self.angle + lag_comp
        r_pos = self.inner_r + (self.note_index * self.spacing) - duck_factor

        rad = math.radians(visual_angle - 90)
        x = CENTER[0] + r_pos * math.cos(rad)
        y = CENTER[1] + r_pos * math.sin(rad)

        # 4. Sidechain Scaling (The "Squash")
        base_size = int(2 + (self.energy * self.max_size))
        swell_size = int(base_size * (1.0 - current_boost * 0.4))
        swell_size = max(1, swell_size)

        # 5. Rendering
        surf_dim = max(1, swell_size * 4)
        note_surf = pygame.Surface((surf_dim, surf_dim), pygame.SRCALPHA)

        pygame.draw.circle(note_surf, (*current_color, alpha // 8), (surf_dim // 2, surf_dim // 2), swell_size * 2)
        pygame.draw.circle(note_surf, (*current_color, alpha), (surf_dim // 2, surf_dim // 2), int(swell_size // 1.5))

        surface.blit(note_surf, (x - surf_dim // 2, y - surf_dim // 2))


class InteractiveStaff(AudioVisualizationBase):
    def __init__(self) -> None:
        super().__init__()

        # 1. Register LOCAL Parameters
        self.beat_pulse_enabled = self.hud.register(BooleanParameter("Beat Pulse", True))

        self.max_node_size = self.hud.register(NumericParameter("Max Node Size", 95.0, 5.0, 150.0, 5.0, fmt="{:.0f}"))
        self.lag_comp = self.hud.register(NumericParameter("Lag Comp", 2.0, 0.0, 30.0, 0.5, fmt="{:.1f}°"))
        self.inner_radius = self.hud.register(NumericParameter("Inner Radius", 160.0, 20.0, 300.0, 5.0, fmt="{:.0f}"))

        # 2. Visual Physics State (Moved from Base)
        self.scanning_angle = 0.0
        self.rotation_speed = 2.0
        self.decay_rate = 1.0
        self.beat_boost = 0.0

        # Internal State
        self.ring_spacing = 25.0
        self.active_traces = []

    def _calculate_rotation_physics(self) -> None:
        """
        Translates current BPM into rotational constants and adjusts decay rate
        so traces decay 10 degrees before the staff reaches them again.
        """
        # Constants for 60FPS movement
        beats_per_rotation = 16
        total_frames = ((60.0 / self.bpm) * beats_per_rotation) * 60.0

        self.rotation_speed = 360.0 / total_frames
        # Adjust decay rate to account for 10-degree early decay
        self.decay_rate = 255.0 / ((360.0 - 10.0) / self.rotation_speed)

    def update(self) -> None:
        """Main update loop: handles audio events and physics."""
        new_events = self.process_audio_frame()
        self._calculate_rotation_physics()
        self._update_visual_physics()

        for note in new_events:
            self.active_traces.append(
                NoteTrace(
                    note["index"],
                    self.scanning_angle,
                    note["energy"],
                    self.decay_rate,
                    self.inner_radius.value,
                    self.ring_spacing,
                    self.max_node_size.value,
                )
            )

        self.active_traces = [t for t in self.active_traces if (t.update() or t.life > 0)]

    def _update_visual_physics(self) -> None:
        """Handles the movement and beat-pulsing logic."""
        # Update Angle
        self.scanning_angle = (self.scanning_angle + self.rotation_speed) % 360

        # Handle Beat Pulse
        if self.receiver.beat_detected and self.beat_pulse_enabled.value:
            self.beat_boost = 1.0

        self.beat_boost = max(0, self.beat_boost * 0.85)

    def render_visualization(self, screen: pygame.Surface, font: pygame.font.Font) -> None:
        """Renders the Radar, Rings, and Traces."""

        # Use self.brightness from the Base Class for visual intensity
        bg_val = max(0, 15 - int(self.beat_boost * 10))
        screen.fill((bg_val, bg_val, bg_val + 5))

        # 1. Draw Concentric Rings
        duck_offset = self.beat_boost * 15.0
        for i in range(12):
            r = self.inner_radius.value + (i * self.ring_spacing) - duck_offset
            ring_bright = 30 + int(self.beat_boost * 30)
            pygame.draw.circle(screen, (ring_bright, ring_bright, ring_bright + 10), CENTER, int(r), 1)

        # 2. Draw Active Note Traces
        for t in self.active_traces:
            t.draw(screen, self.beat_boost, self.lag_comp.value, self.brightness)

        # 3. Draw Scanning Radar Line
        rad = math.radians(self.scanning_angle - 90)
        line_len = self.inner_radius.value + 12 * self.ring_spacing
        end_pos = (
            CENTER[0] + line_len * math.cos(rad),
            CENTER[1] + line_len * math.sin(rad),
        )

        line_width = int(2 + (self.brightness * 8))
        # Use blue theme for the radar line
        line_color = (int(200 + (self.brightness * 55)), int(200 + (self.brightness * 55)), 255)
        pygame.draw.line(screen, line_color, CENTER, end_pos, line_width)


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Interactive Radar - Debug Meter")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("monospace", 18, bold=True)

    viz = InteractiveStaff()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                exit()
            if event.type == pygame.KEYDOWN:
                viz.handle_keys(event.key)
        viz.update()
        viz.draw(screen, font)
        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
