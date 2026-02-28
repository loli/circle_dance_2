import sys

import pygame

from note_dancer.visualization.base.audioviz import AudioVisualizationBase

# Constants
WIDTH, HEIGHT = 800, 600
LOW_COLOR = (255, 50, 50)
MID_COLOR = (50, 255, 50)
HIGH_COLOR = (50, 100, 255)
NOTE_COLOR = (200, 200, 50)
TEXT_COLOR = (220, 220, 220)


class DashboardVisualizer(AudioVisualizationBase):
    def __init__(self):
        super().__init__()
        self.large_font = pygame.font.SysFont("Arial", 32, bold=True)
        self.note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

        # Internal accumulator for a smoother "Beat Pulse" effect
        self.pulse_val = 0.0

    def draw_bar(self, screen, x, y, width, height, value, color, label, font):
        """Helper to draw vertical energy meters."""
        pygame.draw.rect(screen, (40, 40, 45), (x, y, width, height))
        # Clamp value for safety
        val = max(0, min(1.0, value))
        fill_h = int(height * val)
        pygame.draw.rect(screen, color, (x, y + height - fill_h, width, fill_h))

        lbl = font.render(label, True, TEXT_COLOR)
        screen.blit(lbl, (x, y + height + 5))

    def render_visualization(self, screen: pygame.Surface, font: pygame.font.Font):
        # 1. Process Audio Data and get smoothed events
        events = self.process_audio_frame()
        if not events:
            return

        # 2. Draw Background
        screen.fill((15, 15, 20))

        # --- A. Pulse Circle ---
        # If a beat is detected, jump pulse_val to 1.0, otherwise let it decay
        if events["beat"]:
            self.pulse_val = 1.0
        else:
            # Slow decay for the visual pulse (separate from the base class decay)
            self.pulse_val *= 0.9

        pulse_radius = 50 + int(self.pulse_val * 40)

        # Border thickness still driven by flux for "impact"
        flux_border = max(1, int(self.data["flux"] * 3))
        pygame.draw.circle(screen, (255, 255, 255), (WIDTH // 2, 150), pulse_radius, flux_border)

        # Use the Hedged and Smoothed BPM from events
        bpm_text = self.large_font.render(f"{events['bpm']:.1f} BPM", True, TEXT_COLOR)
        screen.blit(bpm_text, (WIDTH // 2 - 70, 135))

        # --- B. Frequency Bands (Using SMOOTHED values from events) ---
        bar_w, bar_h = 60, 200
        y_pos = 300
        self.draw_bar(screen, 100, y_pos, bar_w, bar_h, events["low"], LOW_COLOR, "LOW", font)
        self.draw_bar(screen, 200, y_pos, bar_w, bar_h, events["mid"], MID_COLOR, "MID", font)
        self.draw_bar(screen, 300, y_pos, bar_w, bar_h, events["high"], HIGH_COLOR, "HIGH", font)

        # --- C. Brightness Meter ---
        bright_x = 450
        # Brightness isn't smoothed in the base class yet, so we use self.data
        self.draw_bar(screen, bright_x, y_pos, 30, bar_h, self.data["brightness"], (255, 255, 255), "BRIGHT", font)

        # --- D. Chroma Notes ---
        chroma_start_x = 100
        chroma_y = 550
        for i, val in enumerate(self.data["notes"]):
            n_x = chroma_start_x + (i * 50)
            n_h = int(val * 40)

            # Highlight notes that pass the gated Note Sens threshold
            is_active = i in events["active_notes"]
            color = NOTE_COLOR if is_active else (60, 60, 40)

            pygame.draw.rect(screen, color, (n_x, chroma_y - n_h, 30, n_h))
            screen.blit(font.render(self.note_names[i], True, TEXT_COLOR), (n_x, chroma_y + 5))


def run():
    pygame.init()
    main_screen = pygame.display.set_mode((WIDTH, HEIGHT))
    main_font = pygame.font.SysFont("Arial", 18)

    viz = DashboardVisualizer()
    clock = pygame.time.Clock()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                viz.handle_keys(event.key)

        viz.draw(main_screen, main_font)
        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    run()
