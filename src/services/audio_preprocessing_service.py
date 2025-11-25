"""Audio preprocessing service for VAD, noise reduction, and audio enhancement."""

import logging
import io
import wave
from typing import Tuple, Optional

import numpy as np
import torch
import torchaudio
import noisereduce as nr

logger = logging.getLogger(__name__)


class AudioPreprocessingService:
    """
    Audio preprocessing service for improving transcription quality.

    Features:
    - Voice Activity Detection (VAD) using Silero VAD
    - Noise reduction
    - Volume normalization
    - Silence trimming
    """

    def __init__(self):
        """Initialize audio preprocessing service."""
        self._vad_model = None
        self._vad_utils = None
        self._vad_loaded = False

        logger.info("AudioPreprocessingService initialized")

    def _load_vad_model(self):
        """Load Silero VAD model (lazy loading)."""
        if self._vad_loaded:
            return

        try:
            logger.info("Loading Silero VAD model...")
            self._vad_model, self._vad_utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False
            )
            (self.get_speech_timestamps, _, self.read_audio, _, _) = self._vad_utils
            self._vad_loaded = True
            logger.info("Silero VAD model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load VAD model: {e}")
            self._vad_loaded = False

    def detect_speech_segments(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000,
        threshold: float = 0.5
    ) -> list:
        """
        Detect speech segments in audio using Silero VAD.

        Args:
            audio_data: Audio numpy array
            sample_rate: Sample rate in Hz
            threshold: Speech detection threshold (0.0-1.0)

        Returns:
            List of speech segments as dicts with 'start' and 'end' timestamps
        """
        self._load_vad_model()

        if not self._vad_loaded:
            logger.warning("VAD model not loaded, returning full audio")
            return [{'start': 0, 'end': len(audio_data)}]

        try:
            # Convert to torch tensor
            audio_tensor = torch.from_numpy(audio_data).float()

            # Get speech timestamps
            speech_timestamps = self.get_speech_timestamps(
                audio_tensor,
                self._vad_model,
                sampling_rate=sample_rate,
                threshold=threshold,
                min_speech_duration_ms=250,
                max_speech_duration_s=60,
                min_silence_duration_ms=500,
                window_size_samples=512,
                speech_pad_ms=30
            )

            return speech_timestamps

        except Exception as e:
            logger.error(f"VAD detection failed: {e}")
            return [{'start': 0, 'end': len(audio_data)}]

    def trim_silence(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000,
        threshold: float = 0.5
    ) -> np.ndarray:
        """
        Trim silence from beginning and end of audio using VAD.

        Args:
            audio_data: Audio numpy array
            sample_rate: Sample rate in Hz
            threshold: Speech detection threshold

        Returns:
            Trimmed audio numpy array
        """
        segments = self.detect_speech_segments(audio_data, sample_rate, threshold)

        if not segments:
            logger.warning("No speech detected, returning original audio")
            return audio_data

        # Get first and last speech segment
        first_start = segments[0]['start']
        last_end = segments[-1]['end']

        # Trim audio
        trimmed = audio_data[first_start:last_end]

        logger.info(f"Trimmed {len(audio_data) - len(trimmed)} samples "
                   f"({(len(audio_data) - len(trimmed)) / sample_rate:.2f}s)")

        return trimmed

    def reduce_noise(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000,
        stationary: bool = True
    ) -> np.ndarray:
        """
        Reduce noise in audio using spectral gating.

        Args:
            audio_data: Audio numpy array
            sample_rate: Sample rate in Hz
            stationary: Whether noise is stationary

        Returns:
            Noise-reduced audio numpy array
        """
        try:
            # Apply noise reduction
            reduced = nr.reduce_noise(
                y=audio_data,
                sr=sample_rate,
                stationary=stationary,
                prop_decrease=0.8
            )

            logger.debug("Noise reduction applied")
            return reduced

        except Exception as e:
            logger.error(f"Noise reduction failed: {e}")
            return audio_data

    def normalize_volume(
        self,
        audio_data: np.ndarray,
        target_level: float = 0.8
    ) -> np.ndarray:
        """
        Normalize audio volume to target level.

        Args:
            audio_data: Audio numpy array
            target_level: Target peak level (0.0-1.0)

        Returns:
            Normalized audio numpy array
        """
        # Find current peak
        peak = np.max(np.abs(audio_data))

        if peak == 0:
            logger.warning("Audio is silent, cannot normalize")
            return audio_data

        # Normalize
        normalized = audio_data * (target_level / peak)

        logger.debug(f"Volume normalized: peak {peak:.3f} -> {target_level:.3f}")
        return normalized

    def preprocess_audio(
        self,
        audio_bytes: bytes,
        sample_rate: int = 16000,
        enable_vad: bool = True,
        enable_noise_reduction: bool = True,
        enable_normalization: bool = True
    ) -> bytes:
        """
        Full audio preprocessing pipeline.

        Args:
            audio_bytes: Raw WAV audio bytes
            sample_rate: Sample rate in Hz
            enable_vad: Enable Voice Activity Detection
            enable_noise_reduction: Enable noise reduction
            enable_normalization: Enable volume normalization

        Returns:
            Preprocessed audio as WAV bytes
        """
        logger.info(f"Preprocessing audio: VAD={enable_vad}, "
                   f"NoiseReduce={enable_noise_reduction}, "
                   f"Normalize={enable_normalization}")

        try:
            # Read WAV from bytes
            with wave.open(io.BytesIO(audio_bytes), 'rb') as wf:
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                framerate = wf.getframerate()
                frames = wf.readframes(wf.getnframes())

            # Convert to numpy array
            audio_data = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
            audio_data = audio_data / 32768.0  # Normalize to [-1, 1]

            original_length = len(audio_data)

            # Apply preprocessing steps
            if enable_noise_reduction:
                audio_data = self.reduce_noise(audio_data, sample_rate)

            if enable_vad:
                audio_data = self.trim_silence(audio_data, sample_rate)

            if enable_normalization:
                audio_data = self.normalize_volume(audio_data)

            # Convert back to int16
            audio_data = (audio_data * 32768.0).astype(np.int16)

            # Create WAV bytes
            output = io.BytesIO()
            with wave.open(output, 'wb') as wf:
                wf.setnchannels(n_channels)
                wf.setsampwidth(sampwidth)
                wf.setframerate(framerate)
                wf.writeframes(audio_data.tobytes())

            processed_bytes = output.getvalue()

            logger.info(f"Preprocessing complete: "
                       f"{original_length / sample_rate:.2f}s -> "
                       f"{len(audio_data) / sample_rate:.2f}s "
                       f"({len(audio_bytes)} -> {len(processed_bytes)} bytes)")

            return processed_bytes

        except Exception as e:
            logger.error(f"Preprocessing failed: {e}", exc_info=True)
            return audio_bytes  # Return original on failure

    def cleanup(self):
        """Clean up resources."""
        if self._vad_model is not None:
            del self._vad_model
            del self._vad_utils
            self._vad_model = None
            self._vad_utils = None
            self._vad_loaded = False
            logger.info("VAD model cleaned up")
