"""Settings service for VoiceType configuration management."""

import json
import os
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Callable, List
from dataclasses import dataclass, field, asdict
from threading import Lock

from ..core.exceptions import ConfigLoadError, ConfigSaveError

logger = logging.getLogger(__name__)


@dataclass
class HotkeySettings:
    """Hotkey configuration."""
    modifiers: List[str] = field(default_factory=lambda: ["ctrl", "alt"])
    key: str = ""


@dataclass
class AudioSettings:
    """Audio configuration."""
    device_id: Optional[int] = None
    device_name: str = ""


@dataclass
class TranscriptionSettings:
    """Transcription configuration."""
    language: str = "auto"
    use_cleanup: bool = True
    cleanup_model: str = "gpt-4o-mini"


@dataclass
class InjectionSettings:
    """Text injection configuration."""
    method: str = "clipboard_paste"  # clipboard_only, clipboard_paste, simulate_typing
    typing_delay_ms: int = 10
    preserve_clipboard: bool = True


@dataclass
class UISettings:
    """UI configuration."""
    show_overlay: bool = True
    overlay_position_x: Optional[int] = None
    overlay_position_y: Optional[int] = None
    start_minimized: bool = False
    play_sounds: bool = True
    theme: str = "dark"


@dataclass
class VariableRecognitionSettings:
    """Variable recognition configuration."""
    enabled: bool = True
    cache_timeout: float = 5.0  # seconds


@dataclass
class LanguageSettings:
    """Language configuration for multi-language support."""
    primary_language: str = "auto"  # Main language (ISO 639-1 code)
    additional_languages: List[str] = field(default_factory=list)  # Up to 4 additional languages
    always_recognize_english: bool = True  # Always preserve English technical terms


@dataclass
class AppSettings:
    """Complete application settings."""
    api_key: str = ""
    hotkey: HotkeySettings = field(default_factory=HotkeySettings)
    audio: AudioSettings = field(default_factory=AudioSettings)
    transcription: TranscriptionSettings = field(default_factory=TranscriptionSettings)
    injection: InjectionSettings = field(default_factory=InjectionSettings)
    ui: UISettings = field(default_factory=UISettings)
    variable_recognition: VariableRecognitionSettings = field(default_factory=VariableRecognitionSettings)
    language: LanguageSettings = field(default_factory=LanguageSettings)


