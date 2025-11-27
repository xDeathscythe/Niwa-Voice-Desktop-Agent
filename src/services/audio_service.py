"""Audio capture and processing service for VoiceType."""

import io
import wave
import threading
import queue
import logging
from typing import Optional, List, Callable, Dict, Any
from dataclasses import dataclass
import numpy as np

try:
    import sounddevice as sd
except ImportError:
    sd = None

from ..core.exceptions import (
    AudioDeviceNotFoundError,
    AudioPermissionDeniedError,
    AudioRecordingError,
    AudioTooShortError
)

logger = logging.getLogger(__name__)


@dataclass
class AudioDevice:
    """Represents an audio input device."""
    id: int
    name: str
    channels: int
    sample_rate: float
    is_default: bool = False

    def __str__(self) -> str:
        default_str = " (Default)" if self.is_default else ""
        return f"{self.name}{default_str}"


class AudioService:
    """
    Audio capture service for VoiceType.

    Handles:
    - Device enumeration
    - Audio recording with real-time level monitoring
    - WAV format conversion for Whisper API
    - Thread-safe operations

    Usage:
        service = AudioService()
        devices = service.get_input_devices()
        service.set_device(devices[0].id)

        service.start_recording()
        # ... user speaks ...
        audio_data = service.stop_recording()  # Returns WAV bytes
    """

    # Audio settings optimized for Whisper API
    SAMPLE_RATE = 16000  # Whisper works best with 16kHz
    CHANNELS = 1  # Mono
    DTYPE = np.int16
    CHUNK_SIZE = 1024
    MIN_DURATION = 0.5  # Minimum recording duration in seconds
    MAX_DURATION = 300  # Maximum recording duration (5 minutes)

    def __init__(self):
        """Initialize audio service."""
        if sd is None:
            raise ImportError("sounddevice is required. Install with: pip install sounddevice")

        self._device_id: Optional[int] = None
        self._is_recording = False
        self._audio_buffer: List[np.ndarray] = []
        self._buffer_lock = threading.Lock()
        self._stream: Optional[sd.InputStream] = None
        self._level_callback: Optional[Callable[[float], None]] = None

        # Level monitoring
        self._current_level = 0.0
        self._level_smoothing = 0.3

        logger.info("AudioService initialized")

    def get_input_devices(self) -> List[AudioDevice]:
        """
        Get list of available audio input devices.

        Returns:
            List of AudioDevice objects
        """
        devices = []
        try:
            device_list = sd.query_devices()
            default_input = sd.default.device[0]

            for i, device in enumerate(device_list):
                if device['max_input_channels'] > 0:
                    devices.append(AudioDevice(
                        id=i,
                        name=device['name'],
                        channels=device['max_input_channels'],
                        sample_rate=device['default_samplerate'],
                        is_default=(i == default_input)
                    ))

            logger.debug(f"Found {len(devices)} input devices")

        except Exception as e:
            logger.error(f"Error enumerating devices: {e}")
            raise AudioDeviceNotFoundError(str(e))

        return devices

    def get_default_device(self) -> Optional[AudioDevice]:
        """Get the default input device."""
        devices = self.get_input_devices()
        for device in devices:
            if device.is_default:
                return device
        return devices[0] if devices else None

    def set_device(self, device_id: int) -> None:
        """
        Set the input device to use for recording.

        Args:
            device_id: Device ID from get_input_devices()
        """
        # Verify device exists
        try:
            device_info = sd.query_devices(device_id)
            if device_info['max_input_channels'] < 1:
                raise AudioDeviceNotFoundError(f"Device {device_id} has no input channels")
        except Exception as e:
            raise AudioDeviceNotFoundError(str(e))

        self._device_id = device_id
        logger.info(f"Audio device set to: {device_info['name']}")

    def set_level_callback(self, callback: Callable[[float], None]) -> None:
        """
        Set callback for audio level updates.

        Args:
            callback: Function that receives level (0.0 to 1.0)
        """
        self._level_callback = callback

    def start_recording(self) -> None:
        """
        Start recording audio.

        Raises:
            AudioPermissionDeniedError: If microphone access denied
            AudioRecordingError: If recording fails to start
        """
        if self._is_recording:
            logger.warning("Already recording")
            return

        # Clear buffer
        with self._buffer_lock:
            self._audio_buffer.clear()

        try:
            device_id = self._device_id or sd.default.device[0]

            self._stream = sd.InputStream(
                device=device_id,
                channels=self.CHANNELS,
                samplerate=self.SAMPLE_RATE,
                dtype=self.DTYPE,
                blocksize=self.CHUNK_SIZE,
                callback=self._audio_callback
            )
            self._stream.start()
            self._is_recording = True
            logger.info("Recording started")

        except sd.PortAudioError as e:
            if "permission" in str(e).lower():
                raise AudioPermissionDeniedError()
            raise AudioRecordingError(str(e))
        except Exception as e:
            raise AudioRecordingError(str(e))

    def stop_recording(self) -> bytes:
        """
        Stop recording and return audio data as WAV bytes.

        Includes a small buffer flush delay to ensure all audio is captured,
        preventing cutoff at the end of speech.

        Returns:
            WAV file as bytes, ready for Whisper API

        Raises:
            AudioTooShortError: If recording too short
            AudioRecordingError: If no audio captured
        """
        if not self._is_recording:
            raise AudioRecordingError("Not recording")

        try:
            # Small delay to flush any pending audio buffers
            # This prevents the last few milliseconds from being cut off
            import time
            time.sleep(0.1)  # 100ms buffer flush delay

            # Stop stream
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None

            self._is_recording = False

            # Combine buffer
            with self._buffer_lock:
                if not self._audio_buffer:
                    raise AudioRecordingError("No audio captured")

                audio_data = np.concatenate(self._audio_buffer)
                self._audio_buffer.clear()

            # Check duration
            duration = len(audio_data) / self.SAMPLE_RATE
            if duration < self.MIN_DURATION:
                raise AudioTooShortError(duration)

            logger.info(f"Recording stopped. Duration: {duration:.2f}s, "
                       f"Samples: {len(audio_data)}")

            # Convert to WAV bytes
            wav_bytes = self._to_wav(audio_data)
            return wav_bytes

        except (AudioTooShortError, AudioRecordingError):
            raise
        except Exception as e:
            raise AudioRecordingError(str(e))

    def cancel_recording(self) -> None:
        """Cancel recording without returning data."""
        if not self._is_recording:
            return

        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

        self._is_recording = False

        with self._buffer_lock:
            self._audio_buffer.clear()

        logger.info("Recording cancelled")

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: Any,
        status: sd.CallbackFlags
    ) -> None:
        """Callback for audio stream (runs in audio thread)."""
        if status:
            logger.warning(f"Audio callback status: {status}")

        # Store audio data
        with self._buffer_lock:
            self._audio_buffer.append(indata.copy())

        # Calculate level (RMS)
        rms = np.sqrt(np.mean(indata.astype(np.float32) ** 2))
        # Normalize to 0-1 range (assuming int16)
        level = min(1.0, rms / 10000)

        # Smooth the level
        self._current_level = (
            self._current_level * self._level_smoothing +
            level * (1 - self._level_smoothing)
        )

        # Emit level update
        if self._level_callback:
            self._level_callback(self._current_level)

    def _to_wav(self, audio_data: np.ndarray) -> bytes:
        """Convert numpy array to WAV bytes."""
        buffer = io.BytesIO()

        with wave.open(buffer, 'wb') as wav:
            wav.setnchannels(self.CHANNELS)
            wav.setsampwidth(2)  # 16-bit = 2 bytes
            wav.setframerate(self.SAMPLE_RATE)
            wav.writeframes(audio_data.tobytes())

        buffer.seek(0)
        return buffer.read()

    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._is_recording

    def get_current_level(self) -> float:
        """Get current audio level (0.0 to 1.0)."""
        return self._current_level

    def test_device(self, device_id: Optional[int] = None, duration: float = 1.0) -> float:
        """
        Test a device by recording briefly and returning average level.

        Args:
            device_id: Device to test (default if None)
            duration: Test duration in seconds

        Returns:
            Average audio level during test
        """
        device = device_id if device_id is not None else sd.default.device[0]
        levels = []

        def callback(indata, frames, time_info, status):
            rms = np.sqrt(np.mean(indata.astype(np.float32) ** 2))
            levels.append(min(1.0, rms / 10000))

        try:
            with sd.InputStream(
                device=device,
                channels=self.CHANNELS,
                samplerate=self.SAMPLE_RATE,
                dtype=self.DTYPE,
                blocksize=self.CHUNK_SIZE,
                callback=callback
            ):
                sd.sleep(int(duration * 1000))

            return sum(levels) / len(levels) if levels else 0.0

        except Exception as e:
            logger.error(f"Device test failed: {e}")
            return 0.0

    def cleanup(self) -> None:
        """Clean up resources."""
        if self._is_recording:
            self.cancel_recording()
        logger.info("AudioService cleaned up")
