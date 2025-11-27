"""Prompt templates for multi-language transcription support.

This module provides dynamic prompt generation for:
- Whisper API (speech-to-text)
- LLM cleanup (text post-processing)

Prompts are tailored based on user's language preferences to improve
accuracy when mixing languages (e.g., Serbian with English technical terms).
"""

from typing import List, Optional

# ISO 639-1 language code to full name mapping
LANGUAGE_NAMES = {
    # Common languages
    "en": "English",
    "sr": "Serbian",
    "hr": "Croatian",
    "bs": "Bosnian",
    "sl": "Slovenian",
    "mk": "Macedonian",
    "bg": "Bulgarian",
    "ru": "Russian",
    "uk": "Ukrainian",
    "pl": "Polish",
    "cs": "Czech",
    "sk": "Slovak",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "it": "Italian",
    "pt": "Portuguese",
    "nl": "Dutch",
    "tr": "Turkish",
    "ar": "Arabic",
    "he": "Hebrew",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "hi": "Hindi",
    "bn": "Bengali",
    "vi": "Vietnamese",
    "th": "Thai",
    "id": "Indonesian",
    "ms": "Malay",
    "tl": "Tagalog",
    "sw": "Swahili",
    "ro": "Romanian",
    "hu": "Hungarian",
    "el": "Greek",
    "da": "Danish",
    "sv": "Swedish",
    "no": "Norwegian",
    "fi": "Finnish",
    "et": "Estonian",
    "lv": "Latvian",
    "lt": "Lithuanian",
}

# Language-specific filler words to remove during cleanup
FILLER_WORDS = {
    "sr": ["znači", "ovaj", "kao", "mislim", "ono", "pa", "jel", "bre", "ae", "bukvalno", "tipa"],
    "hr": ["znači", "ovaj", "kao", "mislim", "ono", "pa", "jel", "dakle"],
    "bs": ["znači", "ovaj", "kao", "mislim", "ono", "pa", "jel"],
    "en": ["um", "uh", "like", "you know", "basically", "actually", "literally", "so", "right"],
    "de": ["äh", "ähm", "also", "halt", "sozusagen", "quasi", "irgendwie"],
    "fr": ["euh", "ben", "donc", "genre", "en fait", "voilà", "quoi"],
    "es": ["eh", "pues", "bueno", "o sea", "como", "tipo", "vale"],
    "it": ["eh", "cioè", "allora", "tipo", "praticamente", "insomma"],
    "ru": ["э", "эм", "ну", "как бы", "типа", "вот", "значит", "короче"],
    "pl": ["no", "właśnie", "jakby", "w sumie", "znaczy", "wiesz"],
    "nl": ["eh", "uhm", "dus", "eigenlijk", "gewoon", "zeg maar"],
    "pt": ["é", "tipo", "né", "então", "assim", "bem"],
    "tr": ["şey", "yani", "işte", "hani", "mesela"],
}

# Common technical terms that should be preserved in English
TECHNICAL_TERMS_HINT = """
Common technical terms to preserve in English:
- Programming: function, class, variable, method, API, REST, HTTP, JSON, XML
- Tools: Git, GitHub, Docker, Kubernetes, AWS, Azure, Linux, Windows
- Frameworks: React, Angular, Vue, Node, Django, Flask, Spring
- Concepts: frontend, backend, fullstack, database, server, client, cache
"""


def get_language_name(code: str) -> str:
    """Get full language name from ISO 639-1 code."""
    return LANGUAGE_NAMES.get(code, code.capitalize())


def get_filler_words(languages: List[str]) -> List[str]:
    """Get combined filler words for all specified languages."""
    fillers = []
    for lang in languages:
        fillers.extend(FILLER_WORDS.get(lang, []))
    # Add English fillers by default
    if "en" not in languages:
        fillers.extend(FILLER_WORDS.get("en", []))
    return list(set(fillers))  # Remove duplicates


