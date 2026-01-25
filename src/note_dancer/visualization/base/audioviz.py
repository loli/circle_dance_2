import pygame

from note_dancer.visualization.base.hud import BooleanParameter, NumericParameter
from note_dancer.visualization.base.receiver import AudioReceiver


class AudioVisualizationBase:
    """Base class for audio-reactive visualizations.

    Handles shared audio processing, parameter management, and event detection.
    """

    def __init__(self, hud):
        self.receiver = AudioReceiver()
        self.hud = hud

        # --- Shared Audio Parameters ---
        self.noise_floor = self.hud.register(
            NumericParameter("Noise Floor", -40.0, -60.0, 0.0, 1.0, category="global")
        )
        self.sensitivity = self.hud.register(NumericParameter("Sensitivity", 0.85, 0.1, 0.98, 0.02, category="global"))
        self.attack_threshold = self.hud.register(
            NumericParameter("Attack Thr", 0.18, 0.01, 1.0, 0.02, category="global")
        )
        self.beat_pulse_enabled = self.hud.register(BooleanParameter("Beat Pulse", True, category="global"))

        # --- Shared State ---
        self.bpm = 120.0
        self.rotation_speed = 2.0
        self.decay_rate = 1.0
        self.beat_boost = 0.0
        self.prev_energies = [0.0] * 12
        self.current_brightness = 0.0

    def handle_keys(self, key):
        """Routes key presses to the HUD."""
        self.hud.handle_input(key)

    def update_tempo(self, new_bpm: float):
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

    def process_audio_frame(self):
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

                for i in range(12):
                    attack = new_e[i] - self.prev_energies[i]

                    is_attack = attack > self.attack_threshold.value
                    is_sens = new_e[i] >= (current_peak * self.sensitivity.value)

                    if is_attack and is_sens:
                        # Normalize energy for the visualizer
                        norm_attack = max(0, min(1.0, (attack - self.attack_threshold.value) / 0.8))
                        triggered_notes.append({"index": i, "energy": norm_attack**2})
                self.prev_energies = new_e

        return triggered_notes
