"""System Tray Service - Handles background tray icon."""

import logging
import threading
from typing import Optional, Callable
from PIL import Image, ImageDraw
import pystray

logger = logging.getLogger(__name__)


class SystemTrayService:
    """
    Manages system tray icon and menu.

    Allows app to run in background (system tray) instead of taskbar.
    """

    def __init__(self, app_name: str = "Architects Tool No.1"):
        """Initialize system tray service."""
        self._app_name = app_name
        self._icon: Optional[pystray.Icon] = None
        self._icon_thread: Optional[threading.Thread] = None
        self._on_show_callback: Optional[Callable] = None
        self._on_quit_callback: Optional[Callable] = None
        self._running = False

        logger.info("SystemTrayService initialized")

    def create_icon_image(self) -> Image.Image:
        """Create a simple icon image for the tray."""
        # Create a 64x64 image with a violet circle (matching app accent color)
        size = 64
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Draw violet circle (matching accent color #8b5cf6)
        padding = 8
        draw.ellipse(
            [padding, padding, size - padding, size - padding],
            fill=(139, 92, 246, 255),  # #8b5cf6
            outline=(255, 255, 255, 200),
            width=2
        )

        # Draw small "N" in center (for Niwa)
        # Simple representation using shapes
        center = size // 2
        n_width = 16
        n_height = 24
        n_thickness = 3

        # Left vertical line of "N"
        draw.rectangle(
            [center - n_width//2, center - n_height//2,
             center - n_width//2 + n_thickness, center + n_height//2],
            fill=(255, 255, 255, 255)
        )

        # Right vertical line of "N"
        draw.rectangle(
            [center + n_width//2 - n_thickness, center - n_height//2,
             center + n_width//2, center + n_height//2],
            fill=(255, 255, 255, 255)
        )

        # Diagonal line of "N"
        for i in range(n_height):
            x = center - n_width//2 + (n_width * i // n_height)
            y = center - n_height//2 + i
            draw.rectangle(
                [x, y, x + n_thickness, y + 1],
                fill=(255, 255, 255, 255)
            )

        return image

    def setup(self, on_show: Callable, on_quit: Callable, on_settings: Optional[Callable] = None):
        """
        Setup system tray with callbacks.

        Args:
            on_show: Callback to show/restore main window
            on_quit: Callback to quit application
            on_settings: Callback to show settings window
        """
        self._on_show_callback = on_show
        self._on_quit_callback = on_quit
        self._on_settings_callback = on_settings

        # Create icon image
        icon_image = self.create_icon_image()

        # Create menu
        menu_items = [
            pystray.MenuItem("Show", self._on_show, default=True),
        ]

        # Add settings if callback provided
        if on_settings:
            menu_items.append(pystray.MenuItem("Settings", self._on_settings))

        menu_items.append(pystray.MenuItem("Quit", self._on_quit))

        menu = pystray.Menu(*menu_items)

        # Create icon
        self._icon = pystray.Icon(
            self._app_name,
            icon_image,
            self._app_name,
            menu
        )

        logger.info("System tray icon created")

    def start(self):
        """Start the system tray icon (in background thread)."""
        if not self._icon:
            logger.error("Cannot start - icon not setup")
            return

        if self._running:
            logger.warning("System tray already running")
            return

        self._running = True

        # Run icon in separate thread so it doesn't block
        self._icon_thread = threading.Thread(
            target=self._run_icon,
            daemon=True
        )
        self._icon_thread.start()

        logger.info("System tray icon started")

    def _run_icon(self):
        """Run the icon (in separate thread)."""
        try:
            if self._icon:
                self._icon.run()
        except Exception as e:
            logger.error(f"System tray error: {e}")
            self._running = False

    def stop(self):
        """Stop the system tray icon."""
        if self._icon and self._running:
            try:
                self._running = False
                self._icon.stop()

                # Wait for thread to finish (with timeout)
                if self._icon_thread and self._icon_thread.is_alive():
                    self._icon_thread.join(timeout=1.0)
                    if self._icon_thread.is_alive():
                        logger.warning("System tray thread did not stop cleanly")

                self._icon = None
                self._icon_thread = None
                logger.info("System tray icon stopped")
            except Exception as e:
                logger.error(f"Error stopping system tray: {e}")
                # Force cleanup even on error
                self._running = False
                self._icon = None

    def _on_show(self, icon, item):
        """Handle Show menu item click."""
        if self._on_show_callback:
            self._on_show_callback()

    def _on_settings(self, icon, item):
        """Handle Settings menu item click."""
        if self._on_settings_callback:
            self._on_settings_callback()

    def _on_quit(self, icon, item):
        """Handle Quit menu item click."""
        if self._on_quit_callback:
            self._on_quit_callback()

    def cleanup(self):
        """Clean up resources."""
        self.stop()
        logger.info("SystemTrayService cleanup complete")
