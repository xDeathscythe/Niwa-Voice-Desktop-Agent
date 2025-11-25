"""
Text Cleaner Module for VoiceType Application.

Uses OpenAI GPT API to clean and correct transcribed text.
Handles grammar correction, filler word removal, and text normalization.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import time
import httpx

# Configure logging
logger = logging.getLogger(__name__)


# System prompts for different cleaning modes
SYSTEM_PROMPTS = {
    "default": """Transkribuj sledeći glasovni unos u jasan, gramatički ispravan tekst na jeziku korisnika.
Ignoriši poštapalice, ponavljanja, nepotrebne uzvične reči i zvuke.
Ispravi očigledne greške u izgovoru.
Ne menjaj smisao rečenica.
Ukloni sve nepotrebne pauze i duple reči.
Sačuvaj ton i stil govora korisnika.""",

    "formal": """Pretvori sledeći glasovni unos u formalan, profesionalan tekst.
Ukloni sve poštapalice, ponavljanja i nepotrebne reči.
Koristi formalan stil i gramatički ispravne rečenice.
Zadrži suštinu poruke ali je formuliši profesionalno.
Ispravni sve greške u izgovoru i transkripciji.""",

    "casual": """Pretvori sledeći glasovni unos u čist, čitljiv tekst zadržavajući opušten ton.
Ukloni samo očigledne greške i ponavljanja.
Zadrži prirodan govorni stil korisnika.
Minimalno menjaj originalni tekst - samo očisti nepotrebne zvuke i pauze.""",

    "minimal": """Očisti sledeći tekst minimalno:
- Ukloni samo "um", "uh", "znači", "kao" i slične poštapalice
- Ukloni duple reči
- Ispravi samo očigledne greške
Ne menjaj strukturu rečenica ni stil.""",

    "english": """Clean up the following voice transcription:
