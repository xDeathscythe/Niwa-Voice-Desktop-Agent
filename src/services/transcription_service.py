"""Transcription service using OpenAI Whisper and GPT for text cleanup."""

import logging
import time
from typing import Optional, Callable
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass

from openai import OpenAI
import httpx

from ..core.event_bus import EventBus, create_event
from ..core.events import EventType
from ..core.exceptions import (
    APIKeyMissingError,
    APIKeyInvalidError,
    APIRateLimitError,
    APIQuotaExceededError,
    APINetworkError,
    APITimeoutError,
    TranscriptionEmptyError,
    TranscriptionError
)

logger = logging.getLogger(__name__)


# System prompt for LLM text cleanup
LLM_CLEANUP_PROMPT = """Transkribuj sledeci glasovni unos u jasan, gramaticki ispravan tekst na jeziku korisnika.

Pravila:
1. Ignorisi postapalice, ponavljanja, nepotrebne uzvicne reci i zvuke (npr. 'hmm', 'aaa', 'znaci', 'ovaj', 'pa', 'mislim', 'ono', 'kao').

2. Ispravi ocigledne greske u izgovoru i napisi recenice tako da budu lako citljive.

3. Ne menjaj smisao recenica, ali slobodno preformulisi delove koji su nejasni ili nepotpuni.

4. Ukloni sve nepotrebne pauze, duple reci i neformalne umetke.

5. Ako je recenica nedovrsena ili nejasna, pokusaj da je zavrsis logicno, ali ne izmisljaj informacije.

6. Sacuvaj ton i stil govora korisnika, ali prioritet je jasnoća i preciznost.

7. Zadrzi format (npr. liste, nabrajanja) ako je ocigledno da korisnik to zeli.

VAZNO: Vrati SAMO ociscen tekst, bez objasnjenja ili komentara."""


# Supported languages for Whisper
SUPPORTED_LANGUAGES = {
    "auto": "Auto-detect",
    "sr": "Srpski (Serbian)",
    "hr": "Hrvatski (Croatian)",
    "bs": "Bosanski (Bosnian)",
    "en": "English",
    "de": "Deutsch (German)",
    "fr": "Francais (French)",
    "es": "Espanol (Spanish)",
    "it": "Italiano (Italian)",
    "pt": "Portugues (Portuguese)",
    "ru": "Russkiy (Russian)",
    "pl": "Polski (Polish)",
    "cs": "Cestina (Czech)",
    "sk": "Slovencina (Slovak)",
    "sl": "Slovenscina (Slovenian)",
    "uk": "Ukrainska (Ukrainian)",
    "bg": "Balgarski (Bulgarian)",
    "mk": "Makedonski (Macedonian)",
    "ro": "Romana (Romanian)",
    "hu": "Magyar (Hungarian)",
    "tr": "Turkce (Turkish)",
    "nl": "Nederlands (Dutch)",
    "sv": "Svenska (Swedish)",
    "da": "Dansk (Danish)",
    "no": "Norsk (Norwegian)",
    "fi": "Suomi (Finnish)",
    "el": "Ellinika (Greek)",
    "he": "Ivrit (Hebrew)",
    "ar": "Al-Arabiya (Arabic)",
    "hi": "Hindi",
    "ja": "Nihongo (Japanese)",
    "ko": "Hangugeo (Korean)",
    "zh": "Zhongwen (Chinese)",
    "th": "Thai",
    "vi": "Tieng Viet (Vietnamese)",
    "id": "Bahasa Indonesia",
    "ms": "Bahasa Melayu (Malay)",
    "tl": "Tagalog (Filipino)",
    "sw": "Kiswahili (Swahili)",
    "af": "Afrikaans",
    "cy": "Cymraeg (Welsh)",
    "ga": "Gaeilge (Irish)",
    "eu": "Euskara (Basque)",
    "ca": "Catala (Catalan)",
    "gl": "Galego (Galician)",
    "is": "Islenska (Icelandic)",
    "lv": "Latviesu (Latvian)",
    "lt": "Lietuviu (Lithuanian)",
    "et": "Eesti (Estonian)",
    "mt": "Malti (Maltese)",
}


