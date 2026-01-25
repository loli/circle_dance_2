import pygame
import time
import collections


class Tunable:
    def __init__(self, name, val, min_v, max_v, step, keys, fmt="{:.2f}", transformer=None):
        self.name = name
        self.value = val
        self.min_v = min_v
        self.max_v = max_v
        self.step = step
        self.keys = keys  # (dec, inc) or single key for toggle
        self.fmt = fmt
        self.transformer = transformer

    def handle(self, key):
        # Toggle
        if isinstance(self.keys, int):
            if key == self.keys:
                self.value = not self.value
                return True
            return False

        # Range
        dec, inc = self.keys
        if not isinstance(dec, (list, tuple)):
            dec = [dec]
        if not isinstance(inc, (list, tuple)):
            inc = [inc]

        if key in dec:
            self._update(-1)
            return True
        if key in inc:
            self._update(1)
            return True
        return False

    def _update(self, direction):
        if self.transformer:
            self.value = self.transformer(self.value, self.step, direction)
        else:
            self.value += self.step * direction

        # Clamp
        if isinstance(self.value, (int, float)):
            self.value = max(self.min_v, min(self.max_v, self.value))

    def __str__(self):
        if isinstance(self.value, bool):
            v_str = "ON" if self.value else "OFF"
            k_str = f"[{pygame.key.name(self.keys).upper()}]"
        else:
            v_str = self.fmt.format(self.value)
            k1 = self.keys[0] if not isinstance(self.keys[0], (list, tuple)) else self.keys[0][0]
            k2 = self.keys[1] if not isinstance(self.keys[1], (list, tuple)) else self.keys[1][0]
            k_str = f"[{pygame.key.name(k1).upper()}/{pygame.key.name(k2).upper()}]"

        return f"{k_str:<12} {self.name}: {v_str}"


class HUD:
    def __init__(self):
        self.params = []
        self.show_help = False
        self.help_timer = 0
        self.msg = ""
        self.msg_timer = 0
        # In HUD.__init__
        # We start at -40.0 dB (a common sweet spot for EDM)
        # Range is -60.0 to 0.0, step by 1.0 dB
        self.noise_floor = self.add("Noise Floor", -40.0, -60.0, 0.0, 1.0, (pygame.K_COMMA, pygame.K_PERIOD), fmt="{:.1f} dB")
        self.rms_history = collections.deque(maxlen=200)

    def add(self, *args, **kwargs):
        t = Tunable(*args, **kwargs)
        self.params.append(t)
        return t

    def handle_input(self, key):
        if key == pygame.K_h:
            self.show_help = not self.show_help
            self.help_timer = time.time() + 30.0 if self.show_help else 0
            return

        for p in self.params:
            if p.handle(key):
                self.msg = str(p)
                self.msg_timer = time.time() + 2.0
                return

    def draw(self, surface, font, current_rms=0.0):
        self.rms_history.append(current_rms)
        noise_floor = self.noise_floor.value

        # Draw Msg
        if time.time() < self.msg_timer and not self.show_help:
            img = font.render(self.msg, True, (255, 255, 255))
            surface.blit(img, (20, 20))

        # Draw Help
        if self.show_help:
            if time.time() > self.help_timer:
                self.show_help = False
                return

            # --- Menu Box (Top Left) ---
            bg = pygame.Surface((450, 40 + len(self.params) * 25), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 180))
            surface.blit(bg, (10, 10))

            for i, p in enumerate(self.params):
                img = font.render(str(p), True, (0, 255, 180))
                surface.blit(img, (20, 20 + i * 25))

            # --- Histogram Box (Bottom Right) ---
            sw, sh = surface.get_width(), surface.get_height()
            box_w, box_h = 150, 200
            meter_bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
            meter_bg.fill((0, 0, 0, 180))

            m_w, m_h = 20, 150
            m_x, m_y = 20, (box_h - m_h) // 2

            #  Draw Histogram Bars
            bins = [0] * 50
            for v in self.rms_history:
                # Map dB (-60 to 0) to 0.0-1.0 for the 50 bins
                # Formula: (value - min) / (max - min)
                normalized_v = (v - (-60.0)) / (0.0 - (-60.0))
                idx = int(max(0, min(1.0, normalized_v)) * 49)
                bins[idx] += 1

            for i, count in enumerate(bins):
                if count > 0:
                    bar_w = int((count / len(self.rms_history)) * 100)
                    bar_y = m_y + m_h - int((i + 1) * (m_h / 50))
                    pygame.draw.rect(meter_bg, (0, 200, 255), (m_x, bar_y, bar_w, int(m_h / 50)))

            # Map the floor slider value for visual placement
            normalized_floor = (noise_floor - (-60.0)) / (0.0 - (-60.0))
            floor_y = m_y + m_h - int(normalized_floor * m_h)
            pygame.draw.line(meter_bg, (255, 50, 50), (m_x - 5, floor_y), (m_x + 100 + 5, floor_y), 2)
            label = font.render("FLOOR", True, (255, 50, 50))
            meter_bg.blit(label, (m_x + 100 + 10, floor_y - 10))

            surface.blit(meter_bg, (sw - box_w - 20, sh - box_h - 20))
