import pyaudio
import numpy as np
import numpy.typing as npt
from note_dancer.config import CHUNK, RATE


class AudioStream:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )

    def read(self) -> npt.NDArray[np.float32]:
        """Reads a chunk of audio and returns it as a normalized float32 array."""
        data = self.stream.read(CHUNK, exception_on_overflow=False)
        return np.frombuffer(data, dtype=np.float32)

    def close(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
