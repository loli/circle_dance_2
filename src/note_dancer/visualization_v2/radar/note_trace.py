import colorsys
import math

import pygame


class NoteTrace:
    # Class-level caches shared by all instances
    _glowing_orb_cache = {}

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

    def _get_current_color(self, schema_idx, neon_base_color):
        """Calculates the RGB color based on the selected schema."""

        # SCHEMA 0: Rainbow (Classic)
        if schema_idx == 0:
            rgb = colorsys.hsv_to_rgb(self.note_index / 12.0, 0.8, 1.0)
            return (int(rgb[0] * 255), int(rgb[1] * 255), int(rgb[2] * 255))

        # SCHEMA 1: Thermal (Red -> Orange -> White)
        elif schema_idx == 1:
            t = self.note_index / 11.0  # Normalize 0.0 to 1.0
            if t < 0.5:  # Red to Orange
                lerp = t * 2.0
                return (255, int(160 * lerp), 0)
            else:  # Orange to White
                lerp = (t - 0.5) * 2.0
                return (255, 160 + int(95 * lerp), int(255 * lerp))

        # SCHEMA 2: Monochrome Neon
        elif schema_idx == 2:
            # mix represents the 'heat' of the note (0.0 to 1.0)
            mix = self.note_index / 12.0

            # Instead of white, we mix toward a 'glow' color (like the Glacier Blue)
            glow_color = (220, 240, 255)

            # We use a non-linear mix (power curve) so the 'pure' color
            # stays dominant longer, and only the highest notes 'ignite'.
            heat = mix**1.5

            r = int(neon_base_color[0] + (glow_color[0] - neon_base_color[0]) * heat)
            g = int(neon_base_color[1] + (glow_color[1] - neon_base_color[1]) * heat)
            b = int(neon_base_color[2] + (glow_color[2] - neon_base_color[2]) * heat)

            return (r, g, b)

        return (255, 255, 255)

    def draw(self, surface, center, low_boost, lag_comp, style_idx, schema_idx, neon_color):
        duck_factor = low_boost * 30.0
        visual_angle = self.angle + lag_comp
        r_pos = self.inner_r + (self.note_index * self.spacing) - duck_factor

        rad = math.radians(visual_angle - 90)
        x = center[0] + r_pos * math.cos(rad)
        y = center[1] + r_pos * math.sin(rad)

        alpha = max(0, min(255, int(self.life)))
        # size = int(2 + (self.energy * self.max_size))
        size = int(
            2 + (self.energy * self.energy * self.max_size)
        )  # energy squared to ensure that small sizes are clearly distinct from large one
        # size = int(
        #    2 + (pow(self.energy, 2) * self.max_size)
        # )  # logarithmic scaleing from (frame-wide normalized) energy to size

        self.color = self._get_current_color(schema_idx, neon_color)

        match int(style_idx):
            case 0:
                self._draw_glowing_orb(surface, x, y, size, alpha)
            case 1:
                self._draw_trailing_arc(surface, size, center, rad, r_pos, alpha)
            case 2:
                self._draw_segmented_arc(surface, x, y, self.max_size, visual_angle, alpha)
            case 3:
                self._draw_sober_node(surface, x, y, size, alpha, low_boost)
            case _:
                self._draw_glowing_orb(surface, x, y, size, alpha)

    def _draw_glowing_orb(self, surface, x, y, size, alpha):
        # 2. BRUTAL QUANTIZATION
        # Floating point numbers are the enemy of caches.
        # We round to the nearest 'step' to ensure we hit existing images.

        if size > 100:
            q_size = (int(size) // 10) * 10  # Very aggressive for big notes
        else:
            q_size = (int(size) // 4) * 4

        # q_size = max(1, int(size))  # Integer pixel size
        q_alpha = max(0, (int(alpha) // 8) * 8)  # Groups of 8 (only ~32 possible alpha states)
        # q_alpha = max(0, (int(alpha) // 20) * 20)  # lower this number for smoother note deissapearing (with alpha)

        # Quantize color to 16-step increments (reduces 16 million colors to a few hundred)
        q_color = ((self.color[0] // 16) * 16, (self.color[1] // 16) * 16, (self.color[2] // 16) * 16)
        # q_color = tuple((c // 50) * 50 for c in self.color)  # lower this for more different colors

        # 3. CACHE LOOKUP
        cache_key = (q_color, q_size, q_alpha)

        if cache_key not in self._glowing_orb_cache:
            # 4. RENDER ONCE (The expensive part)
            surf_dim = q_size * 4
            note_surf = pygame.Surface((surf_dim, surf_dim), pygame.SRCALPHA)

            # Draw the circles using the quantized color and alpha
            pygame.draw.circle(note_surf, (*q_color, q_alpha // 8), (surf_dim // 2, surf_dim // 2), q_size * 2)
            pygame.draw.circle(note_surf, (*q_color, q_alpha), (surf_dim // 2, surf_dim // 2), q_size // 2)

            # 5. OPTIMIZE FOR GPU/CPU BLIT
            # .convert_alpha() is what actually fixes the 4K/High-Res lag
            self._glowing_orb_cache[cache_key] = note_surf.convert_alpha()

        # 6. BLIT (The fast part)
        cached_img = self._glowing_orb_cache[cache_key]
        surface.blit(cached_img, (x - cached_img.get_width() // 2, y - cached_img.get_height() // 2))

    def _draw_radial_beam(self, surface, x, y, size, center, rad, r_pos, alpha):
        # Draw a line from the note position pointing inward
        inner_x = center[0] + (r_pos - size * 2) * math.cos(rad)
        inner_y = center[1] + (r_pos - size * 2) * math.sin(rad)
        pygame.draw.line(surface, (*self.color, alpha), (x, y), (inner_x, inner_y), 3)

    def _draw_segmented_arc(self, surface, x, y, max_size, visual_angle, alpha):
        # Draws a small rectangle rotated to the tangent of the circle
        rect_w, rect_h = max_size * 2, max_size // 2
        rect_surf = pygame.Surface((rect_w, rect_h), pygame.SRCALPHA)
        rect_surf.fill((*self.color, alpha))
        # Rotate surface to match the radar angle
        rotated_surf = pygame.transform.rotate(rect_surf, -visual_angle)
        surface.blit(rotated_surf, rotated_surf.get_rect(center=(x, y)))

    def _draw_trailing_arc(self, surface, size, center, rad, r_pos, alpha):
        # Draw 3-4 smaller dots trailing behind the current angle
        for i in range(1, 4):
            trail_rad = rad - (i * 0.05)  # Shift angle back
            tx = center[0] + r_pos * math.cos(trail_rad)
            ty = center[1] + r_pos * math.sin(trail_rad)
            pygame.draw.circle(surface, (*self.color, alpha // (i * 2)), (int(tx), int(ty)), size // (i + 1))

    def _draw_sober_node(self, surface, x, y, size, alpha, low_boost):
        """
        Style 1 (Hot/Sober Orb): High-fidelity node with sidechain 'Squash'
        and color-shifting brightness logic.
        """
        # 1. Sidechain Scaling (The "Squash")
        # Higher bass (low_boost) makes the node smaller/compressed
        swell_size = int(size * (1.0 - low_boost * 0.4))
        swell_size = max(1, swell_size)

        # 2. Color Shift logic
        # We simulate 'global_brightness' using the current audio energy
        # This makes nodes 'whiten' slightly during intense moments
        white_mix = low_boost * 60  # Subtle white injection
        current_color = (
            min(255, int(self.color[0] + white_mix)),
            min(255, int(self.color[1] + white_mix)),
            min(255, int(self.color[2] + white_mix)),
        )

        # 3. Rendering with specific sober layers
        surf_dim = max(1, swell_size * 4)
        note_surf = pygame.Surface((surf_dim, surf_dim), pygame.SRCALPHA)

        # Large, very thin outer glow
        pygame.draw.circle(note_surf, (*current_color, alpha // 8), (surf_dim // 2, surf_dim // 2), swell_size * 2)

        # Solid core with precise scaling
        pygame.draw.circle(
            note_surf, (*current_color, alpha), (surf_dim // 2, surf_dim // 2), max(1, int(swell_size // 1.5))
        )

        surface.blit(note_surf, (x - surf_dim // 2, y - surf_dim // 2))
