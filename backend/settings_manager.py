"""
Settings Manager Module for VoiceType Application.

Handles loading, saving, and managing application settings.
Includes secure storage for API keys using Windows DPAPI encryption.
"""

import os
import json
import base64
import logging
import threading
from pathlib import Path
from typing import Optional, Any, Dict, TypeVar, Generic, Callable, List
from dataclasses import dataclass, field, asdict
from enum import Enum
import ctypes
from ctypes import wintypes

# Configure logging
logger = logging.getLogger(__name__)

# Type variable for generic settings
T = TypeVar('T')


# Windows DPAPI for secure storage
class DATA_BLOB(ctypes.Structure):
    """Windows DATA_BLOB structure for DPAPI."""
    _fields_ = [
        ('cbData', wintypes.DWORD),
        ('pbData', ctypes.POINTER(ctypes.c_char))
    ]


crypt32 = ctypes.windll.crypt32
kernel32 = ctypes.windll.kernel32

# DPAPI flags
CRYPTPROTECT_UI_FORBIDDEN = 0x01
CRYPTPROTECT_LOCAL_MACHINE = 0x04


class SettingsError(Exception):
    """Base exception for settings errors."""
    pass


class SettingsLoadError(SettingsError):
    """Raised when settings cannot be loaded."""
    pass


class SettingsSaveError(SettingsError):
    """Raised when settings cannot be saved."""
    pass


class SecureStorageError(SettingsError):
    """Raised for secure storage errors."""
    pass


class CleaningMode(str, Enum):
    """Text cleaning modes."""
    DEFAULT = "default"
    FORMAL = "formal"
    CASUAL = "casual"
    MINIMAL = "minimal"


class PasteMethod(str, Enum):
    """Methods for pasting text."""
    CTRL_V = "ctrl_v"
    SHIFT_INSERT = "shift_insert"
    TYPE = "type"


@dataclass
class AudioSettings:
    """Audio-related settings."""
    selected_device_index: Optional[int] = None
    sample_rate: int = 16000
    channels: int = 1
    max_recording_seconds: int = 300


@dataclass
class TranscriptionSettings:
    """Transcription-related settings."""
    language: str = "auto"  # "auto" for auto-detect
    whisper_model: str = "whisper-1"
    temperature: float = 0.0


@dataclass
class CleaningSettings:
    """Text cleaning settings."""
    enabled: bool = True
    mode: str = CleaningMode.DEFAULT.value
    gpt_model: str = "gpt-4o-mini"
    custom_prompt: Optional[str] = None


@dataclass
class HotkeySettings:
    """Hotkey settings."""
    record_hotkey: str = "Ctrl+T"
    cancel_hotkey: str = "Escape"


@dataclass
class OutputSettings:
    """Output behavior settings."""
    paste_method: str = PasteMethod.CTRL_V.value
    paste_delay: float = 0.1
    auto_paste: bool = True
    add_newline: bool = False
    restore_clipboard: bool = False


@dataclass
class UISettings:
    """User interface settings."""
    start_minimized: bool = False
    minimize_to_tray: bool = True
    show_notifications: bool = True
    theme: str = "system"  # "light", "dark", "system"
    window_position_x: Optional[int] = None
    window_position_y: Optional[int] = None


@dataclass
class AppSettings:
    """Complete application settings."""
    audio: AudioSettings = field(default_factory=AudioSettings)
    transcription: TranscriptionSettings = field(default_factory=TranscriptionSettings)
    cleaning: CleaningSettings = field(default_factory=CleaningSettings)
    hotkeys: HotkeySettings = field(default_factory=HotkeySettings)
    output: OutputSettings = field(default_factory=OutputSettings)
    ui: UISettings = field(default_factory=UISettings)

    # Metadata
    version: str = "1.0.0"
    first_run: bool = True