- Remove filler words (um, uh, like, you know)
- Fix grammar and punctuation
- Remove repetitions and false starts
- Preserve the speaker's intended meaning and tone
- Do not add or change the core content""",
}


class CleaningMode(Enum):
    """Available text cleaning modes."""
    DEFAULT = "default"
    FORMAL = "formal"
    CASUAL = "casual"
    MINIMAL = "minimal"
    ENGLISH = "english"


class TextCleanerError(Exception):
    """Base exception for text cleaner errors."""
    pass


class APIError(TextCleanerError):
    """Raised for API-related errors."""
    pass


class RateLimitError(TextCleanerError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str, retry_after: Optional[float] = None):
        super().__init__(message)
        self.retry_after = retry_after


@dataclass
class CleaningResult:
    """Result of text cleaning operation."""
    original_text: str
    cleaned_text: str
    language: Optional[str] = None
    mode: CleaningMode = CleaningMode.DEFAULT
    tokens_used: int = 0
    success: bool = True
    error: Optional[str] = None


@dataclass
class TextCleanerConfig:
    """Configuration for text cleaner service."""
    api_key: str
    model: str = "gpt-4o-mini"  # Cost-effective and fast
    base_url: str = "https://api.openai.com/v1"
    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 1.0
    max_input_length: int = 4000  # characters
    temperature: float = 0.3  # Lower for more consistent output


class TextCleaner:
    """
    Service for cleaning transcribed text using OpenAI GPT API.

    Features:
    - Grammar and punctuation correction
    - Filler word removal
    - Multiple cleaning modes (formal, casual, minimal)
    - Multi-language support
    - Custom system prompts

    Thread-safe implementation.

    Example:
        cleaner = TextCleaner(api_key="sk-...")
        result = await cleaner.clean_async(
            "znači ovaj um tekst je kao nekako loš",
            mode=CleaningMode.DEFAULT
        )
        print(result.cleaned_text)  # "Ovaj tekst je nekako loš."
    """

    def __init__(
            self,
            api_key: Optional[str] = None,
            config: Optional[TextCleanerConfig] = None
    ):
        """
        Initialize the text cleaner.

        Args:
            api_key: OpenAI API key.
            config: Optional configuration object.

        Raises:
            TextCleanerError: If no API key is provided.
        """
        if config is not None:
            self._config = config
        elif api_key is not None:
            self._config = TextCleanerConfig(api_key=api_key)
        else:
            raise TextCleanerError("API key must be provided")

        if not self._config.api_key:
            raise TextCleanerError("API key cannot be empty")

        self._client: Optional[httpx.AsyncClient] = None
        self._sync_client: Optional[httpx.Client] = None

        # Custom system prompts
        self._custom_prompts: Dict[str, str] = {}

    @property
    def api_endpoint(self) -> str:
        """Get the chat completions API endpoint."""
        return f"{self._config.base_url}/chat/completions"

    def set_api_key(self, api_key: str) -> None:
        """Update the API key."""
        if not api_key:
            raise TextCleanerError("API key cannot be empty")
        self._config.api_key = api_key

    def set_model(self, model: str) -> None:
        """
        Set the GPT model to use.

        Args:
            model: Model identifier (e.g., "gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo").
        """
        self._config.model = model

    def add_custom_prompt(self, name: str, prompt: str) -> None:
        """
        Add a custom system prompt for text cleaning.

        Args:
            name: Unique name for the prompt.
            prompt: System prompt text.
        """
        self._custom_prompts[name] = prompt

    def get_system_prompt(
            self,
            mode: CleaningMode,
            language: Optional[str] = None,
            custom_prompt: Optional[str] = None
    ) -> str:
        """
        Get the system prompt for a cleaning mode.

        Args:
            mode: Cleaning mode.
            language: Optional language hint.
            custom_prompt: Custom prompt name or text.

        Returns:
            System prompt string.
        """
        if custom_prompt:
            # Check if it's a registered custom prompt name
            if custom_prompt in self._custom_prompts:
                return self._custom_prompts[custom_prompt]
            # Otherwise use as direct prompt
            return custom_prompt

        base_prompt = SYSTEM_PROMPTS.get(mode.value, SYSTEM_PROMPTS["default"])

        # Add language hint if provided
        if language:
            language_hint = f"\nJezik teksta: {language}"
            base_prompt += language_hint

        return base_prompt

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        return {
            "Authorization": f"Bearer {self._config.api_key}",
            "Content-Type": "application/json",
        }

    def _validate_input(self, text: str) -> None:
        """
        Validate input text.

        Args:
            text: Text to validate.

        Raises:
            TextCleanerError: If text is invalid.
        """
        if not text or not text.strip():
            raise TextCleanerError("Input text is empty")

        if len(text) > self._config.max_input_length:
            raise TextCleanerError(
                f"Text too long: {len(text)} chars "
                f"(max: {self._config.max_input_length})"
            )

    async def clean_async(
            self,
            text: str,
            mode: CleaningMode = CleaningMode.DEFAULT,
            language: Optional[str] = None,
            custom_prompt: Optional[str] = None
    ) -> CleaningResult:
        """
        Clean text asynchronously using GPT API.

        Args:
            text: Text to clean.
            mode: Cleaning mode to use.
            language: Optional language code/name.
            custom_prompt: Optional custom prompt name or text.

        Returns:
            CleaningResult with cleaned text.

        Raises:
            APIError: For API errors.
            RateLimitError: If rate limit exceeded.
            TextCleanerError: For other errors.
        """
        self._validate_input(text)

        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._config.timeout)

        system_prompt = self.get_system_prompt(mode, language, custom_prompt)

        request_body = {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            "temperature": self._config.temperature,
            "max_tokens": min(len(text) * 2, 2000),  # Allow some expansion
        }

        # Retry loop with exponential backoff
        last_error: Optional[Exception] = None
        retry_delay = self._config.retry_delay

        for attempt in range(self._config.max_retries):
            try:
                response = await self._client.post(
                    self.api_endpoint,
                    headers=self._get_headers(),
                    json=request_body
                )

                if response.status_code == 200:
                    return self._parse_response(response, text, mode, language)

                elif response.status_code == 401:
                    raise APIError("Invalid API key")

                elif response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    retry_seconds = float(retry_after) if retry_after else retry_delay
                    raise RateLimitError("Rate limit exceeded", retry_after=retry_seconds)

                elif response.status_code >= 500:
                    last_error = APIError(f"Server error: {response.status_code}")

                else:
                    error_detail = self._extract_error(response)
                    raise APIError(f"API error: {error_detail}")

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_error = APIError(f"Network error: {str(e)}")

            except RateLimitError as e:
                if e.retry_after:
                    await asyncio.sleep(e.retry_after)
                    continue
                last_error = e

            except APIError:
                raise

            except Exception as e:
                last_error = TextCleanerError(f"Unexpected error: {str(e)}")

            # Wait before retry
            if attempt < self._config.max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff

        # All retries failed - return original text with error
        return CleaningResult(
            original_text=text,
            cleaned_text=text,  # Return original on failure
            mode=mode,
            language=language,
            success=False,
            error=str(last_error) if last_error else "Unknown error"
        )

    def clean(
            self,
            text: str,
            mode: CleaningMode = CleaningMode.DEFAULT,
            language: Optional[str] = None,
            custom_prompt: Optional[str] = None
    ) -> CleaningResult:
        """
        Clean text synchronously using GPT API.

        Args:
            text: Text to clean.
            mode: Cleaning mode to use.
            language: Optional language code/name.
            custom_prompt: Optional custom prompt.

        Returns:
            CleaningResult with cleaned text.
        """
        self._validate_input(text)

        if self._sync_client is None:
            self._sync_client = httpx.Client(timeout=self._config.timeout)

        system_prompt = self.get_system_prompt(mode, language, custom_prompt)

        request_body = {
            "model": self._config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            "temperature": self._config.temperature,
            "max_tokens": min(len(text) * 2, 2000),
        }

        last_error: Optional[Exception] = None
        retry_delay = self._config.retry_delay

        for attempt in range(self._config.max_retries):
            try:
                response = self._sync_client.post(
                    self.api_endpoint,
                    headers=self._get_headers(),
                    json=request_body
                )

                if response.status_code == 200:
                    return self._parse_response(response, text, mode, language)

                elif response.status_code == 401:
                    raise APIError("Invalid API key")

                elif response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    retry_seconds = float(retry_after) if retry_after else retry_delay
                    time.sleep(retry_seconds)
                    continue

                elif response.status_code >= 500:
                    last_error = APIError(f"Server error: {response.status_code}")

                else:
                    error_detail = self._extract_error(response)
                    raise APIError(f"API error: {error_detail}")

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                last_error = APIError(f"Network error: {str(e)}")

            except APIError:
                raise

            except Exception as e:
                last_error = TextCleanerError(f"Unexpected error: {str(e)}")

            if attempt < self._config.max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2

        return CleaningResult(
            original_text=text,
            cleaned_text=text,
            mode=mode,
            language=language,
            success=False,
            error=str(last_error) if last_error else "Unknown error"
        )

    def _parse_response(
            self,
            response: httpx.Response,
            original_text: str,
            mode: CleaningMode,
            language: Optional[str]
    ) -> CleaningResult:
        """
        Parse API response into CleaningResult.

        Args:
            response: HTTP response.
            original_text: Original input text.
            mode: Cleaning mode used.
            language: Language used.

        Returns:
            CleaningResult with cleaned text.
        """
        data = response.json()

        cleaned_text = ""
        tokens_used = 0

        if "choices" in data and len(data["choices"]) > 0:
            message = data["choices"][0].get("message", {})
            cleaned_text = message.get("content", "").strip()

        if "usage" in data:
            tokens_used = data["usage"].get("total_tokens", 0)

        # If cleaning returned empty, use original
        if not cleaned_text:
            cleaned_text = original_text

        return CleaningResult(
            original_text=original_text,
            cleaned_text=cleaned_text,
            mode=mode,
            language=language,
            tokens_used=tokens_used,
            success=True
        )

    def _extract_error(self, response: httpx.Response) -> str:
        """Extract error message from API response."""
        try:
            data = response.json()
            if "error" in data:
                error = data["error"]
                if isinstance(error, dict):
                    return error.get("message", str(error))
                return str(error)
        except Exception:
            pass
        return f"HTTP {response.status_code}"

    async def clean_batch_async(
            self,
            texts: List[str],
            mode: CleaningMode = CleaningMode.DEFAULT,
            language: Optional[str] = None
    ) -> List[CleaningResult]:
        """
        Clean multiple texts asynchronously.

        Args:
            texts: List of texts to clean.
            mode: Cleaning mode.
            language: Language code.

        Returns:
            List of CleaningResults.
        """
        tasks = [
            self.clean_async(text, mode, language)
            for text in texts
        ]
        return await asyncio.gather(*tasks)

    def is_enabled(self) -> bool:
        """Check if text cleaning is enabled (has valid API key)."""
        return bool(self._config.api_key)

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

    async def __aenter__(self) -> 'TextCleaner':
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()

    def __enter__(self) -> 'TextCleaner':
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close_sync()


# Language-specific prompt generators
def get_language_specific_prompt(language_code: str) -> str:
    """
    Get a language-specific cleaning prompt.

    Args:
        language_code: ISO 639-1 language code.

    Returns:
        System prompt optimized for the language.
    """
    prompts = {
        "sr": """Očisti sledeći srpski tekst transkribovan iz govora:
