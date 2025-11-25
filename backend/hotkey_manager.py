"""
Hotkey Manager Module for VoiceType Application.

Handles global hotkey registration and callback management on Windows.
Supports configurable hotkey combinations and multiple simultaneous hotkeys.
"""

import threading
import logging
import time
from typing import Optional, Callable, Dict, Set, Tuple, Any
from dataclasses import dataclass, field
from enum import IntEnum
import ctypes
from ctypes import wintypes

# Configure logging
logger = logging.getLogger(__name__)


# Windows API Constants
class VirtualKeyCodes(IntEnum):
    """Windows Virtual Key Codes for common keys."""
    # Letters
    VK_A = 0x41
    VK_B = 0x42
    VK_C = 0x43
    VK_D = 0x44
    VK_E = 0x45
    VK_F = 0x46
    VK_G = 0x47
    VK_H = 0x48
    VK_I = 0x49
    VK_J = 0x4A
    VK_K = 0x4B
    VK_L = 0x4C
    VK_M = 0x4D
    VK_N = 0x4E
    VK_O = 0x4F
    VK_P = 0x50
    VK_Q = 0x51
    VK_R = 0x52
    VK_S = 0x53
    VK_T = 0x54
    VK_U = 0x55
    VK_V = 0x56
    VK_W = 0x57
    VK_X = 0x58
    VK_Y = 0x59
    VK_Z = 0x5A

    # Numbers
    VK_0 = 0x30
    VK_1 = 0x31
    VK_2 = 0x32
    VK_3 = 0x33
    VK_4 = 0x34
    VK_5 = 0x35
    VK_6 = 0x36
    VK_7 = 0x37
    VK_8 = 0x38
    VK_9 = 0x39

    # Function keys
    VK_F1 = 0x70
    VK_F2 = 0x71
    VK_F3 = 0x72
    VK_F4 = 0x73
    VK_F5 = 0x74
    VK_F6 = 0x75
    VK_F7 = 0x76
    VK_F8 = 0x77
    VK_F9 = 0x78
    VK_F10 = 0x79
    VK_F11 = 0x7A
    VK_F12 = 0x7B

    # Special keys
    VK_SPACE = 0x20
    VK_RETURN = 0x0D
    VK_ESCAPE = 0x1B
    VK_TAB = 0x09
    VK_BACK = 0x08
    VK_DELETE = 0x2E
    VK_INSERT = 0x2D
    VK_HOME = 0x24
    VK_END = 0x23
    VK_PRIOR = 0x21  # Page Up
    VK_NEXT = 0x22  # Page Down

    # Modifiers
    VK_SHIFT = 0x10
    VK_CONTROL = 0x11
    VK_MENU = 0x12  # Alt
    VK_LWIN = 0x5B
    VK_RWIN = 0x5C


class ModifierFlags(IntEnum):
    """Modifier key flags for RegisterHotKey."""
    MOD_NONE = 0x0000
    MOD_ALT = 0x0001
    MOD_CONTROL = 0x0002
    MOD_SHIFT = 0x0004
    MOD_WIN = 0x0008
    MOD_NOREPEAT = 0x4000  # Prevent repeat when held


# Windows API message constants
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012

# Load Windows DLLs
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


class HotkeyError(Exception):
    """Base exception for hotkey-related errors."""
    pass


class HotkeyRegistrationError(HotkeyError):
    """Raised when hotkey registration fails."""
    pass


class HotkeyAlreadyRegisteredError(HotkeyError):
    """Raised when hotkey is already registered (by this or another app)."""
    pass


