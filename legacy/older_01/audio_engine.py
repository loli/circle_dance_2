import pyaudio
import numpy as np
import librosa
import socket
import json

# --- Config ---
CHUNK = 4096
RATE = 44100
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
SMOOTHING = 0.25  # Lower is smoother, higher is more reactive
SENSITIVITY_THRESHOLD = 0.1  # Ignore anything quieter than this (0.0 to 1.0)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def run_engine():
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32, channels=1, rate=RATE, input=True, frames_per_buffer=CHUNK)

    # Initialize smoothed_energies with zeros
    smoothed_energies = np.zeros(12)

    current_peak = 1.0  # Tracks the max volume for auto-scaling

    print(f"Engine running (Smoothing: {SMOOTHING})...")

    while True:
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            samples = np.frombuffer(data, dtype=np.float32)

            # 1. Chroma calculation
            chroma = librosa.feature.chroma_stft(y=samples, sr=RATE, n_fft=CHUNK, hop_length=CHUNK + 1)
            raw_energies = np.mean(chroma, axis=1)

            # 2. Apply Noise Floor (Threshold)
            # If a note's energy is too low, kill it to prevent "ghost" bars
            raw_energies[raw_energies < SENSITIVITY_THRESHOLD] = 0

            # 3. Dynamic Peak Tracking
            # We track the loudest note to use as a reference ceiling
            max_in_frame = np.max(raw_energies)
            if max_in_frame > current_peak:
                current_peak = max_in_frame  # Move ceiling up immediately
            else:
                current_peak *= 0.99  # Slowly lower the ceiling to adapt to quieter songs

            # 4. Normalize & Smooth
            # Scale the energy so the loudest note is always 1.0
            normalized_energies = raw_energies / (current_peak + 1e-6)
            smoothed_energies = (smoothed_energies * (1 - SMOOTHING)) + (normalized_energies * SMOOTHING)

            # Package and send
            packet = json.dumps(smoothed_energies.tolist()).encode("utf-8")
            sock.sendto(packet, (UDP_IP, UDP_PORT))

        except Exception as e:
            print(f"Error: {e}")
            break


if __name__ == "__main__":
    run_engine()
