import socket
import struct

from note_dancer.config import UDP_IP, UDP_PORT_ENGINE


class NetworkTransmitter:
    def __init__(self, ip: str = UDP_IP, port: int = UDP_PORT_ENGINE):
        self.dest = (ip, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.fmt = "!19f"  # 7 control floats + 12 chroma floats

    def send(self, data):
        try:
            payload = struct.pack(
                self.fmt,
                data["brightness"],
                data["flux"],
                data["low"],
                data["mid"],
                data["high"],
                data["bpm"],
                data["is_beat"],
                *data["notes"],
            )
            self.sock.sendto(payload, self.dest)
        except Exception as e:
            print(f"Send Error: {e}")

    def close(self) -> None:
        """Closes the UDP socket."""
        self.sock.close()
