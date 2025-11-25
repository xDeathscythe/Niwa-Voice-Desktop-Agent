"""
Audio Manager Module for VoiceType Application.

Handles microphone enumeration, audio recording, real-time level monitoring,
and audio format conversion for Whisper API compatibility.
"""

import io
import wave
import threading
import numpy as np
from typing import List, Dict, Optional, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
import queue
import time

try:
    import pyaudio
except ImportError:
    raise ImportError("PyAudio is required. Install with: pip install pyaudio")


class AudioState(Enum):
    """Enumeration of possible audio recording states."""
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    PROCESSING = "processing"


@dataclass
class AudioDevice:
    """Represents an audio input device."""
    index: int
    name: str
    channels: int
    sample_rate: int
    is_default: bool

    def __str__(self) -> str:
        default_marker = " (Default)" if self.is_default else ""
        return f"{self.name}{default_marker}"


@dataclass
class AudioConfig:
    """Audio recording configuration."""
    sample_rate: int = 16000  # Whisper prefers 16kHz
    channels: int = 1  # Mono for speech recognition
    chunk_size: int = 1024  # Frames per buffer
    format: int = pyaudio.paInt16  # 16-bit audio
    max_recording_seconds: int = 300  # 5 minutes max


class AudioManager:
    """
    Manages audio recording and device enumeration for VoiceType.

    This class provides functionality for:
    - Enumerating available audio input devices (microphones)
    - Recording audio from a selected device
    - Real-time audio level monitoring for visualization
    - Converting recorded audio to Whisper API compatible format

    Thread-safe implementation for use in GUI applications.

    Example:
        manager = AudioManager()
        devices = manager.get_available_devices()
        manager.select_device(devices[0].index)
        manager.start_recording()
        # ... recording ...
        audio_data = manager.stop_recording()
        wav_bytes = manager.convert_to_wav(audio_data)
    """

    def __init__(self, config: Optional[AudioConfig] = None):
        """
        Initialize the AudioManager.

        Args:
            config: Optional AudioConfig for custom settings.
                   Uses defaults if not provided.
        """
        self._config = config or AudioConfig()
        self._pyaudio: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None
        self._selected_device_index: Optional[int] = None
        self._state = AudioState.IDLE
        self._state_lock = threading.Lock()

        # Recording data
        self._audio_frames: List[bytes] = []
        self._frames_lock = threading.Lock()

        # Real-time level monitoring
        self._current_level: float = 0.0
        self._level_lock = threading.Lock()
        self._level_callback: Optional[Callable[[float], None]] = None

        # Recording thread
        self._recording_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        # Initialize PyAudio
        self._initialize_pyaudio()

    def _initialize_pyaudio(self) -> None:
        """Initialize PyAudio instance."""
        try:
            self._pyaudio = pyaudio.PyAudio()
        except Exception as e:
            raise RuntimeError(f"Failed to initialize audio system: {e}")

    def get_available_devices(self) -> List[AudioDevice]:
        """
        Enumerate all available audio input devices.

        Returns:
            List of AudioDevice objects representing available microphones.

        Raises:
            RuntimeError: If audio system is not initialized.
        """
        if self._pyaudio is None:
            raise RuntimeError("Audio system not initialized")

        devices: List[AudioDevice] = []
        default_input_index = -1

        try:
            default_info = self._pyaudio.get_default_input_device_info()
            default_input_index = default_info.get('index', -1)
        except IOError:
            # No default input device available
            pass

        device_count = self._pyaudio.get_device_count()

        for i in range(device_count):
            try:
                info = self._pyaudio.get_device_info_by_index(i)

                # Only include input devices (microphones)
                if info.get('maxInputChannels', 0) > 0:
                    device = AudioDevice(
                        index=i,
                        name=info.get('name', f'Device {i}'),
                        channels=info.get('maxInputChannels', 1),
                        sample_rate=int(info.get('defaultSampleRate', 44100)),
                        is_default=(i == default_input_index)
                    )
                    devices.append(device)
            except Exception:
                # Skip devices that can't be queried
                continue

        return devices

    def select_device(self, device_index: int) -> bool:
        """
        Select an audio input device for recording.

        Args:
            device_index: The index of the device to select.

        Returns:
            True if device was successfully selected, False otherwise.

        Raises:
            ValueError: If device index is invalid.
            RuntimeError: If recording is in progress.
        """
        with self._state_lock:
            if self._state == AudioState.RECORDING:
                raise RuntimeError("Cannot change device while recording")

        if self._pyaudio is None:
            raise RuntimeError("Audio system not initialized")

        # Verify device exists and is an input device
        try:
            info = self._pyaudio.get_device_info_by_index(device_index)
            if info.get('maxInputChannels', 0) <= 0:
                raise ValueError(f"Device {device_index} is not an input device")

            self._selected_device_index = device_index
            return True

        except IOError as e:
            raise ValueError(f"Invalid device index {device_index}: {e}")

    def get_selected_device(self) -> Optional[int]:
        """
        Get the currently selected device index.

        Returns:
            Device index or None if no device is selected.
        """
        return self._selected_device_index

    def set_level_callback(self, callback: Optional[Callable[[float], None]]) -> None:
        """
        Set a callback for real-time audio level updates.

        The callback receives a float value between 0.0 and 1.0
        representing the current audio level.

        Args:
            callback: Function to call with level updates, or None to disable.
        """
        self._level_callback = callback

    def get_current_level(self) -> float:
        """
        Get the current audio input level.

        Returns:
            Float between 0.0 and 1.0 representing current level.
        """
        with self._level_lock:
            return self._current_level

    def get_state(self) -> AudioState:
        """
        Get the current recording state.

        Returns:
            Current AudioState enum value.
        """
        with self._state_lock:
            return self._state

    def start_recording(self) -> bool:
        """
        Start recording audio from the selected device.

        Returns:
            True if recording started successfully.

        Raises:
            RuntimeError: If no device is selected or recording already in progress.
        """
        with self._state_lock:
            if self._state == AudioState.RECORDING:
                raise RuntimeError("Recording already in progress")

            if self._selected_device_index is None:
                # Try to use default device
                devices = self.get_available_devices()
                default_devices = [d for d in devices if d.is_default]
                if default_devices:
                    self._selected_device_index = default_devices[0].index
                elif devices:
                    self._selected_device_index = devices[0].index
                else:
                    raise RuntimeError("No audio input devices available")

            self._state = AudioState.RECORDING

        # Clear previous recording
        with self._frames_lock:
            self._audio_frames = []

        # Reset stop event
        self._stop_event.clear()

        # Start recording thread
        self._recording_thread = threading.Thread(
            target=self._recording_loop,
            daemon=True
        )
        self._recording_thread.start()

        return True

    def _recording_loop(self) -> None:
        """Internal recording loop running in a separate thread."""
        try:
            self._stream = self._pyaudio.open(
                format=self._config.format,
                channels=self._config.channels,
                rate=self._config.sample_rate,
                input=True,
                input_device_index=self._selected_device_index,
                frames_per_buffer=self._config.chunk_size
            )

            max_frames = int(
                self._config.sample_rate / self._config.chunk_size *
                self._config.max_recording_seconds
            )
            frame_count = 0

            while not self._stop_event.is_set() and frame_count < max_frames:
                try:
                    data = self._stream.read(
                        self._config.chunk_size,
                        exception_on_overflow=False
                    )

                    # Store frame
                    with self._frames_lock:
                        self._audio_frames.append(data)

                    # Calculate level for visualization
                    self._update_level(data)

                    frame_count += 1

                except IOError as e:
                    # Buffer overflow or other IO error - continue recording
                    continue

        except Exception as e:
            with self._state_lock:
                self._state = AudioState.IDLE
            raise RuntimeError(f"Recording error: {e}")

        finally:
            if self._stream is not None:
                try:
                    self._stream.stop_stream()
                    self._stream.close()
                except Exception:
                    pass
                self._stream = None

    def _update_level(self, data: bytes) -> None:
        """
        Calculate and update the current audio level.

        Args:
            data: Raw audio bytes to analyze.
        """
        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(data, dtype=np.int16)

            # Calculate RMS level
            if len(audio_array) > 0:
                rms = np.sqrt(np.mean(audio_array.astype(np.float64) ** 2))
                # Normalize to 0-1 range (16-bit audio max is 32767)
                level = min(1.0, rms / 32767.0 * 5)  # *5 for better sensitivity
            else:
                level = 0.0

            with self._level_lock:
                self._current_level = level

            # Call callback if set
            if self._level_callback is not None:
                try:
                    self._level_callback(level)
                except Exception:
                    pass  # Don't let callback errors affect recording

        except Exception:
            pass  # Don't let level calculation errors affect recording

    def stop_recording(self) -> bytes:
        """
        Stop recording and return the recorded audio data.

        Returns:
            Raw audio bytes (PCM format).

        Raises:
            RuntimeError: If not currently recording.
        """
        with self._state_lock:
            if self._state != AudioState.RECORDING:
                raise RuntimeError("Not currently recording")
            self._state = AudioState.PROCESSING

        # Signal recording thread to stop
        self._stop_event.set()

        # Wait for recording thread to finish
        if self._recording_thread is not None:
            self._recording_thread.join(timeout=2.0)
            self._recording_thread = None

        # Get recorded frames
        with self._frames_lock:
            audio_data = b''.join(self._audio_frames)
            self._audio_frames = []

        # Reset level
        with self._level_lock:
            self._current_level = 0.0

        with self._state_lock:
            self._state = AudioState.IDLE

        return audio_data

    def cancel_recording(self) -> None:
        """Cancel recording without saving data."""
        with self._state_lock:
            if self._state != AudioState.RECORDING:
                return
            self._state = AudioState.IDLE

        self._stop_event.set()

        if self._recording_thread is not None:
            self._recording_thread.join(timeout=2.0)
            self._recording_thread = None

        with self._frames_lock:
            self._audio_frames = []

        with self._level_lock:
            self._current_level = 0.0

    def convert_to_wav(self, audio_data: bytes) -> bytes:
        """
        Convert raw PCM audio data to WAV format.

        Whisper API accepts WAV files, so this conversion is necessary
        for API compatibility.

        Args:
            audio_data: Raw PCM audio bytes.

        Returns:
            WAV file bytes ready for Whisper API.
        """
        buffer = io.BytesIO()

        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(self._config.channels)
            wav_file.setsampwidth(2)  # 16-bit = 2 bytes
            wav_file.setframerate(self._config.sample_rate)
            wav_file.writeframes(audio_data)

        buffer.seek(0)
        return buffer.read()

    def get_recording_duration(self) -> float:
        """
        Get the current recording duration in seconds.

        Returns:
            Duration in seconds, or 0 if not recording.
        """
        with self._frames_lock:
            frame_count = len(self._audio_frames)

        if frame_count == 0:
            return 0.0

        # Calculate duration based on frames and sample rate
        total_samples = frame_count * self._config.chunk_size
        return total_samples / self._config.sample_rate

    def is_recording(self) -> bool:
        """
        Check if currently recording.

        Returns:
            True if recording is in progress.
        """
        with self._state_lock:
            return self._state == AudioState.RECORDING

    def cleanup(self) -> None:
        """
        Clean up resources.

        Should be called when the AudioManager is no longer needed.
        """
        self.cancel_recording()

        if self._pyaudio is not None:
            try:
                self._pyaudio.terminate()
            except Exception:
                pass
            self._pyaudio = None

    def __enter__(self) -> 'AudioManager':
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.cleanup()

    def __del__(self) -> None:
        """Destructor - ensure cleanup."""
        self.cleanup()


