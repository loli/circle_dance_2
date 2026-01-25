import pyaudio
import numpy as np
import librosa
import socket
import json
import aubio

# --- Config ---
CHUNK = 1024  # Smaller chunk for better aubio accuracy
RATE = 44100
UDP_IP = "127.0.0.1"
UDP_PORT = 5005

# Setup Network
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def run_engine():
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32, channels=1, rate=RATE, input=True, frames_per_buffer=CHUNK)

    # Aubio Tempo Detection Setup
    # buf_size=CHUNK*2, hop_size=CHUNK
    tempo_detector = aubio.tempo("default", CHUNK * 2, CHUNK, RATE)

    print(f"Aubio Engine running. Auto-detecting BPM...")

    while True:
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            samples = np.frombuffer(data, dtype=np.float32)

            # 1. BPM / Beat Detection
            # is_beat is True if a click/kick is detected in this chunk
            is_beat = tempo_detector(samples)
            if is_beat:
                current_bpm = tempo_detector.get_bpm()
                if current_bpm > 0:
                    # Send BPM update to visualizer
                    bpm_packet = json.dumps({"bpm": float(current_bpm)}).encode("utf-8")
                    sock.sendto(bpm_packet, (UDP_IP, UDP_PORT))

            # 2. Chroma Note Detection
            # We use librosa for the chroma math as it's very robust
            chroma = librosa.feature.chroma_stft(y=samples, sr=RATE, n_fft=CHUNK * 2, hop_length=CHUNK + 1)
            energies = np.mean(chroma, axis=1).tolist()

            # 3. Send Note Data
            packet = json.dumps(energies).encode("utf-8")
            sock.sendto(packet, (UDP_IP, UDP_PORT))

        except Exception as e:
            print(f"Error: {e}")
            break


if __name__ == "__main__":
    run_engine()
