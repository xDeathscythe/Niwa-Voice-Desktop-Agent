import { app, BrowserWindow, ipcMain } from 'electron'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import dotenv from 'dotenv'

dotenv.config()

const __dirname = path.dirname(fileURLToPath(import.meta.url))

process.env.APP_ROOT = path.join(__dirname, '..')

// 🚧 Use ['ENV_NAME'] avoid vite:define plugin - Vite@2.x
export const VITE_DEV_SERVER_URL = process.env['VITE_DEV_SERVER_URL']
export const MAIN_DIST = path.join(process.env.APP_ROOT, 'dist-electron')
export const RENDERER_DIST = path.join(process.env.APP_ROOT, 'dist')

process.env.VITE_PUBLIC = VITE_DEV_SERVER_URL ? path.join(process.env.APP_ROOT, 'public') : RENDERER_DIST

let win: BrowserWindow | null

function createWindow() {
    win = new BrowserWindow({
        icon: path.join(process.env.VITE_PUBLIC || '', 'electron-vite.svg'),
        webPreferences: {
            preload: path.join(__dirname, 'preload.mjs'),
        },
        transparent: true,
        frame: false,
        alwaysOnTop: true,
        skipTaskbar: true,
        width: 300,
        height: 300,
        resizable: false,
        hasShadow: false,
    })

    // Test active push message to Renderer-process.
    win.webContents.on('did-finish-load', () => {
        win?.webContents.send('main-process-message', (new Date).toLocaleString())
    })

    if (VITE_DEV_SERVER_URL) {
        win.loadURL(VITE_DEV_SERVER_URL)
    } else {
        // win.loadFile('dist/index.html')
        win.loadFile(path.join(RENDERER_DIST, 'index.html'))
    }
}

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit()
        win = null
    }
})

app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createWindow()
    }
})

app.whenReady().then(() => {
    createWindow()

    // Initialize Wake Word & Gemini
    const accessKey = process.env.VITE_PICOVOICE_ACCESS_KEY
    const googleKey = process.env.VITE_GOOGLE_API_KEY

    if (!accessKey || !googleKey) {
        console.error('❌ Missing API Keys in .env file!')
        console.error('Missing:', [
            !accessKey && 'VITE_PICOVOICE_ACCESS_KEY',
            !googleKey && 'VITE_GOOGLE_API_KEY'
        ].filter(Boolean).join(', '))
        console.error('Please create a .env file based on .env.example')

        // Show error in renderer
        if (win) {
            win.webContents.on('did-finish-load', () => {
                win?.webContents.send('api-error', {
                    message: 'Missing API Keys',
                    details: 'Please configure VITE_PICOVOICE_ACCESS_KEY and VITE_GOOGLE_API_KEY in .env file'
                })
            })
        }
        return
    }

    if (accessKey && googleKey) {
        Promise.all([
            import('./services/wakeWord.ts'),
            import('./services/gemini.ts')
        ]).then(([{ WakeWordListener }, { GeminiLiveService }]) => {

            let geminiService: any = null;

            // Initialize Gemini
            geminiService = new GeminiLiveService(googleKey, (audioData) => {
                // Play audio in Renderer
                if (win) {
                    win.webContents.send('play-audio', audioData)
                    win.webContents.send('niwa-state', 'SPEAKING')
                }
            }, (text) => {
                console.log('Gemini Text:', text)
            })

            import('./services/vision.ts').then(({ VisionService }) => {
                const visionService = new VisionService(googleKey);

                // Initialize Wake Word
                const wakeWordListener = new WakeWordListener(accessKey, async (index) => {
                    if (win) {
                        // 0 = Niwa (Porcupine), 1 = Niwa Piši (Bumblebee)
                        const command = index === 0 ? 'NIWA' : 'NIWA_PISI'
                        console.log(`Wake Word Detected: ${command}`)

                        if (command === 'NIWA') {
                            win.webContents.send('niwa-state', 'LISTENING')
                            // Connect to Gemini if not connected
                            if (!geminiService.ws || geminiService.ws.readyState !== 1) {
                                geminiService.connect()
                            }

                            // Start streaming audio to Gemini
                            wakeWordListener.setAudioCallback((frame) => {
                                geminiService.sendAudio(frame)
                            })
                        } else if (command === 'NIWA_PISI') {
                            win.webContents.send('niwa-state', 'THINKING')
                            console.log('Analyzing screen...')
                            const coords = await visionService.analyzeScreenAndFindInput()
                            if (coords) {
                                console.log('Found coordinates:', coords)
                                // TODO: Use Nut.js to click (Native module build failed)
                                // import('@nut-tree/nut-js').then(async ({ mouse, Point }) => {
                                //     await mouse.setPosition(new Point(coords.x, coords.y));
                                //     await mouse.leftClick();
                                //     win?.webContents.send('niwa-state', 'LISTENING')
                                //     // Start dictation mode (streaming to Gemini, but asking for text output)
                                // })
                                console.log('Clicking at', coords)
                                win?.webContents.send('niwa-state', 'LISTENING')
                            }
                        }
                    }
                })
                wakeWordListener.start()

                // Handle Manual Triggers from UI
                ipcMain.on('manual-trigger', async (_event, command: 'NIWA' | 'NIWA_PISI') => {
                    console.log(`Manual Trigger: ${command}`)
                    if (command === 'NIWA') {
                        win?.webContents.send('niwa-state', 'LISTENING')
                        if (!geminiService.ws || geminiService.ws.readyState !== 1) {
                            geminiService.connect()
                        }
                        // For manual trigger, we might need to start recording immediately
                        // But wakeWordListener handles the recorder. 
                        // We need a way to tap into the audio stream without wake word.
                        // Let's force the audio callback on the listener.
                        wakeWordListener.setAudioCallback((frame) => {
                            geminiService.sendAudio(frame)
                        })
                    } else if (command === 'NIWA_PISI') {
                        win?.webContents.send('niwa-state', 'THINKING')
                        console.log('Analyzing screen...')
                        const coords = await visionService.analyzeScreenAndFindInput()
                        if (coords) {
                            console.log('Found coordinates:', coords)
                            console.log('Clicking at', coords)
                            win?.webContents.send('niwa-state', 'LISTENING')
                        }
                    }
                })
            })
        })
    } else {
        console.error('Missing API Keys in environment')
    }
})
