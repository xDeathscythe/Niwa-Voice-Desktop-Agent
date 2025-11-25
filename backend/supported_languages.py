"""
Supported Languages Module for VoiceType Application.

Contains a comprehensive list of 50+ languages supported by OpenAI Whisper API
with their ISO 639-1 codes and native names.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class Language:
    """Represents a supported language."""
    code: str  # ISO 639-1 code
    name: str  # English name
    native_name: str  # Name in native language
    rtl: bool = False  # Right-to-left writing


# Complete list of 50+ languages supported by Whisper API
# Sorted alphabetically by English name
SUPPORTED_LANGUAGES: Dict[str, Language] = {
    "af": Language("af", "Afrikaans", "Afrikaans"),
    "ar": Language("ar", "Arabic", "العربية", rtl=True),
    "hy": Language("hy", "Armenian", "Հայերdelays"),
    "az": Language("az", "Azerbaijani", "Azərbaycan"),
    "be": Language("be", "Belarusian", "Беларуская"),
    "bs": Language("bs", "Bosnian", "Bosanski"),
    "bg": Language("bg", "Bulgarian", "Български"),
    "ca": Language("ca", "Catalan", "Català"),
    "zh": Language("zh", "Chinese", "中文"),
    "hr": Language("hr", "Croatian", "Hrvatski"),
    "cs": Language("cs", "Czech", "Čeština"),
    "da": Language("da", "Danish", "Dansk"),
    "nl": Language("nl", "Dutch", "Nederlands"),
    "en": Language("en", "English", "English"),
    "et": Language("et", "Estonian", "Eesti"),
    "fi": Language("fi", "Finnish", "Suomi"),
    "fr": Language("fr", "French", "Français"),
    "gl": Language("gl", "Galician", "Galego"),
    "de": Language("de", "German", "Deutsch"),
    "el": Language("el", "Greek", "Ελληνικά"),
    "he": Language("he", "Hebrew", "עברית", rtl=True),
    "hi": Language("hi", "Hindi", "हिन्दी"),
    "hu": Language("hu", "Hungarian", "Magyar"),
    "is": Language("is", "Icelandic", "Íslenska"),
    "id": Language("id", "Indonesian", "Bahasa Indonesia"),
    "it": Language("it", "Italian", "Italiano"),
    "ja": Language("ja", "Japanese", "日本語"),
    "kn": Language("kn", "Kannada", "ಕನ್ನಡ"),
    "kk": Language("kk", "Kazakh", "Қазақша"),
    "ko": Language("ko", "Korean", "한국어"),
    "lv": Language("lv", "Latvian", "Latviešu"),
    "lt": Language("lt", "Lithuanian", "Lietuvių"),
    "mk": Language("mk", "Macedonian", "Македонски"),
    "ms": Language("ms", "Malay", "Bahasa Melayu"),
    "mr": Language("mr", "Marathi", "मराठी"),
    "mi": Language("mi", "Maori", "Māori"),
    "ne": Language("ne", "Nepali", "नेपाली"),
    "no": Language("no", "Norwegian", "Norsk"),
    "fa": Language("fa", "Persian", "فارسی", rtl=True),
    "pl": Language("pl", "Polish", "Polski"),
    "pt": Language("pt", "Portuguese", "Português"),
    "ro": Language("ro", "Romanian", "Română"),
    "ru": Language("ru", "Russian", "Русский"),
    "sr": Language("sr", "Serbian", "Српски"),
    "sk": Language("sk", "Slovak", "Slovenčina"),
    "sl": Language("sl", "Slovenian", "Slovenščina"),
    "es": Language("es", "Spanish", "Español"),
    "sw": Language("sw", "Swahili", "Kiswahili"),
    "sv": Language("sv", "Swedish", "Svenska"),
    "tl": Language("tl", "Tagalog", "Tagalog"),
    "ta": Language("ta", "Tamil", "தமிழ்"),
    "th": Language("th", "Thai", "ไทย"),
    "tr": Language("tr", "Turkish", "Türkçe"),
    "uk": Language("uk", "Ukrainian", "Українська"),
    "ur": Language("ur", "Urdu", "اردو", rtl=True),
    "vi": Language("vi", "Vietnamese", "Tiếng Việt"),
    "cy": Language("cy", "Welsh", "Cymraeg"),
}

# Special "auto-detect" option
AUTO_DETECT = Language("auto", "Auto-detect", "Auto-detect")


class LanguageCategory(Enum):
    """Categories for organizing languages in UI."""
    COMMON = "common"
    EUROPEAN = "european"
    ASIAN = "asian"
    MIDDLE_EASTERN = "middle_eastern"
    OTHER = "other"


# Categorized language codes for UI organization
LANGUAGE_CATEGORIES: Dict[LanguageCategory, List[str]] = {
    LanguageCategory.COMMON: [
        "en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ko",
        "ar", "hi", "pl", "nl", "tr", "sr", "hr", "bs"
    ],
    LanguageCategory.EUROPEAN: [
        "en", "de", "fr", "es", "it", "pt", "nl", "pl", "ru", "uk",
        "cs", "sk", "hu", "ro", "bg", "hr", "sr", "bs", "sl", "mk",
        "el", "da", "sv", "no", "fi", "et", "lv", "lt", "is", "cy",
        "ca", "gl", "be"
    ],
    LanguageCategory.ASIAN: [
        "zh", "ja", "ko", "hi", "th", "vi", "id", "ms", "tl",
        "ta", "kn", "mr", "ne"
    ],
    LanguageCategory.MIDDLE_EASTERN: [
        "ar", "he", "fa", "tr", "ur"
    ],
    LanguageCategory.OTHER: [
        "af", "sw", "mi"
    ],
}

# Most commonly used languages (for quick selection)
COMMON_LANGUAGES: List[str] = [
    "auto",  # Auto-detect first
    "en",    # English
    "sr",    # Serbian
    "hr",    # Croatian
    "bs",    # Bosnian
    "de",    # German
    "fr",    # French
    "es",    # Spanish
    "it",    # Italian
    "ru",    # Russian
    "pl",    # Polish
    "zh",    # Chinese
    "ja",    # Japanese
    "ko",    # Korean
    "ar",    # Arabic
    "pt",    # Portuguese
    "nl",    # Dutch
    "tr",    # Turkish
]


def get_language(code: str) -> Optional[Language]:
    """
    Get language by ISO code.

    Args:
        code: ISO 639-1 language code.

    Returns:
        Language object or None if not found.
    """
    if code == "auto":
        return AUTO_DETECT
    return SUPPORTED_LANGUAGES.get(code.lower())


def get_all_languages() -> List[Language]:
    """
    Get all supported languages.

    Returns:
        List of all Language objects, sorted by English name.
    """
    languages = list(SUPPORTED_LANGUAGES.values())
    return sorted(languages, key=lambda l: l.name)


def get_languages_with_auto() -> List[Language]:
    """
    Get all languages including auto-detect option.

    Returns:
        List with auto-detect first, then all languages sorted.
    """
    return [AUTO_DETECT] + get_all_languages()


def get_common_languages() -> List[Language]:
    """
    Get commonly used languages.

    Returns:
        List of common Language objects.
    """
    result = []
    for code in COMMON_LANGUAGES:
        lang = get_language(code)
        if lang:
            result.append(lang)
    return result


def get_languages_by_category(category: LanguageCategory) -> List[Language]:
    """
    Get languages in a category.

    Args:
        category: Language category.

    Returns:
        List of Language objects in the category.
    """
    codes = LANGUAGE_CATEGORIES.get(category, [])
    return [get_language(c) for c in codes if get_language(c)]


def search_languages(query: str) -> List[Language]:
    """
    Search languages by name or code.

    Args:
        query: Search query (name or code).

    Returns:
        List of matching Language objects.
    """
    query = query.lower().strip()

    if not query:
        return get_all_languages()

    results = []

    for lang in SUPPORTED_LANGUAGES.values():
        if (query in lang.code.lower() or
                query in lang.name.lower() or
                query in lang.native_name.lower()):
            results.append(lang)

    return sorted(results, key=lambda l: l.name)


def get_language_for_display(code: str) -> str:
    """
    Get display string for a language code.

    Args:
        code: ISO 639-1 code.

    Returns:
        Display string like "English (en)" or the code if not found.
    """
    lang = get_language(code)
    if lang:
        return f"{lang.name} ({lang.code})"
    return code


def get_language_choices() -> List[Tuple[str, str]]:
    """
    Get language choices for UI dropdown.

    Returns:
        List of (code, display_name) tuples.
    """
    choices = [("auto", "Auto-detect")]

    for lang in get_all_languages():
        display = f"{lang.name} - {lang.native_name}"
        choices.append((lang.code, display))

    return choices


def is_rtl_language(code: str) -> bool:
    """
    Check if a language uses right-to-left writing.

    Args:
        code: ISO 639-1 code.

    Returns:
        True if RTL language.
    """
    lang = get_language(code)
    return lang.rtl if lang else False


def get_whisper_language_code(code: str) -> Optional[str]:
    """
    Get the language code to send to Whisper API.

    Args:
        code: Language code from our list.

    Returns:
        Code for Whisper API, or None for auto-detect.
    """
    if code == "auto":
        return None  # Whisper auto-detects when no language is specified

    lang = get_language(code)
    return lang.code if lang else None


# Language name mappings for Whisper API response
WHISPER_LANGUAGE_NAMES: Dict[str, str] = {
    "afrikaans": "af",
    "arabic": "ar",
    "armenian": "hy",
    "azerbaijani": "az",
    "belarusian": "be",
    "bosnian": "bs",
    "bulgarian": "bg",
    "catalan": "ca",
    "chinese": "zh",
    "croatian": "hr",
    "czech": "cs",
    "danish": "da",
    "dutch": "nl",
    "english": "en",
    "estonian": "et",
    "finnish": "fi",
    "french": "fr",
    "galician": "gl",
    "german": "de",
    "greek": "el",
    "hebrew": "he",
    "hindi": "hi",
    "hungarian": "hu",
    "icelandic": "is",
    "indonesian": "id",
    "italian": "it",
    "japanese": "ja",
    "kannada": "kn",
    "kazakh": "kk",
    "korean": "ko",
    "latvian": "lv",
    "lithuanian": "lt",
    "macedonian": "mk",
    "malay": "ms",
    "marathi": "mr",
    "maori": "mi",
    "nepali": "ne",
    "norwegian": "no",
    "persian": "fa",
    "polish": "pl",
    "portuguese": "pt",
    "romanian": "ro",
    "russian": "ru",
    "serbian": "sr",
    "slovak": "sk",
    "slovenian": "sl",
    "spanish": "es",
    "swahili": "sw",
    "swedish": "sv",
    "tagalog": "tl",
    "tamil": "ta",
    "thai": "th",
    "turkish": "tr",
    "ukrainian": "uk",
    "urdu": "ur",
    "vietnamese": "vi",
    "welsh": "cy",
}


def whisper_name_to_code(name: str) -> Optional[str]:
    """
    Convert Whisper's detected language name to ISO code.

    Args:
        name: Language name from Whisper API response.

    Returns:
        ISO 639-1 code or None.
    """
    return WHISPER_LANGUAGE_NAMES.get(name.lower())


# Export all for convenient imports
__all__ = [
    'Language',
    'SUPPORTED_LANGUAGES',
    'AUTO_DETECT',
    'LanguageCategory',
    'LANGUAGE_CATEGORIES',
    'COMMON_LANGUAGES',
    'get_language',
    'get_all_languages',
    'get_languages_with_auto',
    'get_common_languages',
    'get_languages_by_category',
    'search_languages',
    'get_language_for_display',
    'get_language_choices',
    'is_rtl_language',
    'get_whisper_language_code',
    'whisper_name_to_code',
]


if __name__ == "__main__":
    print("Supported Languages for VoiceType")
    print("=" * 60)

    print(f"\nTotal languages: {len(SUPPORTED_LANGUAGES)}")

    print("\n--- All Supported Languages ---")
    for lang in get_all_languages():
        rtl_marker = " [RTL]" if lang.rtl else ""
        print(f"  {lang.code}: {lang.name} ({lang.native_name}){rtl_marker}")

    print("\n--- Common Languages ---")
    for lang in get_common_languages():
        print(f"  {lang.code}: {lang.name}")

    print("\n--- Search Test ---")
    results = search_languages("serb")
    print(f"Search 'serb': {[l.name for l in results]}")

    results = search_languages("sr")
    print(f"Search 'sr': {[l.name for l in results]}")

    print("\n--- RTL Languages ---")
    for lang in get_all_languages():
        if lang.rtl:
            print(f"  {lang.code}: {lang.name}")

    print("\n--- UI Dropdown Choices (first 10) ---")
    choices = get_language_choices()[:10]
    for code, display in choices:
        print(f"  {code}: {display}")

    print("\n--- Balkan Languages ---")
    balkan = ["sr", "hr", "bs", "sl", "mk"]
    for code in balkan:
        lang = get_language(code)
        if lang:
            print(f"  {lang.code}: {lang.name} - {lang.native_name}")
