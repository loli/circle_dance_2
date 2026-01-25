import collections

import pygame

from note_dancer.visualization.base.hud import HUD, BooleanParameter, NumericParameter
from note_dancer.visualization.base.receiver import AudioReceiver


# self-visualizing parameters
class NoiseFloorParameter(NumericParameter):
    def draw_visual(self, surf: pygame.Surface, data: dict) -> None:
        history = data.get("rms_history", [])
        if not history:
            return

        w, h = surf.get_size()
        db_min, db_max = self.min_v, self.max_v

        # 1. Draw RMS Histogram/Sparkline
        points = []
        for i, val in enumerate(history):
            # Map index to x-coordinate
            x = (i / len(history)) * w
            # Map decibels to y-coordinate (inverted for screen space)
            norm_v = (val - db_min) / (db_max - db_min)
            y = h - (norm_v * h)
            points.append((x, y))

        if len(points) > 1:
            pygame.draw.lines(surf, (0, 150, 200), False, points, 1)

        # 2. Draw the "Floor" line based on current parameter value
        norm_floor = (self.value - db_min) / (db_max - db_min)
        floor_y = h - (norm_floor * h)
        pygame.draw.line(surf, (255, 50, 50), (0, floor_y), (w, floor_y), 2)


class SensitivityParameter(NumericParameter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Internal state to keep the drawing smooth
        self.smooth_energies = [0.0] * 12

    def draw_visual(self, surf: pygame.Surface, data: dict):
        raw_energies = data.get("prev_energies", [0.0] * 12)

        # 1. Apply Smoothing (Leaky Integrator)
        # This makes the bars 'float' down rather than snap down
        for i in range(12):
            target = raw_energies[i]
            if target > self.smooth_energies[i]:
                # Attack: fast response to new notes
                self.smooth_energies[i] = target
            else:
                # Release: slow decay (change 0.1 to adjust 'sluggishness')
                self.smooth_energies[i] -= (self.smooth_energies[i] - target) * 0.1

        w, h = surf.get_size()
        # 2. Sort the smoothed energies
        sorted_e = sorted(self.smooth_energies, reverse=True)
        peak = sorted_e[0] if sorted_e[0] > 0 else 1.0

        threshold_val = peak * self.value
        bar_w = w / 12

        # 3. Draw sorted bars
        for i, energy in enumerate(sorted_e):
            # We still normalize heights relative to the current peak
            # so the graph stays 'full' even during quiet parts
            bar_h = int((energy / peak) * h) if peak > 0 else 0
            bar_x = i * bar_w

            # Binary color: Is this smoothed note currently 'above the gate'?
            color = (0, 255, 150) if energy >= threshold_val else (40, 60, 50)
            pygame.draw.rect(surf, color, (bar_x + 1, h - bar_h, bar_w - 2, bar_h))

        # 4. Draw Threshold Line
        # Since we normalized bars to peak height, threshold line stays at (h * self.value)
        line_y = h - int(self.value * h)
        pygame.draw.line(surf, (255, 255, 0), (0, line_y), (w, line_y), 1)


class AttackParameter(NumericParameter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Store a history of the 'attack' values to draw the sparkline
        self.delta_history = collections.deque([0.0] * 100, maxlen=100)

    def draw_visual(self, surf: pygame.Surface, data: dict):
        energies = data.get("prev_energies", [0.0] * 12)
        old_energies = data.get("old_energies", [0.0] * 12)  # You'll need to pass this

        # 1. Calculate the current max attack (the sharpest spike among all notes)
        current_max_attack = 0.0
        for i in range(12):
            attack = energies[i] - old_energies[i]
            current_max_attack = max(current_max_attack, attack)

        self.delta_history.append(current_max_attack)

        w, h = surf.get_size()

        # 2. Draw the Sparkline
        points = []
        for i, val in enumerate(self.delta_history):
            x = (i / len(self.delta_history)) * w
            # Normalize: Attack threshold is usually small (0.0 to 0.5),
            # so we scale the graph so 1.0 is the top
            y = h - max(0, min(h, int(val * h)))
            points.append((x, y))

        if len(points) > 1:
            pygame.draw.lines(surf, (200, 100, 255), False, points, 1)

        # 3. Draw the Threshold Line (Attack Threshold)
        # This is the line the user is moving
        line_y = h - int(self.value * h)

        # Flash the line if the current attack is above the threshold
        color = (255, 255, 255) if current_max_attack > self.value else (150, 50, 200)
        pygame.draw.line(surf, color, (0, line_y), (w, line_y), 2)


class AudioVisualizationBase:
    """Base class for audio-reactive visualizations.

    Handles shared audio processing, parameter management, and event detection.
    """

    def __init__(self) -> None:
        self.receiver = AudioReceiver()
        self.hud = HUD()

        # --- Shared Audio Parameters ---
        self.noise_floor = self.hud.register(
            NoiseFloorParameter("Noise Floor", -40.0, -60.0, 0.0, 1.0, category="global")
        )
        self.sensitivity = self.hud.register(
            SensitivityParameter("Sensitivity", 0.85, 0.1, 0.98, 0.02, category="global")
        )
        self.attack_threshold = self.hud.register(
            AttackParameter("Attack Thr", 0.18, 0.01, 1.0, 0.02, category="global")
        )
        self.beat_pulse_enabled = self.hud.register(BooleanParameter("Beat Pulse", True, category="global"))

        # --- Shared State ---
        self.bpm = 120.0
        self.rms_history = collections.deque(maxlen=200)

        self.rotation_speed = 2.0
        self.decay_rate = 1.0
        self.beat_boost = 0.0
        self.prev_energies = [0.0] * 12
        self.old_energies = [0.0] * 12
        self.current_brightness = 0.0

    def handle_keys(self, key: int) -> None:
        """Routes key presses to the HUD."""
        self.hud.handle_input(key)

    def update_tempo(self, new_bpm: float) -> None:
        """Normalizes BPM to a usable range and calculates movement constants."""

        # Keep BPM in a 'human' dance range (80-160)
        while new_bpm < 80:
            new_bpm *= 2
        while new_bpm > 160:
            new_bpm /= 2

        # Smooth the transition to avoid jerky rotation changes
        self.bpm = (self.bpm * 0.95) + (new_bpm * 0.05)

        # Constants for 60FPS movement
        beats_per_rotation = 16
        total_frames = ((60.0 / self.bpm) * beats_per_rotation) * 60.0

        self.rotation_speed = 360.0 / total_frames
        # Decay should be relative to rotation so traces last exactly one loop
        self.decay_rate = 255.0 / (360.0 / self.rotation_speed)

    def process_audio_frame(self) -> list[dict]:
        """The core logic that turns raw bytes into 'events' for the visualizer."""
        self.receiver.update()

        # 1. Handle Tempo/Beats
        if self.receiver.beat_detected:
            self.update_tempo(self.receiver.bpm)
            if self.beat_pulse_enabled.value:
                self.beat_boost = 1.0

        # 2. Update Beat Boost Decay (Physics)
        if self.beat_boost > 0:
            self.beat_boost *= 0.85
        if self.beat_boost < 0.01:
            self.beat_boost = 0

        # 3. Extract Valid Note Events
        triggered_notes = []
        if self.receiver.notes_updated:
            self.current_brightness = self.receiver.brightness

            # Noise Floor Gate
            if self.receiver.rms >= self.noise_floor.value:
                new_e = self.receiver.notes
                current_peak = max(new_e) if any(new_e) else 0.0

                self.old_energies = list(self.prev_energies)

                for i in range(12):
                    attack = new_e[i] - self.prev_energies[i]

                    is_attack = attack > self.attack_threshold.value
                    is_sens = new_e[i] >= (current_peak * self.sensitivity.value)

                    if is_attack and is_sens:
                        # Normalize energy for the visualizer
                        norm_attack = max(0, min(1.0, (attack - self.attack_threshold.value) / 0.8))
                        triggered_notes.append({"index": i, "energy": norm_attack**2})
                self.prev_energies = new_e

        # 4. Update histories
        self.rms_history.append(self.receiver.rms)

        return triggered_notes

    def draw(self, screen: pygame.Surface, font: pygame.font.Font) -> None:
        """
        The fixed drawing template.
        Subclasses should NOT override this.
        """
        # 1. Call the subclass-specific drawing logic
        self.render_visualization(screen, font)

        # 2. Always draw the HUD last (guaranteed)
        # Assuming self.hud is your HUD instance
        context = {
            "rms_history": self.rms_history,
            "prev_energies": self.prev_energies,
            "old_energies": self.old_energies,
        }
        self.hud.draw(screen, font, audio_state=context)

    def render_visualization(self, screen: pygame.Surface, font: pygame.font.Font) -> None:
        """
        Hook for subclasses to implement their specific visuals.
        """
        raise NotImplementedError("Subclasses must implement render_visualization")