- Ukloni poštapalice (znači, kao, ovaj, onaj, jel'te)
- Ispravi gramatiku i interpunkciju
- Ukloni ponavljanja reči
- Zadrži izvorni smisao i ton""",

        "hr": """Očisti sljedeći hrvatski tekst transkribiran iz govora:
- Ukloni poštapalice (znači, kao, ovaj, onaj)
- Ispravi gramatiku i interpunkciju
- Ukloni ponavljanja riječi
- Zadrži izvorni smisao i ton""",

        "bs": """Očisti sljedeći bosanski tekst transkribiran iz govora:
- Ukloni poštapalice (znači, kao, ovaj, onaj)
- Ispravi gramatiku i interpunkciju
- Ukloni ponavljanja riječi
- Zadrži izvorni smisao i ton""",

        "en": """Clean up the following English transcription:
- Remove filler words (um, uh, like, you know, basically)
- Fix grammar and punctuation
- Remove word repetitions
- Preserve original meaning and tone""",

        "de": """Bereinige die folgende deutsche Transkription:
- Entferne Füllwörter (äh, ähm, also, halt, sozusagen)
- Korrigiere Grammatik und Zeichensetzung
- Entferne Wortwiederholungen
- Behalte die ursprüngliche Bedeutung und den Ton bei""",

        "fr": """Nettoie la transcription française suivante:
- Supprime les mots de remplissage (euh, ben, genre, en fait)
- Corrige la grammaire et la ponctuation
- Supprime les répétitions de mots
- Préserve le sens et le ton d'origine""",

        "es": """Limpia la siguiente transcripción en español:
- Elimina muletillas (eh, pues, o sea, bueno)
- Corrige la gramática y la puntuación
- Elimina repeticiones de palabras
- Conserva el significado y tono originales""",

        "it": """Pulisci la seguente trascrizione italiana:
- Rimuovi le parole riempitive (eh, cioè, tipo, allora)
- Correggi grammatica e punteggiatura
- Rimuovi ripetizioni di parole
- Mantieni significato e tono originali""",

        "ru": """Очисти следующую русскую транскрипцию:
- Убери слова-паразиты (ну, это, как бы, типа, вот)
- Исправь грамматику и пунктуацию
- Убери повторы слов
- Сохрани исходный смысл и тон""",

        "pl": """Oczyść następującą polską transkrypcję:
- Usuń słowa wypełniające (no, znaczy, jakby, wiesz)
- Popraw gramatykę i interpunkcję
- Usuń powtórzenia słów
- Zachowaj oryginalne znaczenie i ton""",
    }

    return prompts.get(language_code, SYSTEM_PROMPTS["default"])


