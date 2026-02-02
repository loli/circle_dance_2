from collections import deque

import aubio
import librosa
import numpy as np
import scipy.ndimage
from scipy.signal import butter, sosfilt

from note_dancer.config import CHUNK, RATE, WINDOW_CHUNKS

SILENCE_DB = -40.0  # dB level considered as silence


class AutoGain:
    def __init__(
        self,
        peak_percentile: int = 90,
        half_life_seconds: int = 15,
        attack_time_seconds: float = 0.1,
        history_seconds: int = 4,
    ):
        """Song loundness tracker for automatic gain control of note energies.

        Implements a percentile-based peak tracker that slowly decays over time, ensuring that note energies remain visually consistent regardless of overall volume changes.

        Args:
            peak_percentile: Percentile of recent frame-wise peaks to consider for the reference peak.
            half_life_seconds: Half life of the reference peak in seconds, aka how quickly it decays over time.
                For electronic music, a half-life of 10 to 20 seconds is usually the sweet spot.
                It's long enough to survive a standard 16-bar breakdown without the "ceiling" falling too low.
            attack_time_seconds: How quickly the reference peak rises to meet new peaks, in seconds.
                A shorter attack time means the ceiling responds more quickly to sudden volume increases.
                For electronic music, around 0.1 seconds is usually good, maybe even less.
            history_seconds: Seconds of recent frames to keep in history for percentile calculation.

        Example:
            >>> agc = AutoGain()
            >>> for frame in audio_frames:
            ...     chroma_raw = compute_chroma(frame)  # Get raw chroma energies
            ...     reference_peak = agc.update(chroma_raw)
            ...     normalized_energies = chroma_raw / reference_peak
        """
        # Engine / backend FPS, aka, the rate at which audio frames are processed.
        # Required to convert time-based parameters (seconds) into frame-based updates.
        # Engine FPS = RATE/CHUNK, e.g., 44100/1024 ~= 43 fps or 44100/512 = 86 fps.
        self.engine_fps = RATE / CHUNK

        # settings
        self.peak_percentile = peak_percentile
        self.peak_decay = 0.5 ** (1 / (half_life_seconds * self.engine_fps))
        self.attack_rate = min(1.0 / (attack_time_seconds * self.engine_fps), 1.0)
        self.peak_floor = 0.01  # Minimum value for the reference peak to avoid division by zero or very small number

        # trackers
        self.song_reference_peak = (
            0.1  # The "Ceiling" that follows the song's volume, used to normalize the note energies
        )
        self.peak_history = deque(maxlen=int(history_seconds * self.engine_fps))

        # init history
        self.peak_history.append(self.peak_floor)

    def update(self, chroma_raw) -> float:
        """Updates the song reference peak based on the current frame's chroma energies.

        Args:
            chroma_raw: The raw chroma energies for the current audio frame.
        Returns:
            The updated song reference peak.
        """
        # 1. Add the stronges peak of the new frame to the history
        self.peak_history.append(np.max(chroma_raw))

        # 2. Compute the target peak based on the desired percentile of recent peaks
        target_peak = float(np.percentile(self.peak_history, self.peak_percentile))
        target_peak = max(target_peak, self.peak_floor)  # safeguard

        # 3. Update the Song Reference Peak (AGC)
        # The ceiling either jumps up to meet a new peak or drifts down slowly
        if target_peak > self.song_reference_peak:
            # Attack: closes a fraction of the gap every frame.
            self.song_reference_peak += (target_peak - self.song_reference_peak) * self.attack_rate
        else:
            self.song_reference_peak *= self.peak_decay
            # Ensure it doesn't hit zero
            self.song_reference_peak = max(self.song_reference_peak, self.peak_floor)

        return self.song_reference_peak


