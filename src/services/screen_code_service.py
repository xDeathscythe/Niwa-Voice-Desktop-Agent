"""Screen Code Service - Extracts code context from screen using OCR."""

import logging
import time
from typing import Dict, List, Optional
from PIL import ImageGrab
import pytesseract
import re

logger = logging.getLogger(__name__)


class ScreenCodeService:
    """
    Service for extracting code context from the screen using OCR.

    Uses Tesseract OCR to capture and extract text from the active window,
    focusing on identifying code identifiers (variables, functions, classes).
    """

    def __init__(self, cache_timeout: float = 5.0):
        """
        Initialize the screen code service.

        Args:
            cache_timeout: How long to cache screen captures (in seconds)
        """
        self._cache_timeout = cache_timeout
        self._cached_context: Optional[Dict] = None
        self._cache_time: float = 0

        # Configure tesseract if needed
        # pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

        logger.info(f"ScreenCodeService initialized (cache_timeout={cache_timeout}s)")

    def get_code_context(self) -> Dict[str, any]:
        """
        Capture screen and extract code context.

        Returns:
            Dictionary with:
                - raw_text: Raw OCR text
                - code_identifiers: List of potential code identifiers found
                - timestamp: When this was captured
                - cached: Whether this result was from cache
        """
        # Check cache
        current_time = time.time()
        if self._cached_context and (current_time - self._cache_time) < self._cache_timeout:
            cached = self._cached_context.copy()
            cached["cached"] = True
            return cached

        try:
            # Capture screen
            screenshot = ImageGrab.grab()

            # Perform OCR
            raw_text = pytesseract.image_to_string(screenshot)

            # Extract code identifiers
            identifiers = self._extract_code_identifiers(raw_text)

            context = {
                "raw_text": raw_text,
                "code_identifiers": identifiers,
                "timestamp": current_time,
                "cached": False
            }

            # Update cache
            self._cached_context = context
            self._cache_time = current_time

            logger.info(f"Captured code context: {len(identifiers)} identifiers found")
            return context

        except Exception as e:
            logger.error(f"Failed to capture code context: {e}")
            return self._create_empty_context()

    def _extract_code_identifiers(self, text: str) -> List[str]:
        """
        Extract potential code identifiers from OCR text.

        Looks for patterns that match:
        - Variables (camelCase, snake_case, PascalCase)
        - Function/method names
        - Class names
        - Constants (UPPER_SNAKE_CASE)

        Args:
            text: Raw text from OCR

        Returns:
            List of unique identifiers found
        """
        identifiers = set()

        # Patterns for different identifier styles
        patterns = [
            # camelCase (must start with lowercase)
            r'\b[a-z][a-zA-Z0-9]*[A-Z][a-zA-Z0-9]*\b',
            # PascalCase (must start with uppercase, at least 2 chars)
            r'\b[A-Z][a-z]+[A-Z][a-zA-Z0-9]*\b',
            # snake_case (letters with underscores)
            r'\b[a-z][a-z0-9_]*[a-z0-9]\b',
            # UPPER_SNAKE_CASE (constants)
            r'\b[A-Z][A-Z0-9_]*[A-Z0-9]\b',
            # Function calls (identifier followed by parentheses)
            r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                # Get the identifier (group 1 if it exists, otherwise group 0)
                identifier = match.group(1) if match.lastindex and match.lastindex >= 1 else match.group(0)

                # Filter out common words and single characters
                if len(identifier) > 1 and not self._is_common_word(identifier):
                    identifiers.add(identifier)

        # Sort by length (longer identifiers are usually more specific)
        sorted_identifiers = sorted(identifiers, key=len, reverse=True)

        # Limit to top 50 identifiers to avoid overwhelming the formatter
        return sorted_identifiers[:50]

    def _is_common_word(self, word: str) -> bool:
        """
        Check if a word is a common English word (likely not a code identifier).

        Args:
            word: Word to check

        Returns:
            True if it's a common word, False otherwise
        """
        # Common words that might appear in code but aren't identifiers
        common_words = {
            'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
            'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
            'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
            'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their',
            'if', 'is', 'are', 'was', 'were', 'been', 'has', 'had', 'can', 'could',
            'should', 'would', 'may', 'might', 'must', 'shall', 'will', 'am',
            # Common programming keywords (handled separately)
            'def', 'class', 'return', 'import', 'from', 'as', 'if', 'else',
            'elif', 'for', 'while', 'try', 'except', 'finally', 'with', 'pass',
            'break', 'continue', 'raise', 'assert', 'yield', 'lambda', 'global',
            'nonlocal', 'del', 'in', 'is', 'not', 'and', 'or', 'true', 'false',
            'none', 'self', 'cls', 'super', 'var', 'let', 'const', 'function',
            'async', 'await', 'new', 'delete', 'typeof', 'instanceof'
        }

        return word.lower() in common_words

    def _create_empty_context(self) -> Dict[str, any]:
        """Create empty code context dict."""
        return {
            "raw_text": "",
            "code_identifiers": [],
            "timestamp": time.time(),
            "cached": False
        }

    def clear_cache(self) -> None:
        """Clear the cached context."""
        self._cached_context = None
        self._cache_time = 0
        logger.debug("Cache cleared")

    def cleanup(self) -> None:
        """Clean up resources."""
        self._cached_context = None
        logger.info("ScreenCodeService cleaned up")
