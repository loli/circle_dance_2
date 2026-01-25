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

# Visual Constants
STAFF_RINGS = 12
INNER_RADIUS = 130
RING_SPACING = 25
SENSITIVITY_GATE = 0.85  # Slightly lower since we are only sampling on the beat

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Rhythmic Sonic Radar (Beat-Synced)")
clock = pygame.time.Clock()
font = pygame.font.SysFont("monospace", 18, bold=True)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.setblocking(False)

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


class NoteTrace:
    def __init__(self, note_index, angle, energy, decay_rate):
        self.note_index = note_index
        self.angle = angle
        self.energy = energy
        self.life = 255.0
        self.decay_rate = decay_rate
        rgb = colorsys.hsv_to_rgb(note_index / 12.0, 0.8, 1.0)
        self.color = (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))

    def update(self):
        self.life -= self.decay_rate

    def draw(self, surface):
        alpha = max(0, min(255, int(self.life)))
        r = INNER_RADIUS + (self.note_index * RING_SPACING)
        rad = math.radians(self.angle - 90)
        x = CENTER[0] + r * math.cos(rad)
        y = CENTER[1] + r * math.sin(rad)

        # Bigger, more impactful nodes for beat-sync
        size = int(6 + (self.energy * 15))
        note_surf = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
        # Glow
        pygame.draw.circle(note_surf, (*self.color, alpha // 3), (size * 2, size * 2), size * 2)
        # Core
        pygame.draw.circle(note_surf, (*self.color, alpha), (size * 2, size * 2), size)
        surface.blit(note_surf, (x - size * 2, y - size * 2))


class RhythmicStaff:
    def __init__(self):
        self.scanning_angle = 0.0
        self.active_traces = []
        self.current_energies = [0.0] * 12
        self.bpm = 120
        self.rotation_speed = 2.0
        self.decay_rate = 1.0
        self.pulse_radius = 0
        self.update_tempo(120)

    def update_tempo(self, new_bpm):
        # Normalize and smooth BPM
        raw_bpm = new_bpm
        while raw_bpm < 80:
            raw_bpm *= 2
        while raw_bpm > 160:
            raw_bpm /= 2

        self.bpm = (self.bpm * 0.9) + (raw_bpm * 0.1)

        beats_per_rotation = 16
        seconds_per_rotation = (60.0 / self.bpm) * beats_per_rotation
        total_frames = seconds_per_rotation * 60.0
        self.rotation_speed = 360.0 / total_frames
        self.decay_rate = 255.0 / (360.0 / self.rotation_speed)

    def capture_audio(self):
        try:
            while True:  # Process all pending packets in the buffer
                data, _ = sock.recvfrom(1024)
                decoded = json.loads(data.decode("utf-8"))

                if isinstance(decoded, dict):
                    # BEAT DETECTED!
                    if "bpm" in decoded:
                        self.update_tempo(decoded["bpm"])
                        self.pulse_radius = 120

                        # Trigger Note Stamps ONLY now
                        max_e = max(self.current_energies) if self.current_energies else 0
                        for i, energy in enumerate(self.current_energies):
                            if energy > 0.15 and energy >= (max_e * SENSITIVITY_GATE):
                                self.active_traces.append(NoteTrace(i, self.scanning_angle, energy, self.decay_rate))
                else:
                    # Just update the background "monitor" of what's playing
                    self.current_energies = decoded
        except (BlockingIOError, json.JSONDecodeError):
            pass

    def update(self):
        self.scanning_angle = (self.scanning_angle + self.rotation_speed) % 360
        for trace in self.active_traces:
            trace.update()
        self.active_traces = [t for t in self.active_traces if t.life > 0]
        if self.pulse_radius > 0:
            self.pulse_radius -= 5

    def draw(self):
        screen.fill((12, 12, 20))

        # Background Beat Ripple
        if self.pulse_radius > 0:
            p_alpha = max(0, min(100, self.pulse_radius))
            pygame.draw.circle(screen, (30, 40, 70), CENTER, INNER_RADIUS + (120 - self.pulse_radius) * 2, 2)

        # Rings
        for i in range(STAFF_RINGS):
            r = INNER_RADIUS + (i * RING_SPACING)
            # Subtle highlight on rings that have active audio
            color_val = 40 + int(self.current_energies[i] * 40)
            pygame.draw.circle(screen, (color_val, color_val, color_val + 10), CENTER, r, 1)

            label = font.render(NOTE_NAMES[i], True, (70, 75, 90))
            screen.blit(label, (CENTER[0] - 15, CENTER[1] - r - 10))

        for trace in self.active_traces:
            trace.draw(screen)

        # Playhead
        rad = math.radians(self.scanning_angle - 90)
        end_r = INNER_RADIUS + (11 * RING_SPACING) + 40
        end_pos = (CENTER[0] + end_r * math.cos(rad), CENTER[1] + end_r * math.sin(rad))
        pygame.draw.line(screen, (220, 220, 255), CENTER, end_pos, 2)
        pygame.draw.circle(screen, (255, 255, 255), (int(end_pos[0]), int(end_pos[1])), 6)

        # HUD
        txt = font.render(f"BEAT-SYNC BPM: {int(self.bpm)}", True, (150, 150, 170))
        screen.blit(txt, (25, 25))


# --- Main ---
visualizer = RhythmicStaff()
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            exit()
    visualizer.capture_audio()
    visualizer.update()
    visualizer.draw()
    pygame.display.flip()
    clock.tick(60)
