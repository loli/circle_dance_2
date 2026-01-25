import pygame
import socket
import json

# --- Setup ---
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.setblocking(False)

WIDTH, HEIGHT = 900, 500
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 22, bold=True)

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# --- Tuning Variables ---
SENSITIVITY_GATE = 0.85  # Higher = only show the most dominant notes
SMOOTHING = 0.2  # Lower = smoother/slower, Higher = twitchier
current_energies = [0.0] * 12
smoothed_energies = [0.0] * 12
current_bpm = 0.0
bg_flash = 0

while True:
    # 1. Background with beat-sync fade
    bg_val = min(20 + bg_flash, 60)
    screen.fill((10, 10, bg_val))
    if bg_flash > 0:
        bg_flash -= 4

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            exit()

    # 2. Receive and Process Data
    try:
        data, addr = sock.recvfrom(1024)
        decoded = json.loads(data.decode("utf-8"))

        if isinstance(decoded, dict):
            if "bpm" in decoded:
                current_bpm = decoded["bpm"]
                bg_flash = 100
        elif isinstance(decoded, list):
            current_energies = decoded

            # --- Taming the "Always Full" Bars ---
            max_e = max(current_energies) if any(current_energies) else 1.0
            for i in range(12):
                val = current_energies[i]

                # 1. Apply Gate: If it's not the main note, push it down
                if val < (max_e * SENSITIVITY_GATE):
                    val = 0

                # 2. Normalize: Scale relative to the peak of the frame
                val = val / (max_e + 1e-6)

                # 3. Smooth: Interpolate between old and new value
                smoothed_energies[i] = (smoothed_energies[i] * (1 - SMOOTHING)) + (val * SMOOTHING)

    except (BlockingIOError, json.JSONDecodeError):
        pass

    # 3. Draw Bars
    for i, energy in enumerate(smoothed_energies):
        # We multiply by 350 for height, but the Smoothing ensures it doesn't jump
        bar_h = int(energy * 350)
        x = (WIDTH // 12) * i + 15

        # Color gradient based on note index
        color = (0, 180 + (energy * 75), 255) if energy < 0.9 else (255, 200, 0)

        # Draw Bar
        pygame.draw.rect(screen, color, (x, HEIGHT - bar_h - 100, 45, bar_h))

        # Draw Label
        txt = font.render(NOTE_NAMES[i], True, (255, 255, 255) if energy > 0.5 else (100, 100, 150))
        screen.blit(txt, (x + 10, HEIGHT - 80))

    # 4. Info UI
    bpm_txt = font.render(f"BPM: {int(current_bpm)}", True, (200, 200, 200))
    screen.blit(bpm_txt, (20, 20))

    pygame.display.flip()
    clock.tick(60)
