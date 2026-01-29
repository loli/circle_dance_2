import socket
import struct


class AudioReceiver:
    def __init__(self, ip="127.0.0.1", port=5005):
        """
        Initializes the UDP receiver for the AudioAnalyzer data.
        The packet format is !19f (76 bytes).
        """
        self.ip = ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Format: 7 control floats + 12 chroma floats
        self.packet_format = "!19f"
        self.packet_size = struct.calcsize(self.packet_format)

        # Internal state to hold the latest data
        self.latest_data = {}
        self._is_bound = False

    def bind(self):
        """Binds the socket to the address. Call this once before receiving."""
        try:
            self.sock.bind((self.ip, self.port))
            self._is_bound = True
            print(f"Receiver bound to {self.ip}:{self.port}")
        except Exception as e:
            print(f"Error binding socket: {e}")

    def wait_for_packet(self):
        """
        Blocks until a packet is received, unpacks it, and updates internal state.
        Returns the data dictionary.
        """
        if not self._is_bound:
            self.bind()

        data, _ = self.sock.recvfrom(self.packet_size)

        if len(data) != self.packet_size:
            return None

        unpacked = struct.unpack(self.packet_format, data)

        # Map indices to keys
        self.latest_data = {
            "brightness": unpacked[0],
            "flux": unpacked[1],
            "low": unpacked[2],
            "mid": unpacked[3],
            "high": unpacked[4],
            "bpm": unpacked[5],
            "is_beat": unpacked[6],
            "notes": list(unpacked[7:]),  # 12 chroma values
        }

        return self.latest_data

    def close(self):
        """Closes the socket."""
        self.sock.close()


# --- Example Usage ---
if __name__ == "__main__":
    receiver = AudioReceiver()
    try:
        while True:
            data = receiver.wait_for_packet()
            if data:
                # Example: Accessing specific values
                if data["is_beat"]:
                    print(f">> BEAT! BPM: {data['bpm']:.1f}")
                else:
                    print(f"Flux: {data['flux']:.2f}", end="\r")
    except KeyboardInterrupt:
        receiver.close()
