"""
Clipboard Manager Module for VoiceType Application.

Handles Windows clipboard operations including copying text,
retrieving clipboard content, and simulating paste operations.
"""

import time
import ctypes
import logging
import threading
from typing import Optional, Callable
from dataclasses import dataclass
from enum import IntEnum
from ctypes import wintypes

# Configure logging
logger = logging.getLogger(__name__)


# Windows API Constants
class ClipboardFormats(IntEnum):
    """Standard Windows clipboard formats."""
    CF_TEXT = 1
    CF_BITMAP = 2
    CF_METAFILEPICT = 3
    CF_SYLK = 4
    CF_DIF = 5
    CF_TIFF = 6
    CF_OEMTEXT = 7
    CF_DIB = 8
    CF_PALETTE = 9
    CF_PENDATA = 10
    CF_RIFF = 11
    CF_WAVE = 12
    CF_UNICODETEXT = 13
    CF_ENHMETAFILE = 14
    CF_HDROP = 15
    CF_LOCALE = 16
    CF_DIBV5 = 17


class VirtualKeyCodes(IntEnum):
    """Virtual key codes for keyboard simulation."""
    VK_CONTROL = 0x11
    VK_V = 0x56
    VK_C = 0x43
    VK_SHIFT = 0x10
    VK_INSERT = 0x2D


class KeyEventFlags(IntEnum):
    """Flags for keybd_event function."""
    KEYEVENTF_KEYDOWN = 0x0000
    KEYEVENTF_KEYUP = 0x0002
    KEYEVENTF_EXTENDEDKEY = 0x0001


# Memory allocation constants
GMEM_MOVEABLE = 0x0002
GMEM_ZEROINIT = 0x0040

# Load Windows DLLs
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Set up function signatures for better error handling
user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL

user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = wintypes.BOOL

user32.EmptyClipboard.argtypes = []
user32.EmptyClipboard.restype = wintypes.BOOL

user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype = wintypes.HANDLE

user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
user32.SetClipboardData.restype = wintypes.HANDLE

user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
user32.IsClipboardFormatAvailable.restype = wintypes.BOOL

kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = wintypes.HANDLE

kernel32.GlobalLock.argtypes = [wintypes.HANDLE]
kernel32.GlobalLock.restype = wintypes.LPVOID

kernel32.GlobalUnlock.argtypes = [wintypes.HANDLE]
kernel32.GlobalUnlock.restype = wintypes.BOOL

kernel32.GlobalSize.argtypes = [wintypes.HANDLE]
kernel32.GlobalSize.restype = ctypes.c_size_t


class ClipboardError(Exception):
    """Base exception for clipboard operations."""
    pass


class ClipboardOpenError(ClipboardError):
    """Raised when clipboard cannot be opened."""
    pass


class ClipboardWriteError(ClipboardError):
    """Raised when clipboard write fails."""
    pass


class ClipboardReadError(ClipboardError):
    """Raised when clipboard read fails."""
    pass


@dataclass
class ClipboardConfig:
    """Configuration for clipboard manager."""
    open_retry_count: int = 5  # Retries for opening clipboard
    open_retry_delay: float = 0.05  # Seconds between retries
    paste_key_delay: float = 0.05  # Delay between key events
    restore_after_paste: bool = False  # Restore clipboard after paste


