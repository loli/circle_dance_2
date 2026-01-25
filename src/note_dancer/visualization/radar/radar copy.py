import pygame
import math
import colorsys
from note_dancer.visualization.base.receiver import AudioReceiver
from note_dancer.visualization.base.hud import HUD

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


class InteractiveStaff:
    def __init__(self):
        # --- Configurable Parameters ---
        self.receiver = AudioReceiver()
        self.hud = HUD()

        # Register parameters
        self.max_node_size = self.hud.add(
            "Max Node Size", 95.0, 5.0, 150.0, 5.0, (pygame.K_9, pygame.K_0), fmt="{:.0f}"
        )

        self.lag_comp = self.hud.add(
            "Lag Comp",
            2.0,
            0.0,
            30.0,
            0.5,
            ([pygame.K_MINUS, pygame.K_KP_MINUS], [pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS]),
            fmt="{:.1f}°",
        )
        self.beat_pulse_enabled = self.hud.add("Beat Pulse", True, 0, 1, 0, pygame.K_b)
        self.sensitivity_gate = self.hud.add("Sensitivity", 0.85, 0.1, 0.98, 0.02, (pygame.K_s, pygame.K_w))
        self.attack_threshold = self.hud.add("Attack Thr", 0.18, 0.01, 1.0, 0.02, (pygame.K_a, pygame.K_d))
        self.inner_radius = self.hud.add(
            "Inner Radius", 160.0, 20.0, 300.0, 5.0, (pygame.K_DOWN, pygame.K_UP), fmt="{:.0f}"
        )

        self.ring_spacing = 25.0

        # --- State Variables ---
        self.current_brightness = 0.0
        self.scanning_angle = 0.0
        self.active_traces = []
        self.current_energies = [0.0] * 12
        self.prev_energies = [0.0] * 12
        self.bpm = 120
        self.rotation_speed = 2.0
        self.decay_rate = 1.0
        self.beat_boost = 0.0

        self.update_tempo(120)

    def handle_keys(self, key):
        self.hud.handle_input(key)

    def update_tempo(self, new_bpm):
        raw_bpm = new_bpm
        while raw_bpm < 80:
            raw_bpm *= 2
        while raw_bpm > 160:
            raw_bpm /= 2
        self.bpm = (self.bpm * 0.95) + (raw_bpm * 0.05)
        beats_per_rotation = 16
        total_frames = ((60.0 / self.bpm) * beats_per_rotation) * 60.0
        self.rotation_speed = 360.0 / total_frames
        self.decay_rate = 255.0 / (360.0 / self.rotation_speed)

    def process_audio_data(self):
        self.receiver.update()

        if self.receiver.beat_detected:
            self.update_tempo(self.receiver.bpm)
            if self.beat_pulse_enabled.value:
                self.beat_boost = 1.0

        if self.receiver.notes_updated:
            new_e = self.receiver.notes
            self.current_brightness = self.receiver.brightness

            # checks if frame of notes meets criteria for processing
            is_loudness_above_floor = self.receiver.rms >= self.hud.noise_floor.value  # This ensures we skip processing when the audio is actually quiet

            if is_loudness_above_floor:
                current_peak = max(new_e) if any(new_e) else 0.0

                for i in range(12):
                    attack = new_e[i] - self.prev_energies[i]

                    # checks if note meets inclusion criteria
                    is_attack = attack > self.attack_threshold.value  # delta energy of note, compared to last frame, must be at least this strong
                    is_above_sensitivity = new_e[i] >= (current_peak * self.sensitivity_gate.value)  # energy of note must be at least this strong; effectively, must be among the sensitivity_gate% strongest notes of frame

                    if is_attack and is_above_sensitivity:
                        norm_attack = (attack - self.attack_threshold.value) / 0.8
                        norm_attack = max(0, min(1.0, norm_attack))
                        scaled_energy = norm_attack**2

                        self.active_traces.append(
                            NoteTrace(
                                i,
                                self.scanning_angle,
                                scaled_energy,
                                self.decay_rate,
                                self.inner_radius.value,
                                self.ring_spacing,
                                self.max_node_size.value,
                            )
                        )
            self.prev_energies = new_e

    def update(self):
        self.process_audio_data()
        self.scanning_angle = (self.scanning_angle + self.rotation_speed) % 360

        for t in self.active_traces:
            t.update()
        self.active_traces = [t for t in self.active_traces if t.life > 0]

        if self.beat_boost > 0:
            self.beat_boost *= 0.85
        if self.beat_boost < 0.01:
            self.beat_boost = 0

    def draw(self, screen, font):
        bg_val = max(0, 15 - int(self.beat_boost * 10))
        screen.fill((bg_val, bg_val, bg_val + 5))

        duck_offset = self.beat_boost * 15.0 if self.beat_pulse_enabled.value else 0.0

        for i in range(12):
            r = self.inner_radius.value + (i * self.ring_spacing) - duck_offset
            ring_bright = 30 + int(self.beat_boost * 30)
            pygame.draw.circle(screen, (ring_bright, ring_bright, ring_bright + 10), CENTER, int(r), 1)

        draw_boost = self.beat_boost if self.beat_pulse_enabled.value else 0.0
        for t in self.active_traces:
            t.draw(screen, draw_boost, self.lag_comp.value, self.current_brightness)

        rad = math.radians(self.scanning_angle - 90)
        end_pos = (
            CENTER[0] + (self.inner_radius.value + 12 * self.ring_spacing) * math.cos(rad),
            CENTER[1] + (self.inner_radius.value + 12 * self.ring_spacing) * math.sin(rad),
        )
        line_width = int(2 + (self.current_brightness * 8))
        line_color = (int(200 + (self.current_brightness * 55)), int(200 + (self.current_brightness * 55)), 255)

        pygame.draw.line(screen, line_color, CENTER, end_pos, line_width)

        self.hud.draw(screen, font, self.receiver.rms)


def main():
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