@dataclass
class Hotkey:
    """Represents a registered hotkey."""
    id: int
    key: int  # Virtual key code
    modifiers: int  # Modifier flags
    callback: Callable[[], None]
    description: str = ""
    enabled: bool = True

    def __str__(self) -> str:
        parts = []
        if self.modifiers & ModifierFlags.MOD_CONTROL:
            parts.append("Ctrl")
        if self.modifiers & ModifierFlags.MOD_ALT:
            parts.append("Alt")
        if self.modifiers & ModifierFlags.MOD_SHIFT:
            parts.append("Shift")
        if self.modifiers & ModifierFlags.MOD_WIN:
            parts.append("Win")

        # Get key name
        key_name = self._get_key_name()
        parts.append(key_name)

        return "+".join(parts)

    def _get_key_name(self) -> str:
        """Get human-readable name for the key code."""
        # Check if it's a letter
        if 0x41 <= self.key <= 0x5A:
            return chr(self.key)
        # Check if it's a number
        if 0x30 <= self.key <= 0x39:
            return chr(self.key)
        # Check if it's a function key
        if 0x70 <= self.key <= 0x7B:
            return f"F{self.key - 0x70 + 1}"
        # Special keys
        special = {
            VirtualKeyCodes.VK_SPACE: "Space",
            VirtualKeyCodes.VK_RETURN: "Enter",
            VirtualKeyCodes.VK_ESCAPE: "Esc",
            VirtualKeyCodes.VK_TAB: "Tab",
            VirtualKeyCodes.VK_BACK: "Backspace",
            VirtualKeyCodes.VK_DELETE: "Delete",
            VirtualKeyCodes.VK_INSERT: "Insert",
            VirtualKeyCodes.VK_HOME: "Home",
            VirtualKeyCodes.VK_END: "End",
            VirtualKeyCodes.VK_PRIOR: "PageUp",
            VirtualKeyCodes.VK_NEXT: "PageDown",
        }
        return special.get(self.key, f"0x{self.key:02X}")


@dataclass
class HotkeyConfig:
    """Configuration for hotkey manager."""
    no_repeat: bool = True  # Prevent callback repeat when key held
    callback_in_thread: bool = True  # Run callbacks in separate threads