def build_whisper_prompt(
    languages: List[str],
    preserve_english: bool = True
) -> str:
    """
    Build contextual prompt for Whisper API.

    The prompt helps Whisper understand the expected language context
    and improves transcription accuracy for code-switching scenarios.

    Args:
        languages: List of language codes, first is primary
        preserve_english: Whether to preserve English technical terms

    Returns:
        Prompt string for Whisper API
    """
    if not languages or languages == ["auto"]:
        base = "Transcribe the speech naturally and accurately."
        if preserve_english:
            base += " Preserve any English technical terms exactly as spoken."
        return base

    primary = languages[0]
    primary_name = get_language_name(primary)

    if len(languages) == 1:
        prompt = f"Transcribe in {primary_name}."
        if preserve_english and primary != "en":
            prompt += " The speaker may use English technical terms - preserve them exactly."
        return prompt

    # Multiple languages
    other_names = [get_language_name(l) for l in languages[1:]]
    prompt = f"Transcribe in {primary_name}. The speaker may also use words from: {', '.join(other_names)}."

    if preserve_english and "en" not in languages:
        prompt += " Preserve English technical terms exactly as spoken."

    return prompt


def build_cleanup_prompt(
    primary_language: str,
    additional_languages: Optional[List[str]] = None,
    preserve_english: bool = True
) -> str:
    """
    Build dynamic cleanup prompt for LLM post-processing.

    Creates a language-aware prompt that:
    - Removes filler words specific to the user's languages
    - Fixes grammar in the primary language
    - Preserves English technical terms when requested
    - Handles code-switching naturally

    Args:
        primary_language: Primary language code (e.g., "sr")
        additional_languages: List of additional language codes
        preserve_english: Whether to preserve English technical terms

    Returns:
        System prompt for LLM cleanup
    """
    additional_languages = additional_languages or []

    # Handle auto-detect case
    if primary_language == "auto":
        lang_name = "the detected language"
        all_langs = additional_languages
    else:
        lang_name = get_language_name(primary_language)
        all_langs = [primary_language] + additional_languages

    # Get filler words for all languages
    fillers = get_filler_words(all_langs)
    filler_examples = ", ".join(fillers[:10])  # Show first 10 as examples

    prompt = f"""Clean up this voice transcription. The text is primarily in {lang_name}.

Rules:
1. Remove filler words and speech disfluencies ({filler_examples}, etc.)
2. Fix grammar and spelling errors in {lang_name}
3. Preserve the FULL content - do NOT shorten, summarize, or remove information
4. Keep the same tone, style, and intent as the speaker
5. Fix punctuation and capitalization appropriately"""

    rule_num = 6

    if preserve_english and primary_language != "en":
        prompt += f"""
{rule_num}. IMPORTANT: Preserve English technical terms EXACTLY as spoken
   - Programming terms: function, class, variable, API, etc.
   - Product names: GitHub, Docker, React, etc.
   - Do NOT translate these to {lang_name}"""
        rule_num += 1

    if additional_languages:
        other_names = [get_language_name(l) for l in additional_languages if l != primary_language]
        if other_names:
            prompt += f"""
{rule_num}. The speaker may also use words from: {', '.join(other_names)}
   - Preserve these naturally, do not force translation to {lang_name}"""
            rule_num += 1

    prompt += """

Return ONLY the cleaned text, no explanations or additional commentary."""

    return prompt


def build_variable_context_prompt(
    variables: List[str],
    primary_language: str = "auto"
) -> str:
    """
    Build prompt hint for Whisper when variable names are detected.

    Args:
        variables: List of variable/function names from code context
        primary_language: Primary language code

    Returns:
        Additional prompt context for Whisper
    """
    if not variables:
        return ""

    # Limit to most relevant variables
    var_sample = variables[:20]
    var_list = ", ".join(var_sample)

    return f"Code context includes: {var_list}. Preserve these identifiers exactly."
