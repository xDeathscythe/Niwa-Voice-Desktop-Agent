"""Audio visualizer component with animated bars."""

import customtkinter as ctk
from typing import List, Optional
import random

from ..styles.theme import COLORS


class AudioVisualizer(ctk.CTkFrame):
    """
    Audio level visualizer with animated vertical bars.

    Displays real-time audio levels in a visually appealing bar chart.

    Usage:
        visualizer = AudioVisualizer(parent)
        visualizer.pack()

        # Update with audio level (0.0 to 1.0)
        visualizer.set_level(0.75)
    """

    def __init__(
        self,
        master,
        num_bars: int = 24,
        bar_width: int = 4,
        bar_gap: int = 3,
        height: int = 50,
        active_color: str = COLORS["primary"],
        inactive_color: str = COLORS["bg_dark"],
        **kwargs
    ):
        """
        Initialize audio visualizer.

        Args:
            master: Parent widget
            num_bars: Number of bars to display
            bar_width: Width of each bar in pixels
            bar_gap: Gap between bars in pixels
            height: Total height of visualizer
            active_color: Color when bar is active
            inactive_color: Background color
        """
        # Calculate width
        width = num_bars * bar_width + (num_bars - 1) * bar_gap + 24

        super().__init__(
            master,
            fg_color=COLORS["bg_dark"],
            corner_radius=8,
            height=height,
            width=width,
            **kwargs
        )

        self.num_bars = num_bars
        self.bar_width = bar_width
        self.bar_gap = bar_gap
        self.bar_height = height - 16  # Padding
        self.active_color = active_color
        self.inactive_color = inactive_color

        self._current_level = 0.0
        self._bar_heights: List[float] = [0.1] * num_bars
        self._smoothing = 0.4
        self._animating = False

        self._create_canvas()

    def _create_canvas(self):
        """Create canvas for drawing bars."""
        self.canvas = ctk.CTkCanvas(
            self,
            bg=COLORS["bg_dark"],
            highlightthickness=0,
            height=self.bar_height + 8,
            width=self.num_bars * self.bar_width + (self.num_bars - 1) * self.bar_gap
        )
        self.canvas.pack(padx=12, pady=8)

        # Draw initial bars
        self._draw_bars()

    def _draw_bars(self):
        """Draw all bars on canvas."""
        self.canvas.delete("all")

        x = 0
        for i in range(self.num_bars):
            height = max(4, int(self._bar_heights[i] * self.bar_height))

            # Draw bar from bottom
            y1 = self.bar_height - height + 4
            y2 = self.bar_height + 4

            # Gradient effect - more active = more colored
            intensity = self._bar_heights[i]
            color = self._interpolate_color(
                self.inactive_color,
                self.active_color,
                intensity
            )

            self.canvas.create_rectangle(
                x, y1, x + self.bar_width, y2,
                fill=color,
                outline="",
                tags="bar"
            )

            x += self.bar_width + self.bar_gap

    def _interpolate_color(self, color1: str, color2: str, ratio: float) -> str:
        """Interpolate between two hex colors."""
        def hex_to_rgb(hex_color: str) -> tuple:
            hex_color = hex_color.lstrip('#')
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

        def rgb_to_hex(rgb: tuple) -> str:
            return '#{:02x}{:02x}{:02x}'.format(*[max(0, min(255, int(c))) for c in rgb])

        r1, g1, b1 = hex_to_rgb(color1)
        r2, g2, b2 = hex_to_rgb(color2)

        r = r1 + (r2 - r1) * ratio
        g = g1 + (g2 - g1) * ratio
        b = b1 + (b2 - b1) * ratio

        return rgb_to_hex((r, g, b))

    def set_level(self, level: float):
        """
        Update visualizer with new audio level.

        Args:
            level: Audio level from 0.0 to 1.0
        """
        self._current_level = max(0.0, min(1.0, level))
        self._update_bars()

    def _update_bars(self):
        """Update bar heights based on current level."""
        base_level = self._current_level

        for i in range(self.num_bars):
            # Add variation to make it look natural
            variation = random.uniform(-0.15, 0.15)
            target = max(0.05, min(1.0, base_level + variation))

            # Smooth transition
            current = self._bar_heights[i]
            self._bar_heights[i] = current * self._smoothing + target * (1 - self._smoothing)

        self._draw_bars()

    def start_animation(self):
        """Start idle animation (small random movements)."""
        self._animating = True
        self._animate()

    def stop_animation(self):
        """Stop idle animation."""
        self._animating = False
        # Reset to minimal bars
        self._bar_heights = [0.05] * self.num_bars
        self._draw_bars()

    def _animate(self):
        """Animation loop for idle state."""
        if not self._animating:
            return

        # Small random movements when idle
        if self._current_level < 0.1:
            for i in range(self.num_bars):
                self._bar_heights[i] = 0.05 + random.uniform(0, 0.1)
        else:
            self._update_bars()

        self._draw_bars()

        # Schedule next frame
        if self._animating:
            self.after(50, self._animate)

    def reset(self):
        """Reset visualizer to initial state."""
        self._current_level = 0.0
        self._bar_heights = [0.05] * self.num_bars
        self._draw_bars()
