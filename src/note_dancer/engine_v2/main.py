from .analyzer import AudioAnalyzer
from .command_listener import CommandListener
from .stream import AudioStream
from .transmitter import NetworkTransmitter


def run_engine():
    stream = AudioStream()
    analyzer = AudioAnalyzer()
    transmitter = NetworkTransmitter()

    # Start listening for parameter changes from the frontend
    _ = CommandListener(analyzer)

    print("Analyzer Active. Listening for commands on 5006, Sending data on 5005.")

    try:
        while True:
            samples = stream.read()
            data = analyzer.process(samples)
            transmitter.send(data)
    except Exception:
        print("Error: Engine died.")
    finally:
        stream.close()


if __name__ == "__main__":
    run_engine()
