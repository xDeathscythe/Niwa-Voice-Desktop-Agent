"""Event type definitions for VoiceType application."""

from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime


class EventType(Enum):
    """All application event types."""

    # Hotkey Events
    HOTKEY_PRESSED = "hotkey_pressed"
    HOTKEY_RELEASED = "hotkey_released"
    HOTKEY_CHANGED = "hotkey_changed"

    # Recording Events
    RECORDING_STARTED = "recording_started"
    RECORDING_STOPPED = "recording_stopped"
    RECORDING_CANCELLED = "recording_cancelled"
    AUDIO_LEVEL_UPDATE = "audio_level_update"

    # Transcription Events
    TRANSCRIPTION_STARTED = "transcription_started"
    TRANSCRIPTION_COMPLETE = "transcription_complete"
    TRANSCRIPTION_FAILED = "transcription_failed"

    # LLM Processing Events
    LLM_PROCESSING_STARTED = "llm_processing_started"
    LLM_PROCESSING_COMPLETE = "llm_processing_complete"
    LLM_PROCESSING_FAILED = "llm_processing_failed"

    # Text Injection Events
    TEXT_INJECTION_STARTED = "text_injection_started"
    TEXT_INJECTION_COMPLETE = "text_injection_complete"
    TEXT_INJECTION_FAILED = "text_injection_failed"

    # State Events
    STATE_CHANGED = "state_changed"

    # Settings Events
    SETTINGS_CHANGED = "settings_changed"
    SETTINGS_LOADED = "settings_loaded"
    SETTINGS_SAVED = "settings_saved"

    # Error Events
    ERROR_OCCURRED = "error_occurred"

    # Application Events
    APP_STARTED = "app_started"
    APP_SHUTTING_DOWN = "app_shutting_down"
    APP_MINIMIZED = "app_minimized"
    APP_RESTORED = "app_restored"


@dataclass
class Event:
    """Base event class with timestamp and data."""

    type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.data is None:
            self.data = {}

    def get(self, key: str, default: Any = None) -> Any:
        """Get data value by key."""
        return self.data.get(key, default)

    def __repr__(self) -> str:
        return f"Event({self.type.value}, data={self.data})"


def create_event(event_type: EventType, **kwargs) -> Event:
    """Factory function for creating events with data."""
    return Event(type=event_type, data=kwargs)


# Specialized Event Classes
@dataclass
class AudioLevelEvent(Event):
    """Audio level update event."""

    level: float = 0.0

    def __post_init__(self):
        self.type = EventType.AUDIO_LEVEL_UPDATE
        self.data = {"level": self.level}
        super().__post_init__()


@dataclass
class StateChangedEvent(Event):
    """State change event."""

    old_state: Optional['State'] = None
    new_state: Optional['State'] = None
    trigger: str = ""

    def __post_init__(self):
        self.type = EventType.STATE_CHANGED
        self.data = {
            "old_state": self.old_state,
            "new_state": self.new_state,
            "trigger": self.trigger
        }
        super().__post_init__()


@dataclass
class TranscriptionCompleteEvent(Event):
    """Transcription complete event."""

    text: str = ""
    raw_text: str = ""
    language: str = ""
    duration: float = 0.0

    def __post_init__(self):
        self.type = EventType.TRANSCRIPTION_COMPLETE
        self.data = {
            "text": self.text,
            "raw_text": self.raw_text,
            "language": self.language,
            "duration": self.duration
        }
        super().__post_init__()


@dataclass
class ErrorEvent(Event):
    """Error occurred event."""

    error_code: str = ""
    message: str = ""
    user_message: str = ""
    recovery_hint: str = ""

    def __post_init__(self):
        self.type = EventType.ERROR_OCCURRED
        self.data = {
            "error_code": self.error_code,
            "message": self.message,
            "user_message": self.user_message,
            "recovery_hint": self.recovery_hint
        }
        super().__post_init__()
