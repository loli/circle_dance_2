import pyaudio
import numpy as np
import librosa
import socket
import json
import aubio

# --- Configuration ---
CHUNK = 1024
RATE = 44100
# We will analyze 4 chunks at once (approx 93ms) for better frequency resolution
WINDOW_CHUNKS = 4
UDP_IP = "127.0.0.1"
UDP_PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def run_engine():
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32, channels=1, rate=RATE, input=True, frames_per_buffer=CHUNK)

    tempo_detector = aubio.tempo("default", CHUNK * 2, CHUNK, RATE)

    # Initialize a Ring Buffer to hold the last X chunks of audio
    audio_buffer = np.zeros(CHUNK * WINDOW_CHUNKS, dtype=np.float32)

    print(f"Stabilized Engine running. Analysis Window: {WINDOW_CHUNKS} chunks.")

    while True:
        try:
            # 1. Capture the newest chunk
            data = stream.read(CHUNK, exception_on_overflow=False)
            new_samples = np.frombuffer(data, dtype=np.float32)

            # 2. Update Ring Buffer (Shift old samples left, add new to right)
            audio_buffer = np.roll(audio_buffer, -CHUNK)
            audio_buffer[-CHUNK:] = new_samples

            # 3. Beat Detection (Perform on the sharpest/newest samples)
            is_beat = tempo_detector(new_samples)
            if is_beat:
                current_bpm = tempo_detector.get_bpm()
                if current_bpm > 0:
                    bpm_packet = json.dumps({"bpm": float(current_bpm)}).encode("utf-8")
                    sock.sendto(bpm_packet, (UDP_IP, UDP_PORT))

            # 4. Stabilized Chroma Detection
            # We use the full audio_buffer (4096 samples) for much better pitch accuracy.
            # We use a Hanning window to prevent "clicks" at the edges of the buffer.
            chroma = librosa.feature.chroma_stft(
                y=audio_buffer,
                sr=RATE,
                n_fft=CHUNK * 2,
                tuning=0.0,  # Lock tuning to A440 for stability
                hop_length=len(audio_buffer) + 1,  # Force a single column output
            )

            # Flatten and send
            energies = chroma.flatten().tolist()
            packet = json.dumps(energies).encode("utf-8")
            sock.sendto(packet, (UDP_IP, UDP_PORT))

        except Exception as e:
            print(f"Error: {e}")
            break

    stream.stop_stream()
    stream.close()
    p.terminate()


if __name__ == "__main__":
    run_engine()
