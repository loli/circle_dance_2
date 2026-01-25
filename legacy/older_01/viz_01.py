import pyaudio
import numpy as np
import pygame
import threading
from scipy.signal import find_peaks
from collections import deque
import colorsys

# --- Configuration ---
CHUNK = 8192
RATE = 44100
HPS_ORDER = 3
THRESHOLD = 0.02
WIDTH, HEIGHT = 1000, 700
FPS = 60

# Shared data
detected_notes_queue = deque(maxlen=15)


def get_note_color(midi_val):
    """Maps 12 semitones to the HSV color wheel."""
    hue = (midi_val % 12) / 12.0
    # Convert HSV (Hue, Saturation, Value) to RGB
    rgb = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
    return (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))


def get_note_info(freq):
    if freq < 20:
        return None
    midi = int(round(12 * np.log2(freq / 440.0) + 69))
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    name = f"{names[midi % 12]}{midi // 12 - 1}"
    return midi, name


def audio_thread():
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=RATE, input=True, frames_per_buffer=CHUNK)
    while True:
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)

            # HPS Analysis
            windowed = samples * np.hanning(len(samples))
            fft_data = np.abs(np.fft.rfft(windowed))
            hps_data = np.copy(fft_data)
            for i in range(2, HPS_ORDER + 1):
                downsampled = fft_data[::i]
                hps_data[: len(downsampled)] *= downsampled

            hps_data /= np.max(hps_data) if np.max(hps_data) > 0 else 1
            freqs = np.fft.rfftfreq(len(samples), 1.0 / RATE)
            peaks, _ = find_peaks(hps_data, height=THRESHOLD, distance=25)

            current_frame_notes = []
            for p_idx in peaks:
                f = freqs[p_idx]
                res = get_note_info(f)
                if res:
                    current_frame_notes.append(res)

            if current_frame_notes:
                detected_notes_queue.append(current_frame_notes)
        except:
            break


# --- Visualizer Setup ---
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Color-Coded Harmonic Visualizer")
clock = pygame.time.Clock()
font = pygame.font.SysFont("monospace", 15, bold=True)

# List of active particles: [x, y, midi, name, color]
particles = []

# Start Audio Thread
threading.Thread(target=audio_thread, daemon=True).start()

running = True
while running:
    # Semi-transparent background creates "motion blur" trails
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(40)
    overlay.fill((5, 5, 15))
    screen.blit(overlay, (0, 0))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # 1. Spawn new notes
    if len(detected_notes_queue) > 0:
        notes = detected_notes_queue.popleft()
        for midi, name in notes:
            # Map MIDI 21-108 to Screen Width
            x = int((midi - 21) / (108 - 21) * WIDTH)
            color = get_note_color(midi)
            particles.append([x, 0, midi, name, color])

    # 2. Update and Draw
    for p in particles[:]:
        x, y, midi, name, color = p

        # Draw glowing note head
        pygame.draw.circle(screen, color, (x, y), 8)
        # Draw label
        txt = font.render(name, True, (255, 255, 255))
        screen.blit(txt, (x + 10, y - 10))

        p[1] += 4  # Speed of fall
        if p[1] > HEIGHT:
            particles.remove(p)

    # 3. Reference Keyboard
    for i in range(21, 109):
        x = int((i - 21) / (108 - 21) * WIDTH)
        ref_color = get_note_color(i)
        # Draw a steady glow at the bottom for each key
        pygame.draw.rect(screen, ref_color, (x - 1, HEIGHT - 5, 3, 5))

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
