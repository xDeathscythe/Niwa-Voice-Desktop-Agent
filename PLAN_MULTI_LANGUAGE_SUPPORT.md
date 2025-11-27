# Plan: Multi-Language Support za Niwa AI Voice Input

## Problem

Trenutna implementacija ima sledece probleme:

1. **Jezik se ne koristi pravilno** - `app.py` ignoriše language setting i uvek koristi auto-detect
2. **LLM cleanup prompt je statičan** - Ne zna koji jezik korisnik koristi
3. **Nema podrške za više jezika** - Korisnik može izabrati samo 1 jezik
4. **Nema prepoznavanja engleskih izraza** - Kad pričaš srpski sa engleskim tehničkim terminima, može doći do grešaka

## Rešenje

### Arhitektura

```
User speaks (Serbian + English terms)
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Whisper API                                            │
│  - language hint: "sr" (primary)                        │
│  - prompt: uključuje kontekst o code-switching          │
└─────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  LLM Cleanup                                            │
│  - Dynamic prompt based on user languages               │
│  - Knows to preserve English technical terms            │
│  - Output in primary language                           │
└─────────────────────────────────────────────────────────┘
         │
         ▼
    Final Text
```

---

## Faza 1: Settings Service Update

### 1.1 Novi Settings Model

**Fajl:** `src/services/settings_service.py`

```python
@dataclass
class LanguageSettings:
    """Language configuration."""
    primary_language: str = "auto"  # Glavni jezik (ISO 639-1)
    additional_languages: List[str] = field(default_factory=list)  # Max 4 dodatna
    always_recognize_english: bool = True  # Uvek prepoznaj engleske izraze
```

**Promene:**
- Dodati `LanguageSettings` dataclass
- Dodati u `AppSettings`
- Dodati helper metode: `get_all_languages()`, `get_primary_language()`

### 1.2 Migracija starih settings

- Ako postoji `transcription.language` → migriraj u `language.primary_language`
- Default: `always_recognize_english = True`

---

## Faza 2: Transcription Service Update

### 2.1 Dynamic Whisper Prompt

**Fajl:** `src/services/transcription_service.py`

Umesto:
```python
kwargs["prompt"] = "This is a transcription of natural speech..."
```

Novi pristup:
```python
def _build_whisper_prompt(self, languages: List[str]) -> str:
    """Build contextual prompt for Whisper based on user languages."""

    if not languages or languages == ["auto"]:
        return "Transcribe naturally. Preserve any technical terms exactly as spoken."

    primary = languages[0]
    lang_names = [LANGUAGE_NAMES.get(l, l) for l in languages]

    if len(languages) == 1:
        return f"Transcribe in {lang_names[0]}. Preserve English technical terms exactly."
    else:
        return f"Transcribe in {lang_names[0]}. The speaker may use terms from: {', '.join(lang_names[1:])} and English. Preserve technical terms exactly."
```

### 2.2 Dynamic LLM Cleanup Prompt

**Fajl:** `src/services/transcription_service.py` (ili novi `prompt_builder.py`)

```python
def build_cleanup_prompt(
    primary_language: str,
    additional_languages: List[str],
    preserve_english: bool = True
) -> str:
    """
    Build dynamic cleanup prompt based on user's language preferences.
    """
    lang_name = LANGUAGE_NAMES.get(primary_language, primary_language)

    prompt = f"""Clean up this voice transcription. The text is primarily in {lang_name}.

Rules:
1. Remove filler words (um, uh, znači, ovaj, kao, mislim, etc.)
2. Fix grammar and spelling errors in {lang_name}
3. Preserve the FULL content - do not shorten or summarize
4. Keep the same tone and style as the speaker
"""

    if preserve_english:
        prompt += """
5. IMPORTANT: Preserve English technical terms EXACTLY as spoken
   - Programming terms: function, class, variable, API, etc.
   - Product names: GitHub, Docker, React, etc.
   - Do NOT translate these to {lang_name}
"""

    if additional_languages:
        other_langs = [LANGUAGE_NAMES.get(l, l) for l in additional_languages]
        prompt += f"""
6. The speaker may also use words from: {', '.join(other_langs)}
   - Preserve these naturally, do not force translation
"""

    prompt += """
Return ONLY the cleaned text, no explanations."""

    return prompt
```

