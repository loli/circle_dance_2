import pyaudio
import numpy as np
import librosa
import socket
import json
import aubio

# --- Configuration ---
CHUNK = 1024
RATE = 44100
WINDOW_CHUNKS = 6  # Increased window for CQT stability
UDP_IP = "127.0.0.1"
UDP_PORT = 5005


class AudioStream:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )

    def read(self):
        data = self.stream.read(CHUNK, exception_on_overflow=False)
        return np.frombuffer(data, dtype=np.float32)

    def close(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()


class NetworkTransmitter:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send_bpm(self, bpm):
        self.sock.sendto(json.dumps({"bpm": float(bpm)}).encode("utf-8"), (UDP_IP, UDP_PORT))

    def send_analysis(self, notes, brightness):
        data_packet = {"notes": notes, "brightness": brightness}
        self.sock.sendto(json.dumps(data_packet).encode("utf-8"), (UDP_IP, UDP_PORT))


class AudioAnalyzer:
    def __init__(self):
        self.tempo_detector = aubio.tempo("default", CHUNK * 2, CHUNK, RATE)
        self.audio_buffer = np.zeros(CHUNK * WINDOW_CHUNKS, dtype=np.float32)
        print(f"CQT Engine running. Bins per octave: 12. Resolution: High-Bass.")

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
        chroma = librosa.feature.chroma_cqt(C=np.abs(cqt), n_chroma=12)
        results["notes"] = chroma.flatten().tolist()

        # 3. Spectral Centroid
        centroid = librosa.feature.spectral_centroid(y=self.audio_buffer, sr=RATE)[0, -1]
        results["brightness"] = float(np.clip(centroid / 11000.0, 0, 1))

        return results


def run_engine():
    stream = AudioStream()
    analyzer = AudioAnalyzer()
    transmitter = NetworkTransmitter()

    while True:
        try:
            samples = stream.read()
            data = analyzer.process(samples)

            if "bpm" in data:
                transmitter.send_bpm(data["bpm"])

            if "notes" in data:
                transmitter.send_analysis(data["notes"], data["brightness"])

        except Exception as e:
            print(f"Error: {e}")
            break

    stream.close()


if __name__ == "__main__":
    run_engine()
