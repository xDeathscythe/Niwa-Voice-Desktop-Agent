"""Standalone test for CodeIdentifierService - no package dependencies."""

import re
import logging
from typing import Optional
from dataclasses import dataclass
from difflib import SequenceMatcher

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class IdentifierMatch:
    """Represents a matched identifier."""
    identifier: str
    confidence: float
    match_type: str


class CodeIdentifierService:
    """Code identifier extraction and matching service."""

    STOPWORDS = {
        'a', 'an', 'the', 'and', 'or', 'but', 'if', 'then', 'else', 'when',
        'at', 'by', 'for', 'from', 'in', 'into', 'of', 'on', 'to', 'with',
        'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has',
        'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could',
        'can', 'may', 'might', 'must', 'get', 'set', 'let', 'make',
        'var', 'const', 'function', 'class', 'return', 'import', 'export',
        'new', 'this', 'super', 'null', 'undefined', 'true', 'false',
    }

    MIN_LENGTH = 2
    MIN_SINGLE_CHAR_UPPERCASE = True

    def __init__(self):
        self._camel_case_pattern = re.compile(r'\b[a-z][a-z0-9]*[A-Z][a-zA-Z0-9]*\b')
        self._pascal_case_pattern = re.compile(r'\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)*\b')
        self._snake_case_pattern = re.compile(r'\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b')
        self._screaming_snake_pattern = re.compile(r'\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b')
        self._kebab_case_pattern = re.compile(r'\b[a-z][a-z0-9]*(?:-[a-z0-9]+)+\b')
        self._single_upper_pattern = re.compile(r'\b[A-Z]\b')
        self._acronym_pattern = re.compile(r'\b[A-Z]{2,5}\b')
        self._function_call_pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\)')
        self._namespace_pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)[.:]{1,2}([a-zA-Z_][a-zA-Z0-9_]*)\b')

    def extract_identifiers(self, text: str) -> list[str]:
        if not text:
            return []

        identifiers = set()

        for match in self._function_call_pattern.finditer(text):
            identifier = match.group(1)
            if self._is_valid_candidate(identifier):
                identifiers.add(identifier)

        for match in self._namespace_pattern.finditer(text):
            namespace = match.group(1)
            member = match.group(2)
            full = f"{namespace}.{member}"
            if self._is_valid_candidate(namespace):
                identifiers.add(namespace)
            if self._is_valid_candidate(member):
                identifiers.add(member)
            identifiers.add(full)

        for match in self._camel_case_pattern.finditer(text):
            identifier = match.group(0)
            if self._is_valid_candidate(identifier):
                identifiers.add(identifier)

        for match in self._pascal_case_pattern.finditer(text):
            identifier = match.group(0)
            if self._is_valid_candidate(identifier):
                identifiers.add(identifier)

        for match in self._snake_case_pattern.finditer(text):
            identifier = match.group(0)
            if self._is_valid_candidate(identifier):
                identifiers.add(identifier)

        for match in self._screaming_snake_pattern.finditer(text):
            identifier = match.group(0)
            if self._is_valid_candidate(identifier):
                identifiers.add(identifier)

        for match in self._kebab_case_pattern.finditer(text):
            identifier = match.group(0)
            if self._is_valid_candidate(identifier):
                identifiers.add(identifier)

        for match in self._acronym_pattern.finditer(text):
            identifier = match.group(0)
            if self._is_valid_candidate(identifier):
                identifiers.add(identifier)

        if self.MIN_SINGLE_CHAR_UPPERCASE:
            for match in self._single_upper_pattern.finditer(text):
                identifiers.add(match.group(0))

        return sorted(identifiers, key=lambda x: self._identifier_score(x), reverse=True)

    def is_valid_identifier(self, word: str) -> bool:
        if not word:
            return False
        patterns = [
            self._camel_case_pattern, self._pascal_case_pattern,
            self._snake_case_pattern, self._screaming_snake_pattern,
            self._kebab_case_pattern, self._acronym_pattern,
        ]
        for pattern in patterns:
            if pattern.match(word):
                return self._is_valid_candidate(word)
        if self.MIN_SINGLE_CHAR_UPPERCASE and self._single_upper_pattern.match(word):
            return True
        return False

    def match_identifier(self, spoken_text: str, identifiers: list[str], threshold: float = 0.6) -> Optional[IdentifierMatch]:
        if not spoken_text or not identifiers:
            return None

        spoken_normalized = self.normalize_identifier(spoken_text)
        best_match = None
        best_score = 0.0

        for identifier in identifiers:
            id_normalized = self.normalize_identifier(identifier)
            if spoken_normalized == id_normalized:
                return IdentifierMatch(identifier=identifier, confidence=1.0, match_type='exact')

            score = SequenceMatcher(None, spoken_normalized, id_normalized).ratio()

            if id_normalized.startswith(spoken_normalized):
                score += 0.2
            elif spoken_normalized.startswith(id_normalized):
                score += 0.1

            if len(spoken_normalized) == len(id_normalized):
                score += 0.1

            spoken_words = spoken_text.lower().split()
            if len(spoken_words) > 1:
                id_lower = identifier.lower()
                if all(word in id_lower for word in spoken_words):
                    score += 0.15

            score = min(1.0, score)

            if score > best_score:
                best_score = score
                best_match = identifier

        if best_match and best_score >= threshold:
            return IdentifierMatch(identifier=best_match, confidence=best_score, match_type='fuzzy')
        return None

    def normalize_identifier(self, word: str) -> str:
        if not word:
            return ""
        normalized = word.lower()
        normalized = normalized.replace('_', '').replace('-', '').replace('.', '').replace('::', '')
        normalized = ''.join(normalized.split())
        return normalized

    def _is_valid_candidate(self, identifier: str) -> bool:
        if not identifier or len(identifier) < self.MIN_LENGTH:
            return False
        if identifier.lower() in self.STOPWORDS:
            return False
        if all(c in '_-' for c in identifier):
            return False
        if not any(c.isalpha() for c in identifier):
            return False
        return True

    def _identifier_score(self, identifier: str) -> float:
        score = min(len(identifier) / 20.0, 1.0) * 10
        has_upper = any(c.isupper() for c in identifier)
        has_lower = any(c.islower() for c in identifier)
        if has_upper and has_lower:
            score += 5
        if identifier.isupper() and '_' in identifier:
            score += 7
        if '_' in identifier or '-' in identifier:
            score += 3
        if '.' in identifier or '::' in identifier:
            score += 8
        return score


