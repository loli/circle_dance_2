import errno
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

        self.sock.setblocking(False)

        # Format: 7 control floats + 12 chroma floats
        self.packet_format = "!19f"
        self.packet_size = struct.calcsize(self.packet_format)

        # Internal state to hold the latest data
        self.latest_data = {  # Initialize with dummy values
            "brightness": 0.0,
            "flux": 0.0,
            "low": 0.0,
            "mid": 0.0,
            "high": 0.0,
            "bpm": 120.0,
            "is_beat": 0.0,
            "notes": [0.0] * 12,
        }
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

    def get_latest(self):
        """
        Non-blocking fetch. Clears the UDP buffer to get the MOST RECENT packet.
        Returns the data dictionary.
        """
        if not self._is_bound:
            self.bind()

        new_data_received = False

        # We loop until the buffer is empty. This prevents 'visual lag'
        # caused by packets queuing up in the OS network stack.
        while True:
            try:
                data, _ = self.sock.recvfrom(self.packet_size)

                if len(data) == self.packet_size:
                    unpacked = struct.unpack(self.packet_format, data)
                    self.latest_data = {
                        "brightness": unpacked[0],
                        "flux": unpacked[1],
                        "low": unpacked[2],
                        "mid": unpacked[3],
                        "high": unpacked[4],
                        "bpm": unpacked[5],
                        "is_beat": unpacked[6] > 0.5,  # Convert float to bool
                        "notes": list(unpacked[7:]),
                    }
                    new_data_received = True
            except socket.error as e:
                # EAGAIN or EWOULDBLOCK means the buffer is finally empty
                err = e.args[0]
                if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
                    break
                else:
                    # A real error occurred
                    print(f"Socket error: {e}")
                    break

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
