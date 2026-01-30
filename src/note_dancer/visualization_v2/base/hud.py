import time

import pygame

from note_dancer.visualization_v2.base.parameters_base import (
    BooleanParameter,
    NumericParameter,
    ParameterContainer,
)


class HUD:
    def __init__(self) -> None:
        self.params = []
        self.registry = []
        self.selected_idx = 0
        self.active_category = "local"
        self.categories = ["local", "physics", "global"]
        self.show_help = True  # Changed to True for testing visibility
        self.help_timer = time.time() + 3600  # Long timer for dev
        self.msg = ""
        self.msg_timer = 0

    def register(self, p):
        self.registry.append(p)
        self._rebuild_selection_list()
        return p

    def _rebuild_selection_list(self) -> None:
        self.params = []
        for item in self.registry:
            if isinstance(item, ParameterContainer):
                for sub in item.get_items():
                    self.params.append(sub)
            else:
                if not hasattr(item, "owner"):
                    item.owner = None
                self.params.append(item)

    def handle_input(self, key: int) -> None:
        # Toggle HUD visibility with 'H'
        if key == pygame.K_h:
            self.show_help = not self.show_help
            self.help_timer = time.time() + 60

        # Only process further input if HUD is visible
        if not self.show_help:
            return

        current_view = [p for p in self.params if p.category == self.active_category]
        if not current_view:
            return

        if key == pygame.K_UP:
            self.selected_idx = (self.selected_idx - 1) % len(current_view)
        elif key == pygame.K_DOWN:
            self.selected_idx = (self.selected_idx + 1) % len(current_view)
        elif key == pygame.K_TAB:
            cat_idx = (self.categories.index(self.active_category) + 1) % len(self.categories)
            self.active_category = self.categories[cat_idx]
            self.selected_idx = 0

        target = current_view[self.selected_idx]
        if isinstance(target, NumericParameter):
            if key == pygame.K_RIGHT:
                target.adjust(1)
            elif key == pygame.K_LEFT:
                target.adjust(-1)
        elif isinstance(target, BooleanParameter):
            if key in [pygame.K_RETURN, pygame.K_SPACE]:
                target.toggle()

    def _render_panel_with_viz(self, surface, font, title, params, pos, color, audio_state, width=480):
        # Determine selection context
        current_view = [p for p in self.params if p.category == self.active_category]

        line_h = 32
        box_h = 45 + (len(params) * line_h)
        panel_surf = pygame.Surface((width, box_h), pygame.SRCALPHA)
        panel_surf.fill((0, 0, 0, 180))
        panel_surf.blit(font.render(title, True, color), (15, 10))

        # Tracks grouped visuals (like Envelopes) to avoid double-drawing
        drawn_groups = set()

        for i, p in enumerate(params):
            y_off = 45 + (i * line_h)

            # Selection & Label
            is_selected = p in current_view and current_view.index(p) == self.selected_idx
            text_color = (255, 255, 255) if is_selected else color
            prefix = "> " if is_selected else "  "

            label_img = font.render(prefix + str(p), True, text_color)
            panel_surf.blit(label_img, (15, y_off))

            # --- VISUALIZATION LOGIC ---
            graph_w = 160
            graph_rect = pygame.Rect(width - graph_w - 15, y_off + 2, graph_w, 22)

            # Check 1: Does this parameter belong to a Container (like Envelope)?
            visual_owner = getattr(p, "owner", None)
            if visual_owner and hasattr(visual_owner, "draw_visual"):
                if visual_owner not in drawn_groups:
                    sub = panel_surf.subsurface(graph_rect)
                    visual_owner.draw_visual(sub, audio_state)
                    drawn_groups.add(visual_owner)

            # Check 2: Is this a specialized Standalone Parameter?
            # (FluxImpactParameter, ChromaSensitivityParameter, etc.)
            elif hasattr(p, "draw_visual"):
                sub = panel_surf.subsurface(graph_rect)
                p.draw_visual(sub, audio_state)

        surface.blit(panel_surf, pos)

    def _render_panel(self, surface, font, title, params, pos, color):
        current_view = [p for p in self.params if p.category == self.active_category]
        line_h = 25
        width = 400
        bg_h = 35 + ((len(params) + 1) * line_h)
        bg = pygame.Surface((width, bg_h), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 160))

        bg.blit(font.render(title, True, color), (10, 10))
        for i, p in enumerate(params):
            is_selected = p in current_view and current_view.index(p) == self.selected_idx
            text_color = (255, 255, 255) if is_selected else color
            prefix = "> " if is_selected else "  "
            bg.blit(font.render(prefix + str(p), True, text_color), (10, 40 + i * line_h))
        surface.blit(bg, pos)

    def draw_scene_controls(self, surface, font):
        local_params = [p for p in self.params if p.category == "local"]
        if local_params:
            self._render_panel(surface, font, "--- SCENE CONTROLS ---", local_params, (10, 10), (0, 255, 150))

    def draw_physics_controls(self, surface, font, audio_state):
        phys_params = [p for p in self.params if p.category == "physics"]
        if phys_params:
            sw = surface.get_width()
            self._render_panel_with_viz(
                surface, font, "--- PHYSICS ---", phys_params, (sw - 410, 10), (255, 150, 0), audio_state, 400
            )

    def draw_audio_controls(self, surface, font, audio_state):
        glob_params = [p for p in self.params if p.category == "global"]
        if glob_params:
            sw, sh = surface.get_width(), surface.get_height()
            box_h = 45 + (len(glob_params) * 32)
            self._render_panel_with_viz(
                surface,
                font,
                "--- AUDIO ---",
                glob_params,
                (sw - 610, sh - box_h - 10),
                (0, 220, 255),
                audio_state,
                600,
            )

    def draw(self, surface, font, audio_state):
        if not self.show_help:
            return  # Toggle 'H' to see menu
        self.draw_scene_controls(surface, font)
        self.draw_physics_controls(surface, font, audio_state)
        self.draw_audio_controls(surface, font, audio_state)
