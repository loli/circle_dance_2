import collections
import time

import pygame


class KeyManager:
    """Static utility class to manage available keys globally."""

    # Class-level attributes (Shared across all calls)
    _single_keys = collections.deque(
        [pygame.K_y, pygame.K_x, pygame.K_c, pygame.K_v, pygame.K_b, pygame.K_n, pygame.K_m]
    )

    _pair_keys = collections.deque(
        [
            (pygame.K_q, pygame.K_a),
            (pygame.K_w, pygame.K_s),
            (pygame.K_e, pygame.K_d),
            (pygame.K_r, pygame.K_f),
            (pygame.K_t, pygame.K_g),
            (pygame.K_z, pygame.K_h),
            (pygame.K_u, pygame.K_j),
            (pygame.K_i, pygame.K_k),
            (pygame.K_o, pygame.K_l),
        ]
    )

    @classmethod
    def get_single(cls) -> int:
        if not cls._single_keys:
            raise IndexError("No single keys left in the pool.")
        return cls._single_keys.popleft()

    @classmethod
    def get_pair(cls) -> tuple[int, int]:
        if not cls._pair_keys:
            raise IndexError("No key pairs left in the pool.")
        return cls._pair_keys.popleft()


class BooleanParameter:
    def __init__(self, name: str, val: bool, category: str = "local") -> None:
        """
        Represents a boolean parameter that can be toggled using a single key.

        Args:
            name: The name of the parameter.
            val: The initial value of the parameter (True/False).
            category: The category of the parameter ("global" or "local").
        """
        self.name = name
        self.value = val
        self.key = KeyManager.get_single()
        self.category = category

    def handle(self, key: int) -> bool:
        """
        Handles keyboard input to toggle the parameter.

        Args:
            key: The key pressed.

        Returns:
            True if the parameter was toggled, False otherwise.
        """
        if key == self.key:
            self.value = not self.value
            return True
        return False

    def __str__(self) -> str:
        """
        Returns a string representation of the parameter.

        Returns:
            A formatted string showing the parameter name, value, and associated key.
        """
        v_str = "ON" if self.value else "OFF"
        k_str = f"[{pygame.key.name(self.key).upper()}]"
        return f"{k_str:<6} {self.name}: {v_str}"

    def __bool__(self) -> bool:
        return self.value


class NumericParameter:
    def __init__(
        self,
        name: str,
        val: float,
        min_v: float,
        max_v: float,
        step: float,
        fmt: str = "{:.2f}",
        category: str = "local",
    ) -> None:
        """
        Represents a numeric parameter that can be adjusted using keyboard input.

        Args:
            name: The name of the parameter.
            val: The initial value of the parameter.
            min_v: The minimum value of the parameter.
            max_v: The maximum value of the parameter.
            step: The step size for incrementing or decrementing the value.
            fmt: The format string for displaying the parameter value.
            category: The category of the parameter ("global" or "local").
        """
        self.name = name
        self.value = val
        self.min_v = min_v
        self.max_v = max_v
        self.step = step
        self.keys = KeyManager.get_pair()
        self.fmt = fmt
        self.category = category

    def handle(self, key: int) -> bool:
        """
        Handles keyboard input to adjust the parameter.

        Args:
            key: The key pressed.

        Returns:
            True if the parameter was adjusted, False otherwise.
        """
        dec, inc = self.keys

        if key == dec:
            self.value -= self.step
            self.value = max(self.min_v, min(self.max_v, self.value))
            return True
        elif key == inc:
            self.value += self.step
            self.value = max(self.min_v, min(self.max_v, self.value))
            return True

        return False

    def __str__(self) -> str:
        """
        Returns a string representation of the parameter.

        Returns:
            A formatted string showing the parameter name, value, and associated keys.
        """
        v_str = self.fmt.format(self.value)
        k1, k2 = self.keys
        k_str = f"[{pygame.key.name(k1).upper()}/{pygame.key.name(k2).upper()}]"
        return f"{k_str:<6} {self.name}: {v_str}"

    def __float__(self) -> float:
        return self.value


