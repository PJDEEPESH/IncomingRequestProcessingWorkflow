import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The frontend calls /api/* which is proxied to the FastAPI backend on :8000,
// so there are no CORS headaches during development.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
