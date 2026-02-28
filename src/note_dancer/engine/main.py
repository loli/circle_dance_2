import time

from note_dancer.config import UDP_PORT_COMMANDS, UDP_PORT_ENGINE

from .analyzer import AudioAnalyzer
from .command_listener import CommandListener
from .debug_monitor import DebugMonitor
from .stream import AudioStream
from .transmitter import NetworkTransmitter


def run_engine():
    stream = AudioStream()
    analyzer = AudioAnalyzer()
    transmitter = NetworkTransmitter()
    monitor = DebugMonitor(summary_interval=2.0)

    # Start listening for parameter changes from the frontend
    command_listener = CommandListener(analyzer, monitor=monitor)

    print(f"Analyzer Active. Listening for commands on {UDP_PORT_COMMANDS}, Sending data on {UDP_PORT_ENGINE}.")

    try:
        while True:
            samples = stream.read()

            # Time the processing
            t_start = time.time()
            data, debug_info = analyzer.process(samples)
            frame_time_ms = (time.time() - t_start) * 1000.0

            # Monitor performance
            monitor.update(
                frame_time_ms,
                data,
                samples,
                debug_info["agc_low"],
                debug_info["agc_mid"],
                debug_info["agc_high"],
            )

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
