import pyaudio
import numpy as np
import librosa
import socket
import json
import aubio

# --- Global Configuration ---
# CHUNK: The number of audio frames processed at once. 1024 at 44.1kHz is ~23ms.
# Lower values reduce latency but increase CPU load and can jitter.
CHUNK = 1024
RATE = 44100
UDP_IP = "127.0.0.1"
UDP_PORT = 5005

# Setup Network: Using UDP (User Datagram Protocol) for speed.
# We prefer speed over reliability here; if a packet is lost, we just wait for the next one.
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def run_engine():
    # Initialize PyAudio: Interface for the computer's microphone/soundcard
    p = pyaudio.PyAudio()

    # Open Stream:
    # format=paFloat32 is required for both Aubio and Librosa calculations.
    stream = p.open(format=pyaudio.paFloat32, channels=1, rate=RATE, input=True, frames_per_buffer=CHUNK)

    # Aubio Tempo Detection Setup:
    # "default" uses the complex-domain onset detection method.
    # buf_size (CHUNK*2): The window size for the Fast Fourier Transform (FFT).
    # hop_size (CHUNK): The number of new samples to read before re-calculating.
    tempo_detector = aubio.tempo("default", CHUNK * 2, CHUNK, RATE)

    print(f"Aubio Engine running. Auto-detecting BPM...")

    while True:
        try:
            # Read raw bytes from the microphone and convert to a Float32 Numpy array
            data = stream.read(CHUNK, exception_on_overflow=False)
            samples = np.frombuffer(data, dtype=np.float32)

            # 1. BPM / BEAT DETECTION (Temporal Analysis)
            # tempo_detector(samples) returns True if a rhythmic transient (beat)
            # is detected within the current CHUNK of audio.
            is_beat = tempo_detector(samples)

            if is_beat:
                # get_bpm() calculates a rolling average of the tempo
                current_bpm = tempo_detector.get_bpm()
                if current_bpm > 0:
                    # Pack the BPM into a dictionary so the visualizer can
                    # distinguish it from note energy lists.
                    bpm_packet = json.dumps({"bpm": float(current_bpm)}).encode("utf-8")
                    sock.sendto(bpm_packet, (UDP_IP, UDP_PORT))

            # 2. CHROMA NOTE DETECTION (Spectral Analysis)
            # librosa.feature.chroma_stft:
            # Maps the 1024-bin FFT result into 12 bins representing the musical
            # semitones (C, C#, D, etc.). This is known as "Pitch Class Profiling."
            # n_fft=CHUNK*2 provides a slightly higher frequency resolution.
            chroma = librosa.feature.chroma_stft(y=samples, sr=RATE, n_fft=CHUNK * 2, hop_length=CHUNK + 1)

            # chroma returns a 2D array; we take the mean across the short time
            # axis to get a single 12-element list of energies.
            energies = np.mean(chroma, axis=1).tolist()

            # 3. SEND NOTE DATA
            # Send the raw list of 12 note energies.
            # The visualizer will handle the "Attack" filtering and normalization.
            packet = json.dumps(energies).encode("utf-8")
            sock.sendto(packet, (UDP_IP, UDP_PORT))

        except Exception as e:
            print(f"Error in Audio Engine: {e}")
            break

    # Cleanup
    stream.stop_stream()
    stream.close()
    p.terminate()


if __name__ == "__main__":
    run_engine()