class HotkeyManager:
    """
    Manager for global Windows hotkeys.

    Features:
    - Register global hotkeys that work in any application
    - Configurable key combinations
    - Multiple hotkeys support
    - Thread-safe callback execution
    - Easy hotkey modification

    Example:
        manager = HotkeyManager()

        def on_record():
            print("Recording started!")

        # Register Ctrl+T for recording
        manager.register_hotkey(
            key=VirtualKeyCodes.VK_T,
            modifiers=ModifierFlags.MOD_CONTROL,
            callback=on_record,
            description="Start/Stop Recording"
        )

        manager.start()
        # ... application runs ...
        manager.stop()
    """

    def __init__(self, config: Optional[HotkeyConfig] = None):
        """
        Initialize the hotkey manager.

        Args:
            config: Optional configuration object.
        """
        self._config = config or HotkeyConfig()
        self._hotkeys: Dict[int, Hotkey] = {}
        self._next_id: int = 1
        self._id_lock = threading.Lock()

        # Message loop thread
        self._loop_thread: Optional[threading.Thread] = None
        self._running = False
        self._thread_id: Optional[int] = None

        # Callback for all hotkey events (for logging/monitoring)
        self._global_callback: Optional[Callable[[Hotkey], None]] = None

    def register_hotkey(
            self,
            key: int,
            modifiers: int = ModifierFlags.MOD_NONE,
            callback: Optional[Callable[[], None]] = None,
            description: str = ""
    ) -> int:
        """
        Register a global hotkey.

        Args:
            key: Virtual key code (use VirtualKeyCodes enum).
            modifiers: Modifier flags (Ctrl, Alt, Shift, Win).
            callback: Function to call when hotkey is pressed.
            description: Human-readable description.

        Returns:
            Hotkey ID for later reference.

        Raises:
            HotkeyRegistrationError: If registration fails.
            HotkeyAlreadyRegisteredError: If hotkey is already registered.
        """
        with self._id_lock:
            hotkey_id = self._next_id
            self._next_id += 1

        # Add no-repeat flag if configured
        final_modifiers = modifiers
        if self._config.no_repeat:
            final_modifiers |= ModifierFlags.MOD_NOREPEAT

        hotkey = Hotkey(
            id=hotkey_id,
            key=key,
            modifiers=final_modifiers,
            callback=callback or (lambda: None),
            description=description
        )

        # Register with Windows if manager is running
        if self._running and self._thread_id is not None:
            if not self._register_with_windows(hotkey):
                raise HotkeyRegistrationError(
                    f"Failed to register hotkey: {hotkey}"
                )

        self._hotkeys[hotkey_id] = hotkey
        logger.info(f"Registered hotkey: {hotkey} (ID: {hotkey_id})")

        return hotkey_id

    def register_hotkey_string(
            self,
            hotkey_string: str,
            callback: Optional[Callable[[], None]] = None,
            description: str = ""
    ) -> int:
        """
        Register a hotkey using a string like "Ctrl+T" or "Alt+Shift+R".

        Args:
            hotkey_string: String representation like "Ctrl+T".
            callback: Callback function.
            description: Description.

        Returns:
            Hotkey ID.

        Raises:
            ValueError: If string cannot be parsed.
        """
        key, modifiers = self.parse_hotkey_string(hotkey_string)
        return self.register_hotkey(key, modifiers, callback, description)

    def unregister_hotkey(self, hotkey_id: int) -> bool:
        """
        Unregister a hotkey.

        Args:
            hotkey_id: ID returned by register_hotkey.

        Returns:
            True if successfully unregistered.
        """
        if hotkey_id not in self._hotkeys:
            return False

        hotkey = self._hotkeys[hotkey_id]

        # Unregister from Windows if running
        if self._running:
            self._unregister_from_windows(hotkey)

        del self._hotkeys[hotkey_id]
        logger.info(f"Unregistered hotkey: {hotkey} (ID: {hotkey_id})")

        return True

    def update_hotkey(
            self,
            hotkey_id: int,
            key: Optional[int] = None,
            modifiers: Optional[int] = None,
            callback: Optional[Callable[[], None]] = None
    ) -> bool:
        """
        Update an existing hotkey's configuration.

        Args:
            hotkey_id: ID of hotkey to update.
            key: New key code (or None to keep current).
            modifiers: New modifiers (or None to keep current).
            callback: New callback (or None to keep current).

        Returns:
            True if successfully updated.
        """
        if hotkey_id not in self._hotkeys:
            return False

        hotkey = self._hotkeys[hotkey_id]

        # Unregister old hotkey
        if self._running:
            self._unregister_from_windows(hotkey)

        # Update values
        if key is not None:
            hotkey.key = key
        if modifiers is not None:
            final_modifiers = modifiers
            if self._config.no_repeat:
                final_modifiers |= ModifierFlags.MOD_NOREPEAT
            hotkey.modifiers = final_modifiers
        if callback is not None:
            hotkey.callback = callback

        # Re-register with new values
        if self._running:
            if not self._register_with_windows(hotkey):
                logger.error(f"Failed to re-register updated hotkey: {hotkey}")
                return False

        logger.info(f"Updated hotkey: {hotkey} (ID: {hotkey_id})")
        return True

    def enable_hotkey(self, hotkey_id: int) -> bool:
        """Enable a disabled hotkey."""
        if hotkey_id not in self._hotkeys:
            return False

        hotkey = self._hotkeys[hotkey_id]
        if hotkey.enabled:
            return True

        hotkey.enabled = True

        if self._running:
            return self._register_with_windows(hotkey)

        return True

    def disable_hotkey(self, hotkey_id: int) -> bool:
        """Disable a hotkey without unregistering it."""
        if hotkey_id not in self._hotkeys:
            return False

        hotkey = self._hotkeys[hotkey_id]
        if not hotkey.enabled:
            return True

        hotkey.enabled = False

        if self._running:
            self._unregister_from_windows(hotkey)

        return True

    def get_hotkey(self, hotkey_id: int) -> Optional[Hotkey]:
        """Get hotkey by ID."""
        return self._hotkeys.get(hotkey_id)

    def get_all_hotkeys(self) -> Dict[int, Hotkey]:
        """Get all registered hotkeys."""
        return dict(self._hotkeys)

    def set_global_callback(
            self,
            callback: Optional[Callable[[Hotkey], None]]
    ) -> None:
        """
        Set a callback that fires for ANY hotkey press.

        Useful for logging or debugging.

        Args:
            callback: Function receiving the Hotkey that was pressed.
        """
        self._global_callback = callback

    def _register_with_windows(self, hotkey: Hotkey) -> bool:
        """Register hotkey with Windows API."""
        result = user32.RegisterHotKey(
            None,  # No window handle (thread-level)
            hotkey.id,
            hotkey.modifiers,
            hotkey.key
        )

        if not result:
            error = kernel32.GetLastError()
            if error == 1409:  # ERROR_HOTKEY_ALREADY_REGISTERED
                logger.warning(f"Hotkey already registered: {hotkey}")
            else:
                logger.error(f"RegisterHotKey failed with error: {error}")
            return False

        return True

    def _unregister_from_windows(self, hotkey: Hotkey) -> bool:
        """Unregister hotkey from Windows API."""
        result = user32.UnregisterHotKey(None, hotkey.id)
        return bool(result)

    def start(self) -> bool:
        """
        Start the hotkey manager.

        Begins listening for registered hotkeys.

        Returns:
            True if started successfully.
        """
        if self._running:
            return True

        self._running = True

        # Start message loop thread
        self._loop_thread = threading.Thread(
            target=self._message_loop,
            daemon=True,
            name="HotkeyManager-MessageLoop"
        )
        self._loop_thread.start()

        # Wait for thread to initialize
        timeout = 2.0
        start_time = time.time()
        while self._thread_id is None and time.time() - start_time < timeout:
            time.sleep(0.01)

        if self._thread_id is None:
            self._running = False
            return False

        logger.info("Hotkey manager started")
        return True

    def stop(self) -> None:
        """Stop the hotkey manager."""
        if not self._running:
            return

        self._running = False

        # Post quit message to message loop thread
        if self._thread_id is not None:
            user32.PostThreadMessageW(self._thread_id, WM_QUIT, 0, 0)

        # Wait for thread to finish
        if self._loop_thread is not None:
            self._loop_thread.join(timeout=2.0)
            self._loop_thread = None

        self._thread_id = None
        logger.info("Hotkey manager stopped")

    def _message_loop(self) -> None:
        """Windows message loop for hotkey events."""
        # Get this thread's ID for posting messages
        self._thread_id = kernel32.GetCurrentThreadId()

        # Register all current hotkeys
        for hotkey in self._hotkeys.values():
            if hotkey.enabled:
                self._register_with_windows(hotkey)

        # Message structure
        msg = wintypes.MSG()

        while self._running:
            # GetMessage blocks until a message is available
            result = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)

            if result == -1:
                # Error
                break
            elif result == 0:
                # WM_QUIT received
                break

            if msg.message == WM_HOTKEY:
                hotkey_id = msg.wParam
                self._handle_hotkey(hotkey_id)

        # Unregister all hotkeys
        for hotkey in self._hotkeys.values():
            self._unregister_from_windows(hotkey)

    def _handle_hotkey(self, hotkey_id: int) -> None:
        """Handle hotkey press event."""
        hotkey = self._hotkeys.get(hotkey_id)

        if hotkey is None:
            return

        if not hotkey.enabled:
            return

        logger.debug(f"Hotkey pressed: {hotkey}")

        # Call global callback if set
        if self._global_callback:
            try:
                self._global_callback(hotkey)
            except Exception as e:
                logger.error(f"Global callback error: {e}")

        # Call hotkey's callback
        if hotkey.callback:
            if self._config.callback_in_thread:
                # Run callback in separate thread to not block message loop
                thread = threading.Thread(
                    target=self._safe_callback,
                    args=(hotkey.callback,),
                    daemon=True
                )
                thread.start()
            else:
                self._safe_callback(hotkey.callback)

    def _safe_callback(self, callback: Callable[[], None]) -> None:
        """Execute callback with error handling."""
        try:
            callback()
        except Exception as e:
            logger.error(f"Hotkey callback error: {e}")

    def is_running(self) -> bool:
        """Check if manager is running."""
        return self._running

    @staticmethod
    def parse_hotkey_string(hotkey_string: str) -> Tuple[int, int]:
        """
        Parse a hotkey string like "Ctrl+T" into key code and modifiers.

        Args:
            hotkey_string: String like "Ctrl+Shift+T" or "Alt+F1".

        Returns:
            Tuple of (key_code, modifiers).

        Raises:
            ValueError: If string cannot be parsed.
        """
        parts = [p.strip().lower() for p in hotkey_string.split("+")]

        modifiers = ModifierFlags.MOD_NONE
        key = None

        modifier_map = {
            "ctrl": ModifierFlags.MOD_CONTROL,
            "control": ModifierFlags.MOD_CONTROL,
            "alt": ModifierFlags.MOD_ALT,
            "shift": ModifierFlags.MOD_SHIFT,
            "win": ModifierFlags.MOD_WIN,
            "windows": ModifierFlags.MOD_WIN,
        }

        for part in parts:
            if part in modifier_map:
                modifiers |= modifier_map[part]
            elif len(part) == 1 and part.isalpha():
                key = ord(part.upper())
            elif len(part) == 1 and part.isdigit():
                key = ord(part)
            elif part.startswith("f") and part[1:].isdigit():
                f_num = int(part[1:])
                if 1 <= f_num <= 12:
                    key = 0x70 + f_num - 1
                else:
                    raise ValueError(f"Invalid function key: {part}")
            elif part == "space":
                key = VirtualKeyCodes.VK_SPACE
            elif part == "enter" or part == "return":
                key = VirtualKeyCodes.VK_RETURN
            elif part == "esc" or part == "escape":
                key = VirtualKeyCodes.VK_ESCAPE
            elif part == "tab":
                key = VirtualKeyCodes.VK_TAB
            elif part == "backspace":
                key = VirtualKeyCodes.VK_BACK
            elif part == "delete":
                key = VirtualKeyCodes.VK_DELETE
            else:
                raise ValueError(f"Unknown key: {part}")

        if key is None:
            raise ValueError("No main key specified in hotkey string")

        return key, modifiers

    @staticmethod
    def format_hotkey(key: int, modifiers: int) -> str:
        """
        Format key code and modifiers as a readable string.

        Args:
            key: Virtual key code.
            modifiers: Modifier flags.

        Returns:
            String like "Ctrl+Shift+T".
        """
        temp_hotkey = Hotkey(
            id=0,
            key=key,
            modifiers=modifiers,
            callback=lambda: None
        )
        return str(temp_hotkey)

    def __enter__(self) -> 'HotkeyManager':
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()

    def __del__(self) -> None:
        """Destructor."""
        self.stop()


