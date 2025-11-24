# Niwa Voice Desktop Agent: Current Issues and Stabilization Steps

This document summarizes the main problems preventing the app from working reliably and recommends concrete fixes or setup steps to reach a functional state.

## Code-level blockers fixed in this branch
- **Renderer hidden while idle:** The React app returned `null` while the assistant was idle, so the window was empty and manual triggers were inaccessible. The UI now stays visible and shows a state label (Idle/Listening/Thinking/Speaking).
- **Preload path mismatch:** The Electron window attempted to load `preload.mjs`, but the Vite build emits `preload.js`. The preload file path is updated to match the built artifact, preventing missing-preload errors.

## Configuration and runtime requirements still outstanding
- **Required API keys:** The app only initializes wake-word detection and Gemini Live when both `VITE_PICOVOICE_ACCESS_KEY` and `VITE_GOOGLE_API_KEY` are present. Provide valid keys (e.g., in a `.env` file) before running.
- **Native audio dependencies:** Picovoice Porcupine and PvRecorder rely on microphone access and native bindings. Ensure the microphone works on the host and that the native modules rebuild successfully for the target platform.
- **Gemini Live model/endpoint stability:** The Gemini WebSocket endpoint and model name (`models/gemini-2.0-flash-exp`) may change. Verify the model is available to your API key and adjust if Google updates naming or access requirements.
- **Vision feature prerequisites:** Screen-capture permissions are needed for `desktopCapturer`. On macOS/Linux/Windows, grant screen-recording permissions to Electron; without them, vision analysis will fail silently.

## Build and packaging considerations
- **Electron download restrictions:** `electron-builder` currently fails to download Electron binaries (HTTP 403 from GitHub). Use a machine with unrestricted GitHub access, configure a download mirror (`ELECTRON_MIRROR`), or pre-cache Electron artifacts to allow packaging.
- **Package metadata:** `electron-builder` warns that `description` and `author` are missing in `package.json`. Add these fields to produce a polished installer.

## Recommended validation steps
1. Add the missing API keys to `.env` and restart the app.
2. Run `npm run dev` for renderer + Electron, verify the Idle UI appears, and use manual triggers to ensure IPC is wired.
3. Confirm microphone input reaches Gemini (watch logs for `Connected to Gemini Live` and state transitions).
4. Test `electron-builder` on a network that can fetch Electron binaries or with a configured mirror.
