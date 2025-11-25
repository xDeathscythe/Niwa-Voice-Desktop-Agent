"""
Gradient Pill with Canvas - True rotating conic gradient like React GradientButton.

Uses PIL to render actual conic gradient animation.
"""

import customtkinter as ctk
from typing import Optional, Callable
from enum import Enum, auto
import logging
import math
from PIL import Image, ImageDraw, ImageTk, ImageFont

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


class GradientPill(ctk.CTkToplevel):
    """
    Floating pill with rotating conic gradient border.

    Recreates the React GradientButton effect using PIL Canvas rendering.
    """

    # Dimensions
    DIMENSIONS = {
        PillState.IDLE: (100, 34),
        PillState.RECORDING: (150, 42),
        PillState.TRANSCRIBING: (140, 38),
        PillState.PROCESSING: (140, 38),
        PillState.SUCCESS: (110, 38),
        PillState.ERROR: (170, 38),
    }

    def __init__(self, on_click: Optional[Callable] = None):
        super().__init__()

        self._state = PillState.IDLE
        self._on_click = on_click
        self._error_message = ""
        self._animation_id = None
        self._gradient_angle = 0  # Rotation angle for conic gradient
        self._text_labels = []

        # Click and drag state
        self._drag_threshold = 15
        self._click_pos = None
        self._is_dragging = False

        self._configure_window()
        self._create_ui()
        self._position_on_screen()

        # Start gradient animation
        self._start_gradient_animation()

        logger.info("GradientPill initialized")

    def _configure_window(self):
        """Configure window properties."""
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.98)
        self.configure(fg_color="black")

        # Try to make transparent
        try:
            self.attributes("-transparentcolor", "black")
        except:
            pass

        width, height = self.DIMENSIONS[PillState.IDLE]
        self.geometry(f"{width}x{height}")

    def _create_ui(self):
        """Create UI with Canvas for gradient rendering."""
        # Canvas for gradient border
        width, height = self.DIMENSIONS[self._state]
        self.canvas = ctk.CTkCanvas(
            self,
            width=width,
            height=height,
            bg="black",
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)

        # Bind events
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        # Create initial content
        self._create_idle_content()

    def _generate_conic_gradient(self, width, height, angle):
        """Generate conic gradient image using PIL."""
        # Create RGBA image
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Define gradient colors (vibrant rainbow)
        colors = [
            (14, 165, 233),   # Sky blue
            (6, 182, 212),    # Cyan
            (139, 92, 246),   # Purple
            (217, 70, 239),   # Fuchsia
            (244, 63, 94),    # Rose
            (249, 115, 22),   # Orange
            (234, 179, 8),    # Yellow
            (132, 204, 22),   # Lime
            (34, 197, 94),    # Green
            (16, 185, 129),   # Emerald
            (20, 184, 166),   # Teal
            (14, 165, 233),   # Back to sky blue
        ]

        cx, cy = width // 2, height // 2
        max_radius = min(width, height) // 2

        # Draw conic gradient by drawing pie slices
        num_slices = len(colors) - 1
        slice_angle = 360 / num_slices

        for i in range(num_slices):
            start_angle = (i * slice_angle + angle) % 360
            end_angle = ((i + 1) * slice_angle + angle) % 360

            # Interpolate between current and next color
            c1 = colors[i]
            c2 = colors[i + 1]

            # Draw filled arc (pie slice)
            draw.pieslice(
                [cx - max_radius, cy - max_radius, cx + max_radius, cy + max_radius],
                start=start_angle,
                end=end_angle,
                fill=c1 + (255,),
                outline=c1 + (255,)
            )

        # Create mask for pill shape (rounded rectangle)
        mask = Image.new('L', (width, height), 0)
        mask_draw = ImageDraw.Draw(mask)
        corner_radius = min(width, height) // 2
        mask_draw.rounded_rectangle(
            [(0, 0), (width, height)],
            radius=corner_radius,
            fill=255
        )

        # Apply mask
        img.putalpha(mask)

        # Create inner transparent area (for border effect)
        inner_mask = Image.new('L', (width, height), 0)
        inner_draw = ImageDraw.Draw(inner_mask)
        border_width = 3
        inner_draw.rounded_rectangle(
            [(border_width, border_width), (width - border_width, height - border_width)],
            radius=corner_radius - border_width,
            fill=255
        )

        # Subtract inner mask to create border
        img_alpha = img.split()[3]
        img_alpha = Image.composite(Image.new('L', (width, height), 0), img_alpha, inner_mask)
        img.putalpha(img_alpha)

        return img

    def _draw_gradient_border(self):
        """Draw the rotating gradient border on canvas."""
        width, height = int(self.canvas.cget("width")), int(self.canvas.cget("height"))

        # Generate gradient image
        gradient_img = self._generate_conic_gradient(width, height, self._gradient_angle)

        # Convert to PhotoImage
        self._gradient_photo = ImageTk.PhotoImage(gradient_img)

        # Clear canvas and draw new gradient
        self.canvas.delete("gradient")
        self.canvas.create_image(0, 0, anchor="nw", image=self._gradient_photo, tags="gradient")

        # Draw inner background
        corner_radius = min(width, height) // 2
        border_width = 3
        inner_color = COLORS["bg_secondary"]
        self.canvas.create_rounded_rectangle(
            border_width, border_width,
            width - border_width, height - border_width,
            radius=corner_radius - border_width,
            fill=inner_color,
            outline="",
            tags="inner"
        )

        # Redraw content on top
        self._redraw_content()

    def _redraw_content(self):
        """Redraw text content on canvas."""
        width = int(self.canvas.cget("width"))
        height = int(self.canvas.cget("height"))

        # Clear text
        self.canvas.delete("text")

        # Draw text based on state
        if self._state == PillState.IDLE:
            text = "Ctrl+Alt"
            self.canvas.create_text(
                width // 2, height // 2,
                text=text,
                fill=COLORS["text_muted"],
                font=(FONTS["family_mono"], FONTS["size_xs"]),
                tags="text"
            )

    def _create_idle_content(self):
        """Create IDLE state content."""
        self._draw_gradient_border()

    def _start_gradient_animation(self):
        """Start rotating the gradient."""
        self._animate_gradient()

    def _animate_gradient(self):
        """Animate gradient rotation."""
        try:
            # Increment rotation angle
            self._gradient_angle = (self._gradient_angle + 3) % 360

            # Redraw gradient
            self._draw_gradient_border()

            # Schedule next frame (30ms for ~33fps)
            self._animation_id = self.after(30, self._animate_gradient)
        except Exception as e:
            logger.error(f"Gradient animation error: {e}")

    def _stop_gradient_animation(self):
        """Stop gradient animation."""
        if self._animation_id:
            self.after_cancel(self._animation_id)
            self._animation_id = None

    def _position_on_screen(self):
        """Position pill at bottom center."""
        self.update_idletasks()

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        width, height = self.DIMENSIONS[self._state]
        margin = 80

        x = (screen_width - width) // 2
        y = screen_height - margin - height

        self.geometry(f"{width}x{height}+{x}+{y}")

    # Click and drag handlers
    def _on_press(self, event):
        """Handle mouse press."""
        self._click_pos = (event.x, event.y)
        self._is_dragging = False
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_motion(self, event):
        """Handle mouse motion."""
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
        """Handle mouse release."""
        was_dragging = self._is_dragging
        self._click_pos = None
        self._is_dragging = False

        if not was_dragging and self._on_click:
            logger.info("✓ Pill clicked!")
            try:
                self._on_click()
            except Exception as e:
                logger.error(f"Click handler error: {e}")

    def show(self):
        """Show the pill."""
        self.deiconify()
        self.lift()

    def hide(self):
        """Hide the pill."""
        self.withdraw()

    def set_state(self, state: PillState, error_message: str = ""):
        """Set pill state."""
        self._state = state
        self._error_message = error_message
        # Resize and update content
        # TODO: Implement state-specific rendering
        self._draw_gradient_border()

    def show_success(self):
        """Show success state."""
        self.set_state(PillState.SUCCESS)

    def show_error(self, message: str):
        """Show error state."""
        self.set_state(PillState.ERROR, error_message=message)


# Helper method for Canvas rounded rectangle
def create_rounded_rectangle(self, x1, y1, x2, y2, radius=25, **kwargs):
    """Create rounded rectangle on canvas."""
    points = [
        x1 + radius, y1,
        x1 + radius, y1,
        x2 - radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1 + radius,
        x1, y1
    ]

    return self.create_polygon(points, **kwargs, smooth=True)


# Monkey-patch the Canvas class
ctk.CTkCanvas.create_rounded_rectangle = create_rounded_rectangle
