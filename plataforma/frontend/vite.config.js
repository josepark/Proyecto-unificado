import path from 'node:path';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

const raiz = path.resolve(__dirname);
const depsCompartidas = ['react', 'react-dom', 'react-router-dom', 'axios', 'lucide-react', 'recharts'];
const aliasDeps = Object.fromEntries(
  depsCompartidas.map((dep) => [dep, path.join(raiz, 'node_modules', dep)]),
);

// React es la interfaz principal en "/". nginx reenvía /api/, /rbac/api/,
// /riesgos/api/, etc. a cada backend.
export default defineConfig({
  base: '/',
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@riesgos': path.resolve(raiz, '../riesgos/frontend/src'),
      ...aliasDeps,
    },
    dedupe: depsCompartidas,
  },
  server: {
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/rbac': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/rbac/, ''),
      },
      '/riesgos/api': { target: 'http://localhost:8001', changeOrigin: true, rewrite: (p) => p.replace(/^\/riesgos/, '') },
      '/riesgos/media': { target: 'http://localhost:8001', changeOrigin: true, rewrite: (p) => p.replace(/^\/riesgos/, '') },
    },
  },
  build: {
    outDir: 'dist',
  },
  test: {
    environment: 'jsdom',
    setupFiles: './src/pruebas/setup.js',
    globals: true,
  },
});
