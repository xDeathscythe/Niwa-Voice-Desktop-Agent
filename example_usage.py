"""
VoiceType - Example Usage

This file demonstrates how to use all backend components together
to create a complete voice-to-text workflow.

Run with: python example_usage.py
"""

import asyncio
import sys
import time
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from backend import (
    # Core components
    AudioManager,
    WhisperService,
    TextCleaner,
    HotkeyManager,
    ClipboardManager,
    SettingsManager,

    # Supporting classes
    CleaningMode,
    VirtualKeyCodes,
    ModifierFlags,

    # Language support
    get_common_languages,
    get_language,
)


class VoiceTypeApp:
    """
    Complete VoiceType application example.

    Demonstrates the full workflow:
    1. Press hotkey to start recording
    2. Speak into microphone
    3. Press hotkey again to stop
    4. Audio is transcribed via Whisper
    5. Text is cleaned via GPT
    6. Result is pasted at cursor position
    """

    def __init__(self):
        print("Initializing VoiceType...")

        # Initialize settings
        self.settings = SettingsManager()

        # Get API key
        self.api_key = self.settings.get_api_key()
        if not self.api_key:
            print("\n[!] No API key found!")
            print("    Set your OpenAI API key with:")
            print("    settings.set_api_key('sk-your-key-here')")
            print()

        # Initialize components
        self.audio = AudioManager()
        self.clipboard = ClipboardManager()
        self.hotkeys = HotkeyManager()

        # These require API key
        self.whisper = None
        self.cleaner = None
        if self.api_key:
            self.whisper = WhisperService(api_key=self.api_key)
            self.cleaner = TextCleaner(api_key=self.api_key)

        # State
        self.is_recording = False
        self.language = self.settings.settings.transcription.language

        # Set up hotkey callback
        self._setup_hotkeys()

        print("VoiceType initialized!")

    def _setup_hotkeys(self):
        """Set up global hotkeys."""
        hotkey_str = self.settings.settings.hotkeys.record_hotkey

        self.hotkeys.register_hotkey_string(
            hotkey_str,
            callback=self.toggle_recording,
            description="Toggle Recording"
        )

        print(f"  Hotkey registered: {hotkey_str}")

    def toggle_recording(self):
        """Toggle recording on/off."""
        if self.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self):
        """Start audio recording."""
        if self.is_recording:
            return

        print("\n[RECORDING] Speak now...")

        # Set up level callback for visual feedback
        self.audio.set_level_callback(self._show_level)

        self.audio.start_recording()
        self.is_recording = True

    def _show_level(self, level: float):
        """Show audio level indicator."""
        bars = int(level * 30)
        print(f"  Level: {'|' * bars}{' ' * (30 - bars)} {level:.2f}", end='\r')

    def stop_recording(self):
        """Stop recording and process audio."""
        if not self.is_recording:
            return

        self.is_recording = False
        print("\n[PROCESSING] Transcribing...")

        # Get recorded audio
        audio_data = self.audio.stop_recording()
        wav_data = self.audio.convert_to_wav(audio_data)

        duration = len(audio_data) / (16000 * 2)  # 16kHz, 16-bit
        print(f"  Recorded {duration:.1f} seconds of audio")

        if not self.whisper:
            print("[ERROR] No API key configured!")
            return

        # Transcribe
        try:
            # Determine language setting
            lang = None if self.language == "auto" else self.language

            result = self.whisper.transcribe(
                wav_data,
                language=lang,
                file_format="wav"
            )

            transcript = result.text
            detected_lang = result.language

            print(f"\n[TRANSCRIPT] ({detected_lang or 'auto'}):")
            print(f"  \"{transcript}\"")

            # Clean text if enabled
            final_text = transcript
            if self.cleaner and self.settings.settings.cleaning.enabled:
                print("\n[CLEANING] Improving text...")

                mode = CleaningMode(self.settings.settings.cleaning.mode)
                cleaned = self.cleaner.clean(transcript, mode=mode)

                if cleaned.success:
                    final_text = cleaned.cleaned_text
                    print(f"  \"{final_text}\"")
                else:
                    print(f"  [Warning] Cleaning failed: {cleaned.error}")

            # Copy to clipboard and paste
            print("\n[OUTPUT] Pasting text...")

            if self.settings.settings.output.auto_paste:
                success = self.clipboard.copy_and_paste(
                    final_text,
                    paste_delay=self.settings.settings.output.paste_delay
                )
            else:
                success = self.clipboard.copy_text(final_text)

            if success:
                print("  Done!")
            else:
                print("  [Warning] Paste may have failed")

        except Exception as e:
            print(f"\n[ERROR] Transcription failed: {e}")

    def run(self):
        """Run the application."""
        print("\n" + "=" * 50)
        print("VoiceType is running!")
        print("=" * 50)
        print(f"\nPress {self.settings.settings.hotkeys.record_hotkey} to start/stop recording")
        print("Press Ctrl+C to exit")
        print()

        # Start hotkey listener
        self.hotkeys.start()

        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n\nShutting down...")

        finally:
            self.cleanup()

    def cleanup(self):
        """Clean up resources."""
        self.hotkeys.stop()
        self.audio.cleanup()

        if self.whisper:
            self.whisper.close_sync()
        if self.cleaner:
            self.cleaner.close_sync()

        print("Goodbye!")