class AudioAnalyzer:
    def __init__(self):
        # Buffers & Memory
        self.audio_buffer = np.zeros(CHUNK * WINDOW_CHUNKS, dtype=np.float32)
        self.prev_percussive_mag = None
        self.flux_history = []
        self.history_limit = 20

        # Parameters (Adjustable via CommandListener)
        self.params = {
            "low_gain": 0.8,
            "mid_gain": 0.8,
            "high_gain": 0.8,
            "flux_sens": 1.0,
            "norm_mode": "statistical",
        }

        # DSP Setup
        self.hop_length = CHUNK
        self.n_fft = CHUNK * 2

        # Filters (SOS for stability)
        self.low_sos = butter(4, 150, "lp", fs=RATE, output="sos")
        self.mid_sos = butter(4, [150, 4000], "bp", fs=RATE, output="sos")
        self.high_sos = butter(4, 4000, "hp", fs=RATE, output="sos")

        # Beat Tracker
        self.tempo_detector = aubio.tempo("default", self.n_fft, CHUNK, RATE)

        # Auto gain trackers (one per band, and one for note energies)
        self.note_agc = AutoGain(peak_percentile=90, half_life_seconds=15)
        self.low_agc = AutoGain(peak_percentile=95, half_life_seconds=10)  # Bass is more spikey, use higher percentile
        self.mid_agc = AutoGain(peak_percentile=90, half_life_seconds=15)
        self.high_agc = AutoGain(peak_percentile=90, half_life_seconds=15)

        # Note detection & normalization trackers
        self.spotlight_peak = 0.01

    def update_parameter(self, key, value):
        if key in self.params:
            self.params[key] = value

    def _get_raw_band_rms(self, samples, sos):
        """
        Calculates the raw Root Mean Square (RMS) energy of a filtered signal.

        Returns the absolute energy level before any gain or normalization is applied.
        This raw value is ideal for feeding into the AutoGain tracker.
        """

        filtered = sosfilt(sos, samples)  # Apply the Second-Order Sections (SOS) filter

        rms = np.sqrt(
            np.mean(filtered**2)
        )  # Calculate the RMS: Square the samples, find the mean, then take the square root

        # Return as a float. We use a tiny epsilon to avoid absolute zero if needed,
        # though the AutoGain floor usually handles this.
        return float(rms)

    def _get_hpss(self, stft_magnitude):
        # Fixed kernel size 31 as agreed for stability
        harmonic_mag = scipy.ndimage.median_filter(stft_magnitude, size=(1, 31))
        percussive_mag = scipy.ndimage.median_filter(stft_magnitude, size=(31, 1))
        return harmonic_mag, percussive_mag

    def process(self, new_samples):
        results = {}

        # 1. Beat Detection (Low Latency)
        is_beat = self.tempo_detector(new_samples)
        results["is_beat"] = 1.0 if is_beat else 0.0
        results["bpm"] = float(self.tempo_detector.get_bpm())

        # 2. Update Buffer
        self.audio_buffer = np.roll(self.audio_buffer, -CHUNK)
        self.audio_buffer[-CHUNK:] = new_samples

        # 3. Spectral Decomposition
        stft = librosa.stft(self.audio_buffer, n_fft=self.n_fft, hop_length=self.hop_length, center=False)
        stft_mag = np.abs(stft)
        harmonic_mag, percussive_mag = self._get_hpss(stft_mag)

        # 4. Feature Extraction
        # 4.1. Get raw RMS for each band (no clipping yet)
        raw_low = self._get_raw_band_rms(new_samples, self.low_sos)
        raw_mid = self._get_raw_band_rms(new_samples, self.mid_sos)
        raw_high = self._get_raw_band_rms(new_samples, self.high_sos)

        # 4.2. Update the trackers with the new raw values
        # We pass the value in a list [raw_low] because your .update() expects a chroma-like array
        ref_low = self.low_agc.update([raw_low])
        ref_mid = self.mid_agc.update([raw_mid])
        ref_high = self.high_agc.update([raw_high])

        # 4.3. Apply the User-Controlled Gain from the Frontend and compute final normalized values
        # The AutoGain provides the "Base" (raw_low / ref_low)
        # The User provides the "Impact" (low_gain)
        eps = 1e-6
        results["low"] = float(np.clip((raw_low / (ref_low + eps)) * self.params["low_gain"], 0, 1))
        results["mid"] = float(np.clip((raw_mid / (ref_mid + eps)) * self.params["mid_gain"], 0, 1))
        results["high"] = float(np.clip((raw_high / (ref_high + eps)) * self.params["high_gain"], 0, 1))

        # Brightness (Spectral Centroid)
        centroid = librosa.feature.spectral_centroid(S=stft_mag[:, -1:], sr=RATE)[0, 0]
        results["brightness"] = float(np.clip(centroid / 11000.0, 0, 1))

        # Flux (Transients)
        current_percussive = percussive_mag[:, -1]
        if self.prev_percussive_mag is not None:
            flux = np.sum(np.maximum(0, current_percussive - self.prev_percussive_mag))
            self.flux_history.append(flux)
            if len(self.flux_history) > self.history_limit:
                self.flux_history.pop(0)
            avg_flux = np.mean(self.flux_history) if self.flux_history else 1.0
            results["flux"] = float((flux / (avg_flux + 1e-9)) * self.params["flux_sens"])
        else:
            results["flux"] = 0.0
        self.prev_percussive_mag = current_percussive

        # Compute note energies (Chroma)
        chroma_raw = librosa.feature.chroma_stft(S=harmonic_mag[:, -1:], sr=RATE, n_chroma=12, norm=None).flatten()

        silence_linear = 10 ** (SILENCE_DB / 20)  # Apply absolute threshold to remove silence
        chroma_clean = np.where(chroma_raw < silence_linear, 0.0, chroma_raw)

        if self.params["norm_mode"] == "fixed":
            results["notes"] = self._note_norm_fixed_gauge(chroma_clean)
        elif self.params["norm_mode"] == "competitive":
            results["notes"] = self._note_norm_competitive_spotlight(chroma_clean)
        else:  # norm_mode = statistical
            results["notes"] = self._note_norm_global_statistical(chroma_clean)

        return results

    def _note_norm_fixed_gauge(self, chroma_clean) -> list[float]:
        """Fixed-Scale Decibel Mapping.

        This variant treats your visualizer like a physical VU meter. It ignores the "history" of the song and maps raw
        audio energy directly to a fixed visual range based on human hearing thresholds.

        The Logic: It converts raw energy into Decibels (dB) and fits them into a "Sober" window (e.g., -45dB to -10dB).

        The Feel: Authentic and Dynamic. If the music gets quiet, the orbs get small. If the DJ cuts the fader, the
        visualization dies. It preserves the "intent" of the mix rather than trying to fix it.

        Effect:
            - -40dB signal -> ( -40 - (-40) ) / 30 = 0.0 -> Energy 0.0
            - -25dB signal -> ( -25 - (-40) ) / 30 = 0.5 -> Energy 0.5
            - -3dB signal -> ( -3 - (-40) ) / 30 = 1.0 -> Energy 1.0
        """
        # N = CHUNK * WINDOW_CHUNKS (1024 * 6 = 6144)
        # The max magnitude of a real FFT is N/2
        FFT_REF = 3072.0

        # Convert to Decibels relative to Full Scale (dBFS) ---
        eps = 1e-9
        chroma_db = 20 * np.log10((chroma_clean / FFT_REF) + eps)

        # Define Human-Audible Boundaries (Club Setting) ---
        # -40dB to -45dB: The "Floor". Below this is silence/noise.
        # -20dB to -5dB: The "Ceiling". This is where a mastered track peaks. Above this is likely clipping/distortion.
        db_min = -60.0
        db_max = -12.0

        # Fixed note energy normalization
        notes_normalized = (chroma_db - db_min) / (db_max - db_min)

        # Scaling
        notes_final = np.clip(notes_normalized, 0, 1)

        return notes_final.tolist()

    def _note_norm_competitive_spotlight(self, chroma_clean) -> list[float]:
        """Competitive Spotlight Normalization.

        This variant normalizes note energies based on the strongest notes in the current frame.
        It creates a "spotlight" effect where only the most prominent notes are highlighted.

        The Logic: It identifies the top N notes in the current frame and scales their energies
        relative to the strongest note. Other notes are diminished.

        The Feel: Dynamic and Focused. The visualization emphasizes the most important musical elements,
        making it ideal for complex mixes where certain notes should stand out.

        Effect:
            - Strongest note -> Energy 1.0
            - Other top N notes -> Scaled between 0.0 and 1.0
            - Remaining notes -> Energy 0.0
        """
        # 1. Find the loudest note in the current frame
        current_max = np.max(chroma_clean)

        # 2. Update the local peak follower (Temporal Inertia)
        # We want a very fast decay (e.g., 0.8) so it stays "per-frame",
        # but slow enough to stop the 60fps micro-jitter.
        if current_max > self.spotlight_peak:
            # Instant attack: jump to the new winner
            self.spotlight_peak = current_max
        else:
            # Fast decay: allow the 'ceiling' to drop quickly for the next note
            self.spotlight_peak *= 0.85

        # Apply a safety floor to avoid division by zero
        self.spotlight_peak = max(self.spotlight_peak, 1e-6)

        # 3. Competitive Normalization
        # Every note is scaled relative to the 'smoothed' frame winner
        notes_normalized = chroma_clean / self.spotlight_peak

        # 4. Sharpen the contrast
        # Squaring is essential here; otherwise, the 'losers' (background harmonics)
        # will be too large and clutter the screen.
        notes_final = np.power(np.clip(notes_normalized, 0, 1), 2)

        return notes_final.tolist()

    def _note_norm_global_statistical(self, chroma_clean) -> list[float]:
        """Global Statistical Normalization

        This variant is the "intelligent" approach. It uses the long-term history of the song to create a stable,
        human-centric visual scale that adapts to the overall loudness of the set.

        The Logic: It tracks a "statistical ceiling" (90th percentile) using a 15-second half-life. It calculates the
        decibel distance from this ceiling, mapping the relative energy into a logarithmic 0.0–1.0 range.

        The Feel: Balanced and Professional. It preserves the "sober" philosophy by keeping note sizes consistent across
        different tracks. Because it uses a logarithmic scale, it reveals the "harmonic dust" and delicate textures of
        the music without letting them overpower the main melody.

        The Nuance: To combat spectral leakage (smear) and clutter, it relies on Local Maxima filtering and Color
        Smoothing. By using adjacent colors for adjacent frequency bins, the "smear" feels like a natural glow or aura
        around the primary note rather than a separate, distracting orb.
        """
        # 0. Optional (still to figure out): Apply Local Maxima Filtering to reduce spectral smear
        # chroma_clean = self._apply_local_maxima(chroma_clean)  # doesn't look good

        # 1. Update the long-term reference peak (the "Ceiling")
        # This ensures the visualizer adapts to the overall volume of the track.
        self.song_reference_peak = self.note_agc.update(chroma_clean)

        # 2. Calculate Logarithmic "Distance from Ceiling"
        # We use log10 to mimic human hearing (perceptual loudness).
        # eps prevents log(0) and aligns with a -60dB noise floor.
        eps = 1e-6
        relative_energy = (chroma_clean + eps) / self.song_reference_peak

        # 3. Logarithmic Mapping (The Contrast Step)
        # We use a 1.5 range (approx -30dB).
        # Anything quieter than 3% of the song's reference peak becomes 0.0.
        log_energy = np.log10(relative_energy)
        notes_normalized = (log_energy + 1.5) / 1.5

        # 4. Final Clip
        # Note: Squaring (np.power) is omitted here and moved to the frontend
        # per your instruction to allow for real-time contrast control.
        notes_final = np.power(np.clip(notes_normalized, 0, 1), 4)

        return notes_final.tolist()

    def _apply_local_maxima(self, chroma):
        """Zeroes out any chroma bins that are not local peaks.

        This effectively 'de-clutters' the visualization by removing
        spectral leakage into adjacent notes.
        """
        # Roll the array to compare with neighbors (circular/wrapped)
        left = np.roll(chroma, 1)
        right = np.roll(chroma, -1)

        # Keep value only if it is strictly greater than its neighbors
        # Otherwise, it's just "harmonic smear"
        mask = (chroma > left) & (chroma > right)

        return np.where(mask, chroma, 0.0)
