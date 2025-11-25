"""Custom exceptions for VoiceType application."""

from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass


class ErrorSeverity(Enum):
    """Error severity levels."""
    INFO = "info"           # Informational, auto-dismiss
    WARNING = "warning"     # User should be aware
    ERROR = "error"         # Operation failed, recoverable
    CRITICAL = "critical"   # App may need restart


class ErrorCategory(Enum):
    """Error categories for grouping."""
    AUDIO = "audio"
    API = "api"
    TRANSCRIPTION = "transcription"
    INJECTION = "injection"
    HOTKEY = "hotkey"
    CONFIG = "config"
    SYSTEM = "system"


@dataclass
class ErrorInfo:
    """Rich error information for UI display."""

    code: str
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    user_message: str  # Friendly message for UI
    recovery_hint: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    original_exception: Optional[Exception] = None


class VoiceTypeError(Exception):
    """Base exception for VoiceType."""

    def __init__(
        self,
        message: str,
        code: str = "UNKNOWN_ERROR",
        category: ErrorCategory = ErrorCategory.SYSTEM,
        severity: ErrorSeverity = ErrorSeverity.ERROR,
        user_message: Optional[str] = None,
        recovery_hint: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.info = ErrorInfo(
            code=code,
            message=message,
            category=category,
            severity=severity,
            user_message=user_message or message,
            recovery_hint=recovery_hint,
            details=details or {}
        )

    def __str__(self) -> str:
        return f"[{self.info.code}] {self.info.message}"


# ============== Audio Errors ==============

class AudioError(VoiceTypeError):
    """Base class for audio-related errors."""

    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('category', ErrorCategory.AUDIO)
        super().__init__(message, **kwargs)


class AudioDeviceNotFoundError(AudioError):
    """Microphone device not found."""

    def __init__(self, device_name: str = ""):
        super().__init__(
            f"Audio device not found: {device_name}",
            code="AUDIO_DEVICE_NOT_FOUND",
            user_message="Mikrofon nije pronaden.",
            recovery_hint="Proverite da li je mikrofon povezan i pokusajte ponovo."
        )


class AudioPermissionDeniedError(AudioError):
    """Microphone access denied by system."""

    def __init__(self):
        super().__init__(
            "Microphone access denied",
            code="AUDIO_PERMISSION_DENIED",
            severity=ErrorSeverity.CRITICAL,
            user_message="Pristup mikrofonu je odbijen.",
            recovery_hint="Omogucite pristup mikrofonu u Windows podesavanjima > Privatnost > Mikrofon."
        )


class AudioRecordingError(AudioError):
    """Error during audio recording."""

    def __init__(self, message: str = "Recording failed"):
        super().__init__(
            message,
            code="AUDIO_RECORDING_ERROR",
            user_message="Greska pri snimanju zvuka.",
            recovery_hint="Pokusajte ponovo ili promenite mikrofon."
        )


class AudioTooShortError(AudioError):
    """Recorded audio too short."""

    def __init__(self, duration: float = 0):
        super().__init__(
            f"Audio too short: {duration:.1f}s (minimum 0.5s)",
            code="AUDIO_TOO_SHORT",
            severity=ErrorSeverity.INFO,
            user_message="Snimak je prekratak.",
            recovery_hint="Snimite duzi audio (minimum 0.5 sekundi).",
            details={"duration": duration}
        )


# ============== API Errors ==============

class APIError(VoiceTypeError):
    """Base class for API-related errors."""

    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('category', ErrorCategory.API)
        super().__init__(message, **kwargs)


class APIKeyMissingError(APIError):
    """API key not configured."""

    def __init__(self):
        super().__init__(
            "OpenAI API key not configured",
            code="API_KEY_MISSING",
            severity=ErrorSeverity.CRITICAL,
            user_message="API kljuc nije podesen.",
            recovery_hint="Unesite OpenAI API kljuc u podesavanjima."
        )


class APIKeyInvalidError(APIError):
    """API key is invalid."""

    def __init__(self):
        super().__init__(
            "Invalid OpenAI API key",
            code="API_KEY_INVALID",
            severity=ErrorSeverity.CRITICAL,
            user_message="API kljuc nije validan.",
            recovery_hint="Proverite API kljuc i pokusajte ponovo. Kljuc treba da pocinje sa 'sk-'."
        )


class APIRateLimitError(APIError):
    """API rate limit exceeded."""

    def __init__(self, retry_after: Optional[int] = None):
        hint = "Sacekajte malo i pokusajte ponovo."
        if retry_after:
            hint = f"Pokusajte ponovo za {retry_after} sekundi."

        super().__init__(
            "API rate limit exceeded",
            code="API_RATE_LIMIT",
            severity=ErrorSeverity.WARNING,
            user_message="Previse zahteva. Limit je prekoracen.",
            recovery_hint=hint,
            details={"retry_after": retry_after}
        )


class APIQuotaExceededError(APIError):
    """API quota exceeded."""

    def __init__(self):
        super().__init__(
            "API quota exceeded",
            code="API_QUOTA_EXCEEDED",
            severity=ErrorSeverity.CRITICAL,
            user_message="API kvota je istrosena.",
            recovery_hint="Proverite vas OpenAI nalog i dopunite kredit."
        )


class APINetworkError(APIError):
    """Network error when calling API."""

    def __init__(self, original: Optional[Exception] = None):
        super().__init__(
            f"Network error: {original}",
            code="API_NETWORK_ERROR",
            user_message="Greska u mrezi.",
            recovery_hint="Proverite internet konekciju i pokusajte ponovo.",
            details={"original": str(original) if original else None}
        )


class APITimeoutError(APIError):
    """API request timed out."""

    def __init__(self, timeout: float = 30):
        super().__init__(
            f"API request timed out after {timeout}s",
            code="API_TIMEOUT",
            user_message="Zahtev je istekao.",
            recovery_hint="Server ne odgovara. Pokusajte ponovo.",
            details={"timeout": timeout}
        )


# ============== Transcription Errors ==============

class TranscriptionError(VoiceTypeError):
    """Base class for transcription errors."""

    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('category', ErrorCategory.TRANSCRIPTION)
        super().__init__(message, **kwargs)


class TranscriptionEmptyError(TranscriptionError):
    """No speech detected in audio."""

    def __init__(self):
        super().__init__(
            "No speech detected in audio",
            code="TRANSCRIPTION_EMPTY",
            severity=ErrorSeverity.INFO,
            user_message="Govor nije prepoznat.",
            recovery_hint="Pokusajte ponovo i govorite glasnije i jasnije."
        )


class TranscriptionLanguageError(TranscriptionError):
    """Language not supported or detected incorrectly."""

    def __init__(self, language: str = ""):
        super().__init__(
            f"Language error: {language}",
            code="TRANSCRIPTION_LANGUAGE_ERROR",
            user_message="Greska sa jezikom.",
            recovery_hint="Izaberite jezik rucno u podesavanjima.",
            details={"language": language}
        )


# ============== Injection Errors ==============

class InjectionError(VoiceTypeError):
    """Base class for text injection errors."""

    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('category', ErrorCategory.INJECTION)
        super().__init__(message, **kwargs)


class ClipboardError(InjectionError):
    """Failed to copy to clipboard."""

    def __init__(self, message: str = "Clipboard operation failed"):
        super().__init__(
            message,
            code="CLIPBOARD_ERROR",
            user_message="Kopiranje u clipboard nije uspelo.",
            recovery_hint="Pokusajte ponovo."
        )


class PasteError(InjectionError):
    """Failed to paste text."""

    def __init__(self):
        super().__init__(
            "Failed to paste text",
            code="PASTE_ERROR",
            user_message="Lepljenje teksta nije uspelo.",
            recovery_hint="Tekst je kopiran u clipboard. Nalepite rucno sa Ctrl+V."
        )


# ============== Hotkey Errors ==============

class HotkeyError(VoiceTypeError):
    """Base class for hotkey errors."""

    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('category', ErrorCategory.HOTKEY)
        super().__init__(message, **kwargs)


class HotkeyRegistrationError(HotkeyError):
    """Failed to register hotkey."""

    def __init__(self, hotkey: str = ""):
        super().__init__(
            f"Failed to register hotkey: {hotkey}",
            code="HOTKEY_REGISTRATION_FAILED",
            user_message=f"Registracija precice '{hotkey}' nije uspela.",
            recovery_hint="Precica je mozda vec zauzeta. Izaberite drugu kombinaciju.",
            details={"hotkey": hotkey}
        )


class HotkeyConflictError(HotkeyError):
    """Hotkey conflicts with another application."""

    def __init__(self, hotkey: str = ""):
        super().__init__(
            f"Hotkey conflict: {hotkey}",
            code="HOTKEY_CONFLICT",
            user_message=f"Precica '{hotkey}' je zauzeta.",
            recovery_hint="Izaberite drugu kombinaciju tastera.",
            details={"hotkey": hotkey}
        )


# ============== Config Errors ==============

class ConfigError(VoiceTypeError):
    """Base class for configuration errors."""

    def __init__(self, message: str, **kwargs):
        kwargs.setdefault('category', ErrorCategory.CONFIG)
        super().__init__(message, **kwargs)


class ConfigLoadError(ConfigError):
    """Failed to load configuration."""

    def __init__(self, path: str = ""):
        super().__init__(
            f"Failed to load config from: {path}",
            code="CONFIG_LOAD_ERROR",
            user_message="Greska pri ucitavanju podesavanja.",
            recovery_hint="Podesavanja ce biti resetovana na podrazumevane vrednosti.",
            details={"path": path}
        )


class ConfigSaveError(ConfigError):
    """Failed to save configuration."""

    def __init__(self, path: str = ""):
        super().__init__(
            f"Failed to save config to: {path}",
            code="CONFIG_SAVE_ERROR",
            user_message="Greska pri cuvanju podesavanja.",
            recovery_hint="Proverite da li imate dozvole za pisanje.",
            details={"path": path}
        )
