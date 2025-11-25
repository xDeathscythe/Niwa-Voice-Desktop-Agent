"""Example usage and tests for TranscriptionFormatterService."""

import logging

from transcription_formatter_service import TranscriptionFormatterService

# Set up logging to see debug output
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def run_examples():
    """Run example formatting scenarios."""
    formatter = TranscriptionFormatterService()

    print("=" * 80)
    print("TranscriptionFormatterService Examples")
    print("=" * 80)

    # Example 1: Basic camelCase identifier
    print("\n--- Example 1: Basic camelCase ---")
    text1 = "use the clear pasteboard function to reset the clipboard"
    identifiers1 = ["clearPasteboard", "reset"]
    result1 = formatter.format_with_code_identifiers(text1, identifiers1)
    print(f"Input:  {text1}")
    print(f"Output: {result1}")

    # Example 2: PascalCase identifier
    print("\n--- Example 2: PascalCase ---")
    text2 = "the Audio Service handles all recording"
    identifiers2 = ["AudioService", "handleRecording"]
    result2 = formatter.format_with_code_identifiers(text2, identifiers2)
    print(f"Input:  {text2}")
    print(f"Output: {result2}")

    # Example 3: snake_case identifier
    print("\n--- Example 3: snake_case ---")
    text3 = "call get user data to fetch the information"
    identifiers3 = ["get_user_data", "fetch_info"]
    result3 = formatter.format_with_code_identifiers(text3, identifiers3)
    print(f"Input:  {text3}")
    print(f"Output: {result3}")

    # Example 4: Already formatted (should be preserved)
    print("\n--- Example 4: Already in backticks ---")
    text4 = "the `clearPasteboard` method is already formatted"
    identifiers4 = ["clearPasteboard"]
    result4 = formatter.format_with_code_identifiers(text4, identifiers4)
    print(f"Input:  {text4}")
    print(f"Output: {result4}")

    # Example 5: In quotes (should be preserved)
    print("\n--- Example 5: In quotes ---")
    text5 = 'use "clear pasteboard" as the function name'
    identifiers5 = ["clearPasteboard"]
    result5 = formatter.format_with_code_identifiers(text5, identifiers5)
    print(f"Input:  {text5}")
    print(f"Output: {result5}")

    # Example 6: Multiple occurrences
    print("\n--- Example 6: Multiple occurrences ---")
    text6 = "reset the state then reset again and finally reset once more"
    identifiers6 = ["reset"]
    result6 = formatter.format_with_code_identifiers(text6, identifiers6)
    print(f"Input:  {text6}")
    print(f"Output: {result6}")

    # Example 7: Prefer longer matches
    print("\n--- Example 7: Prefer longer matches ---")
    text7 = "use clear pasteboard data to clear the clipboard"
    identifiers7 = ["clearPasteboardData", "clearPasteboard", "clear"]
    result7 = formatter.format_with_code_identifiers(text7, identifiers7)
    print(f"Input:  {text7}")
    print(f"Output: {result7}")

    # Example 8: Mixed naming conventions
    print("\n--- Example 8: Mixed naming conventions ---")
    text8 = "the get data method and clear pasteboard function work together"
    identifiers8 = ["get_data", "clearPasteboard", "workTogether"]
    result8 = formatter.format_with_code_identifiers(text8, identifiers8)
    print(f"Input:  {text8}")
    print(f"Output: {result8}")

    # Example 9: Complex identifier with numbers
    print("\n--- Example 9: Identifier with numbers ---")
    text9 = "use base sixty four encode for encoding"
    identifiers9 = ["base64Encode", "encode"]
    result9 = formatter.format_with_code_identifiers(text9, identifiers9)
    print(f"Input:  {text9}")
    print(f"Output: {result9}")

    # Example 10: Real-world code review scenario
    print("\n--- Example 10: Code review scenario ---")
    text10 = "the transcription service uses whisper one model and the cleanup model is gpt four o mini"
    identifiers10 = ["TranscriptionService", "whisper-1", "gpt-4o-mini", "cleanup_model"]
    result10 = formatter.format_with_code_identifiers(text10, identifiers10)
    print(f"Input:  {text10}")
    print(f"Output: {result10}")

    # Example 11: No matches
    print("\n--- Example 11: No matches ---")
    text11 = "this is just regular text with no code identifiers"
    identifiers11 = ["someFunction", "anotherMethod"]
    result11 = formatter.format_with_code_identifiers(text11, identifiers11)
    print(f"Input:  {text11}")
    print(f"Output: {result11}")

    # Example 12: Empty inputs
    print("\n--- Example 12: Empty inputs ---")
    text12 = ""
    identifiers12 = []
    result12 = formatter.format_with_code_identifiers(text12, identifiers12)
    print(f"Input:  '{text12}'")
    print(f"Output: '{result12}'")

    # Example 13: At sentence boundaries
    print("\n--- Example 13: Sentence boundaries ---")
    text13 = "Clear pasteboard. The reset method should be called. Use clear pasteboard again."
    identifiers13 = ["clearPasteboard", "reset"]
    result13 = formatter.format_with_code_identifiers(text13, identifiers13)
    print(f"Input:  {text13}")
    print(f"Output: {result13}")

    # Example 14: URL context (should be skipped)
    print("\n--- Example 14: URL context (should skip) ---")
    text14 = "visit https://example.com/clear/pasteboard for docs"
    identifiers14 = ["clearPasteboard"]
    result14 = formatter.format_with_code_identifiers(text14, identifiers14)
    print(f"Input:  {text14}")
    print(f"Output: {result14}")

    # Example 15: Complex real-world transcription
    print("\n--- Example 15: Complex transcription ---")
    text15 = (
        "so we need to modify the transcription service to use the audio "
        "preprocessing service before calling whisper one. the preprocess audio "
        "method should handle noise reduction and voice activity detection"
    )
    identifiers15 = [
        "TranscriptionService",
        "AudioPreprocessingService",
        "whisper-1",
        "preprocess_audio",
        "noise_reduction",
        "voice_activity_detection"
    ]
    result15 = formatter.format_with_code_identifiers(text15, identifiers15)
    print(f"Input:  {text15}")
    print(f"Output: {result15}")

    print("\n" + "=" * 80)
    print("Examples complete!")
    print("=" * 80)

    # Cleanup
    formatter.cleanup()


if __name__ == "__main__":
    run_examples()
