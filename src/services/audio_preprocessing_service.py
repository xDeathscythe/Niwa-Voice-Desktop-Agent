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
        threshold: float = 0.35
    ) -> list:
        """
        Detect speech segments in audio using Silero VAD.

        Args:
            audio_data: Audio numpy array
            sample_rate: Sample rate in Hz
            threshold: Speech detection threshold (0.0-1.0), lower = more sensitive

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

            # Get speech timestamps with improved settings for better quality
            # - Lower threshold (0.35) to catch softer speech at sentence ends
            # - Longer speech_pad_ms (200ms) to prevent cutting off last words
            # - Longer min_silence_duration (800ms) to not split natural pauses
            speech_timestamps = self.get_speech_timestamps(
                audio_tensor,
                self._vad_model,
                sampling_rate=sample_rate,
                threshold=threshold,
                min_speech_duration_ms=200,       # Shorter minimum to catch brief utterances
                max_speech_duration_s=120,        # Allow longer continuous speech
                min_silence_duration_ms=800,      # Longer silence before considering end
                window_size_samples=512,
                speech_pad_ms=200                 # 200ms padding around speech (was 30ms!)
            )

            return speech_timestamps

        except Exception as e:
            logger.error(f"VAD detection failed: {e}")
            return [{'start': 0, 'end': len(audio_data)}]

    def trim_silence(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000,
        threshold: float = 0.35,
        keep_padding_ms: int = 300
    ) -> np.ndarray:
        """
        Trim silence from beginning and end of audio using VAD.

        Keeps extra padding at start and end to prevent cutting off speech.

        Args:
            audio_data: Audio numpy array
            sample_rate: Sample rate in Hz
            threshold: Speech detection threshold
            keep_padding_ms: Extra padding to keep at start/end in milliseconds

        Returns:
            Trimmed audio numpy array
        """
        segments = self.detect_speech_segments(audio_data, sample_rate, threshold)

        if not segments:
            logger.warning("No speech detected, returning original audio")
            return audio_data

        # Calculate padding in samples
        padding_samples = int(keep_padding_ms * sample_rate / 1000)

        # Get first and last speech segment with extra padding
        first_start = max(0, segments[0]['start'] - padding_samples)
        last_end = min(len(audio_data), segments[-1]['end'] + padding_samples)

        # Trim audio with padding preserved
        trimmed = audio_data[first_start:last_end]

        trimmed_duration = (len(audio_data) - len(trimmed)) / sample_rate
        logger.info(f"Trimmed {trimmed_duration:.2f}s of silence "
                   f"(kept {keep_padding_ms}ms padding at edges)")

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

    def apply_fade(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000,
        fade_in_ms: int = 20,
        fade_out_ms: int = 50
    ) -> np.ndarray:
        """
        Apply fade-in and fade-out to prevent audio clicks/pops.

        Args:
            audio_data: Audio numpy array
            sample_rate: Sample rate in Hz
            fade_in_ms: Fade-in duration in milliseconds
            fade_out_ms: Fade-out duration in milliseconds

        Returns:
            Audio with fades applied
        """
        audio = audio_data.copy()

        fade_in_samples = int(fade_in_ms * sample_rate / 1000)
        fade_out_samples = int(fade_out_ms * sample_rate / 1000)

        # Apply fade-in
        if fade_in_samples > 0 and len(audio) > fade_in_samples:
            fade_in_curve = np.linspace(0, 1, fade_in_samples)
            audio[:fade_in_samples] *= fade_in_curve

        # Apply fade-out
        if fade_out_samples > 0 and len(audio) > fade_out_samples:
            fade_out_curve = np.linspace(1, 0, fade_out_samples)
            audio[-fade_out_samples:] *= fade_out_curve

        logger.debug(f"Applied fade-in ({fade_in_ms}ms) and fade-out ({fade_out_ms}ms)")
        return audio

    def add_silence_padding(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000,
        start_padding_ms: int = 100,
        end_padding_ms: int = 300
    ) -> np.ndarray:
        """
        Add silence padding to start and end of audio.

        This helps Whisper process the audio better and prevents
        cutting off at edges.

        Args:
            audio_data: Audio numpy array
            sample_rate: Sample rate in Hz
            start_padding_ms: Padding at start in milliseconds
            end_padding_ms: Padding at end in milliseconds

        Returns:
            Audio with padding added
        """
        start_samples = int(start_padding_ms * sample_rate / 1000)
        end_samples = int(end_padding_ms * sample_rate / 1000)

        # Create silence arrays
        start_silence = np.zeros(start_samples, dtype=audio_data.dtype)
        end_silence = np.zeros(end_samples, dtype=audio_data.dtype)

        # Concatenate
        padded = np.concatenate([start_silence, audio_data, end_silence])

        logger.debug(f"Added silence padding: {start_padding_ms}ms start, {end_padding_ms}ms end")
        return padded

    def preprocess_audio(
        self,
        audio_bytes: bytes,
        sample_rate: int = 16000,
        enable_vad: bool = True,
        enable_noise_reduction: bool = True,
        enable_normalization: bool = True,
        enable_fade: bool = True,
        enable_padding: bool = True
    ) -> bytes:
        """
        Full audio preprocessing pipeline for optimal transcription quality.

        Pipeline order:
        1. Noise reduction (remove background noise)
        2. VAD trimming (remove long silences, keep padding at edges)
        3. Fade in/out (prevent audio clicks)
        4. Normalization (consistent volume)
        5. Silence padding (add buffer for Whisper)

        Args:
            audio_bytes: Raw WAV audio bytes
            sample_rate: Sample rate in Hz
            enable_vad: Enable Voice Activity Detection
            enable_noise_reduction: Enable noise reduction
            enable_normalization: Enable volume normalization
            enable_fade: Enable fade-in/fade-out
            enable_padding: Enable silence padding for Whisper

        Returns:
            Preprocessed audio as WAV bytes
        """
        logger.info(f"Preprocessing audio: VAD={enable_vad}, "
                   f"NoiseReduce={enable_noise_reduction}, "
                   f"Normalize={enable_normalization}, "
                   f"Fade={enable_fade}, Padding={enable_padding}")

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
            original_duration = original_length / sample_rate

            # Step 1: Noise reduction (before VAD for better detection)
            if enable_noise_reduction:
                audio_data = self.reduce_noise(audio_data, sample_rate)

            # Step 2: VAD trimming (keeps 300ms padding at edges)
            if enable_vad:
                audio_data = self.trim_silence(audio_data, sample_rate, keep_padding_ms=300)

            # Step 3: Apply fade-in/fade-out (prevent clicks)
            if enable_fade:
                audio_data = self.apply_fade(audio_data, sample_rate,
                                            fade_in_ms=20, fade_out_ms=50)

            # Step 4: Normalize volume
            if enable_normalization:
                audio_data = self.normalize_volume(audio_data)

            # Step 5: Add silence padding for Whisper (helps with edge detection)
            if enable_padding:
                audio_data = self.add_silence_padding(audio_data, sample_rate,
                                                     start_padding_ms=100,
                                                     end_padding_ms=300)

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
            final_duration = len(audio_data) / sample_rate

            logger.info(f"Preprocessing complete: "
                       f"{original_duration:.2f}s -> {final_duration:.2f}s "
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
