"""Active Window Service - Detects developer applications."""

import logging
import ctypes
from ctypes import wintypes
from typing import Dict, List, Optional
import time

logger = logging.getLogger(__name__)


class ActiveWindowService:
    """
    Service for detecting active windows and identifying developer applications.

    Uses Windows API to get the currently focused window and determine if it's
    a code editor or IDE.
    """

    # List of known developer applications (case-insensitive)
    DEVELOPER_APPS = {
        "code.exe": "Visual Studio Code",
        "devenv.exe": "Visual Studio",
        "pycharm64.exe": "PyCharm",
        "idea64.exe": "IntelliJ IDEA",
        "sublime_text.exe": "Sublime Text",
        "notepad++.exe": "Notepad++",
        "atom.exe": "Atom",
        "webstorm64.exe": "WebStorm",
        "rider64.exe": "Rider",
        "eclipse.exe": "Eclipse",
        "vim.exe": "Vim",
        "gvim.exe": "GVim",
        "emacs.exe": "Emacs",
        "cursor.exe": "Cursor",
        "windsurf.exe": "Windsurf",
        "zed.exe": "Zed",
    }

    def __init__(self):
        """Initialize the active window service."""
        self._cache_timeout = 1.0  # Cache for 1 second
        self._cached_info: Optional[Dict] = None
        self._cache_time: float = 0

        logger.info("ActiveWindowService initialized")

    def get_active_window_info(self) -> Dict[str, str]:
        """
        Get information about the currently active window.

        Returns:
            Dictionary with:
                - window_title: Title of the active window
                - process_name: Name of the process (e.g., "code.exe")
                - app_name: Friendly name (e.g., "Visual Studio Code") or process name
                - is_developer_app: Boolean indicating if it's a known dev app
        """
        # Check cache
        current_time = time.time()
        if self._cached_info and (current_time - self._cache_time) < self._cache_timeout:
            return self._cached_info

        try:
            # Get foreground window handle
            hwnd = ctypes.windll.user32.GetForegroundWindow()

            if not hwnd:
                return self._create_empty_info()

            # Get window title
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            buff = ctypes.create_unicode_buffer(length + 1)
            ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
            window_title = buff.value

            # Get process ID
            pid = wintypes.DWORD()
            ctypes.windll.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

            # Get process name
            process_name = self._get_process_name(pid.value)

            # Check if it's a developer app
            process_lower = process_name.lower()
            is_dev_app = process_lower in self.DEVELOPER_APPS
            app_name = self.DEVELOPER_APPS.get(process_lower, process_name)

            info = {
                "window_title": window_title,
                "process_name": process_name,
                "app_name": app_name,
                "is_developer_app": is_dev_app
            }

            # Update cache
            self._cached_info = info
            self._cache_time = current_time

            return info

        except Exception as e:
            logger.error(f"Failed to get active window info: {e}")
            return self._create_empty_info()

    def _get_process_name(self, pid: int) -> str:
        """Get process name from PID."""
        try:
            # Windows constants
            PROCESS_QUERY_INFORMATION = 0x0400
            PROCESS_VM_READ = 0x0010

            # Open process
            hProcess = ctypes.windll.kernel32.OpenProcess(
                PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
                False,
                pid
            )

            if not hProcess:
                return ""

            try:
                # Get process name
                MAX_PATH = 260
                buff = ctypes.create_unicode_buffer(MAX_PATH)
                size = wintypes.DWORD(MAX_PATH)

                if ctypes.windll.kernel32.QueryFullProcessImageNameW(
                    hProcess, 0, buff, ctypes.byref(size)
                ):
                    full_path = buff.value
                    # Extract just the filename
                    return full_path.split("\\")[-1]

                return ""

            finally:
                ctypes.windll.kernel32.CloseHandle(hProcess)

        except Exception as e:
            logger.error(f"Failed to get process name for PID {pid}: {e}")
            return ""

    def is_developer_app_active(self) -> bool:
        """
        Check if the currently active window is a known developer application.

        Returns:
            True if a developer app is active, False otherwise
        """
        info = self.get_active_window_info()
        return info.get("is_developer_app", False)

    def _create_empty_info(self) -> Dict[str, str]:
        """Create empty window info dict."""
        return {
            "window_title": "",
            "process_name": "",
            "app_name": "",
            "is_developer_app": False
        }

    def cleanup(self) -> None:
        """Clean up resources."""
        self._cached_info = None
        logger.info("ActiveWindowService cleaned up")