class SecureStorage:
    """
    Secure storage for sensitive data using Windows DPAPI.

    Encrypts data using the user's Windows credentials, making it
    inaccessible to other users or if the data is moved to another machine.
    """

    @staticmethod
    def encrypt(data: str) -> str:
        """
        Encrypt a string using DPAPI.

        Args:
            data: String to encrypt.

        Returns:
            Base64-encoded encrypted data.

        Raises:
            SecureStorageError: If encryption fails.
        """
        try:
            # Convert string to bytes
            data_bytes = data.encode('utf-8')

            # Create input blob
            input_blob = DATA_BLOB()
            input_blob.cbData = len(data_bytes)
            input_blob.pbData = ctypes.cast(
                ctypes.create_string_buffer(data_bytes),
                ctypes.POINTER(ctypes.c_char)
            )

            # Create output blob
            output_blob = DATA_BLOB()

            # Encrypt
            result = crypt32.CryptProtectData(
                ctypes.byref(input_blob),
                None,  # Description
                None,  # Optional entropy
                None,  # Reserved
                None,  # Prompt struct
                CRYPTPROTECT_UI_FORBIDDEN,
                ctypes.byref(output_blob)
            )

            if not result:
                error = kernel32.GetLastError()
                raise SecureStorageError(f"Encryption failed: error {error}")

            # Extract encrypted data
            encrypted_bytes = ctypes.string_at(
                output_blob.pbData,
                output_blob.cbData
            )

            # Free the memory allocated by CryptProtectData
            kernel32.LocalFree(output_blob.pbData)

            # Return as base64
            return base64.b64encode(encrypted_bytes).decode('ascii')

        except SecureStorageError:
            raise
        except Exception as e:
            raise SecureStorageError(f"Encryption error: {e}")

    @staticmethod
    def decrypt(encrypted_data: str) -> str:
        """
        Decrypt DPAPI-encrypted data.

        Args:
            encrypted_data: Base64-encoded encrypted string.

        Returns:
            Decrypted string.

        Raises:
            SecureStorageError: If decryption fails.
        """
        try:
            # Decode base64
            encrypted_bytes = base64.b64decode(encrypted_data.encode('ascii'))

            # Create input blob
            input_blob = DATA_BLOB()
            input_blob.cbData = len(encrypted_bytes)
            input_blob.pbData = ctypes.cast(
                ctypes.create_string_buffer(encrypted_bytes),
                ctypes.POINTER(ctypes.c_char)
            )

            # Create output blob
            output_blob = DATA_BLOB()

            # Decrypt
            result = crypt32.CryptUnprotectData(
                ctypes.byref(input_blob),
                None,  # Description out
                None,  # Optional entropy
                None,  # Reserved
                None,  # Prompt struct
                CRYPTPROTECT_UI_FORBIDDEN,
                ctypes.byref(output_blob)
            )

            if not result:
                error = kernel32.GetLastError()
                raise SecureStorageError(f"Decryption failed: error {error}")

            # Extract decrypted data
            decrypted_bytes = ctypes.string_at(
                output_blob.pbData,
                output_blob.cbData
            )

            # Free memory
            kernel32.LocalFree(output_blob.pbData)

            return decrypted_bytes.decode('utf-8')

        except SecureStorageError:
            raise
        except Exception as e:
            raise SecureStorageError(f"Decryption error: {e}")


