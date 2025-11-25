"""Test script for CodeIdentifierService."""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.code_identifier_service import CodeIdentifierService

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s - %(message)s'
)

def test_extraction():
    """Test identifier extraction from various code samples."""
    service = CodeIdentifierService()

    test_cases = [
        # JavaScript/TypeScript
        ("const myVariable = 'test';", ['myVariable']),
        ("class UserAccount { }", ['UserAccount']),
        ("function getUserById(id) { }", ['getUserById', 'id']),
        ("const API_KEY = 'secret';", ['API_KEY']),
        ("const my_snake_case = 42;", ['my_snake_case']),

        # Python
        ("def get_user_by_id(user_id):", ['get_user_by_id', 'user_id']),
        ("class HttpResponse:", ['HttpResponse']),
        ("MAX_RETRIES = 5", ['MAX_RETRIES']),

        # React/JSX
        ("<MyComponent user-id='123' />", ['MyComponent', 'user-id']),

        # Namespace/Module access
        ("Math.max(x, y)", ['Math', 'max', 'Math.max', 'x', 'y']),
        ("std::vector<int>", ['std', 'vector', 'std.vector']),

        # Mixed
        ("clearPasteboard() returns true", ['clearPasteboard']),
        ("const isActive = checkStatus();", ['isActive', 'checkStatus']),

        # Complex example
        (
            "const userProfile = new UserProfile(); userProfile.getName()",
            ['userProfile', 'UserProfile', 'getName', 'userProfile.getName']
        ),
    ]

    print("\n" + "="*60)
    print("TESTING IDENTIFIER EXTRACTION")
    print("="*60)

    for text, expected in test_cases:
        print(f"\nText: {text}")
        identifiers = service.extract_identifiers(text)
        print(f"Found: {identifiers}")
        print(f"Expected: {expected}")

        # Check if all expected identifiers were found
        found_all = all(exp in identifiers for exp in expected)
        status = "✓ PASS" if found_all else "✗ FAIL"
        print(f"Status: {status}")

        if not found_all:
            missing = [exp for exp in expected if exp not in identifiers]
            print(f"Missing: {missing}")

def test_validation():
    """Test identifier validation."""
    service = CodeIdentifierService()

    test_cases = [
        # Valid identifiers
        ("myVariable", True),
        ("UserAccount", True),
        ("get_user", True),
        ("MAX_VALUE", True),
        ("my-component", True),
        ("X", True),  # Single uppercase
        ("HTTP", True),  # Acronym

        # Invalid (stopwords or too short)
        ("the", False),
        ("and", False),
        ("if", False),
        ("a", False),
        ("is", False),
    ]

    print("\n" + "="*60)
    print("TESTING IDENTIFIER VALIDATION")
    print("="*60)

    for identifier, expected in test_cases:
        result = service.is_valid_identifier(identifier)
        status = "✓ PASS" if result == expected else "✗ FAIL"
        print(f"{identifier:20} -> {result:5} (expected {expected:5}) {status}")

def test_fuzzy_matching():
    """Test fuzzy matching of spoken text to identifiers."""
    service = CodeIdentifierService()

    identifiers = [
        'clearPasteboard',
        'getUserById',
        'userName',
        'user_name',
        'UserAccount',
        'MAX_RETRIES',
        'isActive',
        'HttpResponse',
        'myComponent',
    ]

    test_cases = [
        # Spoken text -> expected match
        ("clear pasteboard", "clearPasteboard"),
        ("get user by id", "getUserById"),
        ("user name", "userName"),  # or user_name
        ("user account", "UserAccount"),
        ("max retries", "MAX_RETRIES"),
        ("is active", "isActive"),
        ("http response", "HttpResponse"),
        ("my component", "myComponent"),

        # Exact matches (normalized)
        ("clearpasteboard", "clearPasteboard"),
        ("getuserbyid", "getUserById"),
    ]

    print("\n" + "="*60)
    print("TESTING FUZZY MATCHING")
    print("="*60)

    for spoken, expected in test_cases:
        match = service.match_identifier(spoken, identifiers)

        print(f"\nSpoken: '{spoken}'")
        if match:
            print(f"Matched: {match.identifier} (confidence: {match.confidence:.2f}, type: {match.match_type})")
            status = "✓ PASS" if match.identifier == expected else "⚠ PARTIAL"
            if match.identifier != expected:
                print(f"Expected: {expected}")
        else:
            print(f"No match found (expected: {expected})")
            status = "✗ FAIL"

        print(f"Status: {status}")

