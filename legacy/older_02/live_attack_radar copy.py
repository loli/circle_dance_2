import pygame
import socket
import json
import math
import colorsys
import time

# --- Setup ---
WIDTH, HEIGHT = 900, 900
CENTER = (WIDTH // 2, HEIGHT // 2)
UDP_IP = "127.0.0.1"
UDP_PORT = 5005

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Log-Scale Interactive Radar - V2")
clock = pygame.time.Clock()
hud_font = pygame.font.SysFont("monospace", 18, bold=True)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.setblocking(False)


class NoteTrace:
    def __init__(self, note_index, angle, energy, decay_rate, inner_r, spacing, size_scalar):
        self.note_index = note_index
        self.angle = angle
        self.energy = energy
        self.life = 255.0
        self.decay_rate = decay_rate
        self.inner_r = inner_r
        self.spacing = spacing
        self.size_scalar = size_scalar  # New: Control overall size

        rgb = colorsys.hsv_to_rgb(note_index / 12.0, 0.8, 1.0)
        self.color = (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))

    def update(self):
        self.life -= self.decay_rate

    def draw(self, surface, current_boost, lag_comp):
        alpha = max(0, min(255, int(self.life + (current_boost * 100))))
        visual_angle = self.angle + lag_comp
        r = self.inner_r + (self.note_index * self.spacing)
        rad = math.radians(visual_angle - 90)
        x = CENTER[0] + r * math.cos(rad)
        y = CENTER[1] + r * math.sin(rad)

        # Sizing logic: Reduced and Scalable
        # Previously: (energy**2) * 30. Now using a user-controlled scalar.
        base_size = int(2 + (self.energy**2) * self.size_scalar)
        swell_size = int(base_size * (1.0 + current_boost * 0.5))

        # Buffer to prevent 0-size surfaces
        surf_dim = max(4, swell_size * 4)
        note_surf = pygame.Surface((surf_dim, surf_dim), pygame.SRCALPHA)
        pygame.draw.circle(note_surf, (*self.color, alpha // 6), (surf_dim // 2, surf_dim // 2), swell_size * 2)
        pygame.draw.circle(note_surf, (*self.color, alpha), (surf_dim // 2, surf_dim // 2), swell_size)
        surface.blit(note_surf, (x - surf_dim // 2, y - surf_dim // 2))


class InteractiveStaff:
    def __init__(self):
        # Parameters
        self.inner_radius = 160.0
        self.ring_spacing = 25.0
        self.sensitivity_gate = 0.73
        self.attack_threshold = 0.0233
        self.lag_comp = 2.0
        self.noise_floor = 0.35  # 0.981
        self.size_scalar = 8.0

        self.beat_pulse_enabled = True
        self.scanning_angle = 0.0
        self.active_traces = []
        self.prev_energies = [0.0] * 12
        self.peak_for_meter = 0.0
        self.bpm = 120
        self.rotation_speed = 2.0
        self.decay_rate = 1.2
        self.beat_boost = 0.0

        self.show_help = False
        self.help_timer = 0
        self.msg = ""
        self.msg_timer = 0
        self.update_tempo(120)

    def set_msg(self, text):
        self.msg = text
        self.msg_timer = time.time() + 2.0

    def handle_keys(self, key):
        # Geometric multipliers
        UP = 1.08
        DOWN = 0.92

        # Menu Toggle
        if key == pygame.K_h:
            self.show_help = not self.show_help
            self.help_timer = time.time() + 5.0

        # --- ALL CONTROLS INDEPENDENT OF MENU ---

        # Node Size (O / L)
        if key == pygame.K_o:
            self.size_scalar = min(50.0, self.size_scalar + 1.0)
            self.set_msg(f"Node Size: {self.size_scalar}")
        if key == pygame.K_l:
            self.size_scalar = max(1.0, self.size_scalar - 1.0)
            self.set_msg(f"Node Size: {self.size_scalar}")

        # Logarithmic Attack (A / D)
        if key == pygame.K_d:
            self.attack_threshold = min(1.0, max(0.0001, self.attack_threshold * UP))
            self.set_msg(f"Atk Thr: {self.attack_threshold:.4f}")
        if key == pygame.K_a:
            self.attack_threshold = max(0.0001, self.attack_threshold * DOWN)
            self.set_msg(f"Atk Thr: {self.attack_threshold:.4f}")

        # Logarithmic Floor ( , / . )
        if key == pygame.K_PERIOD:
            self.noise_floor = min(1.0, max(0.001, self.noise_floor * UP))
            self.set_msg(f"Floor: {self.noise_floor:.3f}")
        if key == pygame.K_COMMA:
            self.noise_floor = max(0.001, self.noise_floor * DOWN)
            self.set_msg(f"Floor: {self.noise_floor:.3f}")

        # Linear Controls
        if key in [pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS]:
            self.lag_comp += 0.5
            self.set_msg(f"Lag: {self.lag_comp}")
        if key in [pygame.K_MINUS, pygame.K_KP_MINUS]:
            self.lag_comp -= 0.5
            self.set_msg(f"Lag: {self.lag_comp}")

        if key == pygame.K_w:
            self.sensitivity_gate = min(0.995, self.sensitivity_gate + 0.005)
            self.set_msg(f"Gate: {self.sensitivity_gate:.3f}")
        if key == pygame.K_s:
            self.sensitivity_gate = max(0.1, self.sensitivity_gate - 0.005)
            self.set_msg(f"Gate: {self.sensitivity_gate:.3f}")

        if key == pygame.K_UP:
            self.inner_radius += 5
        if key == pygame.K_DOWN:
            self.inner_radius -= 5
        if key == pygame.K_b:
            self.beat_pulse_enabled = not self.beat_pulse_enabled
            self.set_msg(f"Beat Pulse: {self.beat_pulse_enabled}")

    def update_tempo(self, new_bpm):
        raw_bpm = new_bpm if new_bpm > 0 else 120
        while raw_bpm < 80:
            raw_bpm *= 2
        while raw_bpm > 160:
            raw_bpm /= 2
        self.bpm = (self.bpm * 0.95) + (raw_bpm * 0.05)
        total_frames = ((60.0 / self.bpm) * 16) * 60.0
        self.rotation_speed = 360.0 / total_frames
        self.decay_rate = 255.0 / (360.0 / self.rotation_speed)

    def capture_audio(self):
        try:
            while True:
                data, _ = sock.recvfrom(2048)
                decoded = json.loads(data.decode("utf-8"))
                if isinstance(decoded, dict):
                    if "bpm" in decoded:
                        self.update_tempo(decoded["bpm"])
                        if self.beat_pulse_enabled:
                            self.beat_boost = 1.0
                else:
                    new_e = decoded
                    self.peak_for_meter = max(new_e) if any(new_e) else 0.0

                    # 1. FIXED NOISE FLOOR LOGIC
                    # Now that the meter isn't always full,
                    # the noise floor will actually work as a gate.
                    if self.peak_for_meter >= self.noise_floor:
                        for i in range(12):
                            if new_e[i] < self.noise_floor:
                                continue

                            diff = new_e[i] - self.prev_energies[i]

                            # 2. IMPROVED DETECTION GATE
                            # We check if the note is a local peak AND if it's rising
                            if diff > self.attack_threshold and new_e[i] >= (
                                self.peak_for_meter * self.sensitivity_gate
                            ):

                                # 3. WEIGHTED ENERGY SIZING
                                # We combine the 'jump' (diff) with the 'absolute volume' (new_e)
                                # This prevents notes from getting smaller during loud sections.
                                visual_energy = (diff * 8.0) + (new_e[i] * 0.5)

                                self.active_traces.append(
                                    NoteTrace(
                                        i,
                                        self.scanning_angle,
                                        visual_energy,
                                        self.decay_rate,
                                        self.inner_radius,
                                        self.ring_spacing,
                                        self.size_scalar,
                                    )
                                )
                    self.prev_energies = new_e
        except (BlockingIOError, json.JSONDecodeError):
            pass

    def update(self):
        self.scanning_angle = (self.scanning_angle + self.rotation_speed) % 360
        for t in self.active_traces:
            t.update()
        self.active_traces = [t for t in self.active_traces if t.life > 0]
        if self.beat_boost > 0:
            self.beat_boost *= 0.88
        if time.time() > self.help_timer:
            self.show_help = False

    def draw(self):
        screen.fill((12 + int(self.beat_boost * 12), 12, 18))
        for i in range(12):
            r = self.inner_radius + (i * self.ring_spacing)
            c = 45 + int(self.beat_boost * 35)
            pygame.draw.circle(screen, (c, c, c + 5), CENTER, int(r), 1)

        draw_boost = self.beat_boost if self.beat_pulse_enabled else 0.0
        for t in self.active_traces:
            t.draw(screen, draw_boost, self.lag_comp)

        rad = math.radians(self.scanning_angle - 90)
        end_pos = (
            CENTER[0] + (self.inner_radius + 12 * self.ring_spacing) * math.cos(rad),
            CENTER[1] + (self.inner_radius + 12 * self.ring_spacing) * math.sin(rad),
        )
        pygame.draw.line(screen, (180, 180, 255), CENTER, end_pos, 2)

        if self.show_help:
            m_x, m_y, m_w, m_h = 420, 20, 25, 150
            pygame.draw.rect(screen, (30, 30, 30), (m_x, m_y, m_w, m_h))
            fill_h = int(min(1.0, self.peak_for_meter) * m_h)
            pygame.draw.rect(screen, (0, 180, 255), (m_x, m_y + m_h - fill_h, m_w, fill_h))
            floor_y = m_y + m_h - int(self.noise_floor * m_h)
            pygame.draw.line(screen, (255, 60, 60), (m_x - 8, floor_y), (m_x + m_w + 8, floor_y), 3)

            lines = [
                f"Atk Thr [A/D] : {self.attack_threshold:.4f}",
                f"Floor   [,/.] : {self.noise_floor:.3f}",
                f"Gate    [W/S] : {self.sensitivity_gate:.3f}",
                f"Node Sz [O/L] : {self.size_scalar}",
                f"Lag     [+/-] : {self.lag_comp:.1f}",
                f"BPM           : {int(self.bpm)}",
            ]
            for i, l in enumerate(lines):
                img = hud_font.render(l, True, (0, 255, 180))
                screen.blit(img, (20, 20 + i * 26))
        elif time.time() < self.msg_timer:
            img = hud_font.render(self.msg, True, (255, 255, 255))
            screen.blit(img, (20, 20))


# --- Run ---
viz = InteractiveStaff()
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            exit()
        if event.type == pygame.KEYDOWN:
            viz.handle_keys(event.key)
    viz.capture_audio()
    viz.update()
    viz.draw()
    pygame.display.flip()
    clock.tick(60)
