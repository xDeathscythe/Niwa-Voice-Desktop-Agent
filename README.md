# Niwa Voice Desktop Agent

AI-powered voice assistant desktop application with wake word detection, built with Electron, React, TypeScript, and Google Gemini.

## Features

- **Wake Word Detection**: Activates on "Porcupine" (for voice commands) and "Bumblebee" (for dictation mode)
- **Google Gemini Live Integration**: Real-time voice conversation with Gemini 2.0 Flash
- **Vision Service**: Screen analysis to find input fields using Gemini 1.5 Pro
- **Transparent Floating UI**: Always-on-top, minimal interface with state indicators

## Prerequisites

- Node.js 18+ and npm
- Picovoice Access Key (for wake word detection)
- Google API Key (for Gemini services)

## Setup

### 1. Install Dependencies

```bash
npm install
```

### 2. Configure Environment Variables

Copy the example environment file and fill in your API keys:

```bash
cp .env.example .env
```

Edit `.env` and add your keys:

```env
VITE_PICOVOICE_ACCESS_KEY=your_picovoice_access_key_here
VITE_GOOGLE_API_KEY=your_google_api_key_here
```

**Getting API Keys:**
- **Picovoice Access Key**: Sign up at [https://console.picovoice.ai/](https://console.picovoice.ai/)
- **Google API Key**: Create one at [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)

## Development

### Run in Development Mode

```bash
npm run dev:electron
```

This starts both the Vite dev server and Electron window.

### Run Vite Dev Server Only

```bash
npm run dev
```

## Building

### Build for Production

```bash
npm run build
```

This will:
1. Compile TypeScript
2. Build React app with Vite
3. Package Electron app with electron-builder

Output will be in the `release/` directory.

## Project Structure

```
├── electron/              # Electron main process
│   ├── main.ts           # Main process entry point
│   ├── preload.ts        # IPC bridge
│   └── services/         # Backend services
│       ├── gemini.ts     # Gemini Live API integration
│       ├── vision.ts     # Screen analysis service
│       └── wakeWord.ts   # Wake word detection
├── src/                  # React renderer process
│   ├── App.tsx          # Main UI component
│   └── main.tsx         # React entry point
├── public/              # Static assets
└── dist/                # Build output (generated)
```

## Usage

### Wake Words

- **"Porcupine"**: Activates voice conversation mode with Gemini
- **"Bumblebee"**: Activates dictation mode (analyzes screen to find input field)

### Manual Triggers

Hover over the application window to reveal manual trigger buttons.

### State Indicators

The floating orb changes color based on state:
- **Purple**: IDLE
- **Green**: LISTENING
- **Yellow**: THINKING
- **Blue**: SPEAKING

## Troubleshooting

### Build Warnings

If you see module type warnings, ensure `package.json` has `"type": "module"`.

### API Keys Not Working

1. Verify keys are correctly set in `.env`
2. Restart the application after updating `.env`
3. Check console logs for specific error messages

### Audio Issues

- Ensure microphone permissions are granted
- Check that your default audio input device is working
- Verify Picovoice Access Key is valid

## Technologies Used

- **Electron 39**: Cross-platform desktop application framework
- **React 19**: UI library
- **TypeScript**: Type-safe development
- **Vite**: Fast build tool and dev server
- **Tailwind CSS**: Utility-first styling
- **Porcupine**: Wake word detection engine
- **Google Gemini**: AI conversation and vision services

## License

Private project
