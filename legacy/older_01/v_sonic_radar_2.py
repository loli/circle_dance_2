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
INNER_RADIUS = 120
RING_SPACING = 25
SENSITIVITY_GATE = 0.92  # Slightly higher for the sharper Aubio transients

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Radial Sonic Radar - Auto-BPM Sync")
clock = pygame.time.Clock()
font = pygame.font.SysFont("monospace", 18, bold=True)

# Network Socket
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
        # Brighter colors for electronic music
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

        size = int(4 + (self.energy * 14))
        # Create a small glow effect
        note_surf = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
        pygame.draw.circle(note_surf, (*self.color, alpha // 2), (size * 2, size * 2), size * 2)
        pygame.draw.circle(note_surf, (*self.color, alpha), (size * 2, size * 2), size)
        surface.blit(note_surf, (x - size * 2, y - size * 2))


class RadialStaff:
    def __init__(self):
        self.scanning_angle = 0.0
        self.active_traces = []
        self.current_energies = [0.0] * 12

        # Tempo & Pulse Management
        self.bpm = 120
        self.rotation_speed = 2.0
        self.decay_rate = 1.0
        self.pulse_radius = 0
        self.update_tempo(120)

    def update_tempo(self, new_bpm):
        # Smoothing: don't let the BPM jump more than 10% at a time
        smoothed_bpm = (self.bpm * 0.8) + (new_bpm * 0.2)
        self.bpm = smoothed_bpm

        beats_per_rotation = 16  # 4 Bars
        seconds_per_rotation = (60.0 / self.bpm) * beats_per_rotation
        total_frames = seconds_per_rotation * 60.0
        self.rotation_speed = 360.0 / total_frames
        self.decay_rate = 255.0 / (360.0 / self.rotation_speed)

    def capture_audio(self):
        try:
            data, _ = sock.recvfrom(1024)
            decoded = json.loads(data.decode("utf-8"))

            if isinstance(decoded, dict):
                if "bpm" in decoded:
                    # Aubio often detects half-time or double-time.
                    # We normalize it to a 80-160 range for consistency.
                    raw_bpm = decoded["bpm"]
                    while raw_bpm < 80:
                        raw_bpm *= 2
                    while raw_bpm > 160:
                        raw_bpm /= 2

                    self.update_tempo(raw_bpm)
                    self.pulse_radius = 100  # Trigger the beat pulse
            else:
                self.current_energies = decoded
                max_e = max(self.current_energies) if self.current_energies else 0
                for i, energy in enumerate(self.current_energies):
                    if energy > 0.1 and energy >= (max_e * SENSITIVITY_GATE):
                        # Only add a trace if it's a "fresh" note for this angle
                        self.active_traces.append(NoteTrace(i, self.scanning_angle, energy, self.decay_rate))
        except (BlockingIOError, json.JSONDecodeError):
            pass

    def update(self):
        self.scanning_angle = (self.scanning_angle + self.rotation_speed) % 360
        for trace in self.active_traces:
            trace.update()
        self.active_traces = [t for t in self.active_traces if t.life > 0]

        # Fade the pulse
        if self.pulse_radius > 0:
            self.pulse_radius -= 4

    def draw(self):
        screen.fill((10, 10, 18))

        # 1. Draw Beat Pulse
        if self.pulse_radius > 0:
            p_color = (40, 40, 80)
            pygame.draw.circle(screen, p_color, CENTER, INNER_RADIUS + self.pulse_radius, 2)

        # 2. Draw Staff Rings
        for i in range(STAFF_RINGS):
            r = INNER_RADIUS + (i * RING_SPACING)
            # Rings brighten slightly based on note activity
            ring_alpha = 60 + int(self.current_energies[i] * 100)
            pygame.draw.circle(screen, (ring_alpha, ring_alpha, ring_alpha + 20), CENTER, r, 1)

            label = font.render(NOTE_NAMES[i], True, (100, 105, 120))
            screen.blit(label, (CENTER[0] - 15, CENTER[1] - r - 10))

        # 3. Draw Note Traces
        for trace in self.active_traces:
            trace.draw(screen)

        # 4. Draw Scanning Playhead
        rad = math.radians(self.scanning_angle - 90)
        end_r = INNER_RADIUS + (11 * RING_SPACING) + 30
        end_x = CENTER[0] + end_r * math.cos(rad)
        end_y = CENTER[1] + end_r * math.sin(rad)

        # Glow line
        pygame.draw.line(screen, (255, 255, 255), CENTER, (end_x, end_y), 2)
        pygame.draw.circle(screen, (255, 255, 255), (int(end_x), int(end_y)), 5)

        # 5. BPM Overlay
        txt = font.render(f"AUTO-BPM: {int(self.bpm)}", True, (180, 180, 200))
        screen.blit(txt, (20, 20))


# --- Main ---
visualizer = RadialStaff()
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            exit()

    visualizer.capture_audio()
    visualizer.update()
    visualizer.draw()
    pygame.display.flip()
    clock.tick(60)
