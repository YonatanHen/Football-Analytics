import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    // Bind-mounted source on Windows/Docker doesn't deliver inotify events;
    // poll so HMR actually picks up edits.
    watch: { usePolling: true, interval: 300 },
  },
})
