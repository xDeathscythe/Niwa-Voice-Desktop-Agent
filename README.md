# Niwa Ai Voice Input

**Voice to Text, Instantly** - Besplatna alternativa za WisprFlow

Niwa Ai Voice Input je Windows desktop aplikacija za glasovnu transkripciju koja koristi OpenAI Whisper API za pretvaranje govora u tekst, uz opcionalnu AI obradu za ciscenje gramatike.

## Funkcionalnosti

- **Globalni hotkey** (default: `Ctrl+T`) - radi u bilo kojoj aplikaciji
- **OpenAI Whisper** transkripcija sa podrskom za 50+ jezika
- **AI ciscenje teksta** - uklanja postapalice, ispravlja gramatiku
- **Floating pill overlay** - vizuelni indikator statusa
- **Auto-paste** - tekst se automatski kopira/lepi
- **Moderan dark UI** - elegantan interfejs

## Instalacija

### 1. Otvori projekat

```bash
cd "C:\Users\alnen\Desktop\Niwa Ai Voice imput"
```

### 2. Instaliraj dependencies

```bash
pip install -r requirements.txt
```

### 3. Pokreni aplikaciju

```bash
python run.py
```

## Konfiguracija

### OpenAI API Key

1. Idi na https://platform.openai.com/api-keys
2. Kreiraj novi API key
3. Unesi key u aplikaciju preko Settings prozora

### Podesavanja

- **Microphone** - izaberi ulazni audio uredaj
- **Language** - izaberi jezik za transkripciju (ili auto-detect)
- **Hotkey** - promeni precicu (default: Ctrl+T)
- **AI Cleanup** - ukljuci/iskljuci GPT ciscenje teksta

## Koriscenje

1. Pokreni aplikaciju
2. Unesi OpenAI API key
3. Klikni "Start"
4. Pritisni `Ctrl+T` da zapocnes snimanje
5. Govori
6. Pritisni `Ctrl+T` ponovo da zavrsis
7. Tekst ce biti automatski nalepljen

## Floating Pill

Mali "pill" indikator se prikazuje na dnu ekrana:
- **Zelen** - aplikacija je spremna
- **Crven (animiran)** - snima se
- **Spinner** - transkribuje se
- **Checkmark** - tekst kopiran!

## Podrzani jezici

Whisper podrzava 50+ jezika ukljucujuci:
- Srpski, Hrvatski, Bosanski
- Engleski, Nemacki, Francuski
- I mnoge druge...

## System Prompt za AI Cleanup

Kada je ukljuceno AI ciscenje, GPT ce:
- Ukloniti postapalice (hmm, aaa, znaci, ovaj...)
- Ispraviti gramaticke greske
- Formatirati recenice
- Zadrzati originalni smisao

## Struktura Projekta

```
Niwa Ai Voice Input/
├── src/
│   ├── core/           # Event bus, State machine
│   ├── services/       # Audio, Transcription, Hotkey
│   ├── ui/             # MainWindow, FloatingPill
│   └── app.py          # Orchestrator
├── requirements.txt
├── run.py              # Entry point
└── README.md
```

## Troubleshooting

### "No microphone found"
- Proveri da li je mikrofon povezan
- Proveri Windows podesavanja zvuka

### "API key invalid"
- Proveri da key pocinje sa `sk-`
- Proveri da imas kredit na OpenAI nalogu

### Hotkey ne radi
- Proveri da aplikacija radi (pill je vidljiv)
- Pokusaj drugu kombinaciju tastera

## Build (Executable)

Za kreiranje standalone .exe fajla:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=resources/icons/app_icon.ico run.py
```

## Licenca

MIT License - koristi slobodno!

## Credits

- OpenAI Whisper - Speech to Text
- OpenAI GPT - Text Cleanup
- CustomTkinter - Modern UI
