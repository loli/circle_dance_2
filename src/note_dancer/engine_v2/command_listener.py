import json
import socket
import threading


class CommandListener:
    def __init__(self, analyzer, port=5006):
        self.analyzer = analyzer
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", port))
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
