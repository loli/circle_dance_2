import pyaudio
import numpy as np
import librosa
import socket
import json
import aubio

# --- Global Configuration ---
CHUNK = 1024
NFFT_CHUNK_MULTIPLIER = 2
RATE = 44100
UDP_IP = "127.0.0.1"
UDP_PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def run_engine():
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32, channels=1, rate=RATE, input=True, frames_per_buffer=CHUNK)
    tempo_detector = aubio.tempo("default", CHUNK * 2, CHUNK, RATE)

    print(f"Log-Scaled Engine running...")

    while True:
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            samples = np.frombuffer(data, dtype=np.float32)

            # 1. BPM DETECTION
            is_beat = tempo_detector(samples)
            if is_beat:
                current_bpm = tempo_detector.get_bpm()
                if current_bpm > 0:
                    bpm_packet = json.dumps({"bpm": float(current_bpm)}).encode("utf-8")
                    sock.sendto(bpm_packet, (UDP_IP, UDP_PORT))

            # 2. Get raw power without internal normalization
            chroma_raw = librosa.feature.chroma_stft(
                y=samples, sr=RATE, n_fft=CHUNK * NFFT_CHUNK_MULTIPLIER, hop_length=CHUNK + 1, norm=None
            )

            # 3. Convert to dB using a FIXED reference (1.0)
            # This prevents the 'always full' blue bar.
            # 1e-6 is a 'floor' to prevent math errors in total silence.
            chroma_db = librosa.power_to_db(chroma_raw, ref=1.0, top_db=80.0)

            # 4. Map to 0.0 - 1.0 range
            # We assume a noise floor of -60dB (silence) and a peak of 0dB (loud).
            # This makes the blue bar highly responsive to actual volume.
            energies = np.clip((np.mean(chroma_db, axis=1) + 60) / 60, 0, 1).tolist()

            # 3. SEND NOTE DATA
            packet = json.dumps(energies).encode("utf-8")
            sock.sendto(packet, (UDP_IP, UDP_PORT))

        except Exception as e:
            print(f"Error in Audio Engine: {e}")
            break

    stream.stop_stream()
    stream.close()
    p.terminate()


if __name__ == "__main__":
    run_engine()
