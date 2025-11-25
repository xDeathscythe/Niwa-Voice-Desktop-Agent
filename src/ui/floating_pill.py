"""
Floating pill overlay for VoiceType - Modern minimal design.

Inspired by Cursor, Notion, Obsidian floating indicators.
"""

import customtkinter as ctk
from typing import Optional, Callable
from enum import Enum, auto
import logging

from .styles.theme import COLORS, FONTS, RADIUS, GRADIENT_BORDER, GRADIENT_TEXT

logger = logging.getLogger(__name__)


class PillState(Enum):
    """Pill overlay states."""
    IDLE = auto()
    RECORDING = auto()
    TRANSCRIBING = auto()
    PROCESSING = auto()
    SUCCESS = auto()
    ERROR = auto()


class FloatingPill(ctk.CTkToplevel):
    """
    Modern floating pill overlay that shows VoiceType status.

    States:
    - IDLE: Minimal pill with hotkey hint
    - RECORDING: Pulsing red indicator with bars
    - TRANSCRIBING: Loading indicator
    - PROCESSING: AI processing indicator
    - SUCCESS: Checkmark
    - ERROR: Error message
    """

    # Dimensions - slightly larger for better visibility
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
        self._bar_ids = []
        self._recording_seconds = 0

        # Gradient animation state
        self._gradient_border_index = 0
        self._gradient_text_index = 0
        self._gradient_animation_id = None
        self._text_labels = []  # Store text labels for animation

        self._configure_window()
        self._create_ui()
        self._position_on_screen()

        # Start gradient animations
        self._start_gradient_animations()

        logger.info("FloatingPill initialized")

    def _configure_window(self):
        """Configure window properties."""
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.95)

        # Transparent background for rounded effect
        self.configure(fg_color="black")

        # Try to make window transparent
        try:
            self.attributes("-transparentcolor", "black")
        except:
            pass

        # Initial size
        width, height = self.DIMENSIONS[PillState.IDLE]
        self.geometry(f"{width}x{height}")

    def _create_ui(self):
        """Create UI components."""
        # Main pill frame - fully rounded with gradient border
        self.pill = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_secondary"],
            corner_radius=50,  # Large radius for pill shape
            border_width=3,  # Thicker border for gradient effect
            border_color=GRADIENT_BORDER[0]  # Start with first gradient color
        )
        self.pill.pack(fill="both", expand=True)

        # Single click to toggle recording, drag to move
        self._drag_threshold = 15  # Increased from 5 to prevent accidental drags
        self._click_pos = None
        self._is_dragging = False

        self.pill.bind("<ButtonPress-1>", self._on_press)
        self.pill.bind("<B1-Motion>", self._on_motion)
        self.pill.bind("<ButtonRelease-1>", self._on_release)

        # Content frame
        self.content = ctk.CTkFrame(self.pill, fg_color="transparent")
        self.content.pack(expand=True)

        # Create initial content
        self._create_idle_content()

        # Bind events to all widgets (CRITICAL FIX!)
        self._bind_click_events_to_all()

    def _bind_click_events_to_all(self):
        """Bind click events to ALL widgets recursively (fixes click reliability)."""
        def bind_recursive(widget):
            try:
                widget.bind("<ButtonPress-1>", self._on_press, add=True)
                widget.bind("<B1-Motion>", self._on_motion, add=True)
                widget.bind("<ButtonRelease-1>", self._on_release, add=True)
                # Recursively bind to all children
                for child in widget.winfo_children():
                    bind_recursive(child)
            except Exception as e:
                logger.debug(f"Could not bind to widget: {e}")

        bind_recursive(self.pill)
        logger.debug("Click events bound to all widgets")

    def _create_idle_content(self):
        """Create IDLE state content."""
        self._clear_content()

        # Status dot (green)
        self.dot = ctk.CTkLabel(
            self.content,
            text="",
            width=6,
            height=6,
            corner_radius=3,
            fg_color=COLORS["success"]
        )
        self.dot.pack(side="left", padx=(12, 6))

        # Hotkey hint with shining effect
        hint = ctk.CTkLabel(
            self.content,
            text="Ctrl+Alt",
            font=(FONTS["family_mono"], FONTS["size_xs"]),
            text_color=GRADIENT_TEXT[self._gradient_text_index]
        )
        hint.pack(side="left", padx=(0, 12))
        self._text_labels.append(hint)  # Add to animation list

        # Re-bind events after creating new widgets
        self._bind_click_events_to_all()

    def _create_recording_content(self):
        """Create RECORDING state content."""
        self._clear_content()

        # Recording dot (red, animated)
        self.rec_dot = ctk.CTkLabel(
            self.content,
            text="",
            width=8,
            height=8,
            corner_radius=4,
            fg_color=COLORS["recording"]
        )
        self.rec_dot.pack(side="left", padx=(12, 8))

        # Audio bars container
        self.bars_frame = ctk.CTkFrame(self.content, fg_color="transparent", width=40, height=20)
        self.bars_frame.pack(side="left", padx=(0, 8))
        self.bars_frame.pack_propagate(False)

        # Create audio bars
        self._bar_ids = []
        for i in range(5):
            bar = ctk.CTkFrame(
                self.bars_frame,
                width=4,
                height=8,
                corner_radius=2,
                fg_color=COLORS["accent"]
            )
            bar.place(x=i*8, rely=0.5, anchor="w")
            self._bar_ids.append(bar)

        # Timer with shining effect
        self.timer = ctk.CTkLabel(
            self.content,
            text="0:00",
            font=(FONTS["family_mono"], FONTS["size_xs"]),
            text_color=GRADIENT_TEXT[self._gradient_text_index]
        )
        self.timer.pack(side="left", padx=(0, 12))
        self._text_labels.append(self.timer)  # Add to animation list

        # Start animations
        self._start_recording_animation()

        # Re-bind events after creating new widgets
        self._bind_click_events_to_all()

    def _create_transcribing_content(self):
        """Create TRANSCRIBING state content."""
        self._clear_content()

        # Spinner dots
        self.spinner = ctk.CTkLabel(
            self.content,
            text="...",
            font=(FONTS["family"], FONTS["size_sm"]),
            text_color=COLORS["accent"]
        )
        self.spinner.pack(side="left", padx=(12, 6))

        # Text with shining effect
        text = ctk.CTkLabel(
            self.content,
            text="Transcribing",
            font=(FONTS["family"], FONTS["size_xs"]),
            text_color=GRADIENT_TEXT[self._gradient_text_index]
        )
        text.pack(side="left", padx=(0, 12))
        self._text_labels.append(text)  # Add to animation list

        self._start_spinner_animation()

        # Re-bind events after creating new widgets
        self._bind_click_events_to_all()

    def _create_processing_content(self):
        """Create PROCESSING state content."""
        self._clear_content()

        # AI icon
        icon = ctk.CTkLabel(
            self.content,
            text="*",
            font=(FONTS["family"], FONTS["size_md"]),
            text_color=COLORS["accent"]
        )
        icon.pack(side="left", padx=(12, 6))

        # Text with shining effect
        text = ctk.CTkLabel(
            self.content,
            text="Processing",
            font=(FONTS["family"], FONTS["size_xs"]),
            text_color=GRADIENT_TEXT[self._gradient_text_index]
        )
        text.pack(side="left", padx=(0, 12))
        self._text_labels.append(text)  # Add to animation list

        # Re-bind events after creating new widgets
        self._bind_click_events_to_all()

    def _create_success_content(self):
        """Create SUCCESS state content."""
        self._clear_content()

        # Checkmark
        check = ctk.CTkLabel(
            self.content,
            text="OK",
            font=(FONTS["family"], FONTS["size_sm"], "bold"),
            text_color=COLORS["success"]
        )
        check.pack(side="left", padx=(12, 6))

        # Text with shining effect
        text = ctk.CTkLabel(
            self.content,
            text="Copied",
            font=(FONTS["family"], FONTS["size_xs"]),
            text_color=GRADIENT_TEXT[self._gradient_text_index]
        )
        text.pack(side="left", padx=(0, 12))
        self._text_labels.append(text)  # Add to animation list

        # Re-bind events after creating new widgets
        self._bind_click_events_to_all()

    def _create_error_content(self):
        """Create ERROR state content."""
        self._clear_content()

        # X icon
        icon = ctk.CTkLabel(
            self.content,
            text="X",
            font=(FONTS["family"], FONTS["size_sm"], "bold"),
            text_color=COLORS["error"]
        )
        icon.pack(side="left", padx=(12, 6))

        # Error message with shining effect
        msg = self._error_message[:15] if self._error_message else "Error"
        text = ctk.CTkLabel(
            self.content,
            text=msg,
            font=(FONTS["family"], FONTS["size_xs"]),
            text_color=GRADIENT_TEXT[self._gradient_text_index]
        )
        text.pack(side="left", padx=(0, 12))
        self._text_labels.append(text)  # Add to animation list

        # Re-bind events after creating new widgets
        self._bind_click_events_to_all()

    def _clear_content(self):
        """Clear all content widgets."""
        self._stop_animation()
        for widget in self.content.winfo_children():
            widget.destroy()
        self._bar_ids = []
        self._text_labels = []  # Clear text labels for animation

    def _start_recording_animation(self):
        """Animate recording indicator."""
        self._animate_recording()

    def _animate_recording(self):
        """Animation loop for recording state."""
        if self._state != PillState.RECORDING:
            return

        # Pulse recording dot
        if hasattr(self, 'rec_dot'):
            current = self.rec_dot.cget("fg_color")
            new_color = COLORS["bg_tertiary"] if current == COLORS["recording"] else COLORS["recording"]
            self.rec_dot.configure(fg_color=new_color)

        # Animate bars
        import random
        for bar in self._bar_ids:
            height = random.randint(4, 18)
            bar.configure(height=height)

        self._animation_id = self.after(150, self._animate_recording)

    def _start_spinner_animation(self):
        """Animate spinner."""
        self._animate_spinner(0)

    def _animate_spinner(self, frame):
        """Spinner animation loop."""
        if self._state != PillState.TRANSCRIBING:
            return

        dots = [".", "..", "...", ""]
        if hasattr(self, 'spinner'):
            self.spinner.configure(text=dots[frame % 4])

        self._animation_id = self.after(300, lambda: self._animate_spinner(frame + 1))

    def _stop_animation(self):
        """Stop all animations."""
        if self._animation_id:
            self.after_cancel(self._animation_id)
            self._animation_id = None

    def _start_gradient_animations(self):
        """Start rotating gradient border and shining text animations."""
        self._animate_gradients()

    def _animate_gradients(self):
        """Animate gradient border and shining text effects."""
        try:
            # Animate border - cycle through gradient colors
            self._gradient_border_index = (self._gradient_border_index + 1) % len(GRADIENT_BORDER)
            border_color = GRADIENT_BORDER[self._gradient_border_index]

            # Update pill border color
            if hasattr(self, 'pill'):
                self.pill.configure(border_color=border_color)

            # Animate text - cycle through shining gradient
            self._gradient_text_index = (self._gradient_text_index + 1) % len(GRADIENT_TEXT)
            text_color = GRADIENT_TEXT[self._gradient_text_index]

            # Update all text labels
            for label in self._text_labels:
                try:
                    if label.winfo_exists():
                        label.configure(text_color=text_color)
                except Exception:
                    pass  # Label might have been destroyed

            # Schedule next frame (60ms for border, smooth animation)
            self._gradient_animation_id = self.after(60, self._animate_gradients)
        except Exception as e:
            logger.error(f"Gradient animation error: {e}")

    def _stop_gradient_animations(self):
        """Stop gradient animations."""
        if self._gradient_animation_id:
            self.after_cancel(self._gradient_animation_id)
            self._gradient_animation_id = None

    def _position_on_screen(self):
        """Position pill at bottom center of screen."""
        self.update_idletasks()

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        width, height = self.DIMENSIONS[self._state]
        margin = 80  # Distance from bottom

        x = (screen_width - width) // 2
        y = screen_height - margin - height

        self.geometry(f"{width}x{height}+{x}+{y}")

    def set_state(self, state: PillState, error_message: str = ""):
        """Set the pill state."""
        if state == self._state and state != PillState.RECORDING:
            return

        self._state = state
        self._error_message = error_message

        # Resize
        width, height = self.DIMENSIONS[state]
        x = self.winfo_x() + (self.winfo_width() - width) // 2
        y = self.winfo_y()
        self.geometry(f"{width}x{height}+{x}+{y}")

        # Update border color
        if state == PillState.RECORDING:
            self.pill.configure(border_color=COLORS["recording"])
        elif state == PillState.SUCCESS:
            self.pill.configure(border_color=COLORS["success"])
        elif state == PillState.ERROR:
            self.pill.configure(border_color=COLORS["error"])
        else:
            self.pill.configure(border_color=COLORS["border"])

        # Update content
        if state == PillState.IDLE:
            self._create_idle_content()
        elif state == PillState.RECORDING:
            self._create_recording_content()
        elif state == PillState.TRANSCRIBING:
            self._create_transcribing_content()
        elif state == PillState.PROCESSING:
            self._create_processing_content()
        elif state == PillState.SUCCESS:
            self._create_success_content()
            self.after(1500, lambda: self.set_state(PillState.IDLE))
        elif state == PillState.ERROR:
            self._create_error_content()
            self.after(3000, lambda: self.set_state(PillState.IDLE))

        logger.debug(f"Pill state: {state.name}")

    def get_state(self) -> PillState:
        """Get current state."""
        return self._state

    def update_audio_level(self, level: float):
        """Update audio visualizer level."""
        # Handled by animation
        pass

    def update_timer(self, seconds: int):
        """Update recording timer display."""
        if self._state == PillState.RECORDING and hasattr(self, 'timer'):
            minutes = seconds // 60
            secs = seconds % 60
            self.timer.configure(text=f"{minutes}:{secs:02d}")

    def show_error(self, message: str):
        """Show error state with message."""
        self.set_state(PillState.ERROR, error_message=message)

    def show_success(self):
        """Show success state."""
        self.set_state(PillState.SUCCESS)

    # Click and drag support
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
        """Handle mouse release - click if not dragging."""
        was_dragging = self._is_dragging
        self._click_pos = None
        self._is_dragging = False

        # Only trigger click if we didn't drag
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
