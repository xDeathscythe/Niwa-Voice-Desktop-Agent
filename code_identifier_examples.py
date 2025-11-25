"""
Example usage of CodeIdentifierService for voice-to-code matching.

This demonstrates how to use the service for real-world scenarios
like voice coding assistants.
"""

import sys
from pathlib import Path

# Add src to path (adjust as needed)
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.code_identifier_service import CodeIdentifierService


def example_1_basic_extraction():
    """Example 1: Basic identifier extraction from code."""
    print("\n" + "="*70)
    print("EXAMPLE 1: Basic Identifier Extraction")
    print("="*70)

    service = CodeIdentifierService()

    code = """
    class UserManager {
        constructor(config) {
            this.userCache = new Map();
            this.MAX_CACHE_SIZE = 1000;
        }

        async getUserById(userId) {
            if (this.userCache.has(userId)) {
                return this.userCache.get(userId);
            }

            const userData = await fetch(`/api/users/${userId}`);
            this.userCache.set(userId, userData);
            return userData;
        }
    }
    """

    identifiers = service.extract_identifiers(code)

    print("\nExtracted identifiers:")
    for i, identifier in enumerate(identifiers, 1):
        id_type = service.get_identifier_type(identifier)
        print(f"  {i:2}. {identifier:25} ({id_type})")


def example_2_voice_to_code():
    """Example 2: Voice command to code identifier matching."""
    print("\n" + "="*70)
    print("EXAMPLE 2: Voice-to-Code Matching")
    print("="*70)

    service = CodeIdentifierService()

    # Simulated codebase identifiers
    codebase_identifiers = [
        'getUserById',
        'setUserData',
        'fetchUserProfile',
        'clearPasteboard',
        'isAuthenticated',
        'userName',
        'user_email',
        'MAX_RETRY_COUNT',
        'HttpClient',
        'ApiResponse',
    ]

    # Simulated voice commands (what a user might say)
    voice_commands = [
        "get user by id",
        "set user data",
        "clear pasteboard",
        "user name",
        "max retry count",
        "http client",
    ]

    print("\nMatching voice commands to code identifiers:")
    for voice in voice_commands:
        match = service.match_identifier(voice, codebase_identifiers)

        if match:
            print(f"\n  Voice: '{voice}'")
            print(f"  → Code: {match.identifier}")
            print(f"  → Confidence: {match.confidence:.1%}")
            print(f"  → Type: {match.match_type}")
        else:
            print(f"\n  Voice: '{voice}' → No match")


def example_3_react_component():
    """Example 3: Extracting identifiers from React component."""
    print("\n" + "="*70)
    print("EXAMPLE 3: React Component Analysis")
    print("="*70)

    service = CodeIdentifierService()

    component = """
    import React, { useState, useEffect } from 'react';
    import { UserAvatar } from './components/UserAvatar';

    export function UserDashboard({ userId, onLogout }) {
        const [isLoading, setIsLoading] = useState(false);
        const [userProfile, setUserProfile] = useState(null);
        const [errorMessage, setErrorMessage] = useState('');

        useEffect(() => {
            fetchUserProfile();
        }, [userId]);

        const fetchUserProfile = async () => {
            setIsLoading(true);
            try {
                const response = await fetch(`/api/users/${userId}`);
                const data = await response.json();
                setUserProfile(data);
            } catch (error) {
                setErrorMessage('Failed to load user profile');
            } finally {
                setIsLoading(false);
            }
        };

        return (
            <div className="user-dashboard">
                <UserAvatar user={userProfile} />
                {errorMessage && <p className="error">{errorMessage}</p>}
            </div>
        );
    }
    """

    identifiers = service.extract_identifiers(component)

    print(f"\nFound {len(identifiers)} identifiers in React component")

    # Group by type
    by_type = {}
    for identifier in identifiers:
        id_type = service.get_identifier_type(identifier) or 'other'
        if id_type not in by_type:
            by_type[id_type] = []
        by_type[id_type].append(identifier)

    for id_type, items in sorted(by_type.items()):
        print(f"\n  {id_type}:")
        for item in items[:10]:  # Show first 10
            print(f"    - {item}")
        if len(items) > 10:
            print(f"    ... and {len(items) - 10} more")

    # Test voice matching
    print("\n  Voice command examples:")
    test_voices = [
        "set user profile",
        "is loading",
        "error message",
        "fetch user profile",
    ]

    for voice in test_voices:
        match = service.match_identifier(voice, identifiers)
        if match:
            print(f"    '{voice}' → {match.identifier} ({match.confidence:.0%})")


