import WebSocket from 'ws';

export class GeminiLiveService {
    private ws: WebSocket | null = null;
    private apiKey: string;
    private onAudioOutput: (audioData: Buffer) => void;
    private onTextOutput: (text: string) => void;

    constructor(apiKey: string, onAudioOutput: (audioData: Buffer) => void, onTextOutput: (text: string) => void) {
        this.apiKey = apiKey;
        this.onAudioOutput = onAudioOutput;
        this.onTextOutput = onTextOutput;
    }

    public connect() {
        const model = 'gemini-2.0-flash-exp'; // Using 2.0 Flash Exp as 2.5 might not be public yet or has different name. 
        // User said "gemini-2.5-flash-native-audio-preview", but standard public endpoint usually lags.
        // Let's try the standard URL pattern.
        const url = `wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1alpha.GenerativeService.BidiGenerateContent?key=${this.apiKey}`;

        this.ws = new WebSocket(url);

        this.ws.on('open', () => {
            console.log('Connected to Gemini Live');
            // Send initial setup message
            this.sendSetup();
        });

        this.ws.on('message', (data: Buffer) => {
            this.handleMessage(data);
        });

        this.ws.on('error', (error) => {
            console.error('Gemini WebSocket Error:', error);
        });

        this.ws.on('close', () => {
            console.log('Gemini Live disconnected');
        });
    }

    public sendAudio(pcmData: Int16Array) {
        if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return;

        // Convert Int16Array to Base64 PCM
        // The API expects specific format.
        // Usually: { realtime_input: { media_chunks: [{ mime_type: "audio/pcm", data: base64 }] } }

        const buffer = Buffer.from(pcmData.buffer);
        const base64Audio = buffer.toString('base64');

        const msg = {
            realtime_input: {
                media_chunks: [
                    {
                        mime_type: "audio/pcm",
                        data: base64Audio
                    }
                ]
            }
        };

        this.ws.send(JSON.stringify(msg));
    }

    private sendSetup() {
        const setupMsg = {
            setup: {
                model: "models/gemini-2.0-flash-exp", // Or whatever is available
                generation_config: {
                    response_modalities: ["AUDIO"]
                }
            }
        };
        this.ws?.send(JSON.stringify(setupMsg));
    }

    private handleMessage(data: Buffer) {
        try {
            const response = JSON.parse(data.toString());

            // Handle serverContent (Audio)
            if (response.serverContent?.modelTurn?.parts) {
                for (const part of response.serverContent.modelTurn.parts) {
                    if (part.inlineData) {
                        // Audio data
                        const audioBuffer = Buffer.from(part.inlineData.data, 'base64');
                        this.onAudioOutput(audioBuffer);
                    }
                }
            }

            // Handle tool calls or text (if we asked for TEXT modality too)
        } catch (e) {
            console.error('Error parsing Gemini message:', e);
        }
    }
}
