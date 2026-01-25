import pyaudio
import numpy as np
from scipy.signal import find_peaks

# --- Configuration ---
DEVICE_INDEX = None  # Try 7 first, then 8 if that fails, maybe use None
CHUNK = 8192
RATE = 44100
HPS_ORDER = 3
THRESHOLD = 0.05


def freq_to_note(freq):
    if freq < 20:
        return None
    midi_note = 12 * np.log2(freq / 440.0) + 69
    return int(round(midi_note))


def midi_to_name(n):
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    return f"{names[n % 12]}{n // 12 - 1}"


p = pyaudio.PyAudio()
stream = p.open(
    format=pyaudio.paInt16, channels=1, rate=RATE, input=True, input_device_index=DEVICE_INDEX, frames_per_buffer=CHUNK
)

print(f"* Listening on device {DEVICE_INDEX}. Play some music!")

try:
    while True:
        data = stream.read(CHUNK, exception_on_overflow=False)
        samples = np.frombuffer(data, dtype=np.int16).astype(np.float32)

        # --- VOLUME VISUALIZER ---
        volume_norm = np.linalg.norm(samples) / (CHUNK**0.5)
        v_meter = int(volume_norm / 50)  # Scale for terminal
        meter_display = "█" * v_meter + "-" * (30 - v_meter)

        # FFT and HPS
        windowed = samples * np.hanning(len(samples))
        fft_data = np.abs(np.fft.rfft(windowed))
        hps_data = np.copy(fft_data)

        for i in range(2, HPS_ORDER + 1):
            downsampled = fft_data[::i]
            hps_data[: len(downsampled)] *= downsampled

        hps_data /= np.max(hps_data) if np.max(hps_data) > 0 else 1
        freqs = np.fft.rfftfreq(len(samples), 1.0 / RATE)
        peaks, _ = find_peaks(hps_data, height=THRESHOLD, distance=20)

        current_notes = set()
        if volume_norm > 100:  # Only process if there is actual sound
            for p_idx in peaks:
                f = freqs[p_idx]
                if 30 < f < 3000:
                    note_val = freq_to_note(f)
                    if note_val:
                        current_notes.add(midi_to_name(note_val))

        notes_str = ", ".join(sorted(list(current_notes)))
        print(f"Vol: [{meter_display}] Notes: {notes_str}          ", end="\r")

except KeyboardInterrupt:
    print("\n* Stopped")
    stream.stop_stream()
    stream.close()
    p.terminate()
