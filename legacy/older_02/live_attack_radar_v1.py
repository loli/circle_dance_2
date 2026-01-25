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
pygame.display.set_caption("Interactive Radar - Debug Meter")
clock = pygame.time.Clock()
hud_font = pygame.font.SysFont("monospace", 18, bold=True)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.setblocking(False)


class NoteTrace:
    def __init__(self, note_index, angle, energy, decay_rate, inner_r, spacing):
        self.note_index = note_index
        self.angle = angle
        self.energy = energy
        self.life = 255.0
        self.decay_rate = decay_rate
        self.inner_r = inner_r
        self.spacing = spacing
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
        base_size = int(4 + (self.energy**2) * 20)
        swell_size = int(base_size * (1.0 + current_boost * 0.8))
        note_surf = pygame.Surface((swell_size * 4, swell_size * 4), pygame.SRCALPHA)
        pygame.draw.circle(note_surf, (*self.color, alpha // 6), (swell_size * 2, swell_size * 2), swell_size * 2)
        pygame.draw.circle(note_surf, (*self.color, alpha), (swell_size * 2, swell_size * 2), swell_size)
        surface.blit(note_surf, (x - swell_size * 2, y - swell_size * 2))


class InteractiveStaff:
    def __init__(self):
        # --- Configurable Parameters ---
        self.inner_radius = 160.0
        self.ring_spacing = 25.0
        self.sensitivity_gate = 0.85
        self.attack_threshold = 0.18
        self.lag_comp = 2.0
        self.noise_floor = 0.05

        self.beat_pulse_enabled = True
        self.scanning_angle = 0.0
        self.active_traces = []
        self.current_energies = [0.0] * 12
        self.prev_energies = [0.0] * 12
        self.peak_for_meter = 0.0  # Used for the HUD meter
        self.bpm = 120
        self.rotation_speed = 2.0
        self.decay_rate = 1.0
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
        if key == pygame.K_h:
            self.show_help = True
            self.help_timer = time.time() + 4.0
        if key == pygame.K_PERIOD:
            self.noise_floor = min(1.0, self.noise_floor + 0.01)
            self.set_msg(f"Noise Floor: {self.noise_floor:.2f}")
        if key == pygame.K_COMMA:
            self.noise_floor = max(0.0, self.noise_floor - 0.01)
            self.set_msg(f"Noise Floor: {self.noise_floor:.2f}")
        if key in [pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS]:
            self.lag_comp = min(30.0, self.lag_comp + 0.5)
            self.set_msg(f"Lag Comp: {self.lag_comp}°")
        if key in [pygame.K_MINUS, pygame.K_KP_MINUS]:
            self.lag_comp = max(0.0, self.lag_comp - 0.5)
            self.set_msg(f"Lag Comp: {self.lag_comp}°")
        if key == pygame.K_b:
            self.beat_pulse_enabled = not self.beat_pulse_enabled
            self.set_msg(f"Beat Pulse: {'ON' if self.beat_pulse_enabled else 'OFF'}")
        if key == pygame.K_w:
            self.sensitivity_gate = min(0.98, self.sensitivity_gate + 0.02)
            self.set_msg(f"Gate: {self.sensitivity_gate:.2f}")
        if key == pygame.K_s:
            self.sensitivity_gate = max(0.1, self.sensitivity_gate - 0.02)
            self.set_msg(f"Gate: {self.sensitivity_gate:.2f}")
        if key == pygame.K_d:
            self.attack_threshold = min(1.0, self.attack_threshold + 0.02)
            self.set_msg(f"Attack Thr: {self.attack_threshold:.2f}")
        if key == pygame.K_a:
            self.attack_threshold = max(0.01, self.attack_threshold - 0.02)
            self.set_msg(f"Attack Thr: {self.attack_threshold:.2f}")
        if key == pygame.K_UP:
            self.inner_radius = min(300, self.inner_radius + 5)
            self.set_msg(f"Inner Radius: {int(self.inner_radius)}")
        if key == pygame.K_DOWN:
            self.inner_radius = max(20, self.inner_radius - 5)
            self.set_msg(f"Inner Radius: {int(self.inner_radius)}")

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

    def capture_audio(self):
        try:
            while True:
                data, _ = sock.recvfrom(1024)
                decoded = json.loads(data.decode("utf-8"))
                if isinstance(decoded, dict):
                    if "bpm" in decoded:
                        self.update_tempo(decoded["bpm"])
                        if self.beat_pulse_enabled:
                            self.beat_boost = 1.0
                else:
                    new_e = decoded
                    self.peak_for_meter = max(new_e) if any(new_e) else 0.0

                    # Logic Fix: If peak is below floor, entire chunk is discarded
                    if self.peak_for_meter < self.noise_floor:
                        self.prev_energies = new_e
                        continue

                    for i in range(12):
                        if new_e[i] < self.noise_floor:
                            continue
                        attack = max(0, new_e[i] - self.prev_energies[i])
                        if attack > self.attack_threshold and new_e[i] >= (
                            self.peak_for_meter * self.sensitivity_gate
                        ):
                            self.active_traces.append(
                                NoteTrace(
                                    i,
                                    self.scanning_angle,
                                    attack,
                                    self.decay_rate,
                                    self.inner_radius,
                                    self.ring_spacing,
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
            self.beat_boost *= 0.85
        if self.beat_boost < 0.01:
            self.beat_boost = 0
        if time.time() > self.help_timer:
            self.show_help = False

    def draw(self):
        bg_val = 10 + int(self.beat_boost * 15)
        screen.fill((bg_val, bg_val, bg_val + 5))
        for i in range(12):
            r = self.inner_radius + (i * self.ring_spacing)
            ring_bright = 30 + int(self.beat_boost * 40)
            pygame.draw.circle(screen, (ring_bright, ring_bright, ring_bright + 10), CENTER, int(r), 1)

        draw_boost = self.beat_boost if self.beat_pulse_enabled else 0.0
        for t in self.active_traces:
            t.draw(screen, draw_boost, self.lag_comp)

        # Playhead
        rad = math.radians(self.scanning_angle - 90)
        end_pos = (
            CENTER[0] + (self.inner_radius + 12 * self.ring_spacing) * math.cos(rad),
            CENTER[1] + (self.inner_radius + 12 * self.ring_spacing) * math.sin(rad),
        )
        pygame.draw.line(screen, (200, 200, 255), CENTER, end_pos, 2)

        # HUD and METER
        now = time.time()
        if self.show_help:
            # 1. Parameter List
            help_surf = pygame.Surface((380, 210), pygame.SRCALPHA)
            help_surf.fill((0, 0, 0, 180))
            screen.blit(help_surf, (10, 10))
            lines = [
                f"[ , / . ] Noise Floor:    {self.noise_floor:.2f}",
                f"[+/-]     Lag Comp:       {self.lag_comp}°",
                f"[B]       Beat Pulse:     {'ON' if self.beat_pulse_enabled else 'OFF'}",
                f"[W/S]     Sensitivity:    {self.sensitivity_gate:.2f}",
                f"[A/D]     Attack Thr:     {self.attack_threshold:.2f}",
                f"[UP/DN]   Inner Rad:      {int(self.inner_radius)}",
                f"BPM: {int(self.bpm)}",
            ]
            for i, line in enumerate(lines):
                img = hud_font.render(line, True, (0, 255, 180))
                screen.blit(img, (20, 20 + i * 25))

            # 2. Peak Energy Meter (Diagnostic)
            # Draws a vertical bar showing current volume vs noise floor
            m_x, m_y, m_w, m_h = 400, 20, 20, 150
            pygame.draw.rect(screen, (50, 50, 50), (m_x, m_y, m_w, m_h))  # Background

            # Current Peak level (clamped for display)
            fill_h = int(min(1.0, self.peak_for_meter) * m_h)
            pygame.draw.rect(screen, (0, 200, 255), (m_x, m_y + m_h - fill_h, m_w, fill_h))

            # Noise Floor Threshold Line
            floor_y = m_y + m_h - int(self.noise_floor * m_h)
            pygame.draw.line(screen, (255, 50, 50), (m_x - 5, floor_y), (m_x + m_w + 5, floor_y), 3)
            label = hud_font.render("FLOOR", True, (255, 50, 50))
            screen.blit(label, (m_x + m_w + 10, floor_y - 10))

        elif now < self.msg_timer:
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
