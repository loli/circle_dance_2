"""Base classes for all parameters used in the visualization HUD."""

import collections
import json
import socket

import pygame


class KeyManager:
    """Static utility class to manage available keys globally."""

    # Class-level attributes (Shared across all calls)
    _single_keys = collections.deque(
        [pygame.K_y, pygame.K_x, pygame.K_c, pygame.K_v, pygame.K_b, pygame.K_n, pygame.K_m]
    )

    _pair_keys = collections.deque(
        [
            (pygame.K_q, pygame.K_a),
            (pygame.K_w, pygame.K_s),
            (pygame.K_e, pygame.K_d),
            (pygame.K_r, pygame.K_f),
            (pygame.K_t, pygame.K_g),
            (pygame.K_u, pygame.K_j),
            (pygame.K_i, pygame.K_k),
            (pygame.K_o, pygame.K_l),
            # Numeric keys for physics/extra parameters
            (pygame.K_1, pygame.K_2),
            (pygame.K_3, pygame.K_4),
            (pygame.K_5, pygame.K_6),
            (pygame.K_z, pygame.K_x),
            (pygame.K_c, pygame.K_v),
            (pygame.K_b, pygame.K_n),
            (pygame.K_m, pygame.K_COMMA),
        ]
    )

    @classmethod
    def get_single(cls) -> int:
        if not cls._single_keys:
            raise IndexError("No single keys left in the pool.")
        return cls._single_keys.popleft()

    @classmethod
    def get_pair(cls) -> tuple[int, int]:
        if not cls._pair_keys:
            raise IndexError("No key pairs left in the pool.")
        return cls._pair_keys.popleft()


class ParameterBase:
    """A minimal base so HUD can type-hint or identify parameters."""

    def __init__(self, name: str, category: str):
        self.name = name
        self.category = category


class BooleanParameter(ParameterBase):
    def __init__(self, name: str, val: bool, category: str = "local") -> None:
        """
        Represents a boolean parameter that can be toggled using a single key.

        Args:
            name: The name of the parameter.
            val: The initial value of the parameter (True/False).
            category: The category of the parameter ("global" or "local").
        """
        self.name = name
        self.value = val
        self.key = KeyManager.get_single()
        self.category = category

    def handle(self, key: int) -> bool:
        """
        Handles keyboard input to toggle the parameter.

        Args:
            key: The key pressed.

        Returns:
            True if the parameter was toggled, False otherwise.
        """
        if key == self.key:
            self.value = not self.value
            return True
        return False

    def __str__(self) -> str:
        """
        Returns a string representation of the parameter.

        Returns:
            A formatted string showing the parameter name, value, and associated key.
        """
        v_str = "ON" if self.value else "OFF"
        k_str = f"[{pygame.key.name(self.key).upper()}]"
        return f"{k_str:<6} {self.name}: {v_str}"

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
        """
        Represents a numeric parameter that can be adjusted using keyboard input.

        Args:
            name: The name of the parameter.
            val: The initial value of the parameter.
            min_v: The minimum value of the parameter.
            max_v: The maximum value of the parameter.
            step: The step size for incrementing or decrementing the value.
            fmt: The format string for displaying the parameter value.
            category: The category of the parameter ("global" or "local").
        """
        self.name = name
        self.value = val
        self.min_v = min_v
        self.max_v = max_v
        self.step = step
        self.keys = KeyManager.get_pair()
        self.fmt = fmt
        self.category = category

    def handle(self, key: int) -> bool:
        """
        Handles keyboard input to adjust the parameter.

        Args:
            key: The key pressed.

        Returns:
            True if the parameter was adjusted, False otherwise.
        """
        dec, inc = self.keys

        if key == dec:
            self.value -= self.step
            self.value = max(self.min_v, min(self.max_v, self.value))
            return True
        elif key == inc:
            self.value += self.step
            self.value = max(self.min_v, min(self.max_v, self.value))
            return True

        return False

    def __str__(self) -> str:
        """
        Returns a string representation of the parameter.

        Returns:
            A formatted string showing the parameter name, value, and associated keys.
        """
        v_str = self.fmt.format(self.value)
        k1, k2 = self.keys
        k_str = f"[{pygame.key.name(k1).upper()}/{pygame.key.name(k2).upper()}]"
        return f"{k_str:<6} {self.name}: {v_str}"

    def __float__(self) -> float:
        return self.value


class EngineParameter(NumericParameter):
    """Extends your NumericParameter to send updates back to the Audio Engine."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.cmd_addr = ("127.0.0.1", 5006)

    def handle(self, key: int) -> bool:
        changed = super().handle(key)
        if changed:
            # Automatic mapping: "Low Gain" -> "low_gain"
            engine_key = self.name.lower().replace(" ", "_")

            # Manual override for specific naming differences
            if engine_key == "flux_thr":
                engine_key = "flux_sens"

            msg = json.dumps({engine_key: float(self.value)})
            self.cmd_sock.sendto(msg.encode(), self.cmd_addr)
        return changed


class ParameterContainer:
    """Base class for grouping multiple parameters into a single UI row."""

    def __init__(self, name: str, category: str = "local"):
        self.name = name
        self.category = category

    def handle(self, key: int) -> bool:
        """Should delegate to children parameters."""
        raise NotImplementedError

    def __str__(self) -> str:
        """The text to display on the left side of the HUD row."""
        raise NotImplementedError

    def draw_visual(self, surf: pygame.Surface, data: dict):
        """Optional: The visualization to display on the right side."""
        pass
