"""
Debug overlay for visualization frontend.

Displays network health, rendering performance, sync metrics, and data quality.
Toggled with 'D' key, positioned in top-right corner to avoid HUD overlap.
"""

from collections import deque
from typing import Any

import numpy as np
import pygame


class DebugOverlay:
    """
    On-screen debug panel showing network, rendering, sync, and data quality metrics.

    Displays organized by category:

    NETWORK & DATA:
    - Backend Packet Rate: Estimated FPS of backend packet generation (render_fps * avg_packets_per_frame).
    - Packets per Frame: Average packets drained from UDP buffer per render cycle.
    - Data Reuse: Percentage of frames that reuse previous packet data (no new packets).
    - Data Errors: Count of packets with invalid data (out-of-range notes, unrealistic BPM).
    - Socket Errors: Count of UDP socket errors encountered.

    RENDERING:
    - Render FPS: Visualization frames per second (should target 60).
    - Frame Time: Average milliseconds to render one frame.

    SYNC & TIMING:
    - (Metrics for future expansion)

    CACHE & MEMORY:
    - Active Traces: Number of active note particle traces currently on screen.
    - Cache Size: Number of pre-rendered note glyphs in LRU cache.

    Toggled on/off with 'D' key. Positioned right-center to avoid HUD overlap.
    """

    def __init__(self):
        """Initialize debug overlay tracking."""
        self.visible = False
        self.frame_times = deque(maxlen=60)
        self.packets_drained_counts = deque(maxlen=60)  # Packets drained per frame
        self.packet_count = 0
        self.data_errors = 0
        self.socket_errors = 0
        self.active_traces_count = 0
        self.cache_size = 0

    def update(
        self,
        frame_time_ms: float,
        packets_drained: int,
        data: dict[str, Any],
        active_traces: int,
        cache_size: int,
    ) -> None:
        """
        Update metrics from render loop.

        Args:
            frame_time_ms: Time to render current frame.
            packets_drained: Number of packets drained from buffer this frame.
            data: Latest packet data.
            active_traces: Number of active note traces.
            cache_size: Size of NoteTrace cache.
        """
        self.frame_times.append(frame_time_ms)
        self.packets_drained_counts.append(packets_drained)
        self.packet_count += 1
        self.active_traces_count = active_traces
        self.cache_size = cache_size

        # Check for data validity
        try:
            notes = data.get("notes", [])
            bpm = data.get("bpm", 0)

            # Validate note range
            if notes and (any(n < 0 or n > 1 for n in notes)):
                self.data_errors += 1

            # Validate BPM
            if not (30 <= bpm <= 300):
                self.data_errors += 1
        except Exception:
            self.data_errors += 1

    def log_socket_error(self) -> None:
        """Log a socket error."""
        self.socket_errors += 1

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        """
        Draw debug overlay in top-right corner.

        Args:
            surface: Pygame surface to draw on.
            font: Font for text rendering.
        """
        if not self.visible:
            return

        # Calculate rendering metrics
        if self.frame_times:
            render_fps = 1000.0 / np.mean(self.frame_times)
            avg_frame_time = np.mean(self.frame_times)
        else:
            render_fps = 0.0
            avg_frame_time = 0.0

        # Calculate backend/packet metrics
        if self.packets_drained_counts and len(self.packets_drained_counts) > 0:
            total_packets = sum(self.packets_drained_counts)
            avg_packets_per_frame = total_packets / len(self.packets_drained_counts)
            # Backend FPS estimate: (total packets drained / num frames) * render FPS
            backend_fps = avg_packets_per_frame * render_fps
            # Data reuse: frames with 0 packets = frame used prior data
            frames_with_zero_packets = sum(1 for count in self.packets_drained_counts if count == 0)
            data_reuse_pct = (frames_with_zero_packets / len(self.packets_drained_counts)) * 100.0
        else:
            backend_fps = 0.0
            avg_packets_per_frame = 0.0
            data_reuse_pct = 0.0

        # Build debug text lines organized by category
        lines = []
        lines.append("=== DEBUG OVERLAY ===")
        lines.append("")

        # Network & Data Health
        lines.append("NETWORK & DATA:")
        lines.append(f"  Backend Packet Rate: {backend_fps:6.1f} fps")
        lines.append(f"  Packets per Frame: {avg_packets_per_frame:6.2f}")
        lines.append(f"  Data Reuse: {data_reuse_pct:6.1f}%")
        lines.append(f"  Data Errors: {self.data_errors:4d}")
        lines.append(f"  Socket Errors: {self.socket_errors:4d}")
        lines.append("")

        # Rendering Performance
        lines.append("RENDERING:")
        lines.append(f"  Render FPS: {render_fps:6.1f}")
        lines.append(f"  Frame Time: {avg_frame_time:6.1f} ms")
        lines.append("")

        # Sync & Timing
        lines.append("SYNC & TIMING:")

        # Data Quality
        lines.append("CACHE & MEMORY:")
        lines.append(f"  Active Traces: {self.active_traces_count:4d}")
        lines.append(f"  Cache Size: {self.cache_size:4d}")
        lines.append("")

        # Render text to surface
        self._render_text_box(surface, font, lines, position="right-center")

    def _render_text_box(
        self, surface: pygame.Surface, font: pygame.font.Font, lines: list[str], position: str = "right-center"
    ) -> None:
        """
        Render a text box at specified position.

        Args:
            surface: Pygame surface to draw on.
            font: Font for text.
            lines: Lines of text to render.
            position: "right-center", "left-center", "top-right", "top-left", "bottom-right", or "bottom-left".
        """
        # Render all text to individual surfaces
        rendered_lines = []
        max_width = 0
        for line in lines:
            if line.strip():
                text_surf = font.render(line, True, (100, 200, 100))
                rendered_lines.append(text_surf)
                max_width = max(max_width, text_surf.get_width())
            else:
                rendered_lines.append(None)

        # Calculate total height
        line_height = font.get_height()
        total_height = sum(line_height for line in rendered_lines)

        # Calculate position
        margin = 10
        if position == "right-center":
            x = surface.get_width() - max_width - margin - 5
            y = (surface.get_height() - total_height) // 2
        elif position == "left-center":
            x = margin + 5
            y = (surface.get_height() - total_height) // 2
        elif position == "top-right":
            x = surface.get_width() - max_width - margin - 5
            y = margin
        elif position == "top-left":
            x = margin + 5
            y = margin
        elif position == "bottom-right":
            x = surface.get_width() - max_width - margin - 5
            y = surface.get_height() - total_height - margin
        else:  # bottom-left
            x = margin + 5
            y = surface.get_height() - total_height - margin

        # Draw semi-transparent background
        bg_rect = pygame.Rect(x - 5, y, max_width + 10, total_height)
        bg_surf = pygame.Surface((bg_rect.width, bg_rect.height))
        bg_surf.fill((20, 20, 20))
        bg_surf.set_alpha(180)
        surface.blit(bg_surf, (bg_rect.x, bg_rect.y))

        # Blit text lines
        y_offset = y
        for text_surf in rendered_lines:
            if text_surf:
                surface.blit(text_surf, (x, y_offset))
            y_offset += line_height
