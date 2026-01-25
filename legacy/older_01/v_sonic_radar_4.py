import pygame
import socket
import json
import math
import colorsys
import time

# =============================================================================
# CONSTANTS & CONFIGURATION
# =============================================================================
WIDTH, HEIGHT = 900, 900
CENTER = (WIDTH // 2, HEIGHT // 2)

# UDP Network Settings: Must match the output of the Aubio Engine
UDP_IP = "127.0.0.1"
UDP_PORT = 5005

# RADIAL STAFF CONSTANTS
STAFF_RINGS = 12  # One ring for each semitone in the chromatic scale (C through B)
INNER_RADIUS = 160  # The "Hollow Center" - larger values prevent low-frequency overlap
RING_SPACING = 25  # Distance between each note ring
SENSITIVITY_GATE = 0.8  # Filters out harmonic "ghosts"; note must be 80% of the loudest note

# SIGNAL PROCESSING CONSTANTS
# ATTACK_THRESHOLD: The minimum "jump" in energy required to stamp a note.
# This is the "Change" filter that prevents blurry donuts.
ATTACK_THRESHOLD = 0.08

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Live Attack Radar - Fully Documented")
clock = pygame.time.Clock()
font = pygame.font.SysFont("monospace", 18, bold=True)

# Socket initialization for real-time data reception
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.setblocking(False)

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


class NoteTrace:
    """
    Represents a single 'memory' of a sound event on the radar.
    Manages its own lifecycle, fading, and rendering.
    """

    def __init__(self, note_index, angle, energy, decay_rate):
        self.note_index = note_index  # Which ring (0-11)
        self.angle = angle  # Where in time (0-359 degrees)
        self.energy = energy  # Intensity of the attack
        self.life = 255.0  # Opacity (0.0 to 255.0)
        self.decay_rate = decay_rate  # Calculated to hit 0 after one full rotation

        # COLOR LOGIC: HSV to RGB conversion
        # Higher notes (A, A#, B) get higher saturation for visual weight.
        sat = 0.6 if note_index < 4 else 0.9
        rgb = colorsys.hsv_to_rgb(note_index / 12.0, sat, 1.0)
        self.color = (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))

    def update(self):
        """Reduces life based on the rotation speed of the playhead."""
        self.life -= self.decay_rate

    def draw(self, surface):
        """Converts Polar data to Screen coordinates and renders the node."""
        alpha = max(0, min(255, int(self.life)))

        # Calculate radius and angle offset (-90 starts 'C' at 12 o'clock)
        r = INNER_RADIUS + (self.note_index * RING_SPACING)
        rad = math.radians(self.angle - 90)

        # POLAR TO CARTESIAN: x = cos(a)*r, y = sin(a)*r
        x = CENTER[0] + r * math.cos(rad)
        y = CENTER[1] + r * math.sin(rad)

        # SIZE SCALING: Exponential scaling makes loud hits significantly
        # larger than background noise, creating better visual hierarchy.
        size = int(4 + (self.energy**2) * 20)

        # Render a 'Glow' layer (larger/fainter) and a 'Core' layer (smaller/solid)
        note_surf = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
        pygame.draw.circle(note_surf, (*self.color, alpha // 4), (size * 2, size * 2), size * 2)
        pygame.draw.circle(note_surf, (*self.color, alpha), (size * 2, size * 2), size)
        surface.blit(note_surf, (x - size * 2, y - size * 2))


class LiveAttackStaff:
    """
    The main engine for the visualization. Handles UDP networking,
    tempo tracking, and the 'Attack' signal processing.
    """

    def __init__(self):
        self.scanning_angle = 0.0
        self.active_traces = []
        self.current_energies = [0.0] * 12
        self.prev_energies = [0.0] * 12  # Needed to calculate the Delta (Attack)

        self.bpm = 120
        self.rotation_speed = 2.0
        self.decay_rate = 1.0
        self.pulse_radius = 0
        self.update_tempo(120)

    def update_tempo(self, new_bpm):
        """
        Calculates how fast the arm should spin based on music BPM.
        Includes 'Caging' logic to keep rotation within a sane human range.
        """
        raw_bpm = new_bpm
        # BPM CAGING: Forces the BPM into an 80-160 range to keep
        # the rotation speed visually consistent even with half-time beats.
        while raw_bpm < 80:
            raw_bpm *= 2
        while raw_bpm > 160:
            raw_bpm /= 2

        # SMOOTHING: Blends 5% of new BPM to prevent the arm from 'jerking'
        self.bpm = (self.bpm * 0.95) + (raw_bpm * 0.05)

        # MATH: Calculate degrees per frame to complete a 4-bar rotation
        beats_per_rotation = 16
        seconds_per_rotation = (60.0 / self.bpm) * beats_per_rotation
        total_frames = seconds_per_rotation * 60.0  # Assuming 60FPS
        self.rotation_speed = 360.0 / total_frames

        # DECAY SYNC: Ensure notes fade out exactly as the arm returns to them
        self.decay_rate = 255.0 / (360.0 / self.rotation_speed)

    def capture_audio(self):
        """
        Listens for UDP packets. Differentiates between:
        - Dictionary packets: Automated BPM/Beat updates from Aubio.
        - List packets: Continuous Chroma/Energy data for the notes.
        """
        try:
            while True:  # Clear the entire buffer to minimize latency
                data, _ = sock.recvfrom(1024)
                decoded = json.loads(data.decode("utf-8"))

                if isinstance(decoded, dict):
                    # BPM Packet: Sync the rotation and trigger a background pulse
                    if "bpm" in decoded:
                        self.update_tempo(decoded["bpm"])
                        self.pulse_radius = 120
                else:
                    # Note Packet: Process for Onsets/Attacks
                    new_energies = decoded
                    max_e = max(new_energies) if any(new_energies) else 1.0

                    for i in range(12):
                        # THE ATTACK FILTER: Calculates the increase in volume
                        attack = max(0, new_energies[i] - self.prev_energies[i])

                        # LOGIC: Stamp a note ONLY if there is a sharp volume jump (attack)
                        # AND the note is one of the dominant notes in the current frame.
                        if attack > ATTACK_THRESHOLD and new_energies[i] >= (max_e * SENSITIVITY_GATE):
                            self.active_traces.append(NoteTrace(i, self.scanning_angle, attack, self.decay_rate))

                    self.prev_energies = new_energies
                    self.current_energies = new_energies
        except (BlockingIOError, json.JSONDecodeError):
            pass

    def update(self):
        """Updates physics and timing for all components."""
        self.scanning_angle = (self.scanning_angle + self.rotation_speed) % 360
        for trace in self.active_traces:
            trace.update()

        # Garbage collection: Remove notes that are fully faded
        self.active_traces = [t for t in self.active_traces if t.life > 0]

        # Beat pulse animation decrement
        if self.pulse_radius > 0:
            self.pulse_radius -= 5

    def draw(self):
        """Renders the UI, Rings, and Active Note Traces."""
        screen.fill((10, 10, 14))  # Deep midnight background

        # RHYTHMIC PULSE: A blue ripple that confirms the beat detection
        if self.pulse_radius > 0:
            pygame.draw.circle(screen, (30, 35, 60), CENTER, INNER_RADIUS + (120 - self.pulse_radius), 2)

        # STAFF RINGS: Reactive concentric circles
        for i in range(STAFF_RINGS):
            r = INNER_RADIUS + (i * RING_SPACING)
            # Subtle glow on the ring itself based on raw audio energy
            bright = 30 + int(self.current_energies[i] * 30)
            pygame.draw.circle(screen, (bright, bright, bright + 10), CENTER, r, 1)

            # Rendering note labels (C, C#, etc.)
            label = font.render(NOTE_NAMES[i], True, (60, 65, 80))
            screen.blit(label, (CENTER[0] - 15, CENTER[1] - r - 10))

        # Render all active note 'stamps'
        for trace in self.active_traces:
            trace.draw(screen)

        # PLAYHEAD: The white 'clock-hand' that represents current time
        rad = math.radians(self.scanning_angle - 90)
        end_r = INNER_RADIUS + (11 * RING_SPACING) + 40
        end_pos = (CENTER[0] + end_r * math.cos(rad), CENTER[1] + end_r * math.sin(rad))
        pygame.draw.line(screen, (255, 255, 255), CENTER, end_pos, 2)
        pygame.draw.circle(screen, (255, 255, 255), (int(end_pos[0]), int(end_pos[1])), 5)


# =============================================================================
# MAIN LOOP
# =============================================================================
visualizer = LiveAttackStaff()
while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            exit()

    visualizer.capture_audio()
    visualizer.update()
    visualizer.draw()

    pygame.display.flip()
    clock.tick(60)  # Locked at 60 FPS for smooth rotation math