# Tests
def run_tests():
    service = CodeIdentifierService()

    print("\n" + "="*70)
    print("TEST 1: IDENTIFIER EXTRACTION")
    print("="*70)

    test_cases = [
        "const myVariable = 'test';",
        "class UserAccount { }",
        "function getUserById(id) { }",
        "const API_KEY = 'secret';",
        "Math.max(x, y)",
        "clearPasteboard() returns true",
    ]

    for text in test_cases:
        identifiers = service.extract_identifiers(text)
        print(f"\nText: {text}")
        print(f"Found: {identifiers}")

    print("\n" + "="*70)
    print("TEST 2: FUZZY MATCHING")
    print("="*70)

    identifiers = ['clearPasteboard', 'getUserById', 'userName', 'UserAccount', 'MAX_RETRIES']
    spoken_tests = [
        "clear pasteboard",
        "get user by id",
        "user name",
        "max retries",
    ]

    for spoken in spoken_tests:
        match = service.match_identifier(spoken, identifiers)
        print(f"\nSpoken: '{spoken}'")
        if match:
            print(f"Matched: {match.identifier} (confidence: {match.confidence:.2f})")
        else:
            print("No match found")

    print("\n" + "="*70)
    print("TEST 3: REAL CODE EXAMPLE")
    print("="*70)

    code = """
    function UserProfile({ userId, isActive }) {
        const [userData, setUserData] = React.useState(null);

        const fetchUserData = async () => {
            const response = await fetch(`/api/users/${userId}`);
            setUserData(response);
        };

        return <div className="user-profile">{userData?.name}</div>;
    }
    """

    identifiers = service.extract_identifiers(code)
    print(f"\nExtracted {len(identifiers)} identifiers:")
    print(f"  {identifiers}")

    spoken = "set user data"
    match = service.match_identifier(spoken, identifiers)
    print(f"\nSpoken: '{spoken}'")
    if match:
        print(f"Matched: {match.identifier} (confidence: {match.confidence:.2f})")

    print("\n" + "="*70)
    print("ALL TESTS COMPLETED")
    print("="*70)


if __name__ == "__main__":
    run_tests()
