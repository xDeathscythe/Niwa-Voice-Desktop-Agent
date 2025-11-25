"""Global hotkey service for VoiceType."""

import threading
import logging
from typing import Optional, Callable, Set, Dict, Any
from dataclasses import dataclass
from enum import Enum

try:
    from pynput import keyboard
    from pynput.keyboard import Key, KeyCode
except ImportError:
    keyboard = None

from ..core.event_bus import EventBus, create_event
from ..core.events import EventType
from ..core.exceptions import HotkeyRegistrationError, HotkeyConflictError

logger = logging.getLogger(__name__)


class ModifierKey(Enum):
    """Modifier keys."""
    CTRL = "ctrl"
    ALT = "alt"
    SHIFT = "shift"
    WIN = "win"


@dataclass
class HotkeyCombo:
    """Represents a hotkey combination."""
    modifiers: Set[ModifierKey]
    key: str

    def __str__(self) -> str:
        parts = []
        if ModifierKey.CTRL in self.modifiers:
            parts.append("Ctrl")
        if ModifierKey.ALT in self.modifiers:
            parts.append("Alt")
        if ModifierKey.SHIFT in self.modifiers:
            parts.append("Shift")
        if ModifierKey.WIN in self.modifiers:
            parts.append("Win")
        parts.append(self.key.upper())
        return " + ".join(parts)

    @classmethod
    def from_string(cls, s: str) -> 'HotkeyCombo':
        """Parse hotkey from string like 'Ctrl+T' or 'Ctrl + Shift + A'."""
        parts = [p.strip().lower() for p in s.replace("+", " ").split()]
        modifiers = set()
        key = ""

        for part in parts:
            if part in ("ctrl", "control"):
                modifiers.add(ModifierKey.CTRL)
            elif part == "alt":
                modifiers.add(ModifierKey.ALT)
            elif part == "shift":
                modifiers.add(ModifierKey.SHIFT)
            elif part in ("win", "windows", "super", "cmd"):
                modifiers.add(ModifierKey.WIN)
            else:
                key = part

        return cls(modifiers=modifiers, key=key)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "modifiers": [m.value for m in self.modifiers],
            "key": self.key
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'HotkeyCombo':
        """Create from dictionary."""
        modifiers = {ModifierKey(m) for m in d.get("modifiers", [])}
        return cls(modifiers=modifiers, key=d.get("key", ""))


