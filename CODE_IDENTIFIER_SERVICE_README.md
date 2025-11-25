# Code Identifier Service

## Overview

The `CodeIdentifierService` is a comprehensive parser for extracting code identifiers (variables, functions, classes) from text and matching them with voice commands. It's designed for voice coding assistants like VoiceType.

**Location**: `src/services/code_identifier_service.py`

## Features

### 1. Multi-Convention Support

Recognizes all major naming conventions:

- **camelCase**: `myVariableName`, `getUserById`, `isActive`
- **PascalCase**: `MyClassName`, `UserAccount`, `HttpResponse`
- **snake_case**: `my_variable_name`, `get_user_by_id`
- **SCREAMING_SNAKE_CASE**: `MY_CONSTANT`, `API_KEY`, `MAX_RETRIES`
- **kebab-case**: `my-component-name`, `user-profile`
- **Acronyms**: `HTTP`, `API`, `URL`, `JSON` (2-5 letters)
- **Single uppercase**: `X`, `Y`, `T` (for generics/math)

### 2. Advanced Pattern Recognition

- **Function calls**: Detects `functionName()` patterns
- **Namespace/module access**: `Math.max`, `std::vector`, `os.path`
- **Mixed patterns**: `React.useState`, `logger.info`

### 3. Intelligent Filtering

- **Stopword filtering**: Removes 75+ common English words and programming keywords
- **Minimum length**: Configurable (default: 2 characters)
- **False positive prevention**: Filters out non-identifiers

### 4. Fuzzy Matching

Matches spoken commands to code identifiers:
- "clear pasteboard" → `clearPasteboard`
- "get user by id" → `getUserById`
- "max retries" → `MAX_RETRIES`

**Matching features**:
- Exact match detection (normalized)
- Sequence similarity scoring
- Prefix/suffix bonuses
- Multi-word boundary matching
- Configurable confidence threshold

## API Reference

### Core Methods

#### `__init__()`
```python
service = CodeIdentifierService()
```
Initializes the service with pre-compiled regex patterns for efficiency.

#### `extract_identifiers(text: str) -> list[str]`
```python
code = "const myVar = new MyClass();"
identifiers = service.extract_identifiers(code)
# Returns: ['MyClass', 'myVar']
```
Extracts all code identifiers from text, sorted by likelihood score.

**Returns**: List of unique identifiers, highest-scored first

#### `is_valid_identifier(word: str) -> bool`
```python
is_valid = service.is_valid_identifier("myVariable")
# Returns: True

is_valid = service.is_valid_identifier("the")
# Returns: False (stopword)
```
Checks if a word appears to be a valid code identifier.

#### `match_identifier(spoken_text: str, identifiers: list[str], threshold: float = 0.6) -> Optional[IdentifierMatch]`
```python
identifiers = ['clearPasteboard', 'getUserById', 'userName']
match = service.match_identifier("clear pasteboard", identifiers)

if match:
    print(f"Matched: {match.identifier}")
    print(f"Confidence: {match.confidence:.2f}")
    print(f"Type: {match.match_type}")
```
Fuzzy matches spoken text to known identifiers.

**Parameters**:
- `spoken_text`: Voice command or spoken identifier
- `identifiers`: List of code identifiers to match against
- `threshold`: Minimum confidence (0.0-1.0, default 0.6)

**Returns**: `IdentifierMatch` object or `None`

#### `normalize_identifier(word: str) -> str`
```python
normalized = service.normalize_identifier("getUserById")
# Returns: "getuserbyid"

normalized = service.normalize_identifier("get_user_by_id")
# Returns: "getuserbyid"
```
Normalizes identifiers for comparison by removing separators and case.

### Helper Methods

#### `get_identifier_type(identifier: str) -> Optional[str]`
```python
id_type = service.get_identifier_type("myVariable")
# Returns: "camelCase"

id_type = service.get_identifier_type("MAX_VALUE")
# Returns: "SCREAMING_SNAKE_CASE"
```
Determines the naming convention used.

**Returns**: One of: `'camelCase'`, `'PascalCase'`, `'snake_case'`, `'SCREAMING_SNAKE_CASE'`, `'kebab-case'`, `'ACRONYM'`, `'SINGLE_UPPER'`, or `None`

#### `split_identifier_words(identifier: str) -> list[str]`
```python
words = service.split_identifier_words("getUserById")
# Returns: ['get', 'User', 'By', 'Id']

words = service.split_identifier_words("user_name")
# Returns: ['user', 'name']
```
Splits an identifier into component words.

#### `cleanup()`
```python
service.cleanup()
```
Cleans up resources (logs cleanup message).

## Data Classes

### `IdentifierMatch`
```python
@dataclass
class IdentifierMatch:
    identifier: str      # The matched identifier
    confidence: float    # Match confidence (0.0 to 1.0)
    match_type: str     # 'exact' or 'fuzzy'
```

## Configuration

### Stopwords
The service includes 75+ stopwords to filter out:
- Common English words (a, the, and, etc.)
- Programming keywords (var, const, function, etc.)
- Common verbs (is, get, set, etc.)

**Customization**: Modify `CodeIdentifierService.STOPWORDS` set

### Minimum Lengths
```python
MIN_LENGTH = 2  # Minimum identifier length
MIN_SINGLE_CHAR_UPPERCASE = True  # Allow single uppercase (X, Y, T)
```