# Utility functions

def get_default_device() -> Optional[AudioDevice]:
    """
    Get the default audio input device.

    Returns:
        AudioDevice for the default microphone, or None if unavailable.
    """
    try:
        manager = AudioManager()
        devices = manager.get_available_devices()
        for device in devices:
            if device.is_default:
                return device
        return devices[0] if devices else None
    except Exception:
        return None
    finally:
        manager.cleanup()


def test_microphone(device_index: int, duration: float = 2.0) -> Tuple[bool, float]:
    """
    Test a microphone by recording briefly and checking levels.

    Args:
        device_index: Index of the device to test.
        duration: How long to test in seconds.

    Returns:
        Tuple of (success: bool, average_level: float).
    """
    manager = AudioManager()
    levels: List[float] = []

    try:
        manager.select_device(device_index)
        manager.set_level_callback(lambda l: levels.append(l))
        manager.start_recording()
        time.sleep(duration)
        manager.stop_recording()

        avg_level = sum(levels) / len(levels) if levels else 0.0
        return True, avg_level

    except Exception:
        return False, 0.0

    finally:
        manager.cleanup()


if __name__ == "__main__":
    # Demo/test code
    print("Audio Manager Demo")
    print("-" * 40)

    with AudioManager() as manager:
        devices = manager.get_available_devices()
        print(f"\nFound {len(devices)} audio input device(s):\n")

        for device in devices:
            print(f"  [{device.index}] {device}")

        if devices:
            print(f"\nTesting default device for 3 seconds...")
            manager.set_level_callback(
                lambda l: print(f"  Level: {'=' * int(l * 50)}", end='\r')
            )
            manager.start_recording()
            time.sleep(3)
            audio = manager.stop_recording()
            wav_data = manager.convert_to_wav(audio)
            print(f"\n\nRecorded {len(audio)} bytes of audio")
            print(f"WAV file size: {len(wav_data)} bytes")
