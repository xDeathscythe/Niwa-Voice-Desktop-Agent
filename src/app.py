"""VoiceType Application - Simplified, fast, reliable."""

import logging
import os
import threading
import time
import io
import wave
from typing import Optional
from enum import Enum, auto

import numpy as np
import pyperclip
from openai import OpenAI

logger = logging.getLogger(__name__)


class AppState(Enum):
    """Simple application states."""
    IDLE = auto()
    RECORDING = auto()
    PROCESSING = auto()


class VoiceTypeApp:
    """
    Simplified VoiceType application.

    Direct, fast, reliable - no complex state machines.
    """

    # Audio settings for Whisper
    SAMPLE_RATE = 16000
    CHANNELS = 1

    def __init__(self):
        """Initialize application."""
        from .services.settings_service import SettingsService
        from .services.audio_service import AudioService
        from .services.audio_preprocessing_service import AudioPreprocessingService
        from .services.windows_hotkey_service import WindowsHotkeyService
        from .services.active_window_service import ActiveWindowService
        from .services.screen_code_service import ScreenCodeService
        from .services.code_identifier_service import CodeIdentifierService
        from .services.transcription_formatter_service import TranscriptionFormatterService
        from .services.system_tray_service import SystemTrayService
        from .ui.main_window import MainWindow
        from .ui.shining_pill import ShiningPill, PillState
        from .ui.styles.theme import COLORS

        self._settings = SettingsService()
        self._audio = AudioService()
        self._preprocessing = AudioPreprocessingService()
        self._hotkey_service = WindowsHotkeyService()
        self._active_window_service = ActiveWindowService()
        self._screen_code_service: Optional[ScreenCodeService] = None
        self._code_identifier_service = CodeIdentifierService()
        self._transcription_formatter_service = TranscriptionFormatterService()
        self._system_tray_service = SystemTrayService()
        self._client: Optional[OpenAI] = None

        self._state = AppState.IDLE
        self._lock = threading.Lock()

        # Paste lock to prevent double paste
        self._last_paste_time = 0
        self._paste_timeout = 0.3  # 300ms timeout between pastes

        # Store for UI access
        self._main_window: Optional[MainWindow] = None
        self._pill: Optional[FloatingPill] = None
        self._PillState = PillState
        self._COLORS = COLORS

        logger.info("VoiceTypeApp initialized")

    def run(self):
        """Run the application."""
        from .ui.main_window import MainWindow
        from .ui.shining_pill import ShiningPill

        try:
            self._settings.load()

            # Initialize OpenAI client if we have a key
            api_key = self._settings.get_api_key()
            if api_key:
                self._client = OpenAI(api_key=api_key, timeout=30.0)

            # Create MainWindow (settings) - visible on startup
            self._main_window = MainWindow(
                settings_service=self._settings,
                audio_service=self._audio,
                on_start=self._start_service,
                on_stop=self._stop_service,
                on_close=self._close_settings
            )

            # Setup system tray with pill show/hide
            self._system_tray_service.setup(
                on_show=self._show_from_tray,
                on_quit=self._quit_from_tray,
                on_settings=self._show_settings_from_tray
            )
            self._system_tray_service.start()

            # Create pill - this is the primary UI
            self._pill = ShiningPill(on_click=self._toggle_recording, on_close=self._hide_to_tray)

            # Auto-start if we have API key
            if api_key:
                self._main_window.after(300, self._auto_start)

            logger.info("Starting main loop")
            self._main_window.mainloop()

        except Exception as e:
            logger.critical(f"Fatal error: {e}", exc_info=True)
            raise
        finally:
            self._cleanup()

    def _auto_start(self):
        """Auto-start the service."""
        self._start_service()
        # Update main window UI
        if self._main_window:
            self._main_window._is_running = True
            self._main_window.start_btn.configure(
                text="Stop",
                fg_color=self._COLORS["error"],
                hover_color="#dc2626"
            )
            self._main_window.status_dot.configure(fg_color=self._COLORS["success"])
            self._main_window.status_label.configure(
                text="Running",
                text_color=self._COLORS["text_secondary"]
            )

    def _start_service(self):
        """Start the voice service."""
        with self._lock:
            if self._hotkey_service.is_registered():
                return

            # Ensure we have API client
            api_key = self._settings.get_api_key()
            if not api_key:
                logger.warning("No API key")
                return

            if not self._client:
                self._client = OpenAI(api_key=api_key, timeout=30.0)

            # Initialize ScreenCodeService with cache timeout from settings
            if not self._screen_code_service:
                from .services.screen_code_service import ScreenCodeService
                cache_timeout = self._settings.get("variable_recognition.cache_timeout", 5.0)
                self._screen_code_service = ScreenCodeService(cache_timeout=cache_timeout)

            # Set microphone from settings, fallback to Buds3 Pro or default
            try:
                saved_device_id = self._settings.get("audio.device_id")
                saved_device_name = self._settings.get("audio.device_name", "")

                if saved_device_id is not None:
                    self._audio.set_device(saved_device_id)
                    logger.info(f"Using saved microphone: {saved_device_name} (id={saved_device_id})")
                else:
                    # Fallback: try to find Buds3 Pro
                    import sounddevice as sd
                    devices = sd.query_devices()
                    for i, d in enumerate(devices):
                        if d['max_input_channels'] > 0 and 'Buds3 Pro' in d['name'] and 'Hands-Free' in d['name']:
                            self._audio.set_device(i)
                            logger.info(f"Using microphone: {d['name']}")
                            break
            except Exception as e:
                logger.warning(f"Could not set microphone: {e}")

            # Register global hotkey using Windows API (PUSH-TO-TALK)
            try:
                # Get hotkey from settings
                hotkey = self._settings.hotkey if hasattr(self._settings, 'hotkey') else self._settings.get_all().hotkey
                modifiers = hotkey.modifiers if hotkey.modifiers else ["ctrl", "alt"]
                key = hotkey.key if hotkey.key else ""

                # Register with on_press and on_release callbacks
                success = self._hotkey_service.register(
                    modifiers,
                    key,
                    on_press=self._on_hotkey_press,
                    on_release=self._on_hotkey_release
                )
                if not success:
                    logger.error("Failed to register hotkey")
                    return
            except Exception as e:
                logger.error(f"Failed to register hotkey: {e}")
                return

        # Show pill (outside lock)
        if self._pill:
            self._pill.show()
            self._pill.set_state(self._PillState.IDLE)

        logger.info("Service started")

    def _stop_service(self):
        """Stop the voice service."""
        with self._lock:
            # Unregister global hotkey
            try:
                self._hotkey_service.unregister()
            except Exception as e:
                logger.error(f"Error unregistering hotkey: {e}")

        if self._pill:
            self._pill.hide()

        logger.info("Service stopped")

    def _on_hotkey_press(self):
        """Handle hotkey press - START recording (PUSH-TO-TALK)."""
        logger.info("✓ Hotkey PRESSED - Starting recording!")
        # Schedule on main thread
        if self._main_window:
            self._main_window.after(0, self._start_recording_from_hotkey)
        else:
            logger.warning("No main window available")

    def _on_hotkey_release(self):
        """Handle hotkey release - STOP recording (PUSH-TO-TALK)."""
        logger.info("✓ Hotkey RELEASED - Stopping recording!")
        # Schedule on main thread
        if self._main_window:
            self._main_window.after(0, self._stop_recording_from_hotkey)
        else:
            logger.warning("No main window available")

    def _start_recording_from_hotkey(self):
        """Start recording from hotkey press."""
        with self._lock:
            if self._state == AppState.IDLE:
                self._start_recording()
            else:
                logger.debug(f"Cannot start recording, current state: {self._state}")

    def _stop_recording_from_hotkey(self):
        """Stop recording from hotkey release."""
        with self._lock:
            if self._state == AppState.RECORDING:
                self._stop_recording()
            else:
                logger.debug(f"Cannot stop recording, current state: {self._state}")

    def _toggle_recording(self):
        """Toggle recording state."""
        # Check state first (atomic read)
        current_state = self._state

        if current_state == AppState.IDLE:
            with self._lock:
                if self._state == AppState.IDLE:
                    self._start_recording()

        elif current_state == AppState.RECORDING:
            with self._lock:
                if self._state == AppState.RECORDING:
                    self._stop_recording()

        elif current_state == AppState.PROCESSING:
            # Provide visual feedback that click was received but busy
            logger.info("Click received during PROCESSING - showing busy feedback")
            if self._pill:
                # Flash border to show click was received
                original_border = self._pill.pill.cget("border_color")
                self._pill.pill.configure(border_color=self._COLORS["accent"])
                self._main_window.after(150, lambda: self._pill.pill.configure(
                    border_color=original_border
                ))

    def _start_recording(self):
        """Start recording audio."""
        try:
            self._state = AppState.RECORDING
            self._audio.start_recording()

            if self._pill:
                self._pill.set_state(self._PillState.RECORDING)

            logger.info("Recording started")

        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self._state = AppState.IDLE
            if self._pill:
                self._pill.show_error("Mic error")

    def _stop_recording(self):
        """Stop recording and process."""
        try:
            # Get audio
            audio_data = self._audio.stop_recording()
            self._state = AppState.PROCESSING

            if self._pill:
                self._pill.set_state(self._PillState.TRANSCRIBING)

            logger.info("Recording stopped, processing...")

            # Process in background
            thread = threading.Thread(
                target=self._process_audio,
                args=(audio_data,),
                daemon=True
            )
            thread.start()

        except Exception as e:
            logger.error(f"Failed to stop recording: {e}")
            self._state = AppState.IDLE
            if self._pill:
                self._pill.show_error(str(e)[:15])

    def _process_audio(self, audio_data: bytes):
        """Process audio in background thread."""
        try:
            if not self._client:
                raise Exception("No API client")

            # DEBUG: Save original audio to file (dynamically determine project root)
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            debug_path = os.path.join(project_root, "debug_audio_original.wav")
            with open(debug_path, 'wb') as f:
                f.write(audio_data)
            logger.info(f"DEBUG: Original audio saved to {debug_path} ({len(audio_data)} bytes)")

            # Apply audio preprocessing (VAD, noise reduction, normalization)
            enable_preprocessing = self._settings.get("audio.preprocessing_enabled", True)
            if enable_preprocessing:
                logger.info("Applying audio preprocessing...")
                preprocess_start = time.time()
                audio_data = self._preprocessing.preprocess_audio(
                    audio_data,
                    sample_rate=self.SAMPLE_RATE,
                    enable_vad=True,
                    enable_noise_reduction=True,
                    enable_normalization=True
                )
                logger.info(f"Preprocessing done in {time.time() - preprocess_start:.2f}s")

                # DEBUG: Save preprocessed audio
                debug_path_processed = os.path.join(project_root, "debug_audio_processed.wav")
                with open(debug_path_processed, 'wb') as f:
                    f.write(audio_data)
                logger.info(f"DEBUG: Preprocessed audio saved to {debug_path_processed}")
            else:
                logger.info("Audio preprocessing disabled")

            # Transcribe with Whisper
            # Calculate audio duration for logging
            audio_duration = len(audio_data) / (self.SAMPLE_RATE * 2)  # 16-bit = 2 bytes per sample
            logger.info(f"Calling Whisper API... Audio size: {len(audio_data)} bytes ({audio_duration:.1f}s)")
            start = time.time()

            # Whisper API call - auto-detect language
            # Language setting is only used as hint for LLM cleanup, not for transcription
            kwargs = {
                "model": "whisper-1",
                "file": ("audio.wav", audio_data, "audio/wav"),
                "response_format": "text",
                "temperature": 0.0  # Reduce hallucinations
            }

            # Generic prompt to reduce hallucinations (no language forcing)
            kwargs["prompt"] = "This is a transcription of natural speech. The text may contain sentences about any topic."

            response = self._client.audio.transcriptions.create(**kwargs)
            raw_text = response.strip() if isinstance(response, str) else response.text.strip()

            logger.info(f"Whisper done in {time.time() - start:.2f}s ({len(raw_text)} chars): {raw_text[:50]}...")

            if not raw_text:
                raise Exception("No speech detected")

            # LLM cleanup if enabled and model selected
            final_text = raw_text
            cleanup_model = self._settings.get("transcription.cleanup_model", "gpt-4o-mini")
            if cleanup_model:  # Only if model is not empty
                if self._pill:
                    self._main_window.after(0, lambda: self._pill.set_state(self._PillState.PROCESSING))

                logger.info(f"Calling {cleanup_model} for cleanup...")
                final_text = self._cleanup_text(raw_text)
                logger.info(f"Cleanup done: {final_text[:50]}...")
            else:
                logger.info("Cleanup skipped (None selected)")

            # Variable Recognition - Format with code identifiers
            try:
                if self._settings.get("variable_recognition.enabled", True):
                    if self._active_window_service.is_developer_app_active():
                        window_info = self._active_window_service.get_active_window_info()
                        logger.info(f"Developer app detected: {window_info['app_name']}")

                        # Get code context from screen
                        if self._screen_code_service:
                            code_context = self._screen_code_service.get_code_context()
                            raw_identifiers = code_context.get("code_identifiers", [])

                            if raw_identifiers:
                                # Extract and validate identifiers
                                identifiers = self._code_identifier_service.extract_identifiers(
                                    "\n".join(raw_identifiers)
                                )

                                if identifiers:
                                    # Format transcription with backticks
                                    formatted_text = self._transcription_formatter_service.format_with_code_identifiers(
                                        final_text,
                                        identifiers
                                    )

                                    if formatted_text != final_text:
                                        logger.info(f"Formatted with {len(identifiers)} code identifiers")
                                        final_text = formatted_text
                                    else:
                                        logger.debug("No identifiers matched in transcription")
                                else:
                                    logger.debug("No valid identifiers found")
                            else:
                                logger.debug("No code identifiers detected from screen")
                    else:
                        logger.debug("No developer app active, skipping variable recognition")
                else:
                    logger.debug("Variable recognition disabled")
            except Exception as e:
                logger.warning(f"Variable recognition failed (continuing with unformatted text): {e}")
                # Continue with unformatted text - don't fail the whole transcription

            # Copy to clipboard and paste
            self._inject_text(final_text)

            # Success
            self._main_window.after(0, self._on_success)

        except Exception as e:
            logger.error(f"Processing failed: {e}")
            self._main_window.after(0, lambda: self._on_error(str(e)))

    def _cleanup_text(self, text: str) -> str:
        """Clean up text with selected model."""
        try:
            model = self._settings.get("transcription.cleanup_model", "gpt-4o-mini")
            if not model:
                return text  # No cleanup

            response = self._client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": """Clean up the transcribed text while preserving the original language.

