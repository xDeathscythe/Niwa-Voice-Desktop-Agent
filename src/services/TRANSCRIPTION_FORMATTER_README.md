# TranscriptionFormatterService

A post-processor service that intelligently wraps code identifiers in backticks within transcribed text.

## Overview

When transcribing code-related speech, identifiers like `clearPasteboard`, `AudioService`, or `get_user_data` are often spoken as natural language ("clear pasteboard", "audio service", "get user data"). This service automatically detects these patterns and wraps them in backticks for better readability in documentation, code reviews, or technical notes.

## Features

- **Intelligent Matching**: Matches spoken phrases to code identifiers with fuzzy logic
- **Multiple Naming Conventions**: Supports camelCase, PascalCase, and snake_case
- **Conservative Formatting**: Only wraps when confident, avoiding over-formatting
- **Context Awareness**: Preserves existing formatting (quotes, backticks, URLs)
- **Overlap Prevention**: Prefers longer matches over shorter ones
- **Extensive Logging**: Debug-level logging for match decisions

## Installation

The service is part of the VoiceType services module:

```python
from services import TranscriptionFormatterService
```

## API

### TranscriptionFormatterService

#### `__init__()`

Initialize the formatter service.

```python
formatter = TranscriptionFormatterService()
```

#### `format_with_code_identifiers(text: str, identifiers: list[str]) -> str`

Wrap code identifiers in backticks in transcribed text.

**Parameters:**
- `text` (str): Raw transcription text
- `identifiers` (list[str]): List of known code identifiers to match

**Returns:**
- str: Formatted text with identifiers wrapped in backticks

**Example:**
```python
text = "use the clear pasteboard function to reset"
identifiers = ["clearPasteboard", "reset"]
result = formatter.format_with_code_identifiers(text, identifiers)
# Result: "use the `clearPasteboard` function to `reset`"
```

#### `cleanup()`

Clean up resources (for consistency with other services).

```python
formatter.cleanup()
```

### Private Methods

#### `_is_already_formatted(text: str, start: int, end: int) -> bool`

Check if text at position is already in backticks, quotes, or special context.

#### `_match_spoken_to_identifier(spoken_phrase: str, identifiers: list[str]) -> Optional[str]`

Match spoken phrase to known identifier with fuzzy logic.

#### `_generate_spoken_forms(identifier: str) -> list[str]`

Generate possible spoken forms of a code identifier.

#### `_overlaps_with_replacements(start: int, end: int, replacements: list) -> bool`

Check if position range overlaps with existing replacements.

## Matching Logic

### Naming Convention Support

The service understands multiple naming conventions:

| Convention | Example Identifier | Spoken Forms |
|------------|-------------------|--------------|
| camelCase | `clearPasteboard` | "clear pasteboard", "clear paste board" |
| PascalCase | `AudioService` | "audio service", "Audio Service" |
| snake_case | `get_user_data` | "get user data", "getdata" |
| kebab-case | `whisper-1` | "whisper-1" |

### Fuzzy Matching

The service generates multiple spoken forms for each identifier:

```python
"clearPasteboard" → ["clearPasteboard", "clear Pasteboard", "clear pasteboard"]
"get_user_data" → ["get_user_data", "get user data", "getuserdata"]
"AudioService" → ["AudioService", "Audio Service", "audio service"]
```

### Preference for Longer Matches

When multiple identifiers could match, the service prefers longer ones:

```python
text = "use clear pasteboard data to clear"
identifiers = ["clearPasteboardData", "clearPasteboard", "clear"]
# Result: "use `clearPasteboardData` to `clear`"
# Not: "use `clear` `pasteboard` data to `clear`"
```

## Formatting Rules

### 1. Don't Wrap if Already Formatted

```python
text = "the `clearPasteboard` method"
# Output: "the `clearPasteboard` method" (unchanged)
```

### 2. Don't Wrap in Quotes

```python
text = 'use "clear pasteboard" as name'
# Output: 'use "clear pasteboard" as name' (unchanged)

text = "use 'clear pasteboard' as name"
# Output: "use 'clear pasteboard' as name" (unchanged)
```

### 3. Don't Wrap in URLs or Paths

```python
text = "visit https://example.com/clear/pasteboard"
# Output: "visit https://example.com/clear/pasteboard" (unchanged)

text = "file at C:/path/clear/pasteboard"
# Output: "file at C:/path/clear/pasteboard" (unchanged)
```

### 4. Handle Multiple Occurrences

```python
text = "reset the state then reset again"
identifiers = ["reset"]
# Output: "`reset` the state then `reset` again"
```

### 5. Work at Sentence Boundaries

```python
text = "Clear pasteboard. Use reset method."
identifiers = ["clearPasteboard", "reset"]
# Output: "`clearPasteboard`. Use `reset` method."
```

## Usage Examples

### Basic Usage

```python
from services import TranscriptionFormatterService

formatter = TranscriptionFormatterService()

# Simple case
text = "call the get data function"
result = formatter.format_with_code_identifiers(text, ["get_data"])
print(result)  # "call the `get_data` function"
```

### Real-World Code Review

