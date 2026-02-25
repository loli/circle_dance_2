import collections
import random
import time

import pygame

from note_dancer.visualization_v2.base.audioviz import AudioVisualizationBase
from note_dancer.visualization_v2.base.hud import NumericParameter

# --- Configuration ---
COLOR_SNAKE_HEAD = (180, 180, 180)
COLOR_SNAKE_BODY = (100, 100, 100)
COLOR_FOOD_NEON = (255, 120, 0)
COLOR_GRID = (20, 20, 20)
COLOR_BG = (0, 0, 0)


class SnakGame:
    def __init__(self, grid_size: int):
        self.grid_size = grid_size
        self.reset()

    def reset(self):
        self.snake = [(2, 5), (1, 5), (0, 5)]
        self.direction = (1, 0)
        self.next_direction = (1, 0)
        self.food_pos = self._spawn_food()
        self.score = 0
        self.just_ate = False

    def _spawn_food(self) -> tuple[int, int]:
        while True:
            pos = (random.randint(0, self.grid_size - 1), random.randint(0, self.grid_size - 1))
            if pos not in self.snake:
                return pos

    def is_safe(self, x: int, y: int) -> bool:
        return 0 <= x < self.grid_size and 0 <= y < self.grid_size and (x, y) not in self.snake

    def move(self) -> bool:
        self.just_ate = False
        self.direction = self.next_direction
        hx, hy = self.snake[0]
        nx, ny = hx + self.direction[0], hy + self.direction[1]

        if not self.is_safe(nx, ny):
            return False

        self.snake.insert(0, (nx, ny))
        if (nx, ny) == self.food_pos:
            self.score += 1
            self.food_pos = self._spawn_food()
            self.just_ate = True
        else:
            self.snake.pop()
        return True

    def find_ai_move(self):
        head = self.snake[0]
        moves = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        safe = [m for m in moves if self.is_safe(head[0] + m[0], head[1] + m[1])]
        if not safe:
            return None
        safe.sort(key=lambda m: abs((head[0] + m[0]) - self.food_pos[0]) + abs((head[1] + m[1]) - self.food_pos[1]))
        return safe[0]