def example_4_python_code():
    """Example 4: Python code identifier extraction."""
    print("\n" + "="*70)
    print("EXAMPLE 4: Python Code Analysis")
    print("="*70)

    service = CodeIdentifierService()

    python_code = """
    from typing import List, Optional
    import logging

    logger = logging.getLogger(__name__)

    class DataProcessor:
        MAX_BATCH_SIZE = 100
        DEFAULT_TIMEOUT = 30

        def __init__(self, config_path: str):
            self.config_path = config_path
            self.processed_count = 0
            self._is_initialized = False

        def process_batch(self, data_items: List[dict]) -> bool:
            if not self._is_initialized:
                logger.warning("Processor not initialized")
                return False

            batch_size = min(len(data_items), self.MAX_BATCH_SIZE)
            logger.info(f"Processing batch of {batch_size} items")

            for item in data_items[:batch_size]:
                self._process_single_item(item)
                self.processed_count += 1

            return True

        def _process_single_item(self, item: dict) -> None:
            # Implementation here
            pass
    """

    identifiers = service.extract_identifiers(python_code)

    print(f"\nExtracted {len(identifiers)} Python identifiers:")

    # Show snake_case and SCREAMING_SNAKE_CASE specifically
    snake_case = [i for i in identifiers if service.get_identifier_type(i) == 'snake_case']
    screaming = [i for i in identifiers if service.get_identifier_type(i) == 'SCREAMING_SNAKE_CASE']
    pascal_case = [i for i in identifiers if service.get_identifier_type(i) == 'PascalCase']

    print(f"\n  PascalCase ({len(pascal_case)}):")
    for item in pascal_case:
        print(f"    - {item}")

    print(f"\n  snake_case ({len(snake_case)}):")
    for item in snake_case[:15]:
        print(f"    - {item}")

    print(f"\n  SCREAMING_SNAKE_CASE ({len(screaming)}):")
    for item in screaming:
        print(f"    - {item}")


def example_5_word_splitting():
    """Example 5: Splitting identifiers into words."""
    print("\n" + "="*70)
    print("EXAMPLE 5: Identifier Word Splitting")
    print("="*70)

    service = CodeIdentifierService()

    identifiers_to_split = [
        'getUserById',
        'setUserData',
        'HTTPResponse',
        'XMLHttpRequest',
        'process_user_data',
        'MAX_RETRY_COUNT',
        'my-component-name',
        'clearPasteboard',
    ]

    print("\nSplitting identifiers into words:")
    for identifier in identifiers_to_split:
        words = service.split_identifier_words(identifier)
        print(f"  {identifier:25} → {words}")


def example_6_normalization():
    """Example 6: Identifier normalization for matching."""
    print("\n" + "="*70)
    print("EXAMPLE 6: Identifier Normalization")
    print("="*70)

    service = CodeIdentifierService()

    # Different representations of the same identifier
    variations = [
        'getUserById',
        'get_user_by_id',
        'get-user-by-id',
        'GetUserById',
        'GETUSERBYID',
        'get user by id',
    ]

    print("\nNormalizing different identifier formats:")
    for variation in variations:
        normalized = service.normalize_identifier(variation)
        print(f"  {variation:25} → '{normalized}'")

    print("\n  All normalize to the same value, enabling fuzzy matching!")


def main():
    """Run all examples."""
    print("\n" + "="*70)
    print("CODE IDENTIFIER SERVICE - USAGE EXAMPLES")
    print("="*70)

    example_1_basic_extraction()
    example_2_voice_to_code()
    example_3_react_component()
    example_4_python_code()
    example_5_word_splitting()
    example_6_normalization()

    print("\n" + "="*70)
    print("All examples completed!")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