def test_normalization():
    """Test identifier normalization."""
    service = CodeIdentifierService()

    test_cases = [
        ("myVariable", "myvariable"),
        ("my_variable", "myvariable"),
        ("my-variable", "myvariable"),
        ("MyVariable", "myvariable"),
        ("MY_VARIABLE", "myvariable"),
        ("my variable", "myvariable"),
        ("Math.max", "mathmax"),
        ("std::vector", "stdvector"),
    ]

    print("\n" + "="*60)
    print("TESTING NORMALIZATION")
    print("="*60)

    for identifier, expected in test_cases:
        result = service.normalize_identifier(identifier)
        status = "✓ PASS" if result == expected else "✗ FAIL"
        print(f"{identifier:20} -> {result:20} (expected {expected:20}) {status}")

def test_identifier_types():
    """Test identifier type detection."""
    service = CodeIdentifierService()

    test_cases = [
        ("myVariable", "camelCase"),
        ("MyClass", "PascalCase"),
        ("my_variable", "snake_case"),
        ("MAX_VALUE", "SCREAMING_SNAKE_CASE"),
        ("my-component", "kebab-case"),
        ("HTTP", "ACRONYM"),
        ("X", "SINGLE_UPPER"),
    ]

    print("\n" + "="*60)
    print("TESTING IDENTIFIER TYPE DETECTION")
    print("="*60)

    for identifier, expected in test_cases:
        result = service.get_identifier_type(identifier)
        status = "✓ PASS" if result == expected else "✗ FAIL"
        print(f"{identifier:20} -> {result or 'None':25} (expected {expected:25}) {status}")

def test_word_splitting():
    """Test splitting identifiers into words."""
    service = CodeIdentifierService()

    test_cases = [
        ("getUserById", ['get', 'User', 'By', 'Id']),
        ("user_name", ['user', 'name']),
        ("my-component", ['my', 'component']),
        ("HTTPResponse", ['HTTP', 'Response']),
        ("clearPasteboard", ['clear', 'Pasteboard']),
        ("MAX_RETRIES", ['MAX', 'RETRIES']),
    ]

    print("\n" + "="*60)
    print("TESTING WORD SPLITTING")
    print("="*60)

    for identifier, expected in test_cases:
        result = service.split_identifier_words(identifier)
        status = "✓ PASS" if result == expected else "✗ FAIL"
        print(f"{identifier:20} -> {result}")
        print(f"{'':20}    Expected: {expected} {status}")

def test_real_world_scenarios():
    """Test with real-world code snippets."""
    service = CodeIdentifierService()

    scenarios = [
        {
            "name": "JavaScript React Component",
            "code": """
                import React from 'react';

                function UserProfile({ userId, isActive }) {
                    const [userData, setUserData] = React.useState(null);

                    const fetchUserData = async () => {
                        const response = await fetch(`/api/users/${userId}`);
                        const data = await response.json();
                        setUserData(data);
                    };

                    return <div className="user-profile">{userData?.name}</div>;
                }
            """,
            "spoken": "set user data",
            "expected": "setUserData"
        },
        {
            "name": "Python Data Processing",
            "code": """
                def process_user_data(user_id, include_metadata=False):
                    raw_data = fetch_raw_data(user_id)
                    processed_data = transform_data(raw_data)

                    if include_metadata:
                        metadata = get_metadata(user_id)
                        return {**processed_data, **metadata}

                    return processed_data
            """,
            "spoken": "include metadata",
            "expected": "include_metadata"
        },
    ]

    print("\n" + "="*60)
    print("TESTING REAL-WORLD SCENARIOS")
    print("="*60)

    for scenario in scenarios:
        print(f"\n{scenario['name']}")
        print("-" * 60)

        identifiers = service.extract_identifiers(scenario['code'])
        print(f"Extracted {len(identifiers)} identifiers:")
        print(f"  {', '.join(identifiers[:15])}")
        if len(identifiers) > 15:
            print(f"  ... and {len(identifiers) - 15} more")

        match = service.match_identifier(scenario['spoken'], identifiers)
        print(f"\nSpoken: '{scenario['spoken']}'")
        if match:
            print(f"Matched: {match.identifier} (confidence: {match.confidence:.2f})")
            status = "✓ PASS" if match.identifier == scenario['expected'] else "⚠ PARTIAL"
            if match.identifier != scenario['expected']:
                print(f"Expected: {scenario['expected']}")
        else:
            print(f"No match (expected: {scenario['expected']})")
            status = "✗ FAIL"

        print(f"Status: {status}")

if __name__ == "__main__":
    print("\n" + "="*60)
    print("CODE IDENTIFIER SERVICE - COMPREHENSIVE TEST SUITE")
    print("="*60)

    try:
        test_extraction()
        test_validation()
        test_fuzzy_matching()
        test_normalization()
        test_identifier_types()
        test_word_splitting()
        test_real_world_scenarios()

        print("\n" + "="*60)
        print("ALL TESTS COMPLETED")
        print("="*60)

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
