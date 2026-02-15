import json
import os
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
        self.preset_slots: dict[str, None | dict] = {str(i): None for i in range(10)}  # Keys '0' through '9'
        self.preset_file = "user_presets.json"
        self.preset_slots = self._load_from_disk()

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

        # Preset Logic
        mods = pygame.key.get_mods()
        is_ctrl = mods & pygame.KMOD_CTRL

        # Check for keys 0-9
        if pygame.K_0 <= key <= pygame.K_9:
            slot = pygame.key.name(key)
            if is_ctrl:
                self._save_preset(slot)
            else:
                self._load_preset(slot)
            return  # Exit early so we don't trigger other HUD actions

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

    def _save_preset(self, slot: str):
        snapshot = {}
        for p in self.registry:
            if isinstance(p, ParameterContainer):
                snapshot[p.name] = {sub.name: sub.value for sub in p.get_items()}
            else:
                snapshot[p.name] = p.value

        self.preset_slots[slot] = snapshot
        self._save_to_disk()

        self._show_message(f"PRESET {slot} SAVED TO DISK")

    def _load_preset(self, slot: str):
        """Applies a saved snapshot to the current parameters."""
        snapshot = self.preset_slots.get(slot)
        if not snapshot:
            return

        for p in self.registry:
            if isinstance(p, ParameterContainer) and p.name in snapshot:
                container_data = snapshot[p.name]
                for sub in p.get_items():
                    if sub.name in container_data:
                        sub.value = type(sub.value)(container_data[sub.name])
            elif p.name in snapshot:
                p.value = type(p.value)(snapshot[p.name])

        self._show_message(f"PRESET {slot} LOADED")

    def _show_message(self, text):
        self.msg = text
        self.msg_timer = time.time() + 2.0

    def _save_to_disk(self):
        """Writes the current preset_slots dictionary to a JSON file."""
        try:
            with open(self.preset_file, "w") as f:
                json.dump(self.preset_slots, f, indent=4)
        except Exception as e:
            print(f"Error saving presets: {e}")

    def _load_from_disk(self):
        """Loads presets from disk or returns empty slots if file doesn't exist."""
        if os.path.exists(self.preset_file):
            try:
                with open(self.preset_file, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading presets: {e}")

        # Return empty slots if file is missing/invalid
        return {str(i): None for i in range(10)}

    def draw_presets(self, surface, font):
        # Position: Bottom Left
        start_x, start_y = 15, surface.get_height() - 40
        size = 25
        spacing = 8

        for i in range(10):
            slot_key = str((i + 1) % 10)  # Order: 1, 2, ... 9, 0
            is_occupied = self.preset_slots[slot_key] is not None

            rect = pygame.Rect(start_x + i * (size + spacing), start_y, size, size)

            # Draw Box
            if is_occupied:
                # Filled box for saved presets (Sober Green/Cyan)
                pygame.draw.rect(surface, (0, 200, 180, 180), rect)
            else:
                # Outline for empty slots
                pygame.draw.rect(surface, (100, 100, 100, 150), rect, 1)

            # Draw Number
            num_img = font.render(slot_key, True, (255, 255, 255))
            # Center the number in the box
            text_rect = num_img.get_rect(center=rect.center)
            surface.blit(num_img, text_rect)

        # Draw temporary status message (e.g., "PRESET 1 SAVED")
        if time.time() < self.msg_timer:
            msg_img = font.render(self.msg, True, (255, 255, 0))
            surface.blit(msg_img, (start_x, start_y - 30))

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

    def draw_fps(self, surface, font, fps):
        # Draw it in the top right or bottom right
        fps_text = f"FPS: {int(fps)}"
        # Color logic: Red if it drops below 50 (indicating stutter)
        fps_color = (0, 255, 0) if fps > 50 else (255, 50, 50)
        fps_img = font.render(fps_text, True, fps_color)

        # Position: Bottom right, above presets
        surface.blit(fps_img, (surface.get_width() - 100, surface.get_height() - 40))

    def draw(self, surface, font, audio_state, fps: float = 0):
        if not self.show_help:
            return  # Toggle 'H' to see menu
        self.draw_scene_controls(surface, font)
        self.draw_physics_controls(surface, font, audio_state)
        self.draw_audio_controls(surface, font, audio_state)
        self.draw_presets(surface, font)
        self.draw_fps(surface, font, fps)
