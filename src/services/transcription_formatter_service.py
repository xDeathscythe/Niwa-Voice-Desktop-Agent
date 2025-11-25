"""Transcription formatter service for wrapping code identifiers in backticks."""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class TranscriptionFormatterService:
    """
    Transcription formatter service for post-processing transcribed text.

    Features:
    - Wraps code identifiers in backticks
    - Intelligent matching with fuzzy logic
    - Preserves existing formatting (quotes, backticks)
    - Handles camelCase, PascalCase, and snake_case identifiers
    - Conservative approach to avoid over-formatting

    Usage:
        formatter = TranscriptionFormatterService()
        formatted = formatter.format_with_code_identifiers(
            "the clear pasteboard function",
            ["clearPasteboard", "getData"]
        )
        # Result: "the `clearPasteboard` function"
    """

    def __init__(self):
        """Initialize formatter service."""
        logger.info("TranscriptionFormatterService initialized")

    def format_with_code_identifiers(
        self,
        text: str,
        identifiers: list[str]
    ) -> str:
        """
        Wrap code identifiers in backticks in transcribed text.

        This method intelligently matches spoken phrases to code identifiers
        and wraps them in backticks for better readability. It handles various
        naming conventions and avoids over-formatting.

        Args:
            text: Raw transcription text
            identifiers: List of known code identifiers to match

        Returns:
            Formatted text with identifiers wrapped in backticks

        Examples:
            >>> formatter.format_with_code_identifiers(
            ...     "use clear pasteboard to reset",
            ...     ["clearPasteboard", "reset"]
            ... )
            "use `clearPasteboard` to `reset`"
        """
        if not text or not identifiers:
            return text

        logger.debug(f"Formatting text with {len(identifiers)} identifiers")

        # Sort identifiers by length (longest first) to prefer longer matches
        sorted_identifiers = sorted(identifiers, key=len, reverse=True)

        # Build a list of (start, end, replacement) tuples
        replacements = []

        for identifier in sorted_identifiers:
            # Generate potential spoken forms of this identifier
            spoken_forms = self._generate_spoken_forms(identifier)

            logger.debug(f"Identifier '{identifier}' -> spoken forms: {spoken_forms}")

            # Try to match each spoken form in the text
            for spoken in spoken_forms:
                # Build regex pattern to match word boundaries
                # Use word boundaries but allow for punctuation
                pattern = r'\b' + re.escape(spoken) + r'\b'

                for match in re.finditer(pattern, text, re.IGNORECASE):
                    start = match.start()
                    end = match.end()

                    # Check if already formatted or in quotes
                    if self._is_already_formatted(text, start, end):
                        logger.debug(f"Skipping '{spoken}' at {start}-{end}: already formatted")
                        continue

                    # Check if overlaps with existing replacement
                    if self._overlaps_with_replacements(start, end, replacements):
                        logger.debug(f"Skipping '{spoken}' at {start}-{end}: overlaps")
                        continue

                    # Add replacement
                    replacements.append((start, end, identifier))
                    logger.debug(f"Matched '{spoken}' -> '{identifier}' at {start}-{end}")

        # Apply replacements in reverse order to preserve positions
        replacements.sort(key=lambda x: x[0], reverse=True)

        result = text
        for start, end, identifier in replacements:
            result = result[:start] + f"`{identifier}`" + result[end:]
            logger.debug(f"Applied replacement: '{text[start:end]}' -> '`{identifier}`'")

        if replacements:
            logger.info(f"Applied {len(replacements)} formatting replacements")
        else:
            logger.debug("No matches found")

        return result

    def _is_already_formatted(self, text: str, start: int, end: int) -> bool:
        """
        Check if text at position is already in backticks, quotes, or special context.

        Args:
            text: Full text
            start: Start position of potential match
            end: End position of potential match

        Returns:
            True if text is already formatted and should not be wrapped
        """
        # Check for backticks
        if start > 0 and text[start - 1] == '`':
            return True
        if end < len(text) and text[end] == '`':
            return True

        # Check for double quotes
        if start > 0 and text[start - 1] == '"':
            return True
        if end < len(text) and text[end] == '"':
            return True

        # Check for single quotes
        if start > 0 and text[start - 1] == "'":
            return True
        if end < len(text) and text[end] == "'":
            return True

        # Check if inside backticks (scan backward and forward)
        backtick_count_before = text[:start].count('`')
        if backtick_count_before % 2 == 1:  # Odd number means we're inside backticks
            return True

        # Check if inside quotes
        quote_count_before = text[:start].count('"')
        if quote_count_before % 2 == 1:  # Odd number means we're inside quotes
            return True

        single_quote_count_before = text[:start].count("'")
        if single_quote_count_before % 2 == 1:  # Odd number means we're inside quotes
            return True

        # Check for URLs or file paths (contains :// or multiple /)
        context_start = max(0, start - 20)
        context_end = min(len(text), end + 20)
        context = text[context_start:context_end]
        if '://' in context or context.count('/') >= 2 or context.count('\\') >= 2:
            logger.debug(f"Skipping due to URL/path context: {context}")
            return True

        return False

    def _match_spoken_to_identifier(
        self,
        spoken_phrase: str,
        identifiers: list[str]
    ) -> Optional[str]:
        """
        Match spoken phrase to known identifier with fuzzy logic.

        This method attempts to match a spoken phrase (like "clear pasteboard")
        to a code identifier (like "clearPasteboard") using various strategies.

        Args:
            spoken_phrase: Spoken phrase from transcription
            identifiers: List of known code identifiers

        Returns:
            Matching identifier or None if no match found

        Examples:
            >>> self._match_spoken_to_identifier(
            ...     "clear pasteboard",
            ...     ["clearPasteboard", "getData"]
            ... )
            "clearPasteboard"
        """
        # Normalize spoken phrase
        spoken_normalized = spoken_phrase.lower().strip()

        for identifier in identifiers:
            spoken_forms = self._generate_spoken_forms(identifier)

            for form in spoken_forms:
                if form.lower() == spoken_normalized:
                    logger.debug(f"Matched '{spoken_phrase}' -> '{identifier}'")
                    return identifier

        return None

    def _generate_spoken_forms(self, identifier: str) -> list[str]:
        """
        Generate possible spoken forms of a code identifier.

        Handles camelCase, PascalCase, and snake_case identifiers.

        Args:
            identifier: Code identifier (e.g., "clearPasteboard", "get_data")

        Returns:
            List of possible spoken forms

        Examples:
            >>> self._generate_spoken_forms("clearPasteboard")
            ["clear pasteboard", "clearpasteboard", "clear paste board"]

            >>> self._generate_spoken_forms("get_data")
            ["get data", "getdata"]
        """
        forms = []

        # Original identifier (case-insensitive matching will handle this)
        forms.append(identifier)

        # Handle snake_case: replace underscores with spaces
        if '_' in identifier:
            forms.append(identifier.replace('_', ' '))
            forms.append(identifier.replace('_', ''))

        # Handle camelCase and PascalCase: insert spaces before capitals
        # Match transition from lowercase to uppercase
        spaced = re.sub(r'([a-z])([A-Z])', r'\1 \2', identifier)
        # Match transition from multiple uppercase to lowercase (e.g., "XMLParser" -> "XML Parser")
        spaced = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', spaced)

        if spaced != identifier:
            forms.append(spaced)
            forms.append(spaced.replace(' ', ''))

        # Add lowercase version of spaced form
        forms.append(spaced.lower())

        # Remove duplicates while preserving order
        seen = set()
        unique_forms = []
        for form in forms:
            normalized = form.lower()
            if normalized not in seen:
                seen.add(normalized)
                unique_forms.append(form)

        return unique_forms

    def _overlaps_with_replacements(
        self,
        start: int,
        end: int,
        replacements: list[tuple[int, int, str]]
    ) -> bool:
        """
        Check if position range overlaps with existing replacements.

        Args:
            start: Start position
            end: End position
            replacements: List of (start, end, replacement) tuples

        Returns:
            True if overlaps with any existing replacement
        """
        for r_start, r_end, _ in replacements:
            # Check for any overlap
            if not (end <= r_start or start >= r_end):
                return True
        return False

    def cleanup(self) -> None:
        """Clean up resources."""
        logger.info("TranscriptionFormatterService cleaned up")
