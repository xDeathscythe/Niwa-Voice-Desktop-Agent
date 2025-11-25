"""Unit tests for TranscriptionFormatterService."""

import unittest
from transcription_formatter_service import TranscriptionFormatterService


class TestTranscriptionFormatterService(unittest.TestCase):
    """Test cases for TranscriptionFormatterService."""

    def setUp(self):
        """Set up test fixtures."""
        self.formatter = TranscriptionFormatterService()

    def tearDown(self):
        """Clean up after tests."""
        self.formatter.cleanup()

    def test_basic_camel_case(self):
        """Test basic camelCase identifier matching."""
        text = "use the clear pasteboard function"
        identifiers = ["clearPasteboard"]
        result = self.formatter.format_with_code_identifiers(text, identifiers)
        self.assertEqual(result, "use the `clearPasteboard` function")

    def test_basic_snake_case(self):
        """Test basic snake_case identifier matching."""
        text = "call get user data to fetch info"
        identifiers = ["get_user_data"]
        result = self.formatter.format_with_code_identifiers(text, identifiers)
        self.assertEqual(result, "call `get_user_data` to fetch info")

    def test_basic_pascal_case(self):
        """Test basic PascalCase identifier matching."""
        text = "the Audio Service handles recording"
        identifiers = ["AudioService"]
        result = self.formatter.format_with_code_identifiers(text, identifiers)
        self.assertEqual(result, "the `AudioService` handles recording")

    def test_already_in_backticks(self):
        """Test that already formatted text is preserved."""
        text = "the `clearPasteboard` method works"
        identifiers = ["clearPasteboard"]
        result = self.formatter.format_with_code_identifiers(text, identifiers)
        self.assertEqual(result, "the `clearPasteboard` method works")

    def test_in_double_quotes(self):
        """Test that text in double quotes is preserved."""
        text = 'use "clear pasteboard" as name'
        identifiers = ["clearPasteboard"]
        result = self.formatter.format_with_code_identifiers(text, identifiers)
        self.assertEqual(result, 'use "clear pasteboard" as name')

    def test_in_single_quotes(self):
        """Test that text in single quotes is preserved."""
        text = "use 'clear pasteboard' as name"
        identifiers = ["clearPasteboard"]
        result = self.formatter.format_with_code_identifiers(text, identifiers)
        self.assertEqual(result, "use 'clear pasteboard' as name")

    def test_multiple_occurrences(self):
        """Test multiple occurrences of same identifier."""
        text = "reset the state then reset again"
        identifiers = ["reset"]
        result = self.formatter.format_with_code_identifiers(text, identifiers)
        self.assertEqual(result, "`reset` the state then `reset` again")

    def test_prefer_longer_match(self):
        """Test that longer matches are preferred."""
        text = "use clear pasteboard data to clear"
        identifiers = ["clearPasteboardData", "clearPasteboard", "clear"]
        result = self.formatter.format_with_code_identifiers(text, identifiers)
        self.assertEqual(result, "use `clearPasteboardData` to `clear`")

    def test_multiple_identifiers(self):
        """Test multiple different identifiers in one text."""
        text = "the get data method and clear pasteboard function"
        identifiers = ["get_data", "clearPasteboard"]
        result = self.formatter.format_with_code_identifiers(text, identifiers)
        self.assertEqual(result, "the `get_data` method and `clearPasteboard` function")

    def test_no_matches(self):
        """Test text with no matching identifiers."""
        text = "this is just regular text"
        identifiers = ["someFunction"]
        result = self.formatter.format_with_code_identifiers(text, identifiers)
        self.assertEqual(result, "this is just regular text")

    def test_empty_text(self):
        """Test empty text input."""
        result = self.formatter.format_with_code_identifiers("", ["func"])
        self.assertEqual(result, "")

    def test_empty_identifiers(self):
        """Test empty identifiers list."""
        result = self.formatter.format_with_code_identifiers("some text", [])
        self.assertEqual(result, "some text")

    def test_empty_both(self):
        """Test both text and identifiers empty."""
        result = self.formatter.format_with_code_identifiers("", [])
        self.assertEqual(result, "")

    def test_sentence_boundaries(self):
        """Test matching at sentence boundaries."""
        text = "Clear pasteboard. Then reset. Use clear pasteboard again."
        identifiers = ["clearPasteboard", "reset"]
        result = self.formatter.format_with_code_identifiers(text, identifiers)
        self.assertEqual(
            result,
            "`clearPasteboard`. Then `reset`. Use `clearPasteboard` again."
        )

    def test_case_insensitive_matching(self):
        """Test case-insensitive matching."""
        text = "use CLEAR PASTEBOARD function"
        identifiers = ["clearPasteboard"]
        result = self.formatter.format_with_code_identifiers(text, identifiers)
        self.assertEqual(result, "use `clearPasteboard` function")

    def test_url_context_skipped(self):
        """Test that URLs are not formatted."""
        text = "visit https://example.com/clear/pasteboard for docs"
        identifiers = ["clearPasteboard"]
        result = self.formatter.format_with_code_identifiers(text, identifiers)
        # Should not format because it's in a URL
        self.assertNotIn("`clearPasteboard`", result)

    def test_generate_spoken_forms_camel_case(self):
        """Test spoken form generation for camelCase."""
        forms = self.formatter._generate_spoken_forms("clearPasteboard")
        self.assertIn("clear Pasteboard", forms)
        self.assertIn("clearPasteboard", forms)

    def test_generate_spoken_forms_snake_case(self):
        """Test spoken form generation for snake_case."""
        forms = self.formatter._generate_spoken_forms("get_user_data")
        self.assertIn("get user data", forms)
        self.assertIn("get_user_data", forms)
        self.assertIn("getuserdata", forms)

    def test_generate_spoken_forms_pascal_case(self):
        """Test spoken form generation for PascalCase."""
        forms = self.formatter._generate_spoken_forms("AudioService")
        self.assertIn("Audio Service", forms)
        self.assertIn("AudioService", forms)

    def test_is_already_formatted_backticks(self):
        """Test detection of backtick formatting."""
        text = "the `clearPasteboard` method"
        # Position 5-20 is "clearPasteboard"
        result = self.formatter._is_already_formatted(text, 5, 20)
        self.assertTrue(result)

    def test_is_already_formatted_quotes(self):
        """Test detection of quote formatting."""
        text = 'use "clearPasteboard" here'
        # Position 5-20 is "clearPasteboard"
        result = self.formatter._is_already_formatted(text, 5, 20)
        self.assertTrue(result)

    def test_is_not_formatted(self):
        """Test detection when not formatted."""
        text = "use clearPasteboard here"
        # Position 4-19 is "clearPasteboard"
        result = self.formatter._is_already_formatted(text, 4, 19)
        self.assertFalse(result)

    def test_overlaps_with_replacements(self):
        """Test overlap detection."""
        replacements = [(10, 20, "identifier1"), (30, 40, "identifier2")]

        # Overlaps with first replacement
        self.assertTrue(self.formatter._overlaps_with_replacements(15, 25, replacements))

        # Overlaps with second replacement
        self.assertTrue(self.formatter._overlaps_with_replacements(25, 35, replacements))

        # No overlap
        self.assertFalse(self.formatter._overlaps_with_replacements(20, 30, replacements))
        self.assertFalse(self.formatter._overlaps_with_replacements(0, 10, replacements))

    def test_match_spoken_to_identifier(self):
        """Test spoken phrase to identifier matching."""
        identifiers = ["clearPasteboard", "get_data", "AudioService"]

        # Exact match
        result = self.formatter._match_spoken_to_identifier("clear pasteboard", identifiers)
        self.assertEqual(result, "clearPasteboard")

        # snake_case match
        result = self.formatter._match_spoken_to_identifier("get data", identifiers)
        self.assertEqual(result, "get_data")

        # PascalCase match
        result = self.formatter._match_spoken_to_identifier("audio service", identifiers)
        self.assertEqual(result, "AudioService")

        # No match
        result = self.formatter._match_spoken_to_identifier("unknown phrase", identifiers)
        self.assertIsNone(result)

    def test_complex_real_world_example(self):
        """Test complex real-world transcription scenario."""
        text = (
            "so we need to modify the transcription service to use the audio "
            "preprocessing service before calling whisper one"
        )
        identifiers = [
            "TranscriptionService",
            "AudioPreprocessingService",
            "whisper-1"
        ]
        result = self.formatter.format_with_code_identifiers(text, identifiers)

        # Should format the services
        self.assertIn("`TranscriptionService`", result)
        self.assertIn("`AudioPreprocessingService`", result)

        # whisper-1 spoken as "whisper one" won't match (different format)
        # This is expected behavior - exact match only for special chars


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and corner cases."""

    def setUp(self):
        """Set up test fixtures."""
        self.formatter = TranscriptionFormatterService()

    def tearDown(self):
        """Clean up after tests."""
        self.formatter.cleanup()

    def test_very_long_text(self):
        """Test with very long text."""
        text = "use clear pasteboard " * 100
        identifiers = ["clearPasteboard"]
        result = self.formatter.format_with_code_identifiers(text, identifiers)
        # Should format all occurrences
        self.assertEqual(result.count("`clearPasteboard`"), 100)

    def test_many_identifiers(self):
        """Test with many identifiers."""
        text = "use func one two three four five"
        identifiers = [f"func{i}" for i in range(100)]
        result = self.formatter.format_with_code_identifiers(text, identifiers)
        # Should not crash or hang
        self.assertIsInstance(result, str)

    def test_special_characters_in_text(self):
        """Test text with special characters."""
        text = "use clear-pasteboard function with @params"
        identifiers = ["clearPasteboard"]
        result = self.formatter.format_with_code_identifiers(text, identifiers)
        # Should handle gracefully
        self.assertIsInstance(result, str)

    def test_unicode_characters(self):
        """Test with Unicode characters."""
        text = "использовать clear pasteboard функцию"
        identifiers = ["clearPasteboard"]
        result = self.formatter.format_with_code_identifiers(text, identifiers)
        self.assertIn("`clearPasteboard`", result)

    def test_nested_backticks(self):
        """Test with nested backticks (malformed)."""
        text = "use `clear `pasteboard` method"
        identifiers = ["clearPasteboard"]
        result = self.formatter.format_with_code_identifiers(text, identifiers)
        # Should handle gracefully without adding more backticks
        self.assertIsInstance(result, str)


def run_tests():
    """Run all tests."""
    unittest.main(verbosity=2)


if __name__ == "__main__":
    run_tests()
