"""Base classes for all parameters used in the visualization HUD."""

import json
import socket

import pygame


class ParameterBase:
    """A minimal base so HUD can type-hint or identify parameters."""

    def __init__(self, name: str, category: str):
        self.name = name
        self.category = category
        self.owner: ParameterContainer | None = None


class BooleanParameter(ParameterBase):
    def __init__(self, name: str, val: bool, category: str = "local") -> None:
        super().__init__(name, category)
        self.value = val

    def toggle(self) -> bool:
        """Toggles the boolean state."""
        self.value = not self.value
        return True

    def __str__(self) -> str:
        v_str = "ON" if self.value else "OFF"
        return f"{self.name}: {v_str}"

    def __bool__(self) -> bool:
        return self.value


class NumericParameter(ParameterBase):
    def __init__(
        self,
        name: str,
        val: float,
        min_v: float,
        max_v: float,
        step: float,
        fmt: str = "{:.2f}",
        category: str = "local",
    ) -> None:
        super().__init__(name, category)
        self.value = val
        self.min_v = min_v
        self.max_v = max_v
        self.step = step
        self.fmt = fmt

    def adjust(self, direction: int) -> bool:
        """
        Adjusts the value based on a direction (1 for up, -1 for down).
        Returns True if the value was successfully adjusted.
        """
        old_val = self.value
        self.value = max(self.min_v, min(self.max_v, self.value + (self.step * direction)))
        return self.value != old_val

    def __str__(self) -> str:
        v_str = self.fmt.format(self.value)
        return f"{self.name}: {v_str}"

    def __float__(self) -> float:
        return self.value


class EngineParameter(NumericParameter):
    """Extends NumericParameter to send updates back to the Audio Engine."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.cmd_addr = ("127.0.0.1", 5006)

    def adjust(self, direction: int) -> bool:
        changed = super().adjust(direction)
        if changed:
            self.send_to_engine()
        return changed

    def send_to_engine(self):
        """Sends current value to the audio engine via UDP."""
        # Automatic mapping: "Low Gain" -> "low_gain"
        engine_key = self.name.lower().replace(" ", "_")

        # Manual override for specific naming differences
        if engine_key == "flux_thr":
            engine_key = "flux_sens"

        msg = json.dumps({engine_key: float(self.value)})
        self.cmd_sock.sendto(msg.encode(), self.cmd_addr)


class ParameterContainer(ParameterBase):
    """Base class for grouping multiple parameters into a single UI row."""

    def __init__(self, name: str, children: list[ParameterBase], category: str = "local"):
        super().__init__(name, category)
        self._items = children

        # Automatically couple children to this container
        for child in self._items:
            child.owner = self
            child.category = category

    def get_items(self) -> list[ParameterBase]:
        """Returns the internal parameters for the HUD selection list."""
        return self._items

    def adjust(self, direction: int) -> bool:
        """Containers usually delegate adjustment to selected children, but can override."""
        return False

    def toggle(self) -> bool:
        """Optional: handle toggle/action for the whole container."""
        return False

    def __str__(self) -> str:
        return f"Group: {self.name}"

    def draw_visual(self, surf: pygame.Surface, data: dict):
        """Optional: The visualization to display on the right side."""
        pass
