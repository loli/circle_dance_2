import colorsys
import math

import pygame

from note_dancer.visualization.base.audioviz import AudioVisualizationBase
from note_dancer.visualization.base.hud import HUD, NumericParameter

# --- Setup ---
WIDTH, HEIGHT = 900, 900
CENTER = (WIDTH // 2, HEIGHT // 2)


class NoteTrace:
    def __init__(self, note_index, angle, energy, decay_rate, inner_r, spacing, max_size):
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

    def update(self):
        self.life -= self.decay_rate

    def draw(self, surface, current_boost, lag_comp, global_brightness):
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
    def __init__(self, hud):
        # 1. Initialize the Audio Brain (Base Class)
        super().__init__(hud)

        # 2. Register LOCAL Parameters (These will appear in the Top-Left HUD)
        self.max_node_size = self.hud.register(
            NumericParameter("Max Node Size", 95.0, 5.0, 150.0, 5.0, fmt="{:.0f}", category="local")
        )
        self.lag_comp = self.hud.register(
            NumericParameter(
                "Lag Comp",
                2.0,
                0.0,
                30.0,
                0.5,
                fmt="{:.1f}°",
                category="local",
            )
        )
        self.inner_radius = self.hud.register(
            NumericParameter("Inner Radius", 160.0, 20.0, 300.0, 5.0, fmt="{:.0f}", category="local")
        )

        # Internal Visual State
        self.ring_spacing = 25.0
        self.scanning_angle = 0.0
        self.active_traces = []

    def update(self):
        """Main update loop: handles audio events and physics."""
        # 1. Process Audio through the Base Class 'Brain'
        # This returns only the notes that pass the noise floor, sensitivity, and attack gates.
        new_events = self.process_audio_frame()

        # 2. Create new visual traces for triggered notes
        for note in new_events:
            self.active_traces.append(
                NoteTrace(
                    note["index"],
                    self.scanning_angle,
                    note["energy"],
                    self.decay_rate,  # Calculated by Base (BPM synced)
                    self.inner_radius.value,
                    self.ring_spacing,
                    self.max_node_size.value,
                )
            )

        # 3. Update Scanning Angle
        self.scanning_angle = (self.scanning_angle + self.rotation_speed) % 360

        # 4. Update and Cull Traces
        for t in self.active_traces:
            t.update()
        self.active_traces = [t for t in self.active_traces if t.life > 0]

    def draw(self, screen, font):
        """Renders the Radar, Rings, and Traces."""
        # Background reacts to the beat (beat_boost is from Base Class)
        bg_val = max(0, 15 - int(self.beat_boost * 10))
        screen.fill((bg_val, bg_val, bg_val + 5))

        # 1. Draw Concentric Rings
        # They 'duck' slightly on the beat
        duck_offset = self.beat_boost * 15.0 if self.beat_pulse_enabled.value else 0.0
        for i in range(12):
            r = self.inner_radius.value + (i * self.ring_spacing) - duck_offset
            ring_bright = 30 + int(self.beat_boost * 30)
            pygame.draw.circle(screen, (ring_bright, ring_bright, ring_bright + 10), CENTER, int(r), 1)

        # 2. Draw Active Note Traces
        # draw_boost handles the 'swell' effect on the beat
        draw_boost = self.beat_boost if self.beat_pulse_enabled.value else 0.0
        for t in self.active_traces:
            t.draw(screen, draw_boost, self.lag_comp.value, self.current_brightness)

        # 3. Draw Scanning Radar Line
        # Brightness comes from the spectral centroid in the Base Class
        rad = math.radians(self.scanning_angle - 90)
        line_len = self.inner_radius.value + 12 * self.ring_spacing
        end_pos = (
            CENTER[0] + line_len * math.cos(rad),
            CENTER[1] + line_len * math.sin(rad),
        )

        line_width = int(2 + (self.current_brightness * 8))
        line_color = (int(200 + (self.current_brightness * 55)), int(200 + (self.current_brightness * 55)), 255)
        pygame.draw.line(screen, line_color, CENTER, end_pos, line_width)

        # 4. Delegate UI Drawing to Base HUD (Handles Global vs Local layout)
        # Note: We pass receiver.rms which is now correctly in dB from the Base Class
        self.hud.draw(screen, font, self.receiver.rms)


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Interactive Radar - Debug Meter")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("monospace", 18, bold=True)

    viz = InteractiveStaff(HUD())
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
