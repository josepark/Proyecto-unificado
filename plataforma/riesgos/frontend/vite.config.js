import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  // En desarrollo local sirve en "/". Al construir para la Plataforma SUIIN
  // unificada (nginx sirve esto bajo /riesgos/, ver plataforma/nginx/Dockerfile),
  // se pasa VITE_BASE_PATH=/riesgos/ como build arg para que cada asset del
  // build quede con ese prefijo horneado.
  base: process.env.VITE_BASE_PATH || '/',
  server: {
    port: 5173,
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.js',
    globals: true,
    css: false,
  },
})
