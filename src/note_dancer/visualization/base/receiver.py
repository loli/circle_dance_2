import socket
import json
from note_dancer.config import UDP_IP, UDP_PORT
from note_dancer.protocol import validate_message_or_raise, NOTES_LEN


class AudioReceiver:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((UDP_IP, UDP_PORT))
        self.sock.setblocking(False)

        # The "Database" - Source of Truth
        self.bpm = 120.0
        self.notes = [0.0] * NOTES_LEN
        self.brightness = 0.0
        self.rms = -100.00  # in decibels, silence by default

        # Event Flags
        self.beat_detected = False
        self.notes_updated = False

    def update(self):
        self.beat_detected = False
        self.notes_updated = False
        try:
            while True:
                data, _ = self.sock.recvfrom(2048)
                decoded = json.loads(data.decode("utf-8"))

                # validate (raises on violation so caller becomes aware of protocol mismatch)
                validate_message_or_raise(decoded)

                if "bpm" in decoded:
                    self.bpm = float(decoded["bpm"])
                    self.beat_detected = True
                if "notes" in decoded:
                    self.notes = [float(n) for n in decoded["notes"]]
                    self.brightness = float(decoded.get("brightness", 0.0))  # don't like defaults here; I think, when notes, then this should always be there
                    self.rms = float(decoded.get("rms", -100.0))  # don't like defaults here; I think, when notes, then this should always be there
                    self.notes_updated = True

        except (BlockingIOError, json.JSONDecodeError):
            pass
