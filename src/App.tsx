import React, { useState, useEffect } from 'react'

type AppState = 'IDLE' | 'LISTENING' | 'THINKING' | 'SPEAKING'

function App() {
    const [state, setState] = useState<AppState>('IDLE')
    const [error, setError] = useState<{message: string, details: string} | null>(null)

    useEffect(() => {
        // Listen for API errors
        const removeErrorListener = (window as any).ipcRenderer.on('api-error', (_event: any, errorData: any) => {
            console.error('API Error:', errorData)
            setError(errorData)
        })

        // Listen for state updates from Main process
        const removeStateListener = (window as any).ipcRenderer.on('niwa-state', (_event: any, newState: any) => {
            console.log('New State:', newState)
            setState(newState as AppState)
        })

        // Listen for audio playback
        const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
        const removeAudioListener = (window as any).ipcRenderer.on('play-audio', async (_event: any, buffer: ArrayBuffer) => {
            try {
                const audioBuffer = await audioContext.decodeAudioData(buffer.slice(0))
                const source = audioContext.createBufferSource()
                source.buffer = audioBuffer
                source.connect(audioContext.destination)
                source.start()
            } catch (e) {
                console.error('Error playing audio:', e)
            }
        })

        return () => {
            removeErrorListener()
            removeStateListener()
            removeAudioListener()
            audioContext.close()
        }
    }, [])

    // Visuals for different states
    const getColor = () => {
        switch (state) {
            case 'LISTENING': return 'bg-red-500'
            case 'THINKING': return 'bg-yellow-500'
            case 'SPEAKING': return 'bg-green-500'
            default: return 'bg-blue-500' // IDLE
        }
    }

    const handleManualTrigger = (command: 'NIWA' | 'NIWA_PISI') => {
        (window as any).ipcRenderer.send('manual-trigger', command)
    }

    // Show error message if API keys are missing
    if (error) {
        return (
            <div className="flex flex-col items-center justify-center h-screen w-screen bg-gradient-to-br from-red-900/80 to-red-600/80 backdrop-blur-sm overflow-hidden p-6">
                <div className="bg-black/60 backdrop-blur-md rounded-2xl p-6 border-2 border-red-500 shadow-2xl max-w-md">
                    <div className="text-red-400 text-4xl mb-4 text-center">⚠️</div>
                    <h2 className="text-white text-xl font-bold mb-3 text-center">{error.message}</h2>
                    <p className="text-gray-300 text-sm mb-4 text-center leading-relaxed">{error.details}</p>
                    <div className="text-xs text-gray-400 text-center">
                        <p>See README.md for setup instructions</p>
                    </div>
                </div>
            </div>
        )
    }

    if (state === 'IDLE') return null

    return (
        <div className="flex flex-col items-center justify-center h-screen w-screen bg-transparent overflow-hidden group">
            <div className="relative flex items-center justify-center w-32 h-32 mb-4">
                <div className={`absolute w-full h-full ${getColor()}/30 rounded-full animate-ping`}></div>
                <div className={`relative w-24 h-24 bg-black/80 text-white rounded-full flex items-center justify-center border-2 border-blue-400 shadow-[0_0_20px_rgba(59,130,246,0.5)] backdrop-blur-md transition-colors duration-300`}>
                    <span className="text-xl font-bold tracking-wider">NIWA</span>
                </div>
            </div>

            {/* Manual Triggers - Visible on Hover */}
            <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                <button
                    onClick={() => handleManualTrigger('NIWA')}
                    className="px-3 py-1 bg-blue-600 text-white text-xs rounded-full hover:bg-blue-500 shadow-lg"
                >
                    Chat
                </button>
                <button
                    onClick={() => handleManualTrigger('NIWA_PISI')}
                    className="px-3 py-1 bg-purple-600 text-white text-xs rounded-full hover:bg-purple-500 shadow-lg"
                >
                    Vision
                </button>
            </div>
        </div>
    )
}

export default App
