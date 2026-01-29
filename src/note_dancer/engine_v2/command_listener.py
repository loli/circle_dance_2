import json
import socket
import threading


class CommandListener:
    def __init__(self, analyzer, port=5006):
        self.analyzer = analyzer
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", port))
        threading.Thread(target=self._listen, daemon=True).start()

    def _listen(self):
        while True:
            try:
                msg, _ = self.sock.recvfrom(1024)
                updates = json.loads(msg.decode())
                for k, v in updates.items():
                    self.analyzer.update_parameter(k, v)
            except Exception:
                pass
