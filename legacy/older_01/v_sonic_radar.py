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
SENSITIVITY_GATE = 0.9  # High gate for clean electronic music detection

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Radial Sonic Radar - Press SPACE to Tap BPM")
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

        rgb = colorsys.hsv_to_rgb(note_index / 12.0, 0.7, 1.0)
        self.color = (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))

    def update(self):
        self.life -= self.decay_rate

    def draw(self, surface):
        alpha = max(0, min(255, int(self.life)))
        r = INNER_RADIUS + (self.note_index * RING_SPACING)
        rad = math.radians(self.angle - 90)  # Offset so 0 is at 12 o'clock

        x = CENTER[0] + r * math.cos(rad)
        y = CENTER[1] + r * math.sin(rad)

        size = int(4 + (self.energy * 12))
        note_surf = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
        pygame.draw.circle(note_surf, (*self.color, alpha), (size * 2, size * 2), size)
        surface.blit(note_surf, (x - size * 2, y - size * 2))


class RadialStaff:
    def __init__(self):
        self.scanning_angle = 0.0
        self.active_traces = []
        self.current_energies = [0.0] * 12

        # Tempo Management
        self.bpm = 120
        self.rotation_speed = 2.0
        self.decay_rate = 1.0
        self.tap_times = []
        self.update_tempo(120)

    def update_tempo(self, new_bpm):
        self.bpm = new_bpm
        # Calculation: We want 1 rotation every 4 bars (16 beats)
        # Frames per rotation = (60 sec / BPM) * 16 beats * 60 FPS
        # Degrees per frame = 360 / frames_per_rotation
        beats_per_rotation = 16
        seconds_per_rotation = (60.0 / self.bpm) * beats_per_rotation
        total_frames = seconds_per_rotation * 60.0
        self.rotation_speed = 360.0 / total_frames
        self.decay_rate = 255.0 / (360.0 / self.rotation_speed)

    def tap_bpm(self):
        now = time.time()
        self.tap_times.append(now)
        if len(self.tap_times) > 4:
            self.tap_times.pop(0)

        if len(self.tap_times) >= 2:
            intervals = [t2 - t1 for t1, t2 in zip(self.tap_times, self.tap_times[1:])]
            avg_interval = sum(intervals) / len(intervals)
            self.update_tempo(60.0 / avg_interval)

    def capture_audio(self):
        try:
            data, _ = sock.recvfrom(1024)
            self.current_energies = json.loads(data.decode("utf-8"))
            max_e = max(self.current_energies) if self.current_energies else 0

            for i, energy in enumerate(self.current_energies):
                # Apply the 0.9 Gate logic
                if energy > 0.1 and energy >= (max_e * SENSITIVITY_GATE):
                    self.active_traces.append(NoteTrace(i, self.scanning_angle, energy, self.decay_rate))
        except BlockingIOError:
            pass

    def update(self):
        self.scanning_angle = (self.scanning_angle + self.rotation_speed) % 360
        for trace in self.active_traces:
            trace.update()
        self.active_traces = [t for t in self.active_traces if t.life > 0]

    def draw(self):
        screen.fill((15, 15, 25))

        # Draw concentric staff rings
        for i in range(STAFF_RINGS):
            r = INNER_RADIUS + (i * RING_SPACING)
            pygame.draw.circle(screen, (40, 45, 60), CENTER, r, 1)
            label = font.render(NOTE_NAMES[i], True, (80, 85, 100))
            screen.blit(label, (CENTER[0] - 20, CENTER[1] - r - 10))

        # Draw the notes
        for trace in self.active_traces:
            trace.draw(screen)

        # Draw the Scanning Playhead
        rad = math.radians(self.scanning_angle - 90)
        end_r = INNER_RADIUS + (11 * RING_SPACING) + 30
        end_x = CENTER[0] + end_r * math.cos(rad)
        end_y = CENTER[1] + end_r * math.sin(rad)
        pygame.draw.line(screen, (200, 200, 255), CENTER, (end_x, end_y), 3)
        pygame.draw.circle(screen, (255, 255, 255), (int(end_x), int(end_y)), 6)

        # Info Text
        bpm_text = font.render(f"BPM: {int(self.bpm)} (Space to Tap)", True, (200, 200, 200))
        screen.blit(bpm_text, (20, 20))


# --- Main ---
visualizer = RadialStaff()
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                visualizer.tap_bpm()

    visualizer.capture_audio()
    visualizer.update()
    visualizer.draw()
    pygame.display.flip()
    clock.tick(60)
