import json
import socket
import threading

from note_dancer.config import UDP_IP, UDP_PORT_COMMANDS


class CommandListener:
    def __init__(self, analyzer, ip: str = UDP_IP, port: int = UDP_PORT_COMMANDS):
        self.analyzer = analyzer
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((ip, port))
        self.running = True
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()

    def _listen(self) -> None:
        """Listens for parameter updates from the frontend."""
        self.sock.settimeout(0.1)  # Allow thread to exit gracefully
        while self.running:
            try:
                msg, _ = self.sock.recvfrom(1024)
                updates = json.loads(msg.decode())
                for k, v in updates.items():
                    self.analyzer.update_parameter(k, v)
            except socket.timeout:
                continue
            except Exception:
                pass

    def close(self) -> None:
        """Stops the listener thread and closes the socket."""
        self.running = False
        self.sock.close()