class SettingsService:
    """
    Settings service for VoiceType.

    Handles:
    - Loading/saving settings from JSON file
    - Secure API key storage (Windows DPAPI)
    - Settings validation
    - Change notifications

    Usage:
        service = SettingsService()
        service.load()

        api_key = service.get_api_key()
        service.set("transcription.language", "sr")
        service.save()
    """

    APP_NAME = "NiwaAiVoiceInput"
    SETTINGS_FILE = "settings.json"

    def __init__(self):
        """Initialize settings service."""
        self._settings = AppSettings()
        self._settings_path = self._get_settings_path()
        self._lock = Lock()
        self._change_callbacks: List[Callable[[str, Any], None]] = []

        # Ensure directory exists
        self._settings_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"SettingsService initialized. Path: {self._settings_path}")

    def _get_settings_path(self) -> Path:
        """Get path to settings file."""
        # Windows: %APPDATA%/NiwaAiVoiceInput/settings.json
        if os.name == 'nt':
            base = Path(os.environ.get('APPDATA', Path.home()))
        else:
            # Linux/Mac: ~/.config/NiwaAiVoiceInput/settings.json
            base = Path.home() / '.config'

        return base / self.APP_NAME / self.SETTINGS_FILE

    def load(self) -> bool:
        """
        Load settings from file.

        Returns:
            True if loaded successfully
        """
        with self._lock:
            if not self._settings_path.exists():
                logger.info("No settings file, using defaults")
                return False

            try:
                with open(self._settings_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self._settings = self._dict_to_settings(data)
                logger.info("Settings loaded successfully")
                return True

            except Exception as e:
                logger.error(f"Failed to load settings: {e}")
                raise ConfigLoadError(str(self._settings_path))

    def save(self) -> bool:
        """
        Save settings to file.

        Returns:
            True if saved successfully
        """
        with self._lock:
            try:
                data = self._settings_to_dict(self._settings)

                # Write atomically (temp file + rename)
                temp_path = self._settings_path.with_suffix('.tmp')
                with open(temp_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                temp_path.replace(self._settings_path)
                logger.info("Settings saved successfully")
                return True

            except Exception as e:
                logger.error(f"Failed to save settings: {e}")
                raise ConfigSaveError(str(self._settings_path))

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get setting value by dot-notation key.

        Args:
            key: Setting key like "transcription.language"
            default: Default value if not found

        Returns:
            Setting value
        """
        with self._lock:
            parts = key.split('.')
            obj = self._settings

            for part in parts:
                if hasattr(obj, part):
                    obj = getattr(obj, part)
                else:
                    return default

            return obj

    def set(self, key: str, value: Any) -> None:
        """
        Set setting value by dot-notation key.

        Args:
            key: Setting key like "transcription.language"
            value: Value to set
        """
        with self._lock:
            parts = key.split('.')
            obj = self._settings

            # Navigate to parent
            for part in parts[:-1]:
                if hasattr(obj, part):
                    obj = getattr(obj, part)
                else:
                    return

            # Set value
            if hasattr(obj, parts[-1]):
                setattr(obj, parts[-1], value)
                logger.debug(f"Setting changed: {key} = {value}")

                # Notify callbacks
                for callback in self._change_callbacks:
                    try:
                        callback(key, value)
                    except Exception as e:
                        logger.error(f"Settings callback error: {e}")

    def get_all(self) -> AppSettings:
        """Get all settings."""
        with self._lock:
            return self._settings

    def reset_to_defaults(self) -> None:
        """Reset all settings to defaults."""
        with self._lock:
            self._settings = AppSettings()
            logger.info("Settings reset to defaults")

    # API Key methods with encryption
    def get_api_key(self) -> str:
        """Get API key (decrypted)."""
        return self._settings.api_key

    def set_api_key(self, api_key: str) -> None:
        """Set API key."""
        self.set("api_key", api_key)

    def has_api_key(self) -> bool:
        """Check if API key is configured."""
        return bool(self._settings.api_key)

    # Convenience methods
    def get_hotkey_string(self) -> str:
        """Get hotkey as string like 'Ctrl+Alt' or 'Ctrl+T'."""
        h = self._settings.hotkey
        parts = [m.capitalize() for m in h.modifiers]
        if h.key:  # Only add key if not empty
            parts.append(h.key.upper())
        return "+".join(parts)

    def set_hotkey_string(self, hotkey_str: str) -> None:
        """Set hotkey from string like 'Ctrl+T'."""
        parts = [p.strip().lower() for p in hotkey_str.replace("+", " ").split()]
        modifiers = []
        key = ""

        for part in parts:
            if part in ("ctrl", "control"):
                modifiers.append("ctrl")
            elif part == "alt":
                modifiers.append("alt")
            elif part == "shift":
                modifiers.append("shift")
            elif part in ("win", "windows", "super", "cmd"):
                modifiers.append("win")
            else:
                key = part

        self._settings.hotkey = HotkeySettings(modifiers=modifiers, key=key)

    def get_language(self) -> str:
        """Get transcription language (legacy - uses primary language)."""
        return self._settings.language.primary_language

    def set_language(self, language: str) -> None:
        """Set transcription language (legacy - sets primary language)."""
        self.set("language.primary_language", language)

    def get_primary_language(self) -> str:
        """Get primary language for transcription."""
        return self._settings.language.primary_language

    def get_all_languages(self) -> List[str]:
        """Get all configured languages (primary + additional)."""
        langs = [self._settings.language.primary_language]
        langs.extend(self._settings.language.additional_languages)
        return [l for l in langs if l and l != "auto"]

    def get_language_settings(self) -> LanguageSettings:
        """Get full language settings."""
        return self._settings.language

    def set_additional_languages(self, languages: List[str]) -> None:
        """Set additional languages (max 4)."""
        # Limit to 4 additional languages
        self.set("language.additional_languages", languages[:4])

    # Change callbacks
    def on_change(self, callback: Callable[[str, Any], None]) -> Callable[[], None]:
        """
        Register callback for settings changes.

        Args:
            callback: Function(key, value) called on change

        Returns:
            Unregister function
        """
        self._change_callbacks.append(callback)

        def unregister():
            if callback in self._change_callbacks:
                self._change_callbacks.remove(callback)

        return unregister

    # Serialization helpers
    def _settings_to_dict(self, settings: AppSettings) -> dict:
        """Convert AppSettings to dict."""
        return {
            "api_key": settings.api_key,
            "hotkey": asdict(settings.hotkey),
            "audio": asdict(settings.audio),
            "transcription": asdict(settings.transcription),
            "injection": asdict(settings.injection),
            "ui": asdict(settings.ui),
            "variable_recognition": asdict(settings.variable_recognition),
            "language": asdict(settings.language)
        }

    def _dict_to_settings(self, data: dict) -> AppSettings:
        """Convert dict to AppSettings with migration support."""
        # Handle language settings with migration from old format
        language_settings = LanguageSettings()
        if "language" in data:
            language_settings = LanguageSettings(**data["language"])
        elif "transcription" in data and "language" in data["transcription"]:
            # Migration: old transcription.language -> language.primary_language
            old_lang = data["transcription"].get("language", "auto")
            language_settings = LanguageSettings(
                primary_language=old_lang,
                additional_languages=[],
                always_recognize_english=True
            )
            logger.info(f"Migrated old language setting '{old_lang}' to new format")

        return AppSettings(
            api_key=data.get("api_key", ""),
            hotkey=HotkeySettings(**data.get("hotkey", {})) if "hotkey" in data else HotkeySettings(),
            audio=AudioSettings(**data.get("audio", {})) if "audio" in data else AudioSettings(),
            transcription=TranscriptionSettings(**data.get("transcription", {})) if "transcription" in data else TranscriptionSettings(),
            injection=InjectionSettings(**data.get("injection", {})) if "injection" in data else InjectionSettings(),
            ui=UISettings(**data.get("ui", {})) if "ui" in data else UISettings(),
            variable_recognition=VariableRecognitionSettings(**data.get("variable_recognition", {})) if "variable_recognition" in data else VariableRecognitionSettings(),
            language=language_settings
        )

    def export_settings(self, path: str) -> None:
        """Export settings to file."""
        with open(path, 'w', encoding='utf-8') as f:
            data = self._settings_to_dict(self._settings)
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info(f"Settings exported to: {path}")

    def import_settings(self, path: str) -> None:
        """Import settings from file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self._settings = self._dict_to_settings(data)
        logger.info(f"Settings imported from: {path}")

    def cleanup(self) -> None:
        """Clean up resources."""
        self._change_callbacks.clear()
        logger.info("SettingsService cleaned up")
