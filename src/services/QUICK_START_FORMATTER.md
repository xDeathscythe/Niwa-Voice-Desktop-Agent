# Quick Start Guide: TranscriptionFormatterService

## Installation

The service is already integrated into your VoiceType project. No additional dependencies required.

## Basic Usage

```python
from services import TranscriptionFormatterService

# Initialize
formatter = TranscriptionFormatterService()

# Format text
text = "use the clear pasteboard function to reset"
identifiers = ["clearPasteboard", "reset"]
result = formatter.format_with_code_identifiers(text, identifiers)

print(result)
# Output: "use the `clearPasteboard` function to `reset`"

# Cleanup
formatter.cleanup()
```

## Integration with Transcription Pipeline

```python
from services import TranscriptionService, TranscriptionFormatterService

# Step 1: Transcribe audio
transcription_service = TranscriptionService(api_key="your-key")
transcription_result = transcription_service.transcribe(audio_data)

# Step 2: Format with code identifiers
formatter = TranscriptionFormatterService()
code_identifiers = [
    "TranscriptionService",
    "AudioService",
    "clearPasteboard",
    "get_user_data"
]

formatted_text = formatter.format_with_code_identifiers(
    transcription_result.cleaned_text,
    code_identifiers
)

print(formatted_text)
```

## Common Use Cases

### 1. Code Review Comments

```python
formatter = TranscriptionFormatterService()

comment = "the transcribe method should handle errors better"
identifiers = ["transcribe", "handle_errors"]

formatted = formatter.format_with_code_identifiers(comment, identifiers)
# Output: "the `transcribe` method should `handle_errors` better"
```

### 2. Documentation Generation

```python
doc = "Use Audio Service to start recording and stop recording"
identifiers = ["AudioService", "start_recording", "stop_recording"]

formatted = formatter.format_with_code_identifiers(doc, identifiers)
# Output: "Use `AudioService` to `start_recording` and `stop_recording`"
```

### 3. Technical Notes

```python
note = "call preprocess audio before calling whisper"
identifiers = ["preprocess_audio", "whisper"]

formatted = formatter.format_with_code_identifiers(note, identifiers)
# Output: "call `preprocess_audio` before calling `whisper`"
```

## Examples and Tests

Run the included examples:

```bash
# Basic examples
python transcription_formatter_example.py

# Integration examples
python transcription_formatter_integration_example.py

# Unit tests (30 tests)
python test_transcription_formatter.py
```

## Tips

1. **Be Specific**: Include only relevant identifiers for your context
2. **Sort by Priority**: Longer/more specific identifiers first
3. **Enable Logging**: Use `logging.DEBUG` to see match decisions
4. **Test First**: Run examples with your specific use case

## Supported Naming Conventions

- **camelCase**: `clearPasteboard` → "clear pasteboard"
- **PascalCase**: `AudioService` → "audio service"
- **snake_case**: `get_user_data` → "get user data"
- **kebab-case**: `whisper-1` → exact match only

## What Gets Formatted

✓ Standalone identifiers: "use clearPasteboard" → "use `clearPasteboard`"
✓ Multiple occurrences: "reset then reset" → "`reset` then `reset`"
✓ Sentence boundaries: "Reset. Then clear." → "`Reset`. Then `clear`."

## What Doesn't Get Formatted

✗ Already formatted: `` `clearPasteboard` `` stays as-is
✗ In quotes: `"clearPasteboard"` stays as-is
✗ In URLs: `https://api.com/clear` stays as-is
✗ Partial matches: "clipboard" doesn't match "clearPasteboard"

## Troubleshooting

**Issue**: Nothing gets formatted
**Solution**: Check if identifiers match spoken forms (enable DEBUG logging)

**Issue**: Too much formatting
**Solution**: Filter identifiers to only relevant ones for context

**Issue**: Wrong identifier matched
**Solution**: Order identifiers by specificity (longer first)

## Files Location

All files in: `C:/Users/alnen/Desktop/Niwa Ai Voice imput/src/services/`

- `transcription_formatter_service.py` - Main service (11KB)
- `transcription_formatter_example.py` - 15 examples (6.4KB)
- `transcription_formatter_integration_example.py` - Integration demos (9.4KB)
- `test_transcription_formatter.py` - 30 unit tests (12KB)
- `TRANSCRIPTION_FORMATTER_README.md` - Full documentation
- `QUICK_START_FORMATTER.md` - This file

## Next Steps

1. Try running the examples
2. Integrate into your transcription pipeline
3. Extract identifiers from your codebase
4. Customize for your use case

Happy coding!
