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

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def run_engine():
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paFloat32, channels=1, rate=RATE, input=True, frames_per_buffer=CHUNK)

    tempo_detector = aubio.tempo("default", CHUNK * 2, CHUNK, RATE)
    audio_buffer = np.zeros(CHUNK * WINDOW_CHUNKS, dtype=np.float32)

    print(f"CQT Engine running. Bins per octave: 12. Resolution: High-Bass.")

    while True:
        try:
            data = stream.read(CHUNK, exception_on_overflow=False)
            new_samples = np.frombuffer(data, dtype=np.float32)

            audio_buffer = np.roll(audio_buffer, -CHUNK)
            audio_buffer[-CHUNK:] = new_samples

            # 1. Beat Detection
            is_beat = tempo_detector(new_samples)
            if is_beat:
                current_bpm = tempo_detector.get_bpm()
                if current_bpm > 0:
                    sock.sendto(json.dumps({"bpm": float(current_bpm)}).encode("utf-8"), (UDP_IP, UDP_PORT))

            # 2. CQT Chroma Analysis
            # CQT is much better for bass notes in EDM.
            # fmin=librosa.note_to_hz('C1') ensures we capture the sub-bass.
            cqt = librosa.cqt(
                audio_buffer,
                sr=RATE,
                hop_length=len(audio_buffer) + 1,
                fmin=librosa.note_to_hz("C1"),
                n_bins=36,  # 3 octaves
                bins_per_octave=12,
            )

            # Convert CQT to Chroma (12 bins)
            chroma = librosa.feature.chroma_cqt(C=np.abs(cqt), n_chroma=12)
            energies = chroma.flatten().tolist()

            # 1. Calculate Spectral Centroid (Brightness)
            # Centroid returns values in Hertz. Low = 500Hz (Bass), High = 8000Hz+ (Crispy/Noisy)
            centroid = librosa.feature.spectral_centroid(y=audio_buffer, sr=RATE)[0, -1]

            # 2. Normalize it for the visualizer (0.0 to 1.0 range)
            # We assume 0Hz to 11000Hz range for music.
            norm_brightness = float(np.clip(centroid / 11000.0, 0, 1))

            # 1. Perform Harmonic-Percussive Source Separation
            # This splits the buffer into two distinct waveforms
            y_harmonic, y_percussive = librosa.effects.hpss(audio_buffer)

            # 2. Analyze Synths/Melody (from the Harmonic part)
            cqt_h = librosa.cqt(
                y_harmonic,
                sr=RATE,
                hop_length=len(audio_buffer) + 1,
                fmin=librosa.note_to_hz("C1"),
                n_bins=36,
                bins_per_octave=12,
            )
            chroma_h = librosa.feature.chroma_cqt(C=np.abs(cqt_h), n_chroma=12)
            harmonic_energies = chroma_h.flatten().tolist()

            # 3. Analyze Drums/Transients (from the Percussive part)
            # We just need the "strength" of the percussion in this chunk
            percussive_energy = float(np.mean(librosa.feature.rms(y=y_percussive)))

            # 4. Brightness (Centroid) stays on the full mix for context
            centroid = librosa.feature.spectral_centroid(y=audio_buffer, sr=RATE)[0, -1]
            norm_brightness = float(np.clip(centroid / 11000.0, 0, 1))

            # 5. Updated Data Packet
            data_packet = {"notes": harmonic_energies, "percussion": percussive_energy, "brightness": norm_brightness}

            # We send a dict so the visualizer can easily distinguish data types
            sock.sendto(json.dumps(data_packet).encode("utf-8"), (UDP_IP, UDP_PORT))

        except Exception as e:
            print(f"Error: {e}")
            break

    stream.stop_stream()
    stream.close()
    p.terminate()


if __name__ == "__main__":
    run_engine()
