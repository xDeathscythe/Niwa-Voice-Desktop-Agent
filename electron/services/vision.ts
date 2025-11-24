import { GoogleGenerativeAI } from '@google/generative-ai';
import { desktopCapturer } from 'electron';

export class VisionService {
    private genAI: GoogleGenerativeAI;
    private model: any;

    constructor(apiKey: string) {
        this.genAI = new GoogleGenerativeAI(apiKey);
        this.model = this.genAI.getGenerativeModel({ model: "gemini-1.5-pro" }); // Using 1.5 Pro as 3 Pro might need specific preview flag or name
    }

    public async analyzeScreenAndFindInput(): Promise<{ x: number, y: number } | null> {
        try {
            // 1. Capture Screen
            const sources = await desktopCapturer.getSources({ types: ['screen'], thumbnailSize: { width: 1920, height: 1080 } });
            const primarySource = sources[0]; // Assuming primary screen
            const imageBase64 = primarySource.thumbnail.toDataURL().split(',')[1];

            // 2. Send to Gemini
            const prompt = `
        Analyze this screenshot. I want to click on the main input field or search bar relevant to the current context.
        If it's a browser, find the search bar or the main text input on the page.
        If it's a code editor, find the cursor position or main editor area.
        Return ONLY a JSON object with "x" and "y" coordinates of the center of that field.
        Example: { "x": 500, "y": 300 }
      `;

            const result = await this.model.generateContent([
                prompt,
                {
                    inlineData: {
                        data: imageBase64,
                        mimeType: "image/png"
                    }
                }
            ]);

            const response = await result.response;
            const text = response.text();

            // Extract JSON
            const jsonMatch = text.match(/\{.*?\}/s);
            if (jsonMatch) {
                const coords = JSON.parse(jsonMatch[0]);
                return coords;
            }

            return null;
        } catch (error) {
            console.error('Vision Service Error:', error);
            return null;
        }
    }
}
