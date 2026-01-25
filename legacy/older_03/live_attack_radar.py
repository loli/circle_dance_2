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


class AudioReceiver:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((UDP_IP, UDP_PORT))
        self.sock.setblocking(False)

        # The "Database" - Source of Truth
        self.bpm = 120
        self.notes = [0.0] * 12
        self.brightness = 0.0

        # Event Flags
        self.beat_detected = False
        self.notes_updated = False

    def update(self):
        self.beat_detected = False
        self.notes_updated = False
        try:
            while True:
                data, _ = self.sock.recvfrom(2048)
                decoded = json.loads(data.decode("utf-8"))

                if "bpm" in decoded:
                    self.bpm = decoded["bpm"]
                    self.beat_detected = True
                elif "notes" in decoded:
                    self.notes = decoded["notes"]
                    self.brightness = decoded.get("brightness", 0.0)
                    self.notes_updated = True
        except (BlockingIOError, json.JSONDecodeError):
            pass


class Tunable:
    def __init__(self, name, val, min_v, max_v, step, keys, fmt="{:.2f}", transformer=None):
        self.name = name
        self.value = val
        self.min_v = min_v
        self.max_v = max_v
        self.step = step
        self.keys = keys  # (dec, inc) or single key for toggle
        self.fmt = fmt
        self.transformer = transformer

    def handle(self, key):
        # Toggle
        if isinstance(self.keys, int):
            if key == self.keys:
                self.value = not self.value
                return True
            return False

        # Range
        dec, inc = self.keys
        if not isinstance(dec, (list, tuple)):
            dec = [dec]
        if not isinstance(inc, (list, tuple)):
            inc = [inc]

        if key in dec:
            self._update(-1)
            return True
        if key in inc:
            self._update(1)
            return True
        return False

    def _update(self, direction):
        if self.transformer:
            self.value = self.transformer(self.value, self.step, direction)
        else:
            self.value += self.step * direction

        # Clamp
        if isinstance(self.value, (int, float)):
            self.value = max(self.min_v, min(self.max_v, self.value))

    def __str__(self):
        if isinstance(self.value, bool):
            v_str = "ON" if self.value else "OFF"
            k_str = f"[{pygame.key.name(self.keys).upper()}]"
        else:
            v_str = self.fmt.format(self.value)
            k1 = self.keys[0] if not isinstance(self.keys[0], (list, tuple)) else self.keys[0][0]
            k2 = self.keys[1] if not isinstance(self.keys[1], (list, tuple)) else self.keys[1][0]
            k_str = f"[{pygame.key.name(k1).upper()}/{pygame.key.name(k2).upper()}]"

        return f"{k_str:<12} {self.name}: {v_str}"


