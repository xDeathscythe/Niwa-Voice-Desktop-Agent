"""
Visual demonstration of CodeIdentifierService pattern recognition.
Shows exactly which patterns match which identifiers.
"""

import re

def demonstrate_patterns():
    """Show what each pattern matches."""

    # Define patterns (same as in service)
    patterns = {
        'camelCase': re.compile(r'\b[a-z][a-z0-9]*[A-Z][a-zA-Z0-9]*\b'),
        'PascalCase': re.compile(r'\b[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]*)*\b'),
        'snake_case': re.compile(r'\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b'),
        'SCREAMING_SNAKE': re.compile(r'\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b'),
        'kebab-case': re.compile(r'\b[a-z][a-z0-9]*(?:-[a-z0-9]+)+\b'),
        'ACRONYM': re.compile(r'\b[A-Z]{2,5}\b'),
        'SINGLE_UPPER': re.compile(r'\b[A-Z]\b'),
        'function_call': re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(\)'),
        'namespace': re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_]*)[.:]{1,2}([a-zA-Z_][a-zA-Z0-9_]*)\b'),
    }

    # Test examples for each pattern
    test_cases = {
        'camelCase': [
            'myVariable',
            'getUserById',
            'isActive',
            'getElementById',
            'clearPasteboard',
            'a',              # Should NOT match
            'myvar',          # Should NOT match
            'MyVariable',     # Should NOT match (PascalCase)
        ],
        'PascalCase': [
            'MyClass',
            'UserAccount',
            'HttpResponse',
            'XMLParser',
            'React',
            'myClass',        # Should NOT match
            'MYCLASS',        # Should NOT match
        ],
        'snake_case': [
            'my_variable',
            'get_user_by_id',
            'user_name',
            'process_data',
            'my',             # Should NOT match
            'myVariable',     # Should NOT match
        ],
        'SCREAMING_SNAKE': [
            'MAX_VALUE',
            'API_KEY',
            'DEFAULT_TIMEOUT',
            'HTTP_PORT',
            'MAX',            # Should NOT match
            'max_value',      # Should NOT match
        ],
        'kebab-case': [
            'my-component',
            'user-profile',
            'main-container',
            'my',             # Should NOT match
            'my_component',   # Should NOT match
        ],
        'ACRONYM': [
            'HTTP',
            'API',
            'URL',
            'JSON',
            'XML',
            'H',              # Should NOT match (too short)
            'TOOLONG',        # Should NOT match (too long)
        ],
        'SINGLE_UPPER': [
            'X',
            'Y',
            'T',
            'K',
            'V',
            'x',              # Should NOT match
            'XY',             # Should NOT match
        ],
    }

    print("="*80)
    print("CODE IDENTIFIER PATTERN DEMONSTRATION")
    print("="*80)

    for pattern_name, pattern_regex in patterns.items():
        if pattern_name in ['function_call', 'namespace']:
            continue  # Skip special patterns for now

        print(f"\n{pattern_name}")
        print("-" * 80)

        examples = test_cases.get(pattern_name, [])

        for example in examples:
            matches = bool(pattern_regex.match(example))
            status = "[MATCH]" if matches else "[NO MATCH]"
            print(f"  {example:30} {status}")

    # Special patterns
    print("\n" + "="*80)
    print("SPECIAL PATTERNS")
    print("="*80)

    print("\nfunction_call (extracts identifier before parentheses)")
    print("-" * 80)
    function_examples = [
        'getData()',
        'myFunc()',
        'process()',
        'Math.max()',
    ]
    for example in function_examples:
        match = patterns['function_call'].search(example)
        if match:
            print(f"  {example:30} -> extracts: '{match.group(1)}'")
        else:
            print(f"  {example:30} [X] NO MATCH")

    print("\nnamespace (module.member or namespace::member)")
    print("-" * 80)
    namespace_examples = [
        'Math.max',
        'std::vector',
        'os.path',
        'React.useState',
        'logger.info',
    ]
    for example in namespace_examples:
        match = patterns['namespace'].search(example)
        if match:
            print(f"  {example:30} -> namespace: '{match.group(1)}', member: '{match.group(2)}'")
        else:
            print(f"  {example:30} [X] NO MATCH")

    # Real-world examples
    print("\n" + "="*80)
    print("REAL-WORLD CODE EXAMPLES")
    print("="*80)

    code_samples = [
        ("JavaScript", "const myVariable = getUserById(userId);"),
        ("Python", "def process_user_data(user_id, max_retries=MAX_RETRIES):"),
        ("React", "<MyComponent className='user-profile' isActive={true} />"),
        ("Math", "let result = Math.max(X, Y);"),
    ]

    for lang, code in code_samples:
        print(f"\n{lang}: {code}")
        print("-" * 80)

        # Find all matches for each pattern
        all_matches = set()
        for pattern_name, pattern_regex in patterns.items():
            if pattern_name == 'function_call':
                for match in pattern_regex.finditer(code):
                    all_matches.add((match.group(1), pattern_name))
            elif pattern_name == 'namespace':
                for match in pattern_regex.finditer(code):
                    all_matches.add((f"{match.group(1)}.{match.group(2)}", pattern_name))
                    all_matches.add((match.group(1), 'namespace_part'))
                    all_matches.add((match.group(2), 'namespace_part'))
            else:
                for match in pattern_regex.finditer(code):
                    all_matches.add((match.group(0), pattern_name))

        # Sort and display
        for identifier, pattern_type in sorted(all_matches):
            print(f"  {identifier:25} ({pattern_type})")

    print("\n" + "="*80)