class SettingsManager:
    """
    Manager for application settings.

    Features:
    - Load/save settings to JSON file
    - Secure API key storage using Windows DPAPI
    - Default values for all settings
    - Change callbacks for reactive updates
    - Thread-safe operations

    Example:
        manager = SettingsManager()
        manager.load()

        # Get settings
        hotkey = manager.settings.hotkeys.record_hotkey

        # Update settings
        manager.settings.hotkeys.record_hotkey = "Ctrl+R"
        manager.save()

        # Secure API key storage
        manager.set_api_key("sk-...")
        api_key = manager.get_api_key()
    """

    DEFAULT_SETTINGS_DIR = Path.home() / ".voicetype"
    SETTINGS_FILENAME = "settings.json"
    SECRETS_FILENAME = "secrets.dat"

    def __init__(
            self,
            settings_dir: Optional[Path] = None,
            auto_load: bool = True
    ):
        """
        Initialize settings manager.

        Args:
            settings_dir: Directory for settings files. Uses default if None.
            auto_load: Whether to automatically load settings on init.
        """
        self._settings_dir = Path(settings_dir) if settings_dir else self.DEFAULT_SETTINGS_DIR
        self._settings_file = self._settings_dir / self.SETTINGS_FILENAME
        self._secrets_file = self._settings_dir / self.SECRETS_FILENAME

        self._settings = AppSettings()
        self._lock = threading.RLock()

        # Change callbacks
        self._change_callbacks: List[Callable[[str, Any], None]] = []

        # Ensure settings directory exists
        self._settings_dir.mkdir(parents=True, exist_ok=True)

        if auto_load:
            self.load()

    @property
    def settings(self) -> AppSettings:
        """Get current settings."""
        return self._settings

    @property
    def settings_file(self) -> Path:
        """Get settings file path."""
        return self._settings_file

    def load(self) -> bool:
        """
        Load settings from file.

        Returns:
            True if settings were loaded, False if using defaults.
        """
        with self._lock:
            if not self._settings_file.exists():
                logger.info("Settings file not found, using defaults")
                self._settings = AppSettings()
                return False

            try:
                with open(self._settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self._settings = self._dict_to_settings(data)
                logger.info(f"Settings loaded from {self._settings_file}")
                return True

            except json.JSONDecodeError as e:
                logger.error(f"Invalid settings JSON: {e}")
                self._settings = AppSettings()
                return False

            except Exception as e:
                logger.error(f"Error loading settings: {e}")
                self._settings = AppSettings()
                return False

    def save(self) -> bool:
        """
        Save settings to file.

        Returns:
            True if settings were saved successfully.

        Raises:
            SettingsSaveError: If save fails.
        """
        with self._lock:
            try:
                data = self._settings_to_dict(self._settings)

                # Write atomically using temp file
                temp_file = self._settings_file.with_suffix('.tmp')

                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                # Replace original file
                temp_file.replace(self._settings_file)

                logger.info(f"Settings saved to {self._settings_file}")
                return True

            except Exception as e:
                logger.error(f"Error saving settings: {e}")
                raise SettingsSaveError(f"Failed to save settings: {e}")

    def _settings_to_dict(self, settings: AppSettings) -> Dict[str, Any]:
        """Convert settings dataclass to dictionary."""
        return {
            'audio': asdict(settings.audio),
            'transcription': asdict(settings.transcription),
            'cleaning': asdict(settings.cleaning),
            'hotkeys': asdict(settings.hotkeys),
            'output': asdict(settings.output),
            'ui': asdict(settings.ui),
            'version': settings.version,
            'first_run': settings.first_run,
        }

    def _dict_to_settings(self, data: Dict[str, Any]) -> AppSettings:
        """Convert dictionary to settings dataclass."""
        settings = AppSettings()

        if 'audio' in data:
            settings.audio = AudioSettings(**data['audio'])
        if 'transcription' in data:
            settings.transcription = TranscriptionSettings(**data['transcription'])
        if 'cleaning' in data:
            settings.cleaning = CleaningSettings(**data['cleaning'])
        if 'hotkeys' in data:
            settings.hotkeys = HotkeySettings(**data['hotkeys'])
        if 'output' in data:
            settings.output = OutputSettings(**data['output'])
        if 'ui' in data:
            settings.ui = UISettings(**data['ui'])

        settings.version = data.get('version', '1.0.0')
        settings.first_run = data.get('first_run', True)

        return settings

    def reset_to_defaults(self) -> None:
        """Reset all settings to default values."""
        with self._lock:
            self._settings = AppSettings()
            self._notify_change('all', None)

    def get_api_key(self) -> Optional[str]:
        """
        Get the stored API key (decrypted).

        Returns:
            API key string or None if not set.
        """
        with self._lock:
            if not self._secrets_file.exists():
                return None

            try:
                with open(self._secrets_file, 'r', encoding='utf-8') as f:
                    secrets = json.load(f)

                encrypted_key = secrets.get('api_key')
                if not encrypted_key:
                    return None

                return SecureStorage.decrypt(encrypted_key)

            except SecureStorageError as e:
                logger.error(f"Failed to decrypt API key: {e}")
                return None

            except Exception as e:
                logger.error(f"Error reading API key: {e}")
                return None

    def set_api_key(self, api_key: str) -> bool:
        """
        Store API key securely.

        Args:
            api_key: The OpenAI API key to store.

        Returns:
            True if stored successfully.
        """
        with self._lock:
            try:
                # Load existing secrets
                secrets = {}
                if self._secrets_file.exists():
                    with open(self._secrets_file, 'r', encoding='utf-8') as f:
                        secrets = json.load(f)

                # Encrypt and store
                encrypted_key = SecureStorage.encrypt(api_key)
                secrets['api_key'] = encrypted_key

                # Write atomically
                temp_file = self._secrets_file.with_suffix('.tmp')

                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(secrets, f)

                temp_file.replace(self._secrets_file)

                logger.info("API key stored securely")
                self._notify_change('api_key', '***')
                return True

            except Exception as e:
                logger.error(f"Failed to store API key: {e}")
                return False

    def has_api_key(self) -> bool:
        """Check if an API key is stored."""
        return self.get_api_key() is not None

    def clear_api_key(self) -> bool:
        """Remove stored API key."""
        with self._lock:
            try:
                if self._secrets_file.exists():
                    secrets = {}
                    with open(self._secrets_file, 'r', encoding='utf-8') as f:
                        secrets = json.load(f)

                    if 'api_key' in secrets:
                        del secrets['api_key']

                        with open(self._secrets_file, 'w', encoding='utf-8') as f:
                            json.dump(secrets, f)

                logger.info("API key cleared")
                self._notify_change('api_key', None)
                return True

            except Exception as e:
                logger.error(f"Failed to clear API key: {e}")
                return False

    def add_change_callback(
            self,
            callback: Callable[[str, Any], None]
    ) -> None:
        """
        Add a callback for settings changes.

        Callback receives (setting_name, new_value).

        Args:
            callback: Function to call on changes.
        """
        self._change_callbacks.append(callback)

    def remove_change_callback(
            self,
            callback: Callable[[str, Any], None]
    ) -> None:
        """Remove a change callback."""
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)

    def _notify_change(self, name: str, value: Any) -> None:
        """Notify callbacks of a setting change."""
        for callback in self._change_callbacks:
            try:
                callback(name, value)
            except Exception as e:
                logger.error(f"Change callback error: {e}")

    def update_setting(self, path: str, value: Any) -> bool:
        """
        Update a setting by path.

        Args:
            path: Dot-separated path like "audio.sample_rate".
            value: New value.

        Returns:
            True if updated successfully.
        """
        with self._lock:
            try:
                parts = path.split('.')
                obj = self._settings

                # Navigate to parent
                for part in parts[:-1]:
                    obj = getattr(obj, part)

                # Set value
                setattr(obj, parts[-1], value)

                self._notify_change(path, value)
                return True

            except AttributeError:
                logger.error(f"Invalid setting path: {path}")
                return False

    def get_setting(self, path: str) -> Any:
        """
        Get a setting by path.

        Args:
            path: Dot-separated path like "audio.sample_rate".

        Returns:
            Setting value or None if not found.
        """
        try:
            parts = path.split('.')
            obj = self._settings

            for part in parts:
                obj = getattr(obj, part)

            return obj

        except AttributeError:
            return None

    def export_settings(self, file_path: Path) -> bool:
        """
        Export settings to a file (without secrets).

        Args:
            file_path: Path to export to.

        Returns:
            True if exported successfully.
        """
        try:
            data = self._settings_to_dict(self._settings)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Settings exported to {file_path}")
            return True

        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False

    def import_settings(self, file_path: Path) -> bool:
        """
        Import settings from a file.

        Args:
            file_path: Path to import from.

        Returns:
            True if imported successfully.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            with self._lock:
                self._settings = self._dict_to_settings(data)
                self.save()

            logger.info(f"Settings imported from {file_path}")
            self._notify_change('all', None)
            return True

        except Exception as e:
            logger.error(f"Import failed: {e}")
            return False

    def mark_first_run_complete(self) -> None:
        """Mark that first run setup is complete."""
        self._settings.first_run = False
        self.save()


# Global settings instance (singleton pattern)
_global_settings: Optional[SettingsManager] = None


def get_settings() -> SettingsManager:
    """
    Get the global settings manager instance.

    Returns:
        Global SettingsManager instance.
    """
    global _global_settings
    if _global_settings is None:
        _global_settings = SettingsManager()
    return _global_settings


if __name__ == "__main__":
    print("Settings Manager Demo")
    print("-" * 40)

    # Create manager with custom path for demo
    demo_dir = Path.home() / ".voicetype_demo"
    manager = SettingsManager(settings_dir=demo_dir)

    # Show current settings
    print("\nCurrent Settings:")
    print(f"  Record Hotkey: {manager.settings.hotkeys.record_hotkey}")
    print(f"  Language: {manager.settings.transcription.language}")
    print(f"  Cleaning Mode: {manager.settings.cleaning.mode}")
    print(f"  Paste Method: {manager.settings.output.paste_method}")

    # Update a setting
    print("\nUpdating record hotkey to Ctrl+R...")
    manager.settings.hotkeys.record_hotkey = "Ctrl+R"
    manager.save()

    # Test API key storage
    print("\n--- API Key Storage Test ---")
    test_key = "sk-test-1234567890"

    print(f"Storing test API key...")
    if manager.set_api_key(test_key):
        print("API key stored successfully!")

        retrieved = manager.get_api_key()
        if retrieved == test_key:
            print("API key retrieval: PASSED")
        else:
            print("API key retrieval: FAILED")

        # Clean up
        manager.clear_api_key()
        print("API key cleared")

    # Using paths
    print("\n--- Path-based Access ---")
    print(f"Get audio.sample_rate: {manager.get_setting('audio.sample_rate')}")

    manager.update_setting('audio.sample_rate', 44100)
    print(f"Updated to: {manager.get_setting('audio.sample_rate')}")

    # Reset and clean up
    manager.reset_to_defaults()
    print("\nSettings reset to defaults")

    # Clean up demo directory
    import shutil
    shutil.rmtree(demo_dir, ignore_errors=True)
    print(f"\nDemo complete! (cleaned up {demo_dir})")