class HUD:
    def __init__(self) -> None:
        """Default visualization interface and parameter manager."""
        self.params = []
        self.show_help = False
        self.help_timer = 0
        self.msg = ""
        self.msg_timer = 0

    def register(self, p: NumericParameter | BooleanParameter) -> NumericParameter | BooleanParameter:
        """Register a new parameter with the HUD."""
        self.params.append(p)
        return p

    def handle_input(self, key: int) -> None:
        """
        Handles keyboard input to adjust parameters or toggle help.

        Args:
            key: The key pressed.
        """
        if key == pygame.K_h:
            self.show_help = not self.show_help
            self.help_timer = time.time() + 30.0 if self.show_help else 0
            return

        for p in self.params:
            if p.handle(key):
                self.msg = str(p)
                self.msg_timer = time.time() + 2.0
                return

    def draw_scene_controls(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        """Local Visualization Params / Scene Controls Panel (Top-Left)"""
        local_params = [p for p in self.params if p.category == "local"]
        if local_params:
            # Theme Colors
            COLOR_HEADER = (0, 255, 150)
            COLOR_TEXT = (0, 255, 150)
            LINE_HEIGHT = 25

            # 1. Render Header
            header_img = font.render("--- SCENE CONTROLS ---", True, COLOR_HEADER)

            # 2. Calculate Background Size
            # We add an extra line for the header + a small buffer
            bg_h = 30 + ((len(local_params) + 1) * LINE_HEIGHT)
            bg_l = pygame.Surface((400, bg_h), pygame.SRCALPHA)
            bg_l.fill((0, 0, 0, 160))

            # 3. Blit to Main Surface
            surface.blit(bg_l, (10, 10))
            surface.blit(header_img, (20, 20))

            # 4. Render Parameters (offset by header height)
            for i, p in enumerate(local_params):
                img = font.render(str(p), True, COLOR_TEXT)
                # Starting at y=50 to leave room for the header at y=20
                surface.blit(img, (20, 50 + i * LINE_HEIGHT))

    def draw_audio_controls(self, surface: pygame.Surface, font: pygame.font.Font, audio_state: dict) -> None:
        global_params = [p for p in self.params if p.category == "global"]
        if not global_params:
            return

        sw, sh = surface.get_width(), surface.get_height()
        # Box is wider now to accommodate graphs on the right
        box_w, box_h = 600, 40 + (len(global_params) * 40)

        br_surf = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        br_surf.fill((0, 0, 0, 160))

        # Header
        br_surf.blit(font.render("--- AUDIO ENGINE ---", True, (0, 220, 255)), (20, 10))

        for i, p in enumerate(global_params):
            y_offset = 45 + (i * 40)

            # 1. Draw the Label
            br_surf.blit(font.render(str(p), True, (0, 220, 255)), (20, y_offset))

            # 2. Define a "Graph Rect" to the right of the text
            graph_rect = pygame.Rect(350, y_offset, 230, 30)

            # 3. Create a sub-surface for the parameter to draw on
            # This keeps the parameter's drawing code relative to (0,0)
            sub_surf = br_surf.subsurface(graph_rect)

            # 4. Let the parameter draw its specific visualization
            if hasattr(p, "draw_visual"):
                p.draw_visual(sub_surf, audio_state)

        surface.blit(br_surf, (sw - box_w - 10, sh - box_h - 10))

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, audio_state: dict) -> None:
        # Draw Quick Feedback Message (if not in help mode)
        if not self.show_help and time.time() < self.msg_timer:
            img = font.render(self.msg, True, (255, 255, 255))
            surface.blit(img, (20, 20))

        if time.time() > self.help_timer:
            self.show_help = False

        if not self.show_help:
            return

        # from here: show help/status panels
        self.draw_scene_controls(surface, font)
        self.draw_audio_controls(surface, font, audio_state)
