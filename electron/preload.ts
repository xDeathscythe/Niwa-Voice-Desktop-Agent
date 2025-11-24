import { ipcRenderer, contextBridge } from 'electron'

contextBridge.exposeInMainWorld('ipcRenderer', {
    on(channel: string, listener: (event: Electron.IpcRendererEvent, ...args: any[]) => void) {
        const subscription = (event: Electron.IpcRendererEvent, ...args: any[]) => listener(event, ...args)
        ipcRenderer.on(channel, subscription)
        return () => {
            ipcRenderer.removeListener(channel, subscription)
        }
    },
    off(channel: string, ...args: any[]) {
        const [listener] = args
        ipcRenderer.off(channel, listener)
    },
    send(channel: string, ...args: any[]) {
        ipcRenderer.send(channel, ...args)
    },
    invoke(channel: string, ...args: any[]) {
        return ipcRenderer.invoke(channel, ...args)
    },
})
