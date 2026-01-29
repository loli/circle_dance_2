"""
Protocol for UDP messages exchanged between engine -> visualizer.

Fields (all optional in a single JSON object; packet may contain any subset):
- bpm: float
    - Description: Beats per minute detected by the audio engine.
    - Type: number (int/float)
    - Range: 20.0 .. 300.0 (typical musical BPM)
- notes: list[12 numbers]
    - Description: Per-semitone energy/chroma values for the 12 pitch classes.
    - Type: list of numbers (int/float)
    - Length: exactly 12 elements
    - Element range: 0.0 .. 1.0 (normalized energy)
- brightness: float
    - Description: Global brightness/strength scalar for visual emphasis.
    - Type: number (int/float)
    - Range: 0.0 .. 1.0
- rms: float
    - Description: Root Mean Square (Volume) of the audio frame.
    - Type: number (int/float)

Validation functions are intentionally minimal and cheap (type checks and simple range checks).
They raise on violations so protocol drift is noticed immediately.
"""

# Constants aligned with float32 digital audio and Librosa defaults
NOTES_LEN = 12
BPM_MIN = 20.0
BPM_MAX = 300.0

# Brightness is clipped to 1.0 in your analyzer code
BRIGHT_MIN = 0.0
BRIGHT_MAX = 1.0

# RMS in decibel
RMS_MIN = -180.0  # Total silence / Noise floor limit
RMS_MAX = 0.0  # Digital clipping point

_ALLOWED_KEYS = {"bpm", "notes", "brightness", "rms"}


def _is_number(x):
    return isinstance(x, (int, float))


def is_structurally_valid(msg: dict) -> bool:
    """Fast boolean structural check (no exceptions)."""
    if not isinstance(msg, dict):
        return False
    for k in msg.keys():
        if k not in _ALLOWED_KEYS:
            return False
    if "bpm" in msg and not _is_number(msg["bpm"]):
        return False
    if "brightness" in msg and not _is_number(msg["brightness"]):
        return False
    if "rms" in msg and not _is_number(msg["rms"]):
        return False
    if "notes" in msg:
        notes = msg["notes"]
        if not isinstance(notes, (list, tuple)) or len(notes) != NOTES_LEN:
            return False
        for n in notes:
            if not _is_number(n):
                return False
    return True


def validate_message_or_raise(msg: dict) -> None:
    """Validate message and raise on any structural or range violation.

    Raises:
        TypeError: if a field has the wrong type
        ValueError: if a field's value is out of the allowed range or unexpected keys are present
    """
    if not isinstance(msg, dict):
        raise TypeError("protocol: message must be a dict (JSON object)")

    for k in msg.keys():
        if k not in _ALLOWED_KEYS:
            raise ValueError(f"protocol: unexpected key '{k}'")

    if "bpm" in msg:
        b = msg["bpm"]
        if not _is_number(b):
            raise TypeError("protocol: 'bpm' must be numeric")
        b = float(b)
        if not (BPM_MIN <= b <= BPM_MAX):
            raise ValueError(f"protocol: 'bpm' out of range ({BPM_MIN}..{BPM_MAX}): {b}")

    if "brightness" in msg:
        br = msg["brightness"]
        if not _is_number(br):
            raise TypeError("protocol: 'brightness' must be numeric")
        br = float(br)
        if not (BRIGHT_MIN <= br <= BRIGHT_MAX):
            raise ValueError(f"protocol: 'brightness' out of range ({BRIGHT_MIN}..{BRIGHT_MAX}): {br}")

    if "rms" in msg:
        r = msg["rms"]
        if not _is_number(r):
            raise TypeError("protocol: 'rms' must be numeric")
        r = float(r)
        if not (RMS_MIN <= r <= RMS_MAX):
            raise ValueError(f"protocol: 'rms' out of range ({RMS_MIN}..{RMS_MAX}): {r}")

    if "notes" in msg:
        notes = msg["notes"]
        if not isinstance(notes, (list, tuple)):
            raise TypeError("protocol: 'notes' must be a list/tuple")
        if len(notes) != NOTES_LEN:
            raise ValueError(f"protocol: 'notes' must have length {NOTES_LEN}")
        for i, n in enumerate(notes):
            if not _is_number(n):
                raise TypeError(f"protocol: 'notes[{i}]' must be numeric")
            fn = float(n)
            if not (BRIGHT_MIN <= fn <= BRIGHT_MAX):
                raise ValueError(f"protocol: 'notes[{i}]' out of range ({BRIGHT_MIN}..{BRIGHT_MAX}): {fn}")
