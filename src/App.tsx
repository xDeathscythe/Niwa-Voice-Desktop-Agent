import React, { useState, useEffect } from 'react'

type AppState = 'IDLE' | 'LISTENING' | 'THINKING' | 'SPEAKING'

function App() {
    const [state, setState] = useState<AppState>('IDLE')

    useEffect(() => {
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

    const getLabel = () => {
        switch (state) {
            case 'LISTENING':
                return 'Listening'
            case 'THINKING':
                return 'Thinking'
            case 'SPEAKING':
                return 'Speaking'
            default:
                return 'Idle'
        }
    }

    const handleManualTrigger = (command: 'NIWA' | 'NIWA_PISI') => {
        (window as any).ipcRenderer.send('manual-trigger', command)
    }

    return (
        <div className="flex flex-col items-center justify-center h-screen w-screen bg-transparent overflow-hidden group">
            <div className="relative flex items-center justify-center w-32 h-32 mb-4">
                <div className={`absolute w-full h-full ${getColor()}/30 rounded-full animate-ping`}></div>
                <div className={`relative w-24 h-24 bg-black/80 text-white rounded-full flex flex-col items-center justify-center border-2 border-blue-400 shadow-[0_0_20px_rgba(59,130,246,0.5)] backdrop-blur-md transition-colors duration-300`}>
                    <span className="text-xl font-bold tracking-wider">NIWA</span>
                    <span className="text-[10px] uppercase tracking-wide opacity-80">{getLabel()}</span>
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
