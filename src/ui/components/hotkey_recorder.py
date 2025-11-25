"""Hotkey recorder component for capturing keyboard shortcuts."""

import customtkinter as ctk
from typing import Callable, Optional, Set
import threading

from ..styles.theme import COLORS

try:
    from pynput import keyboard
    from pynput.keyboard import Key, KeyCode
except ImportError:
    keyboard = None


class HotkeyRecorder(ctk.CTkFrame):
    """
    Hotkey recorder widget.

    Allows users to capture and display keyboard shortcuts.

    Usage:
        recorder = HotkeyRecorder(parent)
        recorder.pack()

        recorder.set_hotkey("Ctrl+T")
        recorder.set_callback(on_hotkey_changed)
    """

    def __init__(
        self,
        master,
        initial_hotkey: str = "Ctrl+T",
        on_change: Optional[Callable[[str], None]] = None,
        **kwargs
    ):
        """
        Initialize hotkey recorder.

        Args:
            master: Parent widget
            initial_hotkey: Initial hotkey string
            on_change: Callback when hotkey changes
        """
        super().__init__(
            master,
            fg_color=COLORS["bg_dark"],
            corner_radius=8,
            **kwargs
        )

        self._hotkey = initial_hotkey
        self._on_change = on_change
        self._recording = False
        self._pressed_keys: Set = set()
        self._listener: Optional[keyboard.Listener] = None

        self._create_widgets()

    def _create_widgets(self):
        """Create internal widgets."""
        # Container
        self.container = ctk.CTkFrame(
            self,
            fg_color="transparent",
            height=52
        )
        self.container.pack(fill="x", padx=2, pady=2)

        # Keys display frame
        self.keys_frame = ctk.CTkFrame(
            self.container,
            fg_color=COLORS["bg_dark"],
            corner_radius=8
        )
        self.keys_frame.pack(fill="x", padx=8, pady=8)

        # Display current hotkey
        self._update_display()

        # Click to record
        self.keys_frame.bind("<Button-1>", self._start_recording)
        self.container.bind("<Button-1>", self._start_recording)

    def _update_display(self):
        """Update the hotkey display."""
        # Clear existing
        for widget in self.keys_frame.winfo_children():
            widget.destroy()

        # Parse hotkey
        parts = self._parse_hotkey(self._hotkey)

        # Create key badges
        keys_container = ctk.CTkFrame(
            self.keys_frame,
            fg_color="transparent"
        )
        keys_container.pack(expand=True, pady=10)

        for i, key in enumerate(parts):
            if i > 0:
                # Plus sign between keys
                plus_label = ctk.CTkLabel(
                    keys_container,
                    text="+",
                    text_color=COLORS["text_muted"],
                    font=("Segoe UI", 14)
                )
                plus_label.pack(side="left", padx=4)

            # Key badge
            badge = ctk.CTkLabel(
                keys_container,
                text=key,
                fg_color=COLORS["bg_light"],
                corner_radius=6,
                text_color=COLORS["text_primary"],
                font=("Segoe UI", 13, "bold"),
                padx=12,
                pady=4
            )
            badge.pack(side="left")

        # Instruction text
        if self._recording:
            instruction = "Press keys..."
            color = COLORS["primary"]
        else:
            instruction = "Click to change"
            color = COLORS["text_muted"]

        hint_label = ctk.CTkLabel(
            self.keys_frame,
            text=instruction,
            text_color=color,
            font=("Segoe UI", 11)
        )
        hint_label.pack(pady=(0, 8))

    def _parse_hotkey(self, hotkey: str) -> list:
        """Parse hotkey string into parts."""
        # Handle common formats
        hotkey = hotkey.replace("+", " + ")
        parts = [p.strip() for p in hotkey.split("+") if p.strip()]
        return [p.capitalize() for p in parts]

    def _start_recording(self, event=None):
        """Start recording a new hotkey."""
        if self._recording:
            return

        self._recording = True
        self._pressed_keys.clear()
        self._update_display()

        # Update visual state
        self.keys_frame.configure(
            border_color=COLORS["primary"],
            border_width=2
        )

        # Start keyboard listener
        if keyboard:
            self._listener = keyboard.Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release
            )
            self._listener.start()

        # Also bind to focus out
        self.keys_frame.bind("<FocusOut>", self._stop_recording)

    def _stop_recording(self, event=None):
        """Stop recording."""
        if not self._recording:
            return

        self._recording = False

        # Stop listener
        if self._listener:
            self._listener.stop()
            self._listener = None

        # Reset visual state
        self.keys_frame.configure(
            border_color=COLORS["border"],
            border_width=0
        )

        self._update_display()

    def _on_key_press(self, key):
        """Handle key press during recording."""
        if not self._recording:
            return

        self._pressed_keys.add(key)
        self._check_combo()

    def _on_key_release(self, key):
        """Handle key release during recording."""
        if not self._recording:
            return

        # If we have a valid combo, stop recording
        if self._has_valid_combo():
            self._finalize_hotkey()

        self._pressed_keys.discard(key)

    def _check_combo(self):
        """Check if current pressed keys form a valid hotkey."""
        # Need at least one modifier and one regular key
        modifiers = []
        regular_key = None

        for key in self._pressed_keys:
            if self._is_modifier(key):
                mod_name = self._get_modifier_name(key)
                if mod_name and mod_name not in modifiers:
                    modifiers.append(mod_name)
            else:
                regular_key = self._get_key_name(key)

        if modifiers and regular_key:
            # Update display with current combo
            combo_parts = modifiers + [regular_key]
            self._hotkey = "+".join(combo_parts)
            self._update_display()

    def _has_valid_combo(self) -> bool:
        """Check if we have a valid hotkey combination."""
        has_modifier = any(self._is_modifier(k) for k in self._pressed_keys)
        has_key = any(not self._is_modifier(k) for k in self._pressed_keys)
        return has_modifier and has_key

    def _finalize_hotkey(self):
        """Finalize the recorded hotkey."""
        self._stop_recording()

        if self._on_change:
            self._on_change(self._hotkey)

    def _is_modifier(self, key) -> bool:
        """Check if key is a modifier."""
        return key in (
            Key.ctrl, Key.ctrl_l, Key.ctrl_r,
            Key.alt, Key.alt_l, Key.alt_r, Key.alt_gr,
            Key.shift, Key.shift_l, Key.shift_r,
            Key.cmd, Key.cmd_l, Key.cmd_r
        )

    def _get_modifier_name(self, key) -> Optional[str]:
        """Get modifier name."""
        if key in (Key.ctrl, Key.ctrl_l, Key.ctrl_r):
            return "Ctrl"
        elif key in (Key.alt, Key.alt_l, Key.alt_r, Key.alt_gr):
            return "Alt"
        elif key in (Key.shift, Key.shift_l, Key.shift_r):
            return "Shift"
        elif key in (Key.cmd, Key.cmd_l, Key.cmd_r):
            return "Win"
        return None

    def _get_key_name(self, key) -> Optional[str]:
        """Get key name for display."""
        if isinstance(key, KeyCode):
            if key.char:
                return key.char.upper()
        elif hasattr(key, 'name'):
            name = key.name
            # Handle function keys
            if name.startswith('f') and name[1:].isdigit():
                return name.upper()
            # Handle special keys
            special_keys = {
                'space': 'Space',
                'enter': 'Enter',
                'tab': 'Tab',
                'backspace': 'Backspace',
                'delete': 'Delete',
                'escape': 'Esc',
                'home': 'Home',
                'end': 'End',
                'page_up': 'PgUp',
                'page_down': 'PgDn',
                'insert': 'Insert',
                'print_screen': 'PrtSc',
                'pause': 'Pause',
            }
            return special_keys.get(name, name.capitalize())
        return None

    def set_hotkey(self, hotkey: str):
        """Set the hotkey programmatically."""
        self._hotkey = hotkey
        self._update_display()

    def get_hotkey(self) -> str:
        """Get the current hotkey string."""
        return self._hotkey

    def set_callback(self, callback: Callable[[str], None]):
        """Set the change callback."""
        self._on_change = callback
