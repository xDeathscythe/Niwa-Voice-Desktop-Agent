"""Integration example showing TranscriptionFormatterService with TranscriptionService."""

import logging
from transcription_formatter_service import TranscriptionFormatterService

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def simulate_transcription_workflow():
    """
    Simulate a complete transcription workflow with code identifier formatting.

    This demonstrates how the formatter would integrate with the existing
    transcription pipeline.
    """
    print("=" * 80)
    print("Transcription + Formatter Integration Example")
    print("=" * 80)

    # Initialize formatter
    formatter = TranscriptionFormatterService()

    # Simulate transcribed text (what Whisper might return)
    raw_transcription = (
        "okay so in the transcription service we use the whisper one model "
        "for audio transcription and then we call the cleanup using gpt four o mini. "
        "the audio preprocessing service handles voice activity detection and "
        "noise reduction before we send it to whisper. the preprocess audio method "
        "is called first, then we get the result and pass it to the text injection service "
        "which uses clear pasteboard and simulate typing methods"
    )

    print("\n--- Raw Transcription ---")
    print(raw_transcription)

    # Extract code identifiers from the current project
    # In a real scenario, these would be dynamically extracted from:
    # 1. Current file being discussed
    # 2. Recently opened files
    # 3. Project symbol index
    # 4. Git diff (for code reviews)
    code_identifiers = [
        # Services
        "TranscriptionService",
        "AudioPreprocessingService",
        "TextInjectionService",

        # Methods
        "preprocess_audio",
        "cleanup",
        "voice_activity_detection",
        "noise_reduction",
        "clearPasteboard",
        "simulate_typing",

        # Models
        "whisper-1",
        "gpt-4o-mini",

        # Other
        "get_result",
        "send_to_whisper"
    ]

    print("\n--- Code Identifiers ---")
    print(f"Found {len(code_identifiers)} identifiers in project")
    for identifier in code_identifiers[:5]:
        print(f"  - {identifier}")
    print(f"  ... and {len(code_identifiers) - 5} more")

    # Format the transcription
    formatted_text = formatter.format_with_code_identifiers(
        raw_transcription,
        code_identifiers
    )

    print("\n--- Formatted Transcription ---")
    print(formatted_text)

    # Show the difference
    print("\n--- Changes Applied ---")
    if formatted_text != raw_transcription:
        # Count backtick pairs
        backtick_count = formatted_text.count('`') // 2
        print(f"[OK] Applied {backtick_count} code identifier formatting(s)")

        # Show some examples
        import re
        backticked = re.findall(r'`([^`]+)`', formatted_text)
        print(f"\nFormatted identifiers:")
        for identifier in backticked[:10]:
            print(f"  - `{identifier}`")
        if len(backticked) > 10:
            print(f"  ... and {len(backticked) - 10} more")
    else:
        print("No changes applied")

    # Cleanup
    formatter.cleanup()

    print("\n" + "=" * 80)


def demonstrate_code_review_scenario():
    """
    Demonstrate using the formatter during a code review session.
    """
    print("\n\n" + "=" * 80)
    print("Code Review Scenario")
    print("=" * 80)

    formatter = TranscriptionFormatterService()

    # Developer dictating code review comments
    review_comments = [
        {
            "file": "services/transcription_service.py",
            "comment": (
                "in the transcribe method we should add error handling "
                "for the call cleanup step because if gpt four o mini fails "
                "we should fall back to the raw text from whisper"
            ),
            "identifiers": ["transcribe", "call_cleanup", "gpt-4o-mini", "raw_text", "whisper"]
        },
        {
            "file": "services/audio_preprocessing_service.py",
            "comment": (
                "the preprocess audio method should check if vad model is loaded "
                "before calling detect speech segments otherwise it might crash"
            ),
            "identifiers": [
                "preprocess_audio",
                "vad_model",
                "detect_speech_segments",
                "is_loaded"
            ]
        },
        {
            "file": "services/text_injection_service.py",
            "comment": (
                "we need to add a delay between copy to clipboard and simulate paste "
                "because on some systems the clipboard takes time to update"
            ),
            "identifiers": [
                "copy_to_clipboard",
                "simulate_paste",
                "clipboard_delay",
                "add_delay"
            ]
        }
    ]

    for i, review in enumerate(review_comments, 1):
        print(f"\n--- Review Comment #{i} ---")
        print(f"File: {review['file']}")
        print(f"\nOriginal comment:")
        print(f"  {review['comment']}")

        formatted = formatter.format_with_code_identifiers(
            review['comment'],
            review['identifiers']
        )

        print(f"\nFormatted comment:")
        print(f"  {formatted}")

    formatter.cleanup()

    print("\n" + "=" * 80)