class ClipboardManager:
    """
    Manager for Windows clipboard operations.

    Provides thread-safe clipboard operations including:
    - Copying text to clipboard
    - Reading text from clipboard
    - Simulating paste (Ctrl+V)
    - Clipboard content backup/restore

    Thread-safe implementation with proper resource management.

    Example:
        manager = ClipboardManager()

        # Copy text
        manager.copy_text("Hello, World!")

        # Paste at cursor
        manager.paste()

        # Or do both
        manager.copy_and_paste("Hello, World!")
    """

    def __init__(self, config: Optional[ClipboardConfig] = None):
        """
        Initialize clipboard manager.

        Args:
            config: Optional configuration object.
        """
        self._config = config or ClipboardConfig()
        self._lock = threading.Lock()

        # Callback for clipboard changes
        self._change_callback: Optional[Callable[[str], None]] = None

    def copy_text(self, text: str) -> bool:
        """
        Copy text to the Windows clipboard.

        Args:
            text: Text to copy.

        Returns:
            True if successful.

        Raises:
            ClipboardOpenError: If clipboard cannot be opened.
            ClipboardWriteError: If write fails.
        """
        if not text:
            return False

        with self._lock:
            return self._copy_text_internal(text)

    def _copy_text_internal(self, text: str) -> bool:
        """Internal implementation of copy_text."""
        # Encode text as UTF-16 (Windows Unicode format)
        text_bytes = (text + '\0').encode('utf-16-le')

        # Allocate global memory
        h_mem = kernel32.GlobalAlloc(
            GMEM_MOVEABLE | GMEM_ZEROINIT,
            len(text_bytes)
        )

        if not h_mem:
            raise ClipboardWriteError("Failed to allocate memory")

        try:
            # Lock memory and copy text
            ptr = kernel32.GlobalLock(h_mem)
            if not ptr:
                raise ClipboardWriteError("Failed to lock memory")

            try:
                ctypes.memmove(ptr, text_bytes, len(text_bytes))
            finally:
                kernel32.GlobalUnlock(h_mem)

            # Open clipboard with retries
            if not self._open_clipboard():
                raise ClipboardOpenError("Failed to open clipboard")

            try:
                # Clear clipboard
                if not user32.EmptyClipboard():
                    raise ClipboardWriteError("Failed to clear clipboard")

                # Set clipboard data
                result = user32.SetClipboardData(
                    ClipboardFormats.CF_UNICODETEXT,
                    h_mem
                )

                if not result:
                    raise ClipboardWriteError("Failed to set clipboard data")

                # Memory is now owned by clipboard - don't free it
                h_mem = None

                logger.debug(f"Copied {len(text)} chars to clipboard")
                return True

            finally:
                user32.CloseClipboard()

        finally:
            # Free memory only if we still own it (error case)
            if h_mem:
                kernel32.GlobalFree(h_mem)

    def get_text(self) -> Optional[str]:
        """
        Get text from the Windows clipboard.

        Returns:
            Clipboard text, or None if clipboard doesn't contain text.

        Raises:
            ClipboardOpenError: If clipboard cannot be opened.
            ClipboardReadError: If read fails.
        """
        with self._lock:
            return self._get_text_internal()

    def _get_text_internal(self) -> Optional[str]:
        """Internal implementation of get_text."""
        # Check if text is available
        if not user32.IsClipboardFormatAvailable(ClipboardFormats.CF_UNICODETEXT):
            return None

        if not self._open_clipboard():
            raise ClipboardOpenError("Failed to open clipboard")

        try:
            h_data = user32.GetClipboardData(ClipboardFormats.CF_UNICODETEXT)

            if not h_data:
                return None

            ptr = kernel32.GlobalLock(h_data)

            if not ptr:
                raise ClipboardReadError("Failed to lock clipboard data")

            try:
                # Get size of data
                size = kernel32.GlobalSize(h_data)

                # Read data as wide string
                text = ctypes.wstring_at(ptr, size // 2)

                # Remove null terminator if present
                if text and text[-1] == '\0':
                    text = text[:-1]

                return text

            finally:
                kernel32.GlobalUnlock(h_data)

        finally:
            user32.CloseClipboard()

    def _open_clipboard(self) -> bool:
        """
        Open clipboard with retries.

        Returns:
            True if clipboard was opened.
        """
        for attempt in range(self._config.open_retry_count):
            if user32.OpenClipboard(None):
                return True
            time.sleep(self._config.open_retry_delay)

        return False

    def clear(self) -> bool:
        """
        Clear the clipboard.

        Returns:
            True if successful.
        """
        with self._lock:
            if not self._open_clipboard():
                return False

            try:
                return bool(user32.EmptyClipboard())
            finally:
                user32.CloseClipboard()

    def has_text(self) -> bool:
        """
        Check if clipboard contains text.

        Returns:
            True if clipboard has text content.
        """
        return bool(
            user32.IsClipboardFormatAvailable(ClipboardFormats.CF_UNICODETEXT) or
            user32.IsClipboardFormatAvailable(ClipboardFormats.CF_TEXT)
        )

    def paste(self, method: str = "ctrl_v") -> bool:
        """
        Simulate paste operation at current cursor position.

        Args:
            method: Paste method - "ctrl_v" or "shift_insert".

        Returns:
            True if paste was simulated.
        """
        if method == "shift_insert":
            return self._simulate_shift_insert()
        else:
            return self._simulate_ctrl_v()

    def _simulate_ctrl_v(self) -> bool:
        """Simulate Ctrl+V key combination."""
        try:
            delay = self._config.paste_key_delay

            # Press Ctrl
            user32.keybd_event(
                VirtualKeyCodes.VK_CONTROL,
                0,
                KeyEventFlags.KEYEVENTF_KEYDOWN,
                0
            )
            time.sleep(delay)

            # Press V
            user32.keybd_event(
                VirtualKeyCodes.VK_V,
                0,
                KeyEventFlags.KEYEVENTF_KEYDOWN,
                0
            )
            time.sleep(delay)

            # Release V
            user32.keybd_event(
                VirtualKeyCodes.VK_V,
                0,
                KeyEventFlags.KEYEVENTF_KEYUP,
                0
            )
            time.sleep(delay)

            # Release Ctrl
            user32.keybd_event(
                VirtualKeyCodes.VK_CONTROL,
                0,
                KeyEventFlags.KEYEVENTF_KEYUP,
                0
            )

            logger.debug("Simulated Ctrl+V paste")
            return True

        except Exception as e:
            logger.error(f"Failed to simulate Ctrl+V: {e}")
            return False

    def _simulate_shift_insert(self) -> bool:
        """Simulate Shift+Insert key combination."""
        try:
            delay = self._config.paste_key_delay

            # Press Shift
            user32.keybd_event(
                VirtualKeyCodes.VK_SHIFT,
                0,
                KeyEventFlags.KEYEVENTF_KEYDOWN,
                0
            )
            time.sleep(delay)

            # Press Insert
            user32.keybd_event(
                VirtualKeyCodes.VK_INSERT,
                0,
                KeyEventFlags.KEYEVENTF_EXTENDEDKEY | KeyEventFlags.KEYEVENTF_KEYDOWN,
                0
            )
            time.sleep(delay)

            # Release Insert
            user32.keybd_event(
                VirtualKeyCodes.VK_INSERT,
                0,
                KeyEventFlags.KEYEVENTF_EXTENDEDKEY | KeyEventFlags.KEYEVENTF_KEYUP,
                0
            )
            time.sleep(delay)

            # Release Shift
            user32.keybd_event(
                VirtualKeyCodes.VK_SHIFT,
                0,
                KeyEventFlags.KEYEVENTF_KEYUP,
                0
            )

            logger.debug("Simulated Shift+Insert paste")
            return True

        except Exception as e:
            logger.error(f"Failed to simulate Shift+Insert: {e}")
            return False

    def copy_and_paste(
            self,
            text: str,
            paste_delay: float = 0.1,
            method: str = "ctrl_v"
    ) -> bool:
        """
        Copy text to clipboard and immediately paste it.

        This is the main function for VoiceType - it puts transcribed
        text into the clipboard and pastes it at the cursor position.

        Args:
            text: Text to copy and paste.
            paste_delay: Delay between copy and paste (seconds).
            method: Paste method.

        Returns:
            True if both operations succeeded.
        """
        if not text:
            return False

        # Optionally backup current clipboard
        backup = None
        if self._config.restore_after_paste:
            backup = self.get_text()

        # Copy new text
        if not self.copy_text(text):
            return False

        # Small delay to ensure clipboard is ready
        time.sleep(paste_delay)

        # Simulate paste
        result = self.paste(method)

        # Optionally restore clipboard
        if self._config.restore_after_paste and backup is not None:
            time.sleep(paste_delay)
            self.copy_text(backup)

        return result

    def type_text(self, text: str, char_delay: float = 0.01) -> bool:
        """
        Type text character by character using keyboard simulation.

        This is an alternative to copy/paste that works in more scenarios
        but is slower.

        Args:
            text: Text to type.
            char_delay: Delay between characters (seconds).

        Returns:
            True if completed.
        """
        if not text:
            return False

        try:
            for char in text:
                # Get virtual key code for character
                vk = user32.VkKeyScanW(ord(char))

                if vk == -1:
                    # Character not directly typeable - skip
                    continue

                key_code = vk & 0xFF
                shift_needed = bool(vk & 0x100)

                if shift_needed:
                    user32.keybd_event(
                        VirtualKeyCodes.VK_SHIFT,
                        0,
                        KeyEventFlags.KEYEVENTF_KEYDOWN,
                        0
                    )

                # Press key
                user32.keybd_event(key_code, 0, KeyEventFlags.KEYEVENTF_KEYDOWN, 0)
                time.sleep(char_delay / 2)

                # Release key
                user32.keybd_event(key_code, 0, KeyEventFlags.KEYEVENTF_KEYUP, 0)

                if shift_needed:
                    user32.keybd_event(
                        VirtualKeyCodes.VK_SHIFT,
                        0,
                        KeyEventFlags.KEYEVENTF_KEYUP,
                        0
                    )

                time.sleep(char_delay / 2)

            logger.debug(f"Typed {len(text)} characters")
            return True

        except Exception as e:
            logger.error(f"Failed to type text: {e}")
            return False

    def set_change_callback(
            self,
            callback: Optional[Callable[[str], None]]
    ) -> None:
        """
        Set callback for clipboard content changes.

        Note: This requires a message loop to be running.
        For VoiceType, clipboard monitoring is optional.

        Args:
            callback: Function receiving new clipboard text.
        """
        self._change_callback = callback


class ClipboardContext:
    """
    Context manager for clipboard operations with automatic backup/restore.

    Example:
        with ClipboardContext() as cb:
            cb.set_text("temporary text")
            cb.paste()
        # Original clipboard content is restored
    """

    def __init__(self):
        self._manager = ClipboardManager()
        self._backup: Optional[str] = None

    def __enter__(self) -> 'ClipboardContext':
        """Backup current clipboard on enter."""
        self._backup = self._manager.get_text()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Restore clipboard on exit."""
        if self._backup is not None:
            time.sleep(0.1)  # Small delay before restore
            self._manager.copy_text(self._backup)

    def set_text(self, text: str) -> bool:
        """Set clipboard text."""
        return self._manager.copy_text(text)

    def get_text(self) -> Optional[str]:
        """Get clipboard text."""
        return self._manager.get_text()

    def paste(self, method: str = "ctrl_v") -> bool:
        """Simulate paste."""
        return self._manager.paste(method)


# Convenience functions
def copy(text: str) -> bool:
    """
    Simple function to copy text to clipboard.

    Args:
        text: Text to copy.

    Returns:
        True if successful.
    """
    manager = ClipboardManager()
    return manager.copy_text(text)


def paste() -> bool:
    """
    Simple function to simulate paste.

    Returns:
        True if successful.
    """
    manager = ClipboardManager()
    return manager.paste()


def get_clipboard() -> Optional[str]:
    """
    Simple function to get clipboard text.

    Returns:
        Clipboard text or None.
    """
    manager = ClipboardManager()
    return manager.get_text()


def copy_and_paste(text: str) -> bool:
    """
    Simple function to copy and paste text.

    Args:
        text: Text to copy and paste.

    Returns:
        True if successful.
    """
    manager = ClipboardManager()
    return manager.copy_and_paste(text)


if __name__ == "__main__":
    print("Clipboard Manager Demo")
    print("-" * 40)

    manager = ClipboardManager()

    # Test copy
    test_text = "Hello from VoiceType! Zdravo iz VoiceType-a!"
    print(f"\nCopying: {test_text}")

    if manager.copy_text(test_text):
        print("Copy successful!")

        # Test read
        read_text = manager.get_text()
        print(f"Read back: {read_text}")

        # Verify
        if read_text == test_text:
            print("Verification: PASSED")
        else:
            print("Verification: FAILED")

    # Test with context manager
    print("\n--- Context Manager Test ---")
    original = manager.get_text()
    print(f"Original clipboard: {original[:50]}..." if original else "Empty")

    with ClipboardContext() as cb:
        cb.set_text("Temporary test content")
        temp = cb.get_text()
        print(f"Temporary content: {temp}")

    restored = manager.get_text()
    print(f"Restored: {restored[:50]}..." if restored else "Empty")

    # Test paste (commented out to avoid unwanted paste)
    print("\n--- Paste Test ---")
    print("To test paste, uncomment the paste code and have a text field focused")
    # manager.copy_and_paste("Test paste: Zdravo!")

    print("\nDemo complete!")
