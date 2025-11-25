"""Code identifier extraction and matching service for VoiceType."""

import re
import logging
from typing import Optional
from dataclasses import dataclass
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


@dataclass
class IdentifierMatch:
    """Represents a matched identifier."""
    identifier: str
    confidence: float  # 0.0 to 1.0
    match_type: str  # 'exact', 'fuzzy', 'phonetic'


class CodeIdentifierService:
    """
    Service for extracting and matching code identifiers from text.

    Handles multiple naming conventions:
    - camelCase (myVariableName)
    - PascalCase (MyClassName)
    - snake_case (my_variable_name)
    - SCREAMING_SNAKE_CASE (MY_CONSTANT)
    - kebab-case (my-component-name)

    Features:
    - Pattern-based identifier extraction
    - Stopword filtering
    - Fuzzy matching for voice-to-code matching
    - Normalization for comparison

    Usage:
        service = CodeIdentifierService()
        identifiers = service.extract_identifiers("const myVar = new MyClass()")
        match = service.match_identifier("my var", identifiers)
    """

    # Common English words to filter out (expanded list)
    STOPWORDS = {
        # Articles, prepositions, conjunctions
        'a', 'an', 'the', 'and', 'or', 'but', 'if', 'then', 'else', 'when',
        'at', 'by', 'for', 'from', 'in', 'into', 'of', 'on', 'to', 'with',

        # Common verbs
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has',
        'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could',
        'can', 'may', 'might', 'must', 'get', 'set', 'let', 'make',

        # Pronouns
        'i', 'you', 'he', 'she', 'it', 'we', 'they', 'them', 'their',
        'this', 'that', 'these', 'those', 'my', 'your', 'his', 'her',

        # Common adjectives/adverbs
        'not', 'no', 'yes', 'all', 'some', 'any', 'each', 'every',
        'more', 'less', 'most', 'least', 'very', 'too', 'so', 'just',

        # Common nouns (non-code)
        'time', 'year', 'day', 'way', 'man', 'thing', 'woman', 'life',
        'child', 'world', 'school', 'state', 'family', 'student', 'group',

        # Programming keywords (language-agnostic common ones)
        'var', 'const', 'let', 'function', 'class', 'return', 'import',
        'export', 'from', 'as', 'new', 'this', 'super', 'extends',
        'implements', 'interface', 'type', 'enum', 'public', 'private',
        'protected', 'static', 'async', 'await', 'try', 'catch', 'finally',
        'throw', 'throws', 'void', 'null', 'undefined', 'true', 'false',
        'break', 'continue', 'while', 'switch', 'case', 'default',

        # Common short words that are rarely identifiers
        'ok', 'go', 'up', 'down', 'out', 'off', 'end', 'run', 'put',
    }

    # Minimum lengths
    MIN_LENGTH = 2  # Minimum identifier length
    MIN_SINGLE_CHAR_UPPERCASE = True  # Allow single uppercase letters (e.g., 'X', 'Y')

    def __init__(self):
        """Initialize identifier patterns and compile regex."""

        # Pattern for camelCase: starts lowercase, has uppercase letter(s)
        # Examples: myVar, getElementById, isActive
        self._camel_case_pattern = re.compile(
            r'\b[a-z][a-z0-9]*[A-Z][a-zA-Z0-9]*\b'
        )

        # Pattern for PascalCase: starts uppercase, has lowercase
        # Examples: MyClass, UserAccount, HttpResponse
        self._pascal_case_pattern = re.compile(
            r'\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)*\b'
        )

        # Pattern for snake_case: lowercase with underscores
        # Examples: my_variable, user_name, get_user_by_id
        self._snake_case_pattern = re.compile(
            r'\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b'
        )

        # Pattern for SCREAMING_SNAKE_CASE: uppercase with underscores
        # Examples: MAX_VALUE, API_KEY, DEFAULT_TIMEOUT
        self._screaming_snake_pattern = re.compile(
            r'\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b'
        )

        # Pattern for kebab-case: lowercase with hyphens
        # Examples: my-component, user-profile, main-container
        self._kebab_case_pattern = re.compile(
            r'\b[a-z][a-z0-9]*(?:-[a-z0-9]+)+\b'
        )

        # Pattern for single uppercase letters (common in math/generics)
        # Examples: X, Y, T, K, V
        self._single_upper_pattern = re.compile(r'\b[A-Z]\b')

        # Pattern for multi-uppercase acronyms/abbreviations
        # Examples: HTTP, API, URL, JSON, XML (2-5 letters)
        self._acronym_pattern = re.compile(r'\b[A-Z]{2,5}\b')

        # Pattern for common function call format: word followed by ()
        # Examples: getData(), myFunc(), process()
        self._function_call_pattern = re.compile(
            r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\)'
        )

        # Pattern for namespace/module access: word.word or word::word
        # Examples: Math.max, std::vector, os.path
        self._namespace_pattern = re.compile(
            r'\b([a-zA-Z_][a-zA-Z0-9_]*)[.:]{1,2}([a-zA-Z_][a-zA-Z0-9_]*)\b'
        )

        logger.info("CodeIdentifierService initialized with comprehensive patterns")

    def extract_identifiers(self, text: str) -> list[str]:
        """
        Extract all code identifiers from text.

        Args:
            text: Text to extract identifiers from

        Returns:
            List of unique identifiers found, sorted by likelihood
        """
        if not text:
            return []

        identifiers = set()

        # Extract function calls (with parentheses)
        for match in self._function_call_pattern.finditer(text):
            identifier = match.group(1)
            if self._is_valid_candidate(identifier):
                identifiers.add(identifier)
                logger.debug(f"Found function call: {identifier}")

        # Extract namespace/module accesses
        for match in self._namespace_pattern.finditer(text):
            # Add both the namespace and the member
            namespace = match.group(1)
            member = match.group(2)
            full = f"{namespace}.{member}"

            if self._is_valid_candidate(namespace):
                identifiers.add(namespace)
            if self._is_valid_candidate(member):
                identifiers.add(member)
            identifiers.add(full)
            logger.debug(f"Found namespace access: {full}")

        # Extract camelCase
        for match in self._camel_case_pattern.finditer(text):
            identifier = match.group(0)
            if self._is_valid_candidate(identifier):
                identifiers.add(identifier)
                logger.debug(f"Found camelCase: {identifier}")

        # Extract PascalCase
        for match in self._pascal_case_pattern.finditer(text):
            identifier = match.group(0)
            if self._is_valid_candidate(identifier):
                identifiers.add(identifier)
                logger.debug(f"Found PascalCase: {identifier}")

        # Extract snake_case
        for match in self._snake_case_pattern.finditer(text):
            identifier = match.group(0)
            if self._is_valid_candidate(identifier):
                identifiers.add(identifier)
                logger.debug(f"Found snake_case: {identifier}")

        # Extract SCREAMING_SNAKE_CASE
        for match in self._screaming_snake_pattern.finditer(text):
            identifier = match.group(0)
            if self._is_valid_candidate(identifier):
                identifiers.add(identifier)
                logger.debug(f"Found SCREAMING_SNAKE_CASE: {identifier}")

        # Extract kebab-case
        for match in self._kebab_case_pattern.finditer(text):
            identifier = match.group(0)
            if self._is_valid_candidate(identifier):
                identifiers.add(identifier)
                logger.debug(f"Found kebab-case: {identifier}")

        # Extract acronyms (2-5 uppercase letters)
        for match in self._acronym_pattern.finditer(text):
            identifier = match.group(0)
            if self._is_valid_candidate(identifier):
                identifiers.add(identifier)
                logger.debug(f"Found acronym: {identifier}")

        # Extract single uppercase letters (if enabled)
        if self.MIN_SINGLE_CHAR_UPPERCASE:
            for match in self._single_upper_pattern.finditer(text):
                identifier = match.group(0)
                # Don't filter these through is_valid_candidate
                # since they're intentionally single char
                identifiers.add(identifier)
                logger.debug(f"Found single uppercase: {identifier}")

        result = sorted(identifiers, key=lambda x: self._identifier_score(x), reverse=True)
        logger.info(f"Extracted {len(result)} identifiers from text")
        return result

    def is_valid_identifier(self, word: str) -> bool:
        """
        Check if word looks like a code identifier.

        Args:
            word: Word to check

        Returns:
            True if word appears to be a code identifier
        """
        if not word:
            return False

        # Check against any pattern
        patterns = [
            self._camel_case_pattern,
            self._pascal_case_pattern,
            self._snake_case_pattern,
            self._screaming_snake_pattern,
            self._kebab_case_pattern,
            self._acronym_pattern,
        ]

        for pattern in patterns:
            if pattern.match(word):
                return self._is_valid_candidate(word)

        # Check single uppercase
        if self.MIN_SINGLE_CHAR_UPPERCASE and self._single_upper_pattern.match(word):
            return True

        return False

    def match_identifier(
        self,
        spoken_text: str,
        identifiers: list[str],
        threshold: float = 0.6
    ) -> Optional[IdentifierMatch]:
        """
        Fuzzy match spoken text to known identifier.

        This handles voice-to-code matching, e.g.:
        - "clear pasteboard" -> "clearPasteboard"
        - "user name" -> "userName" or "user_name"
        - "get user by ID" -> "getUserById"

        Args:
            spoken_text: The spoken/transcribed text
            identifiers: List of known identifiers to match against
            threshold: Minimum confidence threshold (0.0 to 1.0)

        Returns:
            IdentifierMatch if match found above threshold, None otherwise
        """
        if not spoken_text or not identifiers:
            return None

        spoken_normalized = self.normalize_identifier(spoken_text)
        best_match = None
        best_score = 0.0
        best_type = 'fuzzy'

        logger.debug(f"Matching '{spoken_text}' (normalized: '{spoken_normalized}') "
                    f"against {len(identifiers)} identifiers")

        for identifier in identifiers:
            # Exact match (normalized)
            id_normalized = self.normalize_identifier(identifier)
            if spoken_normalized == id_normalized:
                logger.info(f"Exact match: '{spoken_text}' -> '{identifier}'")
                return IdentifierMatch(
                    identifier=identifier,
                    confidence=1.0,
                    match_type='exact'
                )

            # Fuzzy matching using sequence matcher
            score = SequenceMatcher(None, spoken_normalized, id_normalized).ratio()

            # Bonus for starts_with
            if id_normalized.startswith(spoken_normalized):
                score += 0.2
            elif spoken_normalized.startswith(id_normalized):
                score += 0.1

            # Bonus for same length (more likely to be the right match)
            if len(spoken_normalized) == len(id_normalized):
                score += 0.1

            # Bonus for exact word boundaries matching
            # e.g., "user name" matches "userName" better than "username"
            spoken_words = spoken_text.lower().split()
            if len(spoken_words) > 1:
                # Check if identifier contains all spoken words in order
                id_lower = identifier.lower()
                all_words_match = all(word in id_lower for word in spoken_words)
                if all_words_match:
                    score += 0.15

            # Cap score at 1.0
            score = min(1.0, score)

            if score > best_score:
                best_score = score
                best_match = identifier
                best_type = 'fuzzy'

        if best_match and best_score >= threshold:
            logger.info(f"Fuzzy match: '{spoken_text}' -> '{best_match}' "
                       f"(confidence: {best_score:.2f})")
            return IdentifierMatch(
                identifier=best_match,
                confidence=best_score,
                match_type=best_type
            )

        logger.debug(f"No match found above threshold {threshold} "
                    f"(best score: {best_score:.2f})")
        return None

    def normalize_identifier(self, word: str) -> str:
        """
        Normalize identifier for comparison.

        Removes:
        - Underscores
        - Hyphens
        - Case differences
        - Extra whitespace

        Args:
            word: Identifier to normalize

        Returns:
            Normalized identifier (lowercase, no separators)
        """
        if not word:
            return ""

        # Convert to lowercase
        normalized = word.lower()

        # Remove common separators
        normalized = normalized.replace('_', '')
        normalized = normalized.replace('-', '')
        normalized = normalized.replace('.', '')
        normalized = normalized.replace('::', '')

        # Remove extra whitespace
        normalized = ''.join(normalized.split())

        return normalized

    def _is_valid_candidate(self, identifier: str) -> bool:
        """
        Check if identifier candidate should be kept.

        Filters out:
        - Stopwords
        - Too short identifiers
        - Common English words

        Args:
            identifier: Identifier to validate

        Returns:
            True if identifier should be kept
        """
        if not identifier:
            return False

        # Check minimum length
        if len(identifier) < self.MIN_LENGTH:
            return False

        # Check against stopwords (case-insensitive)
        if identifier.lower() in self.STOPWORDS:
            logger.debug(f"Filtered stopword: {identifier}")
            return False

        # If it's all underscores or hyphens, reject
        if all(c in '_-' for c in identifier):
            return False

        # If it contains no letters, reject (e.g., "123", "___")
        if not any(c.isalpha() for c in identifier):
            return False

        return True

    def _identifier_score(self, identifier: str) -> float:
        """
        Score identifier by likelihood of being important.

        Higher scores for:
        - Longer identifiers
        - Mixed case (camelCase, PascalCase)
        - Contains underscores/hyphens (snake_case, kebab-case)

        Args:
            identifier: Identifier to score

        Returns:
            Score (higher is more likely to be important)
        """
        score = 0.0

        # Length bonus (up to 20 chars)
        score += min(len(identifier) / 20.0, 1.0) * 10

        # Mixed case bonus
        has_upper = any(c.isupper() for c in identifier)
        has_lower = any(c.islower() for c in identifier)
        if has_upper and has_lower:
            score += 5

        # All uppercase (constant) bonus
        if identifier.isupper() and '_' in identifier:
            score += 7

        # Contains separators bonus
        if '_' in identifier or '-' in identifier:
            score += 3

        # Namespace/module access bonus
        if '.' in identifier or '::' in identifier:
            score += 8

        # Function call pattern bonus (if we detected it with ())
        # This is handled during extraction, so we give extra weight
        # to identifiers that are likely function names
        if self._camel_case_pattern.match(identifier) or \
           self._snake_case_pattern.match(identifier):
            score += 2

        return score

    def get_identifier_type(self, identifier: str) -> Optional[str]:
        """
        Determine the type/convention of an identifier.

        Args:
            identifier: Identifier to classify

        Returns:
            Type string: 'camelCase', 'PascalCase', 'snake_case',
            'SCREAMING_SNAKE_CASE', 'kebab-case', 'ACRONYM', 'SINGLE_UPPER',
            or None if unrecognized
        """
        if not identifier:
            return None

        if self._camel_case_pattern.match(identifier):
            return 'camelCase'
        elif self._pascal_case_pattern.match(identifier):
            return 'PascalCase'
        elif self._screaming_snake_pattern.match(identifier):
            return 'SCREAMING_SNAKE_CASE'
        elif self._snake_case_pattern.match(identifier):
            return 'snake_case'
        elif self._kebab_case_pattern.match(identifier):
            return 'kebab-case'
        elif self._acronym_pattern.match(identifier):
            return 'ACRONYM'
        elif self._single_upper_pattern.match(identifier):
            return 'SINGLE_UPPER'
        else:
            return None

    def split_identifier_words(self, identifier: str) -> list[str]:
        """
        Split identifier into component words.

        Examples:
            'getUserById' -> ['get', 'User', 'By', 'Id']
            'user_name' -> ['user', 'name']
            'my-component' -> ['my', 'component']
            'HTTPResponse' -> ['HTTP', 'Response']

        Args:
            identifier: Identifier to split

        Returns:
            List of words
        """
        if not identifier:
            return []

        # Handle snake_case and kebab-case
        if '_' in identifier or '-' in identifier:
            return re.split(r'[_-]+', identifier)

        # Handle camelCase and PascalCase
        # Insert space before uppercase letters (except at start)
        words = []
        current_word = []

        for i, char in enumerate(identifier):
            if i > 0 and char.isupper():
                # Check if this is part of an acronym (multiple uppercase in a row)
                if i + 1 < len(identifier) and identifier[i + 1].isupper():
                    # Part of acronym
                    current_word.append(char)
                else:
                    # Start of new word
                    if current_word:
                        words.append(''.join(current_word))
                    current_word = [char]
            else:
                current_word.append(char)

        if current_word:
            words.append(''.join(current_word))

        return words

    def cleanup(self) -> None:
        """Clean up resources."""
        logger.info("CodeIdentifierService cleaned up")
