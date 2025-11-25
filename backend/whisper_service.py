"""
Whisper Service Module for VoiceType Application.

Handles communication with OpenAI's Whisper API for speech-to-text transcription.
Includes retry logic, timeout handling, and error management.
"""

import io
import asyncio
import logging
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
import httpx

# Configure logging
logger = logging.getLogger(__name__)


class TranscriptionError(Exception):
    """Base exception for transcription errors."""
    pass


class APIKeyError(TranscriptionError):
    """Raised when API key is invalid or missing."""
    pass


class RateLimitError(TranscriptionError):
    """Raised when API rate limit is exceeded."""

    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


class AudioFormatError(TranscriptionError):
    """Raised when audio format is invalid."""
    pass


class NetworkError(TranscriptionError):
    """Raised for network-related errors."""
    pass


class TranscriptionStatus(Enum):
    """Status of a transcription request."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TranscriptionResult:
    """Result of a transcription request."""
    text: str
    language: Optional[str] = None
    duration: Optional[float] = None
    status: TranscriptionStatus = TranscriptionStatus.COMPLETED
    error: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


@dataclass
class WhisperConfig:
    """Configuration for Whisper API service."""
    api_key: str
    model: str = "whisper-1"
    base_url: str = "https://api.openai.com/v1"
    timeout: float = 60.0  # seconds
    max_retries: int = 3
    retry_delay: float = 1.0  # seconds
    retry_multiplier: float = 2.0  # exponential backoff
    max_file_size: int = 25 * 1024 * 1024  # 25MB (OpenAI limit)


class WhisperService:
    """
    Service for transcribing audio using OpenAI's Whisper API.

    This class handles:
    - Sending audio files to Whisper API
    - Automatic retry with exponential backoff
    - Timeout handling
    - Multiple audio formats
    - Language detection and specification

    Thread-safe for concurrent use.

    Example:
        service = WhisperService(api_key="sk-...")
        result = await service.transcribe_async(audio_bytes, language="sr")
        print(result.text)

        # Or synchronous:
        result = service.transcribe(audio_bytes)
    """

    SUPPORTED_FORMATS = {
        'flac': 'audio/flac',
        'mp3': 'audio/mpeg',
        'mp4': 'audio/mp4',
        'mpeg': 'audio/mpeg',
        'm4a': 'audio/mp4',
        'ogg': 'audio/ogg',
        'wav': 'audio/wav',
        'webm': 'audio/webm',
    }

    def __init__(
            self,
            api_key: Optional[str] = None,
            config: Optional[WhisperConfig] = None
    ):
        """
        Initialize the Whisper service.

        Args:
            api_key: OpenAI API key. Can also be set via config.
            config: Optional WhisperConfig for custom settings.

        Raises:
            APIKeyError: If no API key is provided.
        """
        if config is not None:
            self._config = config
        elif api_key is not None:
            self._config = WhisperConfig(api_key=api_key)
        else:
            raise APIKeyError("API key must be provided")

        if not self._config.api_key:
            raise APIKeyError("API key cannot be empty")

        self._client: Optional[httpx.AsyncClient] = None
        self._sync_client: Optional[httpx.Client] = None

        # Progress callback
        self._progress_callback: Optional[Callable[[float], None]] = None

    @property
    def api_endpoint(self) -> str:
        """Get the full API endpoint URL."""
        return f"{self._config.base_url}/audio/transcriptions"

    def set_api_key(self, api_key: str) -> None:
        """
        Update the API key.

        Args:
            api_key: New OpenAI API key.

        Raises:
            APIKeyError: If API key is empty.
        """
        if not api_key:
            raise APIKeyError("API key cannot be empty")
        self._config.api_key = api_key

    def set_progress_callback(
            self,
            callback: Optional[Callable[[float], None]]
    ) -> None:
        """
        Set a callback for progress updates during transcription.

        Args:
            callback: Function receiving progress (0.0 to 1.0), or None to disable.
        """
        self._progress_callback = callback

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            "Authorization": f"Bearer {self._config.api_key}",
        }

    def _validate_audio(self, audio_data: bytes, file_format: str = "wav") -> None:
        """
        Validate audio data before sending.

        Args:
            audio_data: Audio bytes to validate.
            file_format: Audio format extension.

        Raises:
            AudioFormatError: If audio is invalid.
        """
        if not audio_data:
            raise AudioFormatError("Audio data is empty")

        if len(audio_data) > self._config.max_file_size:
            raise AudioFormatError(
                f"Audio file too large: {len(audio_data)} bytes "
                f"(max: {self._config.max_file_size} bytes)"
            )

        if file_format.lower() not in self.SUPPORTED_FORMATS:
            raise AudioFormatError(
                f"Unsupported format: {file_format}. "
                f"Supported: {', '.join(self.SUPPORTED_FORMATS.keys())}"
            )

    async def transcribe_async(
            self,
            audio_data: bytes,
            language: Optional[str] = None,
            prompt: Optional[str] = None,
            file_format: str = "wav",
            response_format: str = "json",
            temperature: float = 0.0
    ) -> TranscriptionResult:
        """
        Transcribe audio asynchronously using Whisper API.

        Args:
            audio_data: Audio file bytes.
            language: ISO-639-1 language code (e.g., "en", "sr", "de").
                     If None, Whisper will auto-detect.
            prompt: Optional prompt to guide transcription style.
            file_format: Audio format (wav, mp3, etc.).
            response_format: API response format (json, text, srt, vtt).
            temperature: Sampling temperature (0.0-1.0).

        Returns:
            TranscriptionResult with transcribed text.

        Raises:
            APIKeyError: If API key is invalid.
            RateLimitError: If rate limit exceeded.
            AudioFormatError: If audio format is invalid.
            NetworkError: For network issues.
            TranscriptionError: For other API errors.
        """
        # Validate audio
        self._validate_audio(audio_data, file_format)

        # Create async client if needed
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._config.timeout)

        # Prepare multipart form data
        mime_type = self.SUPPORTED_FORMATS.get(
            file_format.lower(),
            "audio/wav"
        )

        files = {
            "file": (f"audio.{file_format}", audio_data, mime_type)
        }

        data: Dict[str, Any] = {
            "model": self._config.model,
            "response_format": response_format,
            "temperature": str(temperature),
        }

        if language:
            data["language"] = language

        if prompt:
            data["prompt"] = prompt

        # Retry loop with exponential backoff
        last_error: Optional[Exception] = None
        retry_delay = self._config.retry_delay

        for attempt in range(self._config.max_retries):
            try:
                if self._progress_callback:
                    # Estimate progress based on attempt
                    progress = (attempt + 0.5) / self._config.max_retries
                    self._progress_callback(min(0.9, progress))

                response = await self._client.post(
                    self.api_endpoint,
                    headers=self._get_headers(),
                    files=files,
                    data=data
                )

                # Handle response
                if response.status_code == 200:
                    if self._progress_callback:
                        self._progress_callback(1.0)

                    return self._parse_response(response, response_format)

                elif response.status_code == 401:
                    raise APIKeyError("Invalid API key")

                elif response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    retry_seconds = float(retry_after) if retry_after else retry_delay
                    raise RateLimitError(
                        "Rate limit exceeded",
                        retry_after=retry_seconds
                    )

                elif response.status_code >= 500:
                    # Server error - retry
                    last_error = TranscriptionError(
                        f"Server error: {response.status_code}"
                    )

                else:
                    # Client error - don't retry
                    error_detail = self._extract_error(response)
                    raise TranscriptionError(f"API error: {error_detail}")

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_error = NetworkError(f"Network error: {str(e)}")

            except (APIKeyError, AudioFormatError):
                raise

            except RateLimitError as e:
                if e.retry_after:
                    await asyncio.sleep(e.retry_after)
                    continue
                last_error = e

            except TranscriptionError:
                raise

            except Exception as e:
                last_error = TranscriptionError(f"Unexpected error: {str(e)}")

            # Wait before retry (exponential backoff)
            if attempt < self._config.max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= self._config.retry_multiplier

        # All retries failed
        raise last_error or TranscriptionError("Transcription failed after retries")

    def transcribe(
            self,
            audio_data: bytes,
            language: Optional[str] = None,
            prompt: Optional[str] = None,
            file_format: str = "wav",
            response_format: str = "json",
            temperature: float = 0.0
    ) -> TranscriptionResult:
        """
        Transcribe audio synchronously using Whisper API.

        This is a synchronous wrapper around transcribe_async.
        For GUI applications, prefer using transcribe_async.

        Args:
            audio_data: Audio file bytes.
            language: ISO-639-1 language code.
            prompt: Optional prompt to guide transcription.
            file_format: Audio format.
            response_format: API response format.
            temperature: Sampling temperature.

        Returns:
            TranscriptionResult with transcribed text.
        """
        # Validate audio
        self._validate_audio(audio_data, file_format)

        # Create sync client if needed
        if self._sync_client is None:
            self._sync_client = httpx.Client(timeout=self._config.timeout)

        # Prepare request
        mime_type = self.SUPPORTED_FORMATS.get(file_format.lower(), "audio/wav")

        files = {
            "file": (f"audio.{file_format}", audio_data, mime_type)
        }

        data: Dict[str, Any] = {
            "model": self._config.model,
            "response_format": response_format,
            "temperature": str(temperature),
        }

        if language:
            data["language"] = language

        if prompt:
            data["prompt"] = prompt

        # Retry loop
        last_error: Optional[Exception] = None
        retry_delay = self._config.retry_delay

        for attempt in range(self._config.max_retries):
            try:
                response = self._sync_client.post(
                    self.api_endpoint,
                    headers=self._get_headers(),
                    files=files,
                    data=data
                )

                if response.status_code == 200:
                    return self._parse_response(response, response_format)

                elif response.status_code == 401:
                    raise APIKeyError("Invalid API key")

                elif response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    retry_seconds = float(retry_after) if retry_after else retry_delay
                    time.sleep(retry_seconds)
                    continue

                elif response.status_code >= 500:
                    last_error = TranscriptionError(
                        f"Server error: {response.status_code}"
                    )

                else:
                    error_detail = self._extract_error(response)
                    raise TranscriptionError(f"API error: {error_detail}")

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_error = NetworkError(f"Network error: {str(e)}")

            except (APIKeyError, AudioFormatError):
                raise

            except TranscriptionError:
                raise

            except Exception as e:
                last_error = TranscriptionError(f"Unexpected error: {str(e)}")

            # Wait before retry
            if attempt < self._config.max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= self._config.retry_multiplier

        raise last_error or TranscriptionError("Transcription failed after retries")

    def _parse_response(
            self,
            response: httpx.Response,
            response_format: str
    ) -> TranscriptionResult:
        """
        Parse API response into TranscriptionResult.

        Args:
            response: HTTP response object.
            response_format: Expected format (json, text, etc.).

        Returns:
            TranscriptionResult with parsed data.
        """
        if response_format == "json":
            data = response.json()
            return TranscriptionResult(
                text=data.get("text", ""),
                language=data.get("language"),
                duration=data.get("duration"),
                status=TranscriptionStatus.COMPLETED,
                raw_response=data
            )
        else:
            # text, srt, vtt formats
            return TranscriptionResult(
                text=response.text,
                status=TranscriptionStatus.COMPLETED
            )

    def _extract_error(self, response: httpx.Response) -> str:
        """
        Extract error message from API response.

        Args:
            response: HTTP response object.

        Returns:
            Error message string.
        """
        try:
            data = response.json()
            if "error" in data:
                error = data["error"]
                if isinstance(error, dict):
                    return error.get("message", str(error))
                return str(error)
        except Exception:
            pass

        return f"HTTP {response.status_code}: {response.text[:200]}"

    async def check_api_key(self) -> bool:
        """
        Verify that the API key is valid.

        Returns:
            True if API key is valid.
        """
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)

        try:
            # Try to access models endpoint to verify key
            response = await self._client.get(
                f"{self._config.base_url}/models",
                headers=self._get_headers()
            )
            return response.status_code == 200
        except Exception:
            return False

    def check_api_key_sync(self) -> bool:
        """
        Verify that the API key is valid (synchronous).

        Returns:
            True if API key is valid.
        """
        if self._sync_client is None:
            self._sync_client = httpx.Client(timeout=10.0)

        try:
            response = self._sync_client.get(
                f"{self._config.base_url}/models",
                headers=self._get_headers()
            )
            return response.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        """Close async HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def close_sync(self) -> None:
        """Close sync HTTP client."""
        if self._sync_client is not None:
            self._sync_client.close()
            self._sync_client = None

    async def __aenter__(self) -> 'WhisperService':
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    def __enter__(self) -> 'WhisperService':
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close_sync()


