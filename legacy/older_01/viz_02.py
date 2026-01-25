import pyaudio
import numpy as np
import pygame
import threading
from collections import deque
import librosa

# --- Optimized Config ---
CHUNK = 4096  # Reduced for lower latency
RATE = 44100
WIDTH, HEIGHT = 900, 500
FPS = 60

# Shared energy levels for the 12 notes
note_energies = np.zeros(12)


def audio_thread():
    global note_energies
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32, channels=1, rate=RATE, input=True, frames_per_buffer=CHUNK)

    while True:
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            samples = np.frombuffer(data, dtype=np.float32)

            # Simple Chroma calculation without full STFT for speed
            chroma = librosa.feature.chroma_stft(y=samples, sr=RATE, n_fft=CHUNK, hop_length=CHUNK + 1)
            raw_energies = np.mean(chroma, axis=1)

            # Smooth the transition (Inter-frame interpolation)
            note_energies = note_energies * 0.7 + raw_energies * 0.3
        except:
            break


# --- GUI ---
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

threading.Thread(target=audio_thread, daemon=True).start()

while True:
    screen.fill((20, 20, 30))
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()

    # Determine a dynamic threshold based on the loudest current note
    max_now = np.max(note_energies) if np.max(note_energies) > 0 else 1

    for i in range(12):
        energy = note_energies[i]

        # Calculate visual height
        bar_height = int(energy * 300)
        x = (WIDTH // 12) * i + 10
        w = (WIDTH // 12) - 20

        # Color: Bright if it's the "Main" note, dim otherwise
        is_dominant = energy > (max_now * 0.9) and energy > 0.5
        color = (0, 255, 150) if is_dominant else (50, 70, 90)

        # Draw the bar
        pygame.draw.rect(screen, color, (x, HEIGHT - bar_height - 100, w, bar_height))

        # Draw the label
        txt_color = (255, 255, 255) if is_dominant else (100, 100, 100)
        txt = pygame.font.SysFont("monospace", 20, bold=is_dominant).render(NOTE_NAMES[i], True, txt_color)
        screen.blit(txt, (x + (w // 4), HEIGHT - 80))

    pygame.display.flip()
    clock.tick(FPS)
