import colorsys
import math

import pygame


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
        return self.life > 0

    def draw(self, surface, center, low_boost, lag_comp):
        # Apply the 'Duck' based on Smoothed Lows
        duck_factor = low_boost * 30.0
        visual_angle = self.angle + lag_comp
        r_pos = self.inner_r + (self.note_index * self.spacing) - duck_factor

        rad = math.radians(visual_angle - 90)
        x = center[0] + r_pos * math.cos(rad)
        y = center[1] + r_pos * math.sin(rad)

        alpha = max(0, min(255, int(self.life)))
        size = int(2 + (self.energy * self.max_size))

        # Draw Glow
        surf_dim = size * 4
        note_surf = pygame.Surface((surf_dim, surf_dim), pygame.SRCALPHA)
        pygame.draw.circle(note_surf, (*self.color, alpha // 8), (surf_dim // 2, surf_dim // 2), size * 2)
        pygame.draw.circle(note_surf, (*self.color, alpha), (surf_dim // 2, surf_dim // 2), size // 2)
        surface.blit(note_surf, (x - surf_dim // 2, y - surf_dim // 2))