# Convenience function for simple use cases
def create_default_recording_hotkey(
        callback: Callable[[], None],
        hotkey_string: str = "Ctrl+T"
) -> HotkeyManager:
    """
    Create a hotkey manager with default recording hotkey.

    Args:
        callback: Function to call when hotkey is pressed.
        hotkey_string: Hotkey combination (default: Ctrl+T).

    Returns:
        Running HotkeyManager instance.
    """
    manager = HotkeyManager()
    manager.register_hotkey_string(
        hotkey_string,
        callback=callback,
        description="Start/Stop Recording"
    )
    manager.start()
    return manager


if __name__ == "__main__":
    import sys

    print("Hotkey Manager Demo")
    print("-" * 40)

    recording = False

    def toggle_recording():
        global recording
        recording = not recording
        status = "RECORDING" if recording else "STOPPED"
        print(f"\n[{status}] Recording toggled!")

    print("Registering Ctrl+T hotkey...")
    print("Press Ctrl+T to toggle recording")
    print("Press Ctrl+C to exit\n")

    manager = HotkeyManager()

    # Register default hotkey
    hotkey_id = manager.register_hotkey_string(
        "Ctrl+T",
        callback=toggle_recording,
        description="Toggle Recording"
    )

    print(f"Registered: {manager.get_hotkey(hotkey_id)}")

    # Also register Alt+R as alternative
    alt_id = manager.register_hotkey_string(
        "Alt+R",
        callback=toggle_recording,
        description="Toggle Recording (Alt)"
    )

    print(f"Registered: {manager.get_hotkey(alt_id)}")

    manager.start()

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        manager.stop()
        print("Hotkey manager stopped.")