Rules:
1. Remove filler words (um, uh, like, you know, etc. in any language)
2. Fix grammar and spelling in the ORIGINAL language
3. Preserve the original meaning and FULL LENGTH of the text
4. DO NOT shorten or omit parts
5. DO NOT translate - keep the same language as the input
6. Return ONLY the cleaned text"""
                    },
                    {"role": "user", "content": text}
                ],
                temperature=0.1,
                max_tokens=4096
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")
            return text

    def _inject_text(self, text: str):
        """Copy text and paste using Windows API."""
        try:
            import ctypes
            from ctypes import wintypes

            # Check paste timeout to prevent double paste
            current_time = time.time()
            time_since_last_paste = current_time - self._last_paste_time

            if time_since_last_paste < self._paste_timeout:
                logger.warning(f"Paste blocked - too soon ({time_since_last_paste:.3f}s < {self._paste_timeout}s)")
                return

            # Update last paste time
            self._last_paste_time = current_time

            # Copy to clipboard
            pyperclip.copy(text)
            time.sleep(0.05)

            # Simulate Ctrl+V using Windows SendInput
            # Virtual key codes
            VK_CONTROL = 0x11
            VK_V = 0x56
            KEYEVENTF_KEYUP = 0x0002

            # Press Ctrl
            ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)
            time.sleep(0.01)

            # Press V
            ctypes.windll.user32.keybd_event(VK_V, 0, 0, 0)
            time.sleep(0.01)

            # Release V
            ctypes.windll.user32.keybd_event(VK_V, 0, KEYEVENTF_KEYUP, 0)
            time.sleep(0.01)

            # Release Ctrl
            ctypes.windll.user32.keybd_event(VK_CONTROL, 0, KEYEVENTF_KEYUP, 0)

            # Clear clipboard to prevent accidental double paste
            time.sleep(0.05)
            pyperclip.copy("")

            logger.info(f"Text injected: {len(text)} chars")

        except Exception as e:
            logger.error(f"Injection failed: {e}")
            raise

    def _on_success(self):
        """Handle success on main thread."""
        self._state = AppState.IDLE
        if self._pill:
            self._pill.show_success()

    def _on_error(self, error: str):
        """Handle error on main thread."""
        self._state = AppState.IDLE
        if self._pill:
            self._pill.show_error(error[:15])

    def _on_pill_close(self):
        """Handle pill close button - shut down application."""
        logger.info("Shutting down application from pill close button")

        # Clean up resources
        self._cleanup()

        # Destroy pill window
        if self._pill:
            try:
                self._pill.destroy()
            except:
                pass

        # Destroy main window (this will exit the mainloop)
        if self._main_window:
            try:
                self._main_window.destroy()
            except:
                pass

    def _hide_to_tray(self):
        """Hide pill to system tray instead of closing."""
        logger.info("Hiding pill to system tray")
        if self._pill:
            self._pill.withdraw()  # Hide pill

    def _close_settings(self):
        """Close settings window completely (called when X clicked on settings)."""
        logger.info("Closing settings window")
        if self._main_window:
            try:
                self._main_window.destroy()
                self._main_window = None
            except Exception as e:
                logger.error(f"Error closing settings: {e}")

    def _show_from_tray(self):
        """Show pill from system tray."""
        logger.info("Showing pill from system tray")
        if self._pill:
            self._pill.deiconify()  # Show pill
            self._pill.lift()  # Bring to front
            self._pill.focus_force()  # Give focus

    def _show_settings_from_tray(self):
        """Show settings window from system tray (create new if closed)."""
        logger.info("Showing settings from system tray")

        # If settings window was closed, create a new one
        if not self._main_window:
            from .ui.main_window import MainWindow
            self._main_window = MainWindow(
                settings_service=self._settings,
                audio_service=self._audio,
                on_start=self._start_service,
                on_stop=self._stop_service,
                on_close=self._close_settings
            )
            # Update UI if service is running
            if self._hotkey_service.is_registered():
                self._main_window._is_running = True
                self._main_window.start_btn.configure(
                    text="Stop",
                    fg_color=self._COLORS["error"],
                    hover_color="#dc2626"
                )
                self._main_window.status_dot.configure(fg_color=self._COLORS["success"])
                self._main_window.status_label.configure(
                    text="Running",
                    text_color=self._COLORS["text_secondary"]
                )
        else:
            self._main_window.deiconify()  # Show settings
            self._main_window.lift()  # Bring to front
            self._main_window.focus_force()  # Give focus

    def _quit_from_tray(self):
        """Quit application from system tray."""
        logger.info("Quitting application from system tray")
        self._on_pill_close()

    def _cleanup(self):
        """Clean up resources."""
        self._stop_service()
        if self._hotkey_service:
            self._hotkey_service.cleanup()
        if self._audio:
            self._audio.cleanup()
        if self._preprocessing:
            self._preprocessing.cleanup()
        if self._active_window_service:
            self._active_window_service.cleanup()
        if self._screen_code_service:
            self._screen_code_service.cleanup()
        if self._code_identifier_service:
            self._code_identifier_service.cleanup()
        if self._transcription_formatter_service:
            self._transcription_formatter_service.cleanup()
        if self._system_tray_service:
            self._system_tray_service.cleanup()
        logger.info("Cleanup complete")
