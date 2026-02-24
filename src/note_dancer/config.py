import pyaudio

# --- Audio Stream Configuration ---
CHUNK = 1024
FORMAT = pyaudio.paFloat32
WINDOW_CHUNKS = 6

# Sample rate: 44100 Hz for generic audio, 48000 Hz for Behringer soundcard
RATE = 48000  # Change to 44100 if using generic audio input

# --- Network Configuration ---
UDP_IP = "127.0.0.1"  # Localhost; change if running visualizer on different machine
UDP_PORT_ENGINE = 5005  # Engine sends analysis data on this port
UDP_PORT_COMMANDS = 5006  # Frontend sends parameter updates on this port