## Usage Examples

### Example 1: Extract from JavaScript Code
```python
service = CodeIdentifierService()

code = """
function UserProfile({ userId, isActive }) {
    const [userData, setUserData] = useState(null);

    const fetchUserData = async () => {
        const response = await fetch(`/api/users/${userId}`);
        setUserData(response);
    };
}
"""

identifiers = service.extract_identifiers(code)
# Returns: ['fetchUserData', 'setUserData', 'UserProfile', 'userData', 'isActive', 'userId', ...]
```

### Example 2: Voice-to-Code Matching
```python
# Your codebase identifiers
codebase = [
    'getUserById',
    'setUserData',
    'clearPasteboard',
    'isAuthenticated',
    'MAX_RETRY_COUNT'
]

# User says: "set user data"
match = service.match_identifier("set user data", codebase)
print(match.identifier)  # "setUserData"
print(match.confidence)   # 1.0
```

### Example 3: Python Code Analysis
```python
python_code = """
class DataProcessor:
    MAX_BATCH_SIZE = 100

    def __init__(self, config_path: str):
        self.config_path = config_path
        self._is_initialized = False

    def process_batch(self, data_items: List[dict]) -> bool:
        # Implementation
        pass
"""

identifiers = service.extract_identifiers(python_code)
# Returns: ['DataProcessor', 'MAX_BATCH_SIZE', 'config_path',
#           'process_batch', 'data_items', ...]
```

### Example 4: Type Detection and Word Splitting
```python
# Detect identifier type
id_type = service.get_identifier_type("getUserById")
# Returns: "camelCase"

# Split into words
words = service.split_identifier_words("getUserById")
# Returns: ['get', 'User', 'By', 'Id']

# Normalize for matching
normalized = service.normalize_identifier("get_user_by_id")
# Returns: "getuserbyid"
```

## Testing

### Standalone Test
Run the standalone test (no dependencies):
```bash
python test_identifier_standalone.py
```

### Example Usage
Run comprehensive examples:
```bash
python code_identifier_examples.py
```

### Full Test Suite
Run the complete test suite (requires project dependencies):
```bash
python test_code_identifier.py
```

## Implementation Details

### Regex Patterns
All patterns are compiled once during initialization for efficiency:
- `_camel_case_pattern`: Matches camelCase
- `_pascal_case_pattern`: Matches PascalCase
- `_snake_case_pattern`: Matches snake_case
- `_screaming_snake_pattern`: Matches SCREAMING_SNAKE_CASE
- `_kebab_case_pattern`: Matches kebab-case
- `_single_upper_pattern`: Matches single uppercase letters
- `_acronym_pattern`: Matches 2-5 letter acronyms
- `_function_call_pattern`: Matches function()
- `_namespace_pattern`: Matches namespace.member or namespace::member

### Scoring System
Identifiers are scored based on:
- **Length**: Longer identifiers score higher (up to 20 chars)
- **Case mixing**: Mixed case gets +5 bonus
- **Separators**: Underscores/hyphens get +3 bonus
- **Constants**: All uppercase with underscores get +7 bonus
- **Namespace**: Dot/double-colon notation gets +8 bonus

### Fuzzy Matching Algorithm
1. **Normalization**: Remove case, separators, whitespace
2. **Exact match check**: Return 1.0 confidence if normalized forms match
3. **Sequence matching**: Use `difflib.SequenceMatcher` for similarity
4. **Bonuses**:
   - Starts with: +0.2
   - Same length: +0.1
   - Multi-word boundaries: +0.15
5. **Threshold filter**: Only return matches above threshold (default 0.6)

## Performance Characteristics

- **Regex compilation**: O(1) - done once at initialization
- **Extraction**: O(n) where n = text length
- **Fuzzy matching**: O(m×k) where m = identifiers, k = comparison cost
- **Memory**: Minimal - uses compiled patterns and sets

## Logging

The service uses Python's logging module:
```python
import logging
logging.basicConfig(level=logging.INFO)
```

**Log levels**:
- `INFO`: Service lifecycle, matches found
- `DEBUG`: Pattern matches, filtering decisions
- `WARNING`: N/A
- `ERROR`: N/A

## Integration with VoiceType

This service is designed to integrate with VoiceType's voice coding features:

1. **Extract identifiers** from user's codebase or current file
2. **Listen for voice commands** via transcription service
3. **Match voice to code** using fuzzy matching
4. **Inject matched identifier** via text injection service

Example integration:
```python
# Extract from current file
identifiers = code_identifier_service.extract_identifiers(current_file_content)

# User speaks: "set user data"
transcribed = transcription_service.transcribe(audio)

# Find match
match = code_identifier_service.match_identifier(transcribed, identifiers)

if match and match.confidence > 0.7:
    # Inject the code identifier
    text_injection_service.inject(match.identifier)
```

## Limitations and Future Enhancements

### Current Limitations
- No semantic analysis (purely pattern-based)
- Language-agnostic (doesn't understand specific language syntax)
- No context awareness (function vs variable vs class)

### Potential Enhancements
- Phonetic matching for homophones
- Context-aware type detection (is it a class, function, variable?)
- Language-specific optimizations
- Learning from user corrections
- Integration with LSP (Language Server Protocol) for accurate identifier lists

## License

Part of the VoiceType project.
