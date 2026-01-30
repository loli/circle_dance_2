import time

import pygame

from note_dancer.visualization_v2.base.parameters_base import BooleanParameter, NumericParameter, ParameterContainer


class HUD:
    def __init__(self) -> None:
        """Default visualization interface and parameter manager."""
        self.params = []
        self.show_help = False
        self.help_timer = 0
        self.msg = ""
        self.msg_timer = 0

    def register(
        self, p: NumericParameter | BooleanParameter | ParameterContainer
    ) -> NumericParameter | BooleanParameter | ParameterContainer:
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

    def _render_panel_with_viz(self, surface, font, title, params, pos, color, audio_state, width=480):
        line_h = 32
        box_h = 45 + (len(params) * line_h)

        panel_surf = pygame.Surface((width, box_h), pygame.SRCALPHA)
        panel_surf.fill((0, 0, 0, 180))
        panel_surf.blit(font.render(title, True, color), (15, 10))

        for i, p in enumerate(params):
            y_off = 45 + (i * line_h)

            # 1. Label (Works for Parameters and Containers)
            label_img = font.render(str(p), True, color)
            panel_surf.blit(label_img, (15, y_off))

            # 2. Visualization (Unified handling)
            if hasattr(p, "draw_visual"):
                graph_w = 160
                # Positioned relative to the wider panel
                graph_rect = pygame.Rect(width - graph_w - 15, y_off + 2, graph_w, 20)
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