class HUD:
    def __init__(self):
        self.params = []
        self.show_help = False
        self.help_timer = 0
        self.msg = ""
        self.msg_timer = 0

    def add(self, *args, **kwargs):
        t = Tunable(*args, **kwargs)
        self.params.append(t)
        return t

    def handle_input(self, key):
        if key == pygame.K_h:
            self.show_help = not self.show_help
            self.help_timer = time.time() + 30.0 if self.show_help else 0
            return

        for p in self.params:
            if p.handle(key):
                self.msg = str(p)
                self.msg_timer = time.time() + 2.0
                return

    def draw(self, surface, font, peak_meter=0.0, noise_floor=0.0):
        # Draw Msg
        if time.time() < self.msg_timer and not self.show_help:
            img = font.render(self.msg, True, (255, 255, 255))
            surface.blit(img, (20, 20))

        # Draw Help
        if self.show_help:
            if time.time() > self.help_timer:
                self.show_help = False
                return

            bg = pygame.Surface((450, 40 + len(self.params) * 25 + 160), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 180))
            surface.blit(bg, (10, 10))

            for i, p in enumerate(self.params):
                img = font.render(str(p), True, (0, 255, 180))
                surface.blit(img, (20, 20 + i * 25))

            # Meter
            m_y_start = 20 + len(self.params) * 25 + 10
            m_x, m_y, m_w, m_h = 20, m_y_start, 20, 150
            pygame.draw.rect(surface, (50, 50, 50), (m_x, m_y, m_w, m_h))
            fill_h = int(min(1.0, peak_meter) * m_h)
            pygame.draw.rect(surface, (0, 200, 255), (m_x, m_y + m_h - fill_h, m_w, fill_h))

            floor_y = m_y + m_h - int(noise_floor * m_h)
            pygame.draw.line(surface, (255, 50, 50), (m_x - 5, floor_y), (m_x + m_w + 5, floor_y), 3)
            label = font.render("FLOOR", True, (255, 50, 50))
            surface.blit(label, (m_x + m_w + 10, floor_y - 10))


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
        # We use global_brightness to make notes "glow" more during drops
        alpha = max(0, min(255, int(self.life + (global_brightness * 100))))

        # 3. Sidechain Movement (The "Duck")
        # We SUBTRACT current_boost from the radius to pull notes toward the center
        duck_factor = current_boost * 20.0  # Adjust 20.0 for stronger/weaker pull
        visual_angle = self.angle + lag_comp
        r_pos = self.inner_r + (self.note_index * self.spacing) - duck_factor

        rad = math.radians(visual_angle - 90)
        x = CENTER[0] + r_pos * math.cos(rad)
        y = CENTER[1] + r_pos * math.sin(rad)

        # 4. Sidechain Scaling (The "Squash")
        base_size = int(2 + (self.energy * self.max_size))
        # Multiply by (1.0 - boost) so the node shrinks when the beat hits
        # This mimics the volume ducking of a sidechain compressor
        swell_size = int(base_size * (1.0 - current_boost * 0.4))
        swell_size = max(1, swell_size)  # Prevent size from being 0

        # 5. Rendering
        surf_dim = max(1, swell_size * 4)
        note_surf = pygame.Surface((surf_dim, surf_dim), pygame.SRCALPHA)

        # Draw the glow (Outer)
        pygame.draw.circle(note_surf, (*current_color, alpha // 8), (surf_dim // 2, surf_dim // 2), swell_size * 2)

        # Draw the core (Inner)
        pygame.draw.circle(note_surf, (*current_color, alpha), (surf_dim // 2, surf_dim // 2), int(swell_size // 1.5))

        surface.blit(note_surf, (x - surf_dim // 2, y - surf_dim // 2))


class InteractiveStaff:
    def __init__(self):
        # --- Configurable Parameters ---
        self.receiver = AudioReceiver()
        self.hud = HUD()

        # Register parameters
        self.noise_floor = self.hud.add("Noise Floor", 0.05, 0.0, 1.0, 0.01, (pygame.K_COMMA, pygame.K_PERIOD))
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
        self.peak_for_meter = 0.0
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
        # 1. Sync with the "Database"
        self.receiver.update()

        # 2. React to Events
        if self.receiver.beat_detected:
            self.update_tempo(self.receiver.bpm)
            if self.beat_pulse_enabled.value:
                self.beat_boost = 1.0

        if self.receiver.notes_updated:
            new_e = self.receiver.notes
            self.current_brightness = self.receiver.brightness
            self.peak_for_meter = max(new_e) if any(new_e) else 0.0

            # 3. Visualization Logic (Attack Detection)
            if self.peak_for_meter >= self.noise_floor.value:
                for i in range(12):
                    attack = new_e[i] - self.prev_energies[i]
                    if attack > self.attack_threshold.value and new_e[i] >= (
                        self.peak_for_meter * self.sensitivity_gate.value
                    ):
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

        # EDM Sidechain Logic:
        # We want the 'boost' to represent the "ducking" amount.
        if self.beat_boost > 0:
            # This decay rate controls how fast the "release" is.
            # 0.85 is a classic mid-tempo sidechain feel.
            self.beat_boost *= 0.85
        if self.beat_boost < 0.01:
            self.beat_boost = 0

    def draw(self):
        # Background gets slightly darker on the "duck"
        bg_val = max(0, 15 - int(self.beat_boost * 10))
        screen.fill((bg_val, bg_val, bg_val + 5))

        # Determine the ducking amount (e.g., rings shrink by up to 15 pixels)
        duck_offset = self.beat_boost * 15.0 if self.beat_pulse_enabled.value else 0.0

        for i in range(12):
            # The radius now "ducks" inward when the beat hits
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
        # Calculate thickness and color based on brightness
        line_width = int(2 + (self.current_brightness * 8))
        line_color = (int(200 + (self.current_brightness * 55)), int(200 + (self.current_brightness * 55)), 255)

        pygame.draw.line(screen, line_color, CENTER, end_pos, line_width)

        self.hud.draw(screen, hud_font, self.peak_for_meter, self.noise_floor.value)


# --- Run ---
viz = InteractiveStaff()
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            exit()
        if event.type == pygame.KEYDOWN:
            viz.handle_keys(event.key)
    viz.update()
    viz.draw()
    pygame.display.flip()
    clock.tick(60)