```python
text = """
the transcription service uses the audio preprocessing service
for noise reduction. the preprocess audio method should be called
before whisper one transcription.
"""

identifiers = [
    "TranscriptionService",
    "AudioPreprocessingService",
    "preprocess_audio",
    "noise_reduction",
    "whisper-1"
]

result = formatter.format_with_code_identifiers(text, identifiers)
print(result)
# Output:
# the `TranscriptionService` uses the `AudioPreprocessingService`
# for `noise_reduction`. the `preprocess_audio` method should be called
# before whisper one transcription.
```

### Integration with Transcription Pipeline

```python
from services import TranscriptionService, TranscriptionFormatterService

# Transcribe audio
transcription_service = TranscriptionService(api_key="...")
result = transcription_service.transcribe(audio_data)

# Format with code identifiers
formatter = TranscriptionFormatterService()
code_identifiers = ["clearPasteboard", "AudioService", "reset"]
formatted_text = formatter.format_with_code_identifiers(
    result.cleaned_text,
    code_identifiers
)

print(formatted_text)
```

### Dynamic Identifier Extraction

```python
# Extract identifiers from your codebase
def get_code_identifiers_from_file(filepath):
    """Extract function/class names from Python file."""
    import ast
    identifiers = []

    with open(filepath) as f:
        tree = ast.parse(f.read())

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            identifiers.append(node.name)

    return identifiers

# Use in formatter
identifiers = get_code_identifiers_from_file("services/audio_service.py")
formatted = formatter.format_with_code_identifiers(transcription, identifiers)
```

## Logging

The service provides extensive logging at different levels:

```python
import logging

# Enable debug logging to see match decisions
logging.basicConfig(level=logging.DEBUG)

formatter = TranscriptionFormatterService()
result = formatter.format_with_code_identifiers(
    "use clear pasteboard",
    ["clearPasteboard"]
)

# Output:
# DEBUG - Formatting text with 1 identifiers
# DEBUG - Identifier 'clearPasteboard' -> spoken forms: ['clearPasteboard', 'clear Pasteboard']
# DEBUG - Matched 'clear Pasteboard' -> 'clearPasteboard' at 4-20
# DEBUG - Applied replacement: 'clear pasteboard' -> '`clearPasteboard`'
# INFO - Applied 1 formatting replacements
```

## Performance Considerations

### Complexity

- **Time Complexity**: O(n × m × p) where:
  - n = number of identifiers
  - m = number of spoken forms per identifier
  - p = length of text

- **Space Complexity**: O(n × m) for storing spoken forms

### Optimization Tips

1. **Sort identifiers by length**: Longer identifiers are checked first to prefer longer matches
2. **Avoid duplicate identifiers**: Remove duplicates before passing to the formatter
3. **Limit identifier list**: Only include relevant identifiers for the context

```python
# Good: Filtered, relevant identifiers
identifiers = ["clearPasteboard", "AudioService", "reset"]

# Avoid: Entire codebase (thousands of identifiers)
# identifiers = extract_all_identifiers_from_project()  # Too many!
```

## Edge Cases

### Empty Inputs

```python
formatter.format_with_code_identifiers("", [])  # Returns ""
formatter.format_with_code_identifiers("text", [])  # Returns "text"
formatter.format_with_code_identifiers("", ["func"])  # Returns ""
```

### Case Sensitivity

Matching is case-insensitive, but original identifier casing is preserved:

```python
text = "use CLEAR PASTEBOARD function"
identifiers = ["clearPasteboard"]
# Output: "use `clearPasteboard` function"
```

### Partial Matches

Only whole word matches are considered:

```python
text = "use clipboard function"
identifiers = ["clearPasteboard"]  # Contains "board" but no match
# Output: "use clipboard function" (unchanged)
```

### Special Characters

Identifiers with special characters need exact matches:

```python
text = "use whisper one model"
identifiers = ["whisper-1"]
# Output: "use whisper one model" (no match - "whisper one" != "whisper-1")

text = "use whisper dash one model"
identifiers = ["whisper-1"]
# Output: "use whisper dash one model" (no match)
```

## Testing

Run the example script to test all scenarios:

```bash
cd src/services
python transcription_formatter_example.py
```

## Best Practices

1. **Be Conservative**: Only include identifiers you're confident will appear in speech
2. **Context Matters**: Include identifiers relevant to the current discussion/file
3. **Review Output**: Check formatted text before using in production
4. **Enable Logging**: Use DEBUG level during development to understand matching
5. **Handle Edge Cases**: Test with your specific use cases and speech patterns

## Limitations

1. **No Semantic Understanding**: The service uses pattern matching, not semantic analysis
2. **Transcription Quality**: Depends on accurate transcription (garbage in, garbage out)
3. **Language Support**: Optimized for English; may not work well with other languages
4. **Homophones**: Cannot distinguish between homophones (e.g., "cache" vs "cash")
5. **Context Sensitivity**: Cannot determine if an identifier is actually being referenced

## Future Enhancements

Potential improvements for future versions:

- [ ] Machine learning-based matching for better accuracy
- [ ] Context-aware filtering (only match identifiers from current file)
- [ ] Support for property paths (e.g., "user.name" → `user.name`)
- [ ] Configurable formatting styles (bold, italics, etc.)
- [ ] Integration with LSP for real-time identifier extraction
- [ ] Multi-language support for transcription

## Contributing

When modifying this service:

1. Maintain backward compatibility with existing API
2. Add logging for all match decisions
3. Update tests and examples
4. Document new features in this README
5. Follow the existing code style and patterns

## License

Part of the VoiceType project.