class HotkeyService:
    """
    Global hotkey service for VoiceType.

    Listens for keyboard shortcuts system-wide and triggers callbacks.

    Usage:
        service = HotkeyService()
        service.set_hotkey(HotkeyCombo.from_string("Ctrl+T"))
        service.set_callback(my_callback)
        service.start()
    """

    DEFAULT_HOTKEY = HotkeyCombo(modifiers={ModifierKey.CTRL}, key="t")

    def __init__(self, event_bus: Optional[EventBus] = None):
        """
        Initialize hotkey service.

        Args:
            event_bus: EventBus for hotkey events
        """
        if keyboard is None:
            raise ImportError("pynput is required. Install with: pip install pynput")

        self._event_bus = event_bus or EventBus.get_instance()
        self._hotkey = self.DEFAULT_HOTKEY
        self._callback: Optional[Callable[[], None]] = None
        self._listener: Optional[keyboard.Listener] = None
        self._is_running = False
        self._pressed_keys: Set[Any] = set()
        self._lock = threading.Lock()

        # For capturing new hotkey
        self._capturing = False
        self._capture_callback: Optional[Callable[[HotkeyCombo], None]] = None

        logger.info("HotkeyService initialized")

    def set_hotkey(self, hotkey: HotkeyCombo) -> None:
        """
        Set the hotkey combination.

        Args:
            hotkey: HotkeyCombo to use
        """
        old_hotkey = self._hotkey
        self._hotkey = hotkey
        logger.info(f"Hotkey changed: {old_hotkey} -> {hotkey}")

        self._event_bus.emit(
            EventType.HOTKEY_CHANGED,
            old_hotkey=str(old_hotkey),
            new_hotkey=str(hotkey)
        )

    def get_hotkey(self) -> HotkeyCombo:
        """Get current hotkey combination."""
        return self._hotkey

    def set_callback(self, callback: Callable[[], None]) -> None:
        """
        Set callback to execute when hotkey is pressed.

        Args:
            callback: Function to call
        """
        self._callback = callback

    def start(self) -> None:
        """Start listening for hotkeys."""
        if self._is_running:
            return

        try:
            self._listener = keyboard.Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release
            )
            self._listener.start()
            self._is_running = True
            logger.info(f"Hotkey listener started: {self._hotkey}")

        except Exception as e:
            raise HotkeyRegistrationError(str(self._hotkey))

    def stop(self) -> None:
        """Stop listening for hotkeys."""
        if not self._is_running:
            return

        if self._listener:
            self._listener.stop()
            self._listener = None

        self._is_running = False
        self._pressed_keys.clear()
        logger.info("Hotkey listener stopped")

    def is_running(self) -> bool:
        """Check if listener is running."""
        return self._is_running

    def start_capture(self, callback: Callable[[HotkeyCombo], None]) -> None:
        """
        Start capturing a new hotkey combination.

        Args:
            callback: Called with captured HotkeyCombo
        """
        self._capturing = True
        self._capture_callback = callback
        self._pressed_keys.clear()
        logger.debug("Hotkey capture started")

    def stop_capture(self) -> None:
        """Stop capturing hotkey."""
        self._capturing = False
        self._capture_callback = None
        self._pressed_keys.clear()

    def _on_key_press(self, key) -> None:
        """Handle key press event."""
        with self._lock:
            self._pressed_keys.add(key)

            if self._capturing:
                self._handle_capture()
            else:
                self._check_hotkey()

    def _on_key_release(self, key) -> None:
        """Handle key release event."""
        with self._lock:
            self._pressed_keys.discard(key)

            # Emit release event if was recording
            if not self._capturing and self._is_hotkey_combo_pressed():
                self._event_bus.emit(EventType.HOTKEY_RELEASED)

    def _check_hotkey(self) -> None:
        """Check if current pressed keys match the hotkey."""
        if not self._hotkey:
            return

        # Check modifiers
        modifiers_ok = True
        for mod in self._hotkey.modifiers:
            if mod == ModifierKey.CTRL:
                if not any(self._is_ctrl(k) for k in self._pressed_keys):
                    modifiers_ok = False
            elif mod == ModifierKey.ALT:
                if not any(self._is_alt(k) for k in self._pressed_keys):
                    modifiers_ok = False
            elif mod == ModifierKey.SHIFT:
                if not any(self._is_shift(k) for k in self._pressed_keys):
                    modifiers_ok = False
            elif mod == ModifierKey.WIN:
                if not any(self._is_win(k) for k in self._pressed_keys):
                    modifiers_ok = False

        if not modifiers_ok:
            return

        # Check main key
        main_key = self._hotkey.key.lower()
        key_pressed = False

        for k in self._pressed_keys:
            if isinstance(k, KeyCode):
                if k.char and k.char.lower() == main_key:
                    key_pressed = True
                    break
            elif hasattr(k, 'name') and k.name.lower() == main_key:
                key_pressed = True
                break

        if key_pressed:
            logger.debug(f"Hotkey triggered: {self._hotkey}")
            self._event_bus.emit(EventType.HOTKEY_PRESSED, hotkey=str(self._hotkey))

            if self._callback:
                try:
                    self._callback()
                except Exception as e:
                    logger.error(f"Hotkey callback error: {e}")

    def _handle_capture(self) -> None:
        """Handle hotkey capture mode."""
        modifiers = set()
        key = ""

        for k in self._pressed_keys:
            if self._is_ctrl(k):
                modifiers.add(ModifierKey.CTRL)
            elif self._is_alt(k):
                modifiers.add(ModifierKey.ALT)
            elif self._is_shift(k):
                modifiers.add(ModifierKey.SHIFT)
            elif self._is_win(k):
                modifiers.add(ModifierKey.WIN)
            elif isinstance(k, KeyCode) and k.char:
                key = k.char.lower()
            elif hasattr(k, 'name'):
                # Handle special keys like F1-F12
                name = k.name.lower()
                if name.startswith('f') and name[1:].isdigit():
                    key = name

        # Need at least one modifier and one key
        if modifiers and key:
            combo = HotkeyCombo(modifiers=modifiers, key=key)
            self._capturing = False

            if self._capture_callback:
                self._capture_callback(combo)
                self._capture_callback = None

            logger.debug(f"Captured hotkey: {combo}")

    def _is_hotkey_combo_pressed(self) -> bool:
        """Check if hotkey combination is currently pressed."""
        return len(self._pressed_keys) > 0

    @staticmethod
    def _is_ctrl(key) -> bool:
        """Check if key is Ctrl."""
        return key in (Key.ctrl, Key.ctrl_l, Key.ctrl_r)

    @staticmethod
    def _is_alt(key) -> bool:
        """Check if key is Alt."""
        return key in (Key.alt, Key.alt_l, Key.alt_r, Key.alt_gr)

    @staticmethod
    def _is_shift(key) -> bool:
        """Check if key is Shift."""
        return key in (Key.shift, Key.shift_l, Key.shift_r)

    @staticmethod
    def _is_win(key) -> bool:
        """Check if key is Win/Super."""
        return key in (Key.cmd, Key.cmd_l, Key.cmd_r)

    def cleanup(self) -> None:
        """Clean up resources."""
        self.stop()
        logger.info("HotkeyService cleaned up")