---

## Faza 3: App.py Integration

### 3.1 Whisper API Call Update

**Fajl:** `src/app.py` - `_process_audio()` metoda

Promene:
```python
# Get language settings
lang_settings = self._settings.get_all().language
primary_lang = lang_settings.primary_language
all_langs = [primary_lang] + lang_settings.additional_languages

# Build Whisper kwargs
kwargs = {
    "model": "whisper-1",
    "file": ("audio.wav", audio_data, "audio/wav"),
    "response_format": "text",
    "temperature": 0.0
}

# Set language hint (only if not auto)
if primary_lang and primary_lang != "auto":
    kwargs["language"] = primary_lang

# Build contextual prompt
kwargs["prompt"] = self._build_whisper_prompt(all_langs, lang_settings.always_recognize_english)
```

### 3.2 LLM Cleanup Call Update

**Fajl:** `src/app.py` - `_cleanup_text()` metoda

```python
def _cleanup_text(self, text: str) -> str:
    """Clean up text with language-aware prompt."""
    model = self._settings.get("transcription.cleanup_model", "gpt-4o-mini")
    if not model:
        return text

    # Get language settings
    lang_settings = self._settings.get_all().language

    # Build dynamic prompt
    system_prompt = build_cleanup_prompt(
        primary_language=lang_settings.primary_language,
        additional_languages=lang_settings.additional_languages,
        preserve_english=lang_settings.always_recognize_english
    )

    response = self._client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        temperature=0.1,
        max_tokens=4096
    )
    return response.choices[0].message.content.strip()
```

---

## Faza 4: UI Update

### 4.1 Language Selection Component

**Fajl:** `src/ui/main_window.py`

Nova sekcija u settings gridu:

```
┌─────────────────────────────────────────────────────────┐
│  Languages                                              │
│  ┌─────────────────┐  ┌─────────────────────────────┐   │
│  │ Primary: [▼ Sr] │  │ ☑ Always recognize English  │   │
│  └─────────────────┘  └─────────────────────────────┘   │
│                                                         │
│  Additional languages (up to 4):                        │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                   │
│  │ En ✕ │ │ Hr ✕ │ │ + Add│ │      │                   │
│  └──────┘ └──────┘ └──────┘ └──────┘                   │
└─────────────────────────────────────────────────────────┘
```

### 4.2 Implementacija

```python
def _create_language_section(self):
    """Create language settings section."""
    card = ctk.CTkFrame(self.left_panel, ...)

    # Header
    header = ctk.CTkLabel(card, text="Languages")

    # Primary language dropdown
    self.primary_lang_dropdown = ctk.CTkComboBox(
        card,
        values=["Auto-detect"] + [f"{name} ({code})" for code, name in COMMON_LANGUAGES],
        command=self._on_primary_language_change
    )

    # Always recognize English checkbox
    self.english_var = ctk.BooleanVar(value=True)
    english_check = ctk.CTkCheckBox(
        card,
        text="Always recognize English terms",
        variable=self.english_var
    )

    # Additional languages frame
    self.additional_langs_frame = ctk.CTkFrame(card)
    self._selected_additional_langs = []

    # Add language button
    self.add_lang_btn = ctk.CTkButton(
        card,
        text="+ Add Language",
        command=self._show_language_picker
    )
```

### 4.3 Language Picker Dialog

```python
class LanguagePickerDialog(ctk.CTkToplevel):
    """Dialog for selecting additional languages."""

    def __init__(self, parent, excluded_languages: List[str], on_select: Callable):
        # Searchable list of languages
        # Exclude already selected languages
        # Return selected language code
```

---

## Faza 5: Prompt Templates

### 5.1 Novi fajl: `src/services/prompt_templates.py`

