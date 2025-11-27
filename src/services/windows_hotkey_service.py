"""Windows hotkey service - PUSH-TO-TALK using pure GetAsyncKeyState polling."""

import logging
import threading
import ctypes
from ctypes import wintypes
from typing import Callable, Optional, List
import time

logger = logging.getLogger(__name__)

# Virtual key codes for modifiers
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt key
VK_SHIFT = 0x10
VK_LWIN = 0x5B

VK_CODES = {
    'a': 0x41, 'b': 0x42, 'c': 0x43, 'd': 0x44, 'e': 0x45,
    'f': 0x46, 'g': 0x47, 'h': 0x48, 'i': 0x49, 'j': 0x4A,
    'k': 0x4B, 'l': 0x4C, 'm': 0x4D, 'n': 0x4E, 'o': 0x4F,
    'p': 0x50, 'q': 0x51, 'r': 0x52, 's': 0x53, 't': 0x54,
    'u': 0x55, 'v': 0x56, 'w': 0x57, 'x': 0x58, 'y': 0x59,
    'z': 0x5A,
    '0': 0x30, '1': 0x31, '2': 0x32, '3': 0x33, '4': 0x34,
    '5': 0x35, '6': 0x36, '7': 0x37, '8': 0x38, '9': 0x39,
    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73,
    'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77,
    'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
}


class WindowsHotkeyService:
    """Windows hotkey service - PUSH-TO-TALK using pure key polling."""

    def __init__(self):
        self._registered = False
        self._on_press_callback: Optional[Callable] = None
        self._on_release_callback: Optional[Callable] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._is_pressed = False
        self._vk_keys_to_check = []
        self._debounce_time = 0.1  # 100ms debounce

        self.user32 = ctypes.windll.user32
        logger.info("WindowsHotkeyService initialized (PURE POLLING)")

    def register(self, modifiers: List[str], key: str, on_press: Callable, on_release: Callable) -> bool:
        if self._registered:
            logger.warning("Hotkey already registered")
            return False

        # Collect VK codes for polling
        self._vk_keys_to_check = []

        for mod in modifiers:
            if mod.lower() in ('ctrl', 'control'):
                self._vk_keys_to_check.append(VK_CONTROL)
            elif mod.lower() == 'alt':
                self._vk_keys_to_check.append(VK_MENU)
            elif mod.lower() == 'shift':
                self._vk_keys_to_check.append(VK_SHIFT)
            elif mod.lower() in ('win', 'windows', 'super'):
                self._vk_keys_to_check.append(VK_LWIN)

        # Add regular key if specified
        if key:
            vk_code = VK_CODES.get(key.lower(), 0)
            if vk_code == 0:
                logger.error(f"Unknown key: {key}")
                return False
            self._vk_keys_to_check.append(vk_code)

        # Store callbacks
        self._on_press_callback = on_press
        self._on_release_callback = on_release

        # Start polling thread
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._poll_keys, daemon=True)
        self._thread.start()

        self._registered = True

        hotkey_parts = modifiers + ([key] if key else [])
        hotkey_str = "+".join(hotkey_parts)
        logger.info(f"✓ Hotkey polling started: {hotkey_str}")
        return True

    def unregister(self) -> bool:
        if not self._registered:
            return True

        try:
            self._stop_event.set()

            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2.0)
                if self._thread.is_alive():
                    logger.warning("Hotkey thread did not stop cleanly")

            self._thread = None
            self._registered = False
            self._on_press_callback = None
            self._on_release_callback = None
            self._vk_keys_to_check = []

            logger.info("Hotkey polling stopped")
            return True

        except Exception as e:
            logger.error(f"Failed to unregister: {e}")
            # Force cleanup even on error
            self._registered = False
            return False

    def _poll_keys(self):
        """Continuously poll for key state changes."""
        try:
            logger.debug("Key polling started...")
            last_state = False

            while not self._stop_event.is_set():
                # Check if ALL keys are pressed
                all_pressed = True
                for vk_code in self._vk_keys_to_check:
                    state = self.user32.GetAsyncKeyState(vk_code)
                    if not (state & 0x8000):  # Key not pressed
                        all_pressed = False
                        break

                # State changed from not pressed to pressed
                if all_pressed and not last_state:
                    logger.info("✓ Keys PRESSED - Starting recording...")
                    last_state = True
                    self._is_pressed = True

                    if self._on_press_callback:
                        try:
                            self._on_press_callback()
                        except Exception as e:
                            logger.error(f"Press callback error: {e}")

                    # Wait debounce time to ensure recording actually starts
                    time.sleep(self._debounce_time)

                # State changed from pressed to not pressed
                elif not all_pressed and last_state:
                    logger.info("✓ Keys RELEASED - Stopping recording...")
                    last_state = False
                    self._is_pressed = False

                    if self._on_release_callback:
                        try:
                            self._on_release_callback()
                        except Exception as e:
                            logger.error(f"Release callback error: {e}")

                # Poll every 50ms
                time.sleep(0.05)

            logger.debug("Key polling stopped")

        except Exception as e:
            logger.error(f"Polling error: {e}", exc_info=True)

    def is_registered(self) -> bool:
        return self._registered

    def cleanup(self):
        self.unregister()
        logger.info("WindowsHotkeyService cleaned up")