@dataclass
class TranscriptionResult:
    """Result of transcription."""
    raw_text: str
    cleaned_text: str
    language: str
    duration: float
    used_cleanup: bool


class TranscriptionService:
    """
    Transcription service using OpenAI Whisper and GPT.

    Features:
    - Audio transcription via Whisper API
    - Optional text cleanup via GPT
    - Async execution with thread pool
    - Retry logic for transient errors

    Usage:
        service = TranscriptionService(api_key="sk-...")
        result = service.transcribe(audio_bytes, language="sr")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        event_bus: Optional[EventBus] = None,
        use_cleanup: bool = True,
        cleanup_model: str = "gpt-4o-mini"
    ):
        """
        Initialize transcription service.

        Args:
            api_key: OpenAI API key
            event_bus: EventBus for transcription events
            use_cleanup: Whether to use LLM for text cleanup
            cleanup_model: Model to use for cleanup
        """
        self._api_key = api_key
        self._client: Optional[OpenAI] = None
        self._event_bus = event_bus or EventBus.get_instance()
        self._use_cleanup = use_cleanup
        self._cleanup_model = cleanup_model
        self._language = "auto"
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="transcription_")

        if api_key:
            self._init_client()

        logger.info("TranscriptionService initialized")

    def _init_client(self) -> None:
        """Initialize OpenAI client."""
        if not self._api_key:
            raise APIKeyMissingError()

        self._client = OpenAI(
            api_key=self._api_key,
            timeout=60.0,
            max_retries=0  # We handle retries ourselves
        )

    def set_api_key(self, api_key: str) -> None:
        """Update API key."""
        self._api_key = api_key
        self._init_client()
        logger.info("API key updated")

    def validate_api_key(self) -> bool:
        """
        Validate API key by making a test request.

        Returns:
            True if valid

        Raises:
            APIKeyInvalidError: If key is invalid
        """
        if not self._client:
            raise APIKeyMissingError()

        try:
            # Make minimal API call
            self._client.models.list()
            return True
        except Exception as e:
            error_str = str(e).lower()
            if "invalid" in error_str or "incorrect" in error_str:
                raise APIKeyInvalidError()
            raise

    def set_language(self, language: str) -> None:
        """
        Set transcription language.

        Args:
            language: ISO 639-1 code or "auto"
        """
        if language not in SUPPORTED_LANGUAGES and language != "auto":
            logger.warning(f"Unknown language: {language}, using auto-detect")
            language = "auto"

        self._language = language
        logger.info(f"Language set to: {language}")

    def set_use_cleanup(self, enabled: bool) -> None:
        """Enable/disable LLM text cleanup."""
        self._use_cleanup = enabled
        logger.info(f"LLM cleanup: {enabled}")

    def transcribe(
        self,
        audio_data: bytes,
        language: Optional[str] = None,
        use_cleanup: Optional[bool] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio synchronously.

        Args:
            audio_data: WAV audio bytes
            language: Override language (optional)
            use_cleanup: Override cleanup setting (optional)

        Returns:
            TranscriptionResult with raw and cleaned text

        Raises:
            Various API and transcription errors
        """
        if not self._client:
            raise APIKeyMissingError()

        lang = language or self._language
        cleanup = use_cleanup if use_cleanup is not None else self._use_cleanup

        self._event_bus.emit(EventType.TRANSCRIPTION_STARTED)
        start_time = time.time()

        try:
            # Step 1: Whisper transcription
            raw_text = self._call_whisper(audio_data, lang)

            if not raw_text or not raw_text.strip():
                raise TranscriptionEmptyError()

            # Step 2: LLM cleanup (optional)
            cleaned_text = raw_text
            if cleanup:
                self._event_bus.emit(EventType.LLM_PROCESSING_STARTED)
                try:
                    cleaned_text = self._call_cleanup(raw_text)
                    self._event_bus.emit(
                        EventType.LLM_PROCESSING_COMPLETE,
                        raw=raw_text,
                        cleaned=cleaned_text
                    )
                except Exception as e:
                    logger.warning(f"LLM cleanup failed, using raw text: {e}")
                    self._event_bus.emit(EventType.LLM_PROCESSING_FAILED, error=str(e))
                    cleaned_text = raw_text

            duration = time.time() - start_time

            result = TranscriptionResult(
                raw_text=raw_text,
                cleaned_text=cleaned_text,
                language=lang,
                duration=duration,
                used_cleanup=cleanup and (cleaned_text != raw_text)
            )

            self._event_bus.emit(
                EventType.TRANSCRIPTION_COMPLETE,
                text=cleaned_text,
                raw_text=raw_text,
                language=lang,
                duration=duration
            )

            logger.info(f"Transcription complete in {duration:.2f}s")
            return result

        except TranscriptionEmptyError:
            raise
        except Exception as e:
            self._event_bus.emit(EventType.TRANSCRIPTION_FAILED, error=str(e))
            raise

    def transcribe_async(
        self,
        audio_data: bytes,
        callback: Callable[[TranscriptionResult], None],
        error_callback: Optional[Callable[[Exception], None]] = None,
        language: Optional[str] = None,
        use_cleanup: Optional[bool] = None
    ) -> Future:
        """
        Transcribe audio asynchronously.

        Args:
            audio_data: WAV audio bytes
            callback: Called with result on success
            error_callback: Called with exception on failure
            language: Override language
            use_cleanup: Override cleanup setting

        Returns:
            Future for the transcription task
        """
        def task():
            try:
                result = self.transcribe(audio_data, language, use_cleanup)
                callback(result)
                return result
            except Exception as e:
                if error_callback:
                    error_callback(e)
                raise

        return self._executor.submit(task)

    def _call_whisper(self, audio_data: bytes, language: str) -> str:
        """Call Whisper API with retry logic."""
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                kwargs = {
                    "model": "whisper-1",
                    "file": ("audio.wav", audio_data, "audio/wav"),
                    "response_format": "text"
                }

                # Only set language if not auto-detect
                if language and language != "auto":
                    kwargs["language"] = language

                response = self._client.audio.transcriptions.create(**kwargs)

                # Handle different response types
                if isinstance(response, str):
                    return response.strip()
                return response.text.strip()

            except httpx.TimeoutException:
                last_error = APITimeoutError()
            except httpx.NetworkError as e:
                last_error = APINetworkError(e)
            except Exception as e:
                last_error = self._handle_api_error(e)
                if isinstance(last_error, (APIKeyInvalidError, APIQuotaExceededError)):
                    raise last_error

            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2
                logger.warning(f"Whisper API retry {attempt + 1}/{max_retries} in {wait_time}s")
                time.sleep(wait_time)

        raise last_error or TranscriptionError("Whisper API failed")

    def _call_cleanup(self, text: str) -> str:
        """Call GPT for text cleanup."""
        try:
            response = self._client.chat.completions.create(
                model=self._cleanup_model,
                messages=[
                    {"role": "system", "content": LLM_CLEANUP_PROMPT},
                    {"role": "user", "content": text}
                ],
                temperature=0.3,
                max_tokens=2048
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Cleanup API error: {e}")
            raise

    def _handle_api_error(self, error: Exception) -> Exception:
        """Convert API errors to our exception types."""
        error_str = str(error).lower()

        if "invalid_api_key" in error_str or "incorrect api key" in error_str:
            return APIKeyInvalidError()

        if "rate_limit" in error_str:
            return APIRateLimitError()

        if "quota" in error_str or "insufficient" in error_str:
            return APIQuotaExceededError()

        if isinstance(error, httpx.TimeoutException):
            return APITimeoutError()

        if isinstance(error, httpx.NetworkError):
            return APINetworkError(error)

        return TranscriptionError(str(error))

    def get_supported_languages(self) -> dict:
        """Get dictionary of supported languages."""
        return SUPPORTED_LANGUAGES.copy()

    def cleanup(self) -> None:
        """Clean up resources."""
        self._executor.shutdown(wait=False)
        logger.info("TranscriptionService cleaned up")
