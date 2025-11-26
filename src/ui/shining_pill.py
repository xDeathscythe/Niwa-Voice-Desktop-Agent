"""
Simple black pill with shining gradient text effect.

Replicates the React ShiningText component using PIL.
"""

import customtkinter as ctk
from typing import Optional, Callable
from enum import Enum, auto
import logging
import math
from PIL import Image, ImageDraw, ImageFont, ImageTk

from .styles.theme import COLORS, FONTS

logger = logging.getLogger(__name__)


class PillState(Enum):
    """Pill overlay states."""
    IDLE = auto()
    RECORDING = auto()
    TRANSCRIBING = auto()
    PROCESSING = auto()
    SUCCESS = auto()
    ERROR = auto()


class ShiningPill(ctk.CTkToplevel):
    """
    Simple black rounded pill with animated shining text.

    Recreates React's ShiningText gradient animation using PIL.
    """

    # Text for each state
    STATE_TEXT = {
        PillState.IDLE: "Orchestrate",
        PillState.RECORDING: "Recording...",
        PillState.TRANSCRIBING: "Transcribing...",
        PillState.PROCESSING: "Processing...",
        PillState.SUCCESS: "Copied ✓",
        PillState.ERROR: "Error",
    }

    # Pill dimensions (width, height)
    PILL_WIDTH = 140
    PILL_HEIGHT = 42
    CLOSE_BUTTON_SIZE = 28  # Round close button below pill

    def __init__(self, master, on_click: Optional[Callable] = None, on_close: Optional[Callable] = None):
        super().__init__(master)

        self._state = PillState.IDLE
        self._on_click = on_click
        self._on_close = on_close
        self._error_message = ""
        self._animation_id = None
        self._gradient_offset = 0.0  # Horizontal offset for gradient animation
        self._animation_direction = 1  # 1 = forward, -1 = backward
        self._rotation_angle = 0  # For loading square rotation

        # Click and drag
        self._drag_threshold = 15
        self._click_pos = None
        self._is_dragging = False

        self._configure_window()
        self._create_ui()
        self._position_on_screen()
        self._start_animation()

        logger.info("ShiningPill initialized")

    def _configure_window(self):
        """Configure window."""
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.95)

        # Remove from taskbar (Windows only)
        try:
            self.attributes("-toolwindow", True)
        except:
            pass

        self.configure(fg_color="black")

        try:
            self.attributes("-transparentcolor", "black")
        except:
            pass

        # Total height: pill + gap + close button
        total_height = self.PILL_HEIGHT + 8 + self.CLOSE_BUTTON_SIZE
        self.geometry(f"{self.PILL_WIDTH}x{total_height}")

        # Store total height for positioning
        self._total_height = total_height

    def _create_ui(self):
        """Create UI - simple black rounded frame with canvas for text."""
        # Main container with transparent background
        self.configure(fg_color="black")

        # Black rounded pill frame (top)
        self.pill_frame = ctk.CTkFrame(
            self,
            fg_color="#0a0a0a",  # Deep black
            corner_radius=self.PILL_HEIGHT // 2,  # Fully rounded sides
            border_width=0,
            width=self.PILL_WIDTH,
            height=self.PILL_HEIGHT
        )
        self.pill_frame.pack(side="top", padx=0, pady=0)
        self.pill_frame.pack_propagate(False)

        # Canvas for animated text
        self.text_canvas = ctk.CTkCanvas(
            self.pill_frame,
            width=self.PILL_WIDTH - 20,
            height=self.PILL_HEIGHT - 10,
            bg="#0a0a0a",
            highlightthickness=0
        )
        self.text_canvas.place(relx=0.5, rely=0.5, anchor="center")

        # Round close button (separate widget below pill, hidden by default)
        self.close_button = ctk.CTkButton(
            self,
            text="×",
            font=("Segoe UI", 18, "bold"),
            text_color="#ffffff",
            fg_color="#0a0a0a",
            hover_color="#1a1a1a",
            corner_radius=self.CLOSE_BUTTON_SIZE // 2,  # Fully round
            width=self.CLOSE_BUTTON_SIZE,
            height=self.CLOSE_BUTTON_SIZE,
            border_width=0,  # No border for perfect circle
            cursor="hand2",
            command=self._on_close_click
        )

        # Store position for showing/hiding
        self._close_button_x = 0.5
        self._close_button_y = self.PILL_HEIGHT + 8

        # Initially hide completely (don't place it)
        self._close_button_visible = False

        # Bind hover events to show/hide close button
        self.pill_frame.bind("<Enter>", self._on_enter)
        self.pill_frame.bind("<Leave>", self._on_leave)
        self.text_canvas.bind("<Enter>", self._on_enter)
        self.text_canvas.bind("<Leave>", self._on_leave)
        self.close_button.bind("<Enter>", self._on_close_enter)
        self.close_button.bind("<Leave>", self._on_leave)

        # Bind events for pill click and drag
        self.pill_frame.bind("<ButtonPress-1>", self._on_press)
        self.pill_frame.bind("<B1-Motion>", self._on_motion)
        self.pill_frame.bind("<ButtonRelease-1>", self._on_release)
        self.text_canvas.bind("<ButtonPress-1>", self._on_press)
        self.text_canvas.bind("<B1-Motion>", self._on_motion)
        self.text_canvas.bind("<ButtonRelease-1>", self._on_release)

    def _generate_wave_loader(self):
        """
        Generate animated wave loader using PIL.

        5 vertical bars with wave animation (like React WaveLoader).
        """
        img_width = self.PILL_WIDTH - 20
        img_height = self.PILL_HEIGHT - 10

        # Create transparent background
        result = Image.new('RGBA', (img_width, img_height), (10, 10, 10, 0))
        draw = ImageDraw.Draw(result)

        # Bar settings
        bar_width = 2
        gap = 3
        base_heights = [8, 12, 16, 12, 8]  # Medium size heights
        num_bars = 5

        # Calculate total width and center position
        total_width = (bar_width * num_bars) + (gap * (num_bars - 1))
        start_x = (img_width - total_width) // 2

        # Draw bars with wave animation
        for i in range(num_bars):
            # Calculate wave offset using sine wave for smooth animation
            wave_phase = (self._gradient_offset / 30.0) + (i * 0.3)  # Offset each bar
            wave_offset = math.sin(wave_phase) * 4  # ±4px oscillation

            # Calculate bar height with wave
            bar_height = base_heights[i] + wave_offset
            bar_height = max(4, min(bar_height, 20))  # Clamp between 4-20px

            # Calculate bar position
            x = start_x + (i * (bar_width + gap))
            y = (img_height - bar_height) // 2

            # Draw rounded rectangle (bar)
            # Use light gray color
            color = (180, 180, 180, 255)

            # Draw bar with rounded corners
            radius = bar_width // 2
            draw.rounded_rectangle(
                [(x, y), (x + bar_width, y + bar_height)],
                radius=radius,
                fill=color
            )

        return result

    def _generate_rotating_square(self):
        """
        Generate rotating square loader using PIL.

        Used for TRANSCRIBING and PROCESSING states.
        """
        img_width = self.PILL_WIDTH - 20
        img_height = self.PILL_HEIGHT - 10

        # Create transparent background
        result = Image.new('RGBA', (img_width, img_height), (10, 10, 10, 0))

        # Square size
        square_size = 16

        # Create a larger canvas for rotation to avoid clipping
        canvas_size = int(square_size * 1.5)
        square_img = Image.new('RGBA', (canvas_size, canvas_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(square_img)

        # Draw square at center
        offset = (canvas_size - square_size) // 2
        draw.rounded_rectangle(
            [(offset, offset), (offset + square_size, offset + square_size)],
            radius=2,
            fill=(180, 180, 180, 255)
        )

        # Rotate the square
        rotated = square_img.rotate(self._rotation_angle, expand=False, resample=Image.BICUBIC)

        # Paste rotated square at center of result
        paste_x = (img_width - canvas_size) // 2
        paste_y = (img_height - canvas_size) // 2
        result.paste(rotated, (paste_x, paste_y), rotated)

        return result

    def _generate_shining_text_image(self, text: str, offset: float):
        """
        Generate text with animated gradient using PIL.

        True ping-pong: same frames forward and backward.
        """
        # Image dimensions
        img_width = self.PILL_WIDTH - 20
        img_height = self.PILL_HEIGHT - 10

        # Create wider gradient for smooth rendering (3x width for seamless edges)
        gradient_width = img_width * 3
        gradient_img = Image.new('RGB', (gradient_width, img_height), color=(10, 10, 10))
        draw = ImageDraw.Draw(gradient_img)

        # Ultra smooth symmetrical gradient (dark -> bright -> dark)
        # This ensures smooth ping-pong without visible seams
        colors = [
            (40, 40, 40),    # Very dark
            (55, 55, 55),
            (70, 70, 70),
            (90, 90, 90),
            (115, 115, 115),
            (145, 145, 145),
            (175, 175, 175),
            (205, 205, 205),
            (230, 230, 230),
            (250, 250, 250),
            (255, 255, 255), # Bright white (center)
            (250, 250, 250),
            (230, 230, 230),
            (205, 205, 205),
            (175, 175, 175),
            (145, 145, 145),
            (115, 115, 115),
            (90, 90, 90),
            (70, 70, 70),
            (55, 55, 55),
            (40, 40, 40),    # Very dark (matches start)
        ]

        # Draw ultra smooth horizontal gradient
        for x in range(gradient_width):
            # Map x to color with smooth interpolation
            position = (x / gradient_width) * (len(colors) - 1)
            color_index = int(position)
            color_index = max(0, min(color_index, len(colors) - 2))

            # Smooth interpolation
            t = position - color_index
            c1 = colors[color_index]
            c2 = colors[color_index + 1]
            interpolated = tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))

            draw.line([(x, 0), (x, img_height)], fill=interpolated)

        # Use offset directly for ping-pong
        # Offset will be controlled by animation logic (forward/backward)
        shift = int(offset) % (gradient_width - img_width)
        gradient_img = gradient_img.crop((shift, 0, shift + img_width, img_height))

        # Create text mask
        text_mask = Image.new('L', (img_width, img_height), 0)
        text_draw = ImageDraw.Draw(text_mask)

        # Load font
        try:
            font = ImageFont.truetype("seguisb.ttf", 14)  # Segoe UI Semibold
        except:
            font = ImageFont.load_default()

        # Get text bounding box for centering
        bbox = text_draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Center text - account for bbox offset for perfect centering
        text_x = (img_width - text_width) // 2 - bbox[0]
        text_y = (img_height - text_height) // 2 - bbox[1]

        # Draw text on mask
        text_draw.text((text_x, text_y), text, fill=255, font=font)

        # Apply text mask to gradient
        result = Image.new('RGBA', (img_width, img_height), (10, 10, 10, 0))
        result.paste(gradient_img, (0, 0))
        result.putalpha(text_mask)

        return result

    def _update_text(self):
        """Update animated text on canvas."""
        # Use rotating square for transcribing and processing states
        if self._state in (PillState.TRANSCRIBING, PillState.PROCESSING):
            text_img = self._generate_rotating_square()
        else:
            text = self.STATE_TEXT.get(self._state, "")
            if self._state == PillState.ERROR and self._error_message:
                text = self._error_message[:15]

            # Generate text image with current gradient offset
            text_img = self._generate_shining_text_image(text, self._gradient_offset)

        # Convert to PhotoImage
        self._text_photo = ImageTk.PhotoImage(text_img)

        # Update canvas
        self.text_canvas.delete("text")
        self.text_canvas.create_image(
            (self.PILL_WIDTH - 20) // 2,
            (self.PILL_HEIGHT - 10) // 2,
            image=self._text_photo,
            anchor="center",
            tags="text"
        )

    def _start_animation(self):
        """Start gradient animation."""
        self._animate()

    def _animate(self):
        """Animate gradient movement and square rotation."""
        try:
            # Update rotation angle for square (6 degrees per frame for smooth rotation)
            self._rotation_angle = (self._rotation_angle + 6) % 360

            # Maximum offset (gradient travels across text width)
            max_offset = (self.PILL_WIDTH - 20) * 1.8  # Travel distance

            # Update offset based on direction - 2x faster animation
            self._gradient_offset += 4.0 * self._animation_direction

            # Reverse direction at boundaries for ping-pong effect
            if self._gradient_offset >= max_offset:
                self._gradient_offset = max_offset
                self._animation_direction = -1  # Go backward
            elif self._gradient_offset <= 0:
                self._gradient_offset = 0
                self._animation_direction = 1  # Go forward

            # Update text rendering
            self._update_text()

            # Schedule next frame (30ms ≈ 33fps)
            self._animation_id = self.after(30, self._animate)
        except Exception as e:
            logger.error(f"Animation error: {e}")

    def _stop_animation(self):
        """Stop animation."""
        if self._animation_id:
            self.after_cancel(self._animation_id)
            self._animation_id = None

    def _position_on_screen(self):
        """Position at bottom center."""
        self.update_idletasks()

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        x = (screen_width - self.PILL_WIDTH) // 2
        y = screen_height - 100 - self._total_height

        self.geometry(f"{self.PILL_WIDTH}x{self._total_height}+{x}+{y}")

    # Click and drag handlers
    def _on_press(self, event):
        self._click_pos = (event.x, event.y)
        self._is_dragging = False
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_motion(self, event):
        if self._click_pos:
            dx = abs(event.x - self._click_pos[0])
            dy = abs(event.y - self._click_pos[1])
            if dx > self._drag_threshold or dy > self._drag_threshold:
                self._is_dragging = True

        if self._is_dragging:
            x = self.winfo_x() + (event.x - self._drag_x)
            y = self.winfo_y() + (event.y - self._drag_y)
            self.geometry(f"+{x}+{y}")

    def _on_release(self, event):
        was_dragging = self._is_dragging
        self._click_pos = None
        self._is_dragging = False

        if not was_dragging and self._on_click:
            logger.info("✓ Pill clicked!")
            try:
                self._on_click()
            except Exception as e:
                logger.error(f"Click handler error: {e}")

    def _on_enter(self, event):
        """Show close button on hover over pill."""
        if not self._close_button_visible:
            self._close_button_visible = True
            self._fade_in_close_button()

    def _on_close_enter(self, event):
        """Keep close button visible when hovering over it."""
        self._close_button_visible = True

    def _on_leave(self, event):
        """Hide close button when not hovering."""
        # Check if mouse is actually leaving the entire widget area
        x = self.winfo_pointerx() - self.winfo_rootx()
        y = self.winfo_pointery() - self.winfo_rooty()

        # Check if outside the entire widget (pill + close button area)
        if x < 0 or x > self.PILL_WIDTH or y < 0 or y > self._total_height:
            if self._close_button_visible:
                self._close_button_visible = False
                self._fade_out_close_button()

    def _fade_in_close_button(self):
        """Show close button on hover."""
        self.close_button.place(
            relx=self._close_button_x,
            y=self._close_button_y,
            anchor="n"
        )

    def _fade_out_close_button(self):
        """Hide close button when not hovering."""
        self.close_button.place_forget()

    def _on_close_click(self):
        """Handle close button click."""
        logger.info("✓ Close button clicked - shutting down application")
        if self._on_close:
            try:
                self._on_close()
            except Exception as e:
                logger.error(f"Close handler error: {e}")

    # Public API
    def show(self):
        """Show pill."""
        self.deiconify()
        self.lift()

    def hide(self):
        """Hide pill."""
        self.withdraw()

    def set_state(self, state: PillState, error_message: str = ""):
        """Set pill state."""
        self._state = state
        self._error_message = error_message
        self._update_text()

    def show_success(self):
        """Show success."""
        self.set_state(PillState.SUCCESS)
        self.after(1500, lambda: self.set_state(PillState.IDLE))

    def show_error(self, message: str):
        """Show error."""
        self.set_state(PillState.ERROR, error_message=message)
        self.after(3000, lambda: self.set_state(PillState.IDLE))
