import pygame
import time
import collections

class Tunable:
    def __init__(self, name, val, min_v, max_v, step, keys, fmt="{:.2f}", transformer=None, category="local"):
        self.name = name
        self.value = val
        self.min_v = min_v
        self.max_v = max_v
        self.step = step
        self.keys = keys
        self.fmt = fmt
        self.transformer = transformer
        self.category = category  # "global" or "local"

    def handle(self, key):
        if isinstance(self.keys, int):
            if key == self.keys:
                self.value = not self.value
                return True
            return False

        dec, inc = self.keys
        if not isinstance(dec, (list, tuple)): dec = [dec]
        if not isinstance(inc, (list, tuple)): inc = [inc]

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
    DB_MIN = -100.0
    DB_MAX = 0.0

    def __init__(self):
        self.params = []
        self.show_help = False
        self.help_timer = 0
        self.msg = ""
        self.msg_timer = 0
        # The core Noise Floor parameter (Global)
        self.noise_floor = self.add("Noise Floor", -40.0, self.DB_MIN, self.DB_MAX, 1.0, 
                                    (pygame.K_COMMA, pygame.K_PERIOD), fmt="{:.1f} dB", category="global")
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
        sw, sh = surface.get_width(), surface.get_height()

        # 1. Draw Quick Feedback Message (if not in help mode)
        if time.time() < self.msg_timer and not self.show_help:
            img = font.render(self.msg, True, (255, 255, 255))
            surface.blit(img, (20, 20))

        if not self.show_help:
            return

        if time.time() > self.help_timer:
            self.show_help = False
            return

        # 2. DRAW TOP-LEFT MENU (Local Visualization Params)
        local_params = [p for p in self.params if p.category == "local"]
        if local_params:
            bg_l = pygame.Surface((400, 20 + len(local_params) * 25), pygame.SRCALPHA)
            bg_l.fill((0, 0, 0, 160))
            surface.blit(bg_l, (10, 10))
            for i, p in enumerate(local_params):
                img = font.render(str(p), True, (0, 255, 150)) # Greenish for Local
                surface.blit(img, (20, 20 + i * 25))

        # 3. DRAW BOTTOM-RIGHT PANEL (Global Audio & Histogram)
        global_params = [p for p in self.params if p.category == "global"]
        box_w, box_h = 450, 220
        br_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        br_surf.fill((0, 0, 0, 160))

        # --- Histogram Logic ---
        m_w, m_h = 30, 180
        m_x, m_y = box_w - 180, (box_h - m_h) // 2
        
        # Draw Bars
        bins = [0] * 50
        for v in self.rms_history:
            norm_v = (v - self.DB_MIN) / (self.DB_MAX - self.DB_MIN)
            idx = int(max(0, min(1.0, norm_v)) * 49)
            bins[idx] += 1

        for i, count in enumerate(bins):
            if count > 0:
                bar_w = int((count / len(self.rms_history)) * 120)
                bar_y = m_y + m_h - int((i + 1) * (m_h / 50))
                pygame.draw.rect(br_surf, (0, 200, 255), (m_x, bar_y, bar_w, int(m_h / 50)))

        # Draw Floor Line
        norm_floor = (self.noise_floor.value - self.DB_MIN) / (self.DB_MAX - self.DB_MIN)
        floor_y = m_y + m_h - int(norm_floor * m_h)
        pygame.draw.line(br_surf, (255, 50, 50), (m_x - 10, floor_y), (m_x + 130, floor_y), 2)

        # Draw Global Text Params (to the left of the meter)
        for i, p in enumerate(global_params):
            img = font.render(str(p), True, (0, 220, 255)) # Cyan for Global
            br_surf.blit(img, (20, 20 + i * 25))

        surface.blit(br_surf, (sw - box_w - 10, sh - box_h - 10))