class SnakeVisualizer(AudioVisualizationBase):
    def __init__(self):
        super().__init__()
        self.grid_size = 10
        self.cell_size = min(self.width, self.height) // (self.grid_size + 4)
        self.offset_x = (self.width - (self.grid_size * self.cell_size)) // 2
        self.offset_y = (self.height - (self.grid_size * self.cell_size)) // 2

        self.game = SnakGame(self.grid_size)

        # Timing & State
        self.beat_count = 0
        self.last_beat_time = 0
        self.flash_alpha = 0

        # Breakback logic: buffer last 8 beats (2 bars in 4/4) to detect kick presence
        self.kick_history = collections.deque([True] * 8, maxlen=8)
        self.is_in_breakdown = False

        # Parameters
        self.kick_threshold = self.hud.register(NumericParameter("Kick Thr", 0.5, 0.1, 1.0, 0.05, category="local"))
        # 0: Half, 1: Normal, 2: Double
        self.speed_mult = self.hud.register(NumericParameter("BPM Mult", 1, 1, 2, 1, category="local"))

    def render_visualization(self, screen: pygame.Surface, font: pygame.font.Font) -> None:
        events = self.process_audio_frame()
        if not events:
            return

        kick_val = events.get("low", 0.0)
        current_kick_active = kick_val > self.kick_threshold.value

        # --- 1. Beat Processing ---
        if events["beat"]:
            self.beat_count += 1
            self.last_beat_time = time.time()

            # Update kick history for breakdown detection (wait for ~2 bars)
            self.kick_history.append(current_kick_active)
            # If no kicks were detected in the last 8 beats, we are in a breakdown
            self.is_in_breakdown = not any(self.kick_history)

            # Determine movement speed based on BPM Mult control
            # 0 (Half) -> Move every 4 beats
            # 1 (Normal) -> Move every 2 beats
            # 2 (Double) -> Move every beat
            move_trigger = False
            if self.speed_mult.value == 0:
                move_trigger = self.beat_count % 4 == 0
            elif self.speed_mult.value == 1:
                move_trigger = self.beat_count % 2 == 0
            else:
                move_trigger = True

            if move_trigger and not self.is_in_breakdown:
                ai_move = self.game.find_ai_move()
                if ai_move:
                    self.game.next_direction = ai_move
                if not self.game.move():
                    self.game.reset()
                if self.game.just_ate:
                    self.flash_alpha = 120

        # --- 2. Drawing Prep ---
        screen.fill(COLOR_BG)

        # Flash Effect
        if self.flash_alpha > 0:
            flash_surf = pygame.Surface((self.width, self.height))
            flash_surf.fill((255, 255, 255))
            flash_surf.set_alpha(self.flash_alpha)
            screen.blit(flash_surf, (0, 0))
            self.flash_alpha = max(0, self.flash_alpha - 10)

        # Grid
        for i in range(self.grid_size + 1):
            x_line = self.offset_x + i * self.cell_size
            y_line = self.offset_y + i * self.cell_size
            pygame.draw.line(
                screen, COLOR_GRID, (x_line, self.offset_y), (x_line, self.offset_y + self.grid_size * self.cell_size)
            )
            pygame.draw.line(
                screen, COLOR_GRID, (self.offset_x, y_line), (self.offset_x + self.grid_size * self.cell_size, y_line)
            )

        # --- 3. Dance Logic (Color Swap every 4th beat) ---
        dance_swap = self.is_in_breakdown and (self.beat_count // 4) % 2 == 1

        current_food_color = COLOR_SNAKE_HEAD if dance_swap else COLOR_FOOD_NEON
        current_snake_color = COLOR_FOOD_NEON if dance_swap else COLOR_SNAKE_HEAD

        # --- 4. Food Rendering (50% to 100% Growth) ---
        fx, fy = self.game.food_pos
        hx, hy = self.game.snake[0]
        # Max distance is ~14-18; normalize growth so proximity is visible
        dist = abs(fx - hx) + abs(fy - hy)
        proximity = max(0.0, 1.0 - (dist / (self.grid_size * 1.2)))

        # Size Update: Starts at 50%, grows to 100%
        food_scale = 0.5 + (0.5 * proximity)
        food_dim = self.cell_size * food_scale

        food_rect = pygame.Rect(0, 0, food_dim - 2, food_dim - 2)
        food_rect.center = (
            self.offset_x + fx * self.cell_size + self.cell_size // 2,
            self.offset_y + fy * self.cell_size + self.cell_size // 2,
        )

        pygame.draw.rect(screen, current_food_color, food_rect)

        # --- 5. Snake Rendering ---
        time_since_beat = time.time() - self.last_beat_time
        bounce = int(kick_val * 15 * max(0, 1.0 - (time_since_beat * 5.0)))

        for i, (sx, sy) in enumerate(self.game.snake):
            snake_rect = pygame.Rect(
                self.offset_x + sx * self.cell_size + 4,
                self.offset_y + sy * self.cell_size + 4 - bounce,
                self.cell_size - 8,
                self.cell_size - 8,
            )

            if i == 0:
                color = current_snake_color
            else:
                fade = max(0.4, 1.0 - (i / len(self.game.snake)))
                if dance_swap:
                    # Fade the orange body
                    color = (int(current_snake_color[0] * fade), int(current_snake_color[1] * fade), 0)
                else:
                    color = (int(100 * fade), int(100 * fade), int(100 * fade))

            pygame.draw.rect(screen, color, snake_rect)

        # HUD Info
        mode = "BREAKDOWN" if self.is_in_breakdown else "DRIVING"
        speed_label = ["1/4", "1/2", "1/1"][int(self.speed_mult.value)]
        info = font.render(f"SCORE: {self.game.score} | RATE: {speed_label} | {mode}", True, (120, 120, 120))
        screen.blit(info, (self.offset_x, self.offset_y - 35))

    def handle_keys(self, key: int) -> None:
        super().handle_keys(key)


def run():
    SnakeVisualizer().run()


if __name__ == "__main__":
    run()
