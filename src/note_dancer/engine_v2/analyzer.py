import aubio
import librosa
import numpy as np
import scipy.ndimage
from scipy.signal import butter, sosfilt

from note_dancer.config import CHUNK, RATE, WINDOW_CHUNKS


class AudioAnalyzer:
    def __init__(self):
        # 1. Buffers & Memory
        self.audio_buffer = np.zeros(CHUNK * WINDOW_CHUNKS, dtype=np.float32)
        self.prev_percussive_mag = None
        self.flux_history = []
        self.history_limit = 20

        # 2. Parameters (Adjustable via CommandListener)
        self.params = {"low_gain": 10.0, "mid_gain": 10.0, "high_gain": 10.0, "flux_sens": 1.0}

        # 3. DSP Setup
        self.hop_length = CHUNK
        self.n_fft = CHUNK * 2

        # Filters (SOS for stability)
        self.low_sos = butter(4, 150, "lp", fs=RATE, output="sos")
        self.mid_sos = butter(4, [150, 4000], "bp", fs=RATE, output="sos")
        self.high_sos = butter(4, 4000, "hp", fs=RATE, output="sos")

        # Beat Tracker
        self.tempo_detector = aubio.tempo("default", self.n_fft, CHUNK, RATE)

    def update_parameter(self, key, value):
        if key in self.params:
            self.params[key] = value

    def _get_band_rms(self, samples, sos, gain_key):
        filtered = sosfilt(sos, samples)
        rms = np.sqrt(np.mean(filtered**2))
        return float(np.clip(rms * self.params[gain_key], 0, 1))

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
        results["low"] = self._get_band_rms(new_samples, self.low_sos, "low_gain")
        results["mid"] = self._get_band_rms(new_samples, self.mid_sos, "mid_gain")
        results["high"] = self._get_band_rms(new_samples, self.high_sos, "high_gain")

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

        # Clean Chroma
        chroma = librosa.feature.chroma_stft(S=harmonic_mag[:, -1:], sr=RATE, n_chroma=12, n_fft=self.n_fft)
        results["notes"] = chroma.flatten().tolist()

        return results
