"""Text injection service for clipboard and typing simulation."""

import time
import logging
from typing import Optional
from enum import Enum

import pyperclip

try:
    import pyautogui
    pyautogui.FAILSAFE = False
except ImportError:
    pyautogui = None

try:
    from pynput.keyboard import Key, Controller as KeyboardController
except ImportError:
    KeyboardController = None

from ..core.event_bus import EventBus, create_event
from ..core.events import EventType
from ..core.exceptions import ClipboardError, PasteError, InjectionError

logger = logging.getLogger(__name__)


class InjectionMethod(Enum):
    """Text injection methods."""
    CLIPBOARD_ONLY = "clipboard_only"      # Just copy, user pastes
    CLIPBOARD_PASTE = "clipboard_paste"    # Copy + Ctrl+V
    SIMULATE_TYPING = "simulate_typing"    # Type character by character


class TextInjectionService:
    """
    Text injection service for VoiceType.

    Handles:
    - Copying text to clipboard
    - Simulating paste (Ctrl+V)
    - Simulating typing
    - Preserving original clipboard content

    Usage:
        service = TextInjectionService()
        service.inject("Hello world", method=InjectionMethod.CLIPBOARD_PASTE)
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        """
        Initialize text injection service.

        Args:
            event_bus: EventBus for injection events
        """
        self._event_bus = event_bus or EventBus.get_instance()
        self._keyboard: Optional[KeyboardController] = None
        self._method = InjectionMethod.CLIPBOARD_PASTE
        self._typing_delay = 0.01  # Seconds between characters
        self._preserve_clipboard = True
        self._original_clipboard: Optional[str] = None

        if KeyboardController:
            self._keyboard = KeyboardController()

        logger.info("TextInjectionService initialized")

    def set_method(self, method: InjectionMethod) -> None:
        """Set the injection method."""
        self._method = method
        logger.info(f"Injection method: {method.value}")

    def set_typing_delay(self, delay: float) -> None:
        """Set delay between characters when typing."""
        self._typing_delay = max(0.001, delay)

    def set_preserve_clipboard(self, preserve: bool) -> None:
        """Set whether to preserve original clipboard content."""
        self._preserve_clipboard = preserve

    def inject(
        self,
        text: str,
        method: Optional[InjectionMethod] = None
    ) -> bool:
        """
        Inject text using specified or default method.

        Args:
            text: Text to inject
            method: Override injection method

        Returns:
            True if successful

        Raises:
            ClipboardError: If clipboard operation fails
            PasteError: If paste operation fails
        """
        if not text:
            logger.warning("Empty text, nothing to inject")
            return False

        use_method = method or self._method
        self._event_bus.emit(EventType.TEXT_INJECTION_STARTED, method=use_method.value)

        try:
            if use_method == InjectionMethod.CLIPBOARD_ONLY:
                result = self._copy_to_clipboard(text)
            elif use_method == InjectionMethod.CLIPBOARD_PASTE:
                result = self._copy_and_paste(text)
            else:  # SIMULATE_TYPING
                result = self._simulate_typing(text)

            if result:
                self._event_bus.emit(
                    EventType.TEXT_INJECTION_COMPLETE,
                    text=text,
                    method=use_method.value
                )
                logger.info(f"Text injected successfully via {use_method.value}")

            return result

        except Exception as e:
            self._event_bus.emit(EventType.TEXT_INJECTION_FAILED, error=str(e))
            raise

    def _copy_to_clipboard(self, text: str) -> bool:
        """Copy text to clipboard."""
        try:
            # Save original if preserving
            if self._preserve_clipboard:
                try:
                    self._original_clipboard = pyperclip.paste()
                except:
                    self._original_clipboard = None

            pyperclip.copy(text)
            logger.debug(f"Copied to clipboard: {len(text)} chars")
            return True

        except Exception as e:
            raise ClipboardError(f"Failed to copy: {e}")

    def _copy_and_paste(self, text: str) -> bool:
        """Copy text to clipboard and simulate Ctrl+V."""
        # Copy first
        self._copy_to_clipboard(text)

        # Small delay for clipboard to update
        time.sleep(0.05)

        # Simulate Ctrl+V
        try:
            if self._keyboard:
                # Using pynput
                self._keyboard.press(Key.ctrl)
                self._keyboard.press('v')
                self._keyboard.release('v')
                self._keyboard.release(Key.ctrl)
            elif pyautogui:
                # Fallback to pyautogui
                pyautogui.hotkey('ctrl', 'v')
            else:
                raise PasteError()

            logger.debug("Paste simulated")
            return True

        except Exception as e:
            logger.error(f"Paste failed: {e}")
            # Text is still in clipboard
            raise PasteError()

    def _simulate_typing(self, text: str) -> bool:
        """Simulate typing text character by character."""
        try:
            if pyautogui:
                # pyautogui handles Unicode better
                pyautogui.write(text, interval=self._typing_delay)
            elif self._keyboard:
                for char in text:
                    self._keyboard.type(char)
                    time.sleep(self._typing_delay)
            else:
                raise InjectionError("No typing backend available")

            logger.debug(f"Typed {len(text)} characters")
            return True

        except Exception as e:
            raise InjectionError(f"Typing failed: {e}")

    def restore_clipboard(self) -> None:
        """Restore original clipboard content if preserved."""
        if self._preserve_clipboard and self._original_clipboard is not None:
            try:
                pyperclip.copy(self._original_clipboard)
                logger.debug("Clipboard restored")
            except:
                pass
            finally:
                self._original_clipboard = None

    def get_clipboard(self) -> str:
        """Get current clipboard content."""
        try:
            return pyperclip.paste()
        except:
            return ""

    def cleanup(self) -> None:
        """Clean up resources."""
        self.restore_clipboard()
        logger.info("TextInjectionService cleaned up")
