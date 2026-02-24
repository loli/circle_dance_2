"""
Debug monitoring and performance tracking for the audio engine.

Tracks FPS, latency, audio health, feature quality, and system state,
printing summaries every 2 seconds and logging discrete events.
"""

import time
from collections import deque
from typing import Any

import numpy as np

from note_dancer.config import RATE


class DebugMonitor:
    """
    Real-time monitor for audio engine performance and audio quality.

    Prints a summary line every N seconds with the following metrics:
    - FPS: Frames per second (processing rate).
    - Latency: Average frame processing time in ms, with peak (Δ) in this window.
    - Input: Input signal level in dB (detect clipping or silence).
    - Silence: Percentage of frames below -40dB threshold.
    - Beats: Number of beat detections per second (sanity check against BPM).
    - Chroma: Maximum note energy in current frame, sparsity (% of quiet notes).
    - AGC: Automatic Gain Control reference peaks for Low/Mid/High bands
      (should be ~0.1-0.5; stuck values indicate tuning issues).
    - Cmds: Count of parameter updates received from frontend in this window.

    Discrete events (BEAT, CLIP, CMD) are logged when enable_event_logging=True.
    """

    def __init__(self, summary_interval: float = 2.0, enable_event_logging: bool = False):
        """
        Initializes the debug monitor.

        Args:
            summary_interval: Seconds between printing summary statistics.
            enable_event_logging: Whether to log discrete events (BEAT, CLIP, CMD, etc).
        """
        self.summary_interval = summary_interval
        self.enable_event_logging = enable_event_logging
        self.last_summary_time = time.time()
        self.current_bpm = 120.0

        # Performance tracking
        self.frame_times = deque(maxlen=256)  # Rolling buffer of frame times in ms
        self.frame_count = 0

        # Audio health
        self.input_rms_samples = deque(maxlen=128)
        self.silence_count = 0
        self.clip_count = 0
        self.total_frames = 0

        # Feature quality
        self.beat_count = 0
        self.max_chroma_energies = deque(maxlen=128)
        self.chroma_sparsity_samples = deque(maxlen=128)

        # Logging
        self.command_count = 0

    def update(
        self,
        frame_time_ms: float,
        process_results: dict[str, Any],
        raw_audio: np.ndarray,
        agc_low: float,
        agc_mid: float,
        agc_high: float,
    ) -> None:
        """
        Updates monitor with the results from one audio frame.

        Args:
            frame_time_ms: Time to process this frame in milliseconds.
            process_results: Dict returned from analyzer.process() (first element of tuple).
            raw_audio: Raw input samples for this frame.
            agc_low: AGC reference peak for low band.
            agc_mid: AGC reference peak for mid band.
            agc_high: AGC reference peak for high band.
        """
        self.frame_count += 1
        self.total_frames += 1
        self.current_bpm = process_results.get("bpm", 120.0)  # Store BPM for summary

        # Track frame time
        self.frame_times.append(frame_time_ms)

        # Audio health: input RMS
        input_rms = float(np.sqrt(np.mean(raw_audio**2)))
        self.input_rms_samples.append(input_rms)
        input_db = 20 * np.log10(max(input_rms, 1e-10))

        # Check for silence
        if input_db < -40:
            self.silence_count += 1

        # Check for clipping in output
        low_out = process_results.get("low", 0.0)
        mid_out = process_results.get("mid", 0.0)
        high_out = process_results.get("high", 0.0)
        if low_out > 0.99 or mid_out > 0.99 or high_out > 0.99:
            self.clip_count += 1
            self.log_event("CLIP", f"L:{low_out:.2f} M:{mid_out:.2f} H:{high_out:.2f}")

        # Feature quality: beats
        if process_results.get("is_beat", 0.0) > 0.5:
            self.beat_count += 1
            bpm = process_results.get("bpm", 0.0)
            self.log_event("BEAT", f"BPM {bpm:.1f}")

        # Feature quality: chroma
        notes = process_results.get("notes", [0.0] * 12)
        if notes:
            max_chroma = max(notes)
            self.max_chroma_energies.append(max_chroma)
            sparsity = sum(1 for n in notes if n < 0.1) / len(notes) * 100
            self.chroma_sparsity_samples.append(sparsity)

        # Print summary if interval elapsed
        if time.time() - self.last_summary_time >= self.summary_interval:
            self._print_summary(input_db, agc_low, agc_mid, agc_high)
            self.last_summary_time = time.time()

    def log_event(self, event_type: str, message: str) -> None:
        """
        Logs a discrete event (only if enabled).

        Args:
            event_type: Category of event (e.g., "BEAT", "CLIP", "SILENCE", "CMD").
            message: Event details.
        """
        if not self.enable_event_logging:
            return
        elapsed = time.time() - self.last_summary_time
        print(f"[{elapsed:05.1f}s] {event_type:8s} | {message}")

    def log_command(self, key: str, value: float) -> None:
        """Logs a parameter update command."""
        self.command_count += 1
        self.log_event("CMD", f"{key}={value}")

    def _print_summary(self, input_db: float, agc_low: float, agc_mid: float, agc_high: float) -> None:
        """Prints a summary of performance and audio metrics."""
        # Calculate elapsed time from start
        elapsed_total = time.time() - self.last_summary_time
        minutes = int(elapsed_total // 60)
        seconds = int(elapsed_total % 60)
        time_str = f"{minutes:02d}:{seconds:02d}"

        # Calculate FPS and latency stats
        if self.frame_times:
            fps = len(self.frame_times) / (sum(self.frame_times) / 1000.0)
            avg_latency = np.mean(self.frame_times)
            max_latency = np.max(self.frame_times)
        else:
            fps = 0.0
            avg_latency = 0.0
            max_latency = 0.0

        # Beat frequency with BPM
        beat_freq = self.beat_count / self.summary_interval if self.beat_count > 0 else 0.0

        # Chroma stats
        if self.max_chroma_energies:
            max_chroma = np.mean(self.max_chroma_energies)
        else:
            max_chroma = 0.0

        if self.chroma_sparsity_samples:
            avg_sparsity = np.mean(self.chroma_sparsity_samples)
        else:
            avg_sparsity = 0.0

        # Determine status
        status = "OK"
        if input_db > -3:
            status = "⚠ CLIP"
        elif input_db < -40:
            status = "⚠ SILENCE"

        # Format summary line to match proposed format
        summary = (
            f"[{time_str}] FPS: {fps:5.1f} | "
            f"Latency: {avg_latency:5.1f}ms (max {max_latency:5.1f}ms) | "
            f"Input: {input_db:6.1f}dB | "
            f"Beats: {beat_freq:4.1f}/s (BPM: {self.current_bpm:.0f}) | "
            f"Notes: max={max_chroma:.2f} sparse={avg_sparsity:5.1f}% | "
            f"AGC: L:{agc_low:.2f} M:{agc_mid:.2f} H:{agc_high:.2f} | "
            f"Cmds: {self.command_count} | "
            f"Status: {status}"
        )

        print(summary)

        # Reset counters for next interval
        self.frame_count = 0
        self.silence_count = 0
        self.clip_count = 0
        self.beat_count = 0
        self.command_count = 0
