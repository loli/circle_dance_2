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
            (pygame.K_u, pygame.K_j),
            (pygame.K_i, pygame.K_k),
            (pygame.K_o, pygame.K_l),
            # Numeric keys for physics/extra parameters
            (pygame.K_1, pygame.K_2),
            (pygame.K_3, pygame.K_4),
            (pygame.K_5, pygame.K_6),
            (pygame.K_z, pygame.K_x),
            (pygame.K_c, pygame.K_v),
            (pygame.K_b, pygame.K_n),
            (pygame.K_m, pygame.K_COMMA),
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
        """Top-Left Panel"""
        local_params = [p for p in self.params if p.category == "local"]
        if not local_params:
            return
        self._render_panel(surface, font, "--- SCENE CONTROLS ---", local_params, (10, 10), (0, 255, 150))

    def draw_physics_controls(self, surface: pygame.Surface, font: pygame.font.Font, audio_state: dict) -> None:
        """Top-Right Panel for Attack/Decay Physics"""
        physics_params = [p for p in self.params if p.category == "physics"]
        if not physics_params:
            return

        sw = surface.get_width()
        panel_w = 400
        # Position at Top-Right
        x_pos, y_pos = sw - panel_w - 10, 10

        # We reuse the specialized visualization logic from audio_controls
        self._render_panel_with_viz(
            surface, font, "--- PHYSICS ENGINE ---", physics_params, (x_pos, y_pos), (255, 150, 0), audio_state
        )

    def draw_audio_controls(self, surface: pygame.Surface, font: pygame.font.Font, audio_state: dict) -> None:
        """Bottom-Right Panel for Global Audio Engine"""
        global_params = [p for p in self.params if p.category == "global"]
        if not global_params:
            return

        sw, sh = surface.get_width(), surface.get_height()
        box_w = 600
        box_h = 40 + (len(global_params) * 40)
        self._render_panel_with_viz(
            surface,
            font,
            "--- AUDIO ENGINE ---",
            global_params,
            (sw - box_w - 10, sh - box_h - 10),
            (0, 220, 255),
            audio_state,
            box_w,
        )

    def _render_panel_with_viz(self, surface, font, title, params, pos, color, audio_state, width=400):
        """Helper to render panels that include draw_visual support."""
        line_h = 40
        box_h = 40 + (len(params) * line_h)
        panel_surf = pygame.Surface((width, box_h), pygame.SRCALPHA)
        panel_surf.fill((0, 0, 0, 160))

        panel_surf.blit(font.render(title, True, color), (20, 10))
        for i, p in enumerate(params):
            y_off = 45 + (i * line_h)
            panel_surf.blit(font.render(str(p), True, color), (20, y_off))

            if hasattr(p, "draw_visual"):
                # Align visualizers to the right side of the panel
                graph_rect = pygame.Rect(width - 240, y_off, 230, 30)
                sub = panel_surf.subsurface(graph_rect)
                p.draw_visual(sub, audio_state)

        surface.blit(panel_surf, pos)

    def _render_panel(self, surface, font, title, params, pos, color):
        """Helper for standard text-only panels."""
        line_h = 25
        bg_h = 30 + ((len(params) + 1) * line_h)
        bg = pygame.Surface((400, bg_h), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 160))

        bg.blit(font.render(title, True, color), (10, 10))
        for i, p in enumerate(params):
            bg.blit(font.render(str(p), True, color), (10, 40 + i * line_h))
        surface.blit(bg, pos)

    def draw(self, surface: pygame.Surface, font: pygame.font.Font, audio_state: dict) -> None:
        if not self.show_help and time.time() < self.msg_timer:
            img = font.render(self.msg, True, (255, 255, 255))
            surface.blit(img, (20, 20))

        if time.time() > self.help_timer:
            self.show_help = False

        if not self.show_help:
            return

        self.draw_scene_controls(surface, font)
        self.draw_physics_controls(surface, font, audio_state)  # NEW PANEL
        self.draw_audio_controls(surface, font, audio_state)