# Convenience function for one-off transcriptions
async def transcribe_audio(
        audio_data: bytes,
        api_key: str,
        language: Optional[str] = None,
        **kwargs
) -> str:
    """
    Convenience function to transcribe audio with minimal setup.

    Args:
        audio_data: Audio bytes to transcribe.
        api_key: OpenAI API key.
        language: Optional language code.
        **kwargs: Additional arguments for transcribe_async.

    Returns:
        Transcribed text string.
    """
    async with WhisperService(api_key=api_key) as service:
        result = await service.transcribe_async(
            audio_data,
            language=language,
            **kwargs
        )
        return result.text


if __name__ == "__main__":
    # Demo/test code
    import os

    print("Whisper Service Demo")
    print("-" * 40)

    api_key = os.environ.get("OPENAI_API_KEY", "")

    if not api_key:
        print("Set OPENAI_API_KEY environment variable to test")
        print("\nExample usage:")
        print("""
    from whisper_service import WhisperService

    service = WhisperService(api_key="sk-...")

    # Async usage
    result = await service.transcribe_async(audio_bytes, language="en")
    print(result.text)

    # Sync usage
    result = service.transcribe(audio_bytes)
    print(result.text)
        """)
    else:
        # Test API key validity
        service = WhisperService(api_key=api_key)
        valid = service.check_api_key_sync()
        print(f"API Key valid: {valid}")
        service.close_sync()
