# visualizer_compass.py
import pygame
import socket
import json
import numpy as np
import math
import colorsys

# --- UDP Setup ---
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.setblocking(False)

# --- GUI Setup ---
WIDTH, HEIGHT = 800, 800
CENTER = (WIDTH // 2, HEIGHT // 2)
MAX_RADIUS = 300
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
font = pygame.font.SysFont("monospace", 22, bold=True)

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
current_energies = [0.0] * 12


def get_color(i):
    rgb = colorsys.hsv_to_rgb(i / 12.0, 1.0, 1.0)
    return (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))


while True:
    # Trailing effect for smooth motion
    overlay = pygame.Surface((WIDTH, HEIGHT))
    overlay.set_alpha(60)
    overlay.fill((10, 10, 25))
    screen.blit(overlay, (0, 0))

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            exit()

    # 1. Receive Data
    try:
        data, addr = sock.recvfrom(1024)
        current_energies = json.loads(data.decode("utf-8"))
    except BlockingIOError:
        pass

    # 2. Draw Compass
    points = []
    for i, energy in enumerate(current_energies):
        # Calculate angle (start from top/12 o'clock)
        angle = (i * (360 / 12)) - 90
        rad = math.radians(angle)

        # Calculate radius based on energy (with a minimum floor)
        dist = 50 + (energy * MAX_RADIUS)

        x = CENTER[0] + dist * math.cos(rad)
        y = CENTER[1] + dist * math.sin(rad)
        points.append((x, y))

        # Draw individual note glow
        color = get_color(i)
        strength = int(energy * 255)
        if energy > 0.3:
            pygame.draw.circle(screen, color, (int(x), int(y)), int(10 + energy * 20))

        # Draw Note Label
        label = font.render(NOTE_NAMES[i], True, (255, 255, 255) if energy > 0.5 else (100, 100, 120))
        # Position labels slightly further out than the points
        lx = CENTER[0] + (MAX_RADIUS + 60) * math.cos(rad)
        ly = CENTER[1] + (MAX_RADIUS + 60) * math.sin(rad)
        screen.blit(label, (lx - 10, ly - 10))

    # 3. Draw Connecting Web (The "Shape" of the Sound)
    if len(points) > 1:
        # Drawing lines between adjacent notes to create a polygon
        pygame.draw.polygon(screen, (0, 255, 200), points, 2)
        # Optional: draw lines to center for a "star" effect
        for p in points:
            pygame.draw.line(screen, (40, 40, 80), CENTER, p, 1)

    pygame.display.flip()
    clock.tick(60)