```python
"""Prompt templates for different languages and scenarios."""

# Language-specific filler words to remove
FILLER_WORDS = {
    "sr": ["znači", "ovaj", "kao", "mislim", "ono", "pa", "jel", "bre", "ae"],
    "hr": ["znači", "ovaj", "kao", "mislim", "ono", "pa", "jel"],
    "en": ["um", "uh", "like", "you know", "basically", "actually", "literally"],
    "de": ["äh", "ähm", "also", "halt", "sozusagen", "quasi"],
    # ... more languages
}

# Common technical terms to preserve (always in English)
TECHNICAL_TERMS = [
    # Programming
    "function", "class", "variable", "method", "API", "REST", "HTTP",
    "database", "server", "client", "frontend", "backend", "fullstack",
    # Tools
    "Git", "GitHub", "Docker", "Kubernetes", "AWS", "Azure",
    # Frameworks
    "React", "Angular", "Vue", "Node", "Django", "Flask",
    # ... more
]

def get_cleanup_prompt(lang_code: str, additional_langs: List[str] = None) -> str:
    """Get cleanup prompt for specific language configuration."""
    # Implementation
```

---

## Faza 6: Testing

### 6.1 Test scenariji

1. **Čist srpski govor**
   - Input: "Zdravo, ovo je test transkripcije"
   - Expected: Čist srpski output

2. **Srpski sa engleskim terminima**
   - Input: "Treba da napravim novi API endpoint za authentication"
   - Expected: "Treba da napravim novi API endpoint za authentication" (očuvani engleski termini)

3. **Code-switching (Sr + En)**
   - Input: "Function vraća null umesto expected value"
   - Expected: "Function vraća null umesto expected value"

4. **Multi-language (Sr + Hr + En)**
   - Input: Mešavina sve tri
   - Expected: Prirodno očuvanje svih

### 6.2 Test file

**Fajl:** `tests/test_language_support.py`

```python
def test_serbian_with_english_terms():
    prompt = build_cleanup_prompt("sr", [], preserve_english=True)
    assert "English technical terms" in prompt
    assert "Serbian" in prompt or "sr" in prompt.lower()

def test_multi_language_prompt():
    prompt = build_cleanup_prompt("sr", ["en", "hr"], preserve_english=True)
    assert "Croatian" in prompt or "hr" in prompt.lower()
```

---

## Redosled Implementacije

| # | Task | Fajlovi | Procenjena kompleksnost |
|---|------|---------|------------------------|
| 1 | Settings model update | `settings_service.py` | Low |
| 2 | Prompt builder | `prompt_templates.py` (novi) | Medium |
| 3 | Transcription service update | `transcription_service.py` | Medium |
| 4 | App.py integration | `app.py` | Medium |
| 5 | UI - Primary language | `main_window.py` | Low |
| 6 | UI - Additional languages | `main_window.py` | Medium |
| 7 | UI - Language picker dialog | `language_picker.py` (novi) | Medium |
| 8 | Testing | `test_language_support.py` | Low |
| 9 | Settings migration | `settings_service.py` | Low |

---

## API Changes Summary

### Settings JSON (novo)

```json
{
  "language": {
    "primary_language": "sr",
    "additional_languages": ["en", "hr"],
    "always_recognize_english": true
  },
  "transcription": {
    "cleanup_model": "gpt-4o-mini",
    "use_cleanup": true
  }
}
```

### Whisper API Call

```python
# Before
kwargs = {"model": "whisper-1", "file": ..., "response_format": "text"}

# After
kwargs = {
    "model": "whisper-1",
    "file": ...,
    "response_format": "text",
    "language": "sr",  # Primary language hint
    "prompt": "Transcribe in Serbian. Preserve English technical terms exactly."
}
```

### LLM Cleanup Prompt

```python
# Before (hardcoded)
"Clean up the transcribed text while preserving the original language..."

# After (dynamic)
"""Clean up this voice transcription. The text is primarily in Serbian.

Rules:
1. Remove filler words (um, uh, znači, ovaj, kao, mislim, etc.)
2. Fix grammar and spelling errors in Serbian
3. Preserve the FULL content - do not shorten or summarize
4. Keep the same tone and style as the speaker
5. IMPORTANT: Preserve English technical terms EXACTLY as spoken
6. The speaker may also use words from: English, Croatian

Return ONLY the cleaned text, no explanations."""
```

---

## Napomene

1. **Backward compatibility** - Stari settings format će raditi (migracija)
2. **Performance** - Prompt building je brz, nema uticaja na latenciju
3. **UX** - "Always recognize English" je default ON jer većina developera koristi engleske termine
