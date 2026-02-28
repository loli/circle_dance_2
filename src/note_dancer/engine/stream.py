import numpy as np
import numpy.typing as npt
import pyaudio

from note_dancer.config import CHUNK, FORMAT, RATE


class AudioStream:
    def __init__(self):
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=FORMAT,
            channels=2,  # stereo, we average below
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )

    def read(self) -> npt.NDArray[np.float32]:
        """Reads a chunk of audio and returns it as a normalized float32 array."""
        raw_data = self.stream.read(
            CHUNK, exception_on_overflow=False
        )  # a droped frame is better than a delayed frame
        audio_array = np.frombuffer(raw_data, dtype=np.float32)
        mono_signal = (audio_array[0::2] + audio_array[1::2]) / 2.0
        return mono_signal

    def close(self):
        self.stream.stop_stream()
        self.stream.close()
        self.p.terminate()