def demonstrate_documentation_generation():
    """
    Demonstrate using the formatter for generating documentation from speech.
    """
    print("\n\n" + "=" * 80)
    print("Documentation Generation Scenario")
    print("=" * 80)

    formatter = TranscriptionFormatterService()

    # Developer dictating documentation
    doc_sections = [
        {
            "section": "Overview",
            "content": (
                "The audio service handles all audio recording functionality. "
                "It uses sound device for cross platform audio capture and "
                "implements start recording and stop recording methods."
            ),
            "identifiers": [
                "AudioService",
                "sounddevice",
                "start_recording",
                "stop_recording",
                "audio_capture"
            ]
        },
        {
            "section": "Usage",
            "content": (
                "First create an audio service instance, then call start recording "
                "with your sample rate and channels. When done, call stop recording "
                "to get the audio data as bytes."
            ),
            "identifiers": [
                "AudioService",
                "start_recording",
                "stop_recording",
                "sample_rate",
                "channels",
                "audio_data"
            ]
        }
    ]

    print("\nGenerating documentation...\n")

    for section in doc_sections:
        print(f"## {section['section']}\n")

        formatted = formatter.format_with_code_identifiers(
            section['content'],
            section['identifiers']
        )

        print(formatted)
        print()

    formatter.cleanup()

    print("=" * 80)


def demonstrate_dynamic_identifier_extraction():
    """
    Show how identifiers could be dynamically extracted from code.
    """
    print("\n\n" + "=" * 80)
    print("Dynamic Identifier Extraction")
    print("=" * 80)

    # Simulate extracting identifiers from a Python file
    sample_code = '''
class TranscriptionService:
    def __init__(self):
        self._client = None

    def transcribe(self, audio_data):
        raw_text = self._call_whisper(audio_data)
        cleaned_text = self._call_cleanup(raw_text)
        return cleaned_text

    def _call_whisper(self, audio_data):
        pass

    def _call_cleanup(self, text):
        pass
'''

    print("\n--- Sample Code ---")
    print(sample_code)

    # Simple identifier extraction (in real scenario, use AST)
    import re

    # Extract class names
    classes = re.findall(r'class\s+(\w+)', sample_code)

    # Extract method names
    methods = re.findall(r'def\s+(\w+)', sample_code)

    # Extract variable names (simplified)
    variables = re.findall(r'self\.(\w+)', sample_code)

    identifiers = list(set(classes + methods + variables))

    print("\n--- Extracted Identifiers ---")
    for identifier in sorted(identifiers):
        print(f"  - {identifier}")

    # Now use these identifiers
    formatter = TranscriptionFormatterService()

    transcription = (
        "the transcription service has a transcribe method that calls "
        "call whisper to get raw text and then call cleanup to clean it up"
    )

    formatted = formatter.format_with_code_identifiers(transcription, identifiers)

    print("\n--- Formatted Result ---")
    print(formatted)

    formatter.cleanup()

    print("\n" + "=" * 80)


if __name__ == "__main__":
    # Run all demonstrations
    simulate_transcription_workflow()
    demonstrate_code_review_scenario()
    demonstrate_documentation_generation()
    demonstrate_dynamic_identifier_extraction()

    print("\n\n[OK] All integration examples completed successfully!")