if __name__ == "__main__":
    import os

    print("Text Cleaner Demo")
    print("-" * 40)

    api_key = os.environ.get("OPENAI_API_KEY", "")

    if not api_key:
        print("Set OPENAI_API_KEY environment variable to test")
        print("\nExample usage:")
        print("""
    from text_cleaner import TextCleaner, CleaningMode

    cleaner = TextCleaner(api_key="sk-...")

    # Clean transcribed text
    result = cleaner.clean(
        "znači ovaj um tekst je kao nekako loš",
        mode=CleaningMode.DEFAULT
    )
    print(result.cleaned_text)

    # Different modes
    formal = cleaner.clean(text, mode=CleaningMode.FORMAL)
    casual = cleaner.clean(text, mode=CleaningMode.CASUAL)
        """)
    else:
        print("Testing text cleaner...")
        cleaner = TextCleaner(api_key=api_key)

        test_text = "znači ovaj um tekst je kao nekako loš loš i treba ga ispraviti jel"

        print(f"\nOriginal: {test_text}")

        result = cleaner.clean(test_text, mode=CleaningMode.DEFAULT, language="sr")

        if result.success:
            print(f"Cleaned:  {result.cleaned_text}")
            print(f"Tokens:   {result.tokens_used}")
        else:
            print(f"Error: {result.error}")

        cleaner.close_sync()
