import { Porcupine, BuiltinKeyword } from '@picovoice/porcupine-node';
import { PvRecorder } from '@picovoice/pvrecorder-node';

export class WakeWordListener {
    private porcupine: Porcupine | null = null;
    private recorder: PvRecorder | null = null;
    private isListening = false;
    private accessKey: string;
    private onWakeWord: (keywordIndex: number) => void;
    private onAudioData: ((frame: Int16Array) => void) | null = null;

    constructor(accessKey: string, onWakeWord: (keywordIndex: number) => void) {
        this.accessKey = accessKey;
        this.onWakeWord = onWakeWord;
    }

    public setAudioCallback(callback: (frame: Int16Array) => void) {
        this.onAudioData = callback;
    }

    public start() {
        try {
            // TODO: Load custom .ppn files for "Niwa" and "Niwa Piši"
            // For now, use BuiltinKeyword.PORCUPINE as a placeholder for "Niwa"
            // and BuiltinKeyword.BUMBLEBEE as a placeholder for "Niwa Piši"
            this.porcupine = new Porcupine(
                this.accessKey,
                [BuiltinKeyword.PORCUPINE, BuiltinKeyword.BUMBLEBEE],
                [0.5, 0.5] // Sensitivities
            );

            this.recorder = new PvRecorder(this.porcupine.frameLength);
            this.recorder.start();
            this.isListening = true;

            console.log('Wake Word Listener started. Say "Porcupine" (Niwa) or "Bumblebee" (Niwa Piši)');
            this.loop();
        } catch (error) {
            console.error('Failed to start Wake Word Listener:', error);
        }
    }

    public stop() {
        this.isListening = false;
        this.recorder?.stop();
        this.recorder?.release();
        this.porcupine?.release();
        this.recorder = null;
        this.porcupine = null;
    }

    private async loop() {
        while (this.isListening && this.recorder && this.porcupine) {
            try {
                const frame = await this.recorder.read();

                // Emit audio data if callback is set (for Gemini Live)
                if (this.onAudioData) {
                    this.onAudioData(frame);
                }

                // Only process wake word if NOT streaming (or if we want parallel detection)
                // For now, let's keep detecting wake word even while streaming, 
                // but usually we pause it to avoid self-triggering if we speak.
                // But since we use headphones/echo cancellation (not implemented yet), let's just process.
                // Actually, better to PAUSE wake word detection when in conversation.
                if (!this.onAudioData) {
                    const keywordIndex = this.porcupine.process(frame);
                    if (keywordIndex >= 0) {
                        console.log(`Detected keyword index: ${keywordIndex}`);
                        this.onWakeWord(keywordIndex);
                    }
                }
            } catch (error) {
                console.error('Error in Wake Word loop:', error);
                this.isListening = false;
            }
        }
    }
}
