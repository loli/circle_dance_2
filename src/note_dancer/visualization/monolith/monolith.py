import colorsys
import math

import pygame

from note_dancer.visualization.base.audioviz import AudioVisualizationBase
from note_dancer.visualization.base.hud import BooleanParameter, NumericParameter


class MonolithVisualizer(AudioVisualizationBase):
    def __init__(self, width=900, height=900):
        super().__init__()
        self.width, self.height = width, height
        self.center = (width // 2, height // 2)

        # --- Override Engine Defaults for this specific Viz ---
        # We want the Monolith to feel heavy and reactive to Bass
        self.low_gain.value = 10.0  # Boost the bass input, but not too much
        self.low_atk.value = 0.85  # Snappy attack for the jump
        self.low_dcy.value = 0.05  # Very slow decay for 'weight'

        self.flux_thr.value = 7.2  # Higher threshold for cleaner snaps
        self.note_sens.value = 0.95  # Only very high (relative) note energies contribute to color changes

        # --- Scene Controls ---
        self.base_size = self.hud.register(NumericParameter("Base Size", 200.0, 50.0, 400.0, 10.0, category="local"))
        self.jitter_amt = self.hud.register(NumericParameter("Jitter", 20.0, 0.0, 100.0, 5.0, category="local"))
        self.wireframe = self.hud.register(BooleanParameter("Wireframe", False, category="local"))

        # Internal animation state
        self.rotation = 0.0
        self.current_hue = 0.0

    def render_visualization(self, screen, font):
        # 1. Fetch Signal Chain
        events = self.process_audio_frame()
        if not events:
            return

        # --- NEW: STICKY CENTROID COLOR LOGIC ---
        active_indices = events["active_notes"]

        if active_indices:
            # We calculate the 'average' hue.
            # Note indices are 0-11, map them to 0.0-1.0
            # To handle the wrap-around (Red is both 0 and 1), we use basic trig
            sum_sin = 0
            sum_cos = 0
            for idx in active_indices:
                # Map index to angle in radians
                angle = (idx / 12.0) * 2.0 * math.pi
                # Weight by the actual energy of that note for better 'Centroid' feel
                weight = self.notes[idx]
                sum_sin += math.sin(angle) * weight
                sum_cos += math.cos(angle) * weight

            # The target hue is the resulting angle of our combined vectors
            target_hue_angle = math.atan2(sum_sin, sum_cos)
            target_hue = (target_hue_angle / (2.0 * math.pi)) % 1.0

            # HYSTERESIS: Slowly drift toward the target
            # Lowering 0.05 makes the color 'heavier' and stickier
            hue_diff = (target_hue - self.current_hue + 0.5) % 1.0 - 0.5
            self.current_hue = (self.current_hue + hue_diff * 0.05) % 1.0

        # 2. Physics Mapping (Standard Monolith Logic)
        # Inflation tied to Lows (Bass)
        inflation = events["low"] * 160.0
        current_size = self.base_size.value + inflation

        # Jitter tied to Highs (Snappy transients)
        jitter_val = events["high"] * self.jitter_amt.value
        jx = (pygame.time.get_ticks() % 6 - 3) * jitter_val
        jy = (pygame.time.get_ticks() % 4 - 2) * jitter_val

        # Rotation: Continuous drift + Snaps on Impact
        # Mid-range energy makes it spin faster
        self.rotation += 0.5 + events["mid"] * 8.0
        if events["impact"]:
            self.rotation += 15.0  # A smaller 'nudge' than before for cleaner look

        # 3. Background: BPM-Synced Pulse
        # Independent of volume, creates a rhythmic 'breath'
        bpm_t = pygame.time.get_ticks() / 1000.0
        # Use hedged BPM for a consistent pulse speed
        pulse_osc = math.sin(bpm_t * (events["bpm"] / 60.0) * math.pi)
        bg_brightness = 15 + int(pulse_osc * 8)
        screen.fill((bg_brightness, bg_brightness, bg_brightness + 5))

        # 4. Drawing the Monolith
        # Color intensity responds to the Mid-range (vocals/leads)
        brightness_mod = 120 + int(events["mid"] * 135)
        rgb = colorsys.hsv_to_rgb(self.current_hue, 0.9, 1.0)
        main_color = (int(rgb[0] * brightness_mod), int(rgb[1] * brightness_mod), int(rgb[2] * brightness_mod))

        # Project the 4 square points
        points = []
        for i in range(4):
            angle = math.radians(self.rotation + i * 90)
            px = self.center[0] + jx + math.cos(angle) * current_size
            py = self.center[1] + jy + math.sin(angle) * current_size
            points.append((px, py))

        # Draw bloom/glow layers
        for s in range(4, 0, -1):
            alpha = 40 // s
            glow_surf = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            pygame.draw.polygon(glow_surf, (*main_color, alpha), points, s * 3)
            screen.blit(glow_surf, (0, 0))

        # Final Face
        if self.wireframe.value:
            pygame.draw.polygon(screen, main_color, points, 4)
        else:
            pygame.draw.polygon(screen, main_color, points, 0)

    def run(self):
        pygame.init()
        screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("Vision 1: Kinetic Monolith")
        clock = pygame.time.Clock()
        font = pygame.font.SysFont("monospace", 16, bold=True)

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN:
                    self.handle_keys(event.key)

            self.draw(screen, font)
            pygame.display.flip()
            clock.tick(60)


def run():
    viz = MonolithVisualizer()
    viz.run()


if __name__ == "__main__":
    run()
