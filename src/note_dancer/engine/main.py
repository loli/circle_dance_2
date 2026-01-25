from .stream import AudioStream
from .analyzer import AudioAnalyzer
from .transmitter import NetworkTransmitter


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
                transmitter.send_analysis(data["notes"], data["brightness"], data["rms"])

        except Exception as e:
            print(f"Error: {e}")
            break

    stream.close()


if __name__ == "__main__":
    run_engine()