def demonstrate_stopwords():
    """Show stopword filtering."""

    stopwords = {
        'the', 'and', 'or', 'if', 'is', 'var', 'const', 'function',
        'class', 'return', 'import', 'new', 'this'
    }

    print("\n" + "="*80)
    print("STOPWORD FILTERING DEMONSTRATION")
    print("="*80)

    test_identifiers = [
        ('myVariable', False),
        ('the', True),
        ('getUserById', False),
        ('if', True),
        ('UserClass', False),
        ('class', True),
        ('MAX_VALUE', False),
        ('var', True),
    ]

    print("\nIdentifier          Stopword?   Filtered?")
    print("-" * 80)

    for identifier, is_stopword in test_identifiers:
        filtered = is_stopword
        status = "[FILTERED]" if filtered else "[KEPT]"
        print(f"{identifier:20} {'Yes' if is_stopword else 'No ':3}         {status}")


def demonstrate_fuzzy_matching():
    """Show fuzzy matching examples."""

    print("\n" + "="*80)
    print("FUZZY MATCHING DEMONSTRATION")
    print("="*80)

    examples = [
        ("Exact (normalized)", "clear pasteboard", "clearPasteboard", 1.00),
        ("Exact (normalized)", "get user by id", "getUserById", 1.00),
        ("High confidence", "user name", "userName", 1.00),
        ("High confidence", "max retries", "MAX_RETRIES", 1.00),
        ("Partial match", "user", "userName", 0.75),
        ("Partial match", "get user", "getUserById", 0.85),
    ]

    print("\nSpoken Text          Target Identifier    Expected Confidence")
    print("-" * 80)

    for match_type, spoken, target, confidence in examples:
        print(f"{spoken:20} -> {target:20} {confidence:.0%} ({match_type})")

    print("\nNormalization Process:")
    print("-" * 80)
    norm_examples = [
        "clearPasteboard",
        "clear_pasteboard",
        "clear-pasteboard",
        "ClearPasteboard",
        "CLEARPASTEBOARD",
        "clear pasteboard",
    ]

    print("All of these normalize to: 'clearpasteboard'")
    for example in norm_examples:
        normalized = example.lower().replace('_', '').replace('-', '').replace(' ', '')
        print(f"  {example:25} -> '{normalized}'")


if __name__ == "__main__":
    demonstrate_patterns()
    demonstrate_stopwords()
    demonstrate_fuzzy_matching()

    print("\n" + "="*80)
    print("DEMONSTRATION COMPLETE")
    print("="*80 + "\n")
