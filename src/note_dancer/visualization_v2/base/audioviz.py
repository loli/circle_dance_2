import collections

import pygame

from note_dancer.visualization_v2.base.hud import HUD
from note_dancer.visualization_v2.base.parameters import (
    ChromaSensitivityParameter,
    Envelope,
    FluxImpactParameter,
    NumericParameter,
    SpectrumGainParameter,
)
from note_dancer.visualization_v2.base.receiver import AudioReceiver


class AudioVisualizationBase:
    def __init__(self) -> None:
        self.receiver = AudioReceiver()
        self.receiver.bind()
        self.hud = HUD()

        # --- 1. Audio Parameters (Gains & Thresholds) ---
        self.flux_thr = self.hud.register(FluxImpactParameter("Flux Thr", 1.0, 0.0, 10.0, 0.1, category="global"))
        self.low_gain = self.hud.register(SpectrumGainParameter("Low Gain", 10.0, 0.0, 100.0, 1.0, category="global"))
        self.mid_gain = self.hud.register(SpectrumGainParameter("Mid Gain", 10.0, 0.0, 100.0, 1.0, category="global"))
        self.high_gain = self.hud.register(
            SpectrumGainParameter("High Gain", 10.0, 0.0, 100.0, 1.0, category="global")
        )

        # --- 2. Per-Band Physics (Attack & Decay) ---
        # LOWS: Usually slow decay for "weight"
        # Create individual parameters (they get their own keys/sockets)
        self.low_atk = NumericParameter("Low Atk", 0.85, 0.01, 1.0, 0.05, category="hidden")
        self.low_dcy = NumericParameter("Low Dcy", 0.05, 0.01, 1.0, 0.01, category="hidden")
        self.hud.register(Envelope("Low", self.low_atk, self.low_dcy, category="physics"))  # Group them for the HUD

        # MIDS: Balanced
        self.mid_atk = NumericParameter("Mid Atk", 0.6, 0.01, 1.0, 0.05, category="hidden")
        self.mid_dcy = NumericParameter("Mid Dcy", 0.2, 0.01, 1.0, 0.02, category="hidden")
        self.hud.register(Envelope("Mid", self.mid_atk, self.mid_dcy, category="physics"))  # Group them for the HUD

        # HIGHS: Fast attack/decay for "snap"
        self.high_atk = NumericParameter("High Atk", 0.9, 0.01, 1.0, 0.05, category="hidden")
        self.high_dcy = NumericParameter("High Dcy", 0.4, 0.01, 1.0, 0.02, category="hidden")
        self.hud.register(Envelope("High", self.high_atk, self.high_dcy, category="physics"))  # Group them for the HUD

        self.note_sens = self.hud.register(
            ChromaSensitivityParameter("Note Sens", 0.7, 0.1, 0.95, 0.05, category="global")
        )

        # --- 3. State Management (Crucial for History & Smoothing) ---
        # History for the Flux Sparkline (200 frames)
        self.flux_history = collections.deque([0.0] * 200, maxlen=200)

        # Latest chroma note energies
        self.notes = [0.0] * 12

        # Storage for the most recent raw packet
        self.data = {}

        # Accumulators for the Triple-Band Smoothing
        self.smooth_low = 0.0
        self.smooth_mid = 0.0
        self.smooth_high = 0.0
        self.smooth_bpm = 120.0

    def _hedge_bpm(self, raw_bpm):
        """Force BPM into 90-180 range (The Hedging you requested)."""
        if raw_bpm <= 0:
            return 120.0
        temp_bpm = raw_bpm
        # Keep doubling until it hits the floor
        while temp_bpm < 90:
            temp_bpm *= 2
        # Keep halving until it hits the ceiling
        while temp_bpm > 180:
            temp_bpm /= 2
        return temp_bpm

    def handle_keys(self, key: int) -> None:
        self.hud.handle_input(key)

    def process_audio_frame(self):
        """
        Fetches raw data, hedges BPM, and applies per-band
        asymmetric smoothing (Attack/Decay).
        """
        packet = self.receiver.wait_for_packet()
        if not packet:
            return None

        # --- 1. Core State Update ---
        self.data = packet
        self.flux_history.append(packet["flux"])
        self.notes = packet["notes"]

        # --- 2. BPM Hedging & Smoothing ---
        # Forces BPM into 90-180 range and drifts the value smoothly
        target_bpm = self._hedge_bpm(packet["bpm"])
        self.smooth_bpm += (target_bpm - self.smooth_bpm) * 0.1

        # --- 3. Per-Band Asymmetric Smoothing ---
        def lerp_band(current, target, atk_param, dcy_param):
            # Choose alpha based on whether signal is rising (Attack) or falling (Decay)
            alpha = atk_param.value if target > current else dcy_param.value
            return current + (target - current) * alpha

        # Smooth each band using its specific HUD sliders
        self.smooth_low = lerp_band(self.smooth_low, packet["low"], self.low_atk, self.low_dcy)
        self.smooth_mid = lerp_band(self.smooth_mid, packet["mid"], self.mid_atk, self.mid_dcy)
        self.smooth_high = lerp_band(self.smooth_high, packet["high"], self.high_atk, self.high_dcy)

        # --- 4. Event Assembly ---
        peak_note = max(self.notes) if any(self.notes) else 1.0

        return {
            "beat": packet["is_beat"] > 0.5,
            "impact": packet["flux"] > self.flux_thr.value,
            "low": self.smooth_low,
            "mid": self.smooth_mid,
            "high": self.smooth_high,
            "bpm": self.smooth_bpm,
            "active_notes": [i for i, v in enumerate(self.notes) if v >= (peak_note * self.note_sens.value)],
        }

    def draw(self, screen: pygame.Surface, font: pygame.font.Font) -> None:
        """
        The Master Draw Method.
        Now feeds expanded data to the HUD for better visualizations.
        """
        # 1. Execute the 'Art' (Subclass logic)
        self.render_visualization(screen, font)

        # 2. Assemble the "Signal Chain" context for the HUD
        # This is what the parameters use to draw their mini-graphs
        context = {
            "flux_history": self.flux_history,
            "prev_energies": self.notes,
            # Smoothed Values
            "low": self.smooth_low,
            "mid": self.smooth_mid,
            "high": self.smooth_high,
            # Raw Hits (Added mid and high here)
            "raw_low": self.data.get("low", 0.0),
            "raw_mid": self.data.get("mid", 0.0),
            "raw_high": self.data.get("high", 0.0),
            "is_beat": self.data.get("is_beat", 0),
            "flux": self.data.get("flux", 0),
        }

        # 3. Draw the HUD (passes context to all parameters)
        self.hud.draw(screen, font, audio_state=context)

    def render_visualization(self, screen: pygame.Surface, font: pygame.font.Font) -> None:
        raise NotImplementedError("Subclasses must implement render_visualization")
