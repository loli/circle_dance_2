from note_dancer.config import UDP_PORT_COMMANDS, UDP_PORT_ENGINE

from .analyzer import AudioAnalyzer
from .command_listener import CommandListener
from .stream import AudioStream
from .transmitter import NetworkTransmitter


def run_engine():
    stream = AudioStream()
    analyzer = AudioAnalyzer()
    transmitter = NetworkTransmitter()

    # Start listening for parameter changes from the frontend
    command_listener = CommandListener(analyzer)

    print(f"Analyzer Active. Listening for commands on {UDP_PORT_COMMANDS}, Sending data on {UDP_PORT_ENGINE}.")

    try:
        while True:
            samples = stream.read()
            data = analyzer.process(samples)
            transmitter.send(data)
    except KeyboardInterrupt:
        print("Shutting down engine...")
    except Exception as e:
        raise e
    finally:
        stream.close()
        transmitter.close()
        command_listener.close()


if __name__ == "__main__":
    run_engine()