def demo_components():
    """Demo individual components without full app."""
    print("\n" + "=" * 50)
    print("VoiceType Component Demo")
    print("=" * 50)

    # 1. Audio Manager Demo
    print("\n--- Audio Manager ---")
    audio = AudioManager()
    devices = audio.get_available_devices()
    print(f"Found {len(devices)} audio input device(s):")
    for d in devices:
        print(f"  [{d.index}] {d.name}")
    audio.cleanup()

    # 2. Settings Manager Demo
    print("\n--- Settings Manager ---")
    settings = SettingsManager()
    print(f"Settings file: {settings.settings_file}")
    print(f"Has API key: {settings.has_api_key()}")
    print(f"Recording hotkey: {settings.settings.hotkeys.record_hotkey}")
    print(f"Language: {settings.settings.transcription.language}")

    # 3. Languages Demo
    print("\n--- Supported Languages ---")
    common = get_common_languages()
    print(f"Common languages ({len(common)}):")
    for lang in common[:10]:
        print(f"  {lang.code}: {lang.name} ({lang.native_name})")

    # 4. Clipboard Demo
    print("\n--- Clipboard Manager ---")
    clipboard = ClipboardManager()
    test_text = "VoiceType test - Zdravo!"
    clipboard.copy_text(test_text)
    retrieved = clipboard.get_text()
    print(f"Copied and retrieved: '{retrieved}'")
    print(f"Match: {retrieved == test_text}")

    # 5. Hotkey Demo (brief)
    print("\n--- Hotkey Manager ---")
    hotkeys = HotkeyManager()
    hk_id = hotkeys.register_hotkey_string(
        "Ctrl+T",
        callback=lambda: print("Hotkey pressed!"),
        description="Test"
    )
    print(f"Registered: {hotkeys.get_hotkey(hk_id)}")
    hotkeys.unregister_hotkey(hk_id)
    print("Hotkey unregistered")

    print("\n" + "=" * 50)
    print("Demo complete!")
    print("=" * 50)


def setup_api_key():
    """Interactive API key setup."""
    print("\n" + "=" * 50)
    print("VoiceType API Key Setup")
    print("=" * 50)

    settings = SettingsManager()

    if settings.has_api_key():
        print("\nAPI key is already configured!")
        choice = input("Do you want to replace it? (y/n): ")
        if choice.lower() != 'y':
            return

    print("\nEnter your OpenAI API key (starts with 'sk-'):")
    api_key = input("> ").strip()

    if not api_key.startswith("sk-"):
        print("Warning: API key should start with 'sk-'")

    if settings.set_api_key(api_key):
        print("\nAPI key saved securely!")
        print("Your key is encrypted using Windows DPAPI.")
    else:
        print("\nFailed to save API key!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="VoiceType Application")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run component demo instead of full app"
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Set up API key"
    )

    args = parser.parse_args()

    if args.setup:
        setup_api_key()
    elif args.demo:
        demo_components()
    else:
        # Check for API key first
        settings = SettingsManager()
        if not settings.has_api_key():
            print("No API key configured!")
            print("Run with --setup to configure your API key first.")
            print("Or run with --demo to test components without API key.")
            sys.exit(1)

        app = VoiceTypeApp()
        app.run()
