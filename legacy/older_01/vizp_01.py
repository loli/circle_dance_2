# visualizer_pygame.py
import pygame
import socket
import json
import numpy as np

# --- UDP Setup ---
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.setblocking(False)  # Don't freeze if no data

# --- GUI Setup ---
WIDTH, HEIGHT = 900, 500
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

current_energies = [0.0] * 12

while True:
    screen.fill((10, 10, 20))
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            exit()

    # 1. Receive data from Engine
    try:
        data, addr = sock.recvfrom(1024)
        current_energies = json.loads(data.decode("utf-8"))
    except BlockingIOError:
        pass  # No new data yet

    # 2. Draw Visualization
    for i, energy in enumerate(current_energies):
        bar_h = int(energy * 300)
        x = (WIDTH // 12) * i + 10
        pygame.draw.rect(screen, (0, 200, 255), (x, HEIGHT - bar_h - 100, 50, bar_h))

        txt = pygame.font.SysFont("Arial", 20).render(NOTE_NAMES[i], True, (255, 255, 255))
        screen.blit(txt, (x, HEIGHT - 80))

    pygame.display.flip()
    clock.tick(60)
