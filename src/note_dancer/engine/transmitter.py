import json
import socket

from note_dancer.config import UDP_IP, UDP_PORT
from note_dancer.engine.protocol import validate_message_or_raise


class NetworkTransmitter:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send_bpm(self, bpm):
        payload = {"bpm": float(bpm)}
        # validate and raise on contract mismatch
        validate_message_or_raise(payload)
        self.sock.sendto(json.dumps(payload).encode("utf-8"), (UDP_IP, UDP_PORT))

    def send_analysis(self, notes, brightness, rms):
        data_packet = {"notes": notes, "brightness": float(brightness), "rms": float(rms)}
        validate_message_or_raise(data_packet)
        self.sock.sendto(json.dumps(data_packet).encode("utf-8"), (UDP_IP, UDP_PORT))
