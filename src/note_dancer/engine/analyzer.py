import numpy as np
import librosa
import aubio
from note_dancer.config import CHUNK, RATE, WINDOW_CHUNKS


class AudioAnalyzer:
    def __init__(self):
        self.tempo_detector = aubio.tempo("default", CHUNK * 2, CHUNK, RATE)
        self.audio_buffer = np.zeros(CHUNK * WINDOW_CHUNKS, dtype=np.float32)

    def process(self, new_samples):
        self.audio_buffer = np.roll(self.audio_buffer, -CHUNK)
        self.audio_buffer[-CHUNK:] = new_samples

        results = {}

        # 1. Beat Detection
        is_beat = self.tempo_detector(new_samples)
        if is_beat:
            current_bpm = self.tempo_detector.get_bpm()
            if current_bpm > 0:
                results["bpm"] = current_bpm

        # 2. CQT Chroma Analysis
        cqt = librosa.cqt(
            self.audio_buffer,
            sr=RATE,
            hop_length=len(self.audio_buffer) + 1,
            fmin=librosa.note_to_hz("C1"),
            n_bins=36,
            bins_per_octave=12,
        )
        chroma = librosa.feature.chroma_cqt(C=np.abs(cqt), n_chroma=12)  # Note: if too slow, librosa.feature.chroma_stft might be better
        results["notes"] = chroma.flatten().tolist()

        # 3. Spectral Centroid
        centroid = librosa.feature.spectral_centroid(y=self.audio_buffer, sr=RATE)[0, -1]
        results["brightness"] = float(np.clip(centroid / 11000.0, 0, 1))

        # 4. RMS (Volume) converted to Decibels
        rms_linear = np.sqrt(np.mean(new_samples**2))
        rms_db = 20 * np.log10(max(rms_linear, 1e-9))
        results["rms"] = float(rms_db)

        return results
