"""Test script for Variable Recognition integration."""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.settings_service import SettingsService
from services.active_window_service import ActiveWindowService
from services.code_identifier_service import CodeIdentifierService
from services.transcription_formatter_service import TranscriptionFormatterService

def test_settings():
    """Test settings service integration."""
    print("\n=== Testing Settings Service ===")
    settings = SettingsService()

    # Check default values
    vr_enabled = settings.get("variable_recognition.enabled", None)
    vr_timeout = settings.get("variable_recognition.cache_timeout", None)

    print(f"Variable Recognition Enabled: {vr_enabled}")
    print(f"Cache Timeout: {vr_timeout}")

    assert vr_enabled is not None, "variable_recognition.enabled should have a default value"
    assert vr_timeout is not None, "variable_recognition.cache_timeout should have a default value"
    print("✓ Settings service integration working")

def test_active_window_service():
    """Test active window detection."""
    print("\n=== Testing Active Window Service ===")
    service = ActiveWindowService()

    window_info = service.get_active_window_info()
    print(f"Active Window: {window_info['window_title']}")
    print(f"Process: {window_info['process_name']}")
    print(f"App Name: {window_info['app_name']}")
    print(f"Is Developer App: {window_info['is_developer_app']}")

    is_dev_app = service.is_developer_app_active()
    print(f"Developer app active: {is_dev_app}")

    service.cleanup()
    print("✓ Active window service working")

def test_code_identifier_service():
    """Test code identifier extraction."""
    print("\n=== Testing Code Identifier Service ===")
    service = CodeIdentifierService()

    test_code = """
    const myVariable = 123;
    function getUserById(id) {
        return user_database.find(id);
    }
    class UserController {
        handleRequest() {}
    }
    """

    identifiers = service.extract_identifiers(test_code)
    print(f"Found {len(identifiers)} identifiers:")
    for identifier in identifiers[:10]:  # Show first 10
        print(f"  - {identifier}")

    assert len(identifiers) > 0, "Should find identifiers in test code"
    print("✓ Code identifier service working")

def test_transcription_formatter_service():
    """Test transcription formatting."""
    print("\n=== Testing Transcription Formatter Service ===")
    service = TranscriptionFormatterService()

    identifiers = ["getUserById", "myVariable", "UserController"]
    transcription = "use get user by ID to fetch my variable from User Controller"

    formatted = service.format_with_code_identifiers(transcription, identifiers)
    print(f"Original: {transcription}")
    print(f"Formatted: {formatted}")

    assert "`" in formatted, "Should add backticks to formatted text"
    print("✓ Transcription formatter service working")

def test_full_integration():
    """Test full integration workflow."""
    print("\n=== Testing Full Integration ===")

    # Initialize services
    settings = SettingsService()
    active_window = ActiveWindowService()
    code_identifier = CodeIdentifierService()
    formatter = TranscriptionFormatterService()

    # Check if variable recognition is enabled
    vr_enabled = settings.get("variable_recognition.enabled", True)
    print(f"Variable Recognition Enabled: {vr_enabled}")

    # Check active window
    is_dev_app = active_window.is_developer_app_active()
    print(f"Developer App Active: {is_dev_app}")

    if is_dev_app:
        window_info = active_window.get_active_window_info()
        print(f"Developer App Detected: {window_info['app_name']}")

    # Test identifier extraction
    test_identifiers = ["clearPasteboard", "getData", "handleError"]
    transcription = "use clear pasteboard to get data and handle error"

    formatted = formatter.format_with_code_identifiers(transcription, test_identifiers)
    print(f"\nTest Transcription: {transcription}")
    print(f"Formatted Result: {formatted}")

    # Cleanup
    active_window.cleanup()
    code_identifier.cleanup()
    formatter.cleanup()

    print("✓ Full integration test complete")

if __name__ == "__main__":
    print("=" * 60)
    print("Variable Recognition Integration Test")
    print("=" * 60)

    try:
        test_settings()
        test_active_window_service()
        test_code_identifier_service()
        test_transcription_formatter_service()
        test_full_integration()

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
