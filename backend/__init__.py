"""
VoiceType Backend Package

A complete backend solution for voice-to-text transcription
using OpenAI Whisper API with real-time audio recording,
text cleaning, and Windows integration.

Components:
- AudioManager: Microphone enumeration and audio recording
- WhisperService: OpenAI Whisper API integration
- TextCleaner: GPT-based text cleaning and correction
- HotkeyManager: Global Windows hotkey registration
- ClipboardManager: Windows clipboard operations
- SettingsManager: Configuration and secure storage

Example Usage:
    from backend import (
        AudioManager,
        WhisperService,
        TextCleaner,
        HotkeyManager,
        ClipboardManager,
        SettingsManager
    )

    # Initialize components
    settings = SettingsManager()
    api_key = settings.get_api_key()

    audio = AudioManager()
    whisper = WhisperService(api_key=api_key)
    cleaner = TextCleaner(api_key=api_key)
    clipboard = ClipboardManager()
    hotkeys = HotkeyManager()

    # Recording flow
    audio.start_recording()
    # ... wait for user to stop ...
    raw_audio = audio.stop_recording()
    wav_data = audio.convert_to_wav(raw_audio)

    # Transcription
    result = whisper.transcribe(wav_data)
    transcript = result.text

    # Clean up text
    cleaned = cleaner.clean(transcript)
    final_text = cleaned.cleaned_text

    # Output to active window
    clipboard.copy_and_paste(final_text)
"""

__version__ = "1.0.0"
__author__ = "VoiceType Team"

# Import main classes for convenient access
from .audio_manager import (
    AudioManager,
    AudioConfig,
    AudioDevice,
    AudioState,
    get_default_device,
    test_microphone,
)

from .whisper_service import (
    WhisperService,
    WhisperConfig,
    TranscriptionResult,
    TranscriptionStatus,
    TranscriptionError,
    APIKeyError,
    RateLimitError,
    AudioFormatError,
    NetworkError,
    transcribe_audio,
)

from .text_cleaner import (
    TextCleaner,
    TextCleanerConfig,
    CleaningResult,
    CleaningMode,
    TextCleanerError,
    get_language_specific_prompt,
    SYSTEM_PROMPTS,
)

from .hotkey_manager import (
    HotkeyManager,
    HotkeyConfig,
    Hotkey,
    HotkeyError,
    HotkeyRegistrationError,
    HotkeyAlreadyRegisteredError,
    VirtualKeyCodes,
    ModifierFlags,
    create_default_recording_hotkey,
)

from .clipboard_manager import (
    ClipboardManager,
    ClipboardConfig,
    ClipboardContext,
    ClipboardError,
    ClipboardOpenError,
    ClipboardWriteError,
    ClipboardReadError,
    copy,
    paste,
    get_clipboard,
    copy_and_paste,
)

from .settings_manager import (
    SettingsManager,
    AppSettings,
    AudioSettings,
    TranscriptionSettings,
    CleaningSettings,
    HotkeySettings,
    OutputSettings,
    UISettings,
    SecureStorage,
    SettingsError,
    SettingsLoadError,
    SettingsSaveError,
    SecureStorageError,
    get_settings,
)

from .supported_languages import (
    Language,
    SUPPORTED_LANGUAGES,
    AUTO_DETECT,
    LanguageCategory,
    COMMON_LANGUAGES,
    get_language,
    get_all_languages,
    get_languages_with_auto,
    get_common_languages,
    get_language_choices,
    search_languages,
    is_rtl_language,
    get_whisper_language_code,
    whisper_name_to_code,
)


# Module-level exports
__all__ = [
    # Version info
    "__version__",
    "__author__",

    # Audio Manager
    "AudioManager",
    "AudioConfig",
    "AudioDevice",
    "AudioState",
    "get_default_device",
    "test_microphone",

    # Whisper Service
    "WhisperService",
    "WhisperConfig",
    "TranscriptionResult",
    "TranscriptionStatus",
    "TranscriptionError",
    "APIKeyError",
    "RateLimitError",
    "AudioFormatError",
    "NetworkError",
    "transcribe_audio",

    # Text Cleaner
    "TextCleaner",
    "TextCleanerConfig",
    "CleaningResult",
    "CleaningMode",
    "TextCleanerError",
    "get_language_specific_prompt",
    "SYSTEM_PROMPTS",

    # Hotkey Manager
    "HotkeyManager",
    "HotkeyConfig",
    "Hotkey",
    "HotkeyError",
    "HotkeyRegistrationError",
    "HotkeyAlreadyRegisteredError",
    "VirtualKeyCodes",
    "ModifierFlags",
    "create_default_recording_hotkey",

    # Clipboard Manager
    "ClipboardManager",
    "ClipboardConfig",
    "ClipboardContext",
    "ClipboardError",
    "ClipboardOpenError",
    "ClipboardWriteError",
    "ClipboardReadError",
    "copy",
    "paste",
    "get_clipboard",
    "copy_and_paste",

    # Settings Manager
    "SettingsManager",
    "AppSettings",
    "AudioSettings",
    "TranscriptionSettings",
    "CleaningSettings",
    "HotkeySettings",
    "OutputSettings",
    "UISettings",
    "SecureStorage",
    "SettingsError",
    "SettingsLoadError",
    "SettingsSaveError",
    "SecureStorageError",
    "get_settings",

    # Languages
    "Language",
    "SUPPORTED_LANGUAGES",
    "AUTO_DETECT",
    "LanguageCategory",
    "COMMON_LANGUAGES",
    "get_language",
    "get_all_languages",
    "get_languages_with_auto",
    "get_common_languages",
    "get_language_choices",
    "search_languages",
    "is_rtl_language",
    "get_whisper_language_code",
    "whisper_name_to_code",
]